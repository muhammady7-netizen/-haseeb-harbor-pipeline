# Recurring report source-selection standard (REPORTING-OPS-2)

This decides which source a recurring weekly or monthly reporting job should have pulled
from, and it decides whether the pipeline's own row counts are internally consistent. Where
a run log disagrees with this standard, this standard decides.

## 1. Weekly and week-ahead source cutover

Weekly-journal-brief and week-ahead-briefing runs must pull from the `archive` source for
any run date **on or before** 2026-07-06, and from the `live` source for any run date
**after** 2026-07-06. The cutover date itself is still archive — a run dated exactly on
2026-07-06 using archive is correct, not premature. A run whose recorded source does not
match this rule for its own run date is `SOURCE_MISMATCH`.

## 2. Row-count consistency

Where the pipeline's own source-row-count snapshot is available for a run, the run's
reported row count must equal the snapshot's count for whichever source it used. A
mismatch is `ROW_COUNT_MISMATCH`.

## 3. Monthly tail merge

The first monthly report generated after the 2026-07-06 cutover must merge in the
archive source's tail days (the days between the start of that month and the cutover) before
synthesizing the month's weekly briefs. A first-post-cutover monthly report that skipped this
tail merge is `MISSING_TAIL_MERGE`. Later monthly reports do not need a tail merge.

## 4. Required recurring jobs

Every job on the required recurring roster
(weekly-journal-brief, week-ahead-briefing, monthly-report) must have at least one run logged. A job with no run at all is
`MISSING_JOB`.

## Finding names

`SOURCE_MISMATCH`, `ROW_COUNT_MISMATCH`, `MISSING_TAIL_MERGE`, `MISSING_JOB`, or `none`
where the run is compliant.
