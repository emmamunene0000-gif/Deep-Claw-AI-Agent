"""
EpisodeEmitter — watches the delta between consecutive MarketStates
and fires Episode records when something meaningful CHANGED.

This is the key architectural piece that makes the EpisodeStream useful:
it does NOT emit on every bar — only on state transitions.
The chain is a story of what happened, not a log of every measurement.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from deep_claw.core.types import (
    ATRRegime,
    Episode,
    EpisodeType,
    MarketState,
    PDHPDLStatus,
    Session,
)
from deep_claw.journal.episode_stream import EpisodeStream


@dataclass
class _PrevState:
    session: Session | None = None
    atr_regime: ATRRegime | None = None
    rsi_positive: bool = False
    rsi_negative: bool = False
    swing_bias: int = 0
    latest_bos: int = 0
    latest_choch: int = 0
    pdh_pdl_status: PDHPDLStatus | None = None
    ph_top: float = 0.0
    pl_btm: float = 0.0


class EpisodeEmitter:
    """
    One instance per symbol.
    Receives MarketState snapshots, compares to previous state,
    and appends meaningful episodes to the EpisodeStream.

    Call `emit(market_state)` on every confirmed bar close.
    """

    def __init__(self, symbol: str, stream: EpisodeStream) -> None:
        self._symbol = symbol
        self._stream = stream
        self._prev = _PrevState()

    def emit(self, ms: MarketState) -> list[Episode]:
        """
        Compute delta vs previous state and emit all changed episodes.
        Returns the list of episodes emitted (for testing / logging).
        """
        emitted: list[Episode] = []

        # ── Session change ────────────────────────────────────────────
        if self._prev.session is None or ms.session != self._prev.session:
            ep = Episode(
                episode_type=EpisodeType.SESSION_CHANGE,
                symbol=self._symbol,
                timestamp=ms.timestamp,
                payload={"session": ms.session.value, "prev": self._prev.session.value if self._prev.session else None},
                market_state_ref=ms.bar_id,
            )
            self._stream.append(ep)
            emitted.append(ep)

        # ── ATR regime change ─────────────────────────────────────────
        if self._prev.atr_regime is not None and ms.atr_regime != self._prev.atr_regime:
            ep = Episode(
                episode_type=EpisodeType.ATR_REGIME_CHANGE,
                symbol=self._symbol,
                timestamp=ms.timestamp,
                payload={
                    "from": self._prev.atr_regime.value,
                    "to": ms.atr_regime.value,
                    "atr": ms.atr,
                },
                market_state_ref=ms.bar_id,
            )
            self._stream.append(ep)
            emitted.append(ep)

        # ── RSI regime flip ───────────────────────────────────────────
        if ms.rsi_regime_positive != self._prev.rsi_positive or ms.rsi_regime_negative != self._prev.rsi_negative:
            if ms.rsi_regime_positive or ms.rsi_regime_negative:
                direction = 1 if ms.rsi_regime_positive else -1
                ep = Episode(
                    episode_type=EpisodeType.REGIME_FLIP,
                    symbol=self._symbol,
                    timestamp=ms.timestamp,
                    payload={"direction": direction, "rsi": ms.rsi},
                    market_state_ref=ms.bar_id,
                )
                self._stream.append(ep)
                emitted.append(ep)

        # ── SMC: BOS ──────────────────────────────────────────────────
        if ms.smc.latest_bos_direction != 0 and ms.smc.latest_bos_direction != self._prev.latest_bos:
            ep = Episode(
                episode_type=EpisodeType.STRUCTURE_BREAK,
                symbol=self._symbol,
                timestamp=ms.timestamp,
                payload={
                    "direction": ms.smc.latest_bos_direction,
                    "timeframe": ms.timeframe.value,
                    "swing_bias": ms.smc.swing_bias,
                    "price": ms.close,
                },
                market_state_ref=ms.bar_id,
            )
            self._stream.append(ep)
            emitted.append(ep)

        # ── SMC: CHoCH ────────────────────────────────────────────────
        if ms.smc.latest_choch_direction != 0 and ms.smc.latest_choch_direction != self._prev.latest_choch:
            ep = Episode(
                episode_type=EpisodeType.STRUCTURE_CHOCH,
                symbol=self._symbol,
                timestamp=ms.timestamp,
                payload={
                    "direction": ms.smc.latest_choch_direction,
                    "timeframe": ms.timeframe.value,
                    "price": ms.close,
                },
                market_state_ref=ms.bar_id,
            )
            self._stream.append(ep)
            emitted.append(ep)

        # ── Liquidity sweep ───────────────────────────────────────────
        if "SWEPT" in ms.smc.liq_bias:
            side = "BUY" if "BUY" in ms.smc.liq_bias else "SELL"
            level = ms.smc.ph_top if side == "BUY" else ms.smc.pl_btm
            ep = Episode(
                episode_type=EpisodeType.LIQUIDITY_SWEEP,
                symbol=self._symbol,
                timestamp=ms.timestamp,
                payload={
                    "side": side,
                    "level": level,
                    "close": ms.close,
                    "liq_bias": ms.smc.liq_bias,
                },
                market_state_ref=ms.bar_id,
            )
            self._stream.append(ep)
            emitted.append(ep)

        # ── PDH/PDL cross ─────────────────────────────────────────────
        if self._prev.pdh_pdl_status is not None and ms.pdh_pdl_status != self._prev.pdh_pdl_status:
            above_pdh = ms.pdh_pdl_status == PDHPDLStatus.ABOVE_PDH
            below_pdl = ms.pdh_pdl_status == PDHPDLStatus.BELOW_PDL
            if above_pdh or below_pdl:
                ep = Episode(
                    episode_type=EpisodeType.PDH_PDL_CROSS,
                    symbol=self._symbol,
                    timestamp=ms.timestamp,
                    payload={
                        "status": ms.pdh_pdl_status.value,
                        "above_pdh": above_pdh,
                        "price": ms.close,
                        "pdh": ms.pdh,
                        "pdl": ms.pdl,
                    },
                    market_state_ref=ms.bar_id,
                )
                self._stream.append(ep)
                emitted.append(ep)

        # ── Update previous state ─────────────────────────────────────
        self._prev = _PrevState(
            session=ms.session,
            atr_regime=ms.atr_regime,
            rsi_positive=ms.rsi_regime_positive,
            rsi_negative=ms.rsi_regime_negative,
            swing_bias=ms.smc.swing_bias,
            latest_bos=ms.smc.latest_bos_direction,
            latest_choch=ms.smc.latest_choch_direction,
            pdh_pdl_status=ms.pdh_pdl_status,
            ph_top=ms.smc.ph_top,
            pl_btm=ms.smc.pl_btm,
        )

        return emitted
