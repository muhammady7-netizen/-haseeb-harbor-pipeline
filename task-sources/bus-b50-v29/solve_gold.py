#!/usr/bin/env python3
"""
Solver for bus-b50 — computes gold deliverables from input files.
Implements the full attribution method from attribution_note.md.
"""

import csv
import json
import re
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_DOWN
from collections import defaultdict

ROOT = Path(__file__).parent / "environment" / "input"
OUT = Path(__file__).parent / "solution" / "files"

def read_csv(name):
    with (ROOT / name).open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def parse_amendments(note_text):
    """Parse retroactive amendments from attribution_note.md."""
    amendments = {}  # channel_id -> amended_rate
    # Split into amendment blocks
    blocks = re.split(r"(?=\*\*A\d+\*\*)", note_text)
    for block in blocks:
        if not block.strip().startswith("**A"):
            continue
        # Extract channel
        ch_match = re.search(r"For\s+(CH-\d+)", block)
        if not ch_match:
            continue
        ch = ch_match.group(1)
        # Find all "amended to X" and "then to Y" in this block
        rates = re.findall(r"amended\s+to\s+(\d+)|then\s+to\s+(\d+)", block)
        # rates is a list of tuples: [('35', ''), ('', '25')]
        all_rates = []
        for r in rates:
            if r[0]:
                all_rates.append(int(r[0]))
            if r[1]:
                all_rates.append(int(r[1]))
        if all_rates:
            amendments[ch] = all_rates[-1]  # Take the last (latest) amendment
    return amendments

def is_in_campaign_window(week, calendar):
    for row in calendar:
        if row["campaign_week"] == week:
            return row["in_campaign_window"].strip().lower() == "yes"
    return False

