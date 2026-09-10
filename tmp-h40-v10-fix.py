#!/usr/bin/env python3
"""Finish health-h40 v10 Harbor fairness fixes."""
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


def main() -> None:
    # --- instruction.md: rewrite the disclosure paragraph cleanly ---
    instr = (PACK / "instruction.md").read_text(encoding="utf-8")
    # Strip any corrupted control chars from prior bad write
    instr = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", instr)

    disclosure = (
        "When an acknowledger role is not approved by the procedure "
        "(for example ward_clerk or nurse_hca), that entry is not a recognised "
        "acknowledgement: leave acknowledgement_minutes empty, record "
        "acknowledger_unapproved in findings, and in the memo name the role "
        "using the register token (e.g. ward_clerk) or the words unapproved / "
        "not on the approved list (prose forms such as \"ward clerk\" are also "
        "acceptable). Write numeric CSV fields without surrounding quotes "
        "(e.g. 60, not \"60\")."
    )

    # Replace the broken multi-line disclosure if present, else insert after memo paragraph
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
    (PACK / "instruction.md").write_text(instr, encoding="utf-8", newline="\n")

    # --- audit counts ---
    audit_path = PACK / "solution" / "files" / "results_audit.csv"
    rows = list(csv.DictReader(audit_path.open(encoding="utf-8")))
    nb = sum(1 for r in rows if "notification_late" in (r["findings"] or ""))
    ab = sum(1 for r in rows if "acknowledgement_late" in (r["findings"] or ""))
    ua = sum(1 for r in rows if "acknowledger_unapproved" in (r["findings"] or ""))
    me = sum(1 for r in rows if "escalation_missing" in (r["findings"] or ""))
    co = sum(
        1
        for r in rows
        if (r["findings"] or "").strip()
        in ("compliant", "ok", "pass", "none", "no_finding")
    )
    counts = {
        "notification_breaches": nb,
        "acknowledgement_breaches": ab,
        "unapproved_acknowledgement_results": ua,
        "missing_escalation_results": me,
        "results_compliant": co,
    }
    print("counts", counts)

    for p in (
        PACK / "solution" / "files" / "results.json",
        PACK / "solution" / "golden_results.json",
    ):
        p.write_text(json.dumps(counts, indent=2) + "\n", encoding="utf-8")

    # --- verifier.json ---
    vj = PACK / "tests" / "verifier.json"
    data = json.loads(vj.read_text(encoding="utf-8-sig"))
    for v in data["verifiers"]:
        n = v["name"]
        a = v["assertion"]
        if n == "result_notification_breaches":
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
            # allow optional quotes around numeric minutes
            a["expected"] = (
                r"(?mi)^\x22?R-13\x22?\s*,[^\n]*,\s*\x22?\s*50(?:\.0+)?\s*\x22?\s*,"
                r"[^\n]*(late|breach|overdue|fail)"
            )
        elif n == "memo_has_explanatory_body":
            a["expected"] = (
                r"(?is)(?=[\s\S]{900,})"
                r"(?=.*\b(?:because|limit|window|clock start|escalat|"
                r"unapproved|not on the approved|recognised|recognized|notified)\b)"
            )
        elif n == "unapproved_acknowledger_flagged":
            a["expected"] = (
                r"(?mi)^\x22?R-06\x22?\s*,[^\n]*"
                r"(unapprov|not[_ ]?approved|invalid|unauthoris|ward_clerk)"
            )

    # validate all regex expecteds compile
    for v in data["verifiers"]:
        exp = v["assertion"].get("expected")
        if isinstance(exp, str) and exp.startswith("(?") or (
            isinstance(exp, str) and "\\" in exp and v["assertion"].get("type") in (
                None,
                "regex",
                "matches",
                "regex_match",
            )
        ):
            try:
                re.compile(exp)
            except re.error as e:
                # Only compile if it looks like a regex (common in this pack)
                if v["assertion"].get("operator") in (
                    "regex",
                    "matches",
                    "regex_match",
                    "contains_regex",
                ) or "regex" in str(v.get("assertion", {})).lower():
                    raise SystemExit(f"bad regex {v['name']}: {e}\n{exp}")
                # Heuristic: try compile all string expecteds that start with (?
                pass
        if isinstance(exp, str) and exp.startswith("(?"):
            re.compile(exp)

    vj.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print("verifier updated; instruction cleaned")
    print("instruction disclosure ok:", "ward clerk" in (PACK / "instruction.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
