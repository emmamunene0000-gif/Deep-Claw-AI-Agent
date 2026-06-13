"""
Confidence Engine v1 — 6-factor weighted confluence score.
Ported from ADSA v8 §20.5 with session/ATR-regime adaptive weights (Q2 answer).

STRUCTURAL, not cosmetic:
  - Below settings.confidence_threshold: no trade
  - Above threshold: scales Kelly fraction in position_sizer.py
  - Determines holder-mode eligibility

Interface: (MarketState, WeightMatrix) -> ConfidenceResult
This is the seam where learning/inference.py plugs in with the same signature.
Both Phase 1 (this file) and Phase 2 (learning/inference.py) return ConfidenceResult.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from deep_claw.core.types import ATRRegime, ConfidenceResult, Direction, MarketState, Session


@dataclass
class ConfidenceWeights:
    """
    6 factors from v8 §20.5.
    Weights represent relative importance; they're normalized internally.
    """
    mtf_trail: float = 1.5        # MTF trail alignment (highest weight — trend is king)
    rsi_regime: float = 1.0       # RSI regime positive/negative
    vwap: float = 1.0             # VWAP last_swing alignment
    fib_trend: float = 0.5        # Fibonacci trend direction
    volume_profile: float = 0.5   # VP position (above VAH, below VAL, in value area)
    smc_structure: float = 1.0    # SMC swing bias + CHoCH/BOS recency


@dataclass
class WeightMatrix:
    """
    Session/ATR-regime conditional weight profiles.
    The user's Q2 insight: weights should adapt to market conditions and sessions.

    Priority: session+atr match > session-only match > atr-only match > default.
    Start with v8 defaults everywhere; recalibrate from journal data before Phase 2 ML.
    """
    default: ConfidenceWeights = field(default_factory=ConfidenceWeights)

    # Session-specific overrides
    # Key: session value (e.g. "LONDON", "OVERLAP", "TOKYO")
    session_overrides: dict[str, ConfidenceWeights] = field(default_factory=dict)

    # ATR regime overrides
    # Key: atr_regime value (e.g. "HIGH", "LOW")
    atr_overrides: dict[str, ConfidenceWeights] = field(default_factory=dict)

    # Combined session+atr overrides (highest priority)
    # Key: "{session}_{atr_regime}" (e.g. "LONDON_HIGH", "TOKYO_LOW")
    combined_overrides: dict[str, ConfidenceWeights] = field(default_factory=dict)

    def get(self, session: Session, atr_regime: ATRRegime) -> ConfidenceWeights:
        """Return the most specific applicable weight profile."""
        combined_key = f"{session.value}_{atr_regime.value}"
        if combined_key in self.combined_overrides:
            return self.combined_overrides[combined_key]
        if session.value in self.session_overrides:
            return self.session_overrides[session.value]
        if atr_regime.value in self.atr_overrides:
            return self.atr_overrides[atr_regime.value]
        return self.default


# ── Default weight matrix (v8 baseline + session/ATR tuning) ─────────────────

DEFAULT_WEIGHT_MATRIX = WeightMatrix(
    default=ConfidenceWeights(
        mtf_trail=1.5,
        rsi_regime=1.0,
        vwap=1.0,
        fib_trend=0.5,
        volume_profile=0.5,
        smc_structure=1.0,
    ),
    session_overrides={
        # London: higher momentum, trail and structure matter most
        "LONDON": ConfidenceWeights(
            mtf_trail=2.0, rsi_regime=0.8, vwap=1.2,
            fib_trend=0.4, volume_profile=0.4, smc_structure=1.2,
        ),
        # London-NY overlap: highest edge window — weight everything higher
        "OVERLAP": ConfidenceWeights(
            mtf_trail=2.0, rsi_regime=1.0, vwap=1.2,
            fib_trend=0.5, volume_profile=0.6, smc_structure=1.2,
        ),
        # Tokyo: lower volatility, VWAP and structure matter more than momentum
        "TOKYO": ConfidenceWeights(
            mtf_trail=1.0, rsi_regime=1.2, vwap=1.5,
            fib_trend=0.6, volume_profile=0.8, smc_structure=1.0,
        ),
        # Off-session: almost never trade; high bar for everything
        "OFF": ConfidenceWeights(
            mtf_trail=2.0, rsi_regime=1.5, vwap=1.5,
            fib_trend=0.8, volume_profile=1.0, smc_structure=1.5,
        ),
    },
    atr_overrides={
        # High ATR: trail and momentum dominate
        "HIGH": ConfidenceWeights(
            mtf_trail=2.0, rsi_regime=0.8, vwap=0.8,
            fib_trend=0.4, volume_profile=0.4, smc_structure=1.0,
        ),
        # Low ATR: never trade (return very low score)
        "LOW": ConfidenceWeights(
            mtf_trail=0.5, rsi_regime=0.5, vwap=0.5,
            fib_trend=0.2, volume_profile=0.2, smc_structure=0.5,
        ),
    },
)


# ── Confidence computation ────────────────────────────────────────────────────

def confidence(
    market_state: MarketState,
    weight_matrix: WeightMatrix = DEFAULT_WEIGHT_MATRIX,
) -> ConfidenceResult:
    """
    6-factor weighted confluence score → ConfidenceResult.

    Scores each factor 0-1 for bull and bear independently.
    Applies session/ATR-regime weights.
    Normalizes to 0-100.

    This function signature is the seam for Phase 2 ML swap-in.
    learning/inference.py implements the same signature.
    """
    ms = market_state
    w = weight_matrix.get(ms.session, ms.atr_regime)

    # ── Factor scores (0-1 for bull, 0-1 for bear) ──────────────────────────

    # 1. MTF trail alignment
    # Bull: exec AND M15 trailing bullish. Bear: both bearish.
    trail_bull = float(ms.trail_exec.trend == 1)
    trail_bear = float(ms.trail_exec.trend == -1)
    # Bonus if M15 and H1 also align
    if ms.trail_m15.trend == 1:
        trail_bull = min(1.0, trail_bull + 0.3)
    if ms.trail_h1.trend == 1:
        trail_bull = min(1.0, trail_bull + 0.2)
    if ms.trail_m15.trend == -1:
        trail_bear = min(1.0, trail_bear + 0.3)
    if ms.trail_h1.trend == -1:
        trail_bear = min(1.0, trail_bear + 0.2)

    # 2. RSI regime
    rsi_bull = float(ms.rsi_regime_positive)
    rsi_bear = float(ms.rsi_regime_negative)
    # Partial credit for near-extremes
    if ms.rsi < 35:
        rsi_bull = max(rsi_bull, 0.5)  # oversold — potential bull setup
    if ms.rsi > 65:
        rsi_bear = max(rsi_bear, 0.5)

    # 3. VWAP alignment
    vwap_bull = float(ms.last_swing == 1)
    vwap_bear = float(ms.last_swing == -1)

    # 4. Fibonacci trend
    fib_bull = float(ms.trend_fib == 1)
    fib_bear = float(ms.trend_fib == -1)

    # 5. Volume Profile position
    vp_bull = float(ms.vp_strength.value in ("IN VALUE AREA", "ABOVE VAH"))
    vp_bear = float(ms.vp_strength.value in ("IN VALUE AREA", "BELOW VAL"))
    # Stronger if decisively positioned
    if ms.vp_strength.value == "ABOVE VAH":
        vp_bull = 1.0
        vp_bear = 0.0
    elif ms.vp_strength.value == "BELOW VAL":
        vp_bear = 1.0
        vp_bull = 0.0

    # 6. SMC structure
    smc_bull = 0.0
    smc_bear = 0.0
    if ms.smc.swing_bias == 1:
        smc_bull += 0.5
    elif ms.smc.swing_bias == -1:
        smc_bear += 0.5
    if ms.smc.latest_choch_direction == 1:
        smc_bull += 0.5
    elif ms.smc.latest_choch_direction == -1:
        smc_bear += 0.5
    if ms.smc.latest_bos_direction == 1:
        smc_bull = min(1.0, smc_bull + 0.2)
    elif ms.smc.latest_bos_direction == -1:
        smc_bear = min(1.0, smc_bear + 0.2)

    # ATR regime penalty on LOW (cheatsheet §4.5 rule: don't enter on ATR Low)
    atr_penalty = 0.5 if ms.atr_regime.value == "LOW" else 1.0

    # ── Weighted sum ─────────────────────────────────────────────────────────
    total_weight = (
        w.mtf_trail + w.rsi_regime + w.vwap +
        w.fib_trend + w.volume_profile + w.smc_structure
    )

    raw_bull = (
        trail_bull * w.mtf_trail +
        rsi_bull * w.rsi_regime +
        vwap_bull * w.vwap +
        fib_bull * w.fib_trend +
        vp_bull * w.volume_profile +
        smc_bull * w.smc_structure
    )
    raw_bear = (
        trail_bear * w.mtf_trail +
        rsi_bear * w.rsi_regime +
        vwap_bear * w.vwap +
        fib_bear * w.fib_trend +
        vp_bear * w.volume_profile +
        smc_bear * w.smc_structure
    )

    bull_confidence = (raw_bull / total_weight) * 100.0 * atr_penalty
    bear_confidence = (raw_bear / total_weight) * 100.0 * atr_penalty

    breakdown = {
        "trail_bull": trail_bull, "trail_bear": trail_bear,
        "rsi_bull": rsi_bull, "rsi_bear": rsi_bear,
        "vwap_bull": vwap_bull, "vwap_bear": vwap_bear,
        "fib_bull": fib_bull, "fib_bear": fib_bear,
        "vp_bull": vp_bull, "vp_bear": vp_bear,
        "smc_bull": smc_bull, "smc_bear": smc_bear,
        "atr_penalty": atr_penalty,
    }

    return ConfidenceResult(
        bull_confidence=round(bull_confidence, 1),
        bear_confidence=round(bear_confidence, 1),
        breakdown=breakdown,
        weights_used={
            "mtf_trail": w.mtf_trail, "rsi_regime": w.rsi_regime,
            "vwap": w.vwap, "fib_trend": w.fib_trend,
            "volume_profile": w.volume_profile, "smc_structure": w.smc_structure,
        },
        session=ms.session,
        atr_regime=ms.atr_regime,
    )


def get_directional_confidence(result: ConfidenceResult, direction: Direction) -> float:
    if direction == Direction.LONG:
        return result.bull_confidence
    return result.bear_confidence
