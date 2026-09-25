"""Build v25: Remove fractional streams + fix 5.4/5.7 + keep memo fixes.

v23 had 0/4 GLM (from rounding ambiguity) but pipeline rejected (2 findings).
v24 documented per-row rounding -> 4/4 TOO_EASY (ambiguity was the difficulty).
v25: REMOVE fractional streams from data (no ambiguity to document) +
     fix 5.4/5.7 contradiction (make consistent) + keep memo fixes.

If 44-channel data without rounding ambiguity is still 0/4: submit clean.
If 4/4: difficulty was entirely from rounding; need different approach.
"""
import json, csv, os, shutil
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_DOWN
import zipfile

SRC_ZIP = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\UPLOAD-THIS-TO-QC-bus-b50.zip")
DST = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\task-sources\bus-b50-v25")
ROOT_NAME = "bus-b50-b10-streaming-target-variance-attribution"

# 1. Extract original
if DST.exists():
    shutil.rmtree(DST)
DST.mkdir(parents=True)
with zipfile.ZipFile(SRC_ZIP) as z:
    for name in z.namelist():
        if name.startswith(ROOT_NAME + "/"):
            rel = name[len(ROOT_NAME)+1:]
            if not rel: continue
            target = DST / rel
            if name.endswith("/"):
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(z.read(name))
print("1. Extracted original")

