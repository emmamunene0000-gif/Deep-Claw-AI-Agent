# DEEP CLAW — README / NORTH STAR
## "The Claw": A Synthetic Trading Intelligence (Tron + Jarvis)

> **Goal Zero, never lose sight of it:** Convert skill + time + capital into income, via
> probabilistic speculation with positive expectancy, intraday liquidity-extraction
> scalping, and compounding wins — executed by a self-aware system that gets *better*
> the longer it runs.

This document is the synthesis of everything discussed: the ADSA v7/v8 Pine Script
lineage, the v8 failure post-mortem, the architecture addendum, and the episodic-memory/
chain-logic insight. It is the answer to "what are we actually building, and why."

---

## 1. THE ONE-SENTENCE DEFINITION

**Deep Claw is an event-sourced, self-narrating trading organism**: price ticks become
*episodes*, episodes accumulate into a *chain* (memory), the chain is read by both a
learned numeric model (confidence/sizing) and a language model (Claude, narrative
judgment), and the resulting trade instructions are executed broker-agnostically across
Deriv, Bybit, and MT5 — with every decision, win, and loss feeding back into the chain so
the system's judgment compounds along with its capital.

If a single human had to do this job, they'd be: a chart analyst doing top-down
multi-timeframe reads, a risk manager sizing positions against a capital base, a
journal-keeper writing down what happened and why, and a portfolio manager deciding what
to do differently tomorrow. Deep Claw is all four of those roles running continuously,
never sleeping, never forgetting.

---

## 2. THE TRON / JARVIS SPLIT (what each "half" actually is)

```
TRON  = the nervous system            JARVIS = the mind
──────────────────────────            ──────────────────
Lives in the price grid.              Thinks like a prop-desk manager.
Breathes every OHLCV tick from        Reads the chain, not a snapshot.
Deriv / Bybit / MT5.                  Decides: approve / reject / modify.
Normalizes 3 brokers into ONE         Sizes capital with positive
price reality.                        expectancy in mind (fractional
Routes execution back out,            Kelly, R-multiple distributions).
broker-specific, zero leakage         Writes the story of the session —
of wire formats upstream.             for the dashboard, Telegram, and
                                       its own future self.
```

Neither half is "the AI." **The combination is the AI.** Tron without Jarvis is just a
data feed. Jarvis without Tron has nothing to perceive or act on. The synthetic
intelligence *is* the loop between them, mediated by the chain.

---

## 3. THE CORE INSIGHT THAT CHANGES EVERYTHING: CHAIN, NOT TREE

Every prior version (ADSA v7, v8, ATM Protocol) represented market context as a **tree**
— a cross-sectional snapshot of 5 timeframes at the current instant. This is a
*photograph*. It answers "what is true right now" but not "how did we get here" or "what
does this remind us of."

Deep Claw represents market context as a **chain (episode stream)** — an append-only,
chronological log of state-transition events:

```
09:14  Session: Tokyo close. ATR: Low. Standing aside.
09:32  London open. Buy-side liquidity swept at 1.0980.
09:41  M15 CHoCH confirmed bullish.
10:02  M5 UT Bot flip + Confidence 68% -> Signal fired (LOCAL, not SYNC4, H4 still neutral)
10:14  TP1 hit (+1R). SL moved to breakeven.
10:29  TP2 hit (+1.5R). Holder mode armed.
11:05  Structural trail crossed. Trade closed +2.3R. Episode archived.
```

This single data structure — the **EpisodeStream** — is the spine of the whole system,
and it serves **four consumers from one source**:

