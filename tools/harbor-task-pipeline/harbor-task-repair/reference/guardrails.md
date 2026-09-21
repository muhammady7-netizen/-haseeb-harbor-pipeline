# Guardrails

Binding on the orchestrator and every subagent. Merged from six independent repair skills; where
they disagreed, the resolution and its reason are recorded at the bottom.

## Never touch

| Path | Why |
|---|---|
| `instruction.md` | Changes the task contract. **User decision required, every time.** |
| `solution/` (gold answer, golden trajectory, expected diff) | The golden is a fixed point. If the golden is wrong, escalate — never re-derive it. |
| `evaluations/` | Run archives are evidence. Editing them is falsification. |
| `tests/rl_world_verifiers/` | The grading **engine**. Infrastructure-owned. **Carve-out:** a task's own source adapter under `sources/` (any `.py` that is not one of the shipped generic adapters `csv/json/md/xlsx/docx/pdf/pptx/text/filesystem/artifacts/response/registry/__init__`) is **task-owned and editable** — that is where the P1 evaluator module lives. |
| `qc_report.html`, `review.csv` | Client QC records. |
| `environment/` | Except timeouts. |
| The harness-injected `## Working environment` tail of `instruction.md` | Frozen. Only the authored brief is ever editable. |

Editable: `tests/verifier.json` / `tests/manifest.json`, `tests/` helper modules you own, a
task-specific source adapter under `tests/rl_world_verifiers/sources/`, `task.toml` timeouts, and
the corresponding `environment/_app/tests/` mirror.

## Never do

- **Never weaken a check to make a golden or a model run pass.** No repair is a weakening.
- **Never delete a check to clear a finding** without naming the requirement thereby ungraded and
  confirming a wrong answer still fails.
- **Never mutate the grader to admit the golden and nothing else.** Repair changes *what is
  required*, not *what is matched*.
- **Never make checks pickier to raise difficulty.** That re-adds the brittleness you removed.
  Difficulty belongs in the data.
- **Never add a disclosure sentence you would not have written first.** If the disclosure reads
  as verifier transcription, drop the check instead.
- **Never disclose the answer.** Disclose *representation* — format, vocabulary, which topics
  must be covered. Never the finding values themselves.
- **Never certify from a golden pass alone.**
- **Never count a verifier crash, timeout, provider error or sandbox failure as a rejected
  mutant, a model failure, or evidence the answer was wrong.**
- **Never fabricate a run result.** Say what must be re-run.
- **Never invent business rules, expected values, join logic, tolerances, or scoring policy.**
- **Never bulk-delete.** One deletion, one reason, one line.
- **Never report a suspicion as a finding.** Every finding quotes the prompt text *and* the
  verifier pattern. A finding citing neither is noise.
- **Never leave a hidden requirement as-is.** Disclose, drop, relax, or relocate — pick one.

## Always do

- **Hash protected files before and after every edit.** If a protected hash changes, abort and
  report. (`scripts/protect_hashes.py`)
- **Reject symlinks** before reading or writing: the resolved target must be a regular file
  inside the task root.
- **Keep the mirror in sync.** Every `tests/` change propagates to `environment/_app/tests/`, or
  the change never reaches the container and every number since measures the old task.
- **Write findings outside the package.** `.harbor-repair/` sits beside the task folder, never
  inside it — auditor artifacts must not ship to the client.
- **Never create a backup copy inside the task tree.** No `verifier.json.orig`, no
  `Dockerfile.bak`, no `tests-orig/`, no `step05-backup/` under the task folder. The task tree is
  the deliverable and ships verbatim; every byte in it is something the client receives. You do
  not need a backup — the pristine original is in the source bucket and the runner snapshots the
  tree before you start. If you want scratch space, use `.harbor-repair/<task>/`.
- **Never delete a file you did not create.** A file already present when you started is task
  content until proven otherwise — including one whose name ends in `.orig`, `.bak` or `.rej`.
  Several tasks ship exactly such files as deliberate fixture data (a stale plan the audit is
  supposed to catch, a superseded Dockerfile). Suffix is not evidence of junk.
- **Prove a widened check with a valid-output regression** — at least one genuinely valid
  non-golden submission passes.
- **State uncertainty as uncertainty.** Never upgrade a suspicion by restating it.
- **Say which tests you actually ran.** A clean verdict is a claim, not a default. A zero-failure
  area in a small sample is an area nobody has stress-tested — say so rather than calling it
  healthy.

## Where the source skills disagreed

Recorded honestly, with the reason the resolution won.

**1. Auto-convert regex, or report it?**
One source forbids automatically reinterpreting regex-heavy checks; others convert freely.
**Resolution: convert, but only with a valid-output regression attached.** The objection is
sound — a silent rewrite can narrow the valid set — but the regression test answers it directly,
and format coupling is the highest-volume defect in the corpus (85% of tasks). Converting without
the regression is prohibited.

**2. Auto-deduplicate checks, or propose only?**
One source forbids automatic dedup because duplicates can affect weighting.
**Resolution: dedup automatically only when the reward is provably binary** (`test.sh` emits
1/0 — the lint reports this as `OWN1`), where removing a duplicate cannot change any score.
Under any weighted or fractional scheme, dedup is **propose-only**.

**3. Auto-sync divergent mirrors?**
One source forbids it because authority must be established first — the two copies may differ
*meaningfully*, and picking one silently changes scoring.
**Resolution: never auto-sync a divergence you did not create.** If root and `_app` already
disagree on arrival, that is a *finding* for the user, with both versions shown. Mirrors you
yourself edit must of course be propagated.

**4. Judge passes: one, or several for agreement?**
One source says reduce to a single pass and not run redundant identical passes; others require
repeats to detect instability.
**Resolution: repeats are for *detecting* instability before shipping, not for scoring.** Grade
the same frozen trajectory at least twice during repair; if verdicts differ the check is unsound.
At run time, one pass.

**5. Is all-or-nothing scoring a defect to fix, or a constraint to live with?**
**Resolution: a constraint here.** It is real (binary `test.sh` in 75.5% of harder non-connector
packages) and it is infrastructure-owned. This skill routes it out at step 00 and reports it.
What the skill *can* do is stop authoring the unfair check that the binary gate then amplifies.
