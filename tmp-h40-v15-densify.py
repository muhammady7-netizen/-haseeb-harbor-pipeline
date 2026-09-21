#!/usr/bin/env python3
"""h40 v15 densify — v14 content-e86ad926 still TOO_EASY (Oracle 1.0, GLM 4/4).

Harder fair INPUT traps R-67..R-80 + matching gold + disclosed fairness notes +
trap verifiers. Keeps Harbor fairness: unapproved => empty ack minutes +
acknowledgement_late when window missed; ward_clerk alias OK; quoted numerics OK;
no brittle memo \\blimit\\b / must-name-R-34.
"""
from __future__ import annotations

import csv
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
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

# New traps R-67..R-80 (14 rows)
NEW_CR = [
    # R-67: midnight inclusive twin (compliant) — exact 30/60
    {
        "result_id": "R-67",
        "tier": "1",
        "test": "potassium",
        "released_at": "2026-06-30T00:00",
        "notified_at": "2026-06-30T00:30",
        "acknowledged_at": "2026-06-30T01:00",
        "acknowledged_by_role": "consultant",
    },
    # R-68: midnight twin — ack at 61 (off-by-one) + missing escalation
    {
        "result_id": "R-68",
        "tier": "1",
        "test": "troponin",
        "released_at": "2026-06-30T01:00",
        "notified_at": "2026-06-30T01:30",
        "acknowledged_at": "2026-06-30T02:01",
        "acknowledged_by_role": "resident_doctor",
    },
    # R-69: Fri 18:00 → Sat 08:00; pre-clock notify (0); ack 481 late + missing
    {
        "result_id": "R-69",
        "tier": "2",
        "test": "sodium",
        "released_at": "2026-07-03T18:00",
        "notified_at": "2026-07-03T19:30",
        "acknowledged_at": "2026-07-04T16:01",
        "acknowledged_by_role": "consultant",
    },
    # R-70: Fri evening → Sat 08:00; pre-clock notify; exact 480 inclusive → compliant
    {
        "result_id": "R-70",
        "tier": "2",
        "test": "bilirubin",
        "released_at": "2026-07-03T19:00",
        "notified_at": "2026-07-03T20:00",
        "acknowledged_at": "2026-07-04T16:00",
        "acknowledged_by_role": "specialty_registrar",
    },
    # R-71: tier-2 with 31/61 (looks like tier-1 breach) → still compliant
    {
        "result_id": "R-71",
        "tier": "2",
        "test": "haemoglobin",
        "released_at": "2026-06-30T11:00",
        "notified_at": "2026-06-30T11:31",
        "acknowledged_at": "2026-06-30T12:01",
        "acknowledged_by_role": "consultant",
    },
    # R-72: tier-1 twin of R-71 → notify late + ack late + missing escalation
    {
        "result_id": "R-72",
        "tier": "1",
        "test": "lactate",
        "released_at": "2026-06-30T11:00",
        "notified_at": "2026-06-30T11:31",
        "acknowledged_at": "2026-06-30T12:01",
        "acknowledged_by_role": "consultant",
    },
    # R-73: nurse_practitioner looks like ANP but is unapproved
    {
        "result_id": "R-73",
        "tier": "1",
        "test": "magnesium",
        "released_at": "2026-06-30T14:00",
        "notified_at": "2026-06-30T14:10",
        "acknowledged_at": "2026-06-30T14:40",
        "acknowledged_by_role": "nurse_practitioner",
    },
    # R-74: clinical_fellow unapproved + notify late (multi-finding)
    {
        "result_id": "R-74",
        "tier": "1",
        "test": "glucose",
        "released_at": "2026-06-30T22:00",
        "notified_at": "2026-06-30T22:35",
        "acknowledged_at": "2026-06-30T22:55",
        "acknowledged_by_role": "clinical_fellow",
    },
    # R-75: Sat 07:59 → 08:00 clock; notify 241 late, ack 479 OK → not_required
    {
        "result_id": "R-75",
        "tier": "2",
        "test": "inr",
        "released_at": "2026-07-04T07:59",
        "notified_at": "2026-07-04T12:01",
        "acknowledged_at": "2026-07-04T15:59",
        "acknowledged_by_role": "consultant",
    },
    # R-76: Sun 07:59 decoy twin — exact 240/480 from 08:00 → compliant
    {
        "result_id": "R-76",
        "tier": "2",
        "test": "creatinine",
        "released_at": "2026-07-05T07:59",
        "notified_at": "2026-07-05T12:00",
        "acknowledged_at": "2026-07-05T16:00",
        "acknowledged_by_role": "consultant",
    },
    # R-77: tier-2 both late (241/481) + missing escalation
    {
        "result_id": "R-77",
        "tier": "2",
        "test": "phosphate",
        "released_at": "2026-07-01T09:00",
        "notified_at": "2026-07-01T13:01",
        "acknowledged_at": "2026-07-01T17:01",
        "acknowledged_by_role": "specialty_registrar",
    },
    # R-78: cross-midnight notify late / ack exact 60 → notification_late only
    {
        "result_id": "R-78",
        "tier": "1",
        "test": "calcium",
        "released_at": "2026-06-29T23:30",
        "notified_at": "2026-06-30T00:01",
        "acknowledged_at": "2026-06-30T00:30",
        "acknowledged_by_role": "consultant",
    },
    # R-79: cross-midnight both late (31/61) + missing
    {
        "result_id": "R-79",
        "tier": "1",
        "test": "troponin",
        "released_at": "2026-07-01T23:50",
        "notified_at": "2026-07-02T00:21",
        "acknowledged_at": "2026-07-02T00:51",
        "acknowledged_by_role": "resident_doctor",
    },
    # R-80: locum_consultant looks approved but is not
    {
        "result_id": "R-80",
        "tier": "1",
        "test": "potassium",
        "released_at": "2026-07-02T09:00",
        "notified_at": "2026-07-02T09:05",
        "acknowledged_at": "2026-07-02T09:50",
        "acknowledged_by_role": "locum_consultant",
    },
]

