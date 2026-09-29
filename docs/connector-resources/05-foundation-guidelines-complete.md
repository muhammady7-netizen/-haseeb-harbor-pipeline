# Connector Tasks Foundation Guidelines — Complete Document

**Source:** https://docs.google.com/document/d/1nVBar4JGUSvADM-LCeXLrLGPCh5jlgwSZcYmKTr-1VQ/edit
**Title:** Connector Tasks Foundation Guidelines (Google Doc, 5 tabs)
**Accessed:** 2026-09-29 via user-provided text (all 5 tabs)
**Status:** COMPLETE — all 5 tabs read in full

---

## Tab 1 — General Guidelines: TRAINER GUIDELINES

### Claiming, Checking, and Evaluating a Harbor Task Step by Step

This guide is for trainers: people who pick an automatically-mined task from the tracker and iterate on it until it meets our acceptance bar — checking it is runnable and fair, and adjusting the task (verifiers, rubrics, golden answer, instructions, and difficulty) until the model fails it often enough. Evaluate with exactly four GLM-5.2 attempts. A strict pass has reward exactly 1.0. Ship only when 1 or 2 of the 4 attempts strictly pass. Re-roll at 0/4, 3/4, or 4/4. Report all four rewards; do not use the average.

Scope. This guide covers the connector / gym tasks (the harbor/... packages). These build on a shared base image benchmark-base that already contains the mocked company systems (Zeta3 SQL, Jira, Confluence, Slack, Drive, Freshdesk, Email). You pull that image once; every task reuses it.

What is confirmed. The Linux path is tested and working.

There are two parts:
1. General system setup (one-time, per machine)
2. The trainer workflow (per task)

### Part 1 — General system setup (one-time, per machine)

#### 1.1 What you need (at a glance)

| Requirement | Why | Notes |
|---|---|---|
| Docker | Builds and runs the task container | ~64 GB free disk; the shared base image is ~15 GB to download and ~50 GB expanded |
| Google account with delivery-g-obi access | Pulls the private task base image | Ask your lead if unsure |
| gcloud CLI | Authenticates Docker to the private registry | Same commands on every OS |
| Python >= 3.12 | The Harbor CLI requires it | Check with python --version |
| Harbor CLI | Runs and views the evaluations | Installed as a Python tool |
| A personal GLM key | The only key you get — drives the model and grades rubric checks | Sent to you personally; works only against the team LiteLLM proxy |

You only get one key. Everyone is given a single personal GLM key (it works only against the team LiteLLM proxy). Because of budget constraints, glm-5.2 is the only model you can use — it drives the agent and grades any rubric checks (the judge is pointed at glm-5.2 too, via JUDGE_MODEL; see §1.6). There is no separate judge key.

#### 1.2 Install Docker

**Windows:** Download Docker Desktop for Windows. Run the installer. Keep WSL 2 backend enabled (default). Reboot if asked. Launch Docker Desktop.

**macOS:** Download Docker Desktop for Mac. Pick Apple silicon build for M-series Macs, or Intel chip build for older Macs.

**Linux:** Install Docker Engine + Docker Compose plugin. Then allow non-sudo: `sudo usermod -aG docker "$USER"` and `newgrp docker`.

Verify: `docker run --rm hello-world`

Budget 64 GB free. Never run `docker image prune -a` — it deletes the shared base image.

#### 1.3 Install the gcloud CLI and get image access

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

If permission error → ask your lead, do not work around it.

#### 1.4 Pull the benchmark-base image (one-time)

```bash
docker pull us-central1-docker.pkg.dev/delivery-g-obi/data-obi-rl-gym/benchmark-base:latest
docker images | grep benchmark-base
```

Never run `docker image prune -a`.

#### 1.5 Install Python 3.12+ and the Harbor CLI

```bash
python3 --version     # must be >= 3.12

# Recommended: uv
uv tool install harbor

# Alternative
pipx install harbor
# or
python -m pip install --user harbor

harbor --version      # expect 0.20.0 or newer
```

These tasks are `schema_version = "1.1"`. Harbor 0.20.0 accepts 1.1.

