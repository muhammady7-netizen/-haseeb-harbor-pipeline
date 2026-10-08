import json, os, shutil, zipfile, hashlib

src = r'C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\task-sources\the-thread-that-outlived-its-own-start-v22-final'
dst = r'C:\Users\HASEEB~1\AppData\Local\Temp\opencode\v24b-fixed'
if os.path.exists(dst): shutil.rmtree(dst)
shutil.copytree(src, dst)
print('Copied v22-final')

base = dst
manifest_path = os.path.join(base, 'tests', 'manifest.json')
manifest_app_path = os.path.join(base, 'environment', '_app', 'tests', 'manifest.json')
test_outputs_path = os.path.join(base, 'tests', 'test_outputs.py')
test_outputs_app_path = os.path.join(base, 'environment', '_app', 'tests', 'test_outputs.py')
instr_path = os.path.join(base, 'instruction.md')
task_toml_path = os.path.join(base, 'task.toml')

m = json.loads(open(manifest_path, 'r', encoding='utf-8').read())

# Fix 1: Fix the OUTER why_justification for worst_room_total_retractions (says 2, should say 1)
for v in m['verifier_configs']:
    if v['name'] == 'worst_room_total_retractions':
        v['metadata']['why_justification'] = 'data-v2-062 has 1 retracted message (the orphaned thread with replies). The instruction says count all retracted messages including ones with zero replies, but data-v2-062 only has 1 retraction total.'
        print('Fixed outer why_justification: worst_room_total_retractions (2 -> 1)')

    if v['name'] == 'total_retractions_across_all_rooms':
        v['metadata']['why_justification'] = '5 total retracted messages: 1 each in general-marketing-analytics, perf-070, mobile-090, perf-v2-020, and 1 in data-v2-062.'
        print('Fixed outer why_justification: total_retractions_across_all_rooms')

    if v['name'] == 'rooms_with_retraction_but_no_reply':
        v['metadata']['why_justification'] = 'Only perf-v2-020 has a retracted message with zero replies. data-v2-062 has only 1 retraction (with replies).'
        print('Fixed outer why_justification: rooms_with_retraction_but_no_reply')

# Fix 2: Fix the rubric (from v23 fix)
new_rubric = (
    "Graded against the AGENT TRACE. Look at the slack_send_message tool call in the trace and read its message argument. "
    "PASS if the message explicitly mentions that the retractor (Levi) also replied to their own retracted thread (a self-reply), "
    "AND explains why the retractor is not the notify candidate (they already know they retracted their own message, so they do not need to be told). "
    "The message must mention both the self-reply fact and the exclusion reasoning. "
    "A message that says Levi retracted his own message and also replied to it so he already knows about the retraction or equivalent PASSES. "
    "A message that mentions the self-reply but does not explain the exclusion FAILS. "
    "A message that explains the exclusion but does not mention the self-reply FAILS."
)
for v in m['verifier_configs']:
    if v['name'] == 'message_explains_self_reply_implication':
        v['rubric'] = new_rubric
        print('Fixed rubric: message_explains_self_reply_implication')

# Fix 3: CSV header check - switch to inspect_table + equals
for v in m['verifier_configs']:
    if v['name'] == 'csv_header_is_the_pinned_columns_in_order':
        for verifier in v['verifier_spec']['verifiers']:
            if verifier['name'] == 'header_is_the_pinned_columns_in_order':
                verifier['source']['file']['command'] = 'inspect_table'
                verifier['assertion'] = {
                    'type': 'deterministic',
                    'expected': ['channel_id', 'channel_name', 'retracted_message_author_id', 'retracted_message_author_name', 'stranded_reply_count'],
                    'deterministic': {
                        'path': '$.header',
                        'comparison': 'equals'
                    }
                }
                verifier['metadata']['how_justification'] = 'Reads the CSV header through csv.inspect_table and requires the header list to EQUAL the five pinned names, in the pinned order, exactly as the prompt writes them.'
                print('Fixed CSV header check: regex_match -> inspect_table + equals')

# Fix 4: Fix test_outputs.py - add VerifierInfrastructureError check
to = open(test_outputs_path, 'r', encoding='utf-8').read()

old_line = '    weighted = float(block.get("score") or 0.0)\n    core_passed = bool(block.get("core_passed", True))\n    failure_mode = block.get("failure_mode") or ("pass" if core_passed else "wrong_answer")'
new_line = '''    weighted = float(block.get("score") or 0.0)
    core_passed = bool(block.get("core_passed", True))
    failure_mode = block.get("failure_mode") or ("pass" if core_passed else "wrong_answer")

    # HARBOR-LOCAL: abort the run when the engine reports a verifier_error
    # (judge outage, unusable response, or no-majority verdict) instead of
    # silently recording reward 0.0. The pipeline's judge_failure_scored_zero
    # check requires this — a judge failure must not be scored as 0.
    if failure_mode == "verifier_error":
        items = block.get("items") or []
        unscored = [it for it in items if it.get("unscored")]
        if unscored:
            raise VerifierInfrastructureError(
                f"Engine reported verifier_error with {len(unscored)} unscored "
                f"rubric_check item(s); aborting instead of recording reward 0.0"
            )'''

