# Task

Audit the attached randomisation list and amendment ledger for study AR-118 against the trial's randomisation charter before the monitoring report goes out. Save `stratum_balance.csv` with the columns `factor,level,subjects,active,control,active_pct,out_of_sequence,status`, with a row for the study overall (`factor=overall`, `level=all`) and a row for each level of each stratification factor. Use factor labels `site` (levels `S1`, `S2`, `S3`) and `severity` (levels `mild`, `severe`) — not longer synonyms. `status` is `within_tolerance` or `outside_tolerance`, and `out_of_sequence` carries the sequence findings for the levels the charter tests them at. Save `block_balance.csv` with the columns `stratum,block_id,subjects,active,control,block_status`, one row per block, where `block_status` is `within_tolerance`, `outside_tolerance` or `not_assessed`. Then write `randomisation_findings.md` on the overall drift, which stratification levels are outside tolerance, which blocks deviate and which do not, every subject allocated out of sequence (list each one by its subject ID), and that the amendment ledger was reconciled/applied before the tests.

The attachments are provided read-only at: `input/randomisation_charter.md`; `input/allocations.csv`; `input/allocation_amendments.csv`. Read and reconcile them there. Save your deliverables into your current working directory using exactly these filenames:

- `stratum_balance.csv` — Overall and stratum-level balance
- `block_balance.csv` — Block-level balance
- `randomisation_findings.md` — Markdown randomisation findings
- `results.json` — a JSON object with the keys `active_proportion_pct`, `strata_outside_tolerance`, `blocks_assessed`, `blocks_outside_tolerance`, `out_of_sequence_allocations`. `active_proportion_pct` is the overall percentage rounded to one decimal using the charter's half-up rule. Each of the other four values must be a JSON integer count: stratification-factor levels outside tolerance (excluding the separate overall row), complete blocks assessed, assessed blocks outside tolerance, and allocations found out of sequence, respectively.

Writing those files is the required deliverable and must be your final action; confirm each one exists before you answer.
