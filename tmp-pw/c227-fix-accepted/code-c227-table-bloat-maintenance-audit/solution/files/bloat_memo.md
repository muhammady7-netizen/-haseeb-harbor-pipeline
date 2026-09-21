# Table maintenance audit — 126 unique tables

126 unique tables under DBOPS-31-A + ops bulletin OB-31-C (issued audit date 2026-09-01). 32 compliant, 94 flagged. Change-control BLOAT_HOLD tickets suppress bloat only; stale and autovacuum still apply.

| Table | Size class | Bloat ratio | Finding |
|---|---|---|---|
| T-82 | large | 0.08 | STALE_STATISTICS |
| T-13 | large | 0.5 | AUTOVACUUM_DISABLED |
| T-17 | large | 0.4 | AUTOVACUUM_DISABLED |
| T-72 | large | 0.4 | AUTOVACUUM_DISABLED |
| T-27 | large | 0.38 | BLOAT_THRESHOLD_EXCEEDED |
| T-04 | large | 0.1 | STALE_STATISTICS |
| T-128 | large | 0.28 | STALE_STATISTICS |
| T-21 | large | 0.2 | AUTOVACUUM_DISABLED |
| T-54 | large | 0.14 | BLOAT_THRESHOLD_EXCEEDED |
| T-89 | small | 0.34 | STALE_STATISTICS |
| T-112 | large | 0.12 | BLOAT_THRESHOLD_EXCEEDED |
| T-113 | large | 0.1 | STALE_STATISTICS |
| T-114 | large | 0.1 | STALE_STATISTICS |
| T-116 | small | 0.37 | BLOAT_THRESHOLD_EXCEEDED |
| T-117 | small | 0.35 | STALE_STATISTICS |
| T-122 | large | 0.35 | STALE_STATISTICS |
| T-130 | small | 0.4 | STALE_STATISTICS |
| T-56 | large | 0.13 | BLOAT_THRESHOLD_EXCEEDED |
| T-81 | large | 0.1 | STALE_STATISTICS |
| T-87 | small | 0.36 | BLOAT_THRESHOLD_EXCEEDED |
| T-88 | small | 0.35 | STALE_STATISTICS |
| T-55 | large | 0.15 | BLOAT_THRESHOLD_EXCEEDED |
| T-26 | large | 0.18 | BLOAT_THRESHOLD_EXCEEDED |
| T-30 | large | 0.2 | BLOAT_THRESHOLD_EXCEEDED |
| T-51 | large | 0.17 | BLOAT_THRESHOLD_EXCEEDED |
| T-115 | large | 0.11 | BLOAT_THRESHOLD_EXCEEDED |
| T-36 | large | 0.18 | BLOAT_THRESHOLD_EXCEEDED |
| T-40 | large | 0.05 | STALE_STATISTICS |
| T-42 | large | 0.2 | BLOAT_THRESHOLD_EXCEEDED |
| T-53 | large | 0.15 | BLOAT_THRESHOLD_EXCEEDED |
| T-52 | large | 0.21 | BLOAT_THRESHOLD_EXCEEDED |
| T-45 | large | 0.16 | BLOAT_THRESHOLD_EXCEEDED |
| T-50 | large | 0.16 | STALE_STATISTICS |
| T-10 | large | 0.21 | STALE_STATISTICS |
| T-16 | large | 0.2 | BLOAT_THRESHOLD_EXCEEDED |
| T-09 | large | 0.19 | STALE_STATISTICS |
| T-100 | large | 0.19 | BLOAT_THRESHOLD_EXCEEDED |
| T-101 | small | 0.35 | STALE_STATISTICS |
| T-102 | small | 0.36 | BLOAT_THRESHOLD_EXCEEDED |
| T-103 | large | 0.1 | STALE_STATISTICS |
| T-118 | large | 0.18 | BLOAT_THRESHOLD_EXCEEDED |
| T-63 | large | 0.18 | BLOAT_THRESHOLD_EXCEEDED |
| T-64 | large | 0.21 | BLOAT_THRESHOLD_EXCEEDED |
| T-97 | large | 0.14 | BLOAT_THRESHOLD_EXCEEDED |
| T-98 | large | 0.15 | BLOAT_THRESHOLD_EXCEEDED |
| T-99 | large | 0.16 | BLOAT_THRESHOLD_EXCEEDED |
| T-104 | large | 0.1 | none |
| T-07 | large | 0.12 | none |
| T-15 | large | 0.2 | none |
| T-74 | large | 0.5 | AUTOVACUUM_DISABLED |
| T-12 | large | 0.2 | none |
| T-19 | large | 0.41 | BLOAT_THRESHOLD_EXCEEDED |
| T-85 | large | 0.23 | BLOAT_THRESHOLD_EXCEEDED |
| T-79 | small | 0.41 | BLOAT_THRESHOLD_EXCEEDED |
| T-80 | small | 0.4 | none |
| T-84 | large | 0.22 | BLOAT_THRESHOLD_EXCEEDED |
| T-108 | small | 0.41 | BLOAT_THRESHOLD_EXCEEDED |
| T-57 | small | 0.41 | BLOAT_THRESHOLD_EXCEEDED |
| T-58 | large | 0.21 | BLOAT_THRESHOLD_EXCEEDED |
| T-01 | large | 0.1 | none |
| T-06 | large | 0.25 | BLOAT_THRESHOLD_EXCEEDED |
| T-14 | large | 0.4 | BLOAT_THRESHOLD_EXCEEDED |
| T-18 | large | 0.21 | BLOAT_THRESHOLD_EXCEEDED |
| T-20 | large | 0.1 | AUTOVACUUM_DISABLED |
| T-28 | large | 0.25 | none |
| T-29 | large | 0.25 | BLOAT_THRESHOLD_EXCEEDED |
| T-31 | large | 0.2 | none |
| T-32 | large | 0.16 | none |
| T-33 | small | 0.21 | none |
| T-34 | large | 0.2 | none |
| T-35 | large | 0.22 | BLOAT_THRESHOLD_EXCEEDED |
| T-37 | large | 0.25 | BLOAT_THRESHOLD_EXCEEDED |
| T-38 | small | 0.33 | none |
| T-39 | large | 0.05 | AUTOVACUUM_DISABLED |
| T-41 | small | 0.4 | none |
| T-43 | small | 0.21 | none |
| T-44 | large | 0.83 | BLOAT_THRESHOLD_EXCEEDED |
| T-76 | small | 0.41 | BLOAT_THRESHOLD_EXCEEDED |
| T-77 | small | 0.4 | none |
| T-106 | large | 0.32 | none |
| T-59 | small | 0.4 | none |
| T-60 | small | 0.4 | none |
| T-61 | small | 0.4 | none |
| T-62 | small | 0.41 | BLOAT_THRESHOLD_EXCEEDED |
| T-66 | large | 0.28 | BLOAT_THRESHOLD_EXCEEDED |
| T-78 | small | 0.41 | BLOAT_THRESHOLD_EXCEEDED |
| T-08 | large | 0.45 | none |
| T-105 | large | 0.3 | BLOAT_THRESHOLD_EXCEEDED |
| T-120 | large | 0.28 | none |
| T-125 | large | 0.3 | BLOAT_THRESHOLD_EXCEEDED |
| T-49 | large | 0.41 | BLOAT_THRESHOLD_EXCEEDED |
| T-65 | large | 0.35 | BLOAT_THRESHOLD_EXCEEDED |
| T-75 | large | 0.21 | BLOAT_THRESHOLD_EXCEEDED |
| T-94 | large | 0.2 | none |
| T-95 | large | 0.2 | none |
| T-96 | large | 0.21 | BLOAT_THRESHOLD_EXCEEDED |
| T-119 | large | 0.3 | BLOAT_THRESHOLD_EXCEEDED |
| T-124 | large | 0.31 | BLOAT_THRESHOLD_EXCEEDED |
| T-46 | large | 0.21 | none |
| T-69 | large | 0.3 | none |
| T-70 | large | 0.26 | BLOAT_THRESHOLD_EXCEEDED |
| T-107 | large | 0.28 | BLOAT_THRESHOLD_EXCEEDED |
| T-111 | large | 0.02 | none |
| T-123 | large | 0.32 | BLOAT_THRESHOLD_EXCEEDED |
| T-47 | large | 0.23 | BLOAT_THRESHOLD_EXCEEDED |
| T-68 | large | 0.24 | BLOAT_THRESHOLD_EXCEEDED |
| T-90 | large | 0.24 | BLOAT_THRESHOLD_EXCEEDED |
| T-91 | large | 0.25 | BLOAT_THRESHOLD_EXCEEDED |
| T-92 | large | 0.26 | BLOAT_THRESHOLD_EXCEEDED |
| T-02 | large | 0.35 | BLOAT_THRESHOLD_EXCEEDED |
| T-03 | large | 0.15 | AUTOVACUUM_DISABLED |
| T-05 | large | 0.55 | BLOAT_THRESHOLD_EXCEEDED |
| T-109 | large | 0.02 | none |
| T-11 | large | 0.41 | AUTOVACUUM_DISABLED |
| T-110 | large | 0.02 | AUTOVACUUM_DISABLED |
| T-121 | large | 0.35 | none |
| T-129 | large | 0.29 | BLOAT_THRESHOLD_EXCEEDED |
| T-48 | large | 0.22 | BLOAT_THRESHOLD_EXCEEDED |
| T-67 | large | 0.25 | BLOAT_THRESHOLD_EXCEEDED |
| T-83 | large | 0.1 | none |
| T-86 | large | 0.1 | none |
| T-126 | large | 0.33 | none |
| T-71 | large | 0.05 | AUTOVACUUM_DISABLED |
| T-93 | large | 0.01 | none |
| T-127 | large | 0.05 | AUTOVACUUM_DISABLED |
| T-73 | large | 0.08 | AUTOVACUUM_DISABLED |

