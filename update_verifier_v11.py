import json
from pathlib import Path

ROOT = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\task-sources\bus-b50-v29")

# Read solver output
csv_path = ROOT / "solution" / "files" / "shortfall_attribution.csv"
results_path = ROOT / "solution" / "files" / "results.json"

import csv
with csv_path.open(encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

results = json.loads(results_path.read_text(encoding="utf-8"))
print(f"New totals: ce={results['conversion_effect_streams']}, cp={results['counted_placement_count']}")

# Update verifier.json
verifier_path = ROOT / "tests" / "verifier.json"
spec = json.loads(verifier_path.read_text(encoding="utf-8"))

# Update register_table rows for CH-01, CH-06, CH-13
for v in spec["verifiers"]:
    if v["name"] == "register_table":
        for ch_id in ["CH-01", "CH-06", "CH-13"]:
            row = next(r for r in rows if r["channel_id"] == ch_id)
            v["assertion"]["expected"]["rows"][ch_id] = {
                "counted_placements": row["counted_placements"],
                "placements_effect_streams": row["placements_effect_streams"],
                "conversion_effect_streams": row["conversion_effect_streams"],
                "residual_reach_effect_streams": row["residual_reach_effect_streams"],
                "shortfall_to_target_streams": row["shortfall_to_target_streams"],
            }
            print(f"  Updated {ch_id}: ce={row['conversion_effect_streams']}, re={row['residual_reach_effect_streams']}")

    # Update register_table_trap_ch04 (CH-04 unchanged, but verify)
    if v["name"] == "register_table_trap_ch04":
        row = next(r for r in rows if r["channel_id"] == "CH-04")
        v["assertion"]["expected"]["rows"]["CH-04"] = {
            "counted_placements": row["counted_placements"],
            "placements_effect_streams": row["placements_effect_streams"],
            "conversion_effect_streams": row["conversion_effect_streams"],
            "residual_reach_effect_streams": row["residual_reach_effect_streams"],
            "shortfall_to_target_streams": row["shortfall_to_target_streams"],
        }

    # Update results_figures with new totals
    if v["name"] == "results_figures":
        v["assertion"]["expected"]["keys"]["conversion_effect_streams"]["value"] = results["conversion_effect_streams"]
        v["assertion"]["expected"]["keys"]["residual_reach_effect_streams"]["value"] = results["residual_reach_effect_streams"]
        v["assertion"]["expected"]["keys"]["placements_effect_streams"]["value"] = results["placements_effect_streams"]
        v["assertion"]["expected"]["keys"]["shortfall_to_target_streams"]["value"] = results["shortfall_to_target_streams"]
        v["assertion"]["expected"]["keys"]["counted_placement_count"]["value"] = results["counted_placement_count"]
        print(f"  Updated results_figures: ce={results['conversion_effect_streams']}, re={results['residual_reach_effect_streams']}")

    # Update memo_conversion_effect with new total
    if v["name"] == "memo_conversion_effect":
        ce_val = results["conversion_effect_streams"]
        ce_str = str(ce_val)
        ce_comma = f"{ce_val:,}"
        v["assertion"]["expected"] = f"(?is)(?:\\bconversion\\b.+\\b(?:{ce_str}|{ce_comma})\\b|\\b(?:{ce_str}|{ce_comma})\\b.+\\bconversion\\b)"
        print(f"  Updated memo_conversion_effect: {ce_str}")

    # memo_counted_placements unchanged (cp=114, same)
    if v["name"] == "memo_counted_placements":
        cp_val = results["counted_placement_count"]
        cp_str = str(cp_val)
        v["assertion"]["expected"] = f"(?is)(?:\\bcounted\\b.+\\b(?:{cp_str}|{cp_str})\\b|\\b(?:{cp_str}|{cp_str})\\b.+\\bcounted\\b)"
        print(f"  memo_counted_placements: {cp_str} (unchanged)")

verifier_path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
print("\nverifier.json updated!")

# Also update campaign_review.md with new figures
memo_path = ROOT / "solution" / "files" / "campaign_review.md"
memo = memo_path.read_text(encoding="utf-8")

# Replace old conversion effect figure (38831) with new (33551)
memo = memo.replace("38831", str(results["conversion_effect_streams"]))
memo = memo.replace("38,831", f"{results['conversion_effect_streams']:,}")
# Counted placements unchanged (114)
memo_path.write_text(memo, encoding="utf-8")
print(f"campaign_review.md updated with new conversion effect: {results['conversion_effect_streams']}")
