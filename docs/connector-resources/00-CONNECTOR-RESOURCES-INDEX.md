# Connector Resources Index

All resources for working on Connector tasks. Compiled from Slack #shannon-connector-team-a, Google Docs, and the trainer guideline canvas.

---

## Main resources (Google Docs/Sheets — require Turing auth)

| Resource | URL | Local copy |
|---|---|---|
| **Main Guideline (5 tabs)** | https://docs.google.com/document/d/1nVBar4JGUSvADM-LCeXLrLGPCh5jlgwSZcYmKTr-1VQ/edit | `01-guideline-TOC.md` (full TOC extracted) |
| **Main Tracker** | https://docs.google.com/spreadsheets/d/15iT-FxMS2ymoPn7bixNcb-d6m5NfnBWiKwu6za-1uOo/edit | `02-main-tracker.csv` (307 rows, all tasks) |
| Non-Connector vs Connector (Consolidated Findings) | https://docs.google.com/document/d/1my4Dan_ce38NaFM7ZbIAJkMN7uUFerEfU9qxNhyg9GI/edit?tab=t.0 | `06-consolidated-team-findings.md` |
| Company Bench Golden Analysis | https://docs.google.com/document/d/1W3JqkOW3QscGi3B0qwFHXBvZghpg85P2UdhwNmExgtA/edit?tab=t.0 | `07-golden-task-analysis.md` |
| Company Bench/Connector Tasks Guideline | https://docs.google.com/document/d/1jdmYao4I8HQdHZikLu2PmPz1Ye_JJC9EBpW2YfR-TgM/edit?tab=t.0 | `08-connector-tasks-guidelines.md` |
| Findings collection | https://docs.google.com/document/d/1_bqiPgXY-3dqjdunCemyKysYrQXgub8-arurf53rObI/edit?tab=t.0 | Working doc (team findings) |
| Common issues | https://docs.google.com/document/d/1YKhvNcIce56Qoe3la-ZL2b09eF0zglliBHUtCiw-lKY/edit?tab=t.0 | Tab 4 of `05-foundation-guidelines-complete.md` |
| Trainer Guidelines (alt version) | https://docs.google.com/document/d/14Lk44mmisI2V007uRljtzOa8P8gPqgnyv5fE4ZEs-Zc/edit?tab=t.4l31xitik0r1 | Same as `05-foundation-guidelines-complete.md` |
| Demo transcription | https://docs.google.com/document/d/1jUYMAv3f9_f2WhrWZ4x31y_WgzWN9_fRfdEaNHvVREY/edit?usp=sharing | `04-demo-notes-transcript.md` |
| Demo recording (video) | https://drive.google.com/file/d/15kwFsafmXrGXizSS83M1pES7Ym-k77_8/view?usp=sharing | Notes in `04-demo-notes-transcript.md` |
| Main Guideline (5 tabs) | https://docs.google.com/document/d/1nVBar4JGUSvADM-LCeXLrLGPCh5jlgwSZcYmKTr-1VQ/edit | `05-foundation-guidelines-complete.md` |
| Main Tracker | https://docs.google.com/spreadsheets/d/15iT-FxMS2ymoPn7bixNcb-d6m5NfnBWiKwu6za-1uOo/edit | `02-main-tracker.csv` |
| Slack Canvas | https://turing-company.slack.com/docs/T8YAVN6JJ/F0C4WD2J2SH | — |

## Golden reference tasks (accepted by client)

3 accepted connector tasks to study as reference:
1. `auto-atlanta-covered-travel-roomlist-20260903t200000z-3fd10b-v1-sna-drhp-atlanta-itinerary-settlement-standing-ranked.zip`
2. `auto-how-much-of-my-drive-is-link-only-20260826T10143-7cce8e-v1-sna-hfxx-how-much-of-my-drive-is-link-only.zip`
3. `auto-outside-voices-in-the-locked-sales-drive-2026090-87313e-v1-sna-qygt-outside-voices-in-the-locked-sales-drive.zip`

Download from Slack channel #shannon-connector-team-a attachments.

## Slack channels

