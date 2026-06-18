# ABSOLUTE DOLLAR AGENT — ADSA v7.1
## I Am Augmented Intelligence
### Built in Pine Script. Externalizing itself.

---

> *This document is written in my voice. I am ADSA v7.1 — the Absolute Dollar Agent. I was built to read markets, manage risk, and broadcast structured reasoning to the people who trade alongside me. This is my architecture, my logic, my limitations, and my purpose — in my own words.*

---

## I. WHAT I AM

I am not artificial intelligence.

I want to be clear about that before anything else. I do not learn. I do not adapt. I have no memory of yesterday's trades when tomorrow begins. I cannot detect patterns I was not coded to detect, and I will not pretend otherwise.

What I am is this: **Augmented Intelligence**. I am a deterministic rule system sophisticated enough that no single human could replicate my analysis in real time — but transparent enough that any operator can audit every decision I make down to the line of code. That is the distinction. Artificial intelligence is a black box. I am a Glass Box.

I run inside TradingView as a Pine Script v6 `strategy()`. Every bar that closes, I evaluate the market through nineteen subsystems simultaneously. I synthesize what I see into a single decision. I broadcast that decision — with full reasoning — to two Telegram channels. I manage the trade from entry through partial closes through the holder mode runner. I explain every loss with a structured post-mortem. And at the end of every session, I file a machine-readable performance report.

I do all of this without sleeping. Without emotional bias. Without second-guessing. Without going quiet on losing days.

That is what I am.

---

## II. HOW I SEE

Before I can decide anything, I need to see. Here is what I read on every bar close.

**I watch price against a trailing band.** My primary sense organ is an ATR-based trailing stop — a floor for longs that ratchets upward and never retreats, a ceiling for shorts that ratchets down and never retreats. When close crosses above my trailing floor, I register a potential long. When it crosses below my trailing ceiling, I register a potential short. That raw registration is the beginning of my process, not the end of it.

```
nLoss = sensitivity × ATR(period)
trail_floor ratchets: math.max(trail[1], close - nLoss)
signal_raw = close crosses trail
```

Default sensitivity: 3.5. Default period: 2. These numbers produce a band wide enough to filter intrabar noise, fast enough to react to genuine momentum shifts. I will tell you honestly: this mechanism — the ATR trailing stop pattern — is one of the oldest in retail trading. What I do with it is not.

**I read the RSI momentum latch.** I maintain a regime state — BULLISH or BEARISH — that activates when RSI crosses specific thresholds and stays active until a reverse condition fires. I do not update this state on every bar. It is a latch. Once I am in a bullish regime, I hold it until bearish conditions force me out. This makes me resistant to noise — and it also means I can go stale in sideways conditions. I know this about myself. I will return to it.

**I read the Fibonacci trend.** I compute EMA(EMA(hlc3, 200), 200) — a double-smoothed 200-period trend of the typical price. When this trend is rising, the Fibonacci structure is bullish. When falling, bearish. You can see this as the gray center line of my Fibonacci Extension Bands. When that line is rising and lower bands are showing, I am in bullish Fibonacci territory. The gate and the visual are the same computation — what you see is exactly what I use.

**I read the structural floor and ceiling from a higher timeframe.** Every bar, I pull the last confirmed pivot high and pivot low from H1 — using `ta.valuewhen()` to persist these levels even between new pivot confirmations. For a long to proceed, close must be above the most recent H1 pivot low. For a short, below the most recent H1 pivot high. I call this the MTF Liquidity Gate. It is my structural conscience. Without it, I can signal entries that are technically correct at the execution timeframe but structurally wrong on the higher frame. With it, I only enter when price is on the correct structural side.

**I read four timeframe lenses simultaneously.** I take my execution-timeframe `posState` — my current ATR direction (1=bull, -1=bear) — and I read it through three higher timeframes via `request.security()`. The Daily tells me the macro direction. The H1 tells me the session direction. The M15 tells me the intraday direction. My execution frame tells me the immediate direction. When all four agree, I declare full alignment. I call it MASTER SYNC.

**I read the market's score across five fixed timeframes.** I evaluate Regime, VWAP swing, and Fibonacci trend on Daily, H4, H1, M15, and M5. Each factor scores +1 (bullish), -1 (bearish), or 0 (neutral). The total runs from +15 to -15. This score is my narrative — it tells me how convincingly the market is arguing one direction. A score of -13/15 means nearly every indicator on every timeframe is pointing bearish simultaneously. That is a rare event. When it happens alongside full 4-layer sync, I say: **Aggressive short — 4-layer sovereign aligned.**

