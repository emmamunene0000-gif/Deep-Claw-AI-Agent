"""
Deep Claw Orchestrator — the main async event loop.

Data flow (one confirmed bar close triggers everything):
  Feed (Deriv/Bybit WS) → NormalizedCandleBus.ingest() → _on_confirmed_bar()
    → MarketStateBuilder.build()        → MarketState
    → EpisodeEmitter.update()           → structural episodes (BOS/CHoCH/session)
    → PositionStateMachine.update_price()  → TP/SL progression
    → [4 pure signal generators]        → List[SignalCandidate]
    → ChainReasoningEngine.evaluate()   → ChainVerdict
    → confidence()                      → ConfidenceResult
    → [optional Claude qualification]   → QualificationVerdict
    → PositionStateMachine.process_candidates() → TradeInstruction
    → BrokerAdapter.open_position()     → PositionHandle
    → Telegram, FeatureStore, PipTracker

The orchestrator owns NO trade state. All state lives in PositionStateMachine.
The bus is the bridge between feeds and processing — the only data path.

Phase 2 swap: set USE_ML_CONFIDENCE=true to route through learning/inference.py.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path

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
from deep_claw.communication.renderer import EpisodeStreamRenderer
from deep_claw.communication.telegram import TelegramDispatcher
from deep_claw.config.settings import settings
from deep_claw.core.types import (
    ClaudeVerdict,
    Episode,
    EpisodeType,
    MarketState,
    NormalizedCandle,
    PositionHandle,
    SignalCandidate,
    Timeframe,
    TradeInstruction,
)
from deep_claw.journal.daily_report import DailyReport
from deep_claw.journal.episode_stream import EpisodeStream
from deep_claw.journal.feature_store import FeatureStore
from deep_claw.journal.outcome_labeler import OutcomeLabeler
from deep_claw.journal.pip_tracker import PipTracker
from deep_claw.perception.candle_bus import NormalizedCandleBus
from deep_claw.perception.episode_emitter import EpisodeEmitter
from deep_claw.perception.market_state import MarketStateBuilder

log = logging.getLogger(__name__)

# Primary timeframe that triggers signal evaluation
_EXEC_TF = settings.exec_tf


class SymbolContext:
    """All per-symbol processing state. The orchestrator creates one per symbol."""

    def __init__(self, symbol: str, stream: EpisodeStream) -> None:
        self.symbol = symbol
        self.stream = stream
        self.market_state_builder = MarketStateBuilder(symbol, exec_tf=_EXEC_TF)
        self.episode_emitter = EpisodeEmitter(symbol, stream)
        self.chain_engine = ChainReasoningEngine(stream)
        self.pip_tracker = PipTracker(symbol)
        self.position_machine: PositionStateMachine | None = None
        self.last_market_state: MarketState | None = None
        self.last_chain_verdict = None
        self.last_confidence_result = None
        self.session_start: datetime = datetime.now(timezone.utc)


class Orchestrator:
    """
    Stateless routing layer. All trade state lives in PositionStateMachine.
    Registered as a NormalizedCandleBus handler — woken on each confirmed bar close.
    """

    def __init__(
        self,
        symbols: list[str],
        bus: NormalizedCandleBus,
        broker_adapters: dict[str, BrokerAdapter],
        db_path: Path = Path("data"),
    ) -> None:
        self._symbols = [s.upper() for s in symbols]
        self._bus = bus
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

        self._running = False
        self._paused = False
        self._bars_processed = 0
        self._startup_time = datetime.now(timezone.utc)
        self._daily_report_task: asyncio.Task | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    # ── Startup ───────────────────────────────────────────────────────────────

    async def startup(self) -> None:
        self._loop = asyncio.get_running_loop()
        log.info("Deep Claw startup — symbols: %s", self._symbols)

        # Wire PositionStateMachine per symbol
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

        # Register bus handler — woken on every confirmed bar close
        self._bus.register_handler(self._on_confirmed_bar_sync)

        # Backfill outcome labels for trades that closed while offline
        for sym in self._symbols:
            try:
                labeled = self._outcome_labeler.backfill_from_stream(sym)
                if labeled:
                    log.info("Backfilled %d outcome labels for %s", labeled, sym)
            except Exception as e:
                log.warning("Backfill failed for %s: %s", sym, e)

        # EOD report scheduler
        self._daily_report_task = asyncio.create_task(self._daily_report_loop())
        self._running = True

        await self._telegram.send_war_room(
            "<b>🟢 DEEP CLAW ONLINE</b>\n"
            f"Symbols: {', '.join(self._symbols)}\n"
            f"Mode: {'DEMO' if settings.bybit_testnet else 'LIVE'}\n"
            f"Claude: {'ON' if settings.enable_claude_qualification else 'OFF'}\n"
            f"ML Confidence: {'ON' if settings.use_ml_confidence else 'OFF (v1 weights)'}"
        )
        log.info("Deep Claw ready — registered bus handler for %s", self._symbols)

    # ── Bus handler ───────────────────────────────────────────────────────────

    def _on_confirmed_bar_sync(self, candle: NormalizedCandle) -> None:
        """
        Sync entry point called by the bus on each confirmed close.
        Only processes exec TF candles (M15) for signal generation.
        All TF candles are already stored in the bus for indicator lookback.
        """
        if candle.symbol not in self._contexts:
            return
        if candle.timeframe != _EXEC_TF:
            return  # non-exec TF: stored in bus, not processed for signals
        if self._loop is None:
            return
        asyncio.ensure_future(
            self._process_confirmed_bar(candle), loop=self._loop
        )

    async def _process_confirmed_bar(self, candle: NormalizedCandle) -> None:
        """Full processing pipeline for one confirmed M15 bar close."""
        ctx = self._contexts[candle.symbol]
        self._bars_processed += 1

        # 1. Build MarketState from full bus history (all TFs)
        market_state = ctx.market_state_builder.build(self._bus)
        if market_state is None:
            return  # not enough history
        ctx.last_market_state = market_state

        # 2. Structural episode emission (BOS, CHoCH, session change, ATR regime)
        ctx.episode_emitter.update(market_state)

        # 3. TP/SL price-check on open position (runs even when paused)
        if ctx.position_machine:
            instructions = ctx.position_machine.update_price(market_state)
            for inst in instructions:
                await self._dispatch_instruction(ctx, inst, market_state)

        # 4. Signal generation — skipped when paused by operator
        if self._paused:
            return

        candidates = _run_signal_generators(market_state)
        if not candidates:
            return

        # 5. Route each candidate through the full evaluation pipeline
        for candidate in candidates:
            await self._evaluate_candidate(ctx, candidate, market_state)

    # ── Signal evaluation pipeline ────────────────────────────────────────────

    async def _evaluate_candidate(
        self,
        ctx: SymbolContext,
        candidate: SignalCandidate,
        market_state: MarketState,
    ) -> None:
        # Chain reasoning
        chain_verdict = ctx.chain_engine.evaluate(candidate, market_state)

        # Confidence scoring
        if settings.use_ml_confidence:
            conf_result = _ml_confidence(market_state)
        else:
            conf_result = confidence(market_state, DEFAULT_WEIGHT_MATRIX)

        ctx.last_chain_verdict = chain_verdict
        ctx.last_confidence_result = conf_result

        # Write feature row (fired=False initially — updated if accepted below)
        self._feature_store.write_candidate(
            candidate=candidate,
            market_state=market_state,
            chain_verdict=chain_verdict,
            confidence_result=conf_result,
            fired=False,
            rejection_reason=None,
        )

        if not ctx.position_machine:
            return

        # Position machine: one-trade rule, confidence gate, SL/TP computation
        instruction = ctx.position_machine.process_candidates([candidate], market_state)
        if instruction is None:
            return  # rejected — feature row stays shadow-blocked (fired=False)

        # Claude qualification (optional pre-commit gate)
        if settings.enable_claude_qualification:
            qv = await qualify_signal(
                candidate=candidate,
                market_state=market_state,
                chain_verdict=chain_verdict,
                stream=self._stream,
                renderer=self._renderer,
            )
            if qv.verdict == ClaudeVerdict.REJECT:
                log.info("Claude REJECTED %s %s", candidate.source.value, ctx.symbol)
                ctx.pip_tracker.record_blocked()
                return
            if qv.verdict == ClaudeVerdict.MODIFY:
                instruction = _apply_claude_modifiers(instruction, qv)

        # Accepted — update feature row, pip tracker
        self._feature_store.write_candidate(
            candidate=candidate,
            market_state=market_state,
            chain_verdict=chain_verdict,
            confidence_result=conf_result,
            fired=True,
            rejection_reason=None,
            trade_id=instruction.trade_id,
        )
        ctx.pip_tracker.record_signal(market_state.session.value)

        # Dispatch to broker
        await self._dispatch_instruction(ctx, instruction, market_state)

        # Telegram war room alert
        dir_conf = conf_result.bull_confidence if candidate.direction.value == "LONG" else conf_result.bear_confidence
        war_room = self._renderer.to_telegram_narrative(
            symbol=ctx.symbol,
            event_title=f"SIGNAL — {candidate.source.value}",
            event_commentary=(
                f"{candidate.direction.value} | {chain_verdict.verdict.value} "
                f"| conf {dir_conf:.0f}% | R={instruction.tp1:.5f}"
            ),
            market_state=market_state,
        )
        public = self._renderer.to_telegram_public(war_room)
        asyncio.ensure_future(self._telegram.send_signal_alert(war_room, public))

    # ── Trade instruction dispatch ────────────────────────────────────────────

    async def _dispatch_instruction(
        self,
        ctx: SymbolContext,
        instruction: TradeInstruction,
        market_state: MarketState,
    ) -> None:
        """
        Route a TradeInstruction to the broker adapter.
        Also handles SL autopsy on stop-outs.
        """
        adapter = self._broker_adapters.get(ctx.symbol)
        if not adapter:
            return

        try:
            if getattr(instruction, "action", "OPEN") == "OPEN":
                handle: PositionHandle = await adapter.open_position(instruction)
                # Store handle back in position machine
                if ctx.position_machine and ctx.position_machine._state:
                    ctx.position_machine._state.handle = handle
                log.info("Position opened: %s trade_id=%s", ctx.symbol, instruction.trade_id)

        except Exception as e:
            log.error("Broker error [%s]: %s", ctx.symbol, e)
            asyncio.ensure_future(self._telegram.send_error(ctx.symbol, str(e)))

        # Outcome labeling for closing events
        episode_type = getattr(instruction, "_episode_type", None)
        if episode_type in {EpisodeType.SL_HIT, EpisodeType.TRADE_CLOSED, EpisodeType.HOLDER_EXIT}:
            recent = self._stream.recent(ctx.symbol, n=1)
            if recent:
                self._outcome_labeler.process_episode(recent[0])

            # SL autopsy
            if episode_type == EpisodeType.SL_HIT:
                sl_episodes = self._stream.recent(ctx.symbol, n=1)
                if sl_episodes:
                    lesson = await run_sl_autopsy(sl_episodes[0], market_state, self._stream)
                    asyncio.ensure_future(
                        self._telegram.send_sl_autopsy(ctx.symbol, instruction.trade_id or "?", lesson)
                    )

    # ── Episode subscriber (called by PositionStateMachine via stream callbacks) ─

    def on_episode(self, episode: Episode) -> None:
        """
        Route outcome-closing episodes to labeler and pip tracker.
        Called by EpisodeStream after each append (if wired).
        """
        if not self._outcome_labeler.process_episode(episode):
            return
        ctx = self._contexts.get(episode.symbol)
        if not ctx:
            return
        payload = episode.payload
        r = float(payload.get("realized_r", 0.0))
        reason = payload.get("exit_reason", "")
        if reason == "SL":
            ctx.pip_tracker.record_sl(r)
        elif reason == "TP1":
            ctx.pip_tracker.record_tp1(r)
        elif reason == "TP2":
            ctx.pip_tracker.record_tp2(r)
        elif reason == "TP3":
            ctx.pip_tracker.record_tp3(r)
        elif reason == "HOLDER_EXIT":
            ctx.pip_tracker.record_holder_exit(r)

    # ── EOD report loop ───────────────────────────────────────────────────────

    async def _daily_report_loop(self) -> None:
        while self._running:
            now = datetime.now(timezone.utc)
            seconds = _seconds_until_hour(now, settings.report_hour_utc)
            await asyncio.sleep(seconds)
            if self._running:
                await self._run_eod_reports()

    async def _run_eod_reports(self) -> None:
        log.info("Running EOD daily reports")
        for sym, ctx in self._contexts.items():
            since = ctx.session_start
            try:
                proposals = await run_daily_assessment(
                    symbol=sym, since=since, stream=self._stream, renderer=self._renderer,
                )
                assessment_text = "; ".join(proposals[:3])

                self._daily_report.write(
                    symbol=sym, pip_tracker=ctx.pip_tracker,
                    stream=self._stream, since=since,
                    assessment_text=assessment_text,
                    proposal_count=len(proposals),
                )

                summary = self._renderer.to_daily_summary(sym, since)
                await self._telegram.send_daily_summary(sym, summary)
                if proposals:
                    await self._telegram.send_proposal_alert(sym, proposals)

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
        await self._run_eod_reports()
        await self._telegram.send_war_room("<b>🔴 DEEP CLAW OFFLINE</b>")
        log.info("Deep Claw shut down cleanly")

    # ── Operator control (Jarvis commands) ───────────────────────────────────

    def pause(self) -> None:
        self._paused = True
        log.info("Signal evaluation PAUSED by operator")

    def resume(self) -> None:
        self._paused = False
        log.info("Signal evaluation RESUMED by operator")

    @property
    def is_paused(self) -> bool:
        return self._paused

    def get_status(self) -> dict:
        elapsed = (datetime.now(timezone.utc) - self._startup_time).total_seconds()
        h, rem = divmod(int(elapsed), 3600)
        m = rem // 60
        return {
            "symbols": self._symbols,
            "paused": self._paused,
            "uptime": f"{h}h {m}m",
            "bars_processed": self._bars_processed,
            "open_positions": sum(
                1 for ctx in self._contexts.values()
                if ctx.position_machine and getattr(ctx.position_machine, "_state", None) is not None
            ),
        }

    def get_open_positions(self) -> list[dict]:
        result = []
        for sym, ctx in self._contexts.items():
            psm = ctx.position_machine
            if psm is None:
                continue
            state = getattr(psm, "_state", None)
            if state is None:
                continue
            direction = getattr(state, "direction", "?")
            result.append({
                "symbol": sym,
                "direction": direction.value if hasattr(direction, "value") else str(direction),
                "entry": float(getattr(state, "entry", 0)),
                "sl": float(getattr(state, "sl", 0)),
                "tp1": float(getattr(state, "tp1", 0)),
                "size_usd": float(getattr(state, "size_usd_risk", 0)),
                "trade_id": getattr(state, "trade_id", "?"),
            })
        return result

    def get_last_reasoning_for(self, symbol: str) -> str:
        recent = self._stream.recent(symbol, n=30)
        for ep in reversed(recent):
            if ep.episode_type in {EpisodeType.SIGNAL_ACCEPTED, EpisodeType.SIGNAL_REJECTED}:
                reasoning = (
                    ep.payload.get("claude_reasoning")
                    or ep.payload.get("causal_trace")
                    or ep.payload.get("episodic_note")
                    or ""
                )
                if reasoning:
                    ts = ep.timestamp.strftime("%H:%M UTC")
                    return f"[{ep.episode_type.value} @ {ts}]\n{reasoning}"
        return ""

    def get_last_reasoning(self) -> str:
        for sym in self._symbols:
            r = self.get_last_reasoning_for(sym)
            if r:
                return f"[{sym}] {r}"
        return ""

    def get_dashboard_state(self) -> dict:
        sys_state = self.get_status()
        symbols = {}
        for sym, ctx in self._contexts.items():
            ms = ctx.last_market_state
            cv = ctx.last_chain_verdict
            cr = ctx.last_confidence_result

            market_dict = {}
            if ms:
                try:
                    market_dict = {
                        "close": float(getattr(ms, "close", 0) or 0),
                        "session": getattr(ms.session, "value", str(ms.session)) if hasattr(ms, "session") else "?",
                        "atr_regime": getattr(ms.atr_regime, "value", str(ms.atr_regime)) if hasattr(ms, "atr_regime") else "?",
                        "trend": getattr(ms.trend_fib, "value", str(ms.trend_fib)) if hasattr(ms, "trend_fib") else "?",
                        "atr_val": float(getattr(ms, "atr_exec", 0) or 0),
                        "ts": ms.timestamp.strftime("%H:%M UTC") if hasattr(ms, "timestamp") else "",
                    }
                except Exception:
                    pass

            chain_dict = {}
            if cv:
                try:
                    chain_dict = {
                        "verdict": getattr(cv.verdict, "value", str(cv.verdict)),
                        "causal_trace": str(getattr(cv, "causal_trace", "") or ""),
                        "sovereign": str(getattr(cv, "sovereign_bias", "?")),
                        "anchor": str(getattr(cv, "anchor_bias", "?")),
                        "filter_bias": str(getattr(cv, "filter_bias", "?")),
                        "exec_bias": str(getattr(cv, "exec_bias", "?")),
                    }
                except Exception:
                    pass

            conf_dict = {}
            if cr:
                try:
                    conf_dict = {
                        "bull": float(getattr(cr, "bull_confidence", 0)),
                        "bear": float(getattr(cr, "bear_confidence", 0)),
                        "components": {k: float(v) for k, v in (getattr(cr, "component_scores", {}) or {}).items()},
                    }
                except Exception:
                    pass

            episodes = []
            try:
                for ep in self._stream.recent(sym, n=20):
                    episodes.append({
                        "type": ep.episode_type.value,
                        "ts": ep.timestamp.strftime("%H:%M"),
                        "summary": str(list(ep.payload.values())[0])[:60] if ep.payload else "",
                    })
            except Exception:
                pass

            position = next((p for p in self.get_open_positions() if p["symbol"] == sym), None)
            stats = ctx.pip_tracker.get_stats() if hasattr(ctx.pip_tracker, "get_stats") else {}

            symbols[sym] = {
                "market": market_dict,
                "chain": chain_dict,
                "confidence": conf_dict,
                "position": position,
                "reasoning": self.get_last_reasoning_for(sym),
                "episodes": episodes,
                "stats": stats,
            }

        return {
            "system": sys_state,
            "symbols": symbols,
            "exec_tf": settings.exec_tf.value,
        }

    def get_today_summary(self) -> str:
        lines = []
        for sym, ctx in self._contexts.items():
            try:
                summary = self._renderer.to_daily_summary(sym, ctx.session_start)
                lines.append(f"<b>{sym}</b>\n{summary}")
            except Exception:
                lines.append(f"<b>{sym}</b>\nNo data yet.")
        return "\n\n".join(lines) if lines else "No data yet."

    def get_risk_exposure(self) -> dict:
        daily_trades = signals_fired = signals_blocked = 0
        for ctx in self._contexts.values():
            pt = ctx.pip_tracker
            stats = pt.get_stats() if hasattr(pt, "get_stats") else {}
            daily_trades += stats.get("total_trades", 0)
            signals_fired += stats.get("signals_fired", 0)
            signals_blocked += stats.get("signals_blocked", 0)
        return {
            "daily_trades": daily_trades,
            "signals_fired": signals_fired,
            "signals_blocked": signals_blocked,
        }

    # ── Dashboard accessors ───────────────────────────────────────────────────

    @property
    def stream(self) -> EpisodeStream:
        return self._stream

    @property
    def renderer(self) -> EpisodeStreamRenderer:
        return self._renderer

    @property
    def pip_trackers(self) -> dict[str, PipTracker]:
        return {s: ctx.pip_tracker for s, ctx in self._contexts.items()}

    @property
    def daily_report(self) -> DailyReport:
        return self._daily_report


# ── Pure helpers ──────────────────────────────────────────────────────────────

def _run_signal_generators(market_state: MarketState) -> list[SignalCandidate]:
    """All 4 generators are pure functions. Zero shared state between them."""
    results = []
    for gen in [ut_bot_signal, smart_rsi_signal, liquidity_zone_signal, structure_shift_signal]:
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
    from dataclasses import replace
    new_sl = instruction.sl * verdict.sl_modifier if instruction.sl and verdict.sl_modifier != 1.0 else instruction.sl
    return replace(
        instruction,
        size_usd_risk=instruction.size_usd_risk * verdict.size_modifier,
        sl=new_sl,
    )


def _ml_confidence(market_state: MarketState):
    try:
        from deep_claw.learning.inference import predict_confidence
        return predict_confidence(market_state)
    except ImportError:
        return confidence(market_state, DEFAULT_WEIGHT_MATRIX)


def _seconds_until_hour(now: datetime, target_hour: int) -> float:
    if now.hour < target_hour:
        delta = (target_hour - now.hour) * 3600 - now.minute * 60 - now.second
    else:
        delta = (24 - now.hour + target_hour) * 3600 - now.minute * 60 - now.second
    return max(60.0, float(delta))
