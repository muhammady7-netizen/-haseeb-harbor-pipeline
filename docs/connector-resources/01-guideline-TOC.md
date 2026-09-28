# Connector Tasks Foundation Guidelines — Full Table of Contents

**Source:** https://docs.google.com/document/d/1nVBar4JGUSvADM-LCeXLrLGPCh5jlgwSZcYmKTr-1VQ/edit?usp=sharing
**Title:** Connector Tasks Foundation Guidelines (Google Doc, 5 tabs)
**Accessed:** 2026-09-28 via Playwright browser (authenticated as muhammad.y7@turing.com)
**Status:** View-only (request edit access). Full TOC extracted via Ctrl+A + getSelection.

---

## Tab 1 — General Guidelines

### TRAINER GUIDELINES: Claiming, Checking, and Evaluating a Harbor Task Step by Step

**Contents**

**Part 1 — General system setup (one-time, per machine)**
- 1.1 What you need (at a glance)
- 1.2 Install Docker (Windows/macOS/Linux, disk space)
- 1.3 Install the gcloud CLI and get image access (Install gcloud, Authenticate, Verify access)
- 1.4 Pull the benchmark-base image (one-time)
- 1.5 Install Python 3.12+ and the Harbor CLI (Check Python, Install Harbor [uv/pipx/pip], Verify)
- 1.6 Set up your API keys (keep them secret) (Store outside repo, Quick key sanity check)
- 1.7 Setup is done when…
- 1.8 Set up an AI coding assistant — opencode (preferred) or Cursor
- 1.9 Create the GLM harbor config file (one-time)

**Part 2 — The trainer workflow (per task)**
- Step 1 — Claim a task from the tracker
- Step 2 — Inspect the task files for general correctness
  - 2a. instruction.md — the task prompt (the "query")
  - 2b. tests/manifest.json — the verifiers
  - 2c. solution/ — the golden answer
- Step 3 — Run the oracle check (and fix the gold if it fails)
  - 3a. Run the oracle
  - 3b. Read the oracle result
  - 3c. If oracle fails — find the cause and fix it
  - 3d. What "passing" vs "a broken run" look like
  - 3e. If the golden trajectory is missing or very wrong — defer it
- Step 4 — Run 4 model runs and check the pass rate is 50% or below
  - 4a. (Optional but recommended) One run first
  - 4b. The 4-run battery (Choosing --n-concurrent)
  - 4c. Read the results
  - 4d. The pass rate you report — and the 50% acceptance bar
  - Definition of done — before you submit (Step 5)
- Step 5 — Run the unified QC tool; submit the task for automated QC
  - 5a. Get the tool
  - 5b. Setup (about 2 minutes)
  - 5c. Start here (free, makes no API call)
  - 5d. Real review
  - 5e. Post-run QC — reviews your actual harbor runs
  - 5f. Three things worth knowing before you start
  - 5g. What you get
  - Quick reference
  - Troubleshooting

**Local Setup (Used in onboarding)**
- Company Bench: Running a Task Locally, From Scratch
  - What you are setting up / Prerequisites at a glance
  - Step 1: Docker
  - Step 2: Access to the task image (Install gcloud, Authenticate, Verify access)
  - Step 3: The Harbor CLI (Install [uv/pipx/pip], Verify)
  - Step 4: Credentials (Why both variables, Optional: JUDGE_MODEL, Verify)
  - Step 5: Your first run (Oracle) (What to expect, Success looks like)
  - Step 6: GLM-5.2 runs (A single run first, The 4-run battery, Choosing --n-concurrent, Reading the results, Where things land, The browser UI easiest option, The score, Which verifiers passed and why, Telling a broken run from a genuine failure, Troubleshooting, Quick reference)

---

## Tab 2 — Onboarding Process

### Connector Tasks — New Trainer Onboarding Guide

**Workflow Overview**

**PART A: One-Time Project Setup**
1. Verify Access & Permissions
2. Install and Configure Docker
3. Set Up GCP & Artifact Registry
4. Install Python & Harbor CLI
5. Environment & API Configuration
6. Harbor GLM Configuration
7. Optional: AI Coding Assistant Setup

**Part A Verification Checklist**

**PART B: Task Execution Workflow**
8. Claim and Download Task
9. Task Understanding & Review
10. Oracle Execution
11. Model Evaluation & Trajectory Analysis
12. Task Hardening
13. Quality Control (QC)
14. Final Package Consistency Check

**Submission Readiness Checklist**

---

## Tab 3 — Connector Task Detail (THE KEY REFERENCE)

### Connector Tasks — Onboarding Handbook

**Overview**
**Acceptance criteria**
- The difficulty band
- Why tasks are rejected
- Five rules that are never negotiable
**Glossary**

