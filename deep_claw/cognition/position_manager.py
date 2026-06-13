"""
PositionStateMachine — THE single owner of trade state.

Rules:
  1. Only this class creates or mutates PositionState.
  2. Every signal candidate is explicitly accepted OR rejected with a logged reason.
  3. Rejected candidates are logged as SIGNAL_REJECTED episodes (shadow-blocked data).
     They are NEVER silently dropped and NEVER corrupt the open trade's labels.
  4. Reversal = close existing (log P&L) + open new. No orphan trades. No dead zones.
  5. SL labels are only written by this class's price-check logic. Never by a signal firing.

This is the structural fix for v8's root cause:
  v8: UT Bot OR Smart RSI → shared posState → orphan trades → corrupted ML labels.
  Here: N generators → List[SignalCandidate] → THIS class → one PositionState.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from deep_claw.core.types import (
    AutopsyTag,
    ChainVerdict,
    ClosedTrade,
    ConfidenceResult,
    Direction,
    Episode,
    EpisodeType,
    ExitReason,
    MarketState,
    Phase,
    PositionHandle,
    PositionState,
    Restriction,
    SignalCandidate,
    SizingResult,
    TradeInstruction,
    Verdict,
)
from deep_claw.cognition.chain_reasoning import ChainReasoningEngine
from deep_claw.cognition.confidence_v1 import (
    DEFAULT_WEIGHT_MATRIX,
    WeightMatrix,
    confidence,
    get_directional_confidence,
)
from deep_claw.cognition.risk.notional_router import get_live_pnl
from deep_claw.cognition.risk.position_sizer import compute_size
from deep_claw.cognition.risk.r_multiple_planner import compute_sl, compute_tp_levels, realized_r
from deep_claw.journal.episode_stream import EpisodeStream
from deep_claw.config.settings import settings


TradeCallback = Callable[[TradeInstruction], PositionHandle]
ModifyCallback = Callable[[PositionHandle, float], None]
PartialCloseCallback = Callable[[PositionHandle, float], None]
CloseCallback = Callable[[PositionHandle], None]


def _generate_trade_id(symbol: str, direction: Direction, counter: int) -> str:
    now = datetime.now(timezone.utc)
    dir_str = "BUY" if direction == Direction.LONG else "SELL"
    return f"ATM-{now.strftime('%Y%m%d')}-{now.strftime('%H%M')}-{dir_str}-{counter}"


def _build_autopsy_tag(market_state: MarketState, chain_verdict: ChainVerdict) -> AutopsyTag:
    """
    Priority-ordered SL root-cause labeler (cheatsheet §4.5).
    Called at SL-hit time with the MarketState at that moment.
    """
    ms = market_state
    if "SWEPT" in ms.smc.liq_bias:
        return AutopsyTag.LIQUIDITY_TRAP
    if ms.atr_regime.value == "LOW":
        return AutopsyTag.VOLATILITY_COLLAPSE
    if chain_verdict.verdict == Verdict.COUNTER_TREND:
        return AutopsyTag.SOVEREIGN_VETO
    if abs(ms.total_score) < 4:
        return AutopsyTag.WEAK_ALIGNMENT
    return AutopsyTag.MACRO_ROTATION


class PositionStateMachine:
    """
    Single-symbol position state manager.
    Create one instance per symbol.
    """

    def __init__(
        self,
        symbol: str,
        stream: EpisodeStream,
        chain_engine: ChainReasoningEngine,
        weight_matrix: WeightMatrix = DEFAULT_WEIGHT_MATRIX,
        equity: float = 1000.0,
        on_open: TradeCallback | None = None,
        on_modify: ModifyCallback | None = None,
        on_partial_close: PartialCloseCallback | None = None,
        on_close: CloseCallback | None = None,
    ) -> None:
        self.symbol = symbol
        self._stream = stream
        self._chain = chain_engine
        self._weights = weight_matrix
        self._equity = equity

        # Broker callbacks (wired up by orchestrator)
        self._on_open = on_open
        self._on_modify = on_modify
        self._on_partial_close = on_partial_close
        self._on_close = on_close

        self._state: PositionState | None = None
        self._daily_trade_counter: int = 0
        self._daily_sl_count: int = 0

    # ── Public API ────────────────────────────────────────────────────────────

    def process_candidates(
        self,
        candidates: list[SignalCandidate],
        market_state: MarketState,
    ) -> TradeInstruction | None:
        """
        Main entry point. Called once per bar with all signal candidates.
        Returns a TradeInstruction if a new trade should be opened, else None.

        Every candidate is explicitly accepted or rejected — nothing is silent.
        """
        if not candidates:
            return None

        # Evaluate each candidate against current state
        accepted: list[tuple[SignalCandidate, ChainVerdict, ConfidenceResult]] = []

        for candidate in candidates:
            verdict = self._chain.evaluate(candidate, market_state)
            conf_result = confidence(market_state, self._weights)
            directional_conf = get_directional_confidence(conf_result, candidate.direction)

            # Gate 1: Chain structural veto
            if verdict.verdict == Verdict.REJECTED:
                self._log_rejection(candidate, market_state, "CHAIN_VETO", verdict)
                continue

            # Gate 2: Confidence threshold (structural, not cosmetic)
            if directional_conf < settings.confidence_threshold:
                self._log_rejection(
                    candidate, market_state,
                    f"CONFIDENCE_TOO_LOW:{directional_conf:.1f}<{settings.confidence_threshold}",
                    verdict,
                )
                continue

            # Gate 3: ATR regime (never enter on Low)
            if market_state.atr_regime.value == "LOW":
                self._log_rejection(candidate, market_state, "ATR_TOO_LOW", verdict)
                continue

            # Gate 4: One-trade-per-symbol rule
            if self._state is not None and settings.one_trade_per_symbol:
                # If it would be a reversal, we handle it below; otherwise reject
                if candidate.direction == self._state.direction:
                    self._log_rejection(candidate, market_state, "ONE_TRADE_RULE", verdict)
                    continue

            accepted.append((candidate, verdict, conf_result))

        if not accepted:
            return None

        # Pick the highest confidence among accepted candidates
        accepted.sort(
            key=lambda t: get_directional_confidence(t[2], t[0].direction),
            reverse=True,
        )
        best_candidate, best_verdict, best_conf = accepted[0]

        # Reject all others (they were real candidates that didn't win)
        for cand, verd, conf_r in accepted[1:]:
            self._log_rejection(
                cand, market_state, "ONE_TRADE_RULE:LOWER_CONFIDENCE", verd
            )

        # Handle reversal: close existing first
        if self._state is not None and best_candidate.direction != self._state.direction:
            self._close_trade(market_state, ExitReason.REVERSAL)

        return self._open_trade(best_candidate, best_verdict, best_conf, market_state)

    def update_price(self, market_state: MarketState) -> list[TradeInstruction]:
        """
        Called on every bar close with the latest MarketState.
        Checks TP1/TP2/TP3/Holder/SL progression and emits instructions.
        Returns list of TradeInstructions (could be empty, or contain modify/partial-close).
        """
        if self._state is None:
            return []

        ms = market_state
        state = self._state
        instructions: list[TradeInstruction] = []

        close = ms.close
        is_long = state.direction == Direction.LONG

        # Update running MFE/MAE
        if is_long:
            profit_pips = (close - state.entry) / ms.atr * 100  # normalized
            loss_pips = (state.entry - close) / ms.atr * 100
        else:
            profit_pips = (state.entry - close) / ms.atr * 100
            loss_pips = (close - state.entry) / ms.atr * 100

        if profit_pips > 0:
            state.mfe_pips = max(state.mfe_pips, profit_pips)
            state.peak_profit_pips = state.mfe_pips
        if loss_pips > 0:
            state.mae_pips = max(state.mae_pips, loss_pips)

        state.bar_count += 1

        # ── Phase progression (cheatsheet §4.4) ──────────────────────────────

        if state.phase == Phase.ENTRY:
            # SL check (only before TP1 is secured)
            sl_hit = (is_long and close <= state.sl) or (not is_long and close >= state.sl)
            if sl_hit:
                self._close_trade(ms, ExitReason.SL)
                return instructions

            # TP1
            tp1_hit = (is_long and close >= state.tp1) or (not is_long and close <= state.tp1)
            if tp1_hit:
                self._hit_tp1(ms)

        elif state.phase == Phase.TP1_HIT:
            # TP2
            tp2_hit = (is_long and close >= state.tp2) or (not is_long and close <= state.tp2)
            if tp2_hit:
                self._hit_tp2(ms)

        elif state.phase == Phase.TP2_HIT:
            # TP3
            if Restriction.TP1_ONLY not in state.restrictions:
                tp3_hit = (is_long and close >= state.tp3) or (not is_long and close <= state.tp3)
                if tp3_hit:
                    self._hit_tp3(ms)

        elif state.phase == Phase.HOLDER_MODE:
            # Exit when price crosses back through VWAP (cheatsheet §4.4)
            if Restriction.NO_HOLDER_MODE not in state.restrictions:
                holder_exit = (
                    (is_long and close < ms.vap_current) or
                    (not is_long and close > ms.vap_current)
                )
                if holder_exit:
                    self._close_trade(ms, ExitReason.HOLDER_EXIT)

        return instructions

    # ── Internal: trade lifecycle ─────────────────────────────────────────────

    def _open_trade(
        self,
        candidate: SignalCandidate,
        verdict: ChainVerdict,
        conf_result: ConfidenceResult,
        ms: MarketState,
    ) -> TradeInstruction:
        directional_conf = get_directional_confidence(conf_result, candidate.direction)

        # Apply SL modifier from chain verdict
        raw_sl_distance = abs(ms.close - candidate.proposed_sl)
        modified_sl_distance = raw_sl_distance * verdict.sl_modifier
        if candidate.direction == Direction.LONG:
            final_sl = ms.close - modified_sl_distance
        else:
            final_sl = ms.close + modified_sl_distance

        tp1, tp2, tp3 = compute_tp_levels(
            entry=ms.close,
            sl=final_sl,
            direction=candidate.direction,
            r_multiples=settings.tp_r_multiples,
        )

        # Apply HALF_SIZE restriction
        effective_risk = settings.risk_per_trade_usd
        if Restriction.HALF_SIZE in verdict.restrictions:
            effective_risk *= 0.5

        sizing = compute_size(
            symbol=candidate.symbol,
            sl_distance=modified_sl_distance,
            confidence=directional_conf,
            equity=self._equity,
            risk_per_trade_usd=effective_risk,
            max_equity_pct=settings.max_equity_risk_pct,
        )

        self._daily_trade_counter += 1
        trade_id = _generate_trade_id(
            candidate.symbol, candidate.direction, self._daily_trade_counter
        )

        from deep_claw.cognition.risk.notional_router import get_instrument
        inst = get_instrument(candidate.symbol)

        instruction = TradeInstruction(
            symbol=candidate.symbol,
            direction=candidate.direction,
            entry=ms.close,
            sl=final_sl,
            tp1=tp1,
            tp2=tp2,
            tp3=tp3,
            size_units=sizing.final_size,
            size_usd_risk=effective_risk,
            venue=inst.preferred_venue,
            trade_id=trade_id,
            chain_verdict=verdict.verdict,
            restrictions=verdict.restrictions,
        )

        self._state = PositionState(
            trade_id=trade_id,
            symbol=candidate.symbol,
            direction=candidate.direction,
            entry=ms.close,
            sl=final_sl,
            tp1=tp1,
            tp2=tp2,
            tp3=tp3,
            size_units=sizing.final_size,
            size_usd_risk=effective_risk,
            venue=inst.preferred_venue,
            phase=Phase.ENTRY,
            signal_source=candidate.source,
            chain_verdict=verdict.verdict,
            confidence_at_entry=directional_conf,
            restrictions=verdict.restrictions,
            handle=None,
            opened_at=ms.timestamp,
        )

        # Log SIGNAL_ACCEPTED episode
        ep = Episode(
            episode_type=EpisodeType.SIGNAL_ACCEPTED,
            symbol=candidate.symbol,
            timestamp=ms.timestamp,
            payload={
                "trade_id": trade_id,
                "source": candidate.source.value,
                "direction": candidate.direction.value,
                "entry": ms.close,
                "sl": final_sl,
                "tp1": tp1,
                "tp2": tp2,
                "tp3": tp3,
                "size_units": sizing.final_size,
                "verdict": verdict.verdict.value,
                "confidence": directional_conf,
                "restrictions": [r.value for r in verdict.restrictions],
                "causal_trace": verdict.causal_trace,
                "session": ms.session.value,
                "atr_regime": ms.atr_regime.value,
                "total_score": ms.total_score,
                "sizing_binding_clamp": sizing.binding_clamp,
                "sl_modifier": verdict.sl_modifier,
            },
            market_state_ref=ms.bar_id,
        )
        self._stream.append(ep)

        return instruction

    def _hit_tp1(self, ms: MarketState) -> None:
        if self._state is None:
            return
        self._state.phase = Phase.TP1_HIT
        # Move SL to breakeven after TP1 (not breakeven yet — tighten at TP2)
        ep = Episode(
            episode_type=EpisodeType.TP1_HIT,
            symbol=self._state.symbol,
            timestamp=ms.timestamp,
            payload={
                "trade_id": self._state.trade_id,
                "price": ms.close,
                "mfe_pips": self._state.mfe_pips,
            },
            market_state_ref=ms.bar_id,
        )
        self._stream.append(ep)
        if self._on_partial_close:
            # Take 25-33% off at TP1
            pass  # Action adapter handles the percentage

    def _hit_tp2(self, ms: MarketState) -> None:
        if self._state is None:
            return
        self._state.phase = Phase.TP2_HIT
        # Move SL to breakeven (entry)
        if self._state.handle and self._on_modify:
            self._on_modify(self._state.handle, self._state.entry)
        self._state.sl = self._state.entry

        ep = Episode(
            episode_type=EpisodeType.TP2_HIT,
            symbol=self._state.symbol,
            timestamp=ms.timestamp,
            payload={
                "trade_id": self._state.trade_id,
                "price": ms.close,
                "sl_moved_to_be": self._state.entry,
            },
            market_state_ref=ms.bar_id,
        )
        self._stream.append(ep)

    def _hit_tp3(self, ms: MarketState) -> None:
        if self._state is None:
            return
        if Restriction.TP1_ONLY in self._state.restrictions:
            # Counter-trend restriction: close at TP1, don't let it run
            self._close_trade(ms, ExitReason.TP1)
            return

        self._state.phase = Phase.TP3_HIT

        if Restriction.NO_HOLDER_MODE not in self._state.restrictions:
            self._state.phase = Phase.HOLDER_MODE

        ep = Episode(
            episode_type=EpisodeType.TP3_HIT,
            symbol=self._state.symbol,
            timestamp=ms.timestamp,
            payload={
                "trade_id": self._state.trade_id,
                "price": ms.close,
                "holder_mode": self._state.phase == Phase.HOLDER_MODE,
            },
            market_state_ref=ms.bar_id,
        )
        self._stream.append(ep)

    def _close_trade(self, ms: MarketState, exit_reason: ExitReason) -> None:
        """
        Close the current trade, compute full outcome, and write to EpisodeStream.
        This is the ONLY place TRADE_CLOSED and SL_HIT episodes are written.
        """
        if self._state is None:
            return

        state = self._state
        close_price = ms.close
        sl_distance = abs(state.entry - state.sl)

        r = realized_r(state.entry, close_price, state.sl, state.direction)
        mfe_r = state.mfe_pips / (sl_distance / ms.atr * 100) if sl_distance > 0 else 0.0
        mae_r = state.mae_pips / (sl_distance / ms.atr * 100) if sl_distance > 0 else 0.0

        autopsy: AutopsyTag | None = None
        if exit_reason == ExitReason.SL:
            autopsy = _build_autopsy_tag(ms, ChainVerdict(
                verdict=state.chain_verdict,
                confidence_override=None,
                restrictions=state.restrictions,
                sl_modifier=1.0,
                causal_trace="",
                episodic_note=None,
                layer_states={},
                total_score=ms.total_score,
            ))
            self._daily_sl_count += 1

        closed = ClosedTrade(
            trade_id=state.trade_id,
            symbol=state.symbol,
            direction=state.direction,
            signal_source=state.signal_source,
            chain_verdict=state.chain_verdict,
            confidence_at_entry=state.confidence_at_entry,
            restrictions=frozenset(state.restrictions),
            entry=state.entry,
            exit=close_price,
            sl_at_entry=state.sl,
            sl_distance=sl_distance,
            tp1=state.tp1,
            tp2=state.tp2,
            tp3=state.tp3,
            size_units=state.size_units,
            size_usd_risk=state.size_usd_risk,
            venue=state.venue,
            exit_reason=exit_reason,
            autopsy_tag=autopsy,
            mfe_pips=state.mfe_pips,
            mae_pips=state.mae_pips,
            mfe_r=round(mfe_r, 3),
            mae_r=round(mae_r, 3),
            realized_r=round(r, 3),
            bar_count=state.bar_count,
            opened_at=state.opened_at,
            closed_at=ms.timestamp,
            session_at_entry=ms.session,
            atr_regime_at_entry=ms.atr_regime,
            total_score_at_entry=ms.total_score,
        )

        # Write the episode — this is the ground truth for the ML label
        ep_type = EpisodeType.SL_HIT if exit_reason == ExitReason.SL else (
            EpisodeType.HOLDER_EXIT if exit_reason == ExitReason.HOLDER_EXIT else
            EpisodeType.TRADE_CLOSED
        )
        ep = Episode(
            episode_type=ep_type,
            symbol=state.symbol,
            timestamp=ms.timestamp,
            payload={
                "trade_id": state.trade_id,
                "exit_reason": exit_reason.value,
                "realized_r": round(r, 3),
                "mfe_r": round(mfe_r, 3),
                "mae_r": round(mae_r, 3),
                "mfe_pips": state.mfe_pips,
                "mae_pips": state.mae_pips,
                "bar_count": state.bar_count,
                "entry": state.entry,
                "exit": close_price,
                "sl_at_entry": state.sl,
                "signal_source": state.signal_source.value,
                "autopsy_tag": autopsy.value if autopsy else None,
                "confidence_at_entry": state.confidence_at_entry,
                "peak_pips": state.peak_profit_pips,
            },
            market_state_ref=ms.bar_id,
        )
        self._stream.append(ep)

        # Execute broker close
        if state.handle and self._on_close:
            self._on_close(state.handle)

        # Clear state AFTER logging — the log is the source of truth
        self._state = None

    def _log_rejection(
        self,
        candidate: SignalCandidate,
        ms: MarketState,
        reason: str,
        verdict: ChainVerdict | None,
    ) -> None:
        """
        Log a shadow-blocked candidate. NEVER silently drop.
        These are critical for survivorship-bias-free ML training.
        ONE_TRADE_RULE and CONFIDENCE_TOO_LOW are different features — preserve the distinction.
        """
        ep = Episode(
            episode_type=EpisodeType.SIGNAL_REJECTED,
            symbol=candidate.symbol,
            timestamp=ms.timestamp,
            payload={
                "candidate_id": candidate.candidate_id,
                "source": candidate.source.value,
                "direction": candidate.direction.value,
                "rejection_reason": reason,
                "proposed_sl": candidate.proposed_sl,
                "proposed_tp1": candidate.proposed_tp1,
                "verdict": verdict.verdict.value if verdict else None,
                "causal_trace": verdict.causal_trace if verdict else None,
                "session": ms.session.value,
                "atr_regime": ms.atr_regime.value,
                "total_score": ms.total_score,
                "trade_open": self._state is not None,
            },
            market_state_ref=ms.bar_id,
        )
        self._stream.append(ep)

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def has_open_trade(self) -> bool:
        return self._state is not None

    @property
    def state(self) -> PositionState | None:
        return self._state

    def register_handle(self, trade_id: str, handle: PositionHandle) -> None:
        """Called by Action adapter after broker order is filled."""
        if self._state and self._state.trade_id == trade_id:
            self._state.handle = handle

    def update_equity(self, equity: float) -> None:
        self._equity = equity
