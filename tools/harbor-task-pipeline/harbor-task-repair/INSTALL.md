# Installing `harbor-task-repair`

## What you need

| Requirement | Why | Check |
|---|---|---|
| **opencode** ≥ 1.18 | Native skill + subagent support | `opencode --version` |
| **Python 3.10+** | The three scripts. **Standard library only** — nothing to `pip install` | `python --version` |
| A model configured in opencode | The orchestrator and subagents | `opencode models` |

**The skill itself has no Python dependencies.** `lint_verifiers.py`, `protect_hashes.py` and
`proof_suite.py` import only from the standard library.

### Step 11 needs the verifier engine's dependencies — and Python 3.11+

To execute a task's verifier (step 11, the proof suite) you need the packages
`tests/rl_world_verifiers/` imports. **Most packages ship no `tests/test_requirements.txt`**, so
this list is not discoverable from the task — it was derived by grepping the engine's imports:

```bash
pip install pytest pydantic jsonpath-ng openpyxl python-docx python-pptx pypdf tenacity litellm
```

> **`litellm` requires Python 3.11+** (it imports `NotRequired` from `typing`). On Ubuntu 22.04,
> whose system Python is 3.10, put the deps in a newer venv and run the skill under it:
>
> ```bash
> sudo add-apt-repository -y ppa:deadsnakes/ppa && sudo apt install -y python3.12 python3.12-venv
> python3.12 -m venv ~/harbor/venv
> ~/harbor/venv/bin/pip install pytest pydantic jsonpath-ng openpyxl python-docx \
>     python-pptx pypdf tenacity litellm
> ```

**Without these, step 11 silently reports that it cannot execute** and every run ends
`repaired-unproven` — the anti-hacking guarantee is absent, and nothing tells you loudly. Verify
before a batch:

```bash
cd <a-task> && <python> -m pytest --collect-only -q tests | tail -2   # expect "N tests collected"
```

The skill's own scripts remain standard-library only; this applies to executing the *task's*
verifier, not to the skill.

## Install

Copy two directories into the repo where you work on tasks:

```
<your-repo>/
├── .opencode/
│   ├── skill/
│   │   └── harbor-task-repair/      <- the whole folder
│   └── agent/
│       ├── harbor-repair.md         <- the orchestrator (primary)
│       └── harbor-fixer.md          <- the worker (subagent)
```

That is the entire install. Start `opencode` from that repo root and confirm:

```
/skills          -> harbor-task-repair listed
/agents          -> harbor-repair (primary) and harbor-fixer (subagent) listed
```

