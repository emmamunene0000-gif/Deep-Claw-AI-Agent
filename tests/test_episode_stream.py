"""
Tests for EpisodeStream — the spine.
Verifies append-only integrity, query, and narrative rendering.
"""
from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path

from deep_claw.core.types import Episode, EpisodeType
from deep_claw.journal.episode_stream import EpisodeStream


def _stream(tmp_path: Path) -> EpisodeStream:
    return EpisodeStream(db_path=tmp_path / "test.db")


def test_append_and_query(tmp_path):
    s = _stream(tmp_path)
    ep = Episode(
        episode_type=EpisodeType.SESSION_CHANGE,
        symbol="EURUSD",
        timestamp=datetime.now(timezone.utc),
        payload={"session": "LONDON", "prev": None},
    )
    s.append(ep)
    results = s.query("EURUSD")
    assert len(results) == 1
    assert results[0].episode_type == EpisodeType.SESSION_CHANGE
    assert results[0].payload["session"] == "LONDON"


def test_query_by_type(tmp_path):
    s = _stream(tmp_path)
    now = datetime.now(timezone.utc)
    s.append(Episode(EpisodeType.SESSION_CHANGE, "BTCUSDT", now, {}))
    s.append(Episode(EpisodeType.SL_HIT, "BTCUSDT", now, {"exit_reason": "SL"}))
    s.append(Episode(EpisodeType.TP1_HIT, "BTCUSDT", now, {}))

    sl_only = s.query("BTCUSDT", episode_types=[EpisodeType.SL_HIT])
    assert len(sl_only) == 1
    assert sl_only[0].episode_type == EpisodeType.SL_HIT


def test_recent(tmp_path):
    s = _stream(tmp_path)
    from datetime import timedelta
    base = datetime.now(timezone.utc)
    for i in range(10):
        # Distinct timestamps so ordering is deterministic
        ts = base + timedelta(minutes=i)
        s.append(Episode(EpisodeType.REGIME_FLIP, "XAUUSD", ts, {"i": i}))

    recent = s.recent("XAUUSD", n=5)
    assert len(recent) == 5
    # Should be in chronological order (oldest first among the last 5)
    assert recent[0].payload["i"] == 5  # oldest of the last 5
    assert recent[-1].payload["i"] == 9  # most recent


def test_narrative_renders_without_error(tmp_path):
    s = _stream(tmp_path)
    now = datetime.now(timezone.utc)
    s.append(Episode(EpisodeType.SESSION_CHANGE, "VOLATILITY_75_INDEX", now, {"session": "LONDON", "prev": "TOKYO"}))
    s.append(Episode(EpisodeType.SIGNAL_ACCEPTED, "VOLATILITY_75_INDEX", now, {
        "source": "UT_BOT", "direction": "LONG", "entry": 1234.5,
        "sl": 1230.0, "tp1": 1239.0, "verdict": "SYNC4", "confidence": 75.0,
    }))
    s.append(Episode(EpisodeType.TP1_HIT, "VOLATILITY_75_INDEX", now, {}))

    narrative = s.render_narrative("VOLATILITY_75_INDEX", n=10)
    assert "VOLATILITY_75_INDEX" in narrative
    assert "Session:" in narrative or "Signal ACCEPTED" in narrative
    assert "TP1 hit" in narrative


def test_no_cross_symbol_contamination(tmp_path):
    s = _stream(tmp_path)
    now = datetime.now(timezone.utc)
    s.append(Episode(EpisodeType.SL_HIT, "BTCUSDT", now, {}))
    s.append(Episode(EpisodeType.TP1_HIT, "ETHUSDT", now, {}))

    btc = s.query("BTCUSDT")
    eth = s.query("ETHUSDT")
    assert len(btc) == 1 and btc[0].episode_type == EpisodeType.SL_HIT
    assert len(eth) == 1 and eth[0].episode_type == EpisodeType.TP1_HIT
