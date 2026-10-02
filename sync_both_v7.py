import json, re, hashlib, shutil

# Thread task
t = r'C:\Users\HASEEB~1\AppData\Local\Temp\opencode\thread\the-thread-that-outlived-its-own-start'
sha_t = hashlib.sha256(open(t + r'\instruction.md','rb').read()).hexdigest()
for p in [t + r'\tests\manifest.json', t + r'\environment\_app\tests\manifest.json']:
    c = open(p,'r',encoding='utf-8').read()
    c = re.sub(r'"instruction_sha256"\s*:\s*"[a-f0-9]+"', '"instruction_sha256": "' + sha_t + '"', c)
    open(p,'w',encoding='utf-8').write(c)
shutil.copy2(t + r'\instruction.md', t + r'\environment\_app\instruction.md')
shutil.copy2(t + r'\tests\manifest.json', t + r'\environment\_app\tests\manifest.json')
print('Thread sha:', sha_t[:16])

# Answer task
a = r'C:\Users\HASEEB~1\AppData\Local\Temp\opencode\answer\the-answer-she-already-gave'
sha_a = hashlib.sha256(open(a + r'\instruction.md','rb').read()).hexdigest()
for p in [a + r'\tests\manifest.json', a + r'\environment\_app\tests\manifest.json']:
    c = open(p,'r',encoding='utf-8').read()
    c = re.sub(r'"instruction_sha256"\s*:\s*"[a-f0-9]+"', '"instruction_sha256": "' + sha_a + '"', c)
    open(p,'w',encoding='utf-8').write(c)
shutil.copy2(a + r'\instruction.md', a + r'\environment\_app\instruction.md')
shutil.copy2(a + r'\tests\manifest.json', a + r'\environment\_app\tests\manifest.json')
shutil.copy2(a + r'\tests\test_outputs.py', a + r'\environment\_app\tests\test_outputs.py')
print('Answer sha:', sha_a[:16])

# Verify
for name, base in [('Thread', t), ('Answer', a)]:
    m = json.load(open(base + r'\tests\manifest.json','r',encoding='utf-8'))
    r = hashlib.sha256(open(base + r'\instruction.md','rb').read()).hexdigest()[:16]
    ap = hashlib.sha256(open(base + r'\environment\_app\instruction.md','rb').read()).hexdigest()[:16]
    print(f'{name}: {len(m["verifier_configs"])} verifiers, mirror={r==ap}')
