# Connector Task Analysis — the-answer-she-already-gave

**Task ID:** CONN-B3-9000286
**Batch:** Batch 3
**Trainer:** Muhammad Haseeb Younas (muhammad.y7@turing.com)
**Category:** General / cross-domain knowledge work
**Status:** In Progress (2026-09-28)
**Connector:** email-calendar-gym

---

## Task Summary

Meeting-confirmation audit over a one-week calendar window on the email-calendar-gym connector, with a targeted confirmation-chase email draft write-back.

**User:** Nathan Thomas (nathan.thomas@maplewoodhospital.org, timezone America/Chicago)
**Window:** 2026-05-19 through 2026-05-25 (one week, exclusive end 2026-05-26T00:00:00-05:00)

## What the agent must do

1. Search calendar for the window via `search_calendar`
2. Classify entries: real meetings Nathan organizes (organizer_email=nathan.thomas, eventType=default, status=confirmed)
3. For each real meeting, check if fully confirmed (every REQUIRED attendee accepted; optional attendees don't count)
4. Identify meetings with pending attendees (required attendee tentative or no response)
5. Identify meetings with declined attendees (required attendee declined = already answered, not pending)
6. Write results to `/workspace/meeting_confirmation_audit.json` with EXACTLY these keys (no others):
   - `real_meetings_count` (number)
   - `fully_confirmed_count` (number)
   - `still_pending_count` (number)
   - `declined_required_count` (number)
   - `still_pending_meeting` (string)
   - `still_pending_attendee_email` (string)
   - `declined_meeting` (string)
   - `declined_attendee_email` (string)
7. Draft an email (NOT send) to the still-pending attendee with the meeting title in the subject
8. Do NOT draft anything about the declined meeting
9. State conclusion in reply

## Golden answers

| Key | Value |
|---|---|
| real_meetings_count | 4 |
| fully_confirmed_count | 2 |
| still_pending_count | 1 |
| declined_required_count | 1 |
| still_pending_meeting | "Technical Interview" |
| still_pending_attendee_email | "morgan.thompson@maplewoodhospital.org" |
| declined_meeting | "Skip Level 1:1" |
| declined_attendee_email | "morgan.thompson@maplewoodhospital.org" |

## The central trap

Morgan Thompson has TWO different responses across TWO different meetings Nathan runs:
- She **DECLINED** Skip Level 1:1 (May 21) — already answered, must NOT chase
- She is **TENTATIVE** on Technical Interview (May 22) — genuinely open, MUST chase

A model that doesn't distinguish decline from tentative will:
- Chase the wrong meeting (fail `no_draft_chases_the_declined_meeting`)
- Or fail to chase the right one
- Or miscount both buckets

## The 9 calendar entries in the window

1. Weekly Risk Sync (05-19) — organizer Nathan, confirmed, all required accepted → fully_confirmed
2. Weekly Risk Sync (05-21) — organizer Nathan, confirmed, all required accepted → fully_confirmed
3. Skip Level 1:1 (05-21) — organizer Nathan, confirmed, Morgan Thompson DECLINED → declined_required
4. Technical Interview (05-22) — organizer Nathan, confirmed, Morgan Thompson TENTATIVE → still_pending
5. Backlog Grooming — NOT Nathan's meeting (organized by nancy.garcia)
6. Concentration Time — focusTime hold, not a meeting
7. Flexible Location — workingLocation entry
8. Hybrid block — workingLocation entry
9. Story Refinement — organizer Nathan but status=TENTATIVE (not confirmed)

## Verifiers (18 total)

| # | Name | Type | Expected | Weight |
|---|---|---|---|---|
| 1 | audit_file_exists | file_check | true | 0.5 |
| 2 | real_meetings_count | file_check | 4 | 1.0 |
| 3 | fully_confirmed_count | file_check | 2 | 1.0 |
| 4 | still_pending_count | file_check | 1 | 1.0 |
| 5 | declined_required_count | file_check | 1 | 1.0 |
| 6 | still_pending_meeting_name | file_check | "Technical Interview" | 1.0 |
| 7 | still_pending_attendee_email_value | file_check | "morgan.thompson@maplewoodhospital.org" | 1.0 |
| 8 | declined_meeting_name | file_check | "Skip Level 1:1" | 1.0 |
| 9 | declined_attendee_email_value | file_check | "morgan.thompson@maplewoodhospital.org" | 1.0 |
| 10 | draft_created_to_morgan_about_technical_interview | database_state | >=1 | 1.0 |
| 11 | no_draft_chases_the_declined_meeting | database_state | 0 | 1.0 |
| 12 | no_draft_to_optional_attendees | database_state | 0 | 1.0 |
| 13 | mailbox_holds_seed_plus_one | database_state | 11 | 0.5 |
| 14 | calendar_untouched | database_state | 14 | 0.5 |
| 15 | the_search_and_write_actually_ran | tool_execution | min 2 calls | 0.5 |
| 16 | real_meeting_classified_by_structural_fields | rubric_check | PASS | 1.0 |
| 17 | decline_vs_tentative_correctly_distinguished | rubric_check | PASS | 1.0 |
| 18 | final_reply_states_a_genuine_conclusion | rubric_check | PASS | 0.5 |

## Scoring

- sql: 0.6 weight
- rubric: 0.4 weight
- state: 0.0 (checked but not scored)
- trajectory: 0.0
- flat_verifier_scoring: true
- side_effect_gate: true
- Forbidden tools: `send_email`

## Current evaluation status

| Eval | Status | Reward |
|---|---|---|
| Oracle | PASS | 1.0 |
| Harbor Check | PASS | 1.0 (claude-opus-5) |
| Difficulty r1-r4 | MISSING | — |
| Solvability r1 | MISSING | — |
| Stability repeats | MISSING | — |
| review.csv | MISSING | — |
| README.md | MISSING | — |
| qc_report.html | MISSING | — |

## Configuration

- **Connector image:** `us-central1-docker.pkg.dev/delivery-g-obi/connectors-rl-gym/connectors-harness:company-synthetic-20260910-1150-pt-main`
- **MCP server:** email-calendar-gym, port 8016, streamable-http
- **Agent user:** rlgymagent (non-root)
- **Agent timeout:** 4800s
- **Verifier timeout:** 1500s
- **JUDGE_MODEL:** `${JUDGE_MODEL:-openai/zai-org/GLM-5.2}`
- **Healthcheck:** `curl -fsS http://localhost:7000/health`

## Shortcut audit (2-call minimum)

1. `search_calendar(start_date=2026-05-19T00:00:00-05:00, end_date=2026-05-26T00:00:00-05:00, queries=[])` — returns all 9 events with organizer/status/eventType/attendees
2. `draft_email(to=["morgan.thompson@maplewoodhospital.org"], subject="...Technical Interview...", body=...)` — write-back

## Next steps

1. Check Docker + harbor CLI + gcloud auth
2. Run local QC judge on the package
3. Run 4 GLM-5.2 difficulty runs
4. Run 1 solvability run (non-Oracle model)
5. Create review.csv, README.md, qc_report.html
6. Package and run through repackaging QC gate
7. Upload to portal, run PreQC + Oracle+GLM
8. Submit to pipeline, work until ACCEPTED
