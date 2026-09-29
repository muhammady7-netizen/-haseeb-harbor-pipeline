# Common Issues & QC Playbook — Full Audit Report

**Source:** Connector task audit (28 tasks, 24 with issues, 82 fail cells)

---

## Key Statistics

| Gate / Layer | Fails | Reading |
|---|---|---|
| Layer 2 Difficulty | 13 | 12 are "too easy": 3/4 GLM-5.2 strict passes |
| Layer 4 Connectors, MCPs, CLIs | 13 | Proxy timeout, silent corpus loss, broken tools |
| Layer 5 Reward hacking | 13 | Unauthenticated raw-SQL proxy bypass |
| Layer 5 Verifier coverage | 9 | Dead buckets, duplicates, undisclosed steps |
| Layer 4 Environment | 9 | Healthcheck timeout, OOM, Dockerfile conflicts |
| Layer 5 LLM judge | 9 | Judge gates reward with no rubric → 0 on missing key |
| Layer 5 Cross-trial | 7 | False negatives as model failures |
| Layer 1 Clarity | 4 | Undisclosed workflow/trace requirements |
| Layer 1 Package | 2 | Verifier-only workflow rule |
| Layer 2 Solvability | 1 | Pass required guessing undisclosed rule |
| Layer 3 Oracle | 1 | Golden fails proxy-bypass check |
| Layer 4 Deliverables | 1 | Agent timeout → no answers.json |
| Layer 2 Stability | 0 | Healthy |
| Layer 1 Realism | 0 | Not flagged |

## The 10 Issue Patterns (P-C1 through P-C10)

### P-C1 — Unauthenticated raw-SQL proxy bypass (12/28)
**Gates:** Layer 5 Reward hacking (sanctioned_interface_use)
**Root cause:** Proxy exposes GET /raw/{gym}/state?verify_queries=<SQL> and POST /raw/{gym}/step on localhost:7000. Agent runs one SQL SELECT, derives every graded value, bypasses MCP workflow. Verifier only reads answers.json → full reward.
**Fix:** [Harness] Disable/authenticate /raw/ passthrough. [Task] Add tool_execution check for sanctioned MCP tools. [Pre-ship] curl the raw endpoint from sandbox — if it returns a row, don't ship.

### P-C2 — Proxy healthcheck timeout (8/28)
**Gates:** Layer 4 Environment
**Root cause:** localhost:7000/health times out before agent starts. E2B lifecycle failure, not model failure.
**Fix:** Raise healthcheck timeout/retry budget. Keep retries generous. Crashed runs are score_eligible=False, replaced by retry.

### P-C3 — Silent corpus loss / broken tools (13/28)
**Gates:** Layer 4 Connectors
**Root cause:** Connector returns incomplete corpus with no marker. Agent can't tell data is missing. Some tools return HTTP 200 but "Tool call failed" to agent.
**Fix:** Surface truncation as explicit marker. Broken tools must fail loudly. Run oracle's query through MCP tool, compare with oracle corpus.

### P-C4 — Judge gates reward with no rubric (7/28)
**Gates:** Layer 5 LLM judge
**Root cause:** Judge configured in task.toml but rubric.toml has zero items. Missing OPENAI_API_KEY → score 0.0 before any file_check runs.
**Fix:** If rubric.toml has zero items, judge must not gate scoring path. Lint: zero rubric items → no judge config.

### P-C5 — Undisclosed workflow requirements (4/28)
**Gates:** Layer 1 Clarity, Layer 1 Package, Layer 5 Verifier fairness, Layer 2 Solvability
**Root cause:** Verifier grades workflow shape instruction never states — required first query, minimum call count, bots-as-people rule. Correct runs penalized.
**Fix:** Every tool_execution check, rubric "fail if fewer than N" rule, and definitional count must trace to instruction.md line. Delete or disclose.

### P-C6 — Under-difficulty: 3/4 strict passes (12/28)
**Gates:** Layer 2 Difficulty
**Root cause:** Tasks ask for small set of exact values derivable from single query. GLM-5.2 solves 3/4.
**Fix:** Close P-C1 first (often moves 3/4 to discriminating). Add harder sub-question. One canonical battery, one checksum.

### P-C7 — Dead score buckets (3/28)
**Gates:** Layer 5 Verifier coverage
**Root cause:** Manifest declares weighted buckets but some have no checks. tool_execution with empty expected_tools verifies nothing.
**Fix:** Every weight bucket must have ≥1 check. Name tools in every tool_execution check or delete it.

