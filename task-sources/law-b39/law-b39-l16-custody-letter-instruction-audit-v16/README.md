# Custody Letter Instruction Audit

Audit a draft letter to opposing counsel against the client's two messages (original instruction + clarification). For each line of the draft, determine whether the client's record verifies it, whether it is at odds with the record, or whether neither record speaks to it, and name the governing entry.

## What makes this non-trivial

- The clarification prevails over the original on any subject it speaks to (RP-401)
- A line citing an original entry on a subject the clarification covers is still governed by the clarification
- Lines on subjects neither record mentions are NOT_IN_RECORD with governing entry NONE
- The draft may cite entries that don't exist in either record
- Densified population: 207 draft lines with precedence, repeat-subject, NOT_IN_RECORD, and person-identity traps

## Bundle contents

- `environment/input/`: letter_lines.csv (207 draft lines), original_instruction.md (11 entries), clarification.md (6 entries), review_protocol.md (6 rules), submission_format.md (layout spec)
- `solution/files/`: answer.md, letter_line_review.csv, results.json (gold: 82 verified / 89 at_odds / 36 not_in_record / 83 clarification-governed)
- `tests/verifier.json`: 9 deterministic checks (7 core, 2 incidental): file existence, CSV header, table_equals with 207-row row_set lock, results object_equals, at-odds figure as core (markdown-tolerant), anti-hedge, and a 60+ word prose floor requiring the domain word `record` (incidental; not a keyword-set lookahead soup)
- `task.toml`: `artifacts = []`; `tests/test.sh` copies graded `/app` deliverables into `/logs/artifacts/app` for Harbor export

## Reward shape

Core gate in `tests/score.py`: any core failure → reward 0.0. All core pass → incidental weights add toward 1.0. Gold scores exactly 1.0.
