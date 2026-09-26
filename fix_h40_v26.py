"""Fix health-h40 pipeline rejection findings.

Fixes:
1. instruction.md: Add explicit rule that unapproved acknowledgement doesn't stop the window
2. test_outputs.py: Rewrite test_memo_addresses_key_content with paragraph-level checks
3. verifier.json: Remove 4 redundant pytest_* checks
4. golden_results.json: Fix stale counts
"""
import json, csv, os, re
from pathlib import Path

ROOT = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\-haseeb-harbor-pipeline\task-sources\health-h40-critical-result-acknowledgement")

# === 1. Fix instruction.md: Add unapproved ack window rule ===
instr_path = ROOT / "instruction.md"
instr = instr_path.read_text(encoding="utf-8")

# Find the line about "record both acknowledger_unapproved and acknowledgement_late"
if "does not stop the acknowledgement window" not in instr:
    instr = instr.replace(
        "Where an unapproved role means there is no recognised acknowledgement and the acknowledgement window has been missed, record both `acknowledger_unapproved` and `acknowledgement_late`",
        "Where an unapproved role means there is no recognised acknowledgement and the acknowledgement window has been missed, record both `acknowledger_unapproved` and `acknowledgement_late`. An acknowledgement by an unapproved role does not stop the acknowledgement window running — it is as if no acknowledgement was made, however prompt the entry — so where no approved-role acknowledgement arrives before the window closes, the window is missed and `acknowledgement_late` is recorded alongside `acknowledger_unapproved` (this applies even when the unapproved entry was itself within the window)"
    )
    print("1. Fixed instruction.md: added unapproved ack window rule")

instr_path.write_text(instr, encoding="utf-8")

# === 2. Fix test_outputs.py: Rewrite test_memo_addresses_key_content ===
test_path = ROOT / "tests/test_outputs.py"
test_code = test_path.read_text(encoding="utf-8")

# Find and replace test_memo_addresses_key_content
old_test_start = test_code.find("def test_memo_addresses_key_content")
if old_test_start == -1:
    print("ERROR: test_memo_addresses_key_content not found")
else:
    # Find the end of the function (next def or end of file)
    next_def = test_code.find("\ndef ", old_test_start + 1)
    if next_def == -1:
        next_def = test_code.find("\nclass ", old_test_start + 1)
    if next_def == -1:
        next_def = len(test_code)
    
    old_test = test_code[old_test_start:next_def]
    
    new_test = '''def test_memo_addresses_key_content():
    """The memo must name each result by ID and explain the finding (per-result, not document-wide)."""
    import re
    memo_path = WORKSPACE / "results_memo.md"
    if not memo_path.is_file():
        pytest.skip("no results_memo.md")
    text = memo_path.read_text(encoding="utf-8")
    
    # Split into paragraphs
    paragraphs = text.split("\\n\\n")
    
    # For each result ID mentioned, check its paragraph has the right context
    # Late notifications must mention notification window
    # Late/absent acks must mention acknowledgement window  
    # Unapproved acknowledgers must name the role
    # Missing escalations must note absence
    
    required_ids = {
        "R-02": "notification",  # late notification
        "R-09": "notification",
        "R-06": "unapproved",   # unapproved acknowledger
        "R-22": "unapproved",
        "R-35": "unapproved",
    }
    
    for rid, expected_context in required_ids.items():
        found = False
        for para in paragraphs:
            if rid in para:
                if expected_context == "notification":
                    assert any(w in para.lower() for w in ["notification", "window", "30", "240"]), (
                        f"Paragraph mentioning {rid} must mention notification window"
                    )
                elif expected_context == "unapproved":
                    assert any(w in para.lower() for w in ["unapproved", "ward_clerk", "nurse_hca", "healthcare", "porter", "not approved", "role"]), (
                        f"Paragraph mentioning {rid} must name the unapproved role"
                    )
                elif expected_context == "ack_late":
                    assert any(w in para.lower() for w in ["acknowledgement", "window", "60", "480", "late"]), (
                        f"Paragraph mentioning {rid} must mention acknowledgement window"
                    )
                elif expected_context == "escalation":
                    assert any(w in para.lower() for w in ["escalation", "missing", "absence", "no escalation"]), (
                        f"Paragraph mentioning {rid} must note missing escalation"
                    )
                found = True
                break
        assert found, f"memo must name result {rid} and explain the finding"
    
    # Must mention clock (core-hours start)
    assert "clock" in text.lower(), "memo must mention the clock (core-hours start)"
    
    # Must mention escalation
    assert "escalat" in text.lower(), "memo must mention escalation"

'''
    
    test_code = test_code[:old_test_start] + new_test + test_code[next_def:]
    print("2. Fixed test_memo_addresses_key_content: paragraph-level checks")

