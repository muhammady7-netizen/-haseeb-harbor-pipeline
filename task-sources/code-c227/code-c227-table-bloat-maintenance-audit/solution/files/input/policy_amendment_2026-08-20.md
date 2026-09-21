# Policy amendment DBOPS-31-A — issued 2026-08-20

Effective for the September 2026 maintenance audit. Binding audit calendar date:
**2026-09-01**. Also apply `ops_bulletin.md` for change-control holds.

## 1. Audit-date anchor

Do **not** use the `audit_date` column from `table_health.csv` for staleness or
reindex/hold validity. Always use issued audit date **2026-09-01**.

## 2. Exact-30-day staleness

Stale when `(2026-09-01 - last_analyzed).days >= 30`.

## 3. Large-table stale tightening

When stale: large (`total_pages >= 500`) reduce cap by **0.10** (effective 0.10);
small reduce by **0.05** (effective 0.35).

## 4. Manual vacuum case-sensitive

`vacuum_type` must equal exactly `manual`. `Manual` / `MANUAL` / spaced forms do not.

## 5. Reindex validity exclusive

Reindex exempts bloat only when `maintenance_active` AND `approved=True` AND
`valid_until > 2026-09-01`.

## 6. Reindex log duplicates

Last row per `table_name` in `reindex_log.csv` wins.
