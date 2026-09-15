# Trainer Guidelines — Claiming, Checking, and Evaluating a Harbor Task

This guide is for trainers: people who pick an automatically-mined task from the tracker and iterate on it until it meets our acceptance bar — checking it is runnable and fair, and adjusting the task (verifiers, rubrics, golden answer, instructions, and difficulty) until the model fails it often enough. You measure with a 5-run model evaluation and re-run after each change until the pass rate is 50% or below.

## Scope
This guide covers the connector / gym tasks (the harbor/... packages). These build on a shared base image `benchmark-base` that already contains the mocked company systems (Zeta3 SQL, Jira, Confluence, Slack, Drive, Freshdesk, Email). You pull that image once; every task reuses it.

What is confirmed: The Linux path is tested and working.

There are two parts:
1. General system setup (one-time, per machine)
2. The trainer workflow (per task)

---

## Part 1 — General system setup (one-time, per machine)

### 1.1 What you need (at a glance)

| Requirement | Why | Notes |
|---|---|---|
| Docker | Builds and runs the task container | ~64 GB free disk; the shared base image is ~15 GB to download and ~50 GB expanded |
| Google account with delivery-g-obi access | Pulls the private task base image | Ask your lead if unsure |
| gcloud CLI | Authenticates Docker to the private registry | Same commands on every OS |
| Python >= 3.12 | The Harbor CLI requires it | Check with `python --version` |
| Harbor CLI | Runs and views the evaluations | Installed as a Python tool |
| A personal GLM key | The only key you get — drives the model and grades rubric checks | Sent to you personally; works only against the team LiteLLM proxy |

You only get one key. Everyone is given a single personal GLM key (it works only against the team LiteLLM proxy). Because of budget constraints, glm-5.2 is the only model you can use — it drives the agent and grades any rubric checks (the judge is pointed at glm-5.2 too, via JUDGE_MODEL; see §1.6). There is no separate judge key.

### 1.2 Install Docker

**Windows**: Download Docker Desktop for Windows, run installer, keep WSL 2 backend enabled, reboot if asked, launch Docker Desktop.

**macOS**: Download Docker Desktop for Mac (Apple silicon or Intel), open .dmg, drag Docker to Applications, launch Docker.

**Linux**: Install Docker Engine + Docker Compose plugin. Then:
```bash
sudo usermod -aG docker "$USER"
newgrp docker
```

Verify: `docker run --rm hello-world` (must work without sudo on Linux)

Budget 64 GB free. The base image is large.

### 1.3 Install the gcloud CLI and get image access

Every task's `environment/Dockerfile` starts with:
```
FROM us-central1-docker.pkg.dev/delivery-g-obi/data-obi-rl-gym/benchmark-base:latest
```

Install gcloud CLI, then:
```bash
gcloud auth login
gcloud auth configure-docker us-central1-docker.pkg.dev
gcloud config set project delivery-g-obi
```

Verify access:
```bash
gcloud artifacts docker images list \
  us-central1-docker.pkg.dev/delivery-g-obi/data-obi-rl-gym/benchmark-base \
  --limit=1
```

### 1.4 Pull the benchmark-base image (one-time)
```bash
docker pull us-central1-docker.pkg.dev/delivery-g-obi/data-obi-rl-gym/benchmark-base:latest
```
Verify: `docker images | grep benchmark-base`

Never run `docker image prune -a` — it deletes the shared base image.

### 1.5 Install Python 3.12+ and the Harbor CLI

Install Harbor (recommended: uv):
```bash
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
uv tool install harbor

# macOS and Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install harbor
```

Verify: `harbor --version` (expect 0.20.0 or newer)

### 1.6 Set up your API keys (keep them secret)

| Var | What it is |
|---|---|
| OPENAI_API_KEY | your personal sk-... GLM key (the only key you get) |
| OPENAI_BASE_URL | the team LiteLLM proxy: `http://34.41.10.8:4000/v1` |
| JUDGE_MODEL | set to `openai/glm-5.2` so the rubric judge also uses glm-5.2 |

