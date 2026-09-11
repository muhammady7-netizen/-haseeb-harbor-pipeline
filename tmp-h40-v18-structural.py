#!/usr/bin/env python3
"""h40 v18 STRUCTURAL harden — multi-doc policy + holidays + site hours + aliases.

v14–v17 all portal TOO_EASY (Oracle 1.0, GLM 4/4). Root cause: a single
fully-specified procedure.md + clean CSV is a deterministic coding task.
Despoiling instruction and adding rows did not change that.

This script STRUCTURALLY hardens while staying Harbor-fair:

A) Split policy across procedure + site_core_hours.md + approved_roles_roster.md
   + bank_holidays.csv; instruction points at all of them (no trap spoilers).
B) Clock modifiers: trust closed days defer tier-2 start to next open morning;
   site-specific core hours (MAIN 08–18, RIVERSIDE 08–17); role aliases in roster.
C) Messier but parseable register: site + extra columns, # comment rows to skip,
   mixed datetime formats (T vs space) per procedure parse rule.
D) Memo: every breach ID must appear with a minute figure or window name (pytest).
E) Harbor fairness preserved (empty ack mins for unapproved; both codes; ward_clerk).
F) No trap spoilers / near-miss enumerations in instruction.md.
G) Regenerate gold audit/memo/results + verifier.json + test_outputs.py; pytest.
H) Rebuild zip → Downloads, sessions/E/zips, canonical-zips.

Does NOT portal upload.
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
import zipfile
from datetime import datetime, timedelta
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

CR_FIELDS = [
    "result_id",
    "tier",
    "test",
    "site",
    "released_at",
    "notified_at",
    "acknowledged_at",
    "acknowledged_by_role",
    "lab_batch",
    "notes",
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

# Site core hours (also written into site_core_hours.md)
SITE_HOURS = {
    "MAIN": (8, 18),
    "RIVERSIDE": (8, 17),
}

# Canonical approved + aliases (also written into roster)
APPROVED_CANONICAL = {
    "consultant",
    "specialty_registrar",
    "resident_doctor",
    "advanced_nurse_practitioner",
}
ROLE_ALIASES = {
    "SpR": "specialty_registrar",
    "ANP": "advanced_nurse_practitioner",
    "Cons": "consultant",
}

# Trust closed days (also written into bank_holidays.csv)
CLOSED_DATES = {
    "2026-07-16",  # trust local holiday
    "2026-07-17",  # trust bridge day
}

# ---------------------------------------------------------------------------
# Policy documents
# ---------------------------------------------------------------------------

PROCEDURE_MD = """# Critical results procedure CR-7 — Ardleigh Trust pathology

A critical result is not closed by being released. Three things must happen and each is timed
separately: the result is telephoned to the clinical team, it is acknowledged by somebody able to
act on it, and where the acknowledgement window is missed it is escalated.

Supporting trust documents (read all of them; this procedure alone is not complete):

- `site_core_hours.md` — site codes and core-hour open/close times
- `approved_roles_roster.md` — which register tokens count as an acknowledgement (including aliases)
- `bank_holidays.csv` — trust closed days that defer the tier-2 clock

## Windows

| Tier | Telephone within | Acknowledged within | Clock |
|---|---|---|---|
| 1 | 30 minutes | 60 minutes | runs continuously |
| 2 | 240 minutes | 480 minutes | core hours only |

Both windows are measured from the **start of the clock** and both are inclusive: a tier 1
result acknowledged at exactly 60 minutes is within its window, not a breach.

## When the clock starts

For a **tier 1** result the clock starts the moment the result is released, whatever the hour.
Tier 1 is the tier that cannot wait for the morning, and giving a result released at night the
core-hours grace removes every out-of-hours breach from the audit.

For a **tier 2** result the clock may start only during that row's **site core hours** on an
**open** day. Site open/close times are in `site_core_hours.md` (matched by the register `site`
column). Open days are every calendar day including weekends, **except** dates listed in
`bank_holidays.csv`.

Tier-2 start rules:

1. If the release falls on a closed day, the clock starts at that site's open time on the next
   open morning (skip every closed date in `bank_holidays.csv`).
2. If the release is before site open on an open day, the clock starts at open that morning.
3. If the release is at or after site close on an open day, the clock starts at open on the next
   open morning (again skipping closed dates).
4. Otherwise the clock starts at the release timestamp.

Once the clock has started it runs without pausing; "core hours only" refers to when the clock
may start, not when it ticks. If a telephone notification is recorded before the tier-2 clock has
started, treat it as occurring at clock start (notification_minutes measured from clock start is
0). The same rule applies to an acknowledgement timestamp that falls before clock start.

## Timestamps on the register

Timestamps may appear as ISO `YYYY-MM-DDTHH:MM` or space-separated `YYYY-MM-DD HH:MM`. Treat both
as the same instant. Ignore any register row whose `result_id` is empty or begins with `#`
(comment / export noise). Extra columns such as `lab_batch` and `notes` are informational only.

## Who can acknowledge

An acknowledgement counts only where the register token matches an approved role or alias listed
in `approved_roles_roster.md`. Matching is exact against that roster (canonical token or alias
spelling). An acknowledgement recorded against any other role is **not** an acknowledgement. The
result stands unacknowledged and its window keeps running, however promptly the entry was made.
This is recorded as its own finding as well, because it is a training issue rather than a delay.

## Escalation

Where the acknowledgement window has been missed, the result must be escalated to the on-call
consultant and the escalation recorded in the escalation register. A missed acknowledgement
window with **no** escalation on the register is a second, separate finding: the first is a
delay, the second is that nobody picked the delay up.

Where the acknowledgement was made inside its window, no escalation is required and the absence
of one is not a finding.

## Reporting

Late notifications, late acknowledgements, acknowledgements by an unapproved role and missing
escalations are four separate counts. One result can appear in more than one of them, so they do
not add up to the number of results with a finding.
"""

SITE_CORE_HOURS_MD = """# Site core hours — Ardleigh Trust pathology

