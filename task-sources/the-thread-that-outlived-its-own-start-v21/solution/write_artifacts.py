#!/usr/bin/env python3
"""Materialise the ORACLE's deliverables into the agent workspace.

The golden trajectory is gym tool calls only, so nothing in the replay puts a file on
disk -- but the `file_check` verifier grades files in the workspace. Without this the
oracle scores less than 1.0 on a task that is not actually broken.

Both deliverables here are machine-readable (JSON + CSV); there is no prose artifact.
"""
import csv
import json
import os
from pathlib import Path

sol = Path(os.environ.get("SOLUTION_DIR", "/solution"))
ws = Path(os.environ.get("WORKSPACE", os.environ.get("TH_WORKSPACE_DIR", "/workspace")))
ws.mkdir(parents=True, exist_ok=True)
plan = json.loads((sol / "artifact_plan.json").read_text())

if plan.get("json_path"):
    (ws / plan["json_path"]).write_text(json.dumps(plan["json"], indent=2) + "\n")
    print("wrote", plan["json_path"], "keys", sorted(plan["json"]))

if plan.get("csv_path"):
    with (ws / plan["csv_path"]).open("w", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerows(plan["csv"])
    print("wrote", plan["csv_path"], "rows", len(plan["csv"]) - 1)
