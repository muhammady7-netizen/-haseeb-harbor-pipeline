# Connector Task Status — Oct 7, 2026 (Final)

## Thread Task (the-thread-that-outlived-its-own-start) — FINAL VERSION v21
- **Portal URL:** https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-98f78b7a0b5ab5726589be24f5f12113-v1
- **Run ID:** evaluation-0fbdaa74d8d845b2
- **Content ID:** content-98f78b7a0b5ab5726589be24f5f12113-v1
- **Version:** v21 (FINAL)
- **Status:** Oracle PASSED (1.0), GLM ×4 RUNNING
- **Verifiers:** 43 (all core)
- **Gold keys:** 27 (all disclosed in instruction)
- **Hardening:** 10 interpretive discriminators + 3 message body SQL checks + 5 rubric checks
- **Key traps:**
  - rooms_with_notify_candidate=3 (perf-070 has only self-reply, no notify candidate)
  - rooms_with_no_external_reply=1 (perf-070 is pure self-reply)
  - self_reply_room_ids=["CJWT99KXPLPI","CN20Z0W91YE0"] (alphabetical)
  - worst_room_external_reply_count=1 (2 replies - 1 self = 1 external)
  - non_worst_room_external_reply_count=2 (perf-070's self-reply doesn't count)
  - problem_rooms_with_only_external_replies=2 (general-marketing + mobile-090)
  - Message must name retractor "Levi", explain self-reply, name both clean rooms
- **Fixes:**
  - CSV header: regex_match with quote/whitespace tolerance
  - SQL message: char(13) CRLF tolerance
  - Flaky rubric removed (agent_distinguished_clean_with_retraction)
  - Core gate in test_outputs.py
  - minimum_tool_calls=25, healthcheck retries=40
  - Tool disclosure: slack_read_channel, slack_read_thread, slack_read_user_profile
  - retractor_self_reply_count=2 (Ellie + Levi)
  - All CRLF fixed, mirror synced, sha256 verified
- **Zip:** canonical-zips/UPLOAD-THIS-TO-QC-the-thread-v21-fair-hard.zip
- **Source:** task-sources/the-thread-that-outlived-its-own-start-v21/

## Answer Task (the-answer-she-already-gave)
- **Status:** ACCEPTED BY PIPELINE (per other PC commit)
- **Portal URL:** https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-2c4203188f34ec27e7e7f2cb51edff50-v1
- **Zip:** canonical-zips/UPLOAD-THIS-TO-QC-the-answer-she-already-gave-v7.zip
- **Source:** task-sources/the-answer-she-already-gave-v7/

## Version History (Thread Task)
- v1-v6: Initial versions, various blockers (hidden keys, ambiguity, tool disclosure)
- v7: My version — 2/4 difficulty, 2 tool disclosure blockers
- v8: Other PC — 0/4 (unfair: wrong gold + surface form brittleness)
- v9: My version — 0/4 (unfair: surface form brittleness), 1 blocker (semantic_equivalence)
- v10-v17: Other PC iterations
- v18: Other PC — 0/4, errored on flaky rubric check
- v19: My version — 4/4 (all checks fair but too easy)
- v20: My version — 4/4 (added message body SQL checks, still too easy)
- v21: FINAL — 43 verifiers, 10 interpretive discriminators, 3 message body checks. Running now.