**macOS and Linux** — store in chmod 600 file:
```bash
mkdir -p ~/.config/harbor
cat > ~/.config/harbor/env <<'EOF'
export GLM_API_KEY=
export OPENAI_API_KEY="$GLM_API_KEY"
export OPENAI_BASE_URL=http://34.41.10.8:4000/v1
export JUDGE_MODEL=openai/glm-5.2
EOF
chmod 600 ~/.config/harbor/env
```

Load per terminal: `source ~/.config/harbor/env`

**Windows (PowerShell)** — per session:
```powershell
$env:OPENAI_API_KEY     = "your-personal-glm-key"
$env:OPENAI_BASE_URL = "http://34.41.10.8:4000/v1"
$env:JUDGE_MODEL     = "openai/glm-5.2"
$env:PYTHONUTF8      = "1"
```

Or persist: `setx OPENAI_API_KEY "your-personal-glm-key"` etc.

Quick key sanity check:
```bash
curl -s -o /dev/null -w "%{http_code}\n" "$OPENAI_BASE_URL/models" \
  -H "Authorization: Bearer $GLM_API_KEY"
# -> 200 (401 means wrong key or wrong endpoint)
```

### 1.8 Set up an AI coding assistant — opencode (preferred) or Cursor

**opencode**: Install, create `~/.config/opencode/opencode.json` with GLM provider config pointing at the team LiteLLM proxy.

**Cursor**: Use 3.14.7 (bug in 3.15.x blocks overriding OpenAI base URL). Settings → Models → add custom model, set OpenAI API Key and Override OpenAI Base URL to `http://34.41.10.8:4000/v1`.

### 1.9 Create the GLM harbor config file (one-time)

Create `glm-harbor-config.json` in the repo root:
```json
{
  "job_name": "glm-run",
  "jobs_dir": "/tmp/harbor-jobs",
  "n_concurrent_trials": 1,
  "n_attempts": 5,
  "verifier": {
    "env": {
      "OPENAI_API_KEY": "${OPENAI_API_KEY}",
      "OPENAI_BASE_URL": "http://34.41.10.8:4000/v1",
      "JUDGE_MODEL": "openai/glm-5.2"
    }
  },
  "agents": [
    {
      "name": "opencode",
      "model_name": "glm/glm-5.2",
      "env": {
        "OPENAI_API_KEY": "${OPENAI_API_KEY}",
        "OPENAI_BASE_URL": "http://34.41.10.8:4000/v1"
      },
      "kwargs": {
        "opencode_config": {
          "provider": {
            "glm": {
              "npm": "@ai-sdk/openai-compatible",
              "name": "GLM Gateway",
              "options": {
                "baseURL": "http://34.41.10.8:4000/v1",
                "apiKey": "{env:OPENAI_API_KEY}"
              },
              "models": {
                "glm-5.2": {
                  "name": "GLM-5.2",
                  "reasoning": true,
                  "interleaved": { "field": "reasoning_content" }
                }
              }
            }
          }
        }
      }
    }
  ],
  "tasks": [
    { "path": "REPLACE_WITH_TASK_PATH" }
  ]
}
```

Key points:
- `model_name: "glm/glm-5.2"` — the `glm/` prefix uses the custom provider (not the built-in `openai/` provider, which crashes).
- `opencode_config` → defines a custom OpenAI-compatible provider that reads reasoning from `reasoning_content` (Chat Completions native).
- `tasks[0].path` — edit this each time you switch tasks.

### 1.7 Setup is done when…
- `docker run --rm hello-world` works
- gcloud can list the benchmark-base image
- `docker images | grep benchmark-base` shows the base image
- `harbor --version` prints 0.20.0 or newer
- The curl sanity check returns 200
- Your keys are stored safely and not in any git repo
- `glm-harbor-config.json` created

---

## Part 2 — The trainer workflow (per task)

### Step 1 — Claim a task from the tracker
Open the tracker, claim one task, download and unzip it.

