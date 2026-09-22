# Task

Before these leadership-brief scripts get recorded, audit the attached inputs under `input/` against the internal communications style guide and the current policy errata (ignore obsolete errata and informal ops notes; honor trim, last-wins, and token rules stated in the authoritative errata): recording clearance, retirement, air window, negation-pivot rhetoric, scripture citation, and runtime band — third-party testimony is handled differently from the presenter's own material. Save `script_style_audit.csv` with header `script_id,finding` and one row per script and a single `finding` value (`ON_HOLD`, `RETIRED`, `OUT_OF_WINDOW`, `NEGATION_PIVOT_USED`, `UNCITED_SCRIPTURE_REF`, `RUNTIME_OUT_OF_BAND`, `none`). Then write `style_audit_memo.md` (at least 800 characters) explaining each finding and how the testimony exemption applies.

---
Save your deliverables into your current working directory using exactly these filenames:
    - `script_style_audit.csv` — Per-script style audit
    - `style_audit_memo.md` — Markdown memo
    - `results.json` — a JSON object with the keys `script_count` (errata v4 takes precedence for all count definitions; script_count counts all scripts whose winning clearance is CLEARED regardless of other findings), `flagged_count` (scripts with a finding other than `none`), `negation_pivot_count`, `uncited_scripture_count`, `runtime_breach_count`
- Writing those files is the required deliverable and must be your final action; confirm each one exists before you answer.

---

## Working environment

- Your current working directory is `/app`, and it is writable.
- The read-only attachments referred to as `input/` are at `/app/input`.
- Write every deliverable into `/app`, at the exact filenames listed above.