def compute_channel_values(channel_id, plan_rows, ledger_rows, placement_rows, calendar, amendments):
    """Compute gold values for one channel."""
    plan = next((r for r in plan_rows if r["channel_id"] == channel_id), None)
    if not plan:
        return None
    
    planned_placements = int(plan["planned_placements"])
    planned_reach = int(plan["planned_reach_per_placement"])
    original_rate = int(plan["planned_streams_per_1000_reach"])
    
    # Amended rate (if any)
    amended_rate = amendments.get(channel_id, original_rate)
    
    # Count placements
    ch_placements = [p for p in placement_rows if p["channel_id"] == channel_id]
    counted_placements = 0
    for p in ch_placements:
        if p["placement_status"].strip() == "cancelled":
            continue
        if p["offer_type"].strip() == "guaranteed_streams":
            continue
        ran_week = p["ran_week"].strip()
        if not ran_week:
            continue
        if not is_in_campaign_window(ran_week, calendar):
            continue
        counted_placements += 1
    
    # Get ledger rows for this channel
    ch_ledger = [r for r in ledger_rows if r["channel_id"] == channel_id]
    
    # Filter ledger rows: in campaign window, not guaranteed_streams
    # Need to check placement_log for offer_type
    placement_by_id = {p["placement_id"]: p for p in placement_rows}
    
    delivered_reach = 0
    delivered_streams = 0
    conversion_contributions = []  # per-row contributions for conversion effect
    
    for row in ch_ledger:
        week = row["campaign_week"].strip()
        if not is_in_campaign_window(week, calendar):
            continue
        
        placement_id = row.get("placement_id", "").strip()
        
        # Check if this placement is guaranteed_streams
        if placement_id and placement_id in placement_by_id:
            p = placement_by_id[placement_id]
            if p["offer_type"].strip() == "guaranteed_streams":
                continue
        
        # Per-row rounding (rule 3.5)
        reach_val = float(row["delivered_reach"])
        streams_val = float(row["delivered_streams"])
        
        # Round to nearest whole, halves away from zero
        reach_rounded = int(Decimal(str(reach_val)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        streams_rounded = int(Decimal(str(streams_val)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        
        # Handle negative streams (rule 3.4)
        if streams_val < 0:
            streams_rounded = int(Decimal(str(abs(streams_val))).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
            streams_rounded = -streams_rounded
            reach_rounded = int(Decimal(str(abs(reach_val))).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
            # Negative streams still count reach? Let me check...
            # Rule 3.4: "A ledger row carrying negative streams is a platform correction and is counted as it stands, sign included."
            # So reach is still counted normally, only streams are negative
        
        delivered_reach += reach_rounded
        delivered_streams += streams_rounded
        
        # Conversion effect contribution (rule 5.6, 5.8)
        rate = amended_rate  # Use amended rate for conversion effect (rule 7.4)
        # Time-dependent rate (rule 5.6): W1-W3 full rate, W4-W7 90%
        if week in ("W1", "W2", "W3"):
            time_rate = 1.0
        else:
            time_rate = 0.9
        
        # Per-row contribution: delivered_reach * rate * planned_streams_per_1000_reach / 1000
        # Using amended_rate for conversion effect
        contribution = reach_rounded * time_rate * amended_rate / 1000
        conversion_contributions.append(contribution)
    
    # Target (rule 4.1)
    target = planned_placements * planned_reach * original_rate / 1000
    
    # Shortfall (rule 4.2)
    shortfall = target - delivered_streams
    
    # Placements effect (rule 5.1) - uses ORIGINAL rate
    placements_effect_raw = (planned_placements - counted_placements) * planned_reach * original_rate / 1000
    
    # Conversion effect (rule 5.2, 5.8) - uses AMENDED rate
    # Sum of per-row contributions less delivered streams
    conversion_effect_raw = sum(conversion_contributions) - delivered_streams
    
    # Residual (rule 5.3)
    residual_raw = shortfall - placements_effect_raw - conversion_effect_raw
    
    # Rounding (rule 5.4, 5.7)
    # Placements effect: halves away from zero when shortfall positive, toward zero when negative
    if shortfall >= 0:
        placements_effect = int(Decimal(str(placements_effect_raw)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    else:
        placements_effect = int(Decimal(str(placements_effect_raw)).quantize(Decimal("1"), rounding=ROUND_HALF_DOWN))
    
    # Conversion effect: always halves toward zero
    conversion_effect = int(Decimal(str(conversion_effect_raw)).quantize(Decimal("1"), rounding=ROUND_HALF_DOWN))
    
    # Residual is the balance
    residual = int(shortfall - placements_effect - conversion_effect)
    
    return {
        "channel_id": channel_id,
        "counted_placements": counted_placements,
        "placements_effect_streams": placements_effect,
        "conversion_effect_streams": conversion_effect,
        "residual_reach_effect_streams": residual,
        "shortfall_to_target_streams": int(shortfall),
    }

def main():
    plan_rows = read_csv("channel_plan.csv")
    ledger_rows = read_csv("streaming_ledger.csv")
    placement_rows = read_csv("placement_log.csv")
    calendar = read_csv("campaign_calendar.csv")
    
    note_text = (ROOT / "attribution_note.md").read_text(encoding="utf-8")
    amendments = parse_amendments(note_text)
    print(f"Amendments: {amendments}")
    
    # Compute all channels
    results = []
    for plan in plan_rows:
        ch = plan["channel_id"]
        val = compute_channel_values(ch, plan_rows, ledger_rows, placement_rows, calendar, amendments)
        if val:
            results.append(val)
            print(f"  {ch}: cp={val['counted_placements']}, pe={val['placements_effect_streams']}, ce={val['conversion_effect_streams']}, re={val['residual_reach_effect_streams']}, st={val['shortfall_to_target_streams']}")
    
    # Write shortfall_attribution.csv
    header = "channel_id,counted_placements,placements_effect_streams,conversion_effect_streams,residual_reach_effect_streams,shortfall_to_target_streams"
    lines = [header]
    for r in results:
        lines.append(f"{r['channel_id']},{r['counted_placements']},{r['placements_effect_streams']},{r['conversion_effect_streams']},{r['residual_reach_effect_streams']},{r['shortfall_to_target_streams']}")
    
    csv_path = OUT / "shortfall_attribution.csv"
    csv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nWrote {csv_path}")
    
    # Compute results.json
    total_cp = sum(r["counted_placements"] for r in results)
    total_pe = sum(r["placements_effect_streams"] for r in results)
    total_ce = sum(r["conversion_effect_streams"] for r in results)
    total_re = sum(r["residual_reach_effect_streams"] for r in results)
    total_st = sum(r["shortfall_to_target_streams"] for r in results)
    
    results_json = {
        "counted_placement_count": total_cp,
        "placements_effect_streams": total_pe,
        "conversion_effect_streams": total_ce,
        "residual_reach_effect_streams": total_re,
        "shortfall_to_target_streams": total_st,
    }
    
    json_path = OUT / "results.json"
    json_path.write_text(json.dumps(results_json, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {json_path}")
    print(f"Totals: cp={total_cp}, pe={total_pe}, ce={total_ce}, re={total_re}, st={total_st}")
    
    # Check if parts add up
    for r in results:
        check = r["placements_effect_streams"] + r["conversion_effect_streams"] + r["residual_reach_effect_streams"]
        if check != r["shortfall_to_target_streams"]:
            print(f"  WARNING: {r['channel_id']} parts {check} != shortfall {r['shortfall_to_target_streams']}")

if __name__ == "__main__":
    main()
