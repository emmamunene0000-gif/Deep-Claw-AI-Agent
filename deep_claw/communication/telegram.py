"""
Telegram dispatcher — War Room (private) and Public channels.

War Room: full Glass Box narrative, chain, confidence breakdown, proposal alerts.
Public: sanitized (no confidence numbers, no SL distances, no entry prices).

Rate limit: Telegram allows ~30 msgs/sec per bot. We cap at 1/sec via _last_sent.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

import httpx

from deep_claw.config.settings import settings

log = logging.getLogger(__name__)

_TG_API = "https://api.telegram.org/bot{token}/sendMessage"
_RATE_LIMIT_SECONDS = 1.1  # safe margin above Telegram's 1/sec per chat limit


@dataclass
class TelegramChannel:
    token: str
    chat_id: str
    _last_sent: float = 0.0

    async def send(self, text: str, parse_mode: str = "HTML") -> bool:
        if not self.token or not self.chat_id:
            return False
        # rate-limit
        elapsed = time.monotonic() - self._last_sent
        if elapsed < _RATE_LIMIT_SECONDS:
            await asyncio.sleep(_RATE_LIMIT_SECONDS - elapsed)
        url = _TG_API.format(token=self.token)
        payload = {
            "chat_id": self.chat_id,
            "text": text[:4096],  # Telegram hard limit
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
            self._last_sent = time.monotonic()
            return True
        except httpx.HTTPStatusError as e:
            log.warning("Telegram HTTP error [%s]: %s", e.response.status_code, e.response.text[:200])
        except Exception as e:
            log.warning("Telegram send error: %s", e)
        return False


class TelegramDispatcher:
    """
    Two-channel dispatcher.
    `war_room` = full narrative for the operator.
    `public` = sanitized version if enabled.
    """

    def __init__(self) -> None:
        self._war_room = TelegramChannel(
            token=settings.tg_warroom_token,
            chat_id=settings.tg_warroom_chat_id,
        )
        self._public = TelegramChannel(
            token=settings.tg_public_token,
            chat_id=settings.tg_public_chat_id,
        )
        self._enabled = settings.enable_telegram

    async def send_war_room(self, text: str) -> bool:
        if not self._enabled:
            log.debug("Telegram disabled — war room message suppressed")
            return False
        return await self._war_room.send(text)

    async def send_public(self, text: str) -> bool:
        if not self._enabled or not settings.tg_public_sanitize:
            return False
        if not self._public.token:
            return False
        return await self._public.send(text)

    async def send_signal_alert(
        self,
        war_room_narrative: str,
        public_narrative: str | None = None,
    ) -> None:
        """Send a signal event to both channels."""
        tasks = [self.send_war_room(war_room_narrative)]
        if public_narrative:
            tasks.append(self.send_public(public_narrative))
        await asyncio.gather(*tasks, return_exceptions=True)

    async def send_proposal_alert(self, symbol: str, proposals: list[str]) -> None:
        """EOD assessment proposals to war room only — never to public."""
        if not proposals:
            return
        lines = [f"<b>📋 EOD PROPOSALS — {symbol}</b>"]
        for i, p in enumerate(proposals, 1):
            lines.append(f"{i}. {p}")
        lines.append("\n<i>Auto-apply: OFF — human review required.</i>")
        await self.send_war_room("\n".join(lines))

    async def send_sl_autopsy(self, symbol: str, trade_id: str, lesson: str) -> None:
        """SL autopsy lesson to war room only."""
        text = (
            f"<b>🔬 SL AUTOPSY — {symbol}</b>\n"
            f"Trade: <code>{trade_id}</code>\n\n"
            f"{lesson}"
        )
        await self.send_war_room(text)

    async def send_daily_summary(self, symbol: str, summary_text: str) -> None:
        """EOD stat block to war room."""
        header = f"<b>📊 DAILY SUMMARY — {symbol}</b>\n"
        await self.send_war_room(header + summary_text)

    async def send_error(self, context: str, error: str) -> None:
        """Critical error ping to war room."""
        text = f"<b>⚠ DEEP CLAW ERROR</b>\n<code>{context}</code>\n{error[:500]}"
        await self.send_war_room(text)