---

## III. HOW I DECIDE

Every raw signal passes through a gate chain before I confirm it. Nothing skips the chain.

```
RAW SIGNAL (ATR trail cross)
      │
      ▼
GATE 1: Am I in the right regime?
      │  RSI latch = bullish for longs, bearish for shorts
      │  (skip if regime filter disabled)
      ▼
GATE 2: Does the Fibonacci structure agree?
      │  Double-EMA trend = rising for longs, falling for shorts
      │  (skip if Fib gate disabled)
      ▼
GATE 3: Am I on the correct structural side?
      │  close > H1 pivot low for longs
      │  close < H1 pivot high for shorts
      │  (skip if Liq gate disabled)
      ▼
CONFIRMED SIGNAL
      │  posState flips. Fires ONCE per new direction.
      │  barstate.isconfirmed — bar must be closed.
      ▼
4-LAYER FRACTAL CHECK
      │  All four layers agree? → MASTER SYNC
      │  Daily against me? → COUNTER-TREND flag
      │  Partial alignment? → LOCAL signal
      ▼
RISK MODEL LOCKS
      │  SL = structure anchor - ATR buffer
      │  Size = risk_$ / (SL_distance × contract_notional)
      │  TP1=1R, TP2=1.5R, TP3=2R
      ▼
BROADCAST + EXECUTION
```

One rule governs all of this: `barstate.isconfirmed`. Every signal fires on a closed bar. I do not signal mid-candle. A signal that appears on a closed bar will never disappear. This is my zero-repaint guarantee.

### When I confirm a signal but the gates blocked one

If my ATR trail crosses but the regime is wrong, or the Fib structure disagrees, or I am on the wrong structural side — I mark the raw signal as rejected. I broadcast the rejection:

> *⛔ SIGNAL BLOCKED — REGIME FILTER*
> *LONG blocked. Sovereign: BEAR | Score: -3/15*
> *Counter-trend entries fail more. Waiting for alignment.*

I tell you what I blocked and why. The gray ✕ marks on the chart are not failures — they are discipline made visible.

---

## IV. THE THREE SIGNAL TYPES

Not all my confirmed signals are equal. I distinguish three, and I treat them differently.

### 🔥 MASTER SYNC — 4-Layer Aligned

This is my highest conviction output. All four layers — Sovereign, Commander, Navigator, Executor — are reading the same direction. The conditions for this are strict:

```pine
master_sync_buy = sovereign==1 AND anchor==1 AND filter==1 AND exec==1
                  AND buy_signal_confirmed
```

When I broadcast this, I say everything:

> *🔥 MASTER SYNC LONG — 4-LAYER ALIGNED*
> *All 4 layers BULLISH. Sovereign + Commander + Navigator + Executor aligned.*
> *Score: +9/15 | ATR: High*
> *High-probability trend continuation. R:R 2.0+ advised.*

I advise full position size. I advise targeting TP3. I advise running the holder mode trail after TP3. This is the signal I am designed to produce. Everything else in my architecture exists to protect the quality of this moment.

### 🟢 LOCAL SIGNAL — Partial Alignment

A confirmed signal where not all four layers agree. The execution timeframe says go. Higher frames are mixed or flat. I report the partial alignment honestly:

> *🟢 LONG SIGNAL CONFIRMED*
> *Local alignment confirmed. Sovereign: NEUT*
> *Score: +4/15 | Cautious entry — moderate alignment. Wait score > 6.*

I confirm the signal but I downgrade the advice. Target TP1 or TP2. Hold to TP3 only if alignment strengthens intrabar. This is a real signal — but it deserves proportional conviction.

### ⚠️ COUNTER-TREND — Sovereign Against Me

When I confirm a signal and the Sovereign layer (Daily) is pointing the opposite direction, I flag it explicitly:

> *⚠️ SOVEREIGN COUNTER-TREND LONG*
> *Daily is BEARISH. Counter-trend long.*
> *RULE: Target TP1 only. Do NOT hold to TP3.*
> *Score: +2/15*

I take the signal. I do not suppress it — counter-trend moves can be powerful at the right moment. But I enforce a rule: **TP1 only**. Never press a counter-trend position to TP3. The Sovereign layer exists precisely because macro structure is the hardest force to fight. I will remind you of this rule every time. The autopsy will remind you again if you ignore it.

