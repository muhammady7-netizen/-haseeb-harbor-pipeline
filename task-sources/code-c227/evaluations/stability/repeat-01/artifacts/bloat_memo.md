# Table maintenance audit — 40 unique tables

40 unique tables checked against DBOPS-31 (42 input rows collapsed for T-31/T-32
duplicates). 13 are compliant and 27 carry a finding.

| Table | Size class | Bloat ratio | Finding |
|---|---|---|---|
| T-13 | large | 0.5 | AUTOVACUUM_DISABLED |
| T-17 | large | 0.4 | AUTOVACUUM_DISABLED |
| T-27 | large | 0.38 | BLOAT_THRESHOLD_EXCEEDED |
| T-04 | large | 0.1 | STALE_STATISTICS |
| T-21 | large | 0.2 | AUTOVACUUM_DISABLED |
| T-26 | large | 0.18 | BLOAT_THRESHOLD_EXCEEDED |
| T-30 | large | 0.2 | BLOAT_THRESHOLD_EXCEEDED |
| T-10 | large | 0.21 | STALE_STATISTICS |
| T-16 | large | 0.2 | BLOAT_THRESHOLD_EXCEEDED |
| T-09 | large | 0.19 | none |
| T-07 | large | 0.12 | none |
| T-15 | large | 0.2 | none |
| T-12 | large | 0.2 | none |
| T-19 | large | 0.41 | BLOAT_THRESHOLD_EXCEEDED |
| T-01 | large | 0.1 | none |
| T-06 | large | 0.25 | BLOAT_THRESHOLD_EXCEEDED |
| T-14 | large | 0.4 | BLOAT_THRESHOLD_EXCEEDED |
| T-18 | large | 0.21 | BLOAT_THRESHOLD_EXCEEDED |
| T-20 | large | 0.1 | AUTOVACUUM_DISABLED |
| T-28 | large | 0.25 | none |
| T-29 | large | 0.25 | BLOAT_THRESHOLD_EXCEEDED |
| T-31 | small | 0.3 | none |
| T-32 | small | 0.4 | none |
| T-08 | large | 0.45 | BLOAT_THRESHOLD_EXCEEDED |
| T-02 | large | 0.35 | BLOAT_THRESHOLD_EXCEEDED |
| T-03 | large | 0.15 | AUTOVACUUM_DISABLED |
| T-05 | large | 0.55 | BLOAT_THRESHOLD_EXCEEDED |
| T-11 | large | 0.41 | AUTOVACUUM_DISABLED |


## T-05 is a bloat finding (unapproved reindex)

T-05's bloat ratio of 0.55 is far over the large-table cap of 0.2. Although
maintenance_active=True, the reindex is unapproved (approved=False in
reindex_log.csv), so the exemption does not apply and the bloat check runs
normally. Finding: BLOAT_THRESHOLD_EXCEEDED.

## Other findings

T-02's bloat ratio of 0.35 is over the large-table cap with no maintenance flag, so the finding is BLOAT_THRESHOLD_EXCEEDED.
T-03 has autovacuum disabled and that check overrides later bloat review: AUTOVACUUM_DISABLED.
T-04's statistics are 45 days stale, over the 30-day limit: STALE_STATISTICS.
T-06's size_class column says small but total_pages=1000 computes as large (cap 0.2); its bloat ratio 0.25 is over that large cap: BLOAT_THRESHOLD_EXCEEDED.
T-08's size_class column is wrong — total_pages=1000 so the computed size class is large (cap 0.2), and its bloat ratio of 0.45 is over that large cap: BLOAT_THRESHOLD_EXCEEDED.
T-13 is a large table (total_pages 1000) with autovacuum disabled; autovacuum is checked first: AUTOVACUUM_DISABLED.


## Tables T-09 through T-11

- **T-09**: A large table with bloat ratio 0.19 (under the 0.20 cap) and statistics last refreshed 30 days ago. The policy says "more than 30 days ago" — 30 is not more than 30. Finding: none.
- **T-10**: Large table, bloat 0.21 under active reindex, but statistics are 31 days stale. Reindex does not exempt staleness. Finding: STALE_STATISTICS.
- **T-11**: size_class says small but total_pages=1000 computes as large; bloat 0.41 over cap, yet autovacuum is disabled and overrides first. Finding: AUTOVACUUM_DISABLED.

## Boundary equality

- **T-12**: A large table with bloat ratio exactly 0.20 — equal to the large-table cap. The policy says a table *over* its cap is BLOAT_THRESHOLD_EXCEEDED; 0.20 is not over 0.20. Finding: none.
- **T-14**: size_class says small but total_pages=1000 computes as large (cap 0.2). Bloat ratio 0.40 is over that large cap. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-15**: A large table with bloat ratio 0.200 — numerically equal to the large-table cap of 0.2. Finding: none.

## Multi-rule interaction cases

- **T-16**: Reindex expired (valid_until before audit_date), so not exempt; stale stats tighten the large cap to 0.15 and ratio 0.20 is over it. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-17**: size_class says small but total_pages=1000 computes as large; bloat and stale apply, but autovacuum is disabled and overrides first. Finding: AUTOVACUUM_DISABLED.

## Round-half-up traps

