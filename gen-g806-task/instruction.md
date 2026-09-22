# Task

Before these leadership-brief scripts get recorded, audit the attached script inventory against the internal communications style guide: whether the banned negation-pivot rhetorical pattern was used, whether scripture references are cited, and whether the runtime sits within the format's target band — verbatim-testimony scripts are handled differently from the presenter's own material. Save `script_style_audit.csv` with one row per script and a `finding` column (`NEGATION_PIVOT_USED`, `UNCITED_SCRIPTURE_REF`, `RUNTIME_OUT_OF_BAND`, `none`). Then write `style_audit_memo.md` explaining each finding and how the verbatim-testimony exemption applies.

---
Save your deliverables into your current working directory using exactly these filenames:
    - `script_style_audit.csv` — Per-script style audit
    - `style_audit_memo.md` — Markdown memo
    - `results.json` — a JSON object with the keys `script_count`, `flagged_count`, `negation_pivot_count`, `uncited_scripture_count`, `runtime_breach_count`
- Writing those files is the required deliverable and must be your final action; confirm each one exists before you answer.

---

## Working environment

- Your current working directory is `/app`, and it is writable.
- The read-only attachments referred to as `input/` are at `/app/input`.
- Write every deliverable into `/app`, at the exact filenames listed above.
