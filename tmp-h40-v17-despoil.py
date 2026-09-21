#!/usr/bin/env python3
"""h40 v17 despoil — remove trap spoilers from instruction.md.

Root cause of repeated TOO_EASY (v14/v15/v16 GLM 4/4): densify scripts kept
ADDINGinstruction spoilers that teach every trap. Agents then implement the
spoilered rules perfectly. More CSV rows will not help.

This script:
1. Rewrites instruction.md as a clean task brief (deliverables + Harbor
   fairness contract only). Trap mechanics stay in procedure.md + data.
2. Ensures procedure.md fairly documents clock/role/window rules agents must
   read (incl. weekend core hours + pre-clock notify = 0).
3. Leaves the v16 hard register (105 rows) / gold / escalations / verifiers.
4. Runs pytest against gold workspace and rebuilds upload zips.

Does NOT upload to portal.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline")
PACK = (
    ROOT
    / "qc-out"
    / "ework"
    / "UPLOAD-THIS-TO-QC-health-h40"
    / "health-h40-critical-result-acknowledgement"
)

# Clean brief: contract + Harbor fairness; NO near-miss role lists, NO
# tier-swap lectures, NO recorded-vs-missing lectures, NO pre-clock / weekend
# spoilers (those belong in procedure.md).
CLEAN_INSTRUCTION = """# Task

Audit the critical results register against the trust's critical results procedure. Save `results_audit.csv` with the columns `result_id,tier,clock_start,notification_minutes,acknowledgement_minutes,acknowledged_by_role,escalation_status,findings` covering every result on the register, where the two minute figures are measured from the clock start you derive, `acknowledgement_minutes` is left empty where there is no acknowledgement the procedure recognises, and where present is a whole number (e.g. `5`, not `5.0`), and `findings` lists every finding against that result or records it as compliant. Then write `results_memo.md` covering the late notifications, the late or absent acknowledgements, which results should have been escalated and were not, and which long elapsed times are not breaches at all.

The `findings` column must use only these semicolon-separated category codes: `notification_late` for a late notification, `acknowledgement_late` for a late or absent acknowledgement, `acknowledger_unapproved` for an acknowledgement by a role the procedure does not recognise, `escalation_missing` for a missed acknowledgement window with no escalation on the register, or `compliant` if the result has no finding. A result may carry more than one code, separated by semicolons.

The `escalation_status` column must use one of: `not_required` when the acknowledgement was within its window, `recorded` when the window was missed and an escalation appears on the register, or `missing` when the window was missed and no escalation appears. The `clock_start` column must use ISO 8601 format `YYYY-MM-DDTHH:MM` (e.g. `2026-06-16T08:00`).

The `results_memo.md` must name each result by its ID (e.g. R-03) and explain the finding: late notifications must mention the notification window, late acknowledgements must mention the acknowledgement window, unapproved acknowledgers must be named by role, and missing escalations must note the absence. A memo that merely lists result IDs and finding labels without explaining the breach does not satisfy this requirement.

When an acknowledger role is not approved by the procedure (for example ward_clerk, nurse_hca, or phlebotomist), that entry is not a recognised acknowledgement: leave acknowledgement_minutes empty, record acknowledger_unapproved in findings, and in the memo name the role using the register token (e.g. ward_clerk) or the words unapproved / not on the approved list (prose forms such as "ward clerk" are also acceptable). Where an unapproved role means there is no recognised acknowledgement and the acknowledgement window has been missed, record both `acknowledger_unapproved` and `acknowledgement_late` (and `escalation_missing` when no escalation appears). In the memo, when explaining long elapsed times that are not breaches, state the reason in plain language (for example inclusive window limits or core-hours clock start); naming a particular result ID is optional.

The procedure at `input/critical_results_procedure.md` is the source of truth for approved roles, tier windows, when the clock starts, and escalation. Audit every row in `input/critical_results.csv` against that procedure and the escalation register at `input/escalations.csv`.

- The attachments are provided read-only at: `input/critical_results_procedure.md`; `input/critical_results.csv`; `input/escalations.csv`. Read them there.
- Save your deliverables into your current working directory using exactly these filenames:
    - `results_audit.csv` - Result-level critical results audit
    - `results_memo.md` - Markdown critical results memo
    - `results.json` - a JSON object whose values are integer counts for the keys `notification_breaches`, `acknowledgement_breaches`, `unapproved_acknowledgement_results`, `missing_escalation_results`, `results_compliant` (do not use arrays of result IDs)
