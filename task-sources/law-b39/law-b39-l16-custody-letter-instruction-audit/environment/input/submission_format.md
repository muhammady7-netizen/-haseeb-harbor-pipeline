# Submission format

Deliver exactly these files, in your working directory:

- `answer.md` — The written review, carrying the number of letter lines at odds with the client's record
- `letter_line_review.csv` — One row per line of the draft letter, giving its verdict and the record entry that governs it
- `results.json` — a JSON object; see below.

## `answer.md`

`answer.md` states `Letter lines at odds with the record: <count>` — the figure placed beside its label, in the very sentence that names the label (that sentence may appear anywhere in the review, including mid-paragraph). Optional markdown emphasis around the figure is fine (`124`, `**124**`, `*124*`, `__124__`). At least one hundred words of prose that use the vocabulary of that required label (including the word `record`). Each figure stands beside its label once, stated as the finding — not offered as one of two candidates.

## `letter_line_review.csv`

Header, exactly: `line_id,verdict,record_entry`
One row per record, keyed by `line_id`.
`verdict` takes exactly one of: `VERIFIED`, `AT_ODDS`, `NOT_IN_RECORD`.
The lines of `input/letter_lines.csv` appear in their numbered order, one row apiece, each carrying the verdict and the governing entry (`OI-…` or `CL-…`; `NONE` when neither record speaks to the subject).

Example (placeholder values):

```
line_id,verdict,record_entry
ST-100,VERIFIED,OI-200
```

## `results.json`

A JSON object with exactly these keys and nothing else:

- `verified_count` — number
- `at_odds_count` — number
- `not_in_record_count` — number
- `clarification_governed_count` — number

Shape example (placeholder values):

```json
{
  "verified_count": 0,
  "at_odds_count": 0,
  "not_in_record_count": 0,
  "clarification_governed_count": 0
}
```
