# Table maintenance & vacuum policy (DBOPS-31)

This decides whether a table's maintenance state is compliant. Where the database's own
health dashboard disagrees, this policy decides.

## 1. Autovacuum

A table with autovacuum disabled is `AUTOVACUUM_DISABLED`. This is checked first and
overrides every other check for that table, whatever its current bloat ratio reads.

## 2. Bloat cap by size class

| size class | max bloat ratio |
|---|---|
| large | 0.2 |
| small | 0.4 |

A table's bloat ratio is judged against its own size class's cap, never the other class's —
a large table is never given the small-table allowance. A table over its own cap is
`BLOAT_THRESHOLD_EXCEEDED` — **unless** the table is marked under an approved active reindex
operation, in which case elevated bloat during the rebuild is expected and the table is
exempt from this check for the duration of the operation.

## 3. Statistics staleness

A table whose planner statistics were last refreshed more than 30 days ago is
`STALE_STATISTICS`. This applies independently of the bloat check.

## 4. Finding names

`AUTOVACUUM_DISABLED`, `BLOAT_THRESHOLD_EXCEEDED`, `STALE_STATISTICS`, or `none`.