#### 1.6 Set up your API keys (keep them secret)

| Var | What it is |
|---|---|
| OPENAI_API_KEY | your personal sk-... GLM key (the only key you get) |
| OPENAI_BASE_URL | the team LiteLLM proxy: http://34.41.10.8:4000/v1 |
| JUDGE_MODEL | set to openai/glm-5.2 so the rubric judge also uses glm-5.2 |

Keep keys secret — store them outside any repo.

macOS/Linux:
```bash
mkdir -p ~/.config/harbor
cat > ~/.config/harbor/env <<'EOF'
export GLM_API_KEY=
export OPENAI_API_KEY="$GLM_API_KEY"
export OPENAI_BASE_URL=http://34.41.10.8:4000/v1
export JUDGE_MODEL=openai/glm-5.2
EOF
chmod 600 ~/.config/harbor/env
source ~/.config/harbor/env
```

Windows (PowerShell):
```powershell
$env:OPENAI_API_KEY = "your-personal-glm-key"
$env:OPENAI_BASE_URL = "http://34.41.10.8:4000/v1"
$env:JUDGE_MODEL = "openai/glm-5.2"
$env:PYTHONUTF8 = "1"
```

Quick key sanity check:
```bash
curl -s -o /dev/null -w "%{http_code}\n" "$OPENAI_BASE_URL/models" \
  -H "Authorization: Bearer $GLM_API_KEY"
# -> 200  (401 means wrong key or wrong endpoint)
```

#### 1.7 Setup is done when…
- docker run --rm hello-world works
- gcloud lists an image
- docker images shows benchmark-base
- harbor --version prints 0.20.0+
- curl sanity check returns 200
- Keys stored safely, not in any git repo
- glm-harbor-config.json created (§1.9)

#### 1.8 Set up an AI coding assistant — opencode (preferred) or Cursor

Create `~/.config/opencode/opencode.json` with your personal GLM key and the team LiteLLM proxy.

#### 1.9 Create the GLM harbor config file (one-time)

Create `glm-harbor-config.json`:
```json
{
  "jobs_dir": "/tmp/harbor-jobs",
  "n_concurrent_trials": 1,
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
  ]
}
```

What the config does:
- `model_name: "glm/glm-5.2"` — the glm/ prefix uses the custom provider (not openai/ which crashes)
- `opencode_config → provider.glm` — reads reasoning from reasoning_content (Chat Completions native)
- `verifier.env` — passes key, proxy URL, and JUDGE_MODEL to the verifier

### Part 2 — The trainer workflow (per task)

5 steps:
1. Claim a task from the tracker
2. Inspect the task files for general correctness (keep only `core` rubrics)
3. Run the oracle check; fix the gold if it fails
4. Run 4 model runs; check the pass rate is 50% or below
5. Run the unified QC tool; submit the task for automated QC

#### Step 1 — Claim a task from the tracker
Open the tracker, claim one task, download the zip, unzip it.

#### Step 2 — Inspect the task files for general correctness

**2a. instruction.md** — check it asks for something clear, doesn't give away the answer, deliverables are clear.

**2b. tests/manifest.json** — check verifiers cover what the prompt asks, no verifier tests something the prompt never asked, the primary goal is verified.

**Keep only core verifiers; remove secondary ones.** Every verifier in `verifier_configs` has a "category" field set to "core" or "secondary". Delete any entry with `"category": "secondary"` — keep only "core". We grade on core rubrics only. Do this before the oracle run.

