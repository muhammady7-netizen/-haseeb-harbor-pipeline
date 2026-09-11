"""Add one fair densify trap (RUN-38) to code-c249; regen gold+verifier; pytest."""
from __future__ import annotations

import csv
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

PACK = Path(
    r"C:\Users\Haseeb Mirza\Documents\Codex\2026-08-17"
    r"\this-is-the-very-beginning-of\tasks\code-c249-work"
    r"\code-c249-recurring-report-source-selection-audit"
)

CUTOVER = date(2026, 7, 6)
WEEKLY_JOBS = {"weekly-journal-brief", "week-ahead-briefing"}
REQUIRED_JOBS = ("weekly-journal-brief", "week-ahead-briefing", "monthly-report")
AUDIT_FIELDS = (
    "run_id",
    "job_name",
    "run_date",
    "source_used",
    "reported_row_count",
    "finding",
)

# Mirror of RUN-37: pre-cutover archive/ROW_COUNT + live/SOURCE → keep live/SOURCE
NEW_LOG_ROWS = [
    "RUN-38,weekly-journal-brief,2026-06-22,archive,301,300",
    "RUN-38,weekly-journal-brief,2026-06-22,live,300,300",
]

CONN = (
    r"because|used|uses|using|should|instead|expected|"
    r"required|premature|reported|against|vs\.?|versus|"
    r"although|while|whereas|over|rather|"
    r"pulled|kept|chose|selected|skipped|missing|empty"
)


def append_log() -> None:
    path = PACK / "environment" / "input" / "report_run_log.csv"
    text = path.read_text(encoding="utf-8")
    if "RUN-38," in text:
        print("log already has RUN-38")
        return
    path.write_text(text.rstrip("\n") + "\n" + "\n".join(NEW_LOG_ROWS) + "\n", encoding="utf-8")
    print("appended RUN-38 trap rows")


def _compute_finding(row: dict[str, str], first_post: str | None) -> str:
    job = row.get("job_name", "")
    run_date_s = row.get("run_date", "")
    source = row.get("source_used", "")
    reported = row.get("reported_row_count", "")
    snapshot = row.get("source_row_count_snapshot", "")

    if job == "monthly-report" and row.get("run_id") == first_post:
        if source == "" and reported in {"", "0"}:
            return "MISSING_TAIL_MERGE"

    if job in WEEKLY_JOBS and run_date_s:
        d = date.fromisoformat(run_date_s)
        expected = "archive" if d <= CUTOVER else "live"
        if source and source != expected:
            return "SOURCE_MISMATCH"

    if snapshot != "" and reported != snapshot:
        return "ROW_COUNT_MISMATCH"
    return "none"


def _finding_rank(finding: str) -> int:
    return 0 if finding == "none" else 1


def _source_rank(source: str) -> int:
    if source == "live":
        return 2
    if source == "archive":
        return 1
    return 0


