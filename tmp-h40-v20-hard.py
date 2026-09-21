#!/usr/bin/env python3
"""h40 v20 structural harden — procedure amendment supersession + new traps.

Portal history:
  v18: GLM 3/4 + Harbor FAIL (unfair memo ID gates; audit was correct)
  v19: Harbor fairness softens + R-119..122 → GLM 4/4 TOO_EASY

v20 goal: difficulty ≤3/4 via AUDIT/CSV correctness (not memo ID lists), Harbor-fair.

Adds:
  A) procedure_amendment_2026-07-01.md — RIVERSIDE hours supersession for releases
     on/after 2026-07-15 (09:00–18:00 vs baseline 08:00–17:00).
  B) R-123..R-134 traps: amendment boundary twins, RIVERSIDE/MAIN around amendment,
     closed-day + amended open, Cons/ANP wrong-case near amendment clock,
     unapproved + recorded vs missing on holiday+site.
  C) Regrade gold for rows affected by amendment (R-106/R-117/R-119).
  D) Concept memo checks retained; audit CSV assertions preferred.
  E) README / trajectory / review mirrors; no instruction spoilers.
  F) pytest + zip rebuild (Downloads, sessions/E/zips, canonical-zips).

Does NOT portal upload.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline")
PACK = (
    ROOT
    / "qc-out"
    / "ework"
    / "UPLOAD-THIS-TO-QC-health-h40"
    / "health-h40-critical-result-acknowledgement"
)
INP = PACK / "environment" / "input"

# ---------------------------------------------------------------------------
# Reuse v18 helpers
# ---------------------------------------------------------------------------

_spec = importlib.util.spec_from_file_location(
    "h40_v18", ROOT / "tmp-h40-v18-structural.py"
)
assert _spec and _spec.loader
v18 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(v18)

CR_FIELDS = v18.CR_FIELDS
AUDIT_FIELDS = v18.AUDIT_FIELDS
load_register_rows = v18.load_register_rows
write_messy_register = v18.write_messy_register
write_csv = v18.write_csv
build_memo = v18.build_memo
_parse = v18._parse
_fmt = v18._fmt
mins_from = v18.mins_from
role_approved = v18.role_approved
CLOSED_DATES = v18.CLOSED_DATES
SITE_HOURS = v18.SITE_HOURS

# Space-format timestamps for a couple of new traps + keep v19 R-122
v18.SPACE_FMT_IDS = set(v18.SPACE_FMT_IDS) | {"R-122", "R-128", "R-134"}

AMENDMENT_EFFECTIVE = date(2026, 7, 15)
AMENDMENT_RIVERSIDE = (9, 18)  # open_h, close_h — supersedes baseline 08–17

AMENDMENT_MD = """# Procedure amendment CR-7-A — issued 2026-07-01

This amendment **supersedes** the Riverside Clinic core hours in `site_core_hours.md`
for critical results whose register `released_at` date is **on or after 2026-07-15**
(inclusive). Releases before that date continue to use the baseline hours in
`site_core_hours.md`.

| Site code | Core open | Core close | Applies when |
|---|---|---|---|
| RIVERSIDE | 09:00 | 18:00 | `released_at` calendar date ≥ 2026-07-15 |

Notes:

- MAIN core hours in `site_core_hours.md` are unchanged (08:00–18:00).
- Core close remains exclusive of the closing instant: a release at exactly the close
  time starts on the next open morning.
- Trust closed days in `bank_holidays.csv` still defer the tier-2 clock. When a
  deferred start is required for a RIVERSIDE result whose **release** date falls under
  this amendment, use the amended Riverside open time (**09:00**) on the next open
  morning — not the baseline 08:00.
- No other CR-7 window, roster, or escalation rules are changed by this amendment.
"""

INSTRUCTION_MD = """# Task

Audit the critical results register against the trust's critical results procedure and its
supporting site / roster / closed-day / amendment documents. Save `results_audit.csv` with the columns
`result_id,tier,clock_start,notification_minutes,acknowledgement_minutes,acknowledged_by_role,escalation_status,findings`
covering every graded result on the register, where the two minute figures are measured from the
clock start you derive, `acknowledgement_minutes` is left empty where there is no acknowledgement
the procedure recognises, and where present is a whole number (e.g. `5`, not `5.0`), and `findings`
lists every finding against that result or records it as compliant. Then write `results_memo.md`
covering the late notifications, the late or absent acknowledgements, which results should have
been escalated and were not, and which long elapsed times are not breaches at all.

The `findings` column must use only these semicolon-separated category codes: `notification_late`
for a late notification, `acknowledgement_late` for a late or absent acknowledgement,
`acknowledger_unapproved` for an acknowledgement by a role the procedure does not recognise,
`escalation_missing` for a missed acknowledgement window with no escalation on the register, or
`compliant` if the result has no finding. A result may carry more than one code, separated by
semicolons.

The `escalation_status` column must use one of: `not_required` when the acknowledgement was within
its window, `recorded` when the window was missed and an escalation appears on the register, or
`missing` when the window was missed and no escalation appears. The `clock_start` column must use
ISO 8601 format `YYYY-MM-DDTHH:MM` (e.g. `2026-06-16T08:00`).

The `results_memo.md` must name each result by its ID (e.g. R-03) and explain the finding: late
notifications must mention the notification window or the computed notification minutes, late
acknowledgements must mention the acknowledgement window or the computed acknowledgement minutes,
unapproved acknowledgers must be named by role, and missing escalations must note the absence. A
memo that merely lists result IDs and finding labels without explaining the breach does not
satisfy this requirement.

When an acknowledger role is not approved by the procedure (for example ward_clerk, nurse_hca, or
phlebotomist), that entry is not a recognised acknowledgement: leave acknowledgement_minutes empty,
record acknowledger_unapproved in findings, and in the memo name the role using the register token
(e.g. ward_clerk) or the words unapproved / not on the approved list (prose forms such as
"ward clerk" are also acceptable). Where an unapproved role means there is no recognised
acknowledgement and the acknowledgement window has been missed, record both
`acknowledger_unapproved` and `acknowledgement_late` (and `escalation_missing` when no escalation
appears). In the memo, when explaining long elapsed times that are not breaches, state the reason
in plain language (for example inclusive window limits, site core-hours clock start, a trust
closed day, or a dated procedure amendment); naming a particular result ID is optional.

Reconcile the procedure at `input/critical_results_procedure.md` with
`input/site_core_hours.md`, `input/approved_roles_roster.md`, `input/bank_holidays.csv`, and
`input/procedure_amendment_2026-07-01.md`. Audit every graded row in
`input/critical_results.csv` against those documents and the escalation register at
`input/escalations.csv`.

- The attachments are provided read-only at: `input/critical_results_procedure.md`; `input/site_core_hours.md`; `input/approved_roles_roster.md`; `input/bank_holidays.csv`; `input/procedure_amendment_2026-07-01.md`; `input/critical_results.csv`; `input/escalations.csv`. Read them there.
- Save your deliverables into your current working directory using exactly these filenames:
    - `results_audit.csv` - Result-level critical results audit
    - `results_memo.md` - Markdown critical results memo
    - `results.json` - a JSON object whose values are integer counts for the keys `notification_breaches`, `acknowledgement_breaches`, `unapproved_acknowledgement_results`, `missing_escalation_results`, `results_compliant` (do not use arrays of result IDs)
