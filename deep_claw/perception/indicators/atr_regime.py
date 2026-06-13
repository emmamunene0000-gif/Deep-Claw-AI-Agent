"""
ATR Regime — ATR(14) vs 20-SMA(ATR) → HIGH/MED/LOW categorical.
Pure function. Ported from ADSA v7 §20 narrative block.
"""
from __future__ import annotations

from typing import Sequence

from deep_claw.core.types import ATRRegime


def compute_atr(
    highs: Sequence[float], lows: Sequence[float], closes: Sequence[float], period: int = 14
) -> float:
    """Wilder ATR."""
    if len(closes) < period + 1:
        return (highs[-1] - lows[-1]) if highs and lows else 0.0

    trs: list[float] = [highs[0] - lows[0]]
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)

    avg = sum(trs[:period]) / period
    for tr in trs[period:]:
        avg = (avg * (period - 1) + tr) / period
    return avg


def compute_atr_regime(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    atr_period: int = 14,
    sma_period: int = 20,
) -> tuple[float, ATRRegime]:
    """
    Returns (current_atr, regime).
    HIGH: ATR > 1.2 * SMA(ATR, 20)
    LOW:  ATR < 0.8 * SMA(ATR, 20)
    MED:  otherwise
    """
    if len(closes) < atr_period + sma_period:
        current_atr = compute_atr(highs, lows, closes, atr_period)
        return current_atr, ATRRegime.MED

    # Build ATR series
    atr_vals: list[float] = []
    for i in range(atr_period, len(closes) + 1):
        h = list(highs[:i])
        l = list(lows[:i])
        c = list(closes[:i])
        atr_vals.append(compute_atr(h, l, c, atr_period))

    current_atr = atr_vals[-1]

    sma_window = atr_vals[-sma_period:]
    sma_atr = sum(sma_window) / len(sma_window)

    if current_atr > 1.2 * sma_atr:
        regime = ATRRegime.HIGH
    elif current_atr < 0.8 * sma_atr:
        regime = ATRRegime.LOW
    else:
        regime = ATRRegime.MED

    return current_atr, regime
