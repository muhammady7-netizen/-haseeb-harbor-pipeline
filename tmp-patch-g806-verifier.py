import csv, json, re
from pathlib import Path

PACK = Path(
    r"C:\Users\Haseeb Mirza\Documents\Codex\2026-08-17\this-is-the-very-beginning-of\tasks\NONC-B1-1001634\gen-g806-leadership-brief-rhetorical-style-audit"
)
rows = list(csv.DictReader((PACK / "solution/files/brief_coherence.csv").open(encoding="utf-8")))
by = {r["brief_id"]: r for r in rows}
results = json.loads((PACK / "solution/files/results.json").read_text(encoding="utf-8"))
memo = (PACK / "solution/files/executive_sequence_memo.md").read_text(encoding="utf-8")
vj = json.loads((PACK / "tests/verifier.json").read_text(encoding="utf-8"))

for v in vj["verifiers"]:
    name = v.get("name", "")
    src = v.setdefault("source", {})
    if name.startswith("projected_b"):
        bid = "B-" + name[-2:]
        val = by[bid]["projected_score"]
        src["expected"] = rf"(?mi)^B\-{bid[2:]}\s*,[^,]*,[^,]*,[^,]*,[^,]*,[^,]*,[^,]*,{val}\s*$"
        src["why_justification"] = f"{bid} projected should be {val}."
    elif name.startswith("move_b"):
        bid = "B-" + name[-2:]
        mv = by[bid]["recommended_move"]
        esc = re.escape(mv)
        src["expected"] = rf"(?mi)^B\-{bid[2:]}\s*,[^,]*,[^,]*,[^,]*,[^,]*,[^,]*,{esc}\s*,"
        src["why_justification"] = f"{bid} recommended move should be {mv}."
    elif name.startswith("coherence_b"):
        bid = "B-" + name[-2:]
        sc = by[bid]["coherence_score"]
        src["expected"] = rf"(?mi)^B\-{bid[2:]}\s*,[^,]*,[^,]*,[^,]*,[^,]*,{sc}\s*,"
        src["why_justification"] = f"{bid} coherence_score should be {sc}."

mapping = {
    "result_passing_briefs": results["passing_briefs"],
    "result_failing_briefs": results["failing_briefs"],
    "result_avg_score": results["avg_score"],
    "result_total_breaches": results["total_breaches"],
    "result_total_unanswered": results["total_unanswered"],
    "result_brief_count": results["brief_count"],
}
for v in vj["verifiers"]:
    name = v.get("name", "")
    if name not in mapping:
        continue
    src = v.setdefault("source", {})
    if "expected" in src:
        src["expected"] = mapping[name]
    elif "expected" in v:
        v["expected"] = mapping[name]
    else:
        src["expected"] = mapping[name]

# Strengthen memo: must mention each failing brief, must not require passing-only fluff
failing = [r["brief_id"] for r in rows if int(r["coherence_score"]) < 80]
passing = [r["brief_id"] for r in rows if int(r["coherence_score"]) >= 80]
for v in vj["verifiers"]:
    if v.get("name") == "memo_has_body":
        # require all failing ids present
        parts = [rf"(?=.*{re.escape(b)})" for b in failing]
        v.setdefault("source", {})["expected"] = "(?is)" + "".join(parts) + r".{200,}"
        v["source"]["why_justification"] = (
            "Memo must cover each brief below passing score (80) with substantive body."
        )

(PACK / "tests/verifier.json").write_text(json.dumps(vj, indent=2) + "\n", encoding="utf-8")
print("failing", failing)
print("passing", passing)
print("memo headings", re.findall(r"^## (B-\d+)", memo, re.M))
for v in vj["verifiers"]:
    if v["name"] in ("projected_b01", "move_b05", "move_b01", "result_avg_score", "memo_has_body"):
        print(v["name"], "=>", v.get("source", {}).get("expected"))
print("n_verifiers", len(vj["verifiers"]))