**2c. solution/** — check they answer what instruction.md asks, no obvious errors.

#### Step 3 — Run the oracle check (and fix the gold if it fails)

```bash
harbor run -p "$TASK" -a oracle \
  --ve OPENAI_API_KEY="$GLM_API_KEY" \
  --ve OPENAI_BASE_URL="$OPENAI_BASE_URL" \
  -o /tmp/harbor-jobs --job-name oracle-<task> -n 1 -y
```

Oracle must be exactly 1.0. Anything lower means a verifier rejects the known-correct answer — a defect in the task.

**If oracle fails:**
- Read `test-stdout.txt` to see which assertion failed
- Golden answer wrong → fix solution/
- Golden trajectory wrong → re-run or promote a correct run
- Rubric wrong/over-strict → loosen in manifest.json
- Secondary verifiers still present → delete them
- Check tests something prompt never asked → remove check or add ask to instruction.md

**If golden trajectory is missing/very wrong — defer it.** Leave it for now. After Step 4, promote a fully-correct model run to be the golden trajectory.

#### Step 4 — Run 4 model runs and check the pass rate is 50% or below

**4a. One run first (smoke test):**
```bash
harbor run -c /path/to/glm-harbor-config.json -n 1 -y
```

If AgentSetupTimeoutError:
```bash
harbor run -c glm-harbor-config.json --agent-setup-timeout-multiplier 3 -n 1 -y
```

**4b. The 4-run battery:**
```bash
harbor run -c /path/to/glm-harbor-config.json -n 3 -k 4 -y
```

Choosing --n-concurrent: (your RAM in GB − 4) / 4. 16GB→2, 32GB→3-4, 64GB→5.

**4c. Read the results:**
```bash
cat /tmp/harbor-jobs/glm-5x-<task>/*/verifier/reward.txt
harbor view /tmp/harbor-jobs    # browser UI
```

**4d. The pass rate you report — and the 50% acceptance bar:**

A run fully passes when it passes 100% of the verifiers (reward 1.0). A run that passes only some verifiers is NOT a full pass.

Pass rate = (number of runs that fully pass) ÷ (total number of runs).

- Pass rate <= 50% → accept. The model fails the task most of the time.
- Pass rate > 50% → the task is too easy. Iterate to make it harder.

A reward of 0.0 usually means something crashed. Always check for exception.txt / missing trajectory.json first.

**Definition of done — before you submit:**
1. Golden trajectory in solution/golden_trajectory present
2. Oracle run scores exactly 1.0
3. 4-run pass rate is 50% or below
4. Only core rubrics remain in tests/manifest.json

#### Step 5 — Run the unified QC tool; submit for automated QC

```bash
# Dry-run (free, no API calls):
python3 unified_qc.py --input /path/to/<task-dir> --dry-run

# Real review:
python3 unified_qc.py --input /path/to/<task-dir> --output-dir ~/qc-out/<task>

# With trajectories:
python3 unified_qc.py --input /path/to/<task-dir> \
  --trajectory /tmp/harbor-jobs/<job-name> --include-trajectories required
