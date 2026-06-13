"""
Outcome Labeler — joins closed trade results back to feature store rows.

Listens for TRADE_CLOSED / SL_HIT / HOLDER_EXIT episodes and updates
the feature store row for that trade_id with the realized outcome.

This is the pipeline that makes the learning layer possible.
Labels come from the Position Manager's price-check logic — never from signal firing.
"""
from __future__ import annotations

import logging

from deep_claw.core.types import Episode, EpisodeType
from deep_claw.journal.episode_stream import EpisodeStream
from deep_claw.journal.feature_store import FeatureStore

log = logging.getLogger(__name__)

_OUTCOME_EPISODE_TYPES = {
    EpisodeType.SL_HIT,
    EpisodeType.HOLDER_EXIT,
    EpisodeType.TRADE_CLOSED,
}


class OutcomeLabeler:
    """
    Connects to the EpisodeStream and feature store.
    Called by the orchestrator whenever a trade-closing episode is written.
    """

    def __init__(self, stream: EpisodeStream, feature_store: FeatureStore) -> None:
        self._stream = stream
        self._feature_store = feature_store

    def process_episode(self, episode: Episode) -> bool:
        """
        If this episode closes a trade, update the feature store.
        Returns True if a label was written.
        """
        if episode.episode_type not in _OUTCOME_EPISODE_TYPES:
            return False

        payload = episode.payload
        trade_id = payload.get("trade_id")
        if not trade_id:
            return False

        realized_r = payload.get("realized_r")
        if realized_r is None:
            log.warning("TRADE_CLOSED episode missing realized_r: %s", trade_id)
            return False

        rows_updated = self._feature_store.label_outcome(
            trade_id=trade_id,
            realized_r=float(realized_r),
            exit_reason=payload.get("exit_reason", "UNKNOWN"),
            bar_count=int(payload.get("bar_count", 0)),
            mfe_r=float(payload.get("mfe_r", 0.0)),
            mae_r=float(payload.get("mae_r", 0.0)),
            autopsy_tag=payload.get("autopsy_tag"),
        )

        if rows_updated > 0:
            log.info(
                "Outcome labeled: trade=%s exit=%s R=%.2f (updated %d rows)",
                trade_id,
                payload.get("exit_reason"),
                realized_r,
                rows_updated,
            )
        else:
            log.warning("No feature row found for trade_id=%s — label dropped", trade_id)

        return rows_updated > 0

    def backfill_from_stream(self, symbol: str) -> int:
        """
        Backfill labels for all past closed trades in the stream.
        Useful on startup to catch any trades that closed while labeler was offline.
        """
        episodes = self._stream.query(
            symbol,
            episode_types=[EpisodeType.SL_HIT, EpisodeType.HOLDER_EXIT, EpisodeType.TRADE_CLOSED],
        )
        labeled = 0
        for ep in episodes:
            if self.process_episode(ep):
                labeled += 1
        log.info("Backfill complete for %s: %d labels written", symbol, labeled)
        return labeled
