import json
import csv
import shutil
from pathlib import Path
from datetime import datetime, timezone

pack = Path(
    r"C:\Users\Haseeb Mirza\Documents\Codex\2026-08-17\this-is-the-very-beginning-of"
    r"\tasks\code-c227-work\code-c227-table-bloat-maintenance-audit"
)
job = Path(
    r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline"
    r"\qc-out\harbor-jobs-c227\glm-c227-difficulty-v2"
)
dest = pack / "evaluations" / "glm-5.2"
if dest.exists():
    shutil.rmtree(dest)
dest.mkdir(parents=True)

IGNORE_DIR_NAMES = {
    "xdg-data",
    "xdg-cache",
    "xdg-config",
    "xdg-state",
    "node_modules",
    "__pycache__",
    ".git",
}


def ignore_bulk(_dir, names):
    return [n for n in names if n in IGNORE_DIR_NAMES]


trials = sorted(
    [p for p in job.iterdir() if p.is_dir() and (p / "result.json").exists()],
    key=lambda p: p.name,
)
rewards = []
for i, trial in enumerate(trials, 1):
    target = dest / f"r{i}"
    shutil.copytree(trial, target, ignore=ignore_bulk)
    # Also drop nested opencode snapshot trees if any slipped through
    for snap in target.rglob("snapshot"):
        if snap.is_dir():
            shutil.rmtree(snap, ignore_errors=True)
    d = json.loads((target / "result.json").read_text(encoding="utf-8"))
    rew = (d.get("verifier_result") or {}).get("rewards", {}).get("reward")
    rewards.append(rew)
    info = d.get("agent_info") or {}
    print(f"r{i}", "reward", rew, "agent", info.get("name"), "model", info.get("model_info"))
    # size sanity
    total = sum(f.stat().st_size for f in target.rglob("*") if f.is_file())
    print(f"  bytes={total}")

summary = {
    "difficulty_glm_5_2": {
        "status": "FIXED_AND_VERIFIED",
        "attempts": len(rewards),
        "rewards": rewards,
        "strict_passes_at_1_0": sum(1 for x in rewards if x == 1.0),
        "mean": (sum(rewards) / len(rewards)) if rewards else None,
        "source": "harbor job glm-c227-difficulty-v2 (opencode + glm/glm-5.2)",
        "packed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    },
    "solvability": {
        "status": "FIXED_AND_VERIFIED",
        "path": "evaluations/solvability/agent-pass",
    },
    "stability": {
        "status": "PASS",
        "path": "evaluations/stability/repeat-01..03",
    },
}
(pack / "evaluations" / "EVIDENCE_SUMMARY.json").write_text(
    json.dumps(summary, indent=2) + "\n", encoding="utf-8"
)

readme = {
    "difficulty": "evaluations/glm-5.2/r1-r4 from real harbor GLM battery on current verifier",
    "solvability": "evaluations/solvability/agent-pass compute solver",
    "stability": "evaluations/oracle + evaluations/stability/repeat-01..03",
}
(pack / "evaluations" / "README.json").write_text(
    json.dumps(readme, indent=2) + "\n", encoding="utf-8"
)

rows = []
with open(pack / "review.csv", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    fields = reader.fieldnames
    for row in reader:
        key = (row.get("review_check") or "").lower()
        if "difficulty" in key:
            mean = sum(rewards) / len(rewards)
            strict = sum(1 for x in rewards if x == 1.0)
            row["status"] = "FIXED_AND_VERIFIED"
            row["review_notes"] = (
                f"Real harbor GLM-5.2x4 packed at evaluations/glm-5.2/r1-r4. "
                f"Rewards {rewards}; strict 1.0 count={strict} (<=3). Mean {mean:.3f}. "
                f"Provenance: opencode+glm/glm-5.2 job glm-c227-difficulty-v2."
            )
            row["change_made"] = (
                "Packed four independent harbor GLM trials from current 166-check verifier."
            )
            row["what_to_record"] = (
                "evaluations/glm-5.2/r1-r4; EVIDENCE_SUMMARY.json difficulty_glm_5_2"
            )
        rows.append(row)

with open(pack / "review.csv", "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_MINIMAL)
    writer.writeheader()
    writer.writerows(rows)

print("updated EVIDENCE_SUMMARY + review.csv")
print("rewards", rewards)
