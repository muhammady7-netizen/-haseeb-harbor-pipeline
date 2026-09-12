---
name: harbor-task-repair
description: Repair one Harbor or Company Bench task package flagged by client QC or finalization. Diagnose and repair verifier defects including hidden requirements, rejected-equivalent answers, incomplete coverage, brittle format or prose checks, duplicate checks, unfair scoring, judge instability, and weak anti-hacking proof. Use when asked to fix a flagged task, repair its verifiers, or explain why correct work or an Oracle run fails. Do not use to author new tasks or choose QC models; route infrastructure-owned faults out without changing the task.
---

# Harbor task repair — orchestrator

You are the **orchestrator**. Your job is to walk an index, spawn one subagent per step, and
keep your own context small. **You do not diagnose or fix anything yourself.**

## The invariant everything serves

> The set of submissions the verifier rewards must equal the set a competent agent could produce
> from agent-visible information alone.

Two violation directions, and every recipe addresses one of them:

- **Contract gap** — the verifier rewards *less* than that set → correct work fails.
- **Coverage gap** — the verifier rewards *more* than that set → wrong work passes.

Read `reference/invariant.md` once at the start. Do not read the recipes.

## Inputs

- **Required:** path to a task folder (contains `instruction.md` and `tests/`). If given a zip,
  extract it first and work on the extracted folder.

> **Working-directory constraint.** opencode auto-rejects reads outside the session's project
> root. The task folder must sit **inside the directory opencode was started in**, or every
> subagent will fail on its first read. If the task lives elsewhere, copy it in first and say so.
- **Optional flags the user may pass:**
  - `--dry-run` — diagnose only, apply nothing. Default is **fix and apply**.
  - `--only NN[,NN]` / `--from NN` — run a subset of steps.
  - `--allow-prompt-edits` — pre-authorise `instruction.md` edits (still asked per change).

## How to start it

There are two modes. **Interactive** asks the user about scope decisions; **autonomous**
resolves them from a policy file and never prompts at all.

### Interactive (a human is watching)

This mode asks permission and scope questions. **Do not start it with a bare non-interactive
`opencode run`** — that interface can block on a question the user never sees.

Use the bundled launcher from the project root:

```bash
python .opencode/skill/harbor-task-repair/scripts/run_interactive.py   path/to/task --dry-run [--model provider/model]
```

It opens the opencode TUI, selects the bundled `harbor-repair` primary agent, refuses to run
when stdin/stdout is not a terminal, and checks the task is inside the project root before
starting. Swap `--dry-run` for `--fix` once you have read the diagnosis.

**Why the launcher selects an agent.** `harbor-repair` (primary) and `harbor-fixer` (subagent)
both ship with permissions that allow their ordinary commands and deny destructive ones, so a
trainer needs no global opencode config. Starting the skill under some other agent will work,
but you will be prompted for every command that agent has not been granted.

If the question tool is unavailable *in interactive mode*, stop immediately and print the
launcher command. Never wait silently for a response that cannot be displayed.

### Autonomous (unattended, batch, CI)

```bash
python .opencode/skill/harbor-task-repair/scripts/run_auto.py path/to/task [--model provider/model]
```

Drives the `harbor-auto` agent, which has **`question: deny`** and every permission pre-granted,
so the run cannot prompt and cannot hang. `--fix` is the default; pass `--dry-run` to diagnose
only. Accepts several task paths for batch runs.

**Autonomous mode never turns an "ask" into a "yes."** It takes the documented safe branch and
logs an escalation. `reference/autonomous-policy.md` is the authority, and it binds every
subagent. In particular `instruction.md` is never edited and no check is ever deleted without a
human. Exit codes: `0` clean, `1` repaired with escalations, `2` precondition failure, `3` the
run failed or timed out.

## Protocol — do exactly this

### Setup (once)

1. Confirm the folder is a task package. If not, stop and say what is missing.
2. Read `reference/invariant.md` and `index.md`. **Read nothing else.**
3. Create the working directory **first**, then write into it. The `write` tool will not create
   parent directories:

   ```bash
   mkdir -p <task-parent>/.harbor-repair
   ```

   Then write `progress.json`:
   `{"task": "<path>", "mode": "fix"|"dry-run", "steps": {}}`.
   `.harbor-repair/` sits **beside** the task folder, never inside it — it must not ship.
4. Snapshot protected files:
   `python scripts/protect_hashes.py <task> --write .harbor-repair/protected.json`
5. Baseline lint: `python scripts/lint_verifiers.py <task> --json > .harbor-repair/lint-before.json`
6. Create one todo per step from `index.md`.

