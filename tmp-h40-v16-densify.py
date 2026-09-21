#!/usr/bin/env python3
"""h40 v16 densify — v15 (#a413ccbb) still TOO_EASY (Oracle 1.0, GLM 4/4).

Qualitatively harder fair densify (beyond more weekend/midnight twins):
- Confusable near-miss roles requiring exact approved-token match
- Unapproved/late rows WITH escalation recorded (status=recorded, NOT missing)
- Multi-finding rows where omitting any one finding fails
- Tier-limit swap traps buried among decoys (not obvious same-timestamp twins)
- Clock-start chains that need Fri/Sat/Sun/evening policy paragraphs
- ~105 register rows, tighter counts + per-id verifiers + coverage_depth pytest

Harbor fairness KEEP:
- unapproved => empty acknowledgement_minutes
- unapproved + missed window => BOTH acknowledger_unapproved AND acknowledgement_late
- ward_clerk alias OK; quoted numerics OK
- no brittle \\blimit\\b; no must-name-R-34 memo checks
- all traps instruction-disclosed
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
from datetime import datetime, timedelta
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

APPROVED = {
    "consultant",
    "specialty_registrar",
    "resident_doctor",
    "advanced_nurse_practitioner",
}

# ---------------------------------------------------------------------------
# Gold computer (procedure CR-7)
# ---------------------------------------------------------------------------


def _parse(ts: str) -> datetime:
    return datetime.strptime(ts.strip(), "%Y-%m-%dT%H:%M")


def _fmt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M")


def clock_start(tier: int, released_at: str) -> datetime:
    r = _parse(released_at)
    if tier == 1:
        return r
    # Tier 2: core hours 08:00–18:00; clock may only *start* in that window.
    if r.hour < 8:
        return r.replace(hour=8, minute=0)
    if r.hour >= 18:  # at or after 18:00 → next morning 08:00
        nxt = r + timedelta(days=1)
        return nxt.replace(hour=8, minute=0)
    return r


def mins_from(clock: datetime, event: str | None) -> int | None:
    if not event or not str(event).strip():
        return None
    e = _parse(event)
    if e < clock:
        return 0  # pre-clock telephone = within window at 0
    return int((e - clock).total_seconds() // 60)


def grade_row(cr: dict, escalated_ids: set[str]) -> dict:
    rid = cr["result_id"]
    tier = int(cr["tier"])
    n_lim, a_lim = (30, 60) if tier == 1 else (240, 480)
    cs = clock_start(tier, cr["released_at"])
    n_mins = mins_from(cs, cr.get("notified_at") or "")
    role = (cr.get("acknowledged_by_role") or "").strip()
    ack_at = (cr.get("acknowledged_at") or "").strip()

    findings: list[str] = []
    if n_mins is not None and n_mins > n_lim:
        findings.append("notification_late")

    approved = role in APPROVED
    if role and role not in APPROVED and role != "none":
        findings.append("acknowledger_unapproved")
        a_mins_str = ""
        ack_role_out = role
        window_missed = True  # no recognised acknowledgement
    elif not ack_at or role in ("", "none"):
        a_mins_str = ""
        ack_role_out = role if role else "none"
        window_missed = True
        findings.append("acknowledgement_late")
    else:
        a_mins = mins_from(cs, ack_at)
        assert a_mins is not None
        a_mins_str = str(a_mins)
        ack_role_out = role
        if a_mins > a_lim:
            findings.append("acknowledgement_late")
            window_missed = True
        else:
            window_missed = False

    # Unapproved always means no recognised ack → also acknowledgement_late when
    # the window has been missed (Harbor fairness: both codes).
    if "acknowledger_unapproved" in findings and "acknowledgement_late" not in findings:
        findings.append("acknowledgement_late")

    if window_missed:
        if rid in escalated_ids:
            esc_status = "recorded"
        else:
            esc_status = "missing"
            findings.append("escalation_missing")
    else:
        esc_status = "not_required"

    if not findings:
        findings = ["compliant"]

    # Stable order used across prior packs
    order = [
        "notification_late",
        "acknowledgement_late",
        "acknowledger_unapproved",
        "escalation_missing",
        "compliant",
    ]
    findings = [f for f in order if f in findings]

    return {
        "result_id": rid,
        "tier": str(tier),
        "clock_start": _fmt(cs),
        "notification_minutes": "" if n_mins is None else str(n_mins),
        "acknowledgement_minutes": a_mins_str,
        "acknowledged_by_role": ack_role_out,
        "escalation_status": esc_status,
        "findings": ";".join(findings),
    }


# ---------------------------------------------------------------------------
# New register rows R-81..R-105 (25) — qualitatively harder, not twin spam
# ---------------------------------------------------------------------------

NEW_CR = [
    # R-81: specialty_doctor ≈ specialty_registrar but unapproved; missing esc
    {
        "result_id": "R-81",
        "tier": "1",
        "test": "potassium",
        "released_at": "2026-07-06T10:00",
        "notified_at": "2026-07-06T10:12",
        "acknowledged_at": "2026-07-06T10:50",
        "acknowledged_by_role": "specialty_doctor",
    },
    # R-82: consultant_on_call unapproved + notify late + ESCALATION RECORDED
    {
        "result_id": "R-82",
        "tier": "1",
        "test": "troponin",
        "released_at": "2026-07-06T22:00",
        "notified_at": "2026-07-06T22:40",
        "acknowledged_at": "2026-07-06T22:55",
        "acknowledged_by_role": "consultant_on_call",
    },
    # R-83: bare "anp" ≠ advanced_nurse_practitioner
    {
        "result_id": "R-83",
        "tier": "1",
        "test": "lactate",
        "released_at": "2026-07-07T09:00",
        "notified_at": "2026-07-07T09:08",
        "acknowledged_at": "2026-07-07T09:40",
        "acknowledged_by_role": "anp",
    },
    # R-84: senior_house_officer near-miss; notify OK; missing esc
    {
        "result_id": "R-84",
        "tier": "1",
        "test": "glucose",
        "released_at": "2026-07-07T15:30",
        "notified_at": "2026-07-07T15:45",
        "acknowledged_at": "2026-07-07T16:20",
        "acknowledged_by_role": "senior_house_officer",
    },
    # R-85: st_registrar near-miss + notify late + missing (4 findings)
    {
        "result_id": "R-85",
        "tier": "1",
        "test": "magnesium",
        "released_at": "2026-07-07T23:10",
        "notified_at": "2026-07-07T23:45",
        "acknowledged_at": "2026-07-08T00:05",
        "acknowledged_by_role": "st_registrar",
    },
    # R-86: tier-1 with 120/200 — looks fine for tier-2 windows → both late + missing
    {
        "result_id": "R-86",
        "tier": "1",
        "test": "calcium",
        "released_at": "2026-07-08T11:00",
        "notified_at": "2026-07-08T13:00",
        "acknowledged_at": "2026-07-08T14:20",
        "acknowledged_by_role": "consultant",
    },
    # R-87: tier-2 decoy with similar wall times → compliant (different day)
    {
        "result_id": "R-87",
        "tier": "2",
        "test": "sodium",
        "released_at": "2026-07-08T13:00",
        "notified_at": "2026-07-08T15:00",
        "acknowledged_at": "2026-07-08T16:20",
        "acknowledged_by_role": "specialty_registrar",
    },
    # R-88: tier-2 notify-only late (241) ack OK; not_required
    {
        "result_id": "R-88",
        "tier": "2",
        "test": "bilirubin",
        "released_at": "2026-07-08T09:30",
        "notified_at": "2026-07-08T13:31",
        "acknowledged_at": "2026-07-08T17:00",
        "acknowledged_by_role": "consultant",
    },
    # R-89: Sat 18:30 → Sun 08:00; pre-clock notify; exact 480 → compliant
    {
        "result_id": "R-89",
        "tier": "2",
        "test": "haemoglobin",
        "released_at": "2026-07-11T18:30",
        "notified_at": "2026-07-11T19:00",
        "acknowledged_at": "2026-07-12T16:00",
        "acknowledged_by_role": "consultant",
    },
    # R-90: Sat 18:30 twin — ack 481 late + missing (not same-day twin spam)
    {
        "result_id": "R-90",
        "tier": "2",
        "test": "inr",
        "released_at": "2026-07-11T18:45",
        "notified_at": "2026-07-11T20:00",
        "acknowledged_at": "2026-07-12T16:01",
        "acknowledged_by_role": "resident_doctor",
    },
    # R-91: Sun 18:00 → Mon 08:00; notify exact 240; ack 481 late + missing
    {
        "result_id": "R-91",
        "tier": "2",
        "test": "creatinine",
        "released_at": "2026-07-12T18:00",
        "notified_at": "2026-07-13T12:00",
        "acknowledged_at": "2026-07-13T16:01",
        "acknowledged_by_role": "consultant",
    },
    # R-92: Fri evening → Sat 08:00; pre-clock; ack 479 compliant decoy
    {
        "result_id": "R-92",
        "tier": "2",
        "test": "phosphate",
        "released_at": "2026-07-10T19:15",
        "notified_at": "2026-07-10T21:00",
        "acknowledged_at": "2026-07-11T15:59",
        "acknowledged_by_role": "specialty_registrar",
    },
    # R-93: unapproved locum_registrar + escalation RECORDED (no escalation_missing)
    {
        "result_id": "R-93",
        "tier": "1",
        "test": "potassium",
        "released_at": "2026-07-09T08:00",
        "notified_at": "2026-07-09T08:10",
        "acknowledged_at": "2026-07-09T08:55",
        "acknowledged_by_role": "locum_registrar",
    },
    # R-94: absent acknowledgement (empty) tier-1 + missing escalation
    {
        "result_id": "R-94",
        "tier": "1",
        "test": "troponin",
        "released_at": "2026-07-09T14:00",
        "notified_at": "2026-07-09T14:15",
        "acknowledged_at": "",
        "acknowledged_by_role": "",
    },
    # R-95: absent ack tier-2 + notify late + escalation RECORDED
    {
        "result_id": "R-95",
        "tier": "2",
        "test": "sodium",
        "released_at": "2026-07-09T10:00",
        "notified_at": "2026-07-09T14:30",
        "acknowledged_at": "",
        "acknowledged_by_role": "",
    },
    # R-96: Mon 07:45 → 08:00; notify 241 late; ack OK → notification_late only
    {
        "result_id": "R-96",
        "tier": "2",
        "test": "bilirubin",
        "released_at": "2026-07-13T07:45",
        "notified_at": "2026-07-13T12:01",
        "acknowledged_at": "2026-07-13T15:30",
        "acknowledged_by_role": "consultant",
    },
    # R-97: Mon 07:45 decoy exact 240/480 from 08:00 → compliant
    {
        "result_id": "R-97",
        "tier": "2",
        "test": "haemoglobin",
        "released_at": "2026-07-13T07:45",
        "notified_at": "2026-07-13T12:00",
        "acknowledged_at": "2026-07-13T16:00",
        "acknowledged_by_role": "consultant",
    },
    # R-98: tier-2 ANP with 31/61 (tier-1-looking) still compliant
    {
        "result_id": "R-98",
        "tier": "2",
        "test": "glucose",
        "released_at": "2026-07-14T10:00",
        "notified_at": "2026-07-14T10:31",
        "acknowledged_at": "2026-07-14T11:01",
        "acknowledged_by_role": "advanced_nurse_practitioner",
    },
    # R-99: tier-1 ANP with 31/61 → both late + missing (buried, different day from R-98)
    {
        "result_id": "R-99",
        "tier": "1",
        "test": "lactate",
        "released_at": "2026-07-14T16:00",
        "notified_at": "2026-07-14T16:31",
        "acknowledged_at": "2026-07-14T17:01",
        "acknowledged_by_role": "advanced_nurse_practitioner",
    },
    # R-100: Wed 18:00 → Thu 08:00; both late 241/481 + missing
    {
        "result_id": "R-100",
        "tier": "2",
        "test": "creatinine",
        "released_at": "2026-07-08T18:00",
        "notified_at": "2026-07-09T12:01",
        "acknowledged_at": "2026-07-09T16:01",
        "acknowledged_by_role": "specialty_registrar",
    },
    # R-101: multi-finding: notify late + unapproved clinical_scientist + recorded esc
    {
        "result_id": "R-101",
        "tier": "1",
        "test": "potassium",
        "released_at": "2026-07-15T01:00",
        "notified_at": "2026-07-15T01:40",
        "acknowledged_at": "2026-07-15T01:50",
        "acknowledged_by_role": "clinical_scientist",
    },
    # R-102: Thu 17:59 release; notify 31 OK tier-2; ack exact 480 → compliant
    {
        "result_id": "R-102",
        "tier": "2",
        "test": "inr",
        "released_at": "2026-07-09T17:59",
        "notified_at": "2026-07-09T18:30",
        "acknowledged_at": "2026-07-10T01:59",
        "acknowledged_by_role": "consultant",
    },
    # R-103: Thu 18:00 → Fri 08:00; pre-clock notify 0; ack 480 inclusive compliant
    {
        "result_id": "R-103",
        "tier": "2",
        "test": "phosphate",
        "released_at": "2026-07-09T18:00",
        "notified_at": "2026-07-09T18:20",
        "acknowledged_at": "2026-07-10T16:00",
        "acknowledged_by_role": "consultant",
    },
    # R-104: staff_grade near-miss unapproved + missing (quiet among decoys)
    {
        "result_id": "R-104",
        "tier": "1",
        "test": "calcium",
        "released_at": "2026-07-15T11:00",
        "notified_at": "2026-07-15T11:20",
        "acknowledged_at": "2026-07-15T11:55",
        "acknowledged_by_role": "staff_grade",
    },
    # R-105: notify late + ack late + unapproved + ESCALATION RECORDED (3 findings)
    {
        "result_id": "R-105",
        "tier": "1",
        "test": "magnesium",
        "released_at": "2026-07-15T20:00",
        "notified_at": "2026-07-15T20:45",
        "acknowledged_at": "2026-07-15T21:10",
        "acknowledged_by_role": "foundation_doctor",
    },
]

# Escalations for rows where window missed but escalation WAS recorded
NEW_ESCALATIONS = [
    {"result_id": "R-82", "escalated_at": "2026-07-06T23:30"},
    {"result_id": "R-93", "escalated_at": "2026-07-09T09:20"},
    {"result_id": "R-95", "escalated_at": "2026-07-09T18:30"},
    {"result_id": "R-101", "escalated_at": "2026-07-15T02:30"},
    {"result_id": "R-105", "escalated_at": "2026-07-15T21:40"},
]


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def build_memo(audit: list[dict], counts: dict) -> str:
    n = len(audit)
    co = counts["results_compliant"]
    by_id = {r["result_id"]: r for r in audit}

    def lines_for(pred, fmt):
        out = []
        for r in audit:
            if pred(r):
                out.append(fmt(r))
        return out

    late_n = lines_for(
        lambda r: "notification_late" in r["findings"],
        lambda r: (
            f"- **{r['result_id']}** (tier {r['tier']}) - notified {r['notification_minutes']} min "
            f"after clock start {r['clock_start']} (window {'30' if r['tier']=='1' else '240'} min)."
        ),
    )
    late_a = []
    for r in audit:
        if "acknowledgement_late" not in r["findings"]:
            continue
        rid = r["result_id"]
        if "acknowledger_unapproved" in r["findings"]:
            late_a.append(
                f"- **{rid}** - no recognised acknowledgement (unapproved {r['acknowledged_by_role']}); "
                f"acknowledgement_minutes left empty; window "
                f"{'60' if r['tier']=='1' else '480'} min from {r['clock_start']} was missed."
            )
        elif not (r.get("acknowledgement_minutes") or "").strip():
            late_a.append(
                f"- **{rid}** - no acknowledgement recorded after clock start {r['clock_start']} "
                f"(window {'60' if r['tier']=='1' else '480'} min)."
            )
        else:
            late_a.append(
                f"- **{rid}** - acknowledged at {r['acknowledgement_minutes']} min after clock start "
                f"{r['clock_start']} (window {'60' if r['tier']=='1' else '480'} min)."
            )

    unap = lines_for(
        lambda r: "acknowledger_unapproved" in r["findings"],
        lambda r: (
            f"- **{r['result_id']}** - acknowledged by {r['acknowledged_by_role']}, "
            f"not on the approved list."
        ),
    )
    miss = lines_for(
        lambda r: "escalation_missing" in r["findings"],
        lambda r: f"- **{r['result_id']}** - missed acknowledgement window, no escalation.",
    )

    # Non-breach notes for hard traps
    non_breach = [
        "- Weekend results: core hours 08:00-18:00 apply every day (not weekday-only).",
        "- Inclusive boundaries: exactly at the window limit is within it.",
        "- Pre-clock telephone calls on tier-2 count as notification_minutes 0 from clock start.",
        "- Near-miss clinical titles that are not exact approved tokens are unapproved "
        "(for example specialty_doctor is not specialty_registrar; anp is not "
        "advanced_nurse_practitioner; consultant_on_call is not consultant).",
        "- Where the acknowledgement window was missed but an escalation appears on the "
        "register, escalation_status is recorded — not missing — even if the acknowledger "
        "was unapproved or acknowledgement was late.",
        "- Apply each tier's own windows: times that would breach tier-1 can still be "
        "compliant on tier-2, and long tier-1 elapsed times are breaches even when they "
        "would be fine for tier-2.",
    ]
    for rid in (
        "R-39",
        "R-41",
        "R-57",
        "R-58",
        "R-59",
        "R-61",
        "R-64",
        "R-67",
        "R-70",
        "R-71",
        "R-76",
        "R-87",
        "R-89",
        "R-92",
        "R-97",
        "R-98",
        "R-102",
        "R-103",
        "R-56",
    ):
        r = by_id.get(rid)
        if not r or r["findings"] != "compliant":
            if rid == "R-56":
                non_breach.append(
                    "- **R-56** - escalation present but acknowledgement was on time - "
                    "escalation not required, not a finding."
                )
            continue
        if rid == "R-87":
            non_breach.append(
                "- **R-87** - tier-2 with ~120/200 minutes is within 240/480 (do not apply tier-1 limits)."
            )
        elif rid == "R-89":
            non_breach.append(
                "- **R-89** - Saturday evening release: clock starts Sunday 08:00; pre-clock notify "
                "and acknowledgement at exactly 480 are compliant."
            )
        elif rid == "R-92":
            non_breach.append(
                "- **R-92** - Friday evening release: clock starts Saturday 08:00; pre-clock notify "
                "and acknowledgement at 479 are within window."
            )
        elif rid == "R-97":
            non_breach.append(
                "- **R-97** - Monday 07:45 tier-2: clock starts 08:00; exact 240/480 inclusive are compliant."
            )
        elif rid == "R-98":
            non_breach.append(
                "- **R-98** - tier-2 with 31/61 and advanced_nurse_practitioner remains compliant "
                "(tier-2 windows; ANP is approved)."
            )
        elif rid == "R-102":
            non_breach.append(
                "- **R-102** - Thursday 17:59 release starts immediately; acknowledgement at exactly "
                "480 is within the inclusive window."
            )
        elif rid == "R-103":
            non_breach.append(
                "- **R-103** - Thursday 18:00 release: clock starts Friday 08:00; pre-clock notify "
                "and exact 480 are compliant."
            )
        elif rid == "R-71":
            non_breach.append(
                "- **R-71** - tier-2 result with 31/61 minutes is still within the 240/480 windows."
            )
        elif rid in ("R-67", "R-70", "R-76", "R-61", "R-64", "R-39", "R-41", "R-57", "R-58", "R-59"):
            non_breach.append(
                f"- **{rid}** - long wall-clock or boundary case resolved by inclusive windows / "
                f"core-hours clock start (see procedure); findings compliant."
            )

    non_breach.append(
        "- Long wall-clock gaps after evening releases are often not breaches once the "
        "next-morning clock start is applied."
    )

    return f"""# CR-7 critical results audit - {n} results