## T-05 is a bloat finding (unapproved reindex)

T-05's bloat ratio of 0.55 is far over the large-table cap of 0.2. Although
maintenance_active=True, the reindex is unapproved (approved=False in
reindex_log.csv), so the exemption does not apply and the bloat check runs
normally. Finding: BLOAT_THRESHOLD_EXCEEDED.

## Other findings

T-02's bloat ratio of 0.35 is over the large-table cap with no maintenance flag, so the finding is BLOAT_THRESHOLD_EXCEEDED.
T-03 has autovacuum disabled and that check overrides later bloat review: AUTOVACUUM_DISABLED.
T-04's statistics are 46 days stale, over the 30-day limit: STALE_STATISTICS.
T-06's size_class column says small but total_pages=1000 computes as large (cap 0.2); its bloat ratio 0.25 is over that large cap: BLOAT_THRESHOLD_EXCEEDED.
T-08's size_class column is wrong — total_pages=1000 so the computed size class is large (cap 0.2), and its bloat ratio of 0.45 is over that large cap: BLOAT_THRESHOLD_EXCEEDED.
T-13 is a large table (total_pages 1000) with autovacuum disabled; autovacuum is checked first: AUTOVACUUM_DISABLED.


## Tables T-09 through T-11


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
- **T-32**: total_pages=1000 (< 500), computed size class is large (cap 0.16). The column
  says "large" (WRONG). Bloat ratio 0.40 equals the small cap 0.4 — at the cap, not over.
  Finding: none. If "large" were used (cap 0.2), 0.40 > 0.2 would give BLOAT (incorrect).

