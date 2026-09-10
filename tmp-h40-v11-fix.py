#!/usr/bin/env python3
"""h40 v11: Harbor fixes from #f077d3 (ack=15, soften memo, densify row asserts)."""
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
    audit_path = PACK / "solution" / "files" / "results_audit.csv"
    fields = list(csv.DictReader(audit_path.open(encoding="utf-8-sig")).fieldnames or [])
    audit = list(csv.DictReader(audit_path.open(encoding="utf-8-sig")))

    by_id = {r["result_id"]: r for r in audit}
    # Harbor: unapproved + missed window => also acknowledgement_late (R-06/R-22 like R-35)
    for rid in ("R-06", "R-22"):
        r = by_id[rid]
        findings = [x.strip() for x in r["findings"].split(";") if x.strip()]
        if "acknowledgement_late" not in findings:
            # keep unapproved first for readability
            if "acknowledger_unapproved" in findings:
                findings = ["acknowledger_unapproved", "acknowledgement_late"] + [
                    f for f in findings if f not in ("acknowledger_unapproved", "acknowledgement_late")
                ]
            else:
                findings.append("acknowledgement_late")
            r["findings"] = ";".join(findings)
        r["acknowledgement_minutes"] = ""
    write_csv(audit_path, audit, fields)

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
    assert ab == 15, counts
    print("counts", counts)

    for p in (
        PACK / "solution" / "files" / "results.json",
        PACK / "solution" / "golden_results.json",
    ):
        p.write_text(json.dumps(counts, indent=2) + "\n", encoding="utf-8")

    # memo: mention R-06/R-22 as late+unapproved; keep explanatory words without requiring 'limit'
    memo = (PACK / "solution" / "files" / "results_memo.md").read_text(encoding="utf-8")
    memo = memo.replace(
        "- **R-06** - register shows ward_clerk; that role is unapproved / not on the approved list, so CR-7 treats it as no acknowledgement (acknowledgement_minutes left empty). Escalation was recorded.",
        "- **R-06** - register shows ward_clerk; that role is unapproved / not on the approved list, so CR-7 treats it as no acknowledgement (acknowledgement_minutes left empty). Because there is no recognised acknowledgement the acknowledgement window was missed; escalation was recorded.",
    )
    memo = memo.replace(
        "- **R-22** - register shows nurse_hca; that role is unapproved / not on the approved list, so there is no recognised acknowledgement (acknowledgement_minutes left empty). Escalation was recorded.",
        "- **R-22** - register shows nurse_hca; that role is unapproved / not on the approved list, so there is no recognised acknowledgement (acknowledgement_minutes left empty). Because there is no recognised acknowledgement the acknowledgement window was missed; escalation was recorded.",
    )
    # ensure late-ack section lists R-06/R-22
    if "**R-06**" not in memo.split("## Late or absent acknowledgements")[1].split("## Unapproved")[0]:
        memo = memo.replace(
            "## Late or absent acknowledgements\n\n",
            "## Late or absent acknowledgements\n\n"
            "- **R-06** - no recognised acknowledgement (unapproved ward_clerk), so the acknowledgement window was missed (window 60 min). Clock started 2026-06-15T16:00.\n"
            "- **R-22** - no recognised acknowledgement (unapproved nurse_hca), so the acknowledgement window was missed (window 60 min). Clock started 2026-06-17T14:00.\n",
            1,
        )
    (PACK / "solution" / "files" / "results_memo.md").write_text(memo, encoding="utf-8", newline="\n")

    # instruction: disclose unapproved => acknowledgement_late when window missed; Sunday inclusive example OK without forcing R-34 id in memo
    instr = (PACK / "instruction.md").read_text(encoding="utf-8")
    instr = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", instr)
    add = (
        "Where an unapproved role means there is no recognised acknowledgement and the "
        "acknowledgement window has been missed, record both `acknowledger_unapproved` and "
        "`acknowledgement_late` (and `escalation_missing` when no escalation appears). "
        "In the memo, when explaining long elapsed times that are not breaches, state the "
        "reason in plain language (for example inclusive window limits or core-hours clock start); "
        "naming a particular result ID is optional."
    )
    if "record both `acknowledger_unapproved` and" not in instr:
        if "Write numeric CSV fields" in instr:
            instr = instr.replace(
                "Write numeric CSV fields",
                add + " Write numeric CSV fields",
                1,
            )
        else:
            instr = instr.replace(
                "does not satisfy this requirement.\n",
                "does not satisfy this requirement.\n" + add + "\n",
                1,
            )
    (PACK / "instruction.md").write_text(instr, encoding="utf-8", newline="\n")

    # verifiers
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

    find("result_acknowledgement_breaches")["assertion"]["expected"] = ab
    find("result_notification_breaches")["assertion"]["expected"] = nb
    find("result_unapproved_acknowledgement_results")["assertion"]["expected"] = ua
    find("result_missing_escalation_results")["assertion"]["expected"] = me
    find("result_results_compliant")["assertion"]["expected"] = co

    # soften memo_has_explanatory_body — no singular \blimit\b
    find("memo_has_explanatory_body")["assertion"]["expected"] = (
        r"(?is)(?=[\s\S]{900,})"
        r"(?=.*\b(?:window|clock start|escalat|unapproved|not on the approved|"
        r"recognised|recognized|notified|inclusive|core.?hours)\b)"
        r"(?=.*\b(?:because|so CR-7|treats it|missed|within)\b)"
    )

    # remove brittle R-34-by-name requirement — replace with semantic not-a-breach language
    find("memo_keeps_r34_as_not_a_breach")["assertion"]["expected"] = (
        r"(?is)(?:inclusive|exactly|within (?:its|the) (?:window|limit)|not a (?:finding|breach)|"
        r"core.?hours|weekend|Sunday).{0,200}(?:compliant|within|not a (?:finding|breach)|met)"
    )
    find("memo_keeps_r34_as_not_a_breach")["metadata"]["how_justification"] = (
        "Memo must explain that an inclusive/core-hours long-elapsed case is not a breach "
        "(R-34 style), without requiring a specific ID token."
    )

    # tighten R-03 / R-04 to findings tokens, not loose anywhere-in-row tokens
    find("escalated_breach_not_double_counted")["assertion"]["expected"] = (
        r"(?mi)^\x22?R-03\x22?\s*,[^\n]*,[^\n]*,[^\n]*,[^\n]*,[^\n]*,\s*\x22?recorded\x22?\s*,"
        r"[^\n]*acknowledgement_late"
    )
    find("missing_escalation_flagged")["assertion"]["expected"] = (
        r"(?mi)^\x22?R-04\x22?\s*,[^\n]*,[^\n]*,[^\n]*,[^\n]*,[^\n]*,\s*\x22?missing\x22?\s*,"
        r"[^\n]*escalation_missing"
    )

    # R-06 / R-22 must carry both unapproved + acknowledgement_late
    upsert(
        "unapproved_r06_also_ack_late",
        "unapproved_acknowledger_flagged",
        r"(?mi)^\x22?R-06\x22?\s*,[^\n]*(?=.*acknowledger_unapproved)(?=.*acknowledgement_late)",
        "R-06 must flag both acknowledger_unapproved and acknowledgement_late.",
        "R-06 unapproved void ack also misses the window.",
    )
    upsert(
        "unapproved_r22_also_ack_late",
        "unapproved_acknowledger_flagged",
        r"(?mi)^\x22?R-22\x22?\s*,[^\n]*(?=.*acknowledger_unapproved)(?=.*acknowledgement_late)",
        "R-22 must flag both acknowledger_unapproved and acknowledgement_late.",
        "R-22 unapproved void ack also misses the window.",
    )

    # densify: per-row findings assertions for previously unchecked rows (sample of timing+findings)
    row_specs = {
        "R-01": ("not_required", "compliant"),
        "R-02": ("not_required", "notification_late"),
        "R-07": ("not_required", "compliant"),
        "R-09": ("not_required", "notification_late"),
        "R-10": ("recorded", "acknowledgement_late"),
        "R-18": ("not_required", "compliant"),
        "R-19": ("not_required", "compliant"),
        "R-20": ("not_required", "compliant"),
        "R-21": ("missing", "notification_late"),
        "R-23": ("not_required", "compliant"),
        "R-24": ("recorded", "acknowledgement_late"),
        "R-25": ("not_required", "compliant"),
        "R-26": ("not_required", "notification_late"),
        "R-28": ("not_required", "compliant"),
        "R-29": ("not_required", "compliant"),
        "R-30": ("missing", "acknowledgement_late"),
        "R-31": ("not_required", "notification_late"),
        "R-32": ("recorded", "acknowledgement_late"),
        "R-33": ("missing", "acknowledgement_late"),
    }
    for rid, (esc, finding) in row_specs.items():
        name = f"row_{rid.lower().replace('-', '_')}_findings"
        upsert(
            name,
            "unapproved_acknowledger_flagged",
            rf"(?mi)^\x22?{rid}\x22?\s*,[^\n]*,[^\n]*,[^\n]*,[^\n]*,[^\n]*,\s*\x22?{esc}\x22?\s*,[^\n]*{finding}",
            f"Asserts {rid} escalation_status={esc} and findings contain {finding}.",
            f"{rid} graded at row level.",
        )

    for v in data["verifiers"]:
        exp = v["assertion"].get("expected")
        if isinstance(exp, str) and exp.startswith("(?"):
            re.compile(exp)

    vj.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print("verifiers", len(data["verifiers"]))


if __name__ == "__main__":
    main()
