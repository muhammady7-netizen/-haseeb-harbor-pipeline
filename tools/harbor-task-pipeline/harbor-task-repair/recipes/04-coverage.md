# 04 · Coverage — what nothing checks

**The false-pass direction of the invariant.** Present in 68% of audited tasks, and it is
usually the *substantive* half that is missing: the reasoning, the exception handling, the
recommendation — while the checks fuss over formatting.

**This step runs before any pruning.** 53% of tasks are simultaneously over-constrained and
under-covered; a pass that only removes checks leaves the task measurably under-graded.

## Applicability probe

Requires `.harbor-repair/contract.json`. If it is missing, return `blocked` — do not guess the
requirement list from the checks, which is exactly the anchoring failure step 01 exists to avoid.

Map every `contract.json` requirement to the check that would catch its absence. Any requirement
with no such check is a gap.

## Diagnose

Build the bidirectional map. This step owns direction 1; step 03 owns direction 2.

| Requirement | Quote | Check that catches its absence | Verdict |
|---|---|---|---|
| R4 | "flag any that breach the settlement-window policy" | `breach_set_correct` | covered |
| R7 | "explaining each breach" | — | **GAP** |

Then check the specific things that are usually missed even when a requirement looks covered:

- **The full ID set** — does the check verify every required row, or a sample? Exact row count,
  exact ID set, no duplicates.
- **Every required field** — a passing output with a wrong value in an ungraded column is a
  false pass.
- **Joins and grain** — is the relationship checked, or only the endpoints?
- **Exclusions** — is the record that *should* be filtered actually verified absent?
- **Cross-file totals** — do the artifacts reconcile with each other?
- **Negative cases** — is there a check that fails when a wrong answer is submitted, not just
  one that passes when the right one is?
- **Side effects** — for connector tasks, is the gym state checked (channel created, ticket
  filed), or only that a file appeared?

## Fix

Add the missing check at the right tier. Most gaps are T1 (primary objective) or T3 (decoy
handling) — the parts that carry analytic weight.

Two hard rules:

**1. A new check must be gradeable from the prompt alone.** If you cannot write a fair check
because the prompt never says what "done" means, the prompt is under-specified. Say so and
return `needs_decision` — do not invent a rule, which just creates a fresh hidden requirement.

**2. Recompute the expected value from read-only inputs.** Never copy a constant out of
`solution/`. See step 08.

Prefer one structured check over many: compare the parsed table (rows matched against rows
expected, keyed on the identifier, order-independent) rather than emitting one check per row.

Change class: `coverage_strengthening`.

## Prohibited

- Guessing the requirement list from the existing checks.
- Adding a check for something the prompt does not ask.
- Copying an expected value from the golden.
- Adding a per-row family. One table check, not 110.

## Acceptance

Every `contract.json` requirement maps to at least one check. Mutating the newly-covered
requirement now fails, and demonstrably did not before.

## Return

```json
{"step":"04","applicable":true,"verdict":"fixed",
 "files_changed":["tests/verifier.json","environment/_app/tests/verifier.json"],"findings":2,
 "needs_decision":null,"spillover":[],
 "one_line":"added 2 checks: memo explains each breach (T4), cancelled transfers excluded (T3)"}
```
