"""
Deep Claw — all runtime configuration.
Every Pine input from the cheatsheet §2 has a direct equivalent here.
Hot-reloadable fields (ADMIN_BIAS, ASSET_CONTEXT) are meant to be updated
via the dashboard/admin panel without restarting the process.
"""
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from deep_claw.core.types import AdminBias, Timeframe


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Anthropic ────────────────────────────────────────────────────────────
    anthropic_api_key: str = ""
    claude_model_qualification: str = "claude-sonnet-4-6"
    claude_model_autopsy: str = "claude-sonnet-4-6"
    claude_model_assessment: str = "claude-opus-4-8"

    # ── Deriv ────────────────────────────────────────────────────────────────
    deriv_app_id: str = ""
    deriv_api_token: str = ""
    deriv_ws_url: str = "wss://ws.binaryws.com/websockets/v3"

    # ── Bybit ────────────────────────────────────────────────────────────────
    bybit_api_key: str = ""
    bybit_api_secret: str = ""
    bybit_testnet: bool = False

    # ── MT5 direct bridge (no TradeSgnl) ─────────────────────────────────────
    mt5_login: int = 0
    mt5_password: str = ""
    mt5_server: str = ""
    mt5_path: str = ""

    # ── Telegram ─────────────────────────────────────────────────────────────
    tg_warroom_token: str = ""
    tg_warroom_chat_id: str = ""
    tg_public_token: str = ""
    tg_public_chat_id: str = ""
    tg_public_sanitize: bool = True
    enable_telegram: bool = True

    # ── Risk defaults ─────────────────────────────────────────────────────────
    risk_per_trade_usd: float = 25.0
    max_equity_risk_pct: float = 0.02    # hard 2% ceiling
    confidence_threshold: float = 60.0   # below this = no trade
    sl_buffer_atr_mult: float = 0.5
    tp_r_multiples: list[float] = Field(default=[1.0, 1.5, 2.0])

    # ── Funded account (Atlas/MT5 prop) ──────────────────────────────────────
    funded_daily_loss_pct: float = 0.05
    funded_max_dd_pct: float = 0.10

    # ── Admin / operator ─────────────────────────────────────────────────────
    admin_bias: AdminBias = AdminBias.AUTO
    operator_note: str = ""
    asset_context: str = ""

    # ── Fractal 4-layer TFs (cheatsheet §2.3) ────────────────────────────────
    sovereign_tf: Timeframe = Timeframe.D
    anchor_tf: Timeframe = Timeframe.H4
    filter_tf: Timeframe = Timeframe.H1
    exec_tf: Timeframe = Timeframe.M5

    # ── UT Bot / trail (cheatsheet §2.4) ─────────────────────────────────────
    ut_buy_sens: float = 3.5
    ut_buy_atr_len: int = 2
    ut_sell_sens: float = 3.5
    ut_sell_atr_len: int = 2
    regime_filter_enabled: bool = True
    require_vwap: bool = True
    require_fib_trend: bool = False
    use_trail_gate: bool = True

    # ── Adaptive VWAP (cheatsheet §2.8) ──────────────────────────────────────
    vwap_swing_period: int = 50
    vwap_base_apt: int = 20
    vwap_adapt_by_atr: bool = False
    vwap_vol_bias: float = 10.0

    # ── Fibonacci bands (cheatsheet §2.9) ────────────────────────────────────
    fib_source: str = "hlc3"
    fib_len: int = 21
    fib_atr_len: int = 14
    fib_use_atr: bool = True

    # ── RSI regime (cheatsheet §2.10) ────────────────────────────────────────
    rsi_len: int = 14
    rsi_pos_thresh: float = 55.0
    rsi_neg_thresh: float = 45.0

    # ── Volume profile (cheatsheet §2.11) ────────────────────────────────────
    vp_enabled: bool = True
    vp_session_type: str = "Daily"
    vp_resolution: int = 30
    vp_va_width: float = 70.0

    # ── SMC (cheatsheet §2.12) ───────────────────────────────────────────────
    smc_swing_len: int = 50
    smc_ob_size: int = 5
    smc_eqhl_len: int = 3
    smc_eqhl_thresh: float = 0.1
    liq_pivot_len: int = 14

    # ── ATM Protocol trail / zones (cheatsheet §2.13) ────────────────────────
    trail_ma_len: int = 200
    trail_atr_len: int = 14
    trail_atr_mult: float = 1.25
    zone_swing_len: int = 14
    zone_max_count: int = 3
    zone_atr_mult: float = 0.35

    # ── Signal smoothing (cheatsheet §2.6) ───────────────────────────────────
    signal_smooth_len: int = 21
    linreg_len: int = 11
    use_linreg_candles: bool = False

    # ── Feature flags ─────────────────────────────────────────────────────────
    use_ml_confidence: bool = False
    enable_vanilla_sleeve: bool = False
    enable_claude_qualification: bool = True
    one_trade_per_symbol: bool = True   # Q1 decision: one trade per symbol

    # ── Reporting ─────────────────────────────────────────────────────────────
    report_hour_utc: int = 21
    log_level: str = "INFO"


# Singleton — import this everywhere
settings = Settings()
