from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from .registry_io import load_machine, set_status, utc_now


SEVERITY_RANK = {"P0": 0, "P1": 1, "P2": 2, "INFO": 3}


def _resolve_api_key(machine: dict[str, Any]) -> None:
    env_name = machine.get("api_key_env", "WANDB_GLM_API_KEY")
    if os.environ.get(env_name):
        return
    # Fallbacks commonly set by setup-session.ps1
    for alt in ("OPENAI_API_KEY", "GLM_API_KEY"):
        if os.environ.get(alt):
            os.environ[env_name] = os.environ[alt]
            return


def run_preqc(
    task: dict[str, Any],
    *,
    full_model: bool = False,
    mode: str | None = None,
) -> dict[str, Any]:
    machine = load_machine()
    pack = Path(task["pack_path"])
    if not pack.is_dir() or not (pack / "task.toml").is_file():
        raise FileNotFoundError(f"Task pack missing or no task.toml: {pack}")

    script = Path(machine["preqc_script"])
    config = Path(machine["preqc_config"])
    if not script.is_file():
        raise FileNotFoundError(f"PreQC script missing: {script}")

    out_root = Path(machine.get("qc_out_root") or (Path(__file__).resolve().parents[1] / "qc-out"))
    out_dir = out_root / task["id"] / utc_now().replace(":", "")
    out_dir.mkdir(parents=True, exist_ok=True)

    set_status(task, "preqc_running", next_action="Wait for PreQC")
    _resolve_api_key(machine)

    cmd = [
        sys.executable,
        str(script),
        "--task",
        str(pack),
        "--output-dir",
        str(out_dir),
        "--config",
        str(config),
    ]
    if not full_model:
        cmd.append("--no-model")
    if mode:
        cmd.extend(["--mode", mode])

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["NO_COLOR"] = "1"

    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, encoding="utf-8", errors="replace")
    report_path = out_dir / "qc-report.json"
    findings_csv = out_dir / "findings.csv"
    verdict_md = out_dir / "verdict.md"

    result: dict[str, Any] = {
        "ok": proc.returncode == 0 and report_path.is_file(),
        "returncode": proc.returncode,
        "out_dir": str(out_dir),
        "report_path": str(report_path) if report_path.is_file() else None,
        "stdout_tail": (proc.stdout or "")[-4000:],
        "stderr_tail": (proc.stderr or "")[-4000:],
    }

    if report_path.is_file():
        report = json.loads(report_path.read_text(encoding="utf-8-sig"))
        verdicts = report.get("verdicts") or {}
        findings = report.get("findings") or []
        blocking = [
            f
            for f in findings
            if not f.get("duplicate_of")
            and f.get("severity") in ("P0", "P1")
            and f.get("blocks")
        ]
        # Some findings omit blocks=true; treat P0 always as must-fix locally.
        p0 = [f for f in findings if not f.get("duplicate_of") and f.get("severity") == "P0"]
        must_fix = blocking or p0
        qc_verdict = verdicts.get("qc_verdict") or verdicts.get("review_verdict") or "UNKNOWN"
        result.update(
            {
                "qc_verdict": qc_verdict,
                "review_verdict": verdicts.get("review_verdict"),
                "finding_counts": verdicts.get("counts") or _count_severities(findings),
                "must_fix_count": len(must_fix),
                "must_fix": [
                    {
                        "id": f.get("id"),
                        "severity": f.get("severity"),
                        "title": f.get("title"),
                        "recommended_fix": f.get("recommended_fix"),
                        "gate": f.get("gate"),
                    }
                    for f in sorted(must_fix, key=lambda x: SEVERITY_RANK.get(x.get("severity", "INFO"), 9))[:25]
                ],
            }
        )
        task["last_preqc"] = {
            "at": utc_now(),
            "out_dir": str(out_dir),
            "qc_verdict": qc_verdict,
            "full_model": full_model,
            "must_fix_count": len(must_fix),
            "finding_counts": result["finding_counts"],
            "verdict_md": str(verdict_md) if verdict_md.is_file() else None,
            "findings_csv": str(findings_csv) if findings_csv.is_file() else None,
        }

        if must_fix or qc_verdict == "FAIL":
            set_status(
                task,
                "preqc_needs_fix",
                note=f"PreQC {qc_verdict}; {len(must_fix)} must-fix",
                next_action="Fix PreQC findings then re-run: python -m pipeline.resume preqc --task "
                + task["id"],
            )
            result["status"] = "preqc_needs_fix"
        else:
            set_status(
                task,
                "preqc_clean",
                note=f"PreQC {qc_verdict}; ready to package",
                next_action="Package zip: python -m pipeline.resume package --task " + task["id"],
            )
            result["status"] = "preqc_clean"
    else:
        set_status(
            task,
            "blocked",
            note=f"PreQC failed rc={proc.returncode}",
            next_action="Check stderr and PreQC paths in machine.json",
        )
        result["status"] = "blocked"

    # Compact findings digest for agents
    if findings_csv.is_file():
        result["findings_preview"] = _preview_findings_csv(findings_csv, limit=15)

    return result


def _count_severities(findings: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for f in findings:
        if f.get("duplicate_of"):
            continue
        sev = f.get("severity") or "INFO"
        counts[sev] = counts.get(sev, 0) + 1
    return counts


def _preview_findings_csv(path: Path, limit: int = 15) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if row.get("duplicate_of"):
                continue
            rows.append(
                {
                    "severity": row.get("severity", ""),
                    "title": (row.get("title") or "")[:160],
                    "fix": (row.get("recommended_fix") or "")[:160],
                }
            )
            if len(rows) >= limit:
                break
    return rows
