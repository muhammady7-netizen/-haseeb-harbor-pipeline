"""Densify bus-b50 v18: Three new trap channels exploiting different script assumptions.

CH-60: Cross-channel guaranteed placement - a ledger row for CH-60 references a
       placement_id that exists in placement_log.csv but belongs to CH-01 with
       offer_type=guaranteed_streams. Rule 3.2 excludes it, but a per-channel
       lookup script treats it as organic and counts it.

CH-61: Multiple amendments - CH-61 has TWO amendments: rate 35 for W4-W5 and
       rate 25 for W7. A script that applies one amendment to all late weeks
       gets the wrong conversion effect.

CH-62: Uncounted placement with in-window ledger row - a placement ran in W3
       (outside window, not counted) but its ledger row has campaign_week=W2
       (inside window, counted). Section 2 (placements) and Section 3 (ledger)
       are independent. A script that couples them skips the ledger row.
"""
import json, csv, os, re
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_DOWN

ROOT = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\task-sources\bus-b50")
INPUT = ROOT / "environment" / "input"
SOL = ROOT / "solution" / "files"
TESTS = ROOT / "tests"

def round_half_away(x):
    d = Decimal(str(x))
    if d >= 0:
        return int(d.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    return int(d.quantize(Decimal('1'), rounding=ROUND_HALF_DOWN))

def round_half_toward(x):
    d = Decimal(str(x))
    return int(d.quantize(Decimal('1'), rounding=ROUND_HALF_DOWN))

# === 1. Add amendment rules to attribution_note.md ===
note_path = INPUT / "attribution_note.md"
note = note_path.read_text(encoding="utf-8")
# Find the amendment section and add new amendments
new_amendments = """
**7.3** Amendment A3: For CH-61, the `planned_streams_per_1000_reach` is amended
to 35 (from 40) for campaign weeks W4 and W5. The original value of 40 applies
for all other weeks.

**7.4** Amendment A4: For CH-61, the `planned_streams_per_1000_reach` is further
amended to 25 (from 35) for campaign week W7. Where both A3 and A4 could apply,
the amendment naming the later week takes precedence. The original value of 40
applies for W1 through W3.
"""
note = note.rstrip() + new_amendments
note_path.write_text(note, encoding="utf-8")
print("1. Updated attribution_note.md with amendments A3 and A4")

# === 2. Add channels to channel_plan.csv ===
plan_path = INPUT / "channel_plan.csv"
with open(plan_path, "r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    plan_fields = reader.fieldnames
    plan_rows = list(reader)

new_channels = [
    {"channel_id": "CH-60", "channel_name": "Cross-channel guaranteed ref",
     "planned_placements": "2", "planned_reach_per_placement": "50000",
     "planned_streams_per_1000_reach": "40"},
    {"channel_id": "CH-61", "channel_name": "Multiple amendment rates",
     "planned_placements": "4", "planned_reach_per_placement": "50000",
     "planned_streams_per_1000_reach": "40"},
    {"channel_id": "CH-62", "channel_name": "Uncounted placement in-window ledger",
     "planned_placements": "3", "planned_reach_per_placement": "50000",
     "planned_streams_per_1000_reach": "40"},
]
plan_rows.extend(new_channels)
with open(plan_path, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=plan_fields)
    writer.writeheader()
    writer.writerows(plan_rows)
print(f"2. Added 3 channels to channel_plan.csv ({len(plan_rows)} total)")

# === 3. Add placements to placement_log.csv ===
log_path = INPUT / "placement_log.csv"
with open(log_path, "r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    log_fields = reader.fieldnames
    log_rows = list(reader)

new_placements = [
    # CH-60: 2 real placements (promotional, in window)
    {"placement_id": "PL-601", "channel_id": "CH-60", "planned_week": "W1", "ran_week": "W1", "placement_status": "ran", "offer_type": "promotional"},
    {"placement_id": "PL-602", "channel_id": "CH-60", "planned_week": "W1", "ran_week": "W1", "placement_status": "ran", "offer_type": "promotional"},
    # CH-01: Add a guaranteed placement that CH-60's ledger will reference (cross-channel trap)
    {"placement_id": "PL-GUAR-60", "channel_id": "CH-01", "planned_week": "W1", "ran_week": "W1", "placement_status": "ran", "offer_type": "guaranteed_streams"},
    # CH-61: 4 placements in W1, W2, W4, W7 (all in window)
    {"placement_id": "PL-6101", "channel_id": "CH-61", "planned_week": "W1", "ran_week": "W1", "placement_status": "ran", "offer_type": "promotional"},
    {"placement_id": "PL-6102", "channel_id": "CH-61", "planned_week": "W2", "ran_week": "W2", "placement_status": "ran", "offer_type": "promotional"},
    {"placement_id": "PL-6103", "channel_id": "CH-61", "planned_week": "W4", "ran_week": "W4", "placement_status": "ran", "offer_type": "promotional"},
    {"placement_id": "PL-6104", "channel_id": "CH-61", "planned_week": "W7", "ran_week": "W7", "placement_status": "ran", "offer_type": "promotional"},
    # CH-62: 3 placements, one ran in W3 (OUTSIDE window)
    {"placement_id": "PL-6201", "channel_id": "CH-62", "planned_week": "W1", "ran_week": "W1", "placement_status": "ran", "offer_type": "promotional"},
    {"placement_id": "PL-6202", "channel_id": "CH-62", "planned_week": "W2", "ran_week": "W2", "placement_status": "ran", "offer_type": "promotional"},
    {"placement_id": "PL-6203", "channel_id": "CH-62", "planned_week": "W2", "ran_week": "W3", "placement_status": "ran", "offer_type": "promotional"},
]
log_rows.extend(new_placements)
with open(log_path, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=log_fields)
    writer.writeheader()
    writer.writerows(log_rows)
print(f"3. Added {len(new_placements)} placements to placement_log.csv")

# === 4. Add ledger rows to streaming_ledger.csv ===
ledger_path = INPUT / "streaming_ledger.csv"
with open(ledger_path, "r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    ledger_fields = reader.fieldnames
    ledger_rows = list(reader)

new_ledger_rows = [
    # CH-60: 3 rows - 2 real + 1 cross-channel guaranteed (EXCLUDED)
    {"ledger_ref": "L60-1", "channel_id": "CH-60", "campaign_week": "W1", "placement_id": "PL-601", "delivered_reach": "50000", "delivered_streams": "2000"},
    {"ledger_ref": "L60-2", "channel_id": "CH-60", "campaign_week": "W1", "placement_id": "PL-602", "delivered_reach": "40000", "delivered_streams": "1500"},
    {"ledger_ref": "L60-3", "channel_id": "CH-60", "campaign_week": "W1", "placement_id": "PL-GUAR-60", "delivered_reach": "30000", "delivered_streams": "500"},
    # CH-61: 4 rows in W1, W2, W4, W7
    {"ledger_ref": "L61-1", "channel_id": "CH-61", "campaign_week": "W1", "placement_id": "PL-6101", "delivered_reach": "50000", "delivered_streams": "1800"},
    {"ledger_ref": "L61-2", "channel_id": "CH-61", "campaign_week": "W2", "placement_id": "PL-6102", "delivered_reach": "45000", "delivered_streams": "1700"},
    {"ledger_ref": "L61-3", "channel_id": "CH-61", "campaign_week": "W4", "placement_id": "PL-6103", "delivered_reach": "40000", "delivered_streams": "1300"},
    {"ledger_ref": "L61-4", "channel_id": "CH-61", "campaign_week": "W7", "placement_id": "PL-6104", "delivered_reach": "35000", "delivered_streams": "900"},
    # CH-62: 3 rows - PL-6203 ran in W3 (outside window) but ledger row is W2 (inside window)
    {"ledger_ref": "L62-1", "channel_id": "CH-62", "campaign_week": "W1", "placement_id": "PL-6201", "delivered_reach": "50000", "delivered_streams": "1800"},
    {"ledger_ref": "L62-2", "channel_id": "CH-62", "campaign_week": "W2", "placement_id": "PL-6202", "delivered_reach": "45000", "delivered_streams": "1700"},
    {"ledger_ref": "L62-3", "channel_id": "CH-62", "campaign_week": "W2", "placement_id": "PL-6203", "delivered_reach": "40000", "delivered_streams": "1300"},
]
ledger_rows.extend(new_ledger_rows)
with open(ledger_path, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=ledger_fields)
    writer.writeheader()
    writer.writerows(ledger_rows)
print(f"4. Added {len(new_ledger_rows)} ledger rows to streaming_ledger.csv")

# === 5. Compute gold for each channel ===
print("\n5. Computing gold values:")

# CH-60: Cross-channel guaranteed placement
ch60_counted = 2  # PL-601, PL-602 (both ran in W1, in window)
# PL-GUAR-60 is guaranteed_streams → ledger row EXCLUDED per rule 3.2
ch60_reach = 50000 + 40000  # 90000 (excluding guaranteed row)
ch60_streams = 2000 + 1500  # 3500
ch60_target = 2 * 50000 * 40 / 1000  # 4000
ch60_sf_raw = ch60_target - ch60_streams  # 500
ch60_sf = round_half_toward(ch60_sf_raw)  # 500
ch60_pe_raw = (2 - 2) * 50000 * 40 / 1000  # 0
ch60_pe = round_half_away(ch60_pe_raw) if ch60_sf > 0 else round_half_toward(ch60_pe_raw)  # 0
# CE per row: W1 rate 1.0, original rate 40
ch60_ce_expected = 50000*1.0*40/1000 + 40000*1.0*40/1000  # 2000 + 1600 = 3600
ch60_ce_raw = ch60_ce_expected - ch60_streams  # 3600 - 3500 = 100
ch60_ce = round_half_toward(ch60_ce_raw)  # 100
ch60_rr = ch60_sf - ch60_pe - ch60_ce  # 500 - 0 - 100 = 400
print(f"  CH-60: counted={ch60_counted} PE={ch60_pe} CE={ch60_ce} RR={ch60_rr} SF={ch60_sf}")
assert ch60_pe + ch60_ce + ch60_rr == ch60_sf

# CH-61: Multiple amendments
ch61_counted = 4  # All 4 placements ran in window
ch61_reach = 50000 + 45000 + 40000 + 35000  # 170000
ch61_streams = 1800 + 1700 + 1300 + 900  # 5700
ch61_target = 4 * 50000 * 40 / 1000  # 8000
ch61_sf_raw = ch61_target - ch61_streams  # 2300
ch61_sf = round_half_toward(ch61_sf_raw)  # 2300
ch61_pe_raw = (4 - 4) * 50000 * 40 / 1000  # 0
ch61_pe = round_half_away(ch61_pe_raw) if ch61_sf > 0 else round_half_toward(ch61_pe_raw)  # 0
# CE per row with amendments:
# W1: rate 1.0, original rate 40 → 50000*1.0*40/1000 = 2000
# W2: rate 1.0, original rate 40 → 45000*1.0*40/1000 = 1800
# W4: rate 0.9, amended rate 35 (A3) → 40000*0.9*35/1000 = 1260
# W7: rate 0.9, amended rate 25 (A4) → 35000*0.9*25/1000 = 787.5
ch61_ce_expected = 2000 + 1800 + 1260 + 787.5  # 5847.5
ch61_ce_raw = ch61_ce_expected - ch61_streams  # 5847.5 - 5700 = 147.5
ch61_ce = round_half_toward(ch61_ce_raw)  # 147
ch61_rr = ch61_sf - ch61_pe - ch61_ce  # 2300 - 0 - 147 = 2153
print(f"  CH-61: counted={ch61_counted} PE={ch61_pe} CE={ch61_ce} RR={ch61_rr} SF={ch61_sf}")
assert ch61_pe + ch61_ce + ch61_rr == ch61_sf
# If model applies rate 35 to ALL late weeks: CE_w7 = 35000*0.9*35/1000=1102.5 → CE=6162.5-5700=462.5→462 (WRONG)
# If model uses original 40 for all: CE_w4=1440, CE_w7=1260 → CE=6500-5700=800 (WRONG)

# CH-62: Uncounted placement with in-window ledger row
ch62_counted = 2  # PL-6201 (W1), PL-6202 (W2) counted; PL-6203 ran in W3 (OUTSIDE window, NOT counted)
# But ALL 3 ledger rows have campaign_week in window (W1, W2, W2) → all counted per rule 3.1
ch62_reach = 50000 + 45000 + 40000  # 135000 (all 3 ledger rows counted)
ch62_streams = 1800 + 1700 + 1300  # 4800
ch62_target = 3 * 50000 * 40 / 1000  # 6000
ch62_sf_raw = ch62_target - ch62_streams  # 1200
ch62_sf = round_half_toward(ch62_sf_raw)  # 1200
ch62_pe_raw = (3 - 2) * 50000 * 40 / 1000  # 2000
ch62_pe = round_half_away(ch62_pe_raw) if ch62_sf > 0 else round_half_toward(ch62_pe_raw)  # 2000
# CE per row: all W1-W3, rate 1.0, original rate 40
ch62_ce_expected = 50000*1.0*40/1000 + 45000*1.0*40/1000 + 40000*1.0*40/1000  # 2000+1800+1600=5400
ch62_ce_raw = ch62_ce_expected - ch62_streams  # 5400 - 4800 = 600
ch62_ce = round_half_toward(ch62_ce_raw)  # 600
ch62_rr = ch62_sf - ch62_pe - ch62_ce  # 1200 - 2000 - 600 = -1400
print(f"  CH-62: counted={ch62_counted} PE={ch62_pe} CE={ch62_ce} RR={ch62_rr} SF={ch62_sf}")
assert ch62_pe + ch62_ce + ch62_rr == ch62_sf
# If model skips ledger row for uncounted placement PL-6203:
#   reach=95000, streams=3500, SF=2500, CE=300, RR=200 (ALL WRONG)

# === 6. Update shortfall_attribution.csv ===
sa_path = SOL / "shortfall_attribution.csv"
with open(sa_path, "r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    sa_fields = reader.fieldnames
    sa_rows = list(reader)

for ch_id, counted, pe, ce, rr, sf in [
    ("CH-60", ch60_counted, ch60_pe, ch60_ce, ch60_rr, ch60_sf),
    ("CH-61", ch61_counted, ch61_pe, ch61_ce, ch61_rr, ch61_sf),
    ("CH-62", ch62_counted, ch62_pe, ch62_ce, ch62_rr, ch62_sf),
]:
    sa_rows.append({
        "channel_id": ch_id,
        "counted_placements": str(counted),
        "placements_effect_streams": str(pe),
        "conversion_effect_streams": str(ce),
        "residual_reach_effect_streams": str(rr),
        "shortfall_to_target_streams": str(sf),
    })
with open(sa_path, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=sa_fields)
    writer.writeheader()
    writer.writerows(sa_rows)
print(f"6. Added 3 rows to shortfall_attribution.csv ({len(sa_rows)} total)")

# === 7. Update results.json ===
results_path = SOL / "results.json"
results = json.loads(results_path.read_text(encoding="utf-8"))
results["counted_placement_count"] += ch60_counted + ch61_counted + ch62_counted
results["placements_effect_streams"] += ch60_pe + ch61_pe + ch62_pe
results["conversion_effect_streams"] += ch60_ce + ch61_ce + ch62_ce
results["residual_reach_effect_streams"] += ch60_rr + ch61_rr + ch62_rr
results["shortfall_to_target_streams"] += ch60_sf + ch61_sf + ch62_sf
results_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
print(f"7. Updated results.json: {results}")

# Verify additivity
assert results["placements_effect_streams"] + results["conversion_effect_streams"] + results["residual_reach_effect_streams"] == results["shortfall_to_target_streams"]

# === 8. Update campaign_review.md ===
memo_path = SOL / "campaign_review.md"
memo = memo_path.read_text(encoding="utf-8")
memo = memo.replace("Counted placements: 128", f"Counted placements: {results['counted_placement_count']}")
memo = memo.replace("Conversion effect: 31024", f"Conversion effect: {results['conversion_effect_streams']}")
memo_path.write_text(memo, encoding="utf-8")
print(f"8. Updated campaign_review.md")

# === 9. Update verifier.json ===
verifier_path = TESTS / "verifier.json"
spec = json.loads(verifier_path.read_text(encoding="utf-8"))

for v in spec["verifiers"]:
    if v["name"] == "register_table":
        for ch_id, counted, pe, ce, rr, sf in [
            ("CH-60", ch60_counted, ch60_pe, ch60_ce, ch60_rr, ch60_sf),
            ("CH-61", ch61_counted, ch61_pe, ch61_ce, ch61_rr, ch61_sf),
            ("CH-62", ch62_counted, ch62_pe, ch62_ce, ch62_rr, ch62_sf),
        ]:
            v["assertion"]["expected"]["rows"][ch_id] = {
                "counted_placements": str(counted),
                "placements_effect_streams": str(pe),
                "conversion_effect_streams": str(ce),
                "residual_reach_effect_streams": str(rr),
                "shortfall_to_target_streams": str(sf),
            }
            v["assertion"]["expected"]["row_set"].append(ch_id)

    if v["name"] == "results_figures":
        v["assertion"]["expected"]["keys"]["counted_placement_count"]["value"] = results["counted_placement_count"]
        v["assertion"]["expected"]["keys"]["placements_effect_streams"]["value"] = results["placements_effect_streams"]
        v["assertion"]["expected"]["keys"]["conversion_effect_streams"]["value"] = results["conversion_effect_streams"]
        v["assertion"]["expected"]["keys"]["residual_reach_effect_streams"]["value"] = results["residual_reach_effect_streams"]
        v["assertion"]["expected"]["keys"]["shortfall_to_target_streams"]["value"] = results["shortfall_to_target_streams"]

    # Update memo figure checks
    if v["name"] in ("memo_conversion_effect", "memo_conversion_effect_exactly_one"):
        old_fig = "31024"
        new_fig = str(results["conversion_effect_streams"])
        v["assertion"]["expected"] = v["assertion"]["expected"].replace(old_fig, new_fig)
        old_fig_c = f"{int(old_fig):,}"
        new_fig_c = f"{int(new_fig):,}"
        v["assertion"]["expected"] = v["assertion"]["expected"].replace(old_fig_c, new_fig_c)

    if v["name"] in ("memo_counted_placements", "memo_counted_placements_exactly_one"):
        old_fig = "128"
        new_fig = str(results["counted_placement_count"])
        v["assertion"]["expected"] = v["assertion"]["expected"].replace(old_fig, new_fig)
        old_fig_c = f"{int(old_fig):,}"
        new_fig_c = f"{int(new_fig):,}"
        v["assertion"]["expected"] = v["assertion"]["expected"].replace(old_fig_c, new_fig_c)

verifier_path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
print(f"9. Updated verifier.json")

# === 10. Update golden_trajectory.json ===
traj_path = ROOT / "solution" / "golden_trajectory.json"
traj = json.loads(traj_path.read_text(encoding="utf-8"))
for step in traj:
    cmd = str(step.get("arguments", {}).get("command", ""))
    if "results.json" in cmd and "counted_placement_count" in cmd:
        for old_val, new_val in [("128", str(results["counted_placement_count"])),
                                  ("31699", str(results["placements_effect_streams"])),
                                  ("31024", str(results["conversion_effect_streams"])),
                                  ("50941", str(results["residual_reach_effect_streams"])),
                                  ("113664", str(results["shortfall_to_target_streams"]))]:
            cmd = cmd.replace(f'"counted_placement_count": {old_val}', f'"counted_placement_count": {new_val}')
            cmd = cmd.replace(f'"placements_effect_streams": {old_val}', f'"placements_effect_streams": {new_val}')
            cmd = cmd.replace(f'"conversion_effect_streams": {old_val}', f'"conversion_effect_streams": {new_val}')
            cmd = cmd.replace(f'"residual_reach_effect_streams": {old_val}', f'"residual_reach_effect_streams": {new_val}')
            cmd = cmd.replace(f'"shortfall_to_target_streams": {old_val}', f'"shortfall_to_target_streams": {new_val}')
        step["arguments"]["command"] = cmd

    if "shortfall_attribution.csv" in cmd and "channel_id" in cmd:
        new_rows = ""
        for ch_id, counted, pe, ce, rr, sf in [
            ("CH-60", ch60_counted, ch60_pe, ch60_ce, ch60_rr, ch60_sf),
            ("CH-61", ch61_counted, ch61_pe, ch61_ce, ch61_rr, ch61_sf),
            ("CH-62", ch62_counted, ch62_pe, ch62_ce, ch62_rr, ch62_sf),
        ]:
            new_rows += f"\n{ch_id},{counted},{pe},{ce},{rr},{sf}"
        for term in ["SHORTFALLATTRIBUTIONEOF", "EOF"]:
            if term in cmd:
                cmd = cmd.replace(term, new_rows + "\n" + term)
                break
        step["arguments"]["command"] = cmd

    if "campaign_review.md" in cmd and "Counted placements" in cmd:
        cmd = cmd.replace("Counted placements: 128", f"Counted placements: {results['counted_placement_count']}")
        cmd = cmd.replace("Conversion effect: 31024", f"Conversion effect: {results['conversion_effect_streams']}")
        step["arguments"]["command"] = cmd

traj_path.write_text(json.dumps(traj, indent=2) + "\n", encoding="utf-8")
print(f"10. Updated golden_trajectory.json")

# === 11. Update review.csv ===
review_path = ROOT / "review.csv"
review = review_path.read_text(encoding="utf-8")
review = review.replace("128 counted placements", f"{results['counted_placement_count']} counted placements")
review = review.replace("PE=31699", f"PE={results['placements_effect_streams']}")
review = review.replace("CE=31024", f"CE={results['conversion_effect_streams']}")
review = review.replace("RE=50941", f"RE={results['residual_reach_effect_streams']}")
review = review.replace("SF=113664", f"SF={results['shortfall_to_target_streams']}")
review = review.replace("55 channels", "58 channels")
review = review.replace("55-channel", "58-channel")
review = review.replace("55-row", "58-row")
review = review.replace("55-id", "58-id")
review_path.write_text(review, encoding="utf-8")
print(f"11. Updated review.csv")

# === 12. Convert ALL files to LF ===
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

print(f"\nDone! v18 traps added:")
print(f"  CH-60: Cross-channel guaranteed placement (trips per-channel lookup)")
print(f"  CH-61: Multiple amendments rate 35→25 (trips single-amendment scripts)")
print(f"  CH-62: Uncounted placement + in-window ledger (trips coupled counting)")
print(f"\nNew totals: counted={results['counted_placement_count']} PE={results['placements_effect_streams']} CE={results['conversion_effect_streams']} RR={results['residual_reach_effect_streams']} SF={results['shortfall_to_target_streams']}")
