# Task

Run our monthly table maintenance review on this table export. For each table, check whether autovacuum is enabled first, then whether its bloat ratio is within its own size class's cap — noting that a table under an approved active reindex operation is exempt from the bloat check — and finally whether its statistics are stale. The bloat ratio must be computed as `dead_pages / total_pages` (round-half-up to 2 decimal places) from the input export — it is not read directly. Save `bloat_audit.csv` with exactly the columns `table_name,size_class,bloat_ratio,finding` in that order, one row per unique table, and a `finding` column (`AUTOVACUUM_DISABLED`, `BLOAT_THRESHOLD_EXCEEDED`, `STALE_STATISTICS`, or `none`). Then write `bloat_memo.md` explaining each finding, including the table under active maintenance, and explaining why any table whose bloat ratio exactly equals its size-class cap is compliant.

---
Save your deliverables into your current working directory using exactly these filenames:
    - `bloat_audit.csv` — Per-table maintenance audit
    - `bloat_memo.md` — Markdown table maintenance memo
    - `results.json` — a JSON object with the keys `flagged_count` (number of rows whose finding is not `none`), `autovacuum_disabled_count` (number of rows with `AUTOVACUUM_DISABLED`), `bloat_exceeded_count` (number of rows with `BLOAT_THRESHOLD_EXCEEDED`), `stale_statistics_count` (number of rows with `STALE_STATISTICS`), `compliant_count` (number of rows with `none`)
- Writing those files is the required deliverable and must be your final action; confirm each one exists before you answer.

---

## Working environment

- Your current working directory is `/app`, and it is writable.
- The read-only attachments referred to as `input/` are at `/app/input`.
- Write every deliverable into `/app`, at the exact filenames listed above.

## Binding rules (disclosed)

1. Compute `size_class` from `total_pages` only: `>= 500` → `large` (cap 0.2), `< 500` → `small` (cap 0.4). Ignore the export `size_class` column.
2. If `vacuum_type=manual`, the finding is `AUTOVACUUM_DISABLED` even when `autovacuum_enabled=True`.
3. Statistics are stale if `(audit_date - last_analyzed).days > 30`. Ignore the export `days_since_analyze` field.
4. When stats are stale, tighten the bloat cap by 0.05 before comparing. When statistics are stale, apply the tightened cap before the bloat comparison (including cases where round-half-up leaves the ratio just over the tightened cap). Finding precedence: autovacuum → bloat → stale.
5. Reindex exempts a table from the bloat check only if `maintenance_active` AND `approved=True` AND `valid_until >= audit_date`.
6. Output exactly one row per unique `table_name` (dedupe duplicate input rows).
7. Sort output rows by `last_analyzed` ascending, then by `table_name`.
8. Memo: write prose sentences (≥10 words) explaining each table that has a non-`none` finding; include table id, finding keyword, and ratio/cap in the **same short sentence/bullet** as that table (graders use a ≤~450-character local unit, not a memo-wide bag). Do **not** write graded memo prose for tables whose finding is `none` (compliant). Do not ship CSV/table-only dumps or undifferentiated keyword lists. Graded explanations must also include the substantive evidence tokens below (digit forms, compute stem, size-class labels, autovacuum/reindex/stale where those rules apply).
9. A `medium` value in the export `size_class` column is a trap — still compute size class from `total_pages`.

## Memo requirements

The `bloat_memo.md` must explain each **non-compliant** finding in prose sentences (not a CSV dump, Markdown-table-only dump, or bare keyword list). Tables with finding=`none` do **not** need per-table graded memo explanations. For each table with a finding other than `none`, write a short prose sentence (or contiguous prose window) that:
- States the table name (e.g., "T-02")
- States the finding keyword (`AUTOVACUUM_DISABLED`, `BLOAT_THRESHOLD_EXCEEDED`, or `STALE_STATISTICS`)
- Includes the relevant ratio/cap values
- Uses complete sentences with at least 10 words per explanation

**Disclosed evidence tokens the grader looks for** (include these when they apply to that table; concept paraphrases are accepted as noted). Graders score each table from the **nearest sentence or bullet that names that table id** (about ≤450 characters) — not from a shared memo-wide keyword bag. Each required evidence concept must appear in a **local window** (~400 chars) of that table id inside that unit. Stuffing one undifferentiated token list next to every table id will fail (anti-keyword-stuff / anti bag-dump): explanations must be natural prose with clause punctuation and a connective or framing clause (e.g. which / because / since / records / is …) plus a verb phrase that ties table → finding → evidence (e.g. ratio of / over the / exceeds / overrides / tightened / expired / unapproved). Space-separated number dumps without that prose framing fail; ordinary sentences that mention a few ratios, page counts, or day counts alongside the required evidence are fine:
- `total_pages` as digits **without** thousands separators (e.g. `1000` or `500`, not `1,000`)
- The size-class **computation** concept via a word stem such as compute / computed / computing (or clear “derived from total_pages” wording); do not rely on the export `size_class` column
- Computed size-class labels when relevant (`large`, `small`, and for the medium trap also `medium`)
- `autovacuum` / `auto-vacuum` when the finding is `AUTOVACUUM_DISABLED`
- For stale-statistics cases: the day count as digits (e.g. `31` / `35` / `45`), plus `stale` / `stats` / clear stale-statistics wording; for the legacy-field trap also mention `days_since_analyze` (or “legacy days field”)
- For reindex-exemption / expiry cases: `reindex` / `re-index` plus an expiry/validity paraphrase such as `expired`, `lapsed`, `valid_until`, `approval ended`, `past validity`, or `no longer valid` (exact `valid_until=` is **not** required)
- For round-half-up traps: either the pre-round form (e.g. `0.405` / `0.205`) **or** the rounded 2dp form (e.g. `0.41` / `0.21`) is accepted as numeric near-equivalent evidence — you do **not** need both; also mention round/rounding when that rule decides the finding
- Cap-tightening cases: mention tighten/tightened / reduced cap / effective cap and the effective/tightened cap digits (e.g. `0.15`) along with the ratio
- Manual-vacuum overrides: mention `manual` and `vacuum` (and typically override / supersede / checked first)
- Unapproved-reindex cases: mention **unapproved** / **not approved** / `approved=False` (and reindex), plus that table’s own ratio evidence — do not rely on the bare word `approved` alone

A memo that only lists table names and findings, or that keyword-stuffs the same token bag beside every table without table-bound prose evidence, will not pass.