1. **Dashboard** — renders as a live session timeline (Tron's "I can see the whole grid")
2. **Telegram** — renders as the War Room narrative (chain trace, not tree table)
3. **Claude qualification call** — rendered as prose context: "here's the story so far,
   what's your read?" — this is what makes Claude's role *narrative judgment*, not
   table-reading
4. **Training journal** — the persisted episode stream *is* the literal "episodic
   memory of price" — queryable for "what happened last time we saw this setup?"

Tree formats don't disappear — `MarketState(t)` snapshots still exist as the numeric
feature vector for the ML layer. But the **chain is what Cognition reasons over**, and
the **snapshot is what the chain's links point to** for hard numbers.

---

## 4. THE THREE LAYERS + THE SPINE

```
+--------------+     +-----------------------+     +--------------+
|  PERCEPTION   |---->|      COGNITION         |---->|    ACTION     |
|  (Tron's      |     |      (Jarvis)          |     |  (broker-     |
|   senses)     |     |                        |     |   agnostic    |
|               |     |                        |     |   execution)  |
| MarketState   |     | Signal Generators      |     |               |
| snapshots +   |     |  (pure functions,      |     | BrokerAdapter |
| EpisodeStream |     |   independent)         |     | protocol:     |
| entries, per  |     |                        |     |  open/modify/ |
| symbol/bar,   |     | Chain Reasoning        |     |  partial_close|
| all TFs       |     |  (resolves episode     |     |  /close/pnl   |
|               |     |   chain -> verdict)    |     |               |
|               |     |                        |     | Deriv /       |
|               |     | Confidence Engine      |     | Bybit / MT5   |
|               |     |  (v1: hand-tuned;      |     | adapters --   |
|               |     |   v2: learned)         |     | zero trading  |
|               |     |                        |     | logic, pure   |
|               |     | Position State         |     | I/O           |
|               |     |  Machine                |     |               |
|               |     |  (ONE source of truth, |     |               |
|               |     |   zero orphans)         |     |               |
+--------------+     +-----------------------+     +--------------+
        |                       |                          |
        +-----------------------+--------------------------+
                                 |
                                 v
                    +-------------------------+
                    |   EPISODE STREAM /        |
                    |   JOURNAL (the spine)     |
                    |                           |
                    |  Append-only event log.   |
                    |  Every signal candidate    |
                    |  (accepted AND shadow-     |
                    |  blocked, with reasons),   |
                    |  every state transition,   |
                    |  every closed trade's      |
                    |  MFE/MAE/R-multiple.       |
                    |                           |
                    |  = episodic memory        |
                    |  = chain narrative source  |
                    |  = ML training data        |
                    +-------------------------+
```

Data flows one way: Perception -> Cognition -> Action. Cognition never reaches into
Perception's internals; Action never reaches into Cognition's state. Broker-specific wire
formats (the thing that broke v8 with TradeSgnl/MT5) live *only* inside Action adapters.

---

## 5. WHAT EACH LAYER ACTUALLY CONTAINS

### Perception (`perception/`)
- All indicator computations from the ADSA/ATM lineage, ported as **pure functions** on
  a `NormalizedCandleBus` (no `request.security`, no repaint risk): liquidity trail
  (M5/M15/H1/exec), adaptive VWAP, volume profile (POC/VAH/VAL), RSI regime, Fib trend,
  SMC structure (BOS/CHoCH/OB/FVG/EQH-EQL), PDH/PDL, ATR regime, session detection,
  5-TF EMA grid.
- Emits **two things per bar**: a `MarketState` snapshot (numeric feature vector for ML)
  and zero-or-more `Episode` records (when something *changed* — regime flip, sweep,
  structure break, session change).

### Cognition (`cognition/`)
- **Signal generators** — independent, stateless, pure functions
  `MarketState -> SignalCandidate | None`. Each candidate carries `{source, direction,
  confidence_inputs, proposed_sl, proposed_tp1-3, timestamp, symbol}`. Sources: UT Bot
  trail-flip, Smart RSI extreme, liquidity zone break/retest, structure shift.
- **Chain Reasoning Engine** — walks the recent `EpisodeStream` + the per-TF
  `MarketState`s, resolves into a `ChainVerdict`: verdict (SYNC4/COUNTER_TREND/LOCAL/
  REJECTED), confidence, restrictions (TP1_ONLY, NO_HOLDER_MODE), risk/SL modifiers,
  causal trace (human-readable), and an episodic note (pattern match against history).
- **Confidence Engine** — `confidence_v1.py`: the 6-factor weighted score from v8,
  generalized to `(MarketState, weights) -> {bull_confidence, bear_confidence}`. Phase 2:
  `learning/inference.py` implements the same signature with a learned distributional
  model (LightGBM quantile heads -> R-multiple distribution -> confidence). Swappable via
  `USE_ML_CONFIDENCE`.
- **Position State Machine** — THE single owner of trade state. Receives all
  `SignalCandidate`s, applies the `ChainVerdict` and `one_trade_rule`, explicitly
  accepts/rejects every candidate with a logged reason (rejections feed the feature
  store as shadow-blocked data — never silently dropped, never used to mislabel an
  open trade). Runs TP1->TP2->TP3->Holder->exit progression. **Reversal = close existing +
  log P&L + open new** — no orphans, no dead zones from `prevent_reversals`.

### Action (`action/`)
- `BrokerAdapter` protocol: `open_position`, `modify_stop`, `partial_close`,
  `close_position`, `get_live_pnl`.
- `deriv_multiplier.py`, `deriv_vanilla.py`, `bybit_perp.py`, `mt5_cfd.py` — pure I/O
  translators. Asset-routed notional/sizing math lives in Cognition's risk model;
  Action never recomputes it.
- MT5: direct Python bridge (not TradeSgnl webhook strings) — isolates the exact class
  of "syntax issues" that broke v8.

### The Spine (`journal/`, `feature_store/`)
- Append-only `EpisodeStream`, persisted (SQLite to start). This *is* the episodic
  memory. Every signal candidate (accepted or shadow-blocked, with reason), every
  position-state transition, every closed trade's full outcome (entry/exit/MFE/MAE/
  R-multiple/signal source/confidence-at-entry).
