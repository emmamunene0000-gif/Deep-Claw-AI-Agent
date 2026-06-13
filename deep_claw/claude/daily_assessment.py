"""
Daily Self-Assessment — Claude reads the full day's episode stream
and proposes parameter adjustments.

Proposals are logged to the journal but NEVER auto-applied.
The human reviews them. In Phase 3, the ML model takes over this role.
This is the 'self-awareness' component of the name.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import anthropic

from deep_claw.config.settings import settings
from deep_claw.core.types import Episode, EpisodeType
from deep_claw.journal.episode_stream import EpisodeStream

log = logging.getLogger(__name__)

_ASSESSMENT_PROMPT = """You are the strategic advisor for Deep Claw, a synthetic trading intelligence.
Review today's complete trading session and identify 2-3 concrete, actionable parameter adjustments.

Focus on:
1. CONFIDENCE THRESHOLD: Was it too low (many SL hits, low avg confidence at entry)?
   Or too high (missed clear setups, few signals)?
2. SESSION TIMING: Were signals in certain sessions (Tokyo/London/Overlap/NY) performing worse?
3. WEIGHT MATRIX: Which confidence factors over- or under-predicted outcomes?
   (look at breakdown in SIGNAL_ACCEPTED payloads vs realized_r in TRADE_CLOSED payloads)
4. SL DISTANCES: Were stops too tight (SL hit, then price reversed) or too wide (unnecessary risk)?

Your proposals must be specific (e.g. "Increase CONFIDENCE_THRESHOLD from 60 to 68 for TOKYO session")
NOT generic (e.g. "be more selective").

=== TODAY'S SESSION SUMMARY ===
{summary}

Write exactly 3 proposals in this format:
PROPOSAL 1: [parameter] [change] [reason based on evidence in the chain]
PROPOSAL 2: [parameter] [change] [reason]
PROPOSAL 3: [parameter] [change] [reason]

Then: OVERALL: [1-2 sentence session assessment]
"""


async def run_daily_assessment(
    symbol: str,
    since: datetime,
    stream: EpisodeStream,
    renderer,  # EpisodeStreamRenderer — avoid circular import
) -> list[str]:
    """
    Generate daily self-assessment proposals.
    Returns list of proposal strings (also appended to the stream).
    """
    summary = renderer.to_daily_summary(symbol, since)

    if not settings.anthropic_api_key:
        log.info("Daily assessment skipped — no API key")
        return ["Claude API not configured — manual assessment required."]

    prompt = _ASSESSMENT_PROMPT.format(summary=summary)

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    try:
        message = client.messages.create(
            model=settings.claude_model_assessment,
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
    except Exception as e:
        log.warning("Daily assessment API error: %s", e)
        return [f"API error: {e}"]

    proposals = _parse_proposals(raw)
    overall = _extract_overall(raw)

    # Write each proposal as a PROPOSAL episode (never auto-applied)
    now = datetime.now(timezone.utc)
    for i, proposal in enumerate(proposals):
        ep = Episode(
            episode_type=EpisodeType.PROPOSAL,
            symbol=symbol,
            timestamp=now,
            payload={
                "type": "DAILY_ASSESSMENT",
                "index": i + 1,
                "description": proposal,
                "auto_apply": False,
                "session_date": since.date().isoformat(),
            },
        )
        stream.append(ep)

    # Write overall assessment
    ep = Episode(
        episode_type=EpisodeType.DAILY_ASSESSMENT,
        symbol=symbol,
        timestamp=now,
        payload={
            "summary": overall,
            "proposal_count": len(proposals),
            "session_date": since.date().isoformat(),
        },
    )
    stream.append(ep)

    log.info("Daily assessment complete for %s: %d proposals", symbol, len(proposals))
    return proposals


def _parse_proposals(raw: str) -> list[str]:
    proposals = []
    for line in raw.split("\n"):
        line = line.strip()
        if line.startswith("PROPOSAL"):
            _, _, text = line.partition(":")
            if text.strip():
                proposals.append(text.strip())
    return proposals if proposals else [raw[:200]]


def _extract_overall(raw: str) -> str:
    for line in raw.split("\n"):
        if line.strip().startswith("OVERALL:"):
            return line.partition(":")[2].strip()
    return raw[-200:] if len(raw) > 200 else raw
