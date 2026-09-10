#!/usr/bin/env python3
"""h40 v13 densify — v12 still TOO_EASY 4/4. Harder clock traps; less spoon-feeding."""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

PACK = Path(
    r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline"
    r"\qc-out\ework\UPLOAD-THIS-TO-QC-health-h40"
    r"\health-h40-critical-result-acknowledgement"
)


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def main() -> None:
    # Strip spoon-fed tips from instruction (procedure already states the rules)
    instr_path = PACK / "instruction.md"
    instr = instr_path.read_text(encoding="utf-8")
    instr = re.sub(
        r"Tier 1 clocks run across midnight without reset\..*?weekday-only\.",
        "",
        instr,
        flags=re.S,
    )
    tip = (
        "Apply the procedure's clock-start and inclusive-window rules carefully: "
        "a tier-2 release before 08:00 still starts at 08:00 that morning, even on a weekend."
    )
    if "tier-2 release before 08:00" not in instr:
        if "naming a particular result ID is optional." in instr:
            instr = instr.replace(
                "naming a particular result ID is optional.",
                "naming a particular result ID is optional. " + tip,
                1,
            )
        else:
            instr = instr.rstrip() + "\n" + tip + "\n"
    instr_path.write_text(instr, encoding="utf-8", newline="\n")

    cr_path = PACK / "environment" / "input" / "critical_results.csv"
    cr_fields = list(csv.DictReader(cr_path.open(encoding="utf-8-sig")).fieldnames or [])
    cr = [r for r in csv.DictReader(cr_path.open(encoding="utf-8-sig")) if r["result_id"] not in ("R-39", "R-40", "R-41")]

    # Sunday pre-core release → clock 08:00; looks early but compliant
    cr.append(
        {
            "result_id": "R-39",
            "tier": "2",
            "test": "glucose",
            "released_at": "2026-06-21T07:00",
            "notified_at": "2026-06-21T08:30",
            "acknowledged_at": "2026-06-21T16:00",
            "acknowledged_by_role": "consultant",
        }
    )
    # Tier 1: notify at 31 (late by 1), ack at 60 inclusive OK, escalation missing
    cr.append(
        {
            "result_id": "R-40",
            "tier": "1",
            "test": "potassium",
            "released_at": "2026-06-23T10:00",
            "notified_at": "2026-06-23T10:31",
            "acknowledged_at": "2026-06-23T11:00",
            "acknowledged_by_role": "resident_doctor",
        }
    )
    # Tier 2 at 17:59 with ack exactly 480 — compliant; agents often start next morning
    cr.append(
        {
            "result_id": "R-41",
            "tier": "2",
            "test": "bilirubin",
            "released_at": "2026-06-22T17:59",
            "notified_at": "2026-06-22T18:30",
            "acknowledged_at": "2026-06-23T01:59",
            "acknowledged_by_role": "consultant",
        }
    )
    write_csv(cr_path, cr, cr_fields)

    # no escalations for R-40
    esc_path = PACK / "environment" / "input" / "escalations.csv"
    esc = list(csv.DictReader(esc_path.open(encoding="utf-8-sig")))
    write_csv(esc_path, esc, ["result_id", "escalated_at"])

    audit_path = PACK / "solution" / "files" / "results_audit.csv"
    audit_fields = list(csv.DictReader(audit_path.open(encoding="utf-8-sig")).fieldnames or [])
    audit = [r for r in csv.DictReader(audit_path.open(encoding="utf-8-sig")) if r["result_id"] not in ("R-39", "R-40", "R-41")]
    audit.append(
        {
            "result_id": "R-39",
            "tier": "2",
            "clock_start": "2026-06-21T08:00",
            "notification_minutes": "30",
            "acknowledgement_minutes": "480",
            "acknowledged_by_role": "consultant",
            "escalation_status": "not_required",
            "findings": "compliant",
        }
    )
    audit.append(
        {
            "result_id": "R-40",
            "tier": "1",
            "clock_start": "2026-06-23T10:00",
            "notification_minutes": "31",
            "acknowledgement_minutes": "60",
            "acknowledged_by_role": "resident_doctor",
            "escalation_status": "not_required",
            # notification late but ack within window → escalation not required
            "findings": "notification_late",
        }
    )
    # R-41: clock at release 17:59; notify 31 min; ack 480 inclusive → compliant
    audit.append(
        {
            "result_id": "R-41",
            "tier": "2",
            "clock_start": "2026-06-22T17:59",
            "notification_minutes": "31",
            "acknowledgement_minutes": "480",
            "acknowledged_by_role": "consultant",
            "escalation_status": "not_required",
            "findings": "compliant",
        }
    )
    write_csv(audit_path, audit, audit_fields)

    nb = sum(1 for r in audit if "notification_late" in r["findings"])
    ab = sum(1 for r in audit if "acknowledgement_late" in r["findings"])
    ua = sum(1 for r in audit if "acknowledger_unapproved" in r["findings"])
    me = sum(1 for r in audit if "escalation_missing" in r["findings"])
    co = sum(1 for r in audit if r["findings"].strip() == "compliant")
    counts = {
        "notification_breaches": nb,
        "acknowledgement_breaches": ab,
        "unapproved_acknowledgement_results": ua,
        "missing_escalation_results": me,
        "results_compliant": co,
    }
    print("counts", counts, "n", len(audit))
    for p in (
        PACK / "solution" / "files" / "results.json",
        PACK / "solution" / "golden_results.json",
    ):
        p.write_text(json.dumps(counts, indent=2) + "\n", encoding="utf-8")

    memo_path = PACK / "solution" / "files" / "results_memo.md"
    memo = memo_path.read_text(encoding="utf-8")
    memo = re.sub(
        r"# CR-7 critical results audit - \d+ results",
        f"# CR-7 critical results audit - {len(audit)} results",
        memo,
        count=1,
    )
    memo = re.sub(r"^\d+ results are clean\.", f"{co} results are clean.", memo, count=1, flags=re.M)
    if "**R-40**" not in memo.split("## Late notifications")[1].split("## Late or absent")[0]:
        memo = memo.replace(
            "## Late notifications\n\n",
            "## Late notifications\n\n"
            "- **R-40** (tier 1) - notified 31 min after clock start (limit 30 min). Clock started 2026-06-23T10:00. "
            "Acknowledgement was at exactly 60 min so no acknowledgement breach and no escalation required.\n",
            1,
        )
    add = (
        "\n- **R-39** - Sunday 07:00 tier-2 release: clock starts 08:00 the same morning; "
        "30/480 minute figures are within windows, so compliant.\n"
        "- **R-41** - Friday 17:59 tier-2 release: clock starts immediately; acknowledgement at exactly 480 min is within the inclusive window.\n"
    )
    if "R-39" not in memo:
        memo = memo.replace("## What is not a finding\n", "## What is not a finding\n" + add, 1)
    memo_path.write_text(memo, encoding="utf-8", newline="\n")

    vj = PACK / "tests" / "verifier.json"
    data = json.loads(vj.read_text(encoding="utf-8-sig"))

    def find(name: str):
        return next(v for v in data["verifiers"] if v["name"] == name)

    def upsert(name: str, template: str, expected: str, how: str, why: str):
        try:
            v = find(name)
        except StopIteration:
            v = json.loads(json.dumps(find(template)))
            v["name"] = name
            data["verifiers"].append(v)
        v["assertion"]["expected"] = expected
        v["metadata"]["how_justification"] = how
        v["metadata"]["why_justification"] = why

    ids = [f"R-{i:02d}" for i in range(1, 42)]
    find("audit_covers_every_result")["assertion"]["expected"] = "(?s)" + "".join(
        rf"(?=.*\b{i}\b)" for i in ids
    )
    find("audit_covers_every_result")["metadata"][
        "how_justification"
    ] = "Requires every register ID R-01 through R-41."
    find("audit_covers_every_result")["metadata"][
        "why_justification"
    ] = "All 41 results appear in the audit CSV."

    find("result_notification_breaches")["assertion"]["expected"] = nb
    find("result_acknowledgement_breaches")["assertion"]["expected"] = ab
    find("result_unapproved_acknowledgement_results")["assertion"]["expected"] = ua
    find("result_missing_escalation_results")["assertion"]["expected"] = me
    find("result_results_compliant")["assertion"]["expected"] = co

    upsert(
        "sunday_pre_core_clock_at_0800",
        "early_tier_two_clock_starts_at_core_open",
        r"(?mi)^\x22?R-39\x22?\s*,[^\n]*2026-06-21[T ]0?8:00[^\n]*\x22?(compliant|ok|pass|none|no[_ ]?finding)\x22?\s*$",
        "R-39 Sunday 07:00 release must use clock_start 08:00 and stay compliant.",
        "R-39 pre-core Sunday clock.",
    )
    upsert(
        "notify_late_ack_ok_no_escalation",
        "acknowledgement_boundary_is_inclusive",
        r"(?mi)^\x22?R-40\x22?\s*,[^\n]*,\s*\x22?\s*31(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*60(?:\.0+)?\s*\x22?\s*,[^\n]*,\s*\x22?not_required\x22?\s*,[^\n]*notification_late",
        "R-40: notification_late at 31, ack exactly 60, escalation not_required.",
        "R-40 late notify without ack/escalation breach.",
    )
    upsert(
        "before_close_ack_exactly_480_compliant",
        "tier_two_before_closing_clock_starts_at_release",
        r"(?mi)^\x22?R-41\x22?\s*,[^\n]*2026-06-22[T ]17:59[^\n]*,\s*\x22?\s*31(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*480(?:\.0+)?\s*\x22?\s*,[^\n]*\x22?(compliant|ok|pass|none|no[_ ]?finding)\x22?\s*$",
        "R-41 17:59 release with ack at exactly 480 must be compliant.",
        "R-41 inclusive ack at closing-day clock.",
    )
    upsert(
        "memo_lists_r40_late_notification",
        "memo_lists_late_notifications",
        r"(?is)\bR-40\b.{0,300}(?:notif|31|30[\s-]?min|late|limit|window)",
        "Memo must explain R-40 late notification.",
        "R-40 late notification covered in memo.",
    )

    for v in data["verifiers"]:
        exp = v["assertion"].get("expected")
        if isinstance(exp, str) and exp.startswith("(?"):
            re.compile(exp)

    vj.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print("verifiers", len(data["verifiers"]))


if __name__ == "__main__":
    main()
