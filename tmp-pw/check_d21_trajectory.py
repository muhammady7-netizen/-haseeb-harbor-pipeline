"""Assert golden_trajectory embedded deliverables match solution/files gold."""
from __future__ import annotations

import json
import re
from pathlib import Path

PACK = Path("task-sources/law-b39/law-b39-l16-custody-letter-instruction-audit-v17")
gt = json.loads((PACK / "solution/golden_trajectory.json").read_text(encoding="utf-8"))
gold_csv = (PACK / "solution/files/letter_line_review.csv").read_text(encoding="utf-8")
gold_ans = (PACK / "solution/files/answer.md").read_text(encoding="utf-8")
gold_res = json.loads((PACK / "solution/files/results.json").read_text(encoding="utf-8"))

ans_cmd = gt[5]["arguments"]["command"]
csv_cmd = gt[6]["arguments"]["command"]
res_cmd = gt[7]["arguments"]["command"]

m = re.search(r"cat > answer\.md << 'ANSWEREOF'\n(.*)\nANSWEREOF\Z", ans_cmd, re.S)
assert m, "answer heredoc"
assert m.group(1).rstrip("\n") == gold_ans.rstrip("\n"), "answer mismatch"

m = re.search(
    r"cat > letter_line_review\.csv << 'LETTERLINEREVIEWEOF'\n(.*)\nLETTERLINEREVIEWEOF\Z",
    csv_cmd,
    re.S,
)
assert m, "csv heredoc"
assert m.group(1).rstrip("\n") == gold_csv.rstrip("\n"), "csv mismatch"
body = gold_csv.strip().splitlines()[1:]
assert len(body) == 290, len(body)
assert "ST-354,AT_ODDS,OI-202" in gold_csv
assert "ST-134,AT_ODDS,CL-303" in gold_csv

m = re.search(r"cat > results\.json << 'RESULTSEOF'\n(.*)\nRESULTSEOF\Z", res_cmd, re.S)
assert m, "results heredoc"
traj_res = json.loads(m.group(1))
assert traj_res == gold_res, (traj_res, gold_res)
assert gold_res == {
    "verified_count": 85,
    "at_odds_count": 156,
    "not_in_record_count": 49,
    "clarification_governed_count": 168,
}
print("D21 local check PASS — trajectory == gold", gold_res)
