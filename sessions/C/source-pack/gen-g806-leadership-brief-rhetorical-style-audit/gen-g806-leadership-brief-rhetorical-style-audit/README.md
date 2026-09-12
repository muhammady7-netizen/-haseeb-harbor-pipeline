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
83 deterministic checks (existence, headers, lexicographic order, one full coherence row per brief, full traces, results.json, disclosed memo heading/analysis for failing briefs only).
