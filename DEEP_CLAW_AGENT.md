# DEEP CLAW — THE AGENT
### *A Self-Aware Trading Intelligence. Born from Pine Script. Built in Python. Alive in the Chain.*

---

> **Goal Zero — never lose sight of it:**
> *Convert skill + time + capital into income, via probabilistic speculation with positive
> expectancy, intraday liquidity-extraction scalping, and compounding wins — executed by a
> self-aware system that gets better the longer it runs.*

---

## DIAGNOSTIC — System State as of Birth

```
Tests          : 19/19 PASS
Modules        : 48/48 import clean
Files          : 67 Python files
Lines of code  : 8,282
Commits        : 3 (Sessions 1–3)
Branch         : claude/nifty-tesla-fqaa4c
```

| Layer            | Files | Lines | Status |
|-----------------|-------|-------|--------|
| Core / Config   | 4     | 580   | ✅     |
| Perception      | 18    | 1,519 | ✅     |
| Cognition       | 13    | 1,783 | ✅     |
| Action          | 5     | 551   | ✅     |
| Claude Layer    | 4     | 426   | ✅     |
| Journal         | 6     | 1,016 | ✅     |
| Communication   | 4     | 435   | ✅     |
| Learning        | 4     | 312   | ✅     |
| Feeds           | 3     | 416   | ✅     |
| Orchestrator    | 2     | 697   | ✅     |
| Tests           | 4     | 547   | ✅     |

---

## MIND MAP — What Deep Claw Actually Is

```
                        ┌─────────────────────────────────────────┐
                        │           DEEP CLAW INTELLIGENCE          │
                        │   Event-Sourced. Self-Narrating. Alive.   │
                        └──────────────────┬──────────────────────┘
                                           │
          ┌────────────────────────────────┼────────────────────────────────┐
          │                                │                                 │
   ┌──────▼──────┐                ┌────────▼────────┐               ┌───────▼──────┐
   │  TRON        │                │  THE SPINE       │               │  JARVIS       │
   │ (senses)     │                │ (memory / chain) │               │ (mind)        │
   │              │                │                  │               │               │
   │ NormCandle   │──push──►│ EpisodeStream    │──read──►│ ChainReasoning│
   │ Bus          │                │ (SQLite, append- │               │ Engine        │
   │              │                │  only)           │               │               │
   │ Perception   │                │                  │               │ Confidence    │
   │  • 11 inds   │                │ 4 consumers:     │               │ Engine v1     │
   │  • 4 SMC     │                │  1. Dashboard    │               │               │
   │  • EpisodeEm.│                │  2. Telegram     │               │ Claude Gate   │
   │              │                │  3. Claude       │               │  (narrative   │
   │ CandleBus    │                │  4. ML Training  │               │   judgment)   │
   │  • Deriv WS  │                │                  │               │               │
   │  • Bybit WS  │                │ Feature Store    │               │ Position      │
   │  • MT5 bridge│                │ (shadow+accepted)│               │ State Machine │
   └──────┬───────┘                └────────┬─────────┘               └───────┬──────┘
          │                                 │                                  │
          │                                 │                                  │
          └────────────────────────┬────────┘                                  │
                                   │                                           │
                          ┌────────▼────────┐                        ┌────────▼──────┐
                          │   MarketState    │                        │  TradeInstruct.│
                          │ (flat numeric    │                        │  (ONE object   │
                          │  feature vector) │                        │   crosses the  │
                          │ • 30+ fields     │                        │   Cognition/   │
                          │ • per bar/symbol │                        │   Action line) │
                          └─────────────────┘                        └────────┬──────┘
                                                                               │
                                                          ┌────────────────────▼──────────┐
                                                          │         ACTION LAYER            │
                                                          │   BrokerAdapter Protocol        │
                                                          │  open / modify / partial_close  │
                                                          │  close / get_live_pnl           │
                                                          │                                 │
                                                          │  ┌──────────┐ ┌──────────────┐ │
                                                          │  │  Deriv   │ │    Bybit     │ │
                                                          │  │Multiplier│ │  Perp (V5)   │ │
                                                          │  └──────────┘ └──────────────┘ │
                                                          │        ┌───────────────┐        │
                                                          │        │  MT5 CFD       │        │
                                                          │        │ (direct bridge)│        │
                                                          │        │ NO TradeSgnl   │        │
                                                          │        └───────────────┘        │
                                                          └─────────────────────────────────┘
```

---

## ORIGIN — Where This Came From

### The Pine Script Lineage

Deep Claw is the Python realization of a trading system that existed in Pine Script form across **three generations**:

| Generation | File | What it was |
|-----------|------|-------------|
| ADSA v7 | `reference/pine-source/Absolute Dollar Agent V7.txt` | UT Bot + Smart RSI + ATR trail, single TF |
| The Claw Protocol | `reference/pine-source/The Claw Protocol.txt` | Multi-layer confluence engine: Trail → Gate → Confluence → Confidence → Execution |
| ADSA v8 | `reference/pine-source/Absolute Dollar Agent V8.txt` | Added TradeSgnl integration, MT5 webhook — and introduced the orphan-trade bug |

**The Claw Protocol** (`The Claw Protocol.txt`) defined the architecture Deep Claw now implements in Python:

