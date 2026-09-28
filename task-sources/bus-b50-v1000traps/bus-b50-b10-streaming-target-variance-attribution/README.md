# bus-b50-b10-streaming-target-variance-attribution

Split a single streaming shortfall across its campaign channels.

## What the task does

The agent receives a release campaign plan, placement log, streaming ledger, calendar,
and a standing attribution note that is the sole authority for splitting the shortfall
into placements effect, conversion effect, and residual reach effect.

## Why it is non-trivial

The attribution note contains time-dependent conversion rates (rule 5.6), conditional
PE rounding based on shortfall sign (rule 5.7), and 420 data traps including phantom
placement IDs, guaranteed-streams exclusion, slippage, negative corrections, and
cross-channel references.

## What the bundle contains

- instruction.md, task.toml, review.csv, README.md
- environment/input/ — 6 input files
- environment/Dockerfile — pinned python:3.12-slim-bookworm@sha256
- tests/ — verifier.json, test.sh, test_outputs.py, score.py, rl_world_verifiers/
- solution/ — golden deliverables, solve.sh, golden_trajectory.json
