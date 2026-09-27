import csv
from pathlib import Path

ROOT = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\gen-g806-leadership-brief-rhetorical-style-audit\environment\input")

with (ROOT / "script_inventory.csv").open(encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    rows = list(reader)

modifications = {
    "SC-04": "That is not the right approach. That is the wrong way. Keep the tone procedural; no personal testimony.",
    "SC-16": "It isn't a problem. It's an opportunity. A calm thank-you to the volunteers.",
    "SC-20": "This is not the end. This is the beginning. A soft close that leaves the room.",
    "SC-27": "That was not the plan. That was the backup. A quiet pastoral note before the offering.",
    "SC-28": "It wasn't the right moment. It was too early. Procedural board preview covering consent.",
}

for r in rows:
    sid = r["script_id"].strip().upper()
    if sid in modifications:
        r["body_excerpt"] = modifications[sid]
        print("Modified %s: %s" % (sid, r["body_excerpt"][:60]))

with (ROOT / "script_inventory.csv").open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print("Done - modified 5 scripts with tricky non-pivot patterns")
print("These are NOT negation pivots:")
print("  SC-04: 'That is not X. That is Y.' (uses 'That' not 'It')")
print("  SC-16: 'It isn\\'t X.' (contraction, no separate 'not')")
print("  SC-20: 'This is not X. This is Y.' (uses 'This' not 'It')")
print("  SC-27: 'That was not X. That was Y.' (uses 'That' not 'It')")
print("  SC-28: 'It wasn\\'t X.' (contraction, no separate 'not')")
