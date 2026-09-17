import csv
from pathlib import Path
from collections import defaultdict

p = Path("task-sources/law-b39/law-b39-l16-custody-letter-instruction-audit-v17")
lines = {r["line_id"]: r for r in csv.DictReader((p / "environment/input/letter_lines.csv").open(encoding="utf-8"))}
gold = {r["line_id"]: r for r in csv.DictReader((p / "solution/files/letter_line_review.csv").open(encoding="utf-8"))}

ids = [
    "ST-106","ST-137","ST-139","ST-163","ST-164","ST-166","ST-169","ST-186","ST-187","ST-188","ST-189","ST-191",
    "ST-221","ST-329","ST-330","ST-331","ST-332","ST-335","ST-338","ST-405","ST-407","ST-420","ST-403",
    "ST-415","ST-416","ST-417","ST-418","ST-138","ST-195","ST-226","ST-341"
]
print("=== cited / related lines ===")
for i in ids:
    if i not in gold:
        print(i, "MISSING")
        continue
    g = gold[i]
    L = lines[i]
    w = L["wording"].replace("\n", " ")
    print(f"{i}|gold={g['verdict']}|gov={g['record_entry']}|subj={L['subject']}|pos={L['position']}|cite={L['cited_entry']}")
    print(f"  W: {w[:160]}")

by_text = defaultdict(list)
for lid, L in lines.items():
    t = L["wording"].strip()
    by_text[t].append((lid, gold[lid]["verdict"], gold[lid]["record_entry"], L["subject"], L["cited_entry"]))

print("\n=== identical wording, differing verdicts ===")
n_contra = 0
for t, rows in by_text.items():
    vs = {r[1] for r in rows}
    if len(rows) > 1 and len(vs) > 1:
        n_contra += 1
        print(rows)
        print(" TEXT:", t[:180])

print("\n=== identical wording groups (any) sample ===")
dups = [(t, rows) for t, rows in by_text.items() if len(rows) > 1]
print("dup groups", len(dups), "contradictory", n_contra)
for t, rows in dups[:8]:
    print(len(rows), {r[1] for r in rows}, [r[0] for r in rows])

# fully vs not fully under same gov
print("\n=== concern lines with appreciate ===")
for lid, L in sorted(lines.items()):
    if "appreciate" in L["wording"].lower():
        g = gold[lid]
        print(f"{lid}|{g['verdict']}|{g['record_entry']}|cite={L['cited_entry']}|{L['wording'][:100]}")
