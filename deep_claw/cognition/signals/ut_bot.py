"""
UT Bot Signal Generator — ATR trailing-stop trail-flip.
Ported from ATM Protocol §5 / ADSA v7 §4.

PURE FUNCTION. No shared state. No knowledge of other signal generators.
No knowledge of whether a trade is open. Returns SignalCandidate | None.
The function signature is the structural enforcement of the v8 fix.
"""
from __future__ import annotations

from datetime import datetime

from deep_claw.core.types import Direction, MarketState, SignalCandidate, SignalSource
from deep_claw.cognition.risk.r_multiple_planner import compute_sl, compute_tp_levels
from deep_claw.cognition.risk.notional_router import get_instrument
from deep_claw.config.settings import settings


def ut_bot_signal(market_state: MarketState) -> SignalCandidate | None:
    """
    Detects a UT Bot trail-flip (bullish or bearish) from the current MarketState.
    Returns a SignalCandidate if a flip is detected, None otherwise.

    Trail-flip = exec trail changed direction from last bar. We detect this by
    checking if trail_exec.trend flipped AND close confirms the new direction.

    Additional gates (if enabled in settings):
      - Regime filter: RSI regime must not oppose the signal
      - VWAP gate: last_swing must align with direction
      - Trail gate: M15 trail must align with exec trail direction
    """
    ms = market_state
    trail = ms.trail_exec

    # Trail must be active (non-zero trend)
    if trail.trend == 0:
        return None

    direction = Direction.LONG if trail.trend == 1 else Direction.SHORT

    # Core signal: close crossed the trail value
    if direction == Direction.LONG and ms.close <= trail.trail_value:
        return None
    if direction == Direction.SHORT and ms.close >= trail.trail_value:
        return None

    # Regime filter gate
    if settings.regime_filter_enabled:
        if direction == Direction.LONG and ms.rsi_regime_negative:
            return None
        if direction == Direction.SHORT and ms.rsi_regime_positive:
            return None

    # VWAP gate
    if settings.require_vwap:
        if direction == Direction.LONG and ms.last_swing != 1:
            return None
        if direction == Direction.SHORT and ms.last_swing != -1:
            return None

    # M15 trail gate (higher-TF confirmation)
    if settings.use_trail_gate:
        if direction == Direction.LONG and ms.trail_m15.trend != 1:
            return None
        if direction == Direction.SHORT and ms.trail_m15.trend != -1:
            return None

    # Compute proposed SL and TPs
    proposed_sl = compute_sl(
        entry=ms.close,
        direction=direction,
        atr=ms.atr,
        swing_level=ms.smc.last_swing_low if direction == Direction.LONG else ms.smc.last_swing_high
            if hasattr(ms.smc, 'last_swing_low') else None,
        ema21=ms.ema_grid.get(ms.timeframe.value, None) and ms.ema_grid[ms.timeframe.value].ema21,
        sl_buffer_mult=settings.sl_buffer_atr_mult,
    )
    tp1, tp2, tp3 = compute_tp_levels(
        entry=ms.close,
        sl=proposed_sl,
        direction=direction,
        r_multiples=settings.tp_r_multiples,
    )

    confidence_inputs = {
        "trail_trend": float(trail.trend),
        "rsi_regime_positive": float(ms.rsi_regime_positive),
        "rsi_regime_negative": float(ms.rsi_regime_negative),
        "vwap_swing": float(ms.last_swing),
        "trend_fib": float(ms.trend_fib),
        "vp_strength": 1.0 if (
            (direction == Direction.LONG and ms.vp_strength.value != "BELOW VAL") or
            (direction == Direction.SHORT and ms.vp_strength.value != "ABOVE VAH")
        ) else 0.0,
        "smc_bias": float(ms.smc.swing_bias),
        "atr_regime": 1.0 if ms.atr_regime.value == "HIGH" else (0.5 if ms.atr_regime.value == "MED" else 0.0),
        "trail_m15_align": float(ms.trail_m15.trend == trail.trend),
    }

    return SignalCandidate(
        source=SignalSource.UT_BOT,
        direction=direction,
        symbol=ms.symbol,
        timestamp=ms.timestamp,
        proposed_sl=proposed_sl,
        proposed_tp1=tp1,
        proposed_tp2=tp2,
        proposed_tp3=tp3,
        confidence_inputs=confidence_inputs,
    )
