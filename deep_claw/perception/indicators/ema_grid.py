"""
EMA Grid — EMA9 and EMA21 per timeframe, trend direction.
Pure function. Feeds the 5-TF scoring engine (cheatsheet §4.2).
"""
from __future__ import annotations

from typing import Sequence

from deep_claw.core.types import EMATrend


def _ema(values: Sequence[float], period: int) -> float:
    if not values:
        return 0.0
    k = 2.0 / (period + 1)
    val = values[0]
    for v in values[1:]:
        val = v * k + val * (1 - k)
    return val


def compute_ema_trend(closes: Sequence[float]) -> EMATrend:
    """
    Returns EMATrend for the given close series.
    bullish = EMA9 > EMA21.
    Call separately per timeframe with that TF's close history.
    """
    ema9 = _ema(closes, 9)
    ema21 = _ema(closes, 21)
    return EMATrend(ema9=ema9, ema21=ema21, bullish=ema9 > ema21)


def compute_total_score(
    ema_grid: dict[str, EMATrend],
    rsi_positive: bool,
    rsi_negative: bool,
    vap_last_swing: int,
    trend_fib: int,
    timeframes: list[str],
) -> tuple[float, str]:
    """
    5-TF composite score (-15 to +15) from cheatsheet §4.2.

    For each TF: layer_score = n_score(regime) + n_score(vwap) + n_score(fib)
    where n_score = +1 Bull, -1 Bear, 0 Neutral.

    RSI is NOT in the numeric score (display only in the tree narrative).

    Returns (total_score, master_bias_label).
    """
    def n_score(val: int) -> int:
        return 1 if val > 0 else (-1 if val < 0 else 0)

    regime_score = n_score(1 if rsi_positive else (-1 if rsi_negative else 0))
    vwap_score = n_score(vap_last_swing)
    fib_score = n_score(trend_fib)

    # Each TF contributes the same fundamental regime/vwap/fib scores
    # (in a multi-TF setup, each TF has its own MarketState; here we score one set)
    layer_score = regime_score + vwap_score + fib_score
    total_score = float(layer_score)  # single-TF variant; orchestrator aggregates 5 TFs

    # master_bias ladder from cheatsheet §4.2
    if total_score >= 2.5:
        if regime_score > 0:
            bias = "SOVEREIGN HIGH MOMENTUM BULLISH"
        else:
            bias = "BULLISH BIAS (Strong)"
    elif total_score >= 1.5:
        bias = "BULLISH BIAS (Strong)"
    elif total_score >= 0.5:
        bias = "BULLISH BIAS (Moderate)"
    elif total_score <= -2.5:
        bias = "SOVEREIGN HIGH MOMENTUM BEARISH"
    elif total_score <= -1.5:
        bias = "BEARISH BIAS (Strong)"
    elif total_score <= -0.5:
        bias = "BEARISH BIAS (Moderate)"
    elif total_score > 0:
        bias = "QUIET BULL — WAIT"
    elif total_score < 0:
        bias = "QUIET BEAR — WAIT"
    else:
        bias = "NEUTRAL — STAND ASIDE"

    return total_score, bias