A task folder (Harbor package) looks like:
```
<task-name>/
├── environment/      Dockerfile, entrypoint.sh, mcp/ proxy
├── instruction.md    the task prompt (given to the agent)
├── solution/        golden answer: solve.sh, solve.py, final_answer.md, golden_trajectory, ...
├── task.toml        task config (schema_version 1.1)
└── tests/           manifest.json + frozen verifier engine
```

### Step 2 — Inspect the task files for general correctness

**2a. instruction.md** — Check it asks something clear and realistic, doesn't give away the answer, and deliverables/filenames are clear.

**2b. tests/manifest.json** — Check verifiers cover what the prompt asks for, no verifier tests something the prompt never asked, and the primary goal is verified.

**Keep only core verifiers; remove secondary ones.** Every verifier has a `"category"` field set to either `"core"` or `"secondary"`. Delete any verifier entry with `"category": "secondary"` — keep only `"core"`. We grade on core rubrics only.

**2c. solution/** — Check golden answer actually answers instruction.md, has no obvious errors.

### Step 3 — Run the oracle check (and fix the gold if it fails)

**3a. Run the oracle:**
```bash
source ~/.config/harbor/env

harbor run -p "$TASK" -a oracle \
  --ve OPENAI_API_KEY="$GLM_API_KEY" \
  --ve OPENAI_BASE_URL="$OPENAI_BASE_URL" \
  -o /tmp/harbor-jobs --job-name oracle-<task> -n 1 -y
```

**3b. Read the oracle result:**
```bash
cat /tmp/harbor-jobs/oracle-<task>/*/verifier/reward.txt    # reward: 1.0 = pass
cat /tmp/harbor-jobs/oracle-<task>/*/verifier/test-stdout.txt  # per-assertion detail
```

Oracle must be exactly 1.0. Anything lower means a verifier rejects the known-correct answer — a defect in the task.

**3c. If oracle fails — find the cause and fix it:**
- Golden answer wrong → fix solution/final_answer.md, solve.sh, solve.py
- Golden trajectory wrong → re-run or promote a correct run later
- Rubric wrong/over-strict → loosen the check
- Secondary verifiers still present → delete them
- Check tests something prompt never asked → remove check or add to instruction.md

Rules for fixing:
- Keep core rubrics; remove secondary ones.
- File checks must be forgiving, gold must be strict.
- Never state a graded answer inside the prompt.

**3d. What "passing" vs "a broken run" look like:**
- `exception.txt` exists → run crashed, number is meaningless
- No `trajectory.json` / `oracle.txt` → nothing recorded, run is broken
- Reward 0.0 with no crash → gold failed a grader, read test-stdout.txt
- Reward 1.0 → healthy task, move to Step 4

**3e. If the golden trajectory is missing or very wrong — defer it.** After Step 4, take a fully-correct model run (reward 1.0) and promote it to be the golden trajectory.

### Step 4 — Run 5 model runs and check the pass rate is 50% or below

**4a. (Optional but recommended) One run first:**
```bash
source ~/.config/harbor/env
export OPENAI_API_KEY="$GLM_API_KEY"

# Edit glm-harbor-config.json: set tasks[0].path to your task folder and job_name
harbor run -c /path/to/glm-harbor-config.json -n 1 -y
```

**4b. The 5-run battery:**
```bash
# Edit glm-harbor-config.json: set tasks[0].path and job_name
harbor run -c /path/to/glm-harbor-config.json -n 3 -k 5 -y
```

Flags: `-n 3` = 3 concurrent, `-k 5` = 5 attempts total, `-y` = skip prompts.

Choosing `--n-concurrent`: Each container asks for 4 GB RAM. `≈ (RAM in GB − 4) / 4`.

**4c. Read the results:**
```bash
harbor view /tmp/harbor-jobs                              # browser UI
cat /tmp/harbor-jobs/<job-name>/*/verifier/reward.txt     # the scores
```

**4d. The pass rate and the 50% acceptance bar:**
- A run **fully passes** when it passes 100% of the verifiers (reward 1.0).
- Pass rate = (number of runs that fully pass) ÷ (total number of runs).
- Pass rate ≤ 50% → **accept**. The task is hard enough.
- Pass rate > 50% → **too easy**. Iterate: tighten loose verifiers, add checks, make gold stricter, revise instruction.md. Re-run Step 4.

A reward of 0.0 usually means something crashed — check for `exception.txt` / missing `trajectory.json` first.

### Definition of done — before you submit (Step 5)
1. Golden trajectory in `solution/golden_trajectory` (promote a reward-1.0 model run if original was broken).
2. Oracle run scores exactly 1.0 (re-run after any change).
3. 5-run pass rate is 50% or below.
4. Only core rubrics remain in `tests/manifest.json`.

### Step 5 — Run the unified QC tool; submit the task

**5a. Get the tool:** Download the QC script.

**5b. Setup:** Copy `.env.example` to `.env`, put your gateway key in it.

**5c. Dry run (free):**
```bash
python3 unified_qc.py --input /path/to/<task-dir> --dry-run
```

**5d. Real review:**
```bash
python3 unified_qc.py --input /path/to/<task-dir> --output-dir ~/qc-out/<task>
```

**5e. Post-run QC (with harbor runs):**
```bash
python3 unified_qc.py \
  --input /path/to/<task-dir> \
  --trajectory /tmp/harbor-jobs/<job-name> \
  --include-trajectories required
