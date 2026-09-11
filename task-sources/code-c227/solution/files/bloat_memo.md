# Table maintenance audit — 17 tables

17 tables checked against DBOPS-31. 8 are compliant and 9 carry a
finding.

| Table | Size class | Bloat ratio | Finding |
|---|---|---|---|
| T-01 | large | 0.1 | none |
| T-02 | large | 0.35 | BLOAT_THRESHOLD_EXCEEDED |
| T-03 | small | 0.15 | AUTOVACUUM_DISABLED |
| T-04 | small | 0.1 | STALE_STATISTICS |
| T-05 | large | 0.55 | none |
| T-06 | small | 0.25 | none |
| T-07 | large | 0.12 | none |
| T-08 | small | 0.45 | BLOAT_THRESHOLD_EXCEEDED |
| T-09 | large | 0.19 | none |
| T-10 | large | 0.21 | STALE_STATISTICS |
| T-11 | small | 0.41 | AUTOVACUUM_DISABLED |
| T-12 | large | 0.20 | none |
| T-13 | small | 0.40 | none |
| T-14 | large | 0.55 | STALE_STATISTICS |
| T-15 | small | 0.10 | AUTOVACUUM_DISABLED |
| T-16 | small | 0.25 | none |
| T-17 | small | 0.45 | BLOAT_THRESHOLD_EXCEEDED |

## T-05 is not a bloat finding

T-05's bloat ratio of 0.55 is far over the large-table cap of 0.2, which
looks like `BLOAT_THRESHOLD_EXCEEDED`. The table is marked under an approved active reindex
operation, and the policy exempts a table under active maintenance from the bloat check for
the duration of the operation. The finding is `none`.

## Other findings

T-02's bloat ratio of 0.35 is over the large-table cap with no maintenance flag:
`BLOAT_THRESHOLD_EXCEEDED`. T-03 has autovacuum disabled: `AUTOVACUUM_DISABLED`, checked
before its bloat ratio is even considered. T-04's statistics are 45 days stale, over the
30-day limit: `STALE_STATISTICS`. T-08 is judged against the small size class
cap rather than the large one, and its bloat ratio of 0.45 is over that cap:
`BLOAT_THRESHOLD_EXCEEDED`.


## Tables T-09 through T-17

- **T-09**: A large table with bloat ratio 0.19 (under the 0.20 cap) and statistics last refreshed 30 days ago. The policy says "more than 30 days ago" — 30 is not more than 30. Finding: none.
- **T-10**: A large table with bloat ratio 0.21 (over the 0.20 cap), under an active reindex operation, with statistics 31 days old. The reindex exemption applies only to the bloat check — not to statistics staleness. Finding: STALE_STATISTICS.
- **T-11**: A small table with bloat ratio 0.41 (over the 0.40 cap) and autovacuum disabled. Autovacuum is checked first and overrides every other check. Finding: AUTOVACUUM_DISABLED.
- **T-12**: A large table with bloat ratio 0.20, exactly at the cap. The policy says "over its own cap" — 0.20 is not over 0.20. Finding: none.
- **T-13**: A small table with bloat ratio 0.40, exactly at the cap. Same boundary logic as T-12. Finding: none.
- **T-14**: A large table with bloat ratio 0.55 (over cap) under active reindex, with statistics 45 days old. Reindex exempts bloat but NOT stale stats (45 > 30). Finding: STALE_STATISTICS.
- **T-15**: A small table with bloat ratio 0.10 (under cap) but autovacuum disabled, with stats 60 days old. Autovacuum is checked first and overrides stale stats. Finding: AUTOVACUUM_DISABLED.
- **T-16**: A small table with bloat ratio 0.25. Judged against the small cap (0.40), not the large cap (0.20). 0.25 < 0.40. Finding: none.
- **T-17**: A small table with bloat ratio 0.45. Judged against the small cap (0.40). 0.45 > 0.40. Finding: BLOAT_THRESHOLD_EXCEEDED.
