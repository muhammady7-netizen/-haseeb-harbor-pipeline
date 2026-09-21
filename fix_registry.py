"""Fix registry.json paths for this PC (OneDrive paths instead of Codex paths)."""
import json
from pathlib import Path

reg_path = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\-haseeb-harbor-pipeline\registry.json")
reg = json.loads(reg_path.read_text(encoding="utf-8-sig"))

# Path fixes for this PC
fixes = {
    "gen-g826": {
        "work_root": "C:/Users/Haseeb Mirza/OneDrive/Documents/NONC-B1-1001654",
        "pack_path": "C:/Users/Haseeb Mirza/OneDrive/Documents/NONC-B1-1001654/gen-g826-tender-document-brand-style-audit"
    },
    "code-c227": {
        "work_root": "C:/Users/Haseeb Mirza/OneDrive/Documents/c227-work",
        "pack_path": "C:/Users/Haseeb Mirza/OneDrive/Documents/c227-work/code-c227-table-bloat-maintenance-audit"
    },
    "code-c249": {
        "work_root": "C:/Users/Haseeb Mirza/OneDrive/Documents/c249-work",
        "pack_path": "C:/Users/Haseeb Mirza/OneDrive/Documents/c249-work/code-c249-recurring-report-source-selection-audit"
    },
    "gen-g1205": {
        "work_root": "C:/Users/Haseeb Mirza/OneDrive/Documents/NONC-B1-1002016",
        "pack_path": "C:/Users/Haseeb Mirza/OneDrive/Documents/NONC-B1-1002016/gen-g1205-meal-prep-cost-claim-recompute-audit"
    },
    "the-thread": {
        "work_root": "C:/Users/Haseeb Mirza/OneDrive/Documents/NONC-B1-1001634",
        "pack_path": "C:/Users/Haseeb Mirza/OneDrive/Documents/NONC-B1-1001634/gen-g806-leadership-brief-rhetorical-style-audit"
    }
}

for task in reg["tasks"]:
    short = task.get("short", "")
    if short in fixes:
        for key, val in fixes[short].items():
            old = task.get(key, "")
            task[key] = val
            if old != val:
                print(f"  Fixed {short}.{key}: {old} -> {val}")

# Save
reg["updated_at"] = "2026-09-09T05:30:00Z"
reg_path.write_text(json.dumps(reg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print("Registry paths fixed")

# Verify
for task in reg["tasks"]:
    short = task.get("short", "")
    if short in fixes:
        pack = Path(task["pack_path"])
        exists = pack.is_dir() and (pack / "task.toml").is_file()
        print(f"  {short}: pack exists={exists}")
