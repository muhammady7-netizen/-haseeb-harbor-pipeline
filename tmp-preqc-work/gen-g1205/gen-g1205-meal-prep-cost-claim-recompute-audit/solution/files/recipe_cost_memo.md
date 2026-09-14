# Recipe Cost Claim Audit Memo

## Summary

Audited 220 unique recipes after last-wins collapse of duplicate recipe IDs.

- Flagged: 124
- Cost claim invalid: 45
- Stale price flagged: 40
- Serving count missing: 39
- Compliant: 96

## Method

Applied the secondary price register override to obtain current reference prices:
chicken breast $4.25/lb, cilantro-lime rice $0.65/cup, asparagus $3.25/lb.
Draft/proposed register rows and price_sheet_errata_proposed.md were ignored.

For each unique recipe_id (trim + case-insensitive; report upper-case), applied
precedence SERVING_COUNT_MISSING > PRICE_SHEET_STALE > COST_CLAIM_INVALID > none.

True cost was recomputed at current prices, then rounded half-up to 2 decimal
places before the inclusive $0.25 tolerance compare. A rounded delta of exactly
$0.25 is COST_CLAIM_INVALID.

Pantry exclusion uses only the exact true/TRUE/True token after trim; yes/1/Y/Truee/TRUE!/true. do not exclude.

## Pantry staple exclusion

R-44 (truffle_oil, extra_cost $5.00) has extra_is_pantry_staple = True, so its
extra cost is excluded from the computation — finding none. Other exact-true
exclusions include R-03, R-33, R-53, R-66, R-70, R-75, R-95, R-180, R-212, R-218.
Near-miss tokens on R-176 (true.), R-177 (Truee), R-178 (TRUE!), R-219 (TRUE!)
do not exclude — those rows are COST_CLAIM_INVALID when the extra pushes over.

## SERVING_COUNT_MISSING

Negative, zero, blank, whitespace, fraction strings (3/2, 1/3, 2/2), and
nan/inf serving counts are missing. Examples: R-08 (zero), R-10 (blank),
R-11 (whitespace), R-51 (serving -2), R-151 (-1), R-155 (nan), R-103 (3/2),
R-143 (1/3), R-158 (2/2), R-192 (spaced -2), R-199 (pantry True but serving -1
still missing — precedence). Sample: R-08, R-10, R-11, R-16, R-30, R-37, R-42, R-46, R-51, R-63, R-74, R-79 ...

## PRICE_SHEET_STALE

Chicken_price_used must numerically equal 4.25 after trim. Blank, unparseable,
currency-prefixed ($4.25), comma decimals, and near-miss floats are stale.
Examples: R-04 (4.0), R-29 (blank), R-104 ($4.25), R-161 ($4.25 with space),
R-142 (4.250001), R-187 (4.249999), R-15 (stale wins over would-be invalid).
Scientific 4.25e0 / 425e-2 match and are not stale (R-166, R-167, R-208).
Sample: R-04, R-15, R-24, R-29, R-34, R-35, R-45, R-50, R-54, R-58, R-62, R-67 ...

## COST_CLAIM_INVALID

After half-up rounding, claim shortfalls of at least $0.25 are invalid.
Base-price bait rows R-168/R-169/R-200 claim $4.00 while true is $4.25.
R-171 / R-204 claim $1.79 vs rounded true $2.04 (delta exactly $0.25).
R-135 remains an exact-tolerance invalid example. R-64 stays none (under tolerance).
Sample: R-02, R-05, R-09, R-17, R-18, R-19, R-25, R-26, R-32, R-47, R-49, R-59 ...

## Duplicate last-wins

Last row wins across all fields. R-184's long chain ends COST_CLAIM_INVALID.
R-185 ends none. R-186 ends COST_CLAIM_INVALID (yes is not pantry). R-202 ends
SERVING_COUNT_MISSING (fraction 3/4). R-23 ends none; R-24 ends PRICE_SHEET_STALE.

## Precedence

R-15: stale beats cost-claim. R-79 / R-118 / R-182: serving-missing beats stale.
R-183 / R-199: serving-missing beats cost-claim and pantry interactions.

## Conclusion

124 of 220 recipes flagged after
register override, half-up rounding, inclusive tolerance, exact-true pantry
tokens, and one-finding precedence. Memo length exceeds 1500 characters to
document each finding class with recipe anchors.
