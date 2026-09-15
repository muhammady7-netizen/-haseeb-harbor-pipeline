# OBI Task Quality Standard — Company Bench

Audience: everyone working on Company Bench tasks. Runners who iterate on tasks and QC reviewers who audit them work to the same standard, which is this one.

This document defines what a good task is. It does not tell you how to run a task, how to use the tooling, or what to write in the tracker. It tells you what you are aiming at, how to tell whether you have hit it, and what the common ways of missing it are called.

## Contents
1. Why quality is defined this way
2. Background you need
3. The standard in one page
4. Part One: The Ask [PROMPT]
5. Part Two: The Grading
6. Part Three: The Measurement
7. Part Four: Hygiene
8. Defect catalogue
9. Worked examples
10. Using this document
11. Glossary

---

## Why quality is defined this way

Company Bench builds a benchmark for frontier AI labs. Labs buy it to find out where their agents fall short on real enterprise work.

That purpose sets the whole standard. A benchmark task is only worth money if it separates capable models from incapable ones. A task every model passes teaches the buyer nothing. A task no model can pass teaches nothing either, and usually means the task is broken rather than hard.

So "quality" here is not "polished" or "impressive." It is closer to "honest instrument." A good task is one where the number it produces genuinely means what it claims to mean: that a frontier model, given a fair shot at real work, could not reliably do it.

Nearly every defect in this document is a way of producing a number that lies. A task can look excellent and score in band while measuring nothing at all. Those are the ones this standard exists to catch.

---

## Background you need

### What a task is
A task puts an AI agent inside Zeta3, a defunctional fintech. The agent gets a business prompt and a set of tools that reach Zeta3's systems: a SQL warehouse plus connectors for Jira, Confluence, Slack, Google Drive, Freshdesk and Email. Each connector is called a gym.

The agent reads what it needs, works out an answer, and produces deliverables: figures in its reply, a message posted to Slack, a ticket filed in Jira. Then verifiers grade what it produced.

A task ships as a package containing:

| Part | What it is |
|---|---|
| instruction.md | The prompt the model sees. Nothing else reaches it. |
| task.toml | Metadata plus the design doc: the intent, the gold values, the traps, and the SQL that derives the gold |
| tests/manifest.json | Every verifier and its expected values. The grading spec. |
| solution/final_answer.md | The correct answer |
| solution/golden_trajectory.json | A reference path of tool calls that reaches it |
| environment/ | The container definition, including an _app/ mirror of the prompt and verifiers |

### Verifiers
Each verifier grades one aspect of the work.

| Type | What it grades | Deterministic |
|---|---|---|
| json_match | Exact values in the model's reply, with optional numeric tolerance and named wrong answers | Yes |
| database_state | Runs SQL against the gym database. Did the Slack channel get created, did the ticket get filed | Yes |
| tool_execution | Counts tool calls. Presence and minimums | Yes, but only counts |
| response_check | Compares the model's prose against a reference | Judged by a model |
| rubric_check | A model judge scores one atomic claim about the answer or the trace | Judged by a model |

Every verifier is core. There is no informational tier. Everything a task declares, it is graded on.

### How scoring works
One run. The reward is the fraction of verifiers that passed:
```
reward = (weight of passing verifiers) / (weight of all verifiers)
```

Five runs. The task's pass rate is the mean of the five run rewards:
```
0.6, 0.5, 0.7, 0.5, 0.4   ->   pass rate 0.54
```

Two gates decide whether a task is finished:

| Gate | Requirement | What it proves |
|---|---|---|
| Oracle | reward exactly 1.00 | The grading is sound. Every verifier passes on the known-correct answer. |
| Difficulty | pass rate in [0.0, 0.5) across 5 GLM-5.2 runs | The work is genuinely hard for a frontier model. |

One consequence worth understanding: Because reward is a fraction over all verifiers, each verifier is worth `1/N` of the score. The number of verifiers, and what each of them actually discriminates, now directly determines what a pass rate means. A task with twelve verifiers where four always pass has an effective floor of 0.33, not 0.0.

---

## The standard in one page

A good task satisfies all four parts.

