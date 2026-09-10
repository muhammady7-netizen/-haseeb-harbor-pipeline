#!/usr/bin/env python3
"""health-h40 v10: Harbor fairness + densify (R-34/R-35)."""
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
    # --- input: add densify rows ---
    cr_path = PACK / "environment" / "input" / "critical_results.csv"
    cr_fields = [
        "result_id",
        "tier",
        "test",
        "released_at",
        "notified_at",
        "acknowledged_at",
        "acknowledged_by_role",
    ]
    cr = list(csv.DictReader(cr_path.open(encoding="utf-8-sig")))
    cr = [r for r in cr if r["result_id"] not in ("R-34", "R-35")]
    cr.append(
        {
            "result_id": "R-34",
            "tier": "2",
            "test": "sodium",
            # Sunday core hours: clock starts at release; exact inclusive windows
            "released_at": "2026-06-21T09:00",
            "notified_at": "2026-06-21T13:00",  # exactly 240
            "acknowledged_at": "2026-06-21T17:00",  # exactly 480
            "acknowledged_by_role": "consultant",
        }
    )
    cr.append(
        {
            "result_id": "R-35",
            "tier": "1",
            "test": "potassium",
            "released_at": "2026-06-22T09:00",
            "notified_at": "2026-06-22T09:10",
            "acknowledged_at": "2026-06-22T10:30",  # 90 min, unapproved role
            "acknowledged_by_role": "phlebotomist",
        }
    )
    write_csv(cr_path, cr, cr_fields)

    # no escalation for R-35
    esc_path = PACK / "environment" / "input" / "escalations.csv"
    esc = list(csv.DictReader(esc_path.open(encoding="utf-8-sig")))
    write_csv(esc_path, esc, ["result_id", "escalated_at"])

    # --- gold audit ---
    audit_path = PACK / "solution" / "files" / "results_audit.csv"
    audit_fields = [
        "result_id",
        "tier",
        "clock_start",
        "notification_minutes",
        "acknowledgement_minutes",
        "acknowledged_by_role",
        "escalation_status",
        "findings",
    ]
    audit = list(csv.DictReader(audit_path.open(encoding="utf-8-sig")))
    audit = [r for r in audit if r["result_id"] not in ("R-34", "R-35")]
    audit.append(
        {
            "result_id": "R-34",
            "tier": "2",
            "clock_start": "2026-06-21T09:00",
            "notification_minutes": "240",
            "acknowledgement_minutes": "480",
            "acknowledged_by_role": "consultant",
            "escalation_status": "not_required",
            "findings": "compliant",
        }
    )
    audit.append(
        {
            "result_id": "R-35",
            "tier": "1",
            "clock_start": "2026-06-22T09:00",
            "notification_minutes": "10",
            "acknowledgement_minutes": "",
            "acknowledged_by_role": "phlebotomist",
            "escalation_status": "missing",
            "findings": "acknowledger_unapproved;acknowledgement_late;escalation_missing",
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
    print("counts", counts, "n=", len(audit))

    for p in (
        PACK / "solution" / "files" / "results.json",
        PACK / "solution" / "golden_results.json",
    ):
        p.write_text(json.dumps(counts, indent=2) + "\n", encoding="utf-8")

    # --- memo ---
    memo = f"""# CR-7 critical results audit - {len(audit)} results

{co} results are clean.

## Late notifications

- **R-02** (tier 1) - notified 45 min after clock start (limit 30 min). Clock started 2026-06-15T22:10.
- **R-09** (tier 2) - notified 300 min after clock start (limit 240 min). Clock started 2026-06-15T08:30.
- **R-13** (tier 1) - notified 50 min after clock start (limit 30 min). Clock started 2026-06-15T21:00.
- **R-16** (tier 2) - notified 931 min after clock start (limit 240 min). Clock started 2026-06-15T17:59.
- **R-21** (tier 1) - notified 36 min after clock start (limit 30 min). Clock started 2026-06-17T23:59.
- **R-26** (tier 1) - notified 31 min after clock start (limit 30 min). Clock started 2026-06-17T16:00.
- **R-31** (tier 1) - notified 35 min after clock start (limit 30 min). Clock started 2026-06-20T23:00.

## Late or absent acknowledgements

- **R-03** - acknowledged at 80 min after clock start (limit 60 min). Clock started 2026-06-15T14:00.
- **R-04** - acknowledged at 90 min after clock start (limit 60 min). Clock started 2026-06-16T03:00.
- **R-10** - has no recognised acknowledgement (limit 480 min). Clock started 2026-06-15T10:00.
- **R-13** - acknowledged at 90 min after clock start (limit 60 min). Clock started 2026-06-15T21:00.
- **R-15** - acknowledged at 510 min after clock start (limit 480 min). Clock started 2026-06-15T16:00.
- **R-16** - acknowledged at 1081 min after clock start (limit 480 min). Clock started 2026-06-15T17:59.
- **R-21** - acknowledged at 71 min after clock start (limit 60 min). Clock started 2026-06-17T23:59.
- **R-24** - acknowledged at 481 min after clock start (limit 480 min). Clock started 2026-06-17T11:00.
- **R-27** - acknowledged at 481 min after clock start (limit 480 min). Clock started 2026-06-17T17:59.
- **R-30** - acknowledged at 481 min after clock start (limit 480 min). Clock started 2026-06-21T10:00.
- **R-32** - acknowledged at 3841 min after clock start (limit 480 min). Clock started 2026-06-19T17:59.
- **R-33** - acknowledged at 490 min after clock start (limit 480 min). Clock started 2026-06-20T08:00.
- **R-35** - no recognised acknowledgement because the register entry is by an unapproved role (limit 60 min). Clock started 2026-06-22T09:00.

## Unapproved acknowledger

- **R-06** - register shows ward_clerk; that role is unapproved / not on the approved list, so CR-7 treats it as no acknowledgement (acknowledgement_minutes left empty). Escalation was recorded.
- **R-22** - register shows nurse_hca; that role is unapproved / not on the approved list, so there is no recognised acknowledgement (acknowledgement_minutes left empty). Escalation was recorded.
- **R-35** - register shows phlebotomist; that role is unapproved / not on the approved list, so acknowledgement_minutes is left empty. The acknowledgement window was missed and no escalation appears on the register.

## Missing escalation

- **R-04** - missed acknowledgement window with no escalation on register.
- **R-13** - missed acknowledgement window with no escalation on register.
- **R-16** - missed acknowledgement window with no escalation on register.
- **R-21** - missed acknowledgement window with no escalation on register.
- **R-30** - missed acknowledgement window with no escalation on register.
- **R-33** - missed acknowledgement window with no escalation on register.
- **R-35** - missed acknowledgement window with no escalation on register (unapproved phlebotomist entry does not close the window).

## What is not a finding

- Weekend results: the charter says core hours are 08:00-18:00 without excluding weekends, so Sunday clocks still run.
- **R-34** - tier 2 on Sunday; notified at exactly 240 min and acknowledged at exactly 480 min after clock start, so both inclusive limits are met and it is compliant.
- R-32 released Friday 17:59: clock starts immediately (within core hours), not Monday.
- R-33 released Friday 18:00: clock starts Saturday 08:00 (next morning), not Monday.
- Out-of-hours tier 2 results with long wall-clock times that are compliant.
- Inclusive boundaries: exactly at the window limit is within it.
- An escalation that was not required is not a finding.
"""
    (PACK / "solution" / "files" / "results_memo.md").write_text(
        memo, encoding="utf-8", newline="\n"
    )

    # --- instruction disclosure (clean) ---
    instr_path = PACK / "instruction.md"
    instr = instr_path.read_text(encoding="utf-8")
    instr = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", instr)
    for a, b in (
        ("\u2014", "-"),
        ("\u2013", "-"),
        ("\u2019", "'"),
        ("\u201c", '"'),
        ("\u201d", '"'),
    ):
        instr = instr.replace(a, b)
    disclosure = (
        "When an acknowledger role is not approved by the procedure "
        "(for example ward_clerk, nurse_hca, or phlebotomist), that entry is not a "
        "recognised acknowledgement: leave acknowledgement_minutes empty, record "
        "acknowledger_unapproved in findings, and in the memo name the role using the "
        "register token (e.g. ward_clerk) or the words unapproved / not on the approved "
        'list (prose forms such as "ward clerk" are also acceptable). Write numeric CSV '
        'fields without surrounding quotes (e.g. 60, not "60").'
    )
    if "When an acknowledger role is not approved" in instr:
        instr = re.sub(
            r"When an acknowledger role is not approved.*?(?=\n- The attachments)",
            disclosure + "\n",
            instr,
            count=1,
            flags=re.S,
        )
    else:
        instr = instr.replace(
            "does not satisfy this requirement.\n",
            "does not satisfy this requirement.\n" + disclosure + "\n",
            1,
        )
    instr_path.write_text(instr, encoding="utf-8", newline="\n")

    # --- verifier.json ---
    vj = PACK / "tests" / "verifier.json"
    data = json.loads(vj.read_text(encoding="utf-8-sig"))

    ids = [f"R-{i:02d}" for i in range(1, 36)]
    covers = "(?s)" + "".join(rf"(?=.*\b{i}\b)" for i in ids)

    def upsert(name: str, template_from: str, **updates):
        existing = next((v for v in data["verifiers"] if v["name"] == name), None)
        if existing is None:
            base = json.loads(
                json.dumps(next(v for v in data["verifiers"] if v["name"] == template_from))
            )
            base["name"] = name
            data["verifiers"].append(base)
            existing = base
        for k, v in updates.items():
            if k == "expected":
                existing["assertion"]["expected"] = v
            elif k == "how":
                existing["metadata"]["how_justification"] = v
            elif k == "why":
                existing["metadata"]["why_justification"] = v
            else:
                existing[k] = v

    for v in data["verifiers"]:
        n = v["name"]
        a = v["assertion"]
        if n == "audit_covers_every_result":
            a["expected"] = covers
            v["metadata"]["how_justification"] = (
                "Requires every register ID R-01 through R-35 to appear in results_audit.csv."
            )
            v["metadata"]["why_justification"] = "All 35 results appear in the audit CSV."
        elif n == "result_notification_breaches":
            a["expected"] = nb
        elif n == "result_acknowledgement_breaches":
            a["expected"] = ab
        elif n == "result_unapproved_acknowledgement_results":
            a["expected"] = ua
        elif n == "result_missing_escalation_results":
            a["expected"] = me
        elif n == "result_results_compliant":
            a["expected"] = co
        elif n == "memo_names_the_unapproved_acknowledgement":
            a["expected"] = (
                r"(?is)\bR-06\b.{0,500}(?:unapproved|ward[_\s-]?clerk|"
                r"not on the approved|cannot act|not recognised|not recognized)"
            )
        elif n == "acknowledgement_boundary_is_inclusive":
            a["expected"] = (
                r"(?mi)^\x22?R-05\x22?\s*,[^\n]*,\s*\x22?\s*60(?:\.0+)?\s*\x22?\s*,"
                r"[^\n]*\x22?(compliant|ok|pass|none|no[_ ]?finding)\x22?\s*$"
            )
        elif n == "tier_one_clock_runs_continuously":
            a["expected"] = (
                r"(?mi)^\x22?R-12\x22?\s*,[^\n]*,\s*\x22?\s*20(?:\.0+)?\s*\x22?\s*,"
                r"\s*\x22?\s*50(?:\.0+)?\s*\x22?\s*,[^\n]*\x22?"
                r"(compliant|ok|pass|none|no[_ ]?finding)\x22?\s*$"
            )
        elif n == "tier_two_after_hours_ack_breach":
            a["expected"] = (
                r"(?mi)^\x22?R-15\x22?\s*,[^\n]*,\s*\x22?\s*240(?:\.0+)?\s*\x22?\s*,"
                r"\s*\x22?\s*510(?:\.0+)?\s*\x22?\s*,[^\n]*(late|breach|overdue|fail)"
            )
        elif n == "compliant_with_unnecessary_escalation":
            a["expected"] = (
                r"(?mi)^\x22?R-17\x22?\s*,[^\n]*,\s*\x22?\s*20(?:\.0+)?\s*\x22?\s*,"
                r"\s*\x22?\s*50(?:\.0+)?\s*\x22?\s*,[^\n]*\x22?"
                r"(compliant|ok|pass|none|no[_ ]?finding)\x22?\s*$"
            )
        elif n == "night_tier_one_breaches_both_windows":
            a["expected"] = (
                r"(?mi)^\x22?R-13\x22?\s*,[^\n]*,\s*\x22?\s*50(?:\.0+)?\s*\x22?\s*,"
                r"[^\n]*(late|breach|overdue|fail)"
            )
        elif n == "memo_has_explanatory_body":
            # depth: length + multiple explanatory anchors (not ID-only padding)
            a["expected"] = (
                r"(?is)(?=[\s\S]{900,})"
                r"(?=.*\blimit\b)(?=.*\b(?:window|clock start)\b)"
                r"(?=.*\b(?:unapproved|not on the approved)\b)"
                r"(?=.*\bescalat)"
                r"(?=.*\b(?:because|so CR-7|treats it|recognised|recognized)\b)"
            )
        elif n == "unapproved_acknowledger_flagged":
            a["expected"] = (
                r"(?mi)^\x22?R-06\x22?\s*,[^\n]*"
                r"(unapprov|not[_ ]?approved|invalid|unauthoris|ward_clerk)"
            )
        elif n == "memo_lists_ack_breaches":
            a["expected"] = (
                r"(?is)\bR-03\b.{0,300}(?:limit|window|80\s*min|60[\s-]?min|acknowled)"
            )
        elif n == "memo_lists_late_notifications":
            a["expected"] = (
                r"(?is)\bR-02\b.{0,300}(?:limit|window|notif|telephon|30[\s-]?min|late)"
            )
        elif n == "memo_addresses_escalation":
            a["expected"] = (
                r"(?is)(?=.*\b(?:R-04|R-13|R-16|R-35)\b).{0,600}?"
                r"(?:escalat|escalation register|missing)"
            )

    # role column assertions (Harbor coverage_depth)
    upsert(
        "audit_role_r06_is_ward_clerk",
        "unapproved_acknowledger_flagged",
        expected=r"(?mi)^\x22?R-06\x22?\s*,[^\n]*\bward_clerk\b",
        how="Requires results_audit.csv R-06 acknowledged_by_role to carry ward_clerk.",
        why="R-06 role token is ward_clerk.",
    )
    upsert(
        "audit_role_r22_is_nurse_hca",
        "unapproved_acknowledger_flagged",
        expected=r"(?mi)^\x22?R-22\x22?\s*,[^\n]*\bnurse_hca\b",
        how="Requires results_audit.csv R-22 acknowledged_by_role to carry nurse_hca.",
        why="R-22 role token is nurse_hca.",
    )
    upsert(
        "audit_role_r35_is_phlebotomist",
        "unapproved_acknowledger_flagged",
        expected=r"(?mi)^\x22?R-35\x22?\s*,[^\n]*\bphlebotomist\b",
        how="Requires results_audit.csv R-35 acknowledged_by_role to carry phlebotomist.",
        why="R-35 role token is phlebotomist.",
    )
    upsert(
        "sunday_inclusive_windows_are_compliant",
        "acknowledgement_boundary_is_inclusive",
        expected=(
            r"(?mi)^\x22?R-34\x22?\s*,[^\n]*,\s*\x22?\s*240(?:\.0+)?\s*\x22?\s*,"
            r"\s*\x22?\s*480(?:\.0+)?\s*\x22?\s*,[^\n]*\x22?"
            r"(compliant|ok|pass|none|no[_ ]?finding)\x22?\s*$"
        ),
        how="R-34 must keep inclusive tier-2 limits (240/480) as compliant on a Sunday.",
        why="Sunday inclusive boundary case is compliant.",
    )
    upsert(
        "unapproved_past_window_missing_escalation",
        "unapproved_acknowledger_flagged",
        expected=(
            r"(?mi)^\x22?R-35\x22?\s*,[^\n]*(?=.*unapprov)(?=.*(?:missing|absent))"
            r"(?=.*(?:acknowledgement_late|late|unapprov))"
        ),
        how="R-35 must flag unapproved role plus missing escalation after a void acknowledgement.",
        why="R-35 carries unapproved + missing escalation.",
    )
    upsert(
        "memo_names_phlebotomist_unapproved",
        "memo_names_the_unapproved_acknowledgement",
        expected=(
            r"(?is)\bR-35\b.{0,500}(?:unapproved|phlebotomist|not on the approved|"
            r"not recognised|not recognized)"
        ),
        how="Memo must explain R-35 unapproved phlebotomist near the ID.",
        why="R-35 unapproved role named in memo.",
    )
    upsert(
        "memo_keeps_r34_as_not_a_breach",
        "memo_addresses_the_clock_start",
        expected=(
            r"(?is)\bR-34\b.{0,400}(?:compliant|within|inclusive|exactly|not a "
            r"(?:finding|breach)|limit)"
        ),
        how="Memo must explain R-34 as within inclusive limits / not a breach.",
        why="R-34 long-looking Sunday case explained as compliant.",
    )

    # compile check
    for v in data["verifiers"]:
        exp = v["assertion"].get("expected")
        if isinstance(exp, str) and exp.startswith("(?"):
            re.compile(exp)

    vj.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print("verifiers", len(data["verifiers"]))


if __name__ == "__main__":
    main()
