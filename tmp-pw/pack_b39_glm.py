#!/usr/bin/env python3
"""Pack glm-b39-l16-v10 trials into evaluations/glm-5.2/r1..r4."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

PACK = Path(
    r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline"
    r"\task-sources\law-b39\law-b39-l16-custody-letter-instruction-audit"
)
JOBS = Path(
    r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline"
    r"\qc-out\harbor-jobs-b39"
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


def reward_of(trial: Path):
    rt = trial / "verifier" / "reward.txt"
    if rt.exists():
        return rt.read_text(encoding="utf-8").strip()
    d = json.loads((trial / "result.json").read_text(encoding="utf-8"))
    return (d.get("verifier_result") or {}).get("rewards", {}).get("reward")


def normalize_artifacts(trial_dir: Path) -> None:
    nested = trial_dir / "artifacts" / "logs" / "artifacts" / "app"
    flat = trial_dir / "artifacts" / "app"
    if nested.is_dir():
        flat.parent.mkdir(parents=True, exist_ok=True)
        if flat.exists():
            shutil.rmtree(flat)
        shutil.copytree(nested, flat)
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

    global PACK
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", default="glm-b39-l16-v18")
    ap.add_argument(
        "--pack",
        default=str(PACK),
        help="Task pack root to write evaluations/glm-5.2 into",
    )
    args = ap.parse_args()
    PACK = Path(args.pack)
    job = JOBS / args.job
    if not job.exists():
        raise SystemExit(f"missing job {job}")
    trials = []
    for p in job.rglob("result.json"):
        trial = p.parent
        if not (trial / "verifier" / "reward.txt").exists():
            continue
        # top-level trial dirs only
        if trial.parent != job and trial.parent.parent != job:
            # harbor nests: job/trial_name/
            pass
        trials.append(trial)
    # Prefer unique trial folders directly under job or one level deep
    uniq = {}
    for t in trials:
        uniq[str(t.resolve())] = t
    trials = sorted(uniq.values(), key=lambda p: p.stat().st_mtime)
    # Deduplicate by trial_name
    by_name = {}
    for t in trials:
        try:
            tn = json.loads((t / "result.json").read_text(encoding="utf-8")).get("trial_name", t.name)
        except Exception:
            tn = t.name
        by_name[tn] = t
    trials = list(by_name.values())
    print("trials", len(trials), list(by_name))
    if len(trials) < 4:
        raise SystemExit(f"need 4 glm trials, got {len(trials)}")

    dest = PACK / "evaluations" / "glm-5.2"
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    rewards = []
    for i, trial in enumerate(trials[:4], 1):
        target = dest / f"r{i}"
        shutil.copytree(trial, target, ignore=ignore_bulk)
        normalize_artifacts(target)
        for snap in target.rglob("snapshot"):
            if snap.is_dir():
                shutil.rmtree(snap, ignore_errors=True)
        # strip bulky xdg
        for name in IGNORE:
            p = target / name
            if p.exists():
                shutil.rmtree(p, ignore_errors=True)
        r = reward_of(trial)
        rewards.append(r)
        print(f"r{i}", trial.name, "reward", r)

    passes = sum(1 for r in rewards if str(r) in ("1.0", "1", "1.00") or r == 1.0)
    summary = PACK / "evaluations" / "EVIDENCE_SUMMARY.json"
    data = {}
    if summary.exists():
        try:
            data = json.loads(summary.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
    data["difficulty_glm_5_2"] = {
        "status": "FIXED_AND_VERIFIED",
        "job": args.job,
        "passes": passes,
        "total": 4,
        "rewards": rewards,
        "note": f"GLM-5.2 accuracy@4 = {passes}/4 (strict 1.0 passes)",
    }
    summary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"accuracy@4 = {passes}/4")


if __name__ == "__main__":
    main()
