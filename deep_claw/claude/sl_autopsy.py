"""
SL Autopsy — Claude reads the episode chain leading to a stop-out
and generates a lesson narrative.

This is not a post-hoc excuse generator.
Claude reads the actual chain, identifies what was knowable before entry,
and writes a concrete, actionable lesson stored in the journal.
"""
from __future__ import annotations

import logging

import anthropic

from deep_claw.config.settings import settings
from deep_claw.core.types import AutopsyTag, Episode, EpisodeType, MarketState
from deep_claw.journal.episode_stream import EpisodeStream

log = logging.getLogger(__name__)

_AUTOPSY_PROMPT = """You are a senior trading mentor reviewing a stopped-out trade for Deep Claw.
Your job: read the episode chain and the stop-loss autopsy tag, then write a single concrete lesson.

Not "be more careful." Something specific like:
- "This setup had a VWAP sweep 3 episodes before entry — that was a regime warning sign. Next time, wait 1 bar post-sweep for reversal confirmation before entering."
- "ATR was in LOW regime 4 episodes before entry and climbed to MED. The SL distance was sized for HIGH ATR. Widen SL by 1.5x when entering on ATR regime transition."

=== AUTOPSY TAG (automated root-cause) ===
{autopsy_tag}

=== EPISODE CHAIN (what the system saw) ===
{chain}

=== SL HIT DETAILS ===
{sl_details}

Write your lesson in 2-3 sentences. Be specific. Reference the episode chain evidence.
"""


async def run_sl_autopsy(
    sl_episode: Episode,
    market_state: MarketState,
    stream: EpisodeStream,
) -> str:
    """
    Generate a lesson narrative from the episode chain leading to a SL hit.
    Appended to the journal as a PROPOSAL episode.
    """
    autopsy_tag = sl_episode.payload.get("autopsy_tag", "UNKNOWN")
    chain_narrative = stream.render_narrative(sl_episode.symbol, n=15)

    sl_details = (
        f"Trade ID  : {sl_episode.payload.get('trade_id', '?')}\n"
        f"Source    : {sl_episode.payload.get('signal_source', '?')}\n"
        f"Direction : {sl_episode.payload.get('direction', '?') if 'direction' in sl_episode.payload else '?'}\n"
        f"Entry     : {sl_episode.payload.get('entry', '?')}\n"
        f"SL level  : {sl_episode.payload.get('sl_at_entry', '?')}\n"
        f"MAE       : {sl_episode.payload.get('mae_pips', '?'):.1f} pips\n"
        f"Conf@entry: {sl_episode.payload.get('confidence_at_entry', '?'):.0f}%\n"
        f"Realized R: {sl_episode.payload.get('realized_r', '?'):.2f}R"
    )

    if not settings.anthropic_api_key:
        lesson = f"[Autopsy: {autopsy_tag}] Claude API not configured — manual review required."
        _append_autopsy(stream, sl_episode, lesson)
        return lesson

    prompt = _AUTOPSY_PROMPT.format(
        autopsy_tag=autopsy_tag,
        chain=chain_narrative,
        sl_details=sl_details,
    )

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    try:
        message = client.messages.create(
            model=settings.claude_model_autopsy,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        lesson = message.content[0].text.strip()
    except Exception as e:
        log.warning("SL autopsy API error: %s", e)
        lesson = f"[Autopsy: {autopsy_tag}] API error — see chain for manual review."

    _append_autopsy(stream, sl_episode, lesson)
    log.info("SL autopsy generated for %s: %s...", sl_episode.payload.get("trade_id"), lesson[:60])
    return lesson


def _append_autopsy(stream: EpisodeStream, sl_episode: Episode, lesson: str) -> None:
    import datetime
    ep = Episode(
        episode_type=EpisodeType.PROPOSAL,
        symbol=sl_episode.symbol,
        timestamp=datetime.datetime.now(datetime.timezone.utc),
        payload={
            "type": "SL_AUTOPSY",
            "trade_id": sl_episode.payload.get("trade_id"),
            "autopsy_tag": sl_episode.payload.get("autopsy_tag"),
            "description": lesson,
            "auto_apply": False,
        },
    )
    stream.append(ep)
