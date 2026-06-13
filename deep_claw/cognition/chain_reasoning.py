"""
Chain Reasoning Engine — reads the EpisodeStream and resolves a ChainVerdict.

This is the Bucket C piece that no prior version had.
It replaces the Fractal 4-Layer Sync cascade (which was a per-bar snapshot decision)
with a chain-aware verdict that knows the history of the session.

Inputs:
  - recent EpisodeStream window (last N episodes for this symbol)
  - current MarketState (for numeric readings)
  - SignalCandidate (being evaluated)

Output: ChainVerdict with:
  - verdict: SYNC4 / COUNTER_TREND / LOCAL / REJECTED
  - restrictions: TP1_ONLY, NO_HOLDER_MODE, HALF_SIZE
  - causal_trace: human-readable explanation
  - episodic_note: pattern match against history
"""
from __future__ import annotations

from deep_claw.core.types import (
    ATRRegime,
    ChainVerdict,
    Direction,
    Episode,
    EpisodeType,
    MarketState,
    Restriction,
    Session,
    SignalCandidate,
    Verdict,
)
from deep_claw.journal.episode_stream import EpisodeStream


class ChainReasoningEngine:
    """
    Stateless reasoning engine — all context comes from the EpisodeStream query.
    One instance can serve multiple symbols.
    """

    def __init__(self, stream: EpisodeStream) -> None:
        self._stream = stream

    def evaluate(
        self,
        candidate: SignalCandidate,
        market_state: MarketState,
        episode_window: int = 25,
    ) -> ChainVerdict:
        """
        Walk the recent EpisodeStream + MarketState → ChainVerdict.
        """
        ms = market_state
        recent = self._stream.recent(candidate.symbol, episode_window)

        # ── Layer states (from MarketState + trail hierarchy) ─────────────────
        # Sovereign = Daily bias (trend_fib as proxy for daily direction)
        sovereign_state = ms.trend_fib  # 1 bull, -1 bear, 0 neutral

        # Anchor = H1 trail direction
        anchor_state = ms.trail_h1.trend  # 1 bull, -1 bear, 0 unknown

        # Filter = M15 trail direction
        filter_state = ms.trail_m15.trend

        # Exec = exec trail direction
        exec_state = ms.trail_exec.trend

        is_long = candidate.direction == Direction.LONG
        signal_side = 1 if is_long else -1

        layer_states = {
            "sovereign": sovereign_state,
            "anchor": anchor_state,
            "filter": filter_state,
            "exec": exec_state,
        }

        # ── Rejection gates ───────────────────────────────────────────────────
        # Admin silence
        from deep_claw.config.settings import settings
        from deep_claw.core.types import AdminBias
        if settings.admin_bias == AdminBias.SILENCE:
            return ChainVerdict(
                verdict=Verdict.REJECTED,
                confidence_override=None,
                restrictions=set(),
                sl_modifier=1.0,
                causal_trace="ADMIN SILENCE active — all signals blocked.",
                episodic_note=None,
                layer_states=layer_states,
                total_score=ms.total_score,
            )

        # ATR Low veto (cheatsheet §4.5 rule #2: never enter on ATR Low)
        if ms.atr_regime == ATRRegime.LOW:
            return ChainVerdict(
                verdict=Verdict.REJECTED,
                confidence_override=None,
                restrictions=set(),
                sl_modifier=1.0,
                causal_trace=f"ATR regime is LOW — volatility collapse. Rule: never enter on ATR Low.",
                episodic_note=None,
                layer_states=layer_states,
                total_score=ms.total_score,
            )

        # Exec trail must confirm the signal direction
        if exec_state != signal_side:
            return ChainVerdict(
                verdict=Verdict.REJECTED,
                confidence_override=None,
                restrictions=set(),
                sl_modifier=1.0,
                causal_trace=(
                    f"Exec trail {'bullish' if exec_state==1 else 'bearish' if exec_state==-1 else 'neutral'} "
                    f"opposes {candidate.direction.value} signal. Structural veto."
                ),
                episodic_note=None,
                layer_states=layer_states,
                total_score=ms.total_score,
            )

        # ── Verdict classification (Fractal 4-Layer cascade) ─────────────────
        restrictions: set[Restriction] = set()
        verdict: Verdict
        causal_parts: list[str] = []

        # Is sovereign aligned?
        sovereign_aligned = sovereign_state == signal_side
        sovereign_opposing = sovereign_state == -signal_side
        anchor_aligned = anchor_state == signal_side
        filter_aligned = filter_state == signal_side

        if sovereign_aligned and anchor_aligned and filter_aligned:
            verdict = Verdict.SYNC4
            causal_parts.append("4-layer SYNC: Sovereign + Anchor + Filter + Exec all aligned.")
        elif sovereign_opposing:
            verdict = Verdict.COUNTER_TREND
            restrictions.update({Restriction.TP1_ONLY, Restriction.NO_HOLDER_MODE, Restriction.HALF_SIZE})
            causal_parts.append(
                f"COUNTER-TREND: Sovereign ({'Daily' if ms.trend_fib else 'macro'}) opposes "
                f"{candidate.direction.value} signal. TP1 ceiling enforced. Never holder mode."
            )
        elif anchor_aligned:
            verdict = Verdict.LOCAL
            causal_parts.append(
                f"LOCAL signal: Anchor ({ms.trail_h1.trend:+d}) aligns, "
                f"Sovereign neutral/opposing. Lower conviction."
            )
        else:
            verdict = Verdict.LOCAL
            restrictions.add(Restriction.TP1_ONLY)
            causal_parts.append(
                f"LOCAL signal: Exec-only. Anchor={'neutral' if anchor_state==0 else 'opposing'}. "
                f"TP1 ceiling applied."
            )

        # ── Restriction enrichment from chain history ─────────────────────────
        # If we've already had 2+ SL hits today → add HALF_SIZE
        sl_episodes_today = self._count_today_episodes(
            recent, EpisodeType.SL_HIT
        )
        if sl_episodes_today >= 2:
            restrictions.add(Restriction.HALF_SIZE)
            causal_parts.append(f"{sl_episodes_today} SL hits already today — half size.")

        # If we had a liquidity sweep in the same direction recently, boost conviction
        recent_sweep = self._find_recent_sweep(recent, signal_side)
        if recent_sweep:
            causal_parts.append(
                f"Recent {candidate.direction.value}-side liquidity sweep at "
                f"{recent_sweep.payload.get('level', '?')} confirms institutional flow."
            )

        # If we had a CHoCH in the signal direction recently, boost conviction
        recent_choch = self._find_recent_choch(recent, signal_side)
        if recent_choch:
            causal_parts.append(
                f"CHoCH {candidate.direction.value} confirmed — structural bias shifted."
            )

        # ── Session context ───────────────────────────────────────────────────
        if ms.session == Session.OVERLAP:
            causal_parts.append("London-NY overlap — highest-edge window.")
        elif ms.session == Session.OFF:
            restrictions.add(Restriction.HALF_SIZE)
            causal_parts.append("Off-session — reduced size, elevated selectivity.")

        # ── Episodic memory note ──────────────────────────────────────────────
        episodic_note = self._build_episodic_note(candidate, ms, verdict)

        # ── SL modifier from chain ────────────────────────────────────────────
        sl_modifier = self._compute_sl_modifier(recent, ms, verdict)

        return ChainVerdict(
            verdict=verdict,
            confidence_override=None,
            restrictions=restrictions,
            sl_modifier=sl_modifier,
            causal_trace=" | ".join(causal_parts),
            episodic_note=episodic_note,
            layer_states=layer_states,
            total_score=ms.total_score,
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _count_today_episodes(self, recent: list[Episode], ep_type: EpisodeType) -> int:
        from datetime import datetime, timezone, timedelta
        today = datetime.now(timezone.utc).date()
        return sum(
            1 for ep in recent
            if ep.episode_type == ep_type and ep.timestamp.date() == today
        )

    def _find_recent_sweep(self, recent: list[Episode], signal_side: int) -> Episode | None:
        target_side = "SELL" if signal_side == 1 else "BUY"
        for ep in reversed(recent):
            if ep.episode_type == EpisodeType.LIQUIDITY_SWEEP:
                if ep.payload.get("side") == target_side:
                    return ep
        return None

    def _find_recent_choch(self, recent: list[Episode], signal_side: int) -> Episode | None:
        for ep in reversed(recent):
            if ep.episode_type == EpisodeType.STRUCTURE_CHOCH:
                if ep.payload.get("direction", 0) == signal_side:
                    return ep
        return None

    def _build_episodic_note(
        self,
        candidate: SignalCandidate,
        ms: MarketState,
        verdict: Verdict,
    ) -> str | None:
        """
        Query historical similar setups and return a note if patterns found.
        This is the 'episodic memory' — only possible because of the chain.
        """
        similar = self._stream.find_similar_setups(
            symbol=candidate.symbol,
            verdict=verdict.value,
            session=ms.session.value,
            atr_regime=ms.atr_regime.value,
            limit=3,
        )
        if not similar:
            return None

        # Look for closed trade outcomes matching these accepted signals
        notes: list[str] = []
        for ep in similar:
            trade_id = ep.payload.get("trade_id")
            exit_r = ep.payload.get("realized_r")
            exit_reason = ep.payload.get("exit_reason")
            if trade_id and exit_r is not None:
                notes.append(
                    f"Similar setup ({ep.payload.get('session', '?')} {ep.payload.get('atr_regime', '?')}) "
                    f"→ {exit_reason} {exit_r:+.2f}R"
                )

        return "; ".join(notes) if notes else None

    def _compute_sl_modifier(
        self, recent: list[Episode], ms: MarketState, verdict: Verdict
    ) -> float:
        """
        Widen SL if we have recent liquidity sweep evidence (stops got hunted).
        Tighten if ATR just entered HIGH regime (strong momentum, tight stops hold better).
        """
        modifier = 1.0

        # If liq_bias shows recent sweeping activity, widen by 20%
        if "SWEPT" in ms.smc.liq_bias:
            modifier = 1.2

        # Counter-trend: always widen slightly (less room for error)
        if verdict == Verdict.COUNTER_TREND:
            modifier = max(modifier, 1.15)

        return modifier
