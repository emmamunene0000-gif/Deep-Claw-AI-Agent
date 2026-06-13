# DEEP CLAW MIGRATION CHEAT SHEET
## ADSA v7.0 ("Absolute Dollar Agent") + ATM Protocol Liquidity Suite → Python
### Master reference for porting Pine Script v6 logic into Deep Claw (FastAPI / Deriv / Bybit / MT5)

---

## 0. HOW TO USE THIS DOCUMENT

This is the **single source of truth** for the Python migration. It contains:

1. **Architecture map** — every subsystem in both Pine scripts, mapped to a Python module
2. **Inputs cheat sheet** — every input/setting, grouped, with Python equivalent (config/env var)
3. **Dashboard cheat sheet** — every field on both dashboards, its data source, formula, and refresh logic
4. **Alerts cheat sheet** — every alert/event, its trigger condition, message template, and Telegram routing
5. **Watchlist cheat sheet** — the asset universe (from screenshots) mapped to asset-class routing rules
6. **Asset-execution best practices** — Deriv Multipliers, Deriv Vanilla Options, Bybit Perpetuals, MT5/Deriv CFD
7. **Claude Code build prompt** — drop-in prompt to generate the `learning/` module + execution adapters

---

## 1. ARCHITECTURE MAP — 17(+8) SUBSYSTEMS → PYTHON MODULES

| # | Pine Subsystem | Source File | Python Module (Deep Claw) | Status (per memory) |
|---|---|---|---|---|
| 1 | Fractal 4-Layer Consensus (Sovereign/Anchor/Filter/Exec) | ADSA v7.0 §8 | `core/fractal_sync.py` | Needs verification |
| 2 | Composite 5-TF Scoring Engine (±15) | ADSA v7.0 §20 | `core/scoring.py` | Needs verification |
| 3 | Glass Box Alert Architecture | ADSA v7.0 §26 | `alerts/glassbox.py` | Likely partial |
| 4 | Trade Progression Engine (TP1/TP2/TP3/Holder) | ADSA v7.0 §16 | `core/trade_progression.py` | Needs verification |
| 5 | SL Autopsy Engine | ADSA v7.0 §25 | `alerts/sl_autopsy.py` | Needs verification |
| 6 | Signal Rejection Reports | ADSA v7.0 §26 (rejection_alert) | `alerts/rejection.py` | Needs verification |
| 7 | SMC Engine (BOS/CHoCH/OB/FVG/EQH-EQL/Premium-Discount/Liquidity) | ADSA v7.0 §17-19 | `smc/structure.py`, `smc/order_blocks.py`, `smc/fvg.py`, `smc/liquidity.py` | **Highest priority gap** — this is the most code-heavy section |
| 8 | Adaptive VWAP + Volume Profile + Fibonacci Bands | ADSA v7.0 §4-5, §12-13 | `indicators/adaptive_vwap.py`, `indicators/volume_profile.py`, `indicators/fib_bands.py` | Needs verification |
| 9 | Platinum Risk Model (asset-routed sizing) | ADSA v7.0 §3, §14 | `risk/notional_router.py`, `risk/position_sizer.py` | **Critical** — feeds Kelly sizing engine |
| 10 | Dual Telegram Broadcast (War Room + Public) | ADSA v7.0 §10, §26 | `notifications/telegram_dispatcher.py` | Likely implemented (war room exists) |
| 11 | Super Admin Control Panel (Bias/Silence/Override/Asset Note) | ADSA v7.0 §2 | `core/admin_controls.py` (config-driven, not UI) | Needs verification |
| 12 | Trade ID Engine (`ATM-YYYYMMDD-HHMM-DIR-N`) | ADSA v7.0 §15 | `core/trade_id.py` | Trivial — quick win |
| 13 | Pip Tracker (actual vs expected, daily reset, PF) | ADSA v7.0 §21 | `journal/pip_tracker.py` | Feeds outcome labeler |
| 14 | Performance Table (5-col dual table) | ADSA v7.0 §24 | `dashboard/perf_table.py` (data only — UI optional) | Low priority for headless agent |
| 15 | Daily Report Engine + ML Data Block | ADSA v7.0 §28 | `journal/daily_report.py` | **Critical** — direct feed to `learning/` |
| 16 | Live Dollar P&L Tracker | ADSA v7.0 §3, §23 | `risk/live_pnl.py` | Trivial — quick win |
| 17 | PDH/PDL Context Engine | ADSA v7.0 §15.5 | `indicators/daily_levels.py` | Trivial — quick win |
| 18 | MTF Liquidity Trail (3-EMA/ATR trailing stop, per TF) | ATM Protocol §3 | `indicators/liquidity_trail.py` | **New vs ADSA** — needed for liquidity suite parity |
| 19 | Liquidity Zones (pivot-based S/D boxes, break/retest) | ATM Protocol §4 | `smc/liquidity_zones.py` | **New vs ADSA** |
| 20 | UT Bot (ATR trailing-stop signal, dual sensitivity) | ATM Protocol §5 | `signals/ut_bot.py` | Overlaps ADSA ATM Bot — unify |
| 21 | Decision Matrix (MTF gate × regime × trigger source) | ATM Protocol §6 | `core/decision_matrix.py` | **New vs ADSA** — this is the weighted-signal-matrix predecessor |
| 22 | Position Tool (R-multiple TP1/2/3 box from entry+trail SL) | ATM Protocol §7 | `risk/r_multiple_planner.py` | Directly feeds **outcome labeler (MFE/MAE in R)** |
| 23 | Smart Trading Plan Dashboard (pre-flight checklist) | ATM Protocol §8 | `dashboard/preflight_checklist.py` | Feature-store candidate — checklist booleans = features |
| 24 | Volume Profile (POC/VAH/VAL/Value-Area strength) | ATM Protocol §2 | shared with #8 | Needs verification |

> **Note:** ADSA and ATM Protocol both implement Volume Profile, Adaptive VWAP, RSI Regime, Fib Bands, and a UT-style ATR trailing stop — almost identically. **Deduplicate** into shared `indicators/` modules so both the "Sovereign/Anchor/Filter/Exec" sync and the "MTF Trail + Decision Matrix" logic read from the same indicator outputs. This is a core architectural decision for Deep Claw.

---

## 2. INPUTS CHEAT SHEET

### 2.1 ADSA v7.0 — Super Admin / Control Layer
| Pine Input | Type | Default | Python Config Key | Notes |
|---|---|---|---|---|
| Sovereign TF | timeframe | "D" | `SOVEREIGN_TF` | Macro veto layer |
| Manual Bias Override | enum | AUTO | `ADMIN_BIAS` (AUTO/FORCE_BULL/FORCE_BEAR/SILENCE) | Should be hot-reloadable (DB row, not env var) |
| Asset Context Note | string | "" | `ASSET_CONTEXT` | Appended to all broadcasts |
| Operator Commentary | string | "" | `OPERATOR_NOTE` | War Room only |
| Sanitize Public Channel | bool | true | `TG_PUBLIC_SANITIZE` | |

### 2.2 Telegram / Broadcast
| Pine Input | Python Config Key |
|---|---|
| Premium/War Room enable + chat ID | `TG_WARROOM_ENABLED`, `TG_WARROOM_CHAT_ID` |
| Public/Free enable + chat ID | `TG_PUBLIC_ENABLED`, `TG_PUBLIC_CHAT_ID` |
| Bitget webhook enable | `BITGET_WEBHOOK_ENABLED` (legacy — replace with Bybit/Deriv adapters) |

