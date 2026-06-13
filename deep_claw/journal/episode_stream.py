"""
Deep Claw — EpisodeStream: the append-only chain that is the spine of the whole system.

Four consumers, one source:
  1. Dashboard  → timeline JSON via renderer
  2. Telegram   → chain narrative via renderer
  3. Claude     → prose context via renderer
  4. Learning   → ML training rows via feature_store

SQLite-backed for persistence. All writes are append-only.
Nothing is ever updated or deleted — only appended.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

from deep_claw.core.types import Episode, EpisodeType


_DEFAULT_DB_PATH = Path("data/episode_stream.db")

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS episodes (
    episode_id     TEXT PRIMARY KEY,
    episode_type   TEXT NOT NULL,
    symbol         TEXT NOT NULL,
    timestamp      TEXT NOT NULL,
    payload        TEXT NOT NULL,
    market_state_ref TEXT,
    inserted_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_episodes_symbol_ts ON episodes(symbol, timestamp);
CREATE INDEX IF NOT EXISTS idx_episodes_type ON episodes(episode_type);
"""


class EpisodeStream:
    """
    Append-only, SQLite-backed episode log.

    Thread-safe via SQLite's WAL mode. Not process-safe for multiple writers —
    only the orchestrator writes; readers (renderer, feature_store) are read-only.
    """

    def __init__(self, db_path: Path = _DEFAULT_DB_PATH) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript(_CREATE_TABLE)

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

    # ── Write ─────────────────────────────────────────────────────────────────

    def append(self, episode: Episode) -> None:
        """Append one episode. The only write operation on this store."""
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO episodes
                    (episode_id, episode_type, symbol, timestamp, payload, market_state_ref, inserted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    episode.episode_id,
                    episode.episode_type.value,
                    episode.symbol,
                    episode.timestamp.isoformat(),
                    json.dumps(episode.payload),
                    episode.market_state_ref,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    # ── Read ──────────────────────────────────────────────────────────────────

    def query(
        self,
        symbol: str,
        since: datetime | None = None,
        until: datetime | None = None,
        episode_types: list[EpisodeType] | None = None,
    ) -> list[Episode]:
        """Flexible query. All parameters are optional filters."""
        clauses = ["symbol = ?"]
        params: list = [symbol]

        if since:
            clauses.append("timestamp >= ?")
            params.append(since.isoformat())
        if until:
            clauses.append("timestamp <= ?")
            params.append(until.isoformat())
        if episode_types:
            placeholders = ",".join("?" * len(episode_types))
            clauses.append(f"episode_type IN ({placeholders})")
            params.extend(et.value for et in episode_types)

        sql = f"SELECT * FROM episodes WHERE {' AND '.join(clauses)} ORDER BY timestamp ASC"

        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()

        return [self._row_to_episode(r) for r in rows]

    def recent(self, symbol: str, n: int = 20) -> list[Episode]:
        """Return the n most recent episodes for a symbol, in chronological order."""
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM (
                    SELECT * FROM episodes WHERE symbol = ?
                    ORDER BY timestamp DESC, rowid DESC LIMIT ?
                ) ORDER BY timestamp ASC, rowid ASC
                """,
                (symbol, n),
            ).fetchall()
        return [self._row_to_episode(r) for r in rows]

    def recent_of_types(
        self, symbol: str, episode_types: list[EpisodeType], n: int = 10
    ) -> list[Episode]:
        placeholders = ",".join("?" * len(episode_types))
        with self._conn() as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM (
                    SELECT * FROM episodes
                    WHERE symbol = ? AND episode_type IN ({placeholders})
                    ORDER BY timestamp DESC LIMIT ?
                ) ORDER BY timestamp ASC
                """,
                (symbol, *[et.value for et in episode_types], n),
            ).fetchall()
        return [self._row_to_episode(r) for r in rows]

    def find_similar_setups(
        self,
        symbol: str,
        verdict: str,
        session: str,
        atr_regime: str,
        limit: int = 5,
    ) -> list[Episode]:
        """
        Episodic memory lookup: find past SIGNAL_ACCEPTED episodes that match
        the current verdict + session + ATR regime.
        Used by ChainReasoningEngine to populate episodic_note.
        """
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM episodes
                WHERE symbol = ?
                  AND episode_type = 'SIGNAL_ACCEPTED'
                  AND json_extract(payload, '$.verdict') = ?
                  AND json_extract(payload, '$.session') = ?
                  AND json_extract(payload, '$.atr_regime') = ?
                ORDER BY timestamp DESC LIMIT ?
                """,
                (symbol, verdict, session, atr_regime, limit),
            ).fetchall()
        return [self._row_to_episode(r) for r in rows]

    def get_today_closed_trades(self, symbol: str, since: datetime) -> list[Episode]:
        return self.query(
            symbol, since=since, episode_types=[EpisodeType.TRADE_CLOSED]
        )

    # ── Render (raw narrative for Claude/Telegram) ────────────────────────────

    def render_narrative(self, symbol: str, n: int = 20) -> str:
        """
        Render the last n episodes as a time-ordered prose chain.
        This is the format Claude receives — not a table, a story.
        """
        episodes = self.recent(symbol, n)
        if not episodes:
            return f"No episodes recorded for {symbol} yet."

        lines = [f"=== {symbol} — Episode Chain (last {len(episodes)} events) ==="]
        for ep in episodes:
            ts = ep.timestamp.strftime("%H:%M")
            summary = _episode_to_line(ep)
            lines.append(f"{ts}  {summary}")
        return "\n".join(lines)

    # ── Internal ──────────────────────────────────────────────────────────────

    @staticmethod
    def _row_to_episode(row: sqlite3.Row) -> Episode:
        return Episode(
            episode_id=row["episode_id"],
            episode_type=EpisodeType(row["episode_type"]),
            symbol=row["symbol"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            payload=json.loads(row["payload"]),
            market_state_ref=row["market_state_ref"],
        )


def _episode_to_line(ep: Episode) -> str:
    """Single-line human-readable summary of an episode. Used in chain narrative."""
    p = ep.payload
    match ep.episode_type:
        case EpisodeType.SESSION_CHANGE:
            return f"Session: {p.get('session', '?')} open."
        case EpisodeType.REGIME_FLIP:
            direction = "bullish" if p.get("direction", 0) > 0 else "bearish"
            return f"RSI regime flipped {direction}."
        case EpisodeType.ATR_REGIME_CHANGE:
            return f"ATR regime: {p.get('from', '?')} → {p.get('to', '?')}."
        case EpisodeType.LIQUIDITY_SWEEP:
            side = p.get("side", "?")
            level = p.get("level", "?")
            return f"{side}-side liquidity swept at {level}."
        case EpisodeType.STRUCTURE_BREAK:
            direction = "bullish" if p.get("direction", 0) > 0 else "bearish"
            return f"BOS confirmed {direction} on {p.get('timeframe', '?')}."
        case EpisodeType.STRUCTURE_CHOCH:
            direction = "bullish" if p.get("direction", 0) > 0 else "bearish"
            return f"CHoCH confirmed {direction} on {p.get('timeframe', '?')}."
        case EpisodeType.PDH_PDL_CROSS:
            return f"Price {'above PDH' if p.get('above_pdh') else 'below PDL'} at {p.get('price', '?')}."
        case EpisodeType.SIGNAL_CANDIDATE:
            return (
                f"{p.get('source', '?')} {p.get('direction', '?')} candidate — "
                f"confidence inputs: {p.get('confidence_inputs', {})}."
            )
        case EpisodeType.SIGNAL_ACCEPTED:
            return (
                f"Signal ACCEPTED: {p.get('source', '?')} {p.get('direction', '?')} @ {p.get('entry', '?')} "
                f"SL {p.get('sl', '?')} TP1 {p.get('tp1', '?')} "
                f"[{p.get('verdict', '?')} | conf {p.get('confidence', '?'):.0f}%]."
            )
        case EpisodeType.SIGNAL_REJECTED:
            return (
                f"Signal REJECTED: {p.get('source', '?')} {p.get('direction', '?')} — "
                f"reason: {p.get('rejection_reason', '?')}."
            )
        case EpisodeType.TP1_HIT:
            return f"TP1 hit (+1R). SL moved to breakeven. Holding for TP2."
        case EpisodeType.TP2_HIT:
            return f"TP2 hit (+1.5R). 50% closed. Hunting TP3."
        case EpisodeType.TP3_HIT:
            return f"TP3 hit (+2R). Holder mode armed — trailing via VWAP."
        case EpisodeType.SL_HIT:
            autopsy = p.get("autopsy_tag", "UNKNOWN")
            return f"SL hit. Autopsy: {autopsy}. MAE was {p.get('mae_pips', '?'):.1f} pips."
        case EpisodeType.HOLDER_EXIT:
            return (
                f"Holder exit — VWAP crossed. "
                f"Final R: {p.get('realized_r', '?'):.2f}. "
                f"Peak: {p.get('peak_pips', '?'):.1f} pips."
            )
        case EpisodeType.TRADE_CLOSED:
            return (
                f"Trade closed: {p.get('exit_reason', '?')} "
                f"{p.get('realized_r', '?'):.2f}R "
                f"({p.get('bar_count', '?')} bars). "
                f"MFE {p.get('mfe_r', '?'):.2f}R / MAE {p.get('mae_r', '?'):.2f}R."
            )
        case EpisodeType.CLAUDE_VERDICT:
            return (
                f"Claude: {p.get('verdict', '?')} — {p.get('reasoning', '')[:80]}..."
            )
        case EpisodeType.DAILY_ASSESSMENT:
            return f"Daily self-assessment: {p.get('summary', '')[:80]}..."
        case EpisodeType.PROPOSAL:
            return f"Proposal: {p.get('description', '')[:80]}..."
        case _:
            return f"{ep.episode_type}: {str(p)[:80]}"
