"""
Feature Store — one row per SignalCandidate event (accepted AND shadow-blocked).

This is the training data foundation.
Shadow-blocked candidates (rejected) are EQUALLY important as accepted ones.
ONE_TRADE_RULE and CONFIDENCE_TOO_LOW are different features — never conflated.
The outcome_labeler will join labels back via candidate_id/trade_id after close.

SQLite-backed, like EpisodeStream. Separate DB for cleaner separation.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

from deep_claw.core.types import ChainVerdict, ConfidenceResult, Direction, MarketState, SignalCandidate

_DEFAULT_DB_PATH = Path("data/feature_store.db")

_CREATE = """
CREATE TABLE IF NOT EXISTS features (
    row_id           TEXT PRIMARY KEY,
    candidate_id     TEXT NOT NULL,
    symbol           TEXT NOT NULL,
    timestamp        TEXT NOT NULL,
    bar_id           TEXT,

    -- Signal metadata
    signal_source    TEXT NOT NULL,
    direction        TEXT NOT NULL,
    fired            INTEGER NOT NULL,     -- 1=accepted, 0=shadow-blocked
    rejection_reason TEXT,

    -- MarketState feature vector (flat)
    total_score      REAL,
    master_bias      TEXT,
    rsi              REAL,
    rsi_positive     INTEGER,
    rsi_negative     INTEGER,
    trail_exec_trend INTEGER,
    trail_m5_trend   INTEGER,
    trail_m15_trend  INTEGER,
    trail_h1_trend   INTEGER,
    vap_last_swing   INTEGER,
    vap_current      REAL,
    trend_fib        INTEGER,
    vp_strength      TEXT,
    poc              REAL,
    vah              REAL,
    val              REAL,
    smc_swing_bias   INTEGER,
    smc_latest_bos   INTEGER,
    smc_latest_choch INTEGER,
    smc_ph_top       REAL,
    smc_pl_btm       REAL,
    smc_fvg_bull     INTEGER,
    smc_fvg_bear     INTEGER,
    atr              REAL,
    atr_regime       TEXT,
    session          TEXT,
    pdh_pdl_status   TEXT,
    pdh              REAL,
    pdl              REAL,

    -- Confidence at decision time
    bull_confidence  REAL,
    bear_confidence  REAL,
    directional_conf REAL,
    confidence_breakdown TEXT,  -- JSON

    -- Chain verdict
    chain_verdict    TEXT,
    restrictions     TEXT,  -- JSON list
    total_score_at_verdict REAL,
    causal_trace     TEXT,

    -- Outcome labels (NULL until trade closes — populated by outcome_labeler)
    trade_id         TEXT,
    realized_r       REAL,
    exit_reason      TEXT,
    bar_count        INTEGER,
    mfe_r            REAL,
    mae_r            REAL,
    autopsy_tag      TEXT,

    inserted_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_fs_symbol ON features(symbol, timestamp);
CREATE INDEX IF NOT EXISTS idx_fs_fired ON features(fired);
CREATE INDEX IF NOT EXISTS idx_fs_trade_id ON features(trade_id);
CREATE INDEX IF NOT EXISTS idx_fs_candidate ON features(candidate_id);
"""


class FeatureStore:

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

    # ── Write ─────────────────────────────────────────────────────────────────

    def write_candidate(
        self,
        candidate: SignalCandidate,
        market_state: MarketState,
        chain_verdict: ChainVerdict,
        confidence_result: ConfidenceResult,
        fired: bool,
        rejection_reason: str | None = None,
        trade_id: str | None = None,
    ) -> str:
        """Write one feature row. Returns the row_id."""
        import uuid
        row_id = str(uuid.uuid4())

        ms = market_state
        dir_conf = (
            confidence_result.bull_confidence
            if candidate.direction == Direction.LONG
            else confidence_result.bear_confidence
        )

        with self._conn() as conn:
            conn.execute("""
                INSERT INTO features VALUES (
                    ?,?,?,?,?,
                    ?,?,?,?,
                    ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,
                    ?,?,?,?,
                    ?,?,?,?,
                    ?,?,?,?,?,?,?,
                    ?
                )
            """, (
                row_id, candidate.candidate_id, candidate.symbol,
                candidate.timestamp.isoformat(), ms.bar_id,

                # Signal metadata
                candidate.source.value, candidate.direction.value,
                int(fired), rejection_reason,

                # MarketState features
                ms.total_score, ms.master_bias,
                ms.rsi, int(ms.rsi_regime_positive), int(ms.rsi_regime_negative),
                ms.trail_exec.trend, ms.trail_m5.trend, ms.trail_m15.trend, ms.trail_h1.trend,
                ms.last_swing, ms.vap_current,
                ms.trend_fib,
                ms.vp_strength.value,
                ms.poc, ms.vah, ms.val,
                ms.smc.swing_bias, ms.smc.latest_bos_direction, ms.smc.latest_choch_direction,
                ms.smc.ph_top, ms.smc.pl_btm,
                int(ms.smc.fvg_bull_active), int(ms.smc.fvg_bear_active),
                ms.atr, ms.atr_regime.value,
                ms.session.value, ms.pdh_pdl_status.value,
                ms.pdh, ms.pdl,

                # Confidence
                confidence_result.bull_confidence,
                confidence_result.bear_confidence,
                dir_conf,
                json.dumps(confidence_result.breakdown),

                # Chain verdict
                chain_verdict.verdict.value,
                json.dumps([r.value for r in chain_verdict.restrictions]),
                chain_verdict.total_score,
                chain_verdict.causal_trace[:500] if chain_verdict.causal_trace else None,

                # Outcome labels (NULL initially)
                trade_id, None, None, None, None, None, None,

                datetime.now(timezone.utc).isoformat(),
            ))

        return row_id

    def label_outcome(
        self,
        trade_id: str,
        realized_r: float,
        exit_reason: str,
        bar_count: int,
        mfe_r: float,
        mae_r: float,
        autopsy_tag: str | None,
    ) -> int:
        """
        Join outcome labels onto the accepted feature row for this trade_id.
        Returns number of rows updated (should be 1).
        """
        with self._conn() as conn:
            cur = conn.execute("""
                UPDATE features SET
                    realized_r = ?,
                    exit_reason = ?,
                    bar_count = ?,
                    mfe_r = ?,
                    mae_r = ?,
                    autopsy_tag = ?
                WHERE trade_id = ? AND fired = 1
            """, (realized_r, exit_reason, bar_count, mfe_r, mae_r, autopsy_tag, trade_id))
            return cur.rowcount

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_training_rows(
        self,
        symbol: str | None = None,
        labeled_only: bool = True,
        min_rows: int = 0,
    ) -> list[dict]:
        """Return rows suitable for ML training (labeled + unlabeled for semi-supervised)."""
        clauses = []
        params = []
        if symbol:
            clauses.append("symbol = ?")
            params.append(symbol)
        if labeled_only:
            clauses.append("realized_r IS NOT NULL")

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM features {where} ORDER BY timestamp ASC", params
            ).fetchall()

        return [dict(r) for r in rows]

    def get_shadow_blocked(self, symbol: str | None = None) -> list[dict]:
        """Return all shadow-blocked candidates. Used for counterfactual analysis."""
        clauses = ["fired = 0"]
        params: list = []
        if symbol:
            clauses.append("symbol = ?")
            params.append(symbol)
        with self._conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM features WHERE {' AND '.join(clauses)} ORDER BY timestamp ASC",
                params,
            ).fetchall()
        return [dict(r) for r in rows]

    def count(self, symbol: str | None = None) -> dict[str, int]:
        clauses = ["1=1"]
        params: list = []
        if symbol:
            clauses.append("symbol = ?")
            params.append(symbol)
        where = f"WHERE {' AND '.join(clauses)}"
        with self._conn() as conn:
            total = conn.execute(f"SELECT COUNT(*) FROM features {where}", params).fetchone()[0]
            labeled = conn.execute(
                f"SELECT COUNT(*) FROM features {where} AND realized_r IS NOT NULL", params
            ).fetchone()[0]
            fired = conn.execute(
                f"SELECT COUNT(*) FROM features {where} AND fired=1", params
            ).fetchone()[0]
        return {"total": total, "labeled": labeled, "fired": fired, "shadow": total - fired}
