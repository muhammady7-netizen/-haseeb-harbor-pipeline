# Randomisation findings - AR-118 monitoring extract

Ledger `allocation_amendments.csv` applied first (highest revision only; void excludes
only when it is the winning revision; blank / whitespace-only fields retain the base
extract; subject_id joined case-insensitively; sites reported as S+digits; severity
lowercased; dates accepted as YYYY-MM-DD or YYYY/MM/DD; sequence_no parsed as int;
case/whitespace normalised per charter). Overall active proportion is
64.4% against the 66.7% target (5 pp tolerance;
equality at 5.0 is within).

## Strata

Outside tolerance: site/S3, severity/severe.

## Blocks

Assessed blocks outside tolerance: S2/B21, S3/B12, S3/B13, S3/B8.
Complete blocks within tolerance: S1/B3 (5 active), S1/B32 (4 active), S1/B33 (4 active), S1/B34 (4 active), S2/B14 (3 active), S2/B30 (5 active), S2/B31 (5 active), S2/B32 (4 active), S2/B33 (5 active), S2/B34 (4 active), S2/B6 (4 active), S3/B22 (3 active), S3/B31 (3 active), S3/B32 (3 active), S3/B9 (5 active).
Not assessed (incomplete or over-filled): S1/B1 (7), S1/B10 (8), S1/B2 (7), S1/B20 (7), S1/B23 (4), S1/B30 (5), S1/B31 (7), S2/B11 (3), S2/B24 (7), S2/B4 (7), S2/B5 (8), S3/B30 (7), S3/B33 (2), S3/B7 (9).

## Sequence

Out-of-sequence allocations: SUBJ-001, SUBJ-044, SUBJ-016, SUBJ-061, SUBJ-062, SUBJ-100, SUBJ-119, SUBJ-200, SUBJ-228, SUBJ-261, SUBJ-204, SUBJ-206, SUBJ-212, SUBJ-218, SUBJ-220, SUBJ-224, SUBJ-030, SUBJ-058, SUBJ-067, SUBJ-088, SUBJ-090, SUBJ-106, SUBJ-107, SUBJ-123, SUBJ-230, SUBJ-231, SUBJ-202, SUBJ-236, SUBJ-242, SUBJ-248, SUBJ-254, SUBJ-043, SUBJ-056, SUBJ-045, SUBJ-073, SUBJ-074, SUBJ-079, SUBJ-080, SUBJ-113, SUBJ-114, SUBJ-260, SUBJ-266, SUBJ-272, SUBJ-278.
Within each site, subjects are ordered by parsed randomised date then subject_id; a drop in
sequence number versus the previous subject is a finding. Equal sequence numbers are not out of sequence.
