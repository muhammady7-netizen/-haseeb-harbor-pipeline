import json, hashlib, shutil

# Add new field to Task 2 instruction
instr_path = r'C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\task-sources\the-thread-that-outlived-its-own-start-v7\instruction.md'
with open(instr_path, 'r', encoding='utf-8') as f:
    instr = f.read()

old_text = """- `rooms_with_both_reply_types` (array of strings): the channel IDs of every room with a live
  orphaned thread where the retracted message has BOTH at least one self-reply (from the
  retractor) AND at least one external reply (from someone else). In alphabetical order."""

new_text = old_text + """
- `worst_room_has_more_than_one_external_reply` (boolean): in the single worst room (the one
  with the most stranded replies), are there more than one external replies? An external reply
  is a reply from someone other than the person who retracted the original message. Self-replies
  (from the retractor) do not count as external."""

instr = instr.replace(old_text, new_text)
with open(instr_path, 'w', encoding='utf-8') as f:
    f.write(instr)

# Add new verifier to manifest
manifest_path = r'C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\task-sources\the-thread-that-outlived-its-own-start-v7\tests\manifest.json'
with open(manifest_path, 'r', encoding='utf-8') as f:
    m = json.load(f)

new_v = {
    'name': 'worst_room_has_more_than_one_external_reply',
    'description': 'Whether the worst room has more than one external reply.',
    'category': 'core',
    'weight': 1.0,
    'target': 'workspace_files',
    'verifier_type': 'file_check',
    'type': 'file_check',
    'pass_threshold': 1.0,
    'requirement_id': 'worst_room_has_more_than_one_external_reply',
    'evidence_span': 'in the single worst room, are there more than one external replies',
    'metadata': {
        'why_justification': 'The worst room (data-v2-062) has 2 stranded replies total: 1 self-reply by Levi and 1 external reply by Mitali. The external reply count is 1, not more than 1. A run that confuses total replies with external replies answers True instead of False.'
    },
    'verifier_spec': {
        'task_id': 'worst_room_has_more_than_one_external_reply',
        'verifiers': [{
            'name': 'worst_room_has_more_than_one_external_reply',
            'metadata': {
                'how_justification': 'Reads metrics.json and requires worst_room_has_more_than_one_external_reply = false.',
                'why_justification': 'The worst room has exactly 1 external reply, not more than 1.'
            },
            'source': {'type': 'file', 'file': {'type': 'json', 'command': 'read_file', 'arguments': {'path': 'metrics.json'}}},
            'assertion': {'type': 'deterministic', 'expected': False, 'deterministic': {'path': '$.worst_room_has_more_than_one_external_reply', 'comparison': 'equals'}}
        }]
    }
}
m['verifier_configs'].append(new_v)

# Update instruction_sha256
with open(instr_path, 'rb') as f:
    instr_hash = hashlib.sha256(f.read()).hexdigest()
m['instruction_sha256'] = instr_hash

with open(manifest_path, 'w', encoding='utf-8') as f:
    json.dump(m, f, indent=2, ensure_ascii=False)
    f.write('\n')

# Update artifact_plan.json
plan_path = r'C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\task-sources\the-thread-that-outlived-its-own-start-v7\solution\artifact_plan.json'
with open(plan_path, 'r', encoding='utf-8') as f:
    plan = json.load(f)
plan['json']['worst_room_has_more_than_one_external_reply'] = False
with open(plan_path, 'w', encoding='utf-8') as f:
    json.dump(plan, f, indent=2)
    f.write('\n')

# Sync to environment/_app
base = r'C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\task-sources\the-thread-that-outlived-its-own-start-v7'
shutil.copy2(instr_path, base + r'\environment\_app\instruction.md')
shutil.copy2(manifest_path, base + r'\environment\_app\tests\manifest.json')

print('Added worst_room_has_more_than_one_external_reply = false')
print('Instruction SHA256: ' + instr_hash)
print('Total verifiers: %d' % len(m['verifier_configs']))
