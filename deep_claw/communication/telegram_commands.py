"""
Deep Claw Jarvis — Telegram command center.

Long-polling bot: you send a command from your phone → Jarvis queries the
orchestrator → replies with live system state.

Only responds to TG_WARROOM_CHAT_ID (your private group). All other senders
are silently ignored — the war room is secure.

Commands
────────
/start          Wake Jarvis, print greeting
/status         System health, uptime, mode, paused state
/positions      All open positions with entry / SL / TP / size
/explain        Last Claude reasoning chain
/report         Today's trading stats
/risk           Risk exposure and signal counts
/pause          Halt new signals (SL/TP management still runs)
/resume         Resume signal evaluation
/confidence N   Change confidence threshold live (0–100)
/help           This list
"""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

import httpx

from deep_claw.config.settings import settings

if TYPE_CHECKING:
    from deep_claw.orchestrator import Orchestrator

log = logging.getLogger(__name__)

_TG_BASE = "https://api.telegram.org/bot{token}"
_POLL_TIMEOUT = 30  # seconds for long-polling


class TelegramCommandCenter:
    """
    Jarvis interface. Polls Telegram getUpdates and routes commands.
    Run as a background asyncio.Task alongside the main feed loop.
    """

    def __init__(self, token: str, orchestrator: "Orchestrator") -> None:
        self._token = token
        self._orch = orchestrator
        self._authorized_chat = str(settings.tg_warroom_chat_id).strip()
        self._last_update_id = 0
        self._running = False

    async def start(self) -> None:
        if not self._token:
            log.info("TelegramCommandCenter: no token — Jarvis commands disabled")
            return
        self._running = True
        log.info("Jarvis command center active (long-polling)")
        while self._running:
            try:
                await self._poll_once()
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.warning("TelegramCommandCenter poll error: %s", e)
                await asyncio.sleep(5)

    async def stop(self) -> None:
        self._running = False

    async def _poll_once(self) -> None:
        url = f"{_TG_BASE.format(token=self._token)}/getUpdates"
        params = {
            "offset": self._last_update_id + 1,
            "timeout": _POLL_TIMEOUT,
            "allowed_updates": ["message"],
        }
        async with httpx.AsyncClient(timeout=_POLL_TIMEOUT + 10) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        for update in data.get("result", []):
            self._last_update_id = max(self._last_update_id, update["update_id"])
            await self._handle_update(update)

    async def _handle_update(self, update: dict) -> None:
        message = update.get("message", {})
        chat_id = str(message.get("chat", {}).get("id", ""))
        text = (message.get("text") or "").strip()

        if not text.startswith("/"):
            return

        # Security: only respond to the configured war room
        if self._authorized_chat and chat_id != self._authorized_chat:
            log.warning("Jarvis: rejected command from unauthorized chat_id=%s", chat_id)
            return

        parts = text.split()
        cmd = parts[0].lower().split("@")[0]  # strip @BotName suffix

        try:
            if cmd == "/start":
                await self._reply(chat_id, _greeting())
            elif cmd == "/help":
                await self._reply(chat_id, _help_text())
            elif cmd == "/status":
                await self._cmd_status(chat_id)
            elif cmd == "/positions":
                await self._cmd_positions(chat_id)
            elif cmd == "/explain":
                await self._cmd_explain(chat_id)
            elif cmd == "/report":
                await self._cmd_report(chat_id)
            elif cmd == "/risk":
                await self._cmd_risk(chat_id)
            elif cmd == "/pause":
                await self._cmd_pause(chat_id)
            elif cmd == "/resume":
                await self._cmd_resume(chat_id)
            elif cmd == "/confidence":
                await self._cmd_confidence(chat_id, parts[1] if len(parts) > 1 else "")
            else:
                await self._reply(chat_id, f"Unknown: {cmd}\n/help for commands.")
        except Exception as e:
            log.error("Jarvis command error [%s]: %s", cmd, e)
            await self._reply(chat_id, f"⚠ Error: {e}")

    # ── Command handlers ──────────────────────────────────────────────────────

    async def _cmd_status(self, chat_id: str) -> None:
        s = self._orch.get_status()
        lines = [
            "<b>🤖 DEEP CLAW STATUS</b>",
            f"Mode:        <code>{'DEMO' if settings.bybit_testnet else '⚠ LIVE'}</code>",
            f"State:       <code>{'⏸ PAUSED' if s['paused'] else '▶ RUNNING'}</code>",
            f"Symbols:     <code>{', '.join(s['symbols'])}</code>",
            f"Uptime:      <code>{s['uptime']}</code>",
            f"M15 bars:    <code>{s['bars_processed']}</code>",
            f"Open trades: <code>{s['open_positions']}</code>",
            f"Claude gate: <code>{'ON' if settings.enable_claude_qualification else 'OFF'}</code>",
            f"ML conf:     <code>{'ON' if settings.use_ml_confidence else 'OFF (Phase 1)'}</code>",
            f"Threshold:   <code>{settings.confidence_threshold:.0f}%</code>",
        ]
        await self._reply(chat_id, "\n".join(lines))

    async def _cmd_positions(self, chat_id: str) -> None:
        positions = self._orch.get_open_positions()
        if not positions:
            await self._reply(chat_id, "📭 No open positions.")
            return
        lines = ["<b>📈 OPEN POSITIONS</b>"]
        for p in positions:
            lines.append(
                f"\n<b>{p['symbol']}</b> — {p['direction']}\n"
                f"  Entry:   <code>{p['entry']:.5f}</code>\n"
                f"  SL:      <code>{p['sl']:.5f}</code>\n"
                f"  TP1:     <code>{p['tp1']:.5f}</code>\n"
                f"  Size:    <code>${p['size_usd']:.2f} risk</code>\n"
                f"  ID:      <code>{p['trade_id']}</code>"
            )
        await self._reply(chat_id, "\n".join(lines))

    async def _cmd_explain(self, chat_id: str) -> None:
        reasoning = self._orch.get_last_reasoning()
        if not reasoning:
            await self._reply(chat_id, "📭 No reasoning on record yet. Wait for the next M15 signal.")
            return
        await self._reply(chat_id, f"<b>🧠 LAST CLAUDE REASONING</b>\n\n{reasoning[:3800]}")

    async def _cmd_report(self, chat_id: str) -> None:
        report = self._orch.get_today_summary()
        await self._reply(chat_id, f"<b>📊 TODAY'S REPORT</b>\n\n{report}")

    async def _cmd_risk(self, chat_id: str) -> None:
        r = self._orch.get_risk_exposure()
        lines = [
            "<b>⚖ RISK EXPOSURE</b>",
            f"Risk/trade:      <code>${settings.risk_per_trade_usd:.2f}</code>",
            f"Max equity risk: <code>{settings.max_equity_risk_pct * 100:.1f}%</code>",
            f"Threshold:       <code>{settings.confidence_threshold:.0f}%</code>",
            f"Trades today:    <code>{r['daily_trades']}</code>",
            f"Signals fired:   <code>{r['signals_fired']}</code>",
            f"Signals blocked: <code>{r['signals_blocked']}</code>",
        ]
        await self._reply(chat_id, "\n".join(lines))

    async def _cmd_pause(self, chat_id: str) -> None:
        self._orch.pause()
        await self._reply(
            chat_id,
            "⏸ <b>SIGNAL EVALUATION PAUSED</b>\n\n"
            "No new trades will be opened.\n"
            "Existing positions still managed (SL/TP).\n\n"
            "Send /resume to restart."
        )

    async def _cmd_resume(self, chat_id: str) -> None:
        self._orch.resume()
        await self._reply(
            chat_id,
            f"▶ <b>SIGNAL EVALUATION RESUMED</b>\n\n"
            f"Confidence threshold: <code>{settings.confidence_threshold:.0f}%</code>\n"
            "Next evaluation at next M15 bar close."
        )

    async def _cmd_confidence(self, chat_id: str, value_str: str) -> None:
        if not value_str:
            await self._reply(chat_id, "Usage: /confidence 70\nCurrent: "
                              f"<code>{settings.confidence_threshold:.0f}%</code>")
            return
        try:
            value = float(value_str)
            if not 0 <= value <= 100:
                raise ValueError("must be 0–100")
        except ValueError as e:
            await self._reply(chat_id, f"⚠ Invalid: {e}")
            return
        old = settings.confidence_threshold
        settings.confidence_threshold = value
        await self._reply(
            chat_id,
            f"✅ Confidence threshold: <code>{old:.0f}%</code> → <code>{value:.0f}%</code>\n"
            "Takes effect at next M15 bar close."
        )

    # ── HTTP ──────────────────────────────────────────────────────────────────

    async def _reply(self, chat_id: str, text: str) -> None:
        url = f"{_TG_BASE.format(token=self._token)}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text[:4096],
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
        except Exception as e:
            log.warning("Jarvis reply failed [chat=%s]: %s", chat_id, e)


# ── Static text ───────────────────────────────────────────────────────────────

def _greeting() -> str:
    return (
        "🤖 <b>JARVIS ONLINE — DEEP CLAW COMMAND CENTER</b>\n\n"
        "I watch every market structure shift.\n"
        "I reason through every signal.\n"
        "I execute with precision.\n\n"
        "You command from here. I execute out there.\n\n"
        "Send /help for the full command list."
    )


def _help_text() -> str:
    return (
        "<b>DEEP CLAW — COMMAND REFERENCE</b>\n\n"
        "<b>Intel</b>\n"
        "/status        — system health &amp; uptime\n"
        "/positions     — open trades\n"
        "/explain       — last Claude reasoning chain\n"
        "/report        — today's P&amp;L summary\n"
        "/risk          — risk exposure &amp; signal counts\n\n"
        "<b>Control</b>\n"
        "/pause         — halt new signals (positions managed)\n"
        "/resume        — restart signal evaluation\n"
        "/confidence N  — set threshold e.g. /confidence 70\n\n"
        "/help          — this list"
    )
