# Task

Recompute this batch of meal-prep recipes' per-serving cost claims against the recipe cost claim standard before the shorts post (honor the secondary price register override, trim, last-wins, exact-true pantry tokens, **half-up round-to-2dp before compare**, inclusive $0.25 tolerance, and one-finding precedence stated in the standard). Use the current reference prices after applying the register — not the obsolete base-sheet alone, and not any price a recipe's own notes cite — and remember that not every extra ingredient counts toward the true cost. Also flag any recipe whose own math relied on an out-of-date chicken price, and any recipe with no usable serving count (including **negative** servings, **fraction strings** like `3/2`, and `nan`/`inf`). Currency-prefixed chicken prices such as `$4.25` are unparseable and therefore stale. Save `recipe_cost_audit.csv` with **exactly two columns** — header `recipe_id,finding` only (one data row per unique recipe; no extra diagnostic columns and no pipe characters) — using finding values `COST_CLAIM_INVALID`, `PRICE_SHEET_STALE`, `SERVING_COUNT_MISSING`, or `none`. Then write `recipe_cost_memo.md` (at least 1500 characters) explaining each finding class, how the secondary register changed current prices, half-up rounding before the tolerance compare, and which recipe's extra ingredient the standard excludes from cost. Cite **R-44** (truffle oil) as the pantry-staple exclusion example. Also mention **R-51** (or another negative-serving recipe) with `SERVING_COUNT_MISSING`, **R-104** (or another `$`-prefixed chicken price) with stale/unparseable pricing, **R-103** (or another fraction serving) with missing servings, and **R-171** or **R-135** with the exact-$0.25 tolerance boundary after half-up. The memo must reference the last-wins rule, the secondary price register, the tolerance boundary, the pantry-staple exclusion, the precedence rule, and the stale-price / blank-or-unparseable chicken-price check. When you name a recipe ID next to a finding class or keyword (e.g. `COST_CLAIM_INVALID`, `PRICE_SHEET_STALE`, `SERVING_COUNT_MISSING`, stale/precedence, truffle/excluded, half-up/tolerance), the ID and that keyword may appear in **either order** within about 300 characters of each other.

---
Save your deliverables into your current working directory using exactly these filenames:
    - `recipe_cost_audit.csv` — Per-recipe cost-claim audit
    - `recipe_cost_memo.md` — Markdown memo (minimum 1500 characters)
    - `results.json` — a JSON object with exactly these keys and no others: `recipe_count`, `flagged_count`, `cost_claim_flagged_count`, `stale_price_flagged_count`, `compliant_count`
    10|- Writing those files is the required deliverable and must be your final action; confirm each one exists before you answer.

---

## Working environment

- Your current working directory is `/app`, and it is writable.
- The read-only attachments referred to as `input/` are at `/app/input`.
- Write every deliverable into `/app`, at the exact filenames listed above. Do not nest files in subdirectories.


Note: Scientific notation in serving_count (e.g. 1e1 = 10) is a valid numeric string. Fraction strings like 3/2 are NOT valid floats. Currency prefixes like $ are NOT valid in numeric chicken_price_used fields. Round recomputed cost half-up to 2 decimals before the inclusive $0.25 tolerance compare. This standard was revised for v13 densification with 220 recipes.

The memo must explain: which recipes have pantry staples excluded from cost (and that only exact 'true'/'True'/'TRUE' counts), which recipes have stale chicken prices, which recipes have missing serving counts, which recipes have cost claims that exceed the $0.25 tolerance after half-up rounding, and how duplicate recipe IDs are resolved (last row wins).
