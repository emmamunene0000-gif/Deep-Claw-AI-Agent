"""
EpisodeStream Renderer — one source, four output formats.

Dashboard timeline, Telegram narrative, Claude context, daily summary
all flow from the same EpisodeStream. No separate per-consumer data paths.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from deep_claw.core.types import ChainVerdict, Episode, EpisodeType, MarketState, SignalCandidate
from deep_claw.journal.episode_stream import EpisodeStream, _episode_to_line


class EpisodeStreamRenderer:

    def __init__(self, stream: EpisodeStream) -> None:
        self._stream = stream

    # ── 1. Telegram war-room narrative ───────────────────────────────────────

    def to_telegram_narrative(
        self,
        symbol: str,
        event_title: str,
        event_commentary: str,
        market_state: MarketState | None = None,
        n: int = 15,
    ) -> str:
        """
        Full Glass Box War Room message.
        Chain narrative replaces the old tree-table format.
        Structure from cheatsheet §5.2 — narrative content from EpisodeStream.
        """
        chain = self._stream.render_narrative(symbol, n)
        ms = market_state

        header = (
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "DEEP CLAW — WAR ROOM\n"
            "━━━━━━━━━━━━━━━━━━━━━━"
        )

        context_block = f"Asset: {symbol}"
        if ms:
            context_block = (
                f"Asset   : {symbol}\n"
                f"Price   : {ms.close:.5f}\n"
                f"Session : {ms.session.value}\n"
                f"ATR     : {ms.atr_regime.value} ({ms.atr:.5f})\n"
                f"Daily   : {ms.pdh_pdl_status.value}\n"
                f"Score   : {ms.total_score:+.1f} | {ms.master_bias}"
            )

        narrative = (
            "─────────────────────\n"
            f"EVENT: {event_title}\n"
            "─────────────────────\n"
            f"{event_commentary}\n"
            "─────────────────────\n"
            "EPISODE CHAIN\n"
            "─────────────────────\n"
            f"{chain}"
        )

        footer = (
            "─────────────────────\n"
            "Not financial advice."
        )

        return f"{header}\n{context_block}\n{narrative}\n{footer}"

    def to_telegram_public(self, war_room_msg: str) -> str:
        """Sanitized version — strips the episode chain, keeps event + bias."""
        from deep_claw.config.settings import settings
        if not settings.tg_public_sanitize:
            return war_room_msg
        lines = war_room_msg.split("\n")
        # Keep header, context block, event line, drop chain
        kept = []
        in_chain = False
        for line in lines:
            if "EPISODE CHAIN" in line:
                in_chain = True
                continue
            if in_chain and line.startswith("─"):
                in_chain = False
                continue
            if not in_chain:
                kept.append(line)
        kept.append("Full Glass Box report in War Room.")
        return "\n".join(kept)

    # ── 2. Dashboard timeline ─────────────────────────────────────────────────

    def to_dashboard_timeline(self, symbol: str, n: int = 50) -> list[dict[str, Any]]:
        """
        Structured JSON for dashboard UI consumption.
        Each episode becomes one timeline entry.
        """
        episodes = self._stream.recent(symbol, n)
        return [
            {
                "id": ep.episode_id,
                "type": ep.episode_type.value,
                "symbol": ep.symbol,
                "timestamp": ep.timestamp.isoformat(),
                "summary": _episode_to_line(ep),
                "payload": ep.payload,
            }
            for ep in episodes
        ]

    # ── 3. Claude context (the key format — narrative, not table) ────────────

    def to_claude_context(
        self,
        symbol: str,
        market_state: MarketState,
        chain_verdict: ChainVerdict,
        candidate: SignalCandidate,
        n: int = 20,
    ) -> str:
        """
        Prose briefing for Claude qualification calls.
        Claude reads a story, not a table.
        This is what makes Claude's role 'narrative judgment', not 'table-reading'.
        """
        chain = self._stream.render_narrative(symbol, n)
        ms = market_state

        context = f"""You are the senior desk manager for Deep Claw trading intelligence.
