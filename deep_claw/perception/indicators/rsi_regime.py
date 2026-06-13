"""
RSI Momentum Regime — flip-flop state machine.
Ported exactly from cheatsheet §2.10.
Stateful (one instance per symbol/TF) — update on each confirmed bar.
"""
from __future__ import annotations

from typing import Sequence


def compute_rsi(closes: Sequence[float], period: int = 14) -> float:
    """Wilder RSI. Standard port — no lookforward."""
    if len(closes) < period + 1:
        return 50.0

    gains: list[float] = []
    losses: list[float] = []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _ema5_slope(closes: Sequence[float]) -> float:
    """EMA5 slope (current vs prior bar). Used as RSI regime confirmation."""
    if len(closes) < 6:
        return 0.0
    k = 2.0 / 6.0
    ema = closes[0]
    for c in closes[1:]:
        ema = c * k + ema * (1 - k)
    # Compare last two EMA values
    ema_prev = closes[0]
    for c in closes[1:-1]:
        ema_prev = c * k + ema_prev * (1 - k)
    return ema - ema_prev


class RSIRegime:
    """
    Flip-flop state machine matching Pine's regimeBullish/regimeBearish logic.
    positive=True when RSI crossed above pos_thresh with positive EMA5 slope.
    negative=True when RSI crossed below neg_thresh with negative EMA5 slope.
    Each state flips the other off.
    """

    def __init__(
        self,
        period: int = 14,
        pos_thresh: float = 55.0,
        neg_thresh: float = 45.0,
    ) -> None:
        self._period = period
        self._pos_thresh = pos_thresh
        self._neg_thresh = neg_thresh
        self._positive: bool = False
        self._negative: bool = False
        self._prev_rsi: float = 50.0

    def update(self, closes: Sequence[float]) -> tuple[float, bool, bool]:
        """
        Returns (rsi, positive, negative).
        Call once per confirmed bar close with the full close history.
        """
        rsi = compute_rsi(closes, self._period)
        slope = _ema5_slope(closes)

        # Pine: positive = ta.crossover(rsi, pos_thresh) and rsi > neg_thresh and slope > 0
        crossed_above_pos = self._prev_rsi < self._pos_thresh and rsi >= self._pos_thresh
        crossed_below_neg = self._prev_rsi > self._neg_thresh and rsi <= self._neg_thresh

        if crossed_above_pos and rsi > self._neg_thresh and slope > 0:
            self._positive = True
            self._negative = False
        elif crossed_below_neg and slope < 0:
            self._negative = True
            self._positive = False

        self._prev_rsi = rsi
        return rsi, self._positive, self._negative
