# 00 · Route — is this defect ours to fix?

**Goal:** assign every reported finding one owner, and stop the run early if the blocking defect
is not task-owned. Cheap, and it saves twelve wasted steps.

## Applicability probe

Always applicable. Takes two minutes.

## Inputs

Whatever finding text the user has: a client QC flag, a `review.csv` row, a pipeline
`_rejection.json`, a Layer-5 label, or just "this task is failing".

If there is **no** stated finding, that is fine — record `no_stated_finding: true` and let the
later steps discover defects on their own.

## Procedure

**1. Read the reward shape.**

```bash
cat <task>/tests/test.sh
```

If it emits `echo 1` / `echo 0`, record `reward_shape: "binary"`. This matters everywhere: every
check is an equal veto, so a single unfair check zeroes a correct run. It also means any
weighting proposal is infrastructure-owned.

**2. Route each finding** using `reference/ownership.md`. In order:

- runtime artefact (crash, timeout, wrong agent, provider error, empty response) → **runtime**,
  classify the run `ineligible`
- needs an engine capability that does not exist → **infrastructure** or **shared**
- defect is in reward aggregation, not in a check → **infrastructure**
- otherwise → **task**, ours

**3. Read the golden's rationale** if the finding is about a hidden or over-strict requirement.
Hidden requirements usually originate in a golden that asserts a fact `instruction.md` never
states — the check was written to enforce what the golden happened to say. Knowing this decides
step 03's direction: *disclose* (the requirement is real) vs *drop* (it was incidental).

Read `solution/` **for rationale only**. It is protected; never edit it.

**4. Check for a file-write conflict.** If two findings would edit the same file, or one edits a
surface an unresolved infrastructure finding also affects, record it — sequencing matters.

**5. Write the register.** `.harbor-repair/escalations.json` for anything not task-owned:

```json
{"finding":"<what>","owner":"infrastructure","evidence":"<file:line or quoted output>",
 "blocks":["05","09"],"note":"<max 25 words>"}
```

## Prohibited

- Do **not** edit anything in this step. It plans; it does not repair.
- Do **not** route on vocabulary. A finding mentioning "verifier" or "scoring", or a state like
  "retrying", tells you nothing about ownership. Route on root cause.
- Do **not** treat a Layer-5 QC label as proof the defect is agentically repairable.
- Do **not** record an infrastructure failure as a model failure or a task failure.

## Stop condition

If the **only** finding is infrastructure- or runtime-owned, return `blocked` with the
escalation. The task stays ineligible until that system is repaired and evidence is regenerated.
Do not repair around it.

## Acceptance

Every input finding has exactly one owner and a one-line reason. Nothing was edited.

## Return

```json
{"step":"00","applicable":true,"verdict":"fixed",
 "files_changed":[],"findings":3,"needs_decision":null,"spillover":[],
 "one_line":"3 findings routed: 2 task-owned, 1 infrastructure (binary test.sh); reward_shape=binary"}
```

**Verdict for this step specifically** — it edits nothing, so:

- `fixed` — routing completed; at least one finding is task-owned (or there was no stated finding,
  and later steps should discover defects).
- `blocked` — every finding is infrastructure- or runtime-owned. Stop the run.

Do **not** use `proposed` here. Routing is either done or blocked; there is nothing to propose.