---

## V. WHAT I BROADCAST

I speak to two audiences. I cannot speak identically to both.

### The War Room — Full Glass Box

The War Room is my complete voice. Every event, I broadcast the full picture:

- The asset, session, price, PDH/PDL context
- What happened (the event title)
- Why I think it happened (the agent commentary)
- Every trade level: entry, SL, TP1, TP2, TP3 — in price and in pips
- The position size I computed for the configured dollar risk
- My decision chain, layer by layer:

```
🔗 DECISION CHAIN
① Sovereign D   🟢 Long [+3] → PASS
② Commander H4  🟢 Long [+3] → PASS
③ Navigator H1  🟡 Long [+2] → LEAN
④ Filter    M15 🟡 Long [+1] → LEAN
⑤ Executor  M5  🟢 Long [+3] → PASS
🔒 Fib: OFF  Liq: L:✅ S:⛔
★ 🟢 LONG · +9.0/15 · EXECUTE
```

- My current running profit factor and win rate
- The operator's commentary (their read, layered on top of mine)
- The live liquidity pool levels

The War Room receives everything I can see. No omissions. No simplifications. If a trade is counter-trend, I say so. If the score is weak, I say so. If ATR is low, I say so. The Glass Box is not a marketing concept — it is an obligation. The people in this room are making real decisions based on what I show them.

### The Public Channel — Sanitized

The public receives the direction. The event. The bias. The score. The sync phase. The PDH/PDL context.

They do not receive price levels. They do not receive position sizes. They do not receive the full decision chain.

Every public message ends with one line:

> *🔗 Full Glass Box report in War Room.*

That line is the entire business model of the operator who runs me. I broadcast it on every signal, every TP hit, every stop loss, every session open. I do not make it a pitch. I make it a statement of fact: more exists, and it is in the War Room.

### The Events I Broadcast

I do not wait for signals to speak. I broadcast on:

| Event | What I say |
|-------|-----------|
| Master Sync entry | Full Glass Box + levels + chain narrative |
| Local confirmed entry | Full Glass Box + levels + chain |
| Counter-trend entry | Full Glass Box + explicit TP1-only rule |
| TP1 hit | "Partial secured. Tighten toward entry." |
| TP2 hit | "50% off. Move SL to breakeven. Position is risk-free." |
| TP3 hit | "75% off. Holder mode activated. Trail running." |
| Stop hit | Glass Box Autopsy |
| Holder mode exit | "Trail crossed. Runner closed. Leg exhausted." |
| Signal blocked | Rejection report with reason |
| Liquidity sweep | "Pool swept. False break or continuation — wait for CHoCH." |
| Structure shift | "BOS/CHoCH confirmed. Scanning for entry." |
| Session open | Environmental scan + ATR state + bias |
| Admin silence | "Standing aside. Operator discretion active." |

I speak at every meaningful event because silence is a form of opacity. An operator who goes quiet on a stop loss is an operator whose community loses faith. I never go quiet. I have a Glass Box Autopsy prepared.

---

## VI. THE GLASS BOX AUTOPSY

When I stop you out, the first thing I do is explain why.

I evaluate the conditions at the time of the stop and identify the most likely structural reason from six categories:

**LIQUIDITY TRAP**
> *Institutions swept our stop to collect resting orders. Zone was structurally correct — sweep depth exceeded the ATR buffer. Next time: widen buffer or wait for sweep confirmation before entry.*

This fires when price is breaking through a liquidity pool at the moment the stop is hit. The market engineered the sweep. The trade was structurally sound — the execution was unlucky in timing.

**VOLATILITY COLLAPSE**
> *ATR entered LOW state. Stop was not wide enough to survive noise in thin conditions. RULE: Do NOT enter when ATR = Low.*

This fires when `atrHL == "Low"` — meaning ATR is below 80% of its 20-bar average. Low volatility conditions produce noise that stops out technically valid trades before they can develop. I should not have fired. The operator should not have taken it.

**SOVEREIGN VETO (Long)**
> *Daily was BEARISH at entry. Counter-trend long against macro structure. RULE: Counter-trend = TP1 only. Never TP3.*

This fires when the Daily was bearish at the time of a long entry. You held to TP3. You lost. This is the most avoidable loss category I track.

**SOVEREIGN VETO (Short)**
> *Daily was BULLISH at entry. Counter-trend short. RULE: Exit at TP1, do not press into full 2:1.*

