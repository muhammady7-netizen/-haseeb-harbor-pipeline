"""Densify code-c249 after GLM 4/4 @ 1.0: add 3 fair traps, regen gold+verifier."""
from __future__ import annotations

import csv
import json
import re
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

# Trap rows (append if missing)
NEW_LOG_ROWS = [
    # RUN-35: finding-precedence beats live preference (inverse of RUN-29)
    "RUN-35,weekly-journal-brief,2026-07-20,archive,410,410",
    "RUN-35,weekly-journal-brief,2026-07-20,live,410,410",
    # RUN-36: off-by-one row count with correct post-cutover live source
    "RUN-36,weekly-journal-brief,2026-08-24,live,441,440",
    # RUN-37: both non-none; equal finding-rank → keep live ROW_COUNT_MISMATCH
    "RUN-37,weekly-journal-brief,2026-07-14,archive,455,455",
    "RUN-37,weekly-journal-brief,2026-07-14,live,456,455",
]


def append_log() -> None:
    path = PACK / "environment" / "input" / "report_run_log.csv"
    text = path.read_text(encoding="utf-8")
    if "RUN-35," in text:
        print("log already has RUN-35")
        return
    path.write_text(text.rstrip("\n") + "\n" + "\n".join(NEW_LOG_ROWS) + "\n", encoding="utf-8")
    print("appended", len(NEW_LOG_ROWS), "log rows")


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
                "(live used, archive required)."
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
                "456 against snapshot 455: `ROW_COUNT_MISMATCH`."
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
                f".{{0,160}}?\\b(?:because|used|uses|using|should|instead|expected|"
                f"required|premature|reported|against|vs\\.?|versus)\\b"
            ),
            "deterministic": {"path": "$.text", "comparison": "regex_match"},
        },
    }


def memo_rowcount_check(
    name: str, n: str, a: str, b: str, how: str, why: str
) -> dict:
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
                f"(?=.{{0,600}}?\\b{a}\\b)(?=.{{0,600}}?\\b{b}\\b)"
                f".{{0,160}}?\\b(?:because|used|uses|using|should|instead|expected|"
                f"required|premature|reported|against|vs\\.?|versus)\\b"
            ),
            "deterministic": {"path": "$.text", "comparison": "regex_match"},
        },
    }


