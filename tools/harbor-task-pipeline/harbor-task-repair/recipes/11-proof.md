# 11 · Proof — show the verifier detects wrongness

**This step gates step 12.** Everything before it changed the verifiers; this establishes that
the result is both *hard against wrong answers* and *fair to correct ones*.

## Applicability probe

Applicable whenever any earlier step changed a file. If nothing changed, run the paraphrase half
anyway as a baseline and say so.

## Why a passing golden is not enough

A golden pass proves **compatibility**. It does not prove fairness or coverage. Four ways a
flawed verifier still passes:

- **brittle** — the run used the accepted phrasing
- **incomplete** — the run was wrong in an ungraded field
- **hidden-rule** — the run *guessed* the unstated literal, join grain or rounding convention
- **latent gap** — the run was correct but never exercised the blind spots

## Run the harness first

```bash
python scripts/proof_suite.py <task> \
       --output-dir <task-parent>/.harbor-repair/proof \
       --run --docker [--order-required] [--max-mutations 40]
```

It generates and classifies both halves below and writes `proof.json`.

> **Always pass `--docker`.** The package's `tests/test.sh` does `cd /app`, and `/app` exists
> only inside the container. Run it on the host and every check fails for environmental
> reasons, and the harness concludes *"the verifier REJECTS its own golden"* — a **false** V6
> diagnosis. Measured on `code-c100`: host mode reported 45 failed checks and claimed
> "fairness 13/13 proven"; the same task under `--docker` reported `baseline PASSED reward=1`
> and found **11 real fairness violations**. Host mode is not merely uncertifying — it is
> wrong in both directions.

**Flags that matter:**

- `--run` — without it, cases are generated but never executed (`GENERATED_ONLY`).
- `--docker` — **the only certifying mode.** Builds the package's own `environment/` image once
  (layer-cached; the verifier itself then runs in ~3s), mounts `tests/` at `/tests`, stages the
  candidate into `/app`, and reads the verdict from `/logs/verifier/reward.txt`.
  `BLOCKED_NO_DOCKER` means your user is not in the `docker` group — log out and back in.
- `--allow-unsafe-local` — executes the task's pytest **on this host**. Only for a package that
  ships no `environment/Dockerfile`. The report marks `certifying: false`. **Never report a
  repair as proven from this mode.**
- `--order-required` — pass this when `contract.json` shows the prompt fixes row order. Without
  it, the harness treats a reordered file as a fair variant and will wrongly report a violation.

**Statuses:** `PROOF_PASSED` · `FAIRNESS_FAILED` · `HARDNESS_FAILED` · `INSUFFICIENT_COVERAGE`
· `INCONCLUSIVE` · `REQUIRES_RERUN` · `GENERATED_ONLY`.

**Reading `REQUIRES_RERUN`** — the report tells you which of two very different things happened:

- `RUNTIME_ERROR` → the verifier could not execute (missing pytest, import failure, sandbox
  issue). **Not evidence about the task.** Fix the environment or use the declared sandbox.
- `REJECTED` on the baseline → the verifier rejects **its own golden answer**. That is a V6
  defect. Stop; it must be fixed before anything can be proven.

An engine error is never counted as a rejected mutant.

## Never claim proof you do not have

`proof.json` carries a `certifying` field. It is `true` **only** for a `--docker` run that
reached `PROOF_PASSED`. Your verdict follows that field, not your own reading of the mutation
table:

| `proof.json` says | your verdict |
|---|---|
| `certifying: true` + `PROOF_PASSED` | `fixed` — and only here may you use the word *proven* |
| `FAIRNESS_FAILED` / `HARDNESS_FAILED` | `proposed` — the repair is unfinished; list the violations |
| `certifying: false` (host mode) | `proposed` — say *unproven*, never *proven* |
| `RUNTIME_ERROR` / `BLOCKED_*` | `blocked` — an environment fault, not evidence about the task |

This has already gone wrong once in testing: a host-mode run was reported as
"Fairness 13/13 + hardness 108/110 proven" while the certified run on the same task returned
`FAIRNESS_FAILED` with 11 violations. **If the harness did not certify it, you did not prove
it.**

## Part A · Valid-output regression (fairness)

At least one **genuinely valid, non-golden** submission must pass, with zero rejections and zero
inconclusive results. Vary only what the prompt leaves free:

- QUOTE_ALL-quoted CSV, and unquoted
- CRLF and LF line endings
- reordered permitted columns; reordered rows where no order is required
- equivalent numeric notation (`1234.5` / `1,234.50`; `0.5` / `50%`)
- reordered permitted memo sections; a correct paraphrase of each required claim

## Part B · Mutation matrix (hardness)

Build from the task contract and change **one thing at a time**. Every meaning-changing mutant
must fail, **and fail for the intended reason** — a mutant failing on the wrong check is itself a
finding.

| Case kind | Mutation | Expect |
|---|---|---|
| exact-fact | one field value in one row | fail |
| set/list | drop one required ID; add one extra | fail |
| relationship/join | change a join key | fail |
| scope/precedence | flip a precedence or tie-break rule | fail |
| exclusion | re-admit a record that should be filtered | fail |
| aggregate | change a total or count | fail |
| prose/rubric | invert a claim in the memo | fail |
| prose/rubric | replace the memo with disconnected expected tokens | fail |
| hardcoding | hardcode the answer, then change the input fixture | fail |
| representation-only | change quoting/order/notation only | **pass** |

The harness generates `exact-fact`, `set-list`, `aggregate`, `relationship-join`, `prose-rubric`,
`hardcoding` and `representation-only` mechanically from the artifacts.

**`scope-precedence` and `exclusion` it cannot generate** — they depend on which rule and which
record the task's own semantics single out. The report lists them under
`requires_manual_construction`. For each, either build the case by hand from `contract.json`
(flip the precedence rule the prompt states; re-admit the record the prompt excludes) or record
in `proof.json` why the task has no such rule. Anything left in `missing_case_kinds` is a **gap**,
not an exception — and `representation-only` can never be excepted, because it is the fairness
control.

## Part C · Stability

Re-grade one frozen trajectory at least twice with the same configuration. Differing verdicts →
unsound check, back to step 10.

## Safety

- Run against a **disposable proof workspace**. Never mutate the shipped golden or a production
  seed in place.
- Do **not** execute task-provided verifier code on the host for certification. Use the sandbox
  the package declares.
- Reject symlinks before reading or mutating.
- Hash protected files before and after: `python scripts/protect_hashes.py <task> --verify`.
- A verifier crash, timeout or provider error is **never** a rejected mutant. Re-run it; if it
  keeps erroring, that is a runtime escalation.

## Prohibited

- Certifying from a golden pass.
- Counting an infrastructure failure as a rejected mutant.
- Declaring `fixed` when the suite could not run. Say **unproven**.

## Acceptance

Golden passes on repeated executions; every representation-only variant passes; every
meaning-changing mutant fails for its intended reason; every required case kind has a case;
protected hashes unchanged.

## Return

```json
{"step":"11","applicable":true,"verdict":"fixed",
 "files_changed":[".harbor-repair/proof.json"],"findings":1,
 "needs_decision":null,"spillover":[],
 "one_line":"10/10 mutants rejected, 6/6 representation variants pass; 1 mutant failed on wrong check"}
```

Write the full matrix to `.harbor-repair/proof.json`. If any case kind is missing, `verdict`
is `proposed`, not `fixed`.