Several other tables (T-03, T-04, T-06, T-08, T-11, T-13, T-14, T-17, T-19, T-27) have
incorrect `size_class` column values. The audit uses the computed size class from
`total_pages` in all cases.


## Densified edge cases (T-33 through T-44)

- **T-33**: round-half-up: 41/200 = 0.205 -> 0.21. Small class (200 < 500, cap 0.4). Under cap. Finding: none.
- **T-34**: size_class says small but total_pages=500 computes large; ratio 0.20 equals cap. Finding: none. Compute from total_pages.
- **T-35**: size_class says small but total_pages=500 computes large; ratio 0.22 over cap 0.2. Finding: BLOAT_THRESHOLD_EXCEEDED. Compute from total_pages.
- **T-36**: Stale stats (36 days) tighten the large cap to 0.15; ratio 0.18 is over that tightened cap. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-37**: Reindex expired (valid_until before audit_date) so not exempt; large ratio 0.25 over cap. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-38**: Unapproved reindex (approved=False) does not exempt; small ratio 0.33 under cap. Finding: none.
- **T-39**: vacuum_type=manual with autovacuum_enabled=True, so the manual vacuum overrides the automatic schedule. Finding: AUTOVACUUM_DISABLED.
- **T-40**: days_since_analyze field says 25 but is wrong; actual date gap is 36 days stale. Finding: STALE_STATISTICS.
- **T-41**: Exact small cap boundary 0.40 equals cap. Finding: none.
- **T-42**: Stale stats tighten large cap to 0.15; ratio 0.20 is at the normal cap but over the tightened cap. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-43**: Exact ratio 0.21 under small cap. Finding: none.
- **T-44**: size_class field says medium but total_pages=600 computes large; ratio 0.83 over cap. Finding: BLOAT_THRESHOLD_EXCEEDED. Compute from total_pages.


