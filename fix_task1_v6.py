import json, hashlib

path = r'C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\task-sources\the-answer-she-already-gave-v7\tests\manifest.json'
with open(path, 'r', encoding='utf-8') as f:
    m = json.load(f)

# 1. Change optional_attendee_accepted_count to accept both 1 and 2 (rubric_check)
for v in m['verifier_configs']:
    if v['name'] == 'optional_attendee_accepted_count':
        v['verifier_type'] = 'rubric_check'
        v['type'] = 'rubric_check'
        v['target'] = 'workspace_files'
        v['target_gym_server'] = 'email-calendar-gym'
        v.pop('pass_threshold', None)
        v.pop('verifier_spec', None)
        v['rubric'] = (
            'Reads meeting_confirmation_audit.json. PASS if optional_attendee_accepted_count '
            'is either 1 or 2. Value 2 counts each (meeting, attendee) pair where the optional '
            'attendee accepted (Natalie Gardner on Weekly Risk Sync 05-19 and Nicole Washington '
            'on Technical Interview). Value 1 counts unique optional attendees whose every '
            'response is accepted (only Natalie Gardner, since Nicole is tentative on Skip Level '
            '1:1). Both interpretations are defensible from the instruction text. FAIL only if '
            'the value is 0, 3, or any other number.'
        )
        v['description'] = 'How many optional attendees across all real meetings have response status accepted. Accepts both per-meeting (2) and per-unique-attendee (1) interpretations.'
        v['metadata']['why_justification'] = (
            'Both counting grains are defensible: per-(meeting, attendee) gives 2 (Natalie + Nicole-on-Tech), '
            'per-unique-attendee gives 1 (Natalie only, since Nicole is tentative on Skip Level 1:1). '
            'The verifier accepts both to avoid penalizing a defensible interpretation.'
        )
        break

# 2. Add new verifier: pending_meeting_optional_attendee_count
new_v = {
    'name': 'pending_meeting_optional_attendee_count',
    'description': 'How many optional attendees are on the still-pending meeting.',
    'category': 'core',
    'weight': 1.0,
    'target': 'workspace_files',
    'verifier_type': 'file_check',
    'type': 'file_check',
    'pass_threshold': 1.0,
    'requirement_id': 'pending_meeting_optional_attendee_count',
    'evidence_span': 'how many optional attendees are on the still-pending meeting',
    'metadata': {
        'why_justification': 'The still-pending meeting is Technical Interview. It has 2 optional attendees: Cynthia Nelson (tentative) and Nicole Washington (accepted). A run that misses Nicole Washington on Technical Interview (because she also appears on Skip Level 1:1) answers 1.'
    },
    'verifier_spec': {
        'task_id': 'pending_meeting_optional_attendee_count',
        'verifiers': [{
            'name': 'pending_meeting_optional_attendee_count',
            'metadata': {
                'how_justification': 'Reads meeting_confirmation_audit.json and requires pending_meeting_optional_attendee_count = 2.',
                'why_justification': 'Technical Interview has 2 optional attendees: Cynthia Nelson and Nicole Washington.'
            },
            'source': {'type': 'file', 'file': {'type': 'json', 'command': 'read_file', 'arguments': {'path': 'meeting_confirmation_audit.json'}}},
            'assertion': {'type': 'deterministic', 'expected': 2, 'deterministic': {'path': '$.pending_meeting_optional_attendee_count', 'comparison': 'equals'}}
        }]
    }
}
m['verifier_configs'].append(new_v)

# 3. Update instruction_sha256
instr_path = r'C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\task-sources\the-answer-she-already-gave-v7\instruction.md'
with open(instr_path, 'rb') as f:
    instr_hash = hashlib.sha256(f.read()).hexdigest()
m['instruction_sha256'] = instr_hash

with open(path, 'w', encoding='utf-8') as f:
    json.dump(m, f, indent=2, ensure_ascii=False)
    f.write('\n')
print('Updated: %d verifiers, sha256=%s' % (len(m['verifier_configs']), instr_hash))
