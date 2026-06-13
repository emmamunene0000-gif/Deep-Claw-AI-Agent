# THE CLAW — UNIFIED ARCHITECTURE ADDENDUM
## Lessons from ADSA v8.0 ("Claw Protocol Edition") + Design Principles for the Broker-Agnostic Engine

This document supplements `deep_claw_adsa_cheatsheet.md`. It does **not** ask Claude Code
to port v8.0's Pine logic. Instead it diagnoses *why* the v8.0 merge attempt broke, and
converts the "Tron meets Jarvis" vision into concrete engineering contracts so the Python
build doesn't repeat the same failure mode.

---

## 1. WHAT v8.0 ACTUALLY DELIVERED (keep the ideas, discard the implementation)

| v8.0 Addition | Verdict | Why |
|---|---|---|
| Claw Liquidity Trail (`calcLiqTrail`, MTF M5/M15/H1) | **Keep — as a perception module** | Clean, self-contained ratcheting ATR trail. Good candidate for `perception/liquidity_trail.py`, computed once per TF and exposed as a feature, not wired directly into entry logic. |
| Claw Confidence Engine (6-factor weighted score) | **Keep the *shape*, not the weights** | This is literally a hand-tuned linear model: `score = Σ(weight_i × indicator_i)`. It's the right *interface* (a 0-100% confidence output consumed by sizing/decision logic) but the weights (1.5/1.0/1.0/0.5/0.5/1.0) were operator guesses. This interface is exactly where `learning/inference.py`'s output should plug in later — same signature, learned weights. |
| Smart RSI Extreme Signals (75+/25-, M5-confirmed) | **Keep — as a second, independent signal generator** | But it must NOT be OR'd into the same `posState`/`locked_*` globals as the UT Bot. It's a distinct hypothesis generator. |
| Fib Trend Gate (soft confluence, not hard gate) | **Keep — as a feature, not a gate** | "Adds confluence, does not hard-gate" is the right philosophy — codify it as a feature weight, not an `if` branch. |
| PDH/PDL, tree narrative, live $ P&L, signed net-pips (`dpt_net_pips`), bedist/trdist/trstep | **Keep — data model upgrades** | These are pure additions to the journal/feature schema, orthogonal to the signal-merge problem. Port the *data fields*, not the string-formatting code around them. |
| TradeSgnl `f_format_alert`/`f_format_modify` string templates | **Discard entirely** | This is broker-wire serialization hardcoded as Pine string concatenation. Python execution adapters (per Section 7 of the cheat sheet) replace this completely — no template strings, no `{{placeholder}}` substitution. |
| The `OR`-merge of UT Bot + Smart RSI into `buy_signal_confirmed` | **Discard — root cause of orphan trades** | See Section 2. |
| Orphan-trade patch (Section 16 "FIX") | **Discard — it's a patch for the OR-merge bug** | Once signal sources are properly separated (Section 2), there's nothing to patch. |
| `prevent_reversals` / "Strict One-Trade Rule" | **Keep as a config flag on the Position Manager**, not entangled in signal logic | This is a portfolio-level constraint, not a signal-generation concern. |

---

## 2. ROOT CAUSE: WHY THE MERGE CRASHED

In v8.0, **two independent signal generators** (UT Bot trail-flip, Smart RSI extreme)
write into **one shared mutable state** (`posState`, `locked_entry/sl/tp1-3`,
`trade_direction`, `trade_active`, `is_trade_running`):

```
buy_signal_confirmed  = (UT_bot_long  AND posState flip) OR (Smart_RSI_bull AND claw_exec_bull AND regime AND posState<=0)
sell_signal_confirmed = (UT_bot_short AND posState flip) OR (Smart_RSI_bear AND claw_exec_bear AND regime AND posState>=0)
```

Both branches can independently set `trade_direction`, overwrite `locked_tp1-3`/`locked_sl`,
and re-key `atm_trade_id`. If Smart RSI fires while a UT-Bot-originated trade is still open
(TP1 not hit), v8.0's "fix" force-closes the old trade as an `SL` in the journal — **even
though no stop was actually hit** — purely to keep the array-based journal consistent.
**This corrupts the outcome labels** the ML layer would train on (a TP1-pending trade
gets mislabeled as SL because an unrelated signal generator fired).

