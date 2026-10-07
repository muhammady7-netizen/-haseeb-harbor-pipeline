import json, os, re

for name, path in [('T1-v7', 'task-sources/the-answer-she-already-gave-v7/the-answer-she-already-gave'), ('T2-v7', 'task-sources/the-thread-that-outlived-its-own-start-v7/the-thread-that-outlived-its-own-start')]:
    print(f'=== {name} ===')
    mp = os.path.join(path, 'tests', 'manifest.json')
    if os.path.exists(mp):
        with open(mp, 'r', encoding='utf-8-sig') as f:
            m = json.load(f)
        print(f'  Verifiers: {len(m.get("verifier_configs", []))}')
    ip = os.path.join(path, 'instruction.md')
    if os.path.exists(ip):
        with open(ip, 'r', encoding='utf-8-sig') as f:
            instr = f.read()
        keys = re.findall(r'^- `(\w+)`', instr, re.MULTILINE)
        print(f'  Instruction keys: {len(keys)} = {keys}')
        print(f'  Has search_email: {"search_email" in instr}')
        print(f'  Has structural fields: {"organizer" in instr and "eventType" in instr}')
        print(f'  Has slack_read_channel: {"slack_read_channel" in instr}')
        print(f'  Has slack_read_user_profile: {"slack_read_user_profile" in instr}')
        print(f'  Has audit_has_exact_keys: {"audit_has_exact_keys" in instr}')
    tp = os.path.join(path, 'task.toml')
    if os.path.exists(tp):
        with open(tp, 'r', encoding='utf-8-sig') as f:
            toml = f.read()
        print(f'  Has zai-org: {"zai-org" in toml}')
        print(f'  Has sha256 b1374cd8: {"b1374cd8" in toml}')
    # Check v7 zips
    zpath = f'canonical-zips/UPLOAD-THIS-TO-QC-{name.replace("T1-v7","the-answer-she-already-gave").replace("T2-v7","the-thread-that-outlived-its-own-start")}-v7.zip'
    if os.path.exists(zpath):
        print(f'  Zip exists: {os.path.getsize(zpath)} bytes')
    print()