def update_verifier(counts: dict[str, int], audit_rows: int) -> int:
    path = PACK / "tests" / "verifier.json"
    spec = json.loads(path.read_text(encoding="utf-8"))
    verifiers = spec["verifiers"]

    # Rename / retarget audit row count check
    for v in verifiers:
        if v["name"] == "audit_exactly_29_rows":
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

    existing = {v["name"] for v in verifiers}
    new_checks = [
        row_check(
            "row_run-35_source_mismatch",
            "RUN-35",
            "SOURCE_MISMATCH",
            "RUN-35 densify trap: finding-precedence keeps archive SOURCE_MISMATCH over live none.",
            "RUN-35 must be SOURCE_MISMATCH after de-dupe.",
        ),
        row_check(
            "row_run-36_row_count_mismatch",
            "RUN-36",
            "ROW_COUNT_MISMATCH",
            "RUN-36 densify trap: off-by-one reported 441 vs snapshot 440.",
            "RUN-36 must be ROW_COUNT_MISMATCH.",
        ),
        row_check(
            "row_run-37_row_count_mismatch",
            "RUN-37",
            "ROW_COUNT_MISMATCH",
            "RUN-37 densify trap: both non-none; live ROW_COUNT_MISMATCH wins tie-break.",
            "RUN-37 must be ROW_COUNT_MISMATCH after de-dupe.",
        ),
        memo_source_check(
            "memo_run35_source_mismatch_detail",
            "35",
            "Proximity+prose: RUN-35 + archive/live in ~600 + connective within ~160.",
            "RUN-35 SOURCE_MISMATCH must state used archive vs required live.",
        ),
        memo_rowcount_check(
            "memo_run36_row_count_detail",
            "36",
            "441",
            "440",
            "Proximity+prose: RUN-36 + 441/440 in ~600 + connective within ~160.",
            "RUN-36 ROW_COUNT_MISMATCH must state reported 441 and snapshot 440.",
        ),
        memo_rowcount_check(
            "memo_run37_row_count_detail",
            "37",
            "456",
            "455",
            "Proximity+prose: RUN-37 + 456/455 in ~600 + connective within ~160.",
            "RUN-37 ROW_COUNT_MISMATCH must state reported 456 and snapshot 455.",
        ),
    ]
    for c in new_checks:
        if c["name"] not in existing:
            verifiers.append(c)
            print("added verifier", c["name"])
        else:
            # replace
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
    old = (
        "- Emit **exactly one audit row per unique `run_id`**. When the run log contains "
        "multiple rows with the same `run_id`, collapse them using **finding-precedence**: "
        "prefer a non-`none` finding over `none`, and when comparing otherwise competing "
        "duplicates prefer the `live` source row over the `archive` source row (so a "
        "duplicate pair such as archive/`none` + live/`SOURCE_MISMATCH` keeps the "
        "live/`SOURCE_MISMATCH` row only)."
    )
    new = (
        "- Emit **exactly one audit row per unique `run_id`**. When the run log contains "
        "multiple rows with the same `run_id`, collapse them using **finding-precedence** "
        "in this order: (1) prefer a non-`none` finding over `none`; (2) only when that "
        "preference ties, prefer the `live` source row over the `archive` source row. "
        "Examples of the ordered rule: archive/`none` + live/`SOURCE_MISMATCH` keeps "
        "live/`SOURCE_MISMATCH`; archive/`SOURCE_MISMATCH` + live/`none` keeps "
        "archive/`SOURCE_MISMATCH` (finding wins over live preference); "
        "archive/`SOURCE_MISMATCH` + live/`ROW_COUNT_MISMATCH` keeps "
        "live/`ROW_COUNT_MISMATCH` (findings tie, live wins)."
    )
    if old in text:
        text = text.replace(old, new)
        path.write_text(text, encoding="utf-8")
        print("updated instruction.md de-dupe disclosure")
    elif "only when that preference ties" in text:
        print("instruction.md already densified")
    else:
        raise SystemExit("instruction.md de-dupe bullet not found")


def update_standard() -> None:
    path = PACK / "environment" / "input" / "report_source_standard.md"
    text = path.read_text(encoding="utf-8")
    old = (
        "Emit one row per unique `run_id`. If the run log lists the same `run_id` more "
        "than once, keep a single row by finding-precedence: prefer a non-`none` finding "
        "over `none`, and prefer a `live` source row over an `archive` source row when "
        "both appear for that `run_id`."
    )
    new = (
        "Emit one row per unique `run_id`. If the run log lists the same `run_id` more "
        "than once, keep a single row by finding-precedence in this order: (1) prefer a "
        "non-`none` finding over `none`; (2) only when findings tie on that preference, "
        "prefer a `live` source row over an `archive` source row. A duplicate where "
        "archive carries a finding and live is `none` therefore keeps the archive "
        "finding row. When both duplicates are non-`none`, keep the live row's finding."
    )
    if old in text:
        text = text.replace(old, new)
        path.write_text(text, encoding="utf-8")
        print("updated report_source_standard.md §5")
    elif "only when findings tie" in text:
        print("standard already densified")
    else:
        raise SystemExit("standard §5 de-dupe sentence not found")


