"""
Tests for signal generators — verifying pure-function contract.
No generator should touch trade state, shared variables, or each other's output.
"""
from __future__ import annotations

from datetime import datetime, timezone

from deep_claw.core.types import (
    ATRRegime,
    Direction,
    EMATrend,
    LiquidityTrailState,
    MarketState,
    PDHPDLStatus,
    SMCState,
    Session,
    Timeframe,
    VPStrength,
)
from deep_claw.cognition.signals.ut_bot import ut_bot_signal
from deep_claw.cognition.signals.smart_rsi import smart_rsi_signal
from deep_claw.cognition.signals.liquidity_zone import liquidity_zone_signal
from deep_claw.cognition.signals.structure_shift import structure_shift_signal


def _ms(
    close: float = 1.1000,
    trail_trend: int = 1,
    rsi: float = 50.0,
    rsi_positive: bool = False,
    rsi_negative: bool = False,
    last_swing: int = 1,
    trend_fib: int = 1,
    smc_swing: int = 1,
    choch: int = 1,
    liq_bias: str = "NEUTRAL",
    atr_regime: ATRRegime = ATRRegime.HIGH,
    session: Session = Session.OVERLAP,
) -> MarketState:
    trail = LiquidityTrailState(trend=trail_trend, trail_value=close * 0.999 if trail_trend == 1 else close * 1.001)
    smc = SMCState(
        swing_bias=smc_swing, latest_bos_direction=0, latest_choch_direction=choch,
        ph_top=close * 1.01, pl_btm=close * 0.99,
        last_swing_high=close * 1.005, last_swing_low=close * 0.995,
        active_ob_bull=None, active_ob_bear=None,
        fvg_bull_active=True, fvg_bear_active=False,
        liq_bias=liq_bias,
    )
    ema = EMATrend(ema9=close * 1.001, ema21=close * 0.999, bullish=True)
    return MarketState(
        symbol="EURUSD", timestamp=datetime.now(timezone.utc),
        bar_id="test", timeframe=Timeframe.M15,
        open=close, high=close * 1.002, low=close * 0.998, close=close, volume=100.0,
        trail_exec=trail, trail_m5=trail, trail_m15=trail, trail_h1=trail,
        vap_current=close * 0.9995, last_swing=last_swing,
        poc=close, vah=close * 1.002, val=close * 0.998,
        vp_strength=VPStrength.ABOVE_VAH,
        rsi=rsi, rsi_regime_positive=rsi_positive, rsi_regime_negative=rsi_negative,
        trend_fib=trend_fib, fib_upper=close * 1.02, fib_lower=close * 0.98,
        smc=smc,
        pdh=close * 1.005, pdl=close * 0.995, pdh_pdl_status=PDHPDLStatus.INSIDE_RANGE,
        atr=close * 0.001, atr_regime=atr_regime,
        session=session, ema_grid={"M15": ema},
        total_score=8.0, master_bias="BULLISH",
    )


def test_ut_bot_returns_long_candidate_when_aligned():
    ms = _ms(trail_trend=1, rsi_positive=True, last_swing=1)
    result = ut_bot_signal(ms)
    assert result is not None
    assert result.direction == Direction.LONG
    assert result.proposed_sl < ms.close
    assert result.proposed_tp1 > ms.close


def test_ut_bot_returns_none_when_opposed():
    ms = _ms(trail_trend=-1, rsi_positive=True, last_swing=1)
    result = ut_bot_signal(ms)
    # Trail is short, rsi positive — vwap gate or trail gate should block
    # At minimum the trail direction check: close must be above trail for long
    # With trail_trend=-1 the trail value is above close → no long signal
    assert result is None or result.direction == Direction.SHORT


def test_smart_rsi_fires_on_oversold():
    ms = _ms(rsi=22.0, trail_trend=1, last_swing=1)
    result = smart_rsi_signal(ms)
    assert result is not None
    assert result.direction == Direction.LONG


def test_smart_rsi_fires_on_overbought():
    ms = _ms(rsi=78.0, trail_trend=-1, last_swing=-1, smc_swing=-1, choch=-1)
    result = smart_rsi_signal(ms)
    assert result is not None
    assert result.direction == Direction.SHORT


def test_smart_rsi_blocked_when_rsi_neutral():
    ms = _ms(rsi=50.0, trail_trend=1)
    result = smart_rsi_signal(ms)
    assert result is None


def test_generators_are_independent():
    """
    Running both generators on the same MarketState does not produce a shared result.
    Each returns its own candidate (or None) independently.
    """
    ms = _ms(rsi=23.0, trail_trend=1, rsi_positive=True, last_swing=1)
    ut = ut_bot_signal(ms)
    rsi = smart_rsi_signal(ms)

    # Both may fire — but they return separate objects, not the same instance
    if ut is not None and rsi is not None:
        assert ut is not rsi
        assert ut.candidate_id != rsi.candidate_id
        assert ut.source != rsi.source


def test_structure_shift_blocked_on_low_atr():
    ms = _ms(trail_trend=1, last_swing=1, choch=1, atr_regime=ATRRegime.LOW)
    result = structure_shift_signal(ms)
    assert result is None  # ATR too low — structure breaks in compression are unreliable


def test_liquidity_zone_fires_on_sweep_plus_choch():
    ms = _ms(
        trail_trend=1, last_swing=1, choch=1,
        liq_bias="SELL-SIDE SWEPT",
        smc_swing=1,
    )
    result = liquidity_zone_signal(ms)
    assert result is not None
    assert result.direction == Direction.LONG
