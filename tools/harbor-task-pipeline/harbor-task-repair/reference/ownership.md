# Ownership routing

Used by step 00, and by any step that finds a defect it cannot fix.

**One finding has one primary owner.** If work is needed on two surfaces, record a dependent work
item — do not assign two owners to the same surface.

## The three owners

| Owner | Owns | Fixable by this skill? |
|---|---|---|
| **Task (trainer)** | `instruction.md`, the verifier spec, expected values, tolerances, coverage set | **Yes** — this is our scope |
| **Infrastructure** | Sources, parsers, comparison operators, `test.sh`, reward aggregation, core gate, judge harness, runner error handling | No — report and route |
| **Runtime / environment** | Sandbox, connector health, provider errors, timeouts, wrong-agent runs | No — report and route |

## Decision order

Ask these in sequence. The first "yes" assigns the owner.

**1. Is this a runtime artefact rather than a defect?**
Crash, throttle, auth failure, healthcheck failure, wrong agent, missing output, verifier-process
error, timeout, empty response.
→ **Runtime.** Classify the run `ineligible`. It is **never** a model failure or a task failure.
A `1.0` from the wrong agent is invalid; a `0.0` with no model output is not a model failure.

**2. Does the fair check require a capability the engine does not have?**
No parsed-field comparator, no fact extractor, no way to express the invariant in the spec
schema, weighting not honoured.
→ **Infrastructure**, or **shared**: the trainer defines the invariant and the proof cases,
infrastructure supplies the mechanism.
**Never work around a missing engine capability with a larger regex.** That is how format
coupling gets authored in the first place.

**3. Is the defect in reward aggregation rather than in a check?**
Binary `test.sh`, dead score buckets, empty rubric files, core-gate boundaries.
→ **Infrastructure.** Report it with the evidence and move on.

**4. Otherwise — is the requirement, expected value, tolerance, coverage set or check definition
wrong, and expressible in the current schema?**
→ **Task.** Ours to fix.

## Words that do not establish ownership

A finding that mentions "task", "SQL", "verifier" or "scoring", or a state like "retrying", tells
you nothing about who owns it. **Route on root cause, not on vocabulary.** A Layer-5 QC label
alone does not make a defect an agentic repair.

## The binary-reward constraint

Reward is computed by `tests/test.sh`, not by the verifier spec. In most non-connector packages
it is binary:

```bash
if [ $status -eq 0 ]; then echo 1 > reward.txt; else echo 0 > reward.txt; fi
```

Measured across 310 shipped packages: **75.5%** of harder non-connector, **71.2%** of easier
non-connector, and **0%** of connector packages (which already carry `scoring.weights`).

**Consequences you must act on:**

- Any proposal to weight, tier, or partially credit checks is **infrastructure-owned**. Report
  it; do not write it into the spec expecting it to take effect.
- Because every check is an equal veto, a single unfair check zeroes an otherwise perfect
  submission. This makes steps 03, 05, 06 and 07 *more* urgent, not less.
- Deduplication is score-neutral under binary reward — which is why step 08 may apply it
  automatically here, and only propose it under a weighted scheme.

## Escalation register

Anything not task-owned goes to `.harbor-repair/escalations.json`:

```json
{"finding":"<what>","owner":"infrastructure","evidence":"<file:line or quoted output>",
 "blocks":["05","09"],"note":"<max 25 words>"}
```

An infrastructure blocker means the task stays **ineligible** until that system is repaired and
evidence is regenerated. Say so plainly rather than fixing around it.
