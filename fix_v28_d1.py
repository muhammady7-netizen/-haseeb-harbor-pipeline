"""Fix v28: Migrate memo regex checks to Python assertions + declare standalone tests."""
import json, csv, os
from pathlib import Path

DST = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\task-sources\bus-b50-v28")

# 1. Migrate memo_conversion_effect and memo_counted_placements from verifier.json to test_outputs.py
verifier_path = DST / "tests/verifier.json"
spec = json.loads(verifier_path.read_text(encoding="utf-8"))

# Remove memo_conversion_effect, memo_conversion_effect_exactly_one,
# memo_counted_placements, memo_counted_placements_exactly_one from verifier.json
# (migrate to Python assertions)
names_to_remove = {
    "memo_conversion_effect",
    "memo_conversion_effect_exactly_one",
    "memo_counted_placements",
    "memo_counted_placements_exactly_one",
}
spec["verifiers"] = [v for v in spec["verifiers"] if v["name"] not in names_to_remove]
verifier_path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
print(f"1. Removed {len(names_to_remove)} memo regex checks from verifier.json ({len(spec['verifiers'])} remaining)")

# 2. Add Python assertions for the migrated checks
test_path = DST / "tests/test_outputs.py"
test_code = test_path.read_text(encoding="utf-8")

# Read gold values
results = json.loads((DST / "solution/files/results.json").read_text(encoding="utf-8"))
ce_value = results["conversion_effect_streams"]
cp_value = results["counted_placement_count"]

new_tests = f'''

def test_memo_conversion_effect():
    """The memo must name the conversion effect figure correctly."""
    import re
    memo_path = WORKSPACE / "campaign_review.md"
    if not memo_path.is_file():
        pytest.skip("no campaign_review.md")
    text = memo_path.read_text(encoding="utf-8")
    # Must contain the conversion effect figure
    ce_str = str({ce_value})
    ce_comma = f"{{{ce_value}:,}}"
    patterns = [
        rf"(?<![-\\d.])(?:{ce_str}|{ce_comma})(?!\\d)(?!\\.\\d)",
    ]
    found = any(re.search(p, text) for p in patterns)
    assert found, (
        f"memo must contain the conversion effect figure ({ce_value}) "
        "somewhere in the text"
    )
    # Must NOT hedge (offer the figure as one of several candidates)
    # Check: the figure is not near "or", "alternatively", "possibly", etc.
    hedge_pattern = (
        rf"(?is)(?:(?<![-\\d.])(?:{ce_str}|{ce_comma})(?!\\d)(?!\\.\\d)"
        r"[^\\w;.|/]*(?:\\b(?:or|alternatively|possibly|either|maybe|perhaps"
        r"|not\\s+\\w+\\s+but|rather\\s+than|instead\\s+of|but\\s+not|except)\\b|\\s/\\s)"
        r"[^\\w;.|/]*(?:(?<![\\d.])\\d[\\d,]*(?:\\.\\d+)?(?!\\d)(?!\\.\\d)"
        r"|\\b(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve"
        r"|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty)\\b)"
        r"(?!\\s*(?:raw|total|vs|versus)\\b))"
    )
    assert not re.search(hedge_pattern, text), (
        "conversion effect figure must not be offered as one of several candidates"
    )


def test_memo_counted_placements():
    """The memo must name the counted placements figure correctly."""
    import re
    memo_path = WORKSPACE / "campaign_review.md"
    if not memo_path.is_file():
        pytest.skip("no campaign_review.md")
    text = memo_path.read_text(encoding="utf-8")
    cp_str = str({cp_value})
    cp_comma = f"{{{cp_value}:,}}"
    patterns = [
        rf"(?<![-\\d.])(?:{cp_str}|{cp_comma})(?!\\d)(?!\\.\\d)",
    ]
    found = any(re.search(p, text) for p in patterns)
    assert found, (
        f"memo must contain the counted placements figure ({cp_value}) "
        "somewhere in the text"
    )
    # Must NOT hedge
    hedge_pattern = (
        rf"(?is)(?:(?<![-\\d.])(?:{cp_str}|{cp_comma})(?!\\d)(?!\\.\\d)"
        r"[^\\w;.|/]*(?:\\b(?:or|alternatively|possibly|either|maybe|perhaps"
        r"|not\\s+\\w+\\s+but|rather\\s+than|instead\\s+of|but\\s+not|except)\\b|\\s/\\s)"
        r"[^\\w;.|/]*(?:(?<![\\d.])\\d[\\d,]*(?:\\.\\d+)?(?!\\d)(?!\\.\\d)"
        r"|\\b(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve"
        r"|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty)\\b)"
        r"(?!\\s*(?:raw|total|vs|versus)\\b))"
    )
    assert not re.search(hedge_pattern, text), (
        "counted placements figure must not be offered as one of several candidates"
    )
'''

test_code = test_code.rstrip() + new_tests
test_path.write_text(test_code, encoding="utf-8")
print("2. Added test_memo_conversion_effect + test_memo_counted_placements to test_outputs.py")

# 3. Convert ALL to LF
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
print(f"3. Converted {fixed} files to LF")

# 4. Rebuild zip
import zipfile, shutil
out = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\canonical-zips\UPLOAD-THIS-TO-QC-bus-b50-v28.zip")
ROOT_NAME = "bus-b50-b10-streaming-target-variance-attribution"
EXCLUDE_DIRS = {".git", "__pycache__", ".pytest_cache", "__MACOSX"}
EXCLUDE_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}
EXCLUDE_SUFFIX = (".pyc", ".pyo", ".swp", ".swo", ".orig", ".rej", ":Zone.Identifier")
n = 0
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for p in sorted(DST.rglob("*")):
        if p.is_dir() or p.is_symlink(): continue
        rel = p.relative_to(DST)
        if any(part in EXCLUDE_DIRS for part in rel.parts): continue
        if p.name in EXCLUDE_NAMES or p.name.startswith("._"): continue
        if any(p.name.endswith(s) for s in EXCLUDE_SUFFIX): continue
        z.write(p, os.path.join(ROOT_NAME, rel.as_posix()))
        n += 1
print(f"4. Built {out.name}: {n} files, {out.stat().st_size} bytes")

workspace_copy = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\UPLOAD-THIS-TO-QC-bus-b50-v28.zip")
shutil.copy2(out, workspace_copy)
print("5. Copied to workspace")
print(f"\nDone! v28 fixed: D1 migrated (4 memo regex -> Python assertions), {len(spec['verifiers'])} verifiers remaining")