### The fix is architectural, not a patch:

```
Signal Generators (N independent, stateless)          Position Manager (single, stateful)
+---------------------------+                         +--------------------------------+
| ut_bot_signal()            |--+                      | - owns trade_direction          |
| smart_rsi_signal()          |--+--> SignalCandidate->| - owns locked_entry/sl/tp1-3    |
| liquidity_zone_signal()     |--+    {source, dir,    | - owns trade_phase              |
| structure_break_signal()    |--+     confidence,     | - decides ACCEPT/REJECT/QUEUE   |
+---------------------------+         proposed_sl/tp} |   based on current state +      |
                                                        |   prevent_reversals config      |
                                                        | - is the ONLY writer of         |
                                                        |   trade state                   |
                                                        +--------------------------------+
```

- Each signal generator is a **pure function**: `(market_state) -> SignalCandidate | None`.
  It NEVER touches `locked_*`/`trade_direction` directly.
- The **Position Manager** is the single source of truth for "is there an open trade,
  what's its state, what would happen if I accepted this new candidate." It applies
  `prevent_reversals` and any "one trade at a time" rules **here**, as an explicit
  accept/reject decision with a logged reason — never as a post-hoc journal correction.
- A `SignalCandidate` that's rejected because a trade is already running gets logged as
  a **shadow/blocked candidate** (feeding the feature store per the original cheat sheet's
  Section 3) — it does NOT touch the active trade's labels.

This is the concrete unlock for "self-learning intelligence aware of its own tasks": the
Position Manager's accept/reject log *is* the model's training signal for "should a second
opportunity have overridden the first one" — a question v8.0 couldn't even ask because it
had already corrupted the data by force-closing.

---

## 3. THE THREE-LAYER ENGINE (Tron / Jarvis mapping)

| Layer | "Tron" framing — lives in the grid | Engineering contract |
|---|---|---|
| **Perception** (`perception/`) | "Breathes price" — every OHLC, every TF, continuously computed | Stateless or per-symbol-stateful indicator computations: liquidity trail (all TFs), VWAP, volume profile, RSI regime, fib trend, SMC structure (BOS/CHoCH/OB/FVG), PDH/PDL. Output: a single `MarketState` object per symbol per bar — **this is the feature vector**. No signal logic here. |
| **Cognition** (`cognition/`) | Jarvis — reasons over the grid | (a) N independent **signal generators**, each `MarketState -> SignalCandidate\|None`. (b) **Confidence/Scoring** — the weighted-confluence engine (today: hand-tuned weights; tomorrow: `learning/inference.py` with the same I/O contract). (c) **Position Manager** — the single stateful arbiter described in Section 2. |
| **Action** (`action/`) | The hand that moves — broker execution | Broker-agnostic interface (`open_position`, `modify_stop`, `partial_close`, `close_position`, `get_live_pnl`) implemented per venue (Deriv Multiplier/Vanilla, Bybit Perp, MT5 CFD) per Section 7 of the original cheat sheet. **Zero trading logic here** — it only translates a `TradeInstruction` (entry, sl, tp1-3, size, venue) into venue-specific API calls. |

A fourth, cross-cutting layer:

| Layer | Framing | Contract |
|---|---|---|
| **Memory/Journal** (`journal/`) | The organism's self-awareness of its own performance | Every `SignalCandidate` (accepted or shadow-blocked), every Position Manager decision (with reason), every closed trade's MFE/MAE/R-multiple/exit-reason. This is what makes it "self-learning" — `learning/` trains exclusively off this, never off Pine-style in-session arrays. |

**Critically**: Perception -> Cognition -> Action is a **one-way data flow**. Cognition
never reaches back into Perception's internals; Action never reaches back into Cognition's
state. This is the structural fix for "syntax issues with TradeSgnl/MT5" — broker-specific
string formats live entirely inside `action/`, behind an interface that Cognition never
sees.

---

## 4. CONFIDENCE ENGINE -> ML, A MIGRATION PATH (not a rewrite)

v8.0's Confidence Engine signature, generalized:

```python
def confidence(market_state: MarketState, weights: dict[str, float]) -> dict:
    """Returns {bull_confidence: 0-100, bear_confidence: 0-100, breakdown: {...}}"""
```