### 2.3 Fractal 4-Layer Protocol
| Pine Input | Default | Python Key |
|---|---|---|
| Anchor TF (Layer 2 Commander) | "15" | `ANCHOR_TF` |
| Filter TF (Layer 3 Navigator) | "5" | `FILTER_TF` |
| Exec TF | chart TF | `EXEC_TF` (= bot's primary candle TF) |

### 2.4 ATM Bot / UT Bot
| Pine Input | Default | Python Key |
|---|---|---|
| Buy Sensitivity (`a_buy`) | 3.5 (ADSA) / 1.5 (ATM Protocol) | `UT_BUY_SENS` |
| Buy ATR Period (`c_buy`) | 2 | `UT_BUY_ATR_LEN` |
| Sell Sensitivity (`a_sell`) | 3.5 / 1.5 | `UT_SELL_SENS` |
| Sell ATR Period (`c_sell`) | 2 | `UT_SELL_ATR_LEN` |
| Enable Regime Filter | true | `REGIME_FILTER_ENABLED` |
| Require VWAP Confirmation | true | `REQUIRE_VWAP` |
| Require Fib Trend Confirmation (ATM Protocol only) | false | `REQUIRE_FIB_TREND` |
| Trail Gate for UT signals (ATM Protocol only) | true | `USE_TRAIL_GATE` |

### 2.5 Risk Management (Platinum Risk Model)
| Pine Input | Default | Python Key | Used by |
|---|---|---|---|
| Risk Per Trade ($) | 25.0 | `RISK_PER_TRADE_USD` | `_get_position_size()` |
| SL Buffer (ATR multiplier) | 0.5 | `SL_BUFFER_ATR_MULT` | SL calc |
| Show Min-Unit Actual Risk | true | `SHOW_MIN_UNIT_RISK` | display only |

**Asset notional router (`_get_contract_notional`)** — **critical bug-fixed logic, port exactly**:
```python
def get_contract_notional(symbol_type: str, point_value: float | None) -> float:
    pv = point_value if point_value else 1.0
    if symbol_type == "forex":   return 100_000.0
    if symbol_type == "crypto":  return 1.0
    if symbol_type == "futures": return pv
    return pv
```
- `risk_at_min_lot(sl_distance)` = reference risk at min tradable unit (0.01 lot forex/crypto, 1.0 futures)
- `get_position_size(sl_distance)` = `risk_per_trade / (sl_distance * notional)`, rounded to 4dp
- `live_pnl(entry, current, direction, pos_size)` = `(diff) * pos_size * notional`

### 2.6 LinReg / Signal Smoothing
| Pine Input | Default | Python Key |
|---|---|---|
| Signal Smoothing length | 21 | `SIGNAL_SMOOTH_LEN` |
| Simple MA signal (vs EMA) | true | `SIGNAL_USE_SMA` |
| Use LinReg Candles | false (ADSA) / true (ATM Protocol) | `USE_LINREG_CANDLES` |
| LinReg length | 11 | `LINREG_LEN` |

### 2.7 Longevity Zones
| Pine Input | Default | Python Key |
|---|---|---|
| Show Zones | false/true | `SHOW_LONGEVITY_ZONES` (visual only — likely skip in headless agent) |
| Zone Length | 5 | `LONGEVITY_ZONE_LEN` |

### 2.8 Adaptive VWAP
| Pine Input | Default | Python Key |
|---|---|---|
| Swing Period (`prd`) | 50 | `VWAP_SWING_PERIOD` |
| Adaptive Tracking (`baseAPT`) | 20 | `VWAP_BASE_APT` |
| Adapt by ATR (`useAdapt`) | false | `VWAP_ADAPT_BY_ATR` |
| Volatility Bias | 10.0 | `VWAP_VOL_BIAS` |

Core formula (port exactly):
```python
def alpha_from_apt(apt: float) -> float:
    decay = math.exp(-math.log(2.0) / max(1.0, apt))
    return 1.0 - decay
```
EMA-style running VWAP: `p_vwap = (1-alpha)*p_vwap + alpha*(hlc3*volume)`, `vol_vwap` likewise; `vap = p_vwap/vol_vwap`. Re-anchors on swing flip (`dir_vwap` = `phL > plL ? 1 : -1`, based on `highestbars`/`lowestbars` over `prd`).

### 2.9 Fibonacci Bands
| Pine Input | Default | Python Key |
|---|---|---|
| Source | hlc3 | `FIB_SOURCE` |
| Length | 21 (ADSA) / 200 (ATM Protocol) | `FIB_LEN` |
| ATR Length | 14 | `FIB_ATR_LEN` |
| Use ATR (vs stdev) | true | `FIB_USE_ATR` |

`basis = EMA(EMA(src, len), len)`; `trend_fib = 1 if basis>basis[-1] else -1 if basis<basis[-1] else trend_fib[-1]`. Bands at 0.618 / 2.618 × ATR (or stdev) from basis, only on the active-trend side.

### 2.10 RSI Momentum Regime
| Pine Input | Default | Python Key |
|---|---|---|
| RSI Length | 14 | `RSI_LEN` |
| Positive Above | 55 (ADSA) / 50 (ATM Protocol) | `RSI_POS_THRESH` |
| Negative Below | 45 (ADSA) / 50 (ATM Protocol) | `RSI_NEG_THRESH` |

State machine: `positive=True` when `rsi[-1]<thresh_pos and rsi>thresh_pos and rsi>thresh_neg and Δema5(close)>0`; `negative=True` when `rsi<thresh_neg and Δema5(close)<0`. Each flips the other off.

### 2.11 Volume Profile (shared, both scripts)
| Pine Input | Default | Python Key |
|---|---|---|
| Enable | true | `VP_ENABLED` |
| Session Type | Daily | `VP_SESSION_TYPE` (Tokyo/London/NY/Daily/Weekly/Monthly/Quarterly/Yearly) |
| Resolution | 30 | `VP_RESOLUTION` |
| Value Area % | 70 | `VP_VA_WIDTH` |
| Profile Data Type | Volume | `VP_DATA_TYPE` (Volume/OpenInterest) |
| Smooth Volume | false | `VP_SMOOTH_VOL` |

Outputs: `POC`, `VAH`, `VAL`. ATM Protocol adds `vp_strength`: `"ABOVE VAH"` / `"BELOW VAL"` / `"IN VALUE AREA"` — **this is a clean categorical feature for the ML feature store.**

### 2.12 SMC Inputs (ADSA only — the heavy structural engine)
| Group | Key Inputs | Python Key prefix |
|---|---|---|
| General | Mode (Historical/Present), Style (Colored/Monochrome) | `SMC_MODE`, `SMC_STYLE` (visual — low priority for headless) |
| Internal Structure | Show internal BOS/CHoCH, confluence filter | `SMC_INTERNAL_*` |
| Swing Structure | Show swing BOS/CHoCH, swings length (50) | `SMC_SWING_LEN=50` |
| Order Blocks | Internal/Swing OB size (5), OB filter (ATR/Range), mitigation (Close/HighLow) | `SMC_OB_*` |
| EQH/EQL | Bars confirmation (3), threshold (0.1×ATR) | `SMC_EQHL_LEN=3`, `SMC_EQHL_THRESH=0.1` |
| Fair Value Gaps | Auto threshold, extend bars (1) | `SMC_FVG_*` |
| Daily/Weekly/Monthly Levels | Show + style | `SMC_LEVELS_*` (visual) |
| Premium/Discount Zones | Show, colors | `SMC_PD_ZONES` |
| Liquidity (Swings & Volume) | Pivot lookback (14), swing area (Wick/Full), filter by Count/Volume | `LIQ_PIVOT_LEN=14`, `LIQ_AREA`, `LIQ_FILTER_*` |

### 2.13 ATM Protocol — MTF Trail / Zones / Position Tool (new vs ADSA)
| Pine Input | Default | Python Key |
|---|---|---|
| MA Length (trail basis) | 200 | `TRAIL_MA_LEN` |
| ATR Length (trail) | 14 | `TRAIL_ATR_LEN` |
| Trail Distance (ATR mult) | 1.25 | `TRAIL_ATR_MULT` |
| Swing Lookback (zones) | 14 | `ZONE_SWING_LEN` |
| Max Zones | 3 | `ZONE_MAX_COUNT` |
| Zone Thickness (ATR mult) | 0.35 | `ZONE_ATR_MULT` |
| Keep Broken Zones | true | `ZONE_KEEP_BROKEN` |
| Entry Mode | "Signal Change" | `POS_ENTRY_MODE` ("signal_change"/"trail_retest") |
| TP1/TP2/TP3 (R) | 1.0/2.0/3.0 | `TP_R_MULTIPLES = [1.0, 2.0, 3.0]` |
| Use Liquidity Zone Entries | true | `USE_ZONE_SIGNALS` |
| MTF Gate Mode | "M15 Only" | `MTF_GATE_MODE` (none/m15_only/m15_h1/m5_for_m1) |

---

## 3. DASHBOARD CHEAT SHEET

### 3.1 ADSA v7.0 Main Dashboard (single-cell table, top-right by default)

| Panel Block | Field | Source / Formula |
|---|---|---|
| Header | "🚀 ABSOLUTE DOLLAR AGENT" | static |
| Admin/Sovereign | `🔐 {admin_manual_bias} \| 👑 Sovereign ({sovereign_tf}): {sovereignStatus}` | `sovereignStatus` = sign of `sovereign_state` (D-TF posState via `request.security`) |
| Asset Context | `📌 {asset_context}` | input, conditional |
| Score line | `📊 Score: {total_score}/15 \| Public: SANITIZED/FULL` | `total_score` = sum of 5 layer scores |
| **Fractal Sync block** | L1 Sovereign / L2 Anchor / L3 Filter / L4 Exec status | `posState` per-TF via `request.security(tf, posState)` |
| | `agent_sync_phase` | state machine — see §4 below |
| **Core Signals** | Ticker + TF + price | `_p(close)` |
| | Session + ATR state | `current_session` (NY/London/Tokyo by UTC hour), `atrHL` = High/Med/Low vs 20-SMA of ATR(14) |
| | Daily Context | `pdh_pdl_status` — Above PDH / Below PDL / Inside Range |
| | ATM/Regime/VWAP/Fib/RSI icons | posState, regimeBullish/Bearish, lastSwing, trend_fib, rsi vs thresholds |
| **MTF EMA(9/21)** | 1m/5m/15m/30m/1H/4H/1D/1W/1M arrows | `emaTrend_tf(tf)` = EMA9 > EMA21 ? "G" : "R", per TF via `request.security` |
| **5-Layer AI Narrative** | `effective_bias`, `total_score`, `tree_narrative` | see §4 (scoring) and §5 (tree narrative format) |
| **Agent Advice** | `ai_advice` string | threshold ladder on `total_score` |
| **Liquidity** | `liq_bias`, Buy-side (`ph_top`), Sell-side (`pl_btm`) | pivot-high/low levels from Liquidity Swings Engine |
| **Trade Setup** | `tradeSection` (phase, ID, direction, risk/size, live P&L, entry/SL/TP1-3, holder trail, peak pips) | see §3.3 |
| **Today** | Sigs/Blocked/LDN/NY counts, TP1/2/3/SL counts, WR/PF/Net | from `dpt_*` daily arrays + `pip_*` tracker |
| **Report status** | `✅ SENT` or `⏳ HH:00 UTC` | `dpt_report_sent` flag |
| Footer | disclaimer + copyright | static |

### 3.2 ADSA v7.0 Performance Table (separate 5×10 table, bottom-left by default)

| Row | Columns: Metric / Unit / Actual / Expected / Hits |
|---|---|
| TP1 (1:1) | avg actual pips to TP1 vs expected (= risk_dist×1.0), hit count |
| TP2 (1.5:1) | avg actual vs expected (risk_dist×1.5), hit count |
| TP3 (2:1) | avg actual vs expected (risk_dist×2.0), hit count |
| Stop Loss | avg actual SL distance vs expected (= risk_dist), loss count |
| Profit Factor | `pip_pf` = gross_wins/gross_loss (capped display 99.9, "∞" if losses=0), tag via `_pf_tag` (ELITE ≥2.5 / STRONG ≥2.0 / GOOD ≥1.5 / MARGINAL ≥1.0 / NEGATIVE <1.0); Win Rate = wins/total_signals |
| Net pips today | `pip_net = gross_wins - gross_loss`, plus total_score, W/L record |
| Footer | branding |

**All daily counters reset at `dayofmonth != pip_last_day` (pip tracker) and `dayofweek != dayofweek[1]` (dpt_* daily-performance arrays).** Port both reset triggers as a single "new trading day" event in Python keyed off broker server date.

### 3.3 Trade Setup Block (detail)
```
📊 Phase: {trade_phase_display}      # WAITING/ENTRY/TP1_HIT/TP2_HIT/TP3_HIT/HOLDER_MODE/SL_HIT
ID: {atm_trade_id}                   # ATM-YYYYMMDD-HHMM-DIR-N
Dir: 🟢 LONG / 🔴 SHORT
💡 Min-Unit Risk: ~${locked_actual_risk} | Variable: ${risk_per_trade} → {size}
💵 Live P&L: {pnl_str} (+/-{pips} {unit})
🚪 Entry: {entry}  🛑 SL: {sl}  ({pip_dist})
🎯 TP1: {tp1} [✅ if hit] ({pip_dist})
🎯 TP2: {tp2} [✅ if hit] ({pip_dist})
🚀 TP3: {tp3} [✅ if hit] ({pip_dist})
🔱 VWAP Trail: {vap_current}          # only if holder_mode_active
📈 Peak: {max_profit_pips} {unit}
```
**TP levels are fixed at signal confirmation** (`locked_tp1/2/3 = entry ± risk_dist × {1.0, 1.5, 2.0}`), SL computed from `max(EMA21, swing_low/high) ∓ ATR×sl_buffer`, with a fallback (`close ∓ ATR×1.5`) if the structural SL would be invalid (≥/≤ close).

### 3.4 ATM Protocol — "Smart Trading Plan" Dashboard (22-row × 3-col table)

| Row | Col 0 (Label) | Col 1 (State) | Col 2 (Logic/Gate result) |
|---|---|---|---|
| 0 | "🧠 ATM TRADING PLAN" header | "STATE" | "LOGIC" |
| 1 | "🌐 MTF MACRO CONTEXT" section header (merged) | | |
| 2 | M5 Trend | 🔺BULL/🔻BEAR/⚪NEUT | PASS/FAIL if `mtf_filter_mode == "M5 Gate (for M1)"`, else "⚪ OFF" |
| 3 | M15 Trend | same | PASS/FAIL if mode is M15-based |
| 4 | H1 Trend | same | PASS/FAIL if mode is "Both M15 & H1" |
| 5 | "🟢 LONG PRE-FLIGHT CHECKLIST" header | | |
| 6 | Trail Direction | BULL/BEAR (`ltf_trend`) | `long_trail_ok` |
| 7 | RSI Regime | POS/NEUT | `regimeBullish` |
| 8 | VWAP Anchor | BULL/BEAR (`lastSwing`) | `vwapBullish or not requireVWAP` |
| 9 | Fib Trend | BULL/BEAR (`trend_fib`) | `fibBullish or not requireFibTrend` |
| 10 | Vol Profile | `vp_strength` | `close > VAL` |
| 11 | "🔴 SHORT PRE-FLIGHT CHECKLIST" header | | |
| 12-16 | mirrors 6-10 for short side | | |
| 17 | "⚡ SIGNAL EXECUTION" header | | |
| 18 | Trigger | "⚡ UT BUY/SELL" or "🌊 LIQ LONG/SHORT" or "⏸ WAIT" | `matrix_bull or matrix_bear` |
| 19 | Action | "🟢 EXEC BUY/LONG", "🔴 EXEC SELL/SHORT", "⚪ BLOCKED" | merged cell, colored bg |
| 20 | "🎯 POS: {rr_status}" (merged) | `🟢 {R}R LONG` / `🔴 {R}R SHORT` / "—" | |

**This checklist is a direct feature vector** — each row's pass/fail boolean + the underlying numeric (RSI, trend_fib direction, VAH/VAL distance, MTF trend states) should become columns in the `feature_store`, including the shadow-tracked **blocked** signals (rows 6-16 fail but row 18/19 still record the would-have-fired trigger).

---

## 4. CORE STATE MACHINES (logic to port verbatim)

### 4.1 Fractal 4-Layer Sync (`agent_sync_phase`)
Inputs: `sovereign_state, anchor_state, filter_state, exec_state` ∈ {-1,0,1} (each = `posState` of UT Bot on its respective TF via `request.security`).

Admin override short-circuits everything:
- `SILENCE` → `"🔇 ADMIN SILENCE — STANDING ASIDE"`, no broadcasts except session-open silence pings
- `FORCE BULL` / `FORCE BEAR` → forces `master_sync_buy`/`sell` if the local confirmed signal matches

Otherwise, nested cascade (port as a decision tree, identical for bull/bear mirrored):
```
if sovereign==1:
  if anchor==1:
    if filter==1:
      if exec==1: "🔥 FULLY ALIGNED: BULLISH (4-LAYER)" → master_sync_buy = buy_signal_confirmed
      elif exec==-1: "L4 PULLBACK — Wait for Exec Bull Flip"
      else: "L4 NEUTRAL — Exec Waiting"
    elif filter==-1: "L3 PULLBACK — Wait for Filter Bull Flip"
    else: "L3 NEUTRAL — Navigator Flat"
  elif anchor==-1: "L2 PULLBACK — Wait for Anchor Bull Flip"
  else: "L2 NEUTRAL — Commander Flat"
elif sovereign==-1: (mirror, BEARISH)
else: "SOVEREIGN NEUTRAL — STANDING ASIDE"
```
Also computed: `sovereign_counter_buy` = confirmed long while `sovereign_state==-1` (counter-trend flag → TP1-only rule in SL autopsy / broadcast).

### 4.2 5-Layer Composite Scoring (`total_score`, -15..+15)
For each of 5 TFs (D / 4H / 1H / 15m / 5m), compute 3 sub-scores from `request.security`-fetched state:
- `r` (Regime): `"Long"` if `regimeBullish`, `"Short"` if `regimeBearish`, else `"Neut"`
- `v` (VWAP/lastSwing): `"Bull"` / `"Bear"` / `"Neut"`
- `f` (Fib trend): `"Bull"` / `"Bear"` / `"Neut"`
- `ri` (RSI): `"Bull"` if rsi>55, `"Bear"` if rsi<45, else `"Neut"`

`n_score(s)` = +1 for Long/Bull, -1 for Short/Bear, 0 for Neut. Layer score = `n_score(r)+n_score(v)+n_score(f)` (range -3..+3). `total_score` = sum of 5 layer scores (range -15..+15). RSI (`ri`) is **not** in the numeric score — it's display-only in the tree.

`master_bias` ladder (also gates `ai_advice`):
| Condition | master_bias |
|---|---|
| score≥10 & ATR=High | 🔥 SOVEREIGN HIGH MOMENTUM BULLISH |
| score≤-10 & ATR=High | 🔥 SOVEREIGN HIGH MOMENTUM BEARISH |
| score≥6 | 📈 BULLISH BIAS (Strong) |
| score≤-6 | 📉 BEARISH BIAS (Strong) |
| score≥3 | 📈 BULLISH BIAS (Moderate) |
| score≤-3 | 📉 BEARISH BIAS (Moderate) |
| score>0 | ⏳ QUIET BULL — WAIT |
| score<0 | ⏳ QUIET BEAR — WAIT |
| ==0 | ⚪ NEUTRAL — STAND ASIDE |

`effective_bias` overrides `master_bias` if admin override is active.

`ai_advice` ladder mirrors thresholds at ±10/±6/±3 with text: "Aggressive entry — 4-layer sovereign aligned." / "Confident entry..." / "Cautious entry..." / symmetric short versions / "Neutral. Stand aside. No edge present."

> **This is exactly the kind of hand-tuned threshold ladder the new ML layer should *replace* with a learned probability** — `total_score` (and the 15 underlying r/v/f/ri booleans across 5 TFs) is a 15-20 dim feature vector that should map to a **quantile distribution of R-multiple outcomes**, with `ai_advice` becoming a derived recommendation from the model's predicted distribution rather than a fixed ladder.

### 4.3 Tree-Format Narrative (`tree_narrative`)
For each of D / H4 / H1 / M15 / M5 (last one uses `└──` and no trailing `│`):
```
├── {TF} ({role}) {icon}
│    Regime :{r} V.WAP :{v} Fib Trend :{f} RSI:{ri}
```
`icon` = 🟢 if layer_score≥2.5, 🔴 if ≤-2.5, 🟡 if >0, 🟠 if <0, ⚪ if ==0.

### 4.4 Trade Progression State Machine (`trade_phase`)
States: `WAITING → ENTRY → TP1_HIT → TP2_HIT → TP3_HIT (→ HOLDER_MODE) | SL_HIT`

- On new confirmed signal: reset all hit-flags, `max_profit_pips=0`, phase=`ENTRY`
- Per bar while `trade_active`: update `max_profit_pips = max(max_profit_pips, pips(MFE))` — **this running MFE is exactly the `MFE` half of the MFE/MAE outcome labeler**
- TP1/TP2/TP3 checked sequentially (each requires the prior not yet hit and no SL yet)
- TP3 hit → `holder_mode_active=True`, phase=`TP3_HIT` then `HOLDER_MODE`
- SL check only fires if `not tp1_hit` (i.e., once TP1 is secured, "SL" in the classic sense no longer applies — position is risk-free)
- Holder exit: `close` crosses back through `vap_current` (Adaptive VWAP) — direction-aware (`crossunder` for longs, `crossover` for shorts)

Events (each fires once via `not X[1]` edge-detection, `barstate.isconfirmed`):
`tp1_alert_event, tp2_alert_event, tp3_alert_event, sl_alert_event, holder_exit_event, rejection_alert`

### 4.5 SL Autopsy Engine (`_build_sl_autopsy`)
Priority-ordered explanation generator, evaluated **at the moment SL is hit**:
1. `liq_bias` contains "BREAKING" → "LIQUIDITY TRAP: Institutions swept stop... widen buffer or wait for sweep confirmation"
2. `atrHL=="Low"` → "VOLATILITY COLLAPSE... RULE: Do NOT enter when ATR = Low"
3. `sovereign_state==-1 and trade_direction==1` (or mirror) → "SOVEREIGN VETO... Counter-trend = TP1 only. Never TP3"
4. `abs(total_score) < 4` → "WEAK 5-LAYER ALIGNMENT... RULE: Never enter when abs(score) < 4"
5. else → "MACRO ROTATION: Higher-TF structure shifted post-entry"

> **Port this as a labeling function for the outcome labeler / journal** — each SL-hit trade gets auto-tagged with one of these 5 root-cause categories, which becomes a categorical feature for the ML model (and a great human-readable journal field).

### 4.6 Trade ID Engine
`ATM-{YYYY}{MM}{DD}-{HH}{mm}-{BUY|SELL}-{daily_counter}`, daily_counter resets at `dayofmonth` change.

### 4.7 PDH/PDL Context
`request.security(tickerid, "D", [high[1], low[1]])` (lookahead off, no repaint). Status:
- `close > PDH` → `"🔼 Above PDH ({pdh})"`
- `close < PDL` → `"🔽 Below PDL ({pdl})"`
- else → `"↔ Inside Range [PDH: {pdh} | PDL: {pdl}]"`

---

## 5. ALERTS / BROADCAST CHEAT SHEET

### 5.1 Trigger Conditions (any → fires broadcast, unless `admin_manual_bias=="SILENCE"`)
| Event | Condition |
|---|---|
| Long/Short signal confirmed | `buy_signal_confirmed` / `sell_signal_confirmed` (posState flip + filters) |
| TP1/TP2/TP3 hit | edge of `tp{n}_hit` |
| SL hit | edge of `sl_hit_flag` |
| Holder exit | `holder_exit_event` (VWAP cross while in holder mode) |
| Rejection | `rejection_alert` = (`buy_rejected` or `sell_rejected`) — raw UT trigger fired but regime filter blocked it |
| Liquidity sweep | `close` crosses `ph_top` (buy-side) or `pl_btm` (sell-side) |
| Structure shift | `swingBullish/BearishBOS` or `CHoCH` |
| New session | `vp_newSession` (per Volume-Profile session definition) |
| Silence ping | `admin_manual_bias=="SILENCE"` AND `vp_newSession` |

### 5.2 Message Skeleton (War Room — full Glass Box)
```
━━━━━━━━━━━━━━━━━━━
🔥 ABSOLUTE DOLLAR — WAR ROOM
Supreme Agent ADSA v7.0
━━━━━━━━━━━━━━━━━━━
📊 Asset   : {ticker} | {tf}
💰 Price   : {close}
🌍 Session : {current_session}
📅 Daily   : {pdh_pdl_status}
📌 Context : {asset_context}            # if set
─────────────────────
🔔 EVENT: {event_title}
─────────────────────
📝 AGENT COMMENTARY
{event_commentary}
[🎯 TRADE PARAMETERS block]             # only on new signal — see 5.3
[🧠 GLASS BOX AI NARRATIVE block]       # always — see 5.4
[💬 OPERATOR NOTE]                       # if admin_commentary set
─────────────────────
🧊 LIQUIDITY
Buy-side  : {ph_top}
Sell-side : {pl_btm}
Context   : {liq_bias}
━━━━━━━━━━━━━━━━━━━
⚠️ Not financial advice. © 2026 Absolute Dollar
```

### 5.3 Trade Parameters Block (on entry signals only)
```
─────────────────────
🎯 TRADE PARAMETERS
─────────────────────
Direction  : 🟢 LONG / 🔴 SHORT
Entry      : {entry}
Stop Loss  : {sl}  ({pip_dist})
TP1 (1:1)  : {tp1}  ({pip_dist})
TP2 (1.5:1): {tp2}  ({pip_dist})
TP3 (2:1)  : {tp3}  ({pip_dist})
Risk $     : ${risk_per_trade} → {size_display}
Min-unit risk: ~${locked_actual_risk}    # if show_risk_info
Trade ID   : {atm_trade_id}
4-Layer    : {agent_sync_phase}
```

### 5.4 Glass Box AI Narrative Block (always present)
```
─────────────────────
🧠 GLASS BOX AI NARRATIVE
─────────────────────
Master Bias  : {effective_bias}
Score        : {total_score}/15
Daily Context: {pdh_pdl_status}
─────────────────────
5-LAYER TREE
{tree_narrative}
─────────────────────
💡 AGENT ADVICE
{ai_advice}
PF: {pf} WR: {wr}
```

### 5.5 Per-Event Commentary Templates
| Event | `event_title` | `event_commentary` summary |
|---|---|---|
| SL hit | "💀 STOP HIT — GLASS BOX AUTOPSY" | SL autopsy text + peak pips before stop + min-unit loss estimate + score at entry |
| Holder exit | "🏁 HOLDER MODE EXIT — VWAP CROSSED" | direction, VWAP trail level, peak run, "Close remaining position" |
| TP3 hit | "🚀 TP3 HIT — HOLDER MODE ACTIVATED (2:1)" | "Close 75% at TP3, trail 25% via Adaptive VWAP" |
| TP2 hit | "🎯🎯 TP2 HIT — MOVE STOP TO BREAKEVEN (1.5:1)" | "Take 50% off, move SL to entry, hunting TP3" |
| TP1 hit | "🎯 TP1 HIT — PARTIAL SECURED (1:1)" | "Take 25-33% off, tighten SL, next target TP2" |
| Rejection | "⛔ SIGNAL BLOCKED — REGIME FILTER" | which side blocked + sovereign status + score; "Silence = a position" |
| Master sync buy/sell | "🔥 MASTER SYNC LONG/SHORT — 4-LAYER ALIGNED" | all 4 layers aligned, score, ATR state, "R:R 2.0+ advised" |
| Counter-trend confirmed | "⚠️ SOVEREIGN COUNTER-TREND LONG/SHORT" | "Daily is BEAR/BULL. RULE: Target TP1 only. Do NOT hold to TP3" |
| Local signal | "🟢/🔴 LONG/SHORT SIGNAL CONFIRMED" | "Local alignment confirmed. Sovereign: {status}. Score + ai_advice" |
| Buy-side liquidity swept | "⚠️ BUY-SIDE LIQUIDITY SWEPT" | "Pool at {ph_top} swept. FALSE BREAK→reversal long / BREAKOUT→continuation. Wait for CHoCH/retest" |
| Sell-side liquidity swept | "⚠️ SELL-SIDE LIQUIDITY SWEPT" | mirror |
| Bullish/Bearish structure shift | "📈/📉 BULLISH/BEARISH STRUCTURE SHIFT (BOS/CHoCH)" | "{Buyers/Sellers} losing control. Scanning for {discount/premium} pullback. Score + Liq" |
| Session open | "🕒 SESSION OPEN — ENVIRONMENTAL SCAN" | session name + ATR/score-based readiness verdict + sovereign + liq_bias |
| Admin silence ping | "🔇 ADMIN SILENCE — STANDING ASIDE" | low-vol or mixed-alignment explanation, or "Operator discretion active" |

### 5.6 Public Channel (sanitized, if `tg_public_sanitize=true`)
Same header/event/footer structure, but commentary block is a **1-line generic version** of the above (e.g. TP1→"🎯 TP1 hit — partial secured."), and narrative block is reduced to `Bias / Score / Sync / Daily / Dir`, ending with "🔗 Full Glass Box report in War Room." If `tg_public_sanitize=false`, public channel = identical copy of War Room message.

### 5.7 Daily Report (fires once at `report_hour_utc`, resets at new trading day)
Sections: header → signal summary (total/blocked/long/short/sync4/local/counter) → outcomes (TP1/2/3/SL/Open counts, win rate, PF, net pips) → metrics (avg score, avg peak, ATR state, sovereign, session distribution) → trade log (numbered, one line per trade: direction, type, score, outcome, peak pips, bar count) → self-assessment (ladder based on win rate/avg score/SL-vs-TP ratio/counter-trend ratio) → operator note → **ML DATA BLOCK**:
```
[ATM_DATA_ADSA]
date=YYYY.MM.DD
asset=...  tf=...
signals=...  rejected=...
long=...  short=...
sync4=...  local=...  counter=...
tp1=...  tp2=...  tp3=...  sl=...  open=...
win_rate=...  avg_score=...
avg_pips=...  best_pips=...
pf=...  net_pips=...
london=...  ny=...  asia=...
atr_state=...  sovereign=...  total_score=...
[/ATM_DATA_ADSA]
```
**This block is the seed schema for the daily aggregation table in `journal/` — replicate field-for-field as a structured (JSON/DB row), not a text block, in Python.**

### 5.8 ATM Protocol alertconditions (separate from broadcast text — these are TradingView `alertcondition()` calls, i.e. raw boolean triggers for webhook automation)
| Alert | Condition |
|---|---|
| UT+Liq Long / Short | `final_long` / `final_short` |
| Long/Short Rejected | `rejected_long` / `rejected_short` |
| RSI Positive/Negative | `pcondition` / `ncondition2` |
| VP+UT Long/Short | volume-profile-at-VAL/VAH confluence + final signal |
| Position Tool Long/Short Entry | `do_bull_entry` / `do_bear_entry` |

### 5.9 Bitget/Bybit JSON payload (Section 27 — adapt for Bybit V5 order placement)
```json
{"action":"buy|sell","size":"{position_size}","symbol":"{ticker}","price":"{close}",
 "sl":"{locked_sl}","tp1":"{locked_tp1}","id":"{atm_trade_id}",
 "score":"{total_score}","sync":"{agent_sync_phase}"}
```

---

## 6. WATCHLIST CHEAT SHEET (from uploaded screenshots)

The live Deriv/MT5 watchlist spans 4 asset super-classes — each needs its own notional router branch and (eventually) its own scoring-threshold calibration:

| Class | Symbols (observed) | Notional Router Branch | Notes |
|---|---|---|---|
| **Synthetic Indices (Deriv)** | VOLATILITY_10/25_1S/50/75/100_INDEX, STEP_INDEX (200/300/400/500), JUMP indices (implied) | `crypto`-like (notional=1.0) but **trade via Multipliers/Vanillas, not perp futures** — separate execution adapter | 24/7, no session structure → `current_session` logic (Tokyo/London/NY) is meaningless here; PDH/PDL and session-based VP still apply since they're calendar-day based |
| **Forex Majors/Crosses** | XAUUSD, GBPUSD, EURAUD, NZDUSD, GBPJPY, EURJPY, EURUSD (implied) | `forex` (notional=100,000) | XAUUSD often quoted with `syminfo.type=="forex"` on Deriv/MT5 — verify pip size (`0.01` if ticker contains "JPY", else `0.0001`; gold needs custom pip definition, NOT the JPY/else default — **flag as a known edge case in `_pips()`**) |
| **Crypto** | SOLUSD, XRPUSD, NEARUSD, ALGOUSD | `crypto` (notional=1.0) — **Bybit perpetuals** for these | leverage/funding-rate considerations from Bybit research (§7.3) apply |
| **US/Global Equities & Indices** | TSLA, AAPL, META, GOOGL, HOOD, BABA, MSFT, NVDA, AMD, WALL_STREET_30, US_TECH_100, US_SMALL_CAP_2000, JAPAN_225, NETHERLANDS_25 | `futures`-like via `syminfo.pointvalue` if traded as Deriv CFDs/MT5 indices; equities likely traded as Deriv CFD shares | Confirm `syminfo.pointvalue` is non-null for these on Deriv MT5 feed — router falls back to `pv` (1.0) if null, which would mis-size |

### Watchlist → Execution Routing Table (build this as `config/instrument_registry.yaml`)
For each symbol, Deep Claw needs: `{symbol, deriv_symbol_code, bybit_symbol (if applicable), asset_class, pip_size, contract_notional, min_unit, session_profile (24/7 vs session-based), preferred_venue (deriv_multiplier | deriv_vanilla | bybit_perp | mt5_cfd)}`. This registry is the single config object both the Pine→Python indicator math (`_pips`, `_p`, notional router) AND the execution adapters read from — eliminates per-asset special-casing scattered through the codebase.

---

## 7. ASSET-SPECIFIC EXECUTION — BEST PRACTICES RESEARCH

### 7.1 Deriv Multipliers (Synthetic Indices, Forex, Crypto on Deriv)
- **Mechanism**: leverage without margin calls — loss is hard-capped at stake via an automatic stop-out. This is structurally different from MT5 CFD margin: there's no "margin level" to monitor, only **stake at risk**.
- **API flow** (`deriv-api`): `active_symbols` → `contracts_for(symbol)` → `proposal` (request a quote, get a `proposal_id`) → `buy(proposal_id, price)`. For multipliers, the `proposal` request includes `multiplier`, `basis` (stake), and a `limit_order` object.
- **`limit_order`** supports `take_profit` and `stop_loss` as **absolute P&L amounts** (not price levels) — this maps cleanly onto Deep Claw's `risk_per_trade` (stake) and TP1/2/3-in-$ once you convert `locked_tp{n}` price distance × position size × notional → dollar TP. **Recommendation**: at trade open, submit the contract with `stop_loss = locked_actual_risk` (or the variable-sized $ risk) and **no take_profit** (so TP1/2/3 partial-exit logic stays under Deep Claw's control rather than the broker's single TP), then manage TP1/TP2/TP3 as **partial `sell` calls** on the contract (Deriv multipliers support partial closes) plus SL **modification** via `update_contract` as the trade progresses (e.g., move SL to breakeven on TP2, per the existing Glass Box commentary).
- **Deal cancellation** ("cooling-off") windows (5/10/15/30/60 min) — a free "soft stop" Deep Claw could use on `MASTER SYNC` entries: if price reverses hard within the cancellation window and price action contradicts the entry premise (e.g., immediate CHoCH against direction), cancel for a full refund instead of eating the SL.
- **Risk per trade**: community guidance reiterates the classic 1-2% of equity per trade — this should be a **hard ceiling** on `risk_per_trade` in the Kelly sizing engine output (i.e., fractional-Kelly output is clamped to `min(kelly_size, 0.02 * equity)`).
- **Leverage**: typical multiplier ranges for volatility indices run from ~5x up to 100-200x; Deep Claw should treat the "multiplier" input itself as a tunable hyperparameter the ML layer could eventually adjust per-asset based on predicted outcome variance (higher predicted variance → lower multiplier for the same dollar risk).

### 7.2 Deriv Vanilla Options
- Vanilla options on Deriv are **defined-risk, premium-paid-upfront** instruments (call/put with strike + expiry), distinct from multipliers (which are leveraged CFD-like with no expiry beyond stop-out). Use `proposal` with `contract_type` = `VANILLALONGCALL`/`VANILLALONGPUT`, specifying `barrier` (strike) and `duration`.
- **Best fit in Deep Claw**: vanilla options suit the TP3/Holder-Mode "let it run" thesis with **zero downside beyond premium** — i.e., when the 5-layer score is extremely high (≥10, "SOVEREIGN HIGH MOMENTUM") and the predicted R-distribution has a fat right tail, a small vanilla-option allocation captures convexity that a multiplier (capped at TP via active management) cannot. Treat this as a **separate "lottery sleeve"** sized from a fixed small % of risk budget, not the primary execution path.
- Because vanillas have **time decay (theta)**, the entry timing must respect the holding-period implied by the setup's expected duration (`dpt_bar_count` distribution from the daily report's trade log is a good empirical estimate of expected hold time per signal type — feed this into expiry selection).
- Pricing/Greeks: since Deriv prices vanillas via its own proposal engine (no need to build a Black-Scholes pricer), Deep Claw only needs to compare the quoted premium against the model's predicted P(reach barrier before expiry) to decide if the vanilla is "cheap" relative to the ML-predicted outcome distribution — this is a natural second use of the distributional LightGBM model (predicted probability mass beyond the strike, vs. premium-implied probability).

