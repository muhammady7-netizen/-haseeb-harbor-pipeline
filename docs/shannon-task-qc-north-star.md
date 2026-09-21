# Shannon Task QC North Star

August 2026

## Your role in Quality Control

You are reviewing tasks for quality. This document lays out exactly what we mean by quality, and how to determine if a task is of high quality or not.

### IMPORTANT: How to use LLMs in QC
You should never take an LLM output as the final determination of high quality. You may use LLMs to help parse out information and analyze the task and its individual components, but you can never take an LLM output at face value – especially as the final judge of quality. You need to understand the prompt and verifiers yourself in order to make a determination. You are the ultimate judge of quality.

## Task structure
Every task you review will be composed of a few key parts (format follows the Harbor Framework):
- `instructions.md` — "prompt" - the prompt the model will receive
- `manifest.json` / `verifier.json` — "rubric" aka "verifier", the verifiers that grade the model's work
- the file environment — the input files and tools/skills/connectors the model has access to

Once you have completed a model run (either through Task Hub or harbor run), you will also have access to `trajectory.json` (the agent's steps and tool calls in its run) and other artifacts after a model has attempted the task. This information is critical in determining a good task.

## What is a good task?
- Prompts, input files, and environments are realistic (reflects type of work and prompts from real users), non-trivial, accurate, relevant, and not too long and over-specified.
- Verifiers check what is asked for in the prompt such as deliverables and exact figures/calculations in a complete and fair manner. Verifiers are objective, comprehensive, and deterministic.
- The model fails for real reasons. The prompt and verifiers were aligned, the input files were actually there. The model had all of the information it needed yet it still made a reasoning or process-based error that led to failure.

A good task passes 3 quality gates. Each must pass for a quality task.

---

## STEP 1 — The prompt

Check the prompt against the files (or full environment if needed). Answer each of the following:
1. Does every file, folder, and tool named in the prompt really exist?
2. Does each file hold the data or assumptions or info the prompt says it holds?
3. Can the model find everything it needs in the prompt and the files? (Nothing needed should be missing, hidden, or presumed)
4. If there are connectors/apps that the model needs to work with, are these accurately specified as skills in the environment?
5. Given adequate time, could a human finish this task with only these files?

If the answer to any of these is No, then the task is broken. Stop the review here, and give a verdict of fix or reject.

Then judge the prompt itself:
1. Does the task need several steps and real thinking? One search or one command is not enough and it's too trivial.
2. Does the prompt explain how to do the work, step by step? A Yes here is a problem. A good prompt says what the user wants naturally and realistically, not how to do it.
3. Does the prompt give exact file names, numbers, or wording that only exist to help the verifiers pass? A Yes here is a problem. Real users do not write like this.
4. Does it ask for work that is reasonable and realistic? Does it look like the real user prompts we started from?

Some vagueness is normal and fine. It is only a problem when the prompt can be read in two ways and just one way passes the verifiers.

### Determining realism
A typical realistic prompt is one solid paragraph, or about 90 words. Very short prompts do happen, but they almost always come with input files for context. Very long prompts also happen, and they are usually a list of real requirements from one person's job — not a made-up test asking for a laundry list of facts and figures in formats better suited for LLMs.

For real examples from the data and other useful stats, refer to the appendix at the end of this doc.

---

## STEP 2 — The verifiers

### 2a. Read only instructions.md. Write your own list of checks.
List everything you would check to decide if the work was done correctly: each thing the user asked for, each format, each output and directory where it must be saved, each filter, count, rule, and special case. Write this list out in full before you continue.

### 2b. Now read manifest.json and compare the two lists.
Think about three groups:
- **Missing** — on your list, but not in manifest.json. Flag if critical.
- **Extra** — in manifest.json, but not on your list. Flag — this is a serious issue.
- **Different** — on both lists, but written very differently. Flag if the verifier doesn't really check what the prompt asked for.

### 2c. Judge the whole set of verifiers.
1. Do they cover everything the prompt asks for?
2. Do they check anything the prompt does not ask for?
3. Will they pass good work and fail bad work? Would correct work written in a different but reasonable way still pass?
4. Will they give the same score every time? They must not depend on today's date, live web results, the order of results, or the exact wording the model happens to use.

---

## STEP 3 — The run

Read the GLM-5.2 score and find its `trajectory.json` which includes all steps the model took and tools it used.

Go through the trajectory step by step. At each step ask: did the model have everything it needed here? List every mistake the model made with the step, what went wrong, and whose fault it is.

- **Model's fault** — a good failure. The model had everything it needed and still made a mistake. This is a real gap in the model's capabilities and a valuable, high-quality task.
- **Poor quality task** — a bad failure. Information was missing, wrong, or ambiguous. A file was empty or broken. A verifier has a mistake or grades something the prompt never asked for.

Then judge:
- Under 50% success, and every mistake is the model's fault — this is what we want.
- Almost always succeeds — the task is too easy.
- Zero, and every mistake is the model's fault — fine, as long as STEP 1 showed the task can be done.
- Zero, with mistakes that are our fault — the task is broken, not hard.
- Two runs disagree a lot — check STEP 2 for nondeterministic verifiers.

---

## Appendix — What real user prompts look like

Data from about 1,800 real user prompts collected over one month.

### A1. How long is a typical prompt?

| Words | Value |
|---|---|
| Shortest quarter (25th percentile) | 56 |
| Typical (median) | 88 |
| Longest quarter (75th percentile) | 151 |
| Top 10% | 235 |
| Top 1% | 482 |

| Length | Share of prompts |
|---|---|
| 1–25 words | 6% |
| 26–50 words | 16% |
| 51–100 words | 36% |
| 101–200 words | 28% |
| 201–400 words | 12% |
| Over 400 words | 2% |

Takeaway: task prompts should not be multiple paragraphs long. Realism in length is a short paragraph of about 100 words.

### A2. What shape is the work?
- 61% of prompts need 20 or more steps to finish. 47% need 40 or more.
- 58% describe work that would take a person a day or more.
- 54% come with files attached. Most common: images (26%), PDFs (15%), documents (10%), spreadsheets (5%).
- 44% ask for more than one type of output.
- 22% name a specific file by its exact filename.
- 26% contain numbered or bulleted sub-requirements.
- 12% mention skills, connectors, spaces, crons, agents, or subagents.
- 9% ask for something recurring or scheduled.
- 4% are not in English.

### A3. Who is asking?
- 81% are workers doing their job. 14% are consumers. 5% unclear.
- 75% are individual paid users; 22% are enterprise users; 3% are free users.

### A4. What are they working on?

| Domain | Share | Most common types of work |
|---|---|---|
| Programming | 21% | web development, software development, code writing, debugging |
| Business | 14% | digital marketing, market research, operations, project management |
| Technology | 12% | software, web development, troubleshooting, AI |
| Writing | 11% | content creation, technical writing, rewriting, academic writing |
| Art | 8% | visual arts (image editing, logos, layout) |
| Finance | 6% | investing, financial analysis, personal finance, accounting |
| Health | 4% | medical research, fitness, healthcare, nutrition |
| Education | 3% | curriculum, academic research |
| Law | 3% | legal advice, regulations, contract law |
| Careers | 3% | resume writing, job searching |

### A5. What do they ask for?
Most common outputs: text (33%), code (30%), documents (23%), websites or web apps (19%), images (16%), markdown (9%), PDFs (7%), data files (6%), spreadsheets (6%), slides (4%).

### A6. Example tasks
Real prompts are specific, messy, and tied to one person's actual job. They are not "write about X". These are rewritten summaries.

- Finance — Build a quarterly financial model with DCF and comparable-company valuations, scenario tables, delivered as an interactive dashboard.
- Programming — Build an interactive prompt-builder dashboard for an interior design team.
- Programming — Fix a broken audit script so it runs without leaving blank rows.
- Business — Build a slide deck for entering a new national market with a partner.
- Business — Work out why a weekly billing report breaks every week, then put a permanent fix in place.
- Writing — Rewrite an internal memo as a plain, direct briefing on a client call.
- Law — Using an attached letter, a witness statement, and a draft internal memo, update the memo with tracked changes.
- Law — From an attached permit PDF and a compliance task CSV, build a site compliance plan plus a two-page checklist.
- Health — Build a fitness app and companion ebook with 41 exercises and form cues.
- Education — Build a personalized math learning platform for grades 3–8 with diagnostic test and individual learning path.
- Art — From an attached decal sheet image, remove the watermark and produce a clean vector SVG.
- Real estate — Build an updated floor plan from an architect's PDF plus reference images.

Takeaway: tasks don't have long scenarios and agents.md/claude.md type files. They deal with messy and sometimes brief context as real workers often do. The tasks don't tell the model how to do the work.

---

## Shannon Task Quality Dimensions

### Purpose and standard
This is the quality standard for a Shannon task. A high-quality task is a fair test of useful work:
1. A capable person or agent can complete it from the task environment.
2. The prompt describes real, nontrivial workplace work in natural language.
3. The verifier measures the work the requester asked for, completely and fairly.
4. A failed model run means the model made a genuine reasoning or execution mistake.
5. The package eventually delivered is the exact package that was reviewed and calibrated.

The North Star has three gates, ordered: a task that fails an earlier gate cannot be called difficult or high quality because of a later score.

**Prompt and environment → Verifier → Run evidence → Release integrity**

### Gate 1: prompt and environment

#### 1. Real work, not a benchmark-shaped puzzle
The task should plausibly be requested by a real person in a real workflow. It needs a believable requester, context, deliverable, and consequence. Good signals include real business artifacts, realistic ambiguity, multiple related actions, and outputs a person would actually use.

Review for:
- **Artifact grounding**: Each source artifact is a real-looking, relevant seed. The prompt does not make claims the artifact contradicts.
- **Schema grounding**: Every named table, column, folder, file, filter value, record, and API entity exists.
- **Persona and workflow plausibility**: The stated role could reasonably receive this request.
- **Temporal and world consistency**: Dates, reporting periods, policy versions agree across prompt, data, gold, and verifier.
- **Operational plausibility**: Deliverable volume is feasible for the requested job.

#### 2. The task is fully grounded and solvable
Read the prompt as the agent. For every named input, tool, connector, skill, policy, or destination, establish:
1. It exists and is reachable in the task environment.
2. It contains the information or capability the prompt says it has.
3. The agent can use it to reach the requested answer without a hidden fact, private convention, or unavailable permission.

#### 3. Clear requirements without over-prescribing the solution
The prompt must make the outcome clear: who the agent is acting for, what it must decide or produce, where to put it, and the material constraints. A human should be able to complete the request with the supplied environment.

Ambiguity is a quality failure when two reasonable interpretations would lead to different outputs and the verifier accepts only one.

The prompt should not leak the answer key or reproduce the verifier as a task recipe.

### Gate 2: verifier quality

#### 4. Complete, two-way coverage of the requester's asks
Make an atomic requirement inventory from the prompt. Map each to the exact verifier object. Then reverse map: for every verifier, state the prompt requirement it serves.

Three discrepancies:
- **Missing**: prompt asks for something nothing verifies → add coverage or remove the ask.
- **Extra**: verifier grades an unstated requirement → remove it or add a justified prompt requirement.
- **Different**: prompt and verifier refer to different values/sources/formats/rules → reconcile.

#### 5. Correct answer keys, calculations, and conventions
For every graded number, choice, date, record, and policy conclusion, trace the chain:
source data → calculation → answer key → verifier value → run-time evaluation

The chain must agree at every link. There must be exactly one defensible convention for each graded figure.

Watch for answer leakage: graded values must not be handed to the agent through the prompt, data labels, examples, hidden notes, or verifier-shaped language.

#### 6. Fairness and construct validity: grade the work, not a proxy
Each check must assess the property it claims to assess, using the right evidence.
- A rubric about a workbook must receive the workbook, not only the model's final prose.
- A numeric check must derive or compare the actual result.
- Semantic graders should evaluate substance, not exact wording or brittle format.

Every verifier in the final delivery set must be a core verifier.

#### 7. Deterministic and empirically trustworthy grading
- Does the reference/golden solution pass every required core verifier for the right reason?
- Is any verifier effectively unpassable across clean attempts?
- Does a deterministic fork produce the expected result?
- Is the judge stable when given the same artifact?
- Does an environment change, current date, or mutable source alter the answer?

A golden pass is evidence, not proof.

### Gate 3: run evidence and attribution

#### 8. Clean-run health
Inspect stored trajectories and run artifacts for:
- token or iteration exhaustion
- output truncation or context-window loss
- malformed tool arguments or serialization failures
- provider outages, rate limits, authentication failures
- missing files, broken permissions, connector errors
- verifier or judge failures recorded as if the model failed
- nondeterministic environments

If more than 20% of runs are infrastructure-tainted, return the task for repair.

#### 9. Correctly attribute each failure
For each failing run, walk the trajectory in order and ask:
- At this step, did the model have all relevant information, a working tool, and an unambiguous path?
- Did it retrieve and use the available evidence correctly?
- Did it make a reasoning, planning, execution, or judgment error?

| Attribution | Meaning | What it says about difficulty |
|---|---|---|
| MODEL | The environment was sound; the model made the consequential error. | Valid difficulty signal. |
| VERIFIER | The grader is wrong, incomplete, brittle, or evaluates the wrong evidence. | No difficulty conclusion; repair the verifier. |
| SPEC/TASK | The prompt, key, input, convention, or task design is missing, wrong, or ambiguous. | No difficulty conclusion; repair or reject the task. |
| TOOL/INFRA | The harness, connector, provider, container, permissions, or context limit failed. | No difficulty conclusion; repair the environment and rerun. |

#### 10. Difficulty is calibrated, not manufactured
Measure difficulty only after prompt, verifier, and run health are sound. The QC-framework calibration target is frontier pass@1 of 30–50% (with 20–60% acceptable).

Interpret the evidence:
- Under 50% success with failures that are all MODEL-attributed is often the desired hard task.
- Near-universal success suggests the task may be too easy or its verifier too weak.
- Zero success can be acceptable only if the task is demonstrably solvable and every failure is MODEL-attributed.
- Any task-attributed failure makes the task broken until repaired.
- Large disagreement across clean runs can indicate nondeterminism.

Never tune difficulty by hiding information, adding ambiguity, making the environment flaky, or narrowing a tolerance to reject defensible answers.

### Release integrity: prove the delivered task is the reviewed task
Before release, establish:
- **Effective package integrity**: task root, Docker-copied tree, effective verifier manifest, and verifier code agree.
- **Reproducibility**: Docker base image pinned by immutable digest, dependencies reproducible.
- **Documentation identity**: README/source task ID matches the run-time task actually packaged.
- **Core verification**: Every final verifier is core; artifact-specific judges receive the artifact; outbound delivery actions have direct coverage.
- **Run evidence**: Readable artifacts show no unresolved verifier or infrastructure errors.
- **Oracle and stability evidence**: Oracle/reference artifact present; four exact binary trials; five fresh-container repeats produce the same answer.

The final-release decision: pass only with no blocking critical/high deterministic finding.

---

## Trainer decision checklist

Do not approve until each applicable item is answered yes with primary evidence.

### Prompt and environment
1. Is this believable work for a real requester, with a useful human-facing outcome and meaningful reasoning or execution?
2. Does every named file, folder, record, table, column, filter, tool, connector, policy, skill, and destination exist and contain what the prompt claims?
3. Can the agent access them with the permissions and tools supplied?
4. Could a capable human finish using only this prompt and environment, without a hidden fact or private convention?
5. Are the role, audience, deliverables, locations, material constraints, dates, and as of state clear?
6. Is the request naturally written rather than a disguised verifier specification? Does it avoid answer leakage and an exact solution recipe?
7. Is any apparent ambiguity harmless, or does it risk rejecting one of two reasonable solutions?

### Verifier and key
1. Have I made an atomic list of every material prompt ask before reading the verifier?
2. Can I point from every ask to an exact core verifier, and from every verifier back to a stated ask?
3. Are there no missing, extra, or different requirements?
4. Does each verifier inspect the correct artifact, value, side effect, or trajectory?
5. Would reasonable equivalent solutions pass, while materially wrong work fails?
6. Do source data, calculation, answer key, gold, verifier value, tolerance, units, dates, and conventions agree?
7. Are graders clear, specific, substantive, deterministic, parseable, isolated from key leakage, and free of silent model fallback?
8. Does the reference solution pass every core check for the right reason?
9. Are all final verifiers core, with direct coverage for each outbound delivery action?

### Runs, calibration, and release
1. Are the runs clean: no cap/exhaustion, truncation, tool/provider/harness failure, broken input, verifier crash, or nondeterministic state?
2. For every failure, have I inspected the trajectory and assigned MODEL, VERIFIER, SPEC/TASK, or TOOL/INFRA based on evidence?
3. Is difficulty measured only from clean, MODEL-attributed runs, with appropriate repeat/model calibration?
4. Does the shipped Docker-effective tree, documentation identity, verifier manifest, and code match the reviewed task, with reproducibility and provenance evidence recorded?

If any answer is no, record the exact evidence and owner. Fix or reject the task before relying on its model score.

---

## How the QC systems support the standard

| System | Primary role | Evidence it contributes |
|---|---|---|
| infra/qc AutoQC | Pre-run decision | RUN, FIX_FIRST, or DROP; structural task checks plus answer-key coherence, leakage, convention determinacy, environment determinism, construct validity, deliverable reachability, and expected difficulty. |
| infra/qc-framework | Detailed static and run QC | Realism, process health, verifier meta-review, difficulty calibration, and evidence-attributed team review. |
| infra/unified-qc | One lossless evidence-first review | Atomic requirement inventory; exact ask-to-verifier mapping; prompt, verifier, run, and reconciliation stages. |
| infra/final-qc | Delivery acceptance | Docker-effective package/mirror checks, core-verifier enforcement, golden-delivery coverage, reproducibility, provenance, oracle, target-model, repeat, and batch evidence. |

### Decision rule
Approve a task only when it is real and solvable, its assessment is complete and fair, its clean runs demonstrate model capability signal rather than task noise, and the release package is demonstrably the package that was reviewed. Quality is a judgment supported by traceable primary evidence—not a process completion or an LLM label.
