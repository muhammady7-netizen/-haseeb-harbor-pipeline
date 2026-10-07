import json, os, shutil, zipfile, hashlib
from collections import Counter

src = r'C:\Users\HASEEB~1\AppData\Local\Temp\opencode\v9-hardened-v14'
dst = r'C:\Users\HASEEB~1\AppData\Local\Temp\opencode\v16-perfect'
if os.path.exists(dst): shutil.rmtree(dst)
shutil.copytree(src, dst)
print('Copied v14 base')

base = dst
manifest_path = os.path.join(base, 'tests', 'manifest.json')
plan_path = os.path.join(base, 'solution', 'artifact_plan.json')
instr_path = os.path.join(base, 'instruction.md')

# 1. Fix ALL contradictory why_justifications
m = json.loads(open(manifest_path, 'r', encoding='utf-8').read())
fixes = {
    'total_retractions_across_all_rooms': '5 total retracted messages: 1 each in general-marketing-analytics, perf-070, mobile-090, perf-v2-020, and 1 in data-v2-062.',
    'worst_room_total_retractions': 'data-v2-062 has 1 retracted message (the orphaned thread with replies).',
    'rooms_with_retraction_but_no_reply': 'Only perf-v2-020 has a retracted message with zero replies.',
    'worst_room_retractor_also_posted_in_clean_room': 'Levi (UYIAYBC7FYCG) did not post any non-retracted messages in either clean room.',
}
for v in m['verifier_configs']:
    if v['name'] in fixes:
        for verifier in v['verifier_spec']['verifiers']:
            verifier['metadata']['why_justification'] = fixes[v['name']]
        print('Fixed: %s' % v['name'])

# 2. Add 3 interpretive rubric_check verifiers
new_rubrics = [
    {
        'name': 'agent_explained_why_not_retractor',
        'description': 'Did the agent explain WHY the retractor is not the notify candidate.',
        'category': 'core', 'weight': 1.0,
        'verifier_type': 'rubric_check', 'type': 'rubric_check',
        'target': 'final_answer', 'target_gym_server': 'slack-gym',
        'requirement_id': 'agent_explained_why_not_retractor',
        'evidence_span': 'Dont tell me to notify the person who retracted the message themselves',
        'metadata': {'why_justification': 'Agent must explain WHY retractor is not notify candidate.'},
        'rubric': 'Graded against the agent final reply. PASS if the reply explicitly explains WHY the retractor is not the notify candidate (they already know they retracted their own message). FAIL if the reply only names the notify candidate without this reasoning.',
    },
    {
        'name': 'agent_distinguished_clean_with_retraction_from_completely_clean',
        'description': 'Did the agent explain the difference between perf-v2-020 and mobile-v2-024.',
        'category': 'core', 'weight': 1.0,
        'verifier_type': 'rubric_check', 'type': 'rubric_check',
        'target': 'final_answer', 'target_gym_server': 'slack-gym',
        'requirement_id': 'agent_distinguished_clean_with_retraction',
        'evidence_span': 'A retraction with no replies isnt a live problem',
        'metadata': {'why_justification': 'perf-v2-020 has retraction+0 replies, mobile-v2-024 has no retractions.'},
        'rubric': 'Graded against the agent final reply. PASS if the reply correctly identifies that perf-v2-020 has a retraction with zero replies while mobile-v2-024 has no retractions at all. FAIL if both clean rooms are treated identically without noting the distinction.',
    },
    {
        'name': 'agent_identified_self_reply_trap_in_worst_room',
        'description': 'Did the agent identify the self-reply trap in the worst room.',
        'category': 'core', 'weight': 1.0,
        'verifier_type': 'rubric_check', 'type': 'rubric_check',
        'target': 'trace', 'target_gym_server': 'slack-gym',
        'requirement_id': 'agent_identified_self_reply_trap',
        'evidence_span': 'Dont tell me to notify the person who retracted the message themselves',
        'metadata': {'why_justification': 'Levi retracted AND replied to own thread - self-reply trap.'},
        'rubric': 'Graded against the agent trace. PASS if the trace shows the agent compared reply authors against the retractor author and recognized the self-reply. FAIL if no such comparison exists or the agent picked the retractor as notify candidate.',
    },
]
m['verifier_configs'].extend(new_rubrics)
print('Added 3 interpretive rubric_check verifiers')