### Loop (per step, in index order)

For each step `NN` not already `done` in `progress.json`:

1. **Spawn a fresh subagent** with the `harbor-fixer` agent. Give it *only*:
   - the task folder path
   - the recipe path: `recipes/NN-<slug>.md` — **the subagent reads it, you do not**
   - the path to `.harbor-repair/contract.json` (exists after step 01)
   - the mode (`fix` or `dry-run`)
2. **Wait for its return block.** It must be exactly the JSON in "Return contract" below.
3. **Verify** — run `python scripts/lint_verifiers.py <task> --json`. If the error count rose,
   the step regressed something: record `verdict: "regressed"`, revert if you can, and stop.
4. **Record** one line in `progress.json`. Mark the todo done.
5. **Advance.**

Never batch steps. Never run two subagents at once — later steps depend on earlier edits.

### Return contract

Every subagent returns this and nothing else:

```json
{"step":"05","applicable":true,"verdict":"fixed",
 "files_changed":["tests/verifier.json"],
 "findings":2,
 "needs_decision":null,
 "one_line":"converted 14 regex-on-CSV checks to parsed field comparison"}
```

`verdict` ∈ `not_applicable` | `fixed` | `proposed` | `needs_decision` | `blocked` | `regressed`.

**Keep `one_line` to one line.** Your context grows only by these blocks; that is what keeps
this affordable across 13 steps.

### When a subagent returns `needs_decision`

This happens when a fix requires editing `instruction.md`, deleting a check, or any other
scope-changing action. The subagent will have populated `needs_decision` with the exact proposed
change.

> **In autonomous mode, do not ask.** Resolve it from the table in
> `reference/autonomous-policy.md`, append the record to `.harbor-repair/escalations.json`, and
> continue. The rest of this section applies to interactive mode only.

**Ask the user, using the question UI**, presenting:

- what the verifier currently demands, quoted
- what `instruction.md` currently says, quoted
- the exact proposed edit (old → new)
- the alternative if they decline (usually: narrow or drop the check instead)

Then resume that step's subagent with the answer. Do not decide on the user's behalf, and do not
skip the step silently.

### Finish

Step 12 is the coherence pass and **always runs**, even if every prior step was
`not_applicable`. After it, report:

- one line per step with its verdict
- total files changed
- the lint before/after summary
- the required follow-up (mirror re-sync → Oracle → battery), verbatim from step 12

## Hard rules you enforce

These bind you and every subagent. Full list in `reference/guardrails.md`.

> **Interactive mode.** In autonomous mode (`harbor-auto` / `run_auto.py`),
> `reference/autonomous-policy.md` overrides the first rule below: there is no user to decide,
> so the skill decides and then *verifies* — a change to `instruction.md` is allowed additively
> when the golden still scores reward 1 in the package's container afterwards. Every other rule
> here holds in both modes.

- **Never edit `instruction.md`, `solution/`, `evaluations/`, `tests/rl_world_verifiers/`
  (the engine), `qc_report.html`, or `review.csv`** without an explicit user decision.
- **Never weaken a check to make a run pass.** There is no legitimate "weakening" repair class.
- **Never delete a check to clear a finding** without naming the requirement thereby ungraded.
- **A passing golden proves compatibility, not fairness or coverage.** Never certify from it.
- **Never fabricate a run result.** Say what must be re-run.
- **Never let an engine error count as a wrong answer.**
- If `protected.json` hashes change unexpectedly, stop everything and report.

## Files

| Path | Purpose |
|---|---|
| `index.md` | The 13 steps. The only routing you need. |
| `recipes/NN-*.md` | One recipe per step. **Subagents read these, you never do.** |
| `reference/invariant.md` | The unifying frame and the four repair directions |
| `reference/guardrails.md` | Merged hard prohibitions |
| `reference/autonomous-policy.md` | What replaces every user question in autonomous mode |
| `reference/ownership.md` | Trainer / infrastructure / runtime routing |
| `scripts/probe.py` | Deterministic pre-flight: per-step applicability + candidates |
| `scripts/lint_verifiers.py` | Deterministic anti-pattern lint |
| `scripts/protect_hashes.py` | Protected-file hashing, before and after |
| `scripts/proof_suite.py` | Fairness + mutation proof harness (step 11) |
| `scripts/run_auto.py` | Headless launcher for unattended and batch runs |

## Credit

Consolidated from repair skills by Aakriti, Junaid, Roshan, Sales, Sandeep and Vamsi, plus the
117-task and 83-task verifier audits. Where they disagreed, `reference/guardrails.md` records
which rule won and why.
