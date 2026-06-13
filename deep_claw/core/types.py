"""
Deep Claw — canonical data contracts.

Every module boundary in this system is one of these types.
Nothing in Perception reads from Cognition.
Nothing in Action reads from Cognition's internal state.
Only PositionStateMachine ever mutates PositionState.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


# ── Enumerations ──────────────────────────────────────────────────────────────

class Session(StrEnum):
    TOKYO = "TOKYO"
    LONDON = "LONDON"
    NEW_YORK = "NEW_YORK"
    OVERLAP = "OVERLAP"       # London-NY overlap — highest-edge window
    OFF = "OFF"

class ATRRegime(StrEnum):
    HIGH = "HIGH"
    MED = "MED"
    LOW = "LOW"

class Direction(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"

class SignalSource(StrEnum):
    UT_BOT = "UT_BOT"
    SMART_RSI = "SMART_RSI"
    LIQUIDITY_ZONE = "LIQUIDITY_ZONE"
    STRUCTURE_SHIFT = "STRUCTURE_SHIFT"

class Verdict(StrEnum):
    SYNC4 = "SYNC4"                  # all 4 TF layers aligned
    COUNTER_TREND = "COUNTER_TREND"  # sovereign opposing exec
    LOCAL = "LOCAL"                  # exec-level only, higher TFs neutral/mixed
    REJECTED = "REJECTED"            # structural veto (regime, ATR, etc.)

class Restriction(StrEnum):
    TP1_ONLY = "TP1_ONLY"
    NO_HOLDER_MODE = "NO_HOLDER_MODE"
    HALF_SIZE = "HALF_SIZE"

class Phase(StrEnum):
    WAITING = "WAITING"
    ENTRY = "ENTRY"
    TP1_HIT = "TP1_HIT"
    TP2_HIT = "TP2_HIT"
    TP3_HIT = "TP3_HIT"
    HOLDER_MODE = "HOLDER_MODE"
    CLOSED = "CLOSED"

class ExitReason(StrEnum):
    TP1 = "TP1"
    TP2 = "TP2"
    TP3 = "TP3"
    HOLDER_EXIT = "HOLDER_EXIT"
    SL = "SL"
    MANUAL = "MANUAL"
    REVERSAL = "REVERSAL"  # closed to open opposing trade

class AutopsyTag(StrEnum):
    LIQUIDITY_TRAP = "LIQUIDITY_TRAP"
    VOLATILITY_COLLAPSE = "VOLATILITY_COLLAPSE"
    SOVEREIGN_VETO = "SOVEREIGN_VETO"
    WEAK_ALIGNMENT = "WEAK_ALIGNMENT"
    MACRO_ROTATION = "MACRO_ROTATION"

class RejectionReason(StrEnum):
    ONE_TRADE_RULE = "ONE_TRADE_RULE"
    CONFIDENCE_TOO_LOW = "CONFIDENCE_TOO_LOW"
    CHAIN_VETO = "CHAIN_VETO"
    REGIME_FILTER = "REGIME_FILTER"
    ATR_TOO_LOW = "ATR_TOO_LOW"
    ADMIN_SILENCE = "ADMIN_SILENCE"

class ClaudeVerdict(StrEnum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    MODIFY = "MODIFY"

class VPStrength(StrEnum):
    ABOVE_VAH = "ABOVE VAH"
    BELOW_VAL = "BELOW VAL"
    IN_VALUE_AREA = "IN VALUE AREA"

class PDHPDLStatus(StrEnum):
    ABOVE_PDH = "ABOVE PDH"
    BELOW_PDL = "BELOW PDL"
    INSIDE_RANGE = "INSIDE RANGE"

class Timeframe(StrEnum):
    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    M30 = "M30"
    H1 = "H1"
    H4 = "H4"
    D = "D"
    W = "W"

class AssetClass(StrEnum):
    FOREX = "forex"
    CRYPTO = "crypto"
    FUTURES = "futures"
    SYNTHETIC = "synthetic"  # Deriv synthetic indices

class Venue(StrEnum):
    DERIV_MULTIPLIER = "deriv_multiplier"
    DERIV_VANILLA = "deriv_vanilla"
    BYBIT_PERP = "bybit_perp"
    MT5_CFD = "mt5_cfd"

class AdminBias(StrEnum):
    AUTO = "AUTO"
    FORCE_BULL = "FORCE_BULL"
    FORCE_BEAR = "FORCE_BEAR"
    SILENCE = "SILENCE"


# ── Episode types (the chain) ─────────────────────────────────────────────────

class EpisodeType(StrEnum):
    SESSION_CHANGE = "SESSION_CHANGE"
    REGIME_FLIP = "REGIME_FLIP"
    ATR_REGIME_CHANGE = "ATR_REGIME_CHANGE"
    LIQUIDITY_SWEEP = "LIQUIDITY_SWEEP"
    STRUCTURE_BREAK = "STRUCTURE_BREAK"       # BOS
    STRUCTURE_CHOCH = "STRUCTURE_CHOCH"       # CHoCH
    PDH_PDL_CROSS = "PDH_PDL_CROSS"
    SIGNAL_CANDIDATE = "SIGNAL_CANDIDATE"     # any generator fired
    SIGNAL_ACCEPTED = "SIGNAL_ACCEPTED"       # position manager accepted it
    SIGNAL_REJECTED = "SIGNAL_REJECTED"       # position manager rejected it (shadow-blocked)
    TP1_HIT = "TP1_HIT"
    TP2_HIT = "TP2_HIT"
    TP3_HIT = "TP3_HIT"
    SL_HIT = "SL_HIT"
    HOLDER_EXIT = "HOLDER_EXIT"
    TRADE_CLOSED = "TRADE_CLOSED"
    CLAUDE_VERDICT = "CLAUDE_VERDICT"
    DAILY_ASSESSMENT = "DAILY_ASSESSMENT"
    PROPOSAL = "PROPOSAL"                     # Claude-generated parameter proposals (never auto-applied)


@dataclass
class Episode:
    episode_type: EpisodeType
    symbol: str
    timestamp: datetime
    payload: dict[str, Any]               # typed per episode_type, serialized as JSON
    market_state_ref: str | None = None   # FK to MarketState snapshot (by bar_id)
    episode_id: str = field(default_factory=lambda: str(uuid.uuid4()))


# ── Perception outputs ────────────────────────────────────────────────────────

@dataclass
class EMATrend:
    ema9: float
    ema21: float
    bullish: bool  # ema9 > ema21


@dataclass
class LiquidityTrailState:
    trend: int         # 1 = bullish, -1 = bearish
    trail_value: float


@dataclass
class SMCState:
    swing_bias: int             # 1 bullish, -1 bearish, 0 neutral
    latest_bos_direction: int   # 1 bullish BOS, -1 bearish BOS, 0 none recent
    latest_choch_direction: int # 1 bullish CHoCH, -1 bearish CHoCH, 0 none recent
    ph_top: float               # buy-side liquidity level
    pl_btm: float               # sell-side liquidity level
    last_swing_high: float      # most recent confirmed swing high (for SL computation)
    last_swing_low: float       # most recent confirmed swing low (for SL computation)
    active_ob_bull: float | None  # nearest active bullish order block
    active_ob_bear: float | None  # nearest active bearish order block
    fvg_bull_active: bool
    fvg_bear_active: bool
    liq_bias: str               # human-readable: "BUY-SIDE SWEPT" etc.


@dataclass
class MarketState:
    """
    Flat numeric feature vector — one per symbol per confirmed bar close.
    This is what ML trains on and what signal generators read.
    It is a snapshot. Cognition reasons over the EpisodeStream, not this alone.
    """
    symbol: str
    timestamp: datetime
    bar_id: str   # "{symbol}_{tf}_{timestamp.isoformat()}"
    timeframe: Timeframe

    # Price
    open: float
    high: float
    low: float
    close: float
    volume: float

    # Liquidity trail (exec/M5/M15/H1)
    trail_exec: LiquidityTrailState
    trail_m5: LiquidityTrailState
    trail_m15: LiquidityTrailState
    trail_h1: LiquidityTrailState

    # Adaptive VWAP
    vap_current: float    # current VWAP value
    last_swing: int       # 1 = last swing was bullish (price above VWAP), -1 bearish

    # Volume profile
    poc: float
    vah: float
    val: float
    vp_strength: VPStrength

    # RSI
    rsi: float
    rsi_regime_positive: bool
    rsi_regime_negative: bool

    # Fibonacci bands
    trend_fib: int    # 1, -1, 0
    fib_upper: float
    fib_lower: float

    # SMC
    smc: SMCState

    # Daily levels
    pdh: float
    pdl: float
    pdh_pdl_status: PDHPDLStatus

    # ATR
    atr: float
    atr_regime: ATRRegime

    # Session
    session: Session

    # EMA grid (key = Timeframe)
    ema_grid: dict[str, EMATrend]

    # Derived composite score (-15 to +15, from 5-TF scoring)
    total_score: float
    master_bias: str   # human-readable bias label


# ── Normalized candle (off the bus) ──────────────────────────────────────────

@dataclass
class NormalizedCandle:
    symbol: str
    timeframe: Timeframe
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: datetime
    confirmed: bool   # True only on bar close — never use unconfirmed for signal logic
    venue: Venue


# ── Cognition outputs ─────────────────────────────────────────────────────────

@dataclass
class SignalCandidate:
    source: SignalSource
    direction: Direction
    symbol: str
    timestamp: datetime
    proposed_sl: float
    proposed_tp1: float
    proposed_tp2: float
    proposed_tp3: float
    confidence_inputs: dict[str, float]  # raw factor values before weighting
    candidate_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class ChainVerdict:
    verdict: Verdict
    confidence_override: float | None     # if set, overrides ConfidenceResult
    restrictions: set[Restriction]
    sl_modifier: float                    # multiplier on proposed_sl distance (default 1.0)
    causal_trace: str                     # human-readable explanation
    episodic_note: str | None             # pattern match against history, if any
    layer_states: dict[str, int]          # {"sovereign": 1, "anchor": 1, "filter": -1, "exec": 1}
    total_score: float                    # the composite 5-TF score at verdict time


@dataclass
class ConfidenceResult:
    bull_confidence: float    # 0-100
    bear_confidence: float    # 0-100
    breakdown: dict[str, float]  # per-factor contribution
    weights_used: dict[str, float]  # which weight profile fired
    session: Session
    atr_regime: ATRRegime


@dataclass
class TradeInstruction:
    """
    The only object that crosses the Cognition→Action boundary.
    Action adapters never compute sizing or TP levels.
    """
    symbol: str
    direction: Direction
    entry: float
    sl: float
    tp1: float
    tp2: float
    tp3: float
    size_units: float        # position size in base units (lots, contracts, etc.)
    size_usd_risk: float     # dollar risk being taken (for logging)
    venue: Venue
    trade_id: str
    chain_verdict: Verdict
    restrictions: set[Restriction]


@dataclass
class PositionHandle:
    """Opaque broker reference. Only Action layer knows the internal format."""
    venue: Venue
    broker_ref: str          # venue-specific order/contract ID
    trade_id: str            # links back to PositionState


@dataclass
class PositionState:
    """
    THE single source of truth for open trade state.
    Only PositionStateMachine creates or mutates this.
    Zero other modules hold a reference to a mutable PositionState.
    """
    trade_id: str
    symbol: str
    direction: Direction
    entry: float
    sl: float
    tp1: float
    tp2: float
    tp3: float
    size_units: float
    size_usd_risk: float
    venue: Venue
    phase: Phase
    signal_source: SignalSource
    chain_verdict: Verdict
    confidence_at_entry: float
    restrictions: set[Restriction]
    handle: PositionHandle | None
    opened_at: datetime
    bar_count: int = 0
    mfe_pips: float = 0.0    # max favorable excursion in pips
    mae_pips: float = 0.0    # max adverse excursion in pips
    peak_profit_pips: float = 0.0


@dataclass
class ClosedTrade:
    """Written to the journal when a position closes. Immutable record."""
    trade_id: str
    symbol: str
    direction: Direction
    signal_source: SignalSource
    chain_verdict: Verdict
    confidence_at_entry: float
    restrictions: frozenset[Restriction]
    entry: float
    exit: float
    sl_at_entry: float
    sl_distance: float
    tp1: float
    tp2: float
    tp3: float
    size_units: float
    size_usd_risk: float
    venue: Venue
    exit_reason: ExitReason
    autopsy_tag: AutopsyTag | None
    mfe_pips: float
    mae_pips: float
    mfe_r: float              # MFE in R-multiples
    mae_r: float              # MAE in R-multiples
    realized_r: float         # actual exit P&L in R-multiples
    bar_count: int
    opened_at: datetime
    closed_at: datetime
    session_at_entry: Session
    atr_regime_at_entry: ATRRegime
    total_score_at_entry: float


# ── Risk model types ──────────────────────────────────────────────────────────

@dataclass
class SizingResult:
    final_size: float
    kelly_size: float
    pct_equity_cap: float
    daily_loss_cap: float | None
    margin_cap: float | None
    binding_clamp: str         # which clamp was binding: "kelly"|"pct"|"daily_loss"|"margin"
    kelly_fraction: float
    equity: float


# ── Instrument registry type ──────────────────────────────────────────────────

@dataclass
class Instrument:
    symbol: str
    deriv_code: str | None
    bybit_symbol: str | None
    mt5_symbol: str | None
    asset_class: AssetClass
    pip_size: float            # price per pip (e.g. 0.0001 for EUR/USD)
    contract_notional: float   # notional per base unit
    min_unit: float            # minimum tradeable unit
    session_profile: str       # "24_7" or "session_based"
    preferred_venue: Venue
    point_value: float | None  # for futures/indices — syminfo.pointvalue equivalent
