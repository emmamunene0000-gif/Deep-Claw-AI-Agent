"""
BrokerAdapter Protocol — the ONLY interface between Cognition and broker APIs.

Zero trading logic crosses this boundary.
TradeInstruction carries price levels and size — already computed by Cognition.
Adapters translate, they never compute.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from deep_claw.core.types import PositionHandle, TradeInstruction


@runtime_checkable
class BrokerAdapter(Protocol):
    """
    Minimal broker interface. Each venue implements this exactly.
    No additional methods. No venue-specific logic leaks upstream.
    """

    async def open_position(self, instruction: TradeInstruction) -> PositionHandle:
        """Place the order and return an opaque position reference."""
        ...

    async def modify_stop(self, handle: PositionHandle, new_sl: float) -> None:
        """Move SL (e.g. to breakeven on TP2 hit)."""
        ...

    async def partial_close(self, handle: PositionHandle, fraction: float) -> None:
        """Close `fraction` of the position (0.0-1.0). Used for TP1/TP2 partials."""
        ...

    async def close_position(self, handle: PositionHandle) -> None:
        """Close the entire remaining position."""
        ...

    async def get_live_pnl(self, handle: PositionHandle) -> float:
        """Return current unrealized P&L in USD."""
        ...
