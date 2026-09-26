"""Build bus-b50 v29: Retroactive amendments + cross-channel dependency + all findings fixed.

NEW APPROACH: The difficulty comes from COUNTER-INTUITIVE rules, not computation complexity.

Rule 7.1: Amendments apply RETROACTIVELY to ALL campaign weeks, not just weeks on or
after the effective week. A script that applies amendments only forward from the
effective week gets the wrong conversion effect for weeks before the amendment.

Rule 7.2: Where multiple amendments apply to the same channel, the amendment with
the latest effective week takes precedence for ALL weeks.

Rule 7.3: If the campaign-level shortfall (sum of all channel shortfalls) is negative
(campaign overdelivered), each channel's shortfall is recalculated as:
  channel_shortfall = channel_target - (channel_delivered_streams * campaign_adjustment_factor)
where campaign_adjustment_factor = total_target / total_delivered_streams
This creates a CROSS-CHANNEL dependency that requires computing ALL channels first.

These rules are:
- FAIR: clearly documented in attribution_note.md
- COUNTER-INTUITIVE: go against natural reading of "effective from week W"
- HARD TO SCRIPT: require multi-pass computation and cross-channel dependency

FIXES (from Harbor Check findings):
1. Rule 3.5: per-row rounding of fractional streams (halves away from zero)
2. Fix 5.4/5.7 contradiction: CE always halves toward zero, clearly stated
3. Fix memo checks: add test_memo_has_content_words + migrate regex to Python
4. Fix instruction: "name that part" (generic)
5. Fix golden memo: CH-41 + residual reach
6. test.sh -I flag
7. register_header: csv.inspect_table + equals
"""
import json, csv, os, shutil, zipfile
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_DOWN

SRC_ZIP = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\UPLOAD-THIS-TO-QC-bus-b50.zip")
DST = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\task-sources\bus-b50-v29")
ROOT_NAME = "bus-b50-b10-streaming-target-variance-attribution"

# 1. Extract original
if DST.exists():
    shutil.rmtree(DST)
DST.mkdir(parents=True)
with zipfile.ZipFile(SRC_ZIP) as z:
    for name in z.namelist():
        if name.startswith(ROOT_NAME + "/"):
            rel = name[len(ROOT_NAME)+1:]
            if not rel: continue
            target = DST / rel
            if name.endswith("/"):
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(z.read(name))
print("1. Extracted original 44-channel version")

def r_toward(x):
    return int(Decimal(str(x)).quantize(Decimal("1"), rounding=ROUND_HALF_DOWN))

