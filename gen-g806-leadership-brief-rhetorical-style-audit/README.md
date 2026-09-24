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
- input/script_inventory.csv — 2022 scripts with opening_line and body_excerpt
- input/recording_clearance.csv — clearance status per script
- input/retirement_register.csv — retirement status per script
- input/air_window.csv — air window status per script
- input/timing_log.csv — timed minutes per script
- input/timing_adjustments.csv — adjustment minutes per script (last-wins)
- input/format_band.csv — band assignment per script
- input/speaker_attribution.csv — speech source per script

## Verifier

2036 deterministic checks: 3 file-existence, 2022 per-script finding checks, 1 no_duplicate_script_ids, 1 audit_exactly_n_rows, 1 no_pipe_joins, 1 audit_header_exact, 2 memo content checks (minimum 800 characters; third-party-testimony discussion), 5 results.json equals checks. Fractional reward.
