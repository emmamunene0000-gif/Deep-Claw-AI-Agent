"""
LightGBM Quantile Model — Phase 2 confidence engine.

Trains on feature_store rows (labeled only).
Five quantile heads: q10/q25/q50/q75/q90 predicting realized_r distribution.
Confidence is derived from P(R > 0) estimated from the quantile outputs.

Phase 1 → Phase 2 swap: toggle USE_ML_CONFIDENCE=true in settings.
The inference interface is identical to confidence_v1.confidence().
"""
from __future__ import annotations

import json
import logging
import pickle
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_QUANTILES = [0.10, 0.25, 0.50, 0.75, 0.90]
_MODEL_PATH = Path("data/models/lgbm_confidence.pkl")

# Features used for training — flat numeric columns from feature_store
_FEATURE_COLS = [
    "total_score", "rsi", "rsi_positive", "rsi_negative",
    "trail_exec_trend", "trail_m5_trend", "trail_m15_trend", "trail_h1_trend",
    "vap_last_swing", "vap_current", "trend_fib",
    "poc", "vah", "val",
    "smc_swing_bias", "smc_latest_bos", "smc_latest_choch",
    "smc_fvg_bull", "smc_fvg_bear",
    "atr",
    "bull_confidence", "bear_confidence",
]


class QuantileModel:
    """Thin wrapper around LightGBM quantile regressors."""

    def __init__(self) -> None:
        self._models: dict[float, Any] = {}
        self._trained = False

    def train(self, rows: list[dict], min_rows: int = 200) -> bool:
        """
        Train one LightGBM model per quantile.
        Returns True if training succeeded.
        """
        if len(rows) < min_rows:
            log.warning("Insufficient data: %d rows (need %d)", len(rows), min_rows)
            return False

        try:
            import lightgbm as lgb
            import numpy as np
        except ImportError:
            log.error("pip install lightgbm numpy to enable ML training")
            return False

        labeled = [r for r in rows if r.get("realized_r") is not None]
        if len(labeled) < min_rows:
            log.warning("Insufficient labeled rows: %d", len(labeled))
            return False

        X = _extract_features(labeled)
        y = [r["realized_r"] for r in labeled]

        for q in _QUANTILES:
            params = {
                "objective": "quantile",
                "alpha": q,
                "num_leaves": 31,
                "learning_rate": 0.05,
                "n_estimators": 200,
                "min_child_samples": 20,
                "verbose": -1,
            }
            model = lgb.LGBMRegressor(**params)
            model.fit(X, y)
            self._models[q] = model

        self._trained = True
        log.info("QuantileModel trained on %d labeled rows", len(labeled))
        return True

    def predict_quantiles(self, feature_row: dict) -> dict[float, float]:
        """Returns {quantile: predicted_r} for a single feature row."""
        if not self._trained:
            return {q: 0.0 for q in _QUANTILES}

        try:
            import numpy as np
            X = _extract_features([feature_row])
            return {q: float(m.predict(X)[0]) for q, m in self._models.items()}
        except Exception as e:
            log.warning("Prediction error: %s", e)
            return {q: 0.0 for q in _QUANTILES}

    def p_positive(self, quantiles: dict[float, float]) -> float:
        """
        Estimate P(R > 0) from quantile predictions via linear interpolation.
        If q10 > 0: P(R>0) > 0.90. If q90 < 0: P(R>0) < 0.10.
        """
        vals = [quantiles.get(q, 0.0) for q in sorted(_QUANTILES)]
        # Count how many quantile boundaries are > 0
        pos = sum(1 for v in vals if v > 0)
        return pos / len(vals)

    def save(self, path: Path = _MODEL_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self._models, f)
        log.info("Model saved to %s", path)

    def load(self, path: Path = _MODEL_PATH) -> bool:
        if not path.exists():
            return False
        try:
            with open(path, "rb") as f:
                self._models = pickle.load(f)
            self._trained = bool(self._models)
            log.info("Model loaded from %s", path)
            return True
        except Exception as e:
            log.warning("Failed to load model: %s", e)
            return False


def _extract_features(rows: list[dict]) -> list[list[float]]:
    """Convert feature store rows to numeric matrix."""
    result = []
    for r in rows:
        row_vec = []
        for col in _FEATURE_COLS:
            val = r.get(col)
            row_vec.append(float(val) if val is not None else 0.0)
        result.append(row_vec)
    return result


# Module-level singleton — loaded once at import
_model = QuantileModel()


def load_model(path: Path = _MODEL_PATH) -> bool:
    return _model.load(path)


def get_model() -> QuantileModel:
    return _model
