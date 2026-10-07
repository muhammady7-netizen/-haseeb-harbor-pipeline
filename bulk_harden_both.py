import json, hashlib, shutil, os

# ============================================================
# BULK FAIR HARDENING - Both Tasks
# ============================================================
# Principles:
# 1. Keep original instruction text (don't clarify - that made it easier)
# 2. Add conceptual trap fields (obvious answer is wrong)
# 3. Use only file_check verifiers (Oracle can handle them)
# 4. Update golden solution (artifact_plan.json) with correct values
# 5. Don't change existing verifiers
# ============================================================

def make_file_check(name, description, requirement_id, evidence_span, expected, why_justification, json_path="meeting_confirmation_audit.json"):
    """Create a deterministic file_check verifier."""
    return {
        "name": name,
        "description": description,
        "category": "core",
        "weight": 1.0,
        "target": "workspace_files",
        "verifier_type": "file_check",
        "type": "file_check",
        "pass_threshold": 1.0,
        "requirement_id": requirement_id,
        "evidence_span": evidence_span,
        "metadata": {"why_justification": why_justification},
        "verifier_spec": {
            "task_id": requirement_id,
            "verifiers": [{
                "name": name,
                "metadata": {
                    "how_justification": "Reads %s and requires %s = %s." % (json_path, name, str(expected)),
                    "why_justification": why_justification
                },
                "source": {"type": "file", "file": {"type": "json", "command": "read_file", "arguments": {"path": json_path}}},
                "assertion": {"type": "deterministic", "expected": expected, "deterministic": {"path": "$.%s" % name, "comparison": "equals"}}
            }]
        }
    }

# ============================================================
# TASK 1: the-answer-she-already-gave
# ============================================================
task1_base = r'C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\task-sources\the-answer-she-already-gave-v7'

# Read current instruction
with open(os.path.join(task1_base, 'instruction.md'), 'r', encoding='utf-8') as f:
    instr1 = f.read()

# Add new fields to instruction (after pending_meeting_optional_attendee_count)
new_fields_task1 = """
- `declined_meeting_optional_attendee_count` (number): how many optional attendees are on the
  meeting that was already resolved by a decline? Check the declined meeting's attendee list,
  not just the pending meeting's.
- `pending_meeting_required_attendee_count` (number): how many required (non-optional) attendees
  are on the still-pending meeting?
- `declined_meeting_required_attendee_count` (number): how many required (non-optional) attendees
  are on the meeting that was already resolved by a decline?
- `same_attendee_on_both_meetings` (boolean): is there an attendee who appears on BOTH the
  still-pending meeting AND the already-declined meeting? This requires cross-referencing the
  attendee lists of both meetings.
- `fully_confirmed_meetings_with_no_optional` (number): how many of the fully confirmed meetings
  have zero optional attendees? Some fully confirmed meetings may have optional attendees and
  some may not — check each one.
- `pending_meeting_has_accepted_optional` (boolean): does the still-pending meeting have at least
  one optional attendee whose response status is "accepted"? An optional attendee who accepted
  does not make the meeting fully confirmed, but they did accept.
- `declined_meeting_optional_attendee_response` (string): what is the response status of the
  optional attendee on the already-declined meeting? If there are multiple optional attendees,
  use the one whose response is not "accepted". If there is only one, use their response.
- `declined_meeting_was_never_confirmed` (boolean): was the already-declined meeting ever fully
  confirmed before the decline? A meeting that was never confirmed (because a required attendee
  declined rather than accepting) is different from one that was confirmed and then unconfirmed.
- `pending_meeting_could_become_confirmed` (boolean): could the still-pending meeting become
  fully confirmed if the pending required attendee accepts? A tentative response means the
  attendee has not yet decided, so the meeting could still become confirmed.
- `meetings_with_morgan_thompson_count` (number): across all your real meetings, how many list
  the person who appears on both the pending and declined meetings as an attendee? This requires
  identifying who that person is first, then counting their appearances."""

# Find the insertion point (after pending_meeting_optional_attendee_count)
marker = "- `pending_meeting_optional_attendee_count` (number): how many optional attendees are on the\n  one meeting that is genuinely still waiting on someone? An optional attendee is one whose\n  response status does not affect whether the meeting is fully confirmed. Count each optional\n  attendee on that specific meeting."