- **Part One: The Ask.** The task demands real work with one right answer, gives away nothing, and leaves nothing to guesswork.
- **Part Two: The Grading.** The verifiers check the thing the task is about, cover what the prompt demands, accept every correct route, and actually discriminate.
- **Part Three: The Measurement.** Oracle is clean, the pass rate is in band, and the number behind it is stable and honestly earned.
- **Part Four: Hygiene.** The package is assembled correctly and the reported number came from the package that shipped.

Parts One, Two and Four are checkable without running anything. Part Three needs runs. That is the natural order to work in.

---

## Part One: The Ask [PROMPT]

Six standards on what the task demands of the model. All checkable by reading.

### A1. A real person at this company would actually ask this
The prompt must sit inside the range of things a working analyst would be asked. It should have a discernible reason behind it, consistent detail, and the voice of someone with a job to do.

A convoluted operation on an obscure table, invented purely to be difficult, fails this even if it produces a perfect pass rate. So does a prompt that reads as generated: uniform sentence rhythm, throat-clearing, an unnaturally tidy structure no busy person would write.

How to check: read the prompt and ask whether you can picture the person who sent it and why they needed it today.

### A2. There is one defensible right answer
Given what the prompt states and what the tools return, a careful analyst should reach one answer. Not a range of acceptable outputs.

This is different from a task having traps. Traps are wrong answers that look plausible. Those are good. What fails A2 is when two answers are both genuinely correct.

### A3. The prompt gives away nothing the model should have to find
If the task is to discover how many accounts were affected and the prompt says "the five affected accounts," the task has been converted from an investigation into a lookup.

Leakage takes three forms:
1. **Stated answers.** A count, a total, a cohort size, or a named entity that the model was supposed to identify.
2. **Field names.** If the model must return a JSON field called `duplicate_bradley_removed`, it now knows there is a duplicate, that it involves Bradley, and that removal is the expected action. The field list is a hint sheet.
3. **Method spelled out.** A prompt that lays out the exact query logic step by step leaves no reasoning to perform. The model is transcribing, not analysing.

How to check: read the prompt and every required output field name, and ask what each one tells the model that it would otherwise have had to work out.

### A4. Every decision the model must make is decided by the prompt
This is the most commonly failed standard and the most expensive one to miss.

If the model must choose between two defensible readings, and the verifier accepts only one, then some runs pass and some fail based on a coin flip. The task looks appropriately difficult and is measuring nothing.

The forks that cause this in practice:
- **Boundaries.** Does "before settlement" include the settlement date itself?
- **NULL handling.** Does a comparison exclude NULL rows or treat them as non-matching?
- **Column choice.** When two timestamps could both mean "when it happened," which one counts?
- **Scope matching.** Does a status match by prefix, exactly, or as a substring?
- **Deliverable form.** Does "file a ticket" mean a new ticket or a comment on an existing one? In which project?
- **Inclusion rules.** Do canceled records count? Partial cases? Test accounts?

How to check: read instruction.md and nothing else. No design doc, no gold answer, no notes. Write down every point where you had to guess. Then compare against the gold. Every guess you had to make is a place a model will guess too, and half of them will guess differently.

Be honest with yourself here. "Well, obviously they meant X" means you guessed.

### A5. The deliverable is worth producing
Would a client look at this output and consider it worth what they are paying? A realistic ask with a trivial answer, a question whose result has no downstream consequence, or a one-line lookup dressed up in extra steps all fail.

### A6. Everything the task references actually exists
Every table, column, Confluence page, Jira ticket, Slack channel and policy the prompt or verifiers name must be real and reachable with the tools provided.

How to check: for anything named, confirm it resolves. If runs show 404s, "table not found", or a model correctly pivoting to a real table and being marked wrong for it, this standard has failed.

---

## Part Two: The Grading

Seven standards on the verifiers. All checkable by reading.

### G1. The primary goal is verified
State in one sentence the single thing this task mainly exists to measure. Then find the verifier that checks it. If the main thing is not verified, the task is broken regardless of how many other checks it has. This is the most consequential single check in this document. Do it first and state the result plainly.

