# Task

The board meets next week to declare the final dividend and I need the distributable profits paper. From the attached reserves, the movements in the year and the dividend record, work out the profits available for distribution and whether the proposed final dividend can lawfully be paid. The attached policy is authoritative — read every rule carefully, including when a declared dividend counts as already made, which fair-value gains are realised, what counts as notes to the accounts for the development-cost exception, and how a mixed revaluation reserve splits between realised and unrealised portions.

Save `distributable_profits.csv` with the columns `item,amount_gbp,treatment`, showing the build from retained earnings to distributable profits and including any item you considered and decided needed no adjustment. Use these conventions:

- Each adjustment item gets one row. Deductions (unrealised gains removed from retained earnings, development costs treated as a realised loss, provisions added back) must show a **negative** amount_gbp. Items needing no adjustment must show **0** in amount_gbp.
- Include the total profits available for distribution, the distributions already paid, the maximum further distribution, and the total of capital and reserves not available for distribution (share capital, share premium, capital redemption reserve, and the unrealised portion of the revaluation reserves) as separate rows in the CSV.
- For any dividend whose status in the record is not exactly `Paid` after trimming whitespace, include a row showing the dividend description with amount_gbp 0 and the treatment explaining why it does not count as paid.

Then write `dividend_memo.md` explaining each adjustment, each item you deliberately left alone, and what the board can and cannot declare.

The attachments are provided read-only at `input/distribution_policy.md`, `input/reserves.csv`, `input/movements.csv`, and `input/dividends.csv`. Save your deliverables into your current working directory using exactly these filenames:

- `distributable_profits.csv` — Build from retained earnings to distributable profits
- `dividend_memo.md` — Markdown memo for the board
- `results.json` — a JSON object with the keys `distributable_profits_gbp`, `non_distributable_capital_gbp`, `dividends_paid_gbp`, `maximum_further_dividend_gbp`, `proposed_dividend_is_lawful` (a boolean: `true` if the proposed final dividend may lawfully be paid, `false` otherwise)

Writing those files is the required deliverable and must be your final action; confirm each one exists before you answer.

## Working environment

- Your current working directory is `/app`, and it is writable.
- The read-only attachments referred to as `input/` are at `/app/input`.
- Write every deliverable into `/app`, at the exact filenames listed above.
