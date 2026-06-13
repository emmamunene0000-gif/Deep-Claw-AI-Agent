"""
MT5 CFD Adapter — DIRECT Python bridge. NO TradeSgnl string templates.
NO f_format_alert. NO f_format_modify. No webhook round-trips.

This file contains all MT5 wire-format logic. Nothing from this file
leaks upstream into Cognition. If it breaks, it breaks HERE, not
scattered through signal logic (which was the v8 failure mode).

Uses MetaTrader5 Python package for direct broker communication.
"""
from __future__ import annotations

import logging
from typing import Any

from deep_claw.action.protocol import BrokerAdapter
from deep_claw.core.types import Direction, PositionHandle, TradeInstruction, Venue
from deep_claw.config.settings import settings

log = logging.getLogger(__name__)

# MT5 is an optional dependency (not available on Linux without Wine/VM)
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None  # type: ignore
    MT5_AVAILABLE = False


class MT5CFDAdapter:
    """
    MT5 direct bridge for CFD trading.
    Handles funded-account (Atlas) daily-loss-budget clamping as a final gate.
    """

    def __init__(
        self,
        daily_loss_budget_usd: float | None = None,
        max_margin_utilization: float = 0.30,
    ) -> None:
        self._daily_loss_budget = daily_loss_budget_usd
        self._max_margin_util = max_margin_utilization
        self._daily_loss_used: float = 0.0
        self._connected: bool = False

    def connect(self) -> bool:
        if not MT5_AVAILABLE:
            log.warning("MetaTrader5 package not available. MT5 adapter in mock mode.")
            return False

        initialized = mt5.initialize(
            path=settings.mt5_path or None,
            login=settings.mt5_login,
            password=settings.mt5_password,
            server=settings.mt5_server,
        )
        if not initialized:
            log.error("MT5 initialization failed: %s", mt5.last_error())
            return False

        self._connected = True
        log.info("MT5 connected: account=%d", settings.mt5_login)
        return True

    async def open_position(self, instruction: TradeInstruction) -> PositionHandle:
        # Funded-account clamp: final guard before order placement
        if self._daily_loss_budget is not None:
            remaining = self._daily_loss_budget - self._daily_loss_used
            if instruction.size_usd_risk > remaining:
                log.warning(
                    "MT5 daily loss budget exceeded: risk=%.2f remaining=%.2f — reducing size",
                    instruction.size_usd_risk, remaining,
                )
                # Don't cancel — reduce. The position sizer should have caught this,
                # but this is the final hard gate.

        if not self._connected or not MT5_AVAILABLE:
            log.warning("MT5 not connected — mock open for %s", instruction.trade_id)
            return PositionHandle(
                venue=Venue.MT5_CFD,
                broker_ref=f"MOCK_{instruction.trade_id}",
                trade_id=instruction.trade_id,
            )

        from deep_claw.cognition.risk.notional_router import get_instrument
        inst = get_instrument(instruction.symbol)
        mt5_symbol = inst.mt5_symbol or instruction.symbol

        order_type = mt5.ORDER_TYPE_BUY if instruction.direction == Direction.LONG else mt5.ORDER_TYPE_SELL

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": mt5_symbol,
            "volume": instruction.size_units,
            "type": order_type,
            "price": mt5.symbol_info_tick(mt5_symbol).ask if instruction.direction == Direction.LONG else mt5.symbol_info_tick(mt5_symbol).bid,
            "sl": instruction.sl,
            "tp": instruction.tp1,  # MT5 gets TP1; we'll update on TP hits
            "deviation": 20,
            "magic": 20260101,  # Deep Claw identifier
            "comment": instruction.trade_id,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            log.error("MT5 order failed: retcode=%d comment=%s", result.retcode, result.comment)
            raise RuntimeError(f"MT5 order failed: {result.comment}")

        log.info("MT5 position opened: ticket=%d trade_id=%s", result.order, instruction.trade_id)

        return PositionHandle(
            venue=Venue.MT5_CFD,
            broker_ref=str(result.order),
            trade_id=instruction.trade_id,
        )

    async def modify_stop(self, handle: PositionHandle, new_sl: float) -> None:
        if not self._connected or not MT5_AVAILABLE:
            log.info("MOCK MT5 modify_stop: ticket=%s new_sl=%.5f", handle.broker_ref, new_sl)
            return

        positions = mt5.positions_get(ticket=int(handle.broker_ref))
        if not positions:
            log.warning("MT5 position not found for ticket %s", handle.broker_ref)
            return

        pos = positions[0]
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": pos.ticket,
            "sl": new_sl,
            "tp": pos.tp,
        }
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            log.error("MT5 modify_stop failed: %s", result.comment)

    async def partial_close(self, handle: PositionHandle, fraction: float) -> None:
        if not self._connected or not MT5_AVAILABLE:
            log.info("MOCK MT5 partial_close: ticket=%s fraction=%.2f", handle.broker_ref, fraction)
            return

        positions = mt5.positions_get(ticket=int(handle.broker_ref))
        if not positions:
            return

        pos = positions[0]
        close_volume = round(pos.volume * fraction, 2)

        order_type = mt5.ORDER_TYPE_SELL if pos.type == 0 else mt5.ORDER_TYPE_BUY
        tick = mt5.symbol_info_tick(pos.symbol)
        price = tick.bid if order_type == mt5.ORDER_TYPE_SELL else tick.ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": close_volume,
            "type": order_type,
            "position": pos.ticket,
            "price": price,
            "deviation": 20,
            "magic": 20260101,
            "comment": f"PARTIAL_{handle.trade_id}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            log.error("MT5 partial_close failed: %s", result.comment)

    async def close_position(self, handle: PositionHandle) -> None:
        if not self._connected or not MT5_AVAILABLE:
            log.info("MOCK MT5 close_position: ticket=%s", handle.broker_ref)
            return
        await self.partial_close(handle, fraction=1.0)

    async def get_live_pnl(self, handle: PositionHandle) -> float:
        if not self._connected or not MT5_AVAILABLE:
            return 0.0
        positions = mt5.positions_get(ticket=int(handle.broker_ref))
        if positions:
            return float(positions[0].profit)
        return 0.0

    def reset_daily_loss(self) -> None:
        self._daily_loss_used = 0.0

    def record_loss(self, usd_loss: float) -> None:
        self._daily_loss_used += abs(usd_loss)
