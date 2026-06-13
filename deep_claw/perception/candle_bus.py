"""
NormalizedCandleBus — unified OHLCV stream from all broker feeds.

Replaces Pine's request.security() pattern.
Only emits confirmed (bar-close) candles downstream — no repaint risk.
Per-TF candle histories are maintained here; indicator modules pull
their series from this bus, never from raw broker feeds.
"""
from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import AsyncIterator, Callable

from deep_claw.core.types import NormalizedCandle, Timeframe, Venue


# Max bars kept in memory per symbol per TF (enough for any indicator lookback)
_HISTORY_LEN = 500

BarHandler = Callable[[NormalizedCandle], None]


@dataclass
class CandleHistory:
    """Rolling window of confirmed candles for one symbol/TF pair."""
    symbol: str
    timeframe: Timeframe
    candles: deque[NormalizedCandle] = field(
        default_factory=lambda: deque(maxlen=_HISTORY_LEN)
    )

    def push(self, candle: NormalizedCandle) -> None:
        self.candles.append(candle)

    @property
    def closes(self) -> list[float]:
        return [c.close for c in self.candles]

    @property
    def highs(self) -> list[float]:
        return [c.high for c in self.candles]

    @property
    def lows(self) -> list[float]:
        return [c.low for c in self.candles]

    @property
    def volumes(self) -> list[float]:
        return [c.volume for c in self.candles]

    @property
    def hlc3(self) -> list[float]:
        return [(c.high + c.low + c.close) / 3 for c in self.candles]

    def __len__(self) -> int:
        return len(self.candles)

    def enough(self, n: int) -> bool:
        return len(self.candles) >= n


class NormalizedCandleBus:
    """
    Central candle registry.

    Broker adapters push raw candles to `ingest()`.
    Indicator modules pull history via `get_history()`.
    The bus calls registered handlers only on confirmed closes.
    """

    def __init__(self) -> None:
        # {symbol: {timeframe: CandleHistory}}
        self._histories: dict[str, dict[str, CandleHistory]] = defaultdict(dict)
        # Handlers called on every confirmed close: [(symbol_filter, handler)]
        self._handlers: list[tuple[str | None, BarHandler]] = []
        self._lock = asyncio.Lock()

    def register_handler(
        self, handler: BarHandler, symbol: str | None = None
    ) -> None:
        """Register a callback for confirmed bar closes. symbol=None = all symbols."""
        self._handlers.append((symbol, handler))

    async def ingest(self, candle: NormalizedCandle) -> None:
        """
        Accept a candle from any broker feed.
        Only confirmed closes propagate to handlers.
        """
        async with self._lock:
            sym = candle.symbol
            tf = candle.timeframe.value

            if tf not in self._histories[sym]:
                self._histories[sym][tf] = CandleHistory(sym, candle.timeframe)

            history = self._histories[sym][tf]

            if not candle.confirmed:
                return  # never use unconfirmed bars for signals

            history.push(candle)

        for symbol_filter, handler in self._handlers:
            if symbol_filter is None or symbol_filter == candle.symbol:
                handler(candle)

    def get_history(self, symbol: str, timeframe: Timeframe) -> CandleHistory | None:
        return self._histories.get(symbol, {}).get(timeframe.value)

    def get_latest(self, symbol: str, timeframe: Timeframe) -> NormalizedCandle | None:
        h = self.get_history(symbol, timeframe)
        if h and len(h.candles) > 0:
            return h.candles[-1]
        return None

    def has_enough(self, symbol: str, timeframe: Timeframe, n: int) -> bool:
        h = self.get_history(symbol, timeframe)
        return h is not None and h.enough(n)

    def available_symbols(self) -> list[str]:
        return list(self._histories.keys())