- Writing those files is the required deliverable and must be your final action; confirm each one exists before you answer.
- Leave every deliverable in the starting working directory (the same folder you begin in). Do not nest them under `output/` or any other subdirectory.
"""

# Spoiler fingerprints that must be gone from instruction.md after rewrite.
SPOILER_NEEDLES = [
    "specialty_doctor",
    "senior_house_officer",
    "st_registrar",
    "locum_registrar",
    "staff_grade",
    "foundation_doctor",
    "clinical_scientist",
    "consultant_on_call",
    "near-miss",
    "do not borrow tier-1",
    "borrow tier-1 limits",
    "recorded (not missing)",
    "recorded not missing",
    "before the tier-2 clock has started",
    "notification_minutes 0 from clock start",
    "even on a weekend",
    "nurse_practitioner or locum_consultant",
]

# Harbor fairness residual lines that MUST remain.
FAIRNESS_NEEDLES = [
    "leave acknowledgement_minutes empty",
    "both `acknowledger_unapproved` and `acknowledgement_late`",
    "ward_clerk",
]


def ensure_procedure_complete(text: str) -> str:
    """Keep procedure as the fair source of truth; add missing clock nuance."""
    out = text
    if "including weekends" not in out.lower() and "every calendar day" not in out.lower():
        # Clarify weekends without naming specific trap rows.
        out = out.replace(
            "For a **tier 2** result the clock runs in core hours, 08:00 to\n"
            "18:00.",
            "For a **tier 2** result the clock runs in core hours, 08:00 to\n"
            "18:00, on every calendar day including weekends.",
            1,
        )
    if "before the clock has started" not in out.lower() and "before clock start" not in out.lower():
        insert = (
            " If a telephone notification is recorded before the tier-2 clock "
            "has started, treat it as occurring at clock start "
            "(notification_minutes measured from clock start is 0)."
        )
        anchor = (
            'Once the clock has started it runs without pausing; "core hours only" '
            "refers to when\nthe clock may start, not when it ticks."
        )
        if anchor in out:
            out = out.replace(anchor, anchor + insert, 1)
        else:
            # Fallback: append under When the clock starts
            out = out.rstrip() + "\n\n" + insert.strip() + "\n"
    # Exact-token matching is already implied by the bullet list; make it explicit
    # without enumerating near-miss trap titles.
    if "exact register token" not in out.lower() and "exact token" not in out.lower():
        out = out.replace(
            "An acknowledgement recorded against any other role is **not** an acknowledgement.",
            "Roles must match the approved list as exact register tokens. "
            "An acknowledgement recorded against any other role is **not** an acknowledgement.",
            1,
        )
    return out


def rewrite_instruction() -> tuple[int, int]:
    path = PACK / "instruction.md"
    before = path.read_text(encoding="utf-8")
    before_len = len(before)
    # Backup current (spoiled) instruction once.
    bak = PACK / "instruction.md.bak-pre-v17-despoil"
    if not bak.exists():
        bak.write_text(before, encoding="utf-8", newline="\n")
    path.write_text(CLEAN_INSTRUCTION, encoding="utf-8", newline="\n")
    after = path.read_text(encoding="utf-8")
    return before_len, len(after)


def update_procedure() -> bool:
    path = PACK / "environment" / "input" / "critical_results_procedure.md"
    before = path.read_text(encoding="utf-8")
    after = ensure_procedure_complete(before)
    if after != before:
        bak = PACK / "environment" / "input" / "critical_results_procedure.md.bak-pre-v17"
        if not bak.exists():
            bak.write_text(before, encoding="utf-8", newline="\n")
        path.write_text(after, encoding="utf-8", newline="\n")
        return True
    return False


def assert_despoiled() -> None:
    instr = (PACK / "instruction.md").read_text(encoding="utf-8").lower()
    missing_fair = [n for n in FAIRNESS_NEEDLES if n.lower() not in instr]
    if missing_fair:
        raise SystemExit(f"Harbor fairness lines missing from instruction: {missing_fair}")
    present_spoilers = [n for n in SPOILER_NEEDLES if n.lower() in instr]
    if present_spoilers:
        raise SystemExit(f"Spoilers still present in instruction: {present_spoilers}")
    # Procedure must carry the rules agents need to derive.
    proc = (
        PACK / "environment" / "input" / "critical_results_procedure.md"
    ).read_text(encoding="utf-8").lower()
    for needle in (
        "consultant",
        "specialty_registrar",
        "240 minutes",
        "480 minutes",
        "08:00",
        "18:00",
    ):
        if needle not in proc:
            raise SystemExit(f"procedure.md missing expected content: {needle}")
    if "weekend" not in proc and "every calendar day" not in proc:
        raise SystemExit("procedure.md missing weekend/core-hours every-day note")
    if "notification_minutes" not in proc and "before the tier-2 clock" not in proc:
        raise SystemExit("procedure.md missing pre-clock notify rule")


def register_row_count() -> int:
    import csv

    path = PACK / "environment" / "input" / "critical_results.csv"
    with path.open(encoding="utf-8-sig", newline="") as f:
        return sum(1 for _ in csv.DictReader(f))


def run_pytest() -> int:
    tests = PACK / "tests"
    ws = Path(tempfile.mkdtemp(prefix="h40-v17-gold-"))
    for name in ("results_audit.csv", "results_memo.md", "results.json"):
        shutil.copy2(PACK / "solution" / "files" / name, ws / name)
    inp = ws / "input"
    inp.mkdir()
    for name in (
        "critical_results.csv",
        "escalations.csv",
        "critical_results_procedure.md",
    ):
        src = PACK / "environment" / "input" / name
        if src.exists():
            shutil.copy2(src, inp / name)
    env = os.environ.copy()
    env["HARBOR_TASK_WORKSPACE"] = str(ws)
    print("workspace", ws)
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(tests / "test_outputs.py"),
            "-q",
            "--tb=line",
        ],
        cwd=str(tests),
        env=env,
        capture_output=True,
        text=True,
    )
    print(proc.stdout)
    if proc.stderr:
        print(proc.stderr[-3000:])
    print("pytest_returncode", proc.returncode)
    m = re.search(r"(\d+) passed", proc.stdout)
    if m:
        print("PASSED", m.group(1))
    m2 = re.search(r"(\d+) failed", proc.stdout)
    if m2:
        print("FAILED", m2.group(1))
    return proc.returncode


def rebuild_zips() -> int:
    ignore = {".DS_Store", "__pycache__", ".git", ".pytest_cache"}
    tmp = ROOT / "UPLOAD-THIS-TO-QC-health-h40.zip"
    if tmp.exists():
        tmp.unlink()
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in PACK.rglob("*"):
            if not path.is_file():
                continue
            if any(part in ignore or part.endswith(".pyc") for part in path.parts):
                continue
            if path.name.endswith(".zip"):
                continue
            # Keep bak files out of the upload zip
            if ".bak-" in path.name or path.name.endswith(".bak"):
                continue
            arc = (Path(PACK.name) / path.relative_to(PACK)).as_posix()
            zf.write(path, arcname=arc)
    size = tmp.stat().st_size
    print("built", tmp, size)
    dests = [
        Path(r"C:\Users\Haseeb Mirza\Downloads\UPLOAD-THIS-TO-QC-health-h40.zip"),
        ROOT / "sessions" / "E" / "zips" / "UPLOAD-THIS-TO-QC-health-h40.zip",
        ROOT / "canonical-zips" / "UPLOAD-THIS-TO-QC-health-h40.zip",
    ]
    for d in dests:
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(tmp, d)
        print(d.stat().st_size, d)
    return size


def main() -> int:
    before_len, after_len = rewrite_instruction()
    proc_changed = update_procedure()
    assert_despoiled()
    n_rows = register_row_count()
    print(f"instruction_before_len={before_len}")
    print(f"instruction_after_len={after_len}")
    print(f"procedure_updated={proc_changed}")
    print(f"register_rows={n_rows}")
    if n_rows != 105:
        print(f"WARNING: expected 105 register rows, got {n_rows}")

    rc = run_pytest()
    if rc != 0:
        print("pytest failed; skipping zip rebuild")
        return rc

    size = rebuild_zips()
    print(f"zip_size={size}")
    print("despoil_ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
