"""Judge code-c227-judge.zip — packaging + content spot checks."""
from __future__ import annotations

import csv
import io
import json
import re
import zipfile
from collections import Counter
from pathlib import Path

Z = Path.home() / "Downloads" / "UPLOAD-THIS-TO-QC-code-c227-judge.zip"
ROOT = "code-c227-table-bloat-maintenance-audit"


def main() -> None:
    findings = []
    with zipfile.ZipFile(Z) as zf:
        names = zf.namelist()

        def read(rel: str) -> bytes:
            return zf.read(f"{ROOT}/{rel}")

        # Structure
        need = [
            "instruction.md",
            "task.toml",
            "review.csv",
            "environment/Dockerfile",
            "tests/test.sh",
            "tests/test_outputs.py",
            "solution/solve.sh",
            "solution/files/bloat_audit.csv",
            "solution/files/bloat_memo.md",
            "solution/files/results.json",
        ]
        for n in need:
            if f"{ROOT}/{n}" not in names:
                findings.append(("P0", f"missing {n}"))

        junk = [n for n in names if any(x in n for x in ("_scratch", ".pytest_cache", "__pycache__", "xdg-", "rl_world"))]
        if junk:
            findings.append(("P1", f"junk in zip: {junk[:5]}"))

        # Dockerfile
        df = read("environment/Dockerfile").decode()
        if "COPY tests" in df or "COPY solution" in df:
            findings.append(("P0", "Dockerfile COPY tests/solution"))
        if "chmod 000 /tests" not in df:
            findings.append(("P1", "no /tests lock marker"))
        if "USER appuser" not in df:
            findings.append(("P1", "no USER appuser"))

        # LF
        for rel in ("tests/test.sh", "tests/test_outputs.py", "solution/solve.sh"):
            if b"\r" in read(rel):
                findings.append(("P0", f"CRLF in {rel}"))

        ts = read("tests/test.sh").decode()
        if "ensure_reward" not in ts and "reward.txt" not in ts:
            findings.append(("P0", "test.sh does not write reward.txt"))

        # review.csv
        rev = read("review.csv").decode()
        for row in csv.DictReader(io.StringIO(rev)):
            st = row.get("status", "")
            ch = (row.get("change_made") or "").strip()
            if st == "PASS" and ch:
                findings.append(("P1", f"PASS+change_made: {row.get('review_check')}"))
            if "1/4" in json.dumps(row) and "0/4" not in json.dumps(row):
                pass
        if "0/4" not in rev and "GLM" in rev:
            findings.append(("P2", "review.csv may lack GLM 0/4"))

        # host paths
        host = []
        for n in names:
            if "evaluations/" not in n:
                continue
            if not n.endswith((".json", ".txt", ".log", ".md")):
                continue
            t = zf.read(n).decode("utf-8", "ignore")
            if re.search(r"/workspace Mirza|Haseeb|C:/Users|C:\\\\Users|user/AppData|user\\\\AppData", t, re.I):
                host.append(n)
        if host:
            findings.append(("P1", f"host paths in {len(host)} files: {host[:3]}"))

        # rewards
        def reward(path: str) -> str | None:
            full = f"{ROOT}/{path}"
            if full not in names:
                return None
            return zf.read(full).decode().strip().splitlines()[0]

        oracle = reward("evaluations/oracle/verifier/reward.txt")
        glm = [reward(f"evaluations/glm-5.2/r{i}/verifier/reward.txt") for i in range(1, 5)]
        stab = [reward(f"evaluations/stability/repeat-0{i}/verifier/reward.txt") for i in range(1, 4)]
        solv = reward("evaluations/solvability/agent-pass/verifier/reward.txt")

        print("oracle", oracle)
        print("glm", glm)
        print("stability", stab)
        print("solvability", solv)

        if oracle != "1.0":
            findings.append(("P0", f"oracle reward={oracle}"))
        if any(s != "1.0" for s in stab if s is not None):
            findings.append(("P0", f"stability not all 1.0: {stab}"))
        if solv != "1.0":
            findings.append(("P1", f"solvability={solv}"))
        if any(g is None for g in glm):
            findings.append(("P0", f"missing glm rewards: {glm}"))
        else:
            strict = sum(1 for g in glm if g == "1.0")
            print("glm_strict_passes", strict, "/4")
            if strict >= 4:
                findings.append(("P0", "GLM 4/4 TOO_EASY"))
            elif strict > 2:
                findings.append(("P2", f"GLM {strict}/4 borderline"))

        # gold vs EXPECTED in test_outputs
        gold_csv = list(csv.DictReader(io.StringIO(read("solution/files/bloat_audit.csv").decode())))
        results = json.loads(read("solution/files/results.json").decode())
        print("gold_rows", len(gold_csv), "results", results)

        # Dockerfile only input
        if "COPY input/" not in df:
            findings.append(("P1", "Dockerfile missing COPY input/"))

        print("\nFINDINGS:")
        if not findings:
            print("NONE — packaging looks ship-ready for local judge")
        else:
            for sev, msg in findings:
                print(f"  [{sev}] {msg}")

        # summary verdict
        p0 = [f for f in findings if f[0] == "P0"]
        p1 = [f for f in findings if f[0] == "P1"]
        if p0:
            verdict = "FAIL — P0 blockers"
        elif p1:
            verdict = "REWORK — P1 issues"
        elif findings:
            verdict = "PASS with P2 advisories"
        else:
            verdict = "PASS — ready to judge/upload"
        print("\nVERDICT:", verdict)
        print("ZIP", Z, Z.stat().st_size)


if __name__ == "__main__":
    main()