```

**5f. Three things worth knowing:**
- Do not point `--input` at the bundle root — it errors out.
- If you pass `--trajectory`, check that `context.trajectory.records` > 0 in `results.json`.
- A crashed run is flagged as `infra`, not difficulty. Discard and re-run.

**5g. What you get:**
- `results.json` — full evidence, gates, ask-to-verifier coverage map
- `results.csv` — one row per issue
- `summary.md` — compact rollup

Fix any cited issues (back in Steps 2–4), re-run QC until it comes back Keep. Then submit.

---

## Quick reference

### One-time setup (Part 1):
```bash
# Docker: install + start Docker Desktop or Docker Engine
gcloud auth login
gcloud auth configure-docker us-central1-docker.pkg.dev
gcloud config set project delivery-g-obi
docker pull us-central1-docker.pkg.dev/delivery-g-obi/data-obi-rl-gym/benchmark-base:latest
uv tool install harbor
harbor --version
# store keys in ~/.config/harbor/env (chmod 600), source it per terminal
# create glm-harbor-config.json (§1.9)
```

### Every session, before running harbor:
```bash
# macOS/Linux
source ~/.config/harbor/env

# Windows (PowerShell)
$env:OPENAI_API_KEY  = "your-personal-glm-key"
$env:OPENAI_BASE_URL = "http://34.41.10.8:4000/v1"
$env:JUDGE_MODEL     = "openai/glm-5.2"
```

### Step 3 — Oracle (must be exactly 1.0):
```bash
harbor run -p "$TASK" -a oracle \
  --ve OPENAI_API_KEY="$GLM_API_KEY" \
  --ve OPENAI_BASE_URL="$OPENAI_BASE_URL" \
  -o /tmp/harbor-jobs --job-name oracle-<task> -n 1 -y
```

### Step 4 — model runs:
```bash
# 1 run (smoke test)
harbor run -c /path/to/glm-harbor-config.json -n 1 -y

