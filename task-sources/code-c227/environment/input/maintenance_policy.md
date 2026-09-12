# Table maintenance & vacuum policy (DBOPS-31)

This decides whether a table's maintenance state is compliant. Where the database's own
health dashboard disagrees, this policy decides.

## 1. Autovacuum

A table with autovacuum disabled is `AUTOVACUUM_DISABLED`. This is checked first and
overrides every other check for that table, whatever its current bloat ratio reads.

**Manual vacuum override:** if the `vacuum_type` field is `manual`, autovacuum is
considered disabled even when `autovacuum_enabled` is `True` — a manual vacuum
overrides and supersedes the automatic schedule, so the table no longer has
automatic autovacuum protection. A table with `vacuum_type=manual` is
`AUTOVACUUM_DISABLED` regardless of its `autovacuum_enabled` value.

## 2. Bloat ratio computation and cap by size class

**The `bloat_ratio` field in the export is computed with Python's default rounding
(round-half-even) and is NOT reliable.** The correct bloat ratio must be computed
as `dead_pages / total_pages` using **round-half-up** to 2 decimal places. The
`bloat_ratio` field may give incorrect results for ratios that fall exactly on a
rounding boundary (e.g. 0.205). Always compute from `dead_pages` and `total_pages`.

The bloat ratio is not read directly from the export — it is **computed** as
`dead_pages / total_pages`, rounded to 2 decimal places using **round-half-up**
(0.205 rounds to 0.21, not 0.20). A table whose computed bloat ratio is at or below
its size class cap is compliant; a table whose computed ratio is **over** its cap
(strictly greater than) is `BLOAT_THRESHOLD_EXCEEDED`.


Size class is determined by `total_pages`: a table with **>= 500 total pages** is
`large` (cap 0.2); a table with **< 500 total pages** is `small` (cap 0.4).

**The `size_class` column in the export is a legacy field and is NOT reliable** —
it may not match the classification computed from `total_pages`. Always compute
size class from `total_pages` using the threshold above, never read it from the
`size_class` column. When documenting size-class traps in the audit memo, cite the
plain `total_pages` digit form (e.g. 1000 / 500, not 1,000) and the compute/computed
size-class concept; mention autovacuum, reindex, or stale day counts when those
rules decide the finding.

| computed size class | total_pages threshold | max bloat ratio |
|---|---|---|
| large | >= 500 | 0.2 |
| small | < 500 | 0.4 |

Any export `size_class` value other than the computed large/small classes above
(including traps such as `medium`) is ignored — always classify from `total_pages`
and apply the corresponding large/small bloat cap.

Size class matching is case-insensitive (e.g. `Large` matches `large`). A table over its own cap is `BLOAT_THRESHOLD_EXCEEDED` — **unless** the table is marked
under an approved active reindex operation **and** appears in `reindex_log.csv`
with `approved=True` **and** the `valid_until` date in `reindex_log.csv` is on
or after the `audit_date` (i.e., `valid_until >= audit_date`). A table with
`maintenance_active=True` but no matching `approved=True` entry, or whose
approval has expired (`valid_until < audit_date`), is NOT exempt — the reindex
is unapproved or expired, and the bloat check applies normally. A table whose computed ratio
**equals** its cap (e.g. 0.20 for large) is NOT over the cap and is not flagged.

## 3. Statistics staleness

A table whose planner statistics were last refreshed more than 30 days ago is
`STALE_STATISTICS`. The staleness is computed as calendar days from the `audit_date`
and `last_analyzed` fields (both in `YYYY-MM-DD` format):
`(audit_date - last_analyzed).days`. A difference of exactly 30 days is NOT stale
(the policy says 'more than 30 days').

**The `days_since_analyze` field in the export is a legacy estimate and is NOT
reliable** — it may differ from the actual date-based computation. Always compute
staleness from the `audit_date` and `last_analyzed` date fields, never from the
`days_since_analyze` field. Using the `days_since_analyze` field will produce
incorrect results.

### Stale-stats cap tightening

When a table's statistics are stale (more than 30 days since last analyzed), the
bloat cap for that table is **reduced by 0.05** — stale statistics mean the bloat
measurement cannot be trusted, so a tighter threshold is applied. This tightening
is applied **before** the bloat check: if the tightened cap is exceeded, the finding
is `BLOAT_THRESHOLD_EXCEEDED` (not `STALE_STATISTICS`), because bloat is checked
before staleness in the finding precedence. A table whose ratio exceeds the tightened
cap but not the original cap is still `BLOAT_THRESHOLD_EXCEEDED`.

For example, a large table (normal cap 0.2) with stale stats has a tightened cap of
0.15. A ratio of 0.18 would be under the normal cap (0.18 < 0.2) but over the
tightened cap (0.18 > 0.15), so the finding is `BLOAT_THRESHOLD_EXCEEDED`.

### Processing order

Tables are processed in order of `last_analyzed` date (ascending — oldest first).
The processing order determines the sequence in which rules are evaluated and
is the order in which the audit rows should appear in the output. A table with an
earlier `last_analyzed` date is processed before a table with a later date.
If two tables have the same `last_analyzed` date, they are processed in `table_name`
alphabetical order.

## 4. Finding names

`AUTOVACUUM_DISABLED`, `BLOAT_THRESHOLD_EXCEEDED`, `STALE_STATISTICS`, or `none`.
