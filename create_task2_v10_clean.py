import json, hashlib, os, shutil, zipfile

# ============================================================
# Clean Task 2 v10 from FRESH original v7
# - 4 v8 fields (no duplicates)
# - 3 v11 fields
# - 2 CSV columns
# - Fixed CSV rubric (7 columns)
# - Fixed CSV header (7 columns)
# - Updated README
# - Fixed "exactly" contradiction
# Total: 32 verifiers, 7 CSV columns
# ============================================================

fresh_dir = r'C:\Users\HASEEB~1\AppData\Local\Temp\opencode\orig-task2-fresh\the-thread-that-outlived-its-own-start'
zip_dir = r'C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\canonical-zips'
output_zip = os.path.join(zip_dir, 'UPLOAD-THIS-TO-QC-the-thread-v10-clean.zip')

# 1. Fix instruction
instr_path = os.path.join(fresh_dir, 'instruction.md')
with open(instr_path, 'r', encoding='utf-8') as f:
    instr = f.read()

# Add 7 new fields after retractor_self_reply_count
insert_after = "  stranded reply, but the retractor is never the notify candidate."
insert_point = instr.index(insert_after) + len(insert_after)

new_fields = """
- `total_external_stranded_replies` (number): across all rooms with a live orphaned thread, how
  many of the total stranded replies were written by someone OTHER than the person who retracted
  the original message. This is the count of replies that are NOT self-replies.
- `worst_room_external_reply_count` (number): in the single worst room only, how many of its
  stranded replies were written by someone other than the retractor.
- `rooms_with_self_reply_only` (array of strings): the channel IDs of every room with a live
  orphaned thread where ALL of the stranded replies on the retracted message were written by the
  retractor themselves. In alphabetical order by channel ID.
- `rooms_with_both_reply_types` (array of strings): the channel IDs of every room with a live
  orphaned thread where the retracted message has BOTH at least one self-reply AND at least one
  external reply. In alphabetical order by channel ID.
- `worst_room_external_replier_id` (string): the user ID of the person who wrote the external
  reply in the single worst room. This is the person who should be notified.
- `retractor_self_reply_in_multiple_rooms` (boolean): did any retractor reply to their own
  retracted thread in more than one room? Check each room separately.
- `total_unique_external_repliers` (number): how many unique people (by user ID) wrote external
  replies across all rooms with a live orphaned thread? Count each person once."""

instr = instr[:insert_point] + new_fields + instr[insert_point:]

# Fix CSV columns (5 -> 7)
old_csv = "with exactly these columns in this order: channel_id, channel_name,\nretracted_message_author_id, retracted_message_author_name, stranded_reply_count."
new_csv = "with exactly these columns in this order: channel_id, channel_name,\nretracted_message_author_id, retracted_message_author_name, stranded_reply_count,\nself_reply_count, external_reply_count."
instr = instr.replace(old_csv, new_csv)

with open(instr_path, 'w', encoding='utf-8') as f:
    f.write(instr)

# 2. Update manifest
manifest_path = os.path.join(fresh_dir, 'tests', 'manifest.json')
with open(manifest_path, 'r', encoding='utf-8') as f:
    m = json.load(f)

def make_fc(name, desc, req_id, evidence, expected, why, json_path='metrics.json'):
    return {
        'name': name, 'description': desc, 'category': 'core', 'weight': 1.0,
        'target': 'workspace_files', 'verifier_type': 'file_check', 'type': 'file_check',
        'pass_threshold': 1.0, 'requirement_id': req_id, 'evidence_span': evidence,
        'metadata': {'why_justification': why},
        'verifier_spec': {'task_id': req_id, 'verifiers': [{
            'name': name,
            'metadata': {'how_justification': 'Reads %s.' % json_path, 'why_justification': why},
            'source': {'type': 'file', 'file': {'type': 'json', 'command': 'read_file', 'arguments': {'path': json_path}}},
            'assertion': {'type': 'deterministic', 'expected': expected, 'deterministic': {'path': '$.%s' % name, 'comparison': 'equals'}}
        }]}
    }