**Phase 1 (now):** `weights` = the v8.0 hand-tuned values (MTF trail 1.5, RSI 1.0, VWAP
1.0, Fib 0.5, VP 0.5, SMC structure 1.0), hardcoded in `cognition/confidence_v1.py`.

**Phase 2 (once `journal/` has enough closed trades):** `learning/inference.py`
implements **the same function signature**, replacing hand-tuned `weights` with a model
that outputs a full R-multiple distribution, from which `bull_confidence`/`bear_confidence`
are derived (e.g., P(R>0) or expected R). The Position Manager and sizing engine **don't
change** — they consume the same `{bull_confidence, bear_confidence}` shape regardless of
which implementation produced it. Toggle via `USE_ML_CONFIDENCE=true/false` (same idea as
the original cheat sheet's `USE_ML_SIZING`).

This is the literal embodiment of "Analysis (Perception) + Capital (Risk/Sizing) +
Execution (Action)" — Cognition is the seam where hand-tuned analysis becomes learned
analysis, without anything downstream noticing the swap.

---

## 5. REVISED CLAUDE CODE BUILD PROMPT (supersedes Section 8 of the original cheat sheet for the signal/cognition layer)

```
You are working inside the Deep Claw repository. Two reference documents are attached:
`deep_claw_adsa_cheatsheet.md` (full Pine spec - use for INDICATOR MATH and DATA SCHEMAS
only) and `deep_claw_v8_unified_architecture.md` (this document - use for STRUCTURE and
SIGNAL-FLOW decisions). Where the two conflict on architecture, THIS document wins.

CORE RULE: Do not port v8.0's signal-merge logic (the OR-combination of UT Bot and Smart
RSI into shared posState/locked_* globals), its orphan-trade patch, or its TradeSgnl
string-template functions (f_format_alert, f_format_modify). These are documented failure
modes (Section 2 of this doc), not specifications.

PHASE 1 - PERCEPTION LAYER (perception/):
1. Implement a MarketState dataclass/pydantic model per symbol per bar, containing every
   indicator output from the cheat sheet's Section 2 (inputs) and Section 4 (state
   machines) EXCEPT signal-generation and trade-state fields. Include: liquidity trail
   (exec/M5/M15/H1 trend+trail), VWAP (lastSwing, vap_current), volume profile (POC/VAH/
   VAL/strength), RSI regime (positive/negative, raw rsi), Fib trend, SMC structure state
   (swingTrend.bias, latest BOS/CHoCH, active order blocks, liquidity ph_top/pl_btm),
   PDH/PDL status, ATR state, session, 5-TF EMA trend grid (Section 4.2's r/v/f/ri inputs).
   This is computed ONCE per bar and is the only thing Cognition reads.

PHASE 2 - COGNITION LAYER (cognition/):
2. Implement signal generators as pure functions MarketState -> SignalCandidate | None,
   each independent and NOT writing to shared state:
   - ut_bot_signal() - trail-flip logic (ADSA Section 7 math)
   - smart_rsi_signal() - extreme-zone logic (v8.0 Section 6, "Smart RSI Momentum")
   - liquidity_zone_signal() - ATM Protocol break/retest (original cheat sheet section 1.19)
   - structure_shift_signal() - BOS/CHoCH-based
   SignalCandidate = {source, direction, confidence_inputs, proposed_sl, proposed_tp1-3,
   timestamp, symbol}.

3. Implement confidence_v1.py - the 6-factor weighted confluence score from v8.0 Section
   20.5, AS A PURE FUNCTION (MarketState, weights) -> ConfidenceResult, with weights as a
   named, swappable config object (not hardcoded inline). This is the seam for Phase-2 ML
   per Section 4 of this doc.

4. Implement position_manager.py - THE SINGLE STATEFUL OWNER of open-trade state
   (direction, entry, sl, tp1-3, phase, R-multiple progression per the original cheat
   sheet's Section 4.4). It receives SignalCandidates from ALL generators (potentially
   multiple per bar) and:
   - if no trade open: evaluates each candidate's confidence, accepts the best one above
     threshold, computes locked sl/tp1-3 (Platinum Risk Model, cheat sheet 2.5/3.3),
     creates a TradeInstruction
   - if a trade IS open: applies the configured one_trade_rule (prevent_reversals
     equivalent) - accept/reject EVERY candidate explicitly, log the decision + reason to
     journal/ (no silent drops, no force-closing the open trade)
   - runs the Trade Progression state machine (TP1/TP2/TP3/Holder/SL) from the original
     cheat sheet's Section 4.4 against live price, emitting TradeInstructions for partial
     closes / SL modification (breakeven on TP2, etc.)
   - on trade close, writes the full outcome row (entry, exit, exit_reason, MFE/MAE in R,
     bar_count, signal source, confidence at entry) to journal/

PHASE 3 - ACTION LAYER (action/):
5. Define BrokerAdapter protocol: open_position(TradeInstruction) -> PositionHandle,
   modify_stop(PositionHandle, new_sl), partial_close(PositionHandle, fraction),
   close_position(PositionHandle), get_live_pnl(PositionHandle) -> float.
   Implement deriv_multiplier.py, deriv_vanilla.py, bybit_perp.py, mt5_cfd.py per the
   original cheat sheet's Section 7. NONE of these modules import from cognition/ except
   the TradeInstruction/PositionHandle types - they are pure I/O translators. Whatever
   caused "syntax issues with TradeSgnl/MT5" in v8.0 must be isolated entirely inside
   mt5_cfd.py (or removed if Deep Claw no longer needs the TradeSgnl webhook path -
   confirm with operator).

PHASE 4 - JOURNAL / FEATURE STORE (journal/, feature_store/):
6. Implement per the original cheat sheet's Phase 2 (feature store + outcome labeler),
   but the feature store now reads MarketState snapshots (Phase 1 output) and the
   SignalCandidate + Position Manager decision log (Phase 2 output) - INCLUDING
   shadow-blocked candidates with their rejection reason (e.g., "rejected: trade already
   open, one_trade_rule=true" vs "rejected: confidence 45% < threshold 60%"). These two
   rejection reasons are DIFFERENT FEATURES and must not be conflated.

PHASE 5 - LEARNING (learning/):
7. As original cheat sheet Phase 3, with the addition: inference.py must implement the
   SAME function signature as confidence_v1.py (Section 4 of this doc) so it can be
   swapped in via USE_ML_CONFIDENCE=true without Position Manager changes.

PHASE 6 - PARITY/SANITY:
8. Write unit tests proving: (a) two signal generators firing on the same bar while a
   trade is open produces exactly ONE accepted candidate and ONE+ logged rejections, with
   the open trade's state UNCHANGED; (b) a closed trade's outcome row is written exactly
   once, with exit_reason in {TP1,TP2,TP3,HOLDER_EXIT,SL} - never "SL" due to an unrelated
   signal firing.

Throughout: keep ai_advice/SL-autopsy ladders as the Phase-1 confidence/explanation
baseline (Glass Box principle). Keep all dollar sizing asset-routed via the notional
router (original cheat sheet 2.5) inside Position Manager - Action layer never recomputes
sizing.
```

---

## 6. OPEN QUESTIONS (additive to original cheat sheet's "Open Questions" section)

5. **TradeSgnl/MT5 path** — given the v8.0 syntax issues, confirm whether MT5 execution
   should go through (a) TradeSgnl webhook (legacy, string-template based — fragile) or
   (b) a direct MT5 Python bridge (e.g., `MetaTrader5` package / gRPC bridge) controlled
   entirely from `action/mt5_cfd.py`. Recommendation: (b), since it keeps the broker-wire
   format inside one adapter module instead of round-tripping through TradingView alert
   strings.
6. **Multiple simultaneous signal generators, one_trade_rule default** — should Deep
   Claw's default be "one trade per symbol" (matches v8's `prevent_reversals=true` spirit)
   or "one trade per symbol per signal-source" (lets UT Bot and Smart RSI run concurrent
   positions, each tracked independently)? The latter is more "prop-desk" (multiple
   strategies, independent books) but multiplies margin/risk-budget bookkeeping. This is
   a Position Manager config decision (Section 2/5 above), not a code-structure one — but
   it should be decided before Phase 2 step 4 is implemented.
7. **Confidence weight ownership** — should the Phase-1 hand-tuned weights (v8.0's
   1.5/1.0/1.0/0.5/0.5/1.0) be used as-is for `confidence_v1.py`, or recalibrated from the
   ADSA/ATM Protocol live history already accumulated, before the ML swap-in?
