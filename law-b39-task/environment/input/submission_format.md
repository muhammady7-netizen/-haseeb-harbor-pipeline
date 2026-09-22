# Submission format

Deliver exactly these files, in your working directory:

- `answer.md` Ã¢â‚¬â€ The written review, carrying the number of letter lines at odds with the client's record
- `letter_line_review.csv` Ã¢â‚¬â€ One row per line of the draft letter, giving its verdict and the record entry that governs it
- `results.json` Ã¢â‚¬â€ a JSON object; see below.

## `answer.md`

`answer.md` states `Letter lines at odds with the record: <count>` Ã¢â‚¬â€ the figure placed beside its label, in the very sentence that names the label (that sentence may appear anywhere in the review, including mid-paragraph). Optional markdown emphasis around the figure is fine (`124`, `**124**`, `*124*`, `__124__`). At least one hundred words of prose that use the vocabulary of that required label (including the word `record`) Each figure stands beside its label once, stated as the finding Ã¢â‚¬â€ not offered as one of two candidates.

## `letter_line_review.csv`

Header, exactly: `line_id,verdict,record_entry`
One row per record, keyed by `line_id`.
`verdict` takes exactly one of: `VERIFIED`, `AT_ODDS`, `NOT_IN_RECORD`.
The lines of `input/letter_lines.csv` appear in their numbered order, one row apiece, each carrying the verdict and the governing entry (`OI-Ã¢â‚¬Â¦` or `CL-Ã¢â‚¬Â¦`; `NONE` when neither record speaks to the subject).

Example (placeholder values):

```
line_id,verdict,record_entry
ST-100,VERIFIED,OI-200
```

## `results.json`

A JSON object with exactly these keys and nothing else:

- `verified_count` Ã¢â‚¬â€ number
- `at_odds_count` Ã¢â‚¬â€ number
- `not_in_record_count` Ã¢â‚¬â€ number
- `clarification_governed_count` Ã¢â‚¬â€ number

Shape example (placeholder values):

```json
{
  "verified_count": 0,
  "at_odds_count": 0,
  "not_in_record_count": 0,
  "clarification_governed_count": 0
}
```
