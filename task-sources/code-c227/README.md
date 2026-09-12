# code-c227 â€” Table Bloat Maintenance Audit

Non-connector Harbor task. Audit database table health export against maintenance policy (DBOPS-31).

## Deliverables

- `bloat_audit.csv` â€” Per-table audit with columns table_name, size_class, bloat_ratio, finding
- `bloat_memo.md` â€” Markdown memo explaining each finding in prose sentences (not just a table dump)
- `results.json` â€” flagged_count, autovacuum_disabled_count, bloat_exceeded_count, stale_statistics_count, compliant_count

## Inputs

- `input/maintenance_policy.md` â€” binding policy (autovacuum, bloat cap by size class, staleness, reindex exemption)
- `input/table_health.csv` â€” table health export with total_pages, dead_pages, bloat_ratio, autovacuum_enabled, etc.
- `input/reindex_log.csv` â€” approved reindex operations with valid_until dates

## Expected counts

40 unique tables (42 input rows collapsed for T-31/T-32 duplicates): flagged=27, autovacuum_disabled=7, bloat_exceeded=17, stale_statistics=3, compliant=13.

## Verifier

Grading is via `tests/test_outputs.py` run by `tests/test.sh` (pytest; 166 checks). Core gate: missing deliverable = 0 reward.
Per-check fractional reward is `passed/total` from the pytest summary. `verifier.json` is not used for grading.
`tests/test.sh` launches pytest from `/tmp` with `HARBOR_TASK_WORKSPACE=/app` so a planted `/app/pytest.py` cannot shadow the real module.