# Add 7 new verifiers (NO duplicates)
m['verifier_configs'].extend([
    make_fc('total_external_stranded_replies', 'Total external stranded replies.', 'total_external_stranded_replies', 'how many were written by someone OTHER than the retractor', 3, '3 external replies across all rooms.'),
    make_fc('worst_room_external_reply_count', 'External reply count in worst room.', 'worst_room_external_reply_count', 'external reply count for just the worst room', 1, 'Worst room has 1 external reply.'),
    make_fc('rooms_with_self_reply_only', 'Rooms with only self-replies.', 'rooms_with_self_reply_only', 'rooms where ALL replies are self-replies', ['CJWT99KXPLPI'], 'Only perf-070 has self-reply only.'),
    make_fc('rooms_with_both_reply_types', 'Rooms with both reply types.', 'rooms_with_both_reply_types', 'rooms with BOTH self-reply AND external reply', ['CN20Z0W91YE0'], 'Only data-v2-062 has both types.'),
    make_fc('worst_room_external_replier_id', 'User ID of external replier in worst room.', 'worst_room_external_replier_id', 'the user ID of the person who wrote the external reply in the worst room', 'UNN2VSEY3JSW', 'Mitali Naidu wrote the external reply in data-v2-062.'),
    make_fc('retractor_self_reply_in_multiple_rooms', 'Did any retractor self-reply in multiple rooms.', 'retractor_self_reply_in_multiple_rooms', 'did any retractor reply to their own retracted thread in more than one room', False, 'Each retractor only self-replied in one room.'),
    make_fc('total_unique_external_repliers', 'How many unique people wrote external replies.', 'total_unique_external_repliers', 'how many unique people wrote external replies across all rooms', 3, '3 unique external repliers.'),
])

# Fix CSV header to 7 columns
for v in m['verifier_configs']:
    if v['name'] == 'csv_header_is_the_pinned_columns_in_order':
        v['description'] = 'orphaned_thread_audit.csv carries exactly the seven pinned columns, in the pinned order'
        v['evidence_span'] = 'with exactly these columns in this order: channel_id, channel_name, retracted_message_author_id, retracted_message_author_name, stranded_reply_count, self_reply_count, external_reply_count'
        for verifier in v['verifier_spec']['verifiers']:
            if verifier['name'] == 'header_is_the_pinned_columns_in_order':
                verifier['assertion']['expected'] = ['channel_id', 'channel_name', 'retracted_message_author_id', 'retracted_message_author_name', 'stranded_reply_count', 'self_reply_count', 'external_reply_count']
                verifier['metadata']['how_justification'] = 'Reads the CSV header and requires 7 pinned column names in order.'

# Fix CSV rubric to grade all 7 columns
for v in m['verifier_configs']:
    if v['name'] == 'csv_rows_are_right':
        for verifier in v['verifier_spec']['verifiers']:
            if verifier['name'] == 'csv_rows_are_right':
                verifier['assertion']['rubric']['prompt'] = (
                    'PASS only if the CSV contains exactly these four rooms, each correctly paired '
                    'with the real author, name, stranded-reply count, self-reply count, and '
                    'external-reply count:\n'
                    '  C62RIISXI1FD,general-marketing-analytics,UJCPV75HKG9V,Prakash Pillai Mehta,1,0,1\n'
                    '  CJWT99KXPLPI,perf-070,UWGCP00XPDCQ,Ellie Wendy Brown,1,1,0\n'
                    '  C5H1G0LC1A6C,mobile-090,UPLCK9I5ENM9,Martha Yvonne Nguyen,1,0,1\n'
                    '  CN20Z0W91YE0,data-v2-062,UYIAYBC7FYCG,Levi Francis Nguyen,2,1,1\n'
                    'Row order, quoting, whitespace and letter case are free. FAIL if any value '
                    'does not match.'
                )

# Update instruction_sha256
with open(instr_path, 'rb') as f:
    instr_hash = hashlib.sha256(f.read()).hexdigest()
m['instruction_sha256'] = instr_hash

