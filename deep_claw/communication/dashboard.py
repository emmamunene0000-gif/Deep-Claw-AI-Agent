"""
Dashboard server — serves EpisodeStream timeline JSON over HTTP.

Minimal FastAPI app. Read-only. No auth in Phase 1 (localhost only).
Endpoints:
  GET /timeline/{symbol}?n=30      → recent episodes as JSON
  GET /stats/{symbol}              → today's PipTracker stats
  GET /reports/{symbol}?days=14    → rolling daily report rows
  GET /health                      → liveness probe
  WS  /ws/{symbol}                 → live episode push (future)

Consumed by any dashboard (Streamlit, Grafana, etc.) — not coupled to one.
"""
from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False
    log.warning("FastAPI not installed — dashboard server unavailable")


def build_app(
    stream,            # EpisodeStream
    renderer,          # EpisodeStreamRenderer
    pip_trackers: dict,  # symbol → PipTracker
    daily_report,      # DailyReport
) -> Any:
    """
    Build and return the FastAPI app.
    Call with uvicorn: uvicorn deep_claw.communication.dashboard:app
    Or programmatically via `uvicorn.run(build_app(...), ...)`.
    """
    if not _FASTAPI_AVAILABLE:
        raise RuntimeError("pip install fastapi uvicorn to enable the dashboard")

    app = FastAPI(title="Deep Claw Dashboard", version="1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/timeline/{symbol}")
    async def timeline(symbol: str, n: int = 30):
        episodes = stream.recent(symbol.upper(), n=n)
        return renderer.to_dashboard_timeline(symbol.upper(), n=n)

    @app.get("/stats/{symbol}")
    async def stats(symbol: str):
        sym = symbol.upper()
        tracker = pip_trackers.get(sym)
        if not tracker:
            raise HTTPException(status_code=404, detail=f"No tracker for {sym}")
        s = tracker.today
        return {
            "symbol": sym,
            "date": s.date.isoformat(),
            "signal_count": s.signal_count,
            "blocked_count": s.blocked_count,
            "tp1_hits": s.tp1_hits,
            "tp2_hits": s.tp2_hits,
            "tp3_hits": s.tp3_hits,
            "sl_hits": s.sl_hits,
            "holder_exits": s.holder_exits,
            "gross_win_r": round(s.gross_win_r, 3),
            "gross_loss_r": round(s.gross_loss_r, 3),
            "net_r": round(s.net_r, 3),
            "win_rate": round(s.win_rate, 1),
            "profit_factor": s.profit_factor,
            "london_count": s.london_count,
            "ny_count": s.ny_count,
            "asia_count": s.asia_count,
            "overlap_count": s.overlap_count,
        }

    @app.get("/reports/{symbol}")
    async def reports(symbol: str, days: int = 14):
        sym = symbol.upper()
        rows = daily_report.get_recent(sym, days=days)
        return {"symbol": sym, "days": days, "rows": rows}

    @app.get("/reports/{symbol}/rolling")
    async def rolling(symbol: str, days: int = 14):
        sym = symbol.upper()
        return daily_report.get_rolling_stats(sym, days=days)

    return app
