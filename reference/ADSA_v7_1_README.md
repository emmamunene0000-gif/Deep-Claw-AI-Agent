# ABSOLUTE DOLLAR SUPREME AGENT — ADSA v7.2
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
7a. [v7.2 New Features In Detail](#7a-v72-new-features-in-detail)
7. [Alert & Telegram Setup](#7-alert--telegram-setup)
8. [TradeSgnl / Bitget Automation](#8-tradesgnl--bitget-automation)
9. [M1 & M5 Intraday Framework](#9-m1--m5-intraday-framework)
10. [Is This Approach Profitable?](#10-is-this-approach-profitable)
11. [Glossary](#11-glossary)

---

## 1. What This Is

ADSA v7.2 is a **complete multi-timeframe trading system** built in Pine Script v6 for TradingView. It is not a simple indicator — it is an agent that:

- **Reads the market** across 5 timeframes simultaneously using a composite scoring engine (+15 to −15)
- **Gates signals** through up to 9 stacked layers: regime filter, Fibonacci trend, MTF liquidity position, 5-layer composite score, 4-layer fractal sync, volume confirmation, MACD confirmation, and SMC structure bias
- **Sizes positions** automatically using a dollar-risk model routed through the correct asset-class math (forex lots, crypto coins, futures contracts)
- **Manages trades** through a structured 3-TP progression with an optional runner in Holder Mode
- **Broadcasts reasoning** to Telegram (War Room full Glass Box + Public sanitized) with transparent per-event commentary
- **Logs performance** daily with a reset pip tracker, profit factor display, and a machine-readable ML data block

Everything it does is visible. Every blocked signal has a reason. Every stop loss has an autopsy. That transparency is the architecture's core design principle.

---

## 2. Architecture — 19 Subsystems

| # | Subsystem | What It Does |
|---|-----------|--------------|
| 1 | **Fractal 4-Layer Consensus + Sync Gate** | Sovereign/Anchor/Filter/Exec alignment. Fully aligned = `🔥 MASTER SYNC`. v7.2: configurable min-sync-layers gate *blocks* entries when fewer than N layers agree |
| 2 | **5-TF Composite Scoring + Score Gate** | D/H4/H1/M15/M5 each scored on 3 factors (Regime, VWAP, Fib). Range: +15 to −15. v7.2: score now *wires into the signal chain* — below-threshold entries are blocked |
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
| 18 | **MTF Liquidity Trail** *(v7.1)* | Pivot-based holder trail from a higher TF + optional ATM signal gate. Pivot length now a dropdown: 14/20/50/100/200 (default 50) |
| 19 | **Fibonacci Trend Gate** *(v7.1)* | Double-EMA Fib trend gates ATM signals against counter-trend entries. Default changed to ON in v7.2 |
| 20 | **SMC Structure Gate** *(v7.2 NEW)* | Optional gate using `swingTrend.bias` from the SMC engine — entries require confirmed BOS/CHoCH structural direction agreement |

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
3. Click **Save** → name it "Absolute Dollar Agent v7.2"
4. Click **Add to chart**
5. The strategy will load with default settings — configure using the **Settings** panel

> **Important**: This is a `strategy()` script, not `indicator()`. It will show a Strategy Tester panel. This is intentional — the tester gives you a live backtest of signal quality on the current chart.

> **v7.2 note**: On first load, the Score Gate (default ON, ≥4) and Sync Gate (default ON, ≥2) are active. If you see no signals in the Strategy Tester on a quiet asset/period, this is expected — the gates are working. Try lowering `Min Score Long` to `2` temporarily to see what signals the system would have taken without those gates.

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

### 📊 Signal Gate Chain *(v7.2 NEW)*
| Input | Default | Notes |
|-------|---------|-------|
| Gate Signals on 5-Layer Score | `ON` | Wires the composite score into the signal chain. Uses the *previous bar's* total_score to avoid look-ahead |
| Min Score Long | `4` | Minimum total_score (0–15) required to allow a long entry. Recommended: 4 minimum, 6 for full position |
| Min Score Short | `-4` | Maximum total_score (0 to −15) required to allow a short entry |
| Min 4-Layer Sync | `2` | How many of the 4 fractal layers must agree. `0` = gate disabled; `4` = only MASTER SYNC signals pass |
| Volume Confirm | `OFF` | Require volume > SMA(vol,20) at signal bar. Helps filter low-conviction bar closes |
| MACD Confirm | `OFF` | Require MACD line above/below signal line. Reduces signals in choppy markets |
| SMC Structure Gate | `OFF` | Require `swingTrend.bias` to agree with signal direction. Blocks entries that contradict the last confirmed BOS/CHoCH |

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
| Pivot Lookback Length | `50` *(was 14)* | **Dropdown: 14 / 20 / 50 / 100 / 200.** 50 = Claw Liquidity Suite fast-pivot setting. 200 = macro slow pivots. Higher = fewer, more significant pivot levels |
| Gate ATM Signals to Liq Trail | `ON` | Block entries on the wrong structural side |

### 📊 Fibonacci Trend Gate *(v7.1)*
| Input | Default | Notes |
|-------|---------|-------|
| Require Fibonacci Trend Alignment | `ON` *(was OFF)* | Double-EMA Fib trend gate. **Default changed to ON in v7.2** — gate is now active by default to reduce counter-trend noise. Disable on M1/M5 scalping charts where both-direction entries are needed |

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

Now ON by default in v7.2. The double-EMA basis (`EMA(EMA(close, 200), 200)`) is a slow, smooth trend engine that cuts through noise. Disable it when:
- You are scalping M1/M5 and need signals in both directions within sessions
- Your sovereign/fractal layers are already filtering aggressively

Keep it ON (default) when:
- You are swing trading or intraday trend-following
- You want to reduce counter-trend entry noise

---

## 7a. v7.2 New Features In Detail

### 5-Layer Score Gate (the most important v7.2 change)

**The problem it solves**: In v7.1, the composite score (D/H4/H1/M15/M5, range +15 to −15) was displayed prominently in the dashboard, the Telegram chain, and the Glass Box commentary — but it had **zero effect on whether a signal fired**. The ATM bot could trigger a full long entry with a score of −8 (5 TFs screaming bearish). The score was a label, not a gate.

**How v7.2 fixes it**: The score is now wired into the signal chain via a 1-bar persistence pattern:
- After `total_score` is computed each bar, it is stored in `_prev_score` (a `var` variable)
- On the next bar, `buy_signal_filtered` and `sell_signal_filtered` check `_prev_score` against your threshold before letting a signal through
- The 1-bar lag is intentional — it ensures the gate reads a confirmed, closed-bar score and never repaints

**Threshold guide**:
| Score | Meaning | Recommended action |
|-------|---------|-------------------|
| ±10–15 | Sovereign alignment — all 5 TFs agree | Full position, TP3 target, Holder Mode runner |
| ±6–9 | Strong bias — 4 of 5 TFs aligned | Standard position, TP3 target |
| ±4–5 | At gate threshold (default) | Half position, TP1/TP2 only |
| ±2–3 | Below gate — insufficient MTF edge | Stand aside; system blocks the signal |
| 0–±1 | Neutral — no directional alignment | Stand aside |

The default `min_score_long = 4` / `min_score_short = -4` is a conservative starting point. Raise to `6` for higher win-rate (fewer signals). Lower to `2` if you find the gates too restrictive on your specific asset.

### 4-Layer Fractal Sync Gate

**The problem it solves**: The `🔥 MASTER SYNC` label was informational only in v7.1. The 4-layer state machine (Sovereign/Anchor/Filter/Exec) tracked alignment and annotated commentary labels, but it did not block entries when layers disagreed.

**How v7.2 fixes it**: Two counters — `_sync_bull` and `_sync_bear` — count how many of the 4 fractal layers currently read bullish or bearish. These are compared against `min_sync_layers` (default: 2) before each signal fires.

With `min_sync_layers = 2`:
- An ATM buy signal requires at least 2 of the 4 layers to be in a bullish state
- This eliminates the most common "noise signal": ATM fires on M5 while Sovereign + Anchor are both bearish

**Tier guide**:
| min_sync_layers | Behavior | Best for |
|-----------------|---------|---------|
| `0` | Gate disabled — any signal passes | Maximum frequency; use with strict score gate instead |
| `1` | At least one layer agrees | Permissive; good for assets with low layer correlation |
| `2` *(default)* | Majority of lower layers agree | Balanced — blocks isolated M5 noise while allowing H1/D alignment plays |
| `3` | Strong alignment required | High-quality swing signals; will miss intraday breakouts |
| `4` | MASTER SYNC only | Lowest frequency; only the highest-conviction setups |

### SMC Structure Gate

**What it does**: Uses `swingTrend.bias` from the SMC engine (the same engine that draws BOS/CHoCH labels on the chart). This is the SMC view of structural direction:
- `BULLISH (1)` = the SMC engine has confirmed a bullish BOS or established bullish HTF bias
- `BEARISH (-1)` = bearish structural confirmation
- `0` = undefined / no confirmed structure yet

When enabled (`requireSMCGate = ON`), buy signals are blocked if `swingTrend.bias != BULLISH` and sell signals are blocked if `swingTrend.bias != BEARISH`.

**Important**: This gate uses zero additional `request.security` calls (the script is already near the 40-call limit at ~33 calls). `swingTrend.bias` is a `var trend` type that persists between bars — the gate is reading the *previous bar's confirmed structural bias*, which is clean and non-repainting.

**When to enable**: Turn ON when you want your ATM signals to be anchored to confirmed SMC structure, not just trend proxies. Most effective on M5/M15 when combined with the ScoreGate (prevents entries that have ATM momentum but no structural basis).

### Volume and MACD Confirms

Both are OFF by default — they are secondary filters for users who want tighter entry quality at the cost of signal frequency.

- **Volume Confirm**: Requires volume > SMA(vol,20) at the signal bar. Blocks quiet-session signals that fire on low-conviction candles. Most useful in crypto where volume is a meaningful on-chain proxy.
- **MACD Confirm**: Requires MACD line above signal line (longs) or below signal line (shorts). This is a momentum cross confirmation on top of the ATM trail cross. Useful for preventing entries immediately after a momentum exhaustion.

### Selector Pivot Length for MTF Liquidity

The MTF Liquidity Trail pivot lookback was previously hardcoded to 14 bars. This is now a dropdown:

| Setting | Behavior | Match With |
|---------|---------|-----------|
| `14` | Short lookback — most recent swing pivots | Scalp entries, M1/M5 intraday |
| `20` | Standard swing pivots | M5/M15 standard setup |
| `50` *(default)* | Claw Liquidity Suite fast-pivot | Matches CLS default for consistent level confluence |
| `100` | Macro swing structure | H1/H4 swing trading |
| `200` | Macro slow pivots | Matches Smart Signals 200-bar setting; D/W structural levels |

Setting this to 50 means the liquidity gate and trail levels will match the pivot levels drawn by the Claw Liquidity Suite, making the two systems consistent when used together.

### ai_advice Score-Contextual Sizing Guidance

The `ai_advice` string displayed in the Glass Box and Telegram is now **score-contextual** — it tells you not just direction but *what position size is appropriate* based on the current score:

- `🔥 MAX CONVICTION LONG` (score ≥ 10 + high ATR): Full size, run to TP3, runner in Holder Mode
- `✅ SOVEREIGN BULL` (score ≥ 10): Scale size, watch ATR for expansion
- `✅ HIGH CONF LONG` (score ≥ 6 + high ATR): Standard size, TP3 target
- `✅ STRONG BULL` (score ≥ 6): Standard size, full TP sequence
- `⚠️ AT GATE THRESHOLD` (score ≥ 4): Half size, TP1/TP2 only
- `⏳ BELOW SCORE GATE` (score ≥ 2): Shows current score — wait for gate threshold
- `⏳ LEAN BULL` (score > 0): Insufficient edge — stand aside
- *(symmetric for short side)*

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
- **Decision chain** (v7.2): each MTF layer shown as a single-line gate status — `D: ▲ 3/3 ✅ | H4: ▲ 2/3 ✅ | ...` — replaces the old ASCII tree format
- Score row: `📊 Score: 8.5/15  Gate≥4: ✅`
- Sync row: `🔗 Sync: 3↑/1↓ of 4  Gate≥2: ✅`
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
   - Score ±4–5: minimum gate met — half position, TP1/TP2 only *(v7.2 ScoreGate blocks if below ±4)*
   - Score ±6–9: standard position, TP3 target
   - Score ±10–15: full position, run TP3, activate Holder Mode runner
   - Score < ±4: system will automatically block signals — stand aside
4. **Check 4-Layer Sync**: Dashboard shows `🔗 Sync: N↑/M↓ of 4`. Default gate requires ≥ 2 aligned.
   - 3–4 layers aligned: high conviction, trade full size
   - 2 layers aligned: minimum gate met — reduce size
   - 1 layer: gate blocks signal automatically
5. **Check MTF Pivots on dashboard**: `💧 MTF Pivots [H1]: H=X L=Y`
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
🔒 FibGate: ✅ OK  LiqGate: ✅ OK
📊 ScoreGate: ≥4 | 7.5/15 ✅  Sync: 3↑/1↓ ✅
💧 MTF Pivots [60]: H=1.10023  L=1.09512
```

Read this as:
- `ATM 🟢` — ATM bot is in a buy posture
- `Regime 📈` — RSI momentum confirmed bullish
- `VWAP 📈` — Adaptive VWAP swing is bullish
- `Fib 📈` — Double-EMA trend is bullish
- `FibGate: ✅ OK` — FibTrend gate is ON and agrees (v7.2 default)
- `LiqGate: ✅ OK` — Price is above the H1 structural demand floor
- `ScoreGate: ≥4 | 7.5/15 ✅` — Score gate is active, current score 7.5 meets the ≥4 threshold
- `Sync: 3↑/1↓ ✅` — 3 of 4 fractal layers bullish, meets min-2 sync gate
- `MTF Pivots: L=1.09512` — The demand floor is 1.09512; longs are structurally valid above this

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
A raw ATM bot signal in v7.2 must pass up to 9 stacked gates before it fires: regime filter, Fibonacci trend, liquidity position, 5-layer composite score, 4-layer fractal sync, volume (optional), MACD (optional), and SMC structure (optional). Each layer alone is imperfect. Together they should increase the signal-to-noise ratio significantly compared to a single ATR trail crossing. All optional gates default OFF so the system is not paralysed for new users.

**3. The 5-layer score now controls entry decisions, not just labels.**
In v7.1 the composite score was a display metric — it appeared on the dashboard and in Telegram but had no effect on whether a signal fired. In v7.2, the score is wired into the signal chain via a 1-bar persistence gate. A score of +12/15 means D, H4, H1, M15, and M5 are all aligned across three independent measures each. This now *prevents entries* when the same factors that predict direction also say the edge is insufficient.

**4. Liquidity gate is the single most valuable v7.1 addition.**
The most common reason a technically valid ATM signal fails is that price is entering into a pocket of opposing order flow (a supply zone on a long, a demand zone on a short). The liqGate directly addresses this. It does not eliminate all losses, but it should reduce the number of losses that happen immediately after entry.

**5. The SL Autopsy creates a feedback loop.**
A system that explains its own losses in structured language gives you something to act on. Over 20–30 trades you will see patterns in the autopsy text (e.g. "SOVEREIGN VETO" appears frequently = you are taking too many counter-trend trades; "LOW VOLATILITY" appears = your session timing is wrong). Most systems show you PnL. This one shows you why.

### What Can Undermine It

**1. Signal frequency will be low when gates are strict.**
With the full v7.2 gate chain active (Regime + FibGate + LiqGate + ScoreGate≥4 + SyncGate≥2), you may see 1–3 signals per session day on M5. That is not a flaw — it is the price of quality. The danger is **boredom trading**: manually forcing entries when the agent says stand aside. The rejected signal shapes (grey X) exist precisely to show you what was blocked and why. Honour them.

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
| **Score Gate** *(v7.2)* | 5-layer composite score gate — blocks entries when `total_score` is below the configured threshold |
| **Sync Gate** *(v7.2)* | 4-layer fractal sync gate — blocks entries when fewer than N of 4 layers agree with the signal direction |
| **SMC Gate** *(v7.2)* | SMC Structure Gate — blocks entries that contradict `swingTrend.bias` (last confirmed BOS/CHoCH direction) |
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
*© 2026 Absolute Dollar Intelligence | ADSA v7.2 | Invite-Only*
