"""
R-Multiple TP Planner — computes TP1/TP2/TP3 from entry, SL distance, and R targets.
Fixed at signal acceptance. Never moved.
"""
from __future__ import annotations

from deep_claw.core.types import Direction


def compute_tp_levels(
    entry: float,
    sl: float,
    direction: Direction,
    r_multiples: list[float] | None = None,
) -> tuple[float, float, float]:
    """
    Returns (tp1, tp2, tp3).
    Default R multiples: 1.0, 1.5, 2.0 (cheatsheet §3.3).
    sl_distance is the absolute price distance from entry to SL.
    """
    if r_multiples is None:
        r_multiples = [1.0, 1.5, 2.0]

    sl_distance = abs(entry - sl)
    if direction == Direction.LONG:
        tp1 = entry + sl_distance * r_multiples[0]
        tp2 = entry + sl_distance * r_multiples[1]
        tp3 = entry + sl_distance * r_multiples[2]
    else:
        tp1 = entry - sl_distance * r_multiples[0]
        tp2 = entry - sl_distance * r_multiples[1]
        tp3 = entry - sl_distance * r_multiples[2]

    return tp1, tp2, tp3


def compute_sl(
    entry: float,
    direction: Direction,
    atr: float,
    swing_level: float | None = None,
    ema21: float | None = None,
    sl_buffer_mult: float = 0.5,
) -> float:
    """
    SL computation from cheatsheet §3.3:
    SL = max(EMA21, swing_low) - ATR*buffer for longs
    Fallback: entry - ATR*1.5 if structural SL would be invalid.
    """
    fallback = atr * 1.5

    if direction == Direction.LONG:
        structural = max(
            ema21 if ema21 is not None else 0.0,
            swing_level if swing_level is not None else 0.0,
        )
        candidate_sl = structural - atr * sl_buffer_mult
        if candidate_sl >= entry or candidate_sl <= 0:
            return entry - fallback
        return candidate_sl
    else:
        structural = min(
            ema21 if ema21 is not None else float("inf"),
            swing_level if swing_level is not None else float("inf"),
        )
        if structural == float("inf"):
            return entry + fallback
        candidate_sl = structural + atr * sl_buffer_mult
        if candidate_sl <= entry:
            return entry + fallback
        return candidate_sl


def realized_r(
    entry: float,
    exit_price: float,
    sl_at_entry: float,
    direction: Direction,
) -> float:
    """Realized R-multiple = (exit - entry) / (entry - sl) for longs."""
    sl_distance = abs(entry - sl_at_entry)
    if sl_distance == 0:
        return 0.0
    if direction == Direction.LONG:
        return (exit_price - entry) / sl_distance
    else:
        return (entry - exit_price) / sl_distance