**Global alternative** — to use it in every project, put the same two folders under
`~/.config/opencode/` (Windows: `%USERPROFILE%\.config\opencode\`) instead of the repo.

## What NOT to copy

If you zip your `.opencode/` folder, **exclude these** — opencode generates them itself and its
own auto-created `.opencode/.gitignore` already lists them:

```
.opencode/node_modules/
.opencode/package.json
.opencode/package-lock.json
.opencode/bun.lock
```

They are opencode's plugin runtime (`@opencode-ai/plugin`), installed on first server start in a
project. They are **not** part of this skill, they are version-pinned to the opencode build that
created them, and shipping them can conflict with a different opencode version on the other
machine.

## Approval prompts — no config needed

The package ships **three** things that together remove per-command prompts:

| File | Scope |
|---|---|
| `.opencode/opencode.json` | Project-wide permissions — applies to **every** agent, including the default `build` |
| `.opencode/agent/harbor-repair.md` | The orchestrator's own permissions |
| `.opencode/agent/harbor-fixer.md` | The worker's own permissions |

> :warning: **If you already have a `.opencode/opencode.json`, the zip will overwrite it.**
> Back it up first and merge the `permission` block by hand instead.

`.opencode/opencode.json` is the one that matters most: agent-level permissions only apply when
you launch under that agent, but the project config covers you even if you just run `opencode`
and ask for the skill. It merges with your global config — your providers and models are
untouched.

**The agents also carry their own permissions** so the skill still behaves if the project config
is missing or you install the agents somewhere else.

| Agent | Mode | Role |
|---|---|---|
| `harbor-repair` | primary | Orchestrates the 13 steps |
| `harbor-fixer` | subagent | Executes one step |

Both grant `bash: "*": allow` and deny the destructive commands (`rm`, `rmdir`,
`git checkout/reset/clean/restore`). `harbor-repair` also allows `task` so spawning the worker
13 times does not prompt. `external_directory` and `question` stay on `ask` deliberately — the
first is what keeps a run inside your project, the second is how scope decisions reach you.

**Agent-level permission overrides global config**, which is why this works without you editing
anything — *and* why you must launch under `harbor-repair`. The
`run_interactive.py` launcher passes `--agent harbor-repair` for you. If you start the skill
under some other agent (e.g. the default `build`), you will be prompted for every command that
agent has not been granted.

The real safety is not per-command prompting. It is `protect_hashes.py` (every protected file
hashed before and after), the recipe scope rules, and `needs_decision` for anything that changes
what the task measures.

### Optional: global config

Only needed if you want these permissions outside this skill. Add to your opencode config
(`~/.config/opencode/opencode.json`, Windows `%USERPROFILE%\.config\opencode\opencode.json`):

```json
{
  "permission": {
    "bash": {
      "*": "allow",
      "rm *": "deny",
      "* rm *": "deny",
      "rmdir *": "deny",
      "git checkout*": "deny",
      "git reset*": "deny",
      "git clean*": "deny",
      "git restore*": "deny"
    },
    "edit": "allow",
    "write": "allow",
    "read": "allow",
    "external_directory": "ask"
  }
}
```

Valid actions are `ask`, `allow`, `deny`. Recognised keys: `read`, `edit`, `write`, `glob`,
`grep`, `list`, `bash`, `task`, `external_directory`, `todowrite`, `question`, `webfetch`,
`websearch`, `lsp`, `skill`.

`"permission": "allow"` as a bare string allows *everything*, including `rm -rf`. Not recommended.

Keep `external_directory` on `ask` — it is what stops an agent reading outside the project, and
it fires rarely.

For a one-off non-interactive run you can also pass `--auto` to `opencode run`, which
auto-approves anything not explicitly denied.

## Autonomous mode — zero prompts, for unattended batch fixing

Interactive mode asks you about scope decisions. **Autonomous mode never asks anything.**

```bash
python .opencode/skill/harbor-task-repair/scripts/run_auto.py path/to/task [--model provider/model]
python .opencode/skill/harbor-task-repair/scripts/run_auto.py tasks/*/ --continue-on-error
```

`--fix` is the default; add `--dry-run` to diagnose only. It takes several task paths for batch
runs, has no TTY guard, and closes stdin so a run can never block on input.

| File | Role |
|---|---|
| `.opencode/agent/harbor-auto.md` | primary orchestrator, **`question: deny`** |
| `.opencode/agent/harbor-fixer-auto.md` | worker, **`question: deny`** |
| `reference/autonomous-policy.md` | what replaces every user question |
| `scripts/run_auto.py` | headless launcher |

**Why `question` is denied and not allowed.** `allow` only suppresses the *permission* prompt —
the question tool would still block waiting for a human answer. Denying it makes hanging
structurally impossible.

**Destructive commands stay denied, not asked.** A deny fails the call and the agent adapts; it
never blocks. An unattended run needs that more than an interactive one, not less.

### What it does instead of asking

> Autonomous mode never turns an "ask" into a "yes". It takes the documented safe branch and
> logs an escalation.

`instruction.md` is **never** edited and no check is **ever** deleted without a human. Scope
decisions resolve to the conservative branch and land in `.harbor-repair/escalations.json`. The
full table is in `reference/autonomous-policy.md`.

This means autonomous runs deliberately under-fix some tasks. That is the correct trade — the
escalation log tells you which tasks want a human.

### Getting the tasks out of GCS

Task packages carry `evaluations/` run archives that the skill mostly does not read. Only two
files in there matter — `test-stdout.txt` and `verifier_summary.json`, which the lint uses for
the `A9`/`A5b` run-history checks. Everything else is bulk: agent trajectories, and
`reward_detail.json` files that run to ~20 MB **each**.

```bash
gcloud storage rsync -r \
  --exclude='.*evaluations/(?!.*(test-stdout\.txt|verifier_summary\.json)).*' \
  gs://<bucket>/<prefix> ./tasks
```

Measured on two real packages — **28 MB → 4 MB** and **246 MB → 4 MB** — with `lint` and `probe`
output *byte-identical* to a full download, and all run-evidence files retained. Task sizes vary
by ~10x, so budget from the filtered size (~4 MB each), not from one sample.

> **Two traps.** A pattern like `.*/evaluations/.*/agent/.*` matches **nothing** when the sync
> source is the task directory itself — there is no path segment before `evaluations/`, so the
> filter silently does nothing and you download everything. And excluding `evaluations/`
> wholesale *does* shrink the download, but destroys the run history: `runs_seen` drops to 0 and
> the lint stops emitting `A9`/`A5b` entirely.
>
> `--exclude` takes a Python regex, so negative lookahead works — that is what makes the precise
> filter above possible. Verify after downloading one task:
>
> ```bash
> find <task>/evaluations -name 'test-stdout.txt' -o -name 'verifier_summary.json' | wc -l
> ```

### Large batches (hundreds of tasks)

```bash
python .opencode/skill/harbor-task-repair/scripts/run_auto.py tasks/*/ \
    --model wandb-glm/zai-org/GLM-5.2 --task-jobs 24 --continue-on-error
```

`--task-jobs N` repairs N tasks concurrently. Each task gets its own
`.harbor-repair/<task-name>/` beside it, so concurrent runs cannot clobber each other's
probe, progress, escalations or protected-hash files.

**Use this, not `run_parallel.py`, for a batch.** `run_parallel.py` cuts *per-task latency*
about 40% by running the diagnosis steps concurrently, but it costs about **35% more total
compute** (measured: 3,485 vs 2,572 agent-seconds for the same repair, same final lint). In an
unattended batch nobody waits on one task, so throughput is what matters, and task-level
concurrency wins at every slot count:

| concurrent slots | `run_auto --task-jobs` | `run_parallel` |
|---|---|---|
| 12 | 35.7 h | 48.4 h |
| 24 | **17.9 h** | 24.2 h |
| 48 | 8.9 h | 12.1 h |

(600 tasks, extrapolated from one measured task.)

**Calibrate the slot count.** Concurrency efficiency was measured at 69% for 6 parallel agents
and 58% for 8; it degrades, and above 8 is untested. Run ~20 tasks at `--task-jobs 12` and at
`24` and compare wall time before committing to a number.

**Run on Linux or WSL.** Step 11 (the proof suite) cannot execute on a Windows host, so no
repair is ever formally proven there - across a large batch that silently removes the whole
anti-hacking guarantee.

**Expect most tasks to exit 1.** Escalations ran 3-6 per task in testing. Budget for the review
queue, or the exit code stops being a useful filter.

### Exit codes

| Code | Meaning |
|---|---|
| `0` | repaired, nothing needs review |
| `1` | repaired **with escalations** — review `escalations.json` before shipping |
| `2` | precondition failure (bad path, skill not installed, opencode missing) |
| `3` | the run failed or timed out |

Informational routing notes (e.g. the `OWN1` binary-reward note, which fires on nearly every
package) do **not** trigger exit 1 — only decisions that were auto-resolved or that reduced
coverage do.

### Pre-flight probe

`run_auto.py` runs `scripts/probe.py` first — a deterministic, 0.1s pass that decides
per-step applicability and hands each subagent its candidate list, so steps with zero candidates
are recorded `not_applicable` without spawning a subagent. Measured 2.3 of 13 steps skipped on
average, 6 of 13 on a clean package. Use `--no-probe` to disable.

A step is only skippable when its defect class is *structurally impossible* without the signal.
Steps 03/04/06/08 are semantic and are never auto-skipped, and a spec the probe cannot inspect
(some connector packages) disables every skip.

## Working-directory rule

opencode auto-rejects file reads outside its project root. **The task folder must live inside the
directory you started opencode from.** If your packages live elsewhere, copy one in first:

```bash
cp -r /path/to/task ./work/task && opencode
```

## First run

```
Use the harbor-task-repair skill to repair test_tasks/03-clean-control with --dry-run.
```

`--dry-run` changes nothing. Verified: a full 13-step dry run over two real packages modified
**zero** files.

## Verify the install works

```bash
python .opencode/skill/harbor-task-repair/scripts/lint_verifiers.py test_tasks/03-clean-control
# expect: 0 error(s), 0 warning(s)

python .opencode/skill/harbor-task-repair/scripts/lint_verifiers.py test_tasks/01-per-row-explosion
# expect: 7 error(s), 236 warning(s)
```

If those two disagree with the numbers above, the copy is incomplete.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Skill not listed | Wrong path | Must be `.opencode/skill/harbor-task-repair/SKILL.md` — note `skill`, singular |
| `harbor-fixer` not listed | Agent file missing | `.opencode/agent/harbor-fixer.md` |
| "permission requested: external_directory" | Task is outside the project root | Copy the task inside, restart opencode |
| Subagent fails its first read | Same as above | Same |
| `progress.json` write fails | Parent dir does not exist | The skill runs `mkdir -p` first; if it still fails, create `.harbor-repair/` by hand |
| Step 11 says `GENERATED_ONLY` | You did not pass `--run` | Expected. Add `--run`, and the task's test requirements |
| Step 11 says `RUNTIME_ERROR` | Verifier could not execute here | Environment problem, **not** a task defect. Use the task's declared sandbox |
| Every run ends `repaired-unproven` | Step 11 could not execute | Honest outcome. The repair is proposed but not certified |
