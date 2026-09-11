# Task

Audit this recurring reporting pipeline's logged runs against our source-selection standard. For every run, apply the weekly source-cutover rule, the row-count-consistency rule (comparing `reported_row_count` against `source_row_count_snapshot` in `input/source_row_count_snapshot.csv`) and the monthly tail-merge rule, and separately confirm every required recurring job has at least one run logged — the cutover rule is inclusive of the cutover date itself, so check each run's own date against the standard rather than assuming the cutover date already means live. Save `report_source_audit.csv` with one row per run (plus any missing required job) and a `finding` column using the standard's finding names, `none` where compliant. Then write `report_source_memo.md` explaining every finding and why the cutover-date run is not a source mismatch.

---
Save your deliverables into your current working directory using exactly these filenames:
    - `report_source_audit.csv` — Per-run source-selection audit
    - `report_source_memo.md` — Markdown source-selection audit memo
    - `results.json` — a JSON object with the keys `flagged_count`, `source_mismatch_count`, `row_count_mismatch_count`, `missing_tail_merge_count`, `missing_job_count`
- Writing those files is the required deliverable and must be your final action; confirm each one exists before you answer.

---

## Working environment

- Your current working directory is `/app`, and it is writable.
- The read-only attachments referred to as `input/` are at `/app/input`.
- Write every deliverable into `/app`, at the exact filenames listed above.
