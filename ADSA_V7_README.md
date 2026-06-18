# Absolute Dollar Agent — ADSA v7.0
## TradingView Pine Script Strategy | Super Admin Edition
### © 2026 Absolute Dollar Intelligence — Invite Only | Not Financial Advice

---

## Contents

1. [What ADSA v7.0 Is](#1-what-adsa-v70-is)
2. [17 Subsystem Architecture](#2-17-subsystem-architecture)
3. [Installation & TradingView Setup](#3-installation--tradingview-setup)
4. [Input Panel Reference](#4-input-panel-reference)
5. [Signal Hierarchy — 4-Layer Fractal Protocol](#5-signal-hierarchy--4-layer-fractal-protocol)
6. [Risk Model & Position Sizing](#6-risk-model--position-sizing)
7. [Trade Lifecycle — Entry to Exit](#7-trade-lifecycle--entry-to-exit)
8. [Dashboard & Performance Table](#8-dashboard--performance-table)
9. [Telegram Dual-Channel Broadcast](#9-telegram-dual-channel-broadcast)
10. [Bitget Signal Bot Integration](#10-bitget-signal-bot-integration)
11. [TradeSgnl / MT5 Automation](#11-tradesgnl--mt5-automation)
12. [Daily Report Engine](#12-daily-report-engine)
13. [Intraday Trading Strategy](#13-intraday-trading-strategy)
14. [Glass Box Alert Reference](#14-glass-box-alert-reference)
15. [SMC Engine Reference](#15-smc-engine-reference)
16. [Asset Router — Supported Markets](#16-asset-router--supported-markets)
17. [Changelog v7.0 vs v6.1](#17-changelog-v70-vs-v61)

---

## 1. What ADSA v7.0 Is

ADSA v7.0 is a **complete institutional-grade trading system** built in Pine Script v6. It is not a single indicator — it is 17 coordinated subsystems that share a unified state machine, producing one read-to-execute trade plan per signal with all risk parameters computed automatically.

The system's job, in plain terms:

> Read the market across 5 timeframes. Score the bias numerically. If 4 layers align, fire a signal. Calculate where to enter, where the stop goes, three take-profit targets, and exactly how much size to trade for a fixed dollar risk. Broadcast the trade plan to Telegram, route it to a broker bot, and narrate every decision transparently so the operator understands *why* the trade was taken or rejected.

Every element — from the ATR trailing stop that generates the raw signal, to the sovereign daily layer that may veto it, to the SL autopsy that explains a losing trade in plain language — is surfaced in the dashboard and broadcast in real time.

### What is new in v7.0 (vs v6.1 / SA-GAIP)

| Addition | Summary |
|---|---|
| **Live Dollar P&L Tracker** | Real-time unrealised P&L per bar (`price_diff × position_size × contract_notional`), asset-routed. Displayed in the dashboard Trade Setup panel. |
| **PDH/PDL Context Engine** | Previous Day High/Low fetched (no lookahead). Status: `Above PDH` / `Below PDL` / `Inside Range`. Shown in dashboard, broadcast, and daily report. |
| **Tree-Format AI Narrative** | 5-layer narrative (D/H4/H1/M15/M5) with `R/V/F/RSI` per layer and emoji score icons (🟢🔴🟡🟠⚪). Replaces flat table rows. Injected into War Room Telegram. |

---

## 2. 17 Subsystem Architecture

```
[1]  Fractal 4-Layer Consensus        Sovereign/Anchor/Filter/Exec TF state machine
[2]  Composite 5-TF Scoring Engine    +15 to -15 total score across D/H4/H1/M15/M5
[3]  Glass Box Alert Architecture     Structured reasoning narrative per alert event
[4]  Trade Progression Engine         TP1 (25%/1:1) → TP2 (50%/1.5:1) → TP3 (75%/2:1) → Holder
[5]  SL Autopsy Engine                Contextual transparent loss narrative (4 pattern classes)
[6]  Signal Rejection Reports         Regime filter explainer — why a signal was blocked
[7]  SMC Engine                       BOS/CHoCH/OB/FVG/EQH-EQL/Premium-Discount/Liquidity
[8]  Adaptive VWAP + Vol Profile + Fib  Swing-anchored VWAP · POC/VAH/VAL · ATR Fib bands
[9]  Platinum Risk Model              Auto SL/TP + real-world asset-routed position sizing
[10] Dual Telegram Broadcast          Premium War Room (full Glass Box) + Public (sanitized)
[11] Super Admin Control Panel        Bias/Silence/Override/Asset Note operator controls
[12] Trade ID Engine                  ATM-YYYYMMDD-HHMM-DIR-N format per signal
[13] Pip Tracker                      Actual vs expected pips, daily reset, profit factor
[14] Performance Table                5-column dual table — ELITE/STRONG/ratings live
[15] Daily Report Engine              Full trade log + ML data block at configurable UTC hour
[16] Live Dollar P&L Tracker   [NEW]  Quote-currency P&L per bar, fully asset-routed
[17] PDH/PDL Context Engine    [NEW]  Prev-day high/low + tree-format AI narrative
```

---

## 3. Installation & TradingView Setup

### Add to TradingView

1. Open Pine Editor (bottom of any chart).
2. Paste the full ADSA v7.0 source code.
3. Click **Add to chart**. The strategy deploys on the active ticker/timeframe.
4. The **recommended execution timeframe is M5** (5-minute bars). The fractal protocol reads higher TFs automatically via `request.security`.

### Minimum chart requirements

| Setting | Recommended |
|---|---|
| Timeframe | M5 (execution layer) |
| Bars back | 5,000+ |
| Max labels | 500 |
| Max lines | 500 |
| Max boxes | 500 |

### Alert setup (required for Telegram + broker bots)

1. Right-click chart → **Add Alert**.
2. **Condition**: `Absolute Dollar Agent` — `Any alert() function call`.
3. **Message**: `{{alert_message}}` (verbatim — do not change).
4. **Webhook URL**: Your Telegram bot endpoint `https://api.telegram.org/botTOKEN/sendMessage`, or your broker signal URL.
5. Set frequency to **Once Per Bar Close**.

---

## 4. Input Panel Reference

### 🔐 Super Admin Control Panel

| Input | Default | Purpose |
|---|---|---|
| Sovereign TF | `D` | Macro veto layer — daily trend acts as the 4th-layer gate |
| Manual Bias Override | `AUTO` | `SILENCE` suppresses all alerts · `FORCE BULL/BEAR` overrides regime |
| Asset Context | _(empty)_ | Free-text watchlist note appended to every Telegram alert |
| Operator Commentary | _(empty)_ | Personal analysis appended to War Room alerts only |
| Sanitize Public Channel | `ON` | Public gets signal type + bias only — no levels, no risk params |

### 📱 Telegram Broadcast

| Input | Purpose |
|---|---|
| Premium / War Room Chat ID | Full Glass Box: trade params, autopsy, commentary, tree narrative |
| Public / Free Chat ID | Sanitised signal — direction, session, bias, PDH/PDL |

### 🧠 Fractal 4-Layer Protocol

| Input | Default | Role |
|---|---|---|
| Anchor TF (Layer 2) | `60` (1H) | Commander — directional bias above exec |
| Filter TF (Layer 3) | `15` (M15) | Navigator — intermediate regime gate |
| _(exec = chart TF)_ | M5 | Layer 4 — where the trail fires |
| _(sovereign = Admin panel)_ | Daily | Layer 1 — macro veto |

### 🤖 ATM Bot Settings

| Input | Default | Notes |
|---|---|---|
| Buy/Sell Sensitivity | `3.5` | ATR multiplier for the trailing stop |
| Buy/Sell ATR Period | `2` | Short period — reactive to recent volatility |
| Enable Regime Filter | `ON` | Blocks signals that don't match RSI momentum state |
| Require VWAP Confirmation | `OFF` | Adds VWAP direction as additional gate |

### 💰 Risk Management

| Input | Default | Notes |
|---|---|---|
| Risk Per Trade ($) | `$15` | Dollar amount risked — drives variable position sizing |
| SL Buffer (ATR Multiplier) | `1.5` | Buffer beyond swing low/high for stop placement |
| Show Min-Unit Actual Risk | `ON` | Shows estimated $ risk at minimum lot size alongside variable sizing |
| Strict One-Trade Rule | `OFF` | Blocks opposing signals while a trade is open |
| Holder Mode Trail | `Structural` | `VWAP` or `Structural` (pivot-based) trail for the runner |

---

## 5. Signal Hierarchy — 4-Layer Fractal Protocol

ADSA uses a four-layer decision stack. Every layer must read the same direction for a `MASTER SYNC` signal. A subset produces `LOCAL` or `COUNTER-TREND` signals, each with different risk handling.

```
LAYER 1  Sovereign TF (Daily)    ← Macro veto. Bearish daily = longs flagged counter-trend.
   │
LAYER 2  Anchor TF (1H default)  ← Commander. Confirms medium-term directional bias.
   │
LAYER 3  Filter TF (M15 default) ← Navigator. Intermediate regime gate.
   │
LAYER 4  Exec TF (M5 default)    ← ATM trail flip fires here. This is the entry bar.
```

### Signal types and labels

| Label | Meaning | Risk Handling |
|---|---|---|
| 🔥 `MASTER SYNC LONG/SHORT` (diamond) | All 4 layers aligned | Full size, full TP ladder, holder mode eligible |
| 🟢 `Buy` / 🔴 `Sell` (small label) | Exec TF signal, regime filtered | Standard risk, TP ladder |
| ⚠️ `CT-L` / `CT-S` (triangle, gold) | Counter-trend vs sovereign | Recommend TP1-only, reduced size |
| ✕ Grey cross | Signal fired but regime gate rejected | No trade — logged as rejection |

### Composite score and bias

The system scores five timeframe layers (D/H4/H1/M15/M5), each contributing up to ±3 points (`Regime` + `VWAP` + `Fib`). Maximum score: **±15**.

| Score range | Bias label |
|---|---|
| ≥ +10, ATR High | 🔥 SOVEREIGN HIGH MOMENTUM BULLISH |
| ≥ +6 | 📈 BULLISH BIAS (Strong) |
| +3 to +5 | 📈 BULLISH BIAS (Moderate) |
| +1 to +2 | ⏳ QUIET BULL — WAIT |
| 0 | ⚪ NEUTRAL — STAND ASIDE |
| -1 to -2 | ⏳ QUIET BEAR — WAIT |
| -3 to -5 | 📉 BEARISH BIAS (Moderate) |
| ≤ -6 | 📉 BEARISH BIAS (Strong) |
| ≤ -10, ATR High | 🔥 SOVEREIGN HIGH MOMENTUM BEARISH |

---

## 6. Risk Model & Position Sizing

### How the stop is calculated

For a **long signal**:
```
SL = max(21 EMA, 5-bar swing low) - (ATR(14) × SL_Buffer)
     ← fallback if SL ≥ entry: close - ATR(14) × 1.5
```

For a **short signal**:
```
SL = min(21 EMA, 5-bar swing high) + (ATR(14) × SL_Buffer)
     ← fallback if SL ≤ entry: close + ATR(14) × 1.5
```

### Take-profit ladder

| Level | Distance | Size closed | Action |
|---|---|---|---|
| TP1 | 1.0 × risk | 25–33% | Tighten SL toward entry |
| TP2 | 1.5 × risk | 50% of remaining | Move SL to breakeven |
| TP3 | 2.0 × risk | 75% of remaining | Arm holder mode |
| Holder | Trail | 25% runner | Trail via VWAP or structural pivot until exit |

### Variable position sizing

```
position_size = risk_per_trade / (sl_distance × contract_notional)
```

Contract notional is asset-routed:

| Asset class | Notional per unit |
|---|---|
| Forex | 100,000 (1 standard lot = $100,000 notional) |
| Crypto | 1.0 (1 coin) |
| Futures | `syminfo.pointvalue` |
| Other | `syminfo.pointvalue` |

### Live P&L formula (new in v7.0)

```
P&L = price_diff × position_size × contract_notional
```

Displayed as `+$XX.XX (+Y.Y pips)` in the dashboard Trade Setup panel, updated every bar while the trade is open.

---

## 7. Trade Lifecycle — Entry to Exit

```
ATM trail flip detected (M5 bar close)
        │
        ▼
Regime filter check (RSI momentum state + optional VWAP)
        │
   PASS ──────────────────────── FAIL ──► Grey × plotted, rejection Glass Box sent
        │
        ▼
4-Layer consensus evaluated
        │
   SYNC4 / LOCAL / COUNTER-TREND tag assigned
        │
        ▼
Risk model computes: SL · TP1 · TP2 · TP3 · position_size · Trade ID
        │
        ▼
Entry locks (locked_entry, locked_sl, locked_tp1/2/3, locked_position_size)
        │
        ▼
Glass Box alert fires → War Room + Public Telegram + Broker webhook
        │
        ▼
Trade Progression Engine monitors each bar:
    ├── high/low vs TP1 → TP1 hit → 33% close signal, phase = TP1_HIT
    ├── high/low vs TP2 → TP2 hit → 50% close signal, phase = TP2_HIT
    ├── high/low vs TP3 → TP3 hit → 75% close signal, holder mode armed
    ├── holder mode: trail via VWAP or structural pivot
    │       └── price crosses trail → holder exit alert, trade closed
    └── high/low vs SL  → SL hit → full close signal, SL Autopsy fired
```

---

## 8. Dashboard & Performance Table

### Main dashboard panel

The dashboard (`Top-Right` by default, configurable) shows the full system state at a glance:

| Section | Key data |
|---|---|
| **4-Layer Sync** | Per-layer state (BULL/BEAR/NEUT) and current sync phase |
| **Core Signals** | Price, session, ATR regime, PDH/PDL status, VWAP/Fib/RSI/MACD states |
| **MTF EMA Grid** | 1m/5m/15m/30m/1H/4H/1D/1W/1M trend direction |
| **5-Layer AI Narrative** | Tree-format with emoji scores per TF layer + synthesis line |
| **Agent Advice** | One-line composite read: alignment strength, sovereign context, ATR, liquidity, PDH/PDL |
| **Liquidity** | Current liq bias (sweeping/near/neutral), buy-side and sell-side pool levels |
| **Trade Setup** | Live phase, Trade ID, direction, live P&L, entry/SL/TP1/TP2/TP3, peak pips |
| **Today** | Signal count, blocked count, session breakdown, TP/SL tally, WR, PF, net pips |
| **Session** | Live assessment narrative, counter-trend and sync4 summaries, score momentum |
| **Episode Log** | All signals today: direction, type, score, outcome |

### Performance table (bottom-left)

5 columns × 10 rows showing:
- TP1/TP2/TP3/SL: actual pips vs target pips, hit count
- Profit Factor with `ELITE ✅ / STRONG ✅ / GOOD / MARGINAL ⚠️ / NEGATIVE ❌` tag
- Win rate
- Net pips today
- Session assessment narrative

---

## 9. Telegram Dual-Channel Broadcast

### War Room (Premium channel)

Full Glass Box report per event. Always includes:
- Event title + ticker + timestamp
- Commentary block (event-specific reasoning)
- Trade parameters for entries (entry/SL/TP1/TP2/TP3/size/ID)
- Liquidity context, score momentum, chain synthesis
- Operator commentary and asset note (if set)
- PDH/PDL status

### Public channel

Sanitized by default (configurable). Public users see:
- Signal direction and type tag
- Session and score
- PDH/PDL line
- "Full Glass Box in War Room" footer

### Event types that trigger a broadcast

| Event | War Room | Public |
|---|---|---|
| Long / Short entry | Full params + Glass Box | Direction, score, alignment tag |
| TP1 / TP2 / TP3 hit | Pip result + next target | Milestone confirmation |
| SL hit | Pip loss + full SL Autopsy | "Loss absorbed" |
| Holder mode exit | Trail level + peak run | "Trade concluded" |
| Regime rejection | Which gate failed + what's needed | "Blocked" |
| Liq sweep (buy/sell) | Pool level + score lean + advice | "Liq swept · monitoring" |
| Structure shift (BOS/CHoCH) | Structure tag + context | "Context update" |
| Session open | Session name + PDH/PDL + score + agenda | Session tag + score |
| Admin silence | Reason (ATR low / weak score / manual) | "Standing aside" |

### Telegram bot webhook setup

```
Bot URL format:
https://api.telegram.org/bot{YOUR_BOT_TOKEN}/sendMessage

TradingView Alert:
  Condition  : Absolute Dollar Agent → Any alert() function call
  Message    : {{alert_message}}
  Webhook URL: [paste your bot URL above]
  Frequency  : Once Per Bar Close
```

---

## 10. Bitget Signal Bot Integration

Enable `🤖 Bitget Webhook` in settings. Create a second TradingView alert with your Bitget signal bot URL as the webhook.

The alert fires JSON on every buy or sell signal confirmed:

```json
{
  "action": "buy",
  "size": "0.0150",
  "symbol": "BTCUSDT",
  "price": "67432.50",
  "sl": "67100.00",
  "tp1": "67764.50",
  "id": "ATM-20260615-1023-BUY-1",
  "score": "8.0",
  "sync": "🔥 FULLY ALIGNED: BULLISH (4-LAYER)"
}
```

---

## 11. TradeSgnl / MT5 Automation

ADSA v7.0 uses `strategy.entry()` / `strategy.close()` with custom `alert_message` parameters formatted for TradeSgnl's MT5 Expert Advisor.

### Default message format

**Long entry:**
```
LICENSE_ID,EURUSD,buy,vol_dollar=15,sl_price=1.08234,tp1_price=1.08567,pct1=0.33,tp2_price=1.08734,pct2=0.50,tp3_price=1.08901,exent=1
```

**Long exit (SL or trail):**
```
LICENSE_ID,EURUSD,closebuy
```

### Customising messages

All message templates are configurable in **TradeSgnl Alert Messages**. Leave TP1/TP2/TP3 messages empty — TradeSgnl handles partial closures natively via `pct1`/`pct2`/`exent` on the entry message.

### Available template variables

| Variable | Resolves to |
|---|---|
| `{{vol}}` | Position size (lots/coins/contracts) |
| `{{risk}}` | Dollar risk amount |
| `{{sl}}` | Stop loss price |
| `{{tp1}}` | Take profit 1 price |
| `{{tp2}}` | Take profit 2 price |
| `{{tp3}}` | Take profit 3 price |

---

## 12. Daily Report Engine

Fires once per day at the configured UTC hour (default 21:00 UTC). Produces a full session debrief:

### War Room report sections

1. **Signal summary** — total, blocked, long/short breakdown, sync4/local/counter-trend split
2. **Outcomes** — TP1/TP2/TP3/SL/Open counts, win rate, profit factor, net pips
3. **Metrics** — average score at entry, average peak pips, ATR state, sovereign, sessions
4. **Trade log** — every signal: direction, type, score, outcome, peak pips, bar duration
5. **Agent self-assessment** — automated session quality narrative with pattern notes
6. **ML data block** — structured key-value block for offline training ingestion

### ML data block format

```
[ATM_DATA_ADSA]
date=2026.06.15
asset=XAUUSD
tf=5
signals=4
rejected=1
long=3
short=1
sync4=2
local=1
counter=1
tp1=2
tp2=1
tp3=1
sl=0
win_rate=100.0
avg_score=8.25
avg_pips=12.4
best_pips=18.7
pf=999.00
net_pips=44.1
london=1
ny=3
asia=0
atr_state=High
sovereign=BULL
total_score=9.0
[/ATM_DATA_ADSA]
```

---

## 13. Intraday Trading Strategy

This section defines a complete operational playbook for using ADSA v7.0 intraday. It is written for the **London and New York sessions** where the signal edge is highest, and uses the system's own tools to filter, time, and size every trade.

---

### 13.1 Session Framework

ADSA detects three sessions automatically. Prioritise them in this order:

| Session | UTC | Nairobi (GMT+3) | Edge level | Primary markets |
|---|---|---|---|---|
| **London** | 07:00–16:00 | 10:00–19:00 | High | XAUUSD, EURUSD, indices |
| **London-NY overlap** | 13:00–16:00 | 16:00–19:00 | **Highest** | All majors + XAUUSD |
| **New York** | 13:00–22:00 | 16:00–01:00 | High | XAUUSD, US indices, crypto |
| **Tokyo/Asia** | 22:00–07:00 | 01:00–10:00 | Low | Reduce size 50%, SYNC4 only |

**Rule:** Trade full size only in London and NY sessions. In Asia, only take SYNC4 (4-layer aligned) signals and halve the risk per trade.

---

### 13.2 Pre-Session Routine (run before the session opens)

**1. Check the sovereign layer (Daily)**
- Open a Daily chart of your instrument.
- Is `posState` bullish (+1), bearish (-1), or flat (0)?
- A bearish daily = all long setups are counter-trend. Trade counter-trend longs at TP1-only.

**2. Note PDH/PDL**
- The dashboard shows: `📅 Daily Context: 🔼 Above PDH (1.0980)` or `↔ Inside Range`.
- Price above PDH = **bullish breakout context** — look for pullback longs.
- Price below PDL = **bearish breakdown context** — look for bounce shorts.
- Price inside range = **mean reversion likely** — fade extremes, trail TP1 only.

**3. Check the composite score**
- Score ≥ +6: session opens bullish — bias longs first.
- Score ≤ -6: session opens bearish — bias shorts first.
- Score −3 to +3: mixed — wait for first SYNC4 signal before committing.

**4. Mark the liquidity levels**
- Dashboard shows `Buy-side: X.XXXXX` and `Sell-side: X.XXXXX`.
- These are the liq sweep targets. Price often rallies through buy-side to trigger stops before reversing. Know where they are before the session.

**5. Check ATR regime**
- `ATR HIGH`: normal risk, full TP ladder, holder mode eligible.
- `ATR LOW`: chop risk is elevated — trail TP1 early, do not use holder mode.
- `ATR MED`: standard playbook.

---

### 13.3 Signal Qualification Checklist

Before acting on any signal, run through this checklist:

```
□ 1. Is the session active? (London or NY — not Asia unless SYNC4)
□ 2. Is the score ≥ +3 for longs / ≤ -3 for shorts?
□ 3. Does the ATR regime allow full exposure? (not ATR LOW for holder mode)
□ 4. Is the signal direction consistent with PDH/PDL context?
□ 5. Is the signal type SYNC4 or LOCAL? (counter-trend = TP1 only, half size)
□ 6. Is the sovereign layer (Daily) aligned or neutral? (opposing = counter-trend)
□ 7. Is a liquidity pool nearby? (liq sweeps can stop-out valid trades)
□ 8. Has the liq bias swept? (a sweep followed by an exec flip = high-confidence)
```

A signal that passes all 8 checks = full risk, full TP ladder.
A signal that passes 5–7 = standard risk, TP1+TP2 only, skip holder mode.
A signal that passes < 5 = pass or halve risk.

---

### 13.4 Entry Execution

ADSA entry signals appear when the ATM ATR trailing stop flips direction and the regime filter passes. The entry is the **close of the signal bar** — never chase an entry mid-bar.

**Long entry flow:**
1. M5 bar closes above the ATR buy trail.
2. RSI > 55 (positive momentum state confirmed).
3. (Optional) VWAP is trending bullish (lastSwing = +1).
4. Score ≥ +3.
5. Dashboard shows 🟢 signal + `ENTRY ACTIVE` phase.
6. Enter at market on bar close, or on the next bar's open if using pending orders.

**Short entry flow:**
1. M5 bar closes below the ATR sell trail.
2. RSI < 50 (negative momentum state confirmed).
3. Score ≤ -3.
4. Dashboard shows 🔴 signal + `ENTRY ACTIVE` phase.
5. Enter at market on bar close.

**Never:**
- Enter mid-bar (risk parameters are computed on bar close).
- Take a second signal in the same direction while the first trade is open (the system handles this via the one-trade rule — trust it).
- Override the SL with a tighter stop. The risk model places it correctly.

---

### 13.5 Trade Management by Phase

#### Phase: ENTRY ACTIVE → TP1
- Do not move the stop yet.
- Monitor `Live P&L` in the dashboard. A deep negative P&L at entry = the trade is already under pressure.
- If price returns to entry before TP1 and the exec trail reverses, the system will fire an exit signal. Follow it.

#### Phase: TP1 HIT 🎯
- TP1 alert fires (Telegram + broker bot executes 33% close).
- Manually tighten the stop to entry (breakeven) if using manual execution.
- The risk on the remaining 67% is now zero — stay in.
- Next target: TP2 at 1.5:1.

#### Phase: TP2 HIT 🎯🎯
- 50% of the remaining position closed.
- SL moves to entry (breakeven) — position is risk-free.
- Runner: 25% of original size still open.
- Next target: TP3 at 2:1, then holder mode.

#### Phase: TP3 HIT 🚀
- 75% close at 2:1. Holder mode arms for the remaining 25%.
- Trail is now active: VWAP or structural pivot (configured in `Holder Mode Trail`).
- Only exit when the trail cross fires — don't manually close a running winner.

#### Phase: HOLDER MODE 🔱
- Structural trail: follows 5-bar pivot lows (long) or highs (short).
- VWAP trail: closes when price crosses the adaptive VWAP.
- This phase can hold through multiple sessions if trend is strong.
- The `Peak` pips display shows the max the trade has achieved — a useful reference for whether holder mode is extending or deteriorating.

#### Phase: SL HIT 💀
- Accept the SL and review the autopsy.
- The Glass Box broadcast will contain an SL autopsy narrative explaining whether this was a counter-trend drag, a liq sweep, ATR low chop, or weak alignment.
- Do not immediately re-enter. Check if score or regime has changed before the next signal.

---

### 13.6 Counter-Trend Trade Rules

A counter-trend signal appears when the exec TF fires a signal that opposes the sovereign (daily) layer. These appear with gold triangles (`CT-L` / `CT-S`) on the chart.

**Required rules for counter-trend trades:**
1. **Half position size** — halve `Risk Per Trade` manually or simply target TP1 only.
2. **TP1-only exit** — close the full position at TP1. Do not carry to TP2.
3. **No holder mode** — arm nothing when TP1 hits. Close and walk away.
4. **Score threshold** — only take CT signals if score magnitude is ≥ 5 (i.e., the local TFs are strong even if the daily opposes).
5. **Avoid during high-impact news** — CT trades against the daily trend are the first casualty of a news spike.

---

### 13.7 Liquidity-Based Setups

ADSA v7.0 broadcasts a `⚡ BUY-SIDE LIQ SWEPT` or `⚡ SELL-SIDE LIQ SWEPT` alert when price crosses a swing liquidity pool.

**How to use sweeps as a setup catalyst:**

A liquidity sweep followed by an M5 exec trail flip in the **opposite** direction is the highest-quality setup the system produces:

```
1. Price sweeps buy-side liq (runs stops above a swing high)
   → Alert: ⚡ BUY-SIDE LIQ SWEPT
2. Price fails to sustain above the pool (no follow-through)
3. M5 ATR trail flips SHORT
   → Alert: 🔴 SHORT (or 🥶 MASTER SYNC SHORT if score aligns)
4. Enter short. SL above the sweep high.
5. First target: sell-side liq pool (shown as Sell-side: X.XX in dashboard)
```

**Key context:** the Glass Box alert for a sweep includes a score lean note — "Bullish score lean → false-break probability elevated." Use this to calibrate conviction.

---

### 13.8 Volume Profile Integration

ADSA displays the live session Volume Profile (POC/VAH/VAL) when `Enable Volume Profile` is on.

**Intraday rule set:**
- **POC as a magnet**: if price is trending toward the POC, it often stalls or reverses at it.
- **VAH/VAL as range boundaries**: short near VAH when bearish; long near VAL when bullish.
- **POC as support/resistance**: a bullish exec flip above the POC = confirm long. A bearish flip below POC = confirm short.
- The session broadcast includes `POC X.XXXXX · VAH X.XXXXX · VAL X.XXXXX` — note these at session open.

---

### 13.9 ATR Regime-Specific Rules

| ATR State | Adjustment |
|---|---|
| **ATR HIGH** | Standard playbook. Full TP ladder. Holder mode on for SYNC4. |
| **ATR MED** | Standard playbook. Evaluate holder mode case by case. |
| **ATR LOW** | Reduce expectation. Trail TP1 at the first sign of reversal. Skip holder mode. Widen SL buffer (raise `SL Buffer` to 2.0). Consider waiting for ATR to expand before entering. |

The SL autopsy will flag ATR LOW as a contributing factor if a stop is hit during compressed volatility — review the context note to see if the setup was structurally valid despite the loss.

---

### 13.10 Daily Risk Rules

These are the hard rules that the system does not enforce automatically in v7.0 — the operator must apply them:

| Rule | Threshold |
|---|---|
| Maximum daily loss | Stop trading at 2× the risk per trade (i.e., 2 SL hits) |
| Maximum daily signals | If you have taken 5+ signals, assess session quality before the next |
| Counter-trend cap | No more than 2 CT signals per session |
| News avoidance | Do not enter 5 minutes before or after high-impact news |
| Minimum score | Never take a LOCAL signal with score between -2 and +2 |

---

### 13.11 Weekly Review Checklist (using the ML data block)

Each day at `report_hour_utc` (default 21:00 UTC) the daily report fires. Copy the `[ATM_DATA_ADSA]` block into a spreadsheet. Weekly, review:

1. **Avg score at entry** — is it trending up (better entries) or down (chasing)?
2. **Win rate by signal type** — are SYNC4 trades outperforming LOCAL? (they should)
3. **Win rate by session** — which session is producing edge?
4. **Counter-trend SL rate** — if CT signals are hitting stops more than 50% of the time, reduce CT risk further
5. **ATR state at SL hits** — if most losses happen in ATR LOW, consider disabling trading when `ATR LOW` is active
6. **Best pips vs net pips gap** — a large gap means profits are being left on the table in holder mode or runner management needs adjustment

---

## 14. Glass Box Alert Reference

The Glass Box is the structured reasoning narrative attached to every alert. It replaces generic "signal fired" messages with transparent, operator-readable explanations.

### Anatomy of a buy/sell Glass Box

```
🔥 MASTER SYNC LONG · XAUUSD 5 · 10:23 UTC
──────────────────────────
Signal #2 today · Prior: 1.L[S4]+9.0→TP2

Exec trail ↑ at 2348.40 · ATR trail: 12.4 pips · ATR HIGH (14.2p) · volatile
D↑ 60m↑ 15m↑ 5m↑ · 4/4 layers · Score +9.0/15 · LDN · 🔼 Above PDH (2341.00)
D trail BULL · Sovereign confirmed.
Strong alignment (9.0/15) · with D trail · ATR HIGH (14.2p) · Buy-liq 2352.00 above · 🔼 Above PDH

──────────────────────────
Entry  2348.40    SL 2341.20 (72 pips · $15.00)
TP1    2355.60 (+72 pips · 1:1)
TP2    2359.20 (+108 pips · 1.5:1)
TP3    2362.80 (+144 pips · 2:1)
Size   0.0208 Lots · ID ATM-20260615-1023-BUY-2

──────────────────────────
POC 2345.20 · Buy-liq 2352.00 · Sell-liq 2339.80
Score ↑ from +6.0 at LDN open (now +9.0 — bias strengthening)
→ Full 4-layer alignment long. Trail consensus across all TFs.
```

### SL Autopsy Glass Box (4 pattern classes)

| Pattern | Trigger condition | Narrative theme |
|---|---|---|
| **Counter-trend drag** | Sovereign opposing at entry | "COUNTER-TREND: D trail was BEARISH. Local exec confirmed — macro structure reasserted before target." |
| **Liq zone sweep** | Price swept liq pool at/near SL | "LIQ ZONE SWEEP: Stop was at/near the buy-side pool. SL buffer did not clear the sweep depth." |
| **ATR LOW chop** | ATR below 80% of 20-bar SMA | "LOW ATR: Volatility was compressed. Small noise moves can clip stops. Widen buffer or reduce size." |
| **Weak alignment** | Score < 4 at entry | "WEAK ALIGNMENT: ~N/5 TF layers agreed. Partial alignment entries carry higher invalidation risk." |
| **No dominant pattern** | None of the above | "NO DOMINANT PATTERN: Trade structure was valid. Logged for pattern accumulation." |

---

## 15. SMC Engine Reference

### Structure (BOS / CHoCH)

| Label | Meaning |
|---|---|
| **BOS** (Break of Structure) | Swing high/low broken in the direction of the existing trend — trend continuation |
| **CHoCH** (Change of Character) | Swing high/low broken against the trend — potential reversal |
| Internal (dashed) | 5-bar internal structure — faster, leading signal |
| Swing (solid) | 50-bar swing structure — slower, higher conviction |

### Order Blocks (OB)

Displayed as shaded boxes extending to the right. Represent the last bearish candle before a bullish BOS (bullish OB) or last bullish candle before a bearish BOS (bearish OB). Price retesting an OB is a high-probability entry zone when aligned with the exec trail signal.

### Equal Highs/Lows (EQH/EQL)

Dotted line connecting two nearly equal pivot highs or lows. These are liquidity targets — the pool above EQH or below EQL will be swept before the next structural move.

### Fair Value Gaps (FVG)

Three-bar gaps where the middle candle creates a gap in price. Price frequently returns to fill FVGs before continuing. Bullish FVG = support. Bearish FVG = resistance.

### Premium / Discount Zones

Drawn from the last significant swing. The top 5% = Premium (expensive to buy). The bottom 5% = Discount (cheap to buy). Equilibrium at 50%. Rule: buy in Discount when bullish, sell in Premium when bearish.

---

## 16. Asset Router — Supported Markets

ADSA v7.0 routes all risk and sizing calculations through a contract notional router that handles four asset classes:

| Market | Examples | Contract notional | Min unit |
|---|---|---|---|
| Forex | EURUSD, XAUUSD, GBPJPY | 100,000 | 0.01 lot |
| Crypto | BTCUSDT, ETHUSDT | 1.0 coin | 0.01 coin |
| Futures | ES1!, NQ1!, CL1! | `syminfo.pointvalue` | 1 contract |
| Other/CFD | Indices, stocks | `syminfo.pointvalue` | 1 unit |

The **bug fixed in v6.1** (inherited by v7.0): `_risk_at_min_lot()` previously used forex math universally, producing 10,000× leverage errors on crypto and futures. All sizing now routes through `_get_contract_notional()` as the single source of truth.

---

## 17. Changelog v7.0 vs v6.1

### New in v7.0

**[1] Live Dollar P&L Tracker (Section 3 utility + Section 23 dashboard)**
- `_live_pnl(entry, current_price, direction, pos_size)` computes unrealised P&L per bar
- `_pnl_str()` formats as `+$XX.XX` / `-$XX.XX`
- Dashboard Trade Setup shows: `💵 Live P&L: +$12.34 (+8.7 pips)`
- Fully asset-routed — identical formula for forex, crypto, futures

**[2] PDH/PDL Context Engine (Section 15.5)**
- `request.security("D", [high[1], low[1]])` — `lookahead_off`, no repaint
- `pdh_pdl_status` string resolves to one of three states per bar
- Injected into: dashboard Core Signals panel, session open broadcast, entry broadcast, daily report

**[3] Tree-Format AI Narrative (Section 20 + Section 23)**
- 5 rows (D/H4/H1/M15/M5), each showing `R:X V:X F:X RSI:X  ±score`
- Score icon: 🟢 ≥ 2.5 · 🔴 ≤ -2.5 · 🟡 mild bull · 🟠 mild bear · ⚪ flat
- Synthesis line: chain alignment summary + verdict sentence
- Replaces flat `R= V= F=` format in dashboard and Telegram

### Inherited fixes from v6.1 (both carry forward)
- **Risk router asset bug**: `_risk_at_min_lot()` now uses `_get_contract_notional()` universally
- **Sizing precision**: `math.round(..., 4)` on all position size calculations

---

## Legal

ADSA v7.0 is provided for educational and research purposes only. It is not financial advice. Trading involves substantial risk of loss and is not suitable for all investors. Past performance displayed by any strategy or indicator does not guarantee future results. Always trade with capital you can afford to lose and consult a licensed financial adviser before trading.

© 2026 Absolute Dollar Intelligence | All Rights Reserved | Invite Only