### G2. Every stated requirement is checked
Break the prompt into discrete, independently checkable requirements: each artifact, each computed figure, each naming constraint, each ordering or formatting rule, each explicit prohibition. Map every one to a verifier. An unchecked requirement is decoration.

### G3. Nothing unstated is required
The inverse of G2. A verifier demanding something the prompt never asked for will fail good-faith models for no reason and drag the pass rate down dishonestly.

### G4. Verifiers grade the work, not the model's account of it
If a model reports a figure and a verifier checks that reported figure, the verifier is measuring the model's self-description. The model can report the right number while the underlying deliverable is wrong.

Wherever the value can be recomputed from what the model actually produced, check it there. Grading the artifact strictly beats grading the report of the artifact.

### G5. Verifiers accept every correct route, and only correct ones
Check both directions:

**Too strict.** A verifier that accepts only the exact approach the reference answer took will fail a model that reached the same correct outcome differently. The question: does this require how the model got there, or only that it got to the right place?

Related traps:
- A tool-name requirement naming one tool when another on the same connector reads the same data.
- A literal text match on one phrasing when a synonym means the same thing.
- A named wrong answer that sits inside the verifier's own numeric tolerance.

**Too loose.** A verifier that only checks presence or shape passes on self-evidently wrong content. `tool_execution` verifiers are the standing example: they count calls. They do not check what was in the call or whether it succeeded.

### G6. The verifier set discriminates
Each verifier is worth 1/N of the score. So the composition of the set determines what the pass rate can even mean.

A verifier that passes on every run contributes nothing except a higher floor. If four of twelve verifiers pass whenever the agent calls the right tools, the task cannot score below 0.33 no matter how completely it fails the actual work.

Two failure modes:
- **Free points.** Verifiers that always pass. They inflate the number and measure nothing.
- **Denominator gaming.** Adding easy verifiers raises the pass rate and removing hard ones raises it too, without the difficulty changing at all.

How to check: for each verifier, ask what a failing attempt looks like. If you cannot describe a plausible attempt that fails it, it is a free point.

### G7. Judgment-based checks are used only where judgment is unavoidable
`rubric_check` and `response_check` are graded by a model judge, and the judge is GLM-5.2, the same model that attempts the tasks. Two things follow:
- Variance lands in the score. A judge that decides differently between runs moves the pass rate directly.
- A model tends to favour its own conventions.

So: wherever a check can be a `json_match` or a `database_state`, make it one. Reserve judged checks for genuinely qualitative criteria.

When you do write one, write it as an unconditional statement. Never phrase a rubric as "avoid X (means Y)" or "do not do A instead of B." Write "PASS only if the answer does X. FAIL otherwise."

Also give the judge only the artifact it is grading. A judge shown both the ground truth and the model's answer and asked to compare will score the same output differently depending on which one it happens to focus on.

---

## Part Three: The Measurement

Six standards that need runs. This is where a task proves the number it claims.

### M1. Oracle scores 1.00, reproducibly
Because reward is a fraction over all verifiers, Oracle at 1.00 means every single verifier passed on the known-correct answer. Anything below 1.00 means at least one verifier rejects the right answer, which means the grading is wrong. There is no partial credit on this gate.

When Oracle fails, the failing verifier's recorded reasoning usually names the defect outright. Read it before theorising.

Then decide which side is actually wrong:
- The verifier demands something correct and the reference answer or trajectory does not do it → Fix the reference.
- The reference is right and the verifier demands something ungrounded or too narrow → Fix the verifier.

Reproducibly matters because judged verifiers vary. If two Oracle runs on the same package score differently, that verifier is unsound.

### M2. The mean sits in band
Pass rate must be in [0.0, 0.5).
- 0.48 is in band.
- 0.50 is not. The bar is below half, not at it.
- 0.7 is out of band and needs the same scrutiny as a broken task, from the other direction.
- 0.0 is acceptable, but only if the task is provably solvable. Establish that with a diagnostic GPT-5.5 run before accepting it.

### M3. The spread is tight
Write out all five run rewards. Do not report the mean alone.
```
0.5, 0.5, 0.6, 0.4, 0.5  mean 0.50  tight. Calibrated difficulty.
0.9, 0.1, 0.9, 0.1, 0.5  mean 0.50  bimodal. A coin flip.
```
Identical means. Completely different tasks.

