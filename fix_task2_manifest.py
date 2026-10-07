import json, hashlib

manifest_path = r'C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\task-sources\the-thread-that-outlived-its-own-start-v7\tests\manifest.json'

with open(manifest_path, 'r', encoding='utf-8') as f:
    manifest = json.load(f)

# 1. Update csv_header_is_the_pinned_columns_in_order
for v in manifest['verifier_configs']:
    if v['name'] == 'csv_header_is_the_pinned_columns_in_order':
        v['description'] = 'orphaned_thread_audit.csv carries exactly the seven pinned columns, in the pinned order'
        v['evidence_span'] = 'with exactly these columns in this order: channel_id, channel_name, retracted_message_author_id, retracted_message_author_name, stranded_reply_count, self_reply_count, external_reply_count'
        for verifier in v['verifier_spec']['verifiers']:
            if verifier['name'] == 'header_is_the_pinned_columns_in_order':
                verifier['assertion']['expected'] = [
                    'channel_id', 'channel_name', 'retracted_message_author_id',
                    'retracted_message_author_name', 'stranded_reply_count',
                    'self_reply_count', 'external_reply_count'
                ]
                verifier['metadata']['how_justification'] = 'Reads the CSV real header through csv.inspect_table and requires the header list to EQUAL the seven pinned names, in the pinned order, exactly as the prompt writes them.'

    if v['name'] == 'csv_rows_are_right':
        for verifier in v['verifier_spec']['verifiers']:
            if verifier['name'] == 'csv_rows_are_right':
                verifier['metadata']['how_justification'] = 'A native rubric ASSERTION over the CSV own raw text, judged by the task configured judge at temperature 0. It grades the CELL VALUES the prompt pins for each of the four rooms -- which account retracted message is the one with replies, that account real name, the room stranded-reply count, the self-reply count, and the external-reply count -- none of which a deterministic comparator on this source can address, since csv.extract_text exposes the file only as raw text. Row order, quoting, whitespace and letter case are explicitly free; the twenty-eight pinned values (4 rows x 7 fields) are not.'