```

Results: results.json (full evidence), results.csv (one row per issue), summary.md (compact rollup).

Fix any cited issues, re-run QC until it comes back Keep, then submit.

---

## Tab 2 — Onboarding Process: Connector Tasks New Trainer Onboarding Guide

### Workflow Overview
Access → Setup → Claim → Understand → Oracle → Model Runs → Harden → QC → Submit

### PART A: One-Time Project Setup
1. Verify Access & Permissions (tracker, Drive, GCP, Cloudflare, GLM key)
2. Install and Configure Docker
3. Set Up GCP & Artifact Registry (gcloud auth, pull benchmark-base)
4. Install Python & Harbor CLI
5. Environment & API Configuration (OPENAI_API_KEY, OPENAI_BASE_URL, JUDGE_MODEL)
6. Harbor GLM Configuration (glm-harbor-config.json)
7. Optional: AI Coding Assistant Setup (opencode/Cursor)

### Part A Verification Checklist
- Docker works
- Can pull/access benchmark image
- Harbor runs
- GLM credentials work
- Connector/project access works
- Know where to claim and download a task

### PART B: Task Execution Workflow
8. Claim and Download Task
9. Task Understanding & Review (instruction.md, manifest.json, solution/, task.toml)
10. Oracle Execution (must score 1.0)
11. Model Evaluation & Trajectory Analysis (4 GLM runs, read all trajectories, classify failures)
12. Task Hardening (interpretation not discovery, update all affected files consistently)
13. Quality Control (QC)
14. Final Package Consistency Check

### Submission Readiness Checklist
- Environment and access working
- Task clear and internally consistent
- Instruction and verifier agree
- Golden/oracle solution passes
- Latest model evaluation meets difficulty requirement
- Failures used as difficulty evidence are genuine model failures
- QC completed
- Final package is the same version that was evaluated
- Task packaged and ready for submission
- At least one non-oracle run scored 1.0
- Four-run battery is fresh and in the 1–2/4 band
- review.csv has exactly 14 required rows and 5 columns

---

## Tab 3 — Connector Task Detail: Onboarding Handbook

### Overview
One rule governs the whole job: **The set of submissions the verifier rewards must equal the set a competent agent could produce from agent-visible information alone.** Reward less = Contract Gap. Reward more = Coverage Gap.

### Acceptance criteria
| Criterion | What it means |
|---|---|
| It grades cleanly | Checks measure concrete state, deterministically, and a correct solution passes |
| A model can solve it | At least one non-oracle run reaches full reward |
| Most attempts do not | 1 or 2 of 4 GLM-5.2 attempts strictly pass |
| Nothing is unfair | Every graded requirement traces to a sentence the agent can read |

### The difficulty band
A strict pass is reward exactly 1.0. Run exactly four attempts, report all four rewards, never the average.

| Strict passes | Team rule | Client acceptance |
|---|---|---|
| 4/4 | Re-roll: too easy | Rejected |
| 3/4 | Re-roll | Accepted, but weakest |
| 1/4 or 2/4 | Ship | Accepted — where accepted work sits |
| 0/4 | Re-roll by default | Submittable only with clean non-oracle solvability run |

### Why tasks are rejected (28 audited, 24 had issues)
| Pattern | Tasks | Section |
|---|---|---|
| Too easy — 3/4 strict passes (P-C6) | 12/28 | §2 |
| Open connector surface — one SQL SELECT replaces workflow (P-C1) | 12/28 | §3 |
| Verifier coverage and fairness gate failed (P-C5 in 4) | 9/28 | §4 |

### Five rules that are never negotiable
1. The oracle scores exactly 1.000 before any battery runs
2. The oracle does not prove solvability — needs a non-oracle run at full reward
3. Sync the _app mirror after every task-root edit, re-run oracle after every change
4. Write the prediction before you harden
5. A battery is evidence only for the task as it stood when it ran

### 1 · Connector vs non-connector
- **Non-connector:** Fixed files in environment/input/, reads/computates/writes, verifier checks files
- **Connector:** Live gym via MCP, calls tools/writes deliverable/changes service, verifier checks files + gym DB state + trajectory
- Decided by files, not scenario. Look at tests/ (verifier.json vs manifest.json), environment/ (input/ vs _app/mcp/proxy), task.toml (mcp_servers empty vs defined)

### 1.4 The configuration that bites
| Setting | Value | Why |
|---|---|---|
| [verifier] environment_mode | "shared" | "separate" crashes harbor run |
| [agent] timeout_sec / [verifier] timeout_sec | 4800 / 1500 | Gym setup + heavier grading |
| [agent] user | "rlgymagent" | /app root-only, artifacts under /workspace |
| allow_internet | true | As connector template ships |
| [environment.healthcheck] | required | Container not ready until proxy answers |

Healthcheck: command = `curl -fsS --max-time 3 http://localhost:7000/health`, timeout_sec = 120.0, retries = 150 (template ships 40).

### 2 · Difficulty and hardening
- 13/28 failed Layer 2 Difficulty, 12 at 3/4, none flagged too hard
- A disclosed rule can still be too easy if it's a mechanical threshold (field >= N)
- Difficulty that survives disclosure comes from **interpretation** — connecting an abstract concept to a concrete field
- **The honest levers:** Precision (exact lists not booleans), Interpretation (policy not threshold), Pin every fork, Coupled discriminators, Ship the harness (gold re-derivation script)
- Write the prediction before the battery
- "Too easy" is usually the open surface in costume — close bypass first

### 3 · The connector surface
Most frequent defect family. Proxy exposes unauthenticated raw passthrough on localhost:7000.

**Four doors (closing three = closing none):**
1. State route: GET /raw/{gym}/state?verify_queries=<SQL>
2. Step route: POST /raw/{gym}/step
3. Files on disk: gym SQLite, /opt/proxy/server.py, seed SQL
4. The gym port: direct HTTP access

