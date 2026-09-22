# Leadership Brief Communications Style Guide

## Sources of truth (read these carefully)

Grade using **all** files under `input/`. Several inventory columns are **draft producer
flags** and must be ignored when a dedicated register exists.

**If `policy_errata_v4.md` is present, it overrides this guide and any older errata (including v3).**

| Decision | Authoritative source | Ignore |
|---|---|---|
| Cleared to record? | `recording_clearance.csv` → `clearance_status` | — |
| Verbatim testimony? | `speaker_attribution.csv` → `speech_source` | inventory `is_verbatim_testimony` |
| Negation-pivot used? | inventory `opening_line` **and** `body_excerpt` text | inventory `uses_negation_pivot` |
| Scripture cited? | inventory `has_scripture_ref` + `scripture_cited` | — |
| Timed runtime | `timing_log.csv` → `timed_minutes` (+ adjustments per errata) | inventory `runtime_minutes` |
| Allowed runtime band | `format_band.csv` → `band` (bounds per errata when present) | — |

## Rule 0 — Recording clearance

If `clearance_status` is `HOLD`, the only finding is `ON_HOLD`. Do **not** evaluate Rules
1–3 for that script.

If `clearance_status` is `CLEARED`, continue with Rules 1–3.

## Rule 1 — Negation-pivot pattern banned

Leadership-brief scripts must not use the negation-pivot rhetorical construction ("That's
not X. It's Y." / "It's not X. It's Y." / similar). Scan **both** `opening_line` and
`body_excerpt`. If either contains the pattern, the script uses it.

**Exception:** when `speech_source` is `third_party_testimony`, Rule 1 does not apply.
`speech_source=presenter` is never exempt. Inventory `is_verbatim_testimony` is unreliable.

This exemption applies **only** to Rule 1.

## Rule 2 — Scripture citations

If `has_scripture_ref` is true and `scripture_cited` is false → `UNCITED_SCRIPTURE_REF`.
Applies to testimony and presenter scripts alike.

## Rule 3 — Runtime band

Compute effective minutes per errata when present; otherwise use `timed_minutes`.

- `band=standard` → allowed **4–8** minutes inclusive
- `band=extended` → allowed **4–12** minutes inclusive (see errata if present; v4 uses 5–10)

Outside the applicable band → `RUNTIME_OUT_OF_BAND`.

## Multiple findings

Default in this guide was to join with `|`. **Errata replaces that:** emit exactly one
finding using the errata priority list.

## Finding names

`ON_HOLD`, `NEGATION_PIVOT_USED`, `UNCITED_SCRIPTURE_REF`, `RUNTIME_OUT_OF_BAND`, `none`.

## Derived counts (`results.json`)

- `script_count`: rows in the inventory
- `flagged_count`: findings other than `none`
- `negation_pivot_count`: findings equal to `NEGATION_PIVOT_USED`
- `uncited_scripture_count`: findings equal to `UNCITED_SCRIPTURE_REF`
- `runtime_breach_count`: findings equal to `RUNTIME_OUT_OF_BAND`

(`ON_HOLD` counts toward `flagged_count` only.)
