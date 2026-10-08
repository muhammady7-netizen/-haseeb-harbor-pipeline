import json, os, shutil, zipfile, hashlib

src = r'C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\task-sources\the-thread-that-outlived-its-own-start-v22-final'
dst = r'C:\Users\HASEEB~1\AppData\Local\Temp\opencode\v24-fixed'
if os.path.exists(dst): shutil.rmtree(dst)
shutil.copytree(src, dst)
print('Copied v22-final')

base = dst

# Fix 1: Update gold values in artifact_plan.json
plan_path = os.path.join(base, 'solution', 'artifact_plan.json')
plan = json.loads(open(plan_path, 'r', encoding='utf-8').read())
plan['json']['worst_room_total_retractions'] = 2
plan['json']['total_retractions_across_all_rooms'] = 6
plan['json']['rooms_with_retraction_but_no_reply'] = 2
with open(plan_path, 'w', encoding='utf-8') as f:
    json.dump(plan, f, indent=2, ensure_ascii=False)
    f.write('\n')
print('Fixed artifact_plan.json: worst_room_total_retractions=2, total_retractions=6, rooms_with_retraction_but_no_reply=2')

# Fix 2: Update manifest.json gold values + justifications
manifest_path = os.path.join(base, 'tests', 'manifest.json')
manifest_app_path = os.path.join(base, 'environment', '_app', 'tests', 'manifest.json')
m = json.loads(open(manifest_path, 'r', encoding='utf-8').read())

for v in m['verifier_configs']:
    if v['name'] == 'worst_room_total_retractions':
        v['metadata']['why_justification'] = 'data-v2-062 has 2 retracted messages: one with replies (orphaned thread) and one without. The instruction says count ALL retracted messages including ones with zero replies, so the answer is 2.'
        for verifier in v['verifier_spec']['verifiers']:
            verifier['assertion']['expected'] = 2
            verifier['metadata']['how_justification'] = 'Reads metrics.json and requires worst_room_total_retractions = 2.'
            verifier['metadata']['why_justification'] = 'data-v2-062 has 2 retracted messages: one with replies (orphaned thread) and one with zero replies. The instruction says count all including zero-reply retractions.'
        print('Fixed worst_room_total_retractions: expected 1 -> 2')

    if v['name'] == 'total_retractions_across_all_rooms':
        v['metadata']['why_justification'] = '6 total retracted messages: 1 each in general-marketing-analytics, perf-070, mobile-090, perf-v2-020, and 2 in data-v2-062.'
        for verifier in v['verifier_spec']['verifiers']:
            verifier['assertion']['expected'] = 6
            verifier['metadata']['how_justification'] = 'Reads metrics.json and requires total_retractions_across_all_rooms = 6.'
            verifier['metadata']['why_justification'] = '6 total retracted messages across all six rooms: 1 each in general-marketing-analytics, perf-070, mobile-090, perf-v2-020, and 2 in data-v2-062.'
        print('Fixed total_retractions_across_all_rooms: expected 5 -> 6')

    if v['name'] == 'rooms_with_retraction_but_no_reply':
        v['metadata']['why_justification'] = 'Both perf-v2-020 and data-v2-062 have at least one retracted message with zero replies attached.'
        for verifier in v['verifier_spec']['verifiers']:
            verifier['assertion']['expected'] = 2
            verifier['metadata']['how_justification'] = 'Reads metrics.json and requires rooms_with_retraction_but_no_reply = 2.'
            verifier['metadata']['why_justification'] = 'Both perf-v2-020 and data-v2-062 have a retracted message with zero replies.'
        print('Fixed rooms_with_retraction_but_no_reply: expected 1 -> 2')

# Fix 2b: Also fix the message_explains_self_reply_implication rubric (from v23 fix)
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

# Fix 2c: CSV header check - switch to inspect_table + equals
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

# Update instruction_sha256
instr_path = os.path.join(base, 'instruction.md')
instr = open(instr_path, 'r', encoding='utf-8').read()
instr_hash = hashlib.sha256(instr.encode('utf-8')).hexdigest()
m['instruction_sha256'] = instr_hash

# Write manifest
with open(manifest_path, 'w', encoding='utf-8') as f:
    json.dump(m, f, indent=2, ensure_ascii=False)
    f.write('\n')
shutil.copy2(manifest_path, manifest_app_path)
print('Synced manifest to _app')

# Fix 3: Fix test_outputs.py - add VerifierInfrastructureError check
test_outputs_path = os.path.join(base, 'tests', 'test_outputs.py')
test_outputs_app_path = os.path.join(base, 'environment', '_app', 'tests', 'test_outputs.py')
to = open(test_outputs_path, 'r', encoding='utf-8').read()

# Add error check after line 3163 (weighted = float(block.get("score") or 0.0))
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
    print('WARNING: could not find target line in test_outputs.py')
    # Try a simpler search
    if '    weighted = float(block.get("score") or 0.0)' in to:
        to = to.replace(
            '    weighted = float(block.get("score") or 0.0)\n    core_passed = bool(block.get("core_passed", True))\n    failure_mode = block.get("failure_mode") or ("pass" if core_passed else "wrong_answer")',
            new_line
        )
        print('Fixed test_outputs.py: added VerifierInfrastructureError check (retry)')
    else:
        print('ERROR: could not find target line in test_outputs.py')

# Also check if VerifierInfrastructureError class exists
if 'class VerifierInfrastructureError' not in to:
    # Add it near the top after imports
    if 'class VerifierInfrastructureError' not in to:
        # Find a good insertion point - after the last import
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

# Re-verify gold values
print('\nGold values in artifact_plan:')
plan2 = json.loads(open(plan_path, 'r', encoding='utf-8').read())
print('  worst_room_total_retractions =', plan2['json']['worst_room_total_retractions'])
print('  total_retractions_across_all_rooms =', plan2['json']['total_retractions_across_all_rooms'])
print('  rooms_with_retraction_but_no_reply =', plan2['json']['rooms_with_retraction_but_no_reply'])

# Zip
zip_dir = r'C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\canonical-zips'
output_zip = os.path.join(zip_dir, 'UPLOAD-THIS-TO-QC-the-thread-v24-fixed.zip')
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