**1 · Connector vs non-connector**
- 1.1 Which one are you holding? (What each family is, How to tell from the files, Side by side)
- 1.2 What your experience is worth
- 1.3 Which strategy to use
- 1.4 The configuration that bites
- 1.5 Categories

**2 · Difficulty and hardening**
- 2.1 A disclosed rule can still be too easy
- 2.2 The honest levers
- 2.3 Write the prediction first
- 2.4 "Too easy" is usually a symptom, and ceilings are real

**3 · The connector surface**
- 3.1 Four doors. Closing three is the same as closing none
- 3.2 Probe the live gym before you design anything
- 3.3 Gym and proxy behaviour
- 3.4 Defects you inherit and must disclose

**4 · Verifier fairness**
- Other fairness findings
- 4.1 The full audit distribution, as a checking order
- 4.2 Duplicate checks and disproportionate scoring
- 4.3 The ten client-audit patterns

**5 · Evidence discipline**
- Attribution — whose fault was the run

**6 · Migration discipline**
**7 · Environment and setup**

**8 · Seeding and the upload anchor**
- 8.1 Seeding
- 8.2 Ship the reference server.py unmodified
- 8.3 The upload anchor

**9 · The package and the review record**
- 9.1 What goes in the package
- 9.2 review.csv

**10 · QC review, and reading a failed check**
- The mandatory model-failure sanity check
- When the check aborts

**11 · Where the hours go**
- What reliably adds hours
- Packaging gate findings

**12 · What this guidance does not cover**

**13 · Quick reference checklist**

**14 · The data behind each connector**
- 14.1 The 12 gyms at a glance
- 14.2 Slack
- 14.3 Snowflake
- 14.4 Supabase
- 14.5 Outlook
- 14.6 Email & Calendar
- 14.7 GitHub
- 14.8 Google Workspace
- 14.9 Linear
- 14.10 Microsoft 365
- 14.11 Microsoft Teams
- 14.12 Notion and Shopify
- 14.13 Using the data to design a task

---

## Tab 4 — Common Issues & Strategy

### Connector Tasks — Common Issues & QC Playbook

**How to use this playbook**
**Standards this playbook assumes**
**Order of work**

**Common issues**
**Review strategy**
**Two-pass QC workflow**
- Pass 1: generate the QC report
- Pass 2: verify the report in a fresh session

**Client rejection patterns**

**Issue patterns and what to do**
- At a glance
- P-C1 — Raw-SQL proxy bypass (Writing a fair tool_execution check)
- P-C2 — Proxy healthcheck timeout
- P-C3 — Silent corpus loss and broken tools
- P-C4 — Judge gates reward with no rubric
- P-C5 — Undisclosed workflow requirements
- P-C6 — Task too easy
- P-C7 — Dead score buckets and empty checks
- P-C8 — Duplicate checks and unbalanced weights
- P-C9 — False negatives reported as model failures
- P-C10 — Oracle or solvability failure from a hidden rule
- Too-easy flag (P-TE)
- One-off issue
- Pre-submission self-check

**Glossary**
**Open items**

---

## Tab 5 — Tips & Tricks

### Connector Tasks — Tips & Tricks

**QUICK REFERENCE**
1. Start with the environment, not the task
2. Read the task before you try to improve it
3. Hardening: make the model reason, not hunt
   - Prefer interpretive difficulty
   - Write the prediction before you run the battery
   - Know when the task has hit a ceiling
4. Every meaningful change needs a consistency sweep
5. Evidence must be fresh
6. Read all 4 trajectories — not just the score
7. Re-run the oracle after changes
8. Keep review.csv as history, not a snapshot
9. Useful time-saving habits
10. Common symptoms and what to check first
11. Final submission check

---

## Key takeaways from the TOC structure

1. **Connector tasks have an MCP proxy server** (`environment/mcp/proxy/server.py`) that the agent queries — unlike non-connector tasks where all inputs are static files
2. **Difficulty is about reasoning, not hunting** — prefer interpretive difficulty (Section 3 of Tips)
3. **The connector surface has "four doors"** — closing three is the same as closing none (Section 3.1 of Detail)
4. **Ship the reference server.py unmodified** (Section 8.2 of Detail)
5. **10 client-audit patterns** (P-C1 through P-C10) are the main rejection patterns
6. **Two-pass QC workflow** — generate report, then verify in fresh session
7. **The 12 connector gyms**: Slack, Snowflake, Supabase, Outlook, Email & Calendar, GitHub, Google Workspace, Linear, Microsoft 365, Microsoft Teams, Notion, Shopify
8. **Five rules that are never negotiable** (under Acceptance criteria)
9. **Seeding and upload anchor** are connector-specific concepts (Section 8)
10. **Migration discipline** is connector-specific (Section 6)
