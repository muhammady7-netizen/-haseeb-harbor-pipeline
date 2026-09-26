"""Fix gen-g806 pipeline rejection findings.

Fixes:
1. sc23/sc46 gold: "none" -> "NEGATION_PIVOT_USED" + cascade (results, memo, verifier counts)
2. test_memo_numbers_match_results: add disclosure to instruction.md
3. sc2496-sc2545 regex: add \x22? and \r? to match sc1-sc2495 format
4. Keep (?mi) flag (case-insensitive is needed for cross-referencing, errata says match case-insensitively for lookups)
5. Fix stale golden_results.json counts
6. Fix golden_trajectory.json stale counts
"""
import json, csv, os, re
from pathlib import Path

ROOT = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\-haseeb-harbor-pipeline\gen-g806-leadership-brief-rhetorical-style-audit")

# === 1. Fix sc23/sc46 gold in script_style_audit.csv ===
csv_path = ROOT / "solution/files/script_style_audit.csv"
with open(csv_path, "r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    fields = reader.fieldnames
    rows = list(reader)

changed = 0
for row in rows:
    if row["script_id"] in ("SC-23", "SC-46") and row["finding"] == "none":
        row["finding"] = "NEGATION_PIVOT_USED"
        changed += 1
        print(f"  Fixed {row['script_id']}: none -> NEGATION_PIVOT_USED")

with open(csv_path, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
print(f"1. Fixed {changed} gold values in script_style_audit.csv")

# Recompute counts
counts = {}
for row in rows:
    f = row["finding"]
    counts[f] = counts.get(f, 0) + 1

negation_pivot_count = counts.get("NEGATION_PIVOT_USED", 0)
none_count = counts.get("none", 0)
flagged_count = sum(v for k, v in counts.items() if k != "none")
script_count = len(rows)
uncited_count = counts.get("UNCITED_SCRIPTURE_REF", 0)
runtime_count = counts.get("RUNTIME_OUT_OF_BAND", 0)

print(f"  New counts: script={script_count}, flagged={flagged_count}, negation_pivot={negation_pivot_count}, none={none_count}, uncited={uncited_count}, runtime={runtime_count}")

# === 2. Update results.json ===
results_path = ROOT / "solution/files/results.json"
results = json.loads(results_path.read_text(encoding="utf-8"))
results["script_count"] = script_count
results["flagged_count"] = flagged_count
results["negation_pivot_count"] = negation_pivot_count
results["uncited_scripture_count"] = uncited_count
results["runtime_breach_count"] = runtime_count
results_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
print(f"2. Updated results.json: {results}")

# === 3. Update golden_results.json ===
golden_results_path = ROOT / "solution/golden_results.json"
if golden_results_path.exists():
    golden_results = json.loads(golden_results_path.read_text(encoding="utf-8"))
    golden_results["script_count"] = script_count
    golden_results["flagged_count"] = flagged_count
    golden_results["negation_pivot_count"] = negation_pivot_count
    golden_results["uncited_scripture_count"] = uncited_count
    golden_results["runtime_breach_count"] = runtime_count
    golden_results_path.write_text(json.dumps(golden_results, indent=2) + "\n", encoding="utf-8")
    print(f"3. Updated golden_results.json")

# === 4. Update instruction.md with corrected counts + memo numbers requirement ===
instr_path = ROOT / "instruction.md"
instr = instr_path.read_text(encoding="utf-8")

# Fix counts
instr = instr.replace("script_count=2073", f"script_count={script_count}")
instr = instr.replace("flagged_count=1566", f"flagged_count={flagged_count}")
instr = instr.replace("uncited_scripture_count=210", f"uncited_scripture_count={uncited_count}")
instr = instr.replace("runtime_breach_count=316", f"runtime_breach_count={runtime_count}")

# Add memo numbers requirement
if "must mention the numeric counts" not in instr:
    instr = instr.replace(
        "the memo must name each finding category",
        "the memo must mention the numeric counts (script_count, flagged_count, uncited_scripture_count, runtime_breach_count) and name each finding category"
    )
    print("4. Added memo numbers requirement to instruction.md")

instr_path.write_text(instr, encoding="utf-8")
print(f"4. Updated instruction.md counts + memo requirement")

# === 5. Update style_audit_memo.md ===
memo_path = ROOT / "solution/files/style_audit_memo.md"
memo = memo_path.read_text(encoding="utf-8")

# Fix any count references
memo = memo.replace("2073", str(script_count))
memo = memo.replace("1566", str(flagged_count))
memo = memo.replace("565", str(negation_pivot_count))

# Make sure the required numbers appear
for key, val in [("script_count", script_count), ("flagged_count", flagged_count),
                ("uncited_scripture_count", uncited_count), ("runtime_breach_count", runtime_count)]:
    if str(val) not in memo:
        # Add to the memo
        memo += f"\n\n{key}: {val}"
        print(f"  Added {key}={val} to memo")

memo_path.write_text(memo, encoding="utf-8")
print(f"5. Updated style_audit_memo.md")

# === 6. Update verifier.json ===
verifier_path = ROOT / "tests/verifier.json"
spec_text = verifier_path.read_text(encoding="utf-8")

# Fix sc23 and sc46 expected values
spec_text = spec_text.replace(
    r'(?mi)^\\x22?SC\\-23\\x22?\\s*,\\s*\\x22?none\\x22?\\s*(?:,|\\r?$)',
    r'(?mi)^\\x22?SC\\-23\\x22?\\s*,\\s*\\x22?NEGATION_PIVOT_USED\\x22?\\s*(?:,|\\r?$)'
)
spec_text = spec_text.replace(
    r'(?mi)^\\x22?SC\\-46\\x22?\\s*,\\s*\\x22?none\\x22?\\s*(?:,|\\r?$)',
    r'(?mi)^\\x22?SC\\-46\\x22?\\s*,\\s*\\x22?NEGATION_PIVOT_USED\\x22?\\s*(?:,|\\r?$)'
)

# Fix result count checks
spec_text = spec_text.replace('"value": 565', f'"value": {negation_pivot_count}')
spec_text = spec_text.replace('"value": 1566', f'"value": {flagged_count}')

# Fix sc2496-sc2545: add \x22? and \r? to match sc1-sc2495 format
# Pattern: (?mi)^SC\\-NNNN\\s*,\\s*FINDING\\s*(?:,|$)
# Should be: (?mi)^\\x22?SC\\-NNNN\\x22?\\s*,\\s*\\x22?FINDING\\x22?\\s*(?:,|\\r?$)
# This is tricky because there are 50 checks to fix
# Use regex to find and fix them
def fix_stripped_regex(match):
    full = match.group(0)
    # Extract the SC number and finding
    inner = match.group(1)
    # Replace the pattern
    fixed = full.replace(
        r'(?mi)^SC\\-',
        r'(?mi)^\\x22?SC\\-'
    ).replace(
        r'\s*,\s*',
        r'\\x22?\\s*,\\s*\\x22?'
    ).replace(
        r'\s*(?:,|$)',
        r'\\x22?\\s*(?:,|\\r?$)'
    )
    return fixed

# Actually, let me use a simpler approach - just do string replacements
# The stripped pattern is: (?mi)^SC\\-NNNN\\s*,\\s*FINDING\\s*(?:,|$)
# The fixed pattern is: (?mi)^\\x22?SC\\-NNNN\\x22?\\s*,\\s*\\x22?FINDING\\x22?\\s*(?:,|\\r?$)

# Find all occurrences of the stripped pattern and fix them
# Pattern: (?mi)^SC\\-(\d+)\\s*,\\s*(\w+)\\s*(?:,|$)
stripped_pattern = re.compile(r'\(\?mi\)\^SC\\\\-(\d+)\\\\s\*,\\\\s\*(\w+)\\\\s\*\(?:,\|\$\)')
matches = stripped_pattern.findall(spec_text)
print(f"  Found {len(matches)} stripped regex patterns to fix")

for sc_num, finding in matches:
    old = f'(?mi)^SC\\\\-{sc_num}\\\\s*,\\\\s*{finding}\\\\s*(?:,|$)'
    new = f'(?mi)^\\\\x22?SC\\\\-{sc_num}\\\\x22?\\\\s*,\\\\s*\\\\x22?{finding}\\\\x22?\\\\s*(?:,|\\\\r?$)'
    spec_text = spec_text.replace(old, new)

verifier_path.write_text(spec_text, encoding="utf-8")
print(f"6. Updated verifier.json (sc23/sc46 gold + result counts + {len(matches)} stripped regex patterns)")

# === 7. Update golden_trajectory.json ===
traj_path = ROOT / "solution/golden_trajectory.json"
if traj_path.exists():
    traj = json.loads(traj_path.read_text(encoding="utf-8"))
    traj_text = json.dumps(traj)
    # Fix counts in trajectory
    traj_text = traj_text.replace("2073", str(script_count))
    traj_text = traj_text.replace("1566", str(flagged_count))
    traj_text = traj_text.replace("565", str(negation_pivot_count))
    traj = json.loads(traj_text)
    traj_path.write_text(json.dumps(traj, indent=2) + "\n", encoding="utf-8")
    print(f"7. Updated golden_trajectory.json")

# === 8. Update review.csv ===
review_path = ROOT / "review.csv"
if review_path.exists():
    review = review_path.read_text(encoding="utf-8")
    review = review.replace("2073", str(script_count))
    review = review.replace("1566", str(flagged_count))
    review = review.replace("565", str(negation_pivot_count))
    review_path.write_text(review, encoding="utf-8")
    print(f"8. Updated review.csv")

# === 9. Convert ALL files to LF ===
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
print(f"9. Converted {fixed} files to LF")

# === 10. Build zip ===
import zipfile, shutil
out = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\-haseeb-harbor-pipeline\canonical-zips\UPLOAD-THIS-TO-QC-gen-g806-v20.zip")
ROOT_NAME = "gen-g806-leadership-brief-rhetorical-style-audit"
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
print(f"10. Built {out.name}: {n} files, {out.stat().st_size} bytes")

workspace_copy = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\UPLOAD-THIS-TO-QC-gen-g806-v20.zip")
shutil.copy2(out, workspace_copy)
print("11. Copied to workspace")

print(f"\nDone! gen-g806 v20: ALL pipeline rejection findings fixed")
print(f"  sc23/sc46: none -> NEGATION_PIVOT_USED (with full cascade)")
print(f"  Memo numbers: disclosed in instruction.md")
print(f"  sc2496-sc2545: added quote/CRLF tolerance")
print(f"  Counts: negation_pivot={negation_pivot_count}, flagged={flagged_count}, none={none_count}")