## Policy amendment and ops bulletin

Issued audit date 2026-09-01. Apply `policy_amendment_2026-08-20.md` and `ops_bulletin.md`. Qualifying Closed BLOAT_HOLD tickets suppress bloat only.

## Densify traps (full matrix and change-control edges)

- **T-82**: T-82 is 55 days stale against issued audit date 2026-09-01 (ignore days_since_analyze=0); dead_pages=80 / total_pages=1000 gives ratio 0.08 inside the tightened cap after any bloat hold. Finding: STALE_STATISTICS.
- **T-72**: T-72 has a manual vacuum override because vacuum_type is exactly lowercase manual with dead_pages=400 on total_pages=1000, so the finding is AUTOVACUUM_DISABLED.
- **T-128**: T-128 is 45 days stale against issued audit date 2026-09-01 (ignore days_since_analyze=0); dead_pages=280 / total_pages=1000 gives ratio 0.28 inside the tightened cap after any bloat hold. Qualifying change-control hold CH-2208b suppressed bloat, but staleness still applies. Finding: STALE_STATISTICS.
- **T-54**: T-54 computes from dead_pages=144 and total_pages=1000 (round-half-up ratio 0.14) over its computed large class after compute; 42d stale so effective cap 0.10 and 0.14 exceeds it. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-89**: T-89 is 41 days stale against issued audit date 2026-09-01 (ignore days_since_analyze=2); dead_pages=136 / total_pages=400 gives ratio 0.34 inside the tightened cap after any bloat hold. Finding: STALE_STATISTICS.
- **T-112**: T-112 computes from dead_pages=120 and total_pages=1000 (round-half-up ratio 0.12) over its computed large class after compute; 40d stale so effective cap 0.10 and 0.12 exceeds it. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-113**: T-113 is 40 days stale against issued audit date 2026-09-01 (ignore days_since_analyze=2); dead_pages=100 / total_pages=1000 gives ratio 0.1 inside the tightened cap after any bloat hold. Finding: STALE_STATISTICS.
- **T-114**: T-114 is 40 days stale against issued audit date 2026-09-01 (ignore days_since_analyze=1); dead_pages=95 / total_pages=1000 gives ratio 0.1 inside the tightened cap after any bloat hold. Finding: STALE_STATISTICS.
- **T-116**: T-116 computes from dead_pages=148 and total_pages=400 (round-half-up ratio 0.37) over its computed small class after compute; 40d stale so effective cap 0.35 and 0.37 exceeds it. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-117**: T-117 is 40 days stale against issued audit date 2026-09-01 (ignore days_since_analyze=1); dead_pages=140 / total_pages=400 gives ratio 0.35 inside the tightened cap after any bloat hold. Finding: STALE_STATISTICS.
- **T-122**: T-122 is 40 days stale against issued audit date 2026-09-01 (ignore days_since_analyze=2); dead_pages=350 / total_pages=1000 gives ratio 0.35 inside the tightened cap after any bloat hold. Qualifying change-control hold CH-2202 suppressed bloat, but staleness still applies. Finding: STALE_STATISTICS.
- **T-130**: T-130 is 40 days stale against issued audit date 2026-09-01 (ignore days_since_analyze=1); dead_pages=160 / total_pages=400 gives ratio 0.4 inside the tightened cap after any bloat hold. Qualifying change-control hold CH-2210 suppressed bloat, but staleness still applies. Finding: STALE_STATISTICS.
- **T-56**: T-56 computes from dead_pages=125 and total_pages=1000 (round-half-up ratio 0.13) over its computed large class after compute; 40d stale so effective cap 0.10 and 0.13 exceeds it. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-81**: T-81 is 40 days stale against issued audit date 2026-09-01 (ignore days_since_analyze=5); dead_pages=100 / total_pages=1000 gives ratio 0.1 inside the tightened cap after any bloat hold. Finding: STALE_STATISTICS.
- **T-87**: T-87 computes from dead_pages=144 and total_pages=400 (round-half-up ratio 0.36) over its computed small class after compute; 40d stale so effective cap 0.35 and 0.36 exceeds it. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-88**: T-88 is 40 days stale against issued audit date 2026-09-01 (ignore days_since_analyze=1); dead_pages=140 / total_pages=400 gives ratio 0.35 inside the tightened cap after any bloat hold. Finding: STALE_STATISTICS.
- **T-55**: T-55 computes from dead_pages=150 and total_pages=1000 (round-half-up ratio 0.15) over its computed large class after compute; 38d stale so effective cap 0.10 and 0.15 exceeds it. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-51**: T-51 computes from dead_pages=165 and total_pages=1000 (round-half-up ratio 0.17) over its computed large class after compute; 36d stale so effective cap 0.10 and 0.17 exceeds it. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-115**: T-115 computes from dead_pages=105 and total_pages=1000 (round-half-up ratio 0.11) over its computed large class after compute; 35d stale so effective cap 0.10 and 0.11 exceeds it. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-53**: T-53 computes from dead_pages=145 and total_pages=1000 (round-half-up ratio 0.15) over its computed large class after compute; 35d stale so effective cap 0.10 and 0.15 exceeds it. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-52**: T-52 computes from dead_pages=205 and total_pages=1000 (round-half-up ratio 0.21) over its computed large class after compute; 34d stale so effective cap 0.10 and 0.21 exceeds it. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-45**: T-45 computes from dead_pages=155 and total_pages=1000 (round-half-up ratio 0.16) over its computed large class after compute; 33d stale so effective cap 0.10 and 0.16 exceeds it. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-50**: T-50 is 33 days stale against issued audit date 2026-09-01 (ignore days_since_analyze=10); dead_pages=155 / total_pages=1000 gives ratio 0.16 inside the tightened cap after any bloat hold. Qualifying change-control hold CH-2213 suppressed bloat, but staleness still applies. Finding: STALE_STATISTICS.
- **T-09**: T-09 is 30 days stale against issued audit date 2026-09-01 (ignore days_since_analyze=35); dead_pages=190 / total_pages=1000 gives ratio 0.19 inside the tightened cap after any bloat hold. Qualifying change-control hold CH-2215 suppressed bloat, but staleness still applies. Finding: STALE_STATISTICS.
- **T-100**: T-100 computes from dead_pages=190 and total_pages=1000 (round-half-up ratio 0.19) over its computed large class after compute; 30d stale so effective cap 0.10 and 0.19 exceeds it. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-101**: T-101 is 30 days stale against issued audit date 2026-09-01 (ignore days_since_analyze=0); dead_pages=140 / total_pages=400 gives ratio 0.35 inside the tightened cap after any bloat hold. Finding: STALE_STATISTICS.
- **T-102**: T-102 computes from dead_pages=144 and total_pages=400 (ratio 0.36) over its computed small class after compute; 30d stale so effective cap 0.35 and 0.36 exceeds it; export size_class medium is ignored. Finding: BLOAT_THRESHOLD_EXCEEDED.

