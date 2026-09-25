import zipfile, json, io
z = zipfile.ZipFile(r'C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\UPLOAD-THIS-TO-QC-bus-b50.zip')
base = 'bus-b50-b10-streaming-target-variance-attribution/'

# Dockerfile
df_raw = z.read(base + 'environment/Dockerfile')
print('=== Dockerfile ===')
print('Has USER root:', b'USER root' in df_raw)
print('Has CRLF:', b'\r\n' in df_raw)

# test.sh
ts_raw = z.read(base + 'tests/test.sh')
print('\n=== test.sh ===')
print('Has -I:', b'-I' in ts_raw)
print('Has CRLF:', b'\r\n' in ts_raw)

# review.csv
rc = z.read(base + 'review.csv').decode('utf-8')
print('\n=== review.csv (first 500 chars) ===')
print(rc[:500])

# verifier.json
spec = json.loads(z.read(base + 'tests/verifier.json'))
print('\n=== verifier.json ===')
print('Verifiers:', len(spec['verifiers']))
for v in spec['verifiers']:
    name = v.get('name','?')
    exp = v.get('assertion',{}).get('expected','')
    comp = v.get('assertion',{}).get('deterministic',{}).get('comparison','')
    if isinstance(exp, str) and len(exp) > 100:
        has_star = '.*' in exp
        has_lookahead = '(?=' in exp
        print(f'  {name}: comp={comp} regex_len={len(exp)} has_star={has_star} has_lookahead={has_lookahead}')
    elif isinstance(exp, str):
        print(f'  {name}: comp={comp} exp={exp[:80]}')
    elif isinstance(exp, list):
        print(f'  {name}: comp={comp} list_len={len(exp)}')
    elif isinstance(exp, dict):
        print(f'  {name}: comp={comp} dict_keys={list(exp.keys())[:5]}')
    else:
        print(f'  {name}: comp={comp} type={type(exp).__name__}')

# Check for CRLF in all files
print('\n=== CRLF check ===')
crlf_files = []
for n in z.namelist():
    data = z.read(n)
    if b'\r\n' in data:
        crlf_files.append(n)
print(f'CRLF files: {len(crlf_files)}')
for f in crlf_files[:10]:
    print(f'  {f}')
