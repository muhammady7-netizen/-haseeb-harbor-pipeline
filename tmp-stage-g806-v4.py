"""Post-process v4 Harbor trials: honest manifests from /logs/artifacts export."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

JOBS = Path(
    r"C:\Users\Haseeb Mirza\Documents\Codex\2026-08-17\this-is-the-very-beginning-of\tasks\NONC-B1-1001634\harbor-jobs"
)
DELIVERABLES = (
    "brief_coherence.csv",
    "question_trace.csv",
    "executive_sequence_memo.md",
    "results.json",
)


def find_files(trial: Path) -> dict[str, Path]:
    found: dict[str, Path] = {}
    roots = [
        trial / "artifacts" / "logs" / "artifacts" / "app",
        trial / "artifacts" / "app",
        trial / "artifacts",
        trial / "verifier" / "snapshots" / "app",
    ]
    for root in roots:
        if not root.is_dir():
            continue
        for name in DELIVERABLES:
            p = root / name
            if p.is_file() and name not in found:
                # reject contaminated pane dumps
                text = p.read_text(encoding="utf-8", errors="replace")
                if "root@" in text:
                    continue
                found[name] = p
        if len(found) == 4:
            break
    return found


def write_manifest(path: Path, files: dict[str, Path] | None, *, status: str, note: str) -> None:
    entries = []
    for name in DELIVERABLES:
        entry = {
            "source": f"/app/{name}",
            "destination": f"verifier/snapshots/app/{name}",
            "logs_artifacts": f"/logs/artifacts/app/{name}",
            "type": "file",
            "status": status,
            "note": note,
        }
        if files and name in files:
            data = files[name].read_bytes()
            entry["sha256"] = hashlib.sha256(data).hexdigest()
            entry["bytes"] = len(data)
        entries.append(entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")


def stage(trial: Path) -> None:
    files = find_files(trial)
    dest = trial / "artifacts" / "app"
    snap = trial / "verifier" / "snapshots" / "app"
    if len(files) == 4:
        dest.mkdir(parents=True, exist_ok=True)
        snap.mkdir(parents=True, exist_ok=True)
        staged = {}
        for name, src in files.items():
            shutil.copy2(src, dest / name)
            shutil.copy2(src, snap / name)
            staged[name] = dest / name
        write_manifest(
            trial / "artifacts" / "manifest.json",
            staged,
            status="captured",
            note="Copied from Harbor /logs/artifacts (graded /app state persisted by tests/test.sh).",
        )
        print(f"OK {trial.parent.name}/{trial.name}: captured 4 clean files")
    else:
        if dest.exists():
            shutil.rmtree(dest)
        if snap.exists():
            shutil.rmtree(snap)
        write_manifest(
            trial / "artifacts" / "manifest.json",
            None,
            status="failed",
            note="No clean graded deliverables present after trial (agent produced nothing or export empty).",
        )
        print(f"EMPTY {trial.parent.name}/{trial.name}: files={list(files)}")


def main() -> None:
    for name in [
        "oracle-g806-v4",
        "oracle-g806-v4-s1",
        "oracle-g806-v4-s2",
        "oracle-g806-v4-s3",
        "glm-g806-v4b-1",
        "glm-g806-v4b-2",
        "glm-g806-v4b-3",
        "glm-g806-v4b-4",
    ]:
        job = JOBS / name
        if not job.exists():
            print("missing job", name)
            continue
        trials = list(job.glob("gen-g806*"))
        if not trials:
            print("no trial", name)
            continue
        stage(trials[0])
        rw = trials[0] / "verifier" / "reward.txt"
        meta = trials[0] / "verifier" / "reward_meta.txt"
        print(
            "  reward",
            rw.read_text().strip() if rw.exists() else None,
            "meta",
            meta.read_text().replace("\n", " ").strip() if meta.exists() else None,
        )


if __name__ == "__main__":
    main()
