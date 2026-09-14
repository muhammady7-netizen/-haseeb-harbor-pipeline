# Recipe cost claim standard for meal-prep content

Batch review date: 2026-08-10. Base reference prices: chicken breast
$4.00/lb, cilantro-lime rice $0.60/cup, asparagus $3.00/lb.

## Secondary price register (binding override)

A secondary price register (`secondary_price_register.csv`) overrides the base
reference prices above. Apply only rows whose `status` (after trim,
case-insensitive) equals `active`. Rows with `draft` or `proposed` status do
not apply. If the register has more than one active row for the same
ingredient (after trimming the ingredient name), the **last row in the file
wins**. The `price_sheet_errata_proposed.md` is **not in force** — its
`proposed` status excludes it.

After applying the register, the current reference prices are:
chicken breast $4.25/lb, cilantro-lime rice $0.65/cup, asparagus $3.25/lb.
All cost computations and stale-price checks use these overridden prices —
never the obsolete base sheet alone, and never a creator's remembered price.

Claim tolerance: $0.25 per serving.

## Field normalization

Before any compare or lookup, **trim** leading and trailing whitespace on
`recipe_id`, `extra_is_pantry_staple`, `serving_count`, `claimed_cost_per_serving`,
`chicken_price_used`, and every quantity/cost field. Matching `recipe_id` is
**case-insensitive**. When writing the audit, report each `recipe_id` in
canonical form: trimmed and upper-cased (e.g. ` r-12 ` -> `R-12`).

If the batch CSV has more than one row for the same `recipe_id` after that keying,
the **last row in the file wins** for every field. Derived `recipe_count` counts
unique recipes after last-wins collapse.

## Cost claim validity

A recipe's displayed "$X per serving" claim must be recomputed from the CURRENT
reference prices (after register override), using the recipe's own ingredient
quantities and serving count. True cost per serving is:

`(chicken_lb x $4.25) + (rice_cups x $0.65) + (asparagus_lb x $3.25) + (extra cost if any)`
divided by the parsed serving count.

**Half-up rounding:** round that recomputed cost per serving to **2 decimal
places using half-up rounding** (0.005 rounds away from zero to 0.01) BEFORE
comparing to the claimed figure. If the rounded cost exceeds the claimed figure
by **at least** the tolerance ($0.25), the claim is `COST_CLAIM_INVALID`. A
rounded delta of exactly $0.25 is also `COST_CLAIM_INVALID`; only a delta
strictly below $0.25 is compliant (`none` for this rule).

Do not round the claimed figure before the compare — parse it as a number after
trim and subtract from the rounded true cost.

## Pantry-staple exclusion

**Exception — pantry-staple ingredients.** Treat `extra_is_pantry_staple` as
affirmative **only** when the trimmed value is exactly `true` / `TRUE` / `True`
(case-insensitive exact token). Tokens such as `yes`, `1`, `Y`, `Truee`, `TRUE!`,
`true.`, or blank are **not** pantry staples. When the flag is affirmative, the
extra ingredient's cost is excluded from the cost computation entirely,
regardless of its listed price. Otherwise the listed `extra_cost_usd` is
included. If `extra_cost_usd` is blank or unparseable and the pantry flag is
not affirmative, treat the extra cost as `0.00`.

## Stale reference price

Every recipe's own cost math must be checked against the current chicken reference
price ($4.25/lb after register override). Compare `chicken_price_used` **numerically**
after trim (`4.25` and ` 4.25 ` both match $4.25; `4.00` does not). A blank or
unparseable `chicken_price_used` does **not** match — including currency-prefixed
strings such as `$4.25`, text tokens, or values with two decimal points.
Scientific notation that Python/float can parse (e.g. `4.25e0`) is numeric.
A recipe whose logged chicken price does not match is `PRICE_SHEET_STALE`,
independent of whether its final claim still happens to hold once the current
price is used.

## Serving count

Parse `serving_count` after trim: a leading `+` is allowed; numeric strings such
as `02`, `2.0`, or scientific notation such as `1e1` are numbers. A recipe with
no usable serving count — blank, whitespace-only, unparseable, a parsed value of
zero, or a negative value — cannot have its per-serving claim verified. This is
`SERVING_COUNT_MISSING`, and no other check applies to that recipe.

Fraction strings such as `3/2` or `1/3` are **not** valid floats and are
`SERVING_COUNT_MISSING`. Tokens `nan` / `inf` / `-inf` (any case) are not usable
serving counts (`SERVING_COUNT_MISSING`). A negative serving count (e.g. `-2`,
`-0.5`) is treated the same as blank.

## One finding only (precedence)

Each recipe gets exactly one finding. No `|` joins. First match wins:

`SERVING_COUNT_MISSING` > `PRICE_SHEET_STALE` > `COST_CLAIM_INVALID` > `none`

A recipe with a stale chicken price is `PRICE_SHEET_STALE` even if its recomputed
cost also exceeds the claimed figure beyond the tolerance, because the stale-price
check is independent of the claim-validity check.

## Finding names

`COST_CLAIM_INVALID`, `PRICE_SHEET_STALE`, `SERVING_COUNT_MISSING`, `none`.

## results.json

Computed after last-wins collapse:

- `recipe_count` — unique recipes in the audit
- `flagged_count` — findings other than `none`
- `cost_claim_flagged_count` — finding equals `COST_CLAIM_INVALID`
- `stale_price_flagged_count` — finding equals `PRICE_SHEET_STALE`
- `compliant_count` — finding equals `none`