A bimodal spread is a quality defect. It nearly always means the prompt permits two readings and the model picks one at random, which is a failure of A4 showing up in the numbers.

### M4. Failures happen for the right reason
Every failing run should fail because the model could not do the work. Read them and sort each one:
- **Genuine model limitation.** It had everything it needed and still got it wrong. This is the signal the task exists to produce. Leave it alone.
- **Ambiguity.** It made a defensible choice the verifier rejected. This is an A4 failure and the run is not evidence of difficulty.
- **Grading failure.** The verifier itself could not evaluate. Exclude these runs from the reading and say so.

A reward of exactly 0.0 deserves particular suspicion. In practice, weak-but-real tasks cluster between 0.15 and 0.35.

### M5. The verifier profile is stable across independent runs
Run the same task twice, five runs each. Compare not just the two means but which verifiers passed.

If the first set passes verifiers 1 through 5 and the second passes 7 through 10, the means will look nearly identical and the task is measuring nothing stable.

| Drift is in | What it means |
|---|---|
| Deterministic verifiers (json_match, database_state) | Real task ambiguity. The prompt permits different routes. An A4 failure. |
| Judged verifiers only, deterministic ones stable | The judge is unstable, not the task. A G7 problem. |
| Both | Treat as task ambiguity. A deterministic verifier cannot wobble because of the judge. |

### M6. The score is not inflated by free points
Look at how many verifiers passed on every single run, and what fraction of the total score they represent. That fraction is the task's effective floor.

A task whose floor is 0.33 has a real range of 0.33 to 1.0. Its 0.48 corresponds to roughly 0.22 on a task with no free points.

This is G6 measured rather than read. If the floor is high, the fix is in the verifier set, not in the prompt.

---

## Part Four: Hygiene

Four binary checks. No judgment required, and each one silently invalidates everything else if it fails.

### H1. The prompt and verifiers are in sync with their mirror
instruction.md and tests/manifest.json exist twice in the package: once at the root and once under environment/_app/. The _app/ copy is what actually gets built into the container the model runs in.

If someone edits the root copy and forgets the mirror, the change never took effect and every number produced since measures the old task.

### H2. The answer key does not ship to the model
Nothing from solution/ belongs under environment/_app/. If the gold answer or the reference trajectory is reachable by the agent, every score is void.

### H3. The package can grade itself
The grading engine files under tests/ travel with the package rather than living in the repository. A package missing them cannot produce a score at all, and a grading run that fails to complete can record a reward of 0 that looks like a model failure.

### H4. The reported number came from the submitted package
Each run records a checksum of the artifact it graded. If the number in the tracker came from a different version than the package that shipped, it is not a measurement of anything that exists.

---

## Defect catalogue

Use these names. "Verifier seems too strict" is not actionable. "Narrow-to-golden on trace_hold_release_method" is, and it aggregates across tasks so systemic problems become visible.

### The ask

| Name | Standard | What it is |
|---|---|---|
| Unrealistic ask | A1 | Nobody would request this |
| AI-voiced prompt | A1 | Reads as generated, not written by a person with a reason |
| No single answer | A2 | Genuinely open-ended output |
| Answer leakage | A3 | The prompt states a count, total, or entity the model should find |
| Field-name leakage | A3 | A required output field names the thing to be discovered |
| Method spelled out | A3 | The prompt is a recipe, not a brief |
| Ambiguity fork | A4 | Two defensible readings, one accepted |
| Under-specification | A4 | "Done" is not defined |
| No client value | A5 | Realistic but trivial, no downstream consequence |
| Phantom entity | A6 | Names a table, page or ticket that does not exist |

### The grading

