# code-c227-table-bloat-maintenance-audit

A non-connector Harbor task that audits database table maintenance against a
vacuum and bloat policy.

## What the agent must do

The agent receives `maintenance_policy.md` and `table_health.csv` (17 tables)
as read-only inputs. For each table it must:

1. Check whether autovacuum is enabled (this overrides every other check).
2. Check whether the bloat ratio exceeds the size-class cap
   (large tables > 0.20, small tables > 0.40), unless the table is under an
   approved active reindex operation.
3. Check whether statistics are stale (> 30 days since last analyze).

The agent writes three deliverables:

- `bloat_audit.csv` — one row per table (17 rows) with a `finding` column
  (`AUTOVACUUM_DISABLED`, `BLOAT_THRESHOLD_EXCEEDED`, `STALE_STATISTICS`,
  or `none`).
- `bloat_memo.md` — a Markdown memo explaining each finding, including the
  table under active maintenance and the densified edge-case tables
  (T-09 boundary stats, T-10 reindex-doesn't-exempt-stale, T-11
  autovacuum-overrides-bloat, T-12/T-13 exact-cap boundary, T-14
  maintenance+stale, T-15 autovacuum+stale, T-16/T-17 size-class cap).
- `results.json` — aggregate counts (`flagged_count`,
  `autovacuum_disabled_count`, `bloat_exceeded_count`,
  `stale_statistics_count`, `compliant_count`).

## Verifier

`tests/verifier.json` contains 34 deterministic checks:

- 3 file-existence checks (audit CSV, memo, results JSON).
- 11 per-table CSV regex checks (each table's finding must match the policy).
- 8 memo regex checks (memo must mention size-class cap, bloat cap,
  maintenance/reindex exemption, and each flagged table's reason is
  clause-scoped to prevent reason-rotation exploits).
- 5 results.json value checks (aggregate counts must match gold).
- 3 clean-row checks (compliant tables must read `none`).
- 4 trap checks (T-09 boundary, T-10 reindex+stale, T-11 autovacuum override).

Reward is fractional: `passed / total`.

## Solution

Gold deliverables are under `solution/files/`. `solution/solve.sh` copies
them into the workspace. Oracle reward is 1.0 (34/34).

## Densification

The task was densified from 8 to 17 tables with 9 edge-case traps:
T-09 through T-17, covering boundary bloat ratios (exactly at cap),
maintenance exemption vs stale stats, autovacuum overriding stale stats,
and size-class-specific cap application.
