"""
Structure Shift Signal Generator — BOS/CHoCH-based entry.
Pure function. Fires on confirmed structural bias change with trail alignment.
"""
from __future__ import annotations

from deep_claw.core.types import Direction, MarketState, SignalCandidate, SignalSource
from deep_claw.cognition.risk.r_multiple_planner import compute_sl, compute_tp_levels
from deep_claw.config.settings import settings


def structure_shift_signal(market_state: MarketState) -> SignalCandidate | None:
    """
    Fires on a CHoCH (higher conviction than BOS) when trail and VWAP align.
    BOS-only signals are lower conviction and not taken here — they feed the
    chain narrative as context, not entry signals.

    Bull: CHoCH bullish + exec trail bullish + close above VWAP
    Bear: CHoCH bearish + exec trail bearish + close below VWAP
    """
    ms = market_state

    bull = (
        ms.smc.latest_choch_direction == 1
        and ms.trail_exec.trend == 1
        and ms.last_swing == 1
    )
    bear = (
        ms.smc.latest_choch_direction == -1
        and ms.trail_exec.trend == -1
        and ms.last_swing == -1
    )

    if bull:
        direction = Direction.LONG
    elif bear:
        direction = Direction.SHORT
    else:
        return None

    # Don't fire if ATR is too low — structure breaks in compression are unreliable
    if ms.atr_regime.value == "LOW":
        return None

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
        "choch_direction": float(ms.smc.latest_choch_direction),
        "trail_exec": float(ms.trail_exec.trend),
        "vwap_swing": float(ms.last_swing),
        "smc_bias_after_choch": float(ms.smc.swing_bias),
        "trend_fib": float(ms.trend_fib),
        "rsi_regime": float(ms.rsi_regime_positive if direction == Direction.LONG else ms.rsi_regime_negative),
        "atr_regime": 1.0 if ms.atr_regime.value == "HIGH" else 0.5,
        "fvg_active": float(
            ms.smc.fvg_bull_active if direction == Direction.LONG else ms.smc.fvg_bear_active
        ),
    }

    return SignalCandidate(
        source=SignalSource.STRUCTURE_SHIFT,
        direction=direction,
        symbol=ms.symbol,
        timestamp=ms.timestamp,
        proposed_sl=proposed_sl,
        proposed_tp1=tp1,
        proposed_tp2=tp2,
        proposed_tp3=tp3,
        confidence_inputs=confidence_inputs,
    )
