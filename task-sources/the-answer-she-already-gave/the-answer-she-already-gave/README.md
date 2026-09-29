# the-answer-she-already-gave

## What changed

- manifest: Fixed scoring weight sql 0.6 -> 0.0 (dead score bucket P-C7; sql_verifiers was empty but carried 0.6 weight). Applied to both root and _app mirror copies.
- manifest: Added 19th verifier `pending_attendee_has_other_response` (file_check, expected true, weight 1.0, category core). This is a cross-meeting interpretive discriminator: the model must check whether the pending attendee (Morgan Thompson, tentative on Technical Interview) has already given a definitive response (declined) on any other meeting Nathan organizes in the window (she declined Skip Level 1:1). Chained on the already-correct identification of the pending meeting and attendee; sharp because a model that reads each event in isolation answers false; oracle-proven because the golden answer is true.
- instruction: Added 9th JSON key `pending_attendee_has_other_response` (boolean) to the deliverable spec. Added a disclosure sentence: "The same person may show up as an attendee on more than one of your meetings, with different responses on each. For anyone who is still pending on one meeting, check whether they have already given a definitive response on any other meeting you are running in this window too."
- solution: Updated artifact_plan.json with the 9th key (pending_attendee_has_other_response=true). Updated final_answer.md to state the cross-meeting finding.
- manifest: Recomputed instruction_sha256 after instruction edit. Synced to _app mirror.
- review.csv: Created with 14 rows, 5 columns, byte-exact row names.

## Why it is hard

Difficulty comes from a cross-meeting interpretive relation, not from hiding information or adding volume.

The central trap: Morgan Thompson has two different responses across two different meetings Nathan runs. She DECLINED Skip Level 1:1 (already answered, not pending) and is TENTATIVE on Technical Interview (genuinely open, must chase). A model that reads each calendar event in isolation can identify the pending meeting and attendee correctly, but cannot answer `pending_attendee_has_other_response` without cross-referencing Morgan's responses across both meetings.

The v3 task was 4/4 TOO_EASY because every graded value was derivable from a single `search_calendar` call followed by reading each event's responseStatus in isolation. The 19th verifier requires the model to hold the full roster of Nathan's meetings in mind and check whether the pending attendee appears with a definitive response on any of them — a relation over an already-correct roster, not a new lookup.

Prediction (written before the change): band drops 4/4 -> 1-2/4.

## Measurement

- Generation: 7 (v7; client-feedback / hardening iteration)
- Connector: email-calendar-gym
- Verifiers: 19 (9 file_check, 5 database_state, 1 tool_execution, 3 rubric_check, 1 new file_check)
- Scoring: sql 0.0, state 0.0, rubric 0.4, trajectory 0.0; flat_verifier_scoring true; side_effect_gate true
- Forbidden tools: send_email
- Oracle: PASS 1.0 (v6, same task logic)
- GLM x4: pending (v7 upload)
- Prediction: 1-2/4 strict passes
