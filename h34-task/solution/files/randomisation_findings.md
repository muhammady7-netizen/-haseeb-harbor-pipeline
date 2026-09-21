# Randomisation findings - AR-118 monitoring extract

Ledger `allocation_amendments.csv` applied first (highest revision only; void excludes
only when it is the winning revision; blank / whitespace-only fields retain the base
extract; subject_id joined case-insensitively; sites reported as S+digits; severity
lowercased; dates accepted as YYYY-MM-DD or YYYY/MM/DD; sequence_no parsed as int;
case/whitespace normalised per charter). Overall active proportion is
66.1% against the 66.7% target (5 pp tolerance;
equality at 5.0 is within).

## Strata

Outside tolerance: site/S1, site/S3.

## Blocks

Assessed blocks outside tolerance: S3/B8.
Complete blocks within tolerance: S1/B3 (5 active), S2/B6 (4 active), S3/B9 (5 active).
Not assessed (incomplete or over-filled): S1/B1 (7), S1/B2 (7), S2/B4 (7), S2/B5 (8), S3/B7 (9).

## Sequence

Out-of-sequence allocations: SUBJ-001, SUBJ-044, SUBJ-016, SUBJ-030, SUBJ-058, SUBJ-043, SUBJ-056, SUBJ-045.
Within each site, subjects are ordered by parsed randomised date then subject_id; a drop in
sequence number versus the previous subject is a finding. Equal sequence numbers are not out of sequence.
