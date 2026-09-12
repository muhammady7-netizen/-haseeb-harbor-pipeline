# Autonomous decision policy

This file governs **autonomous mode only** (`harbor-auto` / `run_auto.py`). In interactive mode
the orchestrator asks the user and this file does not apply.

## The one rule

> **Decide, then prove it.** Verification replaces the human, not caution.

The purpose here is to salvage rejected tasks without a person in the loop. A run that stops
half-repaired and files a ticket has salvaged nothing, so this mode **makes the call** — and then
earns it by re-running the golden and the proof suite in the package's own container.

That is a real guarantee, not a softer one. A human reviewer approving a diff would not have
re-run the container; the proof suite does, on every change.

An earlier version of this file said autonomous mode must never turn an "ask" into a "yes". That
was written before step 11 could execute in Docker. Now that a change can be *checked*, refusing
to decide is no longer the safe option — it is just an unfinished repair.

## The table

### The test that replaces the human

You are salvaging rejected tasks. A repair that stops half-done and waits for review has not
salvaged anything. So **decide, then prove it** — the proof suite is what makes deciding safe:

> **Act when you can verify. Escalate only when you cannot.**
>
> A change is verified when the golden still scores **reward 1** in the package's own container.
> If it fails, revert that change and take the smaller branch. Only if no branch verifies do you
> escalate.

**Verify per decision with the golden only — never the whole proof suite.** Measured on the
pilot: the image build costs ~9s once per task, and each golden check inside it ~1s. The full
`proof_suite.py --run --docker` pass costs ~3 minutes, so running it per decision would add
roughly 18 minutes to a task for no extra safety.

```bash
docker build -q -t harbor-verify-<task> <task>/environment          # once per task, ~9s
docker run --rm --network=none -v <task>/tests:/tests:ro \
  -v <logs>:/logs -v <candidate>:/candidate:ro harbor-verify-<task> \
  bash -c 'cp -r /candidate/. /app/ 2>/dev/null; bash /tests/test.sh'
cat <logs>/verifier/reward.txt        # 1 = verified, 0 = revert this change
```

The **full proof suite runs once, at step 11**, over the finished repair. If it reports a
fairness violation or a surviving mutant that the pre-repair baseline did not have, the repair
regressed: identify the responsible change, revert it, and record that as a `decision`
escalation. That ordering — cheap check per decision, one expensive check at the end — is what
keeps the per-task cost flat.

This is a stronger guarantee than review by a human who was not going to re-run the container.

| Decision | Autonomous action | Escalate |
|---|---|---|
| **Disclose a hidden requirement in `instruction.md`** | **Allowed, additively only.** Append a sentence that states the requirement the check already enforces. Never reword, reorder or delete existing prompt text; never change the task's difficulty or intent. Re-run step 01's cold read afterwards: the requirement must now be derivable from the prompt alone. Record the exact diff | only if the golden regresses or the cold read still cannot derive it |
| **Delete a check** | **Allowed when it is provably redundant** — another check fails on every input this one fails on. Prove it with a mutant that both reject. If it is not redundant, narrow it instead and name the requirement thereby ungraded | only if neither redundancy nor a narrowing can be established |
| **Change an expected value** | Change when the replacement is quoted from `instruction.md`, **or** when it is recomputed from the task inputs and the golden still passes. Never copy it from `solution/` | if neither source supports a value |
| **Missing business rule** | **Never invent a rule.** This one does not move: inventing a rule manufactures a fresh hidden requirement, and no amount of verification detects it, because the verifier and the invented rule agree with each other | yes |
| **Mirror drift on arrival** | Take `tests/` as authoritative and re-sync `environment/_app/tests/` to it — that is the direction the engine loads. Record the drift you overwrote | only if the two differ in check *semantics*, not just formatting |
| **Two conflicting spec files** | Use the one the engine actually loads (`load_spec` order) and say so | if both are loadable |
| **Needs a new engine source adapter** | Write the assertion in the task-owned `tests/test_*.py` | only if the logic fits neither the DSL nor pytest |
| **Weighted / fractional reward** | Propose only, change nothing — scoring weights are infrastructure-owned | yes |
| **Golden regression after a fix** | **Revert that change**, try the smaller branch, verify again | only if every branch regresses |

**The one thing that never becomes autonomous** is inventing a business rule. Everything else in
this table is verifiable; that is not, because a verifier built around an invented rule will
happily agree with itself.

Anything not in this table: prefer the smallest change you can verify. Escalate only as a last
resort, and say precisely what you could not verify.

## What still gets fixed autonomously

The policy above blocks scope changes, not repairs. These proceed with no human at all, because
none of them changes what the task measures:

- `equivalence_preserving` — regex-on-CSV → parsed field comparison, quoting fixes, row-order
  decoupling, synonym sets widened to vocabulary the prompt already teaches
- `coverage_strengthening` — adding a check for a requirement the prompt states explicitly
- `evidence_collection` — proof suite, mutation matrix, run archives
- `runtime_repair` — timeouts, missing engine files, mirror re-sync of changes *this run* made

In the measured `code-c284` run, 6 of the 8 steps that did work were entirely in these classes.

## The escalation record

Every auto-resolved decision appends one object to `.harbor-repair/escalations.json`:

```json
{
  "step": "03",
  "what": "edit instruction.md",
  "verifier_quote": "(?i)PR-145.{0,40}74000",
  "prompt_quote": "NONE - the figure 74000 appears nowhere in instruction.md",
  "proposed_but_not_applied": {"old": "...", "new": "..."},
  "action_taken": "narrowed check to the disclosed subset",
  "requirement_now_ungraded": "the 74000 reconciliation figure",
  "policy": "never-edit-instruction-md"
}
```

`requirement_now_ungraded` is mandatory whenever the safe branch reduces coverage. A repair that
quietly stops grading something is worse than one that stops and asks — the log is what keeps it
from being quiet.

### Two kinds of record, and only one blocks

Set `class` on every record. It decides whether a human is asked to look:

| `class` | meaning | drives exit 1 |
|---|---|---|
| `"decision"` | you made a scope-changing call, or you could not verify one | **yes** |
| `"routing"` | infrastructure- or runtime-owned, nothing a trainer can act on — binary `test.sh` reward, tier weighting, `OWN1`, `L8`/`A9` stale evidence, "no verifier changed verdict across N runs" | no |

Measured on the first 680-task batch: **185 of 471 escalations (39%) were routing notes** that
needed no human at all, and they were the reason nearly every task exited 1. A routing note is
context, not a request. Mark it `"routing"` and it stops asking for attention it does not need.

A verified change is **not** an escalation. Record what you did in `auto_resolved[]` with the
evidence — golden reward, proof-suite delta — and move on.

## Reporting

The final report must state, in this order:

1. per-step verdicts
2. lint before → after
3. **`N decisions auto-resolved — see escalations.json`**
4. the mirror → Oracle → battery re-run list

Exit **1** only when at least one record is `class: "decision"` — a scope call you made that could
not be verified, or one you had to leave undone. Routing notes never set it.

A run that changed things and verified every change exits **0**. That is the target state, and on
a salvage batch it should be the common one.
