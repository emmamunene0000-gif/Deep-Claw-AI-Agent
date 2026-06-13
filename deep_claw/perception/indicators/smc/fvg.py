"""
Fair Value Gap (FVG) detection.
A bullish FVG: candle[i-2].high < candle[i].low (gap between candle i-2 and i).
A bearish FVG: candle[i-2].low > candle[i].high.
Ported from ADSA v7 §19.
"""
from __future__ import annotations

from typing import Sequence


def detect_fvg(
    highs: Sequence[float],
    lows: Sequence[float],
) -> tuple[bool, bool]:
    """
    Returns (bull_fvg_active, bear_fvg_active).
    Checks the most recent 3-bar pattern.
    """
    if len(highs) < 3:
        return False, False

    # Most recent completed 3-bar sequence: [-3], [-2], [-1]
    h = list(highs)
    l = list(lows)

    # Bullish FVG: high of bar -3 < low of bar -1
    bull_fvg = h[-3] < l[-1]
    # Bearish FVG: low of bar -3 > high of bar -1
    bear_fvg = l[-3] > h[-1]

    return bull_fvg, bear_fvg
