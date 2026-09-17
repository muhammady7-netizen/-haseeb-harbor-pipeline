"""Verify gold sync after ST-354/ST-134 fix."""
from __future__ import annotations

import json
import re
from pathlib import Path

p = Path("task-sources/law-b39/law-b39-l16-custody-letter-instruction-audit-v17")
print("results", json.loads((p / "solution/files/results.json").read_text(encoding="utf-8")))
print("golden", json.loads((p / "solution/golden_results.json").read_text(encoding="utf-8")))
ans = (p / "solution/files/answer.md").read_text(encoding="utf-8")
print("answer", [l for l in ans.splitlines() if "at odds" in l.lower()][:2])
ver = json.loads((p / "tests/verifier.json").read_text(encoding="utf-8"))
for v in ver["verifiers"]:
    if v["name"] == "results_figures":
        print(
            "ver figures",
            {k: v["assertion"]["expected"]["keys"][k]["value"] for k in v["assertion"]["expected"]["keys"]},
        )
    if v["name"] == "answer_at_odds_figure":
        print("ver regex", v["assertion"]["expected"][:140])
    if v["name"] == "register_table":
        rows = v["assertion"]["expected"]["rows"]
        print("ver ST-354", rows.get("ST-354"))
        print("ver ST-134", rows.get("ST-134"))
gt = (p / "solution/golden_trajectory.json").read_text(encoding="utf-8")
for pat in [
    "verified_count",
    "at_odds_count",
    "not_in_record_count",
    "clarification_governed_count",
]:
    vals = sorted(set(re.findall(rf'{pat}[\"\s:=]+(\d+)', gt)))
    print(pat, vals)
m = re.search(r"ST-354,(\w+),(\w+)", gt)
print("traj ST-354", m.group(0) if m else None)
m = re.search(r"ST-134,(\w+),(\w+)", gt)
print("traj ST-134", m.group(0) if m else None)
print(
    "readme",
    [l for l in (p / "README.md").read_text(encoding="utf-8").splitlines() if "verified" in l.lower()][:3],
)