Probe as the agent user at runtime. Grade the trajectory, not only the deliverable.

### 3.3 Three proxy designs (not interchangeable)
| Design | Auth | Trusted trace | Upload anchor |
|---|---|---|---|
| ~2,051 lines (6/8 repo tasks) | x-connector-internal-capability; client mode on | Yes | Absent |
| ~1,002 lines | x-api-key; client mode off | No | Present |
| ~821 lines | Neither header; still carries /raw/ routes | No | Present |

Client mode is gym-specific. Snowflake drops DB router at import time when client mode on. Supabase gates only docs URLs.

### 4 · Verifier fairness
- Every graded requirement must trace to instruction.md (backward pass)
- Dead score buckets: declared weights with no checks behind them
- Judge over empty rubric: when key unset, scoring returns 0.0
- An ask may legitimately stay ungraded (record the decision)

### 4.1 Full audit distribution (28 tasks, 82 fail cells)
| Gate | Fails | Shape |
|---|---|---|
| Layer 2 Difficulty | 13 | 12 at 3/4 — P-C6 |
| Layer 4 Connectors | 13 | P-C2, P-C3 |
| Layer 5 Reward hacking | 13 | P-C1 — 12 of 13 |
| Layer 5 Verifier fairness | 9 | P-C5, P-C7, P-C8 |
| Layer 4 Environment | 9 | Healthcheck timeout, OOM |
| Layer 5 LLM judge | 9 | P-C4 |
| Layer 5 Cross-trial | 7 | P-C9 |
| Layer 1 Clarity | 4 | Hidden workflow rules |
| Layer 1 Package | 2 | Verifier-only rule |
| Layer 2 Solvability, Layer 3 Oracle, Layer 4 Deliverables | 1 each | P-C10 |
| Layer 2 Stability, Layer 1 Realism | 0 | Clean |

~62 of 82 fail cells are harness/proxy defects (P-C1 to P-C4). Author-side: P-C5 to P-C8, ~20 cells.

### 4.3 The ten client-audit patterns
| Pattern | What | Tasks |
|---|---|---|
| P-C1 | Unauthenticated raw-SQL proxy bypass | 12 |
| P-C2 | Proxy healthcheck timeout | 8 |
| P-C3 | Silent corpus loss / broken tools | 13 |
| P-C4 | Judge gates reward with no rubric | 7 |
| P-C5 | Undisclosed workflow/trace-shape requirement | 4 |
| P-C6 | Under-difficulty: 3/4 strict passes | 12 |
| P-C7 | Dead score buckets / vacuous trajectory checks | 3 |
| P-C8 | Duplicate checks / disproportionate scoring | 2 |
| P-C9 | Verifier/judge false negatives as model failures | 7 |
| P-C10 | Oracle/solvability pass requiring guessing undisclosed rule | 2 |

### 5 · Evidence discipline
- A battery measures only the task as it existed when it ran
- Before believing any zero, read the exception
- Agent timeouts are scored (not void) unless infrastructure hung the agent
- Infrastructure and verifier failures are ineligible — replaced, never counted
- Stability is a regrade, not three fresh runs (harbor trial regrade refuses under shared mode)
- Re-derive every number in your write-up from evidence

### 6 · Migration discipline
When the answer moves, update ALL of: instruction.md, tests/manifest.json, task.toml, solution/, environment/_app/, review.csv.
- The assertion fails loudly; the prose fails silently
- A stale expected array breaks the oracle; a stale why_justification breaks nothing and ships
- The mirror can faithfully copy a self-contradictory root

### 7 · Environment and setup
- Apple Silicon: `export DOCKER_DEFAULT_PLATFORM=linux/amd64`
- Pre-bake Node + opencode into image (without it, install OOMs at container start, exit 137)
- Container memory: 4096 MB per connector trial (peaks at ~2.2 GiB)
- Docker VM memory: 16 GB where host allows
- Python 3.12+
- Healthcheck retries: 150 (template ships 40)
- Clean eval-jobs/ after each battery (~1 GB per trial)
- Semicolon-separated run swallows failures: use `set -eu` + assertion, `set -euo pipefail` for pipes

