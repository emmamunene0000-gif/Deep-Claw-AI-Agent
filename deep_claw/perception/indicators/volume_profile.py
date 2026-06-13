"""
Volume Profile — POC/VAH/VAL and value-area strength.
Ported from cheatsheet §2.11 / ATM Protocol §2.
vp_strength categorical is a first-class ML feature — preserve it exactly.
"""
from __future__ import annotations

from typing import Sequence

from deep_claw.core.types import VPStrength


def compute_volume_profile(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    volumes: Sequence[float],
    resolution: int = 30,
    va_width_pct: float = 70.0,
) -> tuple[float, float, float, VPStrength]:
    """
    Compute POC, VAH, VAL, and vp_strength for the provided bar series.
    Returns (POC, VAH, VAL, vp_strength).

    Uses a price-bucket histogram — volume distributed across `resolution` price levels.
    The value area = price range containing va_width_pct% of total volume.
    """
    if len(closes) < 2:
        price = closes[-1] if closes else 0.0
        return price, price, price, VPStrength.IN_VALUE_AREA

    price_min = min(lows)
    price_max = max(highs)
    price_range = price_max - price_min

    if price_range == 0:
        price = closes[-1]
        return price, price, price, VPStrength.IN_VALUE_AREA

    bucket_size = price_range / resolution
    buckets: list[float] = [0.0] * resolution

    for i in range(len(closes)):
        # Distribute bar's volume across the price range it covers
        bar_low = lows[i]
        bar_high = highs[i]
        bar_vol = volumes[i]

        lo_bucket = int((bar_low - price_min) / bucket_size)
        hi_bucket = int((bar_high - price_min) / bucket_size)
        lo_bucket = max(0, min(lo_bucket, resolution - 1))
        hi_bucket = max(0, min(hi_bucket, resolution - 1))

        n_buckets = hi_bucket - lo_bucket + 1
        vol_per_bucket = bar_vol / n_buckets
        for b in range(lo_bucket, hi_bucket + 1):
            buckets[b] += vol_per_bucket

    # POC = price level with highest volume
    poc_bucket = buckets.index(max(buckets))
    poc = price_min + (poc_bucket + 0.5) * bucket_size

    # Value area: expand from POC until va_width_pct% of total volume is covered
    total_vol = sum(buckets)
    target_vol = total_vol * (va_width_pct / 100.0)

    va_lo = poc_bucket
    va_hi = poc_bucket
    va_vol = buckets[poc_bucket]

    while va_vol < target_vol:
        above = buckets[va_hi + 1] if va_hi + 1 < resolution else 0.0
        below = buckets[va_lo - 1] if va_lo - 1 >= 0 else 0.0

        if above >= below and va_hi + 1 < resolution:
            va_hi += 1
            va_vol += buckets[va_hi]
        elif va_lo - 1 >= 0:
            va_lo -= 1
            va_vol += buckets[va_lo]
        else:
            break

    vah = price_min + (va_hi + 1) * bucket_size
    val = price_min + va_lo * bucket_size

    # vp_strength: where is the current close relative to value area?
    current_close = closes[-1]
    if current_close > vah:
        strength = VPStrength.ABOVE_VAH
    elif current_close < val:
        strength = VPStrength.BELOW_VAL
    else:
        strength = VPStrength.IN_VALUE_AREA

    return poc, vah, val, strength