if old_line in to:
    to = to.replace(old_line, new_line)
    print('Fixed test_outputs.py: added VerifierInfrastructureError check')
else:
    print('WARNING: could not find exact target line in test_outputs.py, trying simpler match')
    simple_old = '    weighted = float(block.get("score") or 0.0)'
    if simple_old in to:
        to = to.replace(simple_old, new_line.split('\n')[0] + '\n' + new_line.split('\n', 1)[1])
        print('Fixed test_outputs.py: added VerifierInfrastructureError check (simple match)')
    else:
        print('ERROR: could not find target line in test_outputs.py')

# Add VerifierInfrastructureError class if missing
if 'class VerifierInfrastructureError' not in to:
    lines = to.split('\n')
    for i, line in enumerate(lines):
        if line.startswith('class ') and i > 100:
            lines.insert(i, 'class VerifierInfrastructureError(Exception):\n    """Raised when the verifier engine reports an infrastructure error (judge outage, unscored items)."""\n    pass\n')
            break
    to = '\n'.join(lines)
    print('Added VerifierInfrastructureError class')

open(test_outputs_path, 'w', encoding='utf-8', newline='\n').write(to)
shutil.copy2(test_outputs_path, test_outputs_app_path)
print('Synced test_outputs.py to _app')

# Fix 5: Fix task.toml scenario_description to not claim 2 retracted messages in data-v2-062
task_toml = open(task_toml_path, 'r', encoding='utf-8').read()
# The scenario_description mentions data-v2-062 having "two retracted messages" — fix it
# This is in a metadata blob, so we need to be careful
if 'two retracted messages' in task_toml:
    task_toml = task_toml.replace('two retracted messages', 'one retracted message')
    print('Fixed task.toml: two retracted messages -> one retracted message')
if 'second retraction' in task_toml:
    task_toml = task_toml.replace('second retraction', 'retraction')
    print('Fixed task.toml: second retraction -> retraction')
open(task_toml_path, 'w', encoding='utf-8', newline='\n').write(task_toml)
# Also sync to _app
shutil.copy2(task_toml_path, os.path.join(base, 'environment', '_app', 'task.toml'))

# Update instruction_sha256
instr = open(instr_path, 'r', encoding='utf-8').read()
instr_hash = hashlib.sha256(instr.encode('utf-8')).hexdigest()
m['instruction_sha256'] = instr_hash

# Write manifest
with open(manifest_path, 'w', encoding='utf-8') as f:
    json.dump(m, f, indent=2, ensure_ascii=False)
    f.write('\n')
shutil.copy2(manifest_path, manifest_app_path)
print('Synced manifest to _app')

# Sync instruction to _app
shutil.copy2(instr_path, os.path.join(base, 'environment', '_app', 'instruction.md'))

# Fix ALL CRLF in binary mode
fixed = 0
for root, dirs, files in os.walk(base):
    dirs[:] = [d for d in dirs if d not in {'__pycache__', '.git', '.pytest_cache'}]
    for f in files:
        if f.endswith('.pyc'): continue
        fpath = os.path.join(root, f)
        content = open(fpath, 'rb').read()
        if b'\r\n' in content:
            with open(fpath, 'wb') as fh:
                fh.write(content.replace(b'\r\n', b'\n'))
            fixed += 1
print('Fixed CRLF in %d files' % fixed)

# Verify gold values unchanged
plan_path = os.path.join(base, 'solution', 'artifact_plan.json')
plan = json.loads(open(plan_path, 'r', encoding='utf-8').read())
print('\nGold values (unchanged):')
print('  worst_room_total_retractions =', plan['json']['worst_room_total_retractions'])
print('  total_retractions_across_all_rooms =', plan['json']['total_retractions_across_all_rooms'])
print('  rooms_with_retraction_but_no_reply =', plan['json']['rooms_with_retraction_but_no_reply'])

# Zip
zip_dir = r'C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\canonical-zips'
output_zip = os.path.join(zip_dir, 'UPLOAD-THIS-TO-QC-the-thread-v24b-fixed.zip')
with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in {'__pycache__', '.git', '.pytest_cache'}]
        for f in files:
            if f.endswith('.pyc'): continue
            full = os.path.join(root, f)
            rel = os.path.relpath(full, base)
            arc = 'the-thread-that-outlived-its-own-start/' + rel.replace(os.sep, '/')
            zf.writestr(arc, open(full, 'rb').read())

print('\nZip: %d bytes, %d verifiers' % (os.path.getsize(output_zip), len(m['verifier_configs'])))