### 7.3 Bybit Perpetual Futures
- **V5 unified API** (use `pybit`): one client handles spot/derivatives/options; supports **one-way** and **hedge** position modes — Deep Claw should run **one-way mode** (matches the single `posState`/`trade_direction` model in ADSA) unless a future "hedged sleeves" feature is added.
- **TP/SL via `set_trading_stop`**: Bybit V5 lets you attach/modify `takeProfit`/`stopLoss` directly on an open position (and choose TP/SL order type Market or Limit) — this is more native than Deriv's $ -based limit orders, so on Bybit, **port `locked_tp{1,2,3}` and `locked_sl` as actual price levels** directly into `set_trading_stop`, updating SL to breakeven on TP2 via the same call (matches existing "Move SL to entry" commentary).
- **Position sizing**: `qty = risk_per_trade_usd / (sl_distance_price * contract_value)`. For linear USDT perpetuals, `contract_value` is generally 1 (qty is in base-asset units), so this collapses to ADSA's `_get_position_size` with `notional=1.0` — confirms the existing `crypto` branch of `_get_contract_notional` is correct for Bybit linear perps.
- **Leverage**: set via `set_leverage` per-symbol; leverage choice should **not** affect `qty` (which is risk-derived) — leverage only affects margin required, so Deep Claw should pick the **minimum leverage that keeps margin requirement comfortably below a max-margin-utilization ceiling** (e.g., ≤30% of free margin), then size `qty` independently from risk. This decouples "how much I risk" from "how much margin I post," avoiding the classic mistake of conflating leverage with position size.
- **Risk Limits / ADL**: Bybit imposes tiered risk limits — large leveraged positions raise maintenance-margin requirements and ADL exposure. For a funded/scaling account, keep position notional well inside the lowest risk-limit tier unless `risk_per_trade` has scaled enough (via the Kelly engine) to justify tier review.
- **Funding rate**: for positions held through a funding timestamp (00:00/08:00/16:00 UTC), factor the funding rate into expected-value — particularly relevant for `HOLDER_MODE` (TP3+ trailing) positions that may span multiple funding intervals. This is a clean additional feature for the outcome labeler (`funding_paid_or_received` per trade).
- **WebSockets over REST polling** for the execution layer — Deep Claw's live feed (for trail/VWAP/structure updates) and order-fill confirmations should both be WebSocket-driven; reserve REST for setup/config calls (leverage, position-mode) and periodic reconciliation.

