"""
Deriv WebSocket feed — multi-TF OHLC subscriptions.

Connects to Deriv's WS API, authorizes with token, subscribes to OHLC
streams for each symbol across exec/M5/M15/H1/H4/D timeframes.

Confirmed-candle logic:
  Deriv sends real-time updates for the CURRENT open candle.
  A candle is confirmed when the epoch changes — i.e., the next candle opens.
  Initial history response: all bars except the last are confirmed.

Reconnection: exponential backoff (2s → 4s → 8s → 16s → 32s cap).
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from deep_claw.config.settings import settings
from deep_claw.core.types import NormalizedCandle, Timeframe, Venue
from deep_claw.perception.candle_bus import NormalizedCandleBus

log = logging.getLogger(__name__)

# Deriv granularity in seconds per timeframe
_TF_TO_GRANULARITY: dict[str, int] = {
    Timeframe.M1.value:  60,
    Timeframe.M5.value:  300,
    Timeframe.M15.value: 900,
    Timeframe.H1.value:  3600,
    Timeframe.H4.value:  14400,
    Timeframe.D.value:   86400,
}

# TFs we subscribe to per Deriv symbol (exec-based system needs these)
_SUBSCRIBED_TFS = [Timeframe.M5, Timeframe.M15, Timeframe.H1, Timeframe.H4, Timeframe.D]

_GRANULARITY_TO_TF = {v: k for k, v in _TF_TO_GRANULARITY.items()}
_MAX_BACKOFF = 32


class DerivFeed:
    """
    One feed instance per Deriv symbol.
    Pushes confirmed NormalizedCandle objects to the shared CandleBus.
    """

    def __init__(
        self,
        symbol: str,          # Deep Claw internal symbol (e.g. VOLATILITY_75_INDEX)
        deriv_code: str,      # Deriv API symbol (e.g. R_75)
        bus: NormalizedCandleBus,
        history_count: int = 500,
    ) -> None:
        self._symbol = symbol
        self._deriv_code = deriv_code
        self._bus = bus
        self._history_count = history_count
        self._running = False
        # {granularity: last_seen_epoch} — used to detect new bars
        self._last_epoch: dict[int, int] = {}
        # {granularity: pending_candle} — the current (unconfirmed) candle
        self._pending: dict[int, dict[str, Any]] = {}

    async def start(self) -> None:
        self._running = True
        backoff = 2
        while self._running:
            try:
                await self._connect_and_stream()
                backoff = 2  # reset on clean disconnect
            except Exception as e:
                log.warning("DerivFeed[%s] disconnected: %s — retry in %ds", self._symbol, e, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, _MAX_BACKOFF)

    async def stop(self) -> None:
        self._running = False

    async def _connect_and_stream(self) -> None:
        try:
            import websockets
        except ImportError:
            log.error("pip install websockets to enable Deriv feed")
            raise

        url = settings.deriv_ws_url
        async with websockets.connect(url, ping_interval=30, ping_timeout=10) as ws:
            log.info("DerivFeed[%s] connected", self._symbol)

            # Authorize
            await ws.send(json.dumps({"authorize": settings.deriv_api_token}))
            auth_resp = json.loads(await ws.recv())
            if auth_resp.get("error"):
                raise RuntimeError(f"Deriv auth failed: {auth_resp['error']['message']}")
            log.info("DerivFeed[%s] authorized as %s", self._symbol,
                     auth_resp.get("authorize", {}).get("loginid", "?"))

            # Subscribe to OHLC for each timeframe
            for tf in _SUBSCRIBED_TFS:
                granularity = _TF_TO_GRANULARITY[tf.value]
                await ws.send(json.dumps({
                    "ticks_history": self._deriv_code,
                    "granularity": granularity,
                    "style": "candles",
                    "end": "latest",
                    "count": self._history_count,
                    "subscribe": 1,
                }))
                log.debug("DerivFeed[%s] subscribed TF=%s gran=%d", self._symbol, tf.value, granularity)

            # Stream loop
            while self._running:
                raw = await asyncio.wait_for(ws.recv(), timeout=90)
                msg = json.loads(raw)
                await self._handle_message(msg)

    async def _handle_message(self, msg: dict) -> None:
        msg_type = msg.get("msg_type")

        if msg_type == "candles":
            # Initial history response
            await self._ingest_history(msg)
        elif msg_type == "ohlc":
            # Real-time update to current candle
            await self._ingest_tick(msg)
        elif msg_type == "error":
            log.warning("DerivFeed[%s] API error: %s", self._symbol, msg.get("error", {}).get("message"))

    async def _ingest_history(self, msg: dict) -> None:
        """Load historical candles. All except the last are confirmed."""
        candles = msg.get("candles", [])
        gran = msg.get("granularity", 900)
        tf_name = _GRANULARITY_TO_TF.get(gran, Timeframe.M15.value)
        tf = Timeframe(tf_name)

        if not candles:
            return

        log.info("DerivFeed[%s] loading %d history bars (gran=%d)", self._symbol, len(candles), gran)

        for i, bar in enumerate(candles):
            is_last = (i == len(candles) - 1)
            confirmed = not is_last  # last bar is still open

            candle = _deriv_bar_to_candle(bar, self._symbol, tf, confirmed=confirmed)
            await self._bus.ingest(candle)

            if is_last:
                # Track the open epoch of the current unconfirmed candle
                self._last_epoch[gran] = bar["epoch"]
                self._pending[gran] = bar
            else:
                self._last_epoch[gran] = bar["epoch"]

    async def _ingest_tick(self, msg: dict) -> None:
        """Handle real-time OHLC update. Detect bar close when epoch changes."""
        ohlc = msg.get("ohlc", {})
        gran = ohlc.get("granularity", 900)
        tf_name = _GRANULARITY_TO_TF.get(gran, Timeframe.M15.value)
        tf = Timeframe(tf_name)

        new_epoch = int(ohlc.get("open_time", ohlc.get("epoch", 0)))
        last_epoch = self._last_epoch.get(gran, 0)

        if new_epoch > last_epoch:
            # Previous candle just closed — confirm it
            prev = self._pending.get(gran)
            if prev and last_epoch > 0:
                confirmed_candle = _deriv_bar_to_candle(prev, self._symbol, tf, confirmed=True)
                await self._bus.ingest(confirmed_candle)
                log.debug(
                    "DerivFeed[%s] confirmed bar: TF=%s close=%.5f ts=%s",
                    self._symbol, tf.value, confirmed_candle.close,
                    confirmed_candle.timestamp.isoformat(),
                )

            self._last_epoch[gran] = new_epoch

        # Always update pending with latest tick data
        self._pending[gran] = {
            "epoch": new_epoch,
            "open": float(ohlc.get("open", 0)),
            "high": float(ohlc.get("high", 0)),
            "low": float(ohlc.get("low", 0)),
            "close": float(ohlc.get("close", 0)),
        }


def _deriv_bar_to_candle(
    bar: dict,
    symbol: str,
    tf: Timeframe,
    confirmed: bool,
) -> NormalizedCandle:
    epoch = bar.get("epoch", bar.get("open_time", 0))
    ts = datetime.fromtimestamp(epoch, tz=timezone.utc)
    return NormalizedCandle(
        symbol=symbol,
        timeframe=tf,
        open=float(bar.get("open", 0)),
        high=float(bar.get("high", 0)),
        low=float(bar.get("low", 0)),
        close=float(bar.get("close", 0)),
        volume=float(bar.get("tick_count", bar.get("volume", 1))),
        timestamp=ts,
        confirmed=confirmed,
        venue=Venue.DERIV_MULTIPLIER,
    )
