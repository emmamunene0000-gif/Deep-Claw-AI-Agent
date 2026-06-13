"""
Liquidity Zones — pivot-based supply/demand boxes and sweep detection.
Ported from ATM Protocol §4 / ADSA v7 §19.

ph_top = highest unmitigated pivot high (buy-side liquidity pool).
pl_btm = lowest unmitigated pivot low (sell-side liquidity pool).
Sweep = price temporarily exceeds the level then reverses within the bar.
"""
from __future__ import annotations

from typing import Sequence


def compute_liquidity_levels(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    pivot_len: int = 14,
) -> tuple[float, float, str]:
    """
    Returns (ph_top, pl_btm, liq_bias).

    liq_bias:
      "BUY-SIDE SWEPT"  — this bar swept ph_top then closed below it
      "SELL-SIDE SWEPT" — this bar swept pl_btm then closed above it
      "BUY-SIDE WATCH"  — close approaching ph_top from below
      "SELL-SIDE WATCH" — close approaching pl_btm from above
      "NEUTRAL"         — no notable liquidity context
    """
    if len(closes) < pivot_len + 1:
        mid = closes[-1] if closes else 0.0
        return mid, mid, "NEUTRAL"

    # Find pivot highs/lows in the lookback window
    window_h = list(highs)[-(pivot_len * 2):]
    window_l = list(lows)[-(pivot_len * 2):]

    ph_top = max(window_h) if window_h else highs[-1]
    pl_btm = min(window_l) if window_l else lows[-1]

    current_high = highs[-1]
    current_low = lows[-1]
    current_close = closes[-1]

    # Sweep detection: wick beyond level but close on the other side
    buy_side_swept = current_high > ph_top and current_close < ph_top
    sell_side_swept = current_low < pl_btm and current_close > pl_btm

    approach_threshold = (ph_top - pl_btm) * 0.05  # within 5% of the range

    if buy_side_swept:
        liq_bias = "BUY-SIDE SWEPT"
    elif sell_side_swept:
        liq_bias = "SELL-SIDE SWEPT"
    elif current_close > ph_top - approach_threshold:
        liq_bias = "BUY-SIDE WATCH"
    elif current_close < pl_btm + approach_threshold:
        liq_bias = "SELL-SIDE WATCH"
    else:
        liq_bias = "NEUTRAL"

    return ph_top, pl_btm, liq_bias
