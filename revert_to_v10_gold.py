import json, csv
from pathlib import Path

ROOT = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\task-sources\bus-b50-v29")

# Read solver output
with (ROOT / "solution/files/shortfall_attribution.csv").open(encoding="utf-8") as f:
    rows = {r["channel_id"]: r for r in csv.DictReader(f)}
results = json.loads((ROOT / "solution/files/results.json").read_text(encoding="utf-8"))
print("Gold values: ce=%s, re=%s, pe=%s, st=%s, cp=%s" % (results["conversion_effect_streams"], results["residual_reach_effect_streams"], results["placements_effect_streams"], results["shortfall_to_target_streams"], results["counted_placement_count"]))

# Update verifier.json
spec = json.loads((ROOT / "tests/verifier.json").read_text(encoding="utf-8"))
for v in spec["verifiers"]:
    if v["name"] == "register_table":
        for ch, row in v["assertion"]["expected"]["rows"].items():
            if ch in rows:
                for col in ["counted_placements","placements_effect_streams","conversion_effect_streams","residual_reach_effect_streams","shortfall_to_target_streams"]:
                    row[col] = rows[ch][col]
    if v["name"] == "register_table_trap_ch04":
        if "CH-04" in rows:
            for col in ["counted_placements","placements_effect_streams","conversion_effect_streams","residual_reach_effect_streams","shortfall_to_target_streams"]:
                v["assertion"]["expected"]["rows"]["CH-04"][col] = rows["CH-04"][col]
    if v["name"] == "results_figures":
        for k, val in v["assertion"]["expected"]["keys"].items():
            val["value"] = results[k]
    if v["name"] == "memo_conversion_effect":
        ce = results["conversion_effect_streams"]
        ce_str = str(ce)
        ce_comma = "%s" % format(ce, ",")
        v["assertion"]["expected"] = "(?is)\\bconversion\\s+effect\\s*[:\\-]\\s*(?:is\\s+|was\\s+|of\\s+|stands\\s+at\\s+)?(?:%s|%s)\\b" % (ce_str, ce_comma)
    if v["name"] == "memo_counted_placements":
        cp = results["counted_placement_count"]
        cp_str = str(cp)
        v["assertion"]["expected"] = "(?is)\\bcounted\\s+placements\\s*[:\\-]\\s*(?:is\\s+|are\\s+|of\\s+|stands\\s+at\\s+)?(?:%s)\\b" % cp_str

(ROOT / "tests/verifier.json").write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
print("verifier.json updated with A1-A5 gold values + tight memo regexes")

# Update campaign_review.md
memo_path = ROOT / "solution/files/campaign_review.md"
memo = memo_path.read_text(encoding="utf-8")
ce_val = results["conversion_effect_streams"]
memo = memo.replace("33551", str(ce_val)).replace("33,551", format(ce_val, ","))
memo_path.write_text(memo, encoding="utf-8")
print("campaign_review.md: conversion effect = %s" % ce_val)

# Update golden_trajectory.json
import subprocess
subprocess.run(["python", str(Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\update_trajectory.py"))], capture_output=True, text=True)
print("golden_trajectory.json updated")

# Verify everything matches
spec2 = json.loads((ROOT / "tests/verifier.json").read_text(encoding="utf-8"))
import re
memo2 = (ROOT / "solution/files/campaign_review.md").read_text(encoding="utf-8")
for v in spec2["verifiers"]:
    if v["name"] in ("memo_conversion_effect", "memo_counted_placements"):
        pattern = v["assertion"]["expected"]
        match = re.search(pattern, memo2)
        print("%s: %s" % (v["name"], "PASS" if match else "FAIL"))
