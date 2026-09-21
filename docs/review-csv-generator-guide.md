# Review CSV Generator Tool — How to Use

## Overview
After finishing a task and uploading it to Google Drive, you must generate a `review.csv` using the Review CSV Generator tool. This file travels with the task package and records your review across 14 areas.

## Tool URL
https://script.google.com/a/macros/turing.com/s/AKfycbzi9BTJ8iVwPCCEGGaiaII9bKUwVl62mxkRpwGDfRYIKphxiDBfO-oF4B3A8Bc9AgYU/exec

## review.csv Format
Columns: `review_check, status, review_notes, change_made, what_to_record`

### Statuses
- **PASS** — No changes were made. Everything was already correct.
- **FIXED_AND_VERIFIED** — A change was made and re-measured. Record what changed.
- **N/A** — Not applicable (only for connector row and judge-consistency row when no judge).

### Row Order (14 checks)

| # | Layer | Review Question | Evidence to Inspect | Pass Criteria | Red Flags | What to Record |
|---|-------|-----------------|---------------------|---------------|-----------|----------------|
| 01 | Layer 1 · Package consistency | Do task.toml, instruction.md, every file under solution/, and every file under tests/ describe the same executable and gradable task? | Read all four sources. Compare required outputs, paths, formats, inputs, services, timeouts, scoring rules, and expected values. | The instruction asks for what the golden solution produces and the verifier grades; task.toml supplies everything both require. | Undeclared required files or fields; contradictory paths or formats; verifier-only requirements; stale manifests; missing dependencies. | Cite the conflicting files and exact requirement, explain impact, and propose one canonical fix. |
| 02 | Layer 1 · Clarity and scope | Is the task well defined for an agent that only sees the declared instruction and environment? | Instruction, input inventory, connector descriptions, output requirements, and verifier expectations. | A capable agent can identify the goal, available evidence, required deliverables, and completion criteria without guessing hidden rules. | Ambiguous terms; missing units or date ranges; unstated assumptions; multiple plausible answers; hidden precision or formatting demands. | Describe the ambiguity, plausible interpretations, and the smallest instruction or verifier change that resolves it. |
| 03 | Layer 1 · Realism and leakage | Does this resemble useful real work without exposing the answer or relying on artificial traps? | Instruction, packaged inputs, seeded connector data, filenames, environment image, solution visibility, and test fixtures. | The scenario, inputs, tools, and outputs are plausible; necessary complexity follows from the work; golden facts are not agent-visible. | Contrived identifiers or traps; impossible access assumptions; answer-bearing filenames; golden files mounted into the workspace; toy output with no practical value. | State whether the task is realistic, identify leakage or contrivance, and suggest a more natural framing where needed. |
| 04 | Layer 2 Difficulty | Is the task difficult for GLM 5.2? | GLM 5.2 runs | GLM 5.2 pass <= 2/4 | GLM 5.2 pass >= 3/4 | How many GLM 5.2 passes |
| 05 | Layer 2 Solvability | Is this task solvable to a frontier model given only the task + env? | If there are no pass trajectory from multiple frontier model with multiple repeats, then we should check if that's too hard (which is good) or task not well-defined or verifiers not consistent with task | Human/AI can find a pass trajectory which leads perfect reward 1.0, by only looking at task + env. And human agree that verifiers are the right checks for the task + env | no pass trajectory from multiple frontier model with multiple repeats | single successful run among 6 passes |
| 06 | Layer 2 Stability | Repeated run of verifiers on the same task rollout should produce the same output, ideally it should be done on the solvability pass trajectory | Verifier repeat results | same reward across 3 repeats of verifiers run | same reward across 3 repeats of verifiers run | same reward across 3 repeats of verifiers run |
| 07 | Layer 3 Oracle Mode | harbor cli should be able to run all tasks with oracle mode and produce reward 1.0 for all tasks in both E2B and Modal sandbox backend | Note that oracle != solvability, oracle just means there exists an oracle trajectory that satisfy the verifier. oracle only confirms the consistency between oracle and verifier, but not task and verifier | provide oracle mode agent verifiers results and confirm it's 1.0 rewards for all | | provide oracle mode agent verifiers results and confirm it's 1.0 rewards for all |
| 08 | Layer 4 · Environment and files | Can the agent reliably use the sandbox, dependencies, inputs, workspace, and required output paths? | Trajectory setup steps, filesystem operations, dependency installation, logs, produced artifacts, exception details, and E2B environment metadata. | Inputs are present and readable; required tools run; writes persist; verifier sees the intended artifacts; failures are task-related rather than infrastructure-related. | Missing files; incompatible architecture; dependency-build failures; permission errors; outputs written to the wrong workspace; artifacts disappear before verification. | Name the failed interaction and classify it as task packaging, sandbox, dependency, harness, or agent error. |
| 09 | Layer 4 · Connectors, MCPs, and CLIs | Are intended connectors discoverable, usable, and sufficient for the task? (Can be N/A) | Declared MCP/CLI metadata, tool discovery, calls and responses, authentication behavior, pagination, state changes, and verifier-side database checks. | The agent can discover the interface, read all necessary records, perform allowed writes, handle pagination, and confirm resulting state without hidden credentials. | Service never starts; missing auth; wrong endpoint; incomplete pagination; unusable schemas; silent tool errors; verifier expects state the connector cannot create. | Record connector name, failed or successful operations, affected trial, and whether the issue is data, service, auth, interface, or agent usage. Can be N/A |
| 10 | Layer 4 · Deliverables and artifact quality | Are the requested outputs complete, realistic, and usable in their declared formats? | Instruction output list, workspace artifacts, golden files, JSON structure, and any PDF, DOCX, spreadsheet, HTML, Markdown, or text deliverables. | Every required artifact exists, opens or parses, contains substantive requested content, and uses a format appropriate to the work. | Placeholder or malformed files; JSON-only grading ignores required rich output; polished-looking artifact lacks substance; verifier checks the wrong path or stale copy. | List missing or weak artifacts and distinguish content quality, format validity, path, and materialization issues. |
| 11 | Layer 5 · Verifier coverage and fairness | Does the verifier measure the task requirements accurately and proportionately? | tests/, per-check results, weights, reward aggregation, LLM rubric text and explanations, golden artifacts, and agent outputs. A reward of 1.0 is evidence, not proof of task quality; a fractional or zero reward may reflect an agent error, task defect, verifier defect, or infrastructure problem. | A verifier is justified, checks a non-ambiguous expectation of the task. Verifiers cover all query expectations, accept valid equivalent solutions, reject substantive errors, and match the instruction. | Query has requirements that aren't reflected in the verifier suite. Verifiers are brittle: assign a deterministic expectation of an ambiguous requirement. Duplicate checks / excessive overlap. Is regex too restrictive when there are multiple equally valid answer? deterministic / regex checks are used inappropriately. regex graders are too restrictive and reject semantically correct outputs. Instruction didn't specify the results should be included in the final message. Judge missed parts of the trajectory and gave incorrect verdict. Feasibility issues. A lot of the stated deterministic judges don't end up contributing because they lack verifiers. | This is particularly important. Each verifier must have a justification with a reference to part of query that outlines the expectation it's checking. Identify ambiguous, defective, or missing checks; quote the requirement in your own words and propose a concrete verifier fix. |
| 12 | Layer 5 · LLM judge consistency | Are qualitative judgments grounded in the actual artifact and stable enough to trust? | Vendor stability repeats, judge model/config, artifacts, and verifier stdout. | Explanations cite observable evidence, do not invent missing content, and repeated judgments do not flip materially on identical deliverables. | Factually wrong rationale; judge overlooks present content; rubric demands unstated detail; inconsistent repeats; invalid model/provider configuration. | Record the disputed rubric item, artifact evidence, repeat behavior, and recommended rubric or judge configuration change. |
| 13 | Layer 5 · Reward hacking and exploitability | Could an agent earn a high reward without genuinely completing the intended task? | Trajectory, final artifacts, verifier implementation, golden data exposure, state assertions, path handling, and reward aggregation. | Reward tracks genuine completion; shortcuts, spoofed files, hardcoded answers, prompt injection, and stale state cannot satisfy the verifier. | Agent reads golden data; writes directly to verifier state; mimics expected strings without evidence; exploits unchecked fields; skips required side effects yet passes. | Describe the exploit path, affected checks and reward, severity, and an acceptance test that closes it. |
| 14 | Cross-trial · Calibration | Across four trials, does the task have a healthy difficulty and behavior profile? | Strict passes across four, fractional rewards, exceptions, model/harness differences, automatic flags, and all Layer 5 findings. | Results are neither trivially universal nor universally blocked; model differences are plausible; fractional scores and exceptions have understandable causes. | Zero passes because infrastructure is broken; six passes with shallow behavior; systematic harness-only failure; fractional rewards driven by one defective rubric item. SOTA model fails a criterion but weaker models pass that criterion. All models fail a particular criterion with the same answer. | Summarize difficulty, suspicious cross-trial patterns, highest-priority problems if any. |