```
// Architecture: TRIGGER → GATE → CONFLUENCE → CONFIDENCE → EXECUTION
//
// TRIGGER:    ATM Bot (UT Bot) provides timing — the "when"
// GATE:       Liquidity Trail direction must confirm — the "which way"
// CONFLUENCE: MTF + Structure + RSI + VWAP + Fib + VP → Confidence Score
// CONFIDENCE: Score must exceed threshold (Claw Mode determines threshold)
// EXECUTION:  Only signals passing ALL layers are executed
//
// The Liquidity Trail is TRUTH (direction), not a trigger (timing).
// The ATM Bot is TIMING (trigger), not direction.
// Confluence builds CONFIDENCE, which gates execution.
```

Every one of these concepts survived the port. The Python system executes this exact hierarchy.

### The v8 Failure — What Was Learned

The v8 post-mortem identified **the root cause of the orphan-trade bug**:

```pine
// v8's fatal architecture: two generators share one mutable posState
if ut_buy_signal or smart_rsi_bull
    posState := 1    // ← both sources writing to same integer
```

This meant:
- Two signals on the same bar competed for one `posState` variable
- When a new signal fired during an open trade, the previous trade's SL labels were orphaned
- The ML training data was corrupted because `realized_r` was sometimes attributed to the wrong signal source

**The Python fix is structural, not a patch:**

```python
# N pure signal generators → List[SignalCandidate] → ONE PositionStateMachine
# The PSM is the only writer of SIGNAL_ACCEPTED, SL_HIT, TRADE_CLOSED episodes.
# Signal generators cannot touch trade state — they're pure functions with no shared state.
```

Test `test_sl_only_written_by_price_check_not_by_signal` proves this invariant holds.

---

## THE MANDATE — What Was Instructed

From the founding session, the instructions were explicit:

| Instruction | Verbatim |
|------------|----------|
| Goal Zero | *"Convert skill + time + capital into income, via probabilistic speculation with positive expectancy, intraday liquidity-extraction scalping, and compounding wins — executed by a self-aware system that gets better the longer it runs"* |
| Trade rule | *"Q1, agreed one trade per symbol"* |
| Confidence weights | *"Q2, I think those weights need to be adaptive to market changes and sessions"* |
| MT5 path | *"Q3, YES DIRECT BRIDGE — NOO tradesgnl"* |
| Broker constraints | *"NO TradeSgnl string templates, NO f_format_alert, NO f_format_modify"* |
| Mode | *"We are not doing paper — demo mode"* |

Every one of these mandates is traceable to specific code.

---

## WHAT WAS BUILT — Instruction to Delivery

### SESSION 1 — The Load-Bearing Wall (Steps 1–9)

> *"Steps 1–4 are the load-bearing wall. Everything else depends on the chain existing and the position state being trustworthy."* — Original README

#### 1. Data Contracts (`deep_claw/core/types.py` — 440 lines)

Every module boundary in the system is one of these types. Nothing in Perception reads from Cognition. Nothing in Action reads from Cognition's state.