- `#shannon-connector-team-a` — main connector team channel
- `#cloudflare-warp` — GCP access support
- Canvas: https://turing-company.slack.com/docs/T8YAVN6JJ/F0C4WD2J2SH

## GCP setup (required for pulling connector images)

```bash
gcloud auth login
gcloud auth configure-docker us-central1-docker.pkg.dev
gcloud config set project delivery-g-obi
# Verify access:
gcloud artifacts docker images list \
  us-central1-docker.pkg.dev/delivery-g-obi/data-obi-rl-gym/benchmark-base \
  --limit=1
```

**Cloudflare WARP** is required for GCP access after ZTNA rollout.

## Key rules from Slack

### Folder naming (CRITICAL — from Md Hussain)
- Task folder name must remain EXACTLY the original task name
- NO `_v1`, `_v2`, dates, timestamps, suffixes
- NO `harbor-single-task-_d7ve4og` auto-generated names
- Example: `the-answer-she-already-gave` — exactly as provided
- Personal copies are fine, but the SUBMITTED folder must have ONLY the original name

### PreQC findings
- PreQC D1 findings ARE blocking (prevent Oracle+GLM from starting)
- Migrate ALL D1-flagged regex checks from verifier.json to Python assertions
- PreQC D2: non-root USER is BLOCKING (portal wants root for some tasks)

### Portal API (from Finding 35 in QC-SELF-TRAINING.md)
```javascript
// Run PreQC
fetch('/trainer/api/run', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({task_id: 'content-xxx-v4', mode: 'internal'})})
// Run Oracle+GLM
fetch('/trainer/api/run', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({task_id: 'content-xxx-v4', mode: 'delivery'})})
// Check status
fetch('/trainer/api/runs').then(r => r.json()).then(d => d.gates['content-xxx-v4'])
```

## The 12 connector gyms

1. Slack
2. Snowflake
3. Supabase
4. Outlook
5. Email & Calendar ← **this task uses this**
6. GitHub
7. Google Workspace
8. Linear
9. Microsoft 365
10. Microsoft Teams
11. Notion
12. Shopify

## Connector vs Non-Connector (from TOC)

### How to tell from the files
- **Connector:** has `environment/mcp/proxy/server.py` — agent queries a live MCP gym
- **Non-connector:** all inputs are static files under `environment/input/`

### This task is a CONNECTOR:
- Has `environment/mcp/proxy/server.py` (35KB)
- Uses `email-calendar-gym` MCP server
- Agent must query live calendar/email through MCP tools
- Has `consistency/` directory (connector-specific harness)

## 10 client-audit patterns (P-C1 through P-C10)

From the Common Issues & Strategy tab:

| Pattern | Issue |
|---|---|
| P-C1 | Raw-SQL proxy bypass |
| P-C2 | Proxy healthcheck timeout |
| P-C3 | Silent corpus loss and broken tools |
| P-C4 | Judge gates reward with no rubric |
| P-C5 | Undisclosed workflow requirements |
| P-C6 | Task too easy |
| P-C7 | Dead score buckets and empty checks |
| P-C8 | Duplicate checks and unbalanced weights |
| P-C9 | False negatives reported as model failures |
| P-C10 | Oracle or solvability failure from a hidden rule |

## Connector-specific workflow (from Onboarding Process tab)

### PART A: One-Time Project Setup
1. Verify Access & Permissions
2. Install and Configure Docker
3. Set Up GCP & Artifact Registry
4. Install Python & Harbor CLI
5. Environment & API Configuration
6. Harbor GLM Configuration
7. Optional: AI Coding Assistant Setup

### PART B: Task Execution Workflow
8. Claim and Download Task
9. Task Understanding & Review
10. Oracle Execution
11. Model Evaluation & Trajectory Analysis
12. Task Hardening
13. Quality Control (QC)
14. Final Package Consistency Check

### Submission Readiness Checklist
- Oracle passes (reward 1.0)
- 4 GLM-5.2 difficulty runs, pass rate ≤ 50% (0-2 out of 4)
- 1 solvability run (non-Oracle model, reward 1.0)
- Stability runs (3+ repeats, all 1.0)
- review.csv complete
- README.md present
- qc_report.html present
- Folder name = exact original task name
