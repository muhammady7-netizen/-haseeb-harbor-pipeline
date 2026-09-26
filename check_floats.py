import csv
from pathlib import Path
ROOT = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\task-sources\bus-b50-v29\solution\files")
with (ROOT / "shortfall_attribution.csv").open(encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
for r in rows:
    for k, v in r.items():
        if "." in str(v) and k != "channel_id":
            print("  FLOAT:", r["channel_id"], k, "=", v)
for ch in ["CH-01", "CH-06", "CH-13"]:
    row = next((r for r in rows if r["channel_id"] == ch), None)
    if row:
        print(ch, row)
