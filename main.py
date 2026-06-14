"""
Deep Claw — main entry point.

Usage:
  python main.py                     # all configured symbols
  python main.py VOLATILITY_75_INDEX BTCUSDT   # specific symbols

Demo mode:
  Deriv: set DERIV_API_TOKEN in .env to your DEMO account token.
         Demo tokens look identical to live — different account type only.
  Bybit: set BYBIT_TESTNET=true in .env to use Bybit testnet.
  MT5:   connect to a demo server in MT5_SERVER.

The system boots, loads bar history from REST APIs, then switches to
live WebSocket streams. Signal evaluation starts as soon as 30+ confirmed
bars are available in each timeframe.
"""
from __future__ import annotations

import asyncio
import logging
import signal
import sys
from pathlib import Path

from deep_claw.config.settings import settings
from deep_claw.perception.candle_bus import NormalizedCandleBus


def _configure_logging() -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("data/deep_claw.log", mode="a"),
        ],
    )
    # Quiet noisy libraries
    for noisy in ("websockets", "httpx", "asyncio", "pybit"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def _resolve_symbols(argv: list[str]) -> list[str]:
    if len(argv) > 1:
        return [s.upper() for s in argv[1:]]
    # Default symbol set from cheatsheet §1.2 demo focus
    return ["VOLATILITY_75_INDEX", "BTCUSDT"]


async def main(symbols: list[str]) -> None:
    from deep_claw.cognition.risk.notional_router import get_instrument
    from deep_claw.feeds.bybit_feed import BybitFeed
    from deep_claw.feeds.deriv_feed import DerivFeed
    from deep_claw.orchestrator import Orchestrator

    log = logging.getLogger("deep_claw.main")
    Path("data").mkdir(exist_ok=True)

    # ── 1. Shared candle bus ─────────────────────────────────────────────────
    bus = NormalizedCandleBus()

    # ── 2. Broker adapters (demo/testnet) ────────────────────────────────────
    broker_adapters = _build_broker_adapters(symbols)

    # ── 3. Orchestrator ──────────────────────────────────────────────────────
    orch = Orchestrator(
        symbols=symbols,
        bus=bus,
        broker_adapters=broker_adapters,
        db_path=Path("data"),
    )

    # ── 4. Feeds (per symbol) ────────────────────────────────────────────────
    feeds = []
    for sym in symbols:
        try:
            inst = get_instrument(sym)
        except KeyError:
            log.warning("Unknown symbol %s — skipped", sym)
            continue

        if inst.preferred_venue == "deriv_multiplier" and inst.deriv_code:
            feed = DerivFeed(symbol=sym, deriv_code=inst.deriv_code, bus=bus)
            feeds.append(feed)
            log.info("DerivFeed registered: %s → %s", sym, inst.deriv_code)

        elif inst.preferred_venue == "bybit_perp" and inst.bybit_symbol:
            feed = BybitFeed(symbol=sym, bybit_symbol=inst.bybit_symbol, bus=bus)
            # Pre-load REST history (fills bus before live stream begins)
            log.info("BybitFeed loading history for %s...", sym)
            await feed.startup_history()
            feeds.append(feed)
            log.info("BybitFeed registered: %s → %s", sym, inst.bybit_symbol)

        elif inst.preferred_venue == "mt5_cfd":
            log.info("MT5 feed for %s — starts when MT5 bridge connects", sym)

    # ── 5. Startup ───────────────────────────────────────────────────────────
    await orch.startup()

    # ── 6. Dashboard (optional) ──────────────────────────────────────────────
    dashboard_task = None
    try:
        import uvicorn
        from deep_claw.communication.dashboard import build_app
        app = build_app(orch)
        config = uvicorn.Config(app, host="0.0.0.0", port=8080, log_level="warning")
        server = uvicorn.Server(config)
        dashboard_task = asyncio.create_task(server.serve())
        log.info("Dashboard at http://localhost:8080")
    except ImportError:
        log.info("uvicorn not installed — dashboard disabled")

    # ── 7. Jarvis Telegram command center ───────────────────────────────────
    from deep_claw.communication.telegram_commands import TelegramCommandCenter
    jarvis = TelegramCommandCenter(
        token=settings.tg_warroom_token,
        orchestrator=orch,
    )
    jarvis_task = asyncio.create_task(jarvis.start())
    log.info("Jarvis command center starting")

    # ── 8. Graceful shutdown wiring ──────────────────────────────────────────
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _signal_handler() -> None:
        log.info("Shutdown signal received")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _signal_handler)

    # ── 9. Run all feed tasks concurrently ───────────────────────────────────
    feed_tasks = [asyncio.create_task(f.start()) for f in feeds]

    _print_banner(symbols)
    log.info("Deep Claw running. Press Ctrl+C to stop.")

    # Wait until shutdown signal
    await stop_event.wait()

    # ── 10. Shutdown ─────────────────────────────────────────────────────────
    log.info("Stopping feeds...")
    for f in feeds:
        await f.stop()
    for t in feed_tasks:
        t.cancel()
    await jarvis.stop()
    jarvis_task.cancel()
    if dashboard_task:
        dashboard_task.cancel()

    await orch.shutdown()
    log.info("Clean exit.")


