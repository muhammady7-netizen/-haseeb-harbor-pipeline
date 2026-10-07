import json, hashlib, shutil

base = r'C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\task-sources\the-thread-that-outlived-its-own-start-v7'

# 1. Fix instruction
instr_path = base + r'\instruction.md'
with open(instr_path, 'r', encoding='utf-8') as f:
    instr = f.read()

instr = instr.replace(
    'Rooms where self-replies equal or exceed external replies are excluded. In alphabetical\n  order.',
    'Rooms where self-replies equal or exceed external replies are excluded. In alphabetical\n  order by channel ID.'
)
instr = instr.replace(
    'have a live orphaned thread, in alphabetical order.',
    'have a live orphaned thread, in alphabetical order by channel ID.'
)

with open(instr_path, 'w', encoding='utf-8') as f:
    f.write(instr)

# 2. Fix manifest
manifest_path = base + r'\tests\manifest.json'
with open(manifest_path, 'r', encoding='utf-8') as f:
    m = json.load(f)

for v in m['verifier_configs']:
    if v['name'] == 'rooms_with_more_external_than_self':
        for verifier in v['verifier_spec']['verifiers']:
            verifier['assertion']['expected'] = ['C5H1G0LC1A6C', 'C62RIISXI1FD']
            verifier['metadata']['how_justification'] = (
                'Reads metrics.json and requires rooms_with_more_external_than_self '
                'to equal the list sorted alphabetically by channel ID.'
            )
            verifier['metadata']['why_justification'] = (
                'general-marketing-analytics and mobile-090 have more external than self. '
                'Alphabetical by channel ID: C5H1G0LC1A6C comes before C62RIISXI1FD.'
            )

# Update instruction_sha256
with open(instr_path, 'rb') as f:
    instr_hash = hashlib.sha256(f.read()).hexdigest()
m['instruction_sha256'] = instr_hash

with open(manifest_path, 'w', encoding='utf-8') as f:
    json.dump(m, f, indent=2, ensure_ascii=False)
    f.write('\n')

# 3. Fix artifact_plan.json
plan_path = base + r'\solution\artifact_plan.json'
with open(plan_path, 'r', encoding='utf-8') as f:
    plan = json.load(f)
plan['json']['rooms_with_more_external_than_self'] = ['C5H1G0LC1A6C', 'C62RIISXI1FD']
with open(plan_path, 'w', encoding='utf-8') as f:
    json.dump(plan, f, indent=2)
    f.write('\n')

# 4. Sync to environment/_app
shutil.copy2(instr_path, base + r'\environment\_app\instruction.md')
shutil.copy2(manifest_path, base + r'\environment\_app\tests\manifest.json')

print('Fixed rooms_with_more_external_than_self: alphabetical by channel ID')
print('Instruction SHA256: ' + instr_hash)
print('Total verifiers: %d' % len(m['verifier_configs']))