# 2. Add new verifiers
new_verifiers = [
    {
        'name': 'total_external_stranded_replies',
        'description': 'Total stranded replies NOT written by the retractor of that thread.',
        'category': 'core',
        'weight': 1.0,
        'target': 'workspace_files',
        'verifier_type': 'file_check',
        'type': 'file_check',
        'pass_threshold': 1.0,
        'requirement_id': 'total_external_stranded_replies',
        'evidence_span': 'how many of the total stranded replies were written by someone OTHER than the person who retracted the original message',
        'metadata': {
            'why_justification': 'Requires classifying each stranded reply as self-reply or external. general-marketing-analytics has 1 external, perf-070 has 0 (self-reply only), mobile-090 has 1 external, data-v2-062 has 1 external. Total = 3.'
        },
        'verifier_spec': {
            'task_id': 'total_external_stranded_replies',
            'verifiers': [{
                'name': 'total_external_stranded_replies',
                'metadata': {
                    'how_justification': 'Reads metrics.json and requires total_external_stranded_replies = 3.',
                    'why_justification': 'Three stranded replies are from someone other than the retractor: one each in general-marketing-analytics, mobile-090, and data-v2-062.'
                },
                'source': {'type': 'file', 'file': {'type': 'json', 'command': 'read_file', 'arguments': {'path': 'metrics.json'}}},
                'assertion': {'type': 'deterministic', 'expected': 3, 'deterministic': {'path': '$.total_external_stranded_replies', 'comparison': 'equals'}}
            }]
        }
    },
    {
        'name': 'worst_room_external_reply_count',
        'description': 'In the worst room, how many stranded replies are from someone other than the retractor.',
        'category': 'core',
        'weight': 1.0,
        'target': 'workspace_files',
        'verifier_type': 'file_check',
        'type': 'file_check',
        'pass_threshold': 1.0,
        'requirement_id': 'worst_room_external_reply_count',
        'evidence_span': 'in the single worst room only, how many of its stranded replies were written by someone other than the retractor',
        'metadata': {
            'why_justification': 'The worst room (data-v2-062) has 2 stranded replies: 1 self-reply by Levi and 1 external reply by Mitali. The external reply count is 1.'
        },
        'verifier_spec': {
            'task_id': 'worst_room_external_reply_count',
            'verifiers': [{
                'name': 'worst_room_external_reply_count',
                'metadata': {
                    'how_justification': 'Reads metrics.json and requires worst_room_external_reply_count = 1.',
                    'why_justification': 'The worst room has exactly 1 external stranded reply (Mitali Naidu in data-v2-062).'
                },
                'source': {'type': 'file', 'file': {'type': 'json', 'command': 'read_file', 'arguments': {'path': 'metrics.json'}}},
                'assertion': {'type': 'deterministic', 'expected': 1, 'deterministic': {'path': '$.worst_room_external_reply_count', 'comparison': 'equals'}}
            }]
        }
    },
    {
        'name': 'rooms_with_self_reply_only',
        'description': 'Channel IDs of rooms where ALL stranded replies are self-replies (no external person to notify).',
        'category': 'core',
        'weight': 1.0,
        'target': 'workspace_files',
        'verifier_type': 'file_check',
        'type': 'file_check',
        'pass_threshold': 1.0,
        'requirement_id': 'rooms_with_self_reply_only',
        'evidence_span': 'the channel IDs of every room with a live orphaned thread where ALL of the stranded replies on the retracted message were written by the retractor themselves',
        'metadata': {
            'why_justification': 'perf-070 (CJWT99KXPLPI) is the only room where the sole stranded reply is from the retractor herself (Ellie Wendy Brown). A run that does not check whether the reply author matches the retractor cannot identify this room.'
        },
        'verifier_spec': {
            'task_id': 'rooms_with_self_reply_only',
            'verifiers': [{
                'name': 'rooms_with_self_reply_only',
                'metadata': {
                    'how_justification': 'Reads metrics.json and requires rooms_with_self_reply_only = ["CJWT99KXPLPI"].',
                    'why_justification': 'Only perf-070 has a self-reply-only pattern: Ellie retracted her message and her own reply is the only one.'
                },
                'source': {'type': 'file', 'file': {'type': 'json', 'command': 'read_file', 'arguments': {'path': 'metrics.json'}}},
                'assertion': {'type': 'deterministic', 'expected': ['CJWT99KXPLPI'], 'deterministic': {'path': '$.rooms_with_self_reply_only', 'comparison': 'equals'}}
            }]
        }
    },
    {
        'name': 'rooms_with_both_reply_types',
        'description': 'Channel IDs of rooms where the retracted message has BOTH a self-reply AND an external reply.',
        'category': 'core',
        'weight': 1.0,
        'target': 'workspace_files',
        'verifier_type': 'file_check',
        'type': 'file_check',
        'pass_threshold': 1.0,
        'requirement_id': 'rooms_with_both_reply_types',
        'evidence_span': 'the channel IDs of every room with a live orphaned thread where the retracted message has BOTH at least one self-reply AND at least one external reply',
        'metadata': {
            'why_justification': 'data-v2-062 (CN20Z0W91YE0) is the only room where the retractor (Levi) self-replied AND someone else (Mitali) also replied. This is the room that requires the deepest analysis to determine the notify candidate.'
        },
        'verifier_spec': {
            'task_id': 'rooms_with_both_reply_types',
            'verifiers': [{
                'name': 'rooms_with_both_reply_types',
                'metadata': {
                    'how_justification': 'Reads metrics.json and requires rooms_with_both_reply_types = ["CN20Z0W91YE0"].',
                    'why_justification': 'Only data-v2-062 has both reply types: Levi self-replied and Mitali replied externally.'
                },
                'source': {'type': 'file', 'file': {'type': 'json', 'command': 'read_file', 'arguments': {'path': 'metrics.json'}}},
                'assertion': {'type': 'deterministic', 'expected': ['CN20Z0W91YE0'], 'deterministic': {'path': '$.rooms_with_both_reply_types', 'comparison': 'equals'}}
            }]
        }
    }
]

manifest['verifier_configs'].extend(new_verifiers)

# 3. Update instruction_sha256
instr_path = r'C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\task-sources\the-thread-that-outlived-its-own-start-v7\instruction.md'
with open(instr_path, 'rb') as f:
    instr_bytes = f.read()
instr_hash = hashlib.sha256(instr_bytes).hexdigest()
manifest['instruction_sha256'] = instr_hash

# Write updated manifest
with open(manifest_path, 'w', encoding='utf-8') as f:
    json.dump(manifest, f, indent=2, ensure_ascii=False)
    f.write('\n')

print(f'Updated manifest: {len(manifest["verifier_configs"])} verifiers')
print(f'Instruction SHA256: {instr_hash}')