### 8 · Seeding and the upload anchor
- Seed only when baked data lacks the relation you need
- Place at environment/seed_<scenario>.py, writing to gym's SQLite
- Assert at build time, fail build on any failure
- No gold leakage in seeded text
- Ship the reference server.py unmodified (converter matches by full file hash)
- Upload anchor: fixed 11-line block at exactly 12-space indentation inside bootstrap()

### 9 · The package and the review record

**9.1 Package structure:**
```
task/
├── task.toml
├── instruction.md
├── review.csv
├── qc_report.html
├── README.md
├── tests/
├── environment/
├── solution/
└── evaluations/
    ├── solvability/r1/    one full-reward non-oracle run
    └── difficulty/r1..r4/  four independent rollouts
```

**9.2 review.csv:**
- Exactly 5 columns: review_check, status, review_notes, change_made, what_to_record
- Exactly 14 rows with byte-exact names (interpunct · on 10 rows, absent on 4 Layer 2/3 rows)
- Status: PASS, FIXED_AND_VERIFIED, or N/A (no FAIL)
- change_made is blank on every PASS row
- Notes are history, not summary — append, never overwrite
- Both fold-ins required: Rollout reasoning → Layer 2 Difficulty; Failure attribution → Cross-trial · Calibration
- Cross-trial · Calibration ends with Verdict: approve. / change. / block.

**14 row names (byte-exact):**
1. Layer 1 · Package consistency
2. Layer 1 · Clarity and scope
3. Layer 1 · Realism and leakage
4. Layer 2 Difficulty
5. Layer 2 Solvability
6. Layer 2 Stability
7. Layer 3 Oracle Mode
8. Layer 4 · Environment and files
9. Layer 4 · Connectors, MCPs, and CLIs
10. Layer 4 · Deliverables and artifact quality
11. Layer 5 · Verifier coverage and fairness
12. Layer 5 · LLM judge consistency
13. Layer 5 · Reward hacking and exploitability
14. Cross-trial · Calibration

### 10 · QC review
- Two passes with isolated context
- Mandatory model-failure sanity check: Reward hacking? Unfair verifier? Non-model-caused failure?
- Separate the abort from the verdict
- Summarise per layer before concluding

### 11 · Where the hours go
2–3.5h to read guidelines, ~2.5h for environment setup, 4.5–10h per task.

### 12 · What this guidance does not cover
Governing standards at OBI project root. Two different "bands" exist (authoring vs delivery folder labels).

### 13 · Quick reference checklist
- [ ] Family and config match
- [ ] Data probed (tenant DB exists after reset, row counts confirmed, facts reachable via tools)
- [ ] Surface closed (all four doors probed as rlgymagent)
- [ ] Backward pass done (every check quotes instruction sentence)
- [ ] Mirror synced after last edit
- [ ] Oracle: exactly 1.000 on final version
- [ ] Battery: exactly 4 attempts, 1-2 strict passes, every zero's exception read
- [ ] Solvability: one non-oracle run at full reward
- [ ] Numbers re-derived from evidence
- [ ] review.csv: 14 byte-exact rows, 5 columns, valid statuses, both fold-ins, verdict line
- [ ] Package: zipped from sanitized tree, qc_report.html inside, anchor checked

### 14 · The data behind each connector (12 gyms)

| Gym | Main records | Tables · rows |
|---|---|---|
| Slack | 102 channels, 100 users, 1,507 messages | 15 · 4,058 |
| Snowflake | 17 databases, 239 tables, 14 roles, 22 users | 21 · 24,344 |
| Supabase | 81 projects, 108 edge functions, 162 API keys | 23 · 50,217 |
| Outlook | 511 messages, 445 calendar events | 8 · 5,044 |
| Email & Calendar | 280 users, 671 messages, 2,609 events | 36 · 30,512 |
| GitHub | 560 repos, 3,583 issues, 1,636 PRs | 58 · 59,995 |
| Google Workspace | 593 files, 904 permissions | 31 · 14,884 |
| Linear | 150 projects, 11,000 issues | 45 · 62,815 |
| Microsoft 365 | 10 sites, 94 drive items | 20 · 804 |
| Microsoft Teams | 155 teams, 244 channels, 403 users | 19 · 2,706 |
| Notion | 301 pages, 5 databases | 24 · 2,354 |
| Shopify | 64 products, 125 variants, 15 orders | 22 · 425 |

