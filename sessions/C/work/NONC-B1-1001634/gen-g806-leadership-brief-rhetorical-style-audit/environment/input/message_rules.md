# Message rules (AUTHORITATIVE)

## Opening purpose
Every brief must open with purpose `decision`. An opening that is `evidence` or `context` incurs a 15-point penalty.

## Permitted purpose transitions
- `decision` -> `evidence` -> `context` -> `evidence` -> `context` (allowed)
- `decision` -> `context` (allowed)
- `evidence` -> `context` (allowed)
- `context` -> `evidence` (allowed)
- Any transition to `decision` after position 1 is a transition breach (10-point penalty each).
- Repeating the same purpose consecutively is a transition breach (5-point penalty each).

## Answer distance
The answer distance for a question is the position of the earliest sentence that answers it, minus 1 (0 = answered in the first sentence). An unanswered question incurs a 20-point penalty. A question answered at distance > 5 incurs a 5-point penalty.

## Word budget
Each brief has a word budget of 200 words. Exceeding the budget by more than 20 words incurs a 10-point penalty.

## Coherence score
Start from 100. Subtract all penalties. Round to the nearest integer (half-up).

## Passing score
A brief **passes** when its coherence score is **>= 80**. Briefs below 80 are failing briefs for the memo and for `passing_briefs` / `failing_briefs` counts.

## Recommended move
Recommend exactly one sentence relocation that produces the largest score improvement without changing question coverage (same answering `sentence_id` per question). If ties, use smallest movement distance, then smallest sentence ID. Format: `sentence_id:from_position->to_position`. The move must not lower the score. If no relocation improves the score, choose the smallest-distance coverage-preserving relocation that keeps the score unchanged (projected_score may equal coherence_score).

## Status vocabulary
In `question_trace.csv`, the status column uses exactly these tokens:
- `answered` when the question is answered at distance `<= 5`
- `answered_far` when the question is answered at distance `> 5`
- `unanswered` when no sentence answers the question (`answer_distance = -1`, `answer_sentence_id` empty)

## results.json schema
`results.json` contains exactly: `brief_count` (total briefs), `passing_briefs` (score >= 80), `failing_briefs` (score < 80), `avg_score` (mean of all scores, rounded to 2 decimals half-up), `total_unanswered` (sum of unanswered across all briefs), `total_breaches` (sum of transition breaches across all briefs).


## Memo format
`executive_sequence_memo.md` covers failing briefs only (`coherence_score < 80`).
Each failing brief gets a markdown heading (`#`/`##`/`###` + brief_id).
Each subsection mentions unanswered/breach status and the recommended move.
Passing briefs must not appear as memo headings.

## Column meanings
`question_count` equals the number of questions in `executive_questions.csv` (6).
`unanswered_questions` is a lexicographically sorted pipe list of unanswered question IDs, or empty.
