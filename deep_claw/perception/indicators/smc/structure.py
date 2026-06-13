"""
SMC Structure — BOS/CHoCH detection on confirmed swing pivots.
Ported from ADSA v7 §17-19. No lookahead; uses only confirmed bars.

BOS  (Break of Structure) = continuation: price breaks the last swing high/low
      in the direction of the existing trend.
CHoCH (Change of Character) = reversal: price breaks the last swing high/low
      AGAINST the existing trend.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass
class StructureState:
    swing_bias: int               # 1 bullish, -1 bearish, 0 neutral
    latest_bos_direction: int     # 1 bullish BOS, -1 bearish BOS, 0 none
    latest_choch_direction: int   # 1 bullish CHoCH, -1 bearish CHoCH, 0 none
    last_swing_high: float
    last_swing_low: float
    ph_top: float                 # highest unmitigated pivot high (buy-side liquidity)
    pl_btm: float                 # lowest unmitigated pivot low (sell-side liquidity)


def _pivot_highs(highs: Sequence[float], lookback: int = 5) -> list[tuple[int, float]]:
    """Returns [(index, value)] of confirmed pivot highs."""
    h = list(highs)
    pivots = []
    for i in range(lookback, len(h) - lookback):
        if all(h[i] >= h[j] for j in range(i - lookback, i + lookback + 1) if j != i):
            pivots.append((i, h[i]))
    return pivots


def _pivot_lows(lows: Sequence[float], lookback: int = 5) -> list[tuple[int, float]]:
    l = list(lows)
    pivots = []
    for i in range(lookback, len(l) - lookback):
        if all(l[i] <= l[j] for j in range(i - lookback, i + lookback + 1) if j != i):
            pivots.append((i, l[i]))
    return pivots


def compute_smc_structure(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    swing_len: int = 50,
    lookback: int = 5,
) -> StructureState:
    """
    Compute current SMC structure state from the bar history.
    Returns a StructureState snapshot.

    Uses confirmed pivot highs/lows only (lookback bars each side).
    """
    if len(closes) < lookback * 2 + 2:
        mid = closes[-1] if closes else 0.0
        return StructureState(0, 0, 0, mid, mid, mid, mid)

    ph_list = _pivot_highs(highs, lookback)
    pl_list = _pivot_lows(lows, lookback)

    # Only consider pivots within swing_len bars
    cutoff = len(closes) - swing_len
    recent_ph = [(i, v) for i, v in ph_list if i >= cutoff]
    recent_pl = [(i, v) for i, v in pl_list if i >= cutoff]

    if not recent_ph or not recent_pl:
        mid = closes[-1]
        return StructureState(0, 0, 0, mid, mid, mid, mid)

    last_sh = recent_ph[-1][1]  # most recent swing high
    last_sl = recent_pl[-1][1]  # most recent swing low

    # Liquidity levels: highest unbroken pivot high and lowest unbroken pivot low
    ph_top = max(v for _, v in recent_ph)
    pl_btm = min(v for _, v in recent_pl)

    current_close = closes[-1]
    prev_close = closes[-2] if len(closes) > 1 else closes[-1]

    bos_bull = 0
    bos_bear = 0
    choch_bull = 0
    choch_bear = 0

    # Determine current bias from sequential pivot structure
    # Bullish: HH + HL pattern; Bearish: LH + LL pattern
    if len(recent_ph) >= 2 and len(recent_pl) >= 2:
        ph_trend = recent_ph[-1][1] > recent_ph[-2][1]  # higher high
        pl_trend = recent_pl[-1][1] > recent_pl[-2][1]  # higher low

        if ph_trend and pl_trend:
            swing_bias = 1
        elif not ph_trend and not pl_trend:
            swing_bias = -1
        else:
            swing_bias = 0
    else:
        swing_bias = 0

    # BOS / CHoCH detection: did current close break the last swing level?
    if prev_close <= last_sh < current_close:
        if swing_bias >= 0:
            bos_bull = 1   # continuation
        else:
            choch_bull = 1  # reversal
    elif prev_close >= last_sl > current_close:
        if swing_bias <= 0:
            bos_bear = -1
        else:
            choch_bear = -1

    latest_bos = bos_bull + bos_bear
    latest_choch = choch_bull + choch_bear

    # Update bias on CHoCH
    if choch_bull:
        swing_bias = 1
    elif choch_bear:
        swing_bias = -1

    return StructureState(
        swing_bias=swing_bias,
        latest_bos_direction=latest_bos,
        latest_choch_direction=latest_choch,
        last_swing_high=last_sh,
        last_swing_low=last_sl,
        ph_top=ph_top,
        pl_btm=pl_btm,
    )