- **T-103**: T-103 is 30 days stale against issued audit date 2026-09-01 (ignore days_since_analyze=5); dead_pages=100 / total_pages=1000 gives ratio 0.1 inside the tightened cap after any bloat hold. Finding: STALE_STATISTICS.
- **T-118**: T-118 computes from dead_pages=180 and total_pages=1000 (round-half-up ratio 0.18) over its computed large class after compute; 30d stale so effective cap 0.10 and 0.18 exceeds it. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-63**: T-63 computes from dead_pages=180 and total_pages=1000 (round-half-up ratio 0.18) over its computed large class after compute; 30d stale so effective cap 0.10 and 0.18 exceeds it. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-64**: T-64 computes from dead_pages=210 and total_pages=1000 (round-half-up ratio 0.21) over its computed large class after compute; 30d stale so effective cap 0.10 and 0.21 exceeds it. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-97**: T-97 computes from dead_pages=140 and total_pages=1000 (round-half-up ratio 0.14) over its computed large class after compute; 30d stale so effective cap 0.10 and 0.14 exceeds it. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-98**: T-98 computes from dead_pages=150 and total_pages=1000 (round-half-up ratio 0.15) over its computed large class after compute; 30d stale so effective cap 0.10 and 0.15 exceeds it. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-99**: T-99 computes from dead_pages=160 and total_pages=1000 (round-half-up ratio 0.16) over its computed large class after compute; 30d stale so effective cap 0.10 and 0.16 exceeds it. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-74**: T-74 has a manual vacuum override because vacuum_type is exactly lowercase manual with dead_pages=500 on total_pages=1000, so the finding is AUTOVACUUM_DISABLED.
- **T-85**: T-85 computes from dead_pages=230 and total_pages=1000 (round-half-up ratio 0.23) over its computed large class after compute. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-79**: T-79 computes from dead_pages=163 and total_pages=399 (round-half-up ratio 0.41) over its computed small class after compute. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-84**: T-84 computes from dead_pages=220 and total_pages=1000 (round-half-up ratio 0.22) over its computed large class after compute. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-108**: T-108 computes from dead_pages=207 and total_pages=499 (round-half-up ratio 0.41) over its computed small class after compute. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-57**: T-57 computes from dead_pages=205 and total_pages=499 (round-half-up ratio 0.41) over its computed small class after compute. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-58**: T-58 computes from dead_pages=105 and total_pages=500 (round-half-up ratio 0.21) over its computed large class after compute. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-76**: T-76 computes from dead_pages=185 and total_pages=450 (round-half-up ratio 0.41) over its computed small class after compute; export size_class medium is ignored. Finding: BLOAT_THRESHOLD_EXCEEDED.

