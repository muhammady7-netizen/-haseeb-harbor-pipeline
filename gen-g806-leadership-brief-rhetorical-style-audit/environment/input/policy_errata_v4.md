# Policy errata v4 (AUTHORITATIVE)

Supersedes the style guide, `policy_errata.md`, `policy_errata_v2.md`,
`policy_errata_v3.md`, and any informal ops notes.

## Join keys and duplicates

Before any lookup or compare, **trim** leading/trailing whitespace on `script_id` and on
every status/boolean/band/source/minutes field used below. Match `script_id`
**case-insensitively**. When reporting a `script_id` in the audit, use the canonical
upper-cased trimmed form (e.g. ` sc-16 ` -> `SC-16`).

If any input file has more than one row for the same `script_id` (after that keying), the
**last row in that file wins** for every field from that file. Do not merge fields across
revisions.

## One finding only

No `|` joins. Priority (first match wins):

`ON_HOLD` > `RETIRED` > `OUT_OF_WINDOW` > `NEGATION_PIVOT_USED` > `UNCITED_SCRIPTURE_REF` >
`RUNTIME_OUT_OF_BAND` > `none`

When a single script is both uncited-scripture and runtime-breaching, `UNCITED_SCRIPTURE_REF`
wins over `RUNTIME_OUT_OF_BAND`.

## Clearance -> ON_HOLD

Read `recording_clearance.csv` after last-wins. After trim, match `clearance_status`
case-insensitively. `HOLD` -> finding `ON_HOLD` (do not evaluate later rules). `CLEARED`
continues. Any other status is treated as not cleared for `script_count` purposes and is
not automatically `ON_HOLD`. Only `HOLD` stops evaluation; every status that is not `HOLD`
(including `CLEARED` and any other value such as `PENDING`) continues to the retirement,
air-window, negation-pivot, scripture, and runtime rules. Only a winning clearance of
exactly `CLEARED` counts toward `script_count`.

## Retirement -> RETIRED

If the winning `retirement_register.csv` row has trimmed `status` equal to `RETIRED`
(case-insensitive), finding is `RETIRED` (unless already `ON_HOLD`). Values such as
`RETIRED_PENDING`, `archived`, or `retire` are **not** retired.

## Air window -> OUT_OF_WINDOW

If the winning `air_window.csv` row has trimmed `in_window` equal to `False`
(case-insensitive), finding is `OUT_OF_WINDOW` (unless already `ON_HOLD` or `RETIRED`).
Values such as `0`, `no`, `N`, `off`, or blank are **not** out-of-window.

## Negation-pivot (text only)

Scan both `opening_line` and `body_excerpt` from the winning inventory row. Inventory
`uses_negation_pivot` is ignored. Pattern: "That's not X. It's Y." / "It's not X. It's Y."
(and close variants like "That is not X. It is Y."). The two clauses may be separated by a
period, em dash, semicolon, ellipsis, or comma. Both present-tense forms ("'s not"/"is not")
and past-tense forms ("was not") match, with "not" appearing as a separate word; contractions
such as "wasn't" or "isn't" (no separate "not") do not match. Match the pattern
case-insensitively, so an all-caps restatement (`THAT IS NOT X. IT IS Y.`) or a
lowercase one (`That's not X, it's Y.`) still counts as a pivot.

The restatement in the second clause must use the pronoun "It" ("It's" / "It is" / "It was"). A restatement that repeats the first clause's own pronoun instead of shifting to "It" — such as "That's not X. That's Y." or "This is not X. This is Y." — is not a negation pivot. (The pattern "It's not X. It's Y." still qualifies, because the second clause is "It".)

**Exemption:** only when winning `speaker_attribution.csv` `speech_source` equals
`third_party_testimony` after trim (case-insensitive). Inventory `is_verbatim_testimony`
is unreliable and never grants the exemption. Exemption applies **only** to negation.

