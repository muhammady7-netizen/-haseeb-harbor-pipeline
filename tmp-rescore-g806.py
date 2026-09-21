import hashlib
import json
import re
from pathlib import Path

PACK = Path(
    r"C:\Users\Haseeb Mirza\Documents\Codex\2026-08-17\this-is-the-very-beginning-of\tasks\NONC-B1-1001634\gen-g806-leadership-brief-rhetorical-style-audit"
)
JOBS = Path(
    r"C:\Users\Haseeb Mirza\Documents\Codex\2026-08-17\this-is-the-very-beginning-of\tasks\NONC-B1-1001634\harbor-jobs"
)
ver = json.loads((PACK / "tests/verifier.json").read_text(encoding="utf-8"))["verifiers"]
gold = PACK / "solution/files"
NAMES = [
    "brief_coherence.csv",
    "question_trace.csv",
    "executive_sequence_memo.md",
    "results.json",
]


def load_texts(app: Path):
    return {p.name: p.read_text(encoding="utf-8") for p in app.glob("*") if p.is_file()}


def score(texts):
    passed = failed = 0
    fails = []
    for c in ver:
        name = c["name"]
        src = c["source"]["file"]
        path = src["arguments"]["path"]
        assertion = c["assertion"]["deterministic"]
        expected = c["assertion"]["expected"]
        comp = assertion["comparison"]
        if src.get("command") == "check_path_exists":
            hit = (path in texts) == bool(expected)
        else:
            text = texts.get(path, "")
            if path.endswith(".json") and assertion["path"].startswith("$."):
                key = assertion["path"][2:]
                try:
                    val = json.loads(text).get(key)
                except Exception:
                    val = None
                hit = val == expected
            elif comp == "regex_match":
                hit = re.search(expected, text) is not None
            elif comp == "not_regex_match":
                hit = re.search(expected, text) is None
            elif comp == "equals":
                hit = text == expected
            else:
                hit = False
        if hit:
            passed += 1
        else:
            failed += 1
            fails.append(name)
    total = passed + failed
    reward = round(passed / total, 6) if total else 0.0
    return reward, passed, failed, fails


def md5s(app: Path):
    out = {}
    for n in NAMES:
        p = app / n
        out[n] = hashlib.md5(p.read_bytes()).hexdigest() if p.exists() else None
    return out


r, p, f, fails = score(load_texts(gold))
print(f"GOLD reward={r} {p}/{p+f} fails={fails[:8]}")
gmd = md5s(gold)

for i in range(1, 5):
    job = JOBS / f"glm-g806-coherence-{i}"
    trials = list(job.glob("gen-g806*"))
    if not trials:
        print(f"r{i}: no trial")
        continue
    t = trials[0]
    app = t / "artifacts" / "app"
    if not app.exists() or not any(app.iterdir()):
        print(f"r{i}: empty artifacts — reward 0.0")
        (t / "verifier" / "reward.txt").write_text("0.0\n", encoding="utf-8")
        (t / "verifier" / "reward.json").write_text(json.dumps({"reward": 0.0}) + "\n", encoding="utf-8")
        continue
    reward, passed, failed, fails = score(load_texts(app))
    print(
        f"r{i}: reward={reward} {passed}/{passed+failed} "
        f"gold_identical={md5s(app)==gmd} sample_fails={fails[:8]}"
    )
    (t / "verifier" / "reward.txt").write_text(f"{reward}\n", encoding="utf-8")
    (t / "verifier" / "reward.json").write_text(json.dumps({"reward": reward}) + "\n", encoding="utf-8")
