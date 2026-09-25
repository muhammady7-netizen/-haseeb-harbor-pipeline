import json, os, zipfile, shutil
from pathlib import Path

DST = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\task-sources\bus-b50-v28")

# Read gold values
results = json.loads((DST / "solution/files/results.json").read_text(encoding="utf-8"))
ce_value = results["conversion_effect_streams"]
cp_value = results["counted_placement_count"]

# Check if step 1 already ran (verifier.json already has memo checks removed)
verifier_path = DST / "tests/verifier.json"
spec = json.loads(verifier_path.read_text(encoding="utf-8"))
verifier_names = [v["name"] for v in spec["verifiers"]]
print("Current verifiers:", len(spec["verifiers"]), verifier_names)

# Remove memo regex checks if still present
names_to_remove = {"memo_conversion_effect", "memo_conversion_effect_exactly_one", "memo_counted_placements", "memo_counted_placements_exactly_one"}
if any(n in verifier_names for n in names_to_remove):
    spec["verifiers"] = [v for v in spec["verifiers"] if v["name"] not in names_to_remove]
    verifier_path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    print(f"Removed {len(names_to_remove)} memo regex checks ({len(spec['verifiers'])} remaining)")
else:
    print("Memo regex checks already removed")

# Add Python assertions
test_path = DST / "tests/test_outputs.py"
test_code = test_path.read_text(encoding="utf-8")

if "test_memo_conversion_effect" not in test_code:
    # Build the test code using regular strings
    new_tests = '\n\ndef test_memo_conversion_effect():\n'
    new_tests += '    """The memo must name the conversion effect figure correctly."""\n'
    new_tests += '    import re\n'
    new_tests += '    memo_path = WORKSPACE / "campaign_review.md"\n'
    new_tests += '    if not memo_path.is_file():\n'
    new_tests += '        pytest.skip("no campaign_review.md")\n'
    new_tests += '    text = memo_path.read_text(encoding="utf-8")\n'
    new_tests += f'    ce_value = {ce_value}\n'
    new_tests += '    ce_comma = format(ce_value, ",")\n'
    new_tests += '    pattern = r"(?<![-\\d.])(" + str(ce_value) + r"|" + ce_comma + r")(?!\\d)(?!\\.\\d)"\n'
    new_tests += '    assert re.search(pattern, text), "memo must contain conversion effect figure "\n'
    new_tests += '    # Anti-hedge\n'
    new_tests += '    hedge = r"(?is)(?:(?<![-\\d.])(?:" + str(ce_value) + r"|" + ce_comma + r")(?!\\d)(?!\\.\\d)[^\\w;.|/]*(?:\\b(?:or|alternatively|possibly|either|maybe|perhaps)\\b|\\s/\\s)[^\\w;.|/]*(?:(?<![\\d.])\\d[\\d,]*(?:\\.\\d+)?(?!\\d)(?!\\.\\d))(?!\\s*(?:raw|total|vs|versus)\\b))"\n'
    new_tests += '    assert not re.search(hedge, text), "conversion effect figure must not be hedged"\n'

    new_tests += '\ndef test_memo_counted_placements():\n'
    new_tests += '    """The memo must name the counted placements figure correctly."""\n'
    new_tests += '    import re\n'
    new_tests += '    memo_path = WORKSPACE / "campaign_review.md"\n'
    new_tests += '    if not memo_path.is_file():\n'
    new_tests += '        pytest.skip("no campaign_review.md")\n'
    new_tests += '    text = memo_path.read_text(encoding="utf-8")\n'
    new_tests += f'    cp_value = {cp_value}\n'
    new_tests += '    cp_comma = format(cp_value, ",")\n'
    new_tests += '    pattern = r"(?<![-\\d.])(" + str(cp_value) + r"|" + cp_comma + r")(?!\\d)(?!\\.\\d)"\n'
    new_tests += '    assert re.search(pattern, text), "memo must contain counted placements figure "\n'
    new_tests += '    # Anti-hedge\n'
    new_tests += '    hedge = r"(?is)(?:(?<![-\\d.])(?:" + str(cp_value) + r"|" + cp_comma + r")(?!\\d)(?!\\.\\d)[^\\w;.|/]*(?:\\b(?:or|alternatively|possibly|either|maybe|perhaps)\\b|\\s/\\s)[^\\w;.|/]*(?:(?<![\\d.])\\d[\\d,]*(?:\\.\\d+)?(?!\\d)(?!\\.\\d))(?!\\s*(?:raw|total|vs|versus)\\b))"\n'
    new_tests += '    assert not re.search(hedge, text), "counted placements figure must not be hedged"\n'

    test_code = test_code.rstrip() + new_tests
    test_path.write_text(test_code, encoding="utf-8")
    print("Added test_memo_conversion_effect + test_memo_counted_placements")
else:
    print("Tests already present")

# Convert ALL to LF
skip_dirs = {".git", "__pycache__", ".pytest_cache", "rl_world_verifiers"}
skip_exts = {".pyc", ".pyo", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".pdf", ".zip", ".xlsx", ".docx", ".pptx", ".so", ".dll", ".egg"}
fixed = 0
for p in DST.rglob("*"):
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

# Rebuild zip
out = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\canonical-zips\UPLOAD-THIS-TO-QC-bus-b50-v28.zip")
ROOT_NAME = "bus-b50-b10-streaming-target-variance-attribution"
n = 0
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for p in sorted(DST.rglob("*")):
        if p.is_dir() or p.is_symlink(): continue
        rel = p.relative_to(DST)
        if any(part in {".git", "__pycache__", ".pytest_cache", "__MACOSX"} for part in rel.parts): continue
        if p.name in {".DS_Store", "Thumbs.db", "desktop.ini"} or p.name.startswith("._"): continue
        if any(p.name.endswith(s) for s in (".pyc", ".pyo", ".swp", ".swo", ".orig", ".rej", ":Zone.Identifier")): continue
        z.write(p, os.path.join(ROOT_NAME, rel.as_posix()))
        n += 1
print(f"Built {out.name}: {n} files, {out.stat().st_size} bytes")

workspace_copy = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\UPLOAD-THIS-TO-QC-bus-b50-v28.zip")
shutil.copy2(out, workspace_copy)
print("Copied to workspace")
print(f"Done! {len(spec['verifiers'])} verifiers in verifier.json, memo checks migrated to Python")
