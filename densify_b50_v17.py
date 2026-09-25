"""Densify bus-b50 v17: Add CH-59 with mid-campaign amendment trap.

The amendment changes planned_streams_per_1000_reach from 40 to 35 for CH-59
in W4-W7. The conversion effect for those rows must use the amended rate.
The placements effect always uses the original plan rate.

A script that doesn't read or implement the amendment gets CE=160 instead of CE=-222.
"""
import json, csv, os, re
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_DOWN

ROOT = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\task-sources\bus-b50")
INPUT = ROOT / "environment" / "input"
SOL = ROOT / "solution" / "files"
TESTS = ROOT / "tests"

def round_half_away(x):
    """Round halves away from zero."""
    from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_DOWN
    d = Decimal(str(x))
    if d >= 0:
        return int(d.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    else:
        return int(d.quantize(Decimal('1'), rounding=ROUND_HALF_DOWN))

def round_half_toward(x):
    """Round halves toward zero."""
    from decimal import Decimal, ROUND_HALF_DOWN
    d = Decimal(str(x))
    return int(d.quantize(Decimal('1'), rounding=ROUND_HALF_DOWN))

# 1. Add amendment rules to attribution_note.md
note_path = INPUT / "attribution_note.md"
note = note_path.read_text(encoding="utf-8")
amendment_text = """

## 7. Mid-campaign plan amendments

**7.1** A channel's `planned_streams_per_1000_reach` may be amended mid-campaign
by a note in this section. An amendment applies only to the channel it names,
and only to ledger rows in weeks on or after the amendment's effective week.
Where an amendment is in force, the conversion effect for affected rows uses
the amended `planned_streams_per_1000_reach` in place of the plan's value, and
the placements effect uses the plan's original value throughout.

**7.2** Amendment A1: For CH-59, the `planned_streams_per_1000_reach` is amended
to 35 (from 40) for campaign weeks W4 through W7. The original value of 40
applies for W1 through W3.
"""
note = note.rstrip() + amendment_text
note_path.write_text(note, encoding="utf-8")
print("1. Updated attribution_note.md with amendment rules")

# 2. Add CH-59 to channel_plan.csv
plan_path = INPUT / "channel_plan.csv"
with open(plan_path, "r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    plan_fields = reader.fieldnames
    plan_rows = list(reader)

plan_rows.append({
    "channel_id": "CH-59",
    "channel_name": "Amended conversion rate",
    "planned_placements": "3",
    "planned_reach_per_placement": "50000",
    "planned_streams_per_1000_reach": "40",
})
with open(plan_path, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=plan_fields)
    writer.writeheader()
    writer.writerows(plan_rows)
print(f"2. Added CH-59 to channel_plan.csv ({len(plan_rows)} channels)")

# 3. Add placements for CH-59 to placement_log.csv
log_path = INPUT / "placement_log.csv"
with open(log_path, "r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    log_fields = reader.fieldnames
    log_rows = list(reader)

# 3 placements, all ran inside window
log_rows.extend([
    {"placement_id": f"PL-59{i}", "channel_id": "CH-59", "planned_week": wk,
     "ran_week": wk, "placement_status": "ran", "offer_type": "promotional"}
    for i, wk in enumerate(["W1", "W4", "W5"], start=1)
])
with open(log_path, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=log_fields)
    writer.writeheader()
    writer.writerows(log_rows)
print(f"3. Added 3 placements for CH-59 to placement_log.csv")

# 4. Add ledger rows for CH-59 to streaming_ledger.csv
ledger_path = INPUT / "streaming_ledger.csv"
with open(ledger_path, "r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    ledger_fields = reader.fieldnames
    ledger_rows = list(reader)

ledger_rows.extend([
    {"ledger_ref": f"L59-{i}", "channel_id": "CH-59", "campaign_week": wk,
     "placement_id": pid, "delivered_reach": reach, "delivered_streams": streams}
    for i, (wk, pid, reach, streams) in enumerate([
        ("W1", "P59-1", "50000", "1900"),
        ("W4", "P59-2", "45000", "1600"),
        ("W5", "P59-3", "40000", "1400"),
    ], start=1)
])
with open(ledger_path, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=ledger_fields)
    writer.writeheader()
    writer.writerows(ledger_rows)
print(f"4. Added 3 ledger rows for CH-59 to streaming_ledger.csv")

# 5. Compute gold for CH-59
# Target = 3 * 50000 * 40 / 1000 = 6000
target = 3 * 50000 * 40 / 1000  # 6000
# Delivered streams = 1900 + 1600 + 1400 = 4900
delivered_streams = 1900 + 1600 + 1400  # 4900
# Delivered reach = 50000 + 45000 + 40000 = 135000
delivered_reach = 50000 + 45000 + 40000  # 135000
# Counted placements = 3 (all ran inside window)
counted = 3
# Shortfall = 6000 - 4900 = 1100
shortfall_raw = target - delivered_streams  # 1100
shortfall = round_half_toward(shortfall_raw)  # 1100

# PE = (3-3) * 50000 * 40 / 1000 = 0
pe_raw = (3 - counted) * 50000 * 40 / 1000  # 0
pe = round_half_away(pe_raw) if shortfall > 0 else round_half_toward(pe_raw)  # 0

# CE with amendment:
# Row W1 (rate 1.0, plan rate 40): 50000 * 1.0 * 40 / 1000 = 2000
# Row W4 (rate 0.9, amended rate 35): 45000 * 0.9 * 35 / 1000 = 1417.5
# Row W5 (rate 0.9, amended rate 35): 40000 * 0.9 * 35 / 1000 = 1260
ce_w1 = 50000 * 1.0 * 40 / 1000  # 2000
ce_w4 = 45000 * 0.9 * 35 / 1000  # 1417.5
ce_w5 = 40000 * 0.9 * 35 / 1000  # 1260
ce_expected = ce_w1 + ce_w4 + ce_w5  # 4677.5
ce_raw = ce_expected - delivered_streams  # 4677.5 - 4900 = -222.5
ce = round_half_toward(ce_raw)  # -222

# RR = shortfall - PE - CE = 1100 - 0 - (-222) = 1322
rr = shortfall - pe - ce  # 1322

print(f"5. CH-59 gold: counted={counted} PE={pe} CE={ce} RR={rr} shortfall={shortfall}")
assert pe + ce + rr == shortfall, f"Parts don't add up: {pe}+{ce}+{rr}={pe+ce+rr} != {shortfall}"

# 6. Update shortfall_attribution.csv
sa_path = SOL / "shortfall_attribution.csv"
with open(sa_path, "r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    sa_fields = reader.fieldnames
    sa_rows = list(reader)

sa_rows.append({
    "channel_id": "CH-59",
    "counted_placements": str(counted),
    "placements_effect_streams": str(pe),
    "conversion_effect_streams": str(ce),
    "residual_reach_effect_streams": str(rr),
    "shortfall_to_target_streams": str(shortfall),
})
with open(sa_path, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=sa_fields)
    writer.writeheader()
    writer.writerows(sa_rows)
print(f"6. Added CH-59 to shortfall_attribution.csv ({len(sa_rows)} rows)")

# 7. Update results.json
results_path = SOL / "results.json"
results = json.loads(results_path.read_text(encoding="utf-8"))
results["counted_placement_count"] += counted  # 125 + 3 = 128
results["placements_effect_streams"] += pe  # 31699 + 0 = 31699
results["conversion_effect_streams"] += ce  # 31246 + (-222) = 31024
results["residual_reach_effect_streams"] += rr  # 49619 + 1322 = 50941
results["shortfall_to_target_streams"] += shortfall  # 112564 + 1100 = 113664
results_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
print(f"7. Updated results.json: {results}")

# 8. Update campaign_review.md
memo_path = SOL / "campaign_review.md"
memo = memo_path.read_text(encoding="utf-8")
memo = memo.replace("Counted placements: 125", f"Counted placements: {results['counted_placement_count']}")
memo = memo.replace("Conversion effect: 31246", f"Conversion effect: {results['conversion_effect_streams']}")
memo_path.write_text(memo, encoding="utf-8")
print(f"8. Updated campaign_review.md figures")

# 9. Update verifier.json
verifier_path = TESTS / "verifier.json"
spec = json.loads(verifier_path.read_text(encoding="utf-8"))

# Add CH-59 to register_table rows and row_set
for v in spec["verifiers"]:
    if v["name"] == "register_table":
        v["assertion"]["expected"]["rows"]["CH-59"] = {
            "counted_placements": str(counted),
            "placements_effect_streams": str(pe),
            "conversion_effect_streams": str(ce),
            "residual_reach_effect_streams": str(rr),
            "shortfall_to_target_streams": str(shortfall),
        }
        v["assertion"]["expected"]["row_set"].append("CH-59")

    # Update results_figures
    if v["name"] == "results_figures":
        v["assertion"]["expected"]["keys"]["counted_placement_count"]["value"] = results["counted_placement_count"]
        v["assertion"]["expected"]["keys"]["placements_effect_streams"]["value"] = results["placements_effect_streams"]
        v["assertion"]["expected"]["keys"]["conversion_effect_streams"]["value"] = results["conversion_effect_streams"]
        v["assertion"]["expected"]["keys"]["residual_reach_effect_streams"]["value"] = results["residual_reach_effect_streams"]
        v["assertion"]["expected"]["keys"]["shortfall_to_target_streams"]["value"] = results["shortfall_to_target_streams"]

    # Update memo figure checks
    if v["name"] == "memo_conversion_effect":
        old_fig = "31246"
        new_fig = str(results["conversion_effect_streams"])
        v["assertion"]["expected"] = v["assertion"]["expected"].replace(old_fig, new_fig)
        # Also update comma-formatted versions
        old_fig_c = f"{int(old_fig):,}"
        new_fig_c = f"{int(new_fig):,}"
        v["assertion"]["expected"] = v["assertion"]["expected"].replace(old_fig_c, new_fig_c)

    if v["name"] == "memo_conversion_effect_exactly_one":
        old_fig = "31246"
        new_fig = str(results["conversion_effect_streams"])
        v["assertion"]["expected"] = v["assertion"]["expected"].replace(old_fig, new_fig)
        old_fig_c = f"{int(old_fig):,}"
        new_fig_c = f"{int(new_fig):,}"
        v["assertion"]["expected"] = v["assertion"]["expected"].replace(old_fig_c, new_fig_c)

    if v["name"] == "memo_counted_placements":
        old_fig = "125"
        new_fig = str(results["counted_placement_count"])
        v["assertion"]["expected"] = v["assertion"]["expected"].replace(old_fig, new_fig)
        old_fig_c = f"{int(old_fig):,}"
        new_fig_c = f"{int(new_fig):,}"
        v["assertion"]["expected"] = v["assertion"]["expected"].replace(old_fig_c, new_fig_c)

    if v["name"] == "memo_counted_placements_exactly_one":
        old_fig = "125"
        new_fig = str(results["counted_placement_count"])
        v["assertion"]["expected"] = v["assertion"]["expected"].replace(old_fig, new_fig)
        old_fig_c = f"{int(old_fig):,}"
        new_fig_c = f"{int(new_fig):,}"
        v["assertion"]["expected"] = v["assertion"]["expected"].replace(old_fig_c, new_fig_c)

verifier_path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
print(f"9. Updated verifier.json with CH-59 row and new figures")

# 10. Update golden_trajectory.json
traj_path = ROOT / "solution" / "golden_trajectory.json"
traj = json.loads(traj_path.read_text(encoding="utf-8"))
for step in traj:
    cmd = str(step.get("arguments", {}).get("command", ""))
    if "results.json" in cmd and "counted_placement_count" in cmd:
        # Update embedded results.json
        old_results = '"counted_placement_count": 125'
        new_results = f'"counted_placement_count": {results["counted_placement_count"]}'
        cmd = cmd.replace(old_results, new_results)
        old_pe = '"placements_effect_streams": 31699'
        new_pe = f'"placements_effect_streams": {results["placements_effect_streams"]}'
        cmd = cmd.replace(old_pe, new_pe)
        old_ce = '"conversion_effect_streams": 31246'
        new_ce = f'"conversion_effect_streams": {results["conversion_effect_streams"]}'
        cmd = cmd.replace(old_ce, new_ce)
        old_rr = '"residual_reach_effect_streams": 49619'
        new_rr = f'"residual_reach_effect_streams": {results["residual_reach_effect_streams"]}'
        cmd = cmd.replace(old_rr, new_rr)
        old_sf = '"shortfall_to_target_streams": 112564'
        new_sf = f'"shortfall_to_target_streams": {results["shortfall_to_target_streams"]}'
        cmd = cmd.replace(old_sf, new_sf)
        step["arguments"]["command"] = cmd

    if "shortfall_attribution.csv" in cmd and "channel_id" in cmd:
        # Add CH-59 row to the embedded CSV
        ch59_line = f"\nCH-59,{counted},{pe},{ce},{rr},{shortfall}"
        # Find the end of the CSV data (before the heredoc terminator)
        for term in ["SHORTFALLATTRIBUTIONEOF", "EOF"]:
            if term in cmd:
                cmd = cmd.replace(term, ch59_line + "\n" + term)
                break
        step["arguments"]["command"] = cmd

    if "campaign_review.md" in cmd and "Counted placements" in cmd:
        cmd = cmd.replace("Counted placements: 125", f"Counted placements: {results['counted_placement_count']}")
        cmd = cmd.replace("Conversion effect: 31246", f"Conversion effect: {results['conversion_effect_streams']}")
        step["arguments"]["command"] = cmd

traj_path.write_text(json.dumps(traj, indent=2) + "\n", encoding="utf-8")
print(f"10. Updated golden_trajectory.json")

# 11. Update review.csv
review_path = ROOT / "review.csv"
review = review_path.read_text(encoding="utf-8")
review = review.replace("125 counted placements", f"{results['counted_placement_count']} counted placements")
review = review.replace("PE=31699", f"PE={results['placements_effect_streams']}")
review = review.replace("CE=31246", f"CE={results['conversion_effect_streams']}")
review = review.replace("RE=49619", f"RE={results['residual_reach_effect_streams']}")
review = review.replace("SF=112564", f"SF={results['shortfall_to_target_streams']}")
review = review.replace("54 channels", "55 channels")
review = review.replace("54-channel", "55-channel")
review = review.replace("54-row", "55-row")
review = review.replace("54-id", "55-id")
review_path.write_text(review, encoding="utf-8")
print(f"11. Updated review.csv")

# 12. Convert ALL files to LF
skip_dirs = {".git", "__pycache__", ".pytest_cache", "rl_world_verifiers"}
skip_exts = {".pyc", ".pyo", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".pdf", ".zip", ".xlsx", ".docx", ".pptx", ".so", ".dll", ".egg"}
fixed = 0
for p in ROOT.rglob("*"):
    if not p.is_file():
        continue
    if any(part in skip_dirs for part in p.parts):
        continue
    if p.suffix.lower() in skip_exts:
        continue
    try:
        data = p.read_bytes()
        if b"\r\n" in data:
            p.write_bytes(data.replace(b"\r\n", b"\n"))
            fixed += 1
    except:
        pass
print(f"12. Converted {fixed} files to LF")

print(f"\nDone! CH-59 amendment trap added.")
print(f"New totals: counted={results['counted_placement_count']} PE={results['placements_effect_streams']} CE={results['conversion_effect_streams']} RR={results['residual_reach_effect_streams']} SF={results['shortfall_to_target_streams']}")
print(f"If model ignores amendment: CE would be 160 instead of {ce}")
