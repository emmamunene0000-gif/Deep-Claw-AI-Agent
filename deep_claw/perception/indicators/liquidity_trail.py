"""
Claw Liquidity Trail — MTF ATR-based ratcheting trailing stop.
Ported from ATM Protocol §3 / ADSA v8 calcLiqTrail.
Pure function: no shared state, no side effects.

Computes for exec/M5/M15/H1 timeframes; the MarketStateBuilder calls this
once per TF per confirmed bar.
"""
from __future__ import annotations

import math
from typing import Sequence


def _ema(values: Sequence[float], period: int) -> float:
    """Exponential moving average of the last `period` values."""
    if len(values) < 1:
        return 0.0
    k = 2.0 / (period + 1)
    result = values[0]
    for v in values[1:]:
        result = v * k + result * (1 - k)
    return result


def _atr(highs: Sequence[float], lows: Sequence[float], closes: Sequence[float], period: int) -> float:
    """Average True Range over `period` bars."""
    if len(closes) < 2:
        return 0.0
    trs: list[float] = []
    for i in range(1, min(len(closes), period + 1)):
        tr = max(
            highs[-i] - lows[-i],
            abs(highs[-i] - closes[-(i + 1)]),
            abs(lows[-i] - closes[-(i + 1)]),
        )
        trs.append(tr)
    return sum(trs) / len(trs) if trs else 0.0


def _sma(values: Sequence[float], period: int) -> float:
    window = list(values)[-period:]
    return sum(window) / len(window) if window else 0.0


def compute_liquidity_trail(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    ma_len: int = 200,
    atr_len: int = 14,
    atr_mult: float = 1.25,
) -> tuple[int, float]:
    """
    Ratcheting ATR-based trailing stop.
    Returns (trend: int, trail_value: float).
    trend = 1 (bullish), -1 (bearish).

    The trail ratchets in the direction of the trend and never moves against it.
    Matches Pine's `calcLiqTrail` logic from ATM Protocol §3.
    """
    if len(closes) < max(ma_len, atr_len) + 2:
        return 0, closes[-1] if closes else 0.0

    current_atr = _atr(list(highs), list(lows), list(closes), atr_len)
    band = atr_mult * current_atr

    closes_list = list(closes)
    highs_list = list(highs)
    lows_list = list(lows)

    # Compute trail ratchet state from scratch over the available history.
    # We need to replay to get the current state since Python doesn't have
    # Pine's implicit bar-state. We replay the last ma_len*2 bars.
    replay_start = max(atr_len + 1, 0)

    trail = closes_list[replay_start]
    trend = 1

    for i in range(replay_start, len(closes_list)):
        window_h = highs_list[max(0, i - atr_len + 1): i + 1]
        window_l = lows_list[max(0, i - atr_len + 1): i + 1]
        window_c = closes_list[max(0, i - atr_len): i + 1]
        if len(window_c) < 2:
            continue

        local_atr = _atr(window_h, window_l, window_c, atr_len)
        local_band = atr_mult * local_atr

        close = closes_list[i]

        if trend == 1:
            new_trail = max(trail, close - local_band)
            if close < new_trail:
                trend = -1
                trail = close + local_band
            else:
                trail = new_trail
        else:
            new_trail = min(trail, close + local_band)
            if close > new_trail:
                trend = 1
                trail = close - local_band
            else:
                trail = new_trail

    return trend, trail
