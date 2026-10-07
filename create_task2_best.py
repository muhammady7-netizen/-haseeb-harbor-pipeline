import json, hashlib, os, shutil, zipfile

# ============================================================
# Create the BEST Task 2 version:
# Original v7 + 4 new interpretive fields + 2 CSV columns + fixed CSV rubric
# This is the v2 version (which got 3/4) with the CSV rubric fix
# ============================================================

orig_dir = r'C:\Users\HASEEB~1\AppData\Local\Temp\opencode\orig-task2-v7\the-thread-that-outlived-its-own-start'
zip_dir = r'C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\canonical-zips'
output_zip = os.path.join(zip_dir, 'UPLOAD-THIS-TO-QC-the-thread-v10-best.zip')

# 1. Read original instruction
instr_path = os.path.join(orig_dir, 'instruction.md')
with open(instr_path, 'r', encoding='utf-8') as f:
    instr = f.read()

# 2. Add 4 new fields + 2 CSV columns to instruction
# Find the insertion point (after the last instruction field, before "Then find the single worst room")
marker = "Then find the single worst room - the one with the most such replies - and"
if marker not in instr:
    # Try alternate
    marker = "Then, for the one meeting"

# Actually, let me find the right insertion point
# The original instruction ends the metrics.json section with the last key, then starts the CSV section
# Let me find "Write the numbers to" which starts the metrics section
metrics_start = instr.index("Write the numbers to")
csv_start = instr.index("List every room")

# Insert new fields between the last original field and the CSV section
# Find the last original field (retractor_self_reply_count... wait, that doesn't exist in original)
# The original v7 instruction has these fields:
# channels_with_live_orphaned_threads, total_stranded_replies, worst_channel_id, 
# worst_channel_stranded_reply_count, notify_candidate_id, notify_candidate_name
# Then additional fields: worst_room_retractor_id, retracted_msg_author_also_replied,
# worst_room_has_self_reply, notify_candidate_is_not_retractor, retractor_also_notifiable,
# clean_rooms_count, clean_room_ids, retractor_self_reply_count

# Find the line after retractor_self_reply_count
insert_after = "  stranded reply, but the retractor is never the notify candidate."
insert_point = instr.index(insert_after) + len(insert_after)

new_fields = """
- `total_external_stranded_replies` (number): across all rooms with a live orphaned thread, how
  many of the total stranded replies were written by someone OTHER than the person who retracted
  the original message. This is the count of replies that are NOT self-replies.
- `worst_room_external_reply_count` (number): in the single worst room only, how many of its
  stranded replies were written by someone other than the retractor. This is the external reply
  count for just the worst room.
- `rooms_with_self_reply_only` (array of strings): the channel IDs of every room with a live
  orphaned thread where ALL of the stranded replies on the retracted message were written by the
  retractor themselves. These rooms have stranded replies but no external person to notify. In
  alphabetical order by channel ID.
- `rooms_with_both_reply_types` (array of strings): the channel IDs of every room with a live
  orphaned thread where the retracted message has BOTH at least one self-reply (from the
  retractor) AND at least one external reply (from someone else). In alphabetical order by
  channel ID."""

instr = instr[:insert_point] + new_fields + instr[insert_point:]

# 3. Update CSV columns in instruction
old_csv = "with exactly these columns in this order: channel_id, channel_name,\nretracted_message_author_id, retracted_message_author_name, stranded_reply_count."
new_csv = "with exactly these columns in this order: channel_id, channel_name,\nretracted_message_author_id, retracted_message_author_name, stranded_reply_count,\nself_reply_count, external_reply_count."
instr = instr.replace(old_csv, new_csv)

# Write updated instruction
temp_instr = os.path.join(orig_dir, 'instruction.md')
with open(temp_instr, 'w', encoding='utf-8') as f:
    f.write(instr)

# 4. Update manifest
manifest_path = os.path.join(orig_dir, 'tests', 'manifest.json')
with open(manifest_path, 'r', encoding='utf-8') as f:
    m = json.load(f)