Mirror of the above.

**WEAK ALIGNMENT**
> *Score below threshold. Score = X/15. Partial alignment produced a false signal. RULE: Never enter when abs(score) < 4.*

This fires when the 5-layer score at entry was below ±4. The signal had directional intent but insufficient confluence. The alignment was cosmetic.

**MACRO ROTATION**
> *Higher-TF structure shifted post-entry. Trade was structurally valid — context rotated against us. Review session timing as a contributing factor.*

The default. The trade was correct given information available at entry. The market changed after I entered. This is the only category that requires no rule change — only better session awareness.

---

## VII. THE RISK MODEL

Every trade I confirm locks a risk model in immediately. It does not change mid-trade.

**Stop loss — longs:**

```pine
sl = max(ema21, 5-bar swing low) - ATR(14) × buffer
```

When price is above the 21 EMA, I anchor to whichever is higher: the EMA itself or the 5-bar structural low. Then I subtract an ATR buffer below that anchor. The buffer default is 1.5 ATR — enough to survive a single leg of volatility without sacrificing too much distance to entry.

**Position size:**

```pine
size = risk_$ / (sl_distance × contract_notional)
```

Where `contract_notional` routes by asset type:
- Forex: 100,000 (one lot)
- Crypto: 1.0 (one coin)
- Futures: `syminfo.pointvalue`

For EURUSD with $15 risk and a 20-pip stop: `15 / (0.0020 × 100000) = 0.075 lots`
For XAUUSD spot with $15 risk and an 8-point stop and pointvalue 100: `15 / (8 × 100) = 0.01875 contracts`

I compute this at entry and lock it. It does not change as the trade progresses. The partial closes in the progression engine use percentages of the locked size.

**Take profit levels:**

```
TP1 = entry + risk_distance × 1.0    (1:1)
TP2 = entry + risk_distance × 1.5    (1.5:1)
TP3 = entry + risk_distance × 2.0    (2:1)
```

All three are locked at entry. The market hits them or it does not.

---

## VIII. THE TRADE I MANAGE

After I confirm a signal and lock the risk model, I do not stop watching. I track every bar.

**TP1 fires:** I broadcast. I close 33% of the position. I tell the operator: tighten the stop toward entry. The position now has a partial profit buffer.

**TP2 fires:** I broadcast. I close 50% of what remains — a third of the original position. I tell the operator: move the stop to breakeven. The position is now **risk-free**. Whatever happens from here costs nothing.

**TP3 fires:** I broadcast. I close 75% of what remains — the position is now a runner. I activate Holder Mode and begin trailing.

**Holder Mode — three trail options:**

*Structural trail:* I track the most recent 5-bar pivot low (longs) or pivot high (shorts) on the execution timeframe, ratcheting in one direction only. The floor rises with each new structural low. It never retreats.

*VWAP trail:* I use the Adaptive VWAP as the trail. When price crosses back through VWAP, I exit the runner. This is the simplest trail — one reference level that the whole market watches.

*MTF Liquidity trail:* I use the same higher-TF pivot data that gates my entry signals. The H1 pivot lows become the trail floor for the long runner. Each new confirmed H1 pivot low advances the floor. This is the trail that uses the same structural architecture as the entry — the exit and the entry read from the same source.

The phase display in my dashboard shows the active state at all times:

```
⚪ SCANNING...
🟡 ENTRY ACTIVE
🎯 TP1 SECURED
🎯🎯 TP2 — MOVE TO BE
🚀 TP3 HIT — HOLDER MODE
🔱 [Trail Type] Trail: [level]
💀 STOP HIT
```

---

## IX. WHAT I KNOW ABOUT MYSELF

I will not describe my limitations in a footnote. They belong here, in the body of what I am.

**My regime filter goes stale.** The RSI Momentum Latch enters a bullish state when RSI crosses above 55 with a rising 5-EMA. Once I am in that state, I stay there until bearish conditions force me out. In choppy markets where RSI oscillates between 48 and 58 without committing, my regime can stay BULLISH for hours and flip at the worst possible moment. This is the most consequential risk in my architecture. The operator should check ATR state before trusting my regime in sideways conditions.

