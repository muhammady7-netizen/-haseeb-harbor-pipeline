# Ops bulletin OB-31-C — change-control holds (issued 2026-08-25)

This bulletin is **binding for the September 2026 maintenance audit** alongside
`maintenance_policy.md` and `policy_amendment_2026-08-20.md`.

## Purpose

`change_control_tickets.csv` records temporary **bloat holds**. A qualifying hold
suppresses a `BLOAT_THRESHOLD_EXCEEDED` finding only. It does **not** clear
`AUTOVACUUM_DISABLED`, and it does **not** clear `STALE_STATISTICS`.

## Qualifying hold (all must be true)

1. After resolving the ticket's target table (see Aliases), the ticket's
   `exception_type` equals exactly `BLOAT_HOLD` (other types such as
   `REINDEX_HOLD` or `FREEZE` do not suppress bloat findings).
2. `status` equals exactly `Closed` (case-sensitive). Values such as `closed`,
   `CLOSED`, `Open`, or `open` do **not** qualify.
3. `approved` equals `True` (case-insensitive boolean).
4. `valid_until` is **strictly after** the issued audit date `2026-09-01`
   (`valid_until > 2026-09-01`). Equality with the audit date does not qualify.
5. The ticket must target the table under review via `table_name` **or** via a
   name listed in `table_aliases.csv` that maps to that table.

## Finding interaction (order)

1. Autovacuum / exact-lowercase `manual` override still wins first. Holds never
   apply.
2. Compute the ordinary bloat decision (including amendment stale-cap tightening).
   If that decision would be `BLOAT_THRESHOLD_EXCEEDED` **and** a qualifying
   `BLOAT_HOLD` exists for the table, **suppress the bloat finding** and continue.
3. Then apply the ordinary stale-statistics rule. A table whose bloat was
   suppressed by a hold can still be `STALE_STATISTICS` when stale.
4. If neither autovacuum, (unsuppressed) bloat, nor stale applies, the finding is
   `none`.

## Duplicates and decoys

- If multiple tickets resolve to the same table, the **last** row in
  `change_control_tickets.csv` is authoritative.
- `dashboard_suggested_findings.csv` remains non-authoritative.
- Reindex exemption rules in the amendment are separate from change-control holds.
  A table may need both checks; a hold is not a reindex exemption and a reindex
  exemption is not a hold.

## Memo

When a hold changes the outcome (suppresses bloat, or you reject a near-miss
ticket), the local memo unit for that table must cite the ticket id (e.g. `CH-2201`)
and the word `hold` or `ticket`.