**Presenter endorsement exception.** The third-party testimony exemption from the
negation-pivot check (see above) applies ONLY when the presenter did NOT endorse the
testimony. If the script's `body_excerpt` contains any of the phrases 'the presenter
agreed', 'the presenter endorsed', 'the presenter confirmed', 'the presenter affirmed',
or 'the presenter accepted' (case-insensitive), the exemption is voided and the
negation-pivot check applies normally, even for third-party testimony speakers. This
is because an endorsement makes the testimony the presenter's own position.

## Scripture citations

Treat `has_scripture_ref` / `scripture_cited` as true **only** when the trimmed value is
exactly `true` (case-insensitive). Tokens such as `yes`, `1`, `Y`, or `TRUE` with extra
characters are **not** true. If `has_scripture_ref` is true and `scripture_cited` is not
true -> `UNCITED_SCRIPTURE_REF`.

**Scripture citation format.** When a script's `has_scripture_ref` is `true` AND
`scripture_cited` is `true`, the citation text in the inventory's `scripture_text`
column must match a canonical entry in `scripture_registry.csv` (columns
`book,chapter,verse_range,canonical_form`). Parse `scripture_text` as `Book`,
`Book Chapter`, or `Book Chapter:Verse` (the book is everything before the last
integer chapter number; chapter and verse are integers). Book names are matched
case-insensitively. A citation that references a book, chapter, or verse NOT in the
registry is treated as `UNCITED_SCRIPTURE_REF` (the reference exists but is not a
recognized canonical citation). For a full `Book Chapter:Verse` citation, the verse
must fall within the `verse_range` of a registry entry whose book (case-insensitive)
and chapter match. Partial citations (`Book` only, or `Book Chapter` without a verse)
are accepted if the book (or book+chapter) appears in the registry. An empty or
unparseable `scripture_text` is treated as not matching (`UNCITED_SCRIPTURE_REF`).

## Runtime bands (effective minutes)

Parse minutes after trim: a leading `+` is allowed; numeric strings such as `08` or `1.0`
are numbers. Effective minutes = `timing_log.timed_minutes` + winning
`timing_adjustments.adjustment_minutes` (missing adjustment -> 0).

**Timing adjustment cap.** When computing effective minutes, if the absolute value of
the timing adjustment exceeds 50% of the original timed minutes from `timing_log.csv`,
the adjustment is "capped": the effective minutes are calculated as `timed_minutes`
(ignoring the adjustment). This prevents a single adjustment from swinging a script's
runtime by more than half its original value. An adjustment whose absolute value is
exactly 50% of timed minutes is **not** capped (the cap requires strictly more than
50%). When `timed_minutes` is 0 the cap does **not** apply (the ratio is undefined) and
effective minutes = `timed_minutes` + adjustment. The cap applies AFTER last-wins
resolution but BEFORE band boundary comparison.
Example: timed=10, last adjustment=-8 (80% of 10 > 50%) -> effective=10 (capped), not 2.
timed=10, last adjustment=-4 (40% <= 50%) -> effective=6 (not capped).

Band bounds are defined in `band_definition.csv`. Apply only rows whose `status` (after
trim, case-insensitive) **equals** `active`. Rows with `draft`, `proposed`, `Active!`,
or any other status that does not trim and casefold to exactly `active` do **not** apply.
Among the active rows for each band, the row with the **latest `effective_date`** wins
(not the last row in file order — the row whose `effective_date` column has the most
recent date). Parse `effective_date` as YYYY-MM-DD. You must parse `band_definition.csv`
yourself to determine the min and max allowed minutes for each band.

Outside the applicable band -> `RUNTIME_OUT_OF_BAND`.

## results.json

- `script_count` = unique scripts whose winning clearance is `CLEARED` (HOLD rows still
  appear in the CSV but do **not** count)
- `flagged_count` = audit rows whose finding is not `none`
- `negation_pivot_count` / `uncited_scripture_count` / `runtime_breach_count` = rows whose
  single finding equals that exact code
