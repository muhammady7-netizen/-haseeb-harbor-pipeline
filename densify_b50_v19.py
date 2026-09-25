"""Densify bus-b50 v19: Rounding traps that exploit Python's banker's rounding.

Python 3's round() uses banker's rounding (round half to EVEN).
The task requires:
  - PE: halves AWAY from zero when SF>0, TOWARD zero when SF<0 (rule 5.7)
  - CE: halves TOWARD zero always (rule 5.4)
  - SF: halves TOWARD zero always (rule 5.5)

When the raw value is X.5:
  - If X is EVEN: Python round(X.5) = X (stays), but away-from-zero = X+1 -> MISMATCH
  - If X is ODD: Python round(X.5) = X+1 (goes up), but toward-zero = X -> MISMATCH

12 new channels:
  CH-63..66: PE=X.5 (X even, SF>0) -> PE should be X+1, Python gives X. CE also trapped.
  CH-67..70: PE=X.5 (X odd, SF<0) -> PE should be X, Python gives X+1. CE also trapped.
  CH-71..74: W4 ledger (0.9 rate), CE=Y.5 (Y odd) -> CE should be Y, Python gives Y+1.
"""
import json, csv, os
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_DOWN

ROOT = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\task-sources\bus-b50")
INPUT = ROOT / "environment" / "input"
SOL = ROOT / "solution" / "files"
TESTS = ROOT / "tests"

