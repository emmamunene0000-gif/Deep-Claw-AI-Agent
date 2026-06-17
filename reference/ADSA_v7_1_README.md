# ABSOLUTE DOLLAR AGENT — ADSA v7.1
## OPERATOR MASTERCLASS
### Supreme Agent Edition — Invite Only

---

> *This document is a surgical deconstruction of every subsystem inside ADSA v7.1. It is written for beta operators who need to understand exactly what they are running — not a simplified summary, not marketing copy dressed as documentation. If you read this and want to use the tool, that desire will be earned. If you read this and have questions, good — that means you're paying attention.*

---

## TABLE OF CONTENTS

1. [What ADSA Actually Is](#1-what-adsa-actually-is)
2. [Architecture Overview — 19 Subsystems](#2-architecture-overview--19-subsystems)
3. [The Complete Signal Flow — End to End](#3-the-complete-signal-flow--end-to-end)
4. [Subsystem Deconstruction](#4-subsystem-deconstruction)
   - [S1: ATM Bot — The Raw Signal Engine](#s1-atm-bot--the-raw-signal-engine)
   - [S2: RSI Momentum Latch — The Regime Filter](#s2-rsi-momentum-latch--the-regime-filter)
   - [S3: Fibonacci Trend Gate](#s3-fibonacci-trend-gate)
   - [S4: MTF Liquidity Gate — The Structural Guard](#s4-mtf-liquidity-gate--the-structural-guard)
   - [S5: Fractal 4-Layer Consensus Machine](#s5-fractal-4-layer-consensus-machine)
   - [S6: 5-Layer Composite Scoring Engine](#s6-5-layer-composite-scoring-engine)
   - [S7: Platinum Risk Model](#s7-platinum-risk-model)
   - [S8: Trade Progression Engine](#s8-trade-progression-engine)
   - [S9: MTF Liquidity Trail — Holder Mode](#s9-mtf-liquidity-trail--holder-mode)
   - [S10: SMC Engine](#s10-smc-engine)
   - [S11: Adaptive VWAP](#s11-adaptive-vwap)
   - [S12: Fibonacci Extension Bands](#s12-fibonacci-extension-bands)
   - [S13: Volume Profile Engine](#s13-volume-profile-engine)
   - [S14: Longevity Zones](#s14-longevity-zones)
   - [S15: Trade ID Engine](#s15-trade-id-engine)
   - [S16: PDH/PDL Context Engine](#s16-pdh-pdl-context-engine)
   - [S17: SL Autopsy Engine](#s17-sl-autopsy-engine)
   - [S18: Glass Box Alert Architecture](#s18-glass-box-alert-architecture)
   - [S19: Daily Report + ML Data Block](#s19-daily-report--ml-data-block)
5. [All Parameters — Complete Reference](#5-all-parameters--complete-reference)
6. [Dashboard Deep Dive — Component by Component](#6-dashboard-deep-dive--component-by-component)
7. [Telegram Architecture — War Room vs Public](#7-telegram-architecture--war-room-vs-public)
8. [TradeSgnl + Bitget Automation](#8-tradesgnl--bitget-automation)
9. [Pip Tracker & Performance Table](#9-pip-tracker--performance-table)
10. [Operator Framework — How to Actually Use This](#10-operator-framework--how-to-actually-use-this)
11. [What This Tool Is — And What It Is Not](#11-what-this-tool-is--and-what-it-is-not)

---

## 1. WHAT ADSA ACTUALLY IS

ADSA v7.1 is a Pine Script v6 `strategy()` that runs on TradingView and does one job: decide whether the current moment is worth entering a trade, how much to risk, where to get out, and how to broadcast that reasoning in structured form to your community.

It is not an AI in the machine-learning sense. It is a deterministic rule system — but one complex enough that no human operator could replicate it manually in real time. Every decision the agent makes can be audited against its source code. That is the meaning of "Glass Box": you can always see exactly why it did what it did.

**What it produces per signal:**
- A directional call (LONG or SHORT)
- A stop loss level, derived from structural context
- Three take profit levels (1:1, 1.5:1, 2:1 R:R)
- A position size in lots/coins/contracts, dollar-denominated and asset-routed
- A structured Telegram broadcast to two separate channels with different disclosure levels
- A Trade ID for audit and tracking
- A live P&L readout updating every bar

**What makes v7.1 specifically:**
- **MTF Liquidity Gate**: signals only fire when price is above the last confirmed higher-TF pivot low (longs) or below the last confirmed pivot high (shorts). This stops entries on the wrong structural side.
- **Fibonacci Trend Gate**: an optional double-EMA trend lock that blocks counter-Fib entries.
- **Chain Narrative**: the Telegram decision chain replaced the old ASCII tree with a sequential ①②③④⑤ format readable on a phone screen.
- **Selectable pivot length** for the liquidity trail (14/20/50/100/200 bars).

---

## 2. ARCHITECTURE OVERVIEW — 19 SUBSYSTEMS

```
[1]  Fractal 4-Layer Consensus    — posState read through D/H1/M15 lens
[2]  Composite 5-TF Scoring       — +15 to -15 display narrative
[3]  Glass Box Alert Architecture — structured event reasoning per bar
[4]  Trade Progression Engine     — TP1/TP2/TP3/Holder phase detection
[5]  SL Autopsy Engine            — 6 contextual loss narratives
[6]  Signal Rejection Reports     — regime filter explainer broadcast
[7]  SMC Engine                   — BOS/CHoCH/OB/FVG/EQH-EQL
[8]  Adaptive VWAP + Volume Profile + Fibonacci Bands
[9]  Platinum Risk Model          — auto SL/TP + asset-routed sizing
[10] Dual Telegram Broadcast      — Premium War Room + Public Channel
[11] Super Admin Control Panel    — Bias/Silence/Override/Asset Note
[12] Trade ID Engine              — ATM-YYYYMMDD-HHMM-DIR-N
[13] Pip Tracker                  — actual vs expected, daily reset
[14] Performance Table            — 5-col dual table with ELITE/STRONG
[15] Daily Report Engine          — full trade log + ML data block
[16] Live Dollar P&L Tracker      — quote-currency, per-bar update
[17] PDH/PDL Context Engine       — previous day high/low context
[18] MTF Liquidity Trail          — pivot-based trail + ATM gate  ★ NEW v7.1
[19] Fibonacci Trend Gate         — Fib EMA trend gate for ATM   ★ NEW v7.1
```

These 19 subsystems share state through a small number of global variables. The critical shared variable is `posState`: an integer (1=bull, -1=bear, 0=flat) computed on the execution timeframe, which is then read through higher timeframes by the 4-Layer Fractal machine.

---

## 3. THE COMPLETE SIGNAL FLOW — END TO END

Understanding the flow is the foundation of operating this tool. Every confirmed signal has passed through every layer in sequence. Nothing bypasses the chain.

```
PRICE DATA (every bar close)
        │
        ▼
┌─────────────────────────────────────────────┐
│  S1: ATM BOT                                │
│  atr = ta.atr(c_buy)                        │
│  nLoss = a_buy * atr                        │
│  trail ratchets: max(trail[1], close-nLoss) │
│  buy_signal_raw = close crosses trail_buy   │
└──────────────┬──────────────────────────────┘
               │ buy_signal_raw / sell_signal_raw
               ▼
┌─────────────────────────────────────────────┐
│  GATE 1: REGIME FILTER (optional)           │
│  positive latch = RSI crosses above pmom    │
│  regimeBullish = positive (RSI state)       │
│  if enableRegimeFilter: require regimeBull  │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  GATE 2: FIBONACCI TREND (optional)         │
│  basis = EMA(EMA(hlc3, 200), 200)           │
│  fibGateBull = trend rising (basis>basis[1])│
│  if requireFibTrend: require fibGateBull    │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  GATE 3: MTF LIQUIDITY (optional)           │
│  mtf_pivot_low = valuewhen(pivotlow on H1)  │
│  liqGateBull = close > mtf_liq_pivot_low    │
│  if requireLiqGate: require liqGateBull     │
└──────────────┬──────────────────────────────┘
               │ buy_signal_filtered (all gates passed)
               ▼
┌─────────────────────────────────────────────┐
│  posState LATCH                             │
│  posState := 1 (on filtered buy)            │
│  buy_signal_confirmed = filtered AND        │
│    posState==1 AND posState[1]<=0           │
│  (fires ONCE per new direction)             │
└──────────────┬──────────────────────────────┘
               │ buy_signal_confirmed
               ▼
┌─────────────────────────────────────────────┐
│  S5: FRACTAL 4-LAYER MACHINE                │
│  sovereign = request.security(D, posState)  │
│  anchor    = request.security(H1, posState) │
│  filter    = request.security(M15, posState)│
│  exec      = posState (chart TF)            │
│  master_sync_buy = all 4==1 AND confirmed   │
└──────────────┬──────────────────────────────┘
               │ master_sync_buy / confirmed signal
               ▼
┌─────────────────────────────────────────────┐
│  S7: PLATINUM RISK MODEL                    │
│  sl = max(ema21, swing_low) - ATR*buffer    │
│  risk_dist = close - sl                     │
│  size = risk_$ / (risk_dist * notional)     │
│  TP1=entry+1R, TP2=entry+1.5R, TP3=entry+2R│
└──────────────┬──────────────────────────────┘
               │ locked trade parameters
               ▼
┌─────────────────────────────────────────────┐
│  S8: TRADE PROGRESSION ENGINE               │
│  monitors: TP1/TP2/TP3/SL touch each bar   │
│  fires alerts at each progression event     │
└──────────────┬──────────────────────────────┘
               │ progression events
               ▼
┌─────────────────────────────────────────────┐
│  S18: GLASS BOX BROADCAST                   │
│  builds event_title + event_commentary      │
│  builds chain_narrative (①②③④⑤)            │
│  builds _tparams (trade levels block)       │
│  dispatches: War Room (full) / Public (lite)│
└─────────────────────────────────────────────┘
```

**Key constraint: `barstate.isconfirmed` on every signal**

```pine
buy_signal = buy_signal_raw and barstate.isconfirmed
```

This is the zero-repaint guarantee. The ATM trail ratchets intrabar, but the signal only fires when the bar closes. You will never see a signal disappear from a closed bar.

**Key constraint: `barmerge.lookahead_off` on all `request.security` calls**

```pine
[mtf_liq_pivot_high, mtf_liq_pivot_low] = request.security(
     syminfo.tickerid, liq_trail_tf,
     _f_mtf_pivots(liq_trail_pivot_len),
     barmerge.gaps_off, barmerge.lookahead_off)
```

No future data leakage on any higher-TF request. The pivot values you see are the ones that were known at the close of that bar in real time.

---

## 4. SUBSYSTEM DECONSTRUCTION

### S1: ATM Bot — The Raw Signal Engine

**What it is:** A vanilla ATR trailing stop engine — the same pattern widely known as "UT Bot" — with configurable ATR multiplier and period.

**How it works (code, Section 7 lines 869–912):**

```pine
src_buy   = close
atr_buy   = ta.atr(c_buy)           // ATR period = c_buy (default 2)
nLoss_buy = a_buy * atr_buy          // band width = 3.5 * ATR(2)

// Ratchet logic: trail only moves in the direction of the position
if src_buy > trail_buy[1] and src_buy[1] > trail_buy[1]
    trail_buy := math.max(trail_buy[1], src_buy - nLoss_buy)  // bull: floor rises
else if src_buy < trail_buy[1] and src_buy[1] < trail_buy[1]
    trail_buy := math.min(trail_buy[1], src_buy + nLoss_buy)  // bear: ceiling falls

// Signal: close crosses ABOVE the trail
buy_signal_raw = buyEnabled and (src_buy > trail_buy) and ta.crossover(ema_buy, trail_buy)
```

**The honest truth about the ATM:** `ema_buy = ta.ema(close, 1)` — EMA(close, 1) equals close. The crossover is close crossing trail_buy. The mechanics are a standard ATR stop-and-reverse pattern with period=2 and multiplier=3.5 defaults. This is a deliberate and sensible configuration. Period 2 is fast enough to be responsive; multiplier 3.5 provides enough width to avoid noise without being so wide that it lags materially.

**What parameters control this:**

| Parameter | Input Name | Default | Effect |
|-----------|-----------|---------|--------|
| Buy ATR Period | `c_buy` | 2 | Shorter = faster, more whipsaw |
| Buy Sensitivity | `a_buy` | 3.5 | Higher = wider trail, fewer but later signals |
| Show Buy Trail | `showTrailBuy` | false | Toggles trail line visibility |

The sell side mirrors this with `c_sell` / `a_sell` / `showTrailSell`.

**Operator note:** The ATM fires frequently in trending markets and whipsaws badly in sideways chop. The three gates (Regime, Fib, Liq) exist specifically to suppress ATM signals that occur in unfavorable conditions.

---

### S2: RSI Momentum Latch — The Regime Filter

**What it is:** A latch (not a real-time filter) that enters a BULLISH or BEARISH regime state and holds it until a release condition fires.

**How it works (Section 6, lines 832–849):**

```pine
rsi = ta.rsi(close, rsiLen)             // default 14
ema5_close = ta.ema(close, 5)
change_ema5 = ta.change(ema5_close)

// ENTRY condition for positive regime
p_mom = rsi[1] < pmom and rsi > pmom   // RSI crosses above 55 (default)
     and rsi > nmom                     // and RSI is above 50
     and change_ema5 > 0               // and 5-EMA is rising

// ENTRY condition for negative regime
n_mom = rsi < nmom and change_ema5 < 0 // RSI below 50 and 5-EMA falling

// STATE LATCH: once set, stays until opposite fires
if p_mom
    positive := true
    negative := false
if n_mom
    positive := false
    negative := true
```

**Critical behavior: REGIME GOES STALE IN CHOP**

Once `positive = true`, it stays true even if RSI retreats to 52, as long as `n_mom` never fires. In choppy markets where RSI oscillates between 48–58, the regime can stay BULLISH for hours and then flip BEARISH at exactly the wrong time. This is the most important risk to understand about the regime filter.

**When enabled vs disabled:**

```pine
// Gate application (Section 7):
buy_signal_filtered = enableRegimeFilter ?
    (buy_signal and regimeBullish and fibGateBull and liqGateBull) :
    (buy_signal and fibGateBull and liqGateBull)
```

If `enableRegimeFilter` is OFF, only the Fib and Liq gates apply.

**VWAP confirmation (optional):**
If `requireVWAP = true`, `regimeBullish` requires BOTH the RSI latch AND that the Adaptive VWAP has registered a bullish swing (`lastSwing == 1`). This is a stricter combined filter.

---

### S3: Fibonacci Trend Gate

**What it is:** A directional gate that reads the trend of a double-EMA applied to hlc3 with a 200-period length.

**How it works (Section 3.5, lines 527–529):**

```pine
_basis_gate      = ta.ema(ta.ema(src_fib, len_fib), len_fib)  // EMA(EMA(hlc3,200),200)
var int _trend_fib_gate = 0
_trend_fib_gate := _basis_gate > _basis_gate[1] ? 1 :
                   _basis_gate < _basis_gate[1] ? -1 : nz(_trend_fib_gate[1])

// Gate application:
fibGateBull = requireFibTrend ? (_trend_fib_gate ==  1) : true
fibGateBear = requireFibTrend ? (_trend_fib_gate == -1) : true
```

**This uses the exact same formula as Section 12 (Fibonacci Bands).** The `basis` in Section 12 and `_basis_gate` in Section 3.5 are computed identically — EMA(EMA(hlc3, 200), 200). The gate is represented visually by the gray center line of the Fib Bands: if that line is rising, fibGateBull=true; if falling, fibGateBear=true.

**Default: OFF.** When ON, a double-smoothed 200-period trend on hlc3 changes maybe once or twice per session. That is the correct behavior — you're only taking signals when the Fibonacci structure agrees with your direction.

---

### S4: MTF Liquidity Gate — The Structural Guard

**What it is:** A gate that requires price to be on the correct structural side of the most recent higher-timeframe pivot level before a signal is confirmed.

**How it works (Section 3.5, lines 533–543):**

```pine
_f_mtf_pivots(int _len) =>
    _ph  = ta.pivothigh(_len, _len)     // confirmed pivot high (len bars each side)
    _pl  = ta.pivotlow(_len, _len)      // confirmed pivot low
    _pvh = ta.valuewhen(not na(_ph), _ph, 0)  // persist last confirmed high
    _pvl = ta.valuewhen(not na(_pl), _pl, 0)  // persist last confirmed low
    [_pvh, _pvl]

[mtf_liq_pivot_high, mtf_liq_pivot_low] = request.security(
     syminfo.tickerid, liq_trail_tf,       // default H1
     _f_mtf_pivots(liq_trail_pivot_len),   // default 50 bars lookback
     barmerge.gaps_off, barmerge.lookahead_off)

// Gate logic (Section 7):
_liqGateActive = requireLiqGate and liq_trail_enabled
liqGateBull = _liqGateActive ? (close > mtf_liq_pivot_low)  : true
liqGateBear = _liqGateActive ? (close < mtf_liq_pivot_high) : true
```

**What this actually does:** For a long to fire, close must be above the most recent H1 pivot low — meaning price is inside demand structure, not below it. For a short to fire, close must be below the most recent H1 pivot high.

**Why this is the most valuable gate:** Without it, the ATM can generate long signals while price is breaking below a key H1 structural low. That is an entry into confirmed structural weakness. The Liq Gate simply refuses to allow that.

**The `valuewhen` persistence:** Without `ta.valuewhen`, the pivot level would be `na` on all bars except the exact bar the pivot was confirmed. `valuewhen` carries the last confirmed value forward so the gate always has a level to compare against.

**Pivot lookback options:** 14 / 20 / 50 / 100 / 200
- 50: fast intraday pivots, good for M5/M15 chart
- 200: macro pivots — effectively acting as a weekly structure gate when on H1
- 14: too frequent for gating purposes, pivots form every few bars

---

### S5: Fractal 4-Layer Consensus Machine

**What it is:** A system that reads the same `posState` variable through four different timeframe lenses and requires all four to agree before a MASTER SYNC signal fires.

**How it works (Section 8, lines 967–970):**

```pine
sovereign_state = request.security(syminfo.tickerid, sovereign_tf, posState, ...)  // D
anchor_state    = request.security(syminfo.tickerid, anchor_tf,    posState, ...)  // H1
filter_state    = request.security(syminfo.tickerid, filter_tf,    posState, ...)  // M15
exec_state      = posState                                                          // chart TF
```

**The nested state machine (lines 987–1026):**

```pine
if sovereign_state == 1
    if anchor_state == 1
        if filter_state == 1
            if exec_state == 1
                agent_sync_phase := "🔥 FULLY ALIGNED: BULLISH (4-LAYER)"
                if buy_signal_confirmed
                    master_sync_buy := true     // MASTER SYNC fires
            else if exec_state == -1
                agent_sync_phase := "L4 PULLBACK — Wait for Exec Bull Flip"
```

**What `posState` actually represents:** `posState` is the ATR trailing stop direction — 1 when price is above the trailing stop, -1 when below. When we read `posState` through the Daily timeframe, we're asking: "on the Daily chart, is price in an ATR uptrend or downtrend?" That is what "Sovereign Layer" means. It is not a separate algorithm — it is the same ATM direction read through a higher-TF lens.

**MASTER SYNC vs regular confirmed signal:**
- `buy_signal_confirmed`: gates passed, posState flipped long on chart TF. Fires at local entries even without 4-layer agreement.
- `master_sync_buy`: confirmed signal AND all four layers agree. Highest-conviction signal the agent produces.

**Counter-trend detection (line 1028):**
```pine
bool sovereign_counter_buy = buy_signal_confirmed and sovereign_state == -1
```
When a confirmed buy fires while the Daily is BEARISH, this flag activates and the broadcast carries an explicit "⚠️ Counter-trend" warning with the rule: TARGET TP1 ONLY.

---

### S6: 5-Layer Composite Scoring Engine

**What it is:** A display narrative system that reads Regime, VWAP trend, and Fibonacci trend from five fixed timeframes (D, H4, H1, M15, M5) and scores each +1/0/-1, producing a total from +15 to -15.

**How it works (Section 20, lines 1901–1920):**

```pine
get_narrative_status(tf) =>
    [ls_tf, ft_tf, rsi_tf, rb_tf, rr_tf] = request.security(syminfo.tickerid, tf,
         [lastSwing, trend_fib, rsi, regimeBullish, regimeBearish], barmerge.gaps_off)
    r_str = rb_tf ? "Long" : rr_tf ? "Short" : "Neut"    // Regime
    v_str = ls_tf == 1 ? "Bull" : ls_tf == -1 ? "Bear" : "Neut"  // VWAP
    f_str = ft_tf == 1 ? "Bull" : ft_tf == -1 ? "Bear" : "Neut"  // Fib Trend

n_score(s) => s == "Long" or s == "Bull" ? 1.0 : s == "Short" or s == "Bear" ? -1.0 : 0.0

sov_score  = n_score(sov_r) + n_score(sov_v) + n_score(sov_f)   // -3 to +3
total_score = sov_score + h4_score + h1_score + m15_score + m5_score  // -15 to +15
```

**CRITICAL: `total_score` is a display metric. It does NOT gate signals.**

The score does not appear anywhere in `buy_signal_filtered` or `buy_signal_confirmed`. It is rich contextual information but not a hard gate. This is intentional — the 4-Layer Fractal uses `posState` (ATM direction) through higher TFs; the 5-Layer Score uses Regime/VWAP/Fib across fixed TFs. They are complementary readings.

**The chain narrative format (①②③④⑤):**

```pine
chain_narrative =
     "🔗 DECISION CHAIN\n" +
     "① Sovereign D   " + _chain_icon(sov_score)  + " Long [+3] → PASS\n" +
     "② Commander H4  " + _chain_icon(h4_score)   + " Long [+2] → LEAN\n" +
     "③ Navigator H1  " + _chain_icon(h1_score)   + " Long [+3] → PASS\n" +
     "④ Filter    M15 " + _chain_icon(m15_score)  + " Neut [0]  → HOLD\n" +
     "⑤ Executor  M5  " + _chain_icon(m5_score)   + " Long [+1] → LEAN\n" +
     "🔒 Fib: Bull ✅  Liq: L:✅ S:⛔\n" +
     "★ 🟢 LONG · +9.0/15 · EXECUTE\n"
```

Icons: 🟢 = score ≥ 2, 🔴 = ≤ -2, 🟡 = +1, 🟠 = -1, ⚪ = 0
Gate label: PASS = abs(score) ≥ 2, LEAN = abs = 1, HOLD = 0

---

### S7: Platinum Risk Model

**What it is:** A fully automatic stop loss calculation, position size calculator, and TP level generator that routes correctly for forex, crypto, and futures.

**Stop loss logic — longs (Section 14, lines 1227–1229):**

```pine
float sl_val = low > ema21 ?
    math.max(ema21, risk_swing_l) - (risk_atr * sl_buffer_atr) :
    risk_swing_l - (risk_atr * sl_buffer_atr)
if sl_val >= close
    sl_val := close - (risk_atr * 1.5)   // safety fallback: SL can never be above entry
```

For longs: the SL anchor is `max(ema21, 5-bar swing low)` when price is above EMA21, or `5-bar swing low` alone. Then it subtracts `ATR(14) * sl_buffer_atr` (default 1.5) as a buffer below the anchor.

For shorts (mirror): `min(ema21, 5-bar swing high) + ATR * buffer`

**TP levels:**
```pine
locked_tp1 = close + risk_dist * 1.0    // 1:1 R:R
locked_tp2 = close + risk_dist * 1.5    // 1.5:1 R:R
locked_tp3 = close + risk_dist * 2.0    // 2:1 R:R
```

**Asset-routed position sizing (Section 3, lines 463–483):**

```pine
_get_contract_notional() =>
    syminfo.type == "forex"   ? 100000.0 :    // 1 lot = 100,000 units
     syminfo.type == "crypto"  ? 1.0       :   // 1 coin = 1 unit
     syminfo.type == "futures" ? syminfo.pointvalue :
     syminfo.pointvalue

_get_position_size(float sl_distance) =>
    float notional = _get_contract_notional()
    math.round(risk_per_trade / (sl_distance * notional), 4)
```

Examples:
- EURUSD, risk $15, SL 20 pips (0.0020): `15 / (0.0020 × 100000) = 0.075 lots`
- BTCUSDT, risk $15, SL $500: `15 / (500 × 1.0) = 0.03 BTC`
- Gold futures, risk $15, SL $8, pointvalue=100: `15 / (8 × 100) = 0.01875 contracts`

The `sl_buffer_atr` parameter is the most consequential risk parameter after `risk_per_trade`. Higher buffer = wider SL = smaller position for the same dollar risk.

---

### S8: Trade Progression Engine

**What it is:** A state machine that monitors every bar for TP1/TP2/TP3/SL touches and transitions the trade phase accordingly. Each transition fires a broadcast event.

**Phase sequence (Section 16):**
```
WAITING → ENTRY → TP1_HIT → TP2_HIT → TP3_HIT → HOLDER_MODE
                                                        ↓
                                                  trail exit
```

```pine
// Sequential gate: TP2 can only hit after TP1, TP3 only after TP2
if not tp1_hit and not sl_hit_flag
    if trade_direction == 1 ? high >= locked_tp1 : low <= locked_tp1
        tp1_hit := true
        trade_phase := "TP1_HIT"
if tp1_hit and not tp2_hit and not sl_hit_flag
    if trade_direction == 1 ? high >= locked_tp2 : low <= locked_tp2
        tp2_hit := true
        trade_phase := "TP2_HIT"
```

**SL is only checked before TP1** — after TP1 fires, the operator is expected to move SL to breakeven. The code mirrors this discipline.

**Position sizing per phase (TradeSgnl):**
- TP1: close 33.3% of position
- TP2: close 50% of remaining → 33% of original is closed
- TP3: close 75% of remaining → runner is ~8% of original
- Holder Mode: trail the runner

---

### S9: MTF Liquidity Trail — Holder Mode

**What it is:** A ratcheting higher-TF trail for the runner position after TP3. The floor (for longs) advances with each new H1 pivot low — it never retreats.

**How it works (Section 16, lines 1374–1382):**

```pine
var float mtf_holder_trail = na
if liq_trail_enabled and holder_mode_active
    if trade_direction == 1
        mtf_holder_trail := na(mtf_holder_trail) ?
             mtf_liq_pivot_low :
             math.max(mtf_holder_trail, mtf_liq_pivot_low)  // floor only rises
    else if trade_direction == -1
        mtf_holder_trail := na(mtf_holder_trail) ?
             mtf_liq_pivot_high :
             math.min(mtf_holder_trail, mtf_liq_pivot_high) // ceiling only falls
```

**Dual purpose of the MTF pivot data:**
1. **Signal gate** (requireLiqGate=ON): blocks entry when price is on wrong side of pivot
2. **Holder trail** (holder_trail_type="MTF Liquidity"): trails the runner using the same pivots

The gate fires before the trade. The trail fires after TP3. They share `mtf_liq_pivot_high/low` but serve entirely different purposes.

---

### S10: SMC Engine

**What it is:** A comprehensive Smart Money Concepts implementation: BOS, CHoCH, Order Blocks, Fair Value Gaps, Equal Highs/Lows, Premium/Discount zones, Liquidity sweep visualization.

The SMC engine runs through Sections 17–19 and executes in Section 29. It produces:
- `swingTrend.bias`: BULLISH or BEARISH swing structure
- `currentAlerts`: per-bar struct with flags for all SMC events
- Visual drawings on chart (lines, boxes, labels)

**Connection to broadcast:** The Glass Box broadcast (Section 26) checks `currentAlerts`:
```pine
else if currentAlerts.swingBullishBOS or currentAlerts.swingBullishCHoCH
    event_title := "📈 BULLISH STRUCTURE SHIFT (BOS/CHoCH)"
```

Structure events broadcast to both channels as informational context even when no trade signal fires.

---

### S11: Adaptive VWAP

A volume-weighted adaptive price line that swings with significant price moves, colored by trend. The VWAP's current swing direction (`lastSwing = 1/-1`) feeds the 5-Layer Score's VWAP contribution and optionally gates the regime filter when `requireVWAP = true`.

---

### S12: Fibonacci Extension Bands

Double-EMA bands (EMA of EMA, 200 periods) with ATR-width. Upper bands only draw in bearish Fib trend (resistance zones); lower bands only in bullish Fib trend (support zones). The center line (`basis`) is the same variable used by the Fibonacci Trend Gate. When the center line is rising, lower bands show and `fibGateBull = true`. Visual and gate are perfectly correlated.

---

### S13: Volume Profile Engine

Session-based volume distribution computing POC (highest volume price node), VAH, and VAL for the current session. Uses `request.security_lower_tf` to gather intrabar OHLCV data. Session boundaries are detected from Volume Profile settings (Daily/Weekly/Monthly/Yearly/specific sessions). POC/VAH/VAL appear on chart and feed into the dashboard CORE SIGNALS section as context.

---

### S14: Longevity Zones

Supply and demand zones at recent swing highs and lows with half-ATR body thickness, confirmed by `high[1] == h_zone[1] and high < h_zone` (a high that broke below the zone on the next bar = confirmed pivot). Zones are automatically removed when violated. Visual reference only — no direct connection to signal logic.

---

### S15: Trade ID Engine

Generates a unique identifier for every trade: `ATM-YYYYMMDD-HHMM-DIR-N`

```pine
atm_trade_id = "ATM-" + str.tostring(year) +
               _pad(month) + _pad(dayofmonth) + "-" +
               _pad(hour) + _pad(minute) + "-" +
               _dir_id + "-" + _pad(atm_daily_counter)
```

Example: `ATM-20260617-1430-BUY-02` = second buy signal at 14:30 on June 17, 2026. Daily counter resets at midnight. Appears in every broadcast and daily report — consistent audit trail across all channels.

---

### S16: PDH/PDL Context Engine

Fetches previous day's high and low with `lookahead_off` and produces a plain-English context string:

```pine
string pdh_pdl_status =
     close > pdh_level ? "🔼 Above PDH (" + _p(pdh_level) + ")" :
     close < pdl_level ? "🔽 Below PDL (" + _p(pdl_level) + ")" :
     "↔ Inside Range [PDH: " + _p(pdh_level) + " | PDL: " + _p(pdl_level) + "]"
```

Feeds every broadcast and the dashboard header. Knowing whether you're breaking out above PDH vs. chopping inside the previous day's range fundamentally changes trade management. This is one of the highest-value context lines in the entire system.

---

### S17: SL Autopsy Engine

When a stop loss fires, the agent evaluates six contextual reasons and broadcasts the most likely cause as a structured post-mortem.

**The 6 autopsy categories (Section 25, lines 2393–2406):**

```pine
_build_sl_autopsy() =>
    if str.contains(liq_bias,"BREAKING")
        → "LIQUIDITY TRAP: Institutions swept our stop..."
    else if atrHL == "Low"
        → "VOLATILITY COLLAPSE: ATR entered LOW state..."
    else if sovereign_state == -1 and trade_direction == 1
        → "SOVEREIGN VETO: Daily was BEARISH at entry..."
    else if sovereign_state == 1 and trade_direction == -1
        → "SOVEREIGN VETO: Daily was BULLISH at entry..."
    else if math.abs(total_score) < 4
        → "WEAK 5-LAYER ALIGNMENT: Score below threshold..."
    else
        → "MACRO ROTATION: Higher-TF structure shifted post-entry..."
```

Each autopsy includes the violated rule and corrective action. The agent explains its own failures — that is Glass Box accountability.

---

### S18: Glass Box Alert Architecture

The full broadcast engine. Produces one structured narrative per event:
- Entry (LONG/SHORT/MASTER SYNC/COUNTER)
- TP1, TP2, TP3, Stop Hit, Holder Exit
- Signal Rejection, Liquidity Sweep, Structure Shift (BOS/CHoCH)
- Session Open, Admin Silence

All events use `barstate.isconfirmed` on the trigger check — broadcasts are always tied to closed bars. All dispatches use `alert.freq_once_per_bar_close`.

---

### S19: Daily Report + ML Data Block

At a configurable UTC hour, the agent compiles a full-day report including every trade, outcomes, session breakdown, average score, and a machine-readable ML data block for later analysis.

**ML data block format:**
```
[ATM_DATA_ADSA]
date=2026.06.17
asset=EURUSD
tf=5
signals=4
rejected=2
long=3
short=1
sync4=1
local=2
counter=1
tp1=2
tp2=1
tp3=0
sl=1
open=0
win_rate=75.0
avg_score=7.25
avg_pips=18.40
best_pips=32.10
pf=2.75
net_pips=+54.2
london=2
ny=2
asia=0
atr_state=High
sovereign=BULL
total_score=9.0
[/ATM_DATA_ADSA]
```

`key=value` one per line, enclosed in tags. Designed for machine parsing — extract from Telegram history and feed to a spreadsheet or model.

---

## 5. ALL PARAMETERS — COMPLETE REFERENCE

### Super Admin Control Panel

| Parameter | Default | What It Does |
|-----------|---------|-------------|
| Sovereign TF | D | Layer 1 macro veto. Change to "W" for position trades. |
| Manual Bias Override | AUTO | AUTO=normal. FORCE BULL/BEAR=override. SILENCE=suppress all signals. |
| Asset Context | (empty) | String appended to every Telegram message. e.g. "GOLD — London watch" |
| Operator Commentary | (empty) | Your analysis. War Room only. |
| Sanitize Public Channel | true | ON=public gets signal type + bias only, no levels. |

### Telegram Broadcast

| Parameter | Default | What It Does |
|-----------|---------|-------------|
| Enable War Room | true | Master toggle for Premium channel. |
| Chat ID (Premium) | (empty) | Your War Room Telegram chat ID. Must be set. |
| Enable Public | true | Master toggle for Public channel. |
| Chat ID (Public) | (empty) | Your Public channel Telegram chat ID. |

### ATM Bot Settings

| Parameter | Default | What It Does |
|-----------|---------|-------------|
| Buy Sensitivity | 3.5 | ATR multiplier. Higher = fewer signals, later entries. |
| Buy ATR Period | 2 | ATR look-back. Lower = faster/noisier. |
| Sell Sensitivity | 3.5 | Mirror for short side. |
| Sell ATR Period | 2 | Mirror for short side. |
| Show Buy Trail | false | Display green trailing stop line. |
| Show Sell Trail | false | Display red trailing stop line. |
| Enable Regime Filter | true | RSI Momentum Latch gates the ATM signal. |
| Require VWAP Confirmation | false | Also require VWAP swing agreement. |
| Activate Glass Box Reports | true | Enables full structured Telegram broadcasts. |

### Risk Management

| Parameter | Default | What It Does |
|-----------|---------|-------------|
| Risk Per Trade ($) | 15.0 | Dollar risked. Size = risk / (SL distance × notional). |
| SL Buffer (ATR Multiplier) | 1.5 | Extra distance below structure anchor. Higher = wider SL, smaller size. |
| Show Min-Unit Actual Risk | true | Shows $-risk at 0.01 lot in dashboard. |
| Strict One-Trade Rule | false | Prevents new signal if current trade hasn't stopped out. |
| Holder Mode Trail | Structural | Trail mechanism after TP3: VWAP / Structural / MTF Liquidity. |

### Fractal 4-Layer Protocol

| Parameter | Default | What It Does |
|-----------|---------|-------------|
| Layer 2 — Anchor TF | 60 (H1) | The "Commander" layer. Change to 240 for H4 on longer setups. |
| Layer 3 — Filter TF | 15 (M15) | The "Navigator" layer. Change to 30/60 on a longer chart TF. |

### MTF Liquidity Trail

| Parameter | Default | What It Does |
|-----------|---------|-------------|
| Enable MTF Liquidity Trail | true | Master switch for both gate and holder trail. |
| Trail Timeframe | 60 (H1) | TF for pivot levels. Must be ≥ chart TF. |
| Pivot Lookback Length | 50 | Bars each side to confirm pivot on Trail TF. |
| Gate ATM Signals to Liq Trail | true | If ON, signals blocked when price is on wrong structural side. |

### Fibonacci Trend Gate

| Parameter | Default | What It Does |
|-----------|---------|-------------|
| Require Fibonacci Trend Alignment | false | If ON, buys blocked when Fib EMA trending down; sells when trending up. |

### RSI Momentum

| Parameter | Default | What It Does |
|-----------|---------|-------------|
| RSI Length | 14 | Standard RSI period. |
| Positive Above | 55 | RSI threshold for positive regime latch to fire. |
| Negative Below | 50 | RSI threshold for negative regime to fire. |
| Show RSI Labels | false | Toggle BULL/BEAR labels on regime transitions. |

### Dashboard

| Parameter | Default | What It Does |
|-----------|---------|-------------|
| Show Dashboard | true | Master toggle. |
| Panel Background | green 80% transparent | Panel fill color. |
| Text Color | black | Panel text. |
| Placement | Top-Right | Position on chart. |
| Show Performance Table | true | Toggle 5-col daily performance table. |

### Daily Performance Report

| Parameter | Default | What It Does |
|-----------|---------|-------------|
| Enable Daily Report | true | Toggle EOD auto-report. |
| Report Hour (UTC) | 21 | Hour report fires. 21=9PM UTC. |
| Send to War Room | true | Dispatch to Premium channel. |
| Send to Public | false | Dispatch sanitized version to Public. |

### LinReg Settings

| Parameter | Default | What It Does |
|-----------|---------|-------------|
| Signal Smoothing | 21 | Period for the signal line (SMA or EMA of close). |
| Simple MA Signal | true | SMA if true, EMA if false. |
| Use LinReg Candles | false | Replaces candles with LinReg. WARNING: repaints history. |

### Oscillators

| Parameter | Default | What It Does |
|-----------|---------|-------------|
| MACD Fast/Slow/Signal | 12/26/9 | Standard MACD. Used for dashboard MACD Bull/Bear display. |
| Stoch Length/K/D | 14/3/3 | Stochastic (computed but not prominently displayed by default). |
| Volume MA | 20 | SMA period for volume moving average reference. |

---

## 6. DASHBOARD DEEP DIVE — COMPONENT BY COMPONENT

The dashboard is a single-cell borderless `table` (1×1) filled with `panelText` — a concatenated string built on every `barstate.islast`. It updates once per bar close on the current bar.

**Full annotated mock (XAUUSD on 5m, active long trade):**

```
━━━━━━━━━━━━━━━━━━━━━━━━━
 🚀 ABSOLUTE DOLLAR AGENT
 Absolute Dollar Intelligence
━━━━━━━━━━━━━━━━━━━━━━━━━
```
*Header — static branding. Lines 2244–2247.*

```
 🔐 AUTO | 👑 Sovereign (D): BULL
 📌 GOLD — London continuation
 📊 Score: +9.0/15  |  Public: SANITIZED
━━━━━━━━━━━━━━━━━━━━━━━━━
```
*Admin panel status. `admin_manual_bias` | sovereign TF + `sovereignStatus` | `total_score` | public sanitize state. Optional `asset_context` on line 2. Lines 2248–2250.*

```
 ⏱️ FRACTAL 4-LAYER SYNC
 L1 Sovereign (D):    BULL
 L2 Anchor   (60):   BULL
 L3 Filter   (15):   BULL
 L4 Exec     (5):    BULL
 🔄 🔥 FULLY ALIGNED: BULLISH (4-LAYER)
━━━━━━━━━━━━━━━━━━━━━━━━━
```
*Four-layer state display. Each layer shows its configured TF and current posState direction. `agent_sync_phase` string at the bottom. Lines 2252–2257.*

```
 📊 CORE SIGNALS
 XAUUSD | 5  2310.20
 🗽 NY SESSION  |  ATR: High (4.82)
 📅 Daily Context: 🔼 Above PDH (2305.10)
 ATM 🟢  Regime 📈
 VWAP 📈  Fib 📈
 RSI 📈 (62)  MACD: Bull
 🔒 FibGate: OFF  LiqGate: ✅ OK
 💧 MTF Pivots [60]: H=2325.50  L=2298.70
━━━━━━━━━━━━━━━━━━━━━━━━━
```
*The most-used section. Line by line:*
- *Asset | TF | Current close*
- *Session (Tokyo/London/NY by UTC hour) | ATR state + raw value*
- *PDH/PDL context string*
- *ATM posState emoji | Regime state emoji*
- *VWAP lastSwing emoji | Fib trend direction emoji*
- *RSI value and state | MACD Bull/Bear*
- *FibGate status (OFF / ✅Bull/Bear / ⛔Neut) | LiqGate status*
- *Live MTF pivot H and L from liq_trail_tf*

*Lines 2259–2268.*

```
 📈 MTF EMA (9/21)
 1m📉 5m📈 15m📈 30m📈 1H📈
 4H📈 1D📈 1W📈 1M📈
━━━━━━━━━━━━━━━━━━━━━━━━━
```
*EMA(9) vs EMA(21) across 9 fixed TFs. 📈 = fast above slow. Quickest multi-TF alignment scan. Lines 2271–2272.*

```
 🧠 5-LAYER AI NARRATIVE  [+9.0/15]
 📈 BULLISH BIAS (Strong)
  ├── D  (Sovereign) 🟢
  │    Regime :Long V.WAP :Bull Fib Trend :Bull RSI:Bull
  ├── H4 (Anchor) 🟢
  │    Regime :Long V.WAP :Bull Fib Trend :Bull RSI:Bull
  ├── H1 🟡
  │    Regime :Long V.WAP :Neut Fib Trend :Bull RSI:Bull
  ├── M15 🟡
  │    Regime :Long V.WAP :Bull Fib Trend :Neut RSI:Neut
  └── M5 ⚪
       Regime :Neut V.WAP :Neut Fib Trend :Neut RSI:Neut
━━━━━━━━━━━━━━━━━━━━━━━━━
```
*The `tree_narrative` string. Each row = one TF. Icon = combined score for that layer. Three indicators: Regime state, VWAP swing, Fib Trend, RSI. `effective_bias` label above. Lines 2274–2276.*

```
 💡 AGENT ADVICE
 Confident entry — bias confirmed. Verify chart.
━━━━━━━━━━━━━━━━━━━━━━━━━
```
*`ai_advice` — score-threshold advice string. Six levels from "Stand aside" through "Aggressive entry". Lines 2278–2279.*

```
 💧 LIQUIDITY
 💧 NEAR SWING HIGH
 🟢 Buy-side:  2325.50
 🔴 Sell-side: 2298.70
━━━━━━━━━━━━━━━━━━━━━━━━━
```
*`liq_bias` context + buy-side pool (last confirmed swing high) + sell-side pool (last confirmed swing low). Lines 2281–2284.*

```
 💰 TRADE SETUP
 📊 Phase: 🎯 TP1 SECURED
 ID: ATM-20260617-1430-BUY-01
 Dir: 🟢 LONG
 💡 Min-Unit Risk: ~$1.82 | Variable: $15 → 0.0750 Lots
 💵 Live P&L: +$22.50 (+15.0 pips)
 🚪 Entry: 2310.20  🛑 SL: 2302.40  (7.8 pips)
 🎯 TP1: 2318.00 ✅  (7.8 pips)
 🎯 TP2: 2321.90   (11.7 pips)
 🚀 TP3: 2325.80   (15.6 pips)
 📈 Peak: 18.2 pips
━━━━━━━━━━━━━━━━━━━━━━━━━
```
*Complete active trade block. Updates every bar. Phase, Trade ID, direction, risk sizing, live unrealised P&L (asset-routed), all levels with distances, peak profit. Lines 2200–2218.*

```
 📅 TODAY
 Sigs: 3  Blocked: 1  LDN: 1  NY: 2
 TP1: 2  TP2: 1  TP3: 0  SL: 0
 WR: 100.0%  PF: ∞  Net: +28.6 pips
 Report: ⏳ 21:00 UTC
━━━━━━━━━━━━━━━━━━━━━━━━━
```
*Intraday summary from pip tracker. Daily reset. Report countdown. Lines 2289–2293.*

```
 ⚠️ Not financial advice.
 © Absolute Dollar 2026
```

---

## 7. TELEGRAM ARCHITECTURE — WAR ROOM VS PUBLIC

### Channel Architecture

Two independent Telegram channels. Messages are JSON-wrapped via `_tg_json()` for TradingView's Telegram webhook integration. Both dispatches use `alert.freq_once_per_bar_close`.

```pine
_tg_json(string chat_id, string msg) =>
    // escapes quotes and newlines for valid JSON
    "{\"chat_id\":\"" + chat_id + "\",\"text\":\"" + s + "\"}"
```

### WAR ROOM MESSAGE — Full Glass Box

Complete mock on a Master Sync Long entry on XAUUSD:

```
━━━━━━━━━━━━━━━━━━━━━
🔥 ABSOLUTE DOLLAR — WAR ROOM
Supreme Agent ADSA v7.1
━━━━━━━━━━━━━━━━━━━━━
📊 Asset   : XAUUSD | 5
💰 Price   : 2310.20
🌍 Session : 🗽 NY SESSION
📅 Daily   : 🔼 Above PDH (2305.10)
📌 Context : GOLD — London continuation
─────────────────────
🔔 EVENT: 🔥 MASTER SYNC LONG — 4-LAYER ALIGNED
─────────────────────
📝 AGENT COMMENTARY
All 4 layers BULLISH. Sovereign + Commander + Navigator + Executor aligned.
Score: +9.0/15 | ATR: High
High-probability trend continuation. R:R 2.0+ advised.
─────────────────────
🎯 TRADE PARAMETERS
─────────────────────
Direction  : 🟢 LONG
Entry      : 2310.20
Stop Loss  : 2302.40  (7.8 pips)
TP1 (1:1)  : 2318.00  (7.8 pips)
TP2 (1.5:1): 2321.90  (11.7 pips)
TP3 (2:1)  : 2325.80  (15.6 pips)
Risk $     : $15 → 0.0750 Lots
Min-unit risk: ~$1.82
Trade ID   : ATM-20260617-1430-BUY-01
4-Layer    : 🔥 FULLY ALIGNED: BULLISH (4-LAYER)
─────────────────────
🧠 GLASS BOX AI NARRATIVE
─────────────────────
Master Bias  : 📈 BULLISH BIAS (Strong)
Score        : +9.0/15
Daily Context: 🔼 Above PDH (2305.10)
─────────────────────
🔗 DECISION CHAIN
① Sovereign D   🟢 Long [+3] → PASS
② Commander H4  🟢 Long [+3] → PASS
③ Navigator H1  🟡 Long [+2] → LEAN
④ Filter    M15 🟡 Long [+1] → LEAN
⑤ Executor  M5  🟢 Long [+3] → PASS
🔒 Fib: OFF  Liq: L:✅ S:⛔
★ 🟢 LONG · +9.0/15 · EXECUTE
─────────────────────
💡 AGENT ADVICE
Confident entry — bias confirmed. Verify chart.
PF: 2.75  WR: 75.0%
─────────────────────
💬 OPERATOR NOTE
Gold held PDH as support. London continuation. Patient at TP2.
─────────────────────
🧊 LIQUIDITY
Buy-side  : 2325.80
Sell-side : 2298.70
Context   : 💧 NEAR SWING HIGH
━━━━━━━━━━━━━━━━━━━━━
⚠️ Not financial advice. © 2026 Absolute Dollar
```

**War Room message anatomy:**

| Block | Source | Notes |
|-------|--------|-------|
| Header | Static | Asset, price, session, daily context, asset_context |
| EVENT | `event_title` | Signal type, TP hit, SL, structure, etc. |
| AGENT COMMENTARY | `event_commentary` | Event-specific structured interpretation |
| TRADE PARAMETERS | `_tparams` | Only on entry signals. Levels, ID, sync phase. |
| GLASS BOX NARRATIVE | `_narrative` | Bias, score, chain_narrative, advice, PF/WR |
| OPERATOR NOTE | `admin_commentary` | Your text. War Room only. |
| LIQUIDITY | Live pools | Buy-side/sell-side pool levels + liq_bias |

### PUBLIC CHANNEL MESSAGE — Sanitized

Same event, public version (sanitize=ON):

```
━━━━━━━━━━━━━━━━━━━━━
🤖 ABSOLUTE DOLLAR — ATM AGENT
Supreme Agent ADSA v7.1
━━━━━━━━━━━━━━━━━━━━━
📊 Asset   : XAUUSD | 5
🌍 Session : 🗽 NY SESSION
📅 Daily   : 🔼 Above PDH (2305.10)
📌 Context : GOLD — London continuation
─────────────────────
🔔 EVENT: 🔥 MASTER SYNC LONG — 4-LAYER ALIGNED
─────────────────────
📝 COMMENTARY
🔥 Master Sync Long — 4 layers aligned.
─────────────────────
🧠 NARRATIVE
Bias  : 📈 BULLISH BIAS (Strong)
Score : +9.0/15
Sync  : 🔥 FULLY ALIGNED: BULLISH (4-LAYER)
Daily : 🔼 Above PDH (2305.10)
Dir   : 🟢 LONG
─────────────────────
🔗 Full Glass Box report in War Room.
─────────────────────
⚠️ Not financial advice. © 2026 Absolute Dollar
```

**What public gets:** signal direction, event type, master bias, score, sync phase, daily context.
**What they don't get:** specific levels (entry, SL, TPs), position size, chain narrative, operator commentary, liquidity levels.

The line "Full Glass Box report in War Room" creates the upsell naturally — no sales pitch required.

### Message Types by Event

| Event | Event Title | Trade Params? | Autopsy? |
|-------|-------------|:---:|:---:|
| Master Sync Long | 🔥 MASTER SYNC LONG — 4-LAYER ALIGNED | ✅ | — |
| Regular Long | 🟢 LONG SIGNAL CONFIRMED | ✅ | — |
| Counter-trend Long | ⚠️ SOVEREIGN COUNTER-TREND LONG | ✅ | — |
| TP1 Hit | 🎯 TP1 HIT — PARTIAL SECURED (1:1) | — | — |
| TP2 Hit | 🎯🎯 TP2 HIT — MOVE STOP TO BREAKEVEN | — | — |
| TP3 Hit | 🚀 TP3 HIT — HOLDER MODE ACTIVATED | — | — |
| Stop Hit | 💀 STOP HIT — GLASS BOX AUTOPSY | — | ✅ |
| Holder Exit | 🏁 HOLDER MODE EXIT | — | — |
| Signal Blocked | ⛔ SIGNAL BLOCKED — REGIME FILTER | — | — |
| Buy-side Sweep | ⚠️ BUY-SIDE LIQUIDITY SWEPT | — | — |
| BOS/CHoCH Bull | 📈 BULLISH STRUCTURE SHIFT | — | — |
| Session Open | 🕒 SESSION OPEN — ENVIRONMENTAL SCAN | — | — |
| Admin Silence | 🔇 ADMIN SILENCE — STANDING ASIDE | — | — |

---

## 8. TRADESGNL + BITGET AUTOMATION

### TradeSgnl (MT5/MT4 EA Integration)

The agent produces alert message strings for TradeSgnl. Default long entry format:

```
LICENSE_ID,{{ticker}},buy,vol_dollar={{risk}},sl_price={{sl}},tp1_price={{tp1}},pct1=0.33,tp2_price={{tp2}},pct2=0.50,tp3_price={{tp3}},exent=1
```

Template substitution at broadcast time via `f_format_alert()` (Section 3):

```pine
f_format_alert(string template, ...) =>
    res := str.replace_all(res, "{{risk}}", str.tostring(risk, "#.##"))
    res := str.replace_all(res, "{{sl}}", f_alert_p(sl))
    res := str.replace_all(res, "{{tp1}}", f_alert_p(tp1))
    // etc.
```

Example output:
```
LICENSE_ID,XAUUSD,buy,vol_dollar=15.00,sl_price=2302.40,tp1_price=2318.00,pct1=0.33,tp2_price=2321.90,pct2=0.50,tp3_price=2325.80,exent=1
```

- `pct1=0.33`: close 33% of position at TP1
- `pct2=0.50`: close 50% of remaining at TP2
- `exent=1`: EA closes any opposing position on reversal
- TP1/TP2/TP3 messages left empty by default — EA manages partials internally using the `pct` values

**Exit message (SL or holder trail):**
```
LICENSE_ID,XAUUSD,closebuy
```

**Section 30 strategy() calls** (lines 2884–2898):
```pine
strategy.entry("Long", strategy.long, alert_message=f_format_alert(...))
strategy.close("Long", qty_percent=33.3, comment="Long TP1", ...)
strategy.close("Long", qty_percent=50.0, comment="Long TP2", ...)
strategy.close("Long", qty_percent=75.0, comment="Long TP3", ...)
```

### Bitget Webhook

When `enable_bitget = true`, entry signals fire a JSON webhook (Section 27):

```json
{
  "action": "buy",
  "size": "0.0750",
  "symbol": "XAUUSD",
  "price": "2310.20",
  "sl": "2302.40",
  "tp1": "2318.00",
  "id": "ATM-20260617-1430-BUY-01",
  "score": "9.0",
  "sync": "🔥 FULLY ALIGNED: BULLISH (4-LAYER)"
}
```

Webhook URL is configured in the TradingView alert panel, not in script inputs.

---

## 9. PIP TRACKER & PERFORMANCE TABLE

### Pip Tracker (Section 21)

Accumulates daily statistics that reset on each new day:

| Metric | Calculation |
|--------|------------|
| TP1 actual avg | Mean pips from entry to TP1 on all TP1-hit trades |
| TP1 expected avg | Risk distance × 1.0 (what the model projected) |
| Win rate | (TP1 + TP2 + TP3 hits) / total closed trades |
| Profit Factor | Gross winning pips / gross losing pips |
| Net pips | Total captured pips minus total lost pips |

Ratings: PF ≥ 2.5 = ELITE ✅, ≥ 2.0 = STRONG ✅, ≥ 1.5 = GOOD, ≥ 1.0 = MARGINAL ⚠️, < 1.0 = NEGATIVE ❌

### Performance Table (Section 24)

5-column × 10-row table at bottom-left:

| Row | Metric | Actual | Expected | Hits |
|-----|--------|--------|----------|------|
| TP1 | avg pips | real captured | risk_dist × 1.0 | count |
| TP2 | avg pips | real captured | risk_dist × 1.5 | count |
| TP3 | avg pips | real captured | risk_dist × 2.0 | count |
| SL | avg pips | real loss | risk_dist | count |
| PF | ratio | rating | Win Rate | % |
| Net | today pips | ±total | W/L count | — |

Color-coded: green for wins, red for losses, gold for highlights. The comparison of actual vs expected tells you whether the model's R:R projections are being realized or whether the market is taking back profits before reaching targets.

---

## 10. OPERATOR FRAMEWORK — HOW TO ACTUALLY USE THIS

### Morning Routine (Pre-London)

1. **Check ATR state.** If "Low" — no trades until ATR expands. The regime can stay stale in thin conditions and produce false signals.
2. **Check Daily Context.** Above PDH = bullish breakout territory. Below PDL = bearish breakdown territory. Inside range = elevated chop probability.
3. **Check 5-Layer narrative score.** Score ≥ +6: confident long bias. ≤ -6: confident short. Between ±3: stand aside.
4. **Set `asset_context`.** e.g. "GOLD — watching 2310 breakout above PDH." Appears in every broadcast.
5. **Note the MTF Pivots [H1].** Know where H=xxx and L=xxx are. These are the Liq Gate reference levels.

### Intraday Operation

**MASTER SYNC signal (🔥/🥶 diamond labels):** Highest conviction. All 4 layers aligned. Score typically ≥ +6. Target full TP3 trail. This is the signal to take every time.

**Regular confirmed signal (Buy/Sell labels):** 3-layer or partial alignment. Target TP1/TP2. Hold for TP3 only if score strengthens and sync narrows intrabar.

**Counter-trend signal (CT-L/CT-S gold labels):** Agent flags with ⚠️ broadcast. RULE: TP1 only. Never press to TP3. The autopsy will remind you when you break this rule.

**Signal rejections (✕ gray marks):** Raw ATM fired but a gate blocked it. Frequent rejections in one direction = structural resistance to that direction. Use as confirmation to avoid that bias.

**SILENCE mode:** When unavailable, when news events are due, when ATR is Low — set `admin_manual_bias = "SILENCE"`. Your community gets a silence broadcast. They trust you more for the explicit "standing aside" call than for going dark.

### Counter-Trend Protocol (Absolute Rules)

When `sovereign_counter_buy` or `sovereign_counter_sell` is true — Daily TF is against your trade:
1. Target TP1 only — close the entire position
2. Do NOT hold to TP2 or TP3
3. Tighten SL after TP1 to tight structure, not just breakeven

The agent broadcasts this rule on every counter-trend event. The autopsy engine fires "SOVEREIGN VETO" when you hold through TP1 on a counter-trend and get stopped. The rules are in the code. You choose whether to follow them.

### Reading the Autopsy

Every SL hit produces one of 6 contextual narratives. Read the autopsy before looking at the chart. The agent's diagnosis is more systematic than your emotional post-trade review. If LIQUIDITY TRAP comes up repeatedly — widen the SL buffer. If WEAK ALIGNMENT comes up — raise your score threshold. If SOVEREIGN VETO comes up — stop taking counter-trend positions to TP3.

### End of Day

Daily Report fires at your configured UTC hour. Every trade, outcome, session breakdown, average entry score, and self-assessment. The ML data block captures everything for later analysis. Read the self-assessment. When it says "DIFFICULT SESSION — SL hits exceeded TP captures" — that session had structural problems. Review ATR state, score averages, and counter-trend ratio from that day.

---

## 11. WHAT THIS TOOL IS — AND WHAT IT IS NOT

### What It Is

**A structured decision support system** that monitors the market 24/5 and alerts when a specific set of conditions converge. It enforces rule-based discipline on entries, manages partial exits systematically, and explains every decision in plain language.

**A community broadcast engine** that maintains two-tier communication — War Room members receive full Glass Box reasoning, public members receive enough to follow the direction. The agent is the consistent voice of your channel, broadcasting whether you're watching or not.

**A transparent system.** Every output is traceable to a specific line of code. When the agent says "LIQUIDITY TRAP" in an autopsy, you can find exactly how it detected that in `_build_sl_autopsy()`. When it says "+9.0/15", you can verify each layer's contribution in the dashboard tree. No black boxes.

**A platform, not a finished product.** The parameters are yours to configure. The TFs are yours to choose. The `admin_commentary` adds your judgment on top of the mechanical framework. The asset_context field tells your community which setups you're watching. The system handles the structure — you provide the context and the accountability.

### What It Is Not

**Not a machine-learning model.** The agent detects only what it was coded to detect. It does not learn from historical outcomes. It does not adapt. Same input always produces same output.

**Not a substitute for trade management.** The agent fires the alert. You or your EA executes. Partial close percentages are in the TradeSgnl format, but the operator monitors and makes discretionary adjustments.

**Not infallible.** The regime filter goes stale. The 5-layer score is display-only. The ATM generates false signals in chop. The Liq Gate reduces but does not eliminate structurally bad entries. The autopsy engine shows you when the system was wrong and why.

**Not responsible for your results.** "Not financial advice" is on every message for a reason. The tool provides structured information. You make the decisions.

---

### A Note On The Architecture

ADSA was built from Nairobi, East Africa. In a market dominated by Western operators, Western signals, Western timing assumptions, and Western audiences, the decision to build a dual-channel broadcast engine, a machine-readable ML data block, and a community-facing public channel came from understanding that retail traders in emerging markets need access to the same structured intelligence that institutional operators take for granted.

The Glass Box architecture is not a marketing concept. It came from a simple question: if you are going to put your analysis in front of a community, can you show your work? The answer in ADSA is yes — down to the line of code. That accountability is the foundation of the community this tool is built to support.

The tool does not pretend to give you an edge you did not earn. It gives you infrastructure — a reliable, auditable, documented system for reading structure, sizing risk, and communicating with discipline. The edge comes from understanding the system well enough to operate it. This document is that understanding.

---

*ADSA v7.1 — Pine Script v6 — Absolute Dollar Intelligence*
*© 2026 Absolute Dollar | Super Admin Edition — Invite Only*

*Build: MTF Liquidity Trail + Fibonacci Trend Gate + Chain Narrative*
*Base: ATM Bot (ATR trailing stop) + 4-Layer Fractal + Platinum Risk Model*

*Not financial advice. Use at your own risk.*
