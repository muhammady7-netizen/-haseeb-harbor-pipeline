# Brief Coherence Evaluation

Evaluate whether leadership briefs answer executive questions in a usable decision sequence.

## Inputs
- brief_sentences.csv: sentence_id, brief_id, position, purpose, word_count, question_ids
- executive_questions.csv: question_id, executive_role, priority
- message_rules.md: required opening purpose, permitted transitions, answer-distance limits, word budgets, passing score (80), trace status vocabulary (`answered`|`answered_far`|`unanswered`)

## Deliverables
- brief_coherence.csv: brief_id, word_count, question_count, unanswered_questions, transition_breaches, coherence_score, recommended_move, projected_score
- question_trace.csv: brief_id, question_id, priority, answer_sentence_id, answer_distance, status (`answered`|`answered_far`|`unanswered`; unanswered distance `-1`)
- executive_sequence_memo.md: `#`/`##`/`###` heading per failing brief only; subsection mentions unanswered/breach + recommended move
- results.json: brief_count, passing_briefs, failing_briefs, avg_score (2 decimal half-up), total_unanswered, total_breaches

## Verifier
77 verifier.json deterministic checks (existence, headers, lexicographic order, one full coherence row per brief, full traces, results.json, memo content-word checks for failing briefs, memo-omit checks for passing briefs) plus 2 pytest row-count guards (brief_coherence.csv = 8 rows, question_trace.csv = 48 rows) that reject duplicated-row submissions. No format-only regex on .md prose; memo substance graded by Harbor Check GLM.
