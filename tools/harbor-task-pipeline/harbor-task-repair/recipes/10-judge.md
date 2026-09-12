# 10 · Judge — LLM-rubric instability

Judged rubrics are only ~0.5% of shipped verifiers, but in the *rejected* population verifier
non-determinism is the single largest rejection category, and roughly three quarters of the
unstable checks are `rubric:` items. Judged checks are rare in shipped tasks **because tasks that
lean on them tend not to survive.**

## Applicability probe

Any assertion of type `rubric` or `agentic_llm_as_judge`, or a `rubric.toml` with content.
None → `not_applicable`, and that is the healthy state.

## The test that matters

> Grade **one frozen trajectory** with the **same** verifier and judge configuration, at least
> **three** times.

Any difference in verdict means the check is unsound — regardless of which way it fell, and
regardless of whether the majority was correct. A missing, unpaired, or differing repeat is
unstable evidence, not weak evidence.

Note the distinction from run-to-run variation: this is the *same* trajectory, so nothing but the
judge changed.

## Diagnose

Beyond instability, check each rubric item for:

- **Invertible phrasing.** "Avoid X (means Y)" is read backwards by a judge under normal
  operation, failing correct answers. Rewrite as `PASS only if … FAIL otherwise`.
- **Non-atomic claims.** One rubric item asserting three things cannot be diagnosed when it
  fails, and is markedly less stable.
- **Judge contamination.** The judge must see only the artifact it grades — never the ground
  truth alongside it. If it sees both, it is comparing, not grading.
- **Empty or missing rubric file.** A rubric check pointing at an empty file is an engine-level
  fault. **Do not invent criteria to fill it** — escalate to infrastructure.
- **Missing artifact reference.** The item must name which file it reads.

## Fix — in order

**1. Replace with a deterministic check.** Most judged checks in this corpus assert something
recomputable. This is the fix; the rest are fallbacks.

**2. Make it atomic.** One claim per item, with an explicit FAIL branch naming the plausible
near-misses: a bare label with no reason, the wrong entity, a silent omission.

**3. Rewrite invertible phrasing** as `PASS only if …`.

**4. Isolate the judge's input** to the artifact under grading.

**5. Re-test stability.** Three gradings of one frozen trajectory. Still disagreeing → drop the
check and record the requirement as ungraded, or escalate for a semantic comparator.

## On repeat passes at run time

One source skill argues for reducing judge passes to one and not running redundant identical
passes for "agreement". That is right *for scoring* — agreement voting hides instability rather
than fixing it. Repeats belong in **repair**, as the detector above. Ship with one pass, having
proven stability first.

## Prohibited

- Shipping a judged check graded only once.
- Inventing rubric criteria to fill an empty file.
- Treating a majority vote across unstable gradings as a pass.
- Counting a judge timeout, truncated reply or provider error as a failed grading — that is
  runtime, and it goes in the escalation register.

## Acceptance

Three gradings of one frozen trajectory give identical verdicts for every judged item. No item is
invertibly phrased. The judge sees only the artifact it grades.

## Return

```json
{"step":"10","applicable":true,"verdict":"fixed",
 "files_changed":["tests/rubric.toml","tests/verifier.json"],"findings":2,
 "needs_decision":null,"spillover":[],
 "one_line":"1 rubric item -> deterministic check; 1 rephrased from invertible; 3/3 gradings now identical"}
```
