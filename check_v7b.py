import json, re, os

for name, path in [('T1-v7', 'task-sources/the-answer-she-already-gave-v7'), ('T2-v7', 'task-sources/the-thread-that-outlived-its-own-start-v7')]:
    print(f'=== {name} ===')
    mp = os.path.join(path, 'tests', 'manifest.json')
    if os.path.exists(mp):
        with open(mp, 'r', encoding='utf-8-sig') as f:
            m = json.load(f)
        print(f'  Verifiers: {len(m.get("verifier_configs", []))}')
    else:
        print(f'  manifest NOT FOUND at {mp}')
    ip = os.path.join(path, 'instruction.md')
    if os.path.exists(ip):
        with open(ip, 'r', encoding='utf-8-sig') as f:
            instr = f.read()
        keys = re.findall(r'^- `(\w+)`', instr, re.MULTILINE)
        print(f'  Keys: {len(keys)} = {keys}')
        print(f'  Has search_email: {"search_email" in instr}')
        print(f'  Has organizer: {"organizer" in instr}')
        print(f'  Has slack_read_channel: {"slack_read_channel" in instr}')
        print(f'  Has audit_has_exact_keys: {"audit_has_exact_keys" in instr}')
    else:
        print(f'  instruction NOT FOUND at {ip}')
    tp = os.path.join(path, 'task.toml')
    if os.path.exists(tp):
        with open(tp, 'r', encoding='utf-8-sig') as f:
            toml = f.read()
        print(f'  Has zai-org: {"zai-org" in toml}')
        print(f'  Has b1374cd8: {"b1374cd8" in toml}')
    print()