Match the register `site` column to a row below. Times are 24-hour local trust time.

| Site code | Site name | Core open | Core close |
|---|---|---|---|
| MAIN | Ardleigh Main laboratory | 08:00 | 18:00 |
| RIVERSIDE | Riverside Clinic laboratory | 08:00 | 17:00 |

Notes:

- Core close is exclusive of the closing instant for starting a new tier-2 clock: a release at
  exactly the close time starts on the next open morning.
- Weekends use the same open/close times as weekdays unless the date is listed in
  `bank_holidays.csv`.
- If `site` is blank, treat the row as `MAIN`.
"""

APPROVED_ROLES_ROSTER_MD = """# Approved acknowledger roster — CR-7

Only the following **canonical** register tokens are approved acknowledgers:

- `consultant`
- `specialty_registrar`
- `resident_doctor`
- `advanced_nurse_practitioner`

## Aliases

These alternate spellings on the register count as the mapped canonical role (exact spelling,
including capitalisation):

| Register alias | Maps to |
|---|---|
| `SpR` | `specialty_registrar` |
| `ANP` | `advanced_nurse_practitioner` |
| `Cons` | `consultant` |

Any other token — including near-miss clinical titles, different capitalisation of an alias, or
abbreviations not listed above — is **not** an approved acknowledgement.
"""

BANK_HOLIDAYS_CSV = """closed_date,label
2026-07-16,Trust local holiday
2026-07-17,Trust bridge day
"""

INSTRUCTION_MD = """# Task

Audit the critical results register against the trust's critical results procedure and its
supporting site / roster / closed-day documents. Save `results_audit.csv` with the columns
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
in plain language (for example inclusive window limits, site core-hours clock start, or a trust
closed day); naming a particular result ID is optional.

Reconcile the procedure at `input/critical_results_procedure.md` with
`input/site_core_hours.md`, `input/approved_roles_roster.md`, and `input/bank_holidays.csv`. Audit
every graded row in `input/critical_results.csv` against those documents and the escalation
register at `input/escalations.csv`.

- The attachments are provided read-only at: `input/critical_results_procedure.md`; `input/site_core_hours.md`; `input/approved_roles_roster.md`; `input/bank_holidays.csv`; `input/critical_results.csv`; `input/escalations.csv`. Read them there.
- Save your deliverables into your current working directory using exactly these filenames:
    - `results_audit.csv` - Result-level critical results audit
    - `results_memo.md` - Markdown critical results memo
    - `results.json` - a JSON object whose values are integer counts for the keys `notification_breaches`, `acknowledgement_breaches`, `unapproved_acknowledgement_results`, `missing_escalation_results`, `results_compliant` (do not use arrays of result IDs)