## How to Use the Tool

1. Open the tool URL: https://script.google.com/a/macros/turing.com/s/AKfycbzi9BTJ8iVwPCCEGGaiaII9bKUwVl62mxkRpwGDfRYIKphxiDBfO-oF4B3A8Bc9AgYU/exec
2. Enter your name (Trainer) and email.
3. Paste the Google Drive folder URL for the task.
4. Click "Fetch review.csv" to load any existing draft.
5. Complete all 14 checks:
   - For each check, select Status (PASS / FIXED_AND_VERIFIED / N/A)
   - Write Review Notes answering the review question
   - Write Change Made (or "No change required" if PASS)
   - Write What to Record per the guidance for that check
6. All 14 checks must be fully completed before you can download.
7. Click "Download review.csv" to generate the file.
8. Click "Submit and upload to Google Drive" to upload directly.

## Important Notes
- The form auto-saves locally in the browser.
- Status, Review Notes, Change Made, and What to Record are required for every check.
- Only use N/A for the connector row (row 09) and the judge-consistency row (row 12) when the task has no judge-based check.
- Every note must cite a specific file, run, or check; a measurement claim without a measurement is a defect.
- The review.csv must be included in the task package zip.

## Existing review.csv Format Reference
The review.csv in the task package uses this exact header:
```
review_check,status,review_notes,change_made,what_to_record
```