test_path.write_text(test_code, encoding="utf-8")

# === 3. Fix verifier.json: Remove 4 redundant pytest_* checks ===
verifier_path = ROOT / "tests/verifier.json"
spec = json.loads(verifier_path.read_text(encoding="utf-8"))

names_to_remove = {"pytest_audit_covers_full_register", "pytest_results_recomputed", "pytest_memo_content_check", "pytest_per_row_correctness"}
original_count = len(spec["verifiers"])
spec["verifiers"] = [v for v in spec["verifiers"] if v["name"] not in names_to_remove]
new_count = len(spec["verifiers"])
verifier_path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
print(f"3. Removed {original_count - new_count} redundant pytest_* checks from verifier.json ({new_count} remaining)")

# === 4. Fix golden_results.json ===
golden_results_path = ROOT / "solution/golden_results.json"
if golden_results_path.exists():
    results_path = ROOT / "solution/files/results.json"
    results = json.loads(results_path.read_text(encoding="utf-8"))
    golden_results = json.loads(golden_results_path.read_text(encoding="utf-8"))
    # Update to match results.json
    for key in results:
        if key in golden_results:
            golden_results[key] = results[key]
    golden_results_path.write_text(json.dumps(golden_results, indent=2) + "\n", encoding="utf-8")
    print(f"4. Fixed golden_results.json to match results.json")

# === 5. Convert ALL to LF ===
skip_dirs = {".git", "__pycache__", ".pytest_cache", "rl_world_verifiers"}
skip_exts = {".pyc", ".pyo", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".pdf", ".zip", ".xlsx", ".docx", ".pptx", ".so", ".dll", ".egg"}
fixed = 0
for p in ROOT.rglob("*"):
    if not p.is_file(): continue
    if any(part in skip_dirs for part in p.parts): continue
    if p.suffix.lower() in skip_exts: continue
    try:
        data = p.read_bytes()
        if b"\r\n" in data:
            p.write_bytes(data.replace(b"\r\n", b"\n"))
            fixed += 1
    except: pass
print(f"5. Converted {fixed} files to LF")

# === 6. Build zip ===
import zipfile, shutil
out = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\-haseeb-harbor-pipeline\canonical-zips\UPLOAD-THIS-TO-QC-health-h40.zip")
ROOT_NAME = "health-h40-critical-result-acknowledgement"
EXCLUDE_DIRS = {".git", "__pycache__", ".pytest_cache", "__MACOSX"}
EXCLUDE_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}
EXCLUDE_SUFFIX = (".pyc", ".pyo", ".swp", ".swo", ".orig", ".rej", ":Zone.Identifier")
n = 0
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for p in sorted(ROOT.rglob("*")):
        if p.is_dir() or p.is_symlink(): continue
        rel = p.relative_to(ROOT)
        if any(part in EXCLUDE_DIRS for part in rel.parts): continue
        if p.name in EXCLUDE_NAMES or p.name.startswith("._"): continue
        if any(p.name.endswith(s) for s in EXCLUDE_SUFFIX): continue
        z.write(p, os.path.join(ROOT_NAME, rel.as_posix()))
        n += 1
print(f"6. Built {out.name}: {n} files, {out.stat().st_size} bytes")

workspace_copy = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\UPLOAD-THIS-TO-QC-health-h40.zip")
shutil.copy2(out, workspace_copy)
print("7. Copied to workspace")

print(f"\nDone! health-h40 v26: ALL pipeline rejection findings fixed")
print(f"  1. instruction.md: unapproved ack window rule disclosed")
print(f"  2. test_memo_addresses_key_content: paragraph-level checks")
print(f"  3. verifier.json: 4 redundant pytest_* checks removed")
print(f"  4. golden_results.json: stale counts fixed")
