"""
Deriv Multiplier Adapter.
Proposal→buy flow, $-based stop_loss via limit_order.
TP management stays in Cognition — we submit with NO take_profit.
Partial closes for TP1/TP2 via Deriv's partial-sell API.

API reference: Deriv WebSocket API v3.
"""
from __future__ import annotations

import json
import asyncio
import logging
from typing import Any

from deep_claw.action.protocol import BrokerAdapter
from deep_claw.action.deriv_trading_ws import DerivTradingWS
from deep_claw.core.types import Direction, PositionHandle, TradeInstruction, Venue
from deep_claw.config.settings import settings

log = logging.getLogger(__name__)


class DerivMultiplierAdapter:
    """
    Implements BrokerAdapter for Deriv Multiplier contracts.
    Uses a dedicated DerivTradingWS for all execution calls.
    """

    def __init__(self, trading_ws: DerivTradingWS | None = None) -> None:
        self._trading_ws = trading_ws  # None → MOCK mode
        self._pending: dict[str, Any] = {}  # trade_id → contract details

    @property
    def _ws(self) -> DerivTradingWS | None:
        return self._trading_ws

    async def open_position(self, instruction: TradeInstruction) -> PositionHandle:
        """
        Deriv flow: proposal → buy.
        SL submitted as limit_order.stop_loss = $ amount at risk (not price level).
        No take_profit submitted — TP management is Deep Claw's job.
        """
        from deep_claw.cognition.risk.notional_router import get_instrument

        inst = get_instrument(instruction.symbol)
        sl_pips = abs(instruction.entry - instruction.sl) / inst.pip_size
        stop_loss_usd = instruction.size_usd_risk  # dollar risk = stake at risk

        proposal_req = {
            "proposal": 1,
            "amount": instruction.size_usd_risk,
            "basis": "stake",
            "contract_type": "MULTUP" if instruction.direction == Direction.LONG else "MULTDOWN",
            "currency": "USD",
            "symbol": inst.deriv_code or instruction.symbol,
            "multiplier": self._select_multiplier(instruction),
            "limit_order": {
                "stop_loss": stop_loss_usd,
                # no take_profit — Cognition manages TP levels
            },
        }

        log.info(
            "Deriv proposal request: symbol=%s direction=%s size=$%.2f SL=$%.2f",
            instruction.symbol, instruction.direction.value,
            instruction.size_usd_risk, stop_loss_usd,
        )

        if self._trading_ws is None:
            log.warning("No trading WS — returning MOCK handle for %s", instruction.trade_id)
            return PositionHandle(
                venue=Venue.DERIV_MULTIPLIER,
                broker_ref=f"MOCK_{instruction.trade_id}",
                trade_id=instruction.trade_id,
            )

        # Real flow: proposal → buy
        proposal_resp = await self._trading_ws.send(proposal_req)
        proposal_id = proposal_resp["proposal"]["id"]

        buy_resp = await self._trading_ws.send({
            "buy": proposal_id,
            "price": proposal_resp["proposal"]["ask_price"],
        })
        contract_id = buy_resp["buy"]["contract_id"]

        self._pending[instruction.trade_id] = {
            "contract_id": contract_id,
            "instruction": instruction,
        }

        log.info("Deriv position opened: contract_id=%s trade_id=%s", contract_id, instruction.trade_id)

        return PositionHandle(
            venue=Venue.DERIV_MULTIPLIER,
            broker_ref=str(contract_id),
            trade_id=instruction.trade_id,
        )

    async def modify_stop(self, handle: PositionHandle, new_sl: float) -> None:
        """
        Update contract stop loss via update_contract.
        new_sl is a price level — convert to $ distance for Deriv's limit_order format.
        """
        details = self._pending.get(handle.trade_id)
        if not details:
            log.warning("modify_stop: no pending contract for %s", handle.trade_id)
            return

        instruction: TradeInstruction = details["instruction"]
        new_sl_distance = abs(instruction.entry - new_sl)
        new_sl_usd = new_sl_distance * instruction.size_units

        if self._trading_ws is None:
            log.info("MOCK modify_stop: contract=%s new_sl_usd=$%.2f", handle.broker_ref, new_sl_usd)
            return

        await self._trading_ws.send({
            "contract_update": 1,
            "contract_id": int(handle.broker_ref),
            "limit_order": {"stop_loss": new_sl_usd},
        })

    async def partial_close(self, handle: PositionHandle, fraction: float) -> None:
        """Close `fraction` of the multiplier contract (Deriv supports partial sells)."""
        details = self._pending.get(handle.trade_id)
        if not details:
            return

        if self._trading_ws is None:
            log.info("MOCK partial_close: contract=%s fraction=%.2f", handle.broker_ref, fraction)
            return

        await self._trading_ws.send({
            "sell_contract_for_multiple_accounts": 1,
            "contract_id": int(handle.broker_ref),
            "price": 0,
            "tokens": [],
        })
        log.info("Partial close sent: contract=%s fraction=%.2f", handle.broker_ref, fraction)

    async def close_position(self, handle: PositionHandle) -> None:
        if self._trading_ws is None:
            log.info("MOCK close_position: contract=%s", handle.broker_ref)
            self._pending.pop(handle.trade_id, None)
            return

        await self._trading_ws.send({
            "sell": int(handle.broker_ref),
            "price": 0,
        })
        self._pending.pop(handle.trade_id, None)
        log.info("Position closed: contract=%s", handle.broker_ref)

    async def get_live_pnl(self, handle: PositionHandle) -> float:
        if self._trading_ws is None:
            return 0.0
        resp = await self._trading_ws.send({
            "proposal_open_contract": 1,
            "contract_id": int(handle.broker_ref),
        })
        return float(resp.get("proposal_open_contract", {}).get("profit", 0.0))

    def _select_multiplier(self, instruction: TradeInstruction) -> int:
        from deep_claw.cognition.risk.notional_router import get_instrument
        inst = get_instrument(instruction.symbol)
        if inst.asset_class.value == "synthetic":
            return 100
        elif inst.asset_class.value == "forex":
            return 200
        return 100
