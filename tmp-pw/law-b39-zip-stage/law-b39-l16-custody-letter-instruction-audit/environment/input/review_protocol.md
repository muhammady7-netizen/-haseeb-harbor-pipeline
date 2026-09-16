# Review protocol — letter to opposing counsel

Governs every line in `letter_lines.csv`, weighed against `original_instruction.md` and
`clarification.md`.

## RP-401 Which record prevails

On any subject the clarification speaks to, the clarification prevails. If the original instruction and the clarification take different positions on a subject, the clarification wins and the original falls away, no matter which entry the draft cites or how plainly the original was put: what the client said last is what the client instructs. For a line on a subject the clarification speaks to, the governing entry is always the clarification entry and never the original one (`RP-401`).

## RP-402 Subjects the clarification repeats

If the clarification repeats a subject in the very terms the original used, the clarification entry nonetheless governs the line, and the line is weighed against it (`RP-402`).

## RP-403 Subjects only the original speaks to

If the clarification leaves a subject alone, the original entry on that subject governs and the line is weighed against it (`RP-403`).

## RP-404 Subjects neither record speaks to

If neither record speaks to a subject — which includes a draft citing an entry that exists nowhere — nothing governs: the line's verdict is NOT_IN_RECORD and its record entry is `NONE`, however reasonable the line may read (`RP-404`).

## RP-405 How a line is weighed

Weighed against its governing entry, a line is VERIFIED when the position it takes is the entry's own, and AT_ODDS when the entry's position differs from it — the reverse, something narrower, or a different person (`RP-405`).

## RP-406 The review table

`record_entry` holds the id of the entry that governs the line, spelled as the records spell it, or `NONE` (`RP-406`).

## Figures

`verified_count` is the number of lines whose verdict is VERIFIED.
`at_odds_count` is the at odds count: the lines whose verdict is AT_ODDS.
`not_in_record_count` is the number of lines whose verdict is NOT_IN_RECORD.
`clarification_governed_count` is the number of lines whose record entry is a clarification entry (`CL-…`).
In the answer, `Letter lines at odds with the record` is the number of lines whose governing entry takes a position
other than the line's.
