#!/usr/bin/env python3
"""Add 200+ trap results to h40 — every boundary, every role, every combination.
All 100% fair, derivable from the disclosed procedure."""
import csv
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

TASK = Path(r"C:\Users\HASEEB~1\AppData\Local\Temp\opencode\h40-work\health-h40-critical-result-acknowledgement")

APPROVED_ROLES = {"consultant", "specialty_registrar", "resident_doctor", "advanced_nurse_practitioner"}

def parse_dt(s):
    return datetime.fromisoformat(s)

def fmt_dt(dt):
    return dt.strftime("%Y-%m-%dT%H:%M")

def clock_start(tier, released_at):
    """Compute clock start per procedure."""
    r = parse_dt(released_at)
    if tier == 1:
        return r  # continuous
    # Tier 2: core hours 08:00-18:00
    hour = r.hour
    minute = r.minute
    # Before 08:00 → clock starts 08:00 same day
    if hour < 8 or (hour == 7 and minute < 60):
        return r.replace(hour=8, minute=0, second=0, microsecond=0)
    # At or after 18:00 → clock starts 08:00 next day
    if hour > 18 or (hour == 18 and minute >= 0):
        next_day = r + timedelta(days=1)
        return next_day.replace(hour=8, minute=0, second=0, microsecond=0)
    # 18:00 exactly → next day 08:00
    if hour == 18 and minute == 0:
        next_day = r + timedelta(days=1)
        return next_day.replace(hour=8, minute=0, second=0, microsecond=0)
    # Within core hours (08:00-17:59) → clock starts at release
    return r

def minutes_between(start, end):
    return int((parse_dt(end) - parse_dt(start)).total_seconds() / 60)

def compute_findings(tier, clock_start_dt, notified_at, acked_at, acked_by, escalations_set):
    """Compute findings for a result."""
    findings = []
    
    notif_mins = minutes_between(fmt_dt(clock_start_dt), notified_at) if notified_at else None
    ack_mins = None
    esc_status = "not_required"
    
    notif_limit = 30 if tier == 1 else 240
    ack_limit = 60 if tier == 1 else 480
    
    # Notification late
    if notif_mins is not None and notif_mins > notif_limit:
        findings.append("notification_late")
    
    # Acknowledgement
    if acked_at and acked_by:
        is_approved = acked_by in APPROVED_ROLES
        if not is_approved:
            findings.append("acknowledger_unapproved")
            # Unapproved = no recognised ack → window keeps running
            # Compute ack minutes anyway but leave empty in output
            ack_mins = minutes_between(fmt_dt(clock_start_dt), acked_at)
            # Check if window missed
            if ack_mins > ack_limit:
                findings.append("acknowledgement_late")
        else:
            ack_mins = minutes_between(fmt_dt(clock_start_dt), acked_at)
            if ack_mins > ack_limit:
                findings.append("acknowledgement_late")
    else:
        # No acknowledgement
        # Window is missed → ack_late
        # But we need a reference time to compute if the window was missed
        # If no ack at all, the window is definitely missed (time has passed)
        findings.append("acknowledgement_late")
    
    # Escalation
    if "acknowledgement_late" in findings:
        if acked_at and acked_by and acked_by not in APPROVED_ROLES:
            # Unapproved ack → window missed → escalation required
            pass
        # Check if escalation exists
        # This is determined by the escalations_set parameter
    
    # Deduplicate and sort
    findings = sorted(set(findings))
    if not findings:
        findings = ["compliant"]
    
    return findings, notif_mins, ack_mins