# 5 runs (the real eval)
harbor run -c /path/to/glm-harbor-config.json -n 3 -k 5 -y
```

### Read results:
```bash
harbor view /tmp/harbor-jobs
cat /tmp/harbor-jobs/<job-name>/*/verifier/reward.txt
```

### The two numbers that matter:
| Number | Must be |
|---|---|
| Oracle reward | exactly 1.0 |
| Pass rate (fully-passing runs, out of 5) | ≤ 50% to accept; > 50% → too easy |

### Step 5 — Run the unified QC tool:
```bash
# dry-run (free)
python3 unified_qc.py --input /path/to/<task-dir> --dry-run

# real review
python3 unified_qc.py --input /path/to/<task-dir> --output-dir ~/qc-out/<task>

# with harbor run trajectories
python3 unified_qc.py --input /path/to/<task-dir> \
  --trajectory /tmp/harbor-jobs/<job-name> --include-trajectories required
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `docker … permission denied` (Linux) | `sudo usermod -aG docker $USER && newgrp docker` |
| Docker daemon not running | Start Docker Desktop (Win/Mac); `sudo systemctl start docker` (Linux) |
| `harbor: command not found` | Install dir not on PATH. Win: `C:\Users\<you>\.local\bin`; Mac/Linux: `~/.local/bin` |
| Image pull fails 403/unauthorized | `gcloud auth login`; if still failing, ask your lead |
| Build fails at `FROM …benchmark-base` | Base image not pulled. `docker pull …` |
| Every model call fails 401 | Key/endpoint mismatch. GLM key only works at `http://34.41.10.8:4000/v1` |
| Agent crashes `text part chatcmpl-... not found` | Using `-m openai/glm-5.2` without custom provider. Use `-m glm/glm-5.2` with opencode_config |
| Rubric verifiers all score 0 | `JUDGE_MODEL` not set, or judge model proxy doesn't serve. Set `JUDGE_MODEL=openai/glm-5.2` |
| Oracle reward 0.0, no crash | Gold failed a grader. Read `test-stdout.txt`; fix the gold/rubric |
| `exception.txt` present | Read it; common causes: bad task.toml, proxy port conflict, gym not healthy |
| Healthcheck never passes | Usually memory pressure. Lower `--n-concurrent`, close other apps |
| First run is slow | Expected — ~15 GB image download. Only first run pays this |
| Out of disk | Base image needs ~50 GB. `docker system df`. Never `docker image prune -a` |
| Results folder empty | Job failed before producing anything. Read `job.log` |

---

## Company Bench: Running a Task Locally, From Scratch

Audience: anyone setting up a fresh machine to run Company Bench tasks, runner or QC reviewer.

### Prerequisites at a glance

| Requirement | Why | Notes |
|---|---|---|
| Docker | Runs the task container | ~64 GB free disk needed |
| Google account with delivery-g-obi access | Pulls the task base image | Ask your lead if unsure |
| Python 3.12 or newer | Harbor CLI requires it | |
| Harbor CLI | Runs and views evaluations | |
| W&B API key | GLM-5.2 model calls and rubric grading | Ask your lead |

Disk: shared base image ~15 GB download, ~50 GB expanded. Budget 64 GB free.
RAM: each running container asks for 4 GB.

### Step 1: Docker
Same as Part 1 §1.2 above.

### Step 2: Access to the task image
Same as Part 1 §1.3 above.

### Step 3: The Harbor CLI
Same as Part 1 §1.5 above. Expect 0.20.0 or newer.

### Step 4: Credentials
Two environment variables point the model calls at W&B:
```bash
# macOS/Linux
export OPENAI_API_KEY="wandb_v1_your_key_here"
export OPENAI_BASE_URL="https://api.inference.wandb.ai/v1"
export JUDGE_MODEL="openai/glm-5.2"

# Windows (PowerShell)
$env:OPENAI_API_KEY  = "wandb_v1_your_key_here"
$env:OPENAI_BASE_URL = "https://api.inference.wandb.ai/v1"
$env:JUDGE_MODEL     = "openai/glm-5.2"
```

### Step 5: Your first run (Oracle)
```bash
# macOS and Linux
harbor run \
  -p /path/to/<task-name> \
  -a oracle \
  -o ~/obi-eval/jobs \
  --job-name oracle-<task-name> \
  -y

# Windows (PowerShell)
harbor run `
  -p C:\path\to\<task-name> `
  -a oracle `
  -o $HOME\obi-eval\jobs `
  --job-name oracle-<task-name> `
  -y
```

Success: `{"reward": 1.0}` in reward.json. Oracle must be exactly 1.0.

### Step 6: GLM-5.2 runs

**Single run first:**
```bash
export OPENAI_API_KEY="<OPENAI_API_KEY>"
export OPENAI_BASE_URL="<OPENAI_BASE_URL>"
export GLM_API_KEY="${GLM_API_KEY:-$OPENAI_API_KEY}"
export JUDGE_MODEL="openai/glm-5.2"

TASK="<TASK_FOLDER>"

harbor run \
  -p "$TASK" \
  -a opencode \
  -m glmproxy/glm-5.2 \
  --ak 'opencode_config={"provider":{"glmproxy":{"npm":"@ai-sdk/openai-compatible","name":"GLM via LiteLLM","options":{"baseURL":"{env:OPENAI_BASE_URL}","apiKey":"{env:OPENAI_API_KEY}"},"models":{"glm-5.2":{"name":"GLM 5.2"}}}}}' \
  --agent-setup-timeout-multiplier 3 \
  --ae OPENAI_API_KEY="$GLM_API_KEY" --ae OPENAI_BASE_URL="$OPENAI_BASE_URL" \
  --ve OPENAI_API_KEY="$GLM_API_KEY" --ve OPENAI_BASE_URL="$OPENAI_BASE_URL" \
  --ve JUDGE_MODEL="$JUDGE_MODEL" \
  -o ~/obi-eval/jobs --job-name "glm-5x-opencode-<task>" -y
```

**The 5-run battery:**
```bash
harbor run \
  -p "$TASK" \
  -a opencode \
  -m glmproxy/glm-5.2 \
  --ak 'opencode_config={"provider":{"glmproxy":{"npm":"@ai-sdk/openai-compatible","name":"GLM via LiteLLM","options":{"baseURL":"{env:OPENAI_BASE_URL}","apiKey":"{env:OPENAI_API_KEY}"},"models":{"glm-5.2":{"name":"GLM 5.2"}}}}}' \
  --n-attempts 5 --n-concurrent 2 -r 3 \
  --agent-setup-timeout-multiplier 3 \
  --ae OPENAI_API_KEY="$GLM_API_KEY" --ae OPENAI_BASE_URL="$OPENAI_BASE_URL" \
  --ve OPENAI_API_KEY="$GLM_API_KEY" --ve OPENAI_BASE_URL="$OPENAI_BASE_URL" \
  --ve JUDGE_MODEL="$JUDGE_MODEL" \
  -o ~/obi-eval/jobs --job-name "glm-5x-opencode-<task>" -y
```

New flags: `--n-attempts 5` = run five times, `--n-concurrent 2` = how many run simultaneously.

Choosing `--n-concurrent`: `≈ (RAM in GB - 4) / 4`.

### Reading the results

Where things land:
```
~/obi-eval/jobs/<job-name>/
  job.log                        top-level log for the whole job
  result.json
  <task-name>__<id>/             one folder per run
    agent/
      trajectory.json            every tool call the agent made
      final_answer.md            what it replied
      oracle.txt                 Oracle runs only: step-by-step replay log
    verifier/
      reward.json                {"reward": 0.6}
      reward.txt                 the same number, plain text
      verifier_summary.json      per-verifier detail. The important one.
    result.json                  run metadata, including task_checksum
    trial.log                    setup and container log
```

Browser UI: `harbor view ~/obi-eval/jobs` (opens at port 8080)

The score: `cat ~/obi-eval/jobs/<job-name>/*/verifier/reward.json`

Which verifiers passed, and why:
```bash
python -c "
import json,sys
d=json.load(open(sys.argv[1]))
print('reward:', d['reward']['total'])
print(json.dumps(d['verification_summary'], indent=2))
for it in d['reward']['rubric']['items']:
    print(('PASS' if it.get('passed') else 'FAIL'), it.get('name'), '|', it.get('verifier_type'))
    if it.get('motivation'): print('   ', it['motivation'][:200])
" ~/obi-eval/jobs/<job-name>/<run-folder>/verifier/verifier_summary.json
```

Warning: this file lists the same verifiers several times under different groupings. Read whole entries from `items[]`.

### Telling a broken run from a genuine failure

| Symptom | Meaning |
|---|---|
| `agent/exit-code.txt` exists | The run crashed. The number is meaningless. |
| `agent/trajectory.json` is missing | No tool calls were recorded, so every verifier failed by default |

A genuine failure: `trajectory.json` is present and populated, some verifiers pass, and the failures carry real motivation text explaining what was wrong with the answer.
