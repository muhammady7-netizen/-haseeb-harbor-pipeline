# Connector Task Status — Oct 6, 2026

## Thread Task (the-thread-that-outlived-its-own-start)
- **Portal URL:** https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-951ea1fc0bdfe640cd7d6b00d95ee61a-v1
- **Run ID:** evaluation-29406ef0dd6b4532
- **Content ID:** content-951ea1fc0bdfe640cd7d6b00d95ee61a-v1
- **Version:** v9 (latest)
- **Status:** Oracle+GLM running on portal
- **Previous result (v8):** 0/4 difficulty (excellent!), 1 blocker (surface_form_brittleness — now fixed)
- **Verifiers:** 29 (all core)
- **Hardening:** 7 interpretive discriminators (clean_rooms_count, clean_room_ids, retractor_self_reply_count, total_retractions_across_all_rooms, worst_room_total_retractions, rooms_with_retraction_but_no_reply, external_stranded_reply_count)
- **Fixes in v9:**
  - Fixed CSV header check: inspect_table+equals → extract_text+regex_match (whitespace-tolerant)
  - Fixed SQL message pattern: added char(13) strip for CRLF tolerance
  - Reverted healthcheck retries from 150 to 40 (150 caused 2+ hour runs)
  - Core gate added to test_outputs.py
  - minimum_tool_calls raised from 10 to 25
  - CRLF fixed in all files
  - Tool disclosure: slack_read_channel, slack_read_thread, slack_read_user_profile
  - retractor_self_reply_count gold fixed: 1 → 2 (Ellie + Levi both self-replied)
  - retractor_also_notifiable verifier added (expected=false)
- **Zip:** canonical-zips/UPLOAD-THIS-TO-QC-the-thread-v9.zip
- **Source:** task-sources/the-thread-that-outlived-its-own-start-v9/

## Answer Task (the-answer-she-already-gave)
- **Portal URL:** https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-2c4203188f34ec27e7e7f2cb51edff50-v1
- **Content ID:** content-2c4203188f34ec27e7e7f2cb51edff50-v1
- **Version:** v7 (on portal, needs more hardening — was 3/4 too easy)
- **Status:** Needs deeper hardening + draft body rubric_check
- **Previous result:** 3/4 (too easy), 2 blockers (draft body not checked by verifier)
- **Verifiers:** 36
- **Zip:** canonical-zips/UPLOAD-THIS-TO-QC-the-answer-she-already-gave-v7.zip
- **Source:** task-sources/the-answer-she-already-gave-v7/
