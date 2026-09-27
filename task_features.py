#!/usr/bin/env python3
"""
Task Feature Extractor — extracts features from a task zip/folder for ML training.
Usage: python task_features.py <task_zip_or_folder>
Outputs: JSON feature vector
"""

import json
import re
import sys
import zipfile
import io
from pathlib import Path
from collections import Counter


def read_task_files(source):
    """Read task files from a zip or folder."""
    source = Path(source)
    if source.is_dir():
        files = {}
        for p in source.rglob("*"):
            if p.is_file():
                rel = p.relative_to(source)
                try:
                    files[str(rel)] = p.read_text(encoding="utf-8")
                except:
                    files[str(rel)] = p.read_bytes().decode("utf-8", "replace")
        return files
    
    if isinstance(source, (str, Path)) and str(source).endswith(".zip"):
        raw = Path(source).read_bytes()
        zf = zipfile.ZipFile(io.BytesIO(raw))
        files = {}
        for name in zf.namelist():
            if not name.endswith("/"):
                try:
                    files[name] = zf.read(name).decode("utf-8")
                except:
                    files[name] = zf.read(name).decode("utf-8", "replace")
        return files
    
    raise ValueError(f"Cannot read: {source}")


def find_file(files, suffix):
    """Find the shallowest file matching suffix."""
    matches = [n for n in files if n.replace("\\", "/").endswith(suffix)]
    matches.sort(key=lambda n: (n.count("/"), n.count("\\"), len(n)))
    return matches[0] if matches else None


def get_file(files, name):
    """Get file content by name, handling backslash paths."""
    for key in files:
        if key.replace("\\", "/") == name:
            return files[key]
    return ""


def load_verifier(files):
    """Load verifier.json or manifest.json."""
    for name in ("tests/verifier.json", "verifier.json", "tests/manifest.json"):
        for key in files:
            if key.replace("\\", "/") == name:
                try:
                    return json.loads(files[key])
                except:
                    pass
    return {}


