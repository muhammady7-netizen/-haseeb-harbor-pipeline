import json, os, shutil, zipfile, hashlib

src = r'C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\task-sources\the-thread-that-outlived-its-own-start-v22-final'
dst = r'C:\Users\HASEEB~1\AppData\Local\Temp\opencode\v23-fixed'
if os.path.exists(dst): shutil.rmtree(dst)
shutil.copytree(src, dst)
print('Copied v22-final')

base = dst
manifest_path = os.path.join(base, 'tests', 'manifest.json')
manifest_app_path = os.path.join(base, 'environment', '_app', 'tests', 'manifest.json')
instr_path = os.path.join(base, 'instruction.md')

m = json.loads(open(manifest_path, 'r', encoding='utf-8').read())

# Fix 1: message_explains_self_reply_implication rubric
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

# Fix 2: header_is_the_pinned_columns_in_order - switch to inspect_table + equals
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
instr = open(instr_path, 'r', encoding='utf-8').read()
instr_hash = hashlib.sha256(instr.encode('utf-8')).hexdigest()
m['instruction_sha256'] = instr_hash

# Write manifest
with open(manifest_path, 'w', encoding='utf-8') as f:
    json.dump(m, f, indent=2, ensure_ascii=False)
    f.write('\n')
shutil.copy2(manifest_path, manifest_app_path)
print('Synced manifest to _app')

# Fix CRLF
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

# Zip
zip_dir = r'C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\canonical-zips'
output_zip = os.path.join(zip_dir, 'UPLOAD-THIS-TO-QC-the-thread-v23-fixed.zip')
with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in {'__pycache__', '.git', '.pytest_cache'}]
        for f in files:
            ext = os.path.splitext(f)[1]
            if ext in {'.pyc', '.swp', '.swo', '.orig', '.rej'}: continue
            full = os.path.join(root, f)
            rel = os.path.relpath(full, base)
            arc = 'the-thread-that-outlived-its-own-start/' + rel.replace(os.sep, '/')
            zf.writestr(arc, open(full, 'rb').read())

print('Zip: %d bytes, %d verifiers' % (os.path.getsize(output_zip), len(m['verifier_configs'])))