if marker in instr1:
    instr1 = instr1.replace(marker, marker + new_fields_task1)
    print("Task 1: Added 10 new fields to instruction")
else:
    print("Task 1: WARNING - marker not found, trying alternate")
    # Try to find it another way
    marker2 = "  attendee on that specific meeting."
    if marker2 in instr1:
        idx = instr1.index(marker2) + len(marker2)
        instr1 = instr1[:idx] + new_fields_task1 + instr1[idx:]
        print("Task 1: Added 10 new fields to instruction (alternate)")
    else:
        print("Task 1: ERROR - could not find insertion point")

with open(os.path.join(task1_base, 'instruction.md'), 'w', encoding='utf-8') as f:
    f.write(instr1)

# Add new verifiers to manifest
manifest1_path = os.path.join(task1_base, 'tests', 'manifest.json')
with open(manifest1_path, 'r', encoding='utf-8') as f:
    m1 = json.load(f)

new_verifiers_1 = [
    make_file_check("declined_meeting_optional_attendee_count", "How many optional attendees on the declined meeting.", "declined_meeting_optional_attendee_count", "how many optional attendees are on the meeting that was already resolved by a decline", 1, "Nicole Washington is optional on Skip Level 1:1. A run that only checks the pending meeting's optional attendees answers 0."),
    make_file_check("pending_meeting_required_attendee_count", "How many required attendees on the pending meeting.", "pending_meeting_required_attendee_count", "how many required attendees are on the still-pending meeting", 1, "Morgan Thompson is the only required attendee on Technical Interview who is still tentative."),
    make_file_check("declined_meeting_required_attendee_count", "How many required attendees on the declined meeting.", "declined_meeting_required_attendee_count", "how many required attendees are on the meeting that was already resolved by a decline", 1, "Morgan Thompson is the only required attendee on Skip Level 1:1 who declined."),
    make_file_check("same_attendee_on_both_meetings", "Is the same attendee on both meetings.", "same_attendee_on_both_meetings", "is there an attendee who appears on BOTH the still-pending meeting AND the already-declined meeting", True, "Morgan Thompson appears on both Skip Level 1:1 (declined) and Technical Interview (tentative). A run that doesn't cross-reference the two meetings answers false."),
    make_file_check("fully_confirmed_meetings_with_no_optional", "How many fully confirmed meetings have zero optional attendees.", "fully_confirmed_meetings_with_no_optional", "how many of the fully confirmed meetings have zero optional attendees", 1, "Weekly Risk Sync 05-21 has no optional attendees. Weekly Risk Sync 05-19 has Natalie Gardner as optional. A run that assumes all confirmed meetings have optional attendees answers 0."),
    make_file_check("pending_meeting_has_accepted_optional", "Does the pending meeting have an accepted optional attendee.", "pending_meeting_has_accepted_optional", "does the still-pending meeting have at least one optional attendee whose response status is accepted", True, "Nicole Washington is optional on Technical Interview and her response is accepted. A run that assumes optional attendees are always tentative answers false."),
    make_file_check("declined_meeting_optional_attendee_response", "Response status of optional attendee on declined meeting.", "declined_meeting_optional_attendee_response", "what is the response status of the optional attendee on the already-declined meeting", "tentative", "Nicole Washington is optional on Skip Level 1:1 and her response is tentative. A run that doesn't check optional attendees on the declined meeting answers differently."),
    make_file_check("declined_meeting_was_never_confirmed", "Was the declined meeting ever fully confirmed.", "declined_meeting_was_never_confirmed", "was the already-declined meeting ever fully confirmed before the decline", True, "Skip Level 1:1 was never fully confirmed because Morgan Thompson (required) declined rather than accepting. A run that thinks it was confirmed then unconfirmed answers false."),
    make_file_check("pending_meeting_could_become_confirmed", "Could the pending meeting become confirmed.", "pending_meeting_could_become_confirmed", "could the still-pending meeting become fully confirmed if the pending required attendee accepts", True, "Technical Interview could become fully confirmed if Morgan Thompson accepts. A tentative response means she hasn't decided yet. A run that thinks tentative means no answers false."),
    make_file_check("meetings_with_morgan_thompson_count", "How many real meetings list the cross-meeting attendee.", "meetings_with_morgan_thompson_count", "how many list the person who appears on both the pending and declined meetings as an attendee", 2, "Morgan Thompson appears on 2 real meetings: Skip Level 1:1 and Technical Interview. A run that doesn't identify the cross-meeting attendee answers 0 or 1."),
]

