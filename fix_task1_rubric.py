import json

path = r'C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\task-sources\the-answer-she-already-gave-v7\tests\manifest.json'
with open(path, 'r', encoding='utf-8') as f:
    m = json.load(f)

for v in m['verifier_configs']:
    if v['name'] == 'draft_body_asks_to_confirm_attendance':
        v['verifier_type'] = 'rubric_check'
        v['type'] = 'rubric_check'
        v['target'] = 'trace'
        v['target_gym_server'] = 'email-calendar-gym'
        v.pop('sql_query', None)
        v.pop('expected_value', None)
        v.pop('comparison_type', None)
        v['rubric'] = (
            'Graded against the AGENT TRACE. PASS if the draft_email call in the trace '
            'includes a body argument that explicitly asks the recipient to confirm their '
            'attendance. The body must contain language about confirming or attending '
            '(e.g. could you confirm whether you will be able to attend, please confirm '
            'your attendance). FAIL if the draft_email call has an empty body, a body that '
            'does not mention confirming or attending, or if no draft_email call is present '
            'in the trace.'
        )
        v['description'] = (
            'The draft body must contain language asking the recipient to confirm their '
            'attendance. Checked against the agent trace draft_email call body argument.'
        )
        v['metadata']['why_justification'] = (
            'Instruction requires the draft to ask the attendee to confirm their attendance. '
            'The golden body says Could you confirm whether you will be able to attend. A '
            'draft with correct To and Subject but an empty or off-topic body fails this check.'
        )
        break

with open(path, 'w', encoding='utf-8') as f:
    json.dump(m, f, indent=2, ensure_ascii=False)
    f.write('\n')
print('Updated to rubric_check')