def gen_results():
    """Generate all new trap results."""
    results = []
    esc_data = []
    rid = 57  # Start after R-56
    
    # Read existing results to preserve them
    with open(TASK / "environment" / "input" / "critical_results.csv", "r", encoding="utf-8-sig") as f:
        existing = list(csv.DictReader(f))
    
    with open(TASK / "environment" / "input" / "escalations.csv", "r", encoding="utf-8-sig") as f:
        existing_esc = list(csv.DictReader(f))
    
    # === CLOCK START BOUNDARIES ===
    # R-57: tier 2, released exactly 08:00 → clock 08:00
    results.append(("R-57", 2, "potassium", "2026-06-26T08:00", "2026-06-26T08:20", "2026-06-26T09:00", "consultant"))
    # R-58: tier 2, released 07:59 → clock 08:00
    results.append(("R-58", 2, "sodium", "2026-06-26T07:59", "2026-06-26T08:30", "2026-06-26T12:00", "consultant"))
    # R-59: tier 2, released exactly 18:00 → clock 08:00 next day
    results.append(("R-59", 2, "creatinine", "2026-06-26T18:00", "2026-06-27T10:00", "2026-06-27T14:00", "consultant"))
    # R-60: tier 2, released 18:01 → clock 08:00 next day
    results.append(("R-60", 2, "glucose", "2026-06-26T18:01", "2026-06-27T10:00", "2026-06-27T14:00", "consultant"))
    # R-61: tier 2, released 17:59 → clock at release (within core hours)
    results.append(("R-61", 2, "lactate", "2026-06-26T17:59", "2026-06-26T18:20", "2026-06-26T22:00", "consultant"))
    # R-62: tier 2, released 07:59 on Saturday → clock 08:00 Saturday
    results.append(("R-62", 2, "bilirubin", "2026-06-27T07:59", "2026-06-27T08:30", "2026-06-27T12:00", "specialty_registrar"))
    # R-63: tier 2, released 18:00 Saturday → clock 08:00 Sunday
    results.append(("R-63", 2, "inr", "2026-06-27T18:00", "2026-06-28T10:00", "2026-06-28T14:00", "consultant"))
    # R-64: tier 2, released 18:00 Sunday → clock 08:00 Monday
    results.append(("R-64", 2, "magnesium", "2026-06-28T18:00", "2026-06-29T10:00", "2026-06-29T14:00", "consultant"))
    # R-65: tier 1, released 23:59 → clock at release
    results.append(("R-65", 1, "troponin", "2026-06-26T23:59", "2026-06-27T00:20", "2026-06-27T00:50", "consultant"))
    
    # === NOTIFICATION BOUNDARIES ===
    # R-66: tier 1, notified at exactly 30 → within
    results.append(("R-66", 1, "potassium", "2026-06-26T10:00", "2026-06-26T10:30", "2026-06-26T10:50", "consultant"))
    # R-67: tier 1, notified at 31 → late
    results.append(("R-67", 1, "sodium", "2026-06-26T10:00", "2026-06-26T10:31", "2026-06-26T10:50", "consultant"))
    # R-68: tier 2, notified at exactly 240 → within
    results.append(("R-68", 2, "creatinine", "2026-06-26T08:00", "2026-06-26T12:00", "2026-06-26T14:00", "consultant"))
    # R-69: tier 2, notified at 241 → late
    results.append(("R-69", 2, "glucose", "2026-06-26T08:00", "2026-06-26T12:01", "2026-06-26T14:00", "consultant"))
    
    # === ACK BOUNDARIES ===
    # R-70: tier 1, ack at exactly 60 → within
    results.append(("R-70", 1, "lactate", "2026-06-26T10:00", "2026-06-26T10:15", "2026-06-26T11:00", "consultant"))
    # R-71: tier 1, ack at 61 → late
    results.append(("R-71", 1, "bilirubin", "2026-06-26T10:00", "2026-06-26T10:15", "2026-06-26T11:01", "consultant"))
    esc_data.append(("R-71", "2026-06-26T11:10"))
    # R-72: tier 2, ack at exactly 480 → within
    results.append(("R-72", 2, "inr", "2026-06-26T08:00", "2026-06-26T10:00", "2026-06-26T16:00", "consultant"))
    # R-73: tier 2, ack at 481 → late
    results.append(("R-73", 2, "magnesium", "2026-06-26T08:00", "2026-06-26T10:00", "2026-06-26T16:01", "consultant"))
    esc_data.append(("R-73", "2026-06-26T16:10"))
    
    # === UNAPPROVED ROLES ===
    unapproved_roles = [
        ("R-74", "ward_clerk"),
        ("R-75", "nurse_hca"),
        ("R-76", "phlebotomist"),
        ("R-77", "healthcare_assistant"),
        ("R-78", "pharmacist"),
        ("R-79", "student_nurse"),
        ("R-80", "lab_technician"),
    ]
    for rid_v, role in unapproved_roles:
        results.append((rid_v, 1, "troponin", "2026-06-26T10:00", "2026-06-26T10:10", "2026-06-26T10:20", role))
        # All within 30 min notification, within 60 min ack time, but unapproved
        # → only acknowledger_unapproved (NOT ack_late, since 20 < 60)
    
    # === COMBINED FINDINGS ===
    # R-81: unapproved + late + no escalation → 3 findings
    results.append(("R-81", 1, "potassium", "2026-06-26T10:00", "2026-06-26T10:10", "2026-06-26T11:30", "ward_clerk"))
    # Notif 10 (within), ack 90 (unapproved + late > 60), no escalation
    # R-82: unapproved + within window → only unapproved
    results.append(("R-82", 1, "sodium", "2026-06-26T10:00", "2026-06-26T10:10", "2026-06-26T10:20", "phlebotomist"))
    # R-83: unapproved + late + escalation exists → 2 findings
    results.append(("R-83", 1, "creatinine", "2026-06-26T10:00", "2026-06-26T10:10", "2026-06-26T11:30", "nurse_hca"))
    esc_data.append(("R-83", "2026-06-26T11:40"))
    
    # === NO ACKNOWLEDGEMENT ===
    # R-84: no ack + escalation exists → ack_late only
    results.append(("R-84", 1, "glucose", "2026-06-26T10:00", "2026-06-26T10:10", "", ""))
    esc_data.append(("R-84", "2026-06-26T11:10"))
    # R-85: no ack + no escalation → ack_late + escalation_missing
    results.append(("R-85", 1, "lactate", "2026-06-26T10:00", "2026-06-26T10:10", "", ""))
    
    # === FINDING PRECEDENCE ===
    # R-86: unapproved within window → only unapproved (NOT late, NOT escalation)
    results.append(("R-86", 2, "bilirubin", "2026-06-26T08:00", "2026-06-26T08:10", "2026-06-26T10:00", "ward_clerk"))
    # Tier 2, ack at 120 min (within 480), but unapproved → only unapproved
    # R-87: unapproved outside window + no escalation → 3 findings
    results.append(("R-87", 2, "inr", "2026-06-26T08:00", "2026-06-26T08:10", "2026-06-26T18:00", "phlebotomist"))
    # Tier 2, ack at 600 min (> 480), unapproved → unapproved + ack_late + escalation_missing
    
    # === CROSS-MIDNIGHT/DAY ===
    # R-88: tier 1, released 23:59, notified 00:29 → 30 min (within boundary)
    results.append(("R-88", 1, "magnesium", "2026-06-26T23:59", "2026-06-27T00:29", "2026-06-27T00:50", "consultant"))
    # R-89: tier 1, released 23:59, notified 00:30 → 31 min (late)
    results.append(("R-89", 1, "troponin", "2026-06-26T23:59", "2026-06-27T00:30", "2026-06-27T00:50", "consultant"))
    # R-90: tier 2, released 17:59 Friday, ack Monday 10:00 → huge, late
    results.append(("R-90", 2, "potassium", "2026-06-26T17:59", "2026-06-26T18:20", "2026-06-29T10:00", "consultant"))
    esc_data.append(("R-90", "2026-06-29T10:30"))
    
    # === WEEKEND CASES ===
    # R-91: tier 2, released 18:00 Saturday → clock 08:00 Sunday
    results.append(("R-91", 2, "sodium", "2026-06-27T18:00", "2026-06-28T10:00", "2026-06-28T14:00", "consultant"))
    # R-92: tier 2, released 07:59 Saturday → clock 08:00 Saturday
    results.append(("R-92", 2, "creatinine", "2026-06-27T07:59", "2026-06-27T08:30", "2026-06-27T12:00", "specialty_registrar"))
    # R-93: tier 2, released 17:59 Saturday → clock at release
    results.append(("R-93", 2, "glucose", "2026-06-27T17:59", "2026-06-27T18:20", "2026-06-28T02:00", "consultant"))
    
    # === MORE BOUNDARY PAIRS (notification at boundary + 1 over) ===
    for i, (tier, notif_within, notif_late, ack_within, ack_late, released) in enumerate([
        (1, 29, 32, 59, 62, "2026-06-26T12:00"),
        (1, 28, 33, 58, 63, "2026-06-26T13:00"),
        (1, 27, 34, 57, 64, "2026-06-26T14:00"),
        (1, 26, 35, 56, 65, "2026-06-26T15:00"),
        (1, 25, 36, 55, 66, "2026-06-26T16:00"),
        (2, 239, 242, 479, 482, "2026-06-26T08:00"),
        (2, 238, 243, 478, 483, "2026-06-26T09:00"),
        (2, 237, 244, 477, 484, "2026-06-26T10:00"),
        (2, 236, 245, 476, 485, "2026-06-26T11:00"),
        (2, 235, 246, 475, 486, "2026-06-26T12:00"),
    ]):
        # Within notification + within ack
        r_id = f"R-{94 + i*4}"
        results.append((r_id, tier, "test", released, 
                       fmt_dt(parse_dt(released) + timedelta(minutes=notif_within)),
                       fmt_dt(parse_dt(released) + timedelta(minutes=ack_within)), "consultant"))
        # Late notification + within ack
        r_id2 = f"R-{95 + i*4}"
        results.append((r_id2, tier, "test", released,
                       fmt_dt(parse_dt(released) + timedelta(minutes=notif_late)),
                       fmt_dt(parse_dt(released) + timedelta(minutes=ack_within)), "consultant"))
        # Within notification + late ack
        r_id3 = f"R-{96 + i*4}"
        results.append((r_id3, tier, "test", released,
                       fmt_dt(parse_dt(released) + timedelta(minutes=notif_within)),
                       fmt_dt(parse_dt(released) + timedelta(minutes=ack_late)), "consultant"))
        esc_data.append((r_id3, fmt_dt(parse_dt(released) + timedelta(minutes=ack_late + 5))))
        # Late notification + late ack
        r_id4 = f"R-{97 + i*4}"
        results.append((r_id4, tier, "test", released,
                       fmt_dt(parse_dt(released) + timedelta(minutes=notif_late)),
                       fmt_dt(parse_dt(released) + timedelta(minutes=ack_late)), "consultant"))
        esc_data.append((r_id4, fmt_dt(parse_dt(released) + timedelta(minutes=ack_late + 5))))
    
    # === UNAPPROVED ROLE + VARIOUS TIMING ===
    for i, role in enumerate(["ward_clerk", "nurse_hca", "phlebotomist", "healthcare_assistant", 
                               "pharmacist", "student_nurse", "lab_technician"]):
        base_rid = 134 + i * 3
        # Unapproved within notification + within ack window → only unapproved
        results.append((f"R-{base_rid}", 1, "test", "2026-06-26T10:00",
                       "2026-06-26T10:10", "2026-06-26T10:20", role))
        # Unapproved within notification + outside ack window → unapproved + ack_late
        results.append((f"R-{base_rid+1}", 1, "test", "2026-06-26T10:00",
                       "2026-06-26T10:10", "2026-06-26T11:30", role))
        esc_data.append((f"R-{base_rid+1}", "2026-06-26T11:40"))
        # Unapproved + late notif + outside ack + no escalation → 4 findings
        results.append((f"R-{base_rid+2}", 1, "test", "2026-06-26T10:00",
                       "2026-06-26T10:45", "2026-06-26T11:30", role))
    
    # === TIER 2 CLOCK START EDGE CASES ===
    for i, (release_time, desc) in enumerate([
        ("2026-06-26T08:00", "exactly 08:00"),
        ("2026-06-26T07:59", "07:59"),
        ("2026-06-26T08:01", "08:01"),
        ("2026-06-26T17:58", "17:58"),
        ("2026-06-26T17:59", "17:59"),
        ("2026-06-26T18:00", "18:00"),
        ("2026-06-26T18:01", "18:01"),
    ]):
        r_id = 155 + i
        cs = clock_start(2, release_time)
        notif = fmt_dt(cs + timedelta(minutes=30))
        ack = fmt_dt(cs + timedelta(minutes=120))
        results.append((f"R-{r_id}", 2, "test", release_time, notif, ack, "consultant"))
    
    # === NO ACK WITH VARIOUS ESCALATION ===
    for i in range(10):
        r_id = 162 + i
        release = f"2026-06-26T{(10+i)%24:02d}:00"
        results.append((f"R-{r_id}", 1 if i % 2 == 0 else 2, "test", release,
                       fmt_dt(parse_dt(release) + timedelta(minutes=15 if i % 2 == 0 else 100)), "", ""))
        if i % 3 == 0:
            esc_data.append((f"R-{r_id}", fmt_dt(parse_dt(release) + timedelta(minutes=90 if i % 2 == 0 else 500))))
    
    # === COMPLIANT RESULTS (various) ===
    for i in range(20):
        r_id = 172 + i
        release = f"2026-06-{min(26+i, 30):02d}T10:00"
        results.append((f"R-{r_id}", 1, "test", release,
                       fmt_dt(parse_dt(release) + timedelta(minutes=15)),
                       fmt_dt(parse_dt(release) + timedelta(minutes=45)), "consultant"))
    
    # === TIER 2 LATE NOTIFICATION VARIATIONS ===
    for i in range(10):
        r_id = 192 + i
        release = "2026-06-26T08:00"
        notif_mins = 241 + i * 5
        ack_mins = 300 + i * 10
        results.append((f"R-{r_id}", 2, "test", release,
                       fmt_dt(parse_dt(release) + timedelta(minutes=notif_mins)),
                       fmt_dt(parse_dt(release) + timedelta(minutes=ack_mins)), "consultant"))
    
    # === TIER 1 LATE ACKNOWLEDGEMENT VARIATIONS ===
    for i in range(10):
        r_id = 202 + i
        day = min(26 + i, 30)
        release = f"2026-06-{day:02d}T{(10+i):02d}:00"
        ack_mins = 61 + i * 3
        results.append((f"R-{r_id}", 1, "test", release,
                       fmt_dt(parse_dt(release) + timedelta(minutes=15)),
                       fmt_dt(parse_dt(release) + timedelta(minutes=ack_mins)), "consultant"))
        if i % 2 == 0:
            esc_data.append((f"R-{r_id}", fmt_dt(parse_dt(release) + timedelta(minutes=ack_mins + 10))))
    
    # === MIXED TIER + UNAPPROVED + ESCALATION COMBINATIONS ===
    combos = [
        (1, "ward_clerk", True, True),   # tier, role, has_esc, is_late_notif
        (1, "nurse_hca", False, True),
        (1, "phlebotomist", True, False),
        (2, "ward_clerk", True, True),
        (2, "nurse_hca", False, False),
        (2, "phlebotomist", True, True),
        (1, "healthcare_assistant", False, True),
        (1, "pharmacist", True, False),
        (2, "student_nurse", False, True),
        (2, "lab_technician", True, False),
    ]
    for i, (tier, role, has_esc, is_late_notif) in enumerate(combos):
        r_id = 212 + i
        release = "2026-06-26T10:00"
        cs = clock_start(tier, release)
        notif_limit = 30 if tier == 1 else 240
        ack_limit = 60 if tier == 1 else 480
        
        if is_late_notif:
            notif = fmt_dt(cs + timedelta(minutes=notif_limit + 5))
        else:
            notif = fmt_dt(cs + timedelta(minutes=min(20, notif_limit - 5)))
        
        ack = fmt_dt(cs + timedelta(minutes=ack_limit + 30))
        
        results.append((f"R-{r_id}", tier, "test", release, notif, ack, role))
        if has_esc:
            esc_data.append((f"R-{r_id}", fmt_dt(cs + timedelta(minutes=ack_limit + 40))))
    
    # === EDGE CASES: notification at boundary exactly ===
    for i, (tier, notif_mins) in enumerate([
        (1, 30), (1, 30), (1, 30),
        (2, 240), (2, 240), (2, 240),
    ]):
        r_id = 222 + i
        release = "2026-06-26T08:00" if tier == 2 else "2026-06-26T10:00"
        cs = clock_start(tier, release)
        results.append((f"R-{r_id}", tier, "test", release,
                       fmt_dt(cs + timedelta(minutes=notif_mins)),
                       fmt_dt(cs + timedelta(minutes=40 if tier == 1 else 300)), "consultant"))
    
    # === EDGE CASES: ack at boundary exactly ===
    for i, (tier, ack_mins) in enumerate([
        (1, 60), (1, 60), (1, 60),
        (2, 480), (2, 480), (2, 480),
    ]):
        r_id = 228 + i
        release = "2026-06-26T08:00" if tier == 2 else "2026-06-26T10:00"
        cs = clock_start(tier, release)
        results.append((f"R-{r_id}", tier, "test", release,
                       fmt_dt(cs + timedelta(minutes=15 if tier == 1 else 100)),
                       fmt_dt(cs + timedelta(minutes=ack_mins)), "consultant"))
    
    # === MORE UNAPPROVED ROLE VARIATIONS (tier 2) ===
    for i, role in enumerate(["ward_clerk", "nurse_hca", "phlebotomist", 
                               "healthcare_assistant", "pharmacist"]):
        r_id = 234 + i * 2
        release = "2026-06-26T08:00"
        cs = clock_start(2, release)
        # Within both windows but unapproved → only unapproved
        results.append((f"R-{r_id}", 2, "test", release,
                       fmt_dt(cs + timedelta(minutes=100)),
                       fmt_dt(cs + timedelta(minutes=200)), role))
        # Outside ack window + unapproved → unapproved + ack_late
        results.append((f"R-{r_id+1}", 2, "test", release,
                       fmt_dt(cs + timedelta(minutes=100)),
                       fmt_dt(cs + timedelta(minutes=500)), role))
        esc_data.append((f"R-{r_id+1}", fmt_dt(cs + timedelta(minutes=510))))
    
    # === VARIOUS COMPLIANT WITH DIFFERENT ROLES ===
    for i, role in enumerate(["consultant", "specialty_registrar", "resident_doctor", "advanced_nurse_practitioner"]):
        r_id = 244 + i * 2
        release = f"2026-06-26T{(10+i):02d}:00"
        # Tier 1 compliant
        results.append((f"R-{r_id}", 1, "test", release,
                       fmt_dt(parse_dt(release) + timedelta(minutes=20)),
                       fmt_dt(parse_dt(release) + timedelta(minutes=50)), role))
        # Tier 2 compliant
        r_id2 = r_id + 1
        release2 = "2026-06-26T08:00"
        cs = clock_start(2, release2)
        results.append((f"R-{r_id2}", 2, "test", release2,
                       fmt_dt(cs + timedelta(minutes=100)),
                       fmt_dt(cs + timedelta(minutes=300)), role))
    
    # === CROSS-DAY TIER 2 ACK ===
    for i in range(5):
        r_id = 252 + i
        release = f"2026-06-26T{(17+i%2):02d}:{59 if i%2 else 0:02d}"
        cs = clock_start(2, release)
        ack = fmt_dt(cs + timedelta(hours=8+i))
        results.append((f"R-{r_id}", 2, "test", release,
                       fmt_dt(cs + timedelta(minutes=100)),
                       ack, "consultant"))
        if i % 2 == 0:
            esc_data.append((f"R-{r_id}", fmt_dt(cs + timedelta(hours=8+i, minutes=10))))
    
    # Generate more random-ish results
    import random
    random.seed(42)
    for i in range(30):
        r_id = 257 + i
        tier = random.choice([1, 2])
        release_hour = random.randint(0, 23)
        release_min = random.choice([0, 15, 30, 45, 59])
        release = f"2026-06-{26 + i % 5:02d}T{release_hour:02d}:{release_min:02d}"
        cs = clock_start(tier, release)
        notif_limit = 30 if tier == 1 else 240
        ack_limit = 60 if tier == 1 else 480
        
        notif_offset = random.choice([notif_limit - 5, notif_limit, notif_limit + 1, notif_limit + 10, notif_limit + 50])
        ack_offset = random.choice([ack_limit - 5, ack_limit, ack_limit + 1, ack_limit + 10, ack_limit + 50])
        
        role = random.choice(["consultant", "specialty_registrar", "resident_doctor", 
                              "advanced_nurse_practitioner", "ward_clerk", "phlebotomist"])
        
        no_ack = random.random() < 0.1
        
        if no_ack:
            results.append((f"R-{r_id}", tier, "test", release,
                           fmt_dt(cs + timedelta(minutes=notif_offset)), "", ""))
            if random.random() < 0.5:
                esc_data.append((f"R-{r_id}", fmt_dt(cs + timedelta(minutes=ack_limit + 20))))
        else:
            results.append((f"R-{r_id}", tier, "test", release,
                           fmt_dt(cs + timedelta(minutes=notif_offset)),
                           fmt_dt(cs + timedelta(minutes=ack_offset)), role))
            if ack_offset > ack_limit and random.random() < 0.7:
                esc_data.append((f"R-{r_id}", fmt_dt(cs + timedelta(minutes=ack_offset + 10))))
    
    return existing, results, existing_esc, esc_data

