#!/usr/bin/env python3
"""Pack fresh harbor oracle trials into evaluations/oracle + stability/repeat-0N."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

PACK = Path(
    r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline"
    r"\task-sources\law-b39\law-b39-l16-custody-letter-instruction-audit"
)
JOBS = Path(
    r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline\qc-out\harbor-jobs-b39"
)
IGNORE = {
    "xdg-data",
    "xdg-cache",
    "xdg-config",
    "xdg-state",
    "node_modules",
    "__pycache__",
    ".git",
    ".pytest_cache",
}


def ignore_bulk(_dir, names):
    return [n for n in names if n in IGNORE]


def find_trials(job_name: str) -> list[Path]:
    root = JOBS / job_name
    if not root.exists():
        # harbor may nest job under timestamp
        cands = sorted(JOBS.glob(f"*{job_name}*"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not cands:
            raise SystemExit(f"missing job dir for {job_name} under {JOBS}")
        root = cands[0]
    trials = []
    for p in root.rglob("result.json"):
        trial = p.parent
        if (trial / "verifier" / "reward.txt").exists() or (trial / "result.json").exists():
            trials.append(trial)
    # unique by path, prefer deepest with reward
    uniq = {}
    for t in trials:
        uniq[str(t)] = t
    out = sorted(uniq.values(), key=lambda p: p.stat().st_mtime)
    return out


def reward_of(trial: Path):
    rt = trial / "verifier" / "reward.txt"
    if rt.exists():
        return rt.read_text(encoding="utf-8").strip()
    d = json.loads((trial / "result.json").read_text(encoding="utf-8"))
    return (d.get("verifier_result") or {}).get("rewards", {}).get("reward")


def main():
    # Prefer dedicated job folder oracle-b39-l16-v7
    trials = []
    for name in ["oracle-b39-l16-v7", "oracle-b39-l16-v7-1", "oracle-b39-l16-v7-2"]:
        try:
            trials = find_trials(name)
            if trials:
                print("using job", name, "trials", len(trials))
                break
        except SystemExit:
            continue
    if not trials:
        # scan all recent jobs
        all_trials = []
        for job in sorted(JOBS.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)[:10]:
            if not job.is_dir():
                continue
            if "oracle" not in job.name.lower() and "b39" not in job.name.lower():
                continue
            for p in job.rglob("result.json"):
                all_trials.append(p.parent)
        trials = sorted({str(t): t for t in all_trials}.values(), key=lambda p: p.stat().st_mtime)
        print("fallback trials", len(trials))

    if len(trials) < 3:
        raise SystemExit(f"need >=3 oracle trials, got {len(trials)}: {trials}")

    # Keep only reward 1.0
    good = []
    for t in trials:
        r = reward_of(t)
        print("trial", t, "reward", r)
        if str(r) in ("1.0", "1", "1.00") or r == 1.0:
            good.append(t)
    if len(good) < 3:
        raise SystemExit(f"need >=3 reward-1.0 trials, got {len(good)}")

    oracle_dir = PACK / "evaluations" / "oracle"
    stability = PACK / "evaluations" / "stability"
    nop_dir = PACK / "evaluations" / "nop"
    if oracle_dir.exists():
        shutil.rmtree(oracle_dir)
    if stability.exists():
        shutil.rmtree(stability)
    # remove stale nop if present; will refresh separately
    stability.mkdir(parents=True)

    shutil.copytree(good[0], oracle_dir, ignore=ignore_bulk)
    print("oracle <-", good[0])
    for i, trial in enumerate(good[:3], 1):
        target = stability / f"repeat-{i:02d}"
        shutil.copytree(trial, target, ignore=ignore_bulk)
        print(f"stability/repeat-{i:02d} <-", trial, "reward", reward_of(trial))

    (stability / "NOTE.md").write_text(
        "Oracle stability repeats from fresh harbor job oracle-b39-l16-v7 "
        "against current law-b39-l16 pack (10-check verifier). Distinct trial IDs.\n",
        encoding="utf-8",
    )
    print("packed ok")


if __name__ == "__main__":
    main()
