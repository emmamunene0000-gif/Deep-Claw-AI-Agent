# ABSOLUTE DOLLAR SUPREME AGENT — ADSA v7.1
### Augmented Intelligence Protocol | Pine Script v6
**© 2026 Absolute Dollar Intelligence | Invite-Only | Not Financial Advice**

---

## Table of Contents
1. [What This Is](#1-what-this-is)
2. [Architecture — 19 Subsystems](#2-architecture--19-subsystems)
3. [Requirements](#3-requirements)
4. [Installation](#4-installation)
5. [Full Settings Guide](#5-full-settings-guide)
6. [v7.1 New Features In Detail](#6-v71-new-features-in-detail)
7. [Alert & Telegram Setup](#7-alert--telegram-setup)
8. [TradeSgnl / Bitget Automation](#8-tradesgnl--bitget-automation)
9. [M1 & M5 Intraday Framework](#9-m1--m5-intraday-framework)
10. [Is This Approach Profitable?](#10-is-this-approach-profitable)
11. [Glossary](#11-glossary)

---

## 1. What This Is

ADSA v7.1 is a **complete multi-timeframe trading system** built in Pine Script v6 for TradingView. It is not a simple indicator — it is an agent that:

- **Reads the market** across 5 timeframes simultaneously using a composite scoring engine (+15 to −15)
- **Gates signals** through a 4-layer fractal consensus, a regime filter, a Fibonacci trend filter, and a structural liquidity filter
- **Sizes positions** automatically using a dollar-risk model routed through the correct asset-class math (forex lots, crypto coins, futures contracts)
- **Manages trades** through a structured 3-TP progression with an optional runner in Holder Mode
- **Broadcasts reasoning** to Telegram (War Room full Glass Box + Public sanitized) with transparent per-event commentary
- **Logs performance** daily with a reset pip tracker, profit factor display, and a machine-readable ML data block

Everything it does is visible. Every blocked signal has a reason. Every stop loss has an autopsy. That transparency is the architecture's core design principle.

---

## 2. Architecture — 19 Subsystems

| # | Subsystem | What It Does |
|---|-----------|--------------|
| 1 | **Fractal 4-Layer Consensus** | Sovereign/Anchor/Filter/Exec alignment check. Fully aligned = `🔥 MASTER SYNC` signal |
| 2 | **5-TF Composite Scoring** | D/H4/H1/M15/M5 each scored on 3 factors (Regime, VWAP, Fib Trend). Range: +15 to −15 |
| 3 | **Glass Box Alerts** | Rich per-event reasoning string dispatched to TradingView alerts |
| 4 | **Trade Progression Engine** | TP1→TP2→TP3→Holder Mode with partial closes at each level |
| 5 | **SL Autopsy Engine** | On stop hit: contextual narrative explaining WHY (liquidity trap, low ATR, sovereign veto, etc.) |
| 6 | **Signal Rejection Reports** | Blocked signal = alert with the reason (regime, fib, liq) clearly stated |
| 7 | **SMC Engine** | BOS, CHoCH, Order Blocks, FVGs, EQH/EQL, Premium/Discount zones, Liquidity sweeps |
| 8 | **Adaptive VWAP + VP + Fib Bands** | Swing-anchored VWAP, session Volume Profile with POC/VAH/VAL, Fibonacci extension bands |
| 9 | **Platinum Risk Model** | ATR-based SL, 1:1/1.5:1/2:1 TPs, position sizing via `risk_per_trade / (sl_dist × notional)` |
| 10 | **Dual Telegram Broadcast** | War Room (full Glass Box) + Public (sanitized direction + bias only) |
| 11 | **Super Admin Control Panel** | Manual bias override, silence mode, asset context note, operator commentary |
| 12 | **Trade ID Engine** | `ATM-YYYYMMDD-HHMM-DIR-N` format for every trade |
| 13 | **Pip Tracker** | Daily-reset actual vs expected pip comparison. TP1/TP2/TP3/SL separately tracked |
| 14 | **Performance Table** | 5-column × 10-row live table: TP hits, SL hits, PF, Win Rate |
| 15 | **Daily Report Engine** | Full trade log + ML data block dispatched to Telegram at configurable UTC hour |
| 16 | **Live Dollar P&L Tracker** | Per-bar unrealised P&L in quote currency, fully asset-routed |
| 17 | **PDH/PDL Context Engine** | Previous Day High/Low with status: Above PDH / Below PDL / Inside Range |
| 18 | **MTF Liquidity Trail** *(v7.1 NEW)* | Pivot-based holder trail from a higher TF + optional ATM signal gate |
| 19 | **Fibonacci Trend Gate** *(v7.1 NEW)* | Double-EMA Fib trend gates ATM signals against counter-trend entries |

---

## 3. Requirements

- **TradingView account**: Essential plan or higher recommended (Pro/Pro+ for faster data; Premium for more indicators)
- **Pine Script v6**: The script declares `//@version=6` — paste into TradingView Pine Editor
- **Optional**: Telegram Bot token + chat IDs for broadcast
- **Optional**: TradeSgnl or Bitget account for automated execution

---

## 4. Installation

1. Open TradingView → **Pine Editor** (bottom panel)
2. Delete any existing code, paste the entire contents of `ADSA_v7_ChatPaste_MTFLiqFib.pine`
3. Click **Save** → name it "Absolute Dollar Agent v7.1"
4. Click **Add to chart**
5. The strategy will load with default settings — configure using the **Settings** panel

> **Important**: This is a `strategy()` script, not `indicator()`. It will show a Strategy Tester panel. This is intentional — the tester gives you a live backtest of signal quality on the current chart.

---

## 5. Full Settings Guide

### 🔐 Super Admin Control Panel
| Input | Default | Notes |
|-------|---------|-------|
| Sovereign TF | `D` | Macro veto layer — Daily bias governs all signal direction |
| Manual Bias Override | `AUTO` | `SILENCE` suppresses all alerts. `FORCE BULL/BEAR` overrides 4-layer logic |
| Asset Context Note | *(empty)* | Appended to every Telegram alert, e.g. `"GOLD — London breakout watch"` |
| Operator Commentary | *(empty)* | War Room only — your personal analysis note |
| Sanitize Public Channel | `ON` | Public gets direction + bias only, no levels |

### 🧠 Fractal 4-Layer Protocol
| Input | Default | Notes |
|-------|---------|-------|
| Anchor TF (Layer 2) | `60` (H1) | Commander TF — should align with Sovereign |
| Filter TF (Layer 3) | `15` (M15) | Navigator TF — confirms Anchor direction |
| Exec TF (Layer 4) | *Chart TF* | Automatic — whatever chart you are on |

### 🤖 ATM Bot Settings
| Input | Default | Notes |
|-------|---------|-------|
| Buy Sensitivity | `3.5` | ATR multiplier for the buy trail. Higher = wider, fewer signals |
| Buy ATR Period | `2` | ATR lookback for buy trail calculation |
| Sell Sensitivity | `3.5` | ATR multiplier for the sell trail |
| Sell ATR Period | `2` | ATR lookback for sell trail |
| Enable Regime Filter | `ON` | Require RSI momentum confirmation before signal fires |
| Require VWAP Confirmation | `OFF` | Also require Adaptive VWAP swing agreement |
| Activate Glass Box Reports | `ON` | Enable rich per-event alert messages |

### 💰 Risk Management
| Input | Default | Notes |
|-------|---------|-------|
| Risk Per Trade ($) | `15.0` | Dollar amount risked. Controls position size |
| SL Buffer (ATR Multiplier) | `1.5` | Buffer added beyond the structural SL level |
| Show Min-Unit Actual Risk | `ON` | Shows reference risk at minimum 0.01 lot |
| Strict One-Trade Rule | `OFF` | Prevents reversal signals while a trade is active |
| Holder Mode Trail | `Structural` | `VWAP` / `Structural` / `MTF Liquidity` (v7.1) |

### 💧 MTF Liquidity Trail *(v7.1)*
| Input | Default | Notes |
|-------|---------|-------|
| Enable MTF Liquidity Trail | `ON` | Master toggle for both the trail and gate |
| Trail Timeframe | `60` (H1) | TF for pivot high/low. Must be ≥ chart TF |
| Pivot Lookback Length | `14` | Bars each side to confirm a swing |
| Gate ATM Signals to Liq Trail | `ON` | Block entries on the wrong structural side |

### 📊 Fibonacci Trend Gate *(v7.1)*
| Input | Default | Notes |
|-------|---------|-------|
| Require Fibonacci Trend Alignment | `OFF` | When ON, adds third gate layer. Reduces signals but increases quality |

---

## 6. v7.1 New Features In Detail

### MTF Liquidity Trail

**What it solves**: The original Holder Mode trailed using a 5-bar pivot low/high on the current chart TF. On M1/M5 that's extremely tight and will stop you out of a move on normal noise. The MTF trail uses pivot extremes from a higher TF (e.g. H1), which are structurally meaningful levels.

**How it works**:
- Uses `ta.valuewhen(not na(ta.pivothigh(...)))` inside `request.security` — no lookahead, no repainting
- For longs: `mtf_holder_trail` ratchets UP as new higher MTF pivot lows form. It never retreats
- For shorts: it ratchets DOWN as new lower MTF pivot highs form
- Exit fires when `close` crosses through the trail (same as VWAP/Structural modes)

**Holder Mode Trail selection guide**:
- `Structural` — best for swing/position trades where you want tight trailing
- `MTF Liquidity` — best for intraday momentum trades where you want the runner to breathe
- `VWAP` — best for continuation trades within a session trend

### ATM Signal Gating to the Liquidity Trail

This is the primary improvement over v7.0. When `requireLiqGate = ON`:
- **Long signals** only fire when `close > mtf_liq_pivot_low` (price is above the structural demand floor)
- **Short signals** only fire when `close < mtf_liq_pivot_high` (price is below the structural supply ceiling)

This filters out the single most common failure mode: entering a long into a bearish supply zone, or a short into a bullish demand zone. The dashboard shows `✅ OK` or `⛔ BLOCKED` in real time.

### Fibonacci Trend Gate

Off by default — it is a **stricter secondary gate** that enforces trend direction. The double-EMA basis (`EMA(EMA(close, 200), 200)`) is a slow, smooth trend engine that cuts through noise. Enable it when:
- You are trading with-trend only and want to eliminate every counter-trend entry
- You want maximum signal quality over signal frequency

Leave it OFF when:
- You are scalping M1/M5 and need signals in both directions within sessions
- Your sovereign/fractal layers are already filtering aggressively

---

## 7. Alert & Telegram Setup

### TradingView Alert Configuration

1. Right-click on the chart → **Add Alert**
2. **Condition**: `Absolute Dollar Agent` → `alert() function calls only`
3. **Message**: `{{alert_message}}` (exactly this — the script builds the message)
4. **Webhook URL**: your Telegram bot URL: `https://api.telegram.org/botYOUR_TOKEN/sendMessage`
5. **Frequency**: `Once Per Bar Close` (required — the script uses `barstate.isconfirmed`)

### Telegram Bot Setup

1. Open Telegram, message `@BotFather` → `/newbot` → follow prompts → copy the **token**
2. Start the bot, then get your chat ID from `https://api.telegram.org/botYOUR_TOKEN/getUpdates`
3. In script settings:
   - **Chat ID (Premium)** = your War Room group/channel ID
   - **Chat ID (Public)** = your public channel ID (or same as Premium if you use one channel)
4. Toggle ON whichever channels you want active

### What You Receive

**War Room (Premium)** receives every event with:
- Full Glass Box commentary (why the signal fired)
- All trade parameters (Entry, SL, TP1/2/3, size, risk)
- 5-layer AI narrative tree (D/H4/H1/M15/M5 each with Regime/VWAP/Fib/RSI)
- PDH/PDL context
- Operator commentary (if set)
- SL Autopsy on stop hits
- Daily Report at configured UTC hour

**Public Channel** receives (when `Sanitize = ON`):
- Direction + event type only
- Master bias + score
- Session context
- Link to War Room for full report

---

## 8. TradeSgnl / Bitget Automation

### TradeSgnl (MT5 automation)

The script outputs a TradeSgnl-compatible alert message format:

```
LICENSE_ID,EURUSD,buy,vol_dollar=15,sl_price=1.23456,tp1_price=1.24567,pct1=0.33,tp2_price=1.25678,pct2=0.50,tp3_price=1.26789,exent=1
```

To configure:
1. Replace `LICENSE_ID` in both Long/Short Entry Message inputs with your actual TradeSgnl license key
2. Keep TP1/TP2/TP3 message fields **empty** — TradeSgnl handles partial closures natively via `pct1` and `pct2`
3. The exit messages (`LICENSE_ID,{{ticker}},closebuy`) fire on SL hit or Holder Mode trail exit

### Bitget Signal Bot

1. Enable **Bitget Webhook** in settings
2. Create a TradingView alert on the same chart (separate from Telegram alert)
3. Set Webhook URL = your Bitget signal bot endpoint
4. The script outputs JSON: `{"action":"buy","size":"0.01","symbol":"BTCUSDT","price":"...","sl":"...","tp1":"...","id":"...","score":"...","sync":"..."}`

---

## 9. M1 & M5 Intraday Framework

This is the recommended configuration and rules-based playbook for intraday trading on M1 and M5.

### Why M5 is the primary intraday TF (not M1)

The 5-layer scoring engine hardcodes D/H4/H1/M15/M5 as its five layers. **M5 is the execution layer in the scoring tree**. When you run the script on an M5 chart with the default settings, the system is architecturally aligned out of the box. M1 requires one TF adjustment (see below).

### Recommended Settings: M5

| Setting | Recommended | Reason |
|---------|-------------|--------|
| **Chart TF** | 5m | Exec layer in the hardcoded scoring tree |
| **Sovereign TF** | `D` | Keep Daily as macro filter — valid even for scalps |
| **Anchor TF** | `60` (H1) | Default is correct for M5 |
| **Filter TF** | `15` (M15) | Default is correct for M5 |
| **ATM Sensitivity** | `2.5`–`3.0` | Tighter than default 3.5; M5 has more signal opportunities |
| **ATM ATR Period** | `3`–`5` | Slightly longer ATR period smooths M5 noise |
| **SL Buffer** | `1.0`–`1.5` | Default 1.5 is fine; reduce to 1.0 in low-ATR sessions |
| **Liq Trail TF** | `15` (M15) | H1 pivots are too wide for M5 runner; M15 is structurally relevant |
| **VP Session Type** | `London` or `New York` | Session profile more relevant than Daily on intraday |
| **Require VWAP Confirmation** | `ON` | High recommendation for M5 — session VWAP acts as daily directional anchor |
| **Require Fib Trend** | `OFF` | Keep OFF — you need both long and short signals within sessions |
| **Require Liq Gate** | `ON` | Essential for M5 — stops entries into session supply/demand zones |

### Recommended Settings: M1

| Setting | Recommended | Reason |
|---------|-------------|--------|
| **Chart TF** | 1m | Scalp execution |
| **Sovereign TF** | `D` | Daily still valid as macro filter |
| **Anchor TF** | `15` (M15) | Drop one level from M5 setup |
| **Filter TF** | `5` (M5) | Drop one level |
| **ATM Sensitivity** | `2.0`–`2.5` | M1 needs tighter trail for responsiveness |
| **ATM ATR Period** | `2`–`3` | Short ATR captures M1 volatility correctly |
| **Liq Trail TF** | `5` (M5) | M5 pivots are the right structural anchor for M1 runners |
| **Liq Trail Pivot Length** | `8`–`10` | Shorter lookback for more recent M5 swings |
| **VP Session Type** | `London` or `New York` | Session-scoped profiles only on M1 |
| **Holder Mode Trail** | `MTF Liquidity` | M1 structural trail is too tight; M5 liq trail breathes correctly |

### The M5 Trade Playbook

#### Pre-session Checklist (before London or NY open)
1. **Check Sovereign**: Is Daily bullish, bearish, or neutral? This determines direction bias.
2. **Check PDH/PDL**: Is price above PDH (breakout), below PDL (breakdown), or inside range?
   - Inside range = lower probability. Wait for a range break or trade off the extremes.
3. **Check Score**: Is `total_score ≥ 6` (bullish) or `≤ −6` (bearish)?
   - Score 3–5: caution entries only; target TP1 only
   - Score ≥ 6: full R:R trade; run to TP3 allowed
   - Score < 3: stand aside; the 5 TFs are not aligned
4. **Check MTF Pivots on dashboard**: `💧 MTF Pivots [15]: H=X L=Y`
   - For longs: price must be above the L= value (liqGate will enforce this automatically)
   - For shorts: price must be below the H= value

#### Entry Rules
- **Wait for `🟢 Buy` or `🔴 Sell` shape** to appear on the M5 chart
- **Only take `🔥 MASTER SYNC` or `📈 BULLISH BIAS (Strong)` signals** at the start of a session
- **`CT-L` / `CT-S` (counter-trend) signals**: TP1 only — never hold to TP3 against the Daily
- **Rejected signals (grey X)**: Do not manually override. The gate fired for a reason.

#### Trade Management
- **TP1 hit (1:1)**: Take 33% off. Move SL to +5 pips above entry (or structural breakeven)
- **TP2 hit (1.5:1)**: Take 50% of remaining. Move SL to entry (risk-free)
- **TP3 hit (2:1)**: Take 75% of remaining. The last 25% enters Holder Mode with MTF Liquidity trail
- **Holder Mode runner**: Exit when `close` crosses back through the MTF Liq pivot trail shown on dashboard

#### Session Windows (UTC)
| Session | Window | Best For |
|---------|--------|----------|
| **London** | 07:00–12:00 | Trending M5 moves; highest probability for MASTER SYNC signals |
| **NY Overlap** | 12:00–16:00 | Highest liquidity; watch for PDH/PDL sweeps before directional move |
| **NY Solo** | 16:00–21:00 | Continuation plays only; volume drops after 18:00 UTC |
| **Avoid** | 21:00–06:00 | Low ATR, high spread, choppy; system will show `⚠️ LOW VOLATILITY` |

#### What the Dashboard Tells You Before Each Entry

```
📊 CORE SIGNALS
EURUSD | 5  1.09845
👑 LONDON SESSION  |  ATR: Med (0.00014)
📅 Daily Context: ↔ Inside Range [PDH: 1.10123 | PDL: 1.09234]
ATM 🟢  Regime 📈
VWAP 📈  Fib 📈
RSI 📈 (62)  MACD: Bull
🔒 FibGate: OFF  LiqGate: ✅ OK
💧 MTF Pivots [15]: H=1.10023  L=1.09512
```

Read this as:
- `ATM 🟢` — ATM bot is in a buy posture
- `Regime 📈` — RSI momentum confirmed bullish
- `VWAP 📈` — Adaptive VWAP swing is bullish
- `Fib 📈` — Double-EMA trend is bullish
- `LiqGate: ✅ OK` — Price is above the M15 structural demand floor
- `MTF Pivots: L=1.09512` — The demand floor is 1.09512; as long as price holds above this, longs are structurally valid

#### What `⛔ BLOCKED` Means and What To Do
- `FibGate: ⛔ Neut` — Fib trend is flat. If FibTrend gate is OFF this does not block; it is informational only.
- `LiqGate: ⛔ BLOCKED` — Price is on the wrong structural side of the MTF pivot. **Stand aside.** Wait for price to sweep the pivot and flip.

### M5 Signal Quality Tiers

| Scenario | Score | 4-Layer | Action |
|----------|-------|---------|--------|
| MASTER SYNC | ≥10, all 4 layers aligned | ✅ All 4 | Full position, TP3 target, activate MTF runner |
| Strong Bias | 6–9, 3+ layers aligned | ✅ 3/4 | Standard position, TP3 target |
| Moderate | 3–5, 2 layers aligned | ✅ 2/4 | Half position, TP1 target only |
| Counter-trend | Any, Sovereign opposite | ⚠️ CT | Quarter position, TP1 only, SL tighter |
| Weak | < 3 | ❌ | Skip. No edge. |

---

## 10. Is This Approach Profitable?

This is the most important question, and it deserves an honest answer — not a sales pitch.

### What the Architecture Gets Right

**1. Risk management is structurally sound.**
The system risks a fixed dollar amount per trade (default $15), not a percentage of account that compounds slippage decisions. Position size is calculated correctly per asset class (forex lots use 100k notional, crypto uses 1:1 notional). The partial exit model (33%→50%→75%) locks in progressively more profit while letting a runner work. This is the right structure.

**2. Multiple confirmation layers reduce noise entries.**
A raw ATM bot signal needs to pass: regime filter (RSI momentum), VWAP confirmation (optional), Fibonacci trend gate (optional), AND liquidity gate (structural position check). Each layer alone is imperfect. Together they should increase the signal-to-noise ratio significantly compared to a single ATR trail crossing.

**3. The 5-layer scoring is a genuine edge indicator.**
A score of +12/15 means D, H4, H1, M15, and M5 are all screaming the same direction across three independent measures each. That is a real confluence reading. The weakest part is that the 5 TFs are hardcoded — you cannot tune them — but the defaults (D/H4/H1/M15/M5) are sensible for any intraday chart.

**4. Liquidity gate is the single most valuable v7.1 addition.**
The most common reason a technically valid ATM signal fails is that price is entering into a pocket of opposing order flow (a supply zone on a long, a demand zone on a short). The liqGate directly addresses this. It does not eliminate all losses, but it should reduce the number of losses that happen immediately after entry.

**5. The SL Autopsy creates a feedback loop.**
A system that explains its own losses in structured language gives you something to act on. Over 20–30 trades you will see patterns in the autopsy text (e.g. "SOVEREIGN VETO" appears frequently = you are taking too many counter-trend trades; "LOW VOLATILITY" appears = your session timing is wrong). Most systems show you PnL. This one shows you why.

### What Can Undermine It

**1. Signal frequency will be low when gates are strict.**
With `requireRegime + requireLiqGate + requireFibTrend` all ON, you may see 1–3 signals per session day on M5. That is not a flaw — it is the price of quality. The danger is **boredom trading**: manually forcing entries when the agent says stand aside. The system cannot prevent that.

**2. The 5-layer scoring hardcodes timeframes that may not match your chart TF.**
The D/H4/H1/M15/M5 scoring tree is excellent when you trade M5. If you trade M15, the M5 layer of the scoring is now your H1 chart context, which creates drift. The system is architecturally built for M5 as the execution TF.

**3. Choppy, low-ATR sessions will produce false signals that pass all gates.**
When `ATR = Low` is shown on dashboard, the system flags it. But the ATM bot can still fire in a ranging market. Rule: when dashboard shows `ATR: Low` and `⚠️ QUIET BULL/BEAR — WAIT`, do not enter regardless of signal shape.

**4. The Daily sovereign filter can be "wrong" for days at a time.**
If Daily flips bearish but H4 and H1 are strongly bullish (a retracement that does not break Daily structure), the fractal system will mark your longs as counter-trend. This is conservative by design — counter-trend entries require TP1-only discipline. The risk is labelling a valid H4 pullback play as high-risk.

**5. No Pine Script strategy is validated by the strategy tester alone.**
The built-in strategy tester uses `strategy.entry/close` calls with default 100% position sizing and no real commissions/slippage configured. The Platinum Risk Model calculates correct lot sizes but the tester does not simulate partial closes at TP1/TP2 with true dollar P&L. The pip tracker and profit factor are the better performance metrics to watch during live forward testing.

### Realistic Expectations

Based on the architecture:

| Metric | Realistic Expectation |
|--------|-----------------------|
| **Win Rate (TP1 reached)** | 45–60% depending on session and asset |
| **Profit Factor** | 1.5–2.5 when score threshold ≥ 6 is respected |
| **Master Sync signals** | 2–5 per week on a major forex pair (EURUSD, GBPUSD) |
| **Average holding time (M5)** | 30 minutes to 4 hours to reach TP3 |
| **Drawdown periods** | Expect 5–8 consecutive SL events when score < 6 entries are taken |

### The Honest Bottom Line

**This system is more likely to be profitable than most retail approaches** because:
- It has structured risk management (fixed $ risk, partial exits)
- It has multiple alignment requirements before firing
- It has a feedback loop (autopsy, daily log, ML data block)
- It respects liquidity structure (PDH/PDL, MTF pivots, sweep detection)

**But profitability is not guaranteed** because:
- It requires strict adherence to the score threshold (≥ 6 for full positions)
- It requires trading the right sessions (London/NY, not Asia)
- It requires not overriding BLOCKED or counter-trend signals
- It requires forward testing on your specific asset before going live

**The recommended forward test period**: 30 trading days on a demo account. Track: signal count, score at entry, gate states, outcome (TP reached vs SL hit), and the SL autopsy reason. After 30 days you will have enough data to see if your specific asset + session combination has a positive profit factor with this system.

---

## 11. Glossary

| Term | Meaning |
|------|---------|
| **Master Sync** | All 4 fractal layers aligned in same direction (strongest signal type) |
| **Counter-Trend (CT)** | Signal fires opposite to the Sovereign (Daily) direction |
| **Regime** | RSI momentum state — Bullish when RSI > 55 with rising EMA5, Bearish when RSI < 50 with falling EMA5 |
| **Liq Gate** | MTF Liquidity Gate — blocks entries on wrong structural side of a higher-TF pivot |
| **Fib Gate** | Fibonacci Trend Gate — blocks entries against the double-EMA trend direction |
| **Holder Mode** | Active after TP3 hit — a 25% runner trails using VWAP, Structural pivot, or MTF Liq pivot |
| **Glass Box** | The named principle: every alert includes transparent reasoning, not just a direction signal |
| **Sovereign** | The highest-priority timeframe (Layer 1) — its direction is the macro veto |
| **PDH/PDL** | Previous Day High / Previous Day Low — key intraday levels |
| **POC** | Point of Control — the Volume Profile price level with the most traded volume |
| **VAH/VAL** | Value Area High / Low — the range containing 70% of session volume |
| **BOS** | Break of Structure — price breaks a prior swing high/low in the trend direction |
| **CHoCH** | Change of Character — price breaks structure against the prior trend (potential reversal) |
| **OB** | Order Block — the last bullish/bearish candle before a BOS, used as a support/resistance zone |
| **FVG** | Fair Value Gap — a 3-candle imbalance where price gapped and may return to fill |
| **EQH/EQL** | Equal Highs / Equal Lows — clustered swing levels that act as liquidity targets |
| **PF** | Profit Factor — gross winning pips divided by gross losing pips. PF > 2.0 = STRONG |

---

*Not financial advice. Past signal behavior does not guarantee future performance.*
*© 2026 Absolute Dollar Intelligence | ADSA v7.1 | Invite-Only*