A signal candidate has cleared the automated threshold and needs your narrative judgment.
Your job: APPROVE, REJECT, or MODIFY (with reasoning and any adjustments).

=== CURRENT MARKET CONTEXT ===
Symbol   : {symbol}
Timestamp: {ms.timestamp.strftime('%Y-%m-%d %H:%M UTC')}
Session  : {ms.session.value} (London-NY overlap = highest-edge window)
Price    : {ms.close:.5f}
ATR      : {ms.atr:.5f} [{ms.atr_regime.value}]
Score    : {ms.total_score:+.1f}/15 — {ms.master_bias}
PDH/PDL  : {ms.pdh_pdl_status.value}

=== WHAT THE CHAIN SAW ===
{chain}

=== SIGNAL BEING EVALUATED ===
Source   : {candidate.source.value}
Direction: {candidate.direction.value}
Entry    : ~{ms.close:.5f}
SL       : {candidate.proposed_sl:.5f}
TP1      : {candidate.proposed_tp1:.5f} (+1R)
TP2      : {candidate.proposed_tp2:.5f} (+1.5R)
TP3      : {candidate.proposed_tp3:.5f} (+2R)

=== AUTOMATED CHAIN VERDICT ===
Verdict      : {chain_verdict.verdict.value}
Restrictions : {', '.join(r.value for r in chain_verdict.restrictions) or 'none'}
Causal trace : {chain_verdict.causal_trace}
{f'Episodic note: {chain_verdict.episodic_note}' if chain_verdict.episodic_note else ''}

=== YOUR VERDICT ===
Respond in exactly this format:
VERDICT: [APPROVE|REJECT|MODIFY]
DIRECTION: [LONG|SHORT|unchanged]
SIZE_MODIFIER: [0.5|1.0|1.5|unchanged]
SL_MODIFIER: [e.g. 1.2 to widen 20%, or unchanged]
REASONING: [one paragraph — read the chain, trust your judgment]
"""
        return context

    # ── 4. Daily summary ──────────────────────────────────────────────────────

    def to_daily_summary(self, symbol: str, since: datetime) -> str:
        """
        Full-day episode stream summary for Claude daily self-assessment.
        """
        episodes = self._stream.query(symbol, since=since)
        if not episodes:
            return f"No episodes for {symbol} since {since.isoformat()}."

        trades = [ep for ep in episodes if ep.episode_type == EpisodeType.TRADE_CLOSED]
        sl_hits = [ep for ep in episodes if ep.episode_type == EpisodeType.SL_HIT]
        signals = [ep for ep in episodes if ep.episode_type in (EpisodeType.SIGNAL_ACCEPTED, EpisodeType.SIGNAL_REJECTED)]
        accepted = [ep for ep in signals if ep.episode_type == EpisodeType.SIGNAL_ACCEPTED]
        rejected = [ep for ep in signals if ep.episode_type == EpisodeType.SIGNAL_REJECTED]

        total_r = sum(ep.payload.get("realized_r", 0.0) for ep in trades)
        win_r = [ep.payload.get("realized_r", 0.0) for ep in trades if ep.payload.get("realized_r", 0.0) > 0]

        summary = f"""=== DAILY SESSION SUMMARY — {symbol} ===
Date     : {since.strftime('%Y-%m-%d')}
Signals  : {len(accepted)} accepted / {len(rejected)} rejected (shadow-blocked)
Trades   : {len(trades)} closed
SL hits  : {len(sl_hits)}
Win rate : {len(win_r)/len(trades)*100:.0f}% ({len(win_r)}/{len(trades)})
Total R  : {total_r:+.2f}R

=== FULL EPISODE CHAIN ===
"""
        for ep in episodes:
            ts = ep.timestamp.strftime("%H:%M")
            summary += f"{ts}  {_episode_to_line(ep)}\n"

        return summary