def compute_gold(existing, new_results, existing_esc, new_esc):
    """Compute gold audit for all results."""
    all_results = existing + [{"result_id": r[0], "tier": str(r[1]), "test": r[2], 
                               "released_at": r[3], "notified_at": r[4], 
                               "acknowledged_at": r[5], "acknowledged_by_role": r[6]} 
                              for r in new_results]
    
    all_esc = existing_esc + [{"result_id": e[0], "escalated_at": e[1]} for e in new_esc]
    esc_set = {e["result_id"] for e in all_esc}
    
    audit_rows = []
    counts = {"notification_breaches": 0, "acknowledgement_breaches": 0, 
              "unapproved_acknowledgement_results": 0, "missing_escalation_results": 0,
              "results_compliant": 0}
    
    for r in all_results:
        rid = r["result_id"]
        tier = int(r["tier"])
        released = r["released_at"]
        notified = r["notified_at"]
        acked = r["acknowledged_at"]
        acked_by = r["acknowledged_by_role"]
        
        cs = clock_start(tier, released)
        cs_str = fmt_dt(cs)
        
        notif_mins = minutes_between(cs_str, notified) if notified else ""
        
        findings = []
        ack_mins_out = ""
        
        notif_limit = 30 if tier == 1 else 240
        ack_limit = 60 if tier == 1 else 480
        
        # Notification late
        if notif_mins != "" and notif_mins > notif_limit:
            findings.append("notification_late")
        
        # Acknowledgement
        is_approved = acked_by in APPROVED_ROLES if acked_by else False
        
        if acked and acked_by:
            if not is_approved:
                findings.append("acknowledger_unapproved")
                # No recognised ack → window keeps running
                actual_ack_mins = minutes_between(cs_str, acked)
                if actual_ack_mins > ack_limit:
                    findings.append("acknowledgement_late")
                # Leave ack_mins empty for unapproved
            else:
                ack_mins_out = minutes_between(cs_str, acked)
                if ack_mins_out > ack_limit:
                    findings.append("acknowledgement_late")
        else:
            # No ack → window missed
            findings.append("acknowledgement_late")
        
        # Escalation
        if "acknowledgement_late" in findings:
            if rid in esc_set:
                esc_status = "recorded"
            else:
                esc_status = "missing"
                findings.append("escalation_missing")
        else:
            esc_status = "not_required"
        
        # Deduplicate and sort
        findings = sorted(set(findings))
        if not findings:
            findings = ["compliant"]
            counts["results_compliant"] += 1
        
        # Count
        if "notification_late" in findings:
            counts["notification_breaches"] += 1
        if "acknowledgement_late" in findings:
            counts["acknowledgement_breaches"] += 1
        if "acknowledger_unapproved" in findings:
            counts["unapproved_acknowledgement_results"] += 1
        if "escalation_missing" in findings:
            counts["missing_escalation_results"] += 1
        
        audit_rows.append({
            "result_id": rid,
            "tier": str(tier),
            "clock_start": cs_str,
            "notification_minutes": str(notif_mins) if notif_mins != "" else "",
            "acknowledgement_minutes": str(ack_mins_out) if ack_mins_out != "" else "",
            "acknowledged_by_role": acked_by if acked_by else "",
            "escalation_status": esc_status,
            "findings": ";".join(findings)
        })
    
    return audit_rows, counts

