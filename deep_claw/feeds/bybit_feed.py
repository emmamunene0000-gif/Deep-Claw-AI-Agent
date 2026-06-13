"""
Bybit WebSocket feed — Kline (OHLCV) subscriptions via pybit V5.

Subscribes to `kline.{interval}.{symbol}` topics.
Bybit sends `confirm: true` when a candle is closed — the cleanest confirmed-bar
signal of any exchange. No epoch-tracking needed.

Supports testnet via bybit_testnet=True in settings (demo mode).
Reconnection: exponential backoff matching Deriv feed.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from deep_claw.config.settings import settings
from deep_claw.core.types import NormalizedCandle, Timeframe, Venue
from deep_claw.perception.candle_bus import NormalizedCandleBus

log = logging.getLogger(__name__)

# Bybit interval strings per Timeframe
_TF_TO_INTERVAL: dict[str, str] = {
    Timeframe.M1.value:  "1",
    Timeframe.M5.value:  "5",
    Timeframe.M15.value: "15",
    Timeframe.H1.value:  "60",
    Timeframe.H4.value:  "240",
    Timeframe.D.value:   "D",
}

_SUBSCRIBED_TFS = [Timeframe.M5, Timeframe.M15, Timeframe.H1, Timeframe.H4, Timeframe.D]

_BYBIT_LIVE_URL  = "wss://stream.bybit.com/v5/public/linear"
_BYBIT_DEMO_URL  = "wss://stream-demo.bybit.com/v5/public/linear"
_BYBIT_TESTNET_URL = "wss://stream-testnet.bybit.com/v5/public/linear"
_MAX_BACKOFF = 32


class BybitFeed:
    """
    One feed instance per Bybit symbol.
    Subscribes to Kline streams; confirmed candles (confirm=true) go straight to the bus.
    """

    def __init__(
        self,
        symbol: str,           # Deep Claw symbol (same as Bybit symbol for perps)
        bybit_symbol: str,     # Bybit market symbol (e.g. BTCUSDT)
        bus: NormalizedCandleBus,
        history_count: int = 500,
    ) -> None:
        self._symbol = symbol
        self._bybit_symbol = bybit_symbol
        self._bus = bus
        self._history_count = history_count
        self._running = False
        self._ws_url = _BYBIT_TESTNET_URL if settings.bybit_testnet else _BYBIT_LIVE_URL

    async def start(self) -> None:
        self._running = True
        backoff = 2
        while self._running:
            try:
                await self._connect_and_stream()
                backoff = 2
            except Exception as e:
                log.warning("BybitFeed[%s] disconnected: %s — retry in %ds", self._symbol, e, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, _MAX_BACKOFF)

    async def stop(self) -> None:
        self._running = False

    async def startup_history(self) -> None:
        """
        Fetch REST history on startup so the bus has enough bars before
        real-time stream begins. Uses pybit HTTP client.
        """
        try:
            from pybit.unified_trading import HTTP
        except ImportError:
            log.warning("pip install pybit to enable Bybit REST history fetch")
            return

        http = HTTP(
            testnet=settings.bybit_testnet,
            api_key=settings.bybit_api_key,
            api_secret=settings.bybit_api_secret,
        )

        for tf in _SUBSCRIBED_TFS:
            interval = _TF_TO_INTERVAL[tf.value]
            try:
                resp = http.get_kline(
                    category="linear",
                    symbol=self._bybit_symbol,
                    interval=interval,
                    limit=self._history_count,
                )
                klines = resp["result"]["list"]
                # Bybit returns newest first — reverse for chronological
                klines = list(reversed(klines))
                log.info("BybitFeed[%s] loading %d history bars TF=%s", self._symbol, len(klines), tf.value)
                for kline in klines:
                    candle = _bybit_kline_to_candle(kline, self._symbol, tf, confirmed=True)
                    await self._bus.ingest(candle)
            except Exception as e:
                log.warning("BybitFeed[%s] REST history fetch failed TF=%s: %s", self._symbol, tf.value, e)

    async def _connect_and_stream(self) -> None:
        try:
            import websockets
        except ImportError:
            log.error("pip install websockets to enable Bybit feed")
            raise

        async with websockets.connect(self._ws_url, ping_interval=20, ping_timeout=10) as ws:
            log.info("BybitFeed[%s] connected to %s", self._symbol, self._ws_url)

            # Subscribe to kline streams
            topics = [
                f"kline.{_TF_TO_INTERVAL[tf.value]}.{self._bybit_symbol}"
                for tf in _SUBSCRIBED_TFS
            ]
            await ws.send(json_dumps({
                "op": "subscribe",
                "args": topics,
            }))
            log.debug("BybitFeed[%s] subscribed to topics: %s", self._symbol, topics)

            while self._running:
                raw = await asyncio.wait_for(ws.recv(), timeout=90)
                msg = _json_loads(raw)
                await self._handle_message(msg)

    async def _handle_message(self, msg: dict) -> None:
        topic = msg.get("topic", "")
        if not topic.startswith("kline."):
            return  # ping/pong/subscription ack

        data_list = msg.get("data", [])
        for kline in data_list:
            confirm = kline.get("confirm", False)
            if not confirm:
                continue  # skip unconfirmed (live updating) candles

            # Parse TF from topic: "kline.15.BTCUSDT" → "15" → Timeframe.M15
            parts = topic.split(".")
            interval = parts[1] if len(parts) > 1 else "15"
            tf = _interval_to_tf(interval)

            candle = _bybit_kline_to_candle(kline, self._symbol, tf, confirmed=True)
            await self._bus.ingest(candle)
            log.debug(
                "BybitFeed[%s] confirmed bar: TF=%s close=%.4f ts=%s",
                self._symbol, tf.value, candle.close, candle.timestamp.isoformat(),
            )


def _bybit_kline_to_candle(
    kline: list | dict,
    symbol: str,
    tf: Timeframe,
    confirmed: bool,
) -> NormalizedCandle:
    # Bybit kline format (REST): [startTime, open, high, low, close, volume, turnover]
    # WebSocket format: {"start": ..., "open": ..., "high": ..., "low": ..., "close": ..., "volume": ..., "confirm": ...}
    if isinstance(kline, list):
        ts = datetime.fromtimestamp(int(kline[0]) / 1000, tz=timezone.utc)
        return NormalizedCandle(
            symbol=symbol, timeframe=tf,
            open=float(kline[1]), high=float(kline[2]),
            low=float(kline[3]), close=float(kline[4]),
            volume=float(kline[5]),
            timestamp=ts, confirmed=confirmed, venue=Venue.BYBIT_PERP,
        )
    else:
        ts = datetime.fromtimestamp(int(kline.get("start", 0)) / 1000, tz=timezone.utc)
        return NormalizedCandle(
            symbol=symbol, timeframe=tf,
            open=float(kline.get("open", 0)), high=float(kline.get("high", 0)),
            low=float(kline.get("low", 0)), close=float(kline.get("close", 0)),
            volume=float(kline.get("volume", 0)),
            timestamp=ts, confirmed=confirmed, venue=Venue.BYBIT_PERP,
        )


def _interval_to_tf(interval: str) -> Timeframe:
    mapping = {"1": Timeframe.M1, "5": Timeframe.M5, "15": Timeframe.M15,
               "30": Timeframe.M30, "60": Timeframe.H1, "240": Timeframe.H4,
               "D": Timeframe.D, "W": Timeframe.W}
    return mapping.get(interval, Timeframe.M15)


def json_dumps(obj: dict) -> str:
    import json
    return json.dumps(obj)


def _json_loads(s: str) -> dict:
    import json
    return json.loads(s)
