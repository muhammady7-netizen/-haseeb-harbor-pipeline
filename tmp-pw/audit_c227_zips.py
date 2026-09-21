"""Audit code-c227 upload zip for common Harbor/QC defects."""
from __future__ import annotations

import csv
import io
import json
import re
import zipfile
from collections import Counter
from pathlib import Path

ZIPS = [
    Path.home() / "Downloads" / "UPLOAD-THIS-TO-QC-code-c227.zip",
    Path.home() / "Downloads" / "UPLOAD-THIS-TO-QC-code-c227-v3.zip",
    Path(
        r"C:\Users\Haseeb Mirza\Documents\Codex\2026-08-17\this-is-the-very-beginning-of\tasks\code-c227-work\UPLOAD-THIS-TO-QC-code-c227.zip"
    ),
]


def audit(zpath: Path) -> None:
    print("\n" + "=" * 72)
    print("ZIP", zpath.name, zpath.stat().st_size)
    with zipfile.ZipFile(zpath) as zf:
        names = zf.namelist()
        roots = sorted({n.split("/")[0] for n in names if n.strip()})
        print("roots", roots)
        # find task root
        task_roots = [r for r in roots if "c227" in r.lower() or "bloat" in r.lower()]
        if not task_roots:
            task_roots = [r for r in roots if r not in {"__MACOSX"}]
        root = task_roots[0] if task_roots else roots[0]
        print("task_root", root)

        def has(suf: str) -> bool:
            return any(n == f"{root}/{suf}" or n.endswith(f"/{suf}") for n in names)

        checks = {
            "instruction.md": has("instruction.md"),
            "task.toml": has("task.toml"),
            "review.csv": has("review.csv"),
            "Dockerfile": any("environment/Dockerfile" in n for n in names),
            "test.sh": any(n.endswith("tests/test.sh") for n in names),
            "solve.sh": any(n.endswith("solution/solve.sh") for n in names),
            "verifier.json": any(n.endswith("tests/verifier.json") for n in names),
        }
        print("presence", checks)

        # nested duplicate?
        nested = [n for n in names if n.count(root) >= 2 or f"{root}/{root}/" in n]
        print("nested_dup_entries", len(nested))

        # junk
        junk = [
            n
            for n in names
            if any(
                x in n
                for x in (
                    "__pycache__",
                    ".pytest_cache",
                    ".git/",
                    "xdg-",
                    "node_modules",
                    ".DS_Store",
                    "__MACOSX",
                )
            )
        ]
        print("junk", len(junk), junk[:5])

        # Dockerfile
        dfn = next(n for n in names if n.endswith("environment/Dockerfile"))
        df = zf.read(dfn).decode("utf-8", "replace")
        print("COPY_tests", "COPY tests" in df or "COPY ./tests" in df)
        print("COPY_solution", "COPY solution" in df)
        print("chmod_000_tests", "chmod 000 /tests" in df)
        print("USER_appuser", "USER appuser" in df)
        print("Dockerfile_CRLF", "\r\n" in df)

        # test.sh LF + restore
        tsn = next(n for n in names if n.endswith("tests/test.sh"))
        ts = zf.read(tsn)
        print("test.sh_CRLF", b"\r\n" in ts or b"\r" in ts)
        print("test.sh_BOM", ts.startswith(b"\xef\xbb\xbf"))
        print("test.sh_restore", b"chmod 755 /tests" in ts)
        print("test.sh_reward", b"reward.txt" in ts)

        # all tests CRLF
        crlf = []
        for n in names:
            if "/tests/" in n and not n.endswith("/"):
                b = zf.read(n)
                if b"\r" in b:
                    crlf.append(n.split(root + "/")[-1])
        print("tests_CRLF_count", len(crlf), crlf[:8])

        # host paths in evaluations
        host = []
        for n in names:
            if "evaluations/" not in n:
                continue
            if not n.endswith((".json", ".txt", ".log", ".md")):
                continue
            try:
                t = zf.read(n).decode("utf-8", "ignore")
            except Exception:
                continue
            if re.search(r"/Users/|C:\\\\Users|C:/Users|Haseeb", t, re.I):
                host.append(n.split(root + "/")[-1])
        print("host_path_files", len(host), host[:8])

        # review.csv
        rn = next(n for n in names if n.endswith("review.csv") and "/evaluations/" not in n)
        rev = zf.read(rn).decode("utf-8", "replace")
        rows = list(csv.DictReader(io.StringIO(rev)))
        print("review_rows", len(rows))
        statuses = Counter(r.get("status") or r.get("Status") or list(r.values())[1] for r in rows)
        print("review_statuses", dict(statuses))
        # PASS with change_made?
        for r in rows:
            vals = list(r.values())
            status = r.get("status") or (vals[1] if len(vals) > 1 else "")
            change = r.get("change_made") or (vals[3] if len(vals) > 3 else "")
            if status == "PASS" and (change or "").strip():
                print("WARN PASS+change", vals[0][:60])

        # evaluations presence
        evals = [n for n in names if "/evaluations/" in n]
        print("eval_files", len(evals))
        for kind in ("oracle", "stability", "glm", "difficulty", "solvability"):
            print(f"  has_{kind}", any(f"/evaluations/{kind}" in n or f"/evaluations/glm" in n for n in names) if kind == "glm" else any(f"/evaluations/{kind}" in n for n in names))

        # rewards
        rewards = []
        for n in names:
            if n.endswith("reward.txt") or n.endswith("reward.json"):
                try:
                    rewards.append((n.split(root + "/")[-1], zf.read(n).decode().strip()[:40]))
                except Exception:
                    pass
        print("rewards", rewards[:12])

        # solve.sh
        sn = next((n for n in names if n.endswith("solution/solve.sh")), None)
        if sn:
            sb = zf.read(sn)
            print("solve_CRLF", b"\r" in sb)
            print("solve_head", sb[:80])

        # golden / solution files
        sol = [n for n in names if "/solution/" in n]
        print("solution_files", len(sol))


def main() -> None:
    for z in ZIPS:
        if z.exists():
            try:
                audit(z)
            except Exception as e:
                print("FAIL", z, e)


if __name__ == "__main__":
    main()
