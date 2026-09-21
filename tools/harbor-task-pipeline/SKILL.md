---
name: harbor-task-pipeline
description: Take one or more flagged Harbor or Company Bench tasks from broken to shippable in one run — repair the verifier defects, package the task, gate the package against the twelve repackaging checks, remediate what the gate finds, and re-run the gate to prove the fixes landed. Use when asked to fix and ship a task, prepare a task for delivery, run the QC gate on a task package, or check whether a repaired task is ready to hand over. For diagnosing a single verifier defect without packaging, use harbor-task-repair directly.
---

# Harbor task pipeline

Wraps two tools that are useless apart: `harbor-task-repair` fixes the task, `repackaging-qc-gate`
proves the package is deliverable. This runs them in the right order with the right defaults.

## Just run it

```bash
python <skill-dir>/run.py <task-folder> [more folders...]
```

`<skill-dir>` is the folder holding this SKILL.md - when installed, that is
`.opencode/skill/harbor-task-pipeline/`. Run it from the directory that contains the task, and
stream its output to the user as it goes: a repair takes 20-90 minutes and silence looks like a
hang.

Do not re-implement the stages. Do not call `run_auto.py` or `qc_gates.py` yourself unless the
user asks for one stage alone — the orchestrator handles staging directories, the two-pass gate,
and the failure modes below, and doing it by hand reintroduces them.

## Before the first run in a fresh environment

```bash
python run.py --doctor
```

It reports Python version, opencode, the bundled tools, a TOML reader, and the verifier engine's
dependencies. Fix what it flags before spending a long repair run.

## Flags that matter

| flag | when |
|---|---|
| `--check-only` | Package and gate only. No opencode, no model spend. Use when the task is already repaired, or to see the packaging state before committing to a repair. |
| `--dry-run` | Repair diagnoses and applies nothing. |
| `--repair-only` | Stop after stage 1. |
| `--jobs N` | Repair N tasks concurrently. Each spawns containers — on 16 cores do not exceed 12. |
| `--model p/m` | opencode model override. |
| `--timeout S` | Per-task repair ceiling. Default 7200s; raise to 10800 for heavy tasks. |

## Reading the outcome

Exit `0` everything fixable is fixed · `1` findings remain for a human · `2` environment or input
problem · `130` interrupted.

The run prints `blocking: N -> M`. **M is the number that matters**, and the run separates two
kinds of leftover:

- **Still open** — real findings. Read `.work/gate-after.json`; each names task, file and evidence.
- **Expected residual** — G06, G10, G11, G12. These cannot be closed by repackaging and are not
  defects in the repair. Report them as expected, never as failures the user must chase.

## What this pipeline will not do

- **It will not invent a business rule, expected value or tolerance.** A repair that cannot be
  derived from the task's own materials is escalated, not guessed.
- **It will not delete a file it did not create.** A pre-existing `.orig`, `.bak` or `.rej` is
  task content until proven otherwise — several tasks ship one as deliberate fixture data.
- **It will not rename two packages to the same name.** Where two declare the same `task.name`,
  both keep their original filenames and the collision is reported for a human decision.
- **It will not reconcile `review.csv` to the packaged rewards.** The finalization pipeline
  regenerates both documents from its own runs; doing it here aligns them to superseded evidence.

## Failure modes worth knowing

**Tasks outside the working directory.** opencode only reads inside the directory it started in.
`run.py` checks this before spending anything and tells the user to `cd` first. If you see every
subagent fail on its first read, this is why — it is a path problem, not a task problem.

**Missing verifier dependencies.** Without `pytest pydantic jsonpath-ng openpyxl python-docx
python-pptx pypdf tenacity litellm`, the repair's proof step cannot execute the task's own
verifier. The run still completes, but the result is *unproven* rather than certified. `--doctor`
catches it; do not let a batch start without it.

**A gate class that fires on nearly every package is a broken check, not N defects.** The gate's
own spec says so. Open one package and confirm the finding against the actual tree before acting
on it — a path assumption in the checker looks exactly like a corpus-wide defect.

## Answering "can I just ask for it"

Yes. Once installed, a user can say *"fix and package the task in ./my-task"* and you invoke this
skill and run the command above - they never type it themselves. The direct command exists for
scripting and CI; the two routes do identical work.

If the skill is not installed yet, the bundle's `install.py` sets up `.opencode/skill/`,
`.opencode/agent/` and the permission config in one step:

```bash
python <bundle>/install.py            # this repo
python <bundle>/install.py --check    # what is installed
```

Without that install the repair stage cannot start: `run_auto.py` requires the `harbor-auto` and
`harbor-fixer-auto` agent definitions, and without the permission config the run stops on
approval prompts instead of completing unattended.

## Full detail

- `README.md` — the trainer-facing quickstart.
- `repackaging-qc-gate/REPACKAGING-QC-GATE.md` — all twelve gates: detection, rationale,
  remediation, and what each must **not** flag.
- `harbor-task-repair/SKILL.md` — the repair orchestrator's own contract.