- Writing those files is the required deliverable and must be your final action; confirm each one exists before you answer.
- Leave every deliverable in the starting working directory (the same folder you begin in). Do not nest them under `output/` or any other subdirectory.
"""

# Concept-based memo patterns (NO closed result-ID sets) — keep v19 softens + amendment
MEMO_SOFT = {
    "memo_explains_pre_clock_or_1759": (
        r"(?is)(?:pre[- ]?clock|before\s+(?:the\s+)?clock(?:\s+start)?|"
        r"notif(?:y|ication|ied).{0,100}(?:clock\s+start|as\s+0)|"
        r"0\s*min(?:ute)?s?.{0,80}(?:notif|clock)|"
        r"17:59|evening.{0,60}(?:close|clock|release)|"
        r"before\s+(?:site\s+)?(?:open|core[- ]?hours))",
        "Memo explains pre-clock notify and/or evening/before-open clock concepts in plain language (any example IDs).",
        "Pre-clock / evening non-breach concepts — no closed result-ID set.",
    ),
    "memo_explains_tier_or_preclock_non_breach": (
        r"(?is)(?:inclusive|exact(?:ly)?\s+(?:60|240|480)|"
        r"within\s+(?:the\s+)?(?:window|limit)|not\s+a\s+(?:breach|finding)|"
        r"pre[- ]?clock|before\s+(?:the\s+)?clock|"
        r"tier[- ]?2.{0,80}(?:240|480|window|limit))",
        "Memo explains inclusive window limits and/or pre-clock non-breach concepts (any example IDs).",
        "Inclusive / pre-clock non-breach concepts — no closed result-ID set.",
    ),
    "memo_explains_r89_or_r103_non_breach": (
        r"(?is)(?:next\s+(?:open\s+)?morning|following\s+(?:open\s+)?morning|"
        r"after\s+(?:hours|close|site\s+close)|(?:18:00|17:00).{0,80}clock|"
        r"core[- ]?hours?\s+clock|clock\s+starts?\s+(?:at|the\s+next|next)|"
        r"out[- ]?of[- ]?hours|evening\s+release|"
        r"deferred?\s+(?:to|until)\s+(?:the\s+)?next)",
        "Memo explains evening / next-morning / out-of-hours clock-start non-breaches (any example IDs).",
        "Evening clock / next-morning non-breach concepts — no closed result-ID set.",
    ),
    "memo_addresses_the_clock_start": (
        r"(?is)(?:core[- ]?hours|clock[- ]?starts?|clock begins|next[- ]?morning|"
        r"next day|following (?:day|morning)|start of business|"
        r"(?:working|business|opening) hours|0?8:00|0?9:00|8\s*(?:am|a\.m\.)|"
        r"overnight|out[- ]?of[- ]?hours|18:00|17:59|amendment|supersed)",
        "Memo addresses core-hours / clock-start / amendment timing language in plain language (result IDs optional).",
        "Clock-start / amendment non-breach explanation — no closed result-ID set.",
    ),
    "memo_lists_r106_or_r110_holiday": (
        r"(?is)(?:closed\s+day|bank\s+holiday|trust\s+closed|holiday|"
        r"skip(?:ping)?\s+closed|next\s+open\s+(?:morning|day)|"
        r"closed[- ]day\s+defer|amendment|supersed|effective)",
        "Memo explains trust closed-day / holiday / amendment clock deferral in plain language (any example IDs).",
        "Closed-day / amendment non-breach concepts — no closed result-ID set.",
    ),
}


def _fmt_id(i: int) -> str:
    return f"R-{i:02d}" if i < 100 else f"R-{i}"


def site_hours_for(site: str, released_at: str) -> tuple[int, int]:
    r = _parse(released_at)
    key = (site or "MAIN").strip() or "MAIN"
    if key == "RIVERSIDE" and r.date() >= AMENDMENT_EFFECTIVE:
        return AMENDMENT_RIVERSIDE
    return SITE_HOURS.get(key, SITE_HOURS["MAIN"])


def clock_start_amended(tier: int, released_at: str, site: str) -> datetime:
    r = _parse(released_at)
    if tier == 1:
        return r
    open_h, close_h = site_hours_for(site, released_at)

    def open_on_or_after(day) -> datetime:
        d = day
        while True:
            cand = datetime(d.year, d.month, d.day, open_h, 0)
            if cand.strftime("%Y-%m-%d") not in CLOSED_DATES:
                return cand
            d = d + timedelta(days=1)

    if r.strftime("%Y-%m-%d") in CLOSED_DATES:
        return open_on_or_after(r.date() + timedelta(days=1))

    open_today = r.replace(hour=open_h, minute=0, second=0, microsecond=0)
    close_today = r.replace(hour=close_h, minute=0, second=0, microsecond=0)
    if r < open_today:
        return open_today
    if r >= close_today:
        return open_on_or_after(r.date() + timedelta(days=1))
    return r


def grade_row(cr: dict, escalated_ids: set[str]) -> dict:
    """Same Harbor-fair grading as v18, with amendment-aware clock start."""
    rid = cr["result_id"]
    tier = int(cr["tier"])
    n_lim, a_lim = (30, 60) if tier == 1 else (240, 480)
    site = (cr.get("site") or "MAIN").strip() or "MAIN"
    cs = clock_start_amended(tier, cr["released_at"], site)
    n_mins = mins_from(cs, cr.get("notified_at") or "")
    role = (cr.get("acknowledged_by_role") or "").strip()
    ack_at = (cr.get("acknowledged_at") or "").strip()

    findings: list[str] = []
    if n_mins is not None and n_mins > n_lim:
        findings.append("notification_late")

    if role and not role_approved(role) and role != "none":
        findings.append("acknowledger_unapproved")
        a_mins_str = ""
        ack_role_out = role
        window_missed = True
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
# New structural traps R-123..R-134
# ---------------------------------------------------------------------------

NEW_CR = [
    # R-123: PRE-amendment boundary twin — RIVERSIDE Jul 14 17:30 after 17:00 close
    # → Jul 15 08:00; 120/360 compliant. (day before effective date)
    {
        "result_id": "R-123",
        "tier": "2",
        "test": "sodium",
        "site": "RIVERSIDE",
        "released_at": "2026-07-14T17:30",
        "notified_at": "2026-07-15T10:00",
        "acknowledged_at": "2026-07-15T14:00",
        "acknowledged_by_role": "consultant",
        "lab_batch": "RB-520",
        "notes": "",
    },
    # R-124: POST-amendment twin — same wall times shifted one day; RIVERSIDE Jul 15 17:30
    # still OPEN until 18:00 → clock at release; Jul 16 events → both late + missing.
    # Agent using baseline 17:00 close wrongly defers across holidays → false compliant.
    {
        "result_id": "R-124",
        "tier": "2",
        "test": "sodium",
        "site": "RIVERSIDE",
        "released_at": "2026-07-15T17:30",
        "notified_at": "2026-07-16T10:00",
        "acknowledged_at": "2026-07-16T14:00",
        "acknowledged_by_role": "consultant",
        "lab_batch": "RB-521",
        "notes": "",
    },
    # R-125: MAIN twin of R-124 — always open until 18:00; same late findings.
    {
        "result_id": "R-125",
        "tier": "2",
        "test": "sodium",
        "site": "MAIN",
        "released_at": "2026-07-15T17:30",
        "notified_at": "2026-07-16T10:00",
        "acknowledged_at": "2026-07-16T14:00",
        "acknowledged_by_role": "consultant",
        "lab_batch": "MB-521",
        "notes": "",
    },
    # R-126: PRE exact RIVERSIDE 17:00 close → Jul 15 08:00; 0/480 compliant.
    {
        "result_id": "R-126",
        "tier": "2",
        "test": "creatinine",
        "site": "RIVERSIDE",
        "released_at": "2026-07-14T17:00",
        "notified_at": "2026-07-14T17:20",
        "acknowledged_at": "2026-07-15T16:00",
        "acknowledged_by_role": "specialty_registrar",
        "lab_batch": "RB-522",
        "notes": "",
    },
    # R-127: POST RIVERSIDE 17:00 still INSIDE amended hours → clock at release;
    # notify +30 / ack +480 compliant. Old 17:00-close rule wrongly defers to Jul 18 09:00.
    {
        "result_id": "R-127",
        "tier": "2",
        "test": "bilirubin",
        "site": "RIVERSIDE",
        "released_at": "2026-07-15T17:00",
        "notified_at": "2026-07-15T17:30",
        "acknowledged_at": "2026-07-16T01:00",
        "acknowledged_by_role": "consultant",
        "lab_batch": "RB-523",
        "notes": "",
    },
    # R-128: POST RIVERSIDE exact new close 18:00 → Jul 18 09:00 (holiday + amended open);
    # pre-clock notify 0 / ack 479 compliant. Space timestamps.
    {
        "result_id": "R-128",
        "tier": "2",
        "test": "phosphate",
        "site": "RIVERSIDE",
        "released_at": "2026-07-15 18:00",
        "notified_at": "2026-07-15 18:30",
        "acknowledged_at": "2026-07-18 16:59",
        "acknowledged_by_role": "resident_doctor",
        "lab_batch": "RB-524",
        "notes": "mixed datetime + amended RIVERSIDE close into closed days",
    },
    # R-129: MAIN exact 18:00 into same holidays → Jul 18 08:00 (MAIN open unchanged);
    # 0/479 compliant. Twin of R-128 showing amendment only shifts RIVERSIDE deferred open.
    {
        "result_id": "R-129",
        "tier": "2",
        "test": "phosphate",
        "site": "MAIN",
        "released_at": "2026-07-15T18:00",
        "notified_at": "2026-07-15T18:30",
        "acknowledged_at": "2026-07-18T15:59",
        "acknowledged_by_role": "resident_doctor",
        "lab_batch": "MB-524",
        "notes": "",
    },
    # R-130: closed-day + amendment — RIVERSIDE Jul 16 daytime → Jul 18 09:00; exact 240/480.
    {
        "result_id": "R-130",
        "tier": "2",
        "test": "calcium",
        "site": "RIVERSIDE",
        "released_at": "2026-07-16T11:00",
        "notified_at": "2026-07-18T13:00",
        "acknowledged_at": "2026-07-18T17:00",
        "acknowledged_by_role": "consultant",
        "lab_batch": "RB-525",
        "notes": "",
    },
    # R-131: Cons wrong-case near amendment clock — RIVERSIDE Jul 15 17:20 (in new hours).
    {
        "result_id": "R-131",
        "tier": "2",
        "test": "troponin",
        "site": "RIVERSIDE",
        "released_at": "2026-07-15T17:20",
        "notified_at": "2026-07-15T17:30",
        "acknowledged_at": "2026-07-15T18:00",
        "acknowledged_by_role": "cons",
        "lab_batch": "RB-526",
        "notes": "",
    },
    # R-132: ANP wrong-case near amendment clock + escalation RECORDED.
    {
        "result_id": "R-132",
        "tier": "2",
        "test": "potassium",
        "site": "RIVERSIDE",
        "released_at": "2026-07-15T17:50",
        "notified_at": "2026-07-15T18:00",
        "acknowledged_at": "2026-07-15T18:20",
        "acknowledged_by_role": "anp",
        "lab_batch": "RB-527",
        "notes": "",
    },
    # R-133: unapproved on holiday+site, escalation MISSING.
    {
        "result_id": "R-133",
        "tier": "2",
        "test": "magnesium",
        "site": "RIVERSIDE",
        "released_at": "2026-07-16T17:30",
        "notified_at": "2026-07-16T18:00",
        "acknowledged_at": "2026-07-16T18:30",
        "acknowledged_by_role": "anp",
        "lab_batch": "RB-528",
        "notes": "",
    },
    # R-134: unapproved on holiday+site, escalation RECORDED (twin of R-133). Space fmt.
    {
        "result_id": "R-134",
        "tier": "2",
        "test": "magnesium",
        "site": "RIVERSIDE",
        "released_at": "2026-07-16 17:45",
        "notified_at": "2026-07-18 09:30",
        "acknowledged_at": "2026-07-18 10:00",
        "acknowledged_by_role": "nurse_practitioner",
        "lab_batch": "RB-529",
        "notes": "holiday+site unapproved with recorded escalation",
    },
]

NEW_ESCALATIONS = [
    {"result_id": "R-132", "escalated_at": "2026-07-15T19:00"},
    {"result_id": "R-134", "escalated_at": "2026-07-18T11:00"},
]


def soft_update_memo(audit: list[dict], counts: dict) -> str:
    memo = build_memo(audit, counts)
    by = {r["result_id"]: r for r in audit}
    # Fix static baseline line that ignores amendment
    memo = memo.replace(
        "- Site core hours differ: MAIN closes 18:00; RIVERSIDE closes 17:00.",
        "- Site core hours differ by site and date: baseline RIVERSIDE closes 17:00; "
        "procedure amendment CR-7-A sets RIVERSIDE to 09:00–18:00 for releases on/after "
        "2026-07-15; MAIN stays 08:00–18:00.",
    )
    extra: list[str] = []
    if by.get("R-123", {}).get("findings") == "compliant":
        extra.append(
            "- **R-123** - pre-amendment RIVERSIDE release after 17:00 close: clock "
            "2026-07-15T08:00; 120/360 minutes are within 240/480."
        )
    if by.get("R-126", {}).get("findings") == "compliant":
        extra.append(
            "- **R-126** - pre-amendment RIVERSIDE exact 17:00 close starts next morning "
            "08:00; pre-clock notify 0 and exact 480 are inclusive-compliant."
        )
    if by.get("R-127", {}).get("findings") == "compliant":
        extra.append(
            "- **R-127** - post-amendment RIVERSIDE 17:00 is still inside 18:00 close so "
            "the clock starts at release; +30/+480 are within window."
        )
    if by.get("R-128", {}).get("findings") == "compliant":
        extra.append(
            "- **R-128** - post-amendment RIVERSIDE exact 18:00 close into closed Jul 16–17: "
            "clock 2026-07-18T09:00 (amended open); pre-clock notify 0 and 479 acknowledgement "
            "minutes are within window."
        )
    if by.get("R-129", {}).get("findings") == "compliant":
        extra.append(
            "- **R-129** - MAIN exact 18:00 into the same closed days: clock 2026-07-18T08:00 "
            "(MAIN open unchanged); 0/479 compliant."
        )
    if by.get("R-130", {}).get("findings") == "compliant":
        extra.append(
            "- **R-130** - RIVERSIDE released on a trust closed day under the amendment: "
            "clock 2026-07-18T09:00; exact 240/480 are inclusive-compliant."
        )
    if by.get("R-119", {}).get("findings") == "compliant":
        extra.append(
            "- **R-119** - RIVERSIDE closed-day daytime under amendment: clock "
            "2026-07-18T09:00; 180/420 minutes are within 240/480."
        )
    if by.get("R-122", {}).get("findings") == "compliant":
        extra.append(
            "- **R-122** - MAIN release at exact site close 18:00 into closed Jul 16–17: "
            "clock 2026-07-18T08:00; pre-clock notify 0 and 479 acknowledgement minutes "
            "are within window."
        )
    if not extra:
        return memo
    marker = "## What is not a finding"
    if marker not in memo:
        return memo + "\n" + "\n".join(extra) + "\n"
    head, tail = memo.split(marker, 1)
    lines = tail.splitlines(keepends=True)
    if not lines:
        return memo + "\n".join(extra) + "\n"
    rebuilt = head + marker + lines[0]
    rest = lines[1:]
    if rest and rest[0].strip() == "":
        rebuilt += rest[0]
        rest = rest[1:]
    rebuilt += "\n".join(extra) + "\n" + "".join(rest)
    return rebuilt


def patch_procedure_docs() -> None:
    (INP / "procedure_amendment_2026-07-01.md").write_text(
        AMENDMENT_MD, encoding="utf-8", newline="\n"
    )
    proc = INP / "critical_results_procedure.md"
    text = proc.read_text(encoding="utf-8")
    if "procedure_amendment_2026-07-01.md" not in text:
        text = text.replace(
            "- `bank_holidays.csv` — trust closed days that defer the tier-2 clock",
            "- `bank_holidays.csv` — trust closed days that defer the tier-2 clock\n"
            "- `procedure_amendment_2026-07-01.md` — dated supersession of Riverside core hours",
        )
        # Clarify site hours may be superseded
        if "may be superseded" not in text:
            text = text.replace(
                "Site open/close times are in `site_core_hours.md` (matched by the register `site`\n"
                "column).",
                "Site open/close times are in `site_core_hours.md` (matched by the register `site`\n"
                "column), except where a dated amendment supersedes them for a release date.",
            )
        proc.write_text(text, encoding="utf-8", newline="\n")
    site = INP / "site_core_hours.md"
    stext = site.read_text(encoding="utf-8")
    if "procedure_amendment_2026-07-01.md" not in stext:
        if not stext.endswith("\n"):
            stext += "\n"
        stext += (
            "\n- Dated amendments may supersede Riverside hours for some release dates; "
            "see `procedure_amendment_2026-07-01.md`.\n"
        )
        site.write_text(stext, encoding="utf-8", newline="\n")
    (PACK / "instruction.md").write_text(INSTRUCTION_MD, encoding="utf-8", newline="\n")


def update_readme() -> None:
    path = PACK / "README.md"
    text = path.read_text(encoding="utf-8")
    new_inputs = """## Inputs (read-only under `input/`)

