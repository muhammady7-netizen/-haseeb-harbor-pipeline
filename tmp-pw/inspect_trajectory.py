"""Inspect golden_trajectory for PreQC count / ST-354 / ST-134 issues."""
from __future__ import annotations

import json
import re
from pathlib import Path

p = Path("task-sources/law-b39/law-b39-l16-custody-letter-instruction-audit-v17/solution/golden_trajectory.json")
gt = json.loads(p.read_text(encoding="utf-8"))
print("type", type(gt).__name__, "len", len(gt) if isinstance(gt, list) else list(gt)[:5] if isinstance(gt, dict) else "?")
if isinstance(gt, list):
    for i, step in enumerate(gt):
        name = step.get("name")
        args = step.get("arguments") or {}
        cmd = args.get("command") or args.get("content") or ""
        preview = (cmd[:80] + "...") if len(cmd) > 80 else cmd
        print(f"step{i}", name, "cmd_len", len(cmd), preview.replace("\n", "\\n"))
        # find count-like numbers
        for pat in ["verified_count", "at_odds_count", "87", "154", "85", "156", "ST-354", "ST-134"]:
            if pat in cmd:
                print("  has", pat)
        # extract csv lines for ST-354/134
        for lid in ("ST-354", "ST-134"):
            m = re.search(rf"{lid},[A-Z_]+,[A-Z0-9-]+", cmd)
            if m:
                print(" ", m.group(0))
