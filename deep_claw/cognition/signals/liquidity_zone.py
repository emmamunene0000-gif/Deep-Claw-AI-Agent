"""
Liquidity Zone Signal Generator — break/retest of pivot-based S/D zones.
Ported from ATM Protocol §4 / cheatsheet section 1.19.

PURE FUNCTION. Fires on confirmed break or retest of a liquidity zone,
with exec trail alignment as confirmation.
"""
from __future__ import annotations

from deep_claw.core.types import Direction, MarketState, SignalCandidate, SignalSource
from deep_claw.cognition.risk.r_multiple_planner import compute_sl, compute_tp_levels
from deep_claw.config.settings import settings


def liquidity_zone_signal(market_state: MarketState) -> SignalCandidate | None:
    """
    Fires on:
    - Bullish: price swept sell-side (pl_btm) and exec trail is now bullish (reversal long)
    - Bearish: price swept buy-side (ph_top) and exec trail is now bearish (reversal short)

    This is the "liquidity sweep + reversal" setup:
    institutions sweep stops below support, then reverse upward.
    """
    ms = market_state

    bull_signal = (
        "SELL-SIDE SWEPT" in ms.smc.liq_bias
        and ms.trail_exec.trend == 1
        and ms.close > ms.smc.pl_btm
    )
    bear_signal = (
        "BUY-SIDE SWEPT" in ms.smc.liq_bias
        and ms.trail_exec.trend == -1
        and ms.close < ms.smc.ph_top
    )

    if bull_signal:
        direction = Direction.LONG
    elif bear_signal:
        direction = Direction.SHORT
    else:
        return None

    # Require CHoCH confirmation for strongest setups
    if direction == Direction.LONG and ms.smc.latest_choch_direction != 1:
        return None
    if direction == Direction.SHORT and ms.smc.latest_choch_direction != -1:
        return None

    proposed_sl = compute_sl(
        entry=ms.close,
        direction=direction,
        atr=ms.atr,
        swing_level=ms.smc.pl_btm if direction == Direction.LONG else ms.smc.ph_top,
        ema21=None,
        sl_buffer_mult=settings.sl_buffer_atr_mult,
    )
    tp1, tp2, tp3 = compute_tp_levels(
        entry=ms.close,
        sl=proposed_sl,
        direction=direction,
        r_multiples=settings.tp_r_multiples,
    )

    confidence_inputs = {
        "liq_sweep_bull": float("SELL-SIDE SWEPT" in ms.smc.liq_bias),
        "liq_sweep_bear": float("BUY-SIDE SWEPT" in ms.smc.liq_bias),
        "trail_confirms": float(ms.trail_exec.trend == (1 if direction == Direction.LONG else -1)),
        "choch_confirms": float(
            (direction == Direction.LONG and ms.smc.latest_choch_direction == 1) or
            (direction == Direction.SHORT and ms.smc.latest_choch_direction == -1)
        ),
        "vwap_swing": float(ms.last_swing),
        "smc_bias": float(ms.smc.swing_bias),
        "rsi_regime": float(ms.rsi_regime_positive if direction == Direction.LONG else ms.rsi_regime_negative),
    }

    return SignalCandidate(
        source=SignalSource.LIQUIDITY_ZONE,
        direction=direction,
        symbol=ms.symbol,
        timestamp=ms.timestamp,
        proposed_sl=proposed_sl,
        proposed_tp1=tp1,
        proposed_tp2=tp2,
        proposed_tp3=tp3,
        confidence_inputs=confidence_inputs,
    )