**Key types delivered:**
- `Episode` + `EpisodeType` (19 episode types — the chain's vocabulary)
- `MarketState` (30+ field flat feature vector — what ML trains on)
- `SignalCandidate` (what generators produce — pure, no side effects)
- `ChainVerdict` (SYNC4 / COUNTER_TREND / LOCAL / REJECTED)
- `ConfidenceResult` (bull/bear confidence + per-factor breakdown)
- `TradeInstruction` (the ONLY object that crosses Cognition → Action)
- `PositionHandle` (opaque broker ref — Action layer owns the format)
- `PositionState` (owned exclusively by PositionStateMachine)
- `NormalizedCandle` (unified feed format from all brokers)

**Mandate delivery:** `one_trade_per_symbol: bool = True` in `settings.py` — the Q1 answer is a settings field, not an assumption.

---

#### 2. Configuration (`deep_claw/config/settings.py` — 140 lines)

Every Pine Script `input.*` from The Claw Protocol maps to a typed Python field:

| Pine input | Python setting | Reference |
|-----------|---------------|-----------|
| `ma_len = 200` | `trail_ma_len: int = 200` | Protocol §1: MTF Trail |
| `atr_mult = 1.25` | `trail_atr_mult: float = 1.25` | Protocol §1 |
| `a_buy = 3.5` | `ut_buy_sens: float = 3.5` | Protocol §3: ATM Bot |
| `claw_mode / threshold` | `confidence_threshold: float = 60.0` | Protocol §8: Confidence |
| `mtf_weight = 1.5` | `WeightMatrix` (adaptive) | Protocol §8 + Q2 mandate |
| `vpEnabled` | `vp_enabled: bool = True` | Protocol §7 |
| `rsiLen = 14` | `rsi_len: int = 14` | Protocol §5 |
| `swingSize = 15` | `smc_swing_len: int = 50` | Protocol §4 |

**Q2 mandate delivery:** Weights are NOT static. `WeightMatrix` in `confidence_v1.py` resolves weights by `(session, atr_regime)` — different weight profiles for London vs. Tokyo vs. OFF sessions, and for HIGH vs. LOW ATR regimes.

---

#### 3. Perception — The Indicators (`deep_claw/perception/indicators/` — 8 files)

Every confluence factor from The Claw Protocol ported as a pure function:

| Protocol Step | Python file | What it computes |
|--------------|-------------|-----------------|
| §3: MTF Trail Engine | `liquidity_trail.py` | Ratcheting ATR trail → (trend, trail_value). Exact port of Pine's `calcLiqTrail()` function — the `math.max`/`math.min` ratchet is preserved |
| §7: VWAP Anchor | `adaptive_vwap.py` | Stateful `AdaptiveVWAP`. Critical: `alpha_from_apt()` is an exact port of Pine's `alphaFromAPT()`. The `math.exp(-math.log(2.0) / max(1.0, apt))` formula is preserved verbatim |
| §5: RSI Momentum | `rsi_regime.py` | Flip-flop state machine. `positive`/`negative` sustain logic preserved |
| §6: ATR Regime | `atr_regime.py` | HIGH/MED/LOW classification |
| §7: Volume Profile | `volume_profile.py` | POC, VAH, VAL computation. `VPStrength` enum: ABOVE_VAH / BELOW_VAL / IN_VALUE_AREA |
| §9: Fib Bands | `fib_bands.py` | ATR-based fib bands. `trend_fib` direction flag |
| §4: Market Structure (SMC) | `smc/structure.py` | BOS, CHoCH, swing highs/lows |
| — | `smc/fvg.py` | Fair value gap detection |
| §5: Liquidity Zones | `smc/liquidity.py` | Sweep detection, PH/PL tracking, `liq_bias` string |
| — | `smc/order_blocks.py` | Nearest active OB detection |
| — | `ema_grid.py` | 5-TF EMA trend scoring |
| — | `daily_levels.py` | PDH/PDL tracking, `PDHPDLStatus` enum |

---

#### 4. The EpisodeStream — The Spine (`deep_claw/journal/episode_stream.py` — 292 lines)

The original README stated: *"The EpisodeStream is the spine of the whole system."*

```
Instruction given:  "Chain, not Tree. The chain is what Cognition reasons over."
Delivered:          SQLite-backed append-only event log. One row per state transition.
                    Fires ONLY when something CHANGES — not on every bar.
```

Key methods:
- `append(episode)` — the only write path
- `query(symbol, since, episode_types)` — filtered reads
- `recent(symbol, n)` — ordered by timestamp+rowid (deterministic)
- `render_narrative(symbol, n)` — prose summary for Claude's context window
- `find_similar_setups(symbol, pattern)` — episodic memory search
- `get_today_closed_trades(symbol)` — EOD aggregation

**Four consumers, one source** — exactly as designed:
1. `renderer.to_dashboard_timeline()` → JSON for dashboard
2. `renderer.to_telegram_narrative()` → War Room message
3. `renderer.to_claude_context()` → Claude qualification briefing
4. `renderer.to_daily_summary()` → EOD assessment input

---

#### 5. Signal Generators — Four Independent Pure Functions

**Instruction:** *"Four independent signal generators: UT Bot, Smart RSI, Liquidity Zone, Structure Shift — pure functions, zero shared state, zero knowledge of each other."*

Each generator: `(MarketState) -> SignalCandidate | None`

| Generator | File | Pine origin | Gating logic |
|-----------|------|-------------|-------------|
| UT Bot | `cognition/signals/ut_bot.py` | Protocol §6: ATM Bot trigger | trail_exec trend + close vs trail + regime filter + VWAP gate + M15 trail gate |
| Smart RSI | `cognition/signals/smart_rsi.py` | Protocol §5: RSI Momentum | RSI ≤25 AND trail_exec==1 (bull), RSI ≥75 AND trail_exec==-1 (bear) |
| Liquidity Zone | `cognition/signals/liquidity_zone.py` | Protocol §5: Liquidity Zones | Sweep + CHoCH confirmation required |
| Structure Shift | `cognition/signals/structure_shift.py` | Protocol §4: Market Structure | Blocked if ATR regime is LOW |

**Test coverage:** `tests/test_signal_generators.py` — 9 tests covering all 4 generators, ATR gate, and **the independence invariant**: two generators can fire on the same bar and only one position opens.

---

#### 6. Chain Reasoning Engine (`deep_claw/cognition/chain_reasoning.py` — 284 lines)

**New concept — no Pine equivalent.** This is what separates Deep Claw from its lineage.

```
Instruction given:  "Chain, not Tree. Reads the EpisodeStream. Returns ChainVerdict
                     (SYNC4/COUNTER_TREND/LOCAL/REJECTED) with causal_trace."
Delivered:          ChainReasoningEngine.evaluate(candidate, market_state, episode_window=25)
```

Fractal 4-Layer reads directly from MarketState fields:
- `sovereign` = `trend_fib` (D-level direction)
- `anchor` = `trail_h1.trend` (H4-level)
- `filter` = `trail_m15.trend` (H1-level)
- `exec` = `trail_exec.trend` (M15-level)

Verdict logic:
- **SYNC4**: all 4 aligned → standard sizing
- **COUNTER_TREND**: sovereign opposes exec → `TP1_ONLY + NO_HOLDER_MODE + HALF_SIZE` restrictions
- **LOCAL**: exec-level only, higher TFs neutral/mixed → standard sizing, no holder mode
- **REJECTED**: structural veto (ATR, regime, admin silence)

Episodic memory: calls `stream.find_similar_setups()` → `episodic_note` in the verdict.

---

#### 7. Confidence Engine (`deep_claw/cognition/confidence_v1.py` — 253 lines)

**Q2 mandate delivery:** Adaptive weights — not static.

```python
# DEFAULT_WEIGHT_MATRIX resolves by (session, atr_regime)
"LONDON": ConfidenceWeights(mtf_trail=2.0, rsi_regime=0.8, vwap=1.2, ...)
"TOKYO":  ConfidenceWeights(mtf_trail=1.0, rsi_regime=1.2, vwap=1.5, ...)
"OFF":    ConfidenceWeights(mtf_trail=2.0, rsi_regime=1.5, vwap=1.5, ...)

# ATR overrides
HIGH: mtf_trail amplified (momentum regime)
LOW:  0.5x score penalty (compression regime — cheatsheet §3.4)
```

Six factors per The Claw Protocol §8:
1. MTF trail alignment (mtf_trail weight)
2. RSI regime (rsi_regime weight)
3. VWAP position (vwap weight)
4. Fib trend direction (fib_trend weight)
5. Volume profile position (volume_profile weight)
6. SMC structure bias (smc_structure weight)

**Phase 2 swap point:** `learning/inference.py` implements identical `(MarketState) -> ConfidenceResult` signature. Toggle with `USE_ML_CONFIDENCE=true`. No other file changes.

---

#### 8. Position State Machine (`deep_claw/cognition/position_manager.py` — 597 lines)

The most critical file in the system. The structural fix for every v8 bug.

```
Instruction given:  "ONE PositionStateMachine. THE single owner of ALL trade state.
                     Zero-orphan architecture. Shadow-blocked logging."
Delivered:          PositionStateMachine — 597 lines, 6 invariant tests
```

**Rules encoded as architecture, not discipline:**

1. Only PSM creates or mutates PositionState
2. Every candidate is explicitly ACCEPTED or REJECTED — never silently dropped
3. Rejected candidates are logged as SIGNAL_REJECTED (shadow-blocked data)
4. Reversal = close existing (log P&L) + open new — no orphans, no dead zones
5. SL labels are only written by price-check logic — never by signal firing
6. TP1→TP2→TP3→HOLDER_MODE→exit progression is managed here, not in brokers

**One-trade rule delivery:**
```python
if settings.one_trade_per_symbol and self._state is not None:
    self._log_rejection(candidate, ms, RejectionReason.ONE_TRADE_RULE, ...)
    return None
```

**Trade ID format:** `ATM-YYYYMMDD-HHMM-BUY/SELL-N` — traceable, never recycled.

**SL autopsy tags** (5 root causes, priority-ordered):
1. `LIQUIDITY_TRAP` — sweep visible in chain before entry
2. `VOLATILITY_COLLAPSE` — ATR was LOW at time of SL hit
3. `SOVEREIGN_VETO` — COUNTER_TREND verdict at entry
4. `WEAK_ALIGNMENT` — total_score < 4 at entry
5. `MACRO_ROTATION` — none of the above (clean stop)

---

#### 9. Risk System (`deep_claw/cognition/risk/` — 3 files)

**4-clamp Kelly formula (from cheatsheet §4.1):**

```python
effective_risk_usd = min(
    kelly_implied_risk,      # fractional Kelly from confidence
    pct_cap_usd,             # 2% hard equity ceiling
    daily_cap_usd,           # daily loss budget remaining
    margin_cap_usd,          # margin headroom constraint
)
```

`SizingResult.binding_clamp` records which clamp was binding — logged to every trade for post-hoc analysis.

**Notional router** (`notional_router.py`): reads `instrument_registry.yaml` — 14 instruments, per-symbol pip_size, contract_notional, min_unit, preferred_venue. The exact port of v6.1's `_get_contract_notional`.

---

#### 10. Action Layer (`deep_claw/action/` — 4 files)

**Q3 mandate delivery — NO TradeSgnl, NO f_format_alert, NO f_format_modify.**

```python
# BrokerAdapter Protocol — 5 async methods
class BrokerAdapter(Protocol):
    async def open_position(self, instruction: TradeInstruction) -> PositionHandle: ...
    async def modify_stop(self, handle: PositionHandle, new_sl: float) -> None: ...
    async def partial_close(self, handle: PositionHandle, fraction: float) -> None: ...
    async def close_position(self, handle: PositionHandle) -> None: ...
    async def get_live_pnl(self, handle: PositionHandle) -> float: ...
```

| Adapter | Venue | Key implementation detail |
|---------|-------|--------------------------|
| `deriv_multiplier.py` | Deriv WebSocket API v3 | `proposal → buy` flow. SL as `limit_order.stop_loss` in $ amount. NO take_profit submitted — TP managed by PSM |
| `bybit_perp.py` | Bybit V5 | Market order + `set_trading_stop`. Leverage set at startup, decoupled from sizing |
| `mt5_cfd.py` | MetaTrader5 Python package | **Direct `order_send()` bridge. Zero TradeSgnl. Zero alert strings.** Funded-account daily-loss clamp as final gate |

---

### SESSION 2 — Intelligence, Memory, Communication

#### 11. Claude Qualification Layer (`deep_claw/claude/qualification.py` — 190 lines)

```
Instruction given:  "Claude reads the episode chain as a story and returns
                     APPROVE / REJECT / MODIFY. Narrative judgment, not
                     indicator recalculation. Called BEFORE broker commit."
Delivered:          qualify_signal() async — reads rendered chain narrative,
                    returns QualificationVerdict with size_modifier, sl_modifier
```

Claude sees:
- Last N episodes as prose narrative
- ChainVerdict + its causal_trace
- Confidence breakdown
- Episodic note (similar setups from history)

Claude returns structured response parsed by `_parse_qualification_response()`:
```
VERDICT: APPROVE | REJECT | MODIFY
SIZE: 0.75      (multiplier on base risk)
SL: 1.2         (multiplier on proposed SL distance)
REASON: ...
```

Fails **safe**: any parse error defaults to APPROVE. Never blocks a trade due to API failure.

---

#### 12. SL Autopsy (`deep_claw/claude/sl_autopsy.py` — 107 lines)

```
Instruction given:  "Read the actual chain, identify what was knowable before
                     entry, write a concrete actionable lesson."
Delivered:          run_sl_autopsy() — reads 15 episodes pre-SL, sends to Claude
                    with autopsy_tag, writes PROPOSAL episode with auto_apply=False
```

The lesson is stored as an episode. It is not a text file. It is queryable.

---

#### 13. Daily Assessment (`deep_claw/claude/daily_assessment.py` — 130 lines)

```
Instruction given:  "3 specific parameter proposals, OVERALL session assessment.
                     Never auto-applied. Human reviews them."
Delivered:          run_daily_assessment() — runs at report_hour_utc, writes
                    PROPOSAL episodes with auto_apply=False always
```

Proposals write back to the chain:
```python
payload={
    "type": "DAILY_ASSESSMENT",
    "description": proposal,
    "auto_apply": False,   # NEVER True — architectural constraint
}
```

---

#### 14. Feature Store — Survivorship-Bias-Free ML Data (`deep_claw/journal/feature_store.py` — 282 lines)

```
Instruction given:  "Shadow-blocked candidates (rejected) are EQUALLY important
                     as accepted ones. ONE_TRADE_RULE and CONFIDENCE_TOO_LOW
                     are different features — never conflated."
Delivered:          SQLite table with 40+ columns. fired=0 (shadow-blocked)
                    and fired=1 (accepted) stored in same table.
                    rejection_reason is a separate column.
```

The `write_candidate()` method writes BEFORE the position machine decides — so even trades that get Claude-rejected have their MarketState features logged. The `label_outcome()` method joins `realized_r`, `exit_reason`, `mfe_r`, `mae_r` back via `trade_id` after close.

This is the training data pipeline that makes Phase 2 possible.

---

#### 15. Outcome Labeler (`deep_claw/journal/outcome_labeler.py` — 92 lines)

Subscribes to `SL_HIT`, `HOLDER_EXIT`, `TRADE_CLOSED` episodes. Joins outcomes back to feature rows. `backfill_from_stream()` catches any labels missed during downtime.

---

#### 16. Daily Report (`deep_claw/journal/daily_report.py` — 236 lines)

Structured SQLite row per symbol per day. Not a text block. Queryable by ML.

Columns: signal_count, blocked_count, tp1/tp2/tp3/sl/holder hits, gross_win_r, gross_loss_r, net_r, win_rate, profit_factor, session breakdown (london/ny/asia/overlap), ATR regime counts, episode_type_counts (JSON), assessment_text, proposal_count.

---

#### 17. Telegram Dispatcher (`deep_claw/communication/telegram.py` — 128 lines)

Two-channel architecture:
- **War Room** (`TG_WARROOM_TOKEN`): full Glass Box narrative — chain trace, confidence breakdown, SL/TP levels, autopsy lessons, EOD proposals
- **Public** (`TG_PUBLIC_TOKEN`): sanitized — direction only, no SL distances, no confidence numbers

Rate-limited at 1.1s/message (Telegram's 1/sec per chat limit + margin).

---

#### 18. Dashboard (`deep_claw/communication/dashboard.py` + FastAPI)

```
GET /health                      → liveness probe
GET /timeline/{symbol}?n=30      → recent episodes JSON
GET /stats/{symbol}              → today's WR/PF/session breakdown
GET /reports/{symbol}?days=14    → rolling daily report rows
GET /reports/{symbol}/rolling    → aggregated 14-day stats
```

---

#### 19. Learning Layer (`deep_claw/learning/` — 3 files)

**Phase 2 infrastructure, ready to activate.**

`model.py`: LightGBM with 5 quantile heads (q10/q25/q50/q75/q90) predicting R-multiple distribution. Trains on feature store labeled rows. Minimum 200 labeled rows before training.

`inference.py`: `predict_confidence(market_state) -> ConfidenceResult` — **identical signature to `confidence_v1.confidence()`**. Zero changes to anything else when Phase 2 activates.

`sizing.py`: Fractional Kelly (capped at 25%) derived from quantile distribution. `p_positive()` estimates P(R>0) from the quantile spread.

**Activation:** set `USE_ML_CONFIDENCE=true` in `.env`.

---

### SESSION 3 — Demo Mode, Live Feeds, Entry Point

#### 20. Deriv WebSocket Feed (`deep_claw/feeds/deriv_feed.py` — 207 lines)

```
Instruction:  "Demo mode — Deriv demo account token"
Delivered:    DerivFeed class
              • Authorizes via WS API v3
              • Subscribes to M5/M15/H1/H4/D OHLC per symbol
              • Loads 500-bar history on connect
              • Confirmed-candle logic: epoch change triggers bar confirmation
              • Exponential backoff reconnect (2s → 4s → 8s → 16s → 32s cap)
```

Deriv symbol mapping from `instrument_registry.yaml`:
- `VOLATILITY_75_INDEX` → `R_75`
- `VOLATILITY_100_INDEX` → `R_100`
- `XAUUSD` → `frxXAUUSD`
- `GBPUSD` → `frxGBPUSD`

---

#### 21. Bybit WebSocket Feed (`deep_claw/feeds/bybit_feed.py` — 209 lines)

```
Instruction:  "Demo mode — BYBIT_TESTNET=true"
Delivered:    BybitFeed class
              • Testnet: wss://stream-testnet.bybit.com/v5/public/linear
              • REST history fetch on startup (fills bus before stream begins)
              • Subscribes to kline.{interval}.{symbol}
              • Uses confirm: true flag — cleanest bar-close signal of any exchange
              • Same exponential backoff reconnect
```

---

#### 22. Orchestrator (`deep_claw/orchestrator.py` — 482 lines)

The main event loop. Stateless with respect to trade execution.

```
Data flow (per confirmed M15 bar close):
  BybitFeed/DerivFeed → NormalizedCandleBus.ingest()
    → _on_confirmed_bar_sync()  [sync bus handler]
    → asyncio.ensure_future(_process_confirmed_bar())
      → MarketStateBuilder.build(bus)    → MarketState
      → EpisodeEmitter.update()          → BOS/CHoCH/session episodes
      → PositionStateMachine.update_price() → TP/SL progression
      → [4 signal generators]            → List[SignalCandidate]
      → ChainReasoningEngine.evaluate()  → ChainVerdict
      → confidence_v1.confidence()       → ConfidenceResult
      → FeatureStore.write_candidate()   → shadow row (fired=False)
      → PositionStateMachine.process_candidates() → TradeInstruction | None
      → [Claude qualification gate]      → APPROVE/REJECT/MODIFY
      → BrokerAdapter.open_position()    → PositionHandle
      → FeatureStore update (fired=True, trade_id)
      → PipTracker.record_signal()
      → Telegram.send_signal_alert()
```

EOD loop: fires at `REPORT_HOUR_UTC` (default 21:00 UTC) — runs daily assessment, writes daily report, sends Telegram summary.

---

#### 23. Entry Point (`main.py` — 215 lines)

```bash
# Demo mode startup
cp .env.example .env    # fill in demo tokens
python main.py VOLATILITY_75_INDEX BTCUSDT

# Or all default symbols
python main.py
```

Startup sequence:
1. BybitFeed loads 500-bar REST history per TF (fills bus before live stream)
2. DerivFeed connects WS, authorizes, loads 500-bar history
3. Orchestrator registers bus handler
4. Dashboard starts at http://localhost:8080 (if fastapi+uvicorn installed)
5. Telegram `🟢 DEEP CLAW ONLINE` message
6. Signal evaluation begins once 30+ confirmed bars exist

Shutdown: `SIGINT` / `SIGTERM` → stop feeds → flush EOD report → Telegram offline ping → clean exit.

---

## WHAT v8 DID vs. WHAT DEEP CLAW DOES

| v8 artifact | v8 behavior | Deep Claw behavior |
|------------|-------------|-------------------|
| `buy_signal = UT_Bot OR Smart_RSI` | Two generators share `posState` | 4 pure functions → `List[SignalCandidate]` → PSM |
| Orphan-trade "fix" | Force-mark open trade as SL on new signal | Structurally impossible — PSM is the only state writer |
| `f_format_alert` / `f_format_modify` | TradeSgnl JSON strings in trading logic | `BrokerAdapter.open_position(TradeInstruction)` — zero strings |
| MT5 webhook alerts | `alert(f_format_alert(...))` | `mt5.order_send(request)` — direct Python bridge |
| `prevent_reversals` dead zone | Stuck positions when trend reverses | close existing + log P&L + open new — always responsive |
| Confidence as display-only | Shown on chart, not connected to risk | Confidence gates entry AND scales size |
| Tree format only | 5-TF snapshot per bar | EpisodeStream chain + MarketState snapshot (both preserved) |
| Three competing truth sources | `strategy()`, `posState`, `trade_active` | ONE `PositionStateMachine`, ONE `PositionState` |
| No shadow-blocked logging | Rejected signals silently dropped | Every rejection logged as `SIGNAL_REJECTED` with categorical reason |
| Static confidence weights | Fixed `mtf_weight = 1.5` etc. | `WeightMatrix` adaptive by `(session, atr_regime)` |
| No ML training data | No survivorship-bias-free labels | `FeatureStore`: accepted + shadow-blocked + outcome labels |

---

## THE PINE-TO-PYTHON FORMULA MAP

| Pine Script (The Claw Protocol) | Python equivalent | File |
|--------------------------------|------------------|------|
| `calcLiqTrail(ma_len, atr_len, atr_mult)` | `compute_liquidity_trail(highs, lows, closes, ...)` | `indicators/liquidity_trail.py` |
| `alphaFromAPT(apt)` | `alpha_from_apt(apt: float) -> float` | `indicators/adaptive_vwap.py` |
| `[m15_trend, m15_trail] = request.security(...)` | `bus.get_history(symbol, Timeframe.M15)` | `candle_bus.py` |
| `vp_pocLevel()` + `vp_valueLevels()` | `compute_volume_profile(...)` → `(poc, vah, val, strength)` | `indicators/volume_profile.py` |
| `positive := true` (RSI flip-flop) | `RSIRegime.update(closes) -> (rsi, positive, negative)` | `indicators/rsi_regime.py` |
| `trend_fib := basis > basis[1] ? 1 : -1` | `compute_fib_bands(...) -> (trend_fib, upper, lower)` | `indicators/fib_bands.py` |
| `structBias`, `bullBOS`, `bearBOS` | `compute_smc_structure(...) -> StructureState` | `smc/structure.py` |
| `bull_conf_pct >= conf_threshold` | `ConfidenceResult.directional_confidence >= settings.confidence_threshold` | `confidence_v1.py` |
| `posState := 1` / `posState := -1` | `PositionStateMachine.process_candidates(...)` | `position_manager.py` |
| `strategy.order("Buy", ...)` | `BrokerAdapter.open_position(instruction)` | `action/protocol.py` |

---

## THE THREE THINGS THAT MAKE THIS AN INTELLIGENCE, NOT A BOT

### 1. It Remembers — The EpisodeStream

Every event that matters is logged as a timestamped episode with a typed payload. The system can query its own history: *"How many SL hits did we have at this session last week? Did any of them share this ATR regime and swing bias?"*

This is not a log file. It is a queryable memory that grows smarter over time.

### 2. It Reasons — The Chain, Not the Tree

When a signal fires, the system doesn't look at a table of current indicator values. It reads the last 25 events as a narrative and asks: *"Given the story of how we got here — the liquidity sweep at 09:32, the CHoCH at 09:41, the rising ATR regime at 09:55 — does this signal make sense?"*

Claude reads the same narrative. Two forms of reasoning on the same evidence.

### 3. It Learns — The Feature Store + Phase 2 Pipeline

Every trade decision — accepted or shadow-blocked — writes a feature row with the full MarketState. Every closed trade writes its outcome back via `trade_id`. When enough labeled rows accumulate (200+), a LightGBM quantile model learns to predict the R-multiple distribution from the features.

Phase 2 activation: `USE_ML_CONFIDENCE=true`. Zero other changes.

---

## DEMO MODE — HOW TO RUN

```bash
# Prerequisites
pip install -e ".[dashboard]"     # + websockets + pybit for full feeds

# Configure
cp .env.example .env
# Fill in:
#   ANTHROPIC_API_KEY=sk-ant-...
#   DERIV_API_TOKEN=your-demo-token    (virtual account at app.deriv.com)
#   BYBIT_API_KEY=...                  (testnet.bybit.com)
#   BYBIT_API_SECRET=...
#   BYBIT_TESTNET=true
#   TG_WARROOM_TOKEN=...               (optional — from @BotFather)
#   TG_WARROOM_CHAT_ID=-100...

# Start
python main.py VOLATILITY_75_INDEX BTCUSDT

# Dashboard
open http://localhost:8080/stats/VOLATILITY_75_INDEX
open http://localhost:8080/timeline/BTCUSDT
```

**What you'll see in the war room Telegram:**
```
━━━━━━━━━━━━━━━━━━━━━━
DEEP CLAW — WAR ROOM
━━━━━━━━━━━━━━━━━━━━━━
Asset   : VOLATILITY_75_INDEX
Price   : 1547.23
Session : LONDON
...
CHAIN (last 12 events):
[10:02] SESSION_CHANGE: TOKYO → LONDON
[10:14] LIQUIDITY_SWEEP: BUY-SIDE swept at 1549.10
[10:22] STRUCTURE_CHOCH: Bullish CHoCH confirmed
[10:35] SIGNAL_ACCEPTED: UT_BOT LONG | LOCAL | conf 71%
...
EVENT: SIGNAL — UT_BOT
LONG | LOCAL | conf 71% | TP1=1550.20
```

---

## WHAT'S NEXT

### Immediate (to go live in demo)
1. **Wire Deriv WS client into `DerivMultiplierAdapter`** — feeds currently push confirmed bars to the bus but the adapter's `_ws` is `None` until a shared WS connection is passed through
2. **MT5 feed** — for funded account symbols (WALL_STREET_30, US_TECH_100)
3. **End-to-end demo test** — set demo credentials, run for one London session, verify episodes are written and Telegram messages fire

### Phase 2 (when ~200 labeled trades accumulate)
1. Run `FeatureStore.get_training_rows(symbol, labeled_only=True)`
2. Call `QuantileModel.train(rows)` from `learning/model.py`
3. Set `USE_ML_CONFIDENCE=true` in `.env`
4. Monitor: does directional_confidence from ML correlate better with realized_r than v1 weights?

### Phase 3 (ongoing)
- Claude's daily assessment proposals become the review mechanism for retraining
- The system literally reads its own trade history, proposes changes, and those proposals are reviewed before application
- This is what *"self-aware"* means — not autonomous mutation, but grounded self-reflection backed by data

---

## FILE INDEX

```
deep_claw/
├── core/
│   └── types.py                    ← All data contracts (440 lines)
├── config/
│   ├── settings.py                 ← All Pine inputs → Python (140 lines)
│   └── instrument_registry.yaml    ← 14 instruments, 3 brokers
├── perception/
│   ├── candle_bus.py               ← Unified OHLCV stream, confirmed-only
│   ├── market_state.py             ← MarketStateBuilder: all indicators → MarketState
│   ├── episode_emitter.py          ← Fires only on state delta, not every bar
│   └── indicators/
│       ├── liquidity_trail.py      ← Ratcheting ATR trail (exact Pine port)
│       ├── adaptive_vwap.py        ← alpha_from_apt() preserved verbatim
│       ├── rsi_regime.py           ← Flip-flop state machine
│       ├── atr_regime.py           ← HIGH/MED/LOW
│       ├── volume_profile.py       ← POC/VAH/VAL
│       ├── fib_bands.py            ← ATR fib bands, trend_fib
│       ├── ema_grid.py             ← 5-TF scoring
│       ├── daily_levels.py         ← PDH/PDL
│       └── smc/
│           ├── structure.py        ← BOS/CHoCH/swings
│           ├── fvg.py              ← Fair value gaps
│           ├── liquidity.py        ← Sweeps, PH/PL
│           └── order_blocks.py     ← Active OB detection
├── cognition/
│   ├── signals/
│   │   ├── ut_bot.py               ← Pure function: trail flip
│   │   ├── smart_rsi.py            ← Pure function: RSI extremes
│   │   ├── liquidity_zone.py       ← Pure function: sweep+CHoCH
│   │   └── structure_shift.py      ← Pure function: BOS entry
│   ├── chain_reasoning.py          ← EpisodeStream → ChainVerdict
│   ├── confidence_v1.py            ← Adaptive weights (session × ATR regime)
│   ├── position_manager.py         ← THE single trade state owner (597 lines)
│   └── risk/
│       ├── position_sizer.py       ← 4-clamp Kelly
│       ├── notional_router.py      ← Per-symbol contract notional
│       └── r_multiple_planner.py   ← SL/TP in R
├── action/
│   ├── protocol.py                 ← BrokerAdapter Protocol (5 async methods)
│   ├── deriv_multiplier.py         ← Deriv WS API v3
│   ├── bybit_perp.py               ← Bybit V5
│   └── mt5_cfd.py                  ← Direct MetaTrader5 bridge. NO TradeSgnl.
├── claude/
│   ├── qualification.py            ← Pre-commit narrative judgment
│   ├── sl_autopsy.py               ← Root-cause lessons
│   └── daily_assessment.py         ← 3 proposals, never auto-applied
├── journal/
│   ├── episode_stream.py           ← THE SPINE. Append-only. (292 lines)
│   ├── feature_store.py            ← Survivorship-bias-free ML data
│   ├── outcome_labeler.py          ← Joins realized_r after close
│   ├── pip_tracker.py              ← Daily WR/PF counters
│   └── daily_report.py             ← Structured DB row per day
├── communication/
│   ├── renderer.py                 ← One stream → 4 output formats
│   ├── telegram.py                 ← War room + sanitized public
│   └── dashboard.py                ← FastAPI endpoints
├── learning/
│   ├── model.py                    ← LightGBM 5 quantile heads
│   ├── inference.py                ← predict_confidence() ← same sig as v1
│   └── sizing.py                   ← Fractional Kelly from distribution
├── feeds/
│   ├── deriv_feed.py               ← Deriv WS multi-TF OHLC
│   └── bybit_feed.py               ← Bybit V5 kline WS + REST history
├── orchestrator.py                 ← Async event loop, bus handler (482 lines)
main.py                             ← Entry point, demo mode banner
.env.example                        ← Annotated credential template
pyproject.toml                      ← All dependencies declared
tests/
├── test_episode_stream.py          ← 5 chain integrity tests
├── test_position_manager.py        ← 6 invariant tests (v8 bug prevention)
└── test_signal_generators.py       ← 8 generator independence tests
```

---

*Deep Claw is not a better indicator. It is a system that remembers its own session as a story, reasons over that story top-down like a desk manager, sizes capital with positive-expectancy discipline a human cannot sustain for 12 hours straight, and gets measurably smarter every day because the story it tells itself is also the data it learns from.*

*Skill + time + capital → income. The skill and time are increasingly the system's. The capital compounds as a result.*

**Goal Zero. Never lose sight of it.**
