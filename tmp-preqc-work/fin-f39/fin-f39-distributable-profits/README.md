# fin-f39-distributable-profits

Non-connector Harbor task. Compute distributable profits available for dividend distribution under UK company law, applying a binding distribution policy to reserves, year movements, and dividend records.

## Deliverables

- `distributable_profits.csv` — build from retained earnings to distributable profits, with columns `item,amount_gbp,treatment`
- `dividend_memo.md` — markdown memo explaining each adjustment and the board's position
- `results.json` — `distributable_profits_gbp`, `non_distributable_capital_gbp`, `dividends_paid_gbp`, `maximum_further_dividend_gbp`, `proposed_dividend_is_lawful`

## Inputs

- `input/distribution_policy.md` — the binding policy (realised vs unrealised profits, revaluation surpluses, fair value gains, development costs, provisions, dividend status rules)
- `input/reserves.csv` — reserves including two mixed revaluation reserves with 3 properties each
- `input/movements.csv` — 11 year movements including fair value gains, development costs, and provisions
- `input/dividends.csv` — 5 dividend records including a case-sensitivity trap (PAID vs Paid)

## Verifier

44 deterministic checks: 44 deterministic checks: 3 file-existence, 1 schema, 1 uniqueness, 15 per-item content, 14 memo content, 5 results.json equals, 5 additional trap checks. Fractional reward.
