import json
import re
from pathlib import Path

p = Path(
    r"C:\Users\Haseeb Mirza\Documents\Codex\2026-08-17\this-is-the-very-beginning-of\tasks\NONC-B1-1001634\gen-g806-leadership-brief-rhetorical-style-audit\tests\verifier.json"
)
v = json.loads(p.read_text(encoding="utf-8"))
for c in v["verifiers"]:
    n = c["name"]
    m = re.search(r"b(\d+)$", n)
    if not m:
        continue
    brief = f"B-{m.group(1)}"
    if n.startswith("memo_has_"):
        c["assertion"]["expected"] = (
            rf"(?mi)(?:^#{{1,3}}\s*{re.escape(brief)}\b|\*\*{re.escape(brief)}\*\*|"
            rf"{re.escape(brief)}\s*\(score|\b{re.escape(brief)}\b[^\n]{{0,80}}(?:Unanswered|score))"
        )
        c["metadata"]["why_justification"] = (
            f"Memo must cover failing brief {brief} with a recognizable section label."
        )
    elif n.startswith("memo_explains_"):
        c["assertion"]["expected"] = (
            rf"(?is)\b{re.escape(brief)}\b.{{0,800}}Unanswered:.{{0,400}}"
            rf"(?:Transition\s+)?[Bb]reaches:.{{0,400}}Recommended:"
        )
        c["metadata"]["why_justification"] = (
            f"Memo section for {brief} must include Unanswered, breaches, and Recommended."
        )
p.write_text(json.dumps(v, indent=2) + "\n", encoding="utf-8")
print("total", len(v["verifiers"]))