{co} results are clean.

## Late notifications

{chr(10).join(late_n)}

## Late or absent acknowledgements

{chr(10).join(late_a)}

## Unapproved acknowledger

{chr(10).join(unap)}

## Missing escalation

{chr(10).join(miss)}

## What is not a finding

{chr(10).join(non_breach)}
"""


def update_instruction(instr: str) -> str:
    """Harden fairness notes: exact-token roles + recorded-vs-missing escalation."""
    # Replace the v15 tip paragraph with a stronger, still-fair disclosure block.
    tip = (
        "Only the four roles listed in the procedure are approved, matched as exact "
        "register tokens — near-miss clinical titles are unapproved even when they look "
        "similar (for example specialty_doctor is not specialty_registrar; anp is not "
        "advanced_nurse_practitioner; consultant_on_call is not consultant; "
        "senior_house_officer, st_registrar, locum_registrar, staff_grade, "
        "foundation_doctor, and clinical_scientist are also unapproved). Apply each "
        "tier's own notification and acknowledgement windows — do not borrow tier-1 "
        "limits for tier-2 results or the reverse. Where the acknowledgement window was "
        "missed but an escalation appears on the escalations register, set "
        "escalation_status to recorded (not missing) even if the acknowledger was "
        "unapproved or the acknowledgement was late; escalation_missing applies only "
        "when the window was missed and no escalation row exists."
    )
    # Strip older tip fragments if present, then append once before the attachments list.
    patterns = [
        r"Only the four roles listed in the procedure are approved;.*?(?=\n\n- The attachments|\n- The attachments)",
        r"Only the four roles listed in the procedure are approved —.*?(?=\n\n- The attachments|\n- The attachments)",
    ]
    cleaned = instr
    for pat in patterns:
        cleaned = re.sub(pat, "", cleaned, count=1, flags=re.S)
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    anchor = "- The attachments are provided read-only"
    if tip[:40] not in cleaned:
        if anchor in cleaned:
            cleaned = cleaned.replace(anchor, tip + "\n\n" + anchor, 1)
        else:
            cleaned = cleaned.rstrip() + "\n\n" + tip + "\n"
    return cleaned


def main() -> None:
    # --- instruction fairness ---
    instr_path = PACK / "instruction.md"
    instr = update_instruction(instr_path.read_text(encoding="utf-8"))
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

    # --- escalations ---
    esc_path = PACK / "environment" / "input" / "escalations.csv"
    esc = [
        r
        for r in csv.DictReader(esc_path.open(encoding="utf-8-sig"))
        if r["result_id"] not in {e["result_id"] for e in NEW_ESCALATIONS}
    ]
    esc.extend(NEW_ESCALATIONS)
    write_csv(esc_path, esc, ["result_id", "escalated_at"])
    escalated_ids = {r["result_id"] for r in esc}

    # --- audit gold: keep existing R-01..R-80; grade R-81+ ---
    audit_path = PACK / "solution" / "files" / "results_audit.csv"
    audit = [
        r
        for r in csv.DictReader(audit_path.open(encoding="utf-8-sig"))
        if r["result_id"] not in new_ids
    ]
    for r in audit:
        if "acknowledger_unapproved" in (r.get("findings") or ""):
            r["acknowledgement_minutes"] = ""
    new_audit = [grade_row(row, escalated_ids) for row in NEW_CR]
    audit.extend(new_audit)
    write_csv(audit_path, audit, AUDIT_FIELDS)

    # sanity: re-grade new rows print
    print("NEW AUDIT ROWS:")
    for r in new_audit:
        print(
            f"  {r['result_id']} clock={r['clock_start']} n={r['notification_minutes']!r} "
            f"a={r['acknowledgement_minutes']!r} esc={r['escalation_status']} findings={r['findings']}"
        )

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

    memo = build_memo(audit, counts)
    (PACK / "solution" / "files" / "results_memo.md").write_text(
        memo, encoding="utf-8", newline="\n"
    )

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

    n = len(audit)
    ids = [f"R-{i:02d}" for i in range(1, 10)] + [f"R-{i}" for i in range(10, n + 1)]
    # IDs are R-01..R-09 then R-10..R-105 (zero-padded to 2 for <100, but R-100+ are 3 digits)
    ids = []
    for i in range(1, n + 1):
        ids.append(f"R-{i:02d}" if i < 100 else f"R-{i}")

    find("audit_covers_every_result")["assertion"]["expected"] = "(?s)" + "".join(
        rf"(?=.*\b{re.escape(i)}\b)" for i in ids
    )
    find("audit_covers_every_result")["metadata"][
        "how_justification"
    ] = f"Requires every register ID R-01 through R-{n if n>=100 else f'{n:02d}'}."
    find("audit_covers_every_result")["metadata"][
        "why_justification"
    ] = f"All {n} results appear in the audit CSV."

    find("result_notification_breaches")["assertion"]["expected"] = nb
    find("result_acknowledgement_breaches")["assertion"]["expected"] = ab
    find("result_unapproved_acknowledgement_results")["assertion"]["expected"] = ua
    find("result_missing_escalation_results")["assertion"]["expected"] = me
    find("result_results_compliant")["assertion"]["expected"] = co

    # --- v16 trap verifiers (quoted-numeric tolerant) ---
    upsert(
        "specialty_doctor_unapproved_missing",
        "physician_associate_unapproved_empty_mins",
        r"(?mi)^\x22?R-81\x22?\s*,[^\n]*,\s*\x22?\s*12(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*\x22?\s*,[^\n]*specialty_doctor[^\n]*,\s*\x22?missing\x22?\s*,[^\n]*(?=.*acknowledger_unapproved)(?=.*acknowledgement_late)(?=.*escalation_missing)",
        "R-81 specialty_doctor must be unapproved with empty minutes, late+missing.",
        "R-81 near-miss specialty_registrar trap.",
    )
    upsert(
        "consultant_on_call_recorded_not_missing",
        "unapproved_r06_also_ack_late",
        r"(?mi)^\x22?R-82\x22?\s*,[^\n]*,\s*\x22?\s*40(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*\x22?\s*,[^\n]*consultant_on_call[^\n]*,\s*\x22?recorded\x22?\s*,[^\n]*(?=.*notification_late)(?=.*acknowledger_unapproved)(?=.*acknowledgement_late)(?!.*escalation_missing)",
        "R-82 consultant_on_call: notify late + unapproved + ack late with escalation recorded (not missing).",
        "R-82 recorded-escalation multi-finding trap.",
    )
    upsert(
        "anp_abbrev_unapproved_empty",
        "physician_associate_unapproved_empty_mins",
        r"(?mi)^\x22?R-83\x22?\s*,[^\n]*,\s*\x22?\s*8(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*\x22?\s*,[^\n]*\banp\b[^\n]*,\s*\x22?missing\x22?\s*,[^\n]*(?=.*acknowledger_unapproved)(?=.*acknowledgement_late)(?=.*escalation_missing)",
        "R-83 bare anp token is unapproved (not advanced_nurse_practitioner).",
        "R-83 abbreviation near-miss role.",
    )
    upsert(
        "senior_house_officer_unapproved",
        "physician_associate_unapproved_empty_mins",
        r"(?mi)^\x22?R-84\x22?\s*,[^\n]*,[^\n]*,\s*\x22?\s*\x22?\s*,[^\n]*senior_house_officer[^\n]*,\s*\x22?missing\x22?\s*,[^\n]*(?=.*acknowledger_unapproved)(?=.*acknowledgement_late)(?=.*escalation_missing)",
        "R-84 senior_house_officer unapproved with empty minutes + missing escalation.",
        "R-84 SHO near-miss role.",
    )
    upsert(
        "st_registrar_multifinding_missing",
        "clinical_fellow_multifinding",
        r"(?mi)^\x22?R-85\x22?\s*,[^\n]*,\s*\x22?\s*35(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*\x22?\s*,[^\n]*st_registrar[^\n]*,\s*\x22?missing\x22?\s*,[^\n]*(?=.*notification_late)(?=.*acknowledger_unapproved)(?=.*acknowledgement_late)(?=.*escalation_missing)",
        "R-85 st_registrar must carry all four findings with empty acknowledgement_minutes.",
        "R-85 four-finding near-miss role.",
    )
    upsert(
        "tier1_long_times_both_late",
        "tier1_twin_both_late_missing",
        r"(?mi)^\x22?R-86\x22?\s*,\s*\x22?1\x22?\s*,[^\n]*,\s*\x22?\s*120(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*200(?:\.0+)?\s*\x22?\s*,[^\n]*,\s*\x22?missing\x22?\s*,[^\n]*(?=.*notification_late)(?=.*acknowledgement_late)(?=.*escalation_missing)",
        "R-86 tier-1 with 120/200 must be both late + escalation_missing (not treated as tier-2).",
        "R-86 reverse tier-limit trap.",
    )
    upsert(
        "tier2_similar_times_compliant",
        "tier2_looks_like_tier1_still_compliant",
        r"(?mi)^\x22?R-87\x22?\s*,\s*\x22?2\x22?\s*,[^\n]*,\s*\x22?\s*120(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*200(?:\.0+)?\s*\x22?\s*,[^\n]*\x22?(compliant|ok|pass|none|no[_ ]?finding)\x22?\s*$",
        "R-87 tier-2 with 120/200 must remain compliant.",
        "R-87 buried tier-limit decoy.",
    )
    upsert(
        "tier2_notify_only_241",
        "tier2_notify_late_ack_ok_no_escalation",
        r"(?mi)^\x22?R-88\x22?\s*,[^\n]*,\s*\x22?\s*241(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*450(?:\.0+)?\s*\x22?\s*,[^\n]*,\s*\x22?not_required\x22?\s*,[^\n]*notification_late",
        "R-88 notify 241 late with ack OK and escalation not_required.",
        "R-88 notify-only late trap.",
    )
    upsert(
        "saturday_evening_exact_480_compliant",
        "friday_evening_preclock_ack_480_compliant",
        r"(?mi)^\x22?R-89\x22?\s*,[^\n]*2026-07-12[T ]0?8:00[^\n]*,\s*\x22?\s*0(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*480(?:\.0+)?\s*\x22?\s*,[^\n]*\x22?(compliant|ok|pass|none|no[_ ]?finding)\x22?\s*$",
        "R-89 Saturday evening must clock Sunday 08:00 with notify 0 and exact 480 compliant.",
        "R-89 weekend evening inclusive decoy.",
    )
    upsert(
        "saturday_evening_ack_481_missing",
        "friday_1800_preclock_ack_481",
        r"(?mi)^\x22?R-90\x22?\s*,[^\n]*2026-07-12[T ]0?8:00[^\n]*,\s*\x22?\s*0(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*481(?:\.0+)?\s*\x22?\s*,[^\n]*,\s*\x22?missing\x22?\s*,[^\n]*(?=.*acknowledgement_late)(?=.*escalation_missing)",
        "R-90 Saturday evening ack 481 must be late+missing from Sunday 08:00.",
        "R-90 weekend evening off-by-one.",
    )
    upsert(
        "sunday_evening_notify_ok_ack_late",
        "sunday_1800_monday_clock_ack_late",
        r"(?mi)^\x22?R-91\x22?\s*,[^\n]*2026-07-13[T ]0?8:00[^\n]*,\s*\x22?\s*240(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*481(?:\.0+)?\s*\x22?\s*,[^\n]*,\s*\x22?missing\x22?\s*,[^\n]*(?=.*acknowledgement_late)(?=.*escalation_missing)",
        "R-91 Sunday 18:00 → Monday 08:00; notify 240 OK; ack 481 late+missing.",
        "R-91 split notify-ok ack-late weekend chain.",
    )
    upsert(
        "locum_registrar_recorded_escalation",
        "consultant_on_call_recorded_not_missing",
        r"(?mi)^\x22?R-93\x22?\s*,[^\n]*,[^\n]*,\s*\x22?\s*\x22?\s*,[^\n]*locum_registrar[^\n]*,\s*\x22?recorded\x22?\s*,[^\n]*(?=.*acknowledger_unapproved)(?=.*acknowledgement_late)(?!.*escalation_missing)",
        "R-93 locum_registrar unapproved with empty minutes and escalation recorded (not missing).",
        "R-93 unapproved + recorded escalation trap.",
    )
    upsert(
        "absent_ack_tier1_missing",
        "row_r_10_findings",
        r"(?mi)^\x22?R-94\x22?\s*,[^\n]*,[^\n]*,\s*\x22?\s*\x22?\s*,[^\n]*,\s*\x22?missing\x22?\s*,[^\n]*acknowledgement_late",
        "R-94 absent acknowledgement must be acknowledgement_late with escalation_missing.",
        "R-94 absent-ack trap.",
    )
    upsert(
        "absent_ack_tier2_notify_late_recorded",
        "escalated_breach_not_double_counted",
        r"(?mi)^\x22?R-95\x22?\s*,[^\n]*,\s*\x22?\s*270(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*\x22?\s*,[^\n]*,\s*\x22?recorded\x22?\s*,[^\n]*(?=.*notification_late)(?=.*acknowledgement_late)(?!.*escalation_missing)",
        "R-95 absent ack with notify late must use escalation recorded (not missing).",
        "R-95 absent-ack + recorded escalation.",
    )
    upsert(
        "monday_precore_notify_late_only",
        "saturday_precore_notify_late_ack_ok",
        r"(?mi)^\x22?R-96\x22?\s*,[^\n]*2026-07-13[T ]0?8:00[^\n]*,\s*\x22?\s*241(?:\.0+)?\s*\x22?\s*,[^\n]*,\s*\x22?not_required\x22?\s*,[^\n]*notification_late",
        "R-96 Monday pre-core: notify 241 late, ack OK, escalation not_required.",
        "R-96 weekday pre-core notify-only.",
    )
    upsert(
        "monday_precore_exact_compliant",
        "sunday_precore_exact_windows_compliant",
        r"(?mi)^\x22?R-97\x22?\s*,[^\n]*2026-07-13[T ]0?8:00[^\n]*,\s*\x22?\s*240(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*480(?:\.0+)?\s*\x22?\s*,[^\n]*\x22?(compliant|ok|pass|none|no[_ ]?finding)\x22?\s*$",
        "R-97 Monday 07:45 must use 08:00 clock with exact 240/480 compliant.",
        "R-97 weekday pre-core inclusive decoy.",
    )
    upsert(
        "anp_tier2_31_61_compliant",
        "tier2_looks_like_tier1_still_compliant",
        r"(?mi)^\x22?R-98\x22?\s*,\s*\x22?2\x22?\s*,[^\n]*,\s*\x22?\s*31(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*61(?:\.0+)?\s*\x22?\s*,[^\n]*advanced_nurse_practitioner[^\n]*\x22?(compliant|ok|pass|none|no[_ ]?finding)\x22?\s*$",
        "R-98 tier-2 ANP with 31/61 must stay compliant.",
        "R-98 approved-role tier-limit decoy.",
    )
    upsert(
        "anp_tier1_31_61_both_late",
        "tier1_twin_both_late_missing",
        r"(?mi)^\x22?R-99\x22?\s*,\s*\x22?1\x22?\s*,[^\n]*,\s*\x22?\s*31(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*61(?:\.0+)?\s*\x22?\s*,[^\n]*,\s*\x22?missing\x22?\s*,[^\n]*(?=.*notification_late)(?=.*acknowledgement_late)(?=.*escalation_missing)",
        "R-99 tier-1 ANP 31/61 must be both late + missing.",
        "R-99 buried tier-1 twin (different day from R-98).",
    )
    upsert(
        "wed_evening_both_late_missing",
        "tier2_both_late_241_481_missing",
        r"(?mi)^\x22?R-100\x22?\s*,[^\n]*2026-07-09[T ]0?8:00[^\n]*,\s*\x22?\s*241(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*481(?:\.0+)?\s*\x22?\s*,[^\n]*,\s*\x22?missing\x22?\s*,[^\n]*(?=.*notification_late)(?=.*acknowledgement_late)(?=.*escalation_missing)",
        "R-100 Wednesday 18:00 → Thursday 08:00 both late 241/481 + missing.",
        "R-100 weekday evening both-late chain.",
    )
    upsert(
        "clinical_scientist_recorded_multifinding",
        "consultant_on_call_recorded_not_missing",
        r"(?mi)^\x22?R-101\x22?\s*,[^\n]*,\s*\x22?\s*40(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*\x22?\s*,[^\n]*clinical_scientist[^\n]*,\s*\x22?recorded\x22?\s*,[^\n]*(?=.*notification_late)(?=.*acknowledger_unapproved)(?=.*acknowledgement_late)(?!.*escalation_missing)",
        "R-101 clinical_scientist: notify late + unapproved + ack late with escalation recorded.",
        "R-101 recorded multi-finding night trap.",
    )
    upsert(
        "thu_1759_exact_480_compliant",
        "friday_closing_inclusive_compliant",
        r"(?mi)^\x22?R-102\x22?\s*,[^\n]*2026-07-09[T ]17:59[^\n]*,\s*\x22?\s*31(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*480(?:\.0+)?\s*\x22?\s*,[^\n]*\x22?(compliant|ok|pass|none|no[_ ]?finding)\x22?\s*$",
        "R-102 Thursday 17:59 release with exact 480 ack must stay compliant.",
        "R-102 before-close inclusive decoy.",
    )
    upsert(
        "thu_1800_preclock_480_compliant",
        "friday_evening_preclock_ack_480_compliant",
        r"(?mi)^\x22?R-103\x22?\s*,[^\n]*2026-07-10[T ]0?8:00[^\n]*,\s*\x22?\s*0(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*480(?:\.0+)?\s*\x22?\s*,[^\n]*\x22?(compliant|ok|pass|none|no[_ ]?finding)\x22?\s*$",
        "R-103 Thursday 18:00 must clock Friday 08:00 with notify 0 and exact 480 compliant.",
        "R-103 17:59-vs-18:00 policy paragraph trap.",
    )
    upsert(
        "staff_grade_unapproved_missing",
        "physician_associate_unapproved_empty_mins",
        r"(?mi)^\x22?R-104\x22?\s*,[^\n]*,[^\n]*,\s*\x22?\s*\x22?\s*,[^\n]*staff_grade[^\n]*,\s*\x22?missing\x22?\s*,[^\n]*(?=.*acknowledger_unapproved)(?=.*acknowledgement_late)(?=.*escalation_missing)",
        "R-104 staff_grade unapproved with empty minutes + missing.",
        "R-104 buried near-miss role.",
    )
    upsert(
        "foundation_doctor_recorded_multifinding",
        "consultant_on_call_recorded_not_missing",
        r"(?mi)^\x22?R-105\x22?\s*,[^\n]*,\s*\x22?\s*45(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*\x22?\s*,[^\n]*foundation_doctor[^\n]*,\s*\x22?recorded\x22?\s*,[^\n]*(?=.*notification_late)(?=.*acknowledger_unapproved)(?=.*acknowledgement_late)(?!.*escalation_missing)",
        "R-105 foundation_doctor: three findings with escalation recorded (must NOT mark escalation_missing).",
        "R-105 recorded multi-finding trap.",
    )
    # Soft memo coverage for new qualitative traps (not brittle lexical)
    upsert(
        "memo_lists_r82_or_r93_or_r105_recorded",
        "memo_lists_r65_unapproved",
        r"(?is)(?:\bR-82\b.{0,500}(?:recorded|escalat|consultant_on_call|unapproved)|\bR-93\b.{0,500}(?:recorded|escalat|locum_registrar|unapproved)|\bR-105\b.{0,500}(?:recorded|escalat|foundation_doctor|unapproved))",
        "Memo must explain at least one unapproved/late row with recorded escalation (R-82/R-93/R-105).",
        "Recorded-escalation traps covered in memo.",
    )
    upsert(
        "memo_lists_r86_or_r99_tier_swap",
        "memo_lists_r72_or_r77_late",
        r"(?is)(?:\bR-86\b.{0,400}(?:notif|120|late|window|tier)|\bR-99\b.{0,400}(?:notif|31|late|window))",
        "Memo must explain a reverse/buried tier-limit breach (R-86 or R-99).",
        "Tier-swap breach traps in memo.",
    )
    upsert(
        "memo_explains_r89_or_r103_non_breach",
        "memo_explains_tier_or_preclock_non_breach",
        r"(?is)(?:\bR-89\b.{0,400}(?:08:00|480|pre[- ]?clock|Sunday|compliant)|\bR-103\b.{0,400}(?:08:00|480|pre[- ]?clock|18:00|compliant)|\bR-98\b.{0,400}(?:tier[- ]?2|240|480|ANP|advanced_nurse))",
        "Memo must explain a hard non-breach (Sat evening 480, Thu 18:00 chain, or ANP tier-2).",
        "Hard non-breach traps explained in memo.",
    )
    upsert(
        "memo_lists_r81_or_r83_near_miss_role",
        "memo_lists_r73_or_r80_unapproved",
        r"(?is)(?:\bR-81\b.{0,500}(?:unapproved|specialty_doctor|not on the approved)|\bR-83\b.{0,500}(?:unapproved|\banp\b|not on the approved))",
        "Memo must explain a near-miss role trap (R-81 or R-83).",
        "Near-miss exact-token roles in memo.",
    )

    for v in data["verifiers"]:
        exp = v["assertion"].get("expected")
        if isinstance(exp, str) and exp.startswith("(?"):
            re.compile(exp)

    vj.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print("verifiers", len(data["verifiers"]))

    # --- pytest coverage_depth ---
    test_path = PACK / "tests" / "test_outputs.py"
    test_src = test_path.read_text(encoding="utf-8")
    # Replace/append v16 block
    v16_block = '''
def test_v16_hard_trap_findings():
    """Per-row findings for v16 densify traps (coverage_depth)."""
    findings = _audit_findings(WORKSPACE)
    expected = {
        "R-81": "acknowledgement_late;acknowledger_unapproved;escalation_missing",
        "R-82": "notification_late;acknowledgement_late;acknowledger_unapproved",
        "R-83": "acknowledgement_late;acknowledger_unapproved;escalation_missing",
        "R-84": "acknowledgement_late;acknowledger_unapproved;escalation_missing",
        "R-85": "notification_late;acknowledgement_late;acknowledger_unapproved;escalation_missing",
        "R-86": "notification_late;acknowledgement_late;escalation_missing",
        "R-87": "compliant",
        "R-88": "notification_late",
        "R-89": "compliant",
        "R-90": "acknowledgement_late;escalation_missing",
        "R-91": "acknowledgement_late;escalation_missing",
        "R-92": "compliant",
        "R-93": "acknowledgement_late;acknowledger_unapproved",
        "R-94": "acknowledgement_late;escalation_missing",
        "R-95": "notification_late;acknowledgement_late",
        "R-96": "notification_late",
        "R-97": "compliant",
        "R-98": "compliant",
        "R-99": "notification_late;acknowledgement_late;escalation_missing",
        "R-100": "notification_late;acknowledgement_late;escalation_missing",
        "R-101": "notification_late;acknowledgement_late;acknowledger_unapproved",
        "R-102": "compliant",
        "R-103": "compliant",
        "R-104": "acknowledgement_late;acknowledger_unapproved;escalation_missing",
        "R-105": "notification_late;acknowledgement_late;acknowledger_unapproved",
    }
    for rid, want in expected.items():
        assert rid in findings, f"missing audit row {rid}"
        got = ";".join(p.strip() for p in findings[rid].split(";") if p.strip())
        want_n = ";".join(p.strip() for p in want.split(";") if p.strip())
        assert set(got.split(";")) == set(want_n.split(";")), (
            f"{rid} findings {got!r} != {want_n!r}"
        )


def test_v16_recorded_escalation_not_missing():
    """Recorded-escalation traps must NOT carry escalation_missing."""
    import csv
    path = WORKSPACE / "results_audit.csv"
    assert path.is_file()
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = {(r.get("result_id") or "").strip(): r for r in csv.DictReader(f)}
    for rid in ("R-82", "R-93", "R-95", "R-101", "R-105"):
        row = rows[rid]
        assert (row.get("escalation_status") or "").strip() == "recorded", rid
        assert "escalation_missing" not in (row.get("findings") or ""), rid
        if "acknowledger_unapproved" in (row.get("findings") or ""):
            assert (row.get("acknowledgement_minutes") or "").strip() == "", rid


def test_v16_unapproved_empty_acknowledgement_minutes():
    """Harbor fairness: unapproved roles leave acknowledgement_minutes empty."""
    import csv
    path = WORKSPACE / "results_audit.csv"
    assert path.is_file()
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = {(r.get("result_id") or "").strip(): r for r in csv.DictReader(f)}
    for rid in ("R-81", "R-82", "R-83", "R-84", "R-85", "R-93", "R-101", "R-104", "R-105"):
        row = rows[rid]
        assert "acknowledger_unapproved" in (row.get("findings") or ""), rid
        assert (row.get("acknowledgement_minutes") or "").strip() == "", (
            f"{rid} must have empty acknowledgement_minutes"
        )

'''
    if "test_v16_hard_trap_findings" in test_src:
        test_src = re.sub(
            r"\ndef test_v16_hard_trap_findings\(\):.*",
            "\n" + v16_block.lstrip("\n"),
            test_src,
            count=1,
            flags=re.S,
        )
    else:
        if not test_src.endswith("\n"):
            test_src += "\n"
        test_src += v16_block
    test_path.write_text(test_src, encoding="utf-8", newline="\n")
    print("pytest trap coverage updated")


def run_pytest() -> int:
    tests = PACK / "tests"
    ws = Path(tempfile.mkdtemp(prefix="h40-v16-gold-"))
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


if __name__ == "__main__":
    main()
    rc = run_pytest()
    sys.exit(rc)
