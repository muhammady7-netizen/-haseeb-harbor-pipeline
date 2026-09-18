# Custody Letter Instruction Audit

Audit a draft letter to opposing counsel against the client's two messages (original instruction + clarification). For each line of the draft, determine whether the client's record verifies it, whether it is at odds with the record, or whether neither record speaks to it, and name the governing entry.

## What makes this non-trivial

- The clarification prevails over the original on any subject it speaks to (RP-401)
- A line citing an original entry on a subject the clarification covers is still governed by the clarification
- When a line cites a clarification entry for a *different* subject, RP-401 sends the line back to the original instruction entry for its own subject
- Lines on subjects neither record mentions are NOT_IN_RECORD with governing entry NONE
- The draft may cite entries that don't exist in either record
- Densified population: 325 draft lines with precedence, repeat-subject, NOT_IN_RECORD, person-identity, conditional-exception, cross-subject-citation and compound-position traps (CL-310/311 override CL-308/307 on interim_contact/without_prejudice subjects; RP-401 sends cross-subject CL citations back to the OI entry for the line's own subject; RP-408 makes a one-limb assertion of a compound position — e.g. ST-556's without-prejudice marking without the soft-tone limb — AT_ODDS)

## Bundle contents

- `environment/input/`: letter_lines.csv (325 draft lines), original_instruction.md (11 entries), clarification.md (8 entries), review_protocol.md (8 rules), submission_format.md (layout spec)
- `solution/files/`: answer.md, letter_line_review.csv, results.json (gold: 100 verified / 181 at_odds / 44 not_in_record / 202 clarification-governed)
- `tests/verifier.json`: 9 deterministic checks (7 core, 2 incidental): file existence, CSV header, table_equals with 325-row row_set lock, results object_equals, at-odds figure as core (markdown-tolerant, with a `(?!\d|[.,]\d)` boundary guard so `177.5`/`177,5` cannot pose as `177`), anti-hedge, and a 100+ word prose floor requiring the domain word `record` AND at least one domain keyword (`verified`, `at odds`, `clarification`, `original`, `governing`) (incidental; rejects a hollow word-repeat with no domain vocabulary)
- `task.toml`: `artifacts = []`; `tests/test.sh` copies graded `/app` deliverables into `/logs/artifacts/app` for Harbor export

## Reward shape

Core gate in `tests/score.py`: any core failure → reward 0.0. All core pass → incidental weights add toward 1.0. Gold scores exactly 1.0.

## QC packaging notes (v19)
- MAX fair harden: CL-307/308/309 override tone/behavioural_plan/concern (RP-401); CL-310/311 add conditional-exception traps on interim_contact and without_prejudice — a line whose subject is interim_contact is governed by CL-310 even when its wording addresses the behavioural plan, and a line whose subject is without_prejudice is governed by CL-311 even when its wording addresses tone; RP-401 cross-subject citation exception — when a line's cited_entry is a CL for a different subject, the OI entry for the line's own subject governs, not the CL; tighter multi-limb OI; gold recomputed by disclosed classifiers only (no FORCE_AT_ODDS / no identical-wording opposite verdicts).
- Cross-subject wording traps (e.g. ST-543..547): the same sentence may appear under two different `subject` values. Verdicts can differ because RP-401/406 weigh the line against the governing entry for **that row's subject**, not against another subject's entry. Same wording + same subject never gets opposite verdicts.
- RP-401 cross-subject citation traps (ST-581..595): when cited_entry is a CL entry for a different subject, the OI entry for the line's subject governs — the trap is that RP-401 would route the model to the CL entry for the line's subject instead. Both verdict and record_entry differ from the RP-401 answer on 8 of the 15 rows; the other 7 share the verdict but the record_entry still differs (OI vs CL).
- All AT_ODDS rows have positions that genuinely differ from the governing entry (dropped limb, wrong tone, missing place, wrong delivery/copy/addressee). No identical-wording contradictions under the same subject/governor.

- `register_table` uses `table_equals` with a closed 325-id `row_set` and `row_set_ordered=true`. Duplicate graded `line_id` values fail (`duplicate id …`); a doubled 650-row CSV cannot match the locked population. Spec-level QC replays that skip the vendored engine / `test_outputs.py` may still flag duplicated-rows as a gap — the engine rejects them.
- `solution/golden_trajectory.json` is a **hand-authored reference trajectory**, not a byte-copy of a model run. `solution/golden_results.json` holds the gold count object. Oracle reward 1.0 proves the gold deliverables are correct.
- Stability repeats under `evaluations/stability/repeat-01`, `repeat-02`, and `repeat-03` ship `result.json` only.
- Trial metadata paths are anonymized to `/workspace`.
- Difficulty vs oracle/stability `task_checksum` may differ because evaluations were packed between Harbor batches; both batteries grade the same verifier grid and gold. Re-run both on one frozen tree if a matched-checksum battery is required.
- Solvability: see `evaluations/solvability/README.md` (Oracle 1.0 proves solvable; GLM was 4/4 TOO_EASY before v18 densification — CL-310/311 conditional-exception traps and RP-401 cross-subject citation traps added to trip subject-vs-wording misrouting).
