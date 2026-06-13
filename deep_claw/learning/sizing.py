"""
ML-informed Kelly sizing — Phase 2.

Uses the predicted R-multiple distribution (from QuantileModel) to compute
a fractional Kelly fraction that accounts for the full distribution shape,
not just the expected value.

Fractional Kelly = f* × kelly_fraction_clamp (default 0.25)
where f* is derived from the predicted win probability and average payoff.

This module is only active when USE_ML_CONFIDENCE=true.
It supplements (not replaces) the 4-clamp safety floor in position_sizer.py.
"""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)

# Kelly fraction cap — never bet more than 25% of the Kelly optimal.
# This is the single most important risk control parameter.
_KELLY_CAP = 0.25


def kelly_from_quantiles(quantiles: dict[float, float]) -> float:
    """
    Derive a fractional Kelly f from quantile predictions.

    Approximation:
      - P(win) = P(R > 0) estimated from quantile spread
      - E(win | win) = q90 / 2 (conservative)
      - E(loss | loss) = abs(q10) / 2 (conservative)
      - Kelly = P(win)/E(loss) - P(loss)/E(win)
      - Apply _KELLY_CAP

    Returns fraction of total risk capital (0.0 to 1.0).
    """
    q10 = quantiles.get(0.10, -1.0)
    q90 = quantiles.get(0.90, 1.0)

    # Estimate win probability from quantile spread
    vals = sorted(quantiles.values())
    p_win = sum(1 for v in vals if v > 0) / len(vals)
    p_loss = 1.0 - p_win

    if p_win <= 0 or p_loss <= 0:
        return 0.0

    avg_win = max(0.01, q90 / 2)
    avg_loss = max(0.01, abs(q10) / 2)

    kelly_f = p_win / avg_loss - p_loss / avg_win
    fractional = kelly_f * _KELLY_CAP

    return max(0.0, min(fractional, _KELLY_CAP))


def ml_risk_scalar(quantiles: dict[float, float], base_risk_usd: float) -> float:
    """
    Scale the base risk by the Kelly fraction.
    Returns the risk amount to pass into compute_size().
    The 4-clamp in position_sizer.py then applies the hard floors.
    """
    k = kelly_from_quantiles(quantiles)
    if k <= 0:
        log.debug("Negative Kelly — no trade")
        return 0.0
    scaled = base_risk_usd * (k / _KELLY_CAP)  # normalize to base risk
    return max(0.0, scaled)