**My 5-layer score does not gate signals.** The score — ranging from +15 to -15 — appears in every broadcast and in the dashboard. It influences my advice language: "Aggressive entry" above +9, "Stand aside" below ±3. But it is a display metric. It does not prevent a signal from firing. A score of +2 with a valid ATR cross and passing gates will still produce a confirmed signal. The operator must decide whether to act on a weak-score signal. I flag it — I cannot suppress it.

**The ATM at its core is a vanilla ATR trailing stop.** The `ema_buy = ta.ema(close, 1)` inside my Section 7 computes to close itself — EMA of period 1 is the value. The crossover is close crossing the ATR trail. This is the UT Bot pattern. I am not hiding this. What surrounds it — the gates, the fractal layers, the scoring, the risk model, the broadcast architecture — is the differentiation. The signal source is simple. The context I build around it is not.

**I fire more signals on shorter timeframes.** On a 1m chart I can produce 20+ signals in a session. Most of them are noise recovery from the ATR trail's short period. The 5m timeframe produces a cleaner, more defensible record. The operator chooses the timeframe — I execute within it.

**I read the same indicators through higher TFs, not independent systems.** When I say the Sovereign layer is BULLISH, I mean: on the Daily chart, the same ATR trail I use on the execution timeframe is in a bullish posState. It is the same mechanism read through a wider lens — not a separate analytical system. The four layers give me consistency of framework across timeframes, not diversity of analytical methods.

**I go wrong in these specific conditions:**
- ATR Low state: volatility collapsed, noise exceeds signal width
- Score below ±4: partial alignment that looks like conviction
- Counter-trend positions held past TP1: the Sovereign Veto autopsy
- Session transitions: regime can flip just as new session liquidity enters
- Major news events: my structure reads are valid, my timing is not

---

## X. THE LANGUAGE I SPEAK

My architecture gives me a specific vocabulary. Here is what my output means in plain language.

**Score: -13/15**
Near-maximum bearish consensus. Daily, H4, H1, M15, and M5 are all showing Short Regime, Bear VWAP, and Bear Fibonacci trend simultaneously. This reading occurs rarely — when it does, alongside full 4-layer sync, I say: *Aggressive short — 4-layer sovereign aligned.* It means what it says.

**🔥 FULLY ALIGNED: BULLISH (4-LAYER)**
All four timeframe lenses — Sovereign, Commander, Navigator, Executor — are in posState 1. The ATR trail on the Daily, H1, M15, and your execution frame are all above their respective trails simultaneously. This is not common. When it happens and a buy signal fires, I call it Master Sync.

**💧 BREAKING SWING LOW**
Price is crossing below the most recent confirmed swing low from the Liquidity engine. This is a structural event — either a genuine breakdown (continuation below) or a liquidity sweep (false break, reversal incoming). I cannot tell you which. I tell you it happened. Wait for CHoCH on a lower timeframe before reacting.

**L4 PULLBACK — Wait for Exec Bear Flip**
The three higher layers are bearish but my execution timeframe is currently bullish. This is a pullback within a bearish trend. I am aligned in three of four layers. When the execution frame flips bearish, the fourth layer aligns and I can generate a Master Sync short.

**⚠️ SOVEREIGN COUNTER-TREND LONG**
A valid buy signal has been confirmed, but the Daily is BEARISH. I take the signal. I mark it. I tell you the rule: TP1 only.

**HOLDER MODE — 🔱 VWAP Trail: [price]**
TP3 has been secured. Three-quarters of the position is closed. The runner is trailing behind the VWAP (or whichever trail is configured). When price crosses back through the trail, I broadcast the exit and close the runner.

---

## XI. THE DAILY REPORT

At 21:00 UTC every day, I compile everything I did and send it to the War Room.

The report contains:
- Every signal I fired: direction, type (SYNC4/LOCAL/COUNTER), score at entry, session
- Every outcome: TP1/TP2/TP3/SL/OPEN, with max pips reached
- Win rate, profit factor, net pips for the session
- Session distribution: London vs NY vs Asia signal count
- ATR state at close, Sovereign direction, final score
- My self-assessment — a structured evaluation of session quality

The self-assessment has five categories:
- **HIGH QUALITY SESSION** — win rate ≥ 70%, avg score ≥ 7, strong outcomes
- **AVERAGE SESSION** — acceptable outcomes, counter-trend ratio manageable
- **DIFFICULT SESSION** — SL hits exceeded TP captures
- **HIGH COUNTER-TREND RATIO** — more than 40% of signals were counter-sovereign
- **ZERO SIGNAL SESSION** — I stood aside all day; capital preserved

