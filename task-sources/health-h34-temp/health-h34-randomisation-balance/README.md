# health-h34-randomisation-balance

**Task ID:** NONC-B1-1000145  
**Trainer:** Muhammad Haseeb Younas (`muhammad.y7@turing.com`)

## What this task is

A clinical-trial randomisation balance audit for study AR-118. The model receives a monitoring extract (`allocations.csv`) and binding charter (`randomisation_charter.md`). It must check overall allocation drift, stratification balance (site and disease severity), complete-block balance, and within-site sequence integrity.

## Inputs (read-only under `input/`)

- `randomisation_charter.md` — RB-3 charter (2:1 active:control, block size 6, tolerances)
- `allocations.csv` — subject-level allocations with site, severity, block, sequence, arm, date
- `allocation_amendments.csv` — amendment ledger (highest revision wins; void / blank-field rules per charter)

## Deliverables (workspace root)

1. `stratum_balance.csv` — overall + each factor level (`factor,level,subjects,active,control,active_pct,out_of_sequence,status`)
2. `block_balance.csv` — one row per block (`stratum,block_id,subjects,active,control,block_status`)
3. `randomisation_findings.md` — narrative covering drift, strata, blocks, sequence, and that the amendment ledger was reconciled/applied
4. `results.json` — `active_proportion_pct` plus four explicitly defined integer counts: `strata_outside_tolerance`, `blocks_assessed`, `blocks_outside_tolerance`, `out_of_sequence_allocations`

## Why it is non-trivial

- Four separate tests with different tolerances and completeness rules (incomplete blocks are `not_assessed`)
- Sequence integrity is site-local and date-ordered (easy to wrongly compare across sites)
- Block “within tolerance” allows 3–5 active; only &lt;3 or &gt;5 is a deviation
- Figures must round half-up to one decimal and match both tables and `results.json`

## Grading

`tests/test.sh` runs deterministic pytest checks and writes a **fractional** reward (`passed/total`) plus `reward_meta.txt`. In addition to file-contract checks from `tests/verifier.json`, the verifier independently reads `input/allocations.csv` and `input/allocation_amendments.csv`, recomputes all stratum, block, sequence, and summary values under the charter rules, and reconciles the submitted tables and JSON to those input-derived values. Harbor mounts tests only for the verifier; they are not copied into the agent workspace.

## Harbor results (package evidence)

| Check | Result |
|---|---|
| Oracle | reward **1.0** (solution/solve.sh installs gold under solution/files/) |
| Stability | **3/3** repeats reward **1.0** (evaluations/stability/repeat-01..03) |
| GLM-5.2 | Platform runs fresh GLM evaluations during pipeline processing |
| Golden trajectory | solution/golden_trajectory.json - oracle ATIF (agent.name=oracle), not a GLM copy |

**Difficulty / solvability note:** The platform runs fresh Oracle + GLM-5.2 x4 + Harbor Check during pipeline evaluation. Packaged evaluations/ contain oracle + 3 stability repeats only.

## QC notes

Delivery Gate requires `evaluations/` (oracle + GLM r1–r5 + stability), fractional `tests/test.sh`, oracle `golden_trajectory.json`, and a completed 14-row `review.csv`. README claims must agree with bundled Harbor evidence.