def _build_broker_adapters(symbols: list[str]) -> dict:
    """
    Build broker adapters per symbol.
    Demo mode: Deriv uses demo token, Bybit uses testnet.
    Adapters without live clients log MOCK for every action.
    """
    from deep_claw.action.deriv_multiplier import DerivMultiplierAdapter
    from deep_claw.action.deriv_trading_ws import DerivTradingWS
    from deep_claw.action.bybit_perp import BybitPerpAdapter
    from deep_claw.action.mt5_cfd import MT5CFDAdapter
    from deep_claw.cognition.risk.notional_router import get_instrument

    adapters = {}
    bybit_client = _build_bybit_client()

    # One shared trading WS for all Deriv symbols (one account = one auth)
    deriv_trading_ws: DerivTradingWS | None = None
    if settings.deriv_api_token:
        deriv_trading_ws = DerivTradingWS(
            token=settings.deriv_api_token,
            ws_url=settings.deriv_ws_url,
            app_id=settings.deriv_app_id,
        )
        logging.getLogger("deep_claw.main").info(
            "Deriv trading WS created (lazy-connects on first trade)"
        )
    else:
        logging.getLogger("deep_claw.main").warning(
            "DERIV_API_TOKEN not set — Deriv adapter in MOCK mode"
        )

    for sym in symbols:
        try:
            inst = get_instrument(sym)
        except KeyError:
            continue

        if inst.preferred_venue == "deriv_multiplier":
            adapters[sym] = DerivMultiplierAdapter(trading_ws=deriv_trading_ws)

        elif inst.preferred_venue == "bybit_perp":
            adapters[sym] = BybitPerpAdapter(client=bybit_client)

        elif inst.preferred_venue == "mt5_cfd":
            adapters[sym] = MT5CFDAdapter()

    return adapters


def _build_bybit_client():
    """Build pybit HTTP client for testnet or live."""
    if not settings.bybit_api_key:
        return None
    try:
        from pybit.unified_trading import HTTP
        client = HTTP(
            testnet=settings.bybit_testnet,
            api_key=settings.bybit_api_key,
            api_secret=settings.bybit_api_secret,
        )
        logging.getLogger("deep_claw.main").info(
            "Bybit client: %s", "TESTNET" if settings.bybit_testnet else "LIVE"
        )
        return client
    except ImportError:
        logging.getLogger("deep_claw.main").warning("pybit not installed — Bybit adapter in MOCK mode")
        return None


def _print_banner(symbols: list[str]) -> None:
    mode = "DEMO/TESTNET" if settings.bybit_testnet else "⚠  LIVE"
    print(f"""
╔══════════════════════════════════════════════════════╗
║            D E E P   C L A W                         ║
║        Self-Aware Trading Intelligence               ║
╠══════════════════════════════════════════════════════╣
║  Mode     : {mode:<41}║
║  Symbols  : {", ".join(symbols):<41}║
║  Exec TF  : M15                                      ║
║  Claude   : {'ON' if settings.enable_claude_qualification else 'OFF':<41}║
║  ML Conf  : {'ON' if settings.use_ml_confidence else 'OFF (Phase 1 weights)':<41}║
║  Telegram : {'ON' if settings.enable_telegram else 'OFF':<41}║
║  Dashboard: http://localhost:8080                    ║
╚══════════════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    _configure_logging()
    syms = _resolve_symbols(sys.argv)
    asyncio.run(main(syms))
