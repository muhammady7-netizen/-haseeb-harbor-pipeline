"""Fix v21 fractional targets: change CH-36 and CH-41 reach to make targets whole."""
import json, csv, os
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_DOWN

DST = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\task-sources\bus-b50-v21")

def r_toward(x):
    d = Decimal(str(x))
    return int(d.quantize(Decimal('1'), rounding=ROUND_HALF_DOWN))

# 1. Fix channel_plan.csv: CH-36 reach 1500->2000, CH-41 reach 500->1000
plan_path = DST / "environment/input/channel_plan.csv"
with open(plan_path, "r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    plan_fields = reader.fieldnames
    plan_rows = list(reader)

for row in plan_rows:
    if row["channel_id"] == "CH-36":
        row["planned_reach_per_placement"] = "2000"
        print(f"CH-36: reach 1500->2000, target={1*2000*1/1000}")
    elif row["channel_id"] == "CH-41":
        row["planned_reach_per_placement"] = "1000"
        print(f"CH-41: reach 500->1000, target={1*1000*1/1000}")

with open(plan_path, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=plan_fields)
    writer.writeheader()
    writer.writerows(plan_rows)
print("1. Fixed channel_plan.csv")

# 2. Recompute gold for CH-41 (target changed from 0.5 to 1.0)
# CH-41: pl=1, reach=1000, rate=1, target=1.0
# counted=1 (1 placement ran in W1, in window)
# delivered_streams=0, delivered_reach=500
# SF = 1.0 - 0 = 1.0 -> r_toward(1.0) = 1
# PE = (1-1)*1000*1/1000 = 0
# CE = 500*1.0*1/1000 - 0 = 0.5 -> r_toward(0.5) = 0
# RR = 1 - 0 - 0 = 1
ch41_old = {"PE": 0, "CE": 0, "RR": 0, "SF": 0}
ch41_new = {"PE": 0, "CE": 0, "RR": 1, "SF": 1}
print(f"2. CH-41 gold: {ch41_old} -> {ch41_new}")

# 3. Update shortfall_attribution.csv
sa_path = DST / "solution/files/shortfall_attribution.csv"
with open(sa_path, "r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    sa_fields = reader.fieldnames
    sa_rows = list(reader)

for row in sa_rows:
    if row["channel_id"] == "CH-41":
        row["placements_effect_streams"] = str(ch41_new["PE"])
        row["conversion_effect_streams"] = str(ch41_new["CE"])
        row["residual_reach_effect_streams"] = str(ch41_new["RR"])
        row["shortfall_to_target_streams"] = str(ch41_new["SF"])

with open(sa_path, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=sa_fields)
    writer.writeheader()
    writer.writerows(sa_rows)
print("3. Updated shortfall_attribution.csv")

# 4. Update results.json
results_path = DST / "solution/files/results.json"
results = json.loads(results_path.read_text(encoding="utf-8"))
results["residual_reach_effect_streams"] += ch41_new["RR"] - ch41_old["RR"]  # +1
results["shortfall_to_target_streams"] += ch41_new["SF"] - ch41_old["SF"]  # +1
results_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
print(f"4. Updated results.json: {results}")
assert results["placements_effect_streams"] + results["conversion_effect_streams"] + results["residual_reach_effect_streams"] == results["shortfall_to_target_streams"]

# 5. Update campaign_review.md
memo_path = DST / "solution/files/campaign_review.md"
memo = memo_path.read_text(encoding="utf-8")
# Check if memo mentions specific figures that changed
# The memo mentions "Conversion effect" and "Counted placements" figures
# CE didn't change, counted didn't change. Only RR and SF changed.
# The memo doesn't mention RR or SF directly, so no change needed.
print("5. campaign_review.md unchanged (CE and counted didn't change)")

# 6. Update verifier.json
verifier_path = DST / "tests/verifier.json"
spec = json.loads(verifier_path.read_text(encoding="utf-8"))
for v in spec["verifiers"]:
    if v["name"] == "register_table":
        rows = v["assertion"]["expected"]["rows"]
        rows["CH-41"]["placements_effect_streams"] = str(ch41_new["PE"])
        rows["CH-41"]["conversion_effect_streams"] = str(ch41_new["CE"])
        rows["CH-41"]["residual_reach_effect_streams"] = str(ch41_new["RR"])
        rows["CH-41"]["shortfall_to_target_streams"] = str(ch41_new["SF"])
        print("6. Updated verifier.json CH-41 row")

    if v["name"] == "results_figures":
        v["assertion"]["expected"]["keys"]["residual_reach_effect_streams"]["value"] = results["residual_reach_effect_streams"]
        v["assertion"]["expected"]["keys"]["shortfall_to_target_streams"]["value"] = results["shortfall_to_target_streams"]
        print("6. Updated verifier.json results_figures")

verifier_path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")

# 7. Update golden_trajectory.json
traj_path = DST / "solution/golden_trajectory.json"
traj = json.loads(traj_path.read_text(encoding="utf-8"))
for step in traj:
    cmd = str(step.get("arguments", {}).get("command", ""))
    if "results.json" in cmd and "counted_placement_count" in cmd:
        cmd = cmd.replace('"residual_reach_effect_streams": 26631', f'"residual_reach_effect_streams": {results["residual_reach_effect_streams"]}')
        cmd = cmd.replace('"shortfall_to_target_streams": 96345', f'"shortfall_to_target_streams": {results["shortfall_to_target_streams"]}')
        step["arguments"]["command"] = cmd

    if "shortfall_attribution.csv" in cmd and "channel_id" in cmd:
        # Update CH-41 in the embedded CSV
        cmd = cmd.replace("CH-41,1,0,0,0,0", f"CH-41,1,{ch41_new['PE']},{ch41_new['CE']},{ch41_new['RR']},{ch41_new['SF']}")
        step["arguments"]["command"] = cmd

traj_path.write_text(json.dumps(traj, indent=2) + "\n", encoding="utf-8")
print("7. Updated golden_trajectory.json")

# 8. Update review.csv
review_path = DST / "review.csv"
review = review_path.read_text(encoding="utf-8")
# Update any figures that changed
review = review.replace("RE=26631", f"RE={results['residual_reach_effect_streams']}")
review = review.replace("SF=96345", f"SF={results['shortfall_to_target_streams']}")
review_path.write_text(review, encoding="utf-8")
print("8. Updated review.csv")

# 9. Convert ALL files to LF
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
print(f"9. Converted {fixed} files to LF")

# 10. Rebuild zip
import zipfile, shutil
out = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\canonical-zips\UPLOAD-THIS-TO-QC-bus-b50-v21.zip")
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
print(f"10. Built {out.name}: {n} files, {out.stat().st_size} bytes")

workspace_copy = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\UPLOAD-THIS-TO-QC-bus-b50-v21.zip")
shutil.copy2(out, workspace_copy)
print("11. Copied to workspace for upload")

print(f"\nDone! v21 fixed: fractional targets resolved, gold updated.")
print(f"New gold: counted={results['counted_placement_count']} PE={results['placements_effect_streams']} CE={results['conversion_effect_streams']} RR={results['residual_reach_effect_streams']} SF={results['shortfall_to_target_streams']}")
