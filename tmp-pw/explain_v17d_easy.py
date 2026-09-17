import csv
from pathlib import Path

p = Path("task-sources/law-b39/law-b39-l16-custody-letter-instruction-audit-v17")
gold = {r["line_id"]: r for r in csv.DictReader((p / "solution/files/letter_line_review.csv").open(encoding="utf-8"))}
lines = {r["line_id"]: r for r in csv.DictReader((p / "environment/input/letter_lines.csv").open(encoding="utf-8"))}
traps = [
    "ST-106","ST-137","ST-139","ST-163","ST-164","ST-166","ST-169","ST-186","ST-187","ST-188",
    "ST-189","ST-191","ST-221","ST-329","ST-330","ST-331","ST-332","ST-335","ST-338",
    "ST-415","ST-416","ST-417","ST-418",
]
print("=== plan traps (gold AT_ODDS) ===")
for lid in traps:
    print(f"{lid}|{gold[lid]['verdict']}|{lines[lid]['wording'][:90]}")

print("\n=== GLM match on traps ===")
for ri in range(1, 5):
    gpath = next(x for x in (p / f"evaluations/glm-5.2/r{ri}").rglob("letter_line_review.csv") if "app" in str(x))
    glm = {r["line_id"]: r for r in csv.DictReader(gpath.open(encoding="utf-8"))}
    mism = [
        lid
        for lid, g in gold.items()
        if glm.get(lid, {}).get("verdict") != g["verdict"]
        or glm.get(lid, {}).get("record_entry") != g["record_entry"]
    ]
    trap_ok = sum(1 for lid in traps if glm.get(lid, {}).get("verdict") == gold[lid]["verdict"])
    reward = (p / f"evaluations/glm-5.2/r{ri}/verifier/reward.txt").read_text(encoding="utf-8").strip()
    print(f"r{ri} reward={reward} total_mismatches={len(mism)} traps_correct={trap_ok}/{len(traps)}")
    if mism:
        print("  sample mism", mism[:8])
