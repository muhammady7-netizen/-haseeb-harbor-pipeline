# 09 · Scoring — shape, weight, and what you cannot change

**Read `reference/ownership.md` before doing anything here.** Most of this step reports rather
than repairs, and knowing that in advance saves the run.

## Applicability probe

```bash
cat <task>/tests/test.sh
python scripts/lint_verifiers.py <task> --json    # codes A5, A9, OWN1
```

## The constraint you are working inside

Reward is computed by `tests/test.sh`, not by the verifier spec. In **75.5%** of harder
non-connector packages it is binary:

```bash
if [ $status -eq 0 ]; then echo 1 > reward.txt; else echo 0 > reward.txt; fi
```

Connector packages carry `scoring.weights` and are unaffected (0% binary).

**So: any proposal to weight, tier, or partially credit checks is infrastructure-owned.** Record
it in `.harbor-repair/escalations.json` with the `test.sh` evidence. Do not write weights into
the spec expecting them to take effect, and do not tell the user the task now scores
proportionally when it does not.

## What you CAN fix here

**1. Free points** — checks that pass in every recorded run (lint `A9`). A check that cannot
fail measures nothing and, under any future proportional scheme, raises the score floor.

- **Keep** a T0 deliverable-existence check (cheap catastrophic-failure guard), or a check
  guarding a trap no run happened to hit.
- **Propose deleting** anything that duplicates another check or that no plausible submission
  fails. One deletion, one reason, one line. *Needs decision.*

**2. No-discrimination** (lint `L8`) — no check changed verdict across the whole battery. The
task measures nothing. This is a task-design finding, not a verifier edit: report it and stop.

**3. Per-row explosion** (lint `A5`) — collapse into one table comparison.

**Set expectations honestly:** this is an **authoring** fix — review cost, legibility, and the
per-row hidden-requirement risk. It is **not** a scoring fix. Replaying 1,064 recorded runs
showed collapsing row families changes scores by −0.003 on average. Do not tell anyone it will
improve the pass rate.

## What you must NOT do

- Do not tighten checks to lower a pass rate. If a task is too easy, difficulty belongs in the
  data and reference material — see `reference/invariant.md`. Making checks pickier re-adds the
  brittleness earlier steps just removed.
- Do not hand-edit rewards in `evaluations/`. Ever.
- Do not treat "too hard" as difficulty. A task at ≤1/6 is almost always a brittleness or
  disclosure defect — steps 03, 05, 06 and 07 own it, not this one.
- Do not delete checks to reach a target number. That is denominator gaming, and it changes the
  measurement without changing the task.

## Acceptance

Every surviving check can fail. Any weighting or aggregation finding is in the escalation
register with its owner. No check was tightened to move a score.

## Return

```json
{"step":"09","applicable":true,"verdict":"proposed",
 "files_changed":[],"findings":4,"needs_decision":null,"spillover":[],
 "one_line":"binary test.sh escalated to infra; 3 free points proposed for deletion, awaiting decision"}
```
