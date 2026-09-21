#!/usr/bin/env python3
"""h40 v14 densify — GLM still 4/4 TOO_EASY on content-a34a429.

Harder INPUT traps + matching gold + disclosed fairness notes + trap verifiers.
Keeps Harbor fairness: unapproved => empty ack minutes + acknowledgement_late when
window missed; ward_clerk alias OK; quoted numerics OK; no brittle memo \\blimit\\b.
"""
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

CR_FIELDS = [
    "result_id",
    "tier",
    "test",
    "released_at",
    "notified_at",
    "acknowledged_at",
    "acknowledged_by_role",
]
AUDIT_FIELDS = [
    "result_id",
    "tier",
    "clock_start",
    "notification_minutes",
    "acknowledgement_minutes",
    "acknowledged_by_role",
    "escalation_status",
    "findings",
]

# New traps R-57..R-66
NEW_CR = [
    # R-57: notified BEFORE tier-2 clock starts (evening release) → notify mins 0, compliant
    {
        "result_id": "R-57",
        "tier": "2",
        "test": "sodium",
        "released_at": "2026-06-26T19:00",
        "notified_at": "2026-06-26T19:45",
        "acknowledged_at": "2026-06-27T15:00",
        "acknowledged_by_role": "consultant",
    },
    # R-58: Sat 17:59 clock-at-release; ack exactly 480 overnight → compliant
    {
        "result_id": "R-58",
        "tier": "2",
        "test": "bilirubin",
        "released_at": "2026-06-27T17:59",
        "notified_at": "2026-06-27T18:30",
        "acknowledged_at": "2026-06-28T01:59",
        "acknowledged_by_role": "consultant",
    },
    # R-59: Sat 18:00 twin → Sun 08:00 clock; exact inclusive limits → compliant
    {
        "result_id": "R-59",
        "tier": "2",
        "test": "inr",
        "released_at": "2026-06-27T18:00",
        "notified_at": "2026-06-28T12:00",
        "acknowledged_at": "2026-06-28T16:00",
        "acknowledged_by_role": "specialty_registrar",
    },
    # R-60: tier-2 notify late (241) but ack within window → escalation not_required
    {
        "result_id": "R-60",
        "tier": "2",
        "test": "haemoglobin",
        "released_at": "2026-06-26T10:00",
        "notified_at": "2026-06-26T14:01",
        "acknowledged_at": "2026-06-26T17:59",
        "acknowledged_by_role": "consultant",
    },
    # R-61: ANP approved at exact 30/60 inclusive → compliant
    {
        "result_id": "R-61",
        "tier": "1",
        "test": "troponin",
        "released_at": "2026-06-26T11:00",
        "notified_at": "2026-06-26T11:30",
        "acknowledged_at": "2026-06-26T12:00",
        "acknowledged_by_role": "advanced_nurse_practitioner",
    },
    # R-62: ack at 61 (off-by-one) → acknowledgement_late + missing escalation
    {
        "result_id": "R-62",
        "tier": "1",
        "test": "potassium",
        "released_at": "2026-06-26T13:00",
        "notified_at": "2026-06-26T13:20",
        "acknowledged_at": "2026-06-26T14:01",
        "acknowledged_by_role": "resident_doctor",
    },
    # R-63: Sun 18:00 → Mon 08:00 clock; ack 481 late, no escalation
    {
        "result_id": "R-63",
        "tier": "2",
        "test": "creatinine",
        "released_at": "2026-06-28T18:00",
        "notified_at": "2026-06-29T08:30",
        "acknowledged_at": "2026-06-29T16:01",
        "acknowledged_by_role": "consultant",
    },
    # R-64: weekday 07:59 → 08:00 clock; exact 240/480 from 08:00 → compliant
    {
        "result_id": "R-64",
        "tier": "2",
        "test": "glucose",
        "released_at": "2026-06-26T07:59",
        "notified_at": "2026-06-26T12:00",
        "acknowledged_at": "2026-06-26T16:00",
        "acknowledged_by_role": "consultant",
    },
    # R-65: new unapproved role; empty minutes; late + missing escalation
    {
        "result_id": "R-65",
        "tier": "1",
        "test": "lactate",
        "released_at": "2026-06-26T15:00",
        "notified_at": "2026-06-26T15:10",
        "acknowledged_at": "2026-06-26T15:40",
        "acknowledged_by_role": "physician_associate",
    },
    # R-66: notify 31 late, ack 59 OK → notification_late only, not_required
    {
        "result_id": "R-66",
        "tier": "1",
        "test": "magnesium",
        "released_at": "2026-06-26T23:50",
        "notified_at": "2026-06-27T00:21",
        "acknowledged_at": "2026-06-27T00:49",
        "acknowledged_by_role": "consultant",
    },
]