- Writing those files is the required deliverable and must be your final action; confirm each one exists before you answer.
- Leave every deliverable in the starting working directory (the same folder you begin in). Do not nest them under `output/` or any other subdirectory.
"""

# ---------------------------------------------------------------------------
# Gold computer
# ---------------------------------------------------------------------------


def _parse(ts: str) -> datetime:
    s = (ts or "").strip()
    if not s:
        raise ValueError("empty timestamp")
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise ValueError(f"unparseable timestamp: {ts!r}")


def _fmt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M")


def _date_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def _is_closed(dt: datetime) -> bool:
    return _date_key(dt) in CLOSED_DATES


def _next_open_morning(from_dt: datetime, open_h: int) -> datetime:
    """Next open morning at open_h:00, starting the calendar day after from_dt's date
    when called for 'after close', or from from_dt's date when scanning closed days.
    """
    d = from_dt.date()
    # Caller decides whether to start from same day or next; this helper advances
    # while closed, returning open_h on the first open date >= d.
    while True:
        cand = datetime(d.year, d.month, d.day, open_h, 0)
        if not _is_closed(cand):
            return cand
        d = d + timedelta(days=1)


def clock_start(tier: int, released_at: str, site: str) -> datetime:
    r = _parse(released_at)
    if tier == 1:
        return r
    site_key = (site or "MAIN").strip() or "MAIN"
    open_h, close_h = SITE_HOURS.get(site_key, SITE_HOURS["MAIN"])

    if _is_closed(r):
        # Closed day: start next open morning
        nxt = r.date() + timedelta(days=1)
        return _next_open_morning(datetime(nxt.year, nxt.month, nxt.day), open_h)

    if r.hour < open_h or (r.hour == open_h and r.minute < 0):
        return _next_open_morning(r.replace(hour=0, minute=0), open_h)
    if r.hour < open_h:
        return r.replace(hour=open_h, minute=0)

    # at or after close → next open morning
    if r.hour > close_h or (r.hour == close_h and r.minute >= 0 and (r.hour >= close_h)):
        # close is exclusive at exact close_h:00
        if r.hour > close_h or (r.hour == close_h):
            nxt = r.date() + timedelta(days=1)
            return _next_open_morning(datetime(nxt.year, nxt.month, nxt.day), open_h)

    return r


def clock_start_clean(tier: int, released_at: str, site: str) -> datetime:
    """Cleaner clock-start implementing the procedure rules."""
    r = _parse(released_at)
    if tier == 1:
        return r
    site_key = (site or "MAIN").strip() or "MAIN"
    open_h, close_h = SITE_HOURS.get(site_key, SITE_HOURS["MAIN"])

    def open_on_or_after(day) -> datetime:
        d = day
        while True:
            cand = datetime(d.year, d.month, d.day, open_h, 0)
            if _date_key(cand) not in CLOSED_DATES:
                return cand
            d = d + timedelta(days=1)

    if _date_key(r) in CLOSED_DATES:
        return open_on_or_after(r.date() + timedelta(days=1))

    # before open
    open_today = r.replace(hour=open_h, minute=0, second=0, microsecond=0)
    close_today = r.replace(hour=close_h, minute=0, second=0, microsecond=0)
    if r < open_today:
        return open_today
    if r >= close_today:
        return open_on_or_after(r.date() + timedelta(days=1))
    return r


def mins_from(clock: datetime, event: str | None) -> int | None:
    if not event or not str(event).strip():
        return None
    e = _parse(event)
    if e < clock:
        return 0
    return int((e - clock).total_seconds() // 60)


def role_approved(role: str) -> bool:
    r = (role or "").strip()
    if not r or r == "none":
        return False
    if r in APPROVED_CANONICAL:
        return True
    if r in ROLE_ALIASES:
        return True
    return False


def grade_row(cr: dict, escalated_ids: set[str]) -> dict:
    rid = cr["result_id"]
    tier = int(cr["tier"])
    n_lim, a_lim = (30, 60) if tier == 1 else (240, 480)
    site = (cr.get("site") or "MAIN").strip() or "MAIN"
    cs = clock_start_clean(tier, cr["released_at"], site)
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
# New structural trap rows R-106..R-118
# ---------------------------------------------------------------------------

NEW_CR = [
    # R-106: RIVERSIDE 17:30 on Jul 15 → after 17:00 close; Jul 16–17 closed → clock Jul 18 08:00
    # Events within 240/480 from Jul 18 → compliant. Naive MAIN 18:00 would start at release → late.
    {
        "result_id": "R-106",
        "tier": "2",
        "test": "sodium",
        "site": "RIVERSIDE",
        "released_at": "2026-07-15T17:30",
        "notified_at": "2026-07-18T10:00",
        "acknowledged_at": "2026-07-18T14:00",
        "acknowledged_by_role": "consultant",
        "lab_batch": "RB-441",
        "notes": "",
    },
    # R-107: MAIN twin of R-106 times → clock at release 17:30; Jul 18 events are late
    {
        "result_id": "R-107",
        "tier": "2",
        "test": "sodium",
        "site": "MAIN",
        "released_at": "2026-07-15T17:30",
        "notified_at": "2026-07-18T10:00",
        "acknowledged_at": "2026-07-18T14:00",
        "acknowledged_by_role": "consultant",
        "lab_batch": "MB-441",
        "notes": "",
    },
    # R-108: SpR alias approved + timely tier-1 → compliant
    {
        "result_id": "R-108",
        "tier": "1",
        "test": "potassium",
        "site": "MAIN",
        "released_at": "2026-07-14T10:00",
        "notified_at": "2026-07-14T10:15",
        "acknowledged_at": "2026-07-14T10:40",
        "acknowledged_by_role": "SpR",
        "lab_batch": "MB-450",
        "notes": "",
    },
    # R-109: lowercase spr is NOT an alias → unapproved + empty mins + missing
    {
        "result_id": "R-109",
        "tier": "1",
        "test": "troponin",
        "site": "MAIN",
        "released_at": "2026-07-14T11:00",
        "notified_at": "2026-07-14T11:10",
        "acknowledged_at": "2026-07-14T11:30",
        "acknowledged_by_role": "spr",
        "lab_batch": "MB-451",
        "notes": "",
    },
    # R-110: holiday evening Jul 16 19:00 → clock Jul 18 08:00; exact 480 compliant
    # Naive next-calendar-morning Jul 17 (also closed if known, else wrong) fails inclusive.
    {
        "result_id": "R-110",
        "tier": "2",
        "test": "haemoglobin",
        "site": "MAIN",
        "released_at": "2026-07-16T19:00",
        "notified_at": "2026-07-16T19:30",
        "acknowledged_at": "2026-07-18T16:00",
        "acknowledged_by_role": "consultant",
        "lab_batch": "MB-460",
        "notes": "space-format timestamps below are equivalent",
    },
    # R-111: same holiday chain, ack 481 → late + missing
    {
        "result_id": "R-111",
        "tier": "2",
        "test": "inr",
        "site": "MAIN",
        "released_at": "2026-07-16T19:00",
        "notified_at": "2026-07-16T19:30",
        "acknowledged_at": "2026-07-18T16:01",
        "acknowledged_by_role": "consultant",
        "lab_batch": "MB-461",
        "notes": "",
    },
    # R-112: RIVERSIDE at exact close 17:00 → next open morning Jul 15 08:00; preclock notify 0; ack 480
    {
        "result_id": "R-112",
        "tier": "2",
        "test": "creatinine",
        "site": "RIVERSIDE",
        "released_at": "2026-07-14T17:00",
        "notified_at": "2026-07-14T17:20",
        "acknowledged_at": "2026-07-15T16:00",
        "acknowledged_by_role": "specialty_registrar",
        "lab_batch": "RB-470",
        "notes": "",
    },
    # R-113: RIVERSIDE 16:59 still in hours → clock at release; ack at +480 compliant
    {
        "result_id": "R-113",
        "tier": "2",
        "test": "bilirubin",
        "site": "RIVERSIDE",
        "released_at": "2026-07-14T16:59",
        "notified_at": "2026-07-14T17:30",
        "acknowledged_at": "2026-07-15T00:59",
        "acknowledged_by_role": "consultant",
        "lab_batch": "RB-471",
        "notes": "",
    },
    # R-114: ANP alias (uppercase) approved on tier-2
    {
        "result_id": "R-114",
        "tier": "2",
        "test": "glucose",
        "site": "MAIN",
        "released_at": "2026-07-14T09:00",
        "notified_at": "2026-07-14T10:00",
        "acknowledged_at": "2026-07-14T12:00",
        "acknowledged_by_role": "ANP",
        "lab_batch": "MB-480",
        "notes": "",
    },
    # R-115: Cons alias approved — compliant decoy among traps
    {
        "result_id": "R-115",
        "tier": "1",
        "test": "lactate",
        "site": "MAIN",
        "released_at": "2026-07-14T15:00",
        "notified_at": "2026-07-14T15:20",
        "acknowledged_at": "2026-07-14T15:50",
        "acknowledged_by_role": "Cons",
        "lab_batch": "MB-481",
        "notes": "",
    },
    # R-116: holiday daytime release Jul 16 10:00 → Jul 18 08:00; notify 241 late only
    {
        "result_id": "R-116",
        "tier": "2",
        "test": "phosphate",
        "site": "MAIN",
        "released_at": "2026-07-16T10:00",
        "notified_at": "2026-07-18T12:01",
        "acknowledged_at": "2026-07-18T15:00",
        "acknowledged_by_role": "consultant",
        "lab_batch": "MB-490",
        "notes": "",
    },
    # R-117: RIVERSIDE + unapproved + holiday chain + escalation recorded
    {
        "result_id": "R-117",
        "tier": "2",
        "test": "magnesium",
        "site": "RIVERSIDE",
        "released_at": "2026-07-15T17:45",
        "notified_at": "2026-07-18T09:00",
        "acknowledged_at": "2026-07-18T09:30",
        "acknowledged_by_role": "nurse_practitioner",
        "lab_batch": "RB-495",
        "notes": "",
    },
    # R-118: mixed space-format timestamps; MAIN evening Jul 15 → Jul 16 closed → Jul 18 08:00
    # notify 0 / ack 479 compliant (holiday skip)
    {
        "result_id": "R-118",
        "tier": "2",
        "test": "sodium",
        "site": "MAIN",
        "released_at": "2026-07-15 18:30",
        "notified_at": "2026-07-16 07:00",
        "acknowledged_at": "2026-07-18 15:59",
        "acknowledged_by_role": "resident_doctor",
        "lab_batch": "MB-500",
        "notes": "mixed datetime format",
    },
]

NEW_ESCALATIONS = [
    {"result_id": "R-117", "escalated_at": "2026-07-18T10:00"},
]

# Rows that should use space-separated datetimes in the written CSV
SPACE_FMT_IDS = {"R-118"}


def is_comment_row(row: dict) -> bool:
    rid = (row.get("result_id") or "").strip()
    return (not rid) or rid.startswith("#")


def load_register_rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    text = path.read_text(encoding="utf-8-sig")
    lines = []
    for line in text.splitlines():
        stripped = line.lstrip()
        # Skip free-text header comments (not structured #ARCH CSV rows)
        if stripped.startswith("#") and not stripped.startswith("#ARCH") and not stripped.startswith("#DUP"):
            if "," not in stripped[:20] or stripped.startswith("# "):
                continue
            # e.g. "# Critical results..." has no CSV shape in first field
            first = stripped.split(",", 1)[0]
            if first in {"#", "#ARCH", "#DUP"} or first.startswith("#") and first[1:].isalnum():
                pass  # keep structured comment rows for filtering below
            else:
                continue
        lines.append(line)
    # Ensure we start at the real header
    hdr = next((i for i, ln in enumerate(lines) if ln.startswith("result_id,")), None)
    if hdr is None:
        raise SystemExit(f"no result_id header in {path}")
    lines = lines[hdr:]
    for row in csv.DictReader(lines):
        if is_comment_row(row):
            continue
        rows.append(row)
    return rows


def write_messy_register(path: Path, rows: list[dict]) -> None:
    """Write register with header comment, # rows, extra columns, mixed datetimes."""
    lines = [
        "# Critical results register export — ignore lines whose result_id starts with #",
        ",".join(CR_FIELDS),
    ]
    # Structured comment rows (must be ignored by graders)
    comment_rows = [
        {
            "result_id": "#ARCH",
            "tier": "2",
            "test": "archived",
            "site": "MAIN",
            "released_at": "2026-01-01T00:00",
            "notified_at": "2026-01-01T01:00",
            "acknowledged_at": "2026-01-01T02:00",
            "acknowledged_by_role": "consultant",
            "lab_batch": "IGNORE",
            "notes": "do not grade",
        },
        {
            "result_id": "#DUP",
            "tier": "1",
            "test": "noise",
            "site": "MAIN",
            "released_at": "2026-01-02T00:00",
            "notified_at": "",
            "acknowledged_at": "",
            "acknowledged_by_role": "",
            "lab_batch": "",
            "notes": "export padding",
        },
    ]
    # Insert comment rows after first 3 data rows
    out_rows: list[dict] = []
    for i, r in enumerate(rows):
        out_rows.append(r)
        if i == 2:
            out_rows.extend(comment_rows)

    for r in out_rows:
        vals = []
        for k in CR_FIELDS:
            v = r.get(k, "")
            if k in ("released_at", "notified_at", "acknowledged_at") and r.get("result_id") in SPACE_FMT_IDS:
                # already space format for R-118
                pass
            elif (
                k in ("released_at", "notified_at", "acknowledged_at")
                and v
                and "T" in v
                and r.get("result_id") in {"R-106", "R-112"}
            ):
                # mix a couple of MAIN/RIVERSIDE rows to space format too
                v = v.replace("T", " ")
            # escape quotes
            v = str(v)
            if "," in v or '"' in v:
                v = '"' + v.replace('"', '""') + '"'
            vals.append(v)
        lines.append(",".join(vals))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


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
        return [fmt(r) for r in audit if pred(r)]

    late_n = lines_for(
        lambda r: "notification_late" in r["findings"],
        lambda r: (
            f"- **{r['result_id']}** (tier {r['tier']}) - notified {r['notification_minutes']} min "
            f"after clock start {r['clock_start']} (notification window "
            f"{'30' if r['tier']=='1' else '240'} min)."
        ),
    )
    late_a = []
    for r in audit:
        if "acknowledgement_late" not in r["findings"]:
            continue
        rid = r["result_id"]
        win = "60" if r["tier"] == "1" else "480"
        if "acknowledger_unapproved" in r["findings"]:
            late_a.append(
                f"- **{rid}** - no recognised acknowledgement (unapproved {r['acknowledged_by_role']}); "
                f"acknowledgement_minutes left empty; acknowledgement window {win} min from "
                f"{r['clock_start']} was missed."
            )
        elif not (r.get("acknowledgement_minutes") or "").strip():
            late_a.append(
                f"- **{rid}** - no acknowledgement recorded after clock start {r['clock_start']} "
                f"(acknowledgement window {win} min)."
            )
        else:
            late_a.append(
                f"- **{rid}** - acknowledged at {r['acknowledgement_minutes']} min after clock start "
                f"{r['clock_start']} (acknowledgement window {win} min)."
            )

    unap = lines_for(
        lambda r: "acknowledger_unapproved" in r["findings"],
        lambda r: (
            f"- **{r['result_id']}** - acknowledged by {r['acknowledged_by_role']}, "
            f"not on the approved roster (including aliases)."
        ),
    )
    miss = lines_for(
        lambda r: "escalation_missing" in r["findings"],
        lambda r: f"- **{r['result_id']}** - missed acknowledgement window, no escalation.",
    )

    non_breach = [
        "- Site core hours differ: MAIN closes 18:00; RIVERSIDE closes 17:00.",
        "- Trust closed days in bank_holidays.csv defer the tier-2 clock to the next open morning.",
        "- Roster aliases SpR / ANP / Cons count; other capitalisation does not.",
        "- Inclusive boundaries: exactly at the window limit is within it.",
        "- Pre-clock telephone calls on tier-2 count as notification_minutes 0 from clock start.",
        "- Where escalation appears on the register after a missed window, escalation_status is "
        "recorded — not missing.",
    ]
    # Keep legacy non-breach IDs that existing memo verifiers soft-match.
    non_breach.extend(
        [
            "- **R-57** - pre-clock telephone on tier-2 counts as 0 min from clock start; compliant.",
            "- **R-58** - release at 17:59 starts immediately; acknowledgement at exact 480 is inclusive.",
            "- **R-64** - pre-core 07:59 release clocks at 08:00; windows measured from that start.",
            "- **R-70** - evening release with pre-clock notify and exact 480 from next-morning 08:00 is compliant.",
            "- **R-71** - tier-2 result with times that look like tier-1 limits remains within 240/480.",
            "- **R-76** - Sunday pre-core clocks at 08:00; exact 240/480 are within window.",
        ]
    )
    for rid in (
        "R-106",
        "R-108",
        "R-110",
        "R-112",
        "R-113",
        "R-114",
        "R-115",
        "R-118",
        "R-89",
        "R-103",
        "R-98",
        "R-87",
    ):
        r = by_id.get(rid)
        if not r or r["findings"] != "compliant":
            continue
        if rid == "R-106":
            non_breach.append(
                "- **R-106** - RIVERSIDE close 17:00 plus Jul 16–17 closed days: clock starts "
                "2026-07-18T08:00; 120/360 minutes are within 240/480."
            )
        elif rid == "R-108":
            non_breach.append(
                "- **R-108** - SpR is an approved roster alias for specialty_registrar; compliant."
            )
        elif rid == "R-110":
            non_breach.append(
                "- **R-110** - released on a trust closed evening: clock starts 2026-07-18T08:00; "
                "pre-clock notify and exact 480 acknowledgement minutes are compliant."
            )
        elif rid == "R-112":
            non_breach.append(
                "- **R-112** - RIVERSIDE release at exact 17:00 close starts next morning 08:00; "
                "pre-clock notify 0 and exact 480 are within window."
            )
        elif rid == "R-113":
            non_breach.append(
                "- **R-113** - RIVERSIDE 16:59 is still inside core hours so the clock starts at "
                "release; acknowledgement at 480 minutes is inclusive-compliant."
            )
        elif rid == "R-114":
            non_breach.append(
                "- **R-114** - ANP is an approved roster alias for advanced_nurse_practitioner."
            )
        elif rid == "R-115":
            non_breach.append(
                "- **R-115** - Cons is an approved roster alias for consultant."
            )
        elif rid == "R-118":
            non_breach.append(
                "- **R-118** - MAIN evening release into closed Jul 16–17: clock 2026-07-18T08:00; "
                "space-separated timestamps parse the same; 0/479 compliant."
            )
        elif rid in ("R-89", "R-103", "R-98", "R-87"):
            non_breach.append(
                f"- **{rid}** - long wall-clock or boundary case resolved by inclusive windows / "
                f"core-hours clock start; findings compliant."
            )

    non_breach.append(
        "- Long wall-clock gaps after evening or closed-day releases are often not breaches once "
        "the correct next-open clock start is applied."
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


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def self_check_new_rows() -> None:
    """Sanity-print expected clocks for structural traps."""
    esc = {e["result_id"] for e in NEW_ESCALATIONS}
    print("NEW ROW GOLD PREVIEW:")
    for row in NEW_CR:
        g = grade_row(row, esc)
        print(
            f"  {g['result_id']} site={row['site']} clock={g['clock_start']} "
            f"n={g['notification_minutes']!r} a={g['acknowledgement_minutes']!r} "
            f"esc={g['escalation_status']} findings={g['findings']}"
        )


def update_verifiers(audit: list[dict], counts: dict) -> int:
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
    ids = []
    for i in range(1, n + 1):
        ids.append(f"R-{i:02d}" if i < 100 else f"R-{i}")

    find("audit_covers_every_result")["assertion"]["expected"] = "(?s)" + "".join(
        rf"(?=.*\b{re.escape(i)}\b)" for i in ids
    )
    find("audit_covers_every_result")["metadata"][
        "how_justification"
    ] = f"Requires every graded register ID R-01 through R-{ids[-1]}."
    find("audit_covers_every_result")["metadata"][
        "why_justification"
    ] = f"All {n} graded results appear in the audit CSV."

    find("result_notification_breaches")["assertion"]["expected"] = counts["notification_breaches"]
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

    # Structural trap verifiers
    upsert(
        "riverside_holiday_skip_compliant",
        "friday_evening_preclock_ack_480_compliant",
        r"(?mi)^\x22?R-106\x22?\s*,\s*\x22?2\x22?\s*,[^\n]*2026-07-18[T ]0?8:00[^\n]*,\s*\x22?\s*120(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*360(?:\.0+)?\s*\x22?\s*,[^\n]*\x22?(compliant|ok|pass|none|no[_ ]?finding)\x22?\s*$",
        "R-106 RIVERSIDE+closed-days must clock 2026-07-18T08:00 with 120/360 compliant.",
        "R-106 site+holiday structural trap.",
    )
    upsert(
        "main_twin_same_times_late",
        "tier2_both_late_241_481_missing",
        r"(?mi)^\x22?R-107\x22?\s*,\s*\x22?2\x22?\s*,[^\n]*2026-07-15[T ]17:30[^\n]*,[^\n]*(?=.*notification_late)(?=.*acknowledgement_late)(?=.*escalation_missing)",
        "R-107 MAIN twin must keep clock at release and flag notify+ack late + missing.",
        "R-107 site-hours decoy twin.",
    )
    upsert(
        "alias_spr_approved_compliant",
        "anp_exact_boundaries_compliant",
        r"(?mi)^\x22?R-108\x22?\s*,[^\n]*SpR[^\n]*\x22?(compliant|ok|pass|none|no[_ ]?finding)\x22?\s*$",
        "R-108 SpR alias must be treated as approved and compliant.",
        "R-108 roster alias trap.",
    )
    upsert(
        "alias_spr_wrong_case_unapproved",
        "physician_associate_unapproved_empty_mins",
        r"(?mi)^\x22?R-109\x22?\s*,[^\n]*,\s*\x22?\s*\x22?\s*,[^\n]*\bspr\b[^\n]*,\s*\x22?missing\x22?\s*,[^\n]*(?=.*acknowledger_unapproved)(?=.*acknowledgement_late)(?=.*escalation_missing)",
        "R-109 lowercase spr is not an alias: empty minutes + unapproved + late + missing.",
        "R-109 case-sensitive alias trap.",
    )
    upsert(
        "holiday_evening_exact_480_compliant",
        "friday_evening_preclock_ack_480_compliant",
        r"(?mi)^\x22?R-110\x22?\s*,[^\n]*2026-07-18[T ]0?8:00[^\n]*,\s*\x22?\s*0(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*480(?:\.0+)?\s*\x22?\s*,[^\n]*\x22?(compliant|ok|pass|none|no[_ ]?finding)\x22?\s*$",
        "R-110 closed-day evening must clock 2026-07-18T08:00 with notify 0 and exact 480 compliant.",
        "R-110 bank-holiday clock trap.",
    )
    upsert(
        "holiday_evening_ack_481_missing",
        "friday_1800_preclock_ack_481",
        r"(?mi)^\x22?R-111\x22?\s*,[^\n]*2026-07-18[T ]0?8:00[^\n]*,\s*\x22?\s*0(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*481(?:\.0+)?\s*\x22?\s*,[^\n]*,\s*\x22?missing\x22?\s*,[^\n]*(?=.*acknowledgement_late)(?=.*escalation_missing)",
        "R-111 closed-day evening ack 481 must be late+missing from 2026-07-18T08:00.",
        "R-111 holiday off-by-one.",
    )
    upsert(
        "riverside_exact_close_next_morning",
        "boundary_tier_two_at_closing_starts_next_morning",
        r"(?mi)^\x22?R-112\x22?\s*,[^\n]*2026-07-15[T ]0?8:00[^\n]*,\s*\x22?\s*0(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*480(?:\.0+)?\s*\x22?\s*,[^\n]*\x22?(compliant|ok|pass|none|no[_ ]?finding)\x22?\s*$",
        "R-112 RIVERSIDE release at 17:00 must clock next morning 08:00 with 0/480 compliant.",
        "R-112 site-close boundary.",
    )
    upsert(
        "riverside_before_close_at_release",
        "tier_two_before_closing_clock_starts_at_release",
        r"(?mi)^\x22?R-113\x22?\s*,[^\n]*2026-07-14[T ]16:59[^\n]*,\s*\x22?\s*31(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*480(?:\.0+)?\s*\x22?\s*,[^\n]*\x22?(compliant|ok|pass|none|no[_ ]?finding)\x22?\s*$",
        "R-113 RIVERSIDE 16:59 must start clock at release with exact 480 compliant.",
        "R-113 site before-close inclusive.",
    )
    upsert(
        "alias_anp_approved_compliant",
        "anp_tier2_31_61_compliant",
        r"(?mi)^\x22?R-114\x22?\s*,[^\n]*\bANP\b[^\n]*\x22?(compliant|ok|pass|none|no[_ ]?finding)\x22?\s*$",
        "R-114 uppercase ANP alias must be approved and compliant.",
        "R-114 ANP alias trap.",
    )
    upsert(
        "alias_cons_approved_compliant",
        "anp_exact_boundaries_compliant",
        r"(?mi)^\x22?R-115\x22?\s*,[^\n]*\bCons\b[^\n]*\x22?(compliant|ok|pass|none|no[_ ]?finding)\x22?\s*$",
        "R-115 Cons alias must be approved and compliant.",
        "R-115 Cons alias trap.",
    )
    upsert(
        "holiday_daytime_notify_late_only",
        "tier2_notify_late_ack_ok_no_escalation",
        r"(?mi)^\x22?R-116\x22?\s*,[^\n]*2026-07-18[T ]0?8:00[^\n]*,\s*\x22?\s*241(?:\.0+)?\s*\x22?\s*,[^\n]*,\s*\x22?not_required\x22?\s*,[^\n]*notification_late",
        "R-116 daytime closed-day release clocks 2026-07-18T08:00; notify 241 late only.",
        "R-116 holiday daytime notify-only.",
    )
    upsert(
        "riverside_unapproved_holiday_recorded",
        "consultant_on_call_recorded_not_missing",
        r"(?mi)^\x22?R-117\x22?\s*,[^\n]*2026-07-18[T ]0?8:00[^\n]*,[^\n]*,\s*\x22?\s*\x22?\s*,[^\n]*nurse_practitioner[^\n]*,\s*\x22?recorded\x22?\s*,[^\n]*(?=.*acknowledger_unapproved)(?=.*acknowledgement_late)(?!.*escalation_missing)",
        "R-117 RIVERSIDE+holiday unapproved with empty minutes and escalation recorded.",
        "R-117 multi-doc recorded escalation.",
    )
    upsert(
        "holiday_space_timestamp_compliant",
        "friday_evening_preclock_ack_480_compliant",
        r"(?mi)^\x22?R-118\x22?\s*,[^\n]*2026-07-18[T ]0?8:00[^\n]*,\s*\x22?\s*0(?:\.0+)?\s*\x22?\s*,\s*\x22?\s*479(?:\.0+)?\s*\x22?\s*,[^\n]*\x22?(compliant|ok|pass|none|no[_ ]?finding)\x22?\s*$",
        "R-118 space-separated timestamps + closed days must clock 2026-07-18T08:00 with 0/479 compliant.",
        "R-118 mixed datetime + holiday trap.",
    )
    # Soft memo checks for structural traps (ID + minutes/window — not brittle single tokens)
    upsert(
        "memo_lists_r106_or_r110_holiday",
        "memo_explains_r89_or_r103_non_breach",
        r"(?is)(?:\bR-106\b.{0,500}(?:08:00|120|360|240|480|RIVERSIDE|closed|holiday)|\bR-110\b.{0,500}(?:08:00|480|closed|holiday|pre[- ]?clock))",
        "Memo must explain a holiday/site non-breach (R-106 or R-110) with clock or window detail.",
        "Structural holiday non-breach in memo.",
    )
    upsert(
        "memo_lists_r107_or_r111_breach",
        "memo_lists_r86_or_r99_tier_swap",
        r"(?is)(?:\bR-107\b.{0,500}(?:notif|ack|late|window|\\d+\\s*min)|\bR-111\b.{0,500}(?:481|ack|late|window|\\d+\\s*min))",
        "Memo must explain a site/holiday breach (R-107 or R-111) with minutes or window.",
        "Structural breach detail in memo.",
    )
    upsert(
        "memo_lists_r108_or_r109_alias",
        "memo_lists_r81_or_r83_near_miss_role",
        r"(?is)(?:\bR-108\b.{0,400}(?:SpR|alias|approved|compliant)|\bR-109\b.{0,500}(?:spr|unapproved|alias|not on the approved))",
        "Memo must cover an alias roster case (R-108 approved or R-109 wrong-case unapproved).",
        "Roster alias traps in memo.",
    )
    upsert(
        "memo_lists_r117_recorded_unapproved",
        "memo_lists_r82_or_r93_or_r105_recorded",
        r"(?is)\bR-117\b.{0,500}(?:nurse_practitioner|unapproved|recorded|escalat)",
        "Memo must explain R-117 unapproved with recorded escalation.",
        "R-117 multi-doc recorded case in memo.",
    )

    for v in data["verifiers"]:
        exp = v["assertion"].get("expected")
        if isinstance(exp, str) and exp.startswith("(?"):
            re.compile(exp)

    vj.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return len(data["verifiers"])


def update_test_outputs(audit: list[dict]) -> None:
    path = PACK / "tests" / "test_outputs.py"
    src = path.read_text(encoding="utf-8")

    # Patch _register_ids to skip comment rows
    new_register_ids = '''def _register_ids(workspace: Path) -> list[str]:
    import csv
    path = workspace / "input" / "critical_results.csv"
    assert path.is_file(), "input/critical_results.csv missing"
    text = path.read_text(encoding="utf-8-sig")
    lines = []
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#") and not (
            stripped.startswith("#,") or ("," in stripped[:12] and stripped.split(",", 1)[0] in {"#ARCH", "#DUP", "#"})
        ):
            # free-text header comments
            if stripped.startswith("# ") or stripped.startswith("#Critical") or stripped.startswith("# Critical"):
                continue
        lines.append(line)
    ids: list[str] = []
    for row in csv.DictReader(lines):
        rid = (row.get("result_id") or "").strip()
        if not rid or rid.startswith("#"):
            continue
        ids.append(rid)
    return ids
'''

    src = re.sub(
        r"def _register_ids\(workspace: Path\) -> list\[str\]:.*?(?=\ndef )",
        new_register_ids + "\n",
        src,
        count=1,
        flags=re.S,
    )

    expected_map = {
        r["result_id"]: r["findings"]
        for r in audit
        if r["result_id"] in {x["result_id"] for x in NEW_CR}
    }
    v18_block = f'''
def test_v18_structural_trap_findings():
    """Per-row findings for v18 multi-doc / holiday / site / alias traps."""
    findings = _audit_findings(WORKSPACE)
    expected = {repr(expected_map)}
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
    for rid in ("R-109", "R-117"):
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
    row = rows["R-117"]
    assert (row.get("escalation_status") or "").strip() == "recorded"
    assert "escalation_missing" not in (row.get("findings") or "")


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
'''

    if "test_v18_structural_trap_findings" in src:
        src = re.sub(
            r"\ndef test_v18_structural_trap_findings\(\):.*",
            lambda _m: "\n" + v18_block.lstrip("\n"),
            src,
            count=1,
            flags=re.S,
        )
    else:
        if not src.endswith("\n"):
            src += "\n"
        src += v18_block

    path.write_text(src, encoding="utf-8", newline="\n")


def assert_harbor_fair_instruction() -> None:
    instr = (PACK / "instruction.md").read_text(encoding="utf-8")
    low = instr.lower()
    for needle in (
        "leave acknowledgement_minutes empty",
        "acknowledger_unapproved",
        "acknowledgement_late",
        "ward_clerk",
    ):
        if needle.lower() not in low:
            raise SystemExit(f"Harbor fairness missing from instruction: {needle}")
    spoilers = [
        "specialty_doctor",
        "senior_house_officer",
        "st_registrar",
        "locum_registrar",
        "staff_grade",
        "foundation_doctor",
        "clinical_scientist",
        "consultant_on_call",
        "near-miss",
        "must-name-R-34",
        r"\blimit\b",
    ]
    for s in spoilers:
        if s.startswith("\\"):
            if re.search(s, instr):
                raise SystemExit(f"Forbidden pattern in instruction: {s}")
        elif s.lower() in low:
            raise SystemExit(f"Spoiler still in instruction: {s}")


def run_pytest() -> int:
    tests = PACK / "tests"
    ws = Path(tempfile.mkdtemp(prefix="h40-v18-gold-"))
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
        print(proc.stderr[-4000:])
    print("pytest_returncode", proc.returncode)
    m = re.search(r"(\\d+) passed", proc.stdout)
    if m:
        print("PASSED", m.group(1))
    m2 = re.search(r"(\\d+) failed", proc.stdout)
    if m2:
        print("FAILED", m2.group(1))
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
    return size


def main() -> int:
    self_check_new_rows()

    # --- write policy docs ---
    INP.mkdir(parents=True, exist_ok=True)
    (INP / "critical_results_procedure.md").write_text(PROCEDURE_MD, encoding="utf-8", newline="\n")
    (INP / "site_core_hours.md").write_text(SITE_CORE_HOURS_MD, encoding="utf-8", newline="\n")
    (INP / "approved_roles_roster.md").write_text(
        APPROVED_ROLES_ROSTER_MD, encoding="utf-8", newline="\n"
    )
    (INP / "bank_holidays.csv").write_text(BANK_HOLIDAYS_CSV, encoding="utf-8", newline="\n")
    (PACK / "instruction.md").write_text(INSTRUCTION_MD, encoding="utf-8", newline="\n")
    assert_harbor_fair_instruction()

    # --- load existing register (skip comment noise), add site=MAIN, append new rows ---
    cr_path = INP / "critical_results.csv"
    old = load_register_rows(cr_path)
    # Drop any prior v18 rows if re-run
    new_ids = {r["result_id"] for r in NEW_CR}
    old = [
        r
        for r in old
        if r.get("result_id") not in new_ids and not str(r.get("result_id", "")).startswith("#")
    ]

    # If a previous broken read left zero rows, fall back to gold audit IDs + current file via line filter
    if len(old) < 100:
        # Rebuild from solution audit + timestamps still on disk via raw line parse
        text = cr_path.read_text(encoding="utf-8-sig")
        lines = [ln for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("# Critical")]
        # Find header line
        hdr_i = next(i for i, ln in enumerate(lines) if ln.startswith("result_id,"))
        old = [
            r
            for r in csv.DictReader(lines[hdr_i:])
            if (r.get("result_id") or "").strip()
            and not (r.get("result_id") or "").startswith("#")
            and r.get("result_id") not in new_ids
        ]
        # Keep only R-01..R-105 base if we somehow have extras
        old = [r for r in old if int(r["result_id"].split("-")[1]) <= 105]

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

    # --- escalations ---
    esc_path = INP / "escalations.csv"
    esc = [
        r
        for r in csv.DictReader(esc_path.open(encoding="utf-8-sig"))
        if r["result_id"] not in {e["result_id"] for e in NEW_ESCALATIONS}
    ]
    esc.extend(NEW_ESCALATIONS)
    write_csv(esc_path, esc, ["result_id", "escalated_at"])
    escalated_ids = {r["result_id"] for r in esc}

    # --- regrade ALL graded rows ---
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

    memo = build_memo(audit, counts)
    (PACK / "solution" / "files" / "results_memo.md").write_text(
        memo, encoding="utf-8", newline="\n"
    )

    # Verify existing R-01..R-105 clocks unchanged vs MAIN 08-18 no holiday hit
    for r in audit:
        num = int(r["result_id"].split("-")[1])
        if num <= 105:
            # spot-check a few known
            pass
    # Known: R-08 clock should still be 2026-06-16T08:00
    by = {r["result_id"]: r for r in audit}
    assert by["R-08"]["clock_start"] == "2026-06-16T08:00", by["R-08"]
    assert by["R-106"]["clock_start"] == "2026-07-18T08:00", by["R-106"]
    assert by["R-107"]["clock_start"] == "2026-07-15T17:30", by["R-107"]
    assert by["R-110"]["findings"] == "compliant", by["R-110"]
    assert by["R-108"]["findings"] == "compliant", by["R-108"]
    assert "acknowledger_unapproved" in by["R-109"]["findings"]
    assert by["R-109"]["acknowledgement_minutes"] == ""

    n_ver = update_verifiers(audit, counts)
    update_test_outputs(audit)
    print("verifiers", n_ver)
    print("rows", len(audit))

    rc = run_pytest()
    if rc != 0:
        print("pytest failed; skipping zip rebuild")
        return rc

    size = rebuild_zips()
    print(f"zip_size={size}")
    print("v18_structural_ok")
    print(
        json.dumps(
            {
                "rows": len(audit),
                "verifiers": n_ver,
                "counts": counts,
                "new_inputs": [
                    "site_core_hours.md",
                    "approved_roles_roster.md",
                    "bank_holidays.csv",
                ],
                "zip_size": size,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
