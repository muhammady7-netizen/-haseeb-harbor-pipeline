# health-h40-critical-result-acknowledgement

**Task ID:** NONC-B1-1000151  
**Trainer:** Muhammad Haseeb Younas (`muhammad.y7@turing.com`)

## What this task is

A pathology critical-results audit for Ardleigh Trust (procedure CR-7). The model receives a results register, an escalation register, and the binding procedure. It must time telephone notification and acknowledgement from the correct clock start (tier 1 continuous vs tier 2 core hours), reject unapproved acknowledger roles, and flag missed acknowledgement windows with no escalation.

## Inputs (read-only under `input/`)

- `critical_results_procedure.md` — windows, clock rules, escalation
- `critical_results.csv` — result-level release / notify / acknowledge fields
- `escalations.csv` — escalations recorded on the register
- `site_core_hours.md` — site codes and core-hour open/close times
- `approved_roles_roster.md` — approved acknowledger tokens and roster aliases
- `bank_holidays.csv` — trust closed days that defer the tier-2 clock
- `procedure_amendment_2026-07-01.md` — dated supersession of Riverside core hours


## Deliverables (workspace root)

1. `results_audit.csv` — one row per result with timing, escalation status, findings
2. `results_memo.md` — late notifications, late/absent acknowledgements, missing escalations, and long wall-clock times that are not breaches
3. `results.json` — integer counts for `notification_breaches`, `acknowledgement_breaches`, `unapproved_acknowledgement_results`, `missing_escalation_results`, `results_compliant` (not arrays of result IDs)

## Why it is non-trivial

- Tier 2 clocks start only in site core hours on open days; closed days, site close times, and dated amendments shift the start
- Unapproved roles void acknowledgements even when “on time”
- Escalation is a separate finding from acknowledgement delay
- Inclusive window boundary (exact 60 minutes is compliant)

## Grading

Deterministic checks in `tests/verifier.json` via vendored `rl_world_verifiers` (`tests/test.sh` → pytest).

## Row-count checks

Added row-count checks for CSV deliverables to reject duplicated-row counterexamples. The pytest layer in test_outputs.py also enforces exact row sets.