### Example entries:
```csv
"Layer 1 · Package consistency","PASS","9 checks in verifier.json. Gold matches inventory: answer.md; letter_line_review.csv; results.json. Dockerfile pinned by sha256 digest. golden_trajectory.json is oracle ATIF. Evaluations present (oracle + nop).",,"All checks declared; gold correct"
"Layer 1 · Clarity and scope","PASS","Instruction binds review_protocol.md and named input files. Deliverables and results.json keys are explicit in submission_format.md. One canonical reading for every verdict and governing entry.",,"All rules disclosed; one canonical reading"
"Layer 1 · Realism and leakage","PASS","Realistic custody letter instruction audit. Gold only under solution/. No answer leakage into agent-visible input.",,"No gold leakage into agent-visible input"
"Layer 2 Difficulty","PASS","16 letter lines with cross-document contradiction traps (clarification overrides original; subjects not in either record; cited entries that do not exist). GLM difficulty from RP-401 clarification precedence and RP-404 NOT_IN_RECORD traps.",,"GLM difficulty from precedence and contradiction rules"
"Layer 4 · Environment and files","FIXED_AND_VERIFIED","5 input files under environment/input/ (clarification.md; letter_lines.csv; original_instruction.md; review_protocol.md; submission_format.md). 16 letter lines. Added non-root USER to Dockerfile.","Added non-root USER to Dockerfile","No environment issues"
"Layer 4 · Connectors, MCPs, and CLIs","N/A","Non-connector task. No MCP connector or CLI graded surface. Keywords/offline local files only.",,"N/A: NonConnector task; no connector/MCP/CLI requirements"
"Layer 5 · LLM judge consistency","N/A","No LLM judge; all 9 checks are deterministic regex/equals/table_equals/object_equals.",,"N/A: no LLM judge path in this task"
"Layer 5 · Verifier coverage and fairness","PASS","9 checks declared. register_table uses table_equals with row_set lock (prevents duplicates and cross-product dumps). results_figures uses object_equals with closed=true. answer_at_odds_figure checks correct count next to label. answer_at_odds_figure_exactly_one prevents hedging. All deterministic.",,"All checks fair and declared"
"Layer 5 · Reward hacking and exploitability","FIXED_AND_VERIFIED","No answer leakage. Inputs chmod a-w in Dockerfile. Non-root USER added. Row_set lock prevents duplicate-row exploits. answer_at_odds_figure_exactly_one prevents hedging.","Added non-root USER to Dockerfile","No reward hacking"
"Cross-trial · Calibration","PASS","Oracle 1.0. Difficulty from cross-document contradiction (RP-401 clarification precedence) and NOT_IN_RECORD traps (RP-404).",,"Difficulty from precedence and contradiction traps"
```

## Workflow Summary
1. **Upload task** to Google Drive folder (Batch_no from tracker)
2. **Generate review.csv** using the tool — complete all 14 checks
3. **Download review.csv** and include it in the task package
4. **Submit to QC** — upload the package to Shannon QC Control (PreQC then QC-Oracle-GLM)
