# 08 · Independence — duplicates, subsets, and copied constants

Two distinct defects with one theme: a check that does not add an independent protection.

## Applicability probe

```bash
python scripts/lint_verifiers.py <task> --json    # code A11
```

Plus: grep the expected values against `solution/` — any constant appearing in both is a
candidate for the copied-constant defect.

## Shape 1 · Duplicate or subset checks

Two checks reading the same source and asserting the same thing, or a narrow check wholly
contained in a broader one.

**Cost:** one requirement gets double weight — under binary reward, double veto. And it masks
coverage: three checks on one fact can look like three checks on three facts.

**Test:** removing this check should reduce a unique protection. If it does not, it is a
duplicate.

**Fix, and the constraint on it.** One source skill forbids automatic deduplication because
duplicates can affect weighting. That is right in general, so:

- **Reward is binary** (`test.sh` emits 1/0 — lint code `OWN1`): removing a duplicate provably
  cannot change any score. **Safe to apply.**
- **Reward is weighted or fractional:** **propose only**, return `needs_decision`.

Keep the broader check; drop the subset. Give every survivor a unique requirement key.

## Shape 2 · Expected values copied from the golden

The check compares against a constant lifted out of `solution/final_answer.md` rather than
recomputed from the inputs.

**Why it is worse than it looks.** It grades *agreement with the reference*, not correctness. If
the golden contains an error, every run that gets the answer *right* fails — and no amount of
Oracle-passing will reveal it, because the golden agrees with itself.

```python
# WRONG - inherits any error in gold
expected_total = 48231.55

# RIGHT - recomputed from the inputs the model also had
expected_total = sum(r["amount"] for r in read_rows("input/deposits.csv")
                     if r["status"] == "SETTLED")
```

**Fix:** recompute from read-only inputs. `equivalence_preserving` when the recomputed value
matches; if it **does not** match the golden, stop — you have found either a wrong golden or a
wrong rule. Escalate; never re-derive the golden yourself.

## Shape 3 · Derivation isolation

A subtler variant, distinct from answer leakage. `solution/` and `tests/` may be correctly absent
from the image, and the verifier can still be exploitable if it **recomputes expectations from
agent-writable files**. Both conditions must hold to be a defect:

1. the verifier derives its expected value from a file in the workspace, and
2. the agent can write that file.

`chmod a-w` is not a control in a root container. If both hold, the expectation must be derived
from a read-only source instead.

## Prohibited

- Auto-deduplicating under any non-binary reward scheme.
- Deleting a check without naming the requirement thereby ungraded.
- Re-deriving the golden when a recomputed value disagrees with it. Escalate.

## Acceptance

Removing any surviving check reduces a unique protection. No requirement gains weight merely by
being asserted twice. Every expected value is derived from a read-only input.

## Return

```json
{"step":"08","applicable":true,"verdict":"fixed",
 "files_changed":["tests/verifier.json"],"findings":3,
 "needs_decision":null,"spillover":[],
 "one_line":"binary reward: dropped 2 duplicate checks; recomputed 1 copied constant from inputs"}
```
