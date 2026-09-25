# Leadership brief style audit — 2472 scripts

2472 logged scripts were checked against the communications style guide and policy errata v4. 906 rows are compliant; 1566 carry a finding.

## Finding categories

Each script receives exactly one finding under the priority chain `ON_HOLD` > `RETIRED` > `OUT_OF_WINDOW` > `NEGATION_PIVOT_USED` > `UNCITED_SCRIPTURE_REF` > `RUNTIME_OUT_OF_BAND` > `none`.

- **ON_HOLD** — 225 scripts.
- **RETIRED** — 136 scripts.
- **OUT_OF_WINDOW** — 114 scripts.
- **NEGATION_PIVOT_USED** — 565 scripts.
- **UNCITED_SCRIPTURE_REF** — 210 scripts.
- **RUNTIME_OUT_OF_BAND** — 316 scripts.
- **none** — 906 scripts (compliant).

## Testimony exemption and the endorsement exception

The negation-pivot rule exempts scripts whose speaker attribution is `third_party_testimony`; this exemption applies only to the negation-pivot rule, not to scripture or runtime checks. The presenter endorsement exception voids that exemption: when a third-party testimony script's `body_excerpt` contains any of the phrases 'the presenter agreed', 'the presenter endorsed', 'the presenter confirmed', 'the presenter affirmed', or 'the presenter accepted' (case-insensitive), the testimony is treated as the presenter's own position and the negation-pivot check applies normally. This is why some third_party_testimony scripts still receive `NEGATION_PIVOT_USED`.

## Scripture citation format

When `has_scripture_ref` is true and `scripture_cited` is true, the citation in `scripture_text` must match a canonical entry in `scripture_registry.csv`. Book names match case-insensitively; partial citations (book only, or book+chapter) are accepted when the book or book+chapter appears in the registry. A full `Book Chapter:Verse` citation is accepted only when the verse falls within the registry's `verse_range` for that book and chapter. A citation that references a book, chapter, or verse not in the registry is `UNCITED_SCRIPTURE_REF`. When `has_scripture_ref` is true but `scripture_cited` is not true, the finding is also `UNCITED_SCRIPTURE_REF` (no format check is needed).

## Timing adjustment cap

Effective minutes normally equal `timing_log.timed_minutes` plus the winning `timing_adjustments.adjustment_minutes` (last row wins). The timing cap limits a single adjustment: when the absolute adjustment exceeds 50% of the original timed minutes, the adjustment is capped and effective minutes equal the original timed minutes. An adjustment of exactly 50% is not capped. When timed minutes is 0 the cap does not apply. The cap is applied after last-wins resolution and before the band boundary comparison in `band_definition.csv` (active rows only, latest effective_date wins). A script outside its band receives `RUNTIME_OUT_OF_BAND`.

## results.json figures

- `script_count` = 2073 (winning clearance CLEARED).
- `flagged_count` = 1566.
- `negation_pivot_count` = 565.
- `uncited_scripture_count` = 210.
- `runtime_breach_count` = 316.
