# ABSOLUTE DOLLAR SUPREME AGENT — ADSA v7.1
### Augmented Intelligence Protocol | Pine Script v6
**© 2026 Absolute Dollar Intelligence | Invite-Only | Not Financial Advice**

---

## Table of Contents
1. [What This Is — Honestly](#1-what-this-is--honestly)
2. [Architecture — 19 Subsystems](#2-architecture--19-subsystems)
3. [How Signals Actually Work](#3-how-signals-actually-work)
4. [The Gate Chain](#4-the-gate-chain)
5. [Full Settings Guide](#5-full-settings-guide)
6. [What the Dashboard Shows](#6-what-the-dashboard-shows)
7. [What Telegram Messages Look Like](#7-what-telegram-messages-look-like)
8. [Alert & Telegram Setup](#8-alert--telegram-setup)
9. [TradeSgnl / Bitget Automation](#9-tradesgnl--bitget-automation)
10. [M1 & M5 Intraday Framework](#10-m1--m5-intraday-framework)
11. [Is This Approach Profitable?](#11-is-this-approach-profitable)
12. [Real-Time Intelligence Layer](#12-real-time-intelligence-layer)
13. [Glossary](#13-glossary)

---

## 1. What This Is — Honestly

ADSA v7.1 is a **professional multi-timeframe strategy** built in Pine Script v6. Here is the unfiltered architectural description:

**Core signal generator**: UT Bot — an ATR trailing stop crossover. When `close` crosses above the buy trail, a long signal fires. When it crosses below the sell trail, a short fires. That's the trigger. Everything else is context, filtering, reporting, and trade management.

**What the system adds on top of that trigger:**
- A 4-layer fractal consensus check (are the same trail algorithms aligned on higher TFs?)
- A regime filter (RSI momentum latch — is RSI in a bullish posture?)
- A structural liquidity gate (is price on the correct structural side of an H1 pivot?)
- A Fibonacci trend gate (is the double-EMA trend aligned? — off by default)
- A 5-layer composite score (reads Regime/VWAP/Fib across D/H4/H1/M15/M5 — **display only, does not gate signals**)
- A full trade management engine (TP1 at 1:1, TP2 at 1.5:1, TP3 at 2:1, Holder Mode runner)
- Dual Telegram broadcast with Glass Box reasoning per event
- Daily performance report with ML data block

**What provides the edge**: The MTF Liquidity Gate is the single most important improvement over a raw UT Bot. It prevents entering longs into bearish supply zones and shorts into bullish demand zones — the most common structural entry failure.

**What is decoration**: The 5-layer score is a genuine read of MTF alignment but it does not currently block or modify any signal. It is an intelligence display. Use it manually to assess conviction before acting.

---

## 2. Architecture — 19 Subsystems

| # | Subsystem | What It Does | Active by Default |
|---|-----------|--------------|-------------------|
| 1 | **Fractal 4-Layer Consensus** | Reads chart-TF `posState` (ATM bot direction) through D/Anchor/Filter TF lens. `MASTER SYNC` = same trail logic long on all 4 TFs simultaneously | Display + label |
| 2 | **5-TF Composite Scoring** | D/H4/H1/M15/M5 each scored on 3 factors (Regime, VWAP, Fib). Range: +15 to −15 | Display only |
| 3 | **Glass Box Alerts** | Structured reasoning string per event — entry, SL hit, TP levels, rejection, liquidity sweep, BOS/CHoCH | ✅ ON |
| 4 | **Trade Progression Engine** | TP1→TP2→TP3→Holder Mode with partial closes. SL autopsy on stop hit | ✅ ON |
| 5 | **SL Autopsy Engine** | On stop: contextual narrative explaining WHY | ✅ ON |
| 6 | **Signal Rejection Reports** | Blocked signal = alert with reason (regime, fib, liq) | ✅ ON |
| 7 | **SMC Engine** | BOS, CHoCH, Order Blocks, FVGs, EQH/EQL, Premium/Discount, Liquidity sweeps | ✅ ON (configurable) |
| 8 | **Adaptive VWAP + VP + Fib Bands** | Swing-anchored VWAP, session Volume Profile with POC/VAH/VAL, Fibonacci extension bands | ✅ ON |
| 9 | **Platinum Risk Model** | ATR-based SL, 1:1/1.5:1/2:1 TPs, position size = `risk_$ / (SL_dist × notional)`. Asset-routed: forex/crypto/futures | ✅ ON |
| 10 | **Dual Telegram Broadcast** | War Room (full Glass Box) + Public (sanitized direction + bias only) | Requires Chat IDs |
| 11 | **Super Admin Control Panel** | Manual bias override, silence mode, asset note, operator commentary | ✅ ON |
| 12 | **Trade ID Engine** | `ATM-YYYYMMDD-HHMM-DIR-N` per trade | ✅ ON |
| 13 | **Pip Tracker** | Daily-reset actual vs expected pip comparison. TP1/TP2/TP3/SL tracked separately | ✅ ON |
| 14 | **Performance Table** | 5-column × 10-row live table: TP hits, SL hits, PF, Win Rate, pip totals | ✅ ON |
| 15 | **Daily Report Engine** | Full trade log + ML data block dispatched at configurable UTC hour | ✅ ON |
| 16 | **Live Dollar P&L Tracker** | Per-bar unrealised P&L in quote currency, fully asset-routed | ✅ ON |
| 17 | **PDH/PDL Context Engine** | Previous Day High/Low with status: Above PDH / Below PDL / Inside Range | ✅ ON |
| 18 | **MTF Liquidity Trail** *(v7.1)* | Pivot-based holder trail from H1 (or configured TF) + ATM signal gate | ✅ ON |
| 19 | **Fibonacci Trend Gate** *(v7.1)* | Double-EMA Fib trend gates ATM signals against counter-trend entries | OFF (toggle) |

---

## 3. How Signals Actually Work

Understanding the exact signal path prevents false expectations.

### Step 1 — ATR Trail Computation (Section 7)
```
trail_buy  = ratchets UP when close > trail, never retreats while long
trail_sell = ratchets DOWN when close < trail, never retreats while short
```
Multiplier: `ATR(period) × sensitivity`. Default: `ATR(2) × 3.5`.

### Step 2 — Raw Signal
```
buy_signal_raw  = close > trail_buy  AND ta.crossover(close, trail_buy)
sell_signal_raw = close < trail_sell AND ta.crossover(trail_sell, close)
```
`EMA(close, 1)` is mathematically identical to `close` — it is not a filter.

### Step 3 — Bar Close Confirmation
```
buy_signal  = buy_signal_raw  AND barstate.isconfirmed
sell_signal = sell_signal_raw AND barstate.isconfirmed
```
Signals only fire on a confirmed (closed) bar. Zero repainting.

### Step 4 — Gate Chain (see Section 4 below)
```
buy_signal_filtered = buy_signal AND regimeBullish AND fibGateBull AND liqGateBull
```

### Step 5 — Position State + Fractal Consensus
```
posState = 1 (long) / -1 (short) / 0 (flat)
sovereign_state = request.security(D,    posState)  ← Daily ATM direction
anchor_state    = request.security(H1,   posState)  ← H1 ATM direction
filter_state    = request.security(M15,  posState)  ← M15 ATM direction
exec_state      = posState                           ← Chart-TF ATM direction
MASTER SYNC = all four == 1 (or all == -1)
```

### Step 6 — Entry
```
buy_signal_confirmed = buy_signal_filtered AND posState == 1 AND posState[1] <= 0
```
Only fires on the transition bar — the first bar where posState flips to 1. Not every bar `posState == 1`.

### Step 7 — Trade Management
| Event | Action |
|-------|--------|
| TP1 (1:1 R) | Close 33% via `strategy.close(qty_percent=33)` |
| TP2 (1.5:1 R) | Close 50% of remaining |
| TP3 (2:1 R) | Close 75% of remaining → Holder Mode activates |
| Holder Mode | Trail 25% runner using VWAP/Structural/MTF Liq pivot |
| SL hit | Close 100%, SL Autopsy alert fires |

---

## 4. The Gate Chain

These are the actual conditions that filter a raw ATM signal. Listed in execution order:

### Gate 1 — Regime Filter (ON by default)
```pine
positive = latches TRUE when RSI crosses above 55 with rising EMA5
         = releases when RSI < 50 with falling EMA5
regimeBullish = positive  (or positive AND vwapBullish if VWAP gate ON)
```
**Important behaviour**: This is a *latch*. Once `positive = true`, it stays true until the release condition fires. In a trending market it stays active for days — this is correct. In a choppy market it stays stale after a pullback — this is the risk. The regime filter is most reliable in trending sessions (London/NY directional days). It is least reliable in ranging/news-driven conditions.

### Gate 2 — Fibonacci Trend Gate (OFF by default)
```pine
_basis_gate = EMA(EMA(close, 200), 200)
fibGateBull = _basis_gate > _basis_gate[1]  ← trend rising
fibGateBear = _basis_gate < _basis_gate[1]  ← trend falling
```
The double-EMA of 200 bars is a very slow, smooth trend engine. Enable it when you want to eliminate all counter-trend signals. Leave OFF for M1/M5 intraday trading where you need signals in both directions within sessions.

### Gate 3 — MTF Liquidity Gate (ON by default)
```pine
liqGateBull = close > mtf_liq_pivot_low   ← above structural demand
liqGateBear = close < mtf_liq_pivot_high  ← below structural supply
```
Pivot levels are fetched from H1 (configurable) using `ta.valuewhen` inside `request.security` with `lookahead_off`. No repainting. The pivot length dropdown (14/20/**50**/100/200) controls how many bars each side confirm a swing. Default 50 matches the Claw Liquidity Suite fast-pivot setting.

**This is the most valuable gate in the system.** It prevents entering longs below where the market has already sold off, and shorts above where the market has already bought up. Structural entry failure is the most common reason technically valid ATM signals immediately reverse.

### What the Score Means (but doesn't gate)
```
total_score = sov_score + h4_score + h1_score + m15_score + m5_score
Range: +15 (all TFs screaming bull) to -15 (all TFs screaming bear)
```
The score does not block or modify any signal. It is a **conviction indicator** — use it manually:
- `score ≥ 6`: high confidence, standard or increased size
- `score 3–5`: moderate alignment, reduced size, TP1 target
- `score < 3`: weak alignment, consider skipping regardless of ATM signal
- Signal direction opposing score direction: **strong warning flag**

---

## 5. Full Settings Guide

### 🔐 Super Admin Control Panel
| Input | Default | Notes |
|-------|---------|-------|
| Sovereign TF | `D` | Macro veto layer — Daily ATM direction governs MASTER SYNC |
| Manual Bias Override | `AUTO` | `SILENCE` suppresses all alerts. `FORCE BULL/BEAR` overrides 4-layer logic |
| Asset Context Note | *(empty)* | Appended to every Telegram alert, e.g. `"GOLD — London breakout watch"` |
| Operator Commentary | *(empty)* | War Room only — your personal analysis note |
| Sanitize Public Channel | `ON` | Public gets direction + bias only, no levels |

### 🧠 Fractal 4-Layer Protocol
| Input | Default | Notes |
|-------|---------|-------|
| Anchor TF (Layer 2) | `60` (H1) | Commander TF — should align with Sovereign daily direction |
| Filter TF (Layer 3) | `15` (M15) | Navigator TF — confirms Anchor direction |
| Exec TF (Layer 4) | *Chart TF* | Automatic — whatever chart you are on |

### 🤖 ATM Bot Settings
| Input | Default | Notes |
|-------|---------|-------|
| Buy Sensitivity | `3.5` | ATR multiplier for the buy trail. Higher = wider trail = fewer but higher quality signals |
| Buy ATR Period | `2` | ATR lookback period. 2 = very reactive to recent volatility |
| Sell Sensitivity | `3.5` | ATR multiplier for the sell trail |
| Sell ATR Period | `2` | ATR lookback for sell trail |
| Enable Regime Filter | `ON` | Require RSI momentum confirmation. See Gate 1 above |
| Require VWAP Confirmation | `OFF` | Also require Adaptive VWAP swing agreement with regime |
| Activate Glass Box Reports | `ON` | Enable rich per-event Telegram messages |

### 💰 Risk Management
| Input | Default | Notes |
|-------|---------|-------|
| Risk Per Trade ($) | `15.0` | Dollar amount risked per trade. Controls position size |
| SL Buffer (ATR Multiplier) | `1.5` | Buffer added beyond the structural SL level |
| Show Min-Unit Actual Risk | `ON` | Shows reference risk at minimum 0.01 lot for comparison |
| Strict One-Trade Rule | `OFF` | Prevents reversal signals while a trade is active |
| Holder Mode Trail | `Structural` | `VWAP` / `Structural` / `MTF Liquidity` (v7.1) |

### 💧 MTF Liquidity Trail *(v7.1)*
| Input | Default | Notes |
|-------|---------|-------|
| Enable MTF Liquidity Trail | `ON` | Master toggle for trail and gate |
| Trail Timeframe | `60` (H1) | TF for pivot high/low. Must be ≥ chart TF |
| Pivot Lookback Length | `50` | **Dropdown: 14 / 20 / 50 / 100 / 200.** 50 = Claw Liquidity Suite match. 200 = macro pivots |
| Gate ATM Signals to Liq Trail | `ON` | Block entries on wrong structural side |

### 📊 Fibonacci Trend Gate *(v7.1)*
| Input | Default | Notes |
|-------|---------|-------|
| Require Fibonacci Trend Alignment | `OFF` | Enable for with-trend-only mode. Leave OFF for intraday scalping |

---

## 6. What the Dashboard Shows

```
 🚀 ABSOLUTE DOLLAR AGENT
 Absolute Dollar Intelligence
 ─────────────────────────
 🔐 AUTO | 👑 Sovereign (D): BULL
 📌 XAUUSD — London breakout watch
 📊 Score: 8.0/15  |  Public: SANITIZED
 ─────────────────────────
 ⏱️ FRACTAL 4-LAYER SYNC
 L1 Sovereign (D):  BULL
 L2 Anchor   (60):  BULL
 L3 Filter   (15):  BULL
 L4 Exec     (5):   BULL
 🔥 FULLY ALIGNED: BULLISH (4-LAYER)
 ─────────────────────────
 📊 CORE SIGNALS
 XAUUSD | 5  2341.45
 👑 LONDON SESSION  |  ATR: Med (1.82)
 📅 Daily Context: ↑ Above PDH [PDH: 2338.10 | PDL: 2321.90]
 ATM 🟢  Regime 📈
 VWAP 📈  Fib 📈
 RSI 📈 (61)  MACD: Bull
 🔒 FibGate: OFF  LiqGate: ✅ OK
 💧 MTF Pivots [60]: H=2351.20  L=2328.60
 ─────────────────────────
 📈 MTF EMA (9/21)
 1m📈 5m📈 15m📈 30m📈 1H📈
 4H📈 1D📈 1W📈 1M📈
 ─────────────────────────
 🧠 5-LAYER AI NARRATIVE  [8.0/15]
 📈 BULLISH BIAS (Strong)
  ├── D  (Sovereign) 🟢
  │    Regime :Long V.WAP :Bull Fib Trend :Bull RSI:Bull
  ├── H4 (Anchor) 🟢
  │    Regime :Long V.WAP :Bull Fib Trend :Bull RSI:Neut
  ├── H1 🟡
  │    Regime :Long V.WAP :Bull Fib Trend :Neut RSI:Bull
  ├── M15 🟡
  │    Regime :Long V.WAP :Neut Fib Trend :Bull RSI:Bull
  └── M5 🟢
       Regime :Long V.WAP :Bull Fib Trend :Bull RSI:Bull
 ─────────────────────────
 💡 AGENT ADVICE
 Confident entry — bias confirmed. Verify chart.
 ─────────────────────────
 💧 LIQUIDITY
 ⚪ Neutral
 🟢 Buy-side:  2351.20
 🔴 Sell-side: 2321.90
 ─────────────────────────
 💰 TRADE SETUP
 📊 Phase: TP1 HIT — Hunting TP2
 ID: ATM-20260617-0923-L-1
 Dir: 🟢 LONG
 💡 Min-Unit Risk: ~$1.82 | Variable: $15 → 0.0082 Lots
 💵 Live P&L: +$22.40 (+14.9 pips)
 🚪 Entry: 2335.60  🛑 SL: 2332.88  (27.2 pips)
 🎯 TP1: 2338.32 ✅  (27.2 pips)
 🎯 TP2: 2339.68    (40.8 pips)
 🚀 TP3: 2341.04    (54.4 pips)
 📈 Peak: 18.2 pips
 ─────────────────────────
 📅 TODAY
 Sigs: 2  Blocked: 1  LDN: 2  NY: 0
 TP1: 1  TP2: 0  TP3: 0  SL: 0
 WR: 50.0%  PF: —  Net: +14.9 pips
 Report: ⏳ 21:00 UTC
 ─────────────────────────
 ⚠️ Not financial advice.
 © Absolute Dollar 2026
```

---

## 7. What Telegram Messages Look Like

### War Room — Long Signal (Master Sync)

```
━━━━━━━━━━━━━━━━━━━━━
🔥 ABSOLUTE DOLLAR — WAR ROOM
Supreme Agent ADSA v7.1
━━━━━━━━━━━━━━━━━━━━━
📊 Asset   : XAUUSD
💰 Price   : 2335.60
🌍 Session : 👑 LONDON SESSION
📅 Daily   : ↑ Above PDH [2338.10 | 2321.90]
📌 Context : XAUUSD — London breakout watch
─────────────────────
🔔 EVENT: 🔥 MASTER SYNC LONG — 4-LAYER ALIGNED
─────────────────────
📝 AGENT COMMENTARY
All 4 layers BULLISH. Sovereign + Commander + Navigator + Executor aligned.
Score: 8.0/15 | ATR: Med
High-probability trend continuation. R:R 2.0+ advised.
─────────────────────
🎯 TRADE PARAMETERS
─────────────────────
Direction  : 🟢 LONG
Entry      : 2335.60
Stop Loss  : 2332.88  (27.2 pips)
TP1 (1:1)  : 2338.32  (27.2 pips)
TP2 (1.5:1): 2339.68  (40.8 pips)
TP3 (2:1)  : 2341.04  (54.4 pips)
Risk $     : $15.00 → 0.0082 Lots
Min-unit risk: ~$1.82
Trade ID   : ATM-20260617-0923-L-1
4-Layer    : 🔥 FULLY ALIGNED: BULLISH (4-LAYER)
─────────────────────
🧠 GLASS BOX AI NARRATIVE
─────────────────────
Master Bias  : 📈 BULLISH BIAS (Strong)
Score        : 8.0/15
Daily Context: ↑ Above PDH [PDH: 2338.10 | PDL: 2321.90]
─────────────────────
🔗 DECISION CHAIN
① Sovereign D   🟢 Long [+3] → PASS
② Commander H4  🟢 Long [+3] → PASS
③ Navigator H1  🟡 Long [+1] → LEAN
④ Filter    M15 🟡 Long [+1] → LEAN
⑤ Executor  M5  🟢 Long [+2] → PASS
🔒 Fib: OFF  Liq: L:✅ S:✅
★ 🟢 LONG · 8.0/15 · WAIT CONF
─────────────────────
💡 AGENT ADVICE
Confident entry — bias confirmed. Verify chart.
PF: —  WR: —
─────────────────────
🧊 LIQUIDITY
Buy-side  : 2351.20
Sell-side : 2321.90
Context   : ⚪ Neutral
━━━━━━━━━━━━━━━━━━━━━
⚠️ Not financial advice. © 2026 Absolute Dollar
```

### War Room — Signal Blocked

```
━━━━━━━━━━━━━━━━━━━━━
🔥 ABSOLUTE DOLLAR — WAR ROOM
Supreme Agent ADSA v7.1
━━━━━━━━━━━━━━━━━━━━━
📊 Asset   : XAUUSD
💰 Price   : 2328.40
🌍 Session : 👑 LONDON SESSION
📅 Daily   : ↔ Inside Range [PDH: 2338.10 | PDL: 2321.90]
─────────────────────
🔔 EVENT: ⛔ SIGNAL BLOCKED — REGIME FILTER
─────────────────────
📝 AGENT COMMENTARY
LONG blocked. Sovereign: BULL | Score: 2.0/15
RSI/VWAP/Regime misaligned. Silence = a position.
─────────────────────
🧠 GLASS BOX AI NARRATIVE
─────────────────────
Master Bias  : ⏳ QUIET BULL — WAIT
Score        : 2.0/15
Daily Context: ↔ Inside Range
─────────────────────
🔗 DECISION CHAIN
① Sovereign D   🟡 Long [+1] → LEAN
② Commander H4  ⚪ Neut [0]  → HOLD
③ Navigator H1  🟡 Long [+1] → LEAN
④ Filter    M15 ⚪ Neut [0]  → HOLD
⑤ Executor  M5  ⚪ Neut [0]  → HOLD
🔒 Fib: OFF  Liq: L:✅ S:✅
★ 🟡 LEAN LONG · 2.0/15 · STAND ASIDE
━━━━━━━━━━━━━━━━━━━━━
⚠️ Not financial advice. © 2026 Absolute Dollar
```

### War Room — SL Hit with Autopsy

```
━━━━━━━━━━━━━━━━━━━━━
🔥 ABSOLUTE DOLLAR — WAR ROOM
Supreme Agent ADSA v7.1
━━━━━━━━━━━━━━━━━━━━━
📊 Asset   : XAUUSD
💰 Price   : 2332.10
🌍 Session : 🗽 NY SESSION
📅 Daily   : ↔ Inside Range
─────────────────────
🔔 EVENT: 💀 STOP LOSS HIT — ATM-20260617-1142-L-2
─────────────────────
📝 AGENT COMMENTARY
[SL Autopsy — XAUUSD Long]
Entry: 2335.90  SL hit: 2332.88  Distance: 30.2 pips
Score at entry: 4.0/15 — Moderate alignment. Below ≥6 threshold.
Regime was BULLISH (latched) but H4 was already neutral.
Sovereign: BULL but fractal alignment was partial (L3/L4 only).
Liq gate was clear — entry structure was valid.
Assessment: Low-conviction entry in chop. Regime latch overstated momentum.
Protocol: Stand aside until score ≥ 6 before next entry.
━━━━━━━━━━━━━━━━━━━━━
⚠️ Not financial advice. © 2026 Absolute Dollar
```

### Public Channel — Same Event

```
━━━━━━━━━━━━━━━━━━━━━
🤖 ABSOLUTE DOLLAR — ATM AGENT
Supreme Agent ADSA v7.1
━━━━━━━━━━━━━━━━━━━━━
📊 Asset   : XAUUSD
🌍 Session : 👑 LONDON SESSION
📅 Daily   : ↑ Above PDH
─────────────────────
🔔 EVENT: 🔥 MASTER SYNC LONG — 4-LAYER ALIGNED
─────────────────────
📝 COMMENTARY
🔥 Master Sync Long — 4 layers aligned.
─────────────────────
🧠 NARRATIVE
Bias  : 📈 BULLISH BIAS (Strong)
Score : 8.0/15
Sync  : 🔥 FULLY ALIGNED: BULLISH (4-LAYER)
Daily : ↑ Above PDH
Dir   : 🟢 LONG
─────────────────────
🔗 Full Glass Box report in War Room.
─────────────────────
⚠️ Not financial advice. © 2026 Absolute Dollar
```

---

## 8. Alert & Telegram Setup

### TradingView Alert Configuration

1. Right-click on the chart → **Add Alert**
2. **Condition**: `Absolute Dollar Agent` → `alert() function calls only`
3. **Message**: `{{alert_message}}` (exactly — the script builds the full message)
4. **Webhook URL**: `https://api.telegram.org/botYOUR_TOKEN/sendMessage`
5. **Frequency**: `Once Per Bar Close` (required — the script uses `barstate.isconfirmed`)

### Telegram Bot Setup

1. Message `@BotFather` → `/newbot` → copy the token
2. Get your chat ID from `https://api.telegram.org/botTOKEN/getUpdates`
3. In Settings → Telegram Broadcast: enter Chat ID (Premium) and Chat ID (Public)
4. Set both toggles ON

### Two channels explained

**War Room (Premium chat)** — full Glass Box every event: trade params, score, chain narrative, PDH/PDL, SL autopsy, commentary, daily report.

**Public channel** — sanitized: event type + direction + bias + score + 4-layer sync phase. No entry/SL/TP levels.

---

## 9. TradeSgnl / Bitget Automation

### TradeSgnl (MT5)

Replace `LICENSE_ID` in the Long/Short Entry Message inputs with your license key. Leave TP1/TP2/TP3 messages empty — TradeSgnl handles partial closures natively via `pct1` and `pct2` in the entry message.

Default entry message format:
```
LICENSE_ID,{{ticker}},buy,vol_dollar={{risk}},sl_price={{sl}},tp1_price={{tp1}},pct1=0.33,tp2_price={{tp2}},pct2=0.50,tp3_price={{tp3}},exent=1
```

### Bitget Webhook

Enable in Settings → Bitget Signal Bot. Create a second TradingView alert on the same chart pointing to your Bitget webhook URL. JSON output format:
```json
{"action":"buy","size":"0.0082","symbol":"XAUUSD","price":"2335.60","sl":"2332.88","tp1":"2338.32","id":"ATM-20260617-0923-L-1","score":"8.0","sync":"🔥 FULLY ALIGNED: BULLISH (4-LAYER)"}
```

---

## 10. M1 & M5 Intraday Framework

### Why M5 is the primary intraday TF

The 5-layer scoring engine hardcodes D/H4/H1/M15/M5 as its five layers. M5 is the Executor layer in the scoring tree. Running on M5 with default settings means the system is architecturally aligned.

### Recommended Settings: M5

| Setting | Recommended | Reason |
|---------|-------------|--------|
| Chart TF | 5m | Executor layer in scoring tree |
| Sovereign TF | `D` | Daily macro filter stays valid for intraday |
| Anchor TF | `60` (H1) | Default is correct |
| Filter TF | `15` (M15) | Default is correct |
| ATM Sensitivity | `2.5`–`3.0` | Tighter than default; more M5 signals |
| Liq Trail TF | `15` (M15) | H1 pivots are too wide for M5; M15 is structurally relevant |
| Holder Mode Trail | `MTF Liquidity` | M5 structural trail is too tight for runners |
| Require VWAP | `ON` | Session VWAP is a meaningful directional anchor on M5 |
| Require Fib Trend | `OFF` | You need both directions within sessions |

### Recommended Settings: M1

| Setting | Recommended | Reason |
|---------|-------------|--------|
| Chart TF | 1m | Scalp execution |
| Sovereign TF | `D` | Daily still valid as macro filter |
| Anchor TF | `15` (M15) | Drop one level from M5 setup |
| Filter TF | `5` (M5) | Drop one level |
| ATM Sensitivity | `2.0`–`2.5` | M1 needs tighter trail |
| Liq Trail TF | `5` (M5) | M5 pivots are the right structural anchor |
| Pivot Length | `14`–`20` | Shorter lookback for recent M5 swings |

### The M5 Trade Playbook

**Pre-session checklist (before London or NY open)**:
1. Is Daily bullish, bearish, or neutral? (L1 Sovereign)
2. Are PDH/PDL above/below price, or inside range?
   - Inside range → lower probability. Wait for a break.
3. What is `total_score`?
   - ≥ 6: confident entry, standard size, full TP sequence
   - 3–5: half size, TP1 target only
   - < 3: stand aside regardless of ATM signal
4. Is `LiqGate: ✅ OK` on dashboard? (enforced automatically — but check)

**Signal quality tiers**:
| Scenario | Score | 4-Layer | Action |
|----------|-------|---------|--------|
| MASTER SYNC | ≥ 10 | All 4 aligned | Full position, TP3 target, MTF runner |
| Strong Bias | 6–9 | 3+ aligned | Standard position, TP3 target |
| Moderate | 3–5 | 2 aligned | Half position, TP1 only |
| Counter-trend | Any | Sovereign opposite | TP1 only, quarter size |
| Weak | < 3 | — | Skip |

### Session Windows (UTC)
| Session | Window | Notes |
|---------|--------|-------|
| **London** | 07:00–12:00 | Highest MASTER SYNC probability |
| **NY Overlap** | 12:00–16:00 | Highest liquidity; watch PDH/PDL sweeps |
| **NY Solo** | 16:00–21:00 | Continuation plays only |
| **Avoid** | 21:00–06:00 | Low ATR; system will flag LOW VOLATILITY |

---

## 11. Is This Approach Profitable?

**Honest structural assessment:**

### What the architecture gets right

**1. Risk management is structurally sound.**
Fixed dollar risk per trade, correctly routed for forex/crypto/futures. Partial exits lock in progressively more profit while letting a runner work. The 33%→50%→75% sequence is mathematically correct for positive expectancy if TP1 win rate is ≥ 40%.

**2. The MTF Liquidity Gate targets a real structural failure mode.**
Entering longs below a supply zone (above a confirmed H1 swing high) is the most common mechanical reason valid-looking signals fail immediately. The liqGate addresses this directly. It is the highest-leverage single filter in the system.

**3. The 4-layer fractal consensus identifies real trend confluence.**
`MASTER SYNC` means the same ATR-trail algorithm has flipped in the same direction on all 4 timeframes simultaneously. That is genuine multi-TF momentum alignment — not just a trend indicator overlay. It lags (appears after a move has started) but lag is fine for trend following.

**4. The Glass Box creates an audit loop.**
A system that explains every blocked signal and every SL hit in structured language creates the feedback you need to improve. After 30 signals you will see which gate is blocking most, which session generates the most SL hits, and whether your entry score threshold is correct.

### What undermines it

**1. The regime filter latches.**
Once `positive = true`, it stays true until `RSI < 50 with falling EMA5`. In choppy markets this latch becomes stale quickly — you get regime-confirmed signals into ranging conditions. **Rule: when the dashboard shows `ATR: Low` and `⏳ QUIET BULL`, the regime filter is lying to you. Stand aside regardless of signal.**

**2. The score doesn't gate signals.**
A score of -8 with a long signal means 5 timeframes are disagreeing with your entry. The system will still take that long. You must manually use the score as your conviction filter. **Rule: do not take signals with `total_score < 3` (longs) or `> -3` (shorts).**

**3. The ATR period is very short.**
`ATR(2)` with multiplier 3.5 is aggressive — it creates a tight, reactive trail that generates more signals but also more false crosses in ranging/news-driven markets. In high-volatility sessions (NFP, Fed) the trail will fire many crosses. Use `ATR(3–5)` for M5 to reduce this.

**4. Signal frequency drops sharply with stricter gates.**
With Regime + LiqGate both ON, and you also manually filtering on score ≥ 6, you may get 1–3 signals per session. That is correct — it is the price of quality. The danger is manual override: taking the `CT-L` gold triangle signals because "the setup looks clean." Counter-trend entries have lower expectancy by definition.

### Realistic Expectations

| Metric | Realistic Range |
|--------|----------------|
| **Win Rate (TP1 reached)** | 45–60% when score ≥ 6 respected |
| **Profit Factor** | 1.5–2.5 when discipline maintained |
| **MASTER SYNC signals** | 2–5 per week on a major pair |
| **Average hold time (M5)** | 30 min–4 hours to TP3 |
| **Drawdown periods** | 5–8 consecutive SLs when low-score entries taken |

**The honest bottom line**: The system's edge is real but narrow, and it lives almost entirely in the combination of the LiqGate (structural positioning) + score discipline (≥ 6 only). Everything else is infrastructure. Use the infrastructure — it will prevent boredom trading. But the discipline of the score threshold is what will determine whether you are profitable.

---

## 12. Real-Time Intelligence Layer

The ADSA v7.1 Telegram War Room message contains everything needed for an external intelligence check on each signal. Each message includes:
- Event type and direction
- Score at time of signal (0–15)
- 4-layer sync state
- Chain narrative (each layer's Regime/VWAP/Fib score)
- LiqGate status
- Entry, SL, TP levels
- PDH/PDL context
- Session

This data is sufficient for a second-opinion analysis before acting on a signal. The check is:

1. **Score alignment**: Does the score support the signal direction? Score ≥ 6 for longs, ≤ -6 for shorts. Score opposing direction = warning.
2. **Chain quality**: How many of the 5 layers have `PASS` (|score| ≥ 2) vs `LEAN` (|score| = 1) vs `HOLD` (score = 0)?
3. **Session context**: London/NY directional day vs Asia/NY-late range? ATR: High/Med/Low?
4. **PDH/PDL**: Is the signal trading through a major structural level (PDH/PDL breakout) or fading into a range?
5. **Previous signal context**: Was the last signal an SL hit? What was the score? Consecutive low-score SL hits = regime is stale.

The goal of this layer is to act as the gating logic that the score cannot currently do automatically — a human-in-the-loop filter that evaluates conviction before execution.

---

## 13. Glossary

| Term | Meaning |
|------|---------|
| **UT Bot** | The underlying signal generator — ATR trailing stop crossover (ta.crossover(close, trail)) |
| **Master Sync** | All 4 fractal layers aligned in same direction — the strongest signal type |
| **Counter-Trend (CT)** | Signal fires opposite to the Sovereign (Daily) ATM direction |
| **Regime** | RSI momentum latch — `positive` when RSI crosses above 55 with rising EMA5; latches until RSI < 50 with falling EMA5 |
| **Liq Gate** | MTF Liquidity Gate — blocks entries on wrong structural side of a higher-TF pivot |
| **Fib Gate** | Fibonacci Trend Gate — blocks entries against the double-EMA trend direction |
| **Holder Mode** | After TP3 hit — trails the 25% runner using VWAP, Structural pivot, or MTF Liq pivot |
| **Glass Box** | Core design principle: every alert includes transparent reasoning, not just a signal direction |
| **Sovereign** | Layer 1 of the 4-layer fractal — the Daily ATM direction; macro veto |
| **posState** | Internal direction variable: 1 = long, -1 = short, 0 = flat |
| **total_score** | 5-TF composite score (+15 to -15). Display only. Does not gate signals. Use manually as conviction filter |
| **ai_advice** | Score-contextual text string shown in dashboard and Telegram. Not automated trade logic |
| **PDH/PDL** | Previous Day High / Previous Day Low — key intraday structural levels |
| **POC** | Point of Control — Volume Profile price with most traded volume |
| **VAH/VAL** | Value Area High / Low — range containing 70% of session volume |
| **BOS** | Break of Structure — price breaks a prior swing high/low in the trend direction |
| **CHoCH** | Change of Character — price breaks structure against the prior trend (potential reversal) |
| **OB** | Order Block — last bullish/bearish candle before a BOS; used as S/R zone |
| **FVG** | Fair Value Gap — 3-candle imbalance where price may return to fill |
| **EQH/EQL** | Equal Highs / Equal Lows — clustered swing levels that act as liquidity targets |
| **PF** | Profit Factor — gross winning pips / gross losing pips. PF > 2.0 = STRONG |

---

*Not financial advice. Past signal behavior does not guarantee future performance.*
*© 2026 Absolute Dollar Intelligence | ADSA v7.1 | Invite-Only*