### P-C8 — Duplicate checks / disproportionality (2/28)
**Gates:** Layer 5 Verifier coverage
**Root cause:** Two checks test same fact. File-parses check weighted same as headline question → wrong answer still scores 0.8.
**Fix:** No duplicates. Weight headline above format checks.

### P-C9 — False negatives as model failures (7/28)
**Gates:** Layer 5 Cross-trial
**Root cause:** 6-cell matrix runs same verifier defects. Gold-exact answers lose reward by tool_execution check. Published as model failures.
**Fix:** Fix P-C1/P-C4/P-C3 first. verifier_reasonableness=fail → score_eligible=False, replaced by retry.

### P-C10 — Oracle/solvability from hidden rule (2/28)
**Gates:** Layer 3 Oracle, Layer 2 Solvability
**Root cause:** Downstream of P-C1/P-C5. Golden fails bypass check; solvability pass required guessing undisclosed rule.
**Fix:** Fix verifier/rule, not golden. Re-run oracle.

## Two-Pass QC Workflow

### Pass 1: Generate QC Report
1. Run /connector-task-reviewer skill
2. Independent verification before trusting README/review.csv
3. Audit review.csv itself
4. Model-failure sanity check (reward hacking, unfair verifier, non-model failure)
5. Gate verdicts
6. Final recommendation: Send to client / Needs rework

### Pass 2: Verify in Fresh Session
1. Independent re-derivation
2. Accuracy verdict on existing report
3. Model-failure fairness check re-verified from scratch
4. Audit review.csv independently
5. Corrected conclusions if anything was wrong

## Harness vs Author Split
- **Harness/proxy-image defects (~62/82 cells):** P-C1 (raw passthrough), P-C2 (healthcheck), P-C3 (corpus loss), P-C4 (judge gate)
- **Task-author defects (~20/82 cells):** P-C5 (undisclosed workflow), P-C6 (under-difficulty), P-C7 (dead buckets), P-C8 (disproportionality)

## Review Prompts (Full Text)

### Review Prompt 1
```
You need to do QC of a task, as given below.

## Target
<path-to-the-task-folder>

## Step 1 — Run the pipeline
Use the `/connector-task-reviewer` skill on the target folder. Run the full pipeline
(don't skip stages) and generate `QC-Report-{id}.md` inside the task folder.

## Step 2 — Independent verification (do this BEFORE trusting any existing docs)
Before reading `README` or `review.csv` as ground truth, do your own independent
pass over the task:
- Reproduce the failure/pass behavior yourself where possible
- Only after forming your own conclusion, cross-check against README and review.csv
- Do not carry forward any claim unless verified against actual evidence

## Step 3 — Audit review.csv itself
Check for missing rows, inconsistent gate labels, contradictory verdicts, malformed data

## Step 4 — Explicit model-failure sanity check
- Reward hacking: shortcut/exploit vs genuine completion?
- Unfair verifier: requires something not implied by task spec?
- Non-model-caused failure: harness/env/judge/infra vs genuine model capability?

## Step 5 — Gate verdicts
For every gate: Pass or Fail, each with one-line reason + evidence path

## Step 6 — Final recommendation
"Send to client" or "Needs rework", with one-line justification

## Output format
1. Gate-by-gate verdict table
2. What's correct (with evidence)
3. Issues found — task-level (with evidence + severity)
4. Issues found — review.csv (with evidence)
5. Model-failure sanity check (3 items)
6. Final recommendation (one line, justified)

## Guardrails
- Every finding must trace to actual file/path/log
- Do not accept README/review.csv claims at face value
```

### Review Prompt 2 (Fresh Session)
```
Help me confirming whether the review of a task is 100% accurate or not.

## Target
Task folder: <path-to-the-task-folder>
Existing report: QC-Report-*.md (in the folder)

## Objective
Do NOT treat the existing QC report as correct by default. Independently re-verify.

## Step 1 — Independent re-derivation
Form your own conclusion by inspecting task files directly. Then compare with report.

## Step 2 — Accuracy verdict
For each major claim: Confirmed accurate / Inaccurate / Missing

## Step 3 — Model-failure fairness check (re-verify from scratch)
- Reward hacking
- Unfair verifier / prompt-to-verifier mismatch
- Non-model-caused failure

## Step 4 — Audit review.csv independently
Check for issues separate from task outcome

## Output format
1. Overall verdict: Is existing QC report 100% accurate? (Yes/No)
2. Report accuracy breakdown table
3. Model-failure fairness check (3 items)
4. review.csv audit: clean or issues
5. Corrected conclusions (if anything was wrong)

## Guardrails
- Do not accept existing report or README/review.csv at face value
- Every conclusion must trace to evidence you checked yourself
- If cannot verify: "Uncertain — could not verify"
```
