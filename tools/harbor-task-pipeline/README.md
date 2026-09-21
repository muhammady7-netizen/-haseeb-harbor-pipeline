# Harbor task pipeline

Fix a flagged task, then prove the package is shippable.

**Two ways to use it. Same work, pick whichever you like.**

```bash
# 1. run the command
python run.py path/to/my-task
```

```
# 2. or just ask, in opencode
   "fix and package the task in ./my-task"
```

Either way you get the repaired task, a packaged `.zip`, and a gate report in
`./harbor-pipeline-out/`. The command is for scripting and CI; asking is for everything else.

---

## Setup (2 minutes, once)

```bash
python install.py            # installs the skill + agents into this repo
pip install pytest pydantic jsonpath-ng openpyxl python-docx python-pptx pypdf tenacity litellm
python run.py --doctor
```

`install.py` puts the skills in `.opencode/skill/`, the agents in `.opencode/agent/`, and the
permission config that lets the repair run without stopping on approval prompts. Use
`--global` to install for every project, `--check` to see what you already have.

**You need `install.py` even if you only ever use the command** — the repair stage requires the
`harbor-auto` agent definitions, and without the permission config it will stall waiting for
approvals.

`--doctor` tells you exactly what's missing and the command to fix it. Green across the board
means you're ready.

**Python 3.11+ is recommended.** On 3.10 `litellm` won't install and two gates degrade — the
pipeline still runs, `--doctor` will say so.

**opencode** must be on your PATH with a model configured (`opencode models`). Only the repair
stage needs it; `--check-only` works without it.

**Docker is optional but worth having** — just the CLI, the engine does not need to be running.
With it, image tags get pinned to their registry digest (gate G01). Without it, unknown tags stay
unpinned and G01 remains open.

---

## What it does

| stage | what happens |
|---|---|
| **1. repair** | `harbor-task-repair` diagnoses and fixes verifier defects — hidden requirements, rejected-equivalent answers, brittle format checks, unfair scoring. Slow: 20–90 min per task. |
| **2. package** | The task tree becomes a delivery `.zip`. **Nothing is stripped** except things we know we created. |
| **3. gate** | `repackaging-qc-gate` finds packaging defects, they get remediated, then **the gate runs again** to prove the fixes landed. |

The second gate pass is the point. A remediation you haven't re-verified is a claim, not a fix.

---

## Commands you'll actually use

```bash
# one task, everything
python run.py my-task

# several tasks
python run.py tasks/*

# I only want to check packaging - no repair, no opencode, no model cost
python run.py my-task --check-only

# diagnose without changing anything
python run.py my-task --dry-run

# repair, but I'll package later
python run.py my-task --repair-only

# 4 tasks at once (needs the RAM and cores - each spawns containers)
python run.py tasks/* --jobs 4
```

Useful flags: `--model provider/model`, `--timeout 10800`, `--out some/dir`.

---

## Reading the result

```
  packages : 3
  blocking : 47 -> 0

  Everything this pipeline can fix is fixed.
```

That's what you want. If something is still open:

```
  Still open (needs a look):
    G04   1
```

Open `harbor-pipeline-out/.work/gate-after.json` — every finding names the task, the file and
the evidence.

### Findings that will not go to zero, and shouldn't

| gate | why it stays |
|---|---|
| **G06** documentation vs evidence | The finalization pipeline regenerates the README and `review.csv` from its own runs. Fixing it here aligns documents to rewards that are about to be replaced. |
| **G10** incomplete difficulty battery | Needs the task re-run — repackaging cannot invent a missing reward. |
| **G11** difficulty band | Recompute once the battery is complete. |
| **G12** manifest | Recomputed at delivery from the delivered bytes. |

The pipeline lists these separately as *expected residual* so you don't chase them.

---

## Exit codes

| code | meaning |
|---|---|
| `0` | Everything fixable is fixed |
| `1` | Findings remain that need a human |
| `2` | Environment or input problem — the message says which |
| `130` | You pressed Ctrl-C |

Scriptable: `python run.py t && ship.sh`

---

## Two things that will bite you

**Run it from the folder that contains your tasks.** opencode only reads inside the directory it
starts in. A task elsewhere fails on every subagent's first read, and the error looks like a task
problem. The pipeline checks this before spending anything and tells you what to do.

**Install the verifier deps.** Without them the repair still runs, but its proof step cannot
execute the task's own verifier — so the result is *unproven* rather than certified, and nothing
says so loudly at the end. `--doctor` catches it.

---

## What's in here

```
run.py                  the only thing you run
stage2_fix.py           the packaging remediator
harbor-task-repair/     the repair skill (stage 1)
repackaging-qc-gate/    the gate + its full spec (stage 3)
```

`repackaging-qc-gate/REPACKAGING-QC-GATE.md` documents all twelve gates: what each detects, why
it matters, how to remediate it, and — just as important — what it must **not** flag.

## Where things end up

```
harbor-pipeline-out/
  <task>.zip                    shippable packages
  pipeline-report.json          what ran, and the before/after counts
  .work/
    gate-before.json            findings before remediation
    gate-after.json             findings after - the one to read
    stage2-changes.json         every change made, with its basis
```

Each package also carries `PACKAGING-PROVENANCE.json` recording what was changed inside it and
why — including the note that a pinned image digest constrains future rebuilds but does **not**
describe the historical runs already recorded under `evaluations/`.