def r_away(x):
    d = Decimal(str(x))
    if d >= 0: return int(d.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    return int(d.quantize(Decimal('1'), rounding=ROUND_HALF_DOWN))

def r_toward(x):
    d = Decimal(str(x))
    return int(d.quantize(Decimal('1'), rounding=ROUND_HALF_DOWN))

# Channel designs: (ch_id, rate, reach, planned_pl, counted_pl, streams, week, target)
# target = planned_pl * reach * rate / 1000
# SF = target - streams  (rounded toward zero)
# PE_raw = (planned_pl - counted_pl) * reach * rate / 1000
# CE_expected = reach * time_rate * rate / 1000  (time_rate=1.0 for W1, 0.9 for W4)
# CE_raw = CE_expected - streams
# RR = SF - PE - CE

channels = []

# PE+CE traps: positive SF, PE=X.5 (X even), CE=Y.5 (Y odd)
for i, (ch_id, rate, streams) in enumerate([
    ("CH-63", 49, 121),  # PE=122.5->123, CE=1.5->1
    ("CH-64", 53, 131),  # PE=132.5->133, CE=1.5->1
    ("CH-65", 57, 141),  # PE=142.5->143, CE=1.5->1
    ("CH-66", 61, 151),  # PE=152.5->153, CE=1.5->1
]):
    reach = 2500
    planned = 2
    counted = 1  # one placement ran in W3 (outside window)
    target = planned * reach * rate / 1000  # whole number
    sf_raw = target - streams
    sf = r_toward(sf_raw)
    pe_raw = (planned - counted) * reach * rate / 1000  # X.5
    pe = r_away(pe_raw) if sf > 0 else r_toward(pe_raw)
    ce_exp = reach * 1.0 * rate / 1000  # same as pe_raw
    ce_raw = ce_exp - streams
    ce = r_toward(ce_raw)
    rr = sf - pe - ce
    channels.append((ch_id, rate, reach, planned, counted, streams, "W1", target, sf, pe, ce, rr))
    print(f"{ch_id}: target={target} SF={sf} PE={pe} (raw={pe_raw}) CE={ce} (raw={ce_raw}) RR={rr}")
    assert pe + ce + rr == sf

# PE+CE traps: negative SF, PE=X.5 (X odd), CE=-Y.5 (Y odd)
for i, (ch_id, rate, streams) in enumerate([
    ("CH-67", 51, 301),  # PE=127.5->127, CE=-173.5->-173
    ("CH-68", 55, 301),  # PE=137.5->137, CE=-163.5->-163
    ("CH-69", 59, 301),  # PE=147.5->147, CE=-153.5->-153
    ("CH-70", 63, 321),  # PE=157.5->157, CE=-163.5->-163
]):
    reach = 2500
    planned = 2
    counted = 1
    target = planned * reach * rate / 1000
    sf_raw = target - streams
    sf = r_toward(sf_raw)
    pe_raw = (planned - counted) * reach * rate / 1000
    pe = r_away(pe_raw) if sf > 0 else r_toward(pe_raw)
    ce_exp = reach * 1.0 * rate / 1000
    ce_raw = ce_exp - streams
    ce = r_toward(ce_raw)
    rr = sf - pe - ce
    channels.append((ch_id, rate, reach, planned, counted, streams, "W1", target, sf, pe, ce, rr))
    print(f"{ch_id}: target={target} SF={sf} PE={pe} (raw={pe_raw}) CE={ce} (raw={ce_raw}) RR={rr}")
    assert pe + ce + rr == sf

# W4 CE traps: 0.9 time rate + CE=Y.5 (Y odd), PE=0
for i, (ch_id, streams) in enumerate([
    ("CH-71", 111),  # CE=1.5->1
    ("CH-72", 109),  # CE=3.5->3
    ("CH-73", 107),  # CE=5.5->5
    ("CH-74", 105),  # CE=7.5->7
]):
    rate = 50
    reach = 2500
    planned = 1
    counted = 1  # all in window (W4 is in_campaign_window=yes)
    target = planned * reach * rate / 1000  # 125
    sf_raw = target - streams
    sf = r_toward(sf_raw)
    pe_raw = 0  # all counted
    pe = 0
    ce_exp = reach * 0.9 * rate / 1000  # 112.5
    ce_raw = ce_exp - streams
    ce = r_toward(ce_raw)
    rr = sf - pe - ce
    channels.append((ch_id, rate, reach, planned, counted, streams, "W4", target, sf, pe, ce, rr))
    print(f"{ch_id}: target={target} SF={sf} PE={pe} CE={ce} (raw={ce_raw}) RR={rr}")
    assert pe + ce + rr == sf

print(f"\nTotal new channels: {len(channels)}")

# === 1. Add channels to channel_plan.csv ===
plan_path = INPUT / "channel_plan.csv"
with open(plan_path, "r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    plan_fields = reader.fieldnames
    plan_rows = list(reader)

for ch_id, rate, reach, planned, counted, streams, week, target, sf, pe, ce, rr in channels:
    plan_rows.append({
        "channel_id": ch_id,
        "channel_name": f"Rounding trap {ch_id}",
        "planned_placements": str(planned),
        "planned_reach_per_placement": str(reach),
        "planned_streams_per_1000_reach": str(rate),
    })
with open(plan_path, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=plan_fields)
    writer.writeheader()
    writer.writerows(plan_rows)
print(f"1. Added {len(channels)} channels to channel_plan.csv ({len(plan_rows)} total)")

# === 2. Add placements to placement_log.csv ===
log_path = INPUT / "placement_log.csv"
with open(log_path, "r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    log_fields = reader.fieldnames
    log_rows = list(reader)

pl_counter = 80000
for ch_id, rate, reach, planned, counted, streams, week, target, sf, pe, ce, rr in channels:
    # Add counted placements (in window)
    for j in range(counted):
        pl_counter += 1
        log_rows.append({
            "placement_id": f"PL-{pl_counter}",
            "channel_id": ch_id,
            "planned_week": week,
            "ran_week": week,
            "placement_status": "ran",
            "offer_type": "promotional",
        })
    # Add uncounted placement (ran in W3, outside window)
    if planned > counted:
        pl_counter += 1
        log_rows.append({
            "placement_id": f"PL-{pl_counter}",
            "channel_id": ch_id,
            "planned_week": week,
            "ran_week": "W3",
            "placement_status": "ran",
            "offer_type": "promotional",
        })

with open(log_path, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=log_fields)
    writer.writeheader()
    writer.writerows(log_rows)
print(f"2. Added placements to placement_log.csv")

# === 3. Add ledger rows to streaming_ledger.csv ===
ledger_path = INPUT / "streaming_ledger.csv"
with open(ledger_path, "r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    ledger_fields = reader.fieldnames
    ledger_rows = list(reader)

l_counter = 80000
for ch_id, rate, reach, planned, counted, streams, week, target, sf, pe, ce, rr in channels:
    l_counter += 1
    # Find the first placement_id for this channel
    pid = None
    for p in log_rows:
        if p["channel_id"] == ch_id and p["ran_week"] == week:
            pid = p["placement_id"]
            break
    ledger_rows.append({
        "ledger_ref": f"L{l_counter}",
        "channel_id": ch_id,
        "campaign_week": week,
        "placement_id": pid or "",
        "delivered_reach": str(reach),
        "delivered_streams": str(streams),
    })

with open(ledger_path, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=ledger_fields)
    writer.writeheader()
    writer.writerows(ledger_rows)
print(f"3. Added ledger rows to streaming_ledger.csv")

# === 4. Update shortfall_attribution.csv ===
sa_path = SOL / "shortfall_attribution.csv"
with open(sa_path, "r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    sa_fields = reader.fieldnames
    sa_rows = list(reader)

total_counted = 0
total_pe = 0
total_ce = 0
total_rr = 0
total_sf = 0

for ch_id, rate, reach, planned, counted, streams, week, target, sf, pe, ce, rr in channels:
    sa_rows.append({
        "channel_id": ch_id,
        "counted_placements": str(counted),
        "placements_effect_streams": str(pe),
        "conversion_effect_streams": str(ce),
        "residual_reach_effect_streams": str(rr),
        "shortfall_to_target_streams": str(sf),
    })
    total_counted += counted
    total_pe += pe
    total_ce += ce
    total_rr += rr
    total_sf += sf

with open(sa_path, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=sa_fields)
    writer.writeheader()
    writer.writerows(sa_rows)
print(f"4. Added {len(channels)} rows to shortfall_attribution.csv ({len(sa_rows)} total)")

# === 5. Update results.json ===
results_path = SOL / "results.json"
results = json.loads(results_path.read_text(encoding="utf-8"))
results["counted_placement_count"] += total_counted
results["placements_effect_streams"] += total_pe
results["conversion_effect_streams"] += total_ce
results["residual_reach_effect_streams"] += total_rr
results["shortfall_to_target_streams"] += total_sf
results_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
print(f"5. Updated results.json: {results}")
assert results["placements_effect_streams"] + results["conversion_effect_streams"] + results["residual_reach_effect_streams"] == results["shortfall_to_target_streams"]

# === 6. Update campaign_review.md ===
memo_path = SOL / "campaign_review.md"
memo = memo_path.read_text(encoding="utf-8")
# Replace any figure that matches the old values
for old, new in [
    ("Counted placements: 136", f"Counted placements: {results['counted_placement_count']}"),
    ("Conversion effect: 31871", f"Conversion effect: {results['conversion_effect_streams']}"),
]:
    memo = memo.replace(old, new)
memo_path.write_text(memo, encoding="utf-8")
print(f"6. Updated campaign_review.md")

# === 7. Update verifier.json ===
verifier_path = TESTS / "verifier.json"
spec = json.loads(verifier_path.read_text(encoding="utf-8"))

for v in spec["verifiers"]:
    if v["name"] == "register_table":
        for ch_id, rate, reach, planned, counted, streams, week, target, sf, pe, ce, rr in channels:
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
        old_fig = "31871"
        new_fig = str(results["conversion_effect_streams"])
        v["assertion"]["expected"] = v["assertion"]["expected"].replace(old_fig, new_fig)
        old_fig_c = f"{int(old_fig):,}"
        new_fig_c = f"{int(new_fig):,}"
        v["assertion"]["expected"] = v["assertion"]["expected"].replace(old_fig_c, new_fig_c)

    if v["name"] in ("memo_counted_placements", "memo_counted_placements_exactly_one"):
        old_fig = "136"
        new_fig = str(results["counted_placement_count"])
        v["assertion"]["expected"] = v["assertion"]["expected"].replace(old_fig, new_fig)
        old_fig_c = f"{int(old_fig):,}"
        new_fig_c = f"{int(new_fig):,}"
        v["assertion"]["expected"] = v["assertion"]["expected"].replace(old_fig_c, new_fig_c)

verifier_path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
print(f"7. Updated verifier.json")

# === 8. Update golden_trajectory.json ===
traj_path = ROOT / "solution" / "golden_trajectory.json"
traj = json.loads(traj_path.read_text(encoding="utf-8"))
for step in traj:
    cmd = str(step.get("arguments", {}).get("command", ""))
    if "results.json" in cmd and "counted_placement_count" in cmd:
        for old_val in ["136", "33699", "31871", "52094", "117664"]:
            new_val_map = {
                "136": str(results["counted_placement_count"]),
                "33699": str(results["placements_effect_streams"]),
                "31871": str(results["conversion_effect_streams"]),
                "52094": str(results["residual_reach_effect_streams"]),
                "117664": str(results["shortfall_to_target_streams"]),
            }
            if old_val in new_val_map:
                cmd = cmd.replace(f'"counted_placement_count": {old_val}', f'"counted_placement_count": {new_val_map[old_val]}')
                cmd = cmd.replace(f'"placements_effect_streams": {old_val}', f'"placements_effect_streams": {new_val_map[old_val]}')
                cmd = cmd.replace(f'"conversion_effect_streams": {old_val}', f'"conversion_effect_streams": {new_val_map[old_val]}')
                cmd = cmd.replace(f'"residual_reach_effect_streams": {old_val}', f'"residual_reach_effect_streams": {new_val_map[old_val]}')
                cmd = cmd.replace(f'"shortfall_to_target_streams": {old_val}', f'"shortfall_to_target_streams": {new_val_map[old_val]}')
        step["arguments"]["command"] = cmd

    if "shortfall_attribution.csv" in cmd and "channel_id" in cmd:
        new_rows = ""
        for ch_id, rate, reach, planned, counted, streams, week, target, sf, pe, ce, rr in channels:
            new_rows += f"\n{ch_id},{counted},{pe},{ce},{rr},{sf}"
        for term in ["SHORTFALLATTRIBUTIONEOF", "EOF"]:
            if term in cmd:
                cmd = cmd.replace(term, new_rows + "\n" + term)
                break
        step["arguments"]["command"] = cmd

    if "campaign_review.md" in cmd and "Counted placements" in cmd:
        cmd = cmd.replace("Counted placements: 136", f"Counted placements: {results['counted_placement_count']}")
        cmd = cmd.replace("Conversion effect: 31871", f"Conversion effect: {results['conversion_effect_streams']}")
        step["arguments"]["command"] = cmd

traj_path.write_text(json.dumps(traj, indent=2) + "\n", encoding="utf-8")
print(f"8. Updated golden_trajectory.json")

# === 9. Update review.csv ===
review_path = ROOT / "review.csv"
review = review_path.read_text(encoding="utf-8")
review = review.replace("136 counted placements", f"{results['counted_placement_count']} counted placements")
review = review.replace("PE=33699", f"PE={results['placements_effect_streams']}")
review = review.replace("CE=31871", f"CE={results['conversion_effect_streams']}")
review = review.replace("RE=52094", f"RE={results['residual_reach_effect_streams']}")
review = review.replace("SF=117664", f"SF={results['shortfall_to_target_streams']}")
review = review.replace("58 channels", "70 channels")
review = review.replace("58-channel", "70-channel")
review = review.replace("58-row", "70-row")
review = review.replace("58-id", "70-id")
review_path.write_text(review, encoding="utf-8")
print(f"9. Updated review.csv")

# === 10. Convert ALL files to LF ===
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
print(f"10. Converted {fixed} files to LF")

print(f"\nDone! v19 rounding traps added:")
print(f"  12 new channels with .5 rounding traps")
print(f"  Python round() gives WRONG answer on ALL of them")
print(f"  Only correct conditional rounding (away for PE+pos SF, toward for CE) works")
print(f"\nNew totals: counted={results['counted_placement_count']} PE={results['placements_effect_streams']} CE={results['conversion_effect_streams']} RR={results['residual_reach_effect_streams']} SF={results['shortfall_to_target_streams']}")
