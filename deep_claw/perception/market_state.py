"""
MarketStateBuilder — assembles all indicator outputs into a single MarketState per bar.

This is the explicit replacement for Pine's implicit request.security() coordination.
Each indicator module is called once per confirmed bar close.
The result is the numeric feature vector that signal generators and the ML layer read.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Sequence

from deep_claw.core.types import (
    ATRRegime,
    EMATrend,
    LiquidityTrailState,
    MarketState,
    PDHPDLStatus,
    SMCState,
    Session,
    Timeframe,
    VPStrength,
)
from deep_claw.perception.candle_bus import CandleHistory, NormalizedCandleBus
from deep_claw.perception.indicators.adaptive_vwap import AdaptiveVWAP
from deep_claw.perception.indicators.atr_regime import compute_atr, compute_atr_regime
from deep_claw.perception.indicators.daily_levels import compute_pdh_pdl
from deep_claw.perception.indicators.ema_grid import compute_ema_trend, compute_total_score
from deep_claw.perception.indicators.fib_bands import compute_fib_bands
from deep_claw.perception.indicators.liquidity_trail import compute_liquidity_trail
from deep_claw.perception.indicators.rsi_regime import RSIRegime
from deep_claw.perception.indicators.smc.fvg import detect_fvg
from deep_claw.perception.indicators.smc.liquidity import compute_liquidity_levels
from deep_claw.perception.indicators.smc.order_blocks import find_order_blocks
from deep_claw.perception.indicators.smc.structure import compute_smc_structure
from deep_claw.perception.indicators.volume_profile import compute_volume_profile


def _detect_session(ts: datetime) -> Session:
    """Session detection based on UTC hour."""
    hour = ts.hour
    # Tokyo: 00-09 UTC; London: 07-16 UTC; NY: 12-21 UTC; Overlap: 12-16 UTC
    in_tokyo = 0 <= hour < 9
    in_london = 7 <= hour < 16
    in_ny = 12 <= hour < 21
    if in_london and in_ny:
        return Session.OVERLAP
    if in_ny:
        return Session.NEW_YORK
    if in_london:
        return Session.LONDON
    if in_tokyo:
        return Session.TOKYO
    return Session.OFF


class MarketStateBuilder:
    """
    One instance per symbol.
    Maintains stateful indicator instances (VWAP, RSI regime) that need bar history.
    All pure-function indicators are called fresh each bar.
    """

    def __init__(self, symbol: str, exec_tf: Timeframe = Timeframe.M15) -> None:
        self.symbol = symbol
        self.exec_tf = exec_tf

        # Stateful indicators (need history)
        self._vwap = AdaptiveVWAP()
        self._rsi_regime = RSIRegime()

    def build(
        self,
        bus: NormalizedCandleBus,
        daily_bus: NormalizedCandleBus | None = None,
    ) -> MarketState | None:
        """
        Build a MarketState from the current bus state.
        Returns None if there isn't enough bar history yet.
        """
        h = bus.get_history(self.symbol, self.exec_tf)
        if h is None or len(h) < 30:
            return None

        closes = h.closes
        highs = h.highs
        lows = h.lows
        volumes = h.volumes
        latest = h.candles[-1]

        # ── Liquidity trails (exec TF) ──────────────────────────────────
        from deep_claw.config.settings import settings

        trend_exec, trail_exec = compute_liquidity_trail(
            highs, lows, closes,
            ma_len=settings.trail_ma_len,
            atr_len=settings.trail_atr_len,
            atr_mult=settings.trail_atr_mult,
        )
        trail_exec_state = LiquidityTrailState(trend=trend_exec, trail_value=trail_exec)

        # For M5/M15/H1 trails, use their respective histories if available
        trail_m5_state = self._get_trail_for_tf(bus, Timeframe.M5, settings)
        trail_m15_state = self._get_trail_for_tf(bus, Timeframe.M15, settings)
        trail_h1_state = self._get_trail_for_tf(bus, Timeframe.H1, settings)

        # ── Adaptive VWAP ──────────────────────────────────────────────
        vap_current, last_swing = self._vwap.update(highs, lows, closes, volumes)

        # ── Volume Profile ─────────────────────────────────────────────
        poc, vah, val, vp_strength = compute_volume_profile(
            highs, lows, closes, volumes,
            resolution=settings.vp_resolution,
            va_width_pct=settings.vp_va_width,
        )

        # ── RSI Regime ─────────────────────────────────────────────────
        rsi, rsi_positive, rsi_negative = self._rsi_regime.update(closes)

        # ── Fib Bands ──────────────────────────────────────────────────
        trend_fib, fib_upper, fib_lower = compute_fib_bands(
            highs, lows, closes,
            fib_len=settings.fib_len,
            atr_len=settings.fib_atr_len,
            use_atr=settings.fib_use_atr,
        )

        # ── SMC Structure ─────────────────────────────────────────────
        structure = compute_smc_structure(
            highs, lows, closes,
            swing_len=settings.smc_swing_len,
        )
        fvg_bull, fvg_bear = detect_fvg(highs, lows)
        ph_top, pl_btm, liq_bias = compute_liquidity_levels(
            highs, lows, closes,
            pivot_len=settings.liq_pivot_len,
        )
        bull_ob, bear_ob = find_order_blocks(
            [c.open for c in h.candles],
            highs, lows, closes,
            bos_bull_idx=None,  # simplified: OB without BOS index tracking for now
            bos_bear_idx=None,
            ob_size=settings.smc_ob_size,
        )

        smc = SMCState(
            swing_bias=structure.swing_bias,
            latest_bos_direction=structure.latest_bos_direction,
            latest_choch_direction=structure.latest_choch_direction,
            ph_top=ph_top,
            pl_btm=pl_btm,
            last_swing_high=structure.last_swing_high,
            last_swing_low=structure.last_swing_low,
            active_ob_bull=bull_ob,
            active_ob_bear=bear_ob,
            fvg_bull_active=fvg_bull,
            fvg_bear_active=fvg_bear,
            liq_bias=liq_bias,
        )

        # ── PDH/PDL ────────────────────────────────────────────────────
        daily_h = daily_bus.get_history(self.symbol, Timeframe.D) if daily_bus else None
        if daily_h and len(daily_h) >= 2:
            pdh, pdl, pdh_pdl_status = compute_pdh_pdl(
                daily_h.highs, daily_h.lows, closes[-1]
            )
        else:
            pdh, pdl = closes[-1], closes[-1]
            pdh_pdl_status = PDHPDLStatus.INSIDE_RANGE

        # ── ATR Regime ─────────────────────────────────────────────────
        current_atr, atr_regime = compute_atr_regime(highs, lows, closes)

        # ── Session ────────────────────────────────────────────────────
        session = _detect_session(latest.timestamp)

        # ── EMA Grid (exec TF only here; orchestrator can aggregate multi-TF) ──
        ema_trend = compute_ema_trend(closes)
        ema_grid = {self.exec_tf.value: ema_trend}

        # ── Composite score (single TF) ────────────────────────────────
        total_score, master_bias = compute_total_score(
            ema_grid=ema_grid,
            rsi_positive=rsi_positive,
            rsi_negative=rsi_negative,
            vap_last_swing=last_swing,
            trend_fib=trend_fib,
            timeframes=[self.exec_tf.value],
        )

        return MarketState(
            symbol=self.symbol,
            timestamp=latest.timestamp,
            bar_id=f"{self.symbol}_{self.exec_tf.value}_{latest.timestamp.isoformat()}",
            timeframe=self.exec_tf,
            open=latest.open,
            high=latest.high,
            low=latest.low,
            close=latest.close,
            volume=latest.volume,
            trail_exec=trail_exec_state,
            trail_m5=trail_m5_state,
            trail_m15=trail_m15_state,
            trail_h1=trail_h1_state,
            vap_current=vap_current,
            last_swing=last_swing,
            poc=poc,
            vah=vah,
            val=val,
            vp_strength=vp_strength,
            rsi=rsi,
            rsi_regime_positive=rsi_positive,
            rsi_regime_negative=rsi_negative,
            trend_fib=trend_fib,
            fib_upper=fib_upper,
            fib_lower=fib_lower,
            smc=smc,
            pdh=pdh,
            pdl=pdl,
            pdh_pdl_status=pdh_pdl_status,
            atr=current_atr,
            atr_regime=atr_regime,
            session=session,
            ema_grid=ema_grid,
            total_score=total_score,
            master_bias=master_bias,
        )

    def _get_trail_for_tf(
        self, bus: NormalizedCandleBus, tf: Timeframe, settings
    ) -> LiquidityTrailState:
        h = bus.get_history(self.symbol, tf)
        if h is None or len(h) < settings.trail_atr_len + 2:
            return LiquidityTrailState(trend=0, trail_value=0.0)
        trend, trail = compute_liquidity_trail(
            h.highs, h.lows, h.closes,
            atr_len=settings.trail_atr_len,
            atr_mult=settings.trail_atr_mult,
        )
        return LiquidityTrailState(trend=trend, trail_value=trail)