# Add 4 new verifiers
def make_fc(name, desc, req_id, evidence, expected, why, json_path="metrics.json"):
    return {
        "name": name, "description": desc, "category": "core", "weight": 1.0,
        "target": "workspace_files", "verifier_type": "file_check", "type": "file_check",
        "pass_threshold": 1.0, "requirement_id": req_id, "evidence_span": evidence,
        "metadata": {"why_justification": why},
        "verifier_spec": {"task_id": req_id, "verifiers": [{
            "name": name,
            "metadata": {"how_justification": "Reads %s." % json_path, "why_justification": why},
            "source": {"type": "file", "file": {"type": "json", "command": "read_file", "arguments": {"path": json_path}}},
            "assertion": {"type": "deterministic", "expected": expected, "deterministic": {"path": "$.%s" % name, "comparison": "equals"}}
        }]}
    }

m['verifier_configs'].extend([
    make_fc("total_external_stranded_replies", "Total external stranded replies.", "total_external_stranded_replies", "how many were written by someone OTHER than the retractor", 3, "3 external replies across all rooms."),
    make_fc("worst_room_external_reply_count", "External reply count in worst room.", "worst_room_external_reply_count", "external reply count for just the worst room", 1, "Worst room has 1 external reply."),
    make_fc("rooms_with_self_reply_only", "Rooms with only self-replies.", "rooms_with_self_reply_only", "rooms where ALL replies are self-replies", ["CJWT99KXPLPI"], "Only perf-070 has self-reply only."),
    make_fc("rooms_with_both_reply_types", "Rooms with both reply types.", "rooms_with_both_reply_types", "rooms with BOTH self-reply AND external reply", ["CN20Z0W91YE0"], "Only data-v2-062 has both types."),
])

# 5. Fix CSV header to 7 columns
for v in m['verifier_configs']:
    if v['name'] == 'csv_header_is_the_pinned_columns_in_order':
        for verifier in v['verifier_spec']['verifiers']:
            if verifier['name'] == 'header_is_the_pinned_columns_in_order':
                verifier['assertion']['expected'] = [
                    'channel_id', 'channel_name', 'retracted_message_author_id',
                    'retracted_message_author_name', 'stranded_reply_count',
                    'self_reply_count', 'external_reply_count'
                ]
                verifier['metadata']['how_justification'] = 'Reads the CSV header and requires 7 pinned column names in order.'

# 6. Fix CSV rubric to grade all 7 columns
for v in m['verifier_configs']:
    if v['name'] == 'csv_rows_are_right':
        for verifier in v['verifier_spec']['verifiers']:
            if verifier['name'] == 'csv_rows_are_right':
                verifier['assertion']['rubric']['prompt'] = (
                    'PASS only if the CSV contains exactly these four rooms, each correctly paired '
                    'with the real author of that room own retracted-and-replied-to message, that '
                    'author real name, that room stranded-reply count, that room self-reply count, '
                    'and that room external-reply count:\n'
                    '  C62RIISXI1FD,general-marketing-analytics,UJCPV75HKG9V,Prakash Pillai Mehta,1,0,1\n'
                    '  CJWT99KXPLPI,perf-070,UWGCP00XPDCQ,Ellie Wendy Brown,1,1,0\n'
                    '  C5H1G0LC1A6C,mobile-090,UPLCK9I5ENM9,Martha Yvonne Nguyen,1,0,1\n'
                    '  CN20Z0W91YE0,data-v2-062,UYIAYBC7FYCG,Levi Francis Nguyen,2,1,1\n'
                    'Row order, quoting, whitespace and letter case are all free. FAIL if any of the '
                    'four rooms is missing, if any author id, name, stranded_reply_count, '
                    'self_reply_count, or external_reply_count value does not match the real value above.'
                )
                verifier['metadata']['how_justification'] = (
                    'A native rubric ASSERTION over the CSV raw text. It grades the CELL VALUES for '
                    'all 7 columns per row -- channel_id, channel_name, retracted_message_author_id, '
                    'retracted_message_author_name, stranded_reply_count, self_reply_count, '
                    'external_reply_count. Row order, quoting, whitespace and letter case are free; '
                    'the twenty-eight pinned values (4 rows x 7 fields) are not.'
                )

