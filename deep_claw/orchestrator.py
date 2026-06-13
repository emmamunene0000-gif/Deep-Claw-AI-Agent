"""
Deep Claw Orchestrator — the main async event loop.

Wiring:
  CandleBus → MarketStateBuilder → EpisodeEmitter
           → [ut_bot, smart_rsi, liquidity_zone, structure_shift]
           → ChainReasoningEngine → ConfidenceEngine
           → [Claude qualification (optional)]
           → PositionStateMachine → BrokerAdapter
           → EpisodeStream → Renderer → Telegram

One PositionStateMachine per symbol. CandleBus is shared across all.
The orchestrator owns no trade state — it is a pure routing layer.

Lifecycle:
  1. startup()  — connect broker feeds, backfill outcome labeler
  2. run()      — event loop until shutdown signal
  3. shutdown() — flush, write daily reports, disconnect

Phase 2 swap point:
  Replace `confidence_v1.confidence(ms, weights)` with
  `learning.inference.predict_confidence(ms)` by setting USE_ML_CONFIDENCE=true.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from deep_claw.action.protocol import BrokerAdapter
from deep_claw.claude.daily_assessment import run_daily_assessment
from deep_claw.claude.qualification import QualificationVerdict, qualify_signal
from deep_claw.claude.sl_autopsy import run_sl_autopsy
from deep_claw.cognition.chain_reasoning import ChainReasoningEngine
from deep_claw.cognition.confidence_v1 import DEFAULT_WEIGHT_MATRIX, confidence
from deep_claw.cognition.position_manager import PositionStateMachine
from deep_claw.cognition.signals.liquidity_zone import liquidity_zone_signal
from deep_claw.cognition.signals.smart_rsi import smart_rsi_signal
from deep_claw.cognition.signals.structure_shift import structure_shift_signal
from deep_claw.cognition.signals.ut_bot import ut_bot_signal
from deep_claw.communication.dashboard import build_app
from deep_claw.communication.renderer import EpisodeStreamRenderer
from deep_claw.communication.telegram import TelegramDispatcher
from deep_claw.config.settings import settings
from deep_claw.core.types import (
    ClaudeVerdict,
    Episode,
    EpisodeType,
    MarketState,
    PositionHandle,
    SignalCandidate,
    TradeInstruction,
)
from deep_claw.journal.daily_report import DailyReport
from deep_claw.journal.episode_stream import EpisodeStream
from deep_claw.journal.feature_store import FeatureStore
from deep_claw.journal.outcome_labeler import OutcomeLabeler
from deep_claw.journal.pip_tracker import PipTracker
from deep_claw.perception.episode_emitter import EpisodeEmitter
from deep_claw.perception.market_state import MarketStateBuilder

log = logging.getLogger(__name__)


class SymbolContext:
    """All per-symbol state bundled together."""

    def __init__(self, symbol: str, stream: EpisodeStream) -> None:
        self.symbol = symbol
        self.stream = stream
        self.market_state_builder = MarketStateBuilder(symbol)
        self.episode_emitter = EpisodeEmitter(stream)
        self.chain_engine = ChainReasoningEngine(stream)
        self.pip_tracker = PipTracker(symbol)
        self.position_machine: PositionStateMachine | None = None  # set after broker adapters ready
        self.last_market_state: MarketState | None = None
        self.session_start: datetime = datetime.now(timezone.utc)


class Orchestrator:
    """
    Top-level coordinator. Stateless with respect to trade execution —
    all trade state lives in PositionStateMachine.
    """

    def __init__(
        self,
        symbols: list[str],
        broker_adapters: dict[str, BrokerAdapter],  # symbol → adapter
        db_path: Path = Path("data"),
        enable_dashboard: bool = True,
    ) -> None:
        self._symbols = [s.upper() for s in symbols]
        self._broker_adapters = broker_adapters
        self._db_path = db_path

        # Shared infrastructure
        self._stream = EpisodeStream(db_path / "episodes.db")
        self._feature_store = FeatureStore(db_path / "feature_store.db")
        self._daily_report = DailyReport(db_path / "daily_reports.db")
        self._renderer = EpisodeStreamRenderer(self._stream)
        self._telegram = TelegramDispatcher()
        self._outcome_labeler = OutcomeLabeler(self._stream, self._feature_store)

        # Per-symbol contexts
        self._contexts: dict[str, SymbolContext] = {
            s: SymbolContext(s, self._stream) for s in self._symbols
        }

        # Dashboard (optional)
        self._dashboard_app = None
        if enable_dashboard:
            try:
                pip_trackers = {s: ctx.pip_tracker for s, ctx in self._contexts.items()}
                self._dashboard_app = build_app(
                    self._stream, self._renderer, pip_trackers, self._daily_report
                )
            except RuntimeError:
                log.info("Dashboard disabled — fastapi not installed")

        self._running = False
        self._daily_report_task: asyncio.Task | None = None

    # ── Startup ───────────────────────────────────────────────────────────────

    async def startup(self) -> None:
        log.info("Deep Claw startup — symbols: %s", self._symbols)

        # Wire PositionStateMachine for each symbol
        for sym, ctx in self._contexts.items():
            adapter = self._broker_adapters.get(sym)
            if not adapter:
                log.warning("No broker adapter for %s — position management disabled", sym)
                continue
            ctx.position_machine = PositionStateMachine(
                symbol=sym,
                stream=self._stream,
                open_trade_fn=lambda inst, a=adapter: asyncio.ensure_future(a.open_position(inst)),
                modify_stop_fn=lambda h, sl, a=adapter: asyncio.ensure_future(a.modify_stop(h, sl)),
                partial_close_fn=lambda h, p, a=adapter: asyncio.ensure_future(a.partial_close(h, p)),
                close_fn=lambda h, a=adapter: asyncio.ensure_future(a.close_position(h)),
            )

        # Backfill outcome labels for any trades that closed while offline
        for sym in self._symbols:
            try:
                labeled = self._outcome_labeler.backfill_from_stream(sym)
                if labeled:
                    log.info("Backfilled %d outcome labels for %s", labeled, sym)
            except Exception as e:
                log.warning("Backfill failed for %s: %s", sym, e)

        # Schedule EOD report
        self._daily_report_task = asyncio.create_task(self._daily_report_loop())
        self._running = True
        log.info("Deep Claw ready")

    # ── Main bar handler ──────────────────────────────────────────────────────

    async def on_bar(self, symbol: str, candle) -> None:
        """
        Called by the broker feed adapter on each confirmed bar close.
        This is the single entry point for all price data.
        """
        ctx = self._contexts.get(symbol)
        if not ctx:
            return

        # 1. Build MarketState from confirmed candle
        market_state = ctx.market_state_builder.update(candle)
        if market_state is None:
            return  # not enough history yet
        ctx.last_market_state = market_state

        # 2. Emit structural episodes (session change, BOS, CHoCH, etc.)
        ctx.episode_emitter.update(market_state)

        # 3. Price check on open position (SL/TP progression)
        if ctx.position_machine:
            instructions = ctx.position_machine.update_price(market_state)
            for inst in instructions:
                await self._handle_trade_instruction(ctx, inst, market_state)

        # 4. Run all signal generators in parallel (pure functions — no shared state)
        candidates = _run_signal_generators(market_state)
        if not candidates:
            return

        # 5. Route candidates through chain + confidence + position machine
        accepted = await self._evaluate_candidates(ctx, candidates, market_state)
        if accepted:
            log.debug("%s: %d candidate(s) accepted", symbol, len(accepted))

    # ── Signal evaluation pipeline ────────────────────────────────────────────

    async def _evaluate_candidates(
        self,
        ctx: SymbolContext,
        candidates: list[SignalCandidate],
        market_state: MarketState,
    ) -> list[TradeInstruction]:
        instructions = []
        for candidate in candidates:
            inst = await self._evaluate_one(ctx, candidate, market_state)
            if inst:
                instructions.append(inst)
        return instructions

    async def _evaluate_one(
        self,
        ctx: SymbolContext,
        candidate: SignalCandidate,
        market_state: MarketState,
    ) -> TradeInstruction | None:
        # Chain reasoning
        chain_verdict = ctx.chain_engine.evaluate(candidate, market_state)

        # Confidence scoring (Phase 1: hand-tuned weights; Phase 2: ML model)
        if settings.use_ml_confidence:
            conf_result = _ml_confidence(market_state)
        else:
            conf_result = confidence(market_state, DEFAULT_WEIGHT_MATRIX)

        # Write feature store row (BEFORE filtering — shadow-blocked rows matter for ML)
        row_id = self._feature_store.write_candidate(
            candidate=candidate,
            market_state=market_state,
            chain_verdict=chain_verdict,
            confidence_result=conf_result,
            fired=False,  # tentative — updated if accepted
            rejection_reason=None,
        )

        # Position machine processes the candidate
        if not ctx.position_machine:
            return None

        instruction = ctx.position_machine.process_candidates([candidate], market_state)

        if instruction is None:
            # Rejected by position machine — feature row stays fired=False
            return None

        # Claude qualification (optional gate before broker commit)
        if settings.enable_claude_qualification:
            verdict = await qualify_signal(
                candidate=candidate,
                market_state=market_state,
                chain_verdict=chain_verdict,
                stream=self._stream,
                renderer=self._renderer,
            )
            if verdict.verdict == ClaudeVerdict.REJECT:
                log.info("Claude REJECTED %s signal for %s", candidate.source.value, ctx.symbol)
                return None
            elif verdict.verdict == ClaudeVerdict.MODIFY:
                instruction = _apply_claude_modifiers(instruction, verdict)

        # Update feature store: mark as fired=True with trade_id
        self._feature_store.label_outcome(
            trade_id=instruction.trade_id or "",
            realized_r=0.0,
            exit_reason="PENDING",
            bar_count=0,
            mfe_r=0.0,
            mae_r=0.0,
            autopsy_tag=None,
        )

        # PipTracker
        ctx.pip_tracker.record_signal(market_state.session.value)

        # Telegram — war room signal alert
        war_room = self._renderer.to_telegram_narrative(
            symbol=ctx.symbol,
            event_title=f"SIGNAL — {candidate.source.value}",
            event_commentary=f"{candidate.direction.value} | {chain_verdict.verdict.value} | conf {conf_result.directional_confidence:.0f}%",
            market_state=market_state,
        )
        public = self._renderer.to_telegram_public(war_room)
        asyncio.ensure_future(self._telegram.send_signal_alert(war_room, public))

        return instruction

    async def _handle_trade_instruction(
        self,
        ctx: SymbolContext,
        instruction: TradeInstruction,
        market_state: MarketState,
    ) -> None:
        """Route a TradeInstruction to the broker adapter."""
        adapter = self._broker_adapters.get(ctx.symbol)
        if not adapter:
            return
        try:
            if instruction.action == "OPEN":
                handle: PositionHandle = await adapter.open_position(instruction)
                log.info("Position opened: %s %s", ctx.symbol, instruction.trade_id)
            elif instruction.action == "CLOSE":
                # Find handle — position machine tracks it
                pass  # PositionStateMachine holds the handle and calls adapter directly
        except Exception as e:
            log.error("Broker error for %s: %s", ctx.symbol, e)
            await self._telegram.send_error(ctx.symbol, str(e))

        # Backfill outcome label after close
        if instruction.action == "CLOSE" and instruction.trade_id:
            self._outcome_labeler.process_episode(
                Episode(
                    episode_type=EpisodeType.TRADE_CLOSED,
                    symbol=ctx.symbol,
                    timestamp=datetime.now(timezone.utc),
                    payload={
                        "trade_id": instruction.trade_id,
                        "realized_r": getattr(instruction, "realized_r", 0.0),
                        "exit_reason": getattr(instruction, "exit_reason", "UNKNOWN"),
                    },
                )
            )

        # SL autopsy if stop-out
        ep_type = getattr(instruction, "_episode_type", None)
        if ep_type == EpisodeType.SL_HIT:
            lesson = await run_sl_autopsy(
                sl_episode=self._stream.recent(ctx.symbol, n=1)[0],
                market_state=market_state,
                stream=self._stream,
            )
            asyncio.ensure_future(
                self._telegram.send_sl_autopsy(
                    ctx.symbol, instruction.trade_id or "?", lesson
                )
            )

    # ── Episode subscription (outcome labeling) ───────────────────────────────

    def on_episode(self, episode: Episode) -> None:
        """
        Called by EpisodeStream subscribers after each append.
        Routes outcome-closing episodes to the labeler.
        """
        if self._outcome_labeler.process_episode(episode):
            ctx = self._contexts.get(episode.symbol)
            if ctx:
                payload = episode.payload
                r = payload.get("realized_r", 0.0)
                exit_reason = payload.get("exit_reason", "")
                if exit_reason == "SL":
                    ctx.pip_tracker.record_sl(r)
                elif exit_reason == "TP1":
                    ctx.pip_tracker.record_tp1(r)
                elif exit_reason == "TP2":
                    ctx.pip_tracker.record_tp2(r)
                elif exit_reason == "TP3":
                    ctx.pip_tracker.record_tp3(r)
                elif exit_reason == "HOLDER_EXIT":
                    ctx.pip_tracker.record_holder_exit(r)

    # ── EOD report loop ───────────────────────────────────────────────────────

    async def _daily_report_loop(self) -> None:
        """Wait until report_hour_utc, write daily reports, then repeat."""
        while self._running:
            now = datetime.now(timezone.utc)
            target_hour = settings.report_hour_utc
            # Seconds until next report window
            seconds_until = _seconds_until_hour(now, target_hour)
            await asyncio.sleep(seconds_until)
            if not self._running:
                break
            await self._run_eod_reports()

    async def _run_eod_reports(self) -> None:
        log.info("Running EOD daily reports")
        for sym, ctx in self._contexts.items():
            since = ctx.session_start
            try:
                # Daily assessment via Claude
                proposals = await run_daily_assessment(
                    symbol=sym,
                    since=since,
                    stream=self._stream,
                    renderer=self._renderer,
                )
                assessment_text = "; ".join(proposals[:3])

                # Write structured daily report row
                self._daily_report.write(
                    symbol=sym,
                    pip_tracker=ctx.pip_tracker,
                    stream=self._stream,
                    since=since,
                    assessment_text=assessment_text,
                    proposal_count=len(proposals),
                )

                # Telegram EOD summary
                summary = self._renderer.to_daily_summary(sym, since)
                await self._telegram.send_daily_summary(sym, summary)
                if proposals:
                    await self._telegram.send_proposal_alert(sym, proposals)

                # Reset session clock
                ctx.session_start = datetime.now(timezone.utc)

            except Exception as e:
                log.error("EOD report failed for %s: %s", sym, e)
                await self._telegram.send_error(f"EOD {sym}", str(e))

    # ── Shutdown ──────────────────────────────────────────────────────────────

    async def shutdown(self) -> None:
        log.info("Deep Claw shutdown initiated")
        self._running = False
        if self._daily_report_task:
            self._daily_report_task.cancel()
            try:
                await self._daily_report_task
            except asyncio.CancelledError:
                pass
        # Final EOD flush
        await self._run_eod_reports()
        log.info("Deep Claw shut down cleanly")


# ── Pure helper functions (no class state) ────────────────────────────────────

def _run_signal_generators(market_state: MarketState) -> list[SignalCandidate]:
    """
    All four generators are pure functions. Called in series — fast enough.
    Each returns SignalCandidate | None. None results are filtered out.
    """
    generators = [ut_bot_signal, smart_rsi_signal, liquidity_zone_signal, structure_shift_signal]
    results = []
    for gen in generators:
        try:
            result = gen(market_state)
            if result is not None:
                results.append(result)
        except Exception as e:
            log.warning("Signal generator %s error: %s", gen.__name__, e)
    return results


def _apply_claude_modifiers(
    instruction: TradeInstruction,
    verdict: QualificationVerdict,
) -> TradeInstruction:
    """Apply Claude's size/SL modifications to a TradeInstruction."""
    from dataclasses import replace
    return replace(
        instruction,
        size=instruction.size * verdict.size_modifier,
        sl=instruction.sl * verdict.sl_modifier if instruction.sl else instruction.sl,
    )


def _ml_confidence(market_state: MarketState):
    """
    Phase 2 swap point. When USE_ML_CONFIDENCE=true, this is called instead of
    confidence_v1.confidence(). Returns same ConfidenceResult interface.
    """
    try:
        from deep_claw.learning.inference import predict_confidence
        return predict_confidence(market_state)
    except ImportError:
        log.warning("ML inference module not available — falling back to v1 confidence")
        return confidence(market_state, DEFAULT_WEIGHT_MATRIX)


def _seconds_until_hour(now: datetime, target_hour: int) -> float:
    """Seconds until the next occurrence of target_hour UTC."""
    if now.hour < target_hour:
        delta_hours = target_hour - now.hour
        delta_seconds = delta_hours * 3600 - now.minute * 60 - now.second
    else:
        # Next day
        delta_hours = 24 - now.hour + target_hour
        delta_seconds = delta_hours * 3600 - now.minute * 60 - now.second
    return max(60.0, float(delta_seconds))
