# Leadership Brief Communications Style Guide

## Rule 1 — Negation-pivot pattern banned

Leadership-brief scripts must not use the negation-pivot rhetorical construction ("That's
not X. It's Y." / "It's not X. It's Y." or any similar pattern). A script using it is
`NEGATION_PIVOT_USED`.

**Exception:** a script tagged `is_verbatim_testimony` (a direct transcript of someone
else's own spoken personal testimony, not the presenter's own rhetoric) is exempt from this
rule entirely — editing a person's own words to remove their natural speech pattern would
misrepresent their testimony. Flagging a verbatim-testimony script for using the pattern is
the commonest false positive.

## Rule 2 — Scripture citations

Any scripture reference used in a script must be cited (book, chapter and verse). A script
with an uncited scripture reference is `UNCITED_SCRIPTURE_REF`.

## Rule 3 — Runtime band

A leadership-brief script's runtime must fall within 4-8 minutes inclusive. A script
outside that band is `RUNTIME_OUT_OF_BAND`.

## Finding names

`NEGATION_PIVOT_USED`, `UNCITED_SCRIPTURE_REF`, `RUNTIME_OUT_OF_BAND`, `none`.