def main():
    existing, new_results, existing_esc, new_esc = gen_results()
    
    # Write new critical_results.csv
    all_results = existing + [{"result_id": r[0], "tier": str(r[1]), "test": r[2],
                               "released_at": r[3], "notified_at": r[4],
                               "acknowledged_at": r[5], "acknowledged_by_role": r[6]}
                              for r in new_results]
    
    cr_path = TASK / "environment" / "input" / "critical_results.csv"
    with open(cr_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["result_id","tier","test","released_at","notified_at","acknowledged_at","acknowledged_by_role"])
        w.writeheader()
        w.writerows(all_results)
    print(f"critical_results.csv: {len(all_results)} results ({len(existing)} existing + {len(new_results)} new)")
    
    # Write new escalations.csv
    all_esc = existing_esc + [{"result_id": e[0], "escalated_at": e[1]} for e in new_esc]
    esc_path = TASK / "environment" / "input" / "escalations.csv"
    with open(esc_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["result_id","escalated_at"])
        w.writeheader()
        w.writerows(all_esc)
    print(f"escalations.csv: {len(all_esc)} escalations ({len(existing_esc)} existing + {len(new_esc)} new)")
    
    # Compute gold
    audit_rows, counts = compute_gold(existing, new_results, existing_esc, new_esc)
    
    # Write results_audit.csv
    audit_path = TASK / "solution" / "files" / "results_audit.csv"
    with open(audit_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["result_id","tier","clock_start","notification_minutes",
                                          "acknowledgement_minutes","acknowledged_by_role",
                                          "escalation_status","findings"])
        w.writeheader()
        w.writerows(audit_rows)
    print(f"results_audit.csv: {len(audit_rows)} rows")
    print(f"Counts: {json.dumps(counts)}")
    
    # Write results.json
    rj_path = TASK / "solution" / "files" / "results.json"
    with open(rj_path, "w", encoding="utf-8") as f:
        json.dump(counts, f, indent=2)
    print(f"results.json: {json.dumps(counts)}")
    
    # Generate memo
    late_notifs = [r for r in audit_rows if "notification_late" in r["findings"]]
    late_acks = [r for r in audit_rows if "acknowledgement_late" in r["findings"]]
    unapproved = [r for r in audit_rows if "acknowledger_unapproved" in r["findings"]]
    missing_esc = [r for r in audit_rows if "escalation_missing" in r["findings"]]
    compliant = [r for r in audit_rows if r["findings"] == "compliant"]
    
    memo_lines = [f"# CR-7 critical results audit - {len(audit_rows)} results", ""]
    memo_lines.append(f"{len(compliant)} results are clean.")
    memo_lines.append("")
    memo_lines.append("## Late notifications")
    memo_lines.append("")
    for r in late_notifs:
        tier = r["tier"]
        limit = 30 if tier == "1" else 240
        memo_lines.append(f"- **{r['result_id']}** (tier {tier}) - notified {r['notification_minutes']} min after clock start {r['clock_start']} (limit {limit} min).")
    memo_lines.append("")
    memo_lines.append("## Late or absent acknowledgements")
    memo_lines.append("")
    for r in late_acks:
        ack_mins = r["acknowledgement_minutes"] if r["acknowledgement_minutes"] else "never"
        memo_lines.append(f"- **{r['result_id']}** - acknowledged at {ack_mins} min after clock start {r['clock_start']}.")
    memo_lines.append("")
    memo_lines.append("## Unapproved acknowledger")
    memo_lines.append("")
    for r in unapproved:
        role = r["acknowledged_by_role"]
        memo_lines.append(f"- **{r['result_id']}** - acknowledged by {role}, not on the approved list.")
    memo_lines.append("")
    memo_lines.append("## Missing escalation")
    memo_lines.append("")
    for r in missing_esc:
        memo_lines.append(f"- **{r['result_id']}** - missed acknowledgement window, no escalation.")
    memo_lines.append("")
    memo_lines.append("## What is not a finding")
    memo_lines.append("")
    memo_lines.append("- Weekend results: core hours 08:00-18:00 apply every day.")
    memo_lines.append("- Inclusive boundaries: exactly at the window limit is within it.")
    memo_lines.append("- A tier 2 result released before 08:00 starts its clock at 08:00 that morning.")
    memo_lines.append("- A tier 2 result released at or after 18:00 starts its clock at 08:00 the next morning.")
    memo_lines.append("- An unapproved acknowledgement means the result stands unacknowledged; the window keeps running.")
    
    memo_path = TASK / "solution" / "files" / "results_memo.md"
    memo_path.write_text("\n".join(memo_lines) + "\n", encoding="utf-8")
    print(f"results_memo.md: {len(memo_lines)} lines")
    
    # Update verifier.json audit_covers_every_result regex
    vpath = TASK / "tests" / "verifier.json"
    with open(vpath, "r", encoding="utf-8") as f:
        vdata = json.load(f)
    
    # Update audit_covers_every_result to match all result IDs
    all_rids = [r["result_id"] for r in audit_rows]
    # Build regex: (?s)(?=.*\bR-01\b)(?=.*\bR-02\b)...
    rid_pattern = "(?s)" + "".join(f"(?=.*\\b{rid}\\b)" for rid in all_rids)
    
    for v in vdata["verifiers"]:
        if v["name"] == "audit_covers_every_result":
            v["assertion"]["expected"] = rid_pattern
            break
    
    with open(vpath, "w", encoding="utf-8") as f:
        json.dump(vdata, f, indent=2, ensure_ascii=False)
    print(f"verifier.json: updated audit_covers_every_result for {len(all_rids)} results")
    
    # Update golden_results.json
    gr_path = TASK / "solution" / "golden_results.json"
    with open(gr_path, "w", encoding="utf-8") as f:
        json.dump(counts, f, indent=2)
    
    print(f"\nTotal results: {len(all_results)}")
    print(f"Total escalations: {len(all_esc)}")
    print(f"Total audit rows: {len(audit_rows)}")
    print(f"Counts: {counts}")
    print("\nDone. Rebuild zip and re-upload.")

if __name__ == "__main__":
    main()
