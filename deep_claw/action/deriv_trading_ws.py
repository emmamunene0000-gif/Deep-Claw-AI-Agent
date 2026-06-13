"""
Dedicated WebSocket client for Deriv trade execution.

Separate from DerivFeed's market-data WS to avoid message-routing complexity.
Handles: authorize → proposal → buy → sell → contract_update.
One trade at a time (matches ONE_TRADE_PER_SYMBOL=true).

Reconnects automatically if the socket drops between operations.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

log = logging.getLogger(__name__)

_MAX_BACKOFF = 32


class DerivTradingWS:
    """
    Lazily-connected WS for multiplier trade execution.
    Call connect() at startup; send() auto-reconnects if needed.
    """

    def __init__(self, token: str, ws_url: str, app_id: str = "") -> None:
        self._token = token
        self._ws_url = ws_url
        self._app_id = app_id
        self._ws: Any | None = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        """Connect and authorize. Safe to call multiple times."""
        if self._ws is not None:
            return
        await self._reconnect()

    async def send(self, payload: dict) -> dict:
        """Send payload, return response. Auto-reconnects on failure."""
        async with self._lock:
            for attempt in range(4):
                try:
                    if self._ws is None:
                        await self._reconnect()
                    await self._ws.send(json.dumps(payload))
                    raw = await asyncio.wait_for(self._ws.recv(), timeout=30)
                    resp = json.loads(raw)
                    if resp.get("error"):
                        raise RuntimeError(f"Deriv API error: {resp['error']['message']}")
                    return resp
                except Exception as exc:
                    backoff = 2 ** attempt
                    log.warning(
                        "DerivTradingWS send failed (attempt %d/4): %s — retry in %ds",
                        attempt + 1, exc, backoff,
                    )
                    self._ws = None
                    if attempt < 3:
                        await asyncio.sleep(backoff)
            raise RuntimeError("DerivTradingWS: failed after 4 attempts")

    async def close(self) -> None:
        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None

    async def _reconnect(self) -> None:
        try:
            import websockets
        except ImportError:
            raise RuntimeError("pip install websockets")

        url = self._ws_url
        if self._app_id:
            url = f"{url}?app_id={self._app_id}"

        log.info("DerivTradingWS connecting to %s", url)
        ws = await websockets.connect(url, ping_interval=30, ping_timeout=10)

        # Authorize
        await ws.send(json.dumps({"authorize": self._token}))
        raw = await asyncio.wait_for(ws.recv(), timeout=15)
        resp = json.loads(raw)
        if resp.get("error"):
            await ws.close()
            raise RuntimeError(f"Deriv trading auth failed: {resp['error']['message']}")

        login_id = resp.get("authorize", {}).get("loginid", "?")
        account_type = resp.get("authorize", {}).get("is_virtual", False)
        log.info(
            "DerivTradingWS authorized: loginid=%s type=%s",
            login_id, "DEMO/VIRTUAL" if account_type else "LIVE",
        )
        self._ws = ws
