# Randomisation charter RB-3 — study AR-118, monitoring extract

## Allocation

Subjects are randomised 2:1 to
active against control, a target active proportion of 66.7%. Randomisation is
in permuted blocks of 6 **within each site**, with a target split of
4 active to 2 control per block.

## Source-record amendments

`allocations.csv` is the monitoring extract and `allocation_amendments.csv` is its
binding correction ledger. Apply the ledger before running any test.

**Normalisation (both files):** trim leading and trailing whitespace on every text
field. A field that is empty or whitespace-only after trim is **blank**. Match
`record_status` and `arm` **case-insensitively** after trim (`ACTIVE`/` Active `
count as active; `VOID`/` void ` count as void). Match `subject_id` **case-insensitively**
after trim when joining the ledger to the base extract (`subj-028` and `SUBJ-028` are
the same subject). For subjects that exist in the base extract, report the base
extract's trimmed `subject_id`; for ledger-only subjects, report the trimmed winning
ledger `subject_id`.

Match `site` case-insensitively after trim, then **report** each site level as capital
`S` followed by its digits (`s2`, ` S2 `, and `S2` all report as `S2`). Match
`disease_severity` case-insensitively after trim and **report** the level lowercased
(`Mild` / ` MILD ` → `mild`). Parse `sequence_no` as an integer after trim (`08` and
`8` are the same sequence). Parse `randomised_date` after trim as a calendar date in
exactly `YYYY-MM-DD` or `YYYY/MM/DD` (same Y-M-D); compare dates as calendar dates,
never as raw strings.

For each `subject_id`, use **only** the row with the highest numeric `revision`.
Superseded lower revisions are discarded entirely — do **not** cascade them. If the
highest revision has `record_status=void`, exclude that subject entirely — including
subjects that exist in the base extract. A void on a lower revision does **not**
exclude the subject when a later revision is `current`; the later current row restores
the subject.

Otherwise replace the base extract values with every non-blank value supplied by that
highest revision only. A blank amendment field on the winning row means “retain the
**base extract** value,” not the value from any superseded amendment. Subjects present
only in the ledger are included only when their highest revision is not void and
supplies all allocation fields. Do not count superseded lower revisions. The ledger may
revise `site`, `disease_severity`, `block_id`, `sequence_no`, `arm`, and
`randomised_date`.

## Test 1 — overall allocation drift

The active proportion across the whole study must sit within
**5 percentage points** of the target. Report the proportion to one
decimal place, rounded **half-up** (not banker's / half-even), and compare the absolute
difference of that reported figure against the tolerance. Equality at exactly 5.0
percentage points is **within** tolerance; only a difference strictly greater than 5.0
is outside.

## Test 2 — stratification balance

The study stratifies on **site** and on **disease severity**. Every level of every
stratification factor is assessed separately, and each must sit within
**8 percentage points** of the target active proportion. Equality at exactly 8.0
percentage points is **within** tolerance for a stratum level.

The stratum tolerance is wider than the overall tolerance because the levels carry fewer
subjects. A level outside it is a finding against that level, not against the study as a
whole; the two tests are reported separately and a study can fail either without failing the
other.

## Test 3 — block balance

A block is assessed only when it is **complete** — exactly 6 allocations issued under
that `(site, block_id)` after the ledger is applied. A block still filling (fewer than 6)
or over-filled (more than 6) is not assessed and is not a finding.

A complete block is a deviation only when its active count is **below 3 or
above 5**. A block at 3 or 5 active departs
from the 4:2 target and is **within
tolerance**: permuted blocks are expected to vary around the target, and the tolerance exists
precisely so that ordinary variation is not reported as a deviation.

## Test 4 — allocation sequence

Within each site, sequence numbers are issued in ascending order as subjects are randomised.
Sort each site's subjects by randomisation date ascending (parsed calendar date), breaking
same-date ties by `subject_id` ascending (the reported id), then walk the list: a subject
whose sequence number is **lower** than that of the subject randomised immediately before
it in the same site was allocated out of sequence. Count one finding per such subject.

Sequence integrity is a site-level test. Sequence numbers restart at 1 in each site, so
comparing them across sites finds deviations that are not there. A subject moved into a
site by the ledger is ordered inside that site's date/`subject_id` walk using the
post-ledger fields.

## Reporting

The four tests produce four separate counts. A subject or a block can appear in more than one
of them, and the counts are never added together. On `stratum_balance.csv`, leave
`out_of_sequence` blank on the overall row and on severity rows; record the per-site counts
only on `factor=site` rows.