(Detailed table schemas for each gym are in the full handbook text.)

---

## Tab 4 — Common Issues & QC Playbook

### Standards
- Model runs per battery: 4 GLM-5.2 runs
- What counts as a pass: reward exactly 1.0
- Acceptance band: 1 or 2 strict passes out of 4
- Oracle: must score exactly 1.0 on current version
- Evidence freshness: every run must match current task_checksum
- Failures that count as difficulty: genuine model failures only

### Order of work
Fix structural problems before tuning difficulty. A task that looks too easy because of P-C1 or P-C4 is broken, not easy.

### Two-pass QC workflow

**Pass 1: generate the QC report** — use /connector-task-reviewer skill, run full pipeline, do independent verification before trusting README/review.csv, check all P-C patterns, audit review.csv itself, model-failure sanity check, gate verdicts, final recommendation.

**Pass 2: verify the report in a fresh session** — open new agent session, independently re-derive conclusions, accuracy verdict on the report, re-verify model-failure fairness check, audit review.csv independently.

### The 10 client-audit patterns (detailed)

**P-C1 — Raw-SQL proxy bypass** (12/28, Fix first)
Proxy exposes unauthenticated raw endpoints. One SQL SELECT gets every graded value. Fix: add tool_execution check naming specific sanctioned MCP tools. Escalate: close raw endpoints in proxy image.

**P-C2 — Proxy healthcheck timeout** (8/28, Medium, Escalate)
Healthcheck times out before agent starts. Fix: keep retries generous, discard crashed run, never count toward pass rate. Escalate: reliable readiness gate.

**P-C3 — Silent corpus loss and broken tools** (13/28, High)
Connector returns incomplete corpus with no truncation marker. Fix: if required item unreachable via MCP, change task. Escalate: silent truncation, opaque errors, exposed admin endpoints.

**P-C4 — Judge gates reward with no rubric** (7/28, Fix first)
task.toml configures judge but rubric.toml has zero items. If key missing, score is 0.0. Fix: remove judge config if no rubric items. Escalate: judge infra failures should produce non-score.

**P-C5 — Undisclosed workflow requirements** (4/28, High)
Check grades something instruction never states. Fix: state the rule in instruction or delete the check.

**P-C6 — Task too easy** (12/28, Medium)
3/4 runs score exactly 1.0. Fix: first rule out P-C1, then add real difficulty (harder sub-question, reconciliation step, complex aggregation).

**P-C7 — Dead score buckets** (3/28, Medium)
Manifest declares weighted buckets with no checks. Fix: ensure every bucket has at least one check, or disable explicitly.

**P-C8 — Duplicate checks** (2/28, Medium)
Two checks test same fact, or file-parses check weighted like main question. Fix: remove duplicates, weight headline question above format checks.

**P-C9 — False negatives as model fails** (7/28, High)
Correct answer loses reward, counted as difficulty. Fix: fix the check causing it. A check that fails gold-exact answers is a verifier defect.

**P-C10 — Oracle/solvability failure from hidden rule** (2/28, Medium)
Golden failed a check tied to P-C1, or pass required guessing P-C5 rule. Fix: fix verifier or rule, not the golden.

### Pre-submission self-check (15 items)
☐ Every instruction requirement has a check, every check traces to instruction
☐ No check grades workflow shape/call count/counting definition not stated in instruction
☐ Every tool_execution check names its tools, golden + correct runs pass it
☐ Raw-SQL curl test was run, result recorded in review.csv
☐ If rubric.toml has zero items, no judge gates the score
☐ Every declared score bucket contains at least one check
☐ No duplicate or implied checks, headline question outweighs format checks
☐ Every tool the instruction relies on returns content through MCP
☐ Oracle scores exactly 1.0 on current version
☐ 4-run battery matches current task_checksum, 1-2 strict passes
☐ All 4 trajectories read, every failure classified, crashed runs discarded
☐ Only one evaluation battery in package, README numbers match
☐ review.csv keeps original findings and appends fixes with evidence
☐ Both QC passes complete, every issue from Pass 2 resolved
☐ No API keys, credentials, or job output folders in package

