import json, os, shutil, zipfile, hashlib

src = r'C:\Users\HASEEB~1\AppData\Local\Temp\opencode\v24b-fixed'
dst = r'C:\Users\HASEEB~1\AppData\Local\Temp\opencode\v25-harder'
if os.path.exists(dst): shutil.rmtree(dst)
shutil.copytree(src, dst)
print('Copied v24b')

base = dst
manifest_path = os.path.join(base, 'tests', 'manifest.json')
manifest_app_path = os.path.join(base, 'environment', '_app', 'tests', 'manifest.json')
instr_path = os.path.join(base, 'instruction.md')

m = json.loads(open(manifest_path, 'r', encoding='utf-8').read())

# Add a new rubric check: message_distinguishes_clean_rooms
# This is disclosed in instruction line 104-105:
# "The message must also name both clean rooms — one that had a retraction with no replies, and one that had no retractions at all."
# GLM must correctly identify which clean room is which type — harder than just naming them.
new_rubric = {
    'name': 'message_distinguishes_clean_room_types',
    'description': 'The posted message correctly identifies which clean room had a retraction with no replies vs which had no retractions at all.',
    'requirement_id': 'message_distinguishes_clean_room_types',
    'evidence_span': 'The message must also name both clean rooms — one that had a retraction with no replies, and one that had no retractions at all.',
    'category': 'core',
    'verifier_type': 'rubric_check',
    'type': 'rubric_check',
    'target': 'trace',
    'weight': 1.0,
    'target_gym_server': 'slack-gym',
    'rubric': (
        "Graded against the AGENT TRACE. Look at the slack_send_message tool call in the trace and read its message argument. "
        "The instruction requires the message to name both clean rooms and distinguish between two types: "
        "(1) a clean room that had a retraction with no replies attached, and "
        "(2) a clean room that had no retractions at all. "
        "PASS if the message correctly identifies which clean room is which type: "
        "perf-v2-020 (or its channel ID) is named as the room that had a retraction with no replies, "
        "AND mobile-v2-024 (or its channel ID) is named as the room that had no retractions at all. "
        "The message must NOT confuse the two types — saying perf-v2-020 had no retractions or saying mobile-v2-024 had a retraction with no replies FAILS. "
        "A message that names both clean rooms but does not distinguish which is which type FAILS. "
        "A message that only names one clean room FAILS."
    )
}
m['verifier_configs'].append(new_rubric)
print('Added rubric: message_distinguishes_clean_room_types')

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

# Zip
zip_dir = r'C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\canonical-zips'
output_zip = os.path.join(zip_dir, 'UPLOAD-THIS-TO-QC-the-thread-v25-harder.zip')
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
