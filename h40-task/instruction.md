# Task

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
