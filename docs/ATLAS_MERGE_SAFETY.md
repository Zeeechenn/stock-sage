# ATLAS Merge-Safety Report (Gate A)

> Scope: the ATLAS work on `codex/atlas` (M33–M40 + the explicit `jsonschema`
> dependency + two M40 fixes), 12 commits over base `8a912b6`.
> Question answered: **Is it safe to merge ATLAS into `main` without changing
> any production trading behaviour?**
> Answer: **Yes** — ATLAS is mergeable as a dormant, import-isolated, advisory
> research/governance layer. This report does NOT claim ATLAS performs better
> (that is Gate B — see the last section).

## What ATLAS added
8 new research modules under `backend/research/` (case, stress_test,
thesis_ledger, theme_hypothesis_engine, review_loop, universe_guard,
forward_thesis, case_view), 7 new additive tables, 40+ gated API routes, 6
feature flags, and ~163 tests. Net `+4000`-ish lines, almost entirely new files.

## Gate A acceptance criteria & evidence

| # | Criterion | Evidence | Status |
|---|---|---|---|
| A1 | Production signal/decision/scheduler source unchanged by ATLAS work | `git diff 8a912b6..HEAD -- backend/decision backend/agents backend/scheduler.py` → empty | ✅ |
| A2 | Production path does not import any ATLAS module (structural isolation) | grep of `backend/decision`, `backend/agents`, `backend/scheduler.py` for the 8 new modules → 0 hits | ✅ |
| A3 | Edits to shared files are additive only | `database.py` (+tables, `CREATE TABLE IF NOT EXISTS` only), `config.py` (+flags), `schemas.py` (+models / optional `case`), `routes/research.py` (+routes; only existing change is `import Query` + moving the catch-all route to last), `dossier.py` (+`case` key, existing keys intact), `ops/llm_usage.py` (+`red_team_review` bucket) | ✅ |
| A4 | The `case` key added to the dossier cannot affect production | `build_research_dossier` is consumed only by `dossier.py` + the research routes — not by decision/scheduler | ✅ |
| A5 | API changes are additive + write routes gated; memory promotion human-gated | new routes only; every write uses `agent_write_guard`; `promote_memory` requires non-empty `confirmed_by` | ✅ |
| A6 | Full test suite green | `uv run pytest` → **860 passed, 5 skipped** (main baseline: 688 passed) | ✅ |
| A7 | App boots, all routes register, migrations execute, E2E lifecycle works | app imports cleanly (112 routes, 42 research); 3 migration scripts run; TestClient lifecycle (create→promote→case-view) passes | ✅ |
| A8 | Startup/import time no pathological regression | `import backend.main`: atlas ~0.5–0.8s vs main ~0.45–0.59s (same order) | ✅ |
| A9 | Reversible | see Rollback below | ✅ |

## Why safety does NOT depend on the feature flags
The 6 flags default `True`, but production safety rests on **structural import
isolation** (A2), not on flag state: the decision/scheduler path never imports
or calls any ATLAS module, so the flags only decide whether the *advisory
research write functions* execute when *explicitly* called via their routes.
No flag state can change a trading signal.

## Rollback procedure
- **Code**: ATLAS is 12 additive commits; `git revert` (or dropping the merge)
  removes all routes/modules. No existing code path depends on them.
- **Schema**: all new tables are additive and created via
  `CREATE TABLE IF NOT EXISTS` / `Base.metadata.create_all`. Rollback options:
  (a) leave the tables (they are inert — nothing in production reads them), or
  (b) `DROP TABLE` the 7 new tables. No existing table was altered, so there is
  nothing to un-migrate.
- **Data**: ATLAS never writes Signal / DecisionRun / M29 / existing
  `ai_memory` rows except via the explicit, human-gated `promote_memory` path
  (which uses the existing `create_stock_memory` API and is opt-in).

## Known caveat (pre-existing, NOT ATLAS)
`backend/data/market.py` differs between `main` and `codex/atlas` (17+/24−).
This divergence predates the M33–M40 work (it is on the atlas base, not in
`8a912b6..HEAD`). It must be reviewed separately before merge — it is the one
production-path file that is not identical between the branches.

## What this report does NOT claim — Gate B (value)
ATLAS changes **zero** trading decisions by design, so it cannot be shown to
out-perform `main` here. "Better" requires, per ATLAS §2 and the existing
validation tooling:
1. wiring ONE ATLAS capability into the decision path behind a flag;
2. an A/B / forward-shadow experiment via `paper_trading/test2_ab_*` +
   `backend/tools/m29_shadow_validation` + `m27_top_decile_forward_shadow`,
   **point-in-time, non-overlapping, survivorship-corrected via the M38
   universe snapshots**;
3. **pre-registered** metrics (rank-IC / hit-rate / calibration-Brier /
   max-drawdown / after-cost return) and a **pre-registered decision rule**
   (e.g. uplift ≥ X with stable sign across K folds and no drawdown worsening)
   before any promotion or `weight_quant` change.
Until a capability passes Gate B, ATLAS is a stronger *research/governance*
layer, not a *better trading system*.

## Sign-off recommendation
Gate A is met (modulo a separate review of the pre-existing `market.py`
divergence). ATLAS may be merged into `main` as dormant, advisory, flag-gated
infrastructure with effectively zero risk to production trading behaviour.
Replacing any of `main`'s decisions requires the corresponding Gate B
experiment.