with open(manifest_path, 'w', encoding='utf-8') as f:
    json.dump(m, f, indent=2, ensure_ascii=False)
    f.write('\n')

# 3. Update artifact_plan.json
plan_path = os.path.join(fresh_dir, 'solution', 'artifact_plan.json')
with open(plan_path, 'r', encoding='utf-8') as f:
    plan = json.load(f)
plan['json']['total_external_stranded_replies'] = 3
plan['json']['worst_room_external_reply_count'] = 1
plan['json']['rooms_with_self_reply_only'] = ['CJWT99KXPLPI']
plan['json']['rooms_with_both_reply_types'] = ['CN20Z0W91YE0']
plan['json']['worst_room_external_replier_id'] = 'UNN2VSEY3JSW'
plan['json']['retractor_self_reply_in_multiple_rooms'] = False
plan['json']['total_unique_external_repliers'] = 3
plan['csv'][0] = ['channel_id', 'channel_name', 'retracted_message_author_id', 'retracted_message_author_name', 'stranded_reply_count', 'self_reply_count', 'external_reply_count']
plan['csv'][1] = ['C62RIISXI1FD', 'general-marketing-analytics', 'UJCPV75HKG9V', 'Prakash Pillai Mehta', 1, 0, 1]
plan['csv'][2] = ['CJWT99KXPLPI', 'perf-070', 'UWGCP00XPDCQ', 'Ellie Wendy Brown', 1, 1, 0]
plan['csv'][3] = ['C5H1G0LC1A6C', 'mobile-090', 'UPLCK9I5ENM9', 'Martha Yvonne Nguyen', 1, 0, 1]
plan['csv'][4] = ['CN20Z0W91YE0', 'data-v2-062', 'UYIAYBC7FYCG', 'Levi Francis Nguyen', 2, 1, 1]
with open(plan_path, 'w', encoding='utf-8') as f:
    json.dump(plan, f, indent=2)
    f.write('\n')

# 4. Update README
readme_path = os.path.join(fresh_dir, 'README.md')
with open(readme_path, 'w', encoding='utf-8') as f:
    f.write('%d verifiers. 7 interpretive discriminators.\n' % len(m['verifier_configs']))

# 5. Sync to environment/_app
shutil.copy2(instr_path, os.path.join(fresh_dir, 'environment', '_app', 'instruction.md'))
shutil.copy2(manifest_path, os.path.join(fresh_dir, 'environment', '_app', 'tests', 'manifest.json'))

# 6. Fix CRLF
for root, dirs, files in os.walk(fresh_dir):
    dirs[:] = [d for d in dirs if d not in {'__pycache__', '.git', '.pytest_cache'}]
    for f in files:
        ext = os.path.splitext(f)[1]
        if ext in {'.py', '.sh', '.toml', '.json', '.md', '.csv', '.txt', '.jsonl'}:
            fpath = os.path.join(root, f)
            content = open(fpath, 'r', encoding='utf-8').read()
            if '\r\n' in content:
                with open(fpath, 'w', encoding='utf-8', newline='\n') as fh:
                    fh.write(content.replace('\r\n', '\n'))

# 7. Zip
exclude_dirs = {'__pycache__', '.git', '.pytest_cache'}
exclude_exts = {'.pyc', '.swp', '.swo', '.orig', '.rej'}
with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(fresh_dir):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for f in files:
            ext = os.path.splitext(f)[1]
            if ext in exclude_exts:
                continue
            full = os.path.join(root, f)
            rel = os.path.relpath(full, fresh_dir)
            arc = 'the-thread-that-outlived-its-own-start/' + rel.replace(os.sep, '/')
            zf.writestr(arc, open(full, 'rb').read())

# Verify no duplicates
names = [v['name'] for v in m['verifier_configs']]
from collections import Counter
dupes = {n: c for n, c in Counter(names).items() if c > 1}

print('Task 2 v10 clean: %d bytes, %d verifiers, sha256=%s' % (os.path.getsize(output_zip), len(m['verifier_configs']), instr_hash))
print('Duplicates:', dupes if dupes else 'NONE')
print('README: %d verifiers' % len(m['verifier_configs']))
