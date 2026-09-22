#!/usr/bin/env python3
"""Fix h34 v2: address all 7 Harbor Check blockers properly.

Strategy:
- Remove ALL standalone tests from test_outputs.py (fixes execution_completeness)
- Keep/restore per-cell checks in verifier.json (they check specific values, not keywords)
- Add tight findings content checks in verifier.json (specific block IDs, not any B\d+)
- Add blank out_of_sequence check as declared entry
- Fix test.sh with -I flag (fixes state_spoofing)
- Remove duplicate checks (fixes check_independence)
"""
import json
import re
from pathlib import Path

TASK = Path(r"C:\Users\Haseeb~1\AppData\Local\Temp\opencode\h34-work\health-h34-randomisation-balance")

# ---- 1. Fix test.sh: add -I flag ----
test_sh = TASK / "tests" / "test.sh"
test_sh_text = test_sh.read_text(encoding="utf-8")
test_sh_text = test_sh_text.replace("python3 -m pytest", "python3 -I -m pytest")
test_sh.write_text(test_sh_text, encoding="utf-8")
print("Fixed test.sh: added -I flag")

# ---- 2. Rewrite verifier.json: keep only non-shallow checks + add tight findings checks ----
vpath = TASK / "tests" / "verifier.json"

# Build the final verifier set from scratch
# Keep: file existence, column checks, factor coverage, site labels
# Restore: per-cell count checks (they check specific CSV values, not keywords)
# Add: tight findings content checks (specific block IDs, stratum levels)
# Add: blank out_of_sequence check
# Remove: keyword-only findings regexes, block status keyword-only checks, fake recompute entries

with open(vpath, "r", encoding="utf-8") as f:
    data = json.load(f)

# Start fresh: keep only the checks that are NOT shallow and NOT duplicate
keep_names = {
    # File existence (not duplicated)
    "balance_exists", "blocks_exist", "findings_exist", "results_exists",
    # Column checks (not duplicated)
    "balance_has_expected_columns", "blocks_have_expected_columns",
    # Factor coverage (not duplicated)
    "balance_covers_both_factors",
    # Site labels (not duplicated)
    "site_levels_use_canonical_S_codes",
    # Per-cell count checks (check specific CSV values — NOT keyword-presence)
    "overall_active_pct_exact",
    "site_s1_subject_count", "site_s2_subject_count", "site_s3_subject_count",
    "severity_severe_counts", "severity_mild_counts",
    # Status checks (check specific row + status keyword — not just any keyword)
    "overall_within_tolerance",
    "balanced_site_s1_within", "balanced_site_s2_not_flagged",
    "imbalanced_severe_flagged", "severity_mild_within_tolerance",
    # Sequence finding counts (check specific site + count)
    "sequence_finding_recorded_at_site_s1",
    "sequence_finding_recorded_at_site_s2",
    "sequence_finding_recorded_at_site_s3",
    # Block checks (check specific block + status)
    "block_b1_not_assessed", "block_b2_not_assessed", "block_b3_within_tolerance",
    "block_b4_not_assessed", "block_b5_not_assessed", "block_b6_within_tolerance",
    "block_b7_not_assessed", "deviating_block_b8_flagged", "block_b9_within_tolerance",
    # Results.json checks (specific values)
    "result_active_proportion_pct", "result_strata_outside_tolerance",
    "result_blocks_assessed", "result_blocks_outside_tolerance",
    "result_out_of_sequence_allocations",
}

kept = [v for v in data["verifiers"] if v["name"] in keep_names]