- One source -> renders into: dashboard timeline, Telegram chain-narrative, Claude
  qualification-call context, and ML training rows.

---

## 6. THE CLAUDE QUALIFICATION LAYER — WHAT IT'S ACTUALLY FOR

Claude is called at threshold moments (a `SignalCandidate` clears the confidence
threshold and the Position Manager is about to act on it). Its input is **not** a wall
of current indicator values — it's a short rendered narrative from the `EpisodeStream`
(the last ~10-20 episodes) plus the `ChainVerdict` plus the episodic-memory match
("similar setup 3 days ago -> SL hit after 12 pips; consider widening").

Claude's job is the thing LLMs are actually good at: reading a story and giving a
verdict — APPROVE / REJECT / MODIFY, with adjusted size/SL and reasoning. It is the
"junior analyst getting briefed by the chain," not "a calculator double-checking
arithmetic." This is the literal mechanism of *Augmented* Intelligence in the name.

Claude is also called for: SL autopsy narratives (reading the episode chain leading to
a stop-out and generating the lesson), and daily self-assessment (reading the day's
full episode stream and recommending parameter adjustments — these recommendations are
*proposals* logged to the journal, not auto-applied, until the learned model takes over
that role).

---

## 7. RISK & CAPITAL PHILOSOPHY (the "Capital" in Analysis+Capital+Execution)

- **Per-trade risk is a dollar amount**, asset-routed via the contract-notional router
  (the one piece of v6.1/v7 that was unambiguously correct and must be preserved exactly).
- **Confidence is structural, not cosmetic** — it gates entry (below threshold = no
  trade), and scales size (fractional-Kelly-style: higher confidence -> larger size,
  within hard caps).
- **Position sizing formula** (from earlier sizing research):
  `position_size = min(kelly_fraction x equity, 0.02 x equity, daily_loss_budget_remaining / sl_distance, margin_headroom_implied_size)`
- **Counter-trend trades are structurally restricted** (TP1-only, half size,
  no holder mode) — encoded as `ChainVerdict.restrictions`, not left to operator
  discipline.
- **MT5 funded-account constraints** (daily loss budget, max drawdown) are enforced in
  the Position State Machine / risk router, not assumed.

---

## 8. SELF-LEARNING: WHAT "SYNTHETIC INTELLIGENCE AWARE OF ITSELF" MEANS CONCRETELY

Not autonomous parameter mutation on day one. Concretely, in order:

1. **Phase 1 (now):** Hand-tuned confidence weights + rule-based chain restrictions.
   Everything is logged to the `EpisodeStream`/journal — including shadow-blocked
   candidates with *why* they were blocked (confidence too low vs. one-trade-rule vs.
   regime veto — these are different features).
2. **Phase 2:** `learning/` module — outcome labeler (MFE/MAE in R-multiples from the
   journal), distributional model (LightGBM quantile heads) predicting R-multiple
   distributions conditioned on `MarketState` + chain features (including "Nth retest
   today," "regime flips in last hour" — recency/repetition features only available
   because of the episode chain).
3. **Phase 3:** `learning/inference.py` swaps in for `confidence_v1.py` behind the same
   interface (`USE_ML_CONFIDENCE=true`). Sizing becomes fractional-Kelly off the learned
   distribution. Position Manager and Action layers are unchanged — they don't know the
   difference.
4. **Ongoing:** Daily self-assessment (Claude-generated, journal-grounded) becomes the
   review mechanism for whether Phase 2/3 models need retraining, and whether
   hand-coded chain restrictions still reflect reality.

