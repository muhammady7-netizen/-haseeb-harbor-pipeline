import json, hashlib, os, shutil, zipfile
from collections import Counter

v9_dir = r'C:\Users\HASEEB~1\AppData\Local\Temp\opencode\v9-deep\the-thread-that-outlived-its-own-start'
fix_dir = r'C:\Users\HASEEB~1\AppData\Local\Temp\opencode\v9-fixed'
if os.path.exists(fix_dir): shutil.rmtree(fix_dir)
shutil.copytree(v9_dir, fix_dir)
print('Copied v9 to fix dir')

# 1. Fix review.csv: healthcheck retries 150 -> 40, verifier count 25 -> 29
review_path = os.path.join(fix_dir, 'review.csv')
with open(review_path, 'r', encoding='utf-8') as f:
    content = f.read()
content = content.replace('150', '40')
content = content.replace('25 verifiers', '29 verifiers')
with open(review_path, 'w', encoding='utf-8', newline='') as f:
    f.write(content)
print('Fixed review.csv: retries 150->40, verifiers 25->29')

# 2. Add RUBRIC_TRACE_RESULT_CHARS=25000 to Dockerfile
dockerfile_path = os.path.join(fix_dir, 'environment', 'Dockerfile')
with open(dockerfile_path, 'r', encoding='utf-8') as f:
    content = f.read()
if 'RUBRIC_TRACE_RESULT_CHARS' not in content:
    content = content.replace('ENV GYM_DATASET=synthetic', 'ENV GYM_DATASET=synthetic\nENV RUBRIC_TRACE_RESULT_CHARS=25000')
    with open(dockerfile_path, 'w', encoding='utf-8', newline='') as f:
        f.write(content)
    print('Added RUBRIC_TRACE_RESULT_CHARS=25000 to Dockerfile')
else:
    print('RUBRIC_TRACE_RESULT_CHARS already present')

# 3. Fix CRLF in all files
for root, dirs, files in os.walk(fix_dir):
    dirs[:] = [d for d in dirs if d not in {'__pycache__', '.git', '.pytest_cache'}]
    for f in files:
        ext = os.path.splitext(f)[1]
        if ext in {'.py', '.sh', '.toml', '.json', '.md', '.csv', '.txt', '.jsonl'}:
            fpath = os.path.join(root, f)
            content = open(fpath, 'r', encoding='utf-8').read()
            if '\r\n' in content:
                with open(fpath, 'w', encoding='utf-8', newline='\n') as fh:
                    fh.write(content.replace('\r\n', '\n'))
print('Fixed CRLF')

# 4. Verify manifest
manifest_path = os.path.join(fix_dir, 'tests', 'manifest.json')
plan_path = os.path.join(fix_dir, 'solution', 'artifact_plan.json')
with open(manifest_path, 'r', encoding='utf-8') as f:
    m = json.load(f)
with open(plan_path, 'r', encoding='utf-8') as f:
    plan = json.load(f)

verifier_names = [v['name'] for v in m['verifier_configs']]
plan_keys = set(plan['json'].keys())
print('Verifiers: %d' % len(verifier_names))
print('Artifact plan keys: %d' % len(plan_keys))

dupes = {n: c for n, c in Counter(verifier_names).items() if c > 1}
if dupes:
    print('DUPLICATES: %s' % dupes)
else:
    print('No duplicates')

# 5. Zip
zip_dir = r'C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\canonical-zips'
output_zip = os.path.join(zip_dir, 'UPLOAD-THIS-TO-QC-the-thread-v9-fixed.zip')
exclude_dirs = {'__pycache__', '.git', '.pytest_cache'}
exclude_exts = {'.pyc', '.swp', '.swo', '.orig', '.rej'}
with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(fix_dir):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for f in files:
            ext = os.path.splitext(f)[1]
            if ext in exclude_exts: continue
            full = os.path.join(root, f)
            rel = os.path.relpath(full, fix_dir)
            arc = 'the-thread-that-outlived-its-own-start/' + rel.replace(os.sep, '/')
            zf.writestr(arc, open(full, 'rb').read())
print('Zip: %d bytes' % os.path.getsize(output_zip))
print('Done!')
