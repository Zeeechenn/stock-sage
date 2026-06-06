# Verification Baseline — 2026-06-06

**Branch:** release/0.3.1-trust-patch  
**Date:** 2026-06-06  
**Purpose:** Pre-change baseline so 0.3.1 regressions can be distinguished from pre-existing state.

---

## Subtarget Results

| Subtarget       | Result | Notes                                                                 |
|-----------------|--------|-----------------------------------------------------------------------|
| `make lint`     | PASS   | ruff check — "All checks passed!" 0 errors, 0 warnings               |
| `make typecheck`| PASS   | mypy — "Success: no issues found in 207 source files"                 |
| `make test`     | PASS   | 1101 passed, 5 skipped, 1 warning in 50.07s                           |
| `make frontend-test` | PASS | 19 tests, 19 pass, 0 fail, 0 skip — duration ~55ms              |
| `make build`    | PASS   | vite v6.4.3 — 62 modules transformed, built in 1.02s                 |

---

## Key Counts

- **Backend test count:** 1101 passed, 5 skipped
- **Frontend test count:** 19 passed, 0 failed

---

## Pre-existing Warnings (Not failures)

- `StarletteDeprecationWarning` in `fastapi/testclient.py`: "Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead." — advisory only, does not affect test outcomes.
- 5 backend tests are skipped (pre-existing, not caused by 0.3.1 changes).

---

## Pre-existing Failures

None. All five subtargets returned exit code 0.

---

## Build Artifact Summary

| File                              | Size      | Gzip       |
|-----------------------------------|-----------|------------|
| `dist/index.html`                 | 0.76 kB   | 0.49 kB    |
| `dist/assets/index-7uVEBW6W.css`  | 37.44 kB  | 7.04 kB    |
| `dist/assets/index-Ckd7NWZ9.js`   | 498.07 kB | 150.40 kB  |

---

## Post-0.3.1 Verify

**Date:** 2026-06-06  
**Branch:** release/0.3.1-trust-patch  
**Run by:** VERIFY agent (Claude Sonnet 4.6)

### Subtarget Results

| Subtarget            | Result | Notes                                                                                     |
|----------------------|--------|-------------------------------------------------------------------------------------------|
| `make lint`          | PASS   | ruff check — "All checks passed!" 0 errors, 0 warnings                                   |
| `make typecheck`     | PASS   | mypy — "Success: no issues found in 207 source files"                                     |
| `make test`          | PASS   | 1101 passed, 5 skipped, 1 warning in 51.27s                                               |
| `make frontend-test` | PASS   | 19 tests, 19 pass, 0 fail, 0 skip — duration ~62ms                                        |
| `make build`         | PASS   | vite v6.4.3 — 64 modules transformed (up from 62; new 0.3.1 modules), built in 1.03s     |

### Comparison vs Baseline

| Subtarget            | Baseline      | Post-0.3.1    | Delta            | Regression? |
|----------------------|---------------|---------------|------------------|-------------|
| `make lint`          | PASS (0 err)  | PASS (0 err)  | no change        | No          |
| `make typecheck`     | PASS (207 src) | PASS (207 src) | no change       | No          |
| `make test`          | 1101p / 5s    | 1101p / 5s    | identical        | No          |
| `make frontend-test` | 19p / 0f      | 19p / 0f      | identical        | No          |
| `make build`         | 62 modules    | 64 modules    | +2 (new modules) | No          |

### Post-0.3.1 Build Artifact Summary

| File                              | Size      | Gzip       |
|-----------------------------------|-----------|------------|
| `dist/index.html`                 | 0.76 kB   | 0.49 kB    |
| `dist/assets/index-7uVEBW6W.css`  | 37.44 kB  | 7.04 kB    |
| `dist/assets/index-DD5slcdg.js`   | 498.14 kB | 150.41 kB  |

### Notes

- JS bundle hash changed (`Ckd7NWZ9` → `DD5slcdg`) and module count increased from 62 to 64. This is expected: the 0.3.1 edits added new source modules that Vite picked up. Bundle size delta is negligible (+0.07 kB raw / +0.01 kB gzip).
- The pre-existing `StarletteDeprecationWarning` from `fastapi/testclient.py` is still advisory-only; no test outcomes affected.
- 5 backend skips remain unchanged from baseline.
- No fixes were needed; all subtargets passed on the first run.

### Verdict

**PASS — no regressions vs baseline.** All five subtargets return exit code 0. Backend test count (1101) is equal to baseline. Frontend tests (19/19) unchanged. Lint, typecheck, and build all clean.
