import json, csv
from pathlib import Path

ROOT = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\task-sources\bus-b50-v29")

# Read solver output
with (ROOT / "solution/files/shortfall_attribution.csv").open(encoding="utf-8") as f:
    solver_rows = {r["channel_id"]: r for r in csv.DictReader(f)}

# Read verifier expected
spec = json.loads((ROOT / "tests/verifier.json").read_text(encoding="utf-8"))
verifier_rows = {}
for v in spec["verifiers"]:
    if v["name"] == "register_table":
        verifier_rows = v["assertion"]["expected"]["rows"]
    if v["name"] == "register_table_trap_ch04":
        verifier_rows["CH-04"] = v["assertion"]["expected"]["rows"]["CH-04"]

# Read results
results = json.loads((ROOT / "solution/files/results.json").read_text(encoding="utf-8"))
ver_results = {}
for v in spec["verifiers"]:
    if v["name"] == "results_figures":
        for k, val in v["assertion"]["expected"]["keys"].items():
            ver_results[k] = val["value"]

# Compare each channel
mismatches = []
for ch in sorted(set(list(solver_rows.keys()) + list(verifier_rows.keys()))):
    s = solver_rows.get(ch, {})
    v = verifier_rows.get(ch, {})
    for col in ["counted_placements", "placements_effect_streams", "conversion_effect_streams", "residual_reach_effect_streams", "shortfall_to_target_streams"]:
        sv = str(s.get(col, "MISSING"))
        vv = str(v.get(col, "MISSING"))
        if sv != vv:
            mismatches.append(f"  {ch} {col}: solver={sv} verifier={vv}")

# Compare results
for k in ["counted_placement_count", "placements_effect_streams", "conversion_effect_streams", "residual_reach_effect_streams", "shortfall_to_target_streams"]:
    sv = str(results.get(k, "MISSING"))
    vv = str(ver_results.get(k, "MISSING"))
    if sv != vv:
        mismatches.append(f"  results.json {k}: solver={sv} verifier={vv}")

if mismatches:
    print(f"MISMATCHES ({len(mismatches)}):")
    for m in mismatches:
        print(m)
else:
    print("ALL MATCH - no mismatches found")