- **T-18**: Large table 205/1000 = 0.205 rounds half-up to 0.21, which is over the large cap 0.2. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-19**: size_class says small but total_pages=1000 computes as large; 405/1000 = 0.405 rounds half-up to 0.41 over large cap. Finding: BLOAT_THRESHOLD_EXCEEDED.

## Manual vacuum override

- **T-20**: A large table with autovacuum_enabled=True but vacuum_type=manual. The manual vacuum overrides and supersedes the automatic schedule. Finding: AUTOVACUUM_DISABLED.
- **T-21**: A large table with vacuum_type=manual at the bloat cap and with stale stats; the manual vacuum override is checked first. Finding: AUTOVACUUM_DISABLED.

## Stale-stats cap tightening

- **T-26**: Large table, ratio 0.18 under normal 0.20, but stale stats tighten the cap to 0.15 so 0.18 exceeds it. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-27**: size_class says small but total_pages=1000 computes as large; stale tightens cap to 0.15 and ratio 0.38 is over it. Finding: BLOAT_THRESHOLD_EXCEEDED.

## Legacy days_since_analyze field

The `days_since_analyze` field in the export is a legacy estimate and is NOT reliable.
Staleness must be computed from the `audit_date` and `last_analyzed` date fields. Several
tables have `days_since_analyze` values that differ from the actual date-based computation
by 5 days. Using the legacy field instead of computing from dates will produce incorrect
findings for those tables.

## Reindex approval expiry

- **T-28**: Large table, ratio 0.25 over cap, but approved reindex with valid_until after audit_date exempts bloat. Finding: none.
- **T-29**: Large table, ratio 0.25, maintenance_active with approved reindex, but approval expired before audit_date so not exempt. Finding: BLOAT_THRESHOLD_EXCEEDED.

## At-cap with stale stats

- **T-30**: Large table at original cap 0.20, but stale stats tighten the effective cap to 0.15 so the ratio exceeds it. Finding: BLOAT_THRESHOLD_EXCEEDED.

## bloat_ratio field is unreliable

The `bloat_ratio` field in the export is computed with Python's default rounding
(round-half-even) and gives incorrect results for rounding-boundary cases. The correct
ratio must be computed from `dead_pages / total_pages` using round-half-up. For example,
T-18 has 205 dead pages out of 1000 total: the correct ratio is 0.21 (round-half-up),
but the `bloat_ratio` field shows 0.2 (Python's round-half-even).

## Computed size class

The `size_class` column in the export is a legacy field and is NOT reliable. Size class
must be computed from `total_pages`: >= 500 is large (cap 0.2), < 500 is small (cap 0.4).

- **T-31**: total_pages=400 (< 500), so computed size class is small (cap 0.4). The
  `size_class` column says "large" (WRONG). Bloat ratio 0.30 is under the small cap 0.4.
  Finding: none. If the column's "large" were used (cap 0.2), 0.30 > 0.2 would give
  BLOAT_THRESHOLD_EXCEEDED (incorrect).
- **T-32**: total_pages=400 (< 500), computed size class is small (cap 0.4). The column
  says "large" (WRONG). Bloat ratio 0.40 equals the small cap 0.4 — at the cap, not over.
  Finding: none. If "large" were used (cap 0.2), 0.40 > 0.2 would give BLOAT (incorrect).

Several other tables (T-03, T-04, T-06, T-08, T-11, T-13, T-14, T-17, T-19, T-27) have
incorrect `size_class` column values. The audit uses the computed size class from
`total_pages` in all cases.


## Densified edge cases (T-33 through T-44)

- **T-33**: round-half-up: 41/200 = 0.205 -> 0.21. Small class (200 < 500, cap 0.4). Under cap. Finding: none.
- **T-34**: size_class says small but total_pages=500 computes large; ratio 0.20 equals cap. Finding: none. Compute from total_pages.
- **T-35**: size_class says small but total_pages=500 computes large; ratio 0.22 over cap 0.2. Finding: BLOAT_THRESHOLD_EXCEEDED. Compute from total_pages.
- **T-36**: Stale stats (35 days) tighten the large cap to 0.15; ratio 0.18 is over that tightened cap. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-37**: Reindex expired (valid_until before audit_date) so not exempt; large ratio 0.25 over cap. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-38**: Unapproved reindex (approved=False) does not exempt; small ratio 0.33 under cap. Finding: none.
- **T-39**: vacuum_type=manual with autovacuum_enabled=True, so the manual vacuum overrides the automatic schedule. Finding: AUTOVACUUM_DISABLED.
- **T-40**: days_since_analyze field says 25 but is wrong; actual date gap is 35 days stale. Finding: STALE_STATISTICS.
- **T-41**: Exact small cap boundary 0.40 equals cap. Finding: none.
- **T-42**: Stale stats tighten large cap to 0.15; ratio 0.20 is at the normal cap but over the tightened cap. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-43**: Exact ratio 0.21 under small cap. Finding: none.
- **T-44**: size_class field says medium but total_pages=600 computes large; ratio 0.83 over cap. Finding: BLOAT_THRESHOLD_EXCEEDED. Compute from total_pages.

## Densify trap T-45

T-45 is computed large from total_pages 1000 (export small is a trap); round-half-up gives ratio 0.16, and because stats are 33 days stale the large cap is tightened to 0.15, so 0.16 exceeds it: BLOAT_THRESHOLD_EXCEEDED.