---

## Tab 5 — Tips & Tricks

### Current evaluation standard
4 GLM runs. Submission-ready band: 1-2 strict passes out of 4. Strict pass = reward exactly 1.0.

### 1. Start with the environment, not the task
- Confirm Cloudflare/Context-Aware Access before treating failures as task defects
- Check memory and disk space before changing task logic
- Clean eval-jobs when disk grows
- Apple Silicon: `export DOCKER_DEFAULT_PLATFORM=linux/amd64`
- Exit code 137 = OOM kill, not task failure. Give 4096 MB per container.

### 2. Read the task before you try to improve it
- Cold read: read instruction.md without looking at the gold
- Forward pass: every instruction requirement → verifier/check
- Backward pass: every verifier/check → instruction text that justifies it
- Surface check: verify all four doors closed (state route, step route, files on disk, gym port)
- Probe as rlgymagent from inside running container
- Do not harden until the task is fair, solvable, and internally consistent

### 3. Hardening: make the model reason, not hunt
- Prefer interpretive difficulty (connect policy to data) over mechanical thresholds
- Write the prediction before the battery
- Know when the task has hit a ceiling — adding more independent easy rules is not the answer

### 4. Every meaningful change needs a consistency sweep
Update ALL of: instruction.md, tests/manifest.json (including instruction_sha256), tests/rubric.toml, task.toml, solution/, README.md, environment/_app/, review.csv

A clean root↔mirror diff proves the mirror matches the root, NOT that the root is correct. Validate the root first, then sync.

### 5. Evidence must be fresh
- A 4-run battery is evidence only for the task version when runs were produced
- After changing grading/deliverable/values/logic, re-run oracle
- After a change affecting difficulty, run fresh 4-run battery
- Do not use stale results as evidence for a newer task version

### 6. Read all 4 trajectories — not just the score
Classify each failure: genuine model failure, verifier/grading defect, instruction mismatch, infra failure, connector failure, judge error, ambiguous requirement.
- Only genuine model failures count as difficulty evidence
- Void run: exception.txt shows crash before/during agent, or trajectory.json missing → replace, never score
- Agent timeout is NOT void: verifier still runs, reward stands

### 7. Re-run the oracle after changes
Any change to prompt/verifier/expected answer/deliverable/hardening can break gold path. Require exactly 1.000 before trusting new battery.

### 8. Keep review.csv as history, not a snapshot
Keep original failure note and append new state + evidence. Never overwrite. No FAIL status. Use PASS, FIXED_AND_VERIFIED, or N/A. Mark FIXED_AND_VERIFIED only after the check has been re-run.

### 9. Useful time-saving habits
- Sync mirror after every edit (but only after validating root)
- Run oracle locally when possible (faster than platform queue)
- Clean eval-jobs after batteries
- Pre-bake required tooling
- Re-run packaging/QC gate after regenerating evaluations

### 10. Common symptoms and what to check first
- Task remains 4/4 after hardening → discriminator is mechanical; redesign around interpretation
- Oracle fails after edit → re-check verifier, expected values, deliverable shape
- Counts disagree across files → cross-file consistency sweep
- Battery predates latest edit → stale, re-run all 4 trials
- Upload rejects server.py → compare with accepted reference; exact structure matters
- Access blocked → resolve Cloudflare before debugging task

### 11. Final submission check
1. Task fair, solvable, internally consistent, instruction matches verifier
2. Oracle scores exactly 1.000 on current version
3. One non-oracle run at full reward in evaluations/solvability/r1/
4. Fresh 4-run battery after latest edits, void runs replaced, 1-2/4 band
5. All 4 trajectories reviewed; root/mirror synchronized; review.csv preserves history
6. QC/package checks re-run after final evaluation refresh
7. Zip contains review.csv AND qc_report.html (client requires both)