def build_audit(log_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    monthly_after = [
        r
        for r in log_rows
        if r.get("job_name") == "monthly-report"
        and (r.get("run_date") or "")
        and date.fromisoformat(r["run_date"]) > CUTOVER
    ]
    monthly_after.sort(key=lambda r: r["run_date"])
    first_post = monthly_after[0]["run_id"] if monthly_after else None

    scored = []
    for row in log_rows:
        finding = _compute_finding(row, first_post)
        scored.append(
            {
                "run_id": row["run_id"],
                "job_name": row["job_name"],
                "run_date": row["run_date"],
                "source_used": row["source_used"],
                "reported_row_count": row["reported_row_count"],
                "finding": finding,
                "_snapshot": row.get("source_row_count_snapshot", ""),
                "_src_rank": _source_rank(row["source_used"]),
                "_find_rank": _finding_rank(finding),
            }
        )

    by_id: dict[str, dict] = {}
    for row in scored:
        rid = row["run_id"]
        prev = by_id.get(rid)
        if prev is None:
            by_id[rid] = row
            continue
        key = (row["_find_rank"], row["_src_rank"])
        prev_key = (prev["_find_rank"], prev["_src_rank"])
        if key > prev_key:
            by_id[rid] = row

    jobs_present = {r["job_name"] for r in by_id.values()}
    out = []
    for row in by_id.values():
        out.append(
            {
                "run_id": row["run_id"],
                "job_name": row["job_name"],
                "run_date": row["run_date"],
                "source_used": row["source_used"],
                "reported_row_count": row["reported_row_count"],
                "finding": row["finding"],
                "_snapshot": row["_snapshot"],
            }
        )
    for job in REQUIRED_JOBS:
        if job not in jobs_present:
            out.append(
                {
                    "run_id": "",
                    "job_name": job,
                    "run_date": "",
                    "source_used": "",
                    "reported_row_count": "0",
                    "finding": "MISSING_JOB",
                    "_snapshot": "",
                }
            )

    def sort_key(r: dict[str, str]):
        if r["finding"] == "MISSING_JOB":
            return ("", "", r["job_name"])
        return (r["run_date"] or "9999", r["run_id"], r["job_name"])

    out.sort(key=sort_key)
    return out


def write_gold_memo(rows: list[dict[str, str]], physical: int) -> str:
    unique = sum(1 for r in rows if r["finding"] != "MISSING_JOB")
    flagged = [r for r in rows if r["finding"] != "none"]
    compliant = len(rows) - len(flagged)

    lines = [
        f"# Recurring report source-selection audit - {unique} unique runs + 1 missing job",
        "",
        (
            f"The run log lists {physical} physical rows. After finding-precedence "
            f"de-duplication (non-`none` over `none`, then `live` over `archive` when "
            f"findings tie) there are {unique} unique runs plus one `MISSING_JOB` row "
            f"for `week-ahead-briefing` ({len(rows)} audit rows total). "
            f"{compliant} rows are compliant (`none`); {len(flagged)} rows are flagged."
        ),
        "",
        "| Run | Job | Run date | Source used | Reported rows | Finding |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        rid = r["run_id"] or "(missing)"
        lines.append(
            f"| {rid} | {r['job_name']} | {r['run_date']} | {r['source_used']} | "
            f"{r['reported_row_count']} | {r['finding']} |"
        )

    lines.extend(
        [
            "",
            "## Duplicate collapse - finding precedence",
            "",
            (
                "RUN-29 appears twice on 2026-06-20: finding-precedence keeps the live "
                "row because it used live instead of archive required on or before the "
                "cutover (`SOURCE_MISMATCH`); the compliant archive duplicate is dropped."
            ),
            "",
            (
                "RUN-35 appears twice on 2026-07-20: the archive row used archive but "
                "should have used live after the cutover (`SOURCE_MISMATCH`), while the "
                "live duplicate is `none`. Non-`none` finding precedence keeps the "
                "archive/`SOURCE_MISMATCH` row and drops the live/`none` duplicate "
                "(live preference only applies when findings tie)."
            ),
            "",
            (
                "RUN-37 appears twice on 2026-07-14: archive carries `SOURCE_MISMATCH` "
                "and live carries `ROW_COUNT_MISMATCH` (reported 456 against snapshot "
                "455). Both are non-`none`, so the live row is kept — "
                "`ROW_COUNT_MISMATCH`."
            ),
            "",
            (
                "RUN-38 appears twice on 2026-06-22: archive reported 301 against "
                "snapshot 300 (`ROW_COUNT_MISMATCH`) while live used live instead of "
                "archive required on or before the cutover (`SOURCE_MISMATCH`). Both "
                "findings are non-`none`, so live preference keeps the live/"
                "`SOURCE_MISMATCH` row (reported 300) rather than the archive row-count "
                "finding."
            ),
            "",
            "## Inclusive cutover - runs on 2026-07-06",
            "",
            (
                "The cutover rule is inclusive: on or before 2026-07-06 uses archive; "
                "after uses live. RUN-05 and RUN-22 correctly used archive on the "
                "cutover date (`none`). RUN-11 (monthly, archive on the cutover date) "
                "is also `none`. RUN-10 used live on the cutover date - premature - so "
                "`SOURCE_MISMATCH` (live used, archive required)."
            ),
            "",
            "## Pre-cutover live mismatches",
            "",
            (
                "RUN-13 and RUN-24 both ran on 2026-07-05 using live. Archive was "
                "required on or before 2026-07-06, so both are `SOURCE_MISMATCH` "
                "(live used, archive required). RUN-29 and RUN-38's kept live rows are "
                "likewise pre-cutover `SOURCE_MISMATCH` (live used, archive required)."
            ),
            "",
            "## Post-cutover archive mismatches",
            "",
            (
                "RUN-17 and RUN-23 both ran on 2026-07-07 using archive; live was "
                "required after 2026-07-06: `SOURCE_MISMATCH` (archive used, live "
                "required). RUN-18 on the same date correctly used live (`none`). "
                "RUN-33 ran on 2026-07-08 still on archive - also `SOURCE_MISMATCH` "
                "(archive used, live required). RUN-35's kept archive row on "
                "2026-07-20 is likewise `SOURCE_MISMATCH` (archive used, live required)."
            ),
            "",
            "## Empty-snapshot and zero-count compliant runs",
            "",
            (
                "RUN-20 and RUN-30 correctly used live after cutover with an empty "
                "`source_row_count_snapshot`, so the row-count rule does not apply "
                "(`none`). RUN-31 reported 0 with snapshot 0 - counts match (`none`)."
            ),
            "",
            "## Monthly edge cases",
            "",
            (
                "RUN-21 is a monthly report on the cutover date using live. The weekly "
                "cutover rule does not apply to monthly-report jobs, and the tail-merge "
                "rule applies only to the first post-cutover monthly report, so RUN-21 "
                "is `none`. RUN-03 (2026-08-03) is that first post-cutover monthly "
                "report, with empty source and zero rows - the archive tail merge was "
                "skipped: `MISSING_TAIL_MERGE`. Later monthly reports (RUN-08, RUN-15, "
                "RUN-28, RUN-34) need no tail merge and are `none` when source/count "
                "rules pass."
            ),
            "",
            "## Row-count mismatches",
            "",
            (
                "RUN-02 used live correctly but reported 388 against snapshot 395: "
                "`ROW_COUNT_MISMATCH`. RUN-25 used live correctly but reported 500 "
                "against snapshot 450: `ROW_COUNT_MISMATCH`. RUN-19 used live correctly "
                "but reported 410 against snapshot 405: `ROW_COUNT_MISMATCH`. RUN-36 "
                "used live correctly but reported 441 against snapshot 440 "
                "(off-by-one): `ROW_COUNT_MISMATCH`. RUN-37's kept live row reported "
                "456 against snapshot 455: `ROW_COUNT_MISMATCH`. (RUN-38's archive "
                "duplicate had 301 vs 300, but that row is dropped by live-source "
                "precedence when both duplicates are non-`none`.)"
            ),
            "",
            "## Missing required job - week-ahead-briefing",
            "",
            (
                "No run is logged for this job, but it is on the required recurring "
                "roster (weekly-journal-brief, week-ahead-briefing, monthly-report). "
                "That is `MISSING_JOB`."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def regen_gold(audit: list[dict[str, str]], physical: int) -> dict[str, int]:
    files = PACK / "solution" / "files"
    files.mkdir(parents=True, exist_ok=True)

    csv_path = files / "report_source_audit.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        f.write(",".join(AUDIT_FIELDS) + "\n")
        for r in audit:
            f.write(
                ",".join(
                    [
                        r["run_id"],
                        r["job_name"],
                        r["run_date"],
                        r["source_used"],
                        r["reported_row_count"],
                        r["finding"],
                    ]
                )
                + "\n"
            )

    memo = write_gold_memo(audit, physical)
    (files / "report_source_memo.md").write_text(memo, encoding="utf-8")

    counts = {
        "flagged_count": sum(1 for r in audit if r["finding"] != "none"),
        "source_mismatch_count": sum(
            1 for r in audit if r["finding"] == "SOURCE_MISMATCH"
        ),
        "row_count_mismatch_count": sum(
            1 for r in audit if r["finding"] == "ROW_COUNT_MISMATCH"
        ),
        "missing_tail_merge_count": sum(
            1 for r in audit if r["finding"] == "MISSING_TAIL_MERGE"
        ),
        "missing_job_count": sum(1 for r in audit if r["finding"] == "MISSING_JOB"),
    }
    payload = json.dumps(counts, indent=2) + "\n"
    (files / "results.json").write_text(payload, encoding="utf-8")
    (PACK / "solution" / "golden_results.json").write_text(payload, encoding="utf-8")
    print("gold counts", counts, "audit_rows", len(audit))
    return counts


def row_check(name: str, run_id: str, finding: str, how: str, why: str) -> dict:
    return {
        "name": name,
        "metadata": {"how_justification": how, "why_justification": why},
        "source": {
            "type": "file",
            "file": {
                "type": "csv",
                "command": "extract_text",
                "arguments": {"path": "report_source_audit.csv"},
            },
        },
        "assertion": {
            "type": "deterministic",
            "expected": (
                f"(?mi)^\\\"?{run_id}\\\"?\\s*(?:,[^\\n]*)?,(?:\\x22?{finding}\\x22?\\s*)$"
            ),
            "deterministic": {"path": "$.text", "comparison": "regex_match"},
        },
    }


def memo_source_check(name: str, n: str, how: str, why: str) -> dict:
    return {
        "name": name,
        "metadata": {"how_justification": how, "why_justification": why},
        "source": {
            "type": "file",
            "file": {
                "type": "md",
                "command": "extract_text",
                "arguments": {"path": "report_source_memo.md"},
            },
        },
        "assertion": {
            "type": "deterministic",
            "expected": (
                f"(?is)(?:RUN[-*_]*\\s*0?{n})"
                f"(?=.{{0,600}}?\\b(?:archive|archived|archives)\\b)"
                f"(?=.{{0,600}}?\\blive\\b)"
                f".{{0,450}}?\\b(?:{CONN})\\b"
            ),
            "deterministic": {"path": "$.text", "comparison": "regex_match"},
        },
    }


def update_verifier(counts: dict[str, int], audit_rows: int) -> int:
    path = PACK / "tests" / "verifier.json"
    spec = json.loads(path.read_text(encoding="utf-8"))
    verifiers = spec["verifiers"]

    for v in verifiers:
        if v["name"].startswith("audit_exactly_") and v["name"].endswith("_rows"):
            v["name"] = f"audit_exactly_{audit_rows}_rows"
            v["metadata"]["how_justification"] = (
                f"{audit_rows} unique-run + MISSING_JOB rows after densify de-dupe; "
                "rejects duplicated-row counterexample."
            )
            v["metadata"]["why_justification"] = (
                f"CSV must contain exactly {audit_rows} data rows."
            )
            v["assertion"]["expected"] = (
                r"\Arun_id,job_name,run_date,source_used,reported_row_count,finding\r?\n"
                rf"(?:.*\r?\n){{{audit_rows}}}(?:\r?\n)?\Z"
            )
        elif v["name"] == "result_flagged_count":
            v["assertion"]["expected"] = counts["flagged_count"]
        elif v["name"] == "result_source_mismatch_count":
            v["assertion"]["expected"] = counts["source_mismatch_count"]
        elif v["name"] == "result_row_count_mismatch_count":
            v["assertion"]["expected"] = counts["row_count_mismatch_count"]

    new_checks = [
        row_check(
            "row_run-38_source_mismatch",
            "RUN-38",
            "SOURCE_MISMATCH",
            "RUN-38 densify trap: both non-none; live SOURCE_MISMATCH beats archive ROW_COUNT_MISMATCH.",
            "RUN-38 must be SOURCE_MISMATCH after de-dupe.",
        ),
        memo_source_check(
            "memo_run38_source_mismatch_detail",
            "38",
            "Proximity+prose: RUN-38 + archive/live in ~600 + connective within ~450.",
            "RUN-38 SOURCE_MISMATCH must state used live vs required archive.",
        ),
    ]
    existing = {v["name"] for v in verifiers}
    for c in new_checks:
        if c["name"] not in existing:
            verifiers.append(c)
            print("added verifier", c["name"])
        else:
            for i, v in enumerate(verifiers):
                if v["name"] == c["name"]:
                    verifiers[i] = c
                    print("replaced verifier", c["name"])
                    break

    spec["verifiers"] = verifiers
    path.write_text(json.dumps(spec, indent=4) + "\n", encoding="utf-8")
    print("verifier count", len(verifiers))
    return len(verifiers)


def update_instruction() -> None:
    path = PACK / "instruction.md"
    text = path.read_text(encoding="utf-8")
    needle = (
        "archive/`SOURCE_MISMATCH` + live/`ROW_COUNT_MISMATCH` keeps "
        "live/`ROW_COUNT_MISMATCH` (findings tie, live wins)."
    )
    addition = (
        "archive/`SOURCE_MISMATCH` + live/`ROW_COUNT_MISMATCH` keeps "
        "live/`ROW_COUNT_MISMATCH` (findings tie, live wins); "
        "archive/`ROW_COUNT_MISMATCH` + live/`SOURCE_MISMATCH` keeps "
        "live/`SOURCE_MISMATCH` (findings tie, live wins — not a severity ranking)."
    )
    if "archive/`ROW_COUNT_MISMATCH` + live/`SOURCE_MISMATCH`" in text:
        print("instruction.md already has RUN-38 disclosure")
        return
    if needle not in text:
        raise SystemExit("instruction.md de-dupe examples not found")
    path.write_text(text.replace(needle, addition), encoding="utf-8")
    print("updated instruction.md RUN-38 disclosure")


def update_standard() -> None:
    path = PACK / "environment" / "input" / "report_source_standard.md"
    text = path.read_text(encoding="utf-8")
    old = (
        "When both duplicates are non-`none`, keep the live row's finding."
    )
    new = (
        "When both duplicates are non-`none`, keep the live row's finding "
        "(for example archive/`ROW_COUNT_MISMATCH` + live/`SOURCE_MISMATCH` keeps "
        "live/`SOURCE_MISMATCH`; there is no separate severity ranking among "
        "non-`none` findings)."
    )
    if "no separate severity ranking" in text:
        print("standard already has RUN-38 disclosure")
        return
    if old not in text:
        raise SystemExit("standard §5 non-none sentence not found")
    path.write_text(text.replace(old, new), encoding="utf-8")
    print("updated report_source_standard.md §5")


def update_test_outputs() -> None:
    path = PACK / "tests" / "test_outputs.py"
    text = path.read_text(encoding="utf-8")
    if '("RUN-38"' in text:
        print("test_outputs already has RUN-38 memo case")
        return
    old = '    ("RUN-35", [r"\\blive\\b", r"\\b(?:archive|archived|archives)\\b"]),\n'
    # RUN-38 is also a source mismatch (kept live vs archive)
    insert_after_35 = (
        '    ("RUN-35", [r"\\blive\\b", r"\\b(?:archive|archived|archives)\\b"]),\n'
        '    ("RUN-38", [r"\\blive\\b", r"\\b(?:archive|archived|archives)\\b"]),\n'
    )
    # Prefer placing near other source-mismatch cases; RUN-35 line uses archive first
    old2 = '    ("RUN-35", [r"\\b(?:archive|archived|archives)\\b", r"\\blive\\b"]),\n'
    new2 = (
        '    ("RUN-35", [r"\\b(?:archive|archived|archives)\\b", r"\\blive\\b"]),\n'
        '    ("RUN-38", [r"\\blive\\b", r"\\b(?:archive|archived|archives)\\b"]),\n'
    )
    if old2 in text:
        path.write_text(text.replace(old2, new2), encoding="utf-8")
        print("added RUN-38 to _FLAGGED_MEMO_CASES")
    elif old in text:
        path.write_text(text.replace(old, insert_after_35), encoding="utf-8")
        print("added RUN-38 to _FLAGGED_MEMO_CASES (alt)")
    else:
        raise SystemExit("RUN-35 memo case not found in test_outputs.py")


def update_readme(
    v_count: int, audit_rows: int, physical: int, unique: int, counts: dict
) -> None:
    path = PACK / "README.md"
    total = v_count + 3
    path.write_text(
        f"""# code-c249-recurring-report-source-selection-audit

Non-connector Harbor task. Audit a recurring reporting pipeline's logged runs against the source-selection standard (REPORTING-OPS-2).

## Deliverables

- `report_source_audit.csv` - one row per unique run_id (finding-precedence de-dupe) plus any missing required job, with a `finding` column
- `report_source_memo.md` - markdown memo explaining every finding
- `results.json` - `flagged_count`, `source_mismatch_count`, `row_count_mismatch_count`, `missing_tail_merge_count`, `missing_job_count`

## Inputs

- `input/report_source_standard.md` - the binding standard (cutover 2026-07-06, row-count, tail-merge, required-jobs, audit deliverable shape / ordered finding-precedence)
- `input/report_run_log.csv` - {physical} logged rows ({unique} unique run_ids after de-dupe of RUN-29/RUN-35/RUN-37/RUN-38) with `source_row_count_snapshot`

## Verifier

{total} graded pytest checks: {v_count} deterministic assertions in `tests/verifier.json` (file existence, unique-run finding rows + missing-job row, `audit_exactly_{audit_rows}_rows`, proximity+prose memo checks with ~450-char connective window including densify traps RUN-35/36/37/38, five `results.json` equals checks) plus 3 checks in `tests/test_outputs.py` (identifying columns, MISSING_JOB empty fields, per-finding local memo prose gate). Fractional reward via pytest passed/total.


Densify notes (post GLM 4/4 @ 1.0): ordered finding-precedence traps (archive-finding beats live-none; dual non-none keeps live — including archive/ROW_COUNT vs live/SOURCE), off-by-one row-count, and memo evidence binding for the new flagged runs. Expected results `{counts['flagged_count']}/{counts['source_mismatch_count']}/{counts['row_count_mismatch_count']}/{counts['missing_tail_merge_count']}/{counts['missing_job_count']}`.
""",
        encoding="utf-8",
    )
    print("updated README.md", total, "checks")


def update_trajectory(physical: int, unique: int, audit_rows: int, counts: dict, total: int) -> None:
    path = PACK / "solution" / "golden_trajectory.json"
    payload = {
        "schema_version": "ATIF-v1.7",
        "agent": {"name": "oracle", "version": "harbor-0.21"},
        "steps": [
            {
                "step_id": 1,
                "source": "user",
                "message": "Audit recurring reporting pipeline against source-selection standard (REPORTING-OPS-2).",
            },
            {
                "step_id": 2,
                "source": "oracle",
                "message": (
                    f"Load standard and run log; parse {physical} physical log rows; "
                    "collapse duplicate RUN-29/RUN-35/RUN-37/RUN-38 by ordered "
                    "finding-precedence (non-none over none, then live over archive on "
                    f"ties) → {unique} unique run_ids; add MISSING_JOB for "
                    f"week-ahead-briefing → {audit_rows} audit rows."
                ),
            },
            {
                "step_id": 3,
                "source": "oracle",
                "message": (
                    "Apply weekly cutover (2026-07-06 inclusive archive), row-count "
                    "consistency (empty snapshot=skip), monthly tail-merge for first "
                    "post-cutover monthly (RUN-03), ordered finding-precedence de-dupe "
                    "(incl. RUN-38 archive/ROW_COUNT vs live/SOURCE → live/SOURCE)."
                ),
            },
            {
                "step_id": 4,
                "source": "oracle",
                "message": (
                    f"Wrote report_source_audit.csv (exact header + {audit_rows} "
                    f"newline-terminated rows), memo explaining all "
                    f"{counts['flagged_count']} findings with local connective prose, "
                    f"results.json (flagged={counts['flagged_count']}, "
                    f"source_mismatch={counts['source_mismatch_count']}, "
                    f"row_count={counts['row_count_mismatch_count']}, "
                    f"tail_merge={counts['missing_tail_merge_count']}, "
                    f"missing_job={counts['missing_job_count']}). "
                    f"{total} graded checks."
                ),
            },
        ],
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print("updated golden_trajectory.json")


def update_compute_solve() -> None:
    block = '''
    run38 = next((r for r in rows if r["run_id"] == "RUN-38"), None)
    if run38 and run38["finding"] == "SOURCE_MISMATCH":
        lines.extend(
            [
                "## Duplicate collapse for RUN-38",
                "",
                (
                    "RUN-38 appears twice on 2026-06-22. Archive reported 301 against "
                    "snapshot 300 (`ROW_COUNT_MISMATCH`) while live used live instead of "
                    "archive required on or before the cutover (`SOURCE_MISMATCH`). Both "
                    "findings are non-`none`, so ordered precedence keeps the live/"
                    "`SOURCE_MISMATCH` row rather than ranking findings by severity."
                ),
                "",
            ]
        )
'''
    for dest in (
        PACK / "evaluations" / "solvability" / "agent-pass" / "compute_solve.py",
        PACK
        / "evaluations"
        / "solvability"
        / "agent-pass"
        / "agent"
        / "compute_solve.py",
    ):
        src = dest.read_text(encoding="utf-8")
        if "Duplicate collapse for RUN-38" in src:
            print("compute_solve already has RUN-38", dest.name)
            continue
        anchor = '    run37 = next((r for r in rows if r["run_id"] == "RUN-37"), None)'
        # Insert after the entire run37 if-block
        marker = (
            '                    "row is kept -- `ROW_COUNT_MISMATCH`."\n'
            "                ),\n"
            "                \"\",\n"
            "            ]\n"
            "        )\n"
        )
        if marker not in src:
            raise SystemExit(f"RUN-37 memo block end not found in {dest}")
        src = src.replace(marker, marker + "\n" + block)
        dest.write_text(src, encoding="utf-8")
        print("wrote RUN-38 memo into", dest.relative_to(PACK))


def update_review(
    v_count: int, audit_rows: int, physical: int, unique: int, counts: dict, total: int
) -> None:
    path = PACK / "review.csv"
    densify_note = (
        f"Densified pack: {physical} log / {unique} unique / {audit_rows} audit; "
        f"results {counts['flagged_count']}/{counts['source_mismatch_count']}/"
        f"{counts['row_count_mismatch_count']}/{counts['missing_tail_merge_count']}/"
        f"{counts['missing_job_count']}; {total} checks incl. RUN-38 mirror "
        f"precedence trap (archive/ROW_COUNT + live/SOURCE → live/SOURCE). "
        f"golden_trajectory updated; do not invent GLM."
    )
    rows = list(csv.DictReader(path.open(encoding="utf-8", newline="")))
    fieldnames = list(rows[0].keys())

    def set_row(check: str, status: str, notes: str, change: str, record: str) -> None:
        for r in rows:
            if r["review_check"] == check:
                r["status"] = status
                r["review_notes"] = notes
                r["change_made"] = change
                r["what_to_record"] = record
                return
        rows.append(
            {
                "review_check": check,
                "status": status,
                "review_notes": notes,
                "change_made": change,
                "what_to_record": record,
            }
        )

    set_row(
        "Layer 1 - Package consistency",
        "FIXED_AND_VERIFIED",
        densify_note,
        "Added RUN-38 trap; regen gold/verifier/instruction/standard/README/trajectory/compute_solve.",
        f"Cite instruction.md; standard §5; tests/verifier.json ({v_count}); test_outputs.py (+3); solution/files; {total} checks.",
    )
    set_row(
        "Layer 2 Difficulty",
        "NEEDS_RERUN",
        "Memo-window widen alone may restore GLM 4/4 @ 1.0; added RUN-38 fair precedence trap. Do not invent GLM; parent re-runs Harbor GLM×4.",
        "RUN-38 densify after memo fairness; left evaluations/glm-5.2 for parent re-run.",
        "Parent re-run Harbor GLM×4 after RUN-38 densify.",
    )
    set_row(
        "Layer 2 Solvability",
        "FIXED_AND_VERIFIED",
        f"compute_solve.py updated for RUN-38; agent-pass re-verified {total}/{total}.",
        "Updated compute_solve.py + re-ran agent-pass compute+pytest.",
        "evaluations/solvability/agent-pass",
    )
    set_row(
        "Layer 3 Oracle Mode",
        "FIXED_AND_VERIFIED",
        f"Gold solution/files regenerated for RUN-38; local gold pytest {total}/{total}.",
        "Regenerated gold audit/memo/results for RUN-38.",
        f"Oracle gold 1.0 on {total} checks.",
    )
    set_row(
        "Layer 4 - Environment and files",
        "PASS",
        f"Inputs present: report_source_standard.md; report_run_log.csv ({physical} rows). Public python:3.12-slim-bookworm.",
        "Appended RUN-38 densify trap rows to report_run_log.csv.",
        "No packaging failures.",
    )
    set_row(
        "Layer 4 - Deliverables and artifact quality",
        "FIXED_AND_VERIFIED",
        f"Gold audit has {audit_rows} data rows; memo explains all {counts['flagged_count']} findings with connective prose incl. RUN-35/36/37/38; results {counts['flagged_count']}/{counts['source_mismatch_count']}/{counts['row_count_mismatch_count']}/{counts['missing_tail_merge_count']}/{counts['missing_job_count']}.",
        "Regenerated gold memo/audit/results for RUN-38.",
        "Deliverables complete and consistent.",
    )
    set_row(
        "Layer 5 - Verifier coverage and fairness",
        "FIXED_AND_VERIFIED",
        f"Added row+memo checks for RUN-38; audit_exactly_{audit_rows}_rows; result counts 16/9/5/1/1; identifying-column + MISSING_JOB + prose gate retained. RUN-38 rule disclosed in instruction+standard.",
        f"verifier.json now {v_count}; total graded {total}.",
        f"{total} checks; RUN-38 graded; identifying columns still checked.",
    )
    set_row(
        "Cross-trial - Calibration",
        "NEEDS_RERUN",
        "RUN-38 densify after memo-window widen. Do not invent GLM; parent re-runs difficulty.",
        "RUN-38 densify complete; GLM difficulty pending parent re-run.",
        "Difficulty = live portal GLM×4 only after densify.",
    )

    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print("updated review.csv")


def run_gold_pytest() -> str:
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        for f in (PACK / "solution" / "files").iterdir():
            shutil.copy2(f, td_path / f.name)
        inp = td_path / "input"
        inp.mkdir()
        shutil.copy2(
            PACK / "environment" / "input" / "report_run_log.csv",
            inp / "report_run_log.csv",
        )
        shutil.copy2(
            PACK / "environment" / "input" / "report_source_standard.md",
            inp / "report_source_standard.md",
        )
        env = {
            **{k: v for k, v in __import__("os").environ.items()},
            "HARBOR_TASK_WORKSPACE": str(td_path),
        }
        r = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                str(PACK / "tests" / "test_outputs.py"),
                "-q",
                "--tb=line",
            ],
            cwd=str(PACK),
            env=env,
            capture_output=True,
            text=True,
        )
        out = (r.stdout or "") + (r.stderr or "")
        print(out[-3000:] if len(out) > 3000 else out)
        print("gold pytest exit", r.returncode)
        if r.returncode != 0:
            raise SystemExit(f"gold pytest failed:\n{out}")
        return out


def run_solvability() -> str:
    agent_pass = PACK / "evaluations" / "solvability" / "agent-pass"
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        inp = td_path / "input"
        inp.mkdir()
        shutil.copy2(
            PACK / "environment" / "input" / "report_run_log.csv",
            inp / "report_run_log.csv",
        )
        shutil.copy2(
            PACK / "environment" / "input" / "report_source_standard.md",
            inp / "report_source_standard.md",
        )
        env = {
            **{k: v for k, v in __import__("os").environ.items()},
            "HARBOR_TASK_WORKSPACE": str(td_path),
        }
        r1 = subprocess.run(
            [sys.executable, str(agent_pass / "compute_solve.py")],
            cwd=str(td_path),
            env=env,
            capture_output=True,
            text=True,
        )
        print(r1.stdout)
        if r1.returncode != 0:
            raise SystemExit(r1.stderr or r1.stdout)

        art = agent_pass / "artifacts"
        art.mkdir(exist_ok=True)
        for name in (
            "report_source_audit.csv",
            "report_source_memo.md",
            "results.json",
        ):
            shutil.copy2(td_path / name, art / name)
            shutil.copy2(td_path / name, agent_pass / name)

        r2 = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                str(PACK / "tests" / "test_outputs.py"),
                "-q",
                "--tb=line",
            ],
            cwd=str(PACK),
            env=env,
            capture_output=True,
            text=True,
        )
        out = (r2.stdout or "") + (r2.stderr or "")
        print(out[-3000:] if len(out) > 3000 else out)
        print("solvability pytest exit", r2.returncode)
        if r2.returncode != 0:
            raise SystemExit(f"solvability pytest failed:\n{out}")
        ver = agent_pass / "verifier"
        ver.mkdir(exist_ok=True)
        (ver / "reward.txt").write_text("1\n", encoding="utf-8")
        (ver / "test-stdout.txt").write_text(out, encoding="utf-8")
        return out


def main() -> None:
    append_log()
    update_instruction()
    update_standard()
    update_test_outputs()

    log_path = PACK / "environment" / "input" / "report_run_log.csv"
    with log_path.open(encoding="utf-8", newline="") as f:
        log_rows = [
            {k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(f)
        ]
    physical = len(log_rows)
    audit = build_audit(log_rows)
    unique = sum(1 for r in audit if r["finding"] != "MISSING_JOB")
    run38 = next(r for r in audit if r["run_id"] == "RUN-38")
    assert run38["finding"] == "SOURCE_MISMATCH", run38
    assert run38["source_used"] == "live", run38
    assert run38["reported_row_count"] == "300", run38

    counts = regen_gold(audit, physical)
    v_count = update_verifier(counts, len(audit))
    total = v_count + 3
    update_readme(v_count, len(audit), physical, unique, counts)
    update_trajectory(physical, unique, len(audit), counts, total)
    update_compute_solve()
    gold_out = run_gold_pytest()
    sol_out = run_solvability()
    update_review(v_count, len(audit), physical, unique, counts, total)

    print("=== SUMMARY ===")
    print("physical", physical, "unique", unique, "audit", len(audit))
    print("counts", counts)
    print("verifier.json", v_count, "total checks", total)
    print("gold pytest OK")
    print("solvability OK")
    _ = gold_out, sol_out


if __name__ == "__main__":
    main()
