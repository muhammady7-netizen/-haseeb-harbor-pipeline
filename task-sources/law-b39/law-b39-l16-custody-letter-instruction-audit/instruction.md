# Task

The short, formal letter I asked for — to the other parent's attorney, about overnight stays that go against our custodial order — has come back addressed to the wrong person, after I had already made clear who is who. I am not sending a word of it until every line has been weighed against what I actually said, first time and second time. The lines are numbered in `input/letter_lines.csv`; my first message is `input/original_instruction.md`; my later one is `input/clarification.md`; `input/review_protocol.md` explains how the two messages combine. For each line, tell me whether my record verifies it, whether it is at odds with the record, or whether the record simply never speaks to it, and name the entry that governs. Write the review to `answer.md`, the per-line table to `letter_line_review.csv`, and the four totals to `results.json`: lines verified, lines at odds with the record (the at odds count), lines not in the record at all, and lines whose governing entry comes from the clarification rather than the original. Layout is in `input/submission_format.md`.

---
Save your deliverables into your current working directory using exactly these filenames:
    - `answer.md` — The written review, carrying the number of letter lines at odds with the client's record
    - `letter_line_review.csv` — One row per line of the draft letter, giving its verdict and the record entry that governs it
    - `results.json` — a JSON object with the keys `verified_count`, `at_odds_count`, `not_in_record_count`, `clarification_governed_count`
- The exact headers, key sets, allowed values and worked examples are specified in `input/submission_format.md` — follow it precisely.
- Writing those files is the required deliverable and must be your final action; confirm each one exists before you answer.

---

## Working environment

- Your current working directory is `/app`, and it is writable.
- The read-only attachments referred to as `input/` are at `/app/input`.
- Write every deliverable into `/app`, at the exact filenames listed above.
