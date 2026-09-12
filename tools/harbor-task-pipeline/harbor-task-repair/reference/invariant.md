# The invariant, and the four repair directions

Read this once. Every recipe is a consequence of it.

## The invariant

> **The set of submissions the verifier rewards must equal the set a competent agent could
> produce from agent-visible information alone.**

"Agent-visible" means: `instruction.md`, the input files, and any policy document the prompt
names. It does **not** include the golden answer, the design doc, or what the author happened to
have in mind.

Every defect is a violation in one of two directions:

| Direction | Name | Symptom | Cost |
|---|---|---|---|
| Verifier rewards **less** than the set | **Contract gap** | Correct work fails | False failure — the task looks harder than it is |
| Verifier rewards **more** than the set | **Coverage gap** | Wrong work passes | False pass — the task looks solved when it is not |

Most real packages have **both at once**. In a 117-task audit, 53% were simultaneously
over-constrained and under-covered: 169 hidden requirements sitting beside 200 uncovered ones.
That is why coverage is closed *before* anything is pruned — a pass that only removes checks
leaves the task measurably under-graded.

## The four repair directions

Every finding routes to exactly one. Decide in this order:

**1. Disclose** — the requirement carries real analytic weight, and the form genuinely matters.
Add it to `instruction.md`.
*Requires a user decision.* Only choose this when you would have written the sentence in the
first place. If the disclosure reads as a transcription of the verifier, choose **Drop** instead.

**2. Drop** — the requirement carries no analytic weight. Delete the check.
Most demands on exact wording, byte form, column order and row order land here.
*Requires a user decision*, and you must name the requirement thereby ungraded.

**3. Relax** — a real requirement with several faithful renderings. Widen the check to accept all
of them, while still rejecting wrong answers.
*Safe to apply* — but it must be proven by a valid-output regression (see below).

**4. Relocate** — the value must be exact, but prose cannot carry it fairly. Move the check to a
structured surface the golden already produces (a CSV field, a JSON key).
*Safe to apply.*

## What difficulty is, and is not

The strongest temptation when a task looks too easy is to tighten the grader. **Don't.**

Measured across three independent batches (150 + 50 + 101 tasks), packages that were *clean* on
contract disclosure scored **higher** observed difficulty than packages that hid requirements —
3.60 vs 3.05, 3.56 vs 3.00, 4.35 vs 3.78. Four fully-disclosed tasks scored 0 of 6 strict passes.

**Withheld requirements do not purchase difficulty.** They purchase false failures that look
like difficulty.

If a task genuinely needs to be harder, difficulty belongs in the **data and the reference
material**, never in check pickiness:

- a stale or superseded prior document that must be noticed
- an exemption that mimics a violation
- a compound case where two rules interact
- a self-contradicting record
- a dangling reference
- a distractor sharing the guilty signature

All of those are answer-neutral. None of them make a correct answer fail.

## What a passing golden proves

**Compatibility. Nothing else.**

It shows one artifact satisfies the checks that exist. It does not show the checks are complete,
fair, or independent. Four distinct ways a flawed verifier still passes a run:

- **Brittle** — the run happened to use the accepted phrasing; an equivalent one would fail.
- **Incomplete** — the run was wrong in an ungraded field.
- **Hidden-rule** — the run *guessed* the unstated literal, join grain or rounding convention.
  A pass here is **evidence of a hidden requirement**, not evidence of quality.
- **Latent gap** — the run was correct, but never exercised the verifier's blind spots.

So: never certify a repair from a golden pass, and never write "4 of 4 runs passed, verifiers
look fine."

## Valid-output regression — the test that makes "Relax" safe

Whenever you change a verifier, you must show you did not narrow the valid set:

> Produce at least one **genuinely valid, non-golden** alternative submission. It must pass, with
> zero rejections and zero inconclusive results.

Without this, "relax" and "convert" are indistinguishable from "weaken". With it, they are
provably intent-preserving.

## Change classes

Every edit you make is one of these. **There is deliberately no "weakening" class.**

| Class | Meaning |
|---|---|
| `equivalence_preserving` | Same requirement, wider or more robust matching (Relax, Relocate, format conversion) |
| `coverage_strengthening` | A requirement that was ungraded is now graded |
| `evidence_collection` | Regenerating runs, hashes, proofs — no semantic change |
| `runtime_repair` | Environment or timeout fixes that do not touch what is required |

If a proposed edit fits none of these, it is a weakening and you must not make it.
