# bus-b50-b10-streaming-target-variance-attribution

Split a single's streaming shortfall across its campaign channels.

## What the task does

The agent receives a release campaign's plan, placement log, streaming ledger, and calendar,
plus a standing attribution note that is the sole authority for how the shortfall to target
is split into three parts (placements effect, conversion effect, residual reach effect).

The agent must compute, per channel:
- How many placements count as delivered (ran in the campaign window, not cancelled, not
  guaranteed streams).
- The delivered reach and streams from the ledger (campaign weeks only, excluding guaranteed
  streams rows, including organic rows and negative corrections).
- The three-part split of the shortfall, taken in order, with halves rounded away from zero.

The agent delivers a CSV register (`shortfall_attribution.csv`), a markdown review
(`campaign_review.md`), and a JSON summary (`results.json`).

## Why it is non-trivial

The attribution note contains subtle rule interactions that a surface reading misses:
- A ledger row naming a placement not in the placement log is organic (rule 3.5).
- A placement that ran in a different week than planned still counts if inside the window
  (rule 2.1).
- Guaranteed-streams rows are excluded from both placement counts and ledger totals
  (rules 2.4 and 3.2).
- Negative stream rows are counted as-is (rule 3.4).
- The first two parts are rounded halves-away-from-zero; the residual is the balance
  (rule 5.4).

## What the bundle contains

- `instruction.md` — the prompt
- `environment/input/` — the campaign data and attribution note
- `environment/Dockerfile` — pinned python:3.12-slim-bookworm with verifier deps
- `tests/` — verifier.json (13 checks), test.sh, test_outputs.py, score.py, rl_world_verifiers/
- `solution/` — golden deliverables, solve.sh, golden_trajectory.json
- `evaluations/` — oracle and nop trial records
