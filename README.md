# Local QC — Harbor Task Quality Control Knowledge Base

**Purpose:** Everything needed to judge a Harbor task zip locally before uploading to the portal — the deep QC algorithm, the 7-layer checklist, the 12-finding case study, and the self-training that prevents missing semantic defects.

**Built from:** A real law-b39-l16-custody-letter-instruction-audit case where the portal's QC found 12 major findings that a local `--no-model` deterministic scan completely missed. This repo captures every lesson.

---

## What's here

```
local-qc/
├── README.md                           This file — overview + how to use
├── QC-SELF-TRAINING.md                 The 12 findings I missed + 7-layer checklist + red flags
├── docs/
│   ├── how-qc-works.md                 Deep analysis of the QC engine algorithm (3 layers, gates, counterexamples)
│   ├── portal-findings-law-b39.md      The 12 portal findings with exact evidence
│   ├── fix-plan-law-b39.md             The fix plan (19 row wording changes + 3 new CL entries)
│   ├── 7-layer-checklist.md            The checklist to run on every zip
│   ├── 9-10-judgment-case-study.md     How judge.py works + what it caught
│   ├── definitive-qc-checklist.md      331 checks across 11 layers with verdict computation
│   ├── qc-engine-deep-research.md      Deep research into the QC engine internals
│   ├── qc-standards-summary.md         OBI task quality standards summary
│   ├── all-hands-key-takeaways.md      Key takeaways from All Hands meeting
│   └── repo-overview.md                What each file in this repo does
├── scripts/
│   ├── judge.py                        One-command task judge (CRLF/BOM + gold derivability + trajectory freshness + review.csv + /tests lock + host paths + D1-D5 linter)
│   └── judge-zip.md                    How to use judge.py
├── web/                                Next.js web app for the local QC judge
│   ├── app/                            Next.js app
│   ├── scripts/                        Server-side scripts
│   └── package.json
├── law-b39-task/                       The law-b39 task (working copy)
│   ├── instruction.md
│   ├── environment/
│   ├── solution/
│   ├── tests/
│   ├── evaluations/
│   ├── review.csv
│   └── task.toml
└── law-b39-TASK-STATE.md               Current state of the law-b39 task
```

## How to use

### Quick judge
```powershell
python scripts/judge.py <task.zip> --no-model
```

### Web app
```powershell
cd web
npm run dev
# Open http://localhost:3000
```

## STRICT WORKFLOW — Read before any task

**`STRICT-WORKFLOW.md` is the authoritative process. Every session follows it. Do not stop working until the task is ACCEPTED in V2.**

The loop: build zip → judge locally (CLI + localhost:3001 web app) → fix blocking findings → push new patterns to GitHub (train local-qc) → re-judge until zero findings → upload to portal (Playwright MCP, already set up) → PreQC → verify review.csv → Oracle+GLM×4 → fix if any blocker → submit → accepted.

Browser automation is already set up with opencode (Playwright MCP) — see `BROWSER-SETUP.md`. Use it. Do not manually click.

## Key lessons

1. **Never trust `--no-model` alone** — it misses semantic defects (gold derivability, self-contradiction, failure cause validity, surface-form fairness)
2. **The 7-layer checklist** must be run on every zip before uploading
3. **CRLF/BOM is a P0 blocker** — Harbor portal crashes on it
4. **review.csv counts must match gold** — stale counts are P1
5. **Trajectory freshness** — embedded counts must match current gold
6. **/tests lock** — Dockerfile must not copy tests/solution/verifier into agent image
7. **D1-D5 linter** — prose regex grading, Dockerfile root, model pinning, agent fixtures, scoring axes
