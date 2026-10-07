import json, hashlib, zipfile, os, shutil

# ============================================================
# Create minimal fix versions from original v7 zips
# Task 1: Original v7 + draft body rubric_check ONLY
# Task 2: Original v7 (no changes)
# ============================================================

temp_dir = r'C:\Users\HASEEB~1\AppData\Local\Temp\opencode'
zip_dir = r'C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\canonical-zips'

# --- Task 1: Add draft body rubric_check to original v7 ---
task1_src = os.path.join(temp_dir, 'orig-task1-v7', 'the-answer-she-already-gave')
task1_manifest = os.path.join(task1_src, 'tests', 'manifest.json')

with open(task1_manifest, 'r', encoding='utf-8') as f:
    m1 = json.load(f)

# Check if draft body verifier already exists
has_draft_body = any(v.get('name') == 'draft_body_asks_to_confirm_attendance' for v in m1['verifier_configs'])
if not has_draft_body:
    # Add draft body rubric_check
    draft_body_verifier = {
        'name': 'draft_body_asks_to_confirm_attendance',
        'description': 'The draft body must contain language asking the recipient to confirm their attendance.',
        'category': 'core',
        'verifier_type': 'rubric_check',
        'type': 'rubric_check',
        'target': 'trace',
        'target_gym_server': 'email-calendar-gym',
        'weight': 1.0,
        'requirement_id': 'draft_body_requests_confirmation',
        'evidence_span': 'The draft body must explicitly ask the recipient to confirm their attendance',
        'metadata': {
            'why_justification': 'Instruction requires the draft to ask the attendee to confirm their attendance. A draft with correct To and Subject but an empty or off-topic body fails this check.'
        },
        'rubric': (
            'Graded against the AGENT TRACE. PASS if the draft_email call in the trace includes '
            'a body argument that explicitly asks the recipient to confirm their attendance. '
            'The body must contain language about confirming or attending. FAIL if the draft_email '
            'call has an empty body, a body that does not mention confirming or attending, or if '
            'no draft_email call is present in the trace.'
        )
    }
    m1['verifier_configs'].append(draft_body_verifier)
    print('Task 1: Added draft_body_asks_to_confirm_attendance rubric_check')
else:
    print('Task 1: draft_body_asks_to_confirm_attendance already exists')

with open(task1_manifest, 'w', encoding='utf-8') as f:
    json.dump(m1, f, indent=2, ensure_ascii=False)
    f.write('\n')

# Sync manifest to environment/_app
shutil.copy2(task1_manifest, os.path.join(task1_src, 'environment', '_app', 'tests', 'manifest.json'))

# Fix CRLF in all files
for root, dirs, files in os.walk(task1_src):
    dirs[:] = [d for d in dirs if d not in {'__pycache__', '.git', '.pytest_cache'}]
    for f in files:
        ext = os.path.splitext(f)[1]
        if ext in {'.py', '.sh', '.toml', '.json', '.md', '.csv', '.txt', '.jsonl'}:
            fpath = os.path.join(root, f)
            content = open(fpath, 'r', encoding='utf-8').read()
            if '\r\n' in content:
                with open(fpath, 'w', encoding='utf-8', newline='\n') as fh:
                    fh.write(content.replace('\r\n', '\n'))

# Zip Task 1
task1_zip = os.path.join(zip_dir, 'UPLOAD-THIS-TO-QC-the-answer-she-already-gave-v9-minimal.zip')
exclude_dirs = {'__pycache__', '.git', '.pytest_cache'}
exclude_exts = {'.pyc', '.swp', '.swo', '.orig', '.rej'}
with zipfile.ZipFile(task1_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(task1_src):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for f in files:
            ext = os.path.splitext(f)[1]
            if ext in exclude_exts:
                continue
            full = os.path.join(root, f)
            rel = os.path.relpath(full, task1_src)
            arc = 'the-answer-she-already-gave/' + rel.replace(os.sep, '/')
            zf.writestr(arc, open(full, 'rb').read())
print('Task 1: %s (%d bytes, %d verifiers)' % (os.path.basename(task1_zip), os.path.getsize(task1_zip), len(m1['verifier_configs'])))

# --- Task 2: No changes needed ---
task2_src = os.path.join(temp_dir, 'orig-task2-v7', 'the-thread-that-outlived-its-own-start')
task2_zip = os.path.join(zip_dir, 'UPLOAD-THIS-TO-QC-the-thread-that-outlived-its-own-start-v9-minimal.zip')
with zipfile.ZipFile(task2_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(task2_src):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for f in files:
            ext = os.path.splitext(f)[1]
            if ext in exclude_exts:
                continue
            full = os.path.join(root, f)
            rel = os.path.relpath(full, task2_src)
            arc = 'the-thread-that-outlived-its-own-start/' + rel.replace(os.sep, '/')
            zf.writestr(arc, open(full, 'rb').read())
print('Task 2: %s (%d bytes)' % (os.path.basename(task2_zip), os.path.getsize(task2_zip)))

print('\nDone! Minimal fix versions created.')
