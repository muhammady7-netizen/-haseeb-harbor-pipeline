import re, json
from pathlib import Path

pack = Path(r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline\task-sources\law-b39\law-b39-l16-custody-letter-instruction-audit")
text = (pack / "solution/files/answer.md").read_text(encoding="utf-8")
spec = json.loads((pack / "tests/verifier.json").read_text(encoding="utf-8"))
for v in spec["verifiers"]:
    if v["name"].startswith("answer_"):
        pat = v["assertion"]["expected"]
        cmp_ = v["assertion"]["deterministic"]["comparison"]
        m = re.search(pat, text)
        ok = (m is not None) if cmp_ == "regex_match" else (m is None)
        print(f"{v['name']}: tag={v['metadata']['tag']} cmp={cmp_} ok={ok}")

fig = next(v["assertion"]["expected"] for v in spec["verifiers"] if v["name"] == "answer_at_odds_figure")
print("empty figure match", bool(re.search(fig, "")))
for sample in [
    "Letter lines at odds with the record: 18\n",
    "\n\n**Letter lines at odds with the record:** **18**\n",
    "  Letter lines at odds with the record: eighteen\n",
    "# Review\n\nLetter lines at odds with the record: 18\n",
]:
    print("sample ok", bool(re.search(fig, sample)), repr(sample[:50]))
