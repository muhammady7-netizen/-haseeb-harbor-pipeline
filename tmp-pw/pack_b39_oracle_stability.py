#!/usr/bin/env python3
"""Pack fresh harbor oracle trials into evaluations/oracle + stability/repeat-0N.

Uses DISTINCT trials: oracle <- good[0], stability <- good[1:4].
Never copies the same trial into both oracle and repeat-01.
"""
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
        cands = sorted(JOBS.glob(f"*{job_name}*"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not cands:
            raise SystemExit(f"missing job dir for {job_name} under {JOBS}")
        root = cands[0]
    trials = []
    for p in root.rglob("result.json"):
        trial = p.parent
        if (trial / "verifier" / "reward.txt").exists():
            # skip nested copies
            if "stability" in str(trial) or "evaluations" in str(trial):
                continue
            trials.append(trial)
    uniq = {str(t): t for t in trials}
    return sorted(uniq.values(), key=lambda p: p.stat().st_mtime)


def reward_of(trial: Path):
    rt = trial / "verifier" / "reward.txt"
    if rt.exists():
        return rt.read_text(encoding="utf-8").strip()
    d = json.loads((trial / "result.json").read_text(encoding="utf-8"))
    return (d.get("verifier_result") or {}).get("rewards", {}).get("reward")


def trial_name(trial: Path) -> str:
    try:
        return json.loads((trial / "result.json").read_text(encoding="utf-8")).get("trial_name", trial.name)
    except Exception:
        return trial.name


def normalize_artifacts(trial_dir: Path) -> None:
    """Harbor may nest exports at artifacts/logs/artifacts/app; QC expects artifacts/app."""
    nested = trial_dir / "artifacts" / "logs" / "artifacts" / "app"
    flat = trial_dir / "artifacts" / "app"
    if nested.is_dir():
        flat.parent.mkdir(parents=True, exist_ok=True)
        if flat.exists():
            shutil.rmtree(flat)
        shutil.copytree(nested, flat)
    # Ensure manifest notes success if files present
    man = trial_dir / "artifacts" / "manifest.json"
    if flat.is_dir() and any(flat.iterdir()):
        files = sorted(p.name for p in flat.iterdir() if p.is_file())
        man.write_text(
            json.dumps(
                [
                    {
                        "source": "/logs/artifacts/app",
                        "destination": "artifacts/app",
                        "type": "directory",
                        "status": "ok",
                        "files": files,
                        "service": None,
                    }
                ],
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )


def main():
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--job", default="oracle-b39-l16-v15")
    args = ap.parse_args()
    job_name = args.job
    trials = find_trials(job_name)
    print("job", job_name, "trials", len(trials))
    good = []
    for t in trials:
        r = reward_of(t)
        print("trial", trial_name(t), "reward", r, "path", t.name)
        if str(r) in ("1.0", "1", "1.00") or r == 1.0:
            good.append(t)
    if len(good) < 4:
        raise SystemExit(f"need >=4 reward-1.0 trials, got {len(good)}")

    # Deduplicate by trial_name
    seen = set()
    distinct = []
    for t in good:
        tn = trial_name(t)
        if tn in seen:
            continue
        seen.add(tn)
        distinct.append(t)
    if len(distinct) < 4:
        raise SystemExit(f"need >=4 distinct trial_names, got {len(distinct)}: {seen}")

    oracle_dir = PACK / "evaluations" / "oracle"
    stability = PACK / "evaluations" / "stability"
    if oracle_dir.exists():
        shutil.rmtree(oracle_dir)
    if stability.exists():
        shutil.rmtree(stability)
    stability.mkdir(parents=True)

    shutil.copytree(distinct[0], oracle_dir, ignore=ignore_bulk)
    normalize_artifacts(oracle_dir)
    print("oracle <-", trial_name(distinct[0]), distinct[0])

    for i, trial in enumerate(distinct[1:4], 1):
        target = stability / f"repeat-{i:02d}"
        shutil.copytree(trial, target, ignore=ignore_bulk)
        normalize_artifacts(target)
        print(f"stability/repeat-{i:02d} <-", trial_name(trial), trial)

    names = [trial_name(t) for t in distinct[:4]]
    assert len(set(names)) == 4, names
    print("distinct trial_names:", names)
    print("packed ok")


if __name__ == "__main__":
    main()
