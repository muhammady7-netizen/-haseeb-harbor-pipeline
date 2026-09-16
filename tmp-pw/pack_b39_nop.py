import shutil
from pathlib import Path

pack = Path(
    r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline"
    r"\task-sources\law-b39\law-b39-l16-custody-letter-instruction-audit"
)
job = Path(
    r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline\qc-out\harbor-jobs-b39\nop-b39-l16-v7"
)
trials = [
    p.parent
    for p in job.rglob("result.json")
    if (p.parent / "verifier" / "reward.txt").exists()
]
print("nop trials", trials)
if not trials:
    raise SystemExit("no nop trial")
dest = pack / "evaluations" / "nop"
if dest.exists():
    shutil.rmtree(dest)


def ignore(_d, names):
    return [
        n
        for n in names
        if n
        in {
            "xdg-data",
            "xdg-cache",
            "xdg-config",
            "xdg-state",
            "node_modules",
            "__pycache__",
            ".git",
            ".pytest_cache",
        }
    ]


shutil.copytree(trials[0], dest, ignore=ignore)
print(
    "packed nop from",
    trials[0],
    "reward",
    (trials[0] / "verifier" / "reward.txt").read_text(encoding="utf-8").strip(),
)
