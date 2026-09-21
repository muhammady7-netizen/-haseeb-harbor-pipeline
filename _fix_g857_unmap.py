"""Normalize g857 unmapped gold to UNMAPPED token and package helpers."""
from __future__ import annotations

import csv
from pathlib import Path

pack = Path(
    "qc-out/ework/gen-g857-portal/gen-g857-department-directory-categorization-audit"
)
mp = pack / "solution/files/g857_mappings.csv"
rows = list(csv.DictReader(mp.open(encoding="utf-8", newline="")))
for r in rows:
    if r["status"].strip() == "NO_ROLE_MATCH":
        r["target_node"] = "UNMAPPED"
        r["confidence"] = "0"
with mp.open("w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(
        f, fieldnames=["person_id", "target_node", "confidence", "status"]
    )
    w.writeheader()
    w.writerows(rows)

inst_path = pack / "instruction.md"
inst = inst_path.read_text(encoding="utf-8")
repls = [
    (
        "write `g857_mappings.csv` with one row per person where `target_node` is empty, `confidence` is `0`, and `status` is `CYCLE_DETECTED`",
        "write `g857_mappings.csv` with one row per person where `target_node` is `UNMAPPED`, `confidence` is `0`, and `status` is `CYCLE_DETECTED`",
    ),
    (
        "the person is unmapped: `target_node` empty, `confidence` `0`, `status` `NO_ROLE_MATCH`.",
        "the person is unmapped: `target_node` is `UNMAPPED`, `confidence` is `0`, `status` is `NO_ROLE_MATCH`.",
    ),
    (
        "Mapped persons have `status` = `MAPPED` and a non-empty `target_node`.",
        "Mapped persons have `status` = `MAPPED` and a concrete taxonomy `target_node` (never `UNMAPPED`).",
    ),
]
for a, b in repls:
    if a not in inst:
        print("MISSING", a[:60])
    else:
        inst = inst.replace(a, b)
        print("replaced ok")
inst_path.write_text(inst, encoding="utf-8")
print("gold lines:")
for line in mp.read_text(encoding="utf-8").splitlines():
    if line.startswith(("P012", "P029", "P030")):
        print(line)
