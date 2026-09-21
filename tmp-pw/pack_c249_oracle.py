import json
import shutil
from pathlib import Path

pack = Path(
    r"C:\Users\Haseeb Mirza\Documents\Codex\2026-08-17\this-is-the-very-beginning-of"
    r"\tasks\code-c249-work\code-c249-recurring-report-source-selection-audit"
)
job = Path(
    r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline"
    r"\qc-out\harbor-jobs-c249\oracle-c249-stability-v4"
)

IGNORE = {
    "xdg-data",
    "xdg-cache",
    "xdg-config",
    "xdg-state",
    "node_modules",
    "__pycache__",
    ".git",
}


def ignore_bulk(_dir, names):
    return [n for n in names if n in IGNORE]


trials = sorted(
    [p for p in job.iterdir() if p.is_dir() and (p / "result.json").exists()],
    key=lambda p: p.name,
)
if len(trials) < 3:
    raise SystemExit(f"expected >=3 oracle trials, got {len(trials)}")

oracle_dir = pack / "evaluations" / "oracle"
stability = pack / "evaluations" / "stability"
if oracle_dir.exists():
    shutil.rmtree(oracle_dir)
if stability.exists():
    shutil.rmtree(stability)
stability.mkdir(parents=True)

# First trial -> oracle; next three -> stability repeats
shutil.copytree(trials[0], oracle_dir, ignore=ignore_bulk)
print("oracle", trials[0].name)
for i, trial in enumerate(trials[:3], 1):
    target = stability / f"repeat-{i:02d}"
    shutil.copytree(trial, target, ignore=ignore_bulk)
    d = json.loads((target / "result.json").read_text(encoding="utf-8"))
    rew = (d.get("verifier_result") or {}).get("rewards", {}).get("reward")
    print(f"repeat-{i:02d}", trial.name, "reward", rew)

note = stability / "NOTE.md"
note.write_text(
    "Oracle stability repeats from harbor job oracle-c249-stability-v4 "
    "on densified 59-check pack. Distinct trial IDs.\n",
    encoding="utf-8",
)
print("oracle/stability refreshed")
