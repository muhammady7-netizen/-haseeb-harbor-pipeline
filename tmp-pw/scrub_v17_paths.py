"""Scrub host paths from v17 evaluation metadata."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(
    "task-sources/law-b39/law-b39-l16-custody-letter-instruction-audit-v17/evaluations"
)


def scrub(s: str) -> str:
    s = s.replace(r"C:\Users\Haseeb Mirza", "/workspace")
    s = s.replace("C:/Users/Haseeb Mirza", "/workspace")
    s = s.replace("C:\\\\Users\\\\Haseeb Mirza", "/workspace")
    s = re.sub(r"[A-Za-z]:\\Users\\[^\\\"']+", "/workspace", s)
    s = re.sub(r"[A-Za-z]:/Users/[^/\"']+", "/workspace", s)
    s = re.sub(
        r"/workspace/Documents/Codex/haseeb-pipeline/task-sources/law-b39/"
        r"law-b39-l16-custody-letter-instruction-audit-v17",
        "/workspace/task",
        s,
    )
    s = re.sub(
        r"\\Documents\\Codex\\haseeb-pipeline\\task-sources\\law-b39\\"
        r"law-b39-l16-custody-letter-instruction-audit-v17",
        r"\\task",
        s,
    )
    return s


def main() -> None:
    sample = (ROOT / "oracle" / "result.json").read_text(encoding="utf-8")
    for line in sample.splitlines():
        if "Users" in line or "Haseeb" in line:
            print("before:", repr(line[:180]))
            break

    n = 0
    for f in ROOT.rglob("*"):
        if not f.is_file():
            continue
        if f.suffix.lower() not in {".json", ".txt", ".log", ".md"}:
            continue
        raw = f.read_text(encoding="utf-8", errors="ignore")
        if "Haseeb" not in raw and "Users\\" not in raw and "Users/" not in raw:
            continue
        new = scrub(raw)
        if new != raw:
            f.write_text(new, encoding="utf-8")
            n += 1
    print("scrubbed", n)

    left = []
    for f in ROOT.rglob("*.json"):
        t = f.read_text(encoding="utf-8", errors="ignore")
        if "Haseeb" in t or re.search(r"Users[/\\]", t):
            left.append(str(f))
    print("remaining", len(left))
    for x in left[:5]:
        print(" ", x)


if __name__ == "__main__":
    main()