# Add tight findings content checks (specific block IDs, not any B\d+)
findings_checks = [
    {
        "name": "findings_name_outside_tolerance_strata",
        "metadata": {"how_justification": "Opens randomisation_findings.md and applies regex_match.", "why_justification": "Findings must name S3 and severe as outside tolerance."},
        "source": {"type": "file", "file": {"type": "md", "command": "extract_text", "arguments": {"path": "randomisation_findings.md"}}},
        "assertion": {"type": "deterministic", "expected": "(?is)(?:S3|site.*S3).{0,200}(?:outside|breach|exceed|fail).*(?:severe|severity.*severe).{0,200}(?:outside|breach|exceed|fail)|(?:severe|severity.*severe).{0,200}(?:outside|breach|exceed|fail).{0,200}(?:S3|site.*S3)", "deterministic": {"path": "$.text", "comparison": "regex_match"}}
    },
    {
        "name": "findings_name_deviating_blocks",
        "metadata": {"how_justification": "Opens randomisation_findings.md and applies regex_match.", "why_justification": "Findings must name the specific deviating blocks B21, B12, B13, B8."},
        "source": {"type": "file", "file": {"type": "md", "command": "extract_text", "arguments": {"path": "randomisation_findings.md"}}},
        "assertion": {"type": "deterministic", "expected": "(?is)B21.{0,200}(?:outside|breach|exceed|fail|deviat).*(?:B12|B13|B8).{0,200}(?:outside|breach|exceed|fail|deviat)|(?:B12|B13|B8).{0,200}(?:outside|breach|exceed|fail|deviat).*(?:B21).{0,200}(?:outside|breach|exceed|fail|deviat)", "deterministic": {"path": "$.text", "comparison": "regex_match"}}
    },
    {
        "name": "findings_name_within_tolerance_blocks",
        "metadata": {"how_justification": "Opens randomisation_findings.md and applies regex_match.", "why_justification": "Findings must name at least one within-tolerance block."},
        "source": {"type": "file", "file": {"type": "md", "command": "extract_text", "arguments": {"path": "randomisation_findings.md"}}},
        "assertion": {"type": "deterministic", "expected": "(?is)(?:B3|B14|B22|B31|B32|B34|B9).{0,200}(?:within|inside|ok|pass|compliant|no[_ ]?finding)", "deterministic": {"path": "$.text", "comparison": "regex_match"}}
    },
    {
        "name": "findings_name_not_assessed_blocks",
        "metadata": {"how_justification": "Opens randomisation_findings.md and applies regex_match.", "why_justification": "Findings must name at least one not-assessed block."},
        "source": {"type": "file", "file": {"type": "md", "command": "extract_text", "arguments": {"path": "randomisation_findings.md"}}},
        "assertion": {"type": "deterministic", "expected": "(?is)(?:B1|B2|B4|B5|B7|B10|B11|B20|B23|B24|B30|B31|B33).{0,200}(?:not[_ ]?assessed|incomplete|partial|still filling|over[_ -]?fill|excluded|n/?a)", "deterministic": {"path": "$.text", "comparison": "regex_match"}}
    },
    {
        "name": "findings_address_overall_drift",
        "metadata": {"how_justification": "Opens randomisation_findings.md and applies regex_match.", "why_justification": "Findings must address overall allocation drift."},
        "source": {"type": "file", "file": {"type": "md", "command": "extract_text", "arguments": {"path": "randomisation_findings.md"}}},
        "assertion": {"type": "deterministic", "expected": "(?i)(?:overall|drift|proportion|active.{0,20}pct|64\\.4)", "deterministic": {"path": "$.text", "comparison": "regex_match"}}
    },
    {
        "name": "findings_address_sequence",
        "metadata": {"how_justification": "Opens randomisation_findings.md and applies regex_match.", "why_justification": "Findings must address allocation sequence."},
        "source": {"type": "file", "file": {"type": "md", "command": "extract_text", "arguments": {"path": "randomisation_findings.md"}}},
        "assertion": {"type": "deterministic", "expected": "(?i)sequence|out of order|ascending", "deterministic": {"path": "$.text", "comparison": "regex_match"}}
    },
    {
        "name": "findings_address_tolerances",
        "metadata": {"how_justification": "Opens randomisation_findings.md and applies regex_match.", "why_justification": "Findings must mention tolerance."},
        "source": {"type": "file", "file": {"type": "md", "command": "extract_text", "arguments": {"path": "randomisation_findings.md"}}},
        "assertion": {"type": "deterministic", "expected": "(?i)toleran|percentage point|drift|range", "deterministic": {"path": "$.text", "comparison": "regex_match"}}
    },
    {
        "name": "findings_address_ledger_reconciliation",
        "metadata": {"how_justification": "Opens randomisation_findings.md and applies regex_match.", "why_justification": "Findings must reference the amendment ledger or reconciliation."},
        "source": {"type": "file", "file": {"type": "md", "command": "extract_text", "arguments": {"path": "randomisation_findings.md"}}},
        "assertion": {"type": "deterministic", "expected": "(?is)(amendment[\\s-]*ledger|correction[\\s-]*ledger|ledger[\\s-]*of[\\s-]*amendments|allocation[\\s_-]*amend\\w*|amend\\w*.{0,60}ledger|ledger.{0,60}amend\\w*|reconcil\\w*.{0,60}(ledger|amend)|applied.{0,60}(ledger|amend)|ledger.{0,60}(reconcil\\w*|applied))", "deterministic": {"path": "$.text", "comparison": "regex_match"}}
    },
]

# Add blank out_of_sequence check
oos_check = {
    "name": "out_of_sequence_blank_on_non_site_rows",
    "metadata": {"how_justification": "Opens stratum_balance.csv and applies regex_match.", "why_justification": "Charter requires out_of_sequence blank on overall and severity rows."},
    "source": {"type": "file", "file": {"type": "csv", "command": "extract_text", "arguments": {"path": "stratum_balance.csv"}}},
    "assertion": {"type": "deterministic", "expected": "(?mi)^\\x22?(?:overall|severity)\\x22?\\s*,[^\\n]*,,[^\\n]*(?:within_tolerance|outside_tolerance)\\s*$", "deterministic": {"path": "$.text", "comparison": "regex_match"}}
}

data["verifiers"] = kept + findings_checks + [oos_check]

with open(vpath, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"verifier.json: {len(data['verifiers'])} checks (kept {len(kept)} + {len(findings_checks)} findings + 1 oos)")

# ---- 3. Remove ALL standalone tests from test_outputs.py ----
tpath = TASK / "tests" / "test_outputs.py"
text = tpath.read_text(encoding="utf-8")

# Keep only the parametrized test_deliverable and the helper functions
# Remove all standalone test_ functions
lines = text.split("\n")
keep_lines = []
in_standalone = False
for line in lines:
    # Detect standalone test function (not parametrized)
    if re.match(r'^def test_', line) and "test_deliverable" not in line:
        in_standalone = True
        continue
    if in_standalone:
        # Skip until next def or class at top level
        if re.match(r'^(def |class |@|import |from )', line) and not re.match(r'^def test_', line):
            in_standalone = False
            keep_lines.append(line)
        elif re.match(r'^def test_deliverable', line):
            in_standalone = False
            keep_lines.append(line)
        # else: skip the line (part of standalone test)
    else:
        keep_lines.append(line)

# Write the cleaned file
tpath.write_text("\n".join(keep_lines), encoding="utf-8")
print("test_outputs.py: removed standalone tests (kept only parametrized test_deliverable + helpers)")

# Count remaining test functions
remaining_tests = len(re.findall(r'^def test_', "\n".join(keep_lines), re.MULTILINE))
print(f"test_outputs.py: {remaining_tests} test functions remaining (should be 1: test_deliverable)")

print(f"\nTotal checks: {len(data['verifiers'])} declared = {remaining_tests} parametrized = {len(data['verifiers'])} actual")
print("Done. Rebuild zip and re-upload.")