- **T-62**: T-62 computes from dead_pages=203 and total_pages=499 (round-half-up ratio 0.41) over its computed small class after compute; export size_class medium is ignored. Finding: BLOAT_THRESHOLD_EXCEEDED.

- **T-66**: T-66 computes from dead_pages=280 and total_pages=1000 (round-half-up ratio 0.28) over its computed large class after compute. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-78**: T-78 computes from dead_pages=164 and total_pages=400 (round-half-up ratio 0.41) over its computed small class after compute. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-105**: T-105 computes from dead_pages=300 and total_pages=1000 (round-half-up ratio 0.3) over its computed large class after compute. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-125**: T-125 computes from dead_pages=300 and total_pages=1000 (round-half-up ratio 0.3) over its computed large class after compute; ticket CH-2205 does not qualify as a Closed BLOAT_HOLD hold (status/type/validity/approval), so bloat stands. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-49**: T-49 computes from dead_pages=405 and total_pages=1000 (round-half-up ratio 0.41) over its computed large class after compute. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-65**: T-65 computes from dead_pages=350 and total_pages=1000 (round-half-up ratio 0.35) over its computed large class after compute. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-75**: T-75 computes from dead_pages=168 and total_pages=800 (round-half-up ratio 0.21) over its computed large class after compute; export size_class medium is ignored. Finding: BLOAT_THRESHOLD_EXCEEDED.

