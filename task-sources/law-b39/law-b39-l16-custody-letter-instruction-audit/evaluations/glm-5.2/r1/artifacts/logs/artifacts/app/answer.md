# Review of draft letter lines against the client's record

I weighed every numbered line in `input/letter_lines.csv` against the client's two messages, using `input/review_protocol.md` to decide which entry governs. On any subject the clarification speaks to, the clarification prevails over the original instruction; on subjects the clarification leaves alone, the original entry governs; on subjects neither record mentions, no entry governs and the verdict is NOT_IN_RECORD. The table in `letter_line_review.csv` gives the verdict and governing record entry for each line, and `results.json` carries the four totals.

Letter lines at odds with the record: 154

The at-odds lines are those whose governing entry takes a position other than the line's: a different addressee, a narrower or broader behavioural plan, a concern limb the client withdrew, a delivery method other than post, a tone other than firm formal brief, or an overnight, naming, accounts, signature, or request position that falls short of the governing entry. Lines not in the record at all are separate: they have no governing entry because neither the original instruction nor the clarification speaks to that subject. Lines verified by the record match the governing entry's own position.
