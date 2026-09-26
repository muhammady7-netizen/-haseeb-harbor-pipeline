import json
from pathlib import Path

ROOT = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\task-sources\bus-b50-v29")
spec = json.loads((ROOT / "tests/verifier.json").read_text(encoding="utf-8"))

for v in spec["verifiers"]:
    if v["name"] == "register_table":
        for ch, row in v["assertion"]["expected"]["rows"].items():
            for col, val in row.items():
                if isinstance(val, str) and "." in val:
                    row[col] = str(int(float(val)))
                    print("  Fixed", ch, col, val, "->", row[col])
    if v["name"] == "results_figures":
        for k, val in v["assertion"]["expected"]["keys"].items():
            if isinstance(val["value"], float):
                val["value"] = int(val["value"])
                print("  Fixed results", k, val["value"])

(ROOT / "tests/verifier.json").write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
print("verifier.json fixed!")
