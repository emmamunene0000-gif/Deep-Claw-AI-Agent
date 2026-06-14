# ADSA v7.5 — Absolute Dollar Agent
## Operator Reference Manual

> **PineScript v6 `strategy()` | Intraday M1/M5 | TradingView → TradeSgnl → Telegram**

---

## Table of Contents

1. [What Is ADSA & What's New in v7.5](#1-what-is-adsa--whats-new-in-v75)
2. [TradingView Setup](#2-tradingview-setup)
3. [Telegram Setup](#3-telegram-setup)
4. [TradeSgnl Setup](#4-tradesgnl-setup)
5. [Complete Input Reference](#5-complete-input-reference)
6. [Signal Lifecycle](#6-signal-lifecycle)
7. [Pyramid Scale-In](#7-pyramid-scale-in)
8. [Reading the Dashboard](#8-reading-the-dashboard)
9. [Reading Telegram Messages](#9-reading-telegram-messages)
10. [Reading the Chain Narrative](#10-reading-the-chain-narrative)
11. [Reading the Episode Log](#11-reading-the-episode-log)
12. [SL Autopsy Guide](#12-sl-autopsy-guide)
13. [Daily Operator Checklist](#13-daily-operator-checklist)
14. [Known Behaviors & Edge Cases](#14-known-behaviors--edge-cases)

---

## 1. What Is ADSA & What's New in v7.5

**ADSA (Absolute Dollar Agent)** is a multi-timeframe, rules-based intraday trading system implemented as a PineScript v6 `strategy()` on TradingView. It combines:

- A **UT Bot ATR trailing stop** as the core signal engine
- A **Fractal 4-Layer State Machine** for multi-TF confluence filtering
- A **5-TF Composite Scoring Engine** for quantified directional conviction
- A **Platinum Risk Model** for position sizing and trade progression
- **Episodic and Session Memory** for real-time contextual awareness
- **Dual Telegram broadcast** (War Room premium + Public sanitized)
- **TradeSgnl broker integration** for automated order execution

The agent does not predict. It confirms. Every trade requires a UT Bot signal, a regime gate pass, and a 4-layer fractal alignment before an entry is valid.

---

### What Changed in v7.5

| Feature | v7.0 | v7.5 |
|---|---|---|
| Fib trend gate | Not present | `requireFib` input — slope-agreement filter on Fib basis |
| Pyramid / Scale-In | Not present | Section 14.5 — 50% scale-in on re-confirmation |
| Session Memory | Not present | Section 22.5 — score/signal/SL/TP counters per VP session |
| Episodic Memory | Arrays tracked | Section 23.1 — `f_session_log()`, `f_signal_context()`, `f_score_momentum()`, `f_live_assessment()` |
| Chain Narrative | Basic | Trail arrows (↑↓→) per TF, single-char states, synthesis line |
| SL Autopsy | Static tags | Priority 1-5 ordered root-cause classification |
| Daily Assessment | Quality tiers | `f_daily_assessment()` — real PF/WR/signal-mix breakdown |
| Scale-in alerts | Not present | Additional `strategy.entry` at 50% size via TradeSgnl |

---

## 2. TradingView Setup

### 2.1 Loading the Script

1. Open TradingView on the **M1 or M5** chart of your instrument.
2. Open the Pine Editor (`/pine-editor` or bottom panel).
3. Paste the ADSA v7.5 source. Click **Save**, then **Add to chart**.
4. The strategy panel will appear at the bottom. The dashboard table will appear on the chart.

### 2.2 Recommended Chart Settings

| Setting | Value |
|---|---|
| Timeframe | M1 or M5 (exec TF) |
| Session | Match your broker session (UTC offset matters for VP sessions) |
| Extended hours | OFF unless you specifically trade pre/post market |
| Bar replay | Supported — useful for strategy backtesting |

### 2.3 Creating Alerts

ADSA fires execution orders through TradingView alerts, not from the Pine script directly. You must create one alert per condition.

**Required alerts (minimum):**

| Alert name | Condition | Alert message |
|---|---|---|
| ADSA Long Entry | `strategy.order` fires (Long) | Use your TradeSgnl long entry template |
| ADSA Short Entry | `strategy.order` fires (Short) | Use your TradeSgnl short entry template |
| ADSA TP1 | `strategy.order` fires (TP1 close) | TP1 template |
| ADSA TP2 | `strategy.order` fires (TP2 close) | TP2 template |
| ADSA TP3 | `strategy.order` fires (TP3 close) | TP3 template |
| ADSA Exit | `strategy.order` fires (Exit/SL) | Exit template |
| ADSA Scale-In | `strategy.order` fires (Scale-In) | Scale-in template |

**Alert settings:**
- **Expiration:** Open-ended (no expiry)
- **Trigger:** Once per bar close (recommended) or Once per bar
- **Notifications:** Webhook URL only (TradeSgnl endpoint)

> Do not enable email or push notification on execution alerts — only the webhook fires the broker. Telegram messages are sent directly from the script via `alertcondition` + separate webhook or via the built-in `alert()` calls in the Broadcast Engine.

---

## 3. Telegram Setup

ADSA broadcasts to two separate Telegram channels with different content tiers.

### 3.1 Create a Telegram Bot

1. Message `@BotFather` on Telegram.
2. Send `/newbot` — follow prompts to name your bot and get a **Bot Token** (format: `1234567890:ABCdef...`).
3. Keep this token private. Anyone with it can send messages as your bot.

### 3.2 Get Chat IDs

**For a channel:**
1. Add your bot as an administrator to the channel.
2. Send any message to the channel.
3. Call `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser.
4. Find `"chat":{"id":...}` — channel IDs are negative numbers (e.g., `-1001234567890`).

**For a group:**
Same process. Group IDs are also negative.

### 3.3 Configure in ADSA

| Input | Value |
|---|---|
| `enable_tg_1` | ON |
| `tg_chat_id_1` | War Room channel ID (e.g., `-1001234567890`) |
| `enable_tg_2` | ON |
| `tg_chat_id_2` | Public channel ID |
| `tg_public_sanitize` | ON (public gets 4-line summaries) |

### 3.4 Webhook Setup

The Broadcast Engine wraps messages in `_tg_json()` for direct Telegram Bot API delivery. The alert webhook URL format is:

```
https://api.telegram.org/bot<TOKEN>/sendMessage
```

Set this as your TradingView webhook URL for Telegram-targeted alerts.

> War Room and Public channel alerts use separate alert conditions, each pointing to the correct chat ID embedded in the message payload.

---

## 4. TradeSgnl Setup

TradeSgnl receives structured alert messages from TradingView and converts them to broker orders.

### 4.1 Message Template Inputs

Configure these in the ADSA inputs panel under the **TradeSgnl** group:

| Input | Purpose | Example value |
|---|---|---|
| `long_entry_message` | Fires on confirmed buy signal | See template below |
| `short_entry_message` | Fires on confirmed sell signal | See template below |
| `tp1_message` | Fires when TP1 close executes | See template below |
| `tp2_message` | Fires when TP2 close executes | See template below |
| `tp3_message` | Fires when TP3 close executes | See template below |
| `exit_message` | Fires on SL hit or manual exit | See template below |
| `scale_in_long_message` | Fires on scale-in (long re-confirm) | See template below |
| `scale_in_short_message` | Fires on scale-in (short re-confirm) | See template below |

### 4.2 Template Placeholders

| Placeholder | Resolves to |
|---|---|
| `{{vol}}` | Calculated position size (contracts/lots) |
| `{{sl}}` | Stop loss price |
| `{{tp1}}` | TP1 price |
| `{{tp2}}` | TP2 price |
| `{{tp3}}` | TP3 price |
| `{{risk}}` | Dollar risk for this trade |

### 4.3 Example Templates

**Long entry:**
```
{"action":"buy","symbol":"{{ticker}}","volume":"{{vol}}","sl":"{{sl}}","tp":"{{tp1}}","comment":"ADSA_L"}
```

**Short entry:**
```
{"action":"sell","symbol":"{{ticker}}","volume":"{{vol}}","sl":"{{sl}}","tp":"{{tp1}}","comment":"ADSA_S"}
```

**TP1 partial close:**
```
{"action":"closebuy","symbol":"{{ticker}}","volume":"{{vol}}","comment":"ADSA_TP1"}
```

**Exit (full close):**
```
{"action":"closebuy","symbol":"{{ticker}}","volume":"all","comment":"ADSA_EXIT"}
```

**Scale-in long:**
```
{"action":"buy","symbol":"{{ticker}}","volume":"{{vol}}","sl":"{{sl}}","comment":"ADSA_SI_L"}
```

> Adjust `action` field to match your TradeSgnl broker connector syntax. `closebuy`/`closesell` vs `close` depends on your broker adapter.

### 4.4 Asset Router

ADSA automatically selects contract notional for position sizing:

| Asset type | Notional used |
|---|---|
| Forex pairs | 100,000 |
| Crypto | 1 |
| Futures | Point value (from `syminfo.pointvalue`) |

Set `asset_context` input to label the instrument in alerts (e.g., `"EURUSD"`, `"BTCUSDT"`).

---

## 5. Complete Input Reference

### 5.1 Super Admin

| Input | Default | Description |
|---|---|---|
| `sovereign_tf` | `"D"` | Macro veto timeframe. Layer 1 of the fractal state machine. |
| `admin_manual_bias` | `AUTO` | Override: `AUTO` = system decides. `FORCE BULL` / `FORCE BEAR` = override direction. `SILENCE` = no signals. |
| `asset_context` | `""` | Watchlist note appended to all alerts. E.g., `"EURUSD London"`. |
| `admin_commentary` | `""` | Operator analysis text. Appears in War Room messages only. |
| `tg_public_sanitize` | `ON` | `ON` = public gets 4-line summaries. `OFF` = full Glass Box output to public. |

### 5.2 Telegram

| Input | Default | Description |
|---|---|---|
| `enable_tg_1` | `ON` | Enable War Room (premium) channel. |
| `tg_chat_id_1` | `""` | War Room Telegram chat ID. |
| `enable_tg_2` | `OFF` | Enable Public channel. |
| `tg_chat_id_2` | `""` | Public Telegram chat ID. |

### 5.3 Fractal 4-Layer State Machine

| Input | Default | Description |
|---|---|---|
| `anchor_tf` | `"60"` | Layer 2 (H1) — session bias timeframe. |
| `filter_tf` | `"15"` | Layer 3 (M15) — navigator/filter timeframe. |
| `sovereign_tf` | `"D"` | Layer 1 (Daily) — macro veto (also in Super Admin). |

Layer 4 is always the chart timeframe (exec TF).

### 5.4 ATM Bot (Signal Engine)

| Input | Default | Description |
|---|---|---|
| `a_buy` | `3.5` | UT Bot sensitivity — buy side. Higher = fewer, later entries. |
| `a_sell` | `3.5` | UT Bot sensitivity — sell side. |
| `c_buy` | `2` | ATR period — buy trail. Lower = faster trailing stop. |
| `c_sell` | `2` | ATR period — sell trail. |
| `enableRegimeFilter` | `ON` | Activates RSI + optional VWAP gate. Strongly recommended ON. |
| `requireVWAP` | `OFF` | Require price above adaptive VWAP for longs / below for shorts. |
| `requireFib` | `OFF` | **v7.5** — Require Fib trend basis slope to agree with exec direction. |

**Tuning guidance:**

- `a_buy/a_sell` 3.0–4.0 is the working range for M1/M5. Below 3 generates noise. Above 4.5 misses moves.
- `c_buy/c_sell` = 2 is aggressive. Set to 3–4 for calmer instruments.
- `requireFib = ON` reduces signal frequency but filters false starts on ranging markets.

### 5.5 Risk Management (Platinum Risk Model)

| Input | Default | Description |
|---|---|---|
| `risk_per_trade` | `$15` | Dollar risk per signal. Drives position size calculation. |
| `sl_buffer_atr` | `1.5` | ATR multiplier applied to swing SL placement. |
| `prevent_reversals` | `ON` | Block opposing signals while a trade is active. |
| `holder_trail_type` | `"Structural"` | Trail method for the runner after TP3: `"Structural"` (pivot) or `"VWAP"`. |

### 5.6 TradeSgnl (Section 30)

| Input | Description |
|---|---|
| `long_entry_message` | JSON template for long entry. |
| `short_entry_message` | JSON template for short entry. |
| `tp1_message` | Template for TP1 partial close. |
| `tp2_message` | Template for TP2 partial close. |
| `tp3_message` | Template for TP3 partial close. |
| `exit_message` | Template for SL hit or full exit. |
| `scale_in_long_message` | Template for scale-in (long). |
| `scale_in_short_message` | Template for scale-in (short). |

### 5.7 Broadcast & Reporting

| Input | Default | Description |
|---|---|---|
| `report_hour_utc` | Configurable | UTC hour to fire the daily report. |
| `enable_tg_1` | `ON` | War Room broadcast toggle. |
| `enable_tg_2` | `OFF` | Public broadcast toggle. |

---

## 6. Signal Lifecycle

A trade moves through a strict pipeline. Each gate is a veto — if any gate fails, the signal is suppressed.

```
UT Bot ATR trail flip
        │
        ▼
  Regime Gate (Section 7)
  ├── RSI direction agrees?
  ├── requireVWAP? → Price vs adaptive VWAP
  └── requireFib? → Fib basis slope agrees?
        │
        ▼
  posState flip (≤0 → 1 for buy, ≥0 → -1 for sell)
        │
        ▼
  prevent_reversals check
  (if ON and opposing trade active → suppress)
        │
        ▼
  buy_signal_confirmed / sell_signal_confirmed
        │
        ▼
  Risk Model (Section 14)
  ├── SL = 5-bar swing high/low ± (sl_buffer_atr × ATR)
  ├── If SL wrong side → fallback = 1.5 ATR
  ├── TP1 = 1:1R | TP2 = 1.5:1R | TP3 = 2:1R
  └── Size = risk_per_trade ÷ (SL_distance × notional)
        │
        ▼
  strategy.entry fires → TradeSgnl webhook → broker order
        │
        ▼
  Trade Progression (Section 16)
  ├── TP1 hit → close 25–33% → SL tightens toward entry
  ├── TP2 hit → close 50% of remaining → SL moves to entry (risk-free)
  ├── TP3 hit → close 75% of remaining → Holder Mode
  │     └── Runner trailed by VWAP or structural pivot
  └── SL hit at any stage → full close + autopsy fires
```

### 6.1 Regime Gate Details

The regime gate is the primary quality filter. With `enableRegimeFilter = ON`:

- **RSI gate:** RSI must be in positive territory for longs, negative for shorts (above/below 50 on the exec TF).
- **VWAP gate** (`requireVWAP = ON`): Price must be above the adaptive VWAP for longs, below for shorts. VWAP is anchored to the session.
- **Fib gate** (`requireFib = ON`, v7.5): The Fib trend basis slope must agree with exec direction. This filters entries against the dominant intraday trend channel.

All enabled gates must pass simultaneously. A partial pass is a fail.

### 6.2 Fractal 4-Layer Alignment

| Layer | TF | Role | Variable |
|---|---|---|---|
| 1 — Sovereign | Daily (`sovereign_tf`) | Macro veto | Counter-trend flag if D opposes exec |
| 2 — Anchor | H1 (`anchor_tf`) | Session bias | Layer 2 direction |
| 3 — Filter | M15 (`filter_tf`) | Navigator | Layer 3 direction |
| 4 — Exec | Chart TF | Entry trigger | UT Bot signal |

`master_sync_buy` = all 4 layers aligned bullish.
`master_sync_sell` = all 4 layers aligned bearish.

When Layer 1 (Sovereign) opposes the exec direction, the **counter-trend flag** fires. Entries can still execute (the agent doesn't hard-block on Layer 1 opposition by default), but:
- The chain narrative synthesis line shows the warning
- TP1 focus is recommended (do not hold for TP3)
- The SL autopsy will classify this as Priority 1 cause if the trade loses

### 6.3 5-TF Composite Score

Each timeframe (D, H4, H1, M15, M5) contributes up to ±3 points:

| Component | Points |
|---|---|
| Regime direction | ±1 |
| VWAP alignment | ±1 |
| Fib direction | ±1 |

**Total range: -15 to +15.**

| Score | Interpretation |
|---|---|
| ≥ +10 | Sovereign momentum condition (requires ATR High state) |
| +6 to +9 | Strong directional bias |
| +3 to +5 | Moderate, tradeable with other gates |
| -2 to +2 | Neutral / choppy — reduce size or skip |
| ≤ -3 | Opposing bias — longs suppressed, shorts favored |

---

## 7. Pyramid Scale-In

### 7.1 What It Is

When ADSA's ATM Bot re-confirms the **same direction** while a trade is already active (posState does not flip — it was already 1 or -1), a **scale-in** fires instead of a new entry.

This is NOT a reversal. It is an addition to the existing trade at a more favorable price.

### 7.2 Scale-In Parameters

| Parameter | Value |
|---|---|
| Size | 50% of original position |
| Stop loss | Original trade entry price (breakeven protection) |
| Original trade SL/TP1-3 | Unchanged — `locked_*` vars are never modified |

### 7.3 Tracking Variables

| Variable | Meaning |
|---|---|
| `si_active` | `true` when a scale-in is currently open |
| `si_entry` | Price at which the scale-in was entered |
| `si_size` | Size of the scale-in position (50% of original) |

The scale-in is tracked independently from the primary trade. Its SL is the original entry — if price reverses to entry, the scale-in closes flat while the original trade remains open (now risk-free after TP2).

### 7.4 Scale-In in TradeSgnl

A separate `strategy.entry` call fires with `{{vol}}` = 50% of original size. Use `scale_in_long_message` / `scale_in_short_message` templates in TradeSgnl. Differentiate these from primary entries in your broker using the `comment` field (e.g., `ADSA_SI_L`).

### 7.5 When NOT to Scale In

- `prevent_reversals = ON` does not block scale-ins (they are same-direction). But if you are already at max exposure for the session, use `SILENCE` mode temporarily.
- Scale-ins with a score below +4 are lower quality — note this in the episode log.
- If sovereign (Layer 1) is opposing, consider skipping scale-ins even when the signal fires.

---

## 8. Reading the Dashboard

The ADSA dashboard table renders on the chart. Sections from top to bottom:

### 8.1 Header Block

```
ADSA v7.5 | [asset_context] | [admin_manual_bias]
Score: +11 ▲  |  ATR: HIGH  |  PDH/PDL: 🔼 Above PDH
```

- **Score** = current 5-TF composite score with directional arrow
- **ATR state** = HIGH / NORMAL / LOW based on current ATR vs average
- **PDH/PDL** = "🔼 Above PDH" / "🔽 Below PDL" / "↔ Inside Range"

### 8.2 Chain Narrative (Section 20)

Shows per-TF trail direction and state. See [Section 10](#10-reading-the-chain-narrative) for full detail.

### 8.3 Active Trade Block

```
LONG active | Entry: 1.08542 | Size: 0.15
SL: 1.08410 | TP1: 1.08674 | TP2: 1.08756 | TP3: 1.08838
Risk: $15.00 | R:R to TP3: 2.0
Stage: TP1 ✓ | SL at entry (risk-free)
```

- **Stage** updates as TP levels are hit
- After TP2, SL displays "at entry (risk-free)"
- After TP3, "Holder Mode — trailing [VWAP/Structural]"

### 8.4 Scale-In Block (when active)

```
SCALE-IN active | si_entry: 1.08590 | si_size: 0.075
si_SL: 1.08542 (original entry)
```

### 8.5 Session Memory Block (Section 22.5)

```
Session: LDN | Open score: +8
Signals: 3 | TP hits: 2 | SL hits: 0
```

Resets at each VP session open (not at midnight — one day can show LDN + NY as separate sessions).

### 8.6 Episode Log (Section 23.1)

Compact list of today's signals. See [Section 11](#11-reading-the-episode-log).

### 8.7 PDH/PDL Context (Section 15.5)

```
PDH: 1.08720  PDL: 1.08340
Status: 🔼 Above PDH
```

PDH/PDL pulled via `request.security("D", high[1]/low[1], lookahead_off)`.

---

## 9. Reading Telegram Messages

### 9.1 War Room (Premium) — Full Glass Box

**Session Open (~9 lines):**
```
⚡ ADSA | EURUSD | LDN SESSION OPEN
Score: +9 | ATR: NORMAL
POC: 1.08541 | VAH: 1.08620 | VAL: 1.08462
PDH: 1.08720 | PDL: 1.08340 | Status: ↔ Inside Range
Agenda: Bullish bias. Watch PDH as first target.
Score momentum: +9 (now) vs +6 (session open) → +3 drift

[admin_commentary if set]
```

**Entry Message (~12 lines):**
```
🟢 LONG ENTRY | EURUSD | M5
Score: +11 | ATR: HIGH | Sovereign: WITH
Fib: ALIGNED | VWAP: ABOVE | RSI: BULLISH
4L Sync: ✓ D H1 M15 M5 aligned

Context: Prior signals today:
  1. L[S+9]→TP2 ✓  2. L[S+8]→TP1 ✓

Entry: 1.08542 | SL: 1.08410 | Risk: $15.00
TP1: 1.08674 | TP2: 1.08756 | TP3: 1.08838
Size: 0.15 | R:R: 2.0 to TP3
ai_advice: Strong momentum. D aligned. ATR high — room to run. Liq above PDH.
[admin_commentary]
```

**TP Messages (~6 lines):**
```
🎯 TP1 HIT | EURUSD LONG
Entry: 1.08542 → TP1: 1.08674 (+132 pips R:1.0)
Closed: 25% | Remaining: 75%
SL tightened → 1.08490
Session tally: TP: 1 | SL: 0
```

**SL Hit:**
```
🔴 SL HIT | EURUSD LONG
Entry: 1.08542 → SL: 1.08410 (-132 pips)
Loss: -$15.00 | Autopsy: COUNTER-TREND (D opposing at entry)
Adjust: Consider skipping entries when Layer 1 opposes.
Session tally: TP: 2 | SL: 1
```

### 9.2 Public Channel (Sanitized) — 4 Lines Max

```
📡 ADSA SIGNAL | EURUSD
LONG entry confirmed. Momentum context: bullish.
Price context: Above PDH — breakout zone.
Full analysis in War Room 👉 [link]
```

Public messages never reveal: entry price, SL, TP levels, score, position size, or admin commentary.

### 9.3 Daily Report

Fires once per day at `report_hour_utc`.

**War Room daily report includes:**
- Full signal log (`f_session_log()` output for all VP sessions)
- Real PF/WR/signal-mix breakdown (`f_daily_assessment()`)
- ML data block:
```
[ATM_DATA_ADSA]
date,signal_type,score,direction,sl_cause,outcome,pips,R
2026-06-14,UT_CONFIRMED,+11,LONG,,TP2,+198,1.5
2026-06-14,UT_CONFIRMED,+8,LONG,COUNTER_TREND,SL,-132,-1.0
```
CSV-parseable for external ML pipelines.

---

## 10. Reading the Chain Narrative

The chain narrative is the multi-TF alignment summary in the dashboard.

### 10.1 Trail Direction Arrows

| Symbol | Meaning |
|---|---|
| ↑ | UT Bot trail is bullish (price above trail) on this TF |
| ↓ | UT Bot trail is bearish (price below trail) on this TF |
| → | Flat / indeterminate on this TF |

### 10.2 Single-Character States

| Char | Meaning |
|---|---|
| `L` | Long bias |
| `S` | Short bias |
| `N` | Neutral |

### 10.3 Full Narrative Example

```
Chain Narrative
D   ↑ L  +2   [Sovereign — WITH]
H4  ↑ L  +2
H1  ↑ L  +3   [Anchor]
M15 ↑ L  +2   [Filter]
M5  ↑ L  +2   [Exec]
─────────────────
Score: +11 | ATR: HIGH
Synthesis: Full 4-layer alignment long. Sovereign WITH. Sovereign momentum condition active.
```

### 10.4 Synthesis Line Patterns

| Synthesis line | Meaning |
|---|---|
| `Full 4-layer alignment long` | All layers agree — highest confidence |
| `Full 4-layer alignment short` | All layers agree short |
| `3/4 TF aligned long. D opposing — counter-trend.` | Layer 1 veto present. TP1 focus. |
| `2/4 aligned. Mixed — no trade.` | Insufficient confluence |
| `Sovereign momentum condition active.` | Score ≥ 10 + ATR High — strongest setup |

### 10.5 ai_advice Assembly

The `ai_advice` line is assembled from four live values:

1. **Score word** — "Strong momentum" (≥10), "Moderate" (6-9), "Weak" (<4)
2. **Sovereign relation** — "D aligned" or "D opposing — caution"
3. **ATR state** — "ATR high — room to run" / "ATR low — compression risk"
4. **Liq pool** — nearest significant level (PDH/PDL/VWAP)

Example: `Strong momentum. D aligned. ATR high — room to run. Liq above PDH.`

---

## 11. Reading the Episode Log

The episode log (Section 23.1 via `f_session_log()`) gives a compact record of every signal today.

### 11.1 Format

```
[index].[direction][type][score][momentum]→[outcome]
```

| Field | Values | Example |
|---|---|---|
| index | Signal number today | `1`, `2`, `3` |
| direction | L = Long, S = Short | `L` |
| type | Signal type in brackets | `[S]` = standard, `[SI]` = scale-in, `[CT]` = counter-trend |
| score | Score with sign | `+9`, `-3` |
| momentum | Score drift from session open | `+3` means score rose 3 from open |
| outcome | TP1/TP2/TP3/SL/OPEN | `→TP2`, `→SL`, `→OPEN` |

### 11.2 Examples

| Episode string | Reading |
|---|---|
| `1.L[S+9]+3→TP2` | Signal 1, Long, standard, score +9, session momentum +3, closed at TP2 |
| `2.L[CT+7]+1→SL` | Signal 2, Long, counter-trend (D opposing), score +7, momentum +1, hit SL |
| `3.S[S+11]+5→TP3` | Signal 3, Short, standard, score +11, momentum +5, hit TP3 |
| `4.L[SI+8]+2→OPEN` | Signal 4, Long scale-in, score +8, momentum +2, still open |

### 11.3 Context Display

`f_signal_context()` prepends the last 2 prior signals to each new entry message in War Room:

```
Context: Prior signals today:
  1. L[S+9]+3→TP2 ✓  2. L[CT+7]+1→SL ✗
```

This lets you immediately assess: "The last CT trade lost. Score has been reliable today."

### 11.4 Score Momentum

`f_score_momentum()` shows:
```
Score at session open: +6
Current score: +11
Drift: +5 ▲ (momentum building)
```

Increasing drift = alignment tightening intraday = higher-quality setups.

---

## 12. SL Autopsy Guide

When a trade hits SL, the autopsy fires automatically and classifies the loss by priority order.

### 12.1 Priority Order

| Priority | Cause | Classification condition |
|---|---|---|
| 1 | **Counter-trend** | Layer 1 (D) was opposing at entry time |
| 2 | **Liquidity sweep** | Price spiked past SL then reversed (wick pattern) |
| 3 | **Low ATR** | ATR was LOW at entry — compression environment |
| 4 | **Weak score** | Score was below +4 at entry |
| 5 | **Unknown** | None of the above — honest classification |

Only the highest-priority matching cause is shown. A trade that was counter-trend AND low ATR is classified as Priority 1.

### 12.2 What Each Cause Tells You

**Priority 1 — Counter-Trend:**
The sovereign (Daily) was opposing direction at entry. These trades carry structural headwinds. The system allows them but flags them clearly.
- *Adjust:* If counter-trend losses are recurring, consider increasing `a_buy/a_sell` sensitivity or setting `admin_manual_bias = SILENCE` during opposing daily sessions.

**Priority 2 — Liquidity Sweep:**
The market spiked through your SL to collect stops before reversing. This is structural — your SL was at a predictable level.
- *Adjust:* Increase `sl_buffer_atr` (e.g., 1.5 → 2.0) to place SL behind the sweep zone. Or accept this as the cost of trading near key levels.

**Priority 3 — Low ATR:**
Entry was in a compression environment. The ATR was below average, meaning the SL distance was tight relative to price noise.
- *Adjust:* Add the ATR state as a filter — skip signals when ATR state = LOW. Or widen `sl_buffer_atr`.

**Priority 4 — Weak Score:**
Score was below +4 at entry — marginal confluence. The UT Bot fired but the TF agreement was weak.
- *Adjust:* Consider a minimum score filter. Signals below +5 with no sovereign alignment should be sized down or skipped.

**Priority 5 — Unknown:**
The loss doesn't match any pattern. Market structure was valid, ATR was normal, score was fine, no counter-trend. Honest losses happen.
- *Adjust:* Nothing structural — maintain discipline and review in weekly data.

### 12.3 Autopsy in Telegram

War Room SL message includes:
```
Autopsy: COUNTER-TREND (D opposing at entry)
Adjust: Consider skipping entries when Layer 1 opposes.
```

The `[ATM_DATA_ADSA]` block in the daily report also logs `sl_cause` for ML analysis.

---

## 13. Daily Operator Checklist

### Morning Setup (30 min before first session)

- [ ] Check `report_hour_utc` fired — review yesterday's daily report
- [ ] Note today's PDH and PDL (displayed in dashboard header)
- [ ] Set `admin_commentary` if you have a directional thesis for the day
- [ ] Confirm `admin_manual_bias` is set correctly (AUTO unless you have a strong session view)
- [ ] Verify War Room and Public Telegram channels are receiving (send test if needed)
- [ ] Confirm TradeSgnl webhook is active — check last alert timestamp
- [ ] Review session memory from yesterday — note signal count and W/L pattern

### Session Open

- [ ] Watch for the **Session Open broadcast** (~9 lines in War Room)
- [ ] Note `mem_session_open_score` — this is your baseline for the session
- [ ] Review POC/VAH/VAL levels in the session open message
- [ ] Check PDH/PDL status — is price above PDH (breakout), below PDL (breakdown), or inside range?
- [ ] Note chain narrative synthesis line — is there 4-layer alignment or mixed signals?

### During Session (each signal)

- [ ] Read the entry Telegram before the broker fills (War Room ~12 lines)
- [ ] Check `f_signal_context()` — what did the last 2 signals do?
- [ ] Check the counter-trend flag — if present, target TP1 only, do not hold for TP3
- [ ] Confirm score at entry is ≥ +5 (or ≥ +8 for full-size trades)
- [ ] If `si_active` fires (scale-in), verify `si_SL` = original entry before accepting
- [ ] After TP1, confirm broker has tightened SL — cross-check with War Room TP1 message
- [ ] After TP2, confirm SL is now at entry (risk-free) — trade can now run to TP3 / Holder Mode

### End of Session

- [ ] Note session tally from final War Room message (Signals: X | TP: X | SL: X)
- [ ] Log any Priority 1 or 2 autopsy causes in your personal trade log
- [ ] If 2+ consecutive SL hits: check if a structural change has occurred (news, regime shift)
- [ ] Set `admin_commentary` for next session if relevant

### EOD Report

- [ ] Review `f_daily_assessment()` output — PF, WR, signal mix
- [ ] Parse `[ATM_DATA_ADSA]` block if running ML pipeline
- [ ] Review score momentum drift over the day — was alignment building or deteriorating?
- [ ] Check if counter-trend losses were dominant — adjust `admin_manual_bias` if needed for tomorrow

---

## 14. Known Behaviors & Edge Cases

### 14.1 `prevent_reversals = ON`

When a trade is active and an opposing signal fires:

- The opposing signal is **completely suppressed** — no alert, no entry, no Telegram message
- The original trade continues unaffected
- This is by design: on M1/M5, UT Bot can briefly flip direction on noise before the original trend resumes
- **Consequence:** If the market does genuinely reverse, you will miss the opposing entry and ride the original trade into SL
- **When to turn OFF:** If you manually manage exits and want to catch both directions of a volatile session. Not recommended for automated TradeSgnl setups

### 14.2 Counter-Trend Entries

Entries when Layer 1 (Daily) opposes exec direction:

- They are **allowed** by default — the agent does not hard-block them
- The counter-trend flag is set → War Room entry message shows `Sovereign: OPPOSING`
- Autopsy Priority 1 activates if the trade loses
- **Best practice:** Treat all counter-trend entries as TP1-only. Remove TP2/TP3 targets in your broker. Scale-in should NOT be taken on counter-trend signals

### 14.3 Fib Gate Lag (`requireFib = ON`)

The Fib trend basis slope uses a calculated basis period. On fast-moving M1/M5 markets:

- The Fib basis may lag 2–5 bars before confirming a new direction
- This means `requireFib = ON` will suppress the **first signal** of a new trend leg
- **Trade-off:** Fewer false starts vs. missing the first entry of a move. If you are early-entry oriented, keep `requireFib = OFF` and rely on score + VWAP gate instead
- **Best practice:** Use `requireFib = ON` during London/NY overlap when ranging is more common. Turn OFF during breakout sessions

### 14.4 Scale-In Fires Without Main Position (edge case)

This should not occur in normal operation, but if TradeSgnl fails to execute the primary entry:

- The scale-in will attempt to fire as if a position is already open
- `si_SL` will be set to the original entry price (which was never filled)
- **Recovery:** If you see `si_active = true` but no primary position in your broker, immediately set `admin_manual_bias = SILENCE` and reset via chart refresh. Notify TradeSgnl support

### 14.5 Session Memory Reset Timing

`mem_session_open_score` and session counters reset at each **VP session open**, not at UTC midnight:

- A single calendar day can have two VP sessions (LDN + NY)
- Each session starts fresh counters
- This means the "today" in the episode log refers to calendar day, but session memory tracks per-VP-session
- Do not confuse the two when reviewing intraday stats

### 14.6 Score at +10 Without ATR High

The sovereign momentum condition requires **both** `total_score >= 10` **and** ATR state = HIGH.

- A score of +12 with ATR LOW is NOT a sovereign momentum condition
- ATR LOW + high score = compression with alignment — wait for ATR expansion before treating it as full momentum
- The chain narrative synthesis line will show score ≥ 10 but will NOT append "Sovereign momentum condition active" unless ATR High also confirms

### 14.7 `admin_manual_bias = FORCE BULL / FORCE BEAR`

- Overrides the regime gate direction check — all regime tests are forced to agree with the bias
- Does NOT override the UT Bot trail flip requirement — you still need a UT Bot signal
- Does NOT override `prevent_reversals` — if a trade is active, opposing signals are still blocked
- **Use case:** You have a strong manual thesis and want to ensure only one direction is taken during the session. Exit or set to AUTO before end of session

### 14.8 PDH/PDL Lookahead

PDH/PDL use `lookahead_off` in `request.security()`. This means:

- Values update at the **daily bar close** of the previous day
- During early pre-market hours, PDH/PDL reflect the day before yesterday until the prior day's bar officially closes
- Adjust your UTC settings and session timing to ensure daily bars close at the correct market time for your instrument

### 14.9 Multiple TP Messages Without Broker Fills

If the price runs through TP1/TP2/TP3 in a single bar (gap or fast move):

- All TP `strategy.close` calls fire in sequence on the same bar
- TradeSgnl will receive all three close messages in rapid succession
- Depending on broker adapter latency, partial fills may not process correctly
- **Mitigation:** Use limit orders at TP levels in your broker setup rather than relying solely on the alert-triggered closes

### 14.10 Holder Mode Trail Type

After TP3, the runner position is trailed by either:

- `"Structural"` — pivot-based structural trail (tighter, more reactive to price structure)
- `"VWAP"` — session VWAP trail (looser, allows larger runner but can give back more)

VWAP trail is better for trending days where VWAP tracks the trend cleanly. Structural is better for choppy post-TP3 environments where you want to lock in more gains. Change `holder_trail_type` at the start of each session based on expected market character.

---

## Quick Reference Card

| Scenario | Action |
|---|---|
| Score < +4 | Skip or reduce size |
| Counter-trend flag | TP1 target only, no scale-in |
| ATR LOW | Wait for expansion or skip |
| 4-layer full sync | Full-size entry, hold for TP3 |
| Score ≥ +10 + ATR HIGH | Sovereign momentum — hold for Holder Mode |
| 2+ SL hits consecutive | Set SILENCE, review regime |
| Scale-in fires, no main position | Set SILENCE, reset chart |
| Fib gate suppressing signals | Consider turning `requireFib = OFF` |
| Day session counter-trend (D vs exec) | Reduce size 50%, TP1 only |

---

*ADSA v7.5 — Absolute Dollar Agent | Internal operator document | Not for redistribution*
