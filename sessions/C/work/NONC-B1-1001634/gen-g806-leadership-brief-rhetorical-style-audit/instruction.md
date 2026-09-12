# Task

Read `/app/input/brief_sentences.csv`, `/app/input/executive_questions.csv`, and `/app/input/message_rules.md`. Sentences contain `sentence_id,brief_id,position,purpose,word_count,question_ids`; questions contain `question_id,executive_role,priority`; rules define required opening purpose, permitted purpose transitions, answer-distance limits, and brief word budgets.

Evaluate whether each leadership brief answers executive questions in a usable decision sequence. For every brief, map each question to its earliest answering sentence, calculate answer distance from the opening, and detect unanswered questions. Validate the purpose-transition chain and determine whether the opening states a decision, evidence, or context as defined in the rules. Compute a coherence score by subtracting the specified penalties from 100 (round half-up to the nearest integer). Recommend exactly one sentence relocation that produces the largest score improvement without changing question coverage (same answering `sentence_id` per question); ties use smallest movement distance, then smallest sentence ID. Format the move as `sentence_id:from_position->to_position`. The move must not lower the score; if no relocation improves the score, choose the smallest-distance coverage-preserving relocation that keeps the score unchanged. This is a structural sequencing analysis, not a review of rhetorical phrases.

## Scoring contract (must match message_rules.md)

- Start at 100. Opening purpose other than `decision`: −15 (this is an opening penalty, not a transition breach).
- After position 1, any transition into `decision`: −10 per event (counts as a transition breach).
- Consecutive identical purposes: −5 per event (counts as a transition breach).
- Unanswered question: −20. Answer distance `position-1` greater than 5: −5.
- Word count greater than 220: −10.
- **Passing score threshold is 80.** Briefs with `coherence_score >= 80` pass; below 80 fail.
- `results.json` `avg_score` is the mean of the eight coherence scores, rounded half-up to **two decimal places**.

## Trace status vocabulary

In `question_trace.csv`, `status` must be exactly one of:
- `answered` — question answered at distance `<= 5`
- `answered_far` — question answered at distance `> 5`
- `unanswered` — no answering sentence; set `answer_sentence_id` empty and `answer_distance` to `-1`

## Deliverables

`question_count` in `brief_coherence.csv` is the number of rows in `executive_questions.csv` (always **6** for this pack). `unanswered_questions` is a sorted pipe-delimited list of unanswered `question_id` values, or empty when none.

## Memo format (graded)

In `executive_sequence_memo.md`:
- Include a markdown heading line (`#`, `##`, or `###` followed by the brief id, e.g. `## B-02` or `### B-02`) **only** for each brief with `coherence_score < 80`.
- Under each failing-brief heading, state unanswered status, transition-breach status, and the recommended relocation (the words unanswered/breach and recommended must appear in that subsection).
- Do **not** give a markdown heading to any brief with `coherence_score >= 80`.

## Deliverables continued

Write `/app/brief_coherence.csv` with `brief_id,word_count,question_count,unanswered_questions,transition_breaches,coherence_score,recommended_move,projected_score`. Write `/app/question_trace.csv` with `brief_id,question_id,priority,answer_sentence_id,answer_distance,status`. Write `/app/executive_sequence_memo.md` with one concise subsection **only** for each brief below the passing score (80). Write `/app/results.json` with `brief_count`, `passing_briefs`, `failing_briefs`, `avg_score`, `total_unanswered`, `total_breaches`.

## Verification

Reject malformed headers, repeated sentence positions, duplicate IDs, unknown question references, nonpositive word counts, or missing rules. Sort briefs and questions lexicographically. Recalculate projected scores by applying the proposed move, ensure no recommendation lowers coverage or score, require sorted pipe lists for unanswered question IDs, and confirm all four files exist before completion.

## Working environment

- Your current working directory is `/app`, and it is writable.
- The read-only attachments referred to as `input/` are at `/app/input`.
- Write every deliverable into `/app`, at the exact filenames listed above. All deliverables must be the final action; confirm each one exists before you answer.


## Memo format

For each failing brief (B-02, B-03, B-04, B-05, B-06, B-08), the memo must:
- Name the brief ID in a heading (e.g. `### B-02`)
- State the status (unanswered question or transition breach)
- Recommend a specific sentence move (e.g. `S-007:7->8`)

Do NOT include passing briefs (B-01, B-07) in the memo.

The memo should be at least 200 characters.
