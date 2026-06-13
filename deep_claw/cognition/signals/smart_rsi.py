"""
Smart RSI Signal Generator — RSI extreme-zone reversal signals.
Ported from ADSA v8 Section 6 "Smart RSI Momentum".

PURE FUNCTION. Independent of UT Bot. Independent of trade state.
This is the exact generator that in v8 was OR'd into shared posState — never again.
"""
from __future__ import annotations

from deep_claw.core.types import Direction, MarketState, SignalCandidate, SignalSource
from deep_claw.cognition.risk.r_multiple_planner import compute_sl, compute_tp_levels
from deep_claw.config.settings import settings


# RSI levels for extreme zones (v8 defaults)
RSI_EXTREME_BULL = 25.0   # oversold — potential long
RSI_EXTREME_BEAR = 75.0   # overbought — potential short


def smart_rsi_signal(market_state: MarketState) -> SignalCandidate | None:
    """
    Fires when RSI is in an extreme zone AND exec trail confirms the reversal direction.

    Bull signal: RSI <= 25 and exec trail bullish (trail_exec.trend == 1)
    Bear signal: RSI >= 75 and exec trail bearish (trail_exec.trend == -1)

    The exec trail confirmation is the "M5-confirmed" gate from v8 §6.
    Without it, RSI extremes in a trending market trigger too early.
    """
    ms = market_state

    if ms.rsi <= RSI_EXTREME_BULL and ms.trail_exec.trend == 1:
        direction = Direction.LONG
    elif ms.rsi >= RSI_EXTREME_BEAR and ms.trail_exec.trend == -1:
        direction = Direction.SHORT
    else:
        return None

    # SMC alignment gate — don't fade a sweep that's still in progress
    if direction == Direction.LONG and "SELL-SIDE SWEPT" in ms.smc.liq_bias:
        return None  # selling pressure sweeping lows — wait for reversal confirmation
    if direction == Direction.SHORT and "BUY-SIDE SWEPT" in ms.smc.liq_bias:
        return None

    proposed_sl = compute_sl(
        entry=ms.close,
        direction=direction,
        atr=ms.atr,
        swing_level=None,
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
        "rsi": ms.rsi,
        "rsi_extreme_bull": float(ms.rsi <= RSI_EXTREME_BULL),
        "rsi_extreme_bear": float(ms.rsi >= RSI_EXTREME_BEAR),
        "trail_confirms": float(ms.trail_exec.trend == (1 if direction == Direction.LONG else -1)),
        "vwap_swing": float(ms.last_swing),
        "trend_fib": float(ms.trend_fib),
        "smc_bias": float(ms.smc.swing_bias),
        "atr_regime": 1.0 if ms.atr_regime.value == "HIGH" else (0.5 if ms.atr_regime.value == "MED" else 0.0),
    }

    return SignalCandidate(
        source=SignalSource.SMART_RSI,
        direction=direction,
        symbol=ms.symbol,
        timestamp=ms.timestamp,
        proposed_sl=proposed_sl,
        proposed_tp1=tp1,
        proposed_tp2=tp2,
        proposed_tp3=tp3,
        confidence_inputs=confidence_inputs,
    )
