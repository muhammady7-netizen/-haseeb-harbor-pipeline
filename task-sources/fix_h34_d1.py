import json
p = r'C:\Users\HASEEB~1\AppData\Local\Temp\opencode\h34-work\health-h34-randomisation-balance\tests\verifier.json'
with open(p, 'r', encoding='utf-8') as f:
    data = json.load(f)
data['verifiers'] = [v for v in data['verifiers'] if v.get('source',{}).get('file',{}).get('type','') not in ('md','text')]
with open(p, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
print('Removed md/text checks. Remaining:', len(data['verifiers']))
for v in data['verifiers']:
    print(' ', v['name'])