def update_readme(v_count: int, audit_rows: int, physical: int, unique: int, counts: dict) -> None:
    path = PACK / "README.md"
    total = v_count + 2
    path.write_text(
        f"""# code-c249-recurring-report-source-selection-audit

Non-connector Harbor task. Audit a recurring reporting pipeline's logged runs against the source-selection standard (REPORTING-OPS-2).

## Deliverables

- `report_source_audit.csv` - one row per unique run_id (finding-precedence de-dupe) plus any missing required job, with a `finding` column
- `report_source_memo.md` - markdown memo explaining every finding
- `results.json` - `flagged_count`, `source_mismatch_count`, `row_count_mismatch_count`, `missing_tail_merge_count`, `missing_job_count`

## Inputs

- `input/report_source_standard.md` - the binding standard (cutover 2026-07-06, row-count, tail-merge, required-jobs, audit deliverable shape / ordered finding-precedence)
- `input/report_run_log.csv` - {physical} logged rows ({unique} unique run_ids after de-dupe of RUN-29/RUN-35/RUN-37) with `source_row_count_snapshot`

## Verifier

{total} graded pytest checks: {v_count} deterministic assertions in `tests/verifier.json` (file existence, {unique} unique-run finding rows + missing-job row with quote-tolerant empty `run_id`, `audit_exactly_{audit_rows}_rows`, proximity+prose memo checks including densify traps RUN-35/36/37, five `results.json` equals checks) plus 2 field-level DictReader checks in `tests/test_outputs.py` that the audit identifying columns (`job_name`, `run_date`, `source_used`, `reported_row_count`) match the de-duplicated run log and that the `MISSING_JOB` row has empty `run_id`/`run_date`/`source_used` with `reported_row_count=0`. Fractional reward via pytest passed/total.

Densify notes (post GLM 4/4 @ 1.0): ordered finding-precedence traps (archive-finding beats live-none; dual non-none keeps live), off-by-one row-count, and memo evidence binding for the new flagged runs. Expected results `{counts['flagged_count']}/{counts['source_mismatch_count']}/{counts['row_count_mismatch_count']}/{counts['missing_tail_merge_count']}/{counts['missing_job_count']}`.
""",
        encoding="utf-8",
    )
    print("updated README.md", total, "checks")


def update_review(v_count: int, audit_rows: int, physical: int, unique: int, counts: dict) -> None:
    path = PACK / "review.csv"
    total = v_count + 2
    densify_note = (
        f"Densified after GLM 4/4 @ reward 1.0 on prior 53-check pack: added ordered "
        f"finding-precedence traps (RUN-35 archive SOURCE_MISMATCH beats live none; "
        f"RUN-37 dual non-none keeps live ROW_COUNT_MISMATCH), off-by-one RUN-36 "
        f"(441 vs 440), and memo proximity gates. Log now {physical} physical / "
        f"{unique} unique + 1 MISSING_JOB = {audit_rows} audit rows; "
        f"{v_count} verifier.json + 2 pytest = {total}; results "
        f"{counts['flagged_count']}/{counts['source_mismatch_count']}/"
        f"{counts['row_count_mismatch_count']}/{counts['missing_tail_merge_count']}/"
        f"{counts['missing_job_count']}. Instruction+standard disclose ordered de-dupe. "
        f"Parent will re-run GLM×4; do not invent GLM evals."
    )
    rows = list(csv.DictReader(path.open(encoding="utf-8", newline="")))
    fieldnames = list(rows[0].keys()) if rows else [
        "review_check",
        "status",
        "review_notes",
        "change_made",
        "what_to_record",
    ]

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
        "Densify traps RUN-35/36/37; instruction+standard ordered precedence; README/review; gold+verifier+compute_solve.",
        f"Cite instruction.md; standard §5; tests/verifier.json ({v_count}); test_outputs.py (+2); solution/files; solvability/agent-pass; README {total}.",
    )
    set_row(
        "Layer 2 Difficulty",
        "NEEDS_RERUN",
        "Prior GLM 4/4 @ 1.0 on 53-check pack forced densify. Stale glm-5.2 evals may remain; parent must re-run Harbor GLM×4 on densified pack (do not invent).",
        "Densified inputs/gold/verifier; left evaluations/glm-5.2 for parent re-run.",
        "Parent re-run GLM×4 after densify.",
    )
    set_row(
        "Layer 2 Solvability",
        "FIXED_AND_VERIFIED",
        f"compute_solve.py updated for ordered de-dupe + new traps; agent-pass re-verified {total}/{total}.",
        "Updated compute_solve.py + re-ran agent-pass compute+pytest.",
        "evaluations/solvability/agent-pass",
    )
    set_row(
        "Layer 3 Oracle Mode",
        "FIXED_AND_VERIFIED",
        f"Gold solution/files regenerated for densify; local gold pytest {total}/{total}.",
        "Regenerated gold audit/memo/results.",
        f"Oracle gold 1.0 on {total} checks.",
    )
    set_row(
        "Layer 4 - Environment and files",
        "PASS",
        f"Inputs present: report_source_standard.md; report_run_log.csv ({physical} rows). Public python:3.12-slim-bookworm.",
        "Appended densify trap rows to report_run_log.csv.",
        "No packaging failures.",
    )
    set_row(
        "Layer 4 - Deliverables and artifact quality",
        "FIXED_AND_VERIFIED",
        f"Gold audit has {audit_rows} data rows; memo explains all {counts['flagged_count']} findings with connective prose incl. RUN-35/36/37; results {counts['flagged_count']}/{counts['source_mismatch_count']}/{counts['row_count_mismatch_count']}/{counts['missing_tail_merge_count']}/{counts['missing_job_count']}.",
        "Regenerated gold memo/audit/results for densify traps.",
        "Deliverables complete and consistent.",
    )
    set_row(
        "Layer 5 - Verifier coverage and fairness",
        "FIXED_AND_VERIFIED",
        f"Added row+memo checks for RUN-35/36/37; audit_exactly_{audit_rows}_rows; result counts updated; identifying-column + MISSING_JOB field checks retained. All densify rules disclosed in instruction+standard.",
        f"verifier.json now {v_count}; total graded {total}.",
        f"{total} checks; densify traps graded; identifying columns still checked.",
    )
    set_row(
        "Cross-trial - Calibration",
        "NEEDS_RERUN",
        "Densify invalidated prior GLM 4/4 distribution. Do not invent GLM; parent re-runs difficulty. Solvability = agent-pass compute; stability oracle replays may need refresh after gold change.",
        "Densify complete; GLM difficulty pending parent re-run.",
        "Difficulty = live portal GLM×4 only after densify.",
    )

    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print("updated review.csv")


