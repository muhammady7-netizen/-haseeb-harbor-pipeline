# Custody Letter Instruction Audit

Audit a draft letter to opposing counsel against the client's two messages (original instruction + clarification). For each line of the draft, determine whether the client's record verifies it, whether it is at odds with the record, or whether neither record speaks to it, and name the governing entry.

## What makes this non-trivial

- The clarification prevails over the original on any subject it speaks to (RP-401)
- A line citing an original entry on a subject the clarification covers is still governed by the clarification
- Lines on subjects neither record mentions are NOT_IN_RECORD with governing entry NONE
- The draft may cite entries that don't exist in either record

## Bundle contents

- `environment/input/`: letter_lines.csv (16 draft lines), original_instruction.md (11 entries), clarification.md (6 entries), review_protocol.md (6 rules), submission_format.md (layout spec)
- `solution/files/`: answer.md, letter_line_review.csv, results.json (gold)
- `tests/verifier.json`: 9 deterministic checks (file existence, prose floor, CSV header, table_equals with row_set lock, results object_equals, answer figure regex)