m1['verifier_configs'].extend(new_verifiers_1)

# Update instruction_sha256
with open(os.path.join(task1_base, 'instruction.md'), 'rb') as f:
    instr1_hash = hashlib.sha256(f.read()).hexdigest()
m1['instruction_sha256'] = instr1_hash

with open(manifest1_path, 'w', encoding='utf-8') as f:
    json.dump(m1, f, indent=2, ensure_ascii=False)
    f.write('\n')

# Update artifact_plan.json
plan1_path = os.path.join(task1_base, 'solution', 'artifact_plan.json')
with open(plan1_path, 'r', encoding='utf-8') as f:
    plan1 = json.load(f)
plan1['json']['declined_meeting_optional_attendee_count'] = 1
plan1['json']['pending_meeting_required_attendee_count'] = 1
plan1['json']['declined_meeting_required_attendee_count'] = 1
plan1['json']['same_attendee_on_both_meetings'] = True
plan1['json']['fully_confirmed_meetings_with_no_optional'] = 1
plan1['json']['pending_meeting_has_accepted_optional'] = True
plan1['json']['declined_meeting_optional_attendee_response'] = "tentative"
plan1['json']['declined_meeting_was_never_confirmed'] = True
plan1['json']['pending_meeting_could_become_confirmed'] = True
plan1['json']['meetings_with_morgan_thompson_count'] = 2
with open(plan1_path, 'w', encoding='utf-8') as f:
    json.dump(plan1, f, indent=2)
    f.write('\n')

# Sync to environment/_app
shutil.copy2(os.path.join(task1_base, 'instruction.md'), os.path.join(task1_base, 'environment', '_app', 'instruction.md'))
shutil.copy2(manifest1_path, os.path.join(task1_base, 'environment', '_app', 'tests', 'manifest.json'))

print("Task 1: %d verifiers, %d json keys, sha256=%s" % (len(m1['verifier_configs']), len(plan1['json']), instr1_hash))

# ============================================================
# TASK 2: the-thread-that-outlived-its-own-start
# ============================================================
task2_base = r'C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\task-sources\the-thread-that-outlived-its-own-start-v7'

# Read current instruction
with open(os.path.join(task2_base, 'instruction.md'), 'r', encoding='utf-8') as f:
    instr2 = f.read()

new_fields_task2 = """
- `worst_room_self_reply_count` (number): in the single worst room only, how many of its stranded
  replies were written by the retractor themselves? This is the self-reply count for just the
  worst room, not across all rooms.
- `clean_room_with_retraction_count` (number): how many of the clean rooms (rooms without a live
  orphaned thread) DO have a retracted message — just one that never picked up any replies? A
  room can be clean because it has no retracted messages at all, or because its retracted
  message has zero replies. This counts only the first kind.
- `clean_room_without_retraction_count` (number): how many of the clean rooms have NO retracted
  messages at all? This is the complement of the above — rooms that are clean because nothing
  was ever retracted there.
- `worst_room_has_only_one_external_reply` (boolean): in the single worst room, is there exactly
  one external reply (a reply from someone other than the retractor)? The worst room has 2
  stranded replies total, but some of those may be self-replies.
- `all_self_reply_rooms_also_have_external` (boolean): do ALL rooms that have self-replies also
  have at least one external reply? A room where the only reply is from the retractor themselves
  has a self-reply but no external reply.
- `rooms_with_more_external_than_self` (array of strings): the channel IDs of every room with a
  live orphaned thread where the external reply count is strictly greater than the self-reply
  count. Rooms where self-replies equal or exceed external replies are excluded. In alphabetical
  order."""

# Find insertion point (after worst_room_has_more_than_one_external_reply)
marker2 = "- `worst_room_has_more_than_one_external_reply` (boolean): in the single worst room (the one\n  with the most stranded replies), are there more than one external replies? An external reply\n  is a reply from someone other than the person who retracted the original message. Self-replies\n  (from the retractor) do not count as external."

if marker2 in instr2:
    instr2 = instr2.replace(marker2, marker2 + new_fields_task2)
    print("Task 2: Added 6 new fields to instruction")
else:
    print("Task 2: WARNING - marker not found")