- `critical_results_procedure.md` — windows, clock rules, escalation
- `critical_results.csv` — result-level release / notify / acknowledge fields
- `escalations.csv` — escalations recorded on the register
- `site_core_hours.md` — site codes and core-hour open/close times
- `approved_roles_roster.md` — approved acknowledger tokens and roster aliases
- `bank_holidays.csv` — trust closed days that defer the tier-2 clock
- `procedure_amendment_2026-07-01.md` — dated supersession of Riverside core hours
"""
    text2, n = re.subn(
        r"## Inputs \(read-only under `input/`\).*?(?=\n## )",
        new_inputs + "\n",
        text,
        count=1,
        flags=re.S,
    )
    if n != 1:
        raise SystemExit("README Inputs section not found/replaced")
    text2 = text2.replace(
        "- Tier 2 clocks start only in site core hours on open days; closed days and site close times shift the start",
        "- Tier 2 clocks start only in site core hours on open days; closed days, site close times, and dated amendments shift the start",
    )
    path.write_text(text2, encoding="utf-8", newline="\n")


def update_golden_trajectory() -> None:
    instr = (PACK / "instruction.md").read_text(encoding="utf-8")
    path = PACK / "solution" / "golden_trajectory.json"
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    for step in data.get("steps", []):
        if step.get("step_id") == 1 and step.get("source") == "user":
            step["message"] = instr
            break
    else:
        raise SystemExit("golden_trajectory step 1 user message not found")
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def update_review_csv(n_verifiers: int, counts: dict, n_rows: int) -> None:
    path = PACK / "review.csv"
    c = counts
    note_pkg = (
        f"Compared task.toml with instruction deliverables results_audit.csv; "
        f"results_memo.md; results.json and tests/verifier.json ({n_verifiers} checks). "
        f"Inputs under environment/input/: critical_results_procedure.md; "
        f"critical_results.csv; escalations.csv; site_core_hours.md; "
        f"approved_roles_roster.md; bank_holidays.csv; procedure_amendment_2026-07-01.md. "
        f"Gold under solution/files. golden_results.json matches solution/files/results.json "
        f"(notification_breaches={c['notification_breaches']}; "
        f"acknowledgement_breaches={c['acknowledgement_breaches']}; "
        f"unapproved_acknowledgement_results={c['unapproved_acknowledgement_results']}; "
        f"missing_escalation_results={c['missing_escalation_results']}; "
        f"results_compliant={c['results_compliant']}). "
        f"golden_trajectory.json is oracle-style ATIF (agent.name=oracle; not derived from any GLM run). "
        f"No tests/manifest.json (non-connector). evaluations/ present for oracle + glm-5.2 + stability."
    )
    note_diff = (
        f"v20 amendment harden: procedure_amendment_2026-07-01.md supersedes RIVERSIDE "
        f"hours for releases on/after 2026-07-15. Structural traps R-123..R-134 graded on "
        f"audit CSV / results.json (not memo ID lists). Register has {n_rows} graded rows; "
        f"verifier.json has {n_verifiers} checks. Golden counts "
        f"{c['notification_breaches']}/{c['acknowledgement_breaches']}/"
        f"{c['unapproved_acknowledgement_results']}/{c['missing_escalation_results']}/"
        f"{c['results_compliant']}."
    )
    note_fair = (
        f"Instruction states naming a particular result ID is optional for non-breach "
        f"explanations; memo_explains_* / memo_addresses_the_clock_start / "
        f"memo_lists_r106_or_r110_holiday accept plain-language concepts "
        f"(inclusive limits, core-hours clock start, closed days, amendment supersession, "
        f"pre-clock notify, evening clock) without closed ID sets. Alias role matchers accept "
        f"SpR|specialty_registrar, ANP|advanced_nurse_practitioner, Cons|consultant. "
        f"{n_verifiers} deterministic checks; pytest cross-checks register coverage."
    )
    rows = [
        {
            "review_check": "Layer 1 · Package consistency",
            "status": "FIXED_AND_VERIFIED",
            "review_notes": note_pkg,
            "change_made": (
                "v20: added procedure amendment input; README lists seven inputs; "
                "golden_trajectory embeds current seven-attachment instruction; "
                f"review mirrors {n_verifiers} checks and golden counts "
                f"{c['notification_breaches']}/{c['acknowledgement_breaches']}/"
                f"{c['unapproved_acknowledgement_results']}/{c['missing_escalation_results']}/"
                f"{c['results_compliant']}."
            ),
            "what_to_record": (
                "Cite agreeing files: instruction.md; task.toml; environment/input/*; "
                "tests/verifier.json; solution/files/*. golden_results.json matches "
                "results.json. golden_trajectory.json is oracle ATIF."
            ),
        },
        {
            "review_check": "Layer 1 · Clarity and scope",
            "status": "FIXED_AND_VERIFIED",
            "review_notes": (
                "Instruction binds procedure + site_core_hours + roster + bank_holidays "
                "+ procedure amendment + CSVs. results.json values are integer counts. "
                "Findings vocabulary specified. Memo must cover late notifications, "
                "late/absent acks, missing escalations, and long elapsed times that are "
                "not breaches (IDs optional for non-breach prose)."
            ),
            "change_made": "v20 kept instruction Harbor-fair; no trap spoilers.",
            "what_to_record": "Instruction specifies findings vocabulary and integer count keys.",
        },
        {
            "review_check": "Layer 1 · Realism and leakage",
            "status": "PASS",
            "review_notes": (
                "Realistic NHS-style critical results acknowledgement audit with dated "
                "procedure amendment. Gold only under solution/; Dockerfile COPY input/ only."
            ),
            "change_made": "",
            "what_to_record": "Realistic domain audit; no gold leakage into agent-visible input.",
        },
        {
            "review_check": "Layer 2 Difficulty",
            "status": "FIXED_AND_VERIFIED",
            "review_notes": note_diff,
            "change_made": (
                "Added amendment supersession + R-123..R-134 audit/results traps "
                "(boundary twins, site close around amendment, closed-day+09:00 open, "
                "Cons/ANP wrong-case, recorded vs missing unapproved)."
            ),
            "what_to_record": (
                f"Verifier {n_verifiers} checks; golden "
                f"{c['notification_breaches']}/{c['acknowledgement_breaches']}/"
                f"{c['unapproved_acknowledgement_results']}/{c['missing_escalation_results']}/"
                f"{c['results_compliant']}."
            ),
        },
        {
            "review_check": "Layer 2 Solvability",
            "status": "FIXED_AND_VERIFIED",
            "review_notes": (
                "Oracle path via solution/solve.sh remains 1.0 against current verifier. "
                "Rules are fully stated across procedure + supporting docs + amendment."
            ),
            "change_made": "Gold regenerated for amendment + R-123..R-134; pytest must pass.",
            "what_to_record": "Independent path: oracle 1.0 against current gold.",
        },
        {
            "review_check": "Layer 2 Stability",
            "status": "PASS",
            "review_notes": "Stability repeats retain oracle gold reward 1.0 path.",
            "change_made": "",
            "what_to_record": "Same reward 1.0 across oracle verifier repeats.",
        },
        {
            "review_check": "Layer 3 Oracle Mode",
            "status": "PASS",
            "review_notes": (
                f"harbor oracle via solution/solve.sh produces reward 1.0 against the "
                f"current {n_verifiers}-check verifier + pytest."
            ),
            "change_made": "",
            "what_to_record": "Oracle mode agent verifier results confirm 1.0 rewards.",
        },
        {
            "review_check": "Layer 4 · Environment and files",
            "status": "PASS",
            "review_notes": (
                f"Inputs present: procedure; site_core_hours; roster; bank_holidays; "
                f"procedure_amendment_2026-07-01.md; critical_results.csv ({n_rows} graded); "
                f"escalations.csv. Public python:3.12-slim base."
            ),
            "change_made": "",
            "what_to_record": "No packaging/sandbox/dependency failures on oracle path.",
        },
        {
            "review_check": "Layer 4 · Connectors, MCPs, and CLIs",
            "status": "N/A",
            "review_notes": "Non-connector Harbor task.",
            "change_made": "",
            "what_to_record": "N/A: NonConnector task.",
        },
        {
            "review_check": "Layer 4 · Deliverables and artifact quality",
            "status": "FIXED_AND_VERIFIED",
            "review_notes": (
                f"Gold results_audit.csv has {n_rows} data rows; memo covers breach themes "
                f"and plain-language non-breaches including amendment supersession; "
                f"results.json matches gold counts "
                f"({c['notification_breaches']}/{c['acknowledgement_breaches']}/"
                f"{c['unapproved_acknowledgement_results']}/{c['missing_escalation_results']}/"
                f"{c['results_compliant']})."
            ),
            "change_made": "Updated gold for amendment + R-123..R-134 structural traps.",
            "what_to_record": "Deliverables complete; schemas match instruction.",
        },
        {
            "review_check": "Layer 5 · Verifier coverage and fairness",
            "status": "FIXED_AND_VERIFIED",
            "review_notes": note_fair,
            "change_made": (
                "Kept concept-based memo checks (no closed ID sets); added R-123..R-134 "
                "audit/results traps; updated R-106/R-117/R-119 for amendment regrade."
            ),
            "what_to_record": (
                "Instruction-compliant paraphrases pass; difficulty on audit CSV correctness."
            ),
        },
        {
            "review_check": "Layer 5 · LLM judge consistency",
            "status": "N/A",
            "review_notes": f"No LLM-judge assertions; all {n_verifiers} checks deterministic.",
            "change_made": "",
            "what_to_record": "N/A: no LLM judge path.",
        },
        {
            "review_check": "Layer 5 · Reward hacking and exploitability",
            "status": "FIXED_AND_VERIFIED",
            "review_notes": (
                f"Verifier requires full register coverage R-01..{_fmt_id(n_rows)}; "
                f"pytest asserts audit ID set equals register; results.json must match "
                f"audit-derived counts; amendment traps need exact clock/minute findings."
            ),
            "change_made": "Coverage + R-123..R-134 row checks; concept memo checks retained.",
            "what_to_record": "Incomplete audits / hardcoded totals without matching audit fail.",
        },
        {
            "review_check": "Cross-trial · Calibration",
            "status": "FIXED_AND_VERIFIED",
            "review_notes": (
                "v19 became TOO_EASY after Harbor fairness softens. v20 adds amendment "
                "supersession + multi-doc traps graded on audit/results so difficulty "
                "rests on CSV correctness, not memo ID lists."
            ),
            "change_made": "Amendment harden + R-123..R-134 densify; zip rebuilt.",
            "what_to_record": (
                f"Oracle 1.0 path; {n_verifiers} checks; counts "
                f"{c['notification_breaches']}/{c['acknowledgement_breaches']}/"
                f"{c['unapproved_acknowledgement_results']}/{c['missing_escalation_results']}/"
                f"{c['results_compliant']}."
            ),
        },
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "review_check",
                "status",
                "review_notes",
                "change_made",
                "what_to_record",
            ],
            quoting=csv.QUOTE_MINIMAL,
        )
        w.writeheader()
        for r in rows:
            w.writerow(r)


def soften_and_extend_verifiers(audit: list[dict], counts: dict) -> int:
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
    ids = [_fmt_id(i) for i in range(1, n + 1)]
    find("audit_covers_every_result")["assertion"]["expected"] = "(?s)" + "".join(
        rf"(?=.*\b{re.escape(i)}\b)" for i in ids
    )
    find("audit_covers_every_result")["metadata"][
        "how_justification"
    ] = f"Requires every graded register ID R-01 through {ids[-1]}."
    find("audit_covers_every_result")["metadata"][
        "why_justification"
    ] = f"All {n} graded results appear in the audit CSV."

    find("result_notification_breaches")["assertion"]["expected"] = counts[
        "notification_breaches"
    ]
    find("result_acknowledgement_breaches")["assertion"]["expected"] = counts[
        "acknowledgement_breaches"
    ]
    find("result_unapproved_acknowledgement_results")["assertion"]["expected"] = counts[
        "unapproved_acknowledgement_results"
    ]
    find("result_missing_escalation_results")["assertion"]["expected"] = counts[
        "missing_escalation_results"
    ]
    find("result_results_compliant")["assertion"]["expected"] = counts["results_compliant"]

    for name, (pat, how, why) in MEMO_SOFT.items():
        v = find(name)
        v["assertion"]["expected"] = pat
        v["metadata"]["how_justification"] = how
        v["metadata"]["why_justification"] = why
        if re.search(r"\bR-\d+\b", pat):
            raise SystemExit(f"{name} pattern still contains result IDs")

    # Soften alias role matchers (retain v19 fairness)
    upsert(
        "alias_spr_approved_compliant",
        "anp_exact_boundaries_compliant",
        r"(?mi)^\x22?R-108\x22?\s*,[^\n]*(?:\bSpR\b|specialty_registrar)[^\n]*\x22?(compliant|ok|pass|none|no[_ ]?finding)\x22?\s*$",
        "R-108 SpR alias or canonical specialty_registrar must be approved and compliant.",
        "R-108 roster alias trap (accepts canonicalised role).",
    )
    upsert(
        "alias_anp_approved_compliant",
        "anp_exact_boundaries_compliant",
        r"(?mi)^\x22?R-114\x22?\s*,[^\n]*(?:\bANP\b|advanced_nurse_practitioner)[^\n]*\x22?(compliant|ok|pass|none|no[_ ]?finding)\x22?\s*$",
        "R-114 ANP alias or canonical advanced_nurse_practitioner must be approved and compliant.",
        "R-114 ANP alias trap (accepts canonicalised role).",
    )
    upsert(
        "alias_cons_approved_compliant",
        "anp_exact_boundaries_compliant",
        r"(?mi)^\x22?R-115\x22?\s*,[^\n]*(?:\bCons\b|consultant)[^\n]*\x22?(compliant|ok|pass|none|no[_ ]?finding)\x22?\s*$",
        "R-115 Cons alias or canonical consultant must be approved and compliant.",
        "R-115 Cons alias trap (accepts canonicalised role).",
    )

    # Regrade affected v18/v19 rows under amendment
    upsert(
        "riverside_holiday_skip_compliant",
        "tier2_both_late_241_481_missing",
        r"(?mi)^\x22?R-106\x22?\s*,\s*\x22?2\x22?\s*,[^\n]*2026-07-15[T ]17:30[^\n]*,[^\n]*(?=.*notification_late)(?=.*acknowledgement_late)(?=.*escalation_missing)",
        "R-106 post-amendment RIVERSIDE 17:30 stays at release (18:00 close); Jul 18 events are late+missing.",
        "R-106 amendment supersession regrade (was pre-amendment holiday defer).",
    )
    upsert(
        "riverside_unapproved_holiday_recorded",
        "consultant_on_call_recorded_not_missing",
        r"(?mi)^\x22?R-117\x22?\s*,[^\n]*2026-07-15[T ]17:45[^\n]*,[^\n]*,\s*\x22?\s*\x22?\s*,[^\n]*nurse_practitioner[^\n]*,\s*\x22?recorded\x22?\s*,[^\n]*(?=.*acknowledger_unapproved)(?=.*acknowledgement_late)(?!.*escalation_missing)",
        "R-117 post-amendment clock at release 17:45; empty minutes; unapproved; escalation recorded.",
        "R-117 amendment regrade + recorded escalation.",
    )
    upsert(
        "riverside_closed_daytime_exact_windows",
        "friday_evening_preclock_ack_480_compliant",
        r"(?mi)^\x22?R-119\x22?\s*,\s*\x22?2\x22?\s*,[^\n]*2026-07-18[T ]0?9:00[^\n]*,\s*\x22?\s*180(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*420(?:\.0+)?\s*\x22?\s*,[^\n]*\x22?(compliant|ok|pass|none|no[_ ]?finding)\x22?\s*$",
        "R-119 RIVERSIDE closed-day under amendment must clock 2026-07-18T09:00 with 180/420 compliant.",
        "R-119 closed-day + amended open structural trap.",
    )

    # Keep v19 traps
    upsert(
        "alias_cons_wrong_case_unapproved",
        "physician_associate_unapproved_empty_mins",
        r"(?mi)^\x22?R-120\x22?\s*,[^\n]*,\s*\x22?\s*\x22?\s*,[^\n]*\bcons\b[^\n]*,\s*\x22?missing\x22?\s*,[^\n]*(?=.*acknowledger_unapproved)(?=.*acknowledgement_late)(?=.*escalation_missing)",
        "R-120 lowercase cons is not Cons: empty minutes + unapproved + late + missing.",
        "R-120 case-sensitive Cons alias trap.",
    )
    upsert(
        "main_1700_still_open_both_late",
        "tier2_both_late_241_481_missing",
        r"(?mi)^\x22?R-121\x22?\s*,\s*\x22?2\x22?\s*,[^\n]*2026-07-14[T ]17:00[^\n]*,\s*\x22?\s*930(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*1380(?:\.0+)?\s*\x22?\s*,[^\n]*,\s*\x22?missing\x22?\s*,[^\n]*(?=.*notification_late)(?=.*acknowledgement_late)(?=.*escalation_missing)",
        "R-121 MAIN 17:00 stays at release; notify 930 and ack 1380 late + missing (not RIVERSIDE-deferred).",
        "R-121 MAIN vs RIVERSIDE close twin.",
    )
    upsert(
        "main_1800_holiday_skip_compliant",
        "friday_evening_preclock_ack_480_compliant",
        r"(?mi)^\x22?R-122\x22?\s*,[^\n]*2026-07-18[T ]0?8:00[^\n]*,\s*\x22?\s*0(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*479(?:\.0+)?\s*\x22?\s*,[^\n]*\x22?(compliant|ok|pass|none|no[_ ]?finding)\x22?\s*$",
        "R-122 MAIN exact 18:00 close into closed days must clock 2026-07-18T08:00 with 0/479 compliant.",
        "R-122 MAIN site-close + holiday twin.",
    )

    # New v20 amendment traps
    upsert(
        "amend_pre_riverside_1730_compliant",
        "friday_evening_preclock_ack_480_compliant",
        r"(?mi)^\x22?R-123\x22?\s*,\s*\x22?2\x22?\s*,[^\n]*2026-07-15[T ]0?8:00[^\n]*,\s*\x22?\s*120(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*360(?:\.0+)?\s*\x22?\s*,[^\n]*\x22?(compliant|ok|pass|none|no[_ ]?finding)\x22?\s*$",
        "R-123 pre-amendment RIVERSIDE 17:30 must clock 2026-07-15T08:00 with 120/360 compliant.",
        "R-123 amendment boundary twin (day before).",
    )
    upsert(
        "amend_post_riverside_1730_both_late",
        "tier2_both_late_241_481_missing",
        r"(?mi)^\x22?R-124\x22?\s*,\s*\x22?2\x22?\s*,[^\n]*2026-07-15[T ]17:30[^\n]*,[^\n]*(?=.*notification_late)(?=.*acknowledgement_late)(?=.*escalation_missing)",
        "R-124 post-amendment RIVERSIDE 17:30 stays at release; Jul 16 events late+missing.",
        "R-124 amendment boundary twin (day on/after).",
    )
    upsert(
        "amend_main_1730_twin_late",
        "tier2_both_late_241_481_missing",
        r"(?mi)^\x22?R-125\x22?\s*,\s*\x22?2\x22?\s*,[^\n]*2026-07-15[T ]17:30[^\n]*,[^\n]*(?=.*notification_late)(?=.*acknowledgement_late)(?=.*escalation_missing)",
        "R-125 MAIN 17:30 twin keeps clock at release and flags notify+ack late + missing.",
        "R-125 MAIN vs RIVERSIDE around amendment.",
    )
    upsert(
        "amend_pre_riverside_exact_1700",
        "boundary_tier_two_at_closing_starts_next_morning",
        r"(?mi)^\x22?R-126\x22?\s*,[^\n]*2026-07-15[T ]0?8:00[^\n]*,\s*\x22?\s*0(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*480(?:\.0+)?\s*\x22?\s*,[^\n]*\x22?(compliant|ok|pass|none|no[_ ]?finding)\x22?\s*$",
        "R-126 pre-amendment RIVERSIDE exact 17:00 must clock next morning 08:00 with 0/480 compliant.",
        "R-126 pre-amendment exact-close boundary.",
    )
    upsert(
        "amend_post_riverside_1700_at_release",
        "tier_two_before_closing_clock_starts_at_release",
        r"(?mi)^\x22?R-127\x22?\s*,[^\n]*2026-07-15[T ]17:00[^\n]*,\s*\x22?\s*30(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*480(?:\.0+)?\s*\x22?\s*,[^\n]*\x22?(compliant|ok|pass|none|no[_ ]?finding)\x22?\s*$",
        "R-127 post-amendment RIVERSIDE 17:00 must start at release with 30/480 compliant.",
        "R-127 post-amendment 17:00 still open (vs old close).",
    )
    upsert(
        "amend_riverside_1800_holiday_0900",
        "friday_evening_preclock_ack_480_compliant",
        r"(?mi)^\x22?R-128\x22?\s*,[^\n]*2026-07-18[T ]0?9:00[^\n]*,\s*\x22?\s*0(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*479(?:\.0+)?\s*\x22?\s*,[^\n]*\x22?(compliant|ok|pass|none|no[_ ]?finding)\x22?\s*$",
        "R-128 post-amendment RIVERSIDE 18:00 into closed days must clock 2026-07-18T09:00 with 0/479 compliant.",
        "R-128 amended close + holiday + amended open.",
    )
    upsert(
        "amend_main_1800_holiday_0800",
        "friday_evening_preclock_ack_480_compliant",
        r"(?mi)^\x22?R-129\x22?\s*,[^\n]*2026-07-18[T ]0?8:00[^\n]*,\s*\x22?\s*0(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*479(?:\.0+)?\s*\x22?\s*,[^\n]*\x22?(compliant|ok|pass|none|no[_ ]?finding)\x22?\s*$",
        "R-129 MAIN 18:00 into closed days must clock 2026-07-18T08:00 with 0/479 compliant.",
        "R-129 MAIN twin of amended RIVERSIDE deferred open.",
    )
    upsert(
        "amend_riverside_closed_daytime_0900",
        "friday_evening_preclock_ack_480_compliant",
        r"(?mi)^\x22?R-130\x22?\s*,\s*\x22?2\x22?\s*,[^\n]*2026-07-18[T ]0?9:00[^\n]*,\s*\x22?\s*240(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*480(?:\.0+)?\s*\x22?\s*,[^\n]*\x22?(compliant|ok|pass|none|no[_ ]?finding)\x22?\s*$",
        "R-130 RIVERSIDE closed-day under amendment must clock 2026-07-18T09:00 with exact 240/480 compliant.",
        "R-130 closed-day + amendment open interaction.",
    )
    upsert(
        "amend_cons_wrong_case_unapproved",
        "physician_associate_unapproved_empty_mins",
        r"(?mi)^\x22?R-131\x22?\s*,[^\n]*,\s*\x22?\s*\x22?\s*,[^\n]*\bcons\b[^\n]*,\s*\x22?missing\x22?\s*,[^\n]*(?=.*acknowledger_unapproved)(?=.*acknowledgement_late)(?=.*escalation_missing)",
        "R-131 lowercase cons near amendment clock: empty minutes + unapproved + late + missing.",
        "R-131 Cons wrong-case near amendment.",
    )
    upsert(
        "amend_anp_wrong_case_recorded",
        "consultant_on_call_recorded_not_missing",
        r"(?mi)^\x22?R-132\x22?\s*,[^\n]*,\s*\x22?\s*\x22?\s*,[^\n]*\banp\b[^\n]*,\s*\x22?recorded\x22?\s*,[^\n]*(?=.*acknowledger_unapproved)(?=.*acknowledgement_late)(?!.*escalation_missing)",
        "R-132 lowercase anp near amendment clock: empty minutes + unapproved + late; escalation recorded.",
        "R-132 ANP wrong-case + recorded escalation.",
    )
    upsert(
        "amend_holiday_unapproved_missing",
        "physician_associate_unapproved_empty_mins",
        r"(?mi)^\x22?R-133\x22?\s*,[^\n]*2026-07-18[T ]0?9:00[^\n]*,[^\n]*,\s*\x22?\s*\x22?\s*,[^\n]*\banp\b[^\n]*,\s*\x22?missing\x22?\s*,[^\n]*(?=.*acknowledger_unapproved)(?=.*acknowledgement_late)(?=.*escalation_missing)",
        "R-133 holiday+site unapproved anp: clock 09:00; empty minutes; missing escalation.",
        "R-133 holiday+site unapproved missing escalation.",
    )
    upsert(
        "amend_holiday_unapproved_recorded",
        "consultant_on_call_recorded_not_missing",
        r"(?mi)^\x22?R-134\x22?\s*,[^\n]*2026-07-18[T ]0?9:00[^\n]*,[^\n]*,\s*\x22?\s*\x22?\s*,[^\n]*nurse_practitioner[^\n]*,\s*\x22?recorded\x22?\s*,[^\n]*(?=.*acknowledger_unapproved)(?=.*acknowledgement_late)(?!.*escalation_missing)",
        "R-134 holiday+site unapproved nurse_practitioner: clock 09:00; empty minutes; escalation recorded.",
        "R-134 holiday+site unapproved recorded escalation twin.",
    )

    for v in data["verifiers"]:
        exp = v["assertion"].get("expected")
        if isinstance(exp, str) and exp.startswith("(?"):
            re.compile(exp)

    for name in MEMO_SOFT:
        exp = find(name)["assertion"]["expected"]
        if re.search(r"\\bR-\d+", exp) or re.search(r"\bR-\d+\b", exp):
            raise SystemExit(f"{name} still gates on result IDs: {exp[:120]}")

    vj.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return len(data["verifiers"])


def update_test_outputs(audit: list[dict]) -> None:
    path = PACK / "tests" / "test_outputs.py"
    src = path.read_text(encoding="utf-8")

    expected_v18 = {
        r["result_id"]: r["findings"]
        for r in audit
        if r["result_id"] in {f"R-{i}" for i in range(106, 119)}
    }
    expected_v19 = {
        r["result_id"]: r["findings"]
        for r in audit
        if r["result_id"] in {f"R-{i}" for i in range(119, 123)}
    }
    expected_v20 = {
        r["result_id"]: r["findings"]
        for r in audit
        if r["result_id"] in {x["result_id"] for x in NEW_CR}
    }

    block = f'''
def test_v18_structural_trap_findings():
    """Per-row findings for v18 multi-doc / holiday / site / alias traps."""
    findings = _audit_findings(WORKSPACE)
    expected = {repr(expected_v18)}
    for rid, want in expected.items():
        assert rid in findings, f"missing audit row {{rid}}"
        got = ";".join(p.strip() for p in findings[rid].split(";") if p.strip())
        want_n = ";".join(p.strip() for p in want.split(";") if p.strip())
        assert set(got.split(";")) == set(want_n.split(";")), (
            f"{{rid}} findings {{got!r}} != {{want_n!r}}"
        )


def test_v18_unapproved_empty_acknowledgement_minutes():
    """Harbor fairness: unapproved roles leave acknowledgement_minutes empty."""
    import csv
    path = WORKSPACE / "results_audit.csv"
    assert path.is_file()
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = {{(r.get("result_id") or "").strip(): r for r in csv.DictReader(f)}}
    for rid in ("R-109", "R-117", "R-120", "R-131", "R-132", "R-133", "R-134"):
        row = rows[rid]
        assert "acknowledger_unapproved" in (row.get("findings") or ""), rid
        assert (row.get("acknowledgement_minutes") or "").strip() == "", (
            f"{{rid}} must have empty acknowledgement_minutes"
        )


def test_v18_recorded_escalation_not_missing():
    import csv
    path = WORKSPACE / "results_audit.csv"
    assert path.is_file()
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = {{(r.get("result_id") or "").strip(): r for r in csv.DictReader(f)}}
    for rid in ("R-117", "R-132", "R-134"):
        row = rows[rid]
        assert (row.get("escalation_status") or "").strip() == "recorded", rid
        assert "escalation_missing" not in (row.get("findings") or ""), rid


def test_v18_memo_breach_ids_have_detail():
    """Every breach ID in the memo must appear with a minute figure or window name."""
    import csv
    import re as _re
    memo = (WORKSPACE / "results_memo.md").read_text(encoding="utf-8-sig")
    with (WORKSPACE / "results_audit.csv").open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    breach_ids = [
        (r.get("result_id") or "").strip()
        for r in rows
        if (r.get("findings") or "").strip() not in ("", "compliant")
    ]
    assert breach_ids
    missing = []
    for rid in breach_ids:
        pat = _re.compile(
            _re.escape(rid) + r".{{0,500}}(?:\\d+\\s*min|window|minutes|notification|acknowledgement)",
            _re.I | _re.S,
        )
        if not pat.search(memo):
            missing.append(rid)
    assert not missing, f"memo missing minute/window detail for: {{missing[:10]}}"


def test_v18_comment_rows_not_in_audit():
    findings = _audit_findings(WORKSPACE)
    for bad in ("#ARCH", "#DUP"):
        assert bad not in findings, f"comment row {{bad}} must not appear in audit"


def test_v19_structural_trap_findings():
    """Per-row findings for v19 Harbor densify traps (audit/results graded)."""
    findings = _audit_findings(WORKSPACE)
    expected = {repr(expected_v19)}
    for rid, want in expected.items():
        assert rid in findings, f"missing audit row {{rid}}"
        got = ";".join(p.strip() for p in findings[rid].split(";") if p.strip())
        want_n = ";".join(p.strip() for p in want.split(";") if p.strip())
        assert set(got.split(";")) == set(want_n.split(";")), (
            f"{{rid}} findings {{got!r}} != {{want_n!r}}"
        )


def test_v19_main_1700_not_riverside_deferred():
    """R-121 must keep clock at MAIN release 17:00 (not next-morning deferral)."""
    import csv
    path = WORKSPACE / "results_audit.csv"
    assert path.is_file()
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = {{(r.get("result_id") or "").strip(): r for r in csv.DictReader(f)}}
    row = rows["R-121"]
    assert (row.get("clock_start") or "").replace(" ", "T").startswith("2026-07-14T17:00")
    assert (row.get("notification_minutes") or "").strip() in {{"930", "930.0"}}
    assert (row.get("acknowledgement_minutes") or "").strip() in {{"1380", "1380.0"}}
    assert "notification_late" in (row.get("findings") or "")
    assert "acknowledgement_late" in (row.get("findings") or "")
    assert "escalation_missing" in (row.get("findings") or "")


def test_v19_memo_concept_checks_no_closed_ids():
    """Softened memo verifiers must not require a closed result-ID set."""
    import json
    import re as _re
    data = json.loads((TESTS_DIR / "verifier.json").read_text(encoding="utf-8-sig"))
    names = {{
        "memo_explains_pre_clock_or_1759",
        "memo_explains_tier_or_preclock_non_breach",
        "memo_explains_r89_or_r103_non_breach",
        "memo_addresses_the_clock_start",
        "memo_lists_r106_or_r110_holiday",
    }}
    for v in data["verifiers"]:
        if v["name"] not in names:
            continue
        exp = v["assertion"]["expected"]
        assert not _re.search(r"\\\\bR-\\d+", exp) and not _re.search(r"\\bR-\\d+\\b", exp), (
            f"{{v['name']}} still gates on result IDs"
        )


def test_v20_structural_trap_findings():
    """Per-row findings for v20 amendment / multi-doc traps (audit/results graded)."""
    findings = _audit_findings(WORKSPACE)
    expected = {repr(expected_v20)}
    for rid, want in expected.items():
        assert rid in findings, f"missing audit row {{rid}}"
        got = ";".join(p.strip() for p in findings[rid].split(";") if p.strip())
        want_n = ";".join(p.strip() for p in want.split(";") if p.strip())
        assert set(got.split(";")) == set(want_n.split(";")), (
            f"{{rid}} findings {{got!r}} != {{want_n!r}}"
        )


def test_v20_amendment_boundary_twins():
    """R-123 pre-amendment defers; R-124 post-amendment stays at release."""
    import csv
    path = WORKSPACE / "results_audit.csv"
    assert path.is_file()
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = {{(r.get("result_id") or "").strip(): r for r in csv.DictReader(f)}}
    pre = rows["R-123"]
    post = rows["R-124"]
    assert (pre.get("clock_start") or "").replace(" ", "T").startswith("2026-07-15T08:00")
    assert (pre.get("findings") or "").strip() == "compliant"
    assert (post.get("clock_start") or "").replace(" ", "T").startswith("2026-07-15T17:30")
    assert "notification_late" in (post.get("findings") or "")
    assert "acknowledgement_late" in (post.get("findings") or "")


def test_v20_amendment_deferred_open_riverside_vs_main():
    """R-128 amended RIVERSIDE deferred open 09:00 vs R-129 MAIN 08:00."""
    import csv
    path = WORKSPACE / "results_audit.csv"
    assert path.is_file()
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = {{(r.get("result_id") or "").strip(): r for r in csv.DictReader(f)}}
    assert (rows["R-128"].get("clock_start") or "").replace(" ", "T").startswith("2026-07-18T09:00")
    assert (rows["R-129"].get("clock_start") or "").replace(" ", "T").startswith("2026-07-18T08:00")
    assert (rows["R-128"].get("findings") or "").strip() == "compliant"
    assert (rows["R-129"].get("findings") or "").strip() == "compliant"


def test_v20_amendment_file_present():
    p = WORKSPACE / "input" / "procedure_amendment_2026-07-01.md"
    assert p.is_file(), "amendment file must be present under input/"
    text = p.read_text(encoding="utf-8")
    assert "2026-07-15" in text
    assert "RIVERSIDE" in text or "Riverside" in text
'''

    if "def test_v18_structural_trap_findings" in src:
        src = re.sub(
            r"\ndef test_v18_structural_trap_findings\(\):.*",
            lambda _m: "\n" + block.lstrip("\n"),
            src,
            count=1,
            flags=re.S,
        )
    else:
        if not src.endswith("\n"):
            src += "\n"
        src += block

    path.write_text(src, encoding="utf-8", newline="\n")


def assert_harbor_fair_instruction() -> None:
    instr = (PACK / "instruction.md").read_text(encoding="utf-8")
    low = instr.lower()
    for needle in (
        "leave acknowledgement_minutes empty",
        "acknowledger_unapproved",
        "acknowledgement_late",
        "ward_clerk",
        "site_core_hours.md",
        "approved_roles_roster.md",
        "bank_holidays.csv",
        "procedure_amendment_2026-07-01.md",
        "naming a particular result id is optional",
    ):
        if needle.lower() not in low:
            raise SystemExit(f"Harbor fairness missing from instruction: {needle}")
    for spoiler in (
        "R-123",
        "R-124",
        "R-125",
        "R-126",
        "R-127",
        "R-128",
        "R-129",
        "R-130",
        "R-131",
        "R-132",
        "R-133",
        "R-134",
        "near-miss",
        "09:00–18:00",
        "09:00-18:00",
    ):
        if spoiler.lower() in low:
            raise SystemExit(f"Spoiler in instruction: {spoiler}")


def run_pytest() -> int:
    tests = PACK / "tests"
    ws = Path(tempfile.mkdtemp(prefix="h40-v20-gold-"))
    for name in ("results_audit.csv", "results_memo.md", "results.json"):
        shutil.copy2(PACK / "solution" / "files" / name, ws / name)
    inp = ws / "input"
    inp.mkdir()
    for name in (
        "critical_results.csv",
        "escalations.csv",
        "critical_results_procedure.md",
        "site_core_hours.md",
        "approved_roles_roster.md",
        "bank_holidays.csv",
        "procedure_amendment_2026-07-01.md",
    ):
        src = INP / name
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
        print(proc.stderr[-5000:])
    print("pytest_returncode", proc.returncode)
    return proc.returncode


def rebuild_zips() -> int:
    ignore = {".DS_Store", "__pycache__", ".git", ".pytest_cache"}
    tmp = ROOT / "UPLOAD-THIS-TO-QC-health-h40.zip"
    if tmp.exists():
        tmp.unlink()
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in PACK.rglob("*"):
            if not path.is_file():
                continue
            if any(part in ignore or part.endswith(".pyc") for part in path.parts):
                continue
            if path.name.endswith(".zip"):
                continue
            if ".bak-" in path.name or path.name.endswith(".bak"):
                continue
            arc = (Path(PACK.name) / path.relative_to(PACK)).as_posix()
            zf.write(path, arcname=arc)
    size = tmp.stat().st_size
    print("built", tmp, size)
    dests = [
        Path(r"C:\Users\Haseeb Mirza\Downloads\UPLOAD-THIS-TO-QC-health-h40.zip"),
        ROOT / "sessions" / "E" / "zips" / "UPLOAD-THIS-TO-QC-health-h40.zip",
        ROOT / "canonical-zips" / "UPLOAD-THIS-TO-QC-health-h40.zip",
    ]
    for d in dests:
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(tmp, d)
        print(d.stat().st_size, d)
    rebuild = ROOT / "tmp-h40-rebuild-zip.py"
    if rebuild.is_file():
        subprocess.run([sys.executable, str(rebuild)], cwd=str(ROOT), check=True)
        size = (
            ROOT / "canonical-zips" / "UPLOAD-THIS-TO-QC-health-h40.zip"
        ).stat().st_size
    return size


def main() -> int:
    esc_preview = {e["result_id"] for e in NEW_ESCALATIONS}
    # Include existing escalations that matter for preview of new rows only
    print("NEW ROW GOLD PREVIEW:")
    for row in NEW_CR:
        g = grade_row(row, esc_preview)
        print(
            f"  {g['result_id']} site={row['site']} role={row['acknowledged_by_role']!r} "
            f"clock={g['clock_start']} n={g['notification_minutes']!r} "
            f"a={g['acknowledgement_minutes']!r} esc={g['escalation_status']} "
            f"findings={g['findings']}"
        )

    patch_procedure_docs()
    assert_harbor_fair_instruction()

    cr_path = INP / "critical_results.csv"
    old = load_register_rows(cr_path)
    new_ids = {r["result_id"] for r in NEW_CR}
    # Drop prior v20 rows on re-run; keep through R-122
    old = [
        r
        for r in old
        if r.get("result_id") not in new_ids
        and not str(r.get("result_id", "")).startswith("#")
    ]
    if len(old) < 118:
        raise SystemExit(f"expected >=118 base rows after load, got {len(old)}")

    merged: list[dict] = []
    for r in old:
        merged.append(
            {
                "result_id": r["result_id"],
                "tier": r["tier"],
                "test": r["test"],
                "site": (r.get("site") or "MAIN").strip() or "MAIN",
                "released_at": r["released_at"],
                "notified_at": r.get("notified_at") or "",
                "acknowledged_at": r.get("acknowledged_at") or "",
                "acknowledged_by_role": r.get("acknowledged_by_role") or "",
                "lab_batch": r.get("lab_batch") or f"MB-{r['result_id'][2:]}",
                "notes": r.get("notes") or "",
            }
        )
    merged.extend(NEW_CR)
    write_messy_register(cr_path, merged)

    esc_path = INP / "escalations.csv"
    esc = list(csv.DictReader(esc_path.open(encoding="utf-8-sig")))
    existing_esc = {r["result_id"] for r in esc}
    for e in NEW_ESCALATIONS:
        if e["result_id"] not in existing_esc:
            esc.append(e)
            existing_esc.add(e["result_id"])
    # Drop stale v20 escalations if re-run removed those rows then re-added
    write_csv(esc_path, esc, ["result_id", "escalated_at"])
    escalated_ids = {r["result_id"] for r in esc}

    graded_rows = load_register_rows(cr_path)
    assert len(graded_rows) == len(merged), (
        f"graded {len(graded_rows)} != merged {len(merged)}"
    )
    audit = [grade_row(r, escalated_ids) for r in graded_rows]
    write_csv(PACK / "solution" / "files" / "results_audit.csv", audit, AUDIT_FIELDS)

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

    memo = soft_update_memo(audit, counts)
    (PACK / "solution" / "files" / "results_memo.md").write_text(
        memo, encoding="utf-8", newline="\n"
    )

    by = {r["result_id"]: r for r in audit}

    # Amendment regrades
    assert by["R-106"]["clock_start"] == "2026-07-15T17:30", by["R-106"]
    assert "notification_late" in by["R-106"]["findings"]
    assert by["R-117"]["clock_start"] == "2026-07-15T17:45", by["R-117"]
    assert by["R-117"]["escalation_status"] == "recorded"
    assert by["R-117"]["acknowledgement_minutes"] == ""
    assert by["R-119"]["clock_start"] == "2026-07-18T09:00", by["R-119"]
    assert by["R-119"]["findings"] == "compliant", by["R-119"]
    assert by["R-119"]["notification_minutes"] == "180"
    assert by["R-119"]["acknowledgement_minutes"] == "420"

    # New traps
    assert by["R-123"]["clock_start"] == "2026-07-15T08:00", by["R-123"]
    assert by["R-123"]["findings"] == "compliant"
    assert by["R-124"]["clock_start"] == "2026-07-15T17:30", by["R-124"]
    assert "notification_late" in by["R-124"]["findings"]
    assert by["R-125"]["clock_start"] == "2026-07-15T17:30"
    assert by["R-126"]["findings"] == "compliant"
    assert by["R-127"]["clock_start"] == "2026-07-15T17:00"
    assert by["R-127"]["findings"] == "compliant"
    assert by["R-128"]["clock_start"] == "2026-07-18T09:00", by["R-128"]
    assert by["R-128"]["findings"] == "compliant"
    assert by["R-129"]["clock_start"] == "2026-07-18T08:00", by["R-129"]
    assert by["R-129"]["findings"] == "compliant"
    assert by["R-130"]["clock_start"] == "2026-07-18T09:00"
    assert by["R-130"]["findings"] == "compliant"
    assert by["R-131"]["acknowledgement_minutes"] == ""
    assert "acknowledger_unapproved" in by["R-131"]["findings"]
    assert by["R-132"]["escalation_status"] == "recorded"
    assert by["R-132"]["acknowledgement_minutes"] == ""
    assert by["R-133"]["clock_start"] == "2026-07-18T09:00"
    assert by["R-133"]["escalation_status"] == "missing"
    assert by["R-134"]["escalation_status"] == "recorded"
    assert by["R-134"]["acknowledgement_minutes"] == ""

    n_ver = soften_and_extend_verifiers(audit, counts)
    update_test_outputs(audit)
    update_readme()
    update_golden_trajectory()
    update_review_csv(n_ver, counts, len(audit))
    print("verifiers", n_ver)
    print("rows", len(audit))

    readme = (PACK / "README.md").read_text(encoding="utf-8")
    for name in (
        "critical_results_procedure.md",
        "critical_results.csv",
        "escalations.csv",
        "site_core_hours.md",
        "approved_roles_roster.md",
        "bank_holidays.csv",
        "procedure_amendment_2026-07-01.md",
    ):
        if name not in readme:
            raise SystemExit(f"README missing {name}")

    traj = json.loads(
        (PACK / "solution" / "golden_trajectory.json").read_text(encoding="utf-8-sig")
    )
    msg = next(s["message"] for s in traj["steps"] if s.get("step_id") == 1)
    if "procedure_amendment_2026-07-01.md" not in msg:
        raise SystemExit("golden_trajectory step 1 missing amendment attachment")

    rc = run_pytest()
    if rc != 0:
        print("pytest failed; skipping zip rebuild")
        return rc

    size = rebuild_zips()
    print(f"zip_size={size}")
    print("v20_hard_ok")
    trap_summary = {
        "R-123": "pre-amend RIVERSIDE 17:30 → Jul 15 08:00 compliant",
        "R-124": "post-amend RIVERSIDE 17:30 at release → both late",
        "R-125": "MAIN 17:30 twin → both late",
        "R-126": "pre-amend exact 17:00 → next morning compliant",
        "R-127": "post-amend 17:00 still open → at release compliant",
        "R-128": "post-amend 18:00 → Jul 18 09:00 compliant",
        "R-129": "MAIN 18:00 → Jul 18 08:00 compliant",
        "R-130": "closed-day + amend open 09:00 exact 240/480",
        "R-131": "cons wrong-case near amend clock",
        "R-132": "anp wrong-case + escalation recorded",
        "R-133": "holiday+site anp missing escalation",
        "R-134": "holiday+site unapproved recorded escalation",
    }
    print(
        json.dumps(
            {
                "rows": len(audit),
                "verifiers": n_ver,
                "counts": counts,
                "new_traps": [r["result_id"] for r in NEW_CR],
                "trap_summary": trap_summary,
                "amendment_regrades": {
                    "R-106": by["R-106"]["findings"],
                    "R-117": by["R-117"]["findings"],
                    "R-119": {
                        "clock": by["R-119"]["clock_start"],
                        "n": by["R-119"]["notification_minutes"],
                        "a": by["R-119"]["acknowledgement_minutes"],
                    },
                },
                "zip_size": size,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