def update_compute_solve() -> None:
    """Refresh both compute_solve.py copies with densify-aware memo notes."""
    # Re-read current and patch write_memo duplicate section + keep logic identical
    src = (PACK / "evaluations" / "solvability" / "agent-pass" / "compute_solve.py").read_text(
        encoding="utf-8"
    )
    # Replace the RUN-29-only memo block with multi-dupe handling
    old_block = '''    # RUN-29 duplicate note (kept live SOURCE_MISMATCH)
    run29 = next((r for r in rows if r["run_id"] == "RUN-29"), None)
    if run29 and run29["finding"] == "SOURCE_MISMATCH":
        lines.extend(
            [
                "## Duplicate collapse for RUN-29",
                "",
                (
                    "RUN-29 appears twice in the log for 2026-06-20. Finding-precedence "
                    "keeps the live row because it used live instead of the archive "
                    "source required on or before the cutover -- that is `SOURCE_MISMATCH`. "
                    "The compliant archive duplicate is dropped."
                ),
                "",
            ]
        )'''
    new_block = '''    # Duplicate collapse notes (densify traps)
    run29 = next((r for r in rows if r["run_id"] == "RUN-29"), None)
    if run29 and run29["finding"] == "SOURCE_MISMATCH":
        lines.extend(
            [
                "## Duplicate collapse for RUN-29",
                "",
                (
                    "RUN-29 appears twice in the log for 2026-06-20. Finding-precedence "
                    "keeps the live row because it used live instead of the archive "
                    "source required on or before the cutover -- that is `SOURCE_MISMATCH`. "
                    "The compliant archive duplicate is dropped."
                ),
                "",
            ]
        )

    run35 = next((r for r in rows if r["run_id"] == "RUN-35"), None)
    if run35 and run35["finding"] == "SOURCE_MISMATCH":
        lines.extend(
            [
                "## Duplicate collapse for RUN-35",
                "",
                (
                    "RUN-35 appears twice on 2026-07-20. The archive duplicate used "
                    "archive but should have used live after the cutover -- "
                    "`SOURCE_MISMATCH` -- while the live duplicate is `none`. Ordered "
                    "finding-precedence keeps the archive/`SOURCE_MISMATCH` row because "
                    "a non-`none` finding beats `none` before live-over-archive applies."
                ),
                "",
            ]
        )

    run37 = next((r for r in rows if r["run_id"] == "RUN-37"), None)
    if run37 and run37["finding"] == "ROW_COUNT_MISMATCH":
        snap = run37.get("_snapshot", "455")
        lines.extend(
            [
                "## Duplicate collapse for RUN-37",
                "",
                (
                    "RUN-37 appears twice on 2026-07-14. Archive carries "
                    "`SOURCE_MISMATCH` and live reported "
                    f"{run37['reported_row_count']} against snapshot {snap} "
                    "(`ROW_COUNT_MISMATCH`). Both findings are non-`none`, so the live "
                    "row is kept -- `ROW_COUNT_MISMATCH`."
                ),
                "",
            ]
        )'''
    if old_block in src:
        src = src.replace(old_block, new_block)
    elif "Duplicate collapse for RUN-35" in src:
        print("compute_solve already has RUN-35 memo")
    else:
        raise SystemExit("compute_solve RUN-29 block not found")

    # Ensure docstring mentions ordered precedence
    src = src.replace(
        "MISSING_JOB, finding-precedence de-dupe).",
        "MISSING_JOB, ordered finding-precedence de-dupe).",
    )

    for dest in (
        PACK / "evaluations" / "solvability" / "agent-pass" / "compute_solve.py",
        PACK
        / "evaluations"
        / "solvability"
        / "agent-pass"
        / "agent"
        / "compute_solve.py",
    ):
        dest.write_text(src, encoding="utf-8")
        print("wrote", dest.relative_to(PACK))