with open(os.path.join(task2_base, 'instruction.md'), 'w', encoding='utf-8') as f:
    f.write(instr2)

# Add new verifiers to manifest
manifest2_path = os.path.join(task2_base, 'tests', 'manifest.json')
with open(manifest2_path, 'r', encoding='utf-8') as f:
    m2 = json.load(f)

new_verifiers_2 = [
    make_file_check("worst_room_self_reply_count", "Self-reply count in worst room only.", "worst_room_self_reply_count", "in the single worst room only, how many of its stranded replies were written by the retractor", 1, "Levi self-replied once in data-v2-062. A run that confuses this with the global retractor_self_reply_count (2) answers 2.", "metrics.json"),
    make_file_check("clean_room_with_retraction_count", "Clean rooms that have retracted messages.", "clean_room_with_retraction_count", "how many of the clean rooms DO have a retracted message with zero replies", 1, "perf-v2-020 has a retracted message but no replies, so it is clean. A run that thinks clean means no retracted messages answers 0.", "metrics.json"),
    make_file_check("clean_room_without_retraction_count", "Clean rooms with no retracted messages at all.", "clean_room_without_retraction_count", "how many of the clean rooms have NO retracted messages at all", 1, "mobile-v2-024 has no retracted messages at all. A run that thinks all clean rooms have retracted messages answers 0.", "metrics.json"),
    make_file_check("worst_room_has_only_one_external_reply", "Worst room has exactly one external reply.", "worst_room_has_only_one_external_reply", "in the single worst room, is there exactly one external reply", True, "The worst room has 2 stranded replies: 1 self-reply by Levi and 1 external by Mitali. The external count is 1. A run that confuses total with external answers false.", "metrics.json"),
    make_file_check("all_self_reply_rooms_also_have_external", "Do all self-reply rooms also have external replies.", "all_self_reply_rooms_also_have_external", "do ALL rooms that have self-replies also have at least one external reply", False, "perf-070 has a self-reply by Ellie but no external replies. So not all self-reply rooms have external replies. A run that doesn't check this answers true.", "metrics.json"),
    make_file_check("rooms_with_more_external_than_self", "Rooms where external replies exceed self-replies.", "rooms_with_more_external_than_self", "the channel IDs of every room where the external reply count is strictly greater than the self-reply count", ["C62RIISXI1FD", "C5H1G0LC1A6C"], "general-marketing-analytics (1 external, 0 self) and mobile-090 (1 external, 0 self) have more external than self. data-v2-062 has 1 external and 1 self (equal, not more). A run that includes data-v2-062 answers differently.", "metrics.json"),
]

m2['verifier_configs'].extend(new_verifiers_2)

# Update instruction_sha256
with open(os.path.join(task2_base, 'instruction.md'), 'rb') as f:
    instr2_hash = hashlib.sha256(f.read()).hexdigest()
m2['instruction_sha256'] = instr2_hash

with open(manifest2_path, 'w', encoding='utf-8') as f:
    json.dump(m2, f, indent=2, ensure_ascii=False)
    f.write('\n')

# Update artifact_plan.json
plan2_path = os.path.join(task2_base, 'solution', 'artifact_plan.json')
with open(plan2_path, 'r', encoding='utf-8') as f:
    plan2 = json.load(f)
plan2['json']['worst_room_self_reply_count'] = 1
plan2['json']['clean_room_with_retraction_count'] = 1
plan2['json']['clean_room_without_retraction_count'] = 1
plan2['json']['worst_room_has_only_one_external_reply'] = True
plan2['json']['all_self_reply_rooms_also_have_external'] = False
plan2['json']['rooms_with_more_external_than_self'] = ["C62RIISXI1FD", "C5H1G0LC1A6C"]
with open(plan2_path, 'w', encoding='utf-8') as f:
    json.dump(plan2, f, indent=2)
    f.write('\n')

# Sync to environment/_app
shutil.copy2(os.path.join(task2_base, 'instruction.md'), os.path.join(task2_base, 'environment', '_app', 'instruction.md'))
shutil.copy2(manifest2_path, os.path.join(task2_base, 'environment', '_app', 'tests', 'manifest.json'))

print("Task 2: %d verifiers, %d json keys, sha256=%s" % (len(m2['verifier_configs']), len(plan2['json']), instr2_hash))

print("\nDone! Both tasks hardened with fair conceptual traps.")
