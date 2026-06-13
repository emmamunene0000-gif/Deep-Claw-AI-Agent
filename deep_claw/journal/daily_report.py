"""
Daily Report — aggregates one trading day into a structured DB row.

Schema mirrors ML_DATA_ADSA §5.7 but stored in SQLite not as text.
Written at EOD (configurable hour). One row per symbol per date.
The ML pipeline reads this table for macro-level pattern detection.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Generator

from deep_claw.core.types import EpisodeType
from deep_claw.journal.episode_stream import EpisodeStream
from deep_claw.journal.pip_tracker import PipTracker

log = logging.getLogger(__name__)

_DEFAULT_DB_PATH = Path("data/daily_reports.db")

_CREATE = """
CREATE TABLE IF NOT EXISTS daily_reports (
    report_id        TEXT PRIMARY KEY,
    symbol           TEXT NOT NULL,
    report_date      TEXT NOT NULL,

    -- Signal activity
    signal_count     INTEGER NOT NULL DEFAULT 0,
    blocked_count    INTEGER NOT NULL DEFAULT 0,
    fired_count      INTEGER NOT NULL DEFAULT 0,

    -- Outcome counters
    tp1_hits         INTEGER NOT NULL DEFAULT 0,
    tp2_hits         INTEGER NOT NULL DEFAULT 0,
    tp3_hits         INTEGER NOT NULL DEFAULT 0,
    sl_hits          INTEGER NOT NULL DEFAULT 0,
    holder_exits     INTEGER NOT NULL DEFAULT 0,

    -- Performance
    gross_win_r      REAL NOT NULL DEFAULT 0.0,
    gross_loss_r     REAL NOT NULL DEFAULT 0.0,
    net_r            REAL NOT NULL DEFAULT 0.0,
    win_rate         REAL NOT NULL DEFAULT 0.0,
    profit_factor    REAL NOT NULL DEFAULT 0.0,

    -- Session breakdown
    london_count     INTEGER NOT NULL DEFAULT 0,
    ny_count         INTEGER NOT NULL DEFAULT 0,
    asia_count       INTEGER NOT NULL DEFAULT 0,
    overlap_count    INTEGER NOT NULL DEFAULT 0,

    -- Regime counts (from episodes)
    atr_high_bars    INTEGER NOT NULL DEFAULT 0,
    atr_med_bars     INTEGER NOT NULL DEFAULT 0,
    atr_low_bars     INTEGER NOT NULL DEFAULT 0,

    -- Episode counts by type (JSON: {"BOS": 3, "CHOCH": 1, ...})
    episode_type_counts TEXT NOT NULL DEFAULT '{}',

    -- Proposal text (from daily assessment)
    assessment_text  TEXT,
    proposal_count   INTEGER NOT NULL DEFAULT 0,

    inserted_at      TEXT NOT NULL,
    UNIQUE(symbol, report_date)
);
CREATE INDEX IF NOT EXISTS idx_dr_symbol ON daily_reports(symbol, report_date);
"""


class DailyReport:
    """Writes one daily-summary row per symbol per date."""

    def __init__(self, db_path: Path = _DEFAULT_DB_PATH) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    @contextmanager
    def _conn(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self._db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init(self) -> None:
        with self._conn() as conn:
            conn.executescript(_CREATE)

    def write(
        self,
        symbol: str,
        pip_tracker: PipTracker,
        stream: EpisodeStream,
        since: datetime,
        assessment_text: str | None = None,
        proposal_count: int = 0,
        report_date: date | None = None,
    ) -> str:
        """
        Aggregate the day and upsert one row.
        Returns the report_id.
        """
        import uuid
        report_date = report_date or datetime.now(timezone.utc).date()
        report_id = f"{symbol}-{report_date.isoformat()}"

        stats = pip_tracker.today

        # Count episodes by type for today
        episodes = stream.query(symbol, since=since)
        type_counts: dict[str, int] = {}
        atr_high = atr_med = atr_low = 0
        for ep in episodes:
            key = ep.episode_type.value
            type_counts[key] = type_counts.get(key, 0) + 1
            if ep.episode_type == EpisodeType.ATR_REGIME_CHANGE:
                regime = ep.payload.get("new_regime", "")
                if regime == "HIGH":
                    atr_high += 1
                elif regime == "MED":
                    atr_med += 1
                elif regime == "LOW":
                    atr_low += 1

        with self._conn() as conn:
            conn.execute("""
                INSERT INTO daily_reports VALUES (
                    ?,?,?,
                    ?,?,?,
                    ?,?,?,?,?,
                    ?,?,?,?,?,
                    ?,?,?,?,
                    ?,?,?,
                    ?,
                    ?,?,
                    ?
                )
                ON CONFLICT(symbol, report_date) DO UPDATE SET
                    signal_count       = excluded.signal_count,
                    blocked_count      = excluded.blocked_count,
                    fired_count        = excluded.fired_count,
                    tp1_hits           = excluded.tp1_hits,
                    tp2_hits           = excluded.tp2_hits,
                    tp3_hits           = excluded.tp3_hits,
                    sl_hits            = excluded.sl_hits,
                    holder_exits       = excluded.holder_exits,
                    gross_win_r        = excluded.gross_win_r,
                    gross_loss_r       = excluded.gross_loss_r,
                    net_r              = excluded.net_r,
                    win_rate           = excluded.win_rate,
                    profit_factor      = excluded.profit_factor,
                    london_count       = excluded.london_count,
                    ny_count           = excluded.ny_count,
                    asia_count         = excluded.asia_count,
                    overlap_count      = excluded.overlap_count,
                    atr_high_bars      = excluded.atr_high_bars,
                    atr_med_bars       = excluded.atr_med_bars,
                    atr_low_bars       = excluded.atr_low_bars,
                    episode_type_counts = excluded.episode_type_counts,
                    assessment_text    = excluded.assessment_text,
                    proposal_count     = excluded.proposal_count,
                    inserted_at        = excluded.inserted_at
            """, (
                report_id, symbol, report_date.isoformat(),

                stats.signal_count, stats.blocked_count,
                stats.tp1_hits + stats.tp2_hits + stats.tp3_hits,

                stats.tp1_hits, stats.tp2_hits, stats.tp3_hits,
                stats.sl_hits, stats.holder_exits,

                stats.gross_win_r, stats.gross_loss_r, stats.net_r,
                stats.win_rate, stats.profit_factor,

                stats.london_count, stats.ny_count,
                stats.asia_count, stats.overlap_count,

                atr_high, atr_med, atr_low,

                json.dumps(type_counts),

                assessment_text, proposal_count,

                datetime.now(timezone.utc).isoformat(),
            ))

        log.info(
            "Daily report written: %s %s — %dT %dW %dL NR=%.2fR PF=%.2f",
            symbol, report_date,
            stats.tp1_hits + stats.sl_hits,
            stats.tp1_hits, stats.sl_hits,
            stats.net_r, stats.profit_factor,
        )
        return report_id

    def get_recent(self, symbol: str, days: int = 30) -> list[dict]:
        """Return the last N daily reports for a symbol."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM daily_reports WHERE symbol = ? "
                "ORDER BY report_date DESC LIMIT ?",
                (symbol, days),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_rolling_stats(self, symbol: str, days: int = 14) -> dict:
        """Rolling aggregate over the last N days — used by ML and dashboard."""
        rows = self.get_recent(symbol, days)
        if not rows:
            return {}
        totals: dict[str, float] = {
            "days": len(rows),
            "net_r": sum(r["net_r"] for r in rows),
            "tp1_hits": sum(r["tp1_hits"] for r in rows),
            "sl_hits": sum(r["sl_hits"] for r in rows),
            "signal_count": sum(r["signal_count"] for r in rows),
        }
        total_closed = totals["tp1_hits"] + totals["sl_hits"]
        totals["win_rate"] = (totals["tp1_hits"] / total_closed * 100) if total_closed else 0.0
        gross_win = sum(r["gross_win_r"] for r in rows)
        gross_loss = sum(r["gross_loss_r"] for r in rows)
        totals["profit_factor"] = round(gross_win / gross_loss, 2) if gross_loss else float("inf")
        return totals