NEW_AUDIT = [
    {
        "result_id": "R-57",
        "tier": "2",
        "clock_start": "2026-06-27T08:00",
        "notification_minutes": "0",
        "acknowledgement_minutes": "420",
        "acknowledged_by_role": "consultant",
        "escalation_status": "not_required",
        "findings": "compliant",
    },
    {
        "result_id": "R-58",
        "tier": "2",
        "clock_start": "2026-06-27T17:59",
        "notification_minutes": "31",
        "acknowledgement_minutes": "480",
        "acknowledged_by_role": "consultant",
        "escalation_status": "not_required",
        "findings": "compliant",
    },
    {
        "result_id": "R-59",
        "tier": "2",
        "clock_start": "2026-06-28T08:00",
        "notification_minutes": "240",
        "acknowledgement_minutes": "480",
        "acknowledged_by_role": "specialty_registrar",
        "escalation_status": "not_required",
        "findings": "compliant",
    },
    {
        "result_id": "R-60",
        "tier": "2",
        "clock_start": "2026-06-26T10:00",
        "notification_minutes": "241",
        "acknowledgement_minutes": "479",
        "acknowledged_by_role": "consultant",
        "escalation_status": "not_required",
        "findings": "notification_late",
    },
    {
        "result_id": "R-61",
        "tier": "1",
        "clock_start": "2026-06-26T11:00",
        "notification_minutes": "30",
        "acknowledgement_minutes": "60",
        "acknowledged_by_role": "advanced_nurse_practitioner",
        "escalation_status": "not_required",
        "findings": "compliant",
    },
    {
        "result_id": "R-62",
        "tier": "1",
        "clock_start": "2026-06-26T13:00",
        "notification_minutes": "20",
        "acknowledgement_minutes": "61",
        "acknowledged_by_role": "resident_doctor",
        "escalation_status": "missing",
        "findings": "acknowledgement_late;escalation_missing",
    },
    {
        "result_id": "R-63",
        "tier": "2",
        "clock_start": "2026-06-29T08:00",
        "notification_minutes": "30",
        "acknowledgement_minutes": "481",
        "acknowledged_by_role": "consultant",
        "escalation_status": "missing",
        "findings": "acknowledgement_late;escalation_missing",
    },
    {
        "result_id": "R-64",
        "tier": "2",
        "clock_start": "2026-06-26T08:00",
        "notification_minutes": "240",
        "acknowledgement_minutes": "480",
        "acknowledged_by_role": "consultant",
        "escalation_status": "not_required",
        "findings": "compliant",
    },
    {
        "result_id": "R-65",
        "tier": "1",
        "clock_start": "2026-06-26T15:00",
        "notification_minutes": "10",
        "acknowledgement_minutes": "",
        "acknowledged_by_role": "physician_associate",
        "escalation_status": "missing",
        "findings": "acknowledgement_late;acknowledger_unapproved;escalation_missing",
    },
    {
        "result_id": "R-66",
        "tier": "1",
        "clock_start": "2026-06-26T23:50",
        "notification_minutes": "31",
        "acknowledgement_minutes": "59",
        "acknowledged_by_role": "consultant",
        "escalation_status": "not_required",
        "findings": "notification_late",
    },
]


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def main() -> None:
    # --- fairness tip in instruction (pre-clock notify) ---
    instr_path = PACK / "instruction.md"
    instr = instr_path.read_text(encoding="utf-8")
    tip = (
        "If a telephone call is made before the tier-2 clock has started, treat the "
        "notification as within window (notification_minutes 0 from clock start)."
    )
    if "before the tier-2 clock has started" not in instr:
        if "even on a weekend." in instr:
            instr = instr.replace(
                "even on a weekend.",
                "even on a weekend. " + tip,
                1,
            )
        else:
            instr = instr.rstrip() + "\n" + tip + "\n"
    instr_path.write_text(instr, encoding="utf-8", newline="\n")

    # --- critical_results ---
    cr_path = PACK / "environment" / "input" / "critical_results.csv"
    cr = [
        r
        for r in csv.DictReader(cr_path.open(encoding="utf-8-sig"))
        if r["result_id"] not in {x["result_id"] for x in NEW_CR}
    ]
    cr.extend(NEW_CR)
    write_csv(cr_path, cr, CR_FIELDS)

    # escalations unchanged (no new escalations for late-ack traps)
    esc_path = PACK / "environment" / "input" / "escalations.csv"
    esc = list(csv.DictReader(esc_path.open(encoding="utf-8-sig")))
    write_csv(esc_path, esc, ["result_id", "escalated_at"])

    # --- audit gold ---
    audit_path = PACK / "solution" / "files" / "results_audit.csv"
    audit = [
        r
        for r in csv.DictReader(audit_path.open(encoding="utf-8-sig"))
        if r["result_id"] not in {x["result_id"] for x in NEW_AUDIT}
    ]
    # Harbor fairness: empty acknowledgement_minutes for unapproved
    for r in audit:
        if "acknowledger_unapproved" in (r.get("findings") or ""):
            r["acknowledgement_minutes"] = ""
    audit.extend(NEW_AUDIT)
    write_csv(audit_path, audit, AUDIT_FIELDS)

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

    # --- memo ---
    memo_path = PACK / "solution" / "files" / "results_memo.md"
    n = len(audit)
    memo = f"""# CR-7 critical results audit - {n} results

{co} results are clean.

## Late notifications

- **R-02** (tier 1) - notified 45 min after clock start 2026-06-15T22:10 (window 30 min).
- **R-09** (tier 2) - notified 300 min after clock start 2026-06-15T08:30 (window 240 min).
- **R-13** (tier 1) - notified 50 min after clock start 2026-06-15T21:00 (window 30 min).
- **R-16** (tier 2) - notified 931 min after clock start 2026-06-15T17:59 (window 240 min).
- **R-21** (tier 1) - notified 36 min after clock start 2026-06-17T23:59 (window 30 min).
- **R-26** (tier 1) - notified 31 min after clock start 2026-06-17T16:00 (window 30 min).
- **R-31** (tier 1) - notified 35 min after clock start 2026-06-20T23:00 (window 30 min).
- **R-40** (tier 1) - notified 31 min after clock start 2026-06-23T10:00 (window 30 min). Acknowledgement was at exactly 60 min so no acknowledgement breach and no escalation required.
- **R-47** (tier 2) - notified 241 min after clock start 2026-06-24T09:00 (window 240 min).
- **R-53** (tier 1) - notified 35 min after clock start 2026-06-25T03:00 (window 30 min).
- **R-60** (tier 2) - notified 241 min after clock start 2026-06-26T10:00 (window 240 min). Acknowledgement at 479 min was within the 480 min window, so escalation is not required.
- **R-66** (tier 1) - notified 31 min after clock start 2026-06-26T23:50 (window 30 min). Acknowledgement at 59 min was within window, so escalation is not required.

## Late or absent acknowledgements

- **R-03** - acknowledged at 80 min after clock start 2026-06-15T14:00 (window 60 min).
- **R-04** - acknowledged at 90 min after clock start 2026-06-16T03:00 (window 60 min).
- **R-06** - no recognised acknowledgement (unapproved ward_clerk); acknowledgement_minutes left empty; window 60 min from 2026-06-15T16:00 was missed.
- **R-10** - no acknowledgement recorded after clock start 2026-06-15T10:00 (window 480 min).
- **R-13** - acknowledged at 90 min after clock start 2026-06-15T21:00 (window 60 min).
- **R-15** - acknowledged at 510 min after clock start 2026-06-15T16:00 (window 480 min).
- **R-16** - acknowledged at 1081 min after clock start 2026-06-15T17:59 (window 480 min).
- **R-21** - acknowledged at 71 min after clock start 2026-06-17T23:59 (window 60 min).
- **R-22** - no recognised acknowledgement (unapproved nurse_hca); acknowledgement_minutes left empty; window 60 min from 2026-06-17T14:00 was missed.
- **R-24** - acknowledged at 481 min after clock start 2026-06-17T11:00 (window 480 min).
- **R-27** - acknowledged at 481 min after clock start 2026-06-17T17:59 (window 480 min).
- **R-30** - acknowledged at 481 min after clock start 2026-06-21T10:00 (window 480 min).
- **R-32** - acknowledged at 3841 min after clock start 2026-06-19T17:59 (window 480 min).
- **R-33** - acknowledged at 490 min after clock start 2026-06-20T08:00 (window 480 min).
- **R-35** - no recognised acknowledgement (unapproved phlebotomist); acknowledgement_minutes left empty; window 60 min from 2026-06-22T09:00 was missed.
- **R-45** - acknowledged at 61 min after clock start 2026-06-24T14:00 (window 60 min).
- **R-49** - acknowledged at 3841 min after clock start 2026-06-20T17:59 (window 480 min).
- **R-52** - no recognised acknowledgement (unapproved healthcare_assistant); acknowledgement_minutes left empty; window 60 min from 2026-06-25T15:00 was missed.
- **R-53** - no recognised acknowledgement (unapproved pharmacist); acknowledgement_minutes left empty; window 60 min from 2026-06-25T03:00 was missed.
- **R-54** - acknowledged at 481 min after clock start 2026-06-21T17:59 (window 480 min).
- **R-55** - acknowledged at 481 min after clock start 2026-06-22T08:00 (window 480 min).
- **R-62** - acknowledged at 61 min after clock start 2026-06-26T13:00 (window 60 min).
- **R-63** - acknowledged at 481 min after clock start 2026-06-29T08:00 (window 480 min).
- **R-65** - no recognised acknowledgement (unapproved physician_associate); acknowledgement_minutes left empty; window 60 min from 2026-06-26T15:00 was missed.

## Unapproved acknowledger

- **R-06** - acknowledged by ward_clerk, not on the approved list.
- **R-22** - acknowledged by nurse_hca, not on the approved list.
- **R-35** - acknowledged by phlebotomist, not on the approved list.
- **R-52** - acknowledged by healthcare_assistant, not on the approved list.
- **R-53** - acknowledged by pharmacist, not on the approved list.
- **R-65** - acknowledged by physician_associate, not on the approved list.

## Missing escalation

- **R-04** - missed acknowledgement window, no escalation.
- **R-13** - missed acknowledgement window, no escalation.
- **R-16** - missed acknowledgement window, no escalation.
- **R-21** - missed acknowledgement window, no escalation.
- **R-30** - missed acknowledgement window, no escalation.
- **R-33** - missed acknowledgement window, no escalation.
- **R-35** - missed acknowledgement window, no escalation.
- **R-45** - missed acknowledgement window, no escalation.
- **R-53** - missed acknowledgement window, no escalation.
- **R-54** - missed acknowledgement window, no escalation.
- **R-55** - missed acknowledgement window, no escalation.
- **R-62** - missed acknowledgement window, no escalation.
- **R-63** - missed acknowledgement window, no escalation.
- **R-65** - missed acknowledgement window, no escalation.

## What is not a finding

- Weekend results: core hours 08:00-18:00 apply every day (not weekday-only).
- Inclusive boundaries: exactly at the window limit is within it.
- **R-39** - Sunday 07:00 tier-2 release: clock starts 08:00 the same morning; within windows.
- **R-41** / **R-58** - Friday/Saturday 17:59 tier-2 release: clock starts immediately; acknowledgement at exactly 480 min is within the inclusive window.
- **R-57** - Friday 19:00 tier-2 release: clock starts Saturday 08:00; telephone call before clock start counts as notification_minutes 0 (within window).
- **R-59** - Saturday 18:00 release: clock starts Sunday 08:00; notify/ack at exact inclusive limits.
- **R-61** - advanced_nurse_practitioner is an approved role; exact 30/60 minute figures are within inclusive windows.
- **R-64** - Thursday 07:59 tier-2 release: clock starts 08:00 that morning; 240/480 from that clock are within windows.
- **R-56** - escalation present but acknowledgement was on time - escalation not required, not a finding.
- Long wall-clock gaps after evening releases are often not breaches once the next-morning clock start is applied.
"""
    memo_path.write_text(memo, encoding="utf-8", newline="\n")

    # --- verifiers ---
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

    ids = [f"R-{i:02d}" for i in range(1, n + 1)]
    find("audit_covers_every_result")["assertion"]["expected"] = "(?s)" + "".join(
        rf"(?=.*\b{i}\b)" for i in ids
    )
    find("audit_covers_every_result")["metadata"][
        "how_justification"
    ] = f"Requires every register ID R-01 through R-{n:02d}."
    find("audit_covers_every_result")["metadata"][
        "why_justification"
    ] = f"All {n} results appear in the audit CSV."

    find("result_notification_breaches")["assertion"]["expected"] = nb
    find("result_acknowledgement_breaches")["assertion"]["expected"] = ab
    find("result_unapproved_acknowledgement_results")["assertion"]["expected"] = ua
    find("result_missing_escalation_results")["assertion"]["expected"] = me
    find("result_results_compliant")["assertion"]["expected"] = co

    # Trap-specific verifiers
    upsert(
        "pre_clock_notify_zero_minutes",
        "evening_tier_two_clock_starts_next_morning",
        r"(?mi)^\x22?R-57\x22?\s*,[^\n]*2026-06-27[T ]0?8:00[^\n]*,\s*\x22?\s*0(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*420(?:\.0+)?\s*\x22?\s*,[^\n]*\x22?(compliant|ok|pass|none|no[_ ]?finding)\x22?\s*$",
        "R-57 evening notify before Saturday 08:00 clock must use clock_start 08:00, notify 0, compliant.",
        "R-57 pre-clock notification trap.",
    )
    upsert(
        "saturday_1759_ack_480_compliant",
        "before_close_ack_exactly_480_compliant",
        r"(?mi)^\x22?R-58\x22?\s*,[^\n]*2026-06-27[T ]17:59[^\n]*,\s*\x22?\s*31(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*480(?:\.0+)?\s*\x22?\s*,[^\n]*\x22?(compliant|ok|pass|none|no[_ ]?finding)\x22?\s*$",
        "R-58 Saturday 17:59 release with ack at exactly 480 must stay compliant.",
        "R-58 weekend before-close inclusive ack.",
    )
    upsert(
        "saturday_1800_next_morning_inclusive",
        "friday_closing_inclusive_compliant",
        r"(?mi)^\x22?R-59\x22?\s*,[^\n]*2026-06-28[T ]0?8:00[^\n]*,\s*\x22?\s*240(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*480(?:\.0+)?\s*\x22?\s*,[^\n]*\x22?(compliant|ok|pass|none|no[_ ]?finding)\x22?\s*$",
        "R-59 Saturday 18:00 must start clock Sunday 08:00 with exact 240/480 compliant.",
        "R-59 18:00 vs 17:59 weekend twin.",
    )
    upsert(
        "tier2_notify_late_ack_ok_no_escalation",
        "notify_late_ack_ok_no_escalation",
        r"(?mi)^\x22?R-60\x22?\s*,[^\n]*,\s*\x22?\s*241(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*479(?:\.0+)?\s*\x22?\s*,[^\n]*,\s*\x22?not_required\x22?\s*,[^\n]*notification_late",
        "R-60: notification_late at 241, ack 479 within window, escalation not_required.",
        "R-60 tier-2 late notify without ack/escalation breach.",
    )
    upsert(
        "anp_exact_boundaries_compliant",
        "audit_role_r36_is_anp",
        r"(?mi)^\x22?R-61\x22?\s*,[^\n]*advanced_nurse_practitioner[^\n]*,\s*\x22?not_required\x22?\s*,\s*\x22?(compliant|ok|pass|none|no[_ ]?finding)\x22?\s*$",
        "R-61 ANP at exact 30/60 inclusive must be compliant (approved role).",
        "R-61 ANP approved inclusive boundaries.",
    )
    upsert(
        "ack_off_by_one_61_missing_escalation",
        "missing_escalation_flagged",
        r"(?mi)^\x22?R-62\x22?\s*,[^\n]*,\s*\x22?\s*20(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*61(?:\.0+)?\s*\x22?\s*,[^\n]*,\s*\x22?missing\x22?\s*,[^\n]*(?=.*acknowledgement_late)(?=.*escalation_missing)",
        "R-62 ack at 61 must be acknowledgement_late with escalation_missing.",
        "R-62 inclusive off-by-one acknowledgement.",
    )
    upsert(
        "sunday_1800_monday_clock_ack_late",
        "tier_two_after_hours_ack_breach",
        r"(?mi)^\x22?R-63\x22?\s*,[^\n]*2026-06-29[T ]0?8:00[^\n]*,\s*\x22?\s*30(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*481(?:\.0+)?\s*\x22?\s*,[^\n]*,\s*\x22?missing\x22?\s*,[^\n]*(?=.*acknowledgement_late)(?=.*escalation_missing)",
        "R-63 Sunday 18:00 must clock Monday 08:00 with ack 481 late and missing escalation.",
        "R-63 Sunday evening next-morning clock.",
    )
    upsert(
        "weekday_pre_core_exact_windows",
        "early_tier_two_clock_starts_at_core_open",
        r"(?mi)^\x22?R-64\x22?\s*,[^\n]*2026-06-26[T ]0?8:00[^\n]*,\s*\x22?\s*240(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*480(?:\.0+)?\s*\x22?\s*,[^\n]*\x22?(compliant|ok|pass|none|no[_ ]?finding)\x22?\s*$",
        "R-64 07:59 release must use 08:00 clock with exact 240/480 compliant.",
        "R-64 weekday pre-core inclusive windows.",
    )
    upsert(
        "physician_associate_unapproved_empty_mins",
        "unapproved_past_window_missing_escalation",
        r"(?mi)^\x22?R-65\x22?\s*,[^\n]*,\s*\x22?\s*10(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*\x22?\s*,[^\n]*physician_associate[^\n]*,\s*\x22?missing\x22?\s*,[^\n]*(?=.*acknowledger_unapproved)(?=.*acknowledgement_late)(?=.*escalation_missing)",
        "R-65 physician_associate unapproved with empty acknowledgement_minutes plus late+missing.",
        "R-65 new unapproved role trap.",
    )
    upsert(
        "cross_midnight_notify_late_ack_ok",
        "notify_late_ack_ok_no_escalation",
        r"(?mi)^\x22?R-66\x22?\s*,[^\n]*,\s*\x22?\s*31(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*59(?:\.0+)?\s*\x22?\s*,[^\n]*,\s*\x22?not_required\x22?\s*,[^\n]*notification_late",
        "R-66 cross-midnight: notify 31 late, ack 59 OK, escalation not_required.",
        "R-66 midnight notify-late ack-ok trap.",
    )
    upsert(
        "memo_lists_r60_late_notification",
        "memo_lists_r40_late_notification",
        r"(?is)\bR-60\b.{0,400}(?:notif|241|240|late|window)",
        "Memo must explain R-60 late notification.",
        "R-60 late notification covered in memo.",
    )
    upsert(
        "memo_lists_r65_unapproved",
        "memo_names_phlebotomist_unapproved",
        r"(?is)\bR-65\b.{0,500}(?:unapproved|physician[_\s-]?associate|not on the approved|not recognised|not recognized)",
        "Memo must explain R-65 unapproved physician_associate.",
        "R-65 unapproved role named in memo.",
    )
    upsert(
        "memo_explains_pre_clock_or_1759",
        "memo_explains_midnight_or_weekend_non_breach",
        r"(?is)(?:\bR-57\b.{0,400}(?:before|0\s*min|clock start|pre[- ]?clock)|\bR-58\b.{0,400}(?:17:59|480|inclusive)|\bR-64\b.{0,400}(?:08:00|pre[- ]?core|07:59))",
        "Memo must explain at least one hard non-breach (pre-clock notify, 17:59, or pre-core).",
        "Hard non-breach traps explained in memo.",
    )

    for v in data["verifiers"]:
        exp = v["assertion"].get("expected")
        if isinstance(exp, str) and exp.startswith("(?"):
            re.compile(exp)

    vj.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print("verifiers", len(data["verifiers"]))


if __name__ == "__main__":
    main()
