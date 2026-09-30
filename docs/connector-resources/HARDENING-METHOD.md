# Hardening Method for Connector Tasks

## The Problem
GLM-5.2 writes Python scripts to solve tasks. Adding more rules, more data, or more precision counts doesn't stop it — it just writes a bigger script.

## What Doesn't Work (proven by 19+ versions on bus-b50, 10+ on connector tasks)

### Mechanical thresholds (§9.1)
```python
# GLM scripts this in one line:
if field >= N: violation = True
```
Discriminators like `version >= 2` or `field == X` are one-step lookups. GLM applies them instantly whether or not the rule is disclosed.

### Precision counts (other PC's approach)
```python
# GLM scripts this:
total_external_stranded = sum(1 for r in replies if r.author != retractor)
```
Adding 16 count-based verifiers (total_stranded_replies, worst_room_external_reply_count, self_reply_rooms_count, etc) gives GLM 16 more things to script. It got 3/4 — still too easy.

### More data
GLM crunches 200,000 rows as fast as 200. Adding more ledger rows, more channels, more traps doesn't slow it down.

## What Works (from docs §9 + golden task analysis §7)

### 1. Interpretation, not lookup (§9.1)
Restate a threshold as a policy the model must connect to data:
- BAD: `version >= 2` → GLM applies in one step
- GOOD: "a function deployed for the first time is still in development" → GLM must connect concept to field to derive threshold (3 steps)

### 2. Cross-source reasoning (§9.2)
Require the agent to call tools from DIFFERENT sources:
- Calendar + Email: must call search_calendar AND search_email
- Channel + User Profile: must call slack_read_channel AND slack_read_user_profile
- GLM that only reads one source cannot answer

### 3. Chained discriminators (§9.2)
One criterion testing several dimensions:
1. Find the worst room (read 27 threads, check deleted_ts)
2. Identify WHO retracted (read user field on retracted message)
3. Check if retractor also replied (compare reply authors against retractor)
4. Understand: retractor already knows, exclude them as notify candidate
5. Find the OTHER person (the external reply author)
6. Call read_user_profile to get their name

Each step depends on the previous. Missing any one fails a core check.

### 4. Conceptual traps (§7 golden tasks)
Create a trap where the "obvious" answer is wrong:
- The retractor replied to their own thread → naive model picks them as notify candidate
- But the retractor already knows → they should NOT be notified
- The correct answer is the OTHER reply author, who is less obvious

### 5. Tool execution checks (§6.1)
Force specific tool calls:
- `expected_tools: ["search_email"]` → GLM must call search_email, not just search_calendar
- `expected_tools: ["slack_read_user_profile"]` → GLM must resolve the name via profile lookup

## Applied Examples

### Task 1 (the-answer-she-already-gave)
- `search_email_was_called` → forces cross-source (calendar + email)
- `pending_attendee_email_thread_exists` → requires interpreting email search results
- `pending_attendee_has_other_response` → cross-meeting analysis (Morgan on 2 meetings)
- `fully_confirmed_with_unanswered_optional` → optional attendee interpretation
- `total_optional_attendees` → precision count (this one IS scriptable, kept for precision)

### Task 2 (the-thread-that-outlived-its-own-start)
- `retracted_msg_author_also_replied` → self-reply detection (interpretation)
- `worst_room_has_self_reply` → distinguishing self from external (interpretation)
- `notify_candidate_is_not_retractor` → concept: retractor already knows (interpretation)
- `worst_room_retractor_id` → identifying WHO retracted (not just that it was retracted)
- `retractor_also_notifiable` = false → TRAP: retractor replied but should NOT be notified
- `read_user_profile_was_called` → forces profile lookup tool call

## What NOT to add
- More count verifiers (total_X_count, worst_room_Y_count) → GLM scripts them
- More data rows → GLM crunches them
- More rules that are `field >= N` or `field == X` → one-step lookup
- Anything a Python script can solve without understanding the concept

## Prediction (written before battery, per §9.3)
Task 2 prediction: band drops 3/4 → 0-1/4, because GLM must:
1. Identify the retractor (not just that message was retracted)
2. Detect self-reply (compare reply author vs retractor)
3. Understand the retractor should NOT be notified (conceptual)
4. Call read_user_profile (forced tool call)
Missing any one of these fails a core check.
