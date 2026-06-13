"""
ML Inference — Phase 2 confidence engine.

Identical call signature to confidence_v1.confidence():
    predict_confidence(market_state) → ConfidenceResult

Toggled by USE_ML_CONFIDENCE=true in settings.
Falls back to confidence_v1 if model not loaded.

The QuantileModel predicts the R-multiple distribution.
P(R>0) from that distribution becomes the directional confidence score (0-100).
Bull/bear split: if direction is bullish (trail > 0), bull_confidence = p_pos * 100.
"""
from __future__ import annotations

import logging

from deep_claw.cognition.confidence_v1 import DEFAULT_WEIGHT_MATRIX, confidence
from deep_claw.core.types import ConfidenceResult, MarketState
from deep_claw.learning.model import get_model

log = logging.getLogger(__name__)


def predict_confidence(market_state: MarketState) -> ConfidenceResult:
    """
    Phase 2 confidence scoring via LightGBM quantile model.
    If the model is not loaded, falls back to confidence_v1.
    """
    model = get_model()
    if not model._trained:
        log.debug("ML model not trained — using confidence_v1 fallback")
        return confidence(market_state, DEFAULT_WEIGHT_MATRIX)

    feature_row = _market_state_to_feature_row(market_state)
    quantiles = model.predict_quantiles(feature_row)
    p_pos = model.p_positive(quantiles)

    # Directional split based on trail trend
    trail_bias = market_state.trail_exec.trend  # +1 = bullish, -1 = bearish

    if trail_bias >= 0:
        bull_conf = p_pos * 100
        bear_conf = (1 - p_pos) * 100
    else:
        bear_conf = p_pos * 100
        bull_conf = (1 - p_pos) * 100

    dir_conf = bull_conf if trail_bias >= 0 else bear_conf

    breakdown = {
        "source": "lgbm_quantile",
        "p_positive": round(p_pos, 3),
        "q10": round(quantiles.get(0.10, 0.0), 3),
        "q50": round(quantiles.get(0.50, 0.0), 3),
        "q90": round(quantiles.get(0.90, 0.0), 3),
    }

    return ConfidenceResult(
        bull_confidence=round(bull_conf, 1),
        bear_confidence=round(bear_conf, 1),
        directional_confidence=round(dir_conf, 1),
        breakdown=breakdown,
    )


def _market_state_to_feature_row(ms: MarketState) -> dict:
    """Convert MarketState to a feature dict matching the feature store schema."""
    return {
        "total_score": ms.total_score,
        "rsi": ms.rsi,
        "rsi_positive": int(ms.rsi_regime_positive),
        "rsi_negative": int(ms.rsi_regime_negative),
        "trail_exec_trend": ms.trail_exec.trend,
        "trail_m5_trend": ms.trail_m5.trend,
        "trail_m15_trend": ms.trail_m15.trend,
        "trail_h1_trend": ms.trail_h1.trend,
        "vap_last_swing": ms.last_swing,
        "vap_current": ms.vap_current,
        "trend_fib": ms.trend_fib,
        "poc": ms.poc,
        "vah": ms.vah,
        "val": ms.val,
        "smc_swing_bias": ms.smc.swing_bias,
        "smc_latest_bos": ms.smc.latest_bos_direction,
        "smc_latest_choch": ms.smc.latest_choch_direction,
        "smc_fvg_bull": int(ms.smc.fvg_bull_active),
        "smc_fvg_bear": int(ms.smc.fvg_bear_active),
        "atr": ms.atr,
        # Confidence_v1 scores as additional features
        "bull_confidence": 0.0,
        "bear_confidence": 0.0,
    }