def run_gold_pytest() -> str:
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        # install gold
        for f in (PACK / "solution" / "files").iterdir():
            shutil.copy2(f, td_path / f.name)
        # input for field-level checks
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
        env = {**dict(**{k: v for k, v in __import__("os").environ.items()}), "HARBOR_TASK_WORKSPACE": str(td_path)}
        r = subprocess.run(
            [sys.executable, "-m", "pytest", str(PACK / "tests" / "test_outputs.py"), "-q", "--tb=line"],
            cwd=str(PACK),
            env=env,
            capture_output=True,
            text=True,
        )
        out = (r.stdout or "") + (r.stderr or "")
        print(out[-2000:] if len(out) > 2000 else out)
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
            raise SystemExit(r1.stderr)

        # copy artifacts into agent-pass
        art = agent_pass / "artifacts"
        art.mkdir(exist_ok=True)
        for name in (
            "report_source_audit.csv",
            "report_source_memo.md",
            "results.json",
        ):
            shutil.copy2(td_path / name, art / name)
            # also top-level for some layouts
            shutil.copy2(td_path / name, agent_pass / name)

        r2 = subprocess.run(
            [sys.executable, "-m", "pytest", str(PACK / "tests" / "test_outputs.py"), "-q", "--tb=line"],
            cwd=str(PACK),
            env=env,
            capture_output=True,
            text=True,
        )
        out = (r2.stdout or "") + (r2.stderr or "")
        print(out[-2000:] if len(out) > 2000 else out)
        print("solvability pytest exit", r2.returncode)
        if r2.returncode != 0:
            raise SystemExit(f"solvability pytest failed:\n{out}")

        # write a simple verifier summary if folder exists
        ver = agent_pass / "verifier"
        ver.mkdir(exist_ok=True)
        (ver / "reward.txt").write_text("1\n", encoding="utf-8")
        (ver / "test-stdout.txt").write_text(out, encoding="utf-8")
        return out


def main() -> None:
    append_log()
    update_instruction()
    update_standard()

    log_path = PACK / "environment" / "input" / "report_run_log.csv"
    with log_path.open(encoding="utf-8", newline="") as f:
        log_rows = [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(f)]
    physical = len(log_rows)
    audit = build_audit(log_rows)
    unique = sum(1 for r in audit if r["finding"] != "MISSING_JOB")
    counts = regen_gold(audit, physical)
    v_count = update_verifier(counts, len(audit))
    update_readme(v_count, len(audit), physical, unique, counts)
    update_compute_solve()
    gold_out = run_gold_pytest()
    sol_out = run_solvability()
    update_review(v_count, len(audit), physical, unique, counts)

    print("=== SUMMARY ===")
    print("physical", physical, "unique", unique, "audit", len(audit))
    print("counts", counts)
    print("verifier.json", v_count, "total checks", v_count + 2)
    print("gold pytest OK")
    print("solvability OK")
    # keep linters quiet
    _ = gold_out, sol_out


if __name__ == "__main__":
    main()
