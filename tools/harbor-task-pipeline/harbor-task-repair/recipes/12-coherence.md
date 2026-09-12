# 12 · Coherence — does the package still make sense as a whole?

**This step always runs**, even when every prior step returned `not_applicable`.

Twelve subagents each made a locally-correct change without seeing the others. That is exactly
the situation in which a package ends up internally inconsistent while every individual edit was
right. This step is the only one that looks at the whole.

## Applicability probe

None. Always applicable.

## Part A · Review the entire diff

```bash
cd <task> && git diff 2>/dev/null || diff -r <pristine-copy> <task>
```

Read **every** changed hunk and answer:

1. **Is every change one of the four classes?** `equivalence_preserving`,
   `coverage_strengthening`, `evidence_collection`, `runtime_repair`. Anything else is a
   weakening and must be reverted.
2. **Do two steps contradict?** Step 04 adding a check that step 09 then proposed deleting; step
   05 converting a check that step 08 deduplicated away; step 06 widening something step 03
   narrowed. Resolve in favour of the invariant, and say which you kept.
3. **Is the check count sane?** Target 8–20. If earlier steps added coverage without pruning,
   say so — it is a legitimate outcome, but the user should know.
4. **Did anything drift outside scope?** Any edit to `solution/`, `evaluations/`,
   `rl_world_verifiers/`, `qc_report.html`, `review.csv`, or `environment/` beyond timeouts must
   be reverted now.

## Part B · Structural gates

```bash
python scripts/protect_hashes.py <task> --verify .harbor-repair/protected.json
diff -rq <task>/tests <task>/environment/_app/tests
python scripts/lint_verifiers.py <task>
```

- Protected hashes **unchanged** — if not, stop and report; something breached scope.
- Mirror **in sync** — every `tests/` change reached `environment/_app/tests/`, or the change
  never reaches the container and every number since measures the old task.
- Lint error count **not higher** than `.harbor-repair/lint-before.json`.

## Part C · Contract closure

Re-read `.harbor-repair/contract.json` and confirm, requirement by requirement:

- every requirement maps to at least one surviving check
- every surviving check maps to at least one requirement
- every `open_question` was either settled by a user decision, or is still genuinely open and
  listed as such

This is the invariant, restated as a checklist. If it does not close, the repair is incomplete —
say so rather than rounding up.

## Part D · Evidence status

**Any verifier change voids the existing run evidence.** Do not let a repaired package keep its
old numbers.

State the required follow-up verbatim:

```
Verifiers changed. evaluations/ is now stale and describes a package that no longer exists.
Required, in order:
  1. re-sync environment/_app/ mirror        (done, verified above)
  2. re-run Oracle                            -> must be exactly 1.00
  3. re-run the model battery                 -> old k/n is void
Oracle 1.00 is necessary, not sufficient: the proof suite in step 11 is what shows the repair
worked.
```

Never fabricate a number. Never report a pass rate the repaired package has not earned.

## Part E · Final report

```
task:              <path>
mode:              fix | dry-run
steps:             12 run, 5 applied, 4 not applicable, 2 escalated, 1 needs decision
files changed:     <n>
lint:              <before errors/warnings> -> <after>
protected hashes:  unchanged
mirror:            in sync
contract closure:  11/11 requirements covered, 0 unmapped checks
proof:             10/10 mutants rejected, 6/6 representation variants pass
escalations:       <n>  (see .harbor-repair/escalations.json)
verdict:           repaired-and-proven | repaired-unproven | partial | blocked
required next:     re-sync -> Oracle 1.00 -> fresh battery
```

`repaired-unproven` is an honest and common outcome — use it whenever step 11 could not run in
full. Do not upgrade it.

## Prohibited

- Declaring success while the contract does not close.
- Declaring success while step 11 returned `proposed`.
- Reporting a pass rate that was not re-earned after the changes.
- Leaving `.harbor-repair/` inside the task folder — it must never ship to the client.

## Acceptance

Diff reviewed hunk by hunk; protected hashes unchanged; mirror in sync; lint not worse; contract
closes; the re-run list is stated.

## Return

```json
{"step":"12","applicable":true,"verdict":"fixed",
 "files_changed":[],"findings":1,"needs_decision":null,"spillover":[],
 "one_line":"coherent: 11/11 requirements covered, mirror synced, hashes intact; battery must be re-run"}
```