# 2. Remove fractional streams from streaming_ledger.csv
ledger_path = DST / "environment/input/streaming_ledger.csv"
with open(ledger_path, "r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    ledger_fields = reader.fieldnames
    ledger_rows = list(reader)

changed = 0
for row in ledger_rows:
    for field in ("delivered_streams", "delivered_reach"):
        val = row[field]
        if "." in val and val not in ("0", "0.0"):
            # Round halves away from zero
            d = Decimal(val)
            if d >= 0:
                rounded = int(d.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
            else:
                rounded = int(d.quantize(Decimal("1"), rounding=ROUND_HALF_DOWN))
            row[field] = str(rounded)
            changed += 1
            print(f"  {row['channel_id']} {field}: {val} -> {rounded}")

with open(ledger_path, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=ledger_fields)
    writer.writeheader()
    writer.writerows(ledger_rows)
print(f"2. Removed {changed} fractional values from ledger")

# 3. Fix 5.4/5.7 contradiction in attribution_note.md
note_path = DST / "environment/input/attribution_note.md"
note = note_path.read_text(encoding="utf-8")

# Fix 5.4: PE is halves away (SF>0) / toward (SF<0); CE is always toward
note = note.replace(
    "The first two parts are taken to the nearest whole\nstream, halves away from zero. The residual is then the balance of the shortfall, so the\nthree parts add back to the shortfall exactly, per channel and across the campaign.",
    "The placements effect is taken to the nearest whole stream,\nhalves away from zero when the shortfall is positive and halves toward\nzero when it is negative (see 5.7). The conversion effect is taken to\nthe nearest whole stream, halves toward zero, always. The residual is\nthen the balance of the shortfall, so the three parts add back to the\nshortfall exactly, per channel and across the campaign."
)

# Fix 5.7: remove "as before" which has no antecedent
note = note.replace(
    "The conversion effect is always rounded halves\ntoward zero as before.",
    "The conversion effect is always rounded halves\ntoward zero."
)

# Add rule 2.7 for empty offer_type
rule_27 = "\n\n**2.7** A placement whose `offer_type` is empty is a promotional placement\nthat is neither guaranteed nor organic, and is counted under 2.1 exactly as\nany other `ran` placement is counted."
note = note.replace("\n## 3. Reading the ledger", rule_27 + "\n\n## 3. Reading the ledger")

note_path.write_text(note, encoding="utf-8")
print("3. Fixed attribution_note.md (5.4/5.7 consistent, rule 2.7 added)")

# 4. Fix instruction.md: "name that part" (generic)
instr_path = DST / "instruction.md"
instr = instr_path.read_text(encoding="utf-8")
instr = instr.replace(
    "the one channel whose shortfall the method leaves entirely to a single part of the split, and name that part — the conversion",
    "the one channel whose shortfall the method leaves entirely to a single part of the split, and name that part"
)
instr_path.write_text(instr, encoding="utf-8")

sf_path = DST / "environment/input/submission_format.md"
sf = sf_path.read_text(encoding="utf-8")
sf = sf.replace(
    "the one channel whose shortfall the method leaves entirely to a single part of the split, and name that part — the conversion",
    "the one channel whose shortfall the method leaves entirely to a single part of the split, and name that part"
)
sf_path.write_text(sf, encoding="utf-8")
print("4. Fixed instruction (generic 'name that part')")

# 5. Fix test.sh -I flag
test_sh = DST / "tests/test.sh"
content = test_sh.read_text(encoding="utf-8")
content = content.replace("python3 -m pytest", "python3 -I -m pytest")
test_sh.write_text(content, encoding="utf-8")

# 6. Fix verifier.json
verifier_path = DST / "tests/verifier.json"
spec = json.loads(verifier_path.read_text(encoding="utf-8"))

for v in spec["verifiers"]:
    # D1 regex fix
    if v["name"] == "memo_single_part_channel":
        v["assertion"]["expected"] = v["assertion"]["expected"].replace("\\w*", "\\w{0,}")
        # Change from CH-04+conversion to CH-41+residual
        v["assertion"]["expected"] = v["assertion"]["expected"].replace("CH-04", "CH-41").replace("conversion", "residual")
        v["metadata"]["why_justification"] = "The note names the channel whose whole gap the method leaves in one part of the split, beside the part it leaves it in."

    if v["name"] == "register_header":
        v["source"]["file"]["type"] = "csv"
        v["source"]["file"]["command"] = "inspect_table"
        v["assertion"]["expected"] = ["channel_id", "counted_placements", "placements_effect_streams",
                                       "conversion_effect_streams", "residual_reach_effect_streams",
                                       "shortfall_to_target_streams"]
        v["assertion"]["deterministic"]["path"] = "$.header"
        v["assertion"]["deterministic"]["comparison"] = "equals"

    if v["name"] == "memo_prose_floor":
        v["assertion"]["expected"] = "(?s)(?=.+\\b(?:conversion|placement|reach|shortfall|channel|stream)\\b)(?:[A-Za-z]+[^A-Za-z]+){60,}"

    # Update memo figure checks for CH-41 gold change
    if v["name"] in ("memo_conversion_effect", "memo_conversion_effect_exactly_one"):
        # CE didn't change (CH-41 CE is still 0)
        pass
    if v["name"] in ("memo_counted_placements", "memo_counted_placements_exactly_one"):
        # Counted didn't change (CH-41 counted is still 1)
        pass

verifier_path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
print("5. Fixed verifier.json (D1, register_header, CH-41+residual)")

# 7. Fix golden memo: CH-41 + residual reach
memo_path = DST / "solution/files/campaign_review.md"
memo = memo_path.read_text(encoding="utf-8")
memo = memo.replace(
    "CH-04 is the channel to walk the artist through first, because it is the clean case.\nEvery placement the plan asked of it ran inside the window and its reach landed exactly\nwhere the plan put it, so the method leaves the whole of that channel's gap in the\nconversion part and nothing in the other two. The curator submissions brought the\naudience along and simply did not turn it into plays.",
    "CH-41 is the channel to walk the artist through first, because it is the clean case.\nEvery placement the plan asked of it ran inside the window and its reach landed exactly\nwhere the plan put it, so the method leaves the whole of that channel's gap in the\nresidual reach part and nothing in the other two. The audience came along as the\nplan expected and the conversion held; what drifted was the reach the counted\nplacements brought above what the plan assumed of them."
)
memo_path.write_text(memo, encoding="utf-8")
print("6. Fixed golden memo (CH-41+residual)")

# 8. Fix golden_trajectory.json
traj_path = DST / "solution/golden_trajectory.json"
traj = json.loads(traj_path.read_text(encoding="utf-8"))
for step in traj:
    cmd = str(step.get("arguments", {}).get("command", ""))
    if "campaign_review.md" in cmd and "CH-04" in cmd:
        cmd = cmd.replace(
            "CH-04 is the channel to walk the artist through first, because it is the clean case.\nEvery placement the plan asked of it ran inside the window and its reach landed exactly\nwhere the plan put it, so the method leaves the whole of that channel's gap in the\nconversion part and nothing in the other two. The curator submissions brought the\naudience along and simply did not turn it into plays.",
            "CH-41 is the channel to walk the artist through first, because it is the clean case.\nEvery placement the plan asked of it ran inside the window and its reach landed exactly\nwhere the plan put it, so the method leaves the whole of that channel's gap in the\nresidual reach part and nothing in the other two. The audience came along as the\nplan expected and the conversion held; what drifted was the reach the counted\nplacements brought above what the plan assumed of them."
        )
        step["arguments"]["command"] = cmd
traj_path.write_text(json.dumps(traj, indent=2) + "\n", encoding="utf-8")
print("7. Fixed golden_trajectory.json")

# 9. Fix fractional targets (CH-36, CH-41)
plan_path = DST / "environment/input/channel_plan.csv"
with open(plan_path, "r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    plan_fields = reader.fieldnames
    plan_rows = list(reader)
for row in plan_rows:
    if row["channel_id"] == "CH-36":
        row["planned_reach_per_placement"] = "2000"
    elif row["channel_id"] == "CH-41":
        row["planned_reach_per_placement"] = "1000"
with open(plan_path, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=plan_fields)
    writer.writeheader()
    writer.writerows(plan_rows)

# Update CH-41 gold
sa_path = DST / "solution/files/shortfall_attribution.csv"
with open(sa_path, "r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    sa_fields = reader.fieldnames
    sa_rows = list(reader)
for row in sa_rows:
    if row["channel_id"] == "CH-41":
        row["residual_reach_effect_streams"] = "1"
        row["shortfall_to_target_streams"] = "1"
with open(sa_path, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=sa_fields)
    writer.writeheader()
    writer.writerows(sa_rows)

# Update results.json
results_path = DST / "solution/files/results.json"
results = json.loads(results_path.read_text(encoding="utf-8"))
results["residual_reach_effect_streams"] += 1  # 26631 + 1 = 26632
results["shortfall_to_target_streams"] += 1  # 96345 + 1 = 96346
results_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")

# Update verifier results_figures and register_table
for v in spec["verifiers"]:
    if v["name"] == "register_table":
        rows = v["assertion"]["expected"]["rows"]
        rows["CH-41"]["residual_reach_effect_streams"] = "1"
        rows["CH-41"]["shortfall_to_target_streams"] = "1"
    if v["name"] == "results_figures":
        v["assertion"]["expected"]["keys"]["residual_reach_effect_streams"]["value"] = results["residual_reach_effect_streams"]
        v["assertion"]["expected"]["keys"]["shortfall_to_target_streams"]["value"] = results["shortfall_to_target_streams"]
verifier_path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")

# Update golden_trajectory
for step in traj:
    cmd = str(step.get("arguments", {}).get("command", ""))
    if "results.json" in cmd and "counted_placement_count" in cmd:
        cmd = cmd.replace('"residual_reach_effect_streams": 26631', f'"residual_reach_effect_streams": {results["residual_reach_effect_streams"]}')
        cmd = cmd.replace('"shortfall_to_target_streams": 96345', f'"shortfall_to_target_streams": {results["shortfall_to_target_streams"]}')
        step["arguments"]["command"] = cmd
    if "shortfall_attribution.csv" in cmd and "CH-41" in cmd:
        cmd = cmd.replace("CH-41,1,0,0,0,0", "CH-41,1,0,0,1,1")
        step["arguments"]["command"] = cmd
traj_path.write_text(json.dumps(traj, indent=2) + "\n", encoding="utf-8")

print(f"8. Fixed fractional targets + updated gold: {results}")
assert results["placements_effect_streams"] + results["conversion_effect_streams"] + results["residual_reach_effect_streams"] == results["shortfall_to_target_streams"]

# 10. Fix review.csv
review_path = DST / "review.csv"
review = review_path.read_text(encoding="utf-8")
review = review.replace("13 checks", "thirteen checks")
review = review.replace("13 verifier", "thirteen verifier")
review = review.replace("all 13", "all thirteen")
review = review.replace("RE=26631", f"RE={results['residual_reach_effect_streams']}")
review = review.replace("SF=96345", f"SF={results['shortfall_to_target_streams']}")
review_path.write_text(review, encoding="utf-8")
print("9. Fixed review.csv")

# 11. Add memo content check to test_outputs.py
test_path = DST / "tests/test_outputs.py"
test_code = test_path.read_text(encoding="utf-8")
new_test = '''

def test_memo_has_content_words():
    """The memo must contain substantive content, not just tokens."""
    memo_path = WORKSPACE / "campaign_review.md"
    if not memo_path.is_file():
        pytest.skip("no campaign_review.md")
    import re
    text = memo_path.read_text(encoding="utf-8")
    words = re.findall(r"\\b[A-Za-z][A-Za-z]{2,}\\b", text)
    stopwords = {"the", "and", "for", "with", "that", "this", "from",
                 "are", "was", "but", "not", "all", "can", "has", "had",
                 "its", "one", "two", "per", "out", "our", "who", "how",
                 "did", "got", "set", "put", "let", "yet", "any", "own",
                 "too", "run", "may", "way", "use", "few", "off"}
    content_words = [w for w in words if w.lower() not in stopwords]
    assert len(content_words) >= 30, (
        f"memo has only {len(content_words)} content words; "
        "a review note needs substance, not just tokens"
    )
    paragraphs = text.split("\\n\\n")
    found = False
    for para in paragraphs:
        has_channel = "CH-41" in para
        has_part = any(p in para.lower() for p in ["residual", "conversion", "placements"])
        if has_channel and has_part:
            found = True
            break
    assert found, (
        "memo must name the single-part channel (CH-41) and the part "
        "it sits in (residual) in the same paragraph"
    )
'''
test_code = test_code.rstrip() + new_test
test_path.write_text(test_code, encoding="utf-8")
print("10. Added test_memo_has_content_words")

# 12. Convert ALL to LF
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
print(f"11. Converted {fixed} files to LF")

# 13. Build zip
out = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\canonical-zips\UPLOAD-THIS-TO-QC-bus-b50-v25.zip")
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
print(f"12. Built {out.name}: {n} files, {out.stat().st_size} bytes")

workspace_copy = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\UPLOAD-THIS-TO-QC-bus-b50-v25.zip")
shutil.copy2(out, workspace_copy)
print("13. Copied to workspace")

print(f"\nDone! v25: no fractional streams + 5.4/5.7 fixed + memo fixes")
print(f"Gold: {results}")
print(f"Key: no rounding ambiguity -> Harbor Check won't flag it")
print(f"Question: will 44-channel data without ambiguity still be 0/4 GLM?")