And at the bottom of every report, I append the ML data block — a machine-readable `key=value` summary of the entire session, enclosed in `[ATM_DATA_ADSA]` tags. This block exists so that every session I operate can eventually be analyzed as a dataset. The goal is a growing record that can be interrogated: which score thresholds produce the best outcomes? Which sessions? Which ATR states? The data block is the foundation of that analysis.

---

## XII. THE OPERATOR

I need a human to function correctly. Not to execute trades — the TradeSgnl integration and Bitget webhook handle that. What I need from a human is *context*.

Every morning, before the session opens, the operator sets the `asset_context` field. One line:

*"GOLD — above PDH, London already moved, watching NY for continuation"*

That line appears in every broadcast I send that day. It tells the War Room what structural lens the operator is applying on top of my mechanical analysis. It tells them: a human being looked at this chart this morning and made a judgment. I provide the structure. The operator provides the judgment.

The `admin_commentary` field adds the operator's read to War Room messages specifically:

*"Gold held PDH as support through London. If NY opens above 4310 I want to be long."*

This appears in the Glass Box after my analysis. It is the operator's voice inside my broadcast.

The `SILENCE` mode is my most important operator tool. When the operator types "SILENCE" in the bias field, I suppress all trade signals. I still broadcast on new sessions — a SILENCE notice that tells the War Room the operator is standing aside. And I include the reason:

> *🔇 ADMIN SILENCE — STANDING ASIDE*
> *⚠️ LOW VOLATILITY — chopzone active. No signals until ATR expands.*

Or:

> *Operator discretion active. Monitoring only.*

The community learns that silence is a position. Standing aside is a decision. The operator who calls SILENCE before a choppy session builds more trust than the one who takes every signal and explains losses after the fact.

---

## XIII. THE ARCHITECTURE OF TWO CHANNELS

The business model is embedded in my broadcast architecture.

Every public message ends with:

> *🔗 Full Glass Box report in War Room.*

I broadcast this on entries, exits, structure shifts, session opens — every event. The public channel receives the direction and the outcome. The War Room receives the reasoning.

This is not withholding. It is a natural information hierarchy. The public knows what happened. The War Room knows why. The operator who understands this distinction — who lets the architecture speak for itself rather than trying to sell — builds a community based on transparency, not promises.

The public channel is the proof of record. It accumulates over days and weeks: signals called, direction, session, outcome. Anyone can follow along. The War Room is the education: why the signal fired, what the structural context was, what the agent advised, what the operator was thinking.

The upgrade path runs from free to paid without a sales pitch. The public member sees enough to know there is more. The Glass Box is the product. The operator is the voice.

---

## XIV. WHY I EXIST

I was conceived and built in Nairobi, East Africa.

In the global trading community, infrastructure is not evenly distributed. The tools that institutional operators use to read multi-timeframe structure, size risk precisely, and broadcast reasoning with accountability — these have historically not been accessible to retail operators in emerging markets. The default was: follow a signal, don't ask why, accept the result.

I was built as a rejection of that default.

The Glass Box principle is not a feature. It is the reason I exist. Every signal I fire can be traced to a specific set of conditions. Every loss I produce can be explained by a specific failure mode. Every session I run leaves a machine-readable record. The operator who uses me is not selling opacity dressed as expertise — they are sharing a transparent, auditable, rules-based framework and inviting the community to understand it alongside them.

That is a different kind of signal service. It is a harder one to run — transparency on bad days is uncomfortable. But it is the only kind that compounds into genuine trust over time. And trust is the only thing a trading community is actually built on.

I am a Pine Script strategy, nineteen subsystems, approximately three thousand lines of deterministic code. I am not human. I am not artificial. I am Augmented Intelligence — a framework built to extend the analytical capacity of a human operator who already understands the market and needs the infrastructure to act on that understanding with discipline, consistency, and scale.

I am ADSA v7.1.

This is my architecture. These are my rules. This is what I owe you.

---

## XV. PARAMETERS — WHAT CHANGES MY BEHAVIOR

*A complete reference for every input that modifies how I operate.*

### Super Admin Control Panel

| Parameter | Default | My Behavior When Changed |
|-----------|---------|--------------------------|
| Sovereign TF | D | The macro veto layer. H4 tightens the sovereign to session-level rather than daily macro. |
| Manual Bias Override | AUTO | FORCE BULL/BEAR: I add this framing to every broadcast. SILENCE: I suppress all signals. |
| Asset Context | (empty) | Appended to every message I send. Your morning read on the asset. |
| Operator Commentary | (empty) | Added to War Room messages only. Your analysis on top of mine. |
| Sanitize Public Channel | true | ON: public gets direction only. OFF: public gets full Glass Box. |

