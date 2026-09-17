# Custody Letter Instruction Audit

Audit a draft letter to opposing counsel against the client's two messages (original instruction + clarification). For each line of the draft, determine whether the client's record verifies it, whether it is at odds with the record, or whether neither record speaks to it, and name the governing entry.

## What makes this non-trivial

- The clarification prevails over the original on any subject it speaks to (RP-401)
- A line citing an original entry on a subject the clarification covers is still governed by the clarification
- Lines on subjects neither record mentions are NOT_IN_RECORD with governing entry NONE
- The draft may cite entries that don't exist in either record
- Densified population: 290 draft lines with precedence, repeat-subject, NOT_IN_RECORD, and person-identity traps

## Bundle contents

- `environment/input/`: letter_lines.csv (290 draft lines), original_instruction.md (11 entries), clarification.md (6 entries), review_protocol.md (6 rules), submission_format.md (layout spec)
- `solution/files/`: answer.md, letter_line_review.csv, results.json (gold: 85 verified / 156 at_odds / 49 not_in_record / 168 clarification-governed)
- `tests/verifier.json`: 9 deterministic checks (7 core, 2 incidental): file existence, CSV header, table_equals with 290-row row_set lock, results object_equals, at-odds figure as core (markdown-tolerant), anti-hedge, and a 60+ word prose floor requiring the domain word `record` (incidental; not a keyword-set lookahead soup)
- `task.toml`: `artifacts = []`; `tests/test.sh` copies graded `/app` deliverables into `/logs/artifacts/app` for Harbor export

## Reward shape

Core gate in `tests/score.py`: any core failure → reward 0.0. All core pass → incidental weights add toward 1.0. Gold scores exactly 1.0.

## QC packaging notes (v17)
- MAX fair harden: CL-307/308/309 override tone/behavioural_plan/concern (RP-401); tighter multi-limb OI; gold recomputed by disclosed classifiers only (no FORCE_AT_ODDS / no identical-wording opposite verdicts).
- Cross-subject wording traps (e.g. ST-543..547): the same sentence may appear under two different `subject` values. Verdicts can differ because RP-401/406 weigh the line against the governing entry for **that row's subject**, not against another subject's entry. Same wording + same subject never gets opposite verdicts.
- All AT_ODDS rows have positions that genuinely differ from the governing entry (dropped limb, wrong tone, missing place, wrong delivery/copy/addressee). No identical-wording contradictions under the same subject/governor.

- `register_table` uses `table_equals` with a closed 230-id `row_set` and `row_set_ordered=true`. Duplicate graded `line_id` values fail (`duplicate id …`); a doubled 460-row CSV cannot match the locked population. Spec-level QC replays that skip the vendored engine / `test_outputs.py` may still flag duplicated-rows as a gap — the engine rejects them.
- `solution/golden_trajectory.json` is a **hand-authored reference trajectory**, not a byte-copy of a model run (GLM difficulty is 0/4). `solution/golden_results.json` holds the gold count object. Oracle reward 1.0 proves the gold deliverables are correct.
- Stability repeats under `evaluations/stability/repeat-01`, `repeat-02`, and `repeat-03` ship `result.json` only.
- Trial metadata paths are anonymized to `/workspace`.
- Difficulty vs oracle/stability `task_checksum` may differ because evaluations were packed between Harbor batches; both batteries grade the same verifier grid and gold. Re-run both on one frozen tree if a matched-checksum battery is required.
- Solvability: see `evaluations/solvability/README.md` (Oracle 1.0 proves solvable; no non-oracle `r1/` while the proxy only exposes glm-5.2 at 0/4).