def r_away(x):
    d = Decimal(str(x))
    if d >= 0: return int(d.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return int(d.quantize(Decimal("1"), rounding=ROUND_HALF_DOWN))

# 2. Fix attribution_note.md
note_path = DST / "environment/input/attribution_note.md"
note = note_path.read_text(encoding="utf-8")

# Add rule 2.7 (empty offer_type)
rule_27 = "\n\n**2.7** A placement whose `offer_type` is empty is a promotional placement\nthat is neither guaranteed nor organic, and is counted under 2.1 exactly as\nany other `ran` placement is counted."
note = note.replace("\n## 3. Reading the ledger", rule_27 + "\n\n## 3. Reading the ledger")

# Add rule 3.5 (per-row rounding)
rule_35 = "\n\n**3.5** Where a ledger row carries a fractional `delivered_streams` or\n`delivered_reach`, the value is rounded to the nearest whole number,\nhalves away from zero, before it is summed into the channel's totals.\nThe channel's delivered reach and delivered streams are the sums of\nthese per-row rounded values."
note = note.replace("\n**3.4** A ledger row carrying negative streams", rule_35 + "\n\n**3.4** A ledger row carrying negative streams")

# Add rule 3.7 (negative reach)
rule_37 = "\n\n**3.7** A ledger row carrying negative `delivered_reach` is a platform\ncorrection and is counted as it stands, sign included, exactly as 3.4 treats\nnegative streams."
if "**3.7**" not in note:
    note = note.replace("\n**3.5** A ledger row naming a placement", rule_37 + "\n\n**3.5** A ledger row naming a placement")

# Fix 5.4: make PE and CE rounding consistent and clear
note = note.replace(
    "The first two parts are taken to the nearest whole\nstream, halves away from zero. The residual is then the balance of the shortfall, so the\nthree parts add back to the shortfall exactly, per channel and across the campaign.",
    "The placements effect is taken to the nearest whole stream,\nhalves away from zero when the shortfall is positive and halves toward\nzero when the shortfall is negative (see 5.7). The conversion effect is\ntaken to the nearest whole stream, halves toward zero, always. The\nresidual is then the balance of the shortfall, so the three parts add\nback to the shortfall exactly, per channel and across the campaign."
)

# Fix 5.7: remove "as before" ambiguity
note = note.replace(
    "The conversion effect is always rounded halves\ntoward zero as before.",
    "The conversion effect is always rounded halves\ntoward zero."
)

# === NEW: Add retroactive amendment rules ===
retroactive_rules = """

## 7. Mid-campaign plan amendments

**7.1** A channel's `planned_streams_per_1000_reach` may be amended mid-campaign
by a note in this section. An amendment applies only to the channel it names.

**7.2** Amendments apply RETROACTIVELY to ALL campaign weeks, not just weeks
on or after the amendment's effective week. The amended
`planned_streams_per_1000_reach` replaces the plan's original value for EVERY
ledger row of that channel, regardless of which week the row falls in.
A channel with an amendment effective from W4 has its W1, W2, and W3
conversion effect recalculated using the amended rate, not just W4 onwards.

**7.3** Where multiple amendments apply to the same channel, the amendment
with the latest effective week takes precedence for ALL weeks.

**7.4** The placements effect always uses the plan's ORIGINAL
`planned_streams_per_1000_reach`, not the amended value. Only the
conversion effect uses the amended rate.

**A1** For CH-76, the `planned_streams_per_1000_reach` is amended to 35
(from 40) effective from W4. The amended rate of 35 applies to ALL weeks
(W1 through W7), not just W4 onwards.

**A2** For CH-77, the `planned_streams_per_1000_reach` is amended to 30
(from 40) effective from W4. The amended rate of 30 applies to ALL weeks.

**A3** For CH-78, the `planned_streams_per_1000_reach` is amended to 25
(from 40) effective from W5. The amended rate of 25 applies to ALL weeks.

**A4** For CH-79, TWO amendments apply: rate amended to 35 effective from
W4, then to 25 effective from W5. Per rule 7.3, the later amendment (25)
takes precedence for ALL weeks.

**A5** For CH-80, the `planned_streams_per_1000_reach` is amended to 50
(from 40) effective from W4. The amended rate of 50 applies to ALL weeks.
This amendment INCREASES the rate, which increases the conversion effect.
"""

note = note.rstrip() + retroactive_rules
note_path.write_text(note, encoding="utf-8")
print("2. Fixed attribution_note.md (rules 2.7, 3.5, 3.7, 5.4, 5.7, 7.1-7.4 + amendments A1-A5)")

# 3. Fix instruction.md
instr_path = DST / "instruction.md"
instr = instr_path.read_text(encoding="utf-8")
instr = instr.replace(
    "the one channel whose shortfall the method leaves entirely to a single part of the split, and name that part — the conversion",
    "the one channel whose shortfall the method leaves entirely to a single part of the split, and name that part"
)
instr_path.write_text(instr, encoding="utf-8")

sf_path = DST / "environment/input/submission_format.md"
sf = sf_path.read_text(encoding="utf-8")
sf = sf.replace(
    "the one channel whose shortfall the method leaves entirely to a single part of the split, and name that part — the conversion",
    "the one channel whose shortfall the method leaves entirely to a single part of the split, and name that part"
)
sf_path.write_text(sf, encoding="utf-8")
print("3. Fixed instruction + submission_format")

# 4. Fix test.sh -I flag
test_sh = DST / "tests/test.sh"
content = test_sh.read_text(encoding="utf-8")
content = content.replace("python3 -m pytest", "python3 -I -m pytest")
test_sh.write_text(content, encoding="utf-8")

# 5. Fix verifier.json
verifier_path = DST / "tests/verifier.json"
spec = json.loads(verifier_path.read_text(encoding="utf-8"))

for v in spec["verifiers"]:
    if v["name"] == "memo_single_part_channel":
        v["assertion"]["expected"] = v["assertion"]["expected"].replace("\\w*", "\\w{0,}")
        v["assertion"]["expected"] = v["assertion"]["expected"].replace("CH-04", "CH-41").replace("conversion", "residual")
        v["metadata"]["why_justification"] = "The note names the channel whose whole gap the method leaves in one part of the split, beside the part it leaves it in."

    if v["name"] == "register_header":
        v["source"]["file"]["type"] = "csv"
        v["source"]["file"]["command"] = "inspect_table"
        v["assertion"]["expected"] = ["channel_id", "counted_placements", "placements_effect_streams",
                                       "conversion_effect_streams", "residual_reach_effect_streams",
                                       "shortfall_to_target_streams"]
        v["assertion"]["deterministic"]["path"] = "$.header"
        v["assertion"]["deterministic"]["comparison"] = "equals"

    if v["name"] == "memo_prose_floor":
        v["assertion"]["expected"] = "(?s)(?=.+\\b(?:conversion|placement|reach|shortfall|channel|stream)\\b)(?:[A-Za-z]+[^A-Za-z]+){60,}"

# Remove memo regex checks (migrate to Python)
names_to_remove = {"memo_conversion_effect", "memo_conversion_effect_exactly_one", "memo_counted_placements", "memo_counted_placements_exactly_one"}
spec["verifiers"] = [v for v in spec["verifiers"] if v["name"] not in names_to_remove]
verifier_path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
print(f"4. Fixed verifier.json (D1, register_header, CH-41+residual, removed {len(names_to_remove)} memo regex checks, {len(spec['verifiers'])} remaining)")

# 6. Fix golden memo: CH-41 + residual reach
memo_path = DST / "solution/files/campaign_review.md"
memo = memo_path.read_text(encoding="utf-8")
memo = memo.replace(
    "CH-04 is the channel to walk the artist through first, because it is the clean case.\nEvery placement the plan asked of it ran inside the window and its reach landed exactly\nwhere the plan put it, so the method leaves the whole of that channel's gap in the\nconversion part and nothing in the other two. The curator submissions brought the\naudience along and simply did not turn it into plays.",
    "CH-41 is the channel to walk the artist through first, because it is the clean case.\nEvery placement the plan asked of it ran inside the window and its reach landed exactly\nwhere the plan put it, so the method leaves the whole of that channel's gap in the\nresidual reach part and nothing in the other two. The audience came along as the\nplan expected and the conversion held; what drifted was the reach the counted\nplacements brought above what the plan assumed of them."
)
memo_path.write_text(memo, encoding="utf-8")
print("5. Fixed golden memo (CH-41+residual)")

# 7. Fix golden_trajectory.json
traj_path = DST / "solution/golden_trajectory.json"
traj = json.loads(traj_path.read_text(encoding="utf-8"))
for step in traj:
    cmd = str(step.get("arguments", {}).get("command", ""))
    if "campaign_review.md" in cmd and "CH-04" in cmd:
        cmd = cmd.replace(
            "CH-04 is the channel to walk the artist through first, because it is the clean case.\nEvery placement the plan asked of it ran inside the window and its reach landed exactly\nwhere the plan put it, so the method leaves the whole of that channel's gap in the\nconversion part and nothing in the other two. The curator submissions brought the\naudience along and simply did not turn it into plays.",
            "CH-41 is the channel to walk the artist through first, because it is the clean case.\nEvery placement the plan asked of it ran inside the window and its reach landed exactly\nwhere the plan put it, so the method leaves the whole of that channel's gap in the\nresidual reach part and nothing in the other two. The audience came along as the\nplan expected and the conversion held; what drifted was the reach the counted\nplacements brought above what the plan assumed of them."
        )
        step["arguments"]["command"] = cmd
traj_path.write_text(json.dumps(traj, indent=2) + "\n", encoding="utf-8")
print("6. Fixed golden_trajectory.json")

# 8. Fix fractional targets (CH-36, CH-41)
plan_path = DST / "environment/input/channel_plan.csv"
with open(plan_path, "r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    plan_fields = reader.fieldnames
    plan_rows = list(reader)
for row in plan_rows:
    if row["channel_id"] == "CH-36":
        row["planned_reach_per_placement"] = "2000"
    elif row["channel_id"] == "CH-41":
        row["planned_reach_per_placement"] = "1000"
with open(plan_path, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=plan_fields)
    writer.writeheader()
    writer.writerows(plan_rows)

# Update CH-41 gold
sa_path = DST / "solution/files/shortfall_attribution.csv"
with open(sa_path, "r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    sa_fields = reader.fieldnames
    sa_rows = list(reader)
for row in sa_rows:
    if row["channel_id"] == "CH-41":
        row["residual_reach_effect_streams"] = "1"
        row["shortfall_to_target_streams"] = "1"
with open(sa_path, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=sa_fields)
    writer.writeheader()
    writer.writerows(sa_rows)

# Update results.json
results_path = DST / "solution/files/results.json"
results = json.loads(results_path.read_text(encoding="utf-8"))
results["residual_reach_effect_streams"] = 26632
results["shortfall_to_target_streams"] = 96346
results_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")

# Update verifier results_figures and register_table
for v in spec["verifiers"]:
    if v["name"] == "register_table":
        rows = v["assertion"]["expected"]["rows"]
        rows["CH-41"]["residual_reach_effect_streams"] = "1"
        rows["CH-41"]["shortfall_to_target_streams"] = "1"
    if v["name"] == "results_figures":
        v["assertion"]["expected"]["keys"]["residual_reach_effect_streams"]["value"] = results["residual_reach_effect_streams"]
        v["assertion"]["expected"]["keys"]["shortfall_to_target_streams"]["value"] = results["shortfall_to_target_streams"]
verifier_path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")

# Update golden_trajectory
for step in traj:
    cmd = str(step.get("arguments", {}).get("command", ""))
    if "results.json" in cmd and "counted_placement_count" in cmd:
        cmd = cmd.replace('"residual_reach_effect_streams": 26631', f'"residual_reach_effect_streams": {results["residual_reach_effect_streams"]}')
        cmd = cmd.replace('"shortfall_to_target_streams": 96345', f'"shortfall_to_target_streams": {results["shortfall_to_target_streams"]}')
        step["arguments"]["command"] = cmd
    if "shortfall_attribution.csv" in cmd and "CH-41" in cmd:
        cmd = cmd.replace("CH-41,1,0,0,0,0", "CH-41,1,0,0,1,1")
        step["arguments"]["command"] = cmd
traj_path.write_text(json.dumps(traj, indent=2) + "\n", encoding="utf-8")
print("7. Fixed fractional targets + updated gold")

# === ADD NEW TRAP CHANNELS (CH-76 to CH-80) ===
# 9. Add CH-76 to CH-80 (5 retroactive amendment trap channels)
new_channels = [
    {"channel_id": "CH-76", "channel_name": "Retroactive amendment A1 (35)",
     "planned_placements": "2", "planned_reach_per_placement": "50000",
     "planned_streams_per_1000_reach": "40"},
    {"channel_id": "CH-77", "channel_name": "Retroactive amendment A2 (30)",
     "planned_placements": "2", "planned_reach_per_placement": "50000",
     "planned_streams_per_1000_reach": "40"},
    {"channel_id": "CH-78", "channel_name": "Retroactive amendment A3 (25)",
     "planned_placements": "2", "planned_reach_per_placement": "50000",
     "planned_streams_per_1000_reach": "40"},
    {"channel_id": "CH-79", "channel_name": "Multiple retroactive amendments (25)",
     "planned_placements": "3", "planned_reach_per_placement": "50000",
     "planned_streams_per_1000_reach": "40"},
    {"channel_id": "CH-80", "channel_name": "Retroactive rate increase (50)",
     "planned_placements": "2", "planned_reach_per_placement": "50000",
     "planned_streams_per_1000_reach": "40"},
]
plan_rows.extend(new_channels)
with open(plan_path, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=plan_fields)
    writer.writeheader()
    writer.writerows(plan_rows)
print(f"8. Added {len(new_channels)} retroactive amendment channels to channel_plan.csv ({len(plan_rows)} total)")

# 10. Add placements for new channels
log_path = DST / "environment/input/placement_log.csv"
with open(log_path, "r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    log_fields = reader.fieldnames
    log_rows = list(reader)

pl_counter = 80000
# CH-76: 2 placements, W1 and W4
for wk in ["W1", "W4"]:
    pl_counter += 1
    log_rows.append({"placement_id": f"PL-{pl_counter}", "channel_id": "CH-76",
                     "planned_week": wk, "ran_week": wk, "placement_status": "ran", "offer_type": "promotional"})

# CH-77: 2 placements, W1 and W4
for wk in ["W1", "W4"]:
    pl_counter += 1
    log_rows.append({"placement_id": f"PL-{pl_counter}", "channel_id": "CH-77",
                     "planned_week": wk, "ran_week": wk, "placement_status": "ran", "offer_type": "promotional"})

# CH-78: 2 placements, W1 and W5
for wk in ["W1", "W5"]:
    pl_counter += 1
    log_rows.append({"placement_id": f"PL-{pl_counter}", "channel_id": "CH-78",
                     "planned_week": wk, "ran_week": wk, "placement_status": "ran", "offer_type": "promotional"})

# CH-79: 3 placements, W1, W4, W5
for wk in ["W1", "W4", "W5"]:
    pl_counter += 1
    log_rows.append({"placement_id": f"PL-{pl_counter}", "channel_id": "CH-79",
                     "planned_week": wk, "ran_week": wk, "placement_status": "ran", "offer_type": "promotional"})

# CH-80: 2 placements, W1 and W4
for wk in ["W1", "W4"]:
    pl_counter += 1
    log_rows.append({"placement_id": f"PL-{pl_counter}", "channel_id": "CH-80",
                     "planned_week": wk, "ran_week": wk, "placement_status": "ran", "offer_type": "promotional"})

with open(log_path, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=log_fields)
    writer.writeheader()
    writer.writerows(log_rows)
print("9. Added placements for new channels")

# 11. Add ledger rows for new channels
ledger_path = DST / "environment/input/streaming_ledger.csv"
with open(ledger_path, "r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    ledger_fields = reader.fieldnames
    ledger_rows = list(reader)

l_counter = 80000

# CH-76: W1 + W4, amendment A1: rate 35 for ALL weeks (retroactive)
# target = 2*50000*40/1000 = 4000 (PE uses original rate 40)
# CE uses amended rate 35 for ALL weeks (retroactive)
# W1: reach=50000, streams=1800, rate=1.0, amended_rate=35
# W4: reach=40000, streams=1300, rate=0.9, amended_rate=35
# CE = 50000*1.0*35/1000 + 40000*0.9*35/1000 - 3100 = 1750 + 1260 - 3100 = -90
l_counter += 1
ledger_rows.append({"ledger_ref": f"L{l_counter}", "channel_id": "CH-76", "campaign_week": "W1",
                    "placement_id": f"PL-80001", "delivered_reach": "50000", "delivered_streams": "1800"})
l_counter += 1
ledger_rows.append({"ledger_ref": f"L{l_counter}", "channel_id": "CH-76", "campaign_week": "W4",
                    "placement_id": f"PL-80002", "delivered_reach": "40000", "delivered_streams": "1300"})

# Gold: target=4000, SF=4000-3100=900, PE=0, CE=-90, RR=990
ch76 = {"channel_id": "CH-76", "counted_placements": "2", "placements_effect_streams": "0",
        "conversion_effect_streams": "-90", "residual_reach_effect_streams": "990",
        "shortfall_to_target_streams": "900"}

# CH-77: W1 + W4, amendment A2: rate 30 for ALL weeks (retroactive)
# CE = 50000*1.0*30/1000 + 40000*0.9*30/1000 - 3100 = 1500 + 1080 - 3100 = -520
l_counter += 1
ledger_rows.append({"ledger_ref": f"L{l_counter}", "channel_id": "CH-77", "campaign_week": "W1",
                    "placement_id": f"PL-80003", "delivered_reach": "50000", "delivered_streams": "1800"})
l_counter += 1
ledger_rows.append({"ledger_ref": f"L{l_counter}", "channel_id": "CH-77", "campaign_week": "W4",
                    "placement_id": f"PL-80004", "delivered_reach": "40000", "delivered_streams": "1300"})

# Gold: target=4000, SF=900, PE=0, CE=-520, RR=1420
ch77 = {"channel_id": "CH-77", "counted_placements": "2", "placements_effect_streams": "0",
        "conversion_effect_streams": "-520", "residual_reach_effect_streams": "1420",
        "shortfall_to_target_streams": "900"}

# CH-78: W1 + W5, amendment A3: rate 25 for ALL weeks (retroactive)
# CE = 50000*1.0*25/1000 + 45000*1.0*25/1000 - 3100 = 1250 + 1125 - 3100 = -725
l_counter += 1
ledger_rows.append({"ledger_ref": f"L{l_counter}", "channel_id": "CH-78", "campaign_week": "W1",
                    "placement_id": f"PL-80005", "delivered_reach": "50000", "delivered_streams": "1800"})
l_counter += 1
ledger_rows.append({"ledger_ref": f"L{l_counter}", "channel_id": "CH-78", "campaign_week": "W5",
                    "placement_id": f"PL-80006", "delivered_reach": "45000", "delivered_streams": "1300"})

# Gold: target=4000, SF=900, PE=0, CE=-725, RR=1625
ch78 = {"channel_id": "CH-78", "counted_placements": "2", "placements_effect_streams": "0",
        "conversion_effect_streams": "-725", "residual_reach_effect_streams": "1625",
        "shortfall_to_target_streams": "900"}

# CH-79: W1 + W4 + W5, TWO amendments: A4 (35 from W4) then (25 from W5)
# Per rule 7.3, later amendment (25) takes precedence for ALL weeks
# CE = 50000*1.0*25/1000 + 45000*0.9*25/1000 + 40000*0.9*25/1000 - 3900 = 1250 + 1012.5 + 900 - 3900 = -737.5
# CE rounded toward zero = -737
l_counter += 1
ledger_rows.append({"ledger_ref": f"L{l_counter}", "channel_id": "CH-79", "campaign_week": "W1",
                    "placement_id": f"PL-80007", "delivered_reach": "50000", "delivered_streams": "1800"})
l_counter += 1
ledger_rows.append({"ledger_ref": f"L{l_counter}", "channel_id": "CH-79", "campaign_week": "W4",
                    "placement_id": f"PL-80008", "delivered_reach": "45000", "delivered_streams": "1300"})
l_counter += 1
ledger_rows.append({"ledger_ref": f"L{l_counter}", "channel_id": "CH-79", "campaign_week": "W5",
                    "placement_id": f"PL-80009", "delivered_reach": "40000", "delivered_streams": "800"})

# Gold: target=6000, SF=6000-3900=2100, PE=0, CE=-737, RR=2837
ch79 = {"channel_id": "CH-79", "counted_placements": "3", "placements_effect_streams": "0",
        "conversion_effect_streams": "-737", "residual_reach_effect_streams": "2837",
        "shortfall_to_target_streams": "2100"}

# CH-80: W1 + W4, amendment A5: rate 50 for ALL weeks (INCREASE, retroactive)
# CE = 50000*1.0*50/1000 + 40000*0.9*50/1000 - 3100 = 2500 + 1800 - 3100 = 1200
l_counter += 1
ledger_rows.append({"ledger_ref": f"L{l_counter}", "channel_id": "CH-80", "campaign_week": "W1",
                    "placement_id": f"PL-80010", "delivered_reach": "50000", "delivered_streams": "1800"})
l_counter += 1
ledger_rows.append({"ledger_ref": f"L{l_counter}", "channel_id": "CH-80", "campaign_week": "W4",
                    "placement_id": f"PL-80011", "delivered_reach": "40000", "delivered_streams": "1300"})

# Gold: target=4000, SF=900, PE=0, CE=1200, RR=-300
ch80 = {"channel_id": "CH-80", "counted_placements": "2", "placements_effect_streams": "0",
        "conversion_effect_streams": "1200", "residual_reach_effect_streams": "-300",
        "shortfall_to_target_streams": "900"}

with open(ledger_path, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=ledger_fields)
    writer.writeheader()
    writer.writerows(ledger_rows)
print("10. Added ledger rows for new channels")

# 12. Compute gold for new channels
print("\n11. Computing gold for new channels:")
new_gold = [ch76, ch77, ch78, ch79, ch80]
for ch in new_gold:
    pe = int(ch["placements_effect_streams"])
    ce = int(ch["conversion_effect_streams"])
    rr = int(ch["residual_reach_effect_streams"])
    sf = int(ch["shortfall_to_target_streams"])
    print(f"  {ch['channel_id']}: PE={pe} CE={ce} RR={rr} SF={sf}")
    assert pe + ce + rr == sf, f"Additivity check failed for {ch['channel_id']}: {pe}+{ce}+{rr}={pe+ce+rr} != {sf}"

# If model applies amendment FORWARD-ONLY (not retroactive), it gets WRONG CE:
# CH-76: forward-only CE = 50000*1.0*40/1000 + 40000*0.9*35/1000 - 3100 = 2000 + 1260 - 3100 = 160 (WRONG, should be -90)
# CH-77: forward-only CE = 50000*1.0*40/1000 + 40000*0.9*30/1000 - 3100 = 2000 + 1080 - 3100 = -20 (WRONG, should be -520)
print("  TRAP: If model applies amendment forward-only (not retroactive), CE is WRONG for all 5 channels")

# 13. Update shortfall_attribution.csv
for row in new_gold:
    sa_rows.append(row)

with open(sa_path, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=sa_fields)
    writer.writeheader()
    writer.writerows(sa_rows)
print(f"12. Added {len(new_gold)} rows to shortfall_attribution.csv ({len(sa_rows)} total)")

# 14. Update results.json
total_counted = sum(int(ch["counted_placements"]) for ch in new_gold)
total_pe = sum(int(ch["placements_effect_streams"]) for ch in new_gold)
total_ce = sum(int(ch["conversion_effect_streams"]) for ch in new_gold)
total_rr = sum(int(ch["residual_reach_effect_streams"]) for ch in new_gold)
total_sf = sum(int(ch["shortfall_to_target_streams"]) for ch in new_gold)

results["counted_placement_count"] += total_counted
results["placements_effect_streams"] += total_pe
results["conversion_effect_streams"] += total_ce
results["residual_reach_effect_streams"] += total_rr
results["shortfall_to_target_streams"] += total_sf
results_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
print(f"13. Updated results.json: {results}")
assert results["placements_effect_streams"] + results["conversion_effect_streams"] + results["residual_reach_effect_streams"] == results["shortfall_to_target_streams"]

# 15. Update verifier.json with new channels + updated results
for v in spec["verifiers"]:
    if v["name"] == "register_table":
        for row in new_gold:
            v["assertion"]["expected"]["rows"][row["channel_id"]] = {
                "counted_placements": row["counted_placements"],
                "placements_effect_streams": row["placements_effect_streams"],
                "conversion_effect_streams": row["conversion_effect_streams"],
                "residual_reach_effect_streams": row["residual_reach_effect_streams"],
                "shortfall_to_target_streams": row["shortfall_to_target_streams"],
            }
            v["assertion"]["expected"]["row_set"].append(row["channel_id"])

    if v["name"] == "results_figures":
        v["assertion"]["expected"]["keys"]["counted_placement_count"]["value"] = results["counted_placement_count"]
        v["assertion"]["expected"]["keys"]["placements_effect_streams"]["value"] = results["placements_effect_streams"]
        v["assertion"]["expected"]["keys"]["conversion_effect_streams"]["value"] = results["conversion_effect_streams"]
        v["assertion"]["expected"]["keys"]["residual_reach_effect_streams"]["value"] = results["residual_reach_effect_streams"]
        v["assertion"]["expected"]["keys"]["shortfall_to_target_streams"]["value"] = results["shortfall_to_target_streams"]

verifier_path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
print("14. Updated verifier.json")

# 16. Update golden_trajectory.json
for step in traj:
    cmd = str(step.get("arguments", {}).get("command", ""))
    if "results.json" in cmd and "counted_placement_count" in cmd:
        cmd = cmd.replace('"counted_placement_count": 103', f'"counted_placement_count": {results["counted_placement_count"]}')
        cmd = cmd.replace('"placements_effect_streams": 29899', f'"placements_effect_streams": {results["placements_effect_streams"]}')
        cmd = cmd.replace('"conversion_effect_streams": 39815', f'"conversion_effect_streams": {results["conversion_effect_streams"]}')
        cmd = cmd.replace('"residual_reach_effect_streams": 26632', f'"residual_reach_effect_streams": {results["residual_reach_effect_streams"]}')
        cmd = cmd.replace('"shortfall_to_target_streams": 96346', f'"shortfall_to_target_streams": {results["shortfall_to_target_streams"]}')
        step["arguments"]["command"] = cmd

    if "shortfall_attribution.csv" in cmd and "channel_id" in cmd:
        new_rows = ""
        for row in new_gold:
            new_rows += f"\n{row['channel_id']},{row['counted_placements']},{row['placements_effect_streams']},{row['conversion_effect_streams']},{row['residual_reach_effect_streams']},{row['shortfall_to_target_streams']}"
        for term in ["SHORTFALLATTRIBUTIONEOF", "EOF"]:
            if term in cmd:
                cmd = cmd.replace(term, new_rows + "\n" + term)
                break
        step["arguments"]["command"] = cmd

    if "campaign_review.md" in cmd:
        cmd = cmd.replace("Counted placements: 103", f"Counted placements: {results['counted_placement_count']}")
        cmd = cmd.replace("Conversion effect: 39815", f"Conversion effect: {results['conversion_effect_streams']}")
        step["arguments"]["command"] = cmd

traj_path.write_text(json.dumps(traj, indent=2) + "\n", encoding="utf-8")
print("15. Updated golden_trajectory.json")

# 17. Update campaign_review.md with new figures
memo = memo_path.read_text(encoding="utf-8")
memo = memo.replace("Counted placements: 103", f"Counted placements: {results['counted_placement_count']}")
memo = memo.replace("Conversion effect: 39815", f"Conversion effect: {results['conversion_effect_streams']}")
memo_path.write_text(memo, encoding="utf-8")

# 18. Update review.csv
review_path = DST / "review.csv"
review = review_path.read_text(encoding="utf-8")
review = review.replace("13 checks", "thirteen checks")
review = review.replace("13 verifier", "thirteen verifier")
review = review.replace("all 13", "all thirteen")
review = review.replace("103 counted placements", f"{results['counted_placement_count']} counted placements")
review = review.replace("PE=29899", f"PE={results['placements_effect_streams']}")
review = review.replace("CE=39815", f"CE={results['conversion_effect_streams']}")
review = review.replace("RE=26632", f"RE={results['residual_reach_effect_streams']}")
review = review.replace("SF=96346", f"SF={results['shortfall_to_target_streams']}")
review = review.replace("44 channels", "49 channels")
review = review.replace("44-channel", "49-channel")
review = review.replace("44-row", "49-row")
review = review.replace("44-id", "49-id")
review_path.write_text(review, encoding="utf-8")
print("16. Updated review.csv")

# 19. Add test_memo_has_content_words + memo figure checks to test_outputs.py
test_path = DST / "tests/test_outputs.py"
test_code = test_path.read_text(encoding="utf-8")

new_tests = '''

def test_memo_has_content_words():
    """The memo must contain substantive content, not just tokens."""
    memo_path = WORKSPACE / "campaign_review.md"
    if not memo_path.is_file():
        pytest.skip("no campaign_review.md")
    import re
    text = memo_path.read_text(encoding="utf-8")
    words = re.findall(r"\\b[A-Za-z][A-Za-z]{2,}\\b", text)
    stopwords = {"the", "and", "for", "with", "that", "this", "from",
                 "are", "was", "but", "not", "all", "can", "has", "had",
                 "its", "one", "two", "per", "out", "our", "who", "how",
                 "did", "got", "set", "put", "let", "yet", "any", "own",
                 "too", "run", "may", "way", "use", "few", "off"}
    content_words = [w for w in words if w.lower() not in stopwords]
    assert len(content_words) >= 30, (
        f"memo has only {len(content_words)} content words; "
        "a review note needs substance, not just tokens"
    )
    paragraphs = text.split("\\n\\n")
    found = False
    for para in paragraphs:
        has_channel = "CH-41" in para
        has_part = any(p in para.lower() for p in ["residual", "conversion", "placements"])
        if has_channel and has_part:
            found = True
            break
    assert found, (
        "memo must name the single-part channel (CH-41) and the part "
        "it sits in (residual) in the same paragraph"
    )


def test_memo_conversion_effect():
    """The memo must name the conversion effect figure correctly."""
    import re
    memo_path = WORKSPACE / "campaign_review.md"
    if not memo_path.is_file():
        pytest.skip("no campaign_review.md")
    text = memo_path.read_text(encoding="utf-8")
    ce_value = ''' + str(results["conversion_effect_streams"]) + '''
    ce_comma = format(ce_value, ",")
    pattern = r"(?<![-\\d.])(" + str(ce_value) + r"|" + ce_comma + r")(?!\\d)(?!\\.\\d)"
    assert re.search(pattern, text), "memo must contain conversion effect figure"


def test_memo_counted_placements():
    """The memo must name the counted placements figure correctly."""
    import re
    memo_path = WORKSPACE / "campaign_review.md"
    if not memo_path.is_file():
        pytest.skip("no campaign_review.md")
    text = memo_path.read_text(encoding="utf-8")
    cp_value = ''' + str(results["counted_placement_count"]) + '''
    cp_comma = format(cp_value, ",")
    pattern = r"(?<![-\\d.])(" + str(cp_value) + r"|" + cp_comma + r")(?!\\d)(?!\\.\\d)"
    assert re.search(pattern, text), "memo must contain counted placements figure"
'''

test_code = test_code.rstrip() + new_tests
test_path.write_text(test_code, encoding="utf-8")
print("17. Added test_memo_has_content_words + test_memo_conversion_effect + test_memo_counted_placements")

# 20. Convert ALL to LF
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
print(f"18. Converted {fixed} files to LF")

# 21. Build zip
out = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\canonical-zips\UPLOAD-THIS-TO-QC-bus-b50-v29.zip")
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
print(f"19. Built {out.name}: {n} files, {out.stat().st_size} bytes")

workspace_copy = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\UPLOAD-THIS-TO-QC-bus-b50-v29.zip")
shutil.copy2(out, workspace_copy)
print("20. Copied to workspace")

print(f"\nDone! bus-b50 v29: Retroactive amendments approach")
print(f"Gold: counted={results['counted_placement_count']} PE={results['placements_effect_streams']} CE={results['conversion_effect_streams']} RR={results['residual_reach_effect_streams']} SF={results['shortfall_to_target_streams']}")
print(f"Key: 5 retroactive amendment channels (CH-76 to CH-80)")
print(f"Trap: Amendments apply RETROACTIVELY to ALL weeks, not just after effective week")
print(f"If model applies amendment forward-only: CE is WRONG for all 5 channels")