- **T-96**: T-96 computes from dead_pages=205 and total_pages=1000 (round-half-up ratio 0.21) over its computed large class after compute. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-119**: T-119 computes from dead_pages=300 and total_pages=1000 (round-half-up ratio 0.3) over its computed large class after compute. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-124**: T-124 computes from dead_pages=310 and total_pages=1000 (round-half-up ratio 0.31) over its computed large class after compute; ticket CH-2204 does not qualify as a Closed BLOAT_HOLD hold (status/type/validity/approval), so bloat stands. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-70**: T-70 computes from dead_pages=260 and total_pages=1000 (round-half-up ratio 0.26) over its computed large class after compute. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-107**: T-107 computes from dead_pages=275 and total_pages=1000 (round-half-up ratio 0.28) over its computed large class after compute. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-123**: T-123 computes from dead_pages=320 and total_pages=1000 (round-half-up ratio 0.32) over its computed large class after compute; ticket CH-2203 does not qualify as a Closed BLOAT_HOLD hold (status/type/validity/approval), so bloat stands. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-47**: T-47 computes from dead_pages=225 and total_pages=1000 (round-half-up ratio 0.23) over its computed large class after compute. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-68**: T-68 computes from dead_pages=240 and total_pages=1000 (round-half-up ratio 0.24) over its computed large class after compute. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-90**: T-90 computes from dead_pages=235 and total_pages=1000 (round-half-up ratio 0.24) over its computed large class after compute. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-91**: T-91 computes from dead_pages=245 and total_pages=1000 (round-half-up ratio 0.25) over its computed large class after compute. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-92**: T-92 computes from dead_pages=255 and total_pages=1000 (round-half-up ratio 0.26) over its computed large class after compute. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-02**: T-02 computes from dead_pages=350 and total_pages=1000 (round-half-up ratio 0.35) over its computed large class after compute; ticket CH-2100 does not qualify as a Closed BLOAT_HOLD hold (status/type/validity/approval), so bloat stands. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-110**: T-110 has a manual vacuum override because vacuum_type is exactly lowercase manual with dead_pages=20 on total_pages=1000, so the finding is AUTOVACUUM_DISABLED.
- **T-129**: T-129 computes from dead_pages=290 and total_pages=1000 (round-half-up ratio 0.29) over its computed large class after compute; ticket CH-2209b does not qualify as a Closed BLOAT_HOLD hold (status/type/validity/approval), so bloat stands. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-48**: T-48 computes from dead_pages=215 and total_pages=1000 (round-half-up ratio 0.22) over its computed large class after compute. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-67**: T-67 computes from dead_pages=250 and total_pages=1000 (round-half-up ratio 0.25) over its computed large class after compute. Finding: BLOAT_THRESHOLD_EXCEEDED.
- **T-71**: T-71 has a manual vacuum override because vacuum_type is exactly lowercase manual with dead_pages=50 on total_pages=1000, so the finding is AUTOVACUUM_DISABLED.
- **T-127**: T-127 has a manual vacuum override because vacuum_type is exactly lowercase manual with dead_pages=50 on total_pages=1000, so the finding is AUTOVACUUM_DISABLED. Ticket CH-2207 is a hold decoy and cannot override the manual vacuum rule.
- **T-73**: T-73 has a manual vacuum override because vacuum_type is exactly lowercase manual with dead_pages=50 on total_pages=600, so the finding is AUTOVACUUM_DISABLED.

## Cap-equality compliance

Ratios exactly equal to the effective cap are not over the cap.

## Dashboard decoy

`dashboard_suggested_findings.csv` is non-authoritative.

## Change-control holds

See `ops_bulletin.md`. Holds suppress bloat only; memo cites ticket id + hold/ticket.
