"""
Order Blocks — last unmitigated bullish/bearish candle before a BOS/CHoCH.
Ported from ADSA v7 §18.

An order block is the last down-candle before a bullish BOS, or
the last up-candle before a bearish BOS. It's "mitigated" when price
trades back through it.
"""
from __future__ import annotations

from typing import Sequence


def find_order_blocks(
    opens: Sequence[float],
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    bos_bull_idx: int | None,
    bos_bear_idx: int | None,
    ob_size: int = 5,
) -> tuple[float | None, float | None]:
    """
    Returns (bullish_ob_level, bearish_ob_level).
    bull_ob = top of last down-candle before most recent bullish BOS.
    bear_ob = bottom of last up-candle before most recent bearish BOS.

    Returns None if no relevant OB found or if price has already mitigated it.
    """
    current_close = closes[-1] if closes else 0.0

    bull_ob: float | None = None
    bear_ob: float | None = None

    if bos_bull_idx is not None and bos_bull_idx > ob_size:
        # Find last bearish (down) candle in the ob_size bars before the BOS
        for i in range(bos_bull_idx - 1, max(0, bos_bull_idx - ob_size - 1), -1):
            if i < len(closes) and closes[i] < opens[i]:  # down candle
                ob_top = highs[i]
                # Mitigated if price has since traded into the OB body
                if current_close < ob_top:
                    bull_ob = ob_top
                break

    if bos_bear_idx is not None and bos_bear_idx > ob_size:
        for i in range(bos_bear_idx - 1, max(0, bos_bear_idx - ob_size - 1), -1):
            if i < len(closes) and closes[i] > opens[i]:  # up candle
                ob_btm = lows[i]
                if current_close > ob_btm:
                    bear_ob = ob_btm
                break

    return bull_ob, bear_ob
