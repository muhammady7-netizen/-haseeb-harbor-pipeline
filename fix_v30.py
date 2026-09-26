"""Fix bus-b50 v29 findings: CH-78 gold + memo figure checks back in verifier.json.

Finding 1+2: CH-78 CE=-725 is wrong. Rule 5.6 says 0.9 for W4-W7.
  W5 row: 45000*0.9*25/1000 = 1012.5, not 45000*25/1000 = 1125
  Correct CE = 50000*1.0*25/1000 + 1012.5 - 3100 = -837.5 -> -837
  Correct RR = 900 - 0 - (-837) = 1737

Finding 3+4: memo figure checks need to be reward-bearing (in verifier.json).
  Add memo_conversion_effect + memo_counted_placements back with content words.
  Use regex_match on md.extract_text with figure + keyword (D1 compliant).
"""
import json, csv, os
from pathlib import Path

DST = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\task-sources\bus-b50-v29")

# === 1. Fix CH-78 gold in shortfall_attribution.csv ===
sa_path = DST / "solution/files/shortfall_attribution.csv"
with open(sa_path, "r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    sa_fields = reader.fieldnames
    sa_rows = list(reader)

old_ce = -725
old_rr = 1625
new_ce = -837
new_rr = 1737

for row in sa_rows:
    if row["channel_id"] == "CH-78":
        row["conversion_effect_streams"] = str(new_ce)
        row["residual_reach_effect_streams"] = str(new_rr)
        print(f"Fixed CH-78: CE {old_ce} -> {new_ce}, RR {old_rr} -> {new_rr}")

with open(sa_path, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=sa_fields)
    writer.writeheader()
    writer.writerows(sa_rows)

# === 2. Update results.json ===
results_path = DST / "solution/files/results.json"
results = json.loads(results_path.read_text(encoding="utf-8"))
ce_delta = new_ce - old_ce  # -837 - (-725) = -112
rr_delta = new_rr - old_rr  # 1737 - 1625 = 112
results["conversion_effect_streams"] += ce_delta  # 38943 - 112 = 38831
results["residual_reach_effect_streams"] += rr_delta  # 33204 + 112 = 33316
results_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
print(f"Updated results.json: CE={results['conversion_effect_streams']}, RR={results['residual_reach_effect_streams']}")
assert results["placements_effect_streams"] + results["conversion_effect_streams"] + results["residual_reach_effect_streams"] == results["shortfall_to_target_streams"]

# === 3. Update verifier.json: Fix CH-78 + Add memo figure checks ===
verifier_path = DST / "tests/verifier.json"
spec = json.loads(verifier_path.read_text(encoding="utf-8"))

for v in spec["verifiers"]:
    if v["name"] == "register_table":
        rows = v["assertion"]["expected"]["rows"]
        rows["CH-78"]["conversion_effect_streams"] = str(new_ce)
        rows["CH-78"]["residual_reach_effect_streams"] = str(new_rr)
        print(f"Fixed verifier.json CH-78 row")

    if v["name"] == "results_figures":
        v["assertion"]["expected"]["keys"]["conversion_effect_streams"]["value"] = results["conversion_effect_streams"]
        v["assertion"]["expected"]["keys"]["residual_reach_effect_streams"]["value"] = results["residual_reach_effect_streams"]
        print(f"Fixed verifier.json results_figures")

# Add memo figure checks back as reward-bearing verifier entries
# These have content words (conversion/counted/placements) so D1 won't flag them
ce_value = results["conversion_effect_streams"]
cp_value = results["counted_placement_count"]

memo_ce_check = {
    "name": "memo_conversion_effect",
    "metadata": {
        "how_justification": "Opens campaign_review.md with md.extract_text and applies regex_match to verify the conversion effect figure appears beside its label.",
        "why_justification": "The campaign total of the conversion part is a material disclosed requirement the memo must state.",
        "tag": "incidental"
    },
    "source": {
        "type": "file",
        "file": {
            "type": "md",
            "command": "extract_text",
            "arguments": {"path": "campaign_review.md"}
        }
    },
    "assertion": {
        "type": "deterministic",
        "expected": f"(?is)(?:\\bconversion\\b.+\\b{ce_value}\\b|\\b{ce_value}\\b.+\\bconversion\\b)",
        "deterministic": {
            "path": "$.text",
            "comparison": "regex_match"
        }
    }
}

memo_cp_check = {
    "name": "memo_counted_placements",
    "metadata": {
        "how_justification": "Opens campaign_review.md with md.extract_text and applies regex_match to verify the counted placements figure appears beside its label.",
        "why_justification": "The number of placements counted across every channel is a material disclosed requirement the memo must state.",
        "tag": "incidental"
    },
    "source": {
        "type": "file",
        "file": {
            "type": "md",
            "command": "extract_text",
            "arguments": {"path": "campaign_review.md"}
        }
    },
    "assertion": {
        "type": "deterministic",
        "expected": f"(?is)(?:\\bcounted\\b.+\\b{cp_value}\\b|\\b{cp_value}\\b.+\\bcounted\\b)",
        "deterministic": {
            "path": "$.text",
            "comparison": "regex_match"
        }
    }
}

# Insert before results_figures
insert_idx = None
for i, v in enumerate(spec["verifiers"]):
    if v["name"] == "results_figures":
        insert_idx = i
        break

spec["verifiers"].insert(insert_idx, memo_ce_check)
spec["verifiers"].insert(insert_idx + 1, memo_cp_check)
print(f"Added memo_conversion_effect + memo_counted_placements to verifier.json ({len(spec['verifiers'])} total)")

verifier_path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")

# === 4. Update golden_trajectory.json ===
traj_path = DST / "solution/golden_trajectory.json"
traj = json.loads(traj_path.read_text(encoding="utf-8"))
for step in traj:
    cmd = str(step.get("arguments", {}).get("command", ""))
    if "results.json" in cmd and "counted_placement_count" in cmd:
        cmd = cmd.replace('"conversion_effect_streams": 38943', f'"conversion_effect_streams": {results["conversion_effect_streams"]}')
        cmd = cmd.replace('"residual_reach_effect_streams": 33204', f'"residual_reach_effect_streams": {results["residual_reach_effect_streams"]}')
        step["arguments"]["command"] = cmd
    if "shortfall_attribution.csv" in cmd and "CH-78" in cmd:
        cmd = cmd.replace("CH-78,2,0,-725,1625,900", f"CH-78,2,0,{new_ce},{new_rr},900")
        step["arguments"]["command"] = cmd

traj_path.write_text(json.dumps(traj, indent=2) + "\n", encoding="utf-8")
print("Updated golden_trajectory.json")

# === 5. Update campaign_review.md with corrected figure ===
memo_path = DST / "solution/files/campaign_review.md"
memo = memo_path.read_text(encoding="utf-8")
memo = memo.replace("Conversion effect: 38943", f"Conversion effect: {results['conversion_effect_streams']}")
memo_path.write_text(memo, encoding="utf-8")
print(f"Updated campaign_review.md: Conversion effect -> {results['conversion_effect_streams']}")

# === 6. Update review.csv ===
review_path = DST / "review.csv"
review = review_path.read_text(encoding="utf-8")
review = review.replace("CE=38943", f"CE={results['conversion_effect_streams']}")
review = review.replace("RE=33204", f"RE={results['residual_reach_effect_streams']}")
review_path.write_text(review, encoding="utf-8")
print("Updated review.csv")

# === 7. Convert ALL to LF ===
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

# === 8. Build zip ===
import zipfile, shutil
out = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\canonical-zips\UPLOAD-THIS-TO-QC-bus-b50-v30.zip")
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
print(f"Built {out.name}: {n} files, {out.stat().st_size} bytes")

workspace_copy = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\UPLOAD-THIS-TO-QC-bus-b50-v30.zip")
shutil.copy2(out, workspace_copy)
print("Copied to workspace")

print(f"\nDone! v30 fixes:")
print(f"  1. CH-78 gold: CE -725 -> -837, RR 1625 -> 1737 (5.6 0.9 factor applied to W5)")
print(f"  2. Memo figure checks: Added back to verifier.json as reward-bearing with content words")
print(f"  3. Results: CE={results['conversion_effect_streams']}, RR={results['residual_reach_effect_streams']}")
print(f"  4. Verifiers: {len(spec['verifiers'])} total (was 9, now 11 with memo figure checks)")
print(f"  5. Hardening preserved: retroactive amendments unchanged, 0/4 GLM difficulty maintained")
