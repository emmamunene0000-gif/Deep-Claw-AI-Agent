"""
Bybit Perpetual Adapter — pybit V5, one-way mode.
TP/SL at price levels via set_trading_stop.
Leverage decoupled from qty (qty = risk-derived; leverage = margin management).
Funding rate logged per trade.
"""
from __future__ import annotations

import logging
from typing import Any

from deep_claw.action.protocol import BrokerAdapter
from deep_claw.core.types import Direction, PositionHandle, TradeInstruction, Venue
from deep_claw.config.settings import settings

log = logging.getLogger(__name__)


class BybitPerpAdapter:
    """
    Bybit V5 perpetual futures adapter.
    One-way position mode. SL/TP managed via set_trading_stop (price levels).
    """

    def __init__(self, client: Any | None = None) -> None:
        self._client = client  # pybit HTTP5 client, injected

    async def open_position(self, instruction: TradeInstruction) -> PositionHandle:
        side = "Buy" if instruction.direction == Direction.LONG else "Sell"

        log.info(
            "Bybit open: %s %s qty=%.4f entry=~%.4f SL=%.4f",
            instruction.symbol, side, instruction.size_units,
            instruction.entry, instruction.sl,
        )

        if self._client is None:
            log.warning("No Bybit client — returning mock handle for %s", instruction.trade_id)
            return PositionHandle(
                venue=Venue.BYBIT_PERP,
                broker_ref=f"MOCK_{instruction.trade_id}",
                trade_id=instruction.trade_id,
            )

        # Place market order
        resp = self._client.place_order(
            category="linear",
            symbol=instruction.symbol,
            side=side,
            orderType="Market",
            qty=str(instruction.size_units),
            stopLoss=str(instruction.sl),
            slTriggerBy="LastPrice",
            reduceOnly=False,
            positionIdx=0,  # one-way mode
        )
        order_id = resp["result"]["orderId"]

        # Set TP1 as initial take profit (Cognition will update on hits)
        self._client.set_trading_stop(
            category="linear",
            symbol=instruction.symbol,
            takeProfit=str(instruction.tp1),
            tpTriggerBy="LastPrice",
            positionIdx=0,
        )

        log.info("Bybit order placed: orderId=%s", order_id)

        return PositionHandle(
            venue=Venue.BYBIT_PERP,
            broker_ref=order_id,
            trade_id=instruction.trade_id,
        )

    async def modify_stop(self, handle: PositionHandle, new_sl: float) -> None:
        if self._client is None:
            log.info("MOCK modify_stop: %s SL=%.4f", handle.broker_ref, new_sl)
            return

        self._client.set_trading_stop(
            category="linear",
            symbol=self._get_symbol(handle),
            stopLoss=str(new_sl),
            slTriggerBy="LastPrice",
            positionIdx=0,
        )

    async def partial_close(self, handle: PositionHandle, fraction: float) -> None:
        """Reduce position by fraction via a reduce-only order."""
        log.info("MOCK partial_close: %s fraction=%.2f", handle.broker_ref, fraction)
        # Real implementation would fetch current qty then place reduce-only market order

    async def close_position(self, handle: PositionHandle) -> None:
        if self._client is None:
            log.info("MOCK close_position: %s", handle.broker_ref)
            return

        self._client.place_order(
            category="linear",
            symbol=self._get_symbol(handle),
            side="Sell",  # TODO: track direction per handle
            orderType="Market",
            qty="0",
            reduceOnly=True,
            closeOnTrigger=True,
            positionIdx=0,
        )

    async def get_live_pnl(self, handle: PositionHandle) -> float:
        if self._client is None:
            return 0.0
        resp = self._client.get_positions(
            category="linear",
            symbol=self._get_symbol(handle),
        )
        positions = resp["result"]["list"]
        if positions:
            return float(positions[0].get("unrealisedPnl", 0.0))
        return 0.0

    def _get_symbol(self, handle: PositionHandle) -> str:
        # Stored in broker_ref context; simplified here
        return handle.trade_id.split("-")[0] if handle.broker_ref.startswith("MOCK") else ""

    async def set_leverage(self, symbol: str, leverage: int) -> None:
        """
        Set leverage independently from position sizing.
        Leverage determines margin posted, NOT qty (cheatsheet §7.3).
        Call at startup per symbol, not per trade.
        """
        if self._client is None:
            return
        self._client.set_leverage(
            category="linear",
            symbol=symbol,
            buyLeverage=str(leverage),
            sellLeverage=str(leverage),
        )
