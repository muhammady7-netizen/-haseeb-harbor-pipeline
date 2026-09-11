# Task

Run our monthly table maintenance review on this table export (17 tables). For each table, check whether autovacuum is enabled first, then whether its bloat ratio is within its own size class's cap — noting that a table under an approved active reindex operation is exempt from the bloat check — and finally whether its statistics are stale. Save `bloat_audit.csv` with one row per table and a `finding` column (`AUTOVACUUM_DISABLED`, `BLOAT_THRESHOLD_EXCEEDED`, `STALE_STATISTICS`, or `none`). Then write `bloat_memo.md` explaining each finding, including the table under active maintenance. The memo must mention: the bloat cap or threshold concept, the size-class distinction (large vs small tables), the reindex or maintenance exemption, and each flagged table's finding reason (autovacuum, bloat, or stale statistics).

---
Save your deliverables into your current working directory using exactly these filenames:
    - `bloat_audit.csv` — Per-table maintenance audit
    - `bloat_memo.md` — Markdown table maintenance memo
    - `results.json` — a JSON object with the keys `flagged_count`, `autovacuum_disabled_count`, `bloat_exceeded_count`, `stale_statistics_count`, `compliant_count`
- Writing those files is the required deliverable and must be your final action; confirm each one exists before you answer.

---

## Working environment

- Your current working directory is `/app`, and it is writable.
- The read-only attachments referred to as `input/` are at `/app/input`.
- Write every deliverable into `/app`, at the exact filenames listed above.
