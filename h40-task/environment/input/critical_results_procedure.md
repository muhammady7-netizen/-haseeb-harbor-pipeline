# Critical results procedure CR-7 — Ardleigh Trust pathology

A critical result is not closed by being released. Three things must happen and each is timed
separately: the result is telephoned to the clinical team, it is acknowledged by somebody able to
act on it, and where the acknowledgement window is missed it is escalated.

Supporting trust documents (read all of them; this procedure alone is not complete):

- `site_core_hours.md` — site codes and core-hour open/close times
- `approved_roles_roster.md` — which register tokens count as an acknowledgement (including aliases)
- `bank_holidays.csv` — trust closed days that defer the tier-2 clock
- `procedure_amendment_2026-07-01.md` — dated supersession of Riverside core hours

## Windows

| Tier | Telephone within | Acknowledged within | Clock |
|---|---|---|---|
| 1 | 30 minutes | 60 minutes | runs continuously |
| 2 | 240 minutes | 480 minutes | core hours only |

Both windows are measured from the **start of the clock** and both are inclusive: a tier 1
result acknowledged at exactly 60 minutes is within its window, not a breach.

## When the clock starts

For a **tier 1** result the clock starts the moment the result is released, whatever the hour.
Tier 1 is the tier that cannot wait for the morning, and giving a result released at night the
core-hours grace removes every out-of-hours breach from the audit.

For a **tier 2** result the clock may start only during that row's **site core hours** on an
**open** day. Site open/close times are in `site_core_hours.md` (matched by the register `site`
column), except where a dated amendment supersedes them for a release date. Open days are every calendar day including weekends, **except** dates listed in
`bank_holidays.csv`.

Tier-2 start rules:

1. If the release falls on a closed day, the clock starts at that site's open time on the next
   open morning (skip every closed date in `bank_holidays.csv`).
2. If the release is before site open on an open day, the clock starts at open that morning.
3. If the release is at or after site close on an open day, the clock starts at open on the next
   open morning (again skipping closed dates).
4. Otherwise the clock starts at the release timestamp.

Once the clock has started it runs without pausing; "core hours only" refers to when the clock
may start, not when it ticks. If a telephone notification is recorded before the tier-2 clock has
started, treat it as occurring at clock start (notification_minutes measured from clock start is
0). The same rule applies to an acknowledgement timestamp that falls before clock start.

## Timestamps on the register

Timestamps may appear as ISO `YYYY-MM-DDTHH:MM` or space-separated `YYYY-MM-DD HH:MM`. Treat both
as the same instant. Ignore any register row whose `result_id` is empty or begins with `#`
(comment / export noise). Extra columns such as `lab_batch` and `notes` are informational only.

## Who can acknowledge

An acknowledgement counts only where the register token matches an approved role or alias listed
in `approved_roles_roster.md`. Matching is exact against that roster (canonical token or alias
spelling). An acknowledgement recorded against any other role is **not** an acknowledgement. The
result stands unacknowledged and its window keeps running, however promptly the entry was made.
This is recorded as its own finding as well, because it is a training issue rather than a delay.

## Escalation

Where the acknowledgement window has been missed, the result must be escalated to the on-call
consultant and the escalation recorded in the escalation register. A missed acknowledgement
window with **no** escalation on the register is a second, separate finding: the first is a
delay, the second is that nobody picked the delay up.

Where the acknowledgement was made inside its window, no escalation is required and the absence
of one is not a finding.

## Reporting

Late notifications, late acknowledgements, acknowledgements by an unapproved role and missing
escalations are four separate counts. One result can appear in more than one of them, so they do
not add up to the number of results with a finding.
