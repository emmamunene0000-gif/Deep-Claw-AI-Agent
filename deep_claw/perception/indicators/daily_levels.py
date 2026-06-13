"""
PDH/PDL — prior day high and low.
No lookahead: uses yesterday's confirmed daily candle only.
Pure function operating on a series of daily OHLCV data.
"""
from __future__ import annotations

from typing import Sequence

from deep_claw.core.types import PDHPDLStatus


def compute_pdh_pdl(
    daily_highs: Sequence[float],
    daily_lows: Sequence[float],
    current_close: float,
) -> tuple[float, float, PDHPDLStatus]:
    """
    Returns (PDH, PDL, status).
    Requires at least 2 daily bars (index -2 = yesterday's confirmed bar).
    """
    if len(daily_highs) < 2:
        fallback = current_close
        return fallback, fallback, PDHPDLStatus.INSIDE_RANGE

    pdh = daily_highs[-2]  # yesterday's high — [-1] is today's in-progress bar
    pdl = daily_lows[-2]

    if current_close > pdh:
        status = PDHPDLStatus.ABOVE_PDH
    elif current_close < pdl:
        status = PDHPDLStatus.BELOW_PDL
    else:
        status = PDHPDLStatus.INSIDE_RANGE

    return pdh, pdl, status