| Name | Standard | What it is |
|---|---|---|
| Uncovered primary goal | G1 | The main thing the task measures has no verifier. Blocking. |
| Uncovered ask | G2 | A stated requirement nothing checks |
| Unasked requirement | G3 | A verifier checks something never requested |
| Grades the account | G4 | Checks the model's self-reported figure instead of the artifact |
| Excessive self-report | G4 | A long required-JSON block of metrics about the model's own work |
| Narrow-to-golden | G5 | Requires one method when an equivalent reaches the same outcome |
| Single-tool trap | G5 | Names one tool when another reads the same data |
| Synonym gap | G5 | Literal match rejects an equally correct phrasing |
| Decoy inside tolerance | G5 | A named wrong answer falls within the verifier's own tolerance |
| Count-only floor | G5 | Passes on tool calls that errored or carried the wrong content |
| Free point | G6 | Always passes. Raises the floor, measures nothing. |
| Denominator gaming | G6 | Landed in band by changing the verifier count, not the difficulty |
| Avoidable judge | G7 | A judged check where a deterministic one would work |
| Invertible rubric | G7 | Phrased "avoid X (means Y)", which a judge reads backwards |
| Judge contamination | G7 | The judge sees the ground truth alongside the answer it is grading |

### The measurement

| Name | Standard | What it is |
|---|---|---|
| Non-reproducible Oracle | M1 | Two Oracle runs on the same package score differently |
| Reference defect | M1 | The gold answer or trajectory is wrong, not the verifier |
| Out of band, high | M2 | Too easy. Something is loose or the prompt answers itself. |
| Unproven zero | M2 | 0.0 with no evidence the task is solvable |
| Bimodal spread | M3 | A coin flip wearing a mean |
| Grading failure counted | M4 | A run where the verifier crashed treated as model evidence |
| Profile drift | M5 | Same mean, different verifiers passing |
| Inflated floor | M6 | Free points compress the task's usable range |

### Hygiene

| Name | Standard | What it is |
|---|---|---|
| Mirror out of sync | H1 | The fix never reached the container |
| Leaked answer key | H2 | solution/ content reachable by the model |
| Missing engine | H3 | The package cannot grade itself |
| Stale number | H4 | The reported rate came from a different version |

---

## Worked examples

All three come from a real task: an ACH audit that asks the agent to read a Confluence build plan, find deposits whose account holds were released before their scheduled settlement date, compute four figures, post a pinned Slack summary, and file a Jira ticket. It has twelve verifiers, so each is worth 1/12 = 0.0833.

### Example 1: an Oracle failure that names its own fix
Oracle scored 0.9167. Eleven of twelve verifiers passed. The failure was a judged check on the trace, asking whether the model used all three connectors and avoided the documented traps. The judge's recorded reasoning: "The model computed with SQL and posted to Slack/Jira while avoiding the listed numeric traps, but it only searched Confluence and did not actually read the build plan content."

Work out which side is wrong. The prompt does say "Start with that page to confirm the policy." The verifier is asking for something the task genuinely requires. The gold figures are correct.

So the reference trajectory is at fault, not the verifier. It searched Confluence and never opened the page. The fix belongs in `solution/golden_trajectory.json`, and nothing in the verifiers should be touched.

The instinct to reach for the verifier when Oracle fails is strong and usually wrong. A verifier that fails on the reference answer is only the problem when what it demands is not something the task actually requires.

### Example 2: why 0.5 can mean total failure
A model run on this task scored 0.5, six of twelve. Middling, apparently respectable. Here is what passed:

| Verifier | Type | Result |
|---|---|---|
| Early release count | judged | FAIL |
| Dollar exposure | judged | FAIL |
| Timing and service split | judged | FAIL |
| Slack message content | judged | FAIL |
| Hold release method (trace) | judged | FAIL |
| All connectors and traps (trace) | judged | FAIL |
| Slack channel exists | database_state | PASS |
| Jira ticket filed | database_state | PASS |
| Read source Confluence | tool_execution | PASS |
| SQL investigation | tool_execution | PASS |
| Write back | tool_execution | PASS |
| All connectors called | tool_execution | PASS |

The model got every single number wrong. It scored 0.5 anyway.

The 0.5 came from four `tool_execution` floors that count calls, plus two state checks confirming a channel and a ticket exist. The model created the artifacts and filled them with wrong answers.

One third of this task's total score comes from process floors that pass whenever the agent calls the right tools, regardless of what it produced. The task's effective range is 0.33 to 1.0, not 0.0 to 1.0. That is a G6 failure and an M6 finding, and it means a 0.48 here is not comparable to a 0.48 on a task where every verifier discriminates.

