# ATLAS — Future Trading Architecture Plan

> Worktree: `/Users/zeeechenn/Documents/项目s/atlas`  
> Branch: `codex/atlas`  
> Purpose: keep the current `main` workspace focused on M29-M32 while this worktree drafts the next architecture layer.

---

## 1. Decision

StockSage should not become a pure research-writing agent.

The long-term goal remains trading decision support: discover candidates, judge entry and exit conditions, monitor positions, and review outcomes so the system can improve its win-rate evidence over time.

The future architecture is therefore:

```text
ResearchCase -> SignalCase -> PositionCase -> ReviewCase
```

Each case has a narrow role:

| Case | Question | Primary owner |
|---|---|---|
| `ResearchCase` | Why is this stock, sector, or theme worth studying? | evidence, thesis, contradiction |
| `SignalCase` | Is there a tradable setup now? | quant, technical, sentiment, market regime |
| `PositionCase` | Why does this position exist and when should it end? | entry, sizing, stop, take-profit, kill conditions |
| `ReviewCase` | What did the outcome teach us? | attribution, calibration, memory promotion |

The first implementation slice is `ResearchCase v0`, but that is only the upstream container. Quantitative evidence stays central through `SignalCase` and `ReviewCase`.

---

## 2. Non-Negotiable Boundaries

- M29 remains the highest-priority current line until fresh forward evidence and quant residual attribution reach a clear gate outcome.
- `weight_quant=0.0` stays unchanged unless M29 promotion gates pass and the user explicitly approves a production change.
- No new architecture PR may alter production signal behavior, daily batch defaults, M29 ledger semantics, checkpoint usage, or real trading state.
- LLM output may organize evidence, propose contradictions, and create review questions, but it must not directly write trusted memory or production ledgers.
- The project does not issue strong-buy labels, deterministic price forecasts, or automatic broker orders.
- Theme research may create hypotheses and candidate tiers, but it must not directly raise buy scores.

---

## 3. Why Not a Big-Bang Rewrite

The reports and discussion point to a large destination, but a single rewrite would mix too many risk surfaces:

- debate semantics;
- research dossier schema;
- quant evidence gates;
- production signal path;
- memory governance;
- frontend routing;
- review/calibration storage.

That would make it impossible to prove which change improved or damaged trading usefulness.

The chosen path is **large architecture, small verifiable slices**:

1. define the stable case contract;
2. adapt existing modules into that contract;
3. move one capability at a time behind the contract;
4. keep production signal diffs at zero until a later explicit promotion review.

---

## 4. Relationship To Existing Milestones

### M29 — Alpha Reset / Forward Evidence Engine

M29 continues in the main worktree. It answers whether the current quant and shadow alpha candidates have enough forward, point-in-time, monotonic, non-overlapping evidence to deserve any production discussion.

ATLAS must not replace M29. It consumes M29 outputs later as `SignalCase` and `ReviewCase` evidence.

### M31 — Productized Operations

M31 improves cache layers, provider fallback clarity, trading-rhythm commands, and report exports. It should reduce operational friction without changing signal logic.

### M32 — Bounded Forward Thesis

M32 turns review evidence into falsifiable forward theses: sector or theme-level statements with horizons, evidence, invalidation conditions, and follow-up metrics. It is not short-term price prediction.

### M33+ — ATLAS Case Architecture

M33 and later milestones unify research, signal, position, and review objects so StockSage can connect thesis, entry, exit, and calibration.

---

## 5. Milestone Plan

### M33 — ResearchCase v0

Goal: create the minimal case envelope without changing behavior.

Scope:

- Add a `ResearchCase` schema.
- Add `QualityGate v0` for missing evidence, stale data, cutoff/as_of checks, and source coverage.
- Add `StructuralValidityCard v0` for point-in-time, universe, provenance, calibration, and cost-awareness status.
- Adapt the existing research dossier into a `case` view while preserving old response fields.
- Add focused tests for case construction and API compatibility.

Non-goals:

- no debate rewrite;
- no production signal change;
- no DB migration unless proven necessary;
- no default new LLM calls;
- no M29 ledger writes.

### M34 — Evidence-Bounded Stress Test

Goal: downgrade debate from "agent voting" into a red-team review of a case.

Scope:

- Add `run_stress_test(case)`.
- Roles become evidence auditor, bear/falsifier, execution-risk reviewer, methodology/base-rate reviewer, and adjudicator.
- Output blockers, decision deltas, follow-up questions, and confidence adjustments.

Non-goals:

- no more rounds as the main optimization;
- no 6+1 expert panel clone;
- no direct trade action override.

### M35 — Thesis Ledger

Goal: convert long-term research into stateful, reviewable thesis records.

Scope:

- thesis status: `active`, `watch`, `broken`, `retired`;
- kill conditions;
- update cadence;
- confidence history;
- linked ResearchCase and ReviewCase references.

### M36 — Theme Hypothesis Engine

Goal: make sector/theme research actionable without becoming a buy-score shortcut.

Scope:

- theme universe;
- hypotheses;
- beneficiary tiers;
- evidence gaps;
- invalidation conditions;
- bridge to M29/M32 forward evidence when enough review data exists.

### M37 — Review / Calibration / Memory Loop

Goal: let only reviewed outcomes become trusted memory.

Scope:

- `ReviewCase` schema;
- outcome attribution;
- memory promotion rules;
- pending vs trusted memory states;
- links to original research, signal, and position cases.

### M38 — Dynamic Universe / Survivorship Guard

Goal: reduce survivorship bias and improve theme/sector validation.

Scope:

- current vs historical universe distinction;
- universe hash and cutoff;
- provenance completeness reporting;
- backtest and forward-validation use only at first.

### M39 — Forward Thesis Beta

Goal: support bounded forward judgment such as "storage cycle recovery is becoming trackable".

Scope:

- thesis horizon;
- evidence manifest;
- confidence band;
- invalidation conditions;
- follow-up metrics;
- review schedule.

Non-goals:

- no target price;
- no tomorrow direction prediction;
- no strong-buy output;
- no production score change.

### M40 — UX Consolidation

Goal: expose the new case model only after the data contract is stable.

Scope:

- individual stock research entry;
- theme research entry;
- review/evidence ledger entry;
- case-linked dossier view.

---

## 6. First PR Definition

Recommended first PR:

```text
branch: codex/atlas
title: docs: define ATLAS research-to-trading architecture
```

If code is added later, the first code PR should be:

```text
branch: codex/m33-research-case-v0
title: feat(research): add ResearchCase v0 envelope
```

Acceptance criteria for the first code PR:

- Existing dossier fields remain compatible.
- New `case` field is optional and read-only.
- Focused tests pass for schema, quality gate, structural validity, and compatibility.
- Production signal output is unchanged.
- No M29 ledger, checkpoint, quant-weight, or daily batch behavior changes.

---

## 7. Open Questions

- What is the minimum `SignalCase` snapshot needed to keep quant evidence first-class from day one?
- Should `ResearchCase` initially live only in API responses, or also persist as a reviewed artifact?
- Which review outcomes are strong enough to promote memory from pending to trusted?
- When M29 finds a valid quant candidate, does it enter `SignalCase` as a continuous score, a discrete filter, or both?

These questions should be answered before implementing later milestones, not before documenting the architecture.
