"""Re-score old c227 GLM trials: recover files from trajectory writes + cat observations."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

job = Path(
    r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline\qc-out\harbor-jobs-c227\glm-c227-difficulty-v2"
)
pack = Path(
    r"C:\Users\Haseeb Mirza\Documents\Codex\2026-08-17\this-is-the-very-beginning-of\tasks\code-c227-work\code-c227-table-bloat-maintenance-audit"
)
names = ("bloat_audit.csv", "bloat_memo.md", "results.json")


def parse_args(args):
    if isinstance(args, str):
        try:
            return json.loads(args)
        except Exception:
            return {}
    return args if isinstance(args, dict) else {}


def obs_text(obs) -> str:
    if not isinstance(obs, dict):
        return ""
    parts = []
    for r in obs.get("results") or []:
        if isinstance(r, dict):
            for k in ("content", "output", "stdout", "text"):
                v = r.get(k)
                if isinstance(v, str):
                    parts.append(v)
        elif isinstance(r, str):
            parts.append(r)
    return "\n".join(parts)


def extract(traj: Path) -> dict:
    d = json.loads(traj.read_text(encoding="utf-8"))
    files: dict[str, str] = {}
    for s in d.get("steps", []):
        for tc in s.get("tool_calls") or []:
            args = parse_args(tc.get("arguments"))
            path = args.get("path") or args.get("filePath") or args.get("file_path")
            content = args.get("content") or args.get("contents") or args.get("file_text")
            if path and content and any(str(path).endswith(n) for n in names):
                files[Path(str(path)).name] = content
        out = obs_text(s.get("observation"))
        if not out:
            continue
        # Isolated JSON dump
        if "results.json" not in files:
            m = re.search(r"(\{\s*\"flagged_count\".*?\})", out, re.S)
            if m:
                try:
                    json.loads(m.group(1))
                    files["results.json"] = m.group(1)
                except Exception:
                    pass
        # CSV after header
        if "bloat_audit.csv" not in files and "table_name,size_class,bloat_ratio,finding" in out:
            m = re.search(
                r"(table_name,size_class,bloat_ratio,finding\r?\n(?:.*\r?\n)+)",
                out,
            )
            if m:
                files["bloat_audit.csv"] = m.group(1).rstrip() + "\n"
    return files


def score(files: dict) -> tuple[int, int, float, str]:
    ws = Path(tempfile.mkdtemp(prefix="c227-rescore-"))
    try:
        shutil.copytree(pack / "environment" / "input", ws / "input")
        for n, content in files.items():
            (ws / n).write_text(content, encoding="utf-8")
        env = os.environ.copy()
        env["HARBOR_TASK_WORKSPACE"] = str(ws)
        env["PYTHONPATH"] = str(pack / "tests")
        r = subprocess.run(
            ["py", "-3", "-m", "pytest", str(pack / "tests" / "test_outputs.py"), "-q", "--tb=line"],
            cwd=str(ws),
            env=env,
            capture_output=True,
            text=True,
        )
        out = (r.stdout or "") + "\n" + (r.stderr or "")
        m = re.search(r"(\d+)\s+failed.*?(\d+)\s+passed|(\d+)\s+passed(?:,\s*(\d+)\s+failed)?", out)
        if not m:
            return 0, 166, 0.0, out[-800:]
        if m.group(1) and m.group(2):
            failed, passed = int(m.group(1)), int(m.group(2))
        else:
            passed = int(m.group(3))
            failed = int(m.group(4) or 0)
        total = passed + failed
        reward = 1.0 if failed == 0 and total else round(passed / total, 10)
        return passed, total, reward, out
    finally:
        shutil.rmtree(ws, ignore_errors=True)


def main():
    for trial in sorted(p for p in job.iterdir() if p.is_dir()):
        traj = trial / "agent" / "trajectory.json"
        if not traj.exists():
            continue
        files = extract(traj)
        print("====", trial.name)
        print(" files", {k: len(v) for k, v in files.items()})
        if set(names) - set(files):
            print(" missing", set(names) - set(files))
            continue
        passed, total, reward, out = score(files)
        print(f" rescore {passed}/{total} reward={reward}")
        if reward < 1.0:
            fails = [ln for ln in out.splitlines() if ln.startswith("FAILED") or "FAILED" in ln][:12]
            print(" fails", fails)


if __name__ == "__main__":
    main()