# 7. Update instruction_sha256
with open(temp_instr, 'rb') as f:
    instr_hash = hashlib.sha256(f.read()).hexdigest()
m['instruction_sha256'] = instr_hash

with open(manifest_path, 'w', encoding='utf-8') as f:
    json.dump(m, f, indent=2, ensure_ascii=False)
    f.write('\n')

# 8. Update artifact_plan.json
plan_path = os.path.join(orig_dir, 'solution', 'artifact_plan.json')
with open(plan_path, 'r', encoding='utf-8') as f:
    plan = json.load(f)
plan['json']['total_external_stranded_replies'] = 3
plan['json']['worst_room_external_reply_count'] = 1
plan['json']['rooms_with_self_reply_only'] = ["CJWT99KXPLPI"]
plan['json']['rooms_with_both_reply_types'] = ["CN20Z0W91YE0"]
# Add self_reply_count and external_reply_count to CSV rows
plan['csv'][0] = ["channel_id", "channel_name", "retracted_message_author_id", "retracted_message_author_name", "stranded_reply_count", "self_reply_count", "external_reply_count"]
plan['csv'][1] = ["C62RIISXI1FD", "general-marketing-analytics", "UJCPV75HKG9V", "Prakash Pillai Mehta", 1, 0, 1]
plan['csv'][2] = ["CJWT99KXPLPI", "perf-070", "UWGCP00XPDCQ", "Ellie Wendy Brown", 1, 1, 0]
plan['csv'][3] = ["C5H1G0LC1A6C", "mobile-090", "UPLCK9I5ENM9", "Martha Yvonne Nguyen", 1, 0, 1]
plan['csv'][4] = ["CN20Z0W91YE0", "data-v2-062", "UYIAYBC7FYCG", "Levi Francis Nguyen", 2, 1, 1]
with open(plan_path, 'w', encoding='utf-8') as f:
    json.dump(plan, f, indent=2)
    f.write('\n')

# 9. Sync to environment/_app
shutil.copy2(temp_instr, os.path.join(orig_dir, 'environment', '_app', 'instruction.md'))
shutil.copy2(manifest_path, os.path.join(orig_dir, 'environment', '_app', 'tests', 'manifest.json'))

# 10. Fix CRLF
for root, dirs, files in os.walk(orig_dir):
    dirs[:] = [d for d in dirs if d not in {'__pycache__', '.git', '.pytest_cache'}]
    for f in files:
        ext = os.path.splitext(f)[1]
        if ext in {'.py', '.sh', '.toml', '.json', '.md', '.csv', '.txt', '.jsonl'}:
            fpath = os.path.join(root, f)
            content = open(fpath, 'r', encoding='utf-8').read()
            if '\r\n' in content:
                with open(fpath, 'w', encoding='utf-8', newline='\n') as fh:
                    fh.write(content.replace('\r\n', '\n'))

# 11. Zip
exclude_dirs = {'__pycache__', '.git', '.pytest_cache'}
exclude_exts = {'.pyc', '.swp', '.swo', '.orig', '.rej'}
with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(orig_dir):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for f in files:
            ext = os.path.splitext(f)[1]
            if ext in exclude_exts:
                continue
            full = os.path.join(root, f)
            rel = os.path.relpath(full, orig_dir)
            arc = 'the-thread-that-outlived-its-own-start/' + rel.replace(os.sep, '/')
            zf.writestr(arc, open(full, 'rb').read())

print('Task 2 best version: %d bytes, %d verifiers, sha256=%s' % (os.path.getsize(output_zip), len(m['verifier_configs']), instr_hash))
print('Fields added: total_external_stranded_replies, worst_room_external_reply_count, rooms_with_self_reply_only, rooms_with_both_reply_types')
print('CSV columns: 7 (added self_reply_count, external_reply_count)')
print('CSV rubric: Fixed to grade all 7 columns')