The episode chain is what makes all of this *possible* — without it, "the Nth time this
setup occurred today" doesn't exist as a feature, and the model can only ever be as smart
as a single-bar snapshot.

---

## 9. WHAT WE EXPLICITLY DO NOT PORT FROM v8 (the failure catalog)

| v8 artifact | Why it's excluded |
|---|---|
| `buy_signal_confirmed = UT_Bot OR Smart_RSI` merged into shared `posState`/`locked_*` | Two signal philosophies racing on one mutable state = orphan trades, corrupted labels |
| Orphan-trade "fix" (force-mark open trade as SL on new signal) | A patch for the bug above; with proper signal-candidate separation, nothing to patch |
| `f_format_alert`/`f_format_modify` TradeSgnl string templates | Broker-wire serialization hardcoded into trading logic — isolate entirely inside `action/mt5_cfd.py` or replace with direct MT5 bridge |
| `prevent_reversals` dead-zone | Replaced by "close existing + log P&L + open new" — always responsive |
| Confidence Engine as display-only | Confidence becomes structural: gates entry, scales size, gates holder-mode eligibility |
| Tree narrative as the *only* context format | Tree (snapshot) still feeds the feature vector; chain (episode stream) is what Cognition and Claude reason over |
| `strategy()` position state vs. `posState` vs. `trade_active` (three competing truths) | ONE `PositionStateMachine`, synced with broker, full stop |

---

## 10. WATCHLIST / SCOPE (where this runs)

- **Tier S/A (primary)**: Deriv synthetics (VOLATILITY_75/100/50, STEP_INDEX) and Deriv
  Multipliers on XAUUSD; Bybit perpetuals (BTC/ETH/SOL).
- **Tier B/C**: Deriv forex multipliers, additional Bybit perps, Deriv Vanilla Options
  as a defined-risk "lottery sleeve" (separate allocation %, TBD).
- **Tier D / Atlas funded account**: MT5 CFDs (indices, select equities) — subject to
  funded-account daily-loss-budget clamps in the risk router.
- Execution window emphasis: London-NY overlap (16:00-19:00 GMT+3 / Nairobi) as the
  highest-liquidity, highest-edge window — the chain's session-detection feeds this
  directly (episodes tagged by session).

---

## 11. BUILD SEQUENCING (the order that avoids v8's mistakes)

1. **Perception**: `MarketState` + `EpisodeStream` schema and emission logic (ported
   indicators, on `NormalizedCandleBus`, no `request.security` lookahead patterns).
2. **Cognition - signal generators**: independent, pure, typed (`SignalType` enum with
   per-type risk/SL modifiers baked in from day one — not bolted on later).
3. **Cognition - Chain Reasoning Engine**: resolves `EpisodeStream` + per-TF
   `MarketState` into `ChainVerdict`. This is new vs. all prior Pine versions.
4. **Cognition - Position State Machine**: single source of truth, zero-orphan
   reversal handling, full TP1->TP2->TP3->Holder progression.
5. **Confidence v1**: hand-tuned weights behind the swappable interface.
6. **Action**: broker adapters (Deriv first — already has live connections per Deep
   Claw's current deployment; then Bybit; MT5 last, direct bridge).
7. **Communication**: render `EpisodeStream` -> dashboard timeline + Telegram chain
   narrative + Claude qualification-call context (one renderer, multiple output formats).
8. **Claude integration**: qualification calls, SL autopsy, daily self-assessment —
   all reading from the rendered chain.
9. **Journal/feature store**: formalize once 1-7 are producing real data.
10. **Learning**: outcome labeler -> distributional model -> `inference.py` swap-in.

Steps 1-4 are the load-bearing wall. Everything else — including the Claude calls
that give Deep Claw its "Augmented Intelligence" name — depends on the chain existing
and the position state being trustworthy. Get those right and the rest is, relatively,
plumbing.

---

## 12. THE NORTH STAR, RESTATED

Deep Claw is not a better indicator, and it's not "ChatGPT bolted onto a trading bot."
It's a system that **remembers its own session as a story**, **reasons over that story
top-down like a desk manager**, **sizes capital against a positive-expectancy edge with
discipline a human can't sustain for 12 hours straight**, and **gets measurably smarter
every day because the story it tells itself is also the data it learns from**. Skill +
time + capital -> income — with the skill and time increasingly supplied by the system
itself, and the capital compounding as a result.
