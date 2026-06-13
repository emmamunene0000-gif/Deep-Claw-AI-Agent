"""
Adaptive VWAP — swing-anchored, EMA-style running VWAP.
Ported exactly from cheatsheet §2.8.

alpha_from_apt and the swing-anchor re-anchor logic are the critical pieces —
port verbatim, no approximations.
"""
from __future__ import annotations

import math
from typing import Sequence


def alpha_from_apt(apt: float) -> float:
    """
    Exact port of Pine's alpha formula (cheatsheet §2.8).
    apt = adaptive period. decay = exp(-ln2 / apt).
    """
    decay = math.exp(-math.log(2.0) / max(1.0, apt))
    return 1.0 - decay


def _highest_bars(values: Sequence[float], period: int) -> int:
    """Index of the highest value in the last `period` bars. Returns bars ago (0 = current)."""
    window = list(values)[-period:]
    if not window:
        return 0
    max_val = max(window)
    # Return how many bars ago the maximum occurred
    for i, v in enumerate(reversed(window)):
        if v == max_val:
            return i
    return 0


def _lowest_bars(values: Sequence[float], period: int) -> int:
    window = list(values)[-period:]
    if not window:
        return 0
    min_val = min(window)
    for i, v in enumerate(reversed(window)):
        if v == min_val:
            return i
    return 0


class AdaptiveVWAP:
    """
    Stateful (one instance per symbol/TF) adaptive VWAP.
    Must be updated on each confirmed bar close.
    """

    def __init__(
        self,
        swing_period: int = 50,
        base_apt: int = 20,
        adapt_by_atr: bool = False,
        vol_bias: float = 10.0,
    ) -> None:
        self._prd = swing_period
        self._base_apt = base_apt
        self._adapt_by_atr = adapt_by_atr
        self._vol_bias = vol_bias

        self._p_vwap: float = 0.0   # numerator accumulator
        self._vol_vwap: float = 0.0 # denominator accumulator
        self._vap: float = 0.0      # current VWAP price
        self._dir: int = 1          # swing direction: 1 = bullish, -1 = bearish
        self._initialized: bool = False

    def update(
        self,
        highs: Sequence[float],
        lows: Sequence[float],
        closes: Sequence[float],
        volumes: Sequence[float],
    ) -> tuple[float, int]:
        """
        Update VWAP with latest bar data.
        Returns (vap_current: float, last_swing: int).
        last_swing = 1 (bullish / price above VWAP anchor), -1 (bearish).
        """
        if len(closes) < self._prd:
            return closes[-1] if closes else 0.0, 1

        hlc3 = [(highs[i] + lows[i] + closes[i]) / 3 for i in range(len(closes))]

        # Swing direction: did price make a new highest high or lowest low recently?
        ph_len = _highest_bars(list(highs), self._prd)
        pl_len = _lowest_bars(list(lows), self._prd)
        new_dir = 1 if ph_len > pl_len else -1

        apt = self._base_apt
        alpha = alpha_from_apt(apt)

        if not self._initialized or new_dir != self._dir:
            # Re-anchor on swing flip
            self._dir = new_dir
            self._p_vwap = hlc3[-1] * volumes[-1]
            self._vol_vwap = volumes[-1]
            self._initialized = True
        else:
            self._p_vwap = (1 - alpha) * self._p_vwap + alpha * (hlc3[-1] * volumes[-1])
            self._vol_vwap = (1 - alpha) * self._vol_vwap + alpha * volumes[-1]

        if self._vol_vwap > 0:
            self._vap = self._p_vwap / self._vol_vwap
        else:
            self._vap = closes[-1]

        return self._vap, self._dir
