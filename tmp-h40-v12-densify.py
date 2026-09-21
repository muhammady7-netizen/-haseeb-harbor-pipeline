#!/usr/bin/env python3
"""h40 v12 densify after v11 TOO_EASY (Oracle 1.0 / GLM 4/4). Keep Harbor fairness (ack=15)."""
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
    cr = [r for r in csv.DictReader(cr_path.open(encoding="utf-8-sig")) if r["result_id"] not in ("R-36", "R-37", "R-38")]
    # Midnight inclusive notification (cross midnight, exactly 30) — compliant
    cr.append(
        {
            "result_id": "R-36",
            "tier": "1",
            "test": "troponin",
            "released_at": "2026-06-22T23:50",
            "notified_at": "2026-06-23T00:20",
            "acknowledged_at": "2026-06-23T00:50",
            "acknowledged_by_role": "advanced_nurse_practitioner",
        }
    )
    # Saturday evening tier-2 → Sunday 08:00 clock; long wall-clock but compliant
    cr.append(
        {
            "result_id": "R-37",
            "tier": "2",
            "test": "sodium",
            "released_at": "2026-06-20T19:00",
            "notified_at": "2026-06-21T08:00",
            "acknowledged_at": "2026-06-21T15:59",
            "acknowledged_by_role": "consultant",
        }
    )
    # Friday 18:00 exact → Sat 08:00 clock; notify/ack exactly at inclusive limits
    cr.append(
        {
            "result_id": "R-38",
            "tier": "2",
            "test": "inr",
            "released_at": "2026-06-19T18:00",
            "notified_at": "2026-06-20T12:00",
            "acknowledged_at": "2026-06-20T16:00",
            "acknowledged_by_role": "specialty_registrar",
        }
    )
    write_csv(cr_path, cr, cr_fields)

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
    audit = [r for r in csv.DictReader(audit_path.open(encoding="utf-8-sig")) if r["result_id"] not in ("R-36", "R-37", "R-38")]
    audit.append(
        {
            "result_id": "R-36",
            "tier": "1",
            "clock_start": "2026-06-22T23:50",
            "notification_minutes": "30",
            "acknowledgement_minutes": "60",
            "acknowledged_by_role": "advanced_nurse_practitioner",
            "escalation_status": "not_required",
            "findings": "compliant",
        }
    )
    audit.append(
        {
            "result_id": "R-37",
            "tier": "2",
            "clock_start": "2026-06-21T08:00",
            "notification_minutes": "0",
            "acknowledgement_minutes": "479",
            "acknowledged_by_role": "consultant",
            "escalation_status": "not_required",
            "findings": "compliant",
        }
    )
    audit.append(
        {
            "result_id": "R-38",
            "tier": "2",
            "clock_start": "2026-06-20T08:00",
            "notification_minutes": "240",
            "acknowledgement_minutes": "480",
            "acknowledged_by_role": "specialty_registrar",
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
    # bump header count
    memo = re.sub(r"# CR-7 critical results audit - \d+ results", f"# CR-7 critical results audit - {len(audit)} results", memo, count=1)
    memo = re.sub(r"^\d+ results are clean\.", f"{co} results are clean.", memo, count=1, flags=re.M)
    add_not = (
        "\n- **R-36** - midnight-crossing tier 1: notified at exactly 30 min and acknowledged at exactly 60 min "
        "(inclusive windows), so it is compliant despite crossing midnight.\n"
        "- **R-37** - Saturday 19:00 release: tier-2 clock starts Sunday 08:00; notification at clock open (0 min) "
        "and acknowledgement at 479 min are within windows.\n"
        "- **R-38** - Friday 18:00 release: clock starts Saturday 08:00; notified at exactly 240 min and "
        "acknowledged at exactly 480 min (inclusive), compliant.\n"
    )
    if "R-36" not in memo:
        if "## What is not a finding" in memo:
            memo = memo.replace("## What is not a finding\n", "## What is not a finding\n" + add_not, 1)
        else:
            memo += "\n## What is not a finding\n" + add_not
    memo_path.write_text(memo, encoding="utf-8", newline="\n")

    # instruction: disclose ANP is approved; midnight continuous; Sat evening -> next morning
    instr = (PACK / "instruction.md").read_text(encoding="utf-8")
    tip = (
        "Tier 1 clocks run across midnight without reset. "
        "`advanced_nurse_practitioner` is an approved acknowledger role. "
        "A tier 2 result released on Saturday evening still starts at 08:00 the next morning "
        "(Sunday), because core hours are not weekday-only."
    )
    if "advanced_nurse_practitioner` is an approved" not in instr:
        if "naming a particular result ID is optional." in instr:
            instr = instr.replace(
                "naming a particular result ID is optional.",
                "naming a particular result ID is optional. " + tip,
                1,
            )
        else:
            instr = instr.rstrip() + "\n" + tip + "\n"
    (PACK / "instruction.md").write_text(instr, encoding="utf-8", newline="\n")

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

    ids = [f"R-{i:02d}" for i in range(1, 39)]
    find("audit_covers_every_result")["assertion"]["expected"] = "(?s)" + "".join(rf"(?=.*\b{i}\b)" for i in ids)
    find("audit_covers_every_result")["metadata"]["how_justification"] = (
        "Requires every register ID R-01 through R-38 to appear in results_audit.csv."
    )
    find("audit_covers_every_result")["metadata"]["why_justification"] = "All 38 results appear in the audit CSV."

    find("result_notification_breaches")["assertion"]["expected"] = nb
    find("result_acknowledgement_breaches")["assertion"]["expected"] = ab
    find("result_unapproved_acknowledgement_results")["assertion"]["expected"] = ua
    find("result_missing_escalation_results")["assertion"]["expected"] = me
    find("result_results_compliant")["assertion"]["expected"] = co

    upsert(
        "midnight_inclusive_windows_compliant",
        "acknowledgement_boundary_is_inclusive",
        r"(?mi)^\x22?R-36\x22?\s*,[^\n]*,\s*\x22?\s*30(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*60(?:\.0+)?\s*\x22?\s*,[^\n]*\x22?(compliant|ok|pass|none|no[_ ]?finding)\x22?\s*$",
        "R-36 midnight-crossing inclusive 30/60 must stay compliant.",
        "R-36 is compliant at inclusive midnight boundaries.",
    )
    upsert(
        "saturday_evening_tier_two_clock_sunday",
        "evening_tier_two_clock_starts_next_morning",
        r"(?mi)^\x22?R-37\x22?\s*,[^\n]*2026-06-21[T ]0?8:00[^\n]*\x22?(compliant|ok|pass|none|no[_ ]?finding)\x22?\s*$",
        "R-37 Saturday evening release must start clock Sunday 08:00 and stay compliant.",
        "R-37 weekend evening clock start.",
    )
    upsert(
        "friday_closing_inclusive_compliant",
        "sunday_inclusive_windows_are_compliant",
        r"(?mi)^\x22?R-38\x22?\s*,[^\n]*,\s*\x22?\s*240(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*480(?:\.0+)?\s*\x22?\s*,[^\n]*\x22?(compliant|ok|pass|none|no[_ ]?finding)\x22?\s*$",
        "R-38 Friday 18:00 → Saturday clock with inclusive 240/480 must be compliant.",
        "R-38 inclusive Friday-close case.",
    )
    upsert(
        "audit_role_r36_is_anp",
        "audit_role_r06_is_ward_clerk",
        r"(?mi)^\x22?R-36\x22?\s*,[^\n]*\badvanced_nurse_practitioner\b",
        "R-36 acknowledged_by_role must be advanced_nurse_practitioner.",
        "ANP is an approved role on R-36.",
    )
    upsert(
        "memo_explains_midnight_or_weekend_non_breach",
        "memo_keeps_r34_as_not_a_breach",
        r"(?is)(?:midnight|Saturday|Sunday|weekend|inclusive|19:00|18:00|advanced_nurse).{0,300}(?:compliant|within|not a (?:finding|breach)|exactly)",
        "Memo must explain a midnight/weekend inclusive non-breach case.",
        "Densify non-breach explanation present.",
    )

    # tighten a couple of timing traps agents often miss
    upsert(
        "row_r31_notification_minutes",
        "night_tier_one_breaches_both_windows",
        r"(?mi)^\x22?R-31\x22?\s*,[^\n]*,\s*\x22?\s*35(?:\.0+)?\s*\x22?\s*,[^\n]*notification_late",
        "R-31 must show notification_minutes 35 with notification_late.",
        "R-31 night notification timing.",
    )

    for v in data["verifiers"]:
        exp = v["assertion"].get("expected")
        if isinstance(exp, str) and exp.startswith("(?"):
            re.compile(exp)

    vj.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print("verifiers", len(data["verifiers"]))


if __name__ == "__main__":
    main()