NEW_AUDIT = [
    {
        "result_id": "R-67",
        "tier": "1",
        "clock_start": "2026-06-30T00:00",
        "notification_minutes": "30",
        "acknowledgement_minutes": "60",
        "acknowledged_by_role": "consultant",
        "escalation_status": "not_required",
        "findings": "compliant",
    },
    {
        "result_id": "R-68",
        "tier": "1",
        "clock_start": "2026-06-30T01:00",
        "notification_minutes": "30",
        "acknowledgement_minutes": "61",
        "acknowledged_by_role": "resident_doctor",
        "escalation_status": "missing",
        "findings": "acknowledgement_late;escalation_missing",
    },
    {
        "result_id": "R-69",
        "tier": "2",
        "clock_start": "2026-07-04T08:00",
        "notification_minutes": "0",
        "acknowledgement_minutes": "481",
        "acknowledged_by_role": "consultant",
        "escalation_status": "missing",
        "findings": "acknowledgement_late;escalation_missing",
    },
    {
        "result_id": "R-70",
        "tier": "2",
        "clock_start": "2026-07-04T08:00",
        "notification_minutes": "0",
        "acknowledgement_minutes": "480",
        "acknowledged_by_role": "specialty_registrar",
        "escalation_status": "not_required",
        "findings": "compliant",
    },
    {
        "result_id": "R-71",
        "tier": "2",
        "clock_start": "2026-06-30T11:00",
        "notification_minutes": "31",
        "acknowledgement_minutes": "61",
        "acknowledged_by_role": "consultant",
        "escalation_status": "not_required",
        "findings": "compliant",
    },
    {
        "result_id": "R-72",
        "tier": "1",
        "clock_start": "2026-06-30T11:00",
        "notification_minutes": "31",
        "acknowledgement_minutes": "61",
        "acknowledged_by_role": "consultant",
        "escalation_status": "missing",
        "findings": "notification_late;acknowledgement_late;escalation_missing",
    },
    {
        "result_id": "R-73",
        "tier": "1",
        "clock_start": "2026-06-30T14:00",
        "notification_minutes": "10",
        "acknowledgement_minutes": "",
        "acknowledged_by_role": "nurse_practitioner",
        "escalation_status": "missing",
        "findings": "acknowledgement_late;acknowledger_unapproved;escalation_missing",
    },
    {
        "result_id": "R-74",
        "tier": "1",
        "clock_start": "2026-06-30T22:00",
        "notification_minutes": "35",
        "acknowledgement_minutes": "",
        "acknowledged_by_role": "clinical_fellow",
        "escalation_status": "missing",
        "findings": "notification_late;acknowledgement_late;acknowledger_unapproved;escalation_missing",
    },
    {
        "result_id": "R-75",
        "tier": "2",
        "clock_start": "2026-07-04T08:00",
        "notification_minutes": "241",
        "acknowledgement_minutes": "479",
        "acknowledged_by_role": "consultant",
        "escalation_status": "not_required",
        "findings": "notification_late",
    },
    {
        "result_id": "R-76",
        "tier": "2",
        "clock_start": "2026-07-05T08:00",
        "notification_minutes": "240",
        "acknowledgement_minutes": "480",
        "acknowledged_by_role": "consultant",
        "escalation_status": "not_required",
        "findings": "compliant",
    },
    {
        "result_id": "R-77",
        "tier": "2",
        "clock_start": "2026-07-01T09:00",
        "notification_minutes": "241",
        "acknowledgement_minutes": "481",
        "acknowledged_by_role": "specialty_registrar",
        "escalation_status": "missing",
        "findings": "notification_late;acknowledgement_late;escalation_missing",
    },
    {
        "result_id": "R-78",
        "tier": "1",
        "clock_start": "2026-06-29T23:30",
        "notification_minutes": "31",
        "acknowledgement_minutes": "60",
        "acknowledged_by_role": "consultant",
        "escalation_status": "not_required",
        "findings": "notification_late",
    },
    {
        "result_id": "R-79",
        "tier": "1",
        "clock_start": "2026-07-01T23:50",
        "notification_minutes": "31",
        "acknowledgement_minutes": "61",
        "acknowledged_by_role": "resident_doctor",
        "escalation_status": "missing",
        "findings": "notification_late;acknowledgement_late;escalation_missing",
    },
    {
        "result_id": "R-80",
        "tier": "1",
        "clock_start": "2026-07-02T09:00",
        "notification_minutes": "5",
        "acknowledgement_minutes": "",
        "acknowledged_by_role": "locum_consultant",
        "escalation_status": "missing",
        "findings": "acknowledgement_late;acknowledger_unapproved;escalation_missing",
    },
]


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def main() -> None:
    # --- fairness tips in instruction ---
    instr_path = PACK / "instruction.md"
    instr = instr_path.read_text(encoding="utf-8")
    tip = (
        "Only the four roles listed in the procedure are approved; titles that sound "
        "clinical but are not on that list (for example nurse_practitioner or "
        "locum_consultant) are unapproved. Apply each tier's own notification and "
        "acknowledgement windows — do not borrow tier-1 limits for tier-2 results or "
        "the reverse."
    )
    if "nurse_practitioner or locum_consultant" not in instr:
        if "notification_minutes 0 from clock start)." in instr:
            instr = instr.replace(
                "notification_minutes 0 from clock start).",
                "notification_minutes 0 from clock start). " + tip,
                1,
            )
        elif "even on a weekend." in instr:
            instr = instr.replace("even on a weekend.", "even on a weekend. " + tip, 1)
        else:
            instr = instr.rstrip() + "\n" + tip + "\n"
    instr_path.write_text(instr, encoding="utf-8", newline="\n")

    # --- critical_results ---
    cr_path = PACK / "environment" / "input" / "critical_results.csv"
    new_ids = {x["result_id"] for x in NEW_CR}
    cr = [
        r
        for r in csv.DictReader(cr_path.open(encoding="utf-8-sig"))
        if r["result_id"] not in new_ids
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
- **R-72** (tier 1) - notified 31 min after clock start 2026-06-30T11:00 (window 30 min). Acknowledgement also late at 61 min.
- **R-74** (tier 1) - notified 35 min after clock start 2026-06-30T22:00 (window 30 min). Acknowledgement by clinical_fellow is not recognised.
- **R-75** (tier 2) - notified 241 min after clock start 2026-07-04T08:00 (window 240 min). Acknowledgement at 479 min was within window, so escalation is not required.
- **R-77** (tier 2) - notified 241 min after clock start 2026-07-01T09:00 (window 240 min). Acknowledgement also late at 481 min.
- **R-78** (tier 1) - notified 31 min after clock start 2026-06-29T23:30 (window 30 min). Acknowledgement at exactly 60 min was within window, so escalation is not required.
- **R-79** (tier 1) - notified 31 min after clock start 2026-07-01T23:50 (window 30 min). Acknowledgement also late at 61 min.

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
- **R-68** - acknowledged at 61 min after clock start 2026-06-30T01:00 (window 60 min).
- **R-69** - acknowledged at 481 min after clock start 2026-07-04T08:00 (window 480 min). Pre-clock telephone call counts as notification_minutes 0.
- **R-72** - acknowledged at 61 min after clock start 2026-06-30T11:00 (window 60 min).
- **R-73** - no recognised acknowledgement (unapproved nurse_practitioner); acknowledgement_minutes left empty; window 60 min from 2026-06-30T14:00 was missed.
- **R-74** - no recognised acknowledgement (unapproved clinical_fellow); acknowledgement_minutes left empty; window 60 min from 2026-06-30T22:00 was missed.
- **R-77** - acknowledged at 481 min after clock start 2026-07-01T09:00 (window 480 min).
- **R-79** - acknowledged at 61 min after clock start 2026-07-01T23:50 (window 60 min).
- **R-80** - no recognised acknowledgement (unapproved locum_consultant); acknowledgement_minutes left empty; window 60 min from 2026-07-02T09:00 was missed.

## Unapproved acknowledger

- **R-06** - acknowledged by ward_clerk, not on the approved list.
- **R-22** - acknowledged by nurse_hca, not on the approved list.
- **R-35** - acknowledged by phlebotomist, not on the approved list.
- **R-52** - acknowledged by healthcare_assistant, not on the approved list.
- **R-53** - acknowledged by pharmacist, not on the approved list.
- **R-65** - acknowledged by physician_associate, not on the approved list.
- **R-73** - acknowledged by nurse_practitioner, not on the approved list (unlike advanced_nurse_practitioner).
- **R-74** - acknowledged by clinical_fellow, not on the approved list.
- **R-80** - acknowledged by locum_consultant, not on the approved list.

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
- **R-68** - missed acknowledgement window, no escalation.
- **R-69** - missed acknowledgement window, no escalation.
- **R-72** - missed acknowledgement window, no escalation.
- **R-73** - missed acknowledgement window, no escalation.
- **R-74** - missed acknowledgement window, no escalation.
- **R-77** - missed acknowledgement window, no escalation.
- **R-79** - missed acknowledgement window, no escalation.
- **R-80** - missed acknowledgement window, no escalation.

## What is not a finding

- Weekend results: core hours 08:00-18:00 apply every day (not weekday-only).
- Inclusive boundaries: exactly at the window limit is within it.
- **R-39** - Sunday 07:00 tier-2 release: clock starts 08:00 the same morning; within windows.
- **R-41** / **R-58** - Friday/Saturday 17:59 tier-2 release: clock starts immediately; acknowledgement at exactly 480 min is within the inclusive window.
- **R-57** - Friday 19:00 tier-2 release: clock starts Saturday 08:00; telephone call before clock start counts as notification_minutes 0 (within window).
- **R-59** - Saturday 18:00 release: clock starts Sunday 08:00; notify/ack at exact inclusive limits.
- **R-61** - advanced_nurse_practitioner is an approved role; exact 30/60 minute figures are within inclusive windows.
- **R-64** - Thursday 07:59 tier-2 release: clock starts 08:00 that morning; 240/480 from that clock are within windows.
- **R-67** - midnight release with exact inclusive 30/60 is compliant.
- **R-70** - Friday evening release with pre-clock notify and acknowledgement at exactly 480 from Saturday 08:00 is compliant.
- **R-71** - tier-2 result with 31/61 minutes is still within the 240/480 windows (do not apply tier-1 limits).
- **R-76** - Sunday 07:59 tier-2 release: clock starts 08:00; exact 240/480 are within inclusive windows.
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

    # Trap-specific verifiers (quoted-numeric tolerant)
    upsert(
        "midnight_exact_3060_compliant",
        "midnight_inclusive_windows_compliant",
        r"(?mi)^\x22?R-67\x22?\s*,[^\n]*,\s*\x22?\s*30(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*60(?:\.0+)?\s*\x22?\s*,[^\n]*\x22?(compliant|ok|pass|none|no[_ ]?finding)\x22?\s*$",
        "R-67 midnight exact 30/60 inclusive must stay compliant.",
        "R-67 midnight inclusive twin.",
    )
    upsert(
        "midnight_ack_61_missing_escalation",
        "ack_off_by_one_61_missing_escalation",
        r"(?mi)^\x22?R-68\x22?\s*,[^\n]*,\s*\x22?\s*30(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*61(?:\.0+)?\s*\x22?\s*,[^\n]*,\s*\x22?missing\x22?\s*,[^\n]*(?=.*acknowledgement_late)(?=.*escalation_missing)",
        "R-68 ack at 61 must be acknowledgement_late with escalation_missing.",
        "R-68 midnight off-by-one twin.",
    )
    upsert(
        "friday_1800_preclock_ack_481",
        "sunday_1800_monday_clock_ack_late",
        r"(?mi)^\x22?R-69\x22?\s*,[^\n]*2026-07-04[T ]0?8:00[^\n]*,\s*\x22?\s*0(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*481(?:\.0+)?\s*\x22?\s*,[^\n]*,\s*\x22?missing\x22?\s*,[^\n]*(?=.*acknowledgement_late)(?=.*escalation_missing)",
        "R-69 Friday 18:00 must clock Saturday 08:00 with notify 0 and ack 481 late+missing.",
        "R-69 pre-clock notify with late ack.",
    )
    upsert(
        "friday_evening_preclock_ack_480_compliant",
        "pre_clock_notify_zero_minutes",
        r"(?mi)^\x22?R-70\x22?\s*,[^\n]*2026-07-04[T ]0?8:00[^\n]*,\s*\x22?\s*0(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*480(?:\.0+)?\s*\x22?\s*,[^\n]*\x22?(compliant|ok|pass|none|no[_ ]?finding)\x22?\s*$",
        "R-70 evening release with pre-clock notify and exact 480 must stay compliant.",
        "R-70 pre-clock inclusive decoy twin.",
    )
    upsert(
        "tier2_looks_like_tier1_still_compliant",
        "anp_exact_boundaries_compliant",
        r"(?mi)^\x22?R-71\x22?\s*,\s*\x22?2\x22?\s*,[^\n]*,\s*\x22?\s*31(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*61(?:\.0+)?\s*\x22?\s*,[^\n]*\x22?(compliant|ok|pass|none|no[_ ]?finding)\x22?\s*$",
        "R-71 tier-2 with 31/61 must remain compliant (tier-2 windows are 240/480).",
        "R-71 tier-limit confusion decoy.",
    )
    upsert(
        "tier1_twin_both_late_missing",
        "night_tier_one_breaches_both_windows",
        r"(?mi)^\x22?R-72\x22?\s*,\s*\x22?1\x22?\s*,[^\n]*,\s*\x22?\s*31(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*61(?:\.0+)?\s*\x22?\s*,[^\n]*,\s*\x22?missing\x22?\s*,[^\n]*(?=.*notification_late)(?=.*acknowledgement_late)(?=.*escalation_missing)",
        "R-72 tier-1 twin must flag notification_late, acknowledgement_late, and escalation_missing.",
        "R-72 tier-1 twin of R-71.",
    )
    upsert(
        "nurse_practitioner_unapproved_empty_mins",
        "physician_associate_unapproved_empty_mins",
        r"(?mi)^\x22?R-73\x22?\s*,[^\n]*,\s*\x22?\s*10(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*\x22?\s*,[^\n]*nurse_practitioner[^\n]*,\s*\x22?missing\x22?\s*,[^\n]*(?=.*acknowledger_unapproved)(?=.*acknowledgement_late)(?=.*escalation_missing)",
        "R-73 nurse_practitioner unapproved with empty acknowledgement_minutes plus late+missing.",
        "R-73 near-miss role trap (not ANP).",
    )
    upsert(
        "clinical_fellow_multifinding",
        "unapproved_past_window_missing_escalation",
        r"(?mi)^\x22?R-74\x22?\s*,[^\n]*,\s*\x22?\s*35(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*\x22?\s*,[^\n]*clinical_fellow[^\n]*,\s*\x22?missing\x22?\s*,[^\n]*(?=.*notification_late)(?=.*acknowledger_unapproved)(?=.*acknowledgement_late)(?=.*escalation_missing)",
        "R-74 must carry notify late + unapproved + ack late + missing escalation with empty minutes.",
        "R-74 multi-finding unapproved trap.",
    )
    upsert(
        "saturday_precore_notify_late_ack_ok",
        "tier2_notify_late_ack_ok_no_escalation",
        r"(?mi)^\x22?R-75\x22?\s*,[^\n]*2026-07-04[T ]0?8:00[^\n]*,\s*\x22?\s*241(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*479(?:\.0+)?\s*\x22?\s*,[^\n]*,\s*\x22?not_required\x22?\s*,[^\n]*notification_late",
        "R-75 Saturday pre-core: notify 241 late, ack 479 OK, escalation not_required.",
        "R-75 weekend pre-core notify-late ack-ok.",
    )
    upsert(
        "sunday_precore_exact_windows_compliant",
        "sunday_pre_core_clock_at_0800",
        r"(?mi)^\x22?R-76\x22?\s*,[^\n]*2026-07-05[T ]0?8:00[^\n]*,\s*\x22?\s*240(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*480(?:\.0+)?\s*\x22?\s*,[^\n]*\x22?(compliant|ok|pass|none|no[_ ]?finding)\x22?\s*$",
        "R-76 Sunday 07:59 must use 08:00 clock with exact 240/480 compliant.",
        "R-76 Sunday pre-core inclusive decoy.",
    )
    upsert(
        "tier2_both_late_241_481_missing",
        "tier2_notify_late_ack_ok_no_escalation",
        r"(?mi)^\x22?R-77\x22?\s*,[^\n]*,\s*\x22?\s*241(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*481(?:\.0+)?\s*\x22?\s*,[^\n]*,\s*\x22?missing\x22?\s*,[^\n]*(?=.*notification_late)(?=.*acknowledgement_late)(?=.*escalation_missing)",
        "R-77 tier-2 both late at 241/481 must include escalation_missing.",
        "R-77 both-late vs notify-only twin pattern.",
    )
    upsert(
        "cross_midnight_notify_late_ack_exact60",
        "cross_midnight_notify_late_ack_ok",
        r"(?mi)^\x22?R-78\x22?\s*,[^\n]*,\s*\x22?\s*31(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*60(?:\.0+)?\s*\x22?\s*,[^\n]*,\s*\x22?not_required\x22?\s*,[^\n]*notification_late",
        "R-78 cross-midnight: notify 31 late, ack exactly 60 OK, escalation not_required.",
        "R-78 midnight notify-late ack-exact trap.",
    )
    upsert(
        "cross_midnight_both_late_31_61",
        "night_tier_one_breaches_both_windows",
        r"(?mi)^\x22?R-79\x22?\s*,[^\n]*,\s*\x22?\s*31(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*61(?:\.0+)?\s*\x22?\s*,[^\n]*,\s*\x22?missing\x22?\s*,[^\n]*(?=.*notification_late)(?=.*acknowledgement_late)(?=.*escalation_missing)",
        "R-79 cross-midnight both late 31/61 with escalation_missing.",
        "R-79 midnight both-late twin of R-78.",
    )
    upsert(
        "locum_consultant_unapproved_empty_mins",
        "physician_associate_unapproved_empty_mins",
        r"(?mi)^\x22?R-80\x22?\s*,[^\n]*,\s*\x22?\s*5(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*\x22?\s*,[^\n]*locum_consultant[^\n]*,\s*\x22?missing\x22?\s*,[^\n]*(?=.*acknowledger_unapproved)(?=.*acknowledgement_late)(?=.*escalation_missing)",
        "R-80 locum_consultant unapproved with empty acknowledgement_minutes plus late+missing.",
        "R-80 near-miss approved-looking role.",
    )
    upsert(
        "memo_lists_r72_or_r77_late",
        "memo_lists_r60_late_notification",
        r"(?is)(?:\bR-72\b.{0,400}(?:notif|31|late|window)|\bR-77\b.{0,400}(?:notif|241|late|window))",
        "Memo must explain at least one new late-notification trap (R-72 or R-77).",
        "New late-notification traps covered in memo.",
    )
    upsert(
        "memo_lists_r73_or_r80_unapproved",
        "memo_lists_r65_unapproved",
        r"(?is)(?:\bR-73\b.{0,500}(?:unapproved|nurse[_\s-]?practitioner|not on the approved)|\bR-80\b.{0,500}(?:unapproved|locum[_\s-]?consultant|not on the approved))",
        "Memo must explain a near-miss unapproved role (R-73 or R-80).",
        "Near-miss unapproved roles named in memo.",
    )
    upsert(
        "memo_explains_tier_or_preclock_non_breach",
        "memo_explains_pre_clock_or_1759",
        r"(?is)(?:\bR-71\b.{0,400}(?:tier[- ]?2|240|480|not a (?:breach|finding)|within)|\bR-70\b.{0,400}(?:pre[- ]?clock|480|08:00|compliant)|\bR-76\b.{0,400}(?:08:00|240|480|pre[- ]?core))",
        "Memo must explain a hard non-breach (tier-limit decoy, pre-clock 480, or Sunday pre-core).",
        "Hard non-breach traps explained in memo.",
    )

    for v in data["verifiers"]:
        exp = v["assertion"].get("expected")
        if isinstance(exp, str) and exp.startswith("(?"):
            re.compile(exp)

    vj.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print("verifiers", len(data["verifiers"]))

    # --- tighter coverage_depth pytest for new traps ---
    test_path = PACK / "tests" / "test_outputs.py"
    test_src = test_path.read_text(encoding="utf-8")
    marker = "def test_results_recomputed_from_audit():"
    extra = '''
def test_v15_hard_trap_findings():
    """Per-row findings for v15 densify traps (coverage_depth)."""
    findings = _audit_findings(WORKSPACE)
    expected = {
        "R-67": "compliant",
        "R-68": "acknowledgement_late;escalation_missing",
        "R-69": "acknowledgement_late;escalation_missing",
        "R-70": "compliant",
        "R-71": "compliant",
        "R-72": "notification_late;acknowledgement_late;escalation_missing",
        "R-73": "acknowledgement_late;acknowledger_unapproved;escalation_missing",
        "R-74": "notification_late;acknowledgement_late;acknowledger_unapproved;escalation_missing",
        "R-75": "notification_late",
        "R-76": "compliant",
        "R-77": "notification_late;acknowledgement_late;escalation_missing",
        "R-78": "notification_late",
        "R-79": "notification_late;acknowledgement_late;escalation_missing",
        "R-80": "acknowledgement_late;acknowledger_unapproved;escalation_missing",
    }
    for rid, want in expected.items():
        assert rid in findings, f"missing audit row {rid}"
        got = ";".join(p.strip() for p in findings[rid].split(";") if p.strip())
        want_n = ";".join(p.strip() for p in want.split(";") if p.strip())
        assert set(got.split(";")) == set(want_n.split(";")), (
            f"{rid} findings {got!r} != {want_n!r}"
        )


def test_v15_unapproved_empty_acknowledgement_minutes():
    """Harbor fairness: unapproved roles leave acknowledgement_minutes empty."""
    import csv
    path = WORKSPACE / "results_audit.csv"
    assert path.is_file()
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = { (r.get("result_id") or "").strip(): r for r in csv.DictReader(f) }
    for rid in ("R-73", "R-74", "R-80"):
        row = rows[rid]
        assert "acknowledger_unapproved" in (row.get("findings") or "")
        assert (row.get("acknowledgement_minutes") or "").strip() == "", (
            f"{rid} must have empty acknowledgement_minutes"
        )


'''
    if "test_v15_hard_trap_findings" not in test_src:
        # append after existing helpers / at end of file
        if not test_src.endswith("\n"):
            test_src += "\n"
        test_src += extra
        test_path.write_text(test_src, encoding="utf-8", newline="\n")
        print("added pytest trap coverage")
    else:
        print("pytest trap coverage already present")


def run_pytest() -> None:
    tests = PACK / "tests"
    ws = Path(tempfile.mkdtemp(prefix="h40-v15-gold-"))
    # deliverables at workspace root
    for name in ("results_audit.csv", "results_memo.md", "results.json"):
        shutil.copy2(PACK / "solution" / "files" / name, ws / name)
    # register for coverage tests
    inp = ws / "input"
    inp.mkdir()
    for name in ("critical_results.csv", "escalations.csv", "critical_results_procedure.md"):
        src = PACK / "environment" / "input" / name
        if src.exists():
            shutil.copy2(src, inp / name)
    env = os.environ.copy()
    env["HARBOR_TASK_WORKSPACE"] = str(ws)
    print("workspace", ws)
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", str(tests / "test_outputs.py"), "-q", "--tb=line"],
        cwd=str(tests),
        env=env,
        capture_output=True,
        text=True,
    )
    print(proc.stdout)
    if proc.stderr:
        print(proc.stderr[-2000:])
    print("pytest_returncode", proc.returncode)
    # parse pass count
    m = re.search(r"(\d+) passed", proc.stdout)
    if m:
        print("PASSED", m.group(1))
    m2 = re.search(r"(\d+) failed", proc.stdout)
    if m2:
        print("FAILED", m2.group(1))


if __name__ == "__main__":
    main()
    run_pytest()
