# DEEP CLAW — CLAUDE CODE BUILD BRIEF
## Mind Map + Reasoning Prompt for Development Kickoff

This document is meant to be pasted (along with the three reference files listed below)
directly into a Claude Code session as the opening brief. It is not a spec to execute
literally — it is a **map of the territory** so Claude Code reasons from first principles
about what Deep Claw *is*, rather than defaulting to "port the Pine Script."

---

## 0. THE WARNING THIS BRIEF EXISTS TO GIVE

We already tried this once. It produced ADSA v8.0 ("Claw Protocol Edition") — a Pine
Script indicator that tried to be an intelligence. It failed not because any single
piece of logic was wrong, but because **we treated migration as translation**: take the
Pine Script's variables, conditions, and comments, and find their Python equivalents.

That approach **carries the garbage forward along with the gold**, because Pine Script
itself encodes a worldview — "recompute everything fresh on every bar, from a snapshot,
with global mutable state, because that's all the language allows." Python does not have
that constraint. If Claude Code starts from "here's the Pine Script, port it," it will
inherit that worldview by default, because the worldview is baked into the *shape* of
the existing code, not just its bugs.

**The instruction to Claude Code is therefore inverted from normal migration work:**
Do not start by reading the Pine Script as a spec to implement. Start by reading the
three reference documents below as the spec — they already extracted the *ideas* worth
keeping from the Pine Script and discarded the Pine-shaped scaffolding. The Pine Script
itself should be consulted only as a **glossary of formulas** (e.g., "what exactly is
the ATR-trail ratchet math," "what is the exact Platinum Risk Model notional formula") —
never as an architectural template.

---

## 1. THE THREE REFERENCE DOCUMENTS — WHAT EACH ONE IS FOR

```
┌─────────────────────────────────────────┬───────────────────────────────────────────┐
│ DOCUMENT                                 │ ROLE IN THIS BUILD                          │
├─────────────────────────────────────────┼───────────────────────────────────────────┤
│ deep_claw_adsa_cheatsheet.md             │ FORMULA GLOSSARY + DATA SCHEMA REFERENCE   │
│ (full input registry, dashboard maps,    │ ONLY. Use for: exact math (notional        │
│ alert catalog, SL autopsy table, daily   │ router, position sizing, R-multiple TP     │
│ report schema, watchlist/broker mapping, │ ladders, VWAP/RSI/Fib formulas, SMC         │
│ Pine->Python porting gotchas table)      │ structure detection rules), the watchlist/  │
│                                           │ broker symbol mapping, and the              │
│                                           │ Pine->Python gotchas table (Section 4 of    │
│                                           │ Part 9) which is genuinely useful for       │
│                                           │ avoiding repaint/lookahead bugs.            │
│                                           │ DO NOT use its dashboard layouts, alert     │
│                                           │ templates, or signal-flow diagrams as       │
│                                           │ architecture — those encode the tree/       │
│                                           │ snapshot worldview being replaced.          │
├─────────────────────────────────────────┼───────────────────────────────────────────┤
│ deep_claw_v8_unified_architecture.md     │ FAILURE DIAGNOSIS + ARCHITECTURAL           │
│ (v8 bug catalog, root-cause analysis of  │ CONSTRAINTS. Use for: the list of what      │
│ the OR-merge/orphan-trade bug, 3-layer   │ NOT to build (Section 9's table is a        │
│ Perception/Cognition/Action mapping,     │ checklist), and the Perception/Cognition/   │
│ confidence-engine migration path)        │ Action layer boundaries (Section 3) as the  │
│                                           │ skeleton everything else fits into.         │
├─────────────────────────────────────────┼───────────────────────────────────────────┤
│ DEEPCLAW_README.md                       │ THE NORTH STAR / PRODUCT VISION. Use for:   │
│ (Tron/Jarvis framing, chain-vs-tree      │ the EpisodeStream/chain-logic concept        │
│ insight, EpisodeStream as the spine,     │ (Section 3) which is the ONE genuinely NEW   │
│ Claude qualification layer's role,       │ architectural element not present in either │
│ build sequencing)                        │ Pine version, the build order (Section 11),  │
│                                           │ and the definition of "done" for each       │
│                                           │ phase — what Claude is FOR (Section 6).     │
└─────────────────────────────────────────┴───────────────────────────────────────────┘
```

**Practical instruction:** attach all three. Tell Claude Code to read them in this
order: README first (vision + what's new), then v8-unified-architecture (what to avoid +
layer skeleton), then cheatsheet (formula reference, consulted on-demand per module —
not read front-to-back). Only fetch the raw Pine Script v8 source if a specific formula
needs verification, and even then, treat it as you'd treat a textbook appendix — copy
the formula, not the surrounding code structure.

---

## 2. MIND MAP — WHAT WE ARE BUILDING

```
                                   DEEP CLAW
                    "A synthetic trading intelligence —
                     not an indicator, not a chatbot wrapper"
                                       |
        +------------------------------+------------------------------+
        |                               |                               |
   WHAT IT DOES                  WHAT MAKES IT NEW              WHAT IT IS NOT
        |                               |                               |
  - Perceives price            - EpisodeStream: chain of        - NOT a ported Pine
    across Deriv/Bybit/MT5       narrative events, not a          indicator with a
    as ONE normalized            per-bar snapshot tree            Python wrapper
    reality (Tron)
                                - Confidence is STRUCTURAL,      - NOT "Claude reads
  - Reasons top-down,             gates entry & sizing,            indicator values
    chain-causal (not flat        not cosmetic display             and says yes/no"
    scoring) about what
    today's session means        - ONE Position State            - NOT a system that
    (Jarvis)                       Machine, broker-synced,          starts blind every
                                    zero orphans by design           session (no memory)
  - Sizes capital with
    positive-expectancy          - Claude's role = narrative      - NOT autonomous
    discipline (fractional         judgment over the chain,         parameter-mutation
    Kelly-style, asset-            not table-reading                on day one (that's
    routed notional)                                                 Phase 3, gated)
                                  - Self-learning is a
  - Executes broker-                pipeline (journal ->
    agnostically, then              labeler -> learned model
    LEARNS from every                -> swap into same
    outcome                          interface), not a vague
                                      aspiration
        |                               |                               |
        +------------------------------+------------------------------+
                                       |
                            THE SPINE: EPISODESTREAM
                  (append-only chain; renders to dashboard,
                   Telegram, Claude prompts, AND ML training rows
                   — one source, four consumers)
                                       |
        +------------------------------+------------------------------+
        |                               |                               |
   PERCEPTION                      COGNITION                       ACTION
   (Tron's senses)                 (Jarvis's mind)              (the hand)
        |                               |                               |
  MarketState snapshot          Signal Generators              BrokerAdapter
  (numeric feature vector,      (pure fns, independent,        protocol:
  per symbol/bar, all TFs)      typed by SignalType)            open/modify/
                                                                 partial_close/
  Episode emission              Chain Reasoning Engine          close/get_pnl
  (state-transition events:     (resolves EpisodeStream +
  regime flips, sweeps,         MarketStates -> ChainVerdict)   deriv_multiplier.py
  BOS/CHoCH, session                                            deriv_vanilla.py
  changes)                      Confidence Engine v1            bybit_perp.py
                                 (hand-tuned weights,            mt5_cfd.py (direct
  Ported indicators              swappable interface for ML)    bridge, NOT
  (liquidity trail, VWAP,                                       TradeSgnl strings)
  volume profile, RSI,          Position State Machine
  Fib, SMC structure,            (single owner of trade state,
  PDH/PDL, ATR regime,           reversal = close+log+open new)
  session detection)
```

---

## 3. THE "WHAT'S ACTUALLY NEW" FILTER

Before Claude Code writes a single module, it should be able to answer: **"is this
component a faithful port of a formula, or is it a structural decision the prior systems
got wrong?"** Everything sorts into one of three buckets:

### Bucket A — Pure formula, port faithfully (cheatsheet is authoritative)
- Contract notional router (`_get_contract_notional`, `_risk_at_min_lot`,
  `_get_position_size`) — this was correct since v6.1, preserve exactly.
- ATR-trail ratchet math (`calcLiqTrail`), VWAP adaptive tracking, Fibonacci band
  calculation, RSI regime thresholds, MACD/Stoch, volume profile POC/VAH/VAL math, SMC
  BOS/CHoCH/OB/FVG/EQH-EQL detection, R-multiple TP ladder (1.0/1.5/2.0).
- These are math. Math doesn't care what language it's in. Port the *formula*, written
  as a pure Python function operating on arrays/series, tested against known outputs.

### Bucket B — Structural decisions the prior systems got wrong, rebuild per README/v8-doc
- Signal generation: independent pure functions emitting `SignalCandidate`s, NOT
  booleans OR'd into shared globals.
- Trade state: ONE `PositionStateMachine`, NOT `posState` + `trade_active` +
  `is_trade_running` + strategy-position as four competing truths.
- Confidence: gates and scales, NOT a displayed percentage.
- Reversal handling: close+log+open, NOT `prevent_reversals` dead zones or orphan
  patches.
- MT5/broker communication: typed adapter calls, NOT TradeSgnl string templates.
- Context for narrative/Claude/journal: EpisodeStream chain, NOT tree-format snapshot
  strings.

### Bucket C — Genuinely new, no prior version had this, design from scratch
- `EpisodeStream` schema and emission rules (what qualifies as an "episode"?).
- `ChainReasoningEngine` / `ChainVerdict` (causal trace, restrictions, episodic-memory
  query).
- The renderer that turns an `EpisodeStream` slice into: (a) dashboard timeline JSON,
  (b) Telegram narrative text, (c) Claude prompt context — one function, three output
  formats.
- The `learning/` pipeline interface (`confidence_v1` vs `inference.py` swap).

**Claude Code should explicitly label which bucket each module/decision falls into as it
proposes a plan** — this is the single biggest guardrail against silently re-importing
v8's worldview, because it forces an explicit "why does this look the way it does"
justification for every piece.

---

## 4. WHAT TO HAND CLAUDE CODE, AND IN WHAT ORDER

### Step 1 — Orientation (no code yet)
Provide: this brief + the three reference docs. Ask Claude Code to produce its own
short **"Plan of Record"** — a restatement of the mind map above in its own words, plus
a proposed module list with each module tagged Bucket A/B/C. This is a checkpoint: if
Claude Code's restatement still smells like "ADSA v9," stop and re-align before any
code is written.

### Step 2 — Foundations (Bucket C first, deliberately)
Build `EpisodeStream`, `MarketState`, `SignalCandidate`, `ChainVerdict`,
`PositionStateMachine` as dataclasses/protocols with NO indicator math yet — just the
shapes and the state-transition logic, with unit tests proving:
- Two signal sources firing same-bar while a trade is open -> one accepted, rest logged
  as shadow-blocked with reasons, open trade state unchanged.
- Reversal -> close+log+open, no orphan rows ever.
- EpisodeStream renders into at least a plain-text chain narrative (even ugly) — prove
  the "four consumers, one source" idea end to end before making it pretty.

### Step 3 — Perception (Bucket A, ported formulas feeding into Bucket C shapes)
Port the indicator math from the cheatsheet as pure functions producing `MarketState`
fields, and wire Episode-emission rules (regime flip, sweep, BOS/CHoCH, session change
-> append to EpisodeStream). Validate against historical data / known Pine outputs where
possible.

### Step 4 — Cognition
Signal generators (Bucket B, typed), Chain Reasoning Engine (Bucket C, consumes Step 2+3
outputs), Confidence v1 (Bucket A's weight *values* behind Bucket B's swappable
interface).

### Step 5 — Action
Broker adapters. Deriv first (live connection already exists), then Bybit, MT5 last with
direct bridge.

### Step 6 — Communication + Claude integration
EpisodeStream renderer -> dashboard/Telegram/Claude-prompt. Claude qualification calls,
SL autopsy, daily self-assessment — all reading the rendered chain.

### Step 7 — Journal/feature store formalization, then Learning pipeline
Only once Steps 2-6 are producing real EpisodeStream data from live or paper trading.

---

## 5. THE PROMPT TO PASTE INTO CLAUDE CODE

```
I'm building "Deep Claw" — a synthetic trading intelligence (not an indicator, not an
LLM wrapper around a trading bot). I'm attaching three documents:

1. DEEPCLAW_README.md — the product vision and north star. Read this FIRST. The core
   idea is "chain, not tree": market context is represented as an append-only
   EpisodeStream (narrative chain of state-transition events), not a per-bar snapshot.
   This EpisodeStream is the spine of the whole system — it feeds the dashboard,
   Telegram, the Claude reasoning calls, AND the ML training data, from one source.

2. deep_claw_v8_unified_architecture.md — a failure post-mortem of a prior attempt
   (ADSA v8.0, a Pine Script indicator that tried to be this intelligence and broke).
   Read this SECOND. Section 9's table is a checklist of specific things NOT to
   replicate (shared mutable trade-state across signal sources, orphan-trade patches,
   TradeSgnl string-template coupling, cosmetic confidence scores, etc.). Section 3's
   Perception/Cognition/Action layering is the skeleton.

3. deep_claw_adsa_cheatsheet.md — a formula and data-schema reference extracted from
   the same Pine Script lineage. This is a GLOSSARY, not a spec. Use it for exact math
   (contract notional routing, position sizing, indicator formulas, R-multiple TP
   ladders, SMC structure detection) and the Pine->Python porting-gotchas table
   (Part 9, Section 4) — but NOT for its dashboard layouts, alert templates, or
   signal-flow diagrams, which encode the tree/snapshot worldview we're moving away
   from.

CRITICAL CONTEXT — read before planning anything:
We previously tried to build this by porting a Pine Script indicator (ADSA v8.0)
directly to Python, treating the migration as translation. It failed — not because
individual formulas were wrong, but because Pine Script's structure (global mutable
state, per-bar snapshot recomputation, two independent signal philosophies OR'd into
one trade-state) got carried into the port along with the math. We ended up rebuilding
the same bugs in a new language.

This time: do NOT start from the Pine Script as an architectural template. The three
documents above already did the work of separating "formulas worth keeping" (Bucket A)
from "structural decisions that were wrong and need rebuilding" (Bucket B) from
"genuinely new concepts neither prior version had" (Bucket C — EpisodeStream, Chain
Reasoning Engine, the renderer that serves dashboard/Telegram/Claude/ML from one
source). Section 3 of this brief gives that bucketed breakdown.

WHAT I NEED FROM YOU RIGHT NOW (Step 1 only — do not write code yet):
Read all three documents fully. Then produce your own "Plan of Record": restate the
architecture in your own words, propose a module/file structure, and for each
module/decision, label it Bucket A (port formula faithfully), Bucket B (rebuild per the
v8 lessons), or Bucket C (new — design from the README's EpisodeStream concept). I want
to review this Plan of Record before any implementation starts, specifically checking
that it doesn't quietly reintroduce the tree/snapshot worldview or the shared-mutable-
trade-state pattern that broke v8.

The end goal, stated plainly: a system that remembers its own trading session as a
story (EpisodeStream), reasons over that story top-down like a desk manager (Chain
Reasoning Engine + Confidence Engine), sizes capital with positive-expectancy discipline
(asset-routed risk model, fractional-Kelly-style sizing), executes broker-agnostically
across Deriv/Bybit/MT5, and gets measurably better over time because the story it tells
itself is also the data it learns from (journal -> learning pipeline). That's "Deep
Claw" — fintech-grade augmented intelligence, not a chatbot bolted onto a chart.
```

---

## 6. ONE LAST GUARDRAIL FOR THE SESSION

If at any point Claude Code's proposed code reintroduces:
- a boolean signal flag written by more than one source into shared state,
- a "snapshot string" that's the *only* thing passed to Claude or Telegram (no chain),
- a confidence number that's computed but doesn't change what happens next,
- or broker-specific string formatting living anywhere outside `action/`,

...that's the v8 smell. Stop, point at Section 9 of `deep_claw_v8_unified_architecture.md`,
and ask for a redesign of that piece specifically. These four smells map 1:1 to the four
root causes of the v8 failure, and catching them early is cheaper than a week of testing
failures again.