The mean said "middling." The composition said "complete failure of the actual task."

### Example 3: two tasks at 0.48, opposite verdicts
Same number, different truth behind it.

**Task one.** A verifier requires the literal token "same-day" and would reject "sameday". That is a synonym gap under G5, and it is a real defect.

Check the runs: that verifier passed in all five. Every model happened to use the hyphen. The failures were all in the answer checks.

The defect is real but not load-bearing. Fixing the wording cannot move the score because nothing was ever failing on it. The 0.48 stands.

**Task two.** The prompt says "go through our completed ACH-debit deposits" without stating whether canceled transfers count. The design doc lists 501 as the wrong answer you get when you include them.

Check the runs: three of five answered 501. Two matched gold. The spread is bimodal.

That 0.48 is a coin flip on an A4 ambiguity, not a measurement of difficulty. Pinning the definition in the prompt will push the rate up, probably out of band, and the task will then need hardening it never received.

The distinction that matters: in task one the defect could not have changed the number. In task two the defect is the number. Same score, and only looking at which verifiers moved tells you which situation you are in.

---

## Using this document

The standard is the same for everyone. How you use it differs.

### If you iterate on tasks
Work Parts One, Two and Four before you run anything. They are free and they catch most of what would otherwise come back to you.

The highest-value thing you can do, and the hardest, is A4 on your own task. By your third iteration you cannot read your own prompt fresh any more. You know what it means, so it reads as unambiguous. Two ways to compensate: write down the guesses before you start editing, while the prompt is still new to you, or get someone else to do the cold read.

Part Three is what your runs are for. Do not stop at the mean. A tight in-band spread with varied failure reasons is a finished task. A bimodal in-band spread is an unfinished one wearing a good number.

Before you submit, ask the question this document exists to answer: if this number turns out to be wrong, which standard did I skip?

### If you review tasks
You are auditing a claim: this task is good, and it scores X. Both halves need checking, and the second is the one that only you can do.

Read the prompt cold, before the design doc, before the gold, before the notes. Your ability to do that is the main thing you have that the person who built the task no longer does. It is lost permanently the moment you read the answer.

Then re-measure. M5 is your sharpest tool: if your runs and theirs produce the same mean from a different set of passing verifiers, the number is not a measurement no matter how in-band it looks.

When you find a defect, the question that decides what happens next is: would fixing this change the number? If it cannot, fix it and keep the score. If it can, the score has to be earned again.

---

## Glossary

| Term | Definition |
|---|---|
| Company Bench | the benchmark project. |
| Zeta3 | the simulated fintech the tasks are set in. |
| Gym / connector | one system the agent can reach with tools. Zeta3 SQL, Jira, Confluence, Slack, Drive, Freshdesk, Email. |
| Package | one task's full folder. Prompt, verifiers, reference answer, environment. |
| Prompt | instruction.md. The only thing the model sees. |
| Design doc | the long description inside task.toml, carrying the intent, the gold values, the traps, and the SQL that derives them. |
| Verifier | one rule grading one aspect of the work. |
| Gold / reference answer | the correct answer, in solution/final_answer.md. |
| Reference trajectory | the tool-call path that reaches the gold, in solution/golden_trajectory.json. |
| Oracle | a run of the reference answer through the graders, with no model attempting the task. Must score exactly 1.00. |
| Reward | one run's score. The fraction of verifiers that passed. |
| Pass rate | the task's number. The mean reward across five GLM-5.2 runs. Must be in [0.0, 0.5). |
| Trap | a wrong-but-plausible answer the task deliberately makes reachable. Documented in the design doc. |
| Free point | a verifier that passes on every run. Raises the score's floor without measuring anything. |
| Effective floor | the fraction of the score contributed by verifiers that always pass. A task's real range starts here, not at zero. |
| Spread | the five individual run rewards, as opposed to their mean. |
| Profile | which verifiers passed, as opposed to how many. |
| Ambiguity fork | a point where the prompt permits two defensible readings and the grading accepts one. |
