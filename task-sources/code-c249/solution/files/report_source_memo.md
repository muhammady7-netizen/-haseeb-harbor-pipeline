# Recurring report source-selection audit — 10 rows

10 logged runs checked against REPORTING-OPS-2, plus the required job roster.
4 rows are compliant and 6 carry a finding.

| Run | Job | Run date | Source used | Reported rows | Finding |
|---|---|---|---|---|---|
| RUN-01 | weekly-journal-brief | 2026-06-29 | archive | 412 | none |
| RUN-02 | weekly-journal-brief | 2026-07-13 | live | 388 | ROW_COUNT_MISMATCH |
| RUN-03 | monthly-report | 2026-08-03 |  | 0 | MISSING_TAIL_MERGE |
| RUN-04 | week-ahead-briefing | 2026-07-20 | archive | 470 | SOURCE_MISMATCH |
| RUN-05 | weekly-journal-brief | 2026-07-06 | archive | 305 | none |
| RUN-06 | weekly-journal-brief | 2026-07-07 | archive | 401 | SOURCE_MISMATCH |
| RUN-07 | week-ahead-briefing | 2026-07-06 | live | 350 | SOURCE_MISMATCH |
| RUN-08 | monthly-report | 2026-09-07 | live | 520 | none |
| RUN-09 | weekly-journal-brief | 2026-07-05 | live | 290 | SOURCE_MISMATCH |
| RUN-10 | week-ahead-briefing | 2026-07-07 | live | 445 | none |

## RUN-05 is not a source-mismatch finding

RUN-05 ran on 2026-07-06, the cutover date itself, and used the archive source. That
looks premature if you assume the switch to live happens starting on the cutover date. But
the standard's cutover rule is inclusive: a run dated **on or before** 2026-07-06 uses
archive, and only a run dated **after** 2026-07-06 switches to live. RUN-05's own row
count also matches the archive snapshot exactly. The finding is `none`.

## RUN-07 is a source-mismatch on the cutover date

RUN-07 ran on 2026-07-06, the cutover date, but used the live source. The cutover rule
is inclusive of the cutover date: on or before 2026-07-06 means archive, not live. Using
live on the cutover date is premature: `SOURCE_MISMATCH`.

## RUN-08 is not a missing tail merge

RUN-08 is a monthly report dated 2026-09-07, which is the second monthly report after
the cutover. Only the first monthly report after the cutover needs the tail merge.
RUN-03 was the first post-cutover monthly report (2026-08-03) and it was the one that
failed the tail-merge check. RUN-08 does not need a tail merge: `none`.

## RUN-09 is a source-mismatch before the cutover

RUN-09 ran on 2026-07-05, which is before the cutover date, but used the live source.
Before or on the cutover date, the correct source is archive. Using live before the
cutover is premature: `SOURCE_MISMATCH`.

## RUN-06 is a source-mismatch after the cutover

RUN-06 ran on 2026-07-07, which is after the cutover date, but used the archive source.
After the cutover date, the correct source is live. Using archive after the cutover is
stale: `SOURCE_MISMATCH`.

## Other findings

RUN-02 correctly used the live source after the cutover, but its reported row count does
not match the pipeline's own live-source snapshot for that run: `ROW_COUNT_MISMATCH`.
RUN-03, the first monthly report generated after the cutover, never applied the required
archive tail merge: `MISSING_TAIL_MERGE`. RUN-04 ran after the cutover but still pulled
from archive instead of live: `SOURCE_MISMATCH`.