def extract_features(source, label=None):
    """Extract features from a task."""
    files = read_task_files(source)
    spec = load_verifier(files)
    
    features = {
        "label": label,
        "file_count": len(files),
    }
    
    # === Verifier features ===
    verifiers = []
    if isinstance(spec.get("verifiers"), list):
        verifiers = spec["verifiers"]
    
    features["verifier_count"] = len(verifiers)
    
    # Check types
    check_names = [v.get("name", "") for v in verifiers]
    comparisons = [v.get("assertion", {}).get("deterministic", {}).get("comparison", "") for v in verifiers]
    comp_counts = Counter(comparisons)
    
    features["regex_match_count"] = comp_counts.get("regex_match", 0)
    features["equals_count"] = comp_counts.get("equals", 0)
    features["table_equals_count"] = comp_counts.get("table_equals", 0)
    features["object_equals_count"] = comp_counts.get("object_equals", 0)
    features["contains_count"] = comp_counts.get("contains", 0)
    features["other_comparison_count"] = sum(v for k, v in comp_counts.items() if k not in ("regex_match", "equals", "table_equals", "object_equals", "contains", ""))
    
    # Tags
    tags = [v.get("metadata", {}).get("tag", "") for v in verifiers]
    tag_counts = Counter(tags)
    features["core_count"] = tag_counts.get("core", 0)
    features["incidental_count"] = tag_counts.get("incidental", 0)
    
    # === Regex quality features ===
    regex_patterns = []
    for v in verifiers:
        det = v.get("assertion", {}).get("deterministic", {})
        if det.get("comparison") == "regex_match":
            pattern = v.get("assertion", {}).get("expected", "")
            if isinstance(pattern, str):
                regex_patterns.append(pattern)
    
    features["total_regex_count"] = len(regex_patterns)
    
    # Brittle regex patterns
    dotall_count = sum(1 for p in regex_patterns if "(?is)" in p or "(?i)" in p)
    wildcard_slack = sum(1 for p in regex_patterns if re.search(r"\.\{0,\d+\}", p))
    narrow_window = sum(1 for p in regex_patterns if re.search(r"\[.{0,(\d+)\]", p))
    case_sensitive = 0
    backslash_b = chr(92) + chr(98)
    for p in regex_patterns:
        if backslash_b in p and "(?i)" not in p and "(?is)" not in p:
            case_sensitive += 1
    
    features["regex_dotall_count"] = dotall_count
    features["regex_wildcard_slack_count"] = wildcard_slack
    features["regex_narrow_window_count"] = narrow_window
    features["regex_case_sensitive_count"] = case_sensitive
    
    # === Memo/prose check features ===
    prose_checks = 0
    for v in verifiers:
        source_info = v.get("source", {}).get("file", {})
        path = source_info.get("arguments", {}).get("path", "")
        file_type = source_info.get("type", "")
        if file_type in ("md", "markdown", "text") or (path and path.endswith((".md", ".txt"))):
            prose_checks += 1
    
    features["prose_check_count"] = prose_checks
    features["has_rubric"] = any(v.get("assertion", {}).get("type") == "rubric" for v in verifiers)
    
    # === Dockerfile features ===
    dockerfile = ""
    for name in ("environment/Dockerfile", "Dockerfile"):
        if name in files:
            dockerfile = files[name]
            break
    
    users = re.findall(r"^\s*USER\s+(\S+)", dockerfile, re.M)
    effective_user = users[-1] if users else "(none)"
    features["dockerfile_user"] = effective_user
    features["dockerfile_is_root"] = effective_user.lower() in ("root", "0", "(none)")
    features["dockerfile_has_chmod"] = "chmod" in dockerfile
    features["dockerfile_has_useradd"] = "useradd" in dockerfile
    
    # === test_outputs.py features ===
    test_py = ""
    for name in ("tests/test_outputs.py", "test_outputs.py"):
        if name in files:
            test_py = files[name]
            break
    
    features["has_test_outputs_py"] = bool(test_py)
    features["test_py_line_count"] = len(test_py.split("\n")) if test_py else 0
    
    # Hardcoded values in test_outputs.py
    hardcoded_values = re.findall(r"(?:ce_value|cp_value|expected)\s*=\s*(\d+)", test_py)
    features["test_py_hardcoded_count"] = len(hardcoded_values)
    
    # === Instruction features ===
    instruction = ""
    for name in ("instruction.md", "environment/input/instruction.md"):
        if name in files:
            instruction = files[name]
            break
    
    features["instruction_word_count"] = len(instruction.split())
    features["instruction_has_must"] = instruction.lower().count("must")
    features["instruction_has_required"] = instruction.lower().count("required")
    
    # === Data features ===
    ledger = ""
    for name in ("environment/input/streaming_ledger.csv", "streaming_ledger.csv"):
        if name in files:
            ledger = files[name]
            break
    
    if ledger:
        lines = ledger.strip().split("\n")
        features["ledger_row_count"] = max(0, len(lines) - 1)
        features["ledger_has_fractional"] = "." in ledger
        features["ledger_has_negative"] = "-" in ledger
    else:
        features["ledger_row_count"] = 0
        features["ledger_has_fractional"] = False
        features["ledger_has_negative"] = False
    
    # === Risk predictions ===
    risks = []
    if features["prose_check_count"] > 0 and not features["has_rubric"]:
        risks.append("shallow_prose_grading")
    if features["regex_wildcard_slack_count"] > 0:
        risks.append("surface_form_brittleness")
    if features["regex_case_sensitive_count"] > 0:
        risks.append("semantic_equivalence")
    if features["dockerfile_is_root"]:
        risks.append("sanctioned_interface_use")
    if features["test_py_hardcoded_count"] > 0:
        risks.append("hardcoded_value_mismatch")
    if features["core_count"] == features["verifier_count"] and features["verifier_count"] > 4:
        risks.append("all_or_nothing_aggregation")
    
    features["predicted_risks"] = risks
    features["risk_count"] = len(risks)
    
    return features


def main():
    if len(sys.argv) < 2:
        print("Usage: python task_features.py <task_zip_or_folder> [accepted|rejected]")
        sys.exit(1)
    
    source = sys.argv[1]
    label = sys.argv[2] if len(sys.argv) > 2 else None
    
    features = extract_features(source, label)
    print(json.dumps(features, indent=2))


if __name__ == "__main__":
    main()