### 7.4 MT5 (Deriv CFDs) — "asset-agnostic" / Atlas funded account
- MT5 remains the right venue for **broad asset access** (the equity/index names in the watchlist: TSLA, AAPL, indices, JAPAN_225 etc.) where Deriv Multipliers/Vanillas and Bybit perps don't apply.
- For a **funded/prop account (Atlas)**: position sizing must additionally respect the **funded account's daily-loss and max-drawdown rules** as a hard outer constraint — i.e., `risk_per_trade` (or the Kelly-derived size) should be clamped not only by the 1-2% equity rule but by `remaining_daily_loss_budget / sl_distance_in_account_currency`, recomputed at the start of each trading day from the prop firm's reset rules. This becomes a third clamp layer alongside Kelly and the 1-2% rule: `final_size = min(kelly_size, pct_equity_cap, daily_loss_budget_cap)`.
- MT5 margin model means **leverage and margin-call/stop-out levels are real constraints** (unlike Deriv multipliers' stake-capped model) — the position sizer needs the account's leverage and the broker's margin-call % as inputs, and should keep `used_margin / equity` under a conservative ceiling (e.g., 20-30%) independent of the risk-per-trade calc, mirroring the "decouple leverage from sizing" principle from §7.3.
- Since MT5 is "asset-agnostic" in this setup, the `_get_contract_notional` router's `forex` (100,000) vs `futures` (`syminfo.pointvalue`) branches are the ones that matter most — **the instrument registry (§6) must carry the correct MT5 `pointvalue`/contract size per symbol**, since a wrong value here directly mis-sizes every trade (this was the exact bug fixed going from v6.0→v6.1).

### 7.5 Cross-cutting sizing principle for Deep Claw
```
position_size = min(
    kelly_fraction(predicted_R_distribution) * equity,   # ML-driven, scales with confidence
    0.02 * equity,                                        # hard 1-2% per-trade ceiling
    daily_loss_budget_remaining / sl_distance_in_$,       # prop/funded account constraint (MT5/Atlas)
    margin_headroom_implied_size                          # leverage/margin ceiling (Bybit/MT5)
)
```
All four clamps should be logged per trade in the journal — this gives the ML layer visibility into *when sizing was constrained by something other than its own confidence*, which is itself a useful feature (a trade sized at the Kelly optimum vs. one capped by the daily-loss budget have different "true" risk profiles even at the same $ amount).

---

## 8. CLAUDE CODE BUILD PROMPT — DROP-IN

Copy everything between the lines below into Claude Code (in the Deep Claw repo root) as the task brief.

```
You are working inside the Deep Claw repository (FastAPI-based algorithmic trading
intelligence system, deployed on Render, connected to Deriv and Bybit APIs, with
Claude API as a signal-qualification layer). Reference document:
`deep_claw_adsa_cheatsheet.md` (attached) contains the full Pine Script v6
specification (ADSA v7.0 + ATM Protocol Liquidity Suite) that the Python system
is meant to mirror.

PHASE 1 — AUDIT (do this first, output a written report before any code changes):
1. Walk the existing codebase and produce a gap report against Section 1
   (Architecture Map) of the cheat sheet: for each of the 24 subsystems, mark
   IMPLEMENTED / PARTIAL / MISSING, with file paths and a 1-line note on fidelity
   to the Pine logic (Section 4: Core State Machines).
2. Specifically verify:
   - the asset notional router (Section 2.5) — confirm it matches
     `_get_contract_notional` exactly, including the forex/crypto/futures
     branches, for every instrument in the instrument registry (Section 6).
   - whether `total_score` / 5-layer scoring (Section 4.2) and `agent_sync_phase`
     (Section 4.1) are implemented as a *shared computation* usable by both the
     live signal path and an offline backtest/feature-generation path.
   - whether the shadow-tracking of blocked/rejected signals (Section 5.5,
     "rejection_alert" and the ATM Protocol pre-flight checklist, Section 3.4)
     is persisted anywhere — this is required for survivorship-bias-free
     training data.

PHASE 2 — FEATURE STORE & LABELER (highest priority, per current roadmap):
3. Build `feature_store/` that, for every bar where ANY of the following fire —
   confirmed signal, rejected signal (regime-filter blocked), or pre-flight
   checklist evaluation (Section 3.4) — writes a feature row containing:
     - the full 5-layer/5-TF feature set from Section 4.2 (r/v/f/ri per TF,
       total_score)
     - ATR state, session, PDH/PDL status (Section 4.7), liquidity bias,
       volume-profile strength (Section 2.11)
     - the ATM Protocol pre-flight checklist booleans (Section 3.4, rows 6-16)
     - whether the signal fired, was blocked, and by which gate
     - instrument metadata from the registry (Section 6)
   Schema should support both "fired" and "blocked" rows with a `fired: bool`
   and `block_reason: str|null` column.

4. Build `journal/outcome_labeler.py` implementing the Trade Progression state
   machine from Section 4.4 verbatim (TP1/TP2/TP3/Holder/SL phases), computing
   for each fired signal:
     - MFE and MAE in R-multiples (R = locked_risk_dist, per Section 3.3)
     - realized exit reason (TP1/TP2/TP3/Holder-exit/SL), using the SL Autopsy
       categorical root-cause (Section 4.5) as an additional label for SL exits
     - bar-count-to-resolution (for expiry/holding-period estimation, relevant
       to Deriv vanilla option sizing per Section 7.2)
   Join outcome rows back to feature_store rows on signal id (Section 4.6 Trade
   ID Engine format).

PHASE 3 — LEARNING MODULE:
5. Build `learning/` containing:
   - `model.py`: distributional LightGBM with quantile-loss heads (multiple
     quantiles, e.g. 0.1/0.25/0.5/0.75/0.9) predicting the R-multiple outcome
     distribution conditioned on the feature_store feature vector.
   - `sizing.py`: fractional-Kelly sizing engine implementing the cross-cutting
     formula in Section 7.5 (Kelly fraction from predicted distribution, clamped
     by 1-2% equity, daily-loss-budget remaining, and margin headroom). Each
     clamp's binding/non-binding status must be logged per trade.
   - `inference.py`: given a live feature vector (computed the same way as
     feature_store rows), return {predicted_quantiles, kelly_fraction,
     recommended_size, recommended_action}. This output should be able to
     *replace* the static `ai_advice` ladder (Section 4.2) once enough trade
     history accumulates — implement as a feature flag
     (`USE_ML_SIZING=true/false`) so the legacy ladder remains as fallback.

PHASE 4 — EXECUTION ADAPTERS (per Section 7):
6. Implement/verify per-venue adapters with a shared interface
   (`open_position`, `modify_stop`, `partial_close`, `close_position`,
   `get_live_pnl`):
   - `execution/deriv_multiplier.py` — proposal→buy flow, $-based stop_loss via
     limit_order, partial closes for TP1/TP2, deal-cancellation usage for
     MASTER SYNC entries (Section 7.1).
   - `execution/deriv_vanilla.py` — separate "lottery sleeve" allocator gated
     on total_score≥10, using model-predicted P(reach barrier) vs quoted
     premium (Section 7.2). Keep this OFF by default
     (`ENABLE_VANILLA_SLEEVE=false`).
   - `execution/bybit_perp.py` — pybit V5, one-way mode, set_trading_stop for
     TP/SL price levels, leverage decoupled from qty per Section 7.3, funding-
     rate logged per trade.
   - `execution/mt5_cfd.py` — funded-account daily-loss-budget clamp (Section
     7.4), margin-headroom clamp, instrument registry pointvalue lookups.

PHASE 5 — PARITY VERIFICATION:
7. Write a backtest harness that replays historical OHLCV through both
   (a) the Python indicator/scoring stack and (b) a recorded export of the Pine
   script's per-bar `total_score`, `agent_sync_phase`, and signal flags (export
   via TradingView bar replay / Pine `plot` to CSV if not already available).
   Report divergence rate; any divergence >2% of bars on any of these three
   outputs is a P0 bug.

Throughout: do NOT remove the existing static `ai_advice`/SL-autopsy/ladder logic
— it remains the fallback and the "explainability baseline" the ML model's
recommendations should be compared against (Glass Box principle, Section 1 #3).
Keep all dollar amounts asset-routed through the registry in Section 6 — never
hardcode forex/crypto/futures notional assumptions outside `risk/notional_router.py`.
```

---

## 9. OPEN QUESTIONS FOR OPERATOR (Emmanuel)

1. **Liquidity Suite vs ADSA unification** — confirm whether Deep Claw should run *one* unified scoring/sync engine (merging Sections 4.1-4.2 with the ATM Protocol Decision Matrix/Pre-Flight Checklist, Section 3.4) or keep them as two parallel signal sources whose outputs are both fed to the ML layer as separate feature groups. The cheat sheet assumes **unification with deduplicated indicators** (Section 1 note) but the final scoring/decision logic merge needs an explicit decision.
2. **Vanilla options sleeve** — confirm risk-budget % allocation before Phase 4 step 6 is enabled (recommend starting at 0%, i.e., disabled, until the ML model has enough live data to estimate tail probabilities reliably).
3. **Instrument registry completeness** — the watchlist screenshots show ~30 instruments; confirm whether all of these are in-scope for live trading or whether the registry should start with a curated subset (e.g., XAUUSD + 2-3 Volatility Indices + BTC/ETH perps) and expand later.
4. **Funded account (Atlas) rules** — provide the specific daily-loss/max-drawdown percentages so `daily_loss_budget_remaining` (Section 7.5) can be hardcoded as a starting config rather than left as a placeholder.
```
