"""Rebuild golden_trajectory.json deliverable steps from current gold files."""
from __future__ import annotations

import json
from pathlib import Path

PACK = Path("task-sources/law-b39/law-b39-l16-custody-letter-instruction-audit-v17")
gt_path = PACK / "solution/golden_trajectory.json"
gt = json.loads(gt_path.read_text(encoding="utf-8"))

answer = (PACK / "solution/files/answer.md").read_text(encoding="utf-8")
csv_text = (PACK / "solution/files/letter_line_review.csv").read_text(encoding="utf-8")
results = (PACK / "solution/files/results.json").read_text(encoding="utf-8")

# Ensure trailing newline for heredocs
if not answer.endswith("\n"):
    answer += "\n"
if not csv_text.endswith("\n"):
    csv_text += "\n"
if not results.endswith("\n"):
    results += "\n"

assert "ST-354,AT_ODDS,OI-202" in csv_text
assert "ST-134,AT_ODDS,CL-303" in csv_text
assert '"at_odds_count": 156' in results
assert "Letter lines at odds with the record: 156" in answer

gt[5]["arguments"]["command"] = "cat > answer.md << 'ANSWEREOF'\n" + answer + "ANSWEREOF"
gt[6]["arguments"]["command"] = (
    "cat > letter_line_review.csv << 'LETTERLINEREVIEWEOF'\n" + csv_text + "LETTERLINEREVIEWEOF"
)
gt[7]["arguments"]["command"] = "cat > results.json << 'RESULTSEOF'\n" + results + "RESULTSEOF"

gt_path.write_text(json.dumps(gt, indent=2) + "\n", encoding="utf-8")

# Sanity counts from trajectory CSV
body = csv_text.strip().splitlines()[1:]
V = sum(1 for l in body if ",VERIFIED," in l)
A = sum(1 for l in body if ",AT_ODDS," in l)
N = sum(1 for l in body if ",NOT_IN_RECORD," in l)
C = sum(1 for l in body if ",CL-" in l)
print("traj rows", len(body), "counts", V, A, N, C)
print("cmd lens", len(gt[5]["arguments"]["command"]), len(gt[6]["arguments"]["command"]), len(gt[7]["arguments"]["command"]))
print("DONE trajectory synced")
