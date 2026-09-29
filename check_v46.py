import json, csv
from pathlib import Path

ROOT = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\task-sources\bus-b50-v1000traps\bus-b50-b10-streaming-target-variance-attribution")

with (ROOT / "solution/files/shortfall_attribution.csv").open(encoding="utf-8") as f:
    csv_rows = {r["channel_id"]: r for r in csv.DictReader(f)}

spec = json.loads((ROOT / "tests/verifier.json").read_text(encoding="utf-8"))
results = json.loads((ROOT / "solution/files/results.json").read_text(encoding="utf-8"))

mismatches = 0
for v in spec["verifiers"]:
    if v["name"] == "register_table":
        ver_rows = v["assertion"]["expected"]["rows"]
        for ch in sorted(set(list(ver_rows.keys()) + list(csv_rows.keys()))):
            vr = ver_rows.get(ch, {})
            cr = csv_rows.get(ch, {})
            for col in ["counted_placements", "placements_effect_streams", "conversion_effect_streams", "residual_reach_effect_streams", "shortfall_to_target_streams"]:
                vv = str(vr.get(col, "MISSING"))
                cv = str(cr.get(col, "MISSING"))
                if vv != cv:
                    mismatches += 1
                    if mismatches <= 10:
                        print("MISMATCH %s %s: verifier=%s csv=%s" % (ch, col, vv, cv))
    if v["name"] == "results_figures":
        for k, val in v["assertion"]["expected"]["keys"].items():
            if val["value"] != results.get(k):
                print("RESULT MISMATCH %s: verifier=%s actual=%s" % (k, val["value"], results.get(k)))

print("Total mismatches: %d" % mismatches)