# 3. Fix instruction
instr = open(instr_path, 'r', encoding='utf-8').read()
instr = instr.replace('under exactly these keys:', 'under these keys:')
for field in ['retractor_replied_in_same_room', 'notify_candidate_also_retracted_somewhere', 'worst_room_retractor_also_posted_in_clean_room']:
    old = '- ' + field + ' (boolean):'
    new = '- `' + field + '` (boolean):'
    instr = instr.replace(old, new)
print('Fixed instruction')

# 4. Fix review.csv
review_path = os.path.join(base, 'review.csv')
review = open(review_path, 'r', encoding='utf-8').read()
review = review.replace('29 verifiers', '35 verifiers')
open(review_path, 'w', encoding='utf-8', newline='').write(review)
print('Fixed review.csv')

# 5. Fix shortcut_audit.md
audit_path = os.path.join(base, 'consistency', 'shortcut_audit.md')
audit = open(audit_path, 'r', encoding='utf-8').read()
audit = audit.replace("data-v2-062's second, unrelated retraction alongside its real orphaned thread", 'data-v2-062 has only 1 retraction (the orphaned thread)')
audit = audit.replace("perf-v2-020's only retraction, and data-v2-062's second, unrelated retraction", 'perf-v2-020 has a retraction with zero replies')
open(audit_path, 'w', encoding='utf-8', newline='').write(audit)
print('Fixed shortcut_audit.md')

# 6. Update instruction_sha256
open(instr_path, 'w', encoding='utf-8', newline='').write(instr)
instr_hash = hashlib.sha256(open(instr_path, 'rb').read()).hexdigest()
m['instruction_sha256'] = instr_hash

# 7. Write manifest
with open(manifest_path, 'w', encoding='utf-8') as f:
    json.dump(m, f, indent=2, ensure_ascii=False)
    f.write('\n')

# 8. Sync to environment/_app
shutil.copy2(instr_path, os.path.join(base, 'environment', '_app', 'instruction.md'))
shutil.copy2(manifest_path, os.path.join(base, 'environment', '_app', 'tests', 'manifest.json'))

# 9. Fix CRLF
for root, dirs, files in os.walk(base):
    dirs[:] = [d for d in dirs if d not in {'__pycache__', '.git', '.pytest_cache'}]
    for f in files:
        ext = os.path.splitext(f)[1]
        if ext in {'.py', '.sh', '.toml', '.json', '.md', '.csv', '.txt'}:
            fpath = os.path.join(root, f)
            content = open(fpath, 'r', encoding='utf-8').read()
            if '\r\n' in content:
                with open(fpath, 'w', encoding='utf-8', newline='\n') as fh:
                    fh.write(content.replace('\r\n', '\n'))

# 10. Zip
zip_dir = r'C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\canonical-zips'
output_zip = os.path.join(zip_dir, 'UPLOAD-THIS-TO-QC-the-thread-v16-perfect.zip')
with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in {'__pycache__', '.git', '.pytest_cache'}]
        for f in files:
            ext = os.path.splitext(f)[1]
            if ext in {'.pyc', '.swp', '.swo', '.orig', '.rej'}:
                continue
            full = os.path.join(root, f)
            rel = os.path.relpath(full, base)
            arc = 'the-thread-that-outlived-its-own-start/' + rel.replace(os.sep, '/')
            zf.writestr(arc, open(full, 'rb').read())

# Verify
names = [v['name'] for v in m['verifier_configs']]
dupes = {n: c for n, c in Counter(names).items() if c > 1}
print('Zip: %d bytes, %d verifiers, sha256=%s' % (os.path.getsize(output_zip), len(m['verifier_configs']), instr_hash))
print('Duplicates: %s' % (dupes if dupes else 'NONE'))
