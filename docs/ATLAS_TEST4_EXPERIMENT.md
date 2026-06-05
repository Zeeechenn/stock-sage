# Atlas test4 — Staged Investment-Effect Pre-Registration

> Durable, pre-registered plan for measuring whether Atlas behavior improves
> investment outcomes, WITHOUT contaminating test2. Thresholds are locked here
> before any Stage is run. This is the **investment-effect gate**, which is
> separate from the already-passed engineering merge gate. test4 alone never
> changes official signals, positions, stops, or execution.

## Boundaries (apply to every stage)

- Runs in the Atlas worktree only; Atlas stays dormant (`ATLAS_ENABLED=false`).
- No merge, no push, no rebase. Production DB is **read-only**; all writes go
  under `/private/tmp`. test2 stays frozen. M29 untouched.
- Promotion to the official path requires a passing Stage 2 **and** explicit
  user confirmation. Stage results are evidence, not authorization.

## Data reality (recorded 2026-06-05)

| Source | Range | Count | Note |
|---|---|---|---|
| `signals` | 2026-05-12 → 2026-06-04 | 879 | ~3.5 weeks, single regime |
| `prices` | 2017-01-23 → 2026-06-04 | 856,241 | deep history for forward returns AND signal backfill |

Implication: forward returns are abundant, but the **signal set the overlay
evaluates is tiny and single-regime**. Pure historical evaluation on the current
signals is low-power and is expected to land INCONCLUSIVE. A high-power historical
answer requires **signal backfill** over multi-year price history; a
promotion-grade answer requires forward OOS data accumulated over calendar time.

## What "Atlas overlay" means here

- **Signal / entry-quality overlay (M33 QualityGate, build_case gate)** — already
  has a PIT-correct historical+prospective harness: `backend.tools.gate_b_tracker`
  (`record` → `realize` → `report`). The gate is **rule-based, not fitted**, so
  historical evaluation is not parameter-overfit; its limits are sample size and
  regime coverage, not curve-fitting.
- **Exit overlay / entry+exit overlay** — Atlas thesis-invalidation-driven
  exits on top of base ATR rules. This is the genuinely new test4 surface and is
  not yet wired as a runnable backtest (see Stage 1B feasibility / Stage 2b).

## Stage map

| Stage | Question | Cost | Output |
|---|---|---|---|
| **Stage 1** (now) | Does the atlas signal overlay even discriminate — help or hurt — on available data? | cheap (minutes) | GREEN / RED / AMBER go-no-go. Diagnostic, NOT promotion. |
| **Stage 1B** (now, scoping) | How cheap is a high-power historical run via signal backfill? | cheap (inspect + tiny dry-run) | feasibility + runtime estimate for Stage 2a |
| **Stage 2a** (later) | High-power historical: backfilled multi-regime signals → Gate-B | medium (compute) | promotion-grade historical evidence |
| **Stage 2b** (later) | Forward shadow with test2-style arms | expensive (calendar time) | promotion-grade forward evidence |
| **Promotion** (later) | Influence official path | — | only if Stage 2 passes AND user confirms |

---

## Stage 1 — LOCKED design (historical diagnostic)

Engine: `backend.tools.gate_b_tracker`, with `--source-database-url` =
production (`sqlite:////Users/zeeechenn/stock-sage/stock-sage.db`, read-only) and
`--database-url` = a throwaway observations DB under `/private/tmp`.

Procedure, for each horizon `H ∈ {5, 10, 20}` trading days (separate obs DBs):

```
record  --as-of 2026-06-04 --horizon-days H
realize --as-of 2026-06-04
report  --format json
```

Metrics captured per horizon: `n_pass`, `n_fail`, `gate_pass_rate`,
`dq_exclusion_rate`, winsorized mean net return (pass / fail / delta), median net
return (pass / fail), hit rate (pass / fail), cross-sectional IC of `gate_score`
vs `forward_return_net`.

### Pre-registered Stage 1 decision matrix (locked)

Evaluate per horizon, then combine. `delta = winsorized_mean_net(pass) − winsorized_mean_net(fail)`.

1. **ABORT (data/bias — not a verdict):** `dq_exclusion_rate > 0.30`, OR
   `gate_pass_rate < 0.02`, OR `gate_pass_rate > 0.80`. → fix data first
   (inherits the Gate-B report rule).
2. **RED / STOP:** `delta < 0` **and** `IC ≤ −0.03`, directionally consistent on
   ≥2 of 3 horizons, with `n_pass ≥ 20` **and** `n_fail ≥ 20`. → the signal
   overlay is harmful; do **not** invest in the exit overlay on this premise.
3. **GREEN / PROCEED:** `delta > 0` **and** `IC ≥ +0.03`, consistent on ≥2 of 3
   horizons, with `n_pass ≥ 20` **and** `n_fail ≥ 20`, DQ clean. → build the exit
   overlay and proceed to Stage 2.
4. **AMBER / INCONCLUSIVE:** sample below thresholds (`n_pass < 20` or
   `n_fail < 20`) OR horizons disagree. → history cannot answer yet; choose the
   Stage 2 path (2a backfill vs 2b forward) by whether the direction is at least
   non-negative.

The Stage 1 IC screen (±0.03) is deliberately **looser** than the official
promotion gate (IC ≥ 0.04, ICIR ≥ 0.40, monotonic buckets) because Stage 1 is a
go/no-go diagnostic, not a promotion test.

Given the data reality above, **AMBER/INCONCLUSIVE is the most likely Stage 1
outcome**, and that is itself a useful result: it proves the effect cannot be
established from current history and forces the Stage 2 path decision.

## Stage 1B — backfill feasibility (scoping, runs with Stage 1)

Assess `backend/backtest/backfill_signals.py`: does signal generation require
only technical/price inputs (cheap, offline) or news/sentiment/LLM per day
(expensive, paid)? Do a tiny `/private/tmp` dry-run (1–2 symbols, ~1 month),
measure wall-time, and extrapolate to a 3–5 year × full-universe backfill.
Output: cheap / expensive / blocked, what it needs, runtime estimate, and a
recommendation between Stage 2a (backfill) and Stage 2b (forward).

---

## Stage 2 — LOCKED design (run later, not now)

### Stage 2a — high-power historical (if backfill is cheap)

Backfill signals over ≥3 years of multi-regime history → Gate-B. Promotion-grade
bar: `IC ≥ 0.04` and `ICIR ≥ 0.40` across non-overlapping time folds, monotonic
`gate_score` buckets, winsorized `delta > 0` with a bootstrap CI excluding 0.

### Stage 2b — forward shadow (test2-style arms)

Arms: `test2_baseline`, `atlas_signal_overlay`, `atlas_exit_overlay`,
`atlas_entry_exit_overlay`. test2 stays frozen (original rules, state, A/B
objective, runner inputs, signal loading, position sizing, exit/entry rules,
state JSON semantics); Atlas runs only as a shadow overlay. Metrics: return, max
drawdown, missed-upside rate, false-trend-kill rate, re-entry quality, proposal
hit rate, opportunity cost, extra drawdown, tail risk. Pre-register the proposal
hit-rate horizon, label source, adjudication rule, sample window (≥ defined
forward weeks / matured trades), and small-sample handling before evaluation.
Same-window replay is diagnostic only, never promotion proof.

### Promotion

Only after Stage 2a and/or 2b pass **and** the user confirms. test4 never changes
official signals by itself.

## Status

| Item | State |
|---|---|
| Pre-registration | locked at this commit |
| Stage 1 | run pending (this commit authorizes the run) |
| Stage 1B | run pending |
| Stage 2a / 2b | not started |
| Promotion | not authorized |
