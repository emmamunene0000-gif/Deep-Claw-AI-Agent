"""
Pip Tracker — daily counters: win/loss, gross pips, PF, WR.
Ported from cheatsheet §4.2. Resets on new trading day.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone


@dataclass
class DailyStats:
    date: date
    symbol: str
    signal_count: int = 0
    blocked_count: int = 0
    tp1_hits: int = 0
    tp2_hits: int = 0
    tp3_hits: int = 0
    sl_hits: int = 0
    holder_exits: int = 0
    gross_win_r: float = 0.0
    gross_loss_r: float = 0.0
    net_r: float = 0.0
    london_count: int = 0
    ny_count: int = 0
    asia_count: int = 0
    overlap_count: int = 0

    @property
    def win_rate(self) -> float:
        total = self.tp1_hits + self.sl_hits
        return (self.tp1_hits / total * 100) if total > 0 else 0.0

    @property
    def profit_factor(self) -> float:
        if self.gross_loss_r == 0:
            return float("inf") if self.gross_win_r > 0 else 0.0
        return round(self.gross_win_r / abs(self.gross_loss_r), 2)


class PipTracker:
    """
    Per-symbol daily stats tracker.
    Reset when the trading day rolls over (cheatsheet §3.2 reset trigger).
    """

    def __init__(self, symbol: str) -> None:
        self._symbol = symbol
        self._today: DailyStats = DailyStats(
            date=datetime.now(timezone.utc).date(),
            symbol=symbol,
        )

    def _check_reset(self) -> None:
        today = datetime.now(timezone.utc).date()
        if today != self._today.date:
            self._today = DailyStats(date=today, symbol=self._symbol)

    def record_signal(self, session: str) -> None:
        self._check_reset()
        self._today.signal_count += 1
        s = session.upper()
        if s == "LONDON":
            self._today.london_count += 1
        elif s == "NEW_YORK":
            self._today.ny_count += 1
        elif s in ("TOKYO", "ASIA"):
            self._today.asia_count += 1
        elif s == "OVERLAP":
            self._today.overlap_count += 1

    def record_blocked(self) -> None:
        self._check_reset()
        self._today.blocked_count += 1

    def record_tp1(self, realized_r: float) -> None:
        self._check_reset()
        self._today.tp1_hits += 1
        self._today.gross_win_r += max(0.0, realized_r)
        self._today.net_r += realized_r

    def record_tp2(self, additional_r: float) -> None:
        self._check_reset()
        self._today.tp2_hits += 1
        self._today.gross_win_r += max(0.0, additional_r)
        self._today.net_r += additional_r

    def record_tp3(self, additional_r: float) -> None:
        self._check_reset()
        self._today.tp3_hits += 1
        self._today.gross_win_r += max(0.0, additional_r)
        self._today.net_r += additional_r

    def record_sl(self, realized_r: float) -> None:
        self._check_reset()
        self._today.sl_hits += 1
        loss = min(0.0, realized_r)
        self._today.gross_loss_r += abs(loss)
        self._today.net_r += loss

    def record_holder_exit(self, realized_r: float) -> None:
        self._check_reset()
        self._today.holder_exits += 1
        if realized_r > 0:
            self._today.gross_win_r += realized_r
        else:
            self._today.gross_loss_r += abs(realized_r)
        self._today.net_r += realized_r

    @property
    def today(self) -> DailyStats:
        self._check_reset()
        return self._today

    def get_stats(self) -> dict:
        self._check_reset()
        s = self._today
        return {
            "signals_fired": s.signal_count,
            "signals_blocked": s.blocked_count,
            "total_trades": s.tp1_hits + s.sl_hits + s.holder_exits,
            "tp_hits": s.tp1_hits + s.tp2_hits + s.tp3_hits,
            "sl_hits": s.sl_hits,
            "net_r": round(s.net_r, 3),
            "win_rate": round(s.win_rate, 1),
            "profit_factor": s.profit_factor,
            "london": s.london_count,
            "ny": s.ny_count,
            "asia": s.asia_count,
        }