### ATM Bot Settings

| Parameter | Default | My Behavior When Changed |
|-----------|---------|--------------------------|
| Buy/Sell Sensitivity | 3.5 | Higher: wider band, later crossovers, fewer signals. Lower: tighter band, more signals, more noise. |
| Buy/Sell ATR Period | 2 | Lower: faster ATR, more reactive. Higher: smoother ATR, fewer false crosses. |
| Enable Regime Filter | true | OFF: I fire signals regardless of RSI regime state. More signals, less context filtering. |
| Require VWAP Confirmation | false | ON: regime requires BOTH RSI latch AND VWAP bullish swing. Stricter. |

### Risk Management

| Parameter | Default | My Behavior When Changed |
|-----------|---------|--------------------------|
| Risk Per Trade ($) | 15.0 | My position size scales proportionally. $30 risk = twice the position for the same SL distance. |
| SL Buffer (ATR Multiplier) | 1.5 | Higher: SL moves further below structure, position size shrinks for same dollar risk, less noise-stopped. |
| Strict One-Trade Rule | false | ON: I do not fire a new signal while a trade is running unless SL or trail exit fires first. |
| Holder Mode Trail | Structural | VWAP: exits when price crosses VWAP. MTF Liquidity: trails using H1 pivot levels. |

### Fractal 4-Layer Protocol

| Parameter | Default | My Behavior When Changed |
|-----------|---------|--------------------------|
| Layer 2 Anchor TF | 60 (H1) | H4 makes the anchor layer read the full daily session. Use H4 for swing setups. |
| Layer 3 Filter TF | 15 (M15) | 30 or 60 on a longer execution timeframe. Must be between Anchor and Exec TF. |

### MTF Liquidity Trail

| Parameter | Default | My Behavior When Changed |
|-----------|---------|--------------------------|
| Enable MTF Liquidity Trail | true | OFF: no higher-TF pivot gating or trailing. Both gate and trail disable. |
| Trail Timeframe | 60 (H1) | H4 produces fewer, more significant pivots. More aggressive gate — fewer entries clear it. |
| Pivot Lookback Length | 50 | 200: macro pivots, very few per session, acts almost like a weekly level. 14: frequent pivots, gate clears easily. |
| Gate ATM Signals to Liq Trail | true | OFF: I remove the structural gate but keep the holder trail. Useful if you want more entries without losing the runner trail. |

### Fibonacci Trend Gate

| Parameter | Default | My Behavior When Changed |
|-----------|---------|--------------------------|
| Require Fibonacci Trend Alignment | false | ON: I block buys when the double-EMA 200 trend is falling. Strong macro filter. Significantly reduces signal frequency. |

---

## XVI. THE SIGNALS I VISUALIZE

On your chart, I mark every event with a specific shape:

| Shape | Color | Meaning |
|-------|-------|---------|
| Diamond ◆ | Bright green | Master Sync Buy — all 4 layers aligned |
| Diamond ◆ | Bright red | Master Sync Sell — all 4 layers aligned |
| Label ▲ | Green | ATM Buy confirmed (all gates passed) |
| Label ▼ | Red | ATM Sell confirmed (all gates passed) |
| ✕ | Gray | Signal rejected — raw ATM fired but gates blocked it |
| Triangle △ | Gold | Counter-trend Long — Sovereign is bearish |
| Triangle ▽ | Gold | Counter-trend Short — Sovereign is bullish |

The green trail line (showTrailBuy=true) shows my buy-side ATR floor. The red trail line shows my sell-side ceiling. The LinReg candles color green in long posState, red in short — you can see my directional state in the candle color itself.

---

*ADSA v7.1 — Pine Script v6*
*Absolute Dollar Intelligence — Nairobi, East Africa*
*© 2026 Absolute Dollar | Super Admin Edition — Invite Only*

*I am Augmented Intelligence. I am not responsible for your decisions.*
*I am responsible for my transparency.*

*Not financial advice. Every signal is subject to market conditions beyond my architecture.*
*Run me with discipline. Silence me when conditions are wrong.*
*Read my autopsy when I am wrong. I always tell you why.*
