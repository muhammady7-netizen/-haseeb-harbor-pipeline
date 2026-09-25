# gen-g806-leadership-brief-rhetorical-style-audit

Non-connector Harbor task. Audit leadership-brief scripts against the communications style guide and policy errata v4.

## Deliverables

- script_style_audit.csv — one row per script with a finding column
- style_audit_memo.md — markdown memo explaining each finding and the testimony exemption
- results.json — script_count, flagged_count, negation_pivot_count, uncited_scripture_count, runtime_breach_count

## Inputs

- input/leadership_brief_style_guide.md — the style guide (overridden by errata v4)
- input/policy_errata_v4.md — the authoritative errata (trim, last-wins, token rules, band bounds)
- input/band_definition.csv — band bounds (active rows only, last-wins)
- input/script_inventory.csv — 2472 scripts with opening_line, body_excerpt and scripture_text
- input/recording_clearance.csv — clearance status per script
- input/retirement_register.csv — retirement status per script
- input/air_window.csv — air window status per script
- input/timing_log.csv — timed minutes per script
- input/timing_adjustments.csv — adjustment minutes per script (last-wins)
- input/format_band.csv — band assignment per script
- input/speaker_attribution.csv — speech source per script
- input/scripture_registry.csv — canonical scripture citations (book,chapter,verse_range,canonical_form)

## Verifier

2422+22 deterministic checks (2444): 3 file-existence, 2422 per-script finding checks, 1 no_duplicate_script_ids, 1 audit_exactly_n_rows, 1 no_pipe_joins, 1 audit_header_exact, 10 memo content checks (testimony, exemption, third_party_testimony, and the 7 finding-category tokens), 5 results.json equals checks. A separate pytest assertion (`test_memo_min_length`) enforces the 800-character memo minimum; it is not a verifier.json regex check (PreQC blocks regex on `.md`). Fractional reward. The 200 added fair-hurdle scripts (SC-2096..SC-2295) exercise derivable edge cases at scale: complex timing adjustments (last-wins vs sum, exact band boundaries, negative effective minutes), multi-rule priority interactions (ON_HOLD > RETIRED > OUT_OF_WINDOW > NEGATION_PIVOT_USED > UNCITED_SCRIPTURE_REF > RUNTIME_OUT_OF_BAND, including triple/quadruple overlaps and PENDING-continues cases), clarified negation-pivot rules (same-pronoun restatements, `was not` vs `wasn't`/`isn't` contractions, `It`-in-second-clause requirement, separators, case-insensitivity, testimony exemption, pivot in body_excerpt), scripture exactly-true token edge cases, and clearance last-wins flips (CLEARED/HOLD/PENDING ordering). A further 200 multi-step reasoning scripts (SC-2296..SC-2495) add three cross-file chains: scripture citation format validation against scripture_registry.csv (book/chapter/verse-range matching, partial citations, case-insensitive book names, empty/garbage citations, the cited=false path), the timing adjustment cap (|adjustment| > 50% of timed minutes caps effective minutes to timed_minutes; exactly-50% and timed=0 edge cases; last-wins interactions; negative adjustments), and the presenter endorsement exception (endorsement phrases in body_excerpt void the third_party_testimony negation-pivot exemption). These are sub-checks of existing finding codes, so no new finding codes are introduced.
