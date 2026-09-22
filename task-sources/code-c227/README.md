# code-c227 — Table Bloat Maintenance Audit

Non-connector Harbor task. Audit database table health export against maintenance policy (DBOPS-31).

## Deliverables

- `bloat_audit.csv` — Per-table audit with columns table_name, size_class, bloat_ratio, finding
- `bloat_memo.md` — Markdown memo explaining each finding in prose sentences (not just a table dump)
- `results.json` — flagged_count, autovacuum_disabled_count, bloat_exceeded_count, stale_statistics_count, compliant_count

## Inputs

- `input/maintenance_policy.md` — binding policy (autovacuum, bloat cap by size class, staleness, reindex exemption)
- `input/table_health.csv` — table health export with total_pages, dead_pages, bloat_ratio, autovacuum_enabled, etc.
- `input/reindex_log.csv` — approved reindex operations with valid_until dates

## Expected counts

40 unique tables (42 input rows collapsed for T-31/T-32 duplicates): flagged=27, autovacuum_disabled=7, bloat_exceeded=17, stale_statistics=3, compliant=13.

## Verifier

- Harbor grading: `tests/test_outputs.py` via `tests/test.sh` (pytest).
- Current suite: **50** `test_*` functions → **170** collected pytest nodes (parametrized).
- Portal catalog: `tests/verifier.json` ships with this package (**34** deterministic verifiers). Required for QC packaging.
- Local gold plant (2026-09-18): **170/170 passed** with `solution/files` + `environment/input`.
- `tests/test.sh` launches pytest from `/tmp` with `HARBOR_TASK_WORKSPACE=/app` so a planted `/app/pytest.py` cannot shadow the real module.

## Evidence status (QC 2026-09-18)

Packaging fixes applied: LF line endings; `tests/verifier.json` present.

Bundled fresh Harbor evidence:
- `evaluations/oracle/` — reward **1.0**
- `evaluations/stability/repeat-01..03` — all **1.0**

Still required before final QC submit:
- GLM 5.2 ×4 difficulty
- Solvability agent-pass

## Near-pass note

Older GLM near-passes (~0.994) mixed two eras: obsolete `T-52` on a pre-restructure grid, and post-densify **T-45** (ratio `0.16` over stale-tightened cap `0.15` memo gate). Re-confirm with fresh GLM×4 before claiming `failure_cause_validity`.
