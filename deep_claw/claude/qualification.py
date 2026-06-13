"""
Claude Qualification Layer — called at threshold-crossing moments.

Claude reads the episode chain as a story and returns APPROVE / REJECT / MODIFY.
This is narrative judgment, not indicator recalculation.
Claude is the 'junior analyst getting briefed by the chain', not a calculator.

Called BEFORE the trade is committed to the broker.
If Claude REJECTS → write SIGNAL_REJECTED episode with reason CLAUDE_REJECT.
If Claude MODIFIES → apply size/SL adjustments, then commit.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import anthropic

from deep_claw.communication.renderer import EpisodeStreamRenderer
from deep_claw.config.settings import settings
from deep_claw.core.types import (
    ChainVerdict,
    ClaudeVerdict,
    Direction,
    Episode,
    EpisodeType,
    MarketState,
    SignalCandidate,
)
from deep_claw.journal.episode_stream import EpisodeStream

log = logging.getLogger(__name__)


@dataclass
class QualificationVerdict:
    verdict: ClaudeVerdict
    direction: Direction | None    # None = unchanged
    size_modifier: float           # 1.0 = unchanged
    sl_modifier: float             # 1.0 = unchanged
    reasoning: str
    raw_response: str


async def qualify_signal(
    candidate: SignalCandidate,
    market_state: MarketState,
    chain_verdict: ChainVerdict,
    stream: EpisodeStream,
    renderer: EpisodeStreamRenderer,
) -> QualificationVerdict:
    """
    Call Claude with the rendered episode chain + signal candidate.
    Returns QualificationVerdict.

    If Claude API is unavailable or disabled, returns APPROVE with no modifications
    (the automated confidence + chain verdict already cleared the signal).
    """
    if not settings.enable_claude_qualification or not settings.anthropic_api_key:
        return QualificationVerdict(
            verdict=ClaudeVerdict.APPROVE,
            direction=None,
            size_modifier=1.0,
            sl_modifier=1.0,
            reasoning="Claude qualification disabled or no API key — auto-approved.",
            raw_response="",
        )

    context = renderer.to_claude_context(
        symbol=candidate.symbol,
        market_state=market_state,
        chain_verdict=chain_verdict,
        candidate=candidate,
        n=20,
    )

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    try:
        message = client.messages.create(
            model=settings.claude_model_qualification,
            max_tokens=512,
            messages=[{"role": "user", "content": context}],
        )
        raw = message.content[0].text
    except Exception as e:
        log.warning("Claude qualification API error: %s — auto-approving", e)
        return QualificationVerdict(
            verdict=ClaudeVerdict.APPROVE,
            direction=None,
            size_modifier=1.0,
            sl_modifier=1.0,
            reasoning=f"Claude API error ({e}) — auto-approved.",
            raw_response="",
        )

    verdict = _parse_qualification_response(raw, candidate.direction)

    # Log the Claude verdict as an episode
    ep = Episode(
        episode_type=EpisodeType.CLAUDE_VERDICT,
        symbol=candidate.symbol,
        timestamp=market_state.timestamp,
        payload={
            "candidate_id": candidate.candidate_id,
            "source": candidate.source.value,
            "direction": candidate.direction.value,
            "claude_verdict": verdict.verdict.value,
            "size_modifier": verdict.size_modifier,
            "sl_modifier": verdict.sl_modifier,
            "reasoning": verdict.reasoning[:500],
        },
        market_state_ref=market_state.bar_id,
    )
    stream.append(ep)

    log.info(
        "Claude qualification: %s signal %s → %s (size×%.1f, SL×%.1f) | %s",
        candidate.source.value, candidate.direction.value,
        verdict.verdict.value, verdict.size_modifier, verdict.sl_modifier,
        verdict.reasoning[:80],
    )

    return verdict


def _parse_qualification_response(raw: str, original_direction: Direction) -> QualificationVerdict:
    """Parse Claude's structured response. Lenient — fail safe to APPROVE."""
    lines = raw.strip().split("\n")
    fields: dict[str, str] = {}
    reasoning_lines: list[str] = []
    in_reasoning = False

    for line in lines:
        if line.startswith("REASONING:"):
            in_reasoning = True
            reasoning_lines.append(line[len("REASONING:"):].strip())
        elif in_reasoning:
            reasoning_lines.append(line)
        elif ":" in line:
            key, _, value = line.partition(":")
            fields[key.strip().upper()] = value.strip()

    # Verdict
    verdict_str = fields.get("VERDICT", "APPROVE").upper()
    if "REJECT" in verdict_str:
        verdict = ClaudeVerdict.REJECT
    elif "MODIFY" in verdict_str:
        verdict = ClaudeVerdict.MODIFY
    else:
        verdict = ClaudeVerdict.APPROVE

    # Direction
    dir_str = fields.get("DIRECTION", "unchanged").upper()
    if dir_str == "LONG":
        direction = Direction.LONG
    elif dir_str == "SHORT":
        direction = Direction.SHORT
    else:
        direction = None  # unchanged

    # Size modifier
    size_str = fields.get("SIZE_MODIFIER", "1.0").replace("unchanged", "1.0")
    try:
        size_modifier = float(size_str)
    except ValueError:
        size_modifier = 1.0

    # SL modifier
    sl_str = fields.get("SL_MODIFIER", "1.0").replace("unchanged", "1.0")
    try:
        sl_modifier = float(sl_str)
    except ValueError:
        sl_modifier = 1.0

    # Clamp modifiers to sane ranges
    size_modifier = max(0.25, min(2.0, size_modifier))
    sl_modifier = max(0.8, min(2.0, sl_modifier))

    reasoning = " ".join(reasoning_lines).strip() or raw[:200]

    return QualificationVerdict(
        verdict=verdict,
        direction=direction,
        size_modifier=size_modifier,
        sl_modifier=sl_modifier,
        reasoning=reasoning,
        raw_response=raw,
    )
