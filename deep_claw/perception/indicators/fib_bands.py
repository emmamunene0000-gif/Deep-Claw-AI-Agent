"""
Fibonacci Bands — double-EMA basis with ATR-scaled bands.
Ported from cheatsheet §2.9.
Pure function.
"""
from __future__ import annotations

import math
from typing import Sequence


def _ema(values: Sequence[float], period: int) -> list[float]:
    """Full EMA series."""
    if not values:
        return []
    k = 2.0 / (period + 1)
    result = [values[0]]
    for v in values[1:]:
        result.append(v * k + result[-1] * (1 - k))
    return result


def _atr_series(
    highs: Sequence[float], lows: Sequence[float], closes: Sequence[float], period: int
) -> list[float]:
    trs = [highs[0] - lows[0]]
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)
    # Wilder smoothing
    atr = [sum(trs[:period]) / period] if len(trs) >= period else [trs[0]]
    for tr in trs[period:]:
        atr.append((atr[-1] * (period - 1) + tr) / period)
    return atr


def compute_fib_bands(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    fib_len: int = 21,
    atr_len: int = 14,
    use_atr: bool = True,
) -> tuple[int, float, float]:
    """
    Returns (trend_fib: int, upper_band: float, lower_band: float).
    trend_fib = 1 if basis rising, -1 if falling, 0 if flat.

    basis = EMA(EMA(hlc3, fib_len), fib_len) — double smoothed.
    Bands at 0.618 * ATR and 2.618 * ATR from basis (active-trend side only).
    """
    if len(closes) < fib_len * 2 + atr_len:
        mid = closes[-1] if closes else 0.0
        return 0, mid, mid

    hlc3 = [(highs[i] + lows[i] + closes[i]) / 3 for i in range(len(closes))]

    ema1 = _ema(hlc3, fib_len)
    basis_series = _ema(ema1, fib_len)
    basis = basis_series[-1]
    basis_prev = basis_series[-2] if len(basis_series) > 1 else basis

    if basis > basis_prev:
        trend_fib = 1
    elif basis < basis_prev:
        trend_fib = -1
    else:
        trend_fib = 0

    if use_atr:
        atr_series = _atr_series(list(highs), list(lows), list(closes), atr_len)
        band_unit = atr_series[-1] if atr_series else 0.0
    else:
        # stdev fallback
        recent = [h - l for h, l in zip(list(highs)[-fib_len:], list(lows)[-fib_len:])]
        band_unit = (sum(r**2 for r in recent) / len(recent)) ** 0.5 if recent else 0.0

    upper_band = basis + 2.618 * band_unit
    lower_band = basis - 2.618 * band_unit

    return trend_fib, upper_band, lower_band
