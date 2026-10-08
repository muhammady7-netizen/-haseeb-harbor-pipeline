import json, os, shutil, zipfile, hashlib

src = r'C:\Users\HASEEB~1\AppData\Local\Temp\opencode\v25-harder'
dst = r'C:\Users\HASEEB~1\AppData\Local\Temp\opencode\v26-binarized'
if os.path.exists(dst): shutil.rmtree(dst)
shutil.copytree(src, dst)
print('Copied v25-harder')

base = dst

# Fix 1: Binarize reward in test_outputs.py
to_path = os.path.join(base, 'tests', 'test_outputs.py')
to_app_path = os.path.join(base, 'environment', '_app', 'tests', 'test_outputs.py')
to = open(to_path, 'r', encoding='utf-8').read()

# Fix 1a: In flat_verifier_scoring branch, binarize scored_weighted
old_scoring = '        scored_weighted = (_pw / _tw) if _tw > 0 else 0.0'
new_scoring = '        scored_weighted = 1.0 if (_tw > 0 and _pw == _tw) else 0.0'
if old_scoring in to:
    to = to.replace(old_scoring, new_scoring)
    print('Fixed flat_verifier_scoring: binarized scored_weighted')
else:
    print('WARNING: could not find flat_verifier_scoring scored_weighted line')

# Fix 1b: In _emit_engine_owned_reward, binarize the weighted score
old_emit = '    weighted = float(block.get("score") or 0.0)\n    core_passed = bool(block.get("core_passed", True))'
new_emit = '    core_passed = bool(block.get("core_passed", True))\n    weighted = 1.0 if core_passed else 0.0'
if old_emit in to:
    to = to.replace(old_emit, new_emit)
    print('Fixed _emit_engine_owned_reward: binarized weighted')
else:
    print('WARNING: could not find _emit_engine_owned_reward weighted line')

# Fix 1c: Also binarize the rubric overall score
old_rubric = '    if flat_mode:\n        overall = (sum(it["score"] for it in item_details) / len(item_details)) if item_details else 0.0'
new_rubric = '    if flat_mode:\n        overall = 1.0 if (item_details and all(it["score"] >= 1.0 for it in item_details)) else 0.0'
if old_rubric in to:
    to = to.replace(old_rubric, new_rubric)
    print('Fixed rubric flat_mode: binarized overall')
else:
    print('WARNING: could not find rubric flat_mode overall line')

open(to_path, 'w', encoding='utf-8', newline='\n').write(to)
shutil.copy2(to_path, to_app_path)
print('Synced test_outputs.py to _app')

# Fix 2: Fix README.md stale count
readme_path = os.path.join(base, 'README.md')
if os.path.exists(readme_path):
    readme = open(readme_path, 'r', encoding='utf-8').read()
    readme = readme.replace('2/4', '3/4')
    open(readme_path, 'w', encoding='utf-8', newline='\n').write(readme)
    print('Fixed README.md: 2/4 -> 3/4')

# Fix 3: Update instruction_sha256 in manifest
manifest_path = os.path.join(base, 'tests', 'manifest.json')
manifest_app_path = os.path.join(base, 'environment', '_app', 'tests', 'manifest.json')
instr_path = os.path.join(base, 'instruction.md')
m = json.loads(open(manifest_path, 'r', encoding='utf-8').read())
instr = open(instr_path, 'r', encoding='utf-8').read()
instr_hash = hashlib.sha256(instr.encode('utf-8')).hexdigest()
m['instruction_sha256'] = instr_hash
with open(manifest_path, 'w', encoding='utf-8') as f:
    json.dump(m, f, indent=2, ensure_ascii=False)
    f.write('\n')
shutil.copy2(manifest_path, manifest_app_path)
print('Updated manifest instruction_sha256')

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
output_zip = os.path.join(zip_dir, 'UPLOAD-THIS-TO-QC-the-thread-v26-binarized.zip')
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
