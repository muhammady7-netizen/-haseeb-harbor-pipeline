import re
from pathlib import Path

ROOT = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\-haseeb-harbor-pipeline\task-sources\health-h40-critical-result-acknowledgement")
test_path = ROOT / "tests" / "test_outputs.py"
test_code = test_path.read_text(encoding="utf-8")

old_test_start = test_code.find("def test_memo_addresses_key_content")
next_def = test_code.find("\ndef ", old_test_start + 1)
if next_def == -1:
    next_def = len(test_code)

new_test = (
    'def test_memo_addresses_key_content():\n'
    '    """The memo must name each result by ID and explain the finding."""\n'
    '    import re\n'
    '    memo_path = WORKSPACE / "results_memo.md"\n'
    '    if not memo_path.is_file():\n'
    '        pytest.skip("no results_memo.md")\n'
    '    text = memo_path.read_text(encoding="utf-8")\n'
    '    paragraphs = text.split("\\n\\n")\n'
    '    required_ids = {\n'
    '        "R-02": "notification",\n'
    '        "R-09": "notification",\n'
    '        "R-06": "unapproved",\n'
    '        "R-22": "unapproved",\n'
    '        "R-35": "unapproved",\n'
    '    }\n'
    '    for rid, expected_context in required_ids.items():\n'
    '        found = False\n'
    '        for para in paragraphs:\n'
    '            if rid in para:\n'
    '                if expected_context == "notification":\n'
    '                    if any(w in para.lower() for w in ["notification", "window", "30", "240", "notified", "limit"]):\n'
    '                        found = True\n'
    '                        break\n'
    '                elif expected_context == "unapproved":\n'
    '                    if any(w in para.lower() for w in ["unapproved", "ward_clerk", "nurse_hca", "healthcare", "porter", "not approved", "role", "approved list"]):\n'
    '                        found = True\n'
    '                        break\n'
    '                elif expected_context == "ack_late":\n'
    '                    if any(w in para.lower() for w in ["acknowledgement", "window", "60", "480", "late"]):\n'
    '                        found = True\n'
    '                        break\n'
    '                elif expected_context == "escalation":\n'
    '                    if any(w in para.lower() for w in ["escalation", "missing", "absence", "no escalation"]):\n'
    '                        found = True\n'
    '                        break\n'
    '        assert found, f"memo must name result {rid} and explain the finding ({expected_context})"\n'
    '    assert "clock" in text.lower(), "memo must mention the clock"\n'
    '    assert "escalat" in text.lower(), "memo must mention escalation"\n'
    '\n'
)

test_code = test_code[:old_test_start] + new_test + test_code[next_def:]
test_path.write_text(test_code, encoding="utf-8")
print("Fixed test_memo_addresses_key_content: check ALL paragraphs for each ID")

# Convert to LF and rebuild
import zipfile, os, shutil
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
print(f"Converted {fixed} files to LF")

out = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\-haseeb-harbor-pipeline\canonical-zips\UPLOAD-THIS-TO-QC-health-h40.zip")
ROOT_NAME = "health-h40-critical-result-acknowledgement"
n = 0
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for p in sorted(ROOT.rglob("*")):
        if p.is_dir() or p.is_symlink(): continue
        rel = p.relative_to(ROOT)
        if any(part in {".git", "__pycache__", ".pytest_cache", "__MACOSX"} for part in rel.parts): continue
        if p.name in {".DS_Store", "Thumbs.db", "desktop.ini"} or p.name.startswith("._"): continue
        if any(p.name.endswith(s) for s in (".pyc", ".pyo", ".swp", ".swo", ".orig", ".rej", ":Zone.Identifier")): continue
        z.write(p, os.path.join(ROOT_NAME, rel.as_posix()))
        n += 1
print(f"Built {out.name}: {n} files, {out.stat().st_size} bytes")

workspace_copy = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\UPLOAD-THIS-TO-QC-health-h40.zip")
shutil.copy2(out, workspace_copy)
print("Copied to workspace")
