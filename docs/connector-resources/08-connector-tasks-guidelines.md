# CompanyBench/Connector Tasks Guidelines

**Source:** docs.google.com/document/d/1jdmYao4I8HQ… (Company Bench/Connector Tasks Guideline)
**Status:** COMPLETE — all 6 parts read in full

---

## CURRENT — If you read one page, read this one

Four things decide whether a task holds up:
1. The known answer grades cleanly
2. A model can solve it
3. Most attempts don't
4. Nothing about it is unfair

The two that catch people out are the third and the fourth — a task can look hard for reasons that have nothing to do with the model, and a verifier can look thorough while rejecting work that is right.

---

## PART 1 — The Work

### 1.1 What these tasks are
We build benchmark tasks. Each one is a self-contained piece of work that a frontier model attempts inside a container, and a grader (the verifier) scores automatically. The client is buying tasks that are hard, fair, and honestly measured.

Most tasks arrive already built and already too easy — mined from real data. Turning that into something that measures a real capability gap is the job.

### 1.2 Connector tasks vs CompanyBench tasks
- **Connector task:** lives inside one application (mailbox, drive, chat). One connector, one focused question.
- **CompanyBench task:** wires several applications together. Crosses apps, requires reconciliation.
- Same machinery: same container, proxy, verifier engine, evidence. Rules apply to both.

### 1.3 What makes this worth doing well
- The environment is live, and mostly not yours — difficulty must come from requiring correct handling of what is already there
- There is a way around the connector (the database underneath) — closing it is YOUR job, and until it's closed, nothing you measure means anything

### 1.4 What a good task looks like
- **Functional:** runs, connectors answer, nothing contradicts
- **Realistic:** reads like work somebody would actually ask
- **Genuinely challenging:** model fails sometimes, always for a reason you can point at
- **Fairly graded:** every correct answer passes, every wrong answer fails
- **Honestly evidenced:** runs match the numbers, write-up matches disk

**Do not build for the checker.** Optimizing for passing makes the task not good and gets caught downstream.

---

## PART 2 — The Twelve Stages

### Stage 1: Claim and Set Up
- Claim tasks in the tracker dashboard only
- Get a local setup (worth an afternoon): oracle loop, connector tool calls, trajectory watching
- Before moving on: task shows against your name, you know the shape, you can run oracle locally

### Stage 2: Learn the Package
Read in this order: task.toml → tests/manifest.json → tests/rubric.toml → solution/ → environment/ → evaluations/ → instruction.md (LAST, for cold read)

**The mirror:** instruction.md, task.toml, and tests/manifest.json exist twice (root + environment/_app/). The _app/ copy ships into the container. Edit only root → change never happened.
```bash
bash environment/sync_app_mirror.sh
diff -r tests environment/_app/tests   # must be clean
```

**What you may change:** tests/manifest.json, tests/rubric.toml, solution/, README.md, review record, task.toml (specific fixes), environment (specific fixes), instruction.md (only to disclose something material)
**Never by hand:** environment/_app/** (regenerate), evaluations/** (leave alone)

### Stage 3: Read the Prompt Cold
Read instruction.md alone — not the solution, not the manifest. Write down every guess you have to make. Then open the golden answer and compare.

**Every guess is an ambiguity, and ambiguity is never difficulty.** Each guess must become either a sentence in the prompt that closes it, or a separately graded question.

Four more checks: Does everything referenced exist? Does it leak the answer? Is it a recipe? Does it sound like a person?

### Stage 4: Trace the Asks to the Checks
**Forward pass:** every instruction requirement → verifier that grades it. Orphans = coverage gaps.
**Backward pass:** every verifier → instruction sentence that creates the requirement. If you can't quote it, delete the check or add the requirement to the prompt.

Name the primary goal — confirm a verifier checks it. A primary goal nobody grades is blocking.

### Stage 5: Close the Connector Surface
Do this BEFORE measuring anything. A task that looks easy because the model can answer with one query is not easy — it is open.

**Three doors, three different answers:**
1. **State route** (used by verifier): gate on root-only key, fail closed
2. **Step route** (used by oracle): gate on same allowlist as connector layer
3. **Files on disk** (gym SQLite, /opt/proxy/server.py, seed SQL): lock them down — this door makes the other two irrelevant

**Prove it from inside the sandbox:** ask proxy for raw state, ask app's port, list seeded DB files. All three must refuse.

**Grade the interface:** make it a core check with sanctioned tools named, disclosed in instruction. Never a bare call count. Never mandate a query shape.

### Stage 6: Run PreQC, and Fix What It Finds
- Required, free, cached per version
- Run it BEFORE spending evaluation runs
- Treat findings as triage — some are wrong
- A dismissed finding needs a written reason with evidence
- A fixed finding needs verification that the problem stopped reproducing

### Stage 7: Prove the Oracle
- Oracle replays known-correct solution, no model, runs verifiers
- Must be exactly 1.0 — no partial credit, no near miss
- When it falls short: golden wrong → fix golden; verifier wrong → fix verifier; can't tell → task.toml design notes settle it
- Re-run after EVERY change to gold, verifiers, instruction, or environment

### Stage 8: Measure It
Two separate questions:
- **Solvability:** one run at full reward from any non-oracle model (NOT an oracle run — most common reason packages come back)
- **Difficulty:** four independent rollouts. A pass is full reward only. Report all four, never the average.

**Band:** 1-3/4 accepted. 4/4 rejected as too easy. Aim for 1-2. 0/4 submittable but needs extra solvability proof.

**Exclude crashed attempts** — a result of exactly zero is usually plumbing, not difficulty. Read the trace.

### Stage 9: Read the Runs
For each attempt below full reward: open trajectory, walk to where it went wrong, give it exactly one label.

**Three shapes that invalidate a fine-looking band:**
1. **Coin flip:** full, nothing, full, nothing = ambiguity
2. **Drift:** same average with different checks passing = noise
3. **One reason four times:** all failing on same clause = prompt/verifier signature

**Attribution:** model failure, verifier defect, ambiguity, infrastructure, judge misread, judge never saw evidence, rubric contradiction, judge penalizes allowed route.

### Stage 10: Harden Honestly
**The lever that works:** Add one new RELATION over something that must already be correct. Not more scale, not more enumeration, not more formatting rules.

**Write the prediction down BEFORE the change.** Say what you expect the band to become, then make the change, then compare.

**What voids the measurement:** instruction wording resolving ambiguity, expected answers, inputs, or set of checks → re-run battery. Grader robustness, packaging, loosening unfair check → no re-run needed.

### Stage 11: Break It Yourself
Twenty minutes. Two suites:

**Must still pass** (perturb golden preserving meaning): shuffle row order, add trailing newline, write numbers as strings, reorder columns, prepend BOM, paraphrase prose, reorder keys, reformat integers, delete unrequired file, quote fields, add trailing zeros, add scratch file, convert line endings, pad fields.

**Must now fail** (break golden for real): flip boundary row, empty deliverables, flip one classification, delete one deliverable, delete one data row, append spurious row, change summary count, replace output with empty object.

**Parity test:** correct paraphrase ≥ gold score; keyword soup < gold score.

### Stage 12: Record It and Submit
Package structure:
```
task/
├── task.toml, instruction.md, review.csv, qc_report.html, README.md
├── tests/ (manifest.json, rubric.toml, engine)
├── environment/ (container, entrypoint, connectors, _app mirror)
├── solution/ (golden trajectory + how produced)
└── evaluations/
    ├── solvability/r1/ (one full-reward non-oracle run)
    └── difficulty/r1..r4/ (four independent rollouts)
```

**The one pass that prevents most rework:** Re-derive every number in your write-up and review record from disk. Fix anything that disagrees.

qc_report.html comes last: run gate → download report → put at task root → re-zip → upload as new version → run gate again → submit that one.

---

## PART 3 — Craft

### 3.1 Writing the Prompt
- Reads like a colleague sent it: one paragraph context, the asks, exact deliverable
- 90-150 words for simple task; longer only for more forks to pin
- **Must have:** reason, deliverable exactly, every fork pinned, decoys named, any workflow you grade
- **Must not:** stated answer, field name giving away mechanism, spelled-out method, deleted standing info, clause-stacked phrasing

### 3.2 Building the Verifiers
**The rule:** A verifier grades the task, not your solution. An assertion is legitimate only if every output that satisfies the instruction passes it.

**Three questions every check must answer:**
A. What requirement is this checking? (point at the sentence)
B. Why is this check sufficient?
C. Why is it permissive enough? (why a valid alternative wouldn't be rejected)

**17 ways a check passes golden but fails a correct model:** number format, float equality, rounding rule, date format, enum case, boolean representation, currency decoration, row order, column order, key order, encoding, quoting, whitespace, prose keyword, tie-break, boundary, extra files.

**Checks in name only:** Free points (passes every run), dead weight buckets (no checks behind weight), count-only floors (satisfied by failed calls), disproportion (file-parses = headline weight), hollow checks (grading model's self-report).

### 3.3 Making it Genuinely Challenging
**Axiom:** Difficulty is work. It is never ambiguity. Every fork pinned or promoted. Never banked.

**Good difficulty:** finding evidence, applying disclosed rule, one determinate answer, realistic reasoning shortcut, meaningful cross-reference, categorical failure, survives full disclosure.

**Bad difficulty:** searching endlessly, guessing undisclosed rules, several defensible answers, trick wording, unnecessary volume, tiny tolerance, disappears once rules disclosed.

**Three properties of a sound discriminator:** Chained (sits on already-correct roster), Sharp (wrong reading produces specific wrong answer), Provable (oracle grades cleanly).

**10 honest levers in order:** 1) Remove leakage, 2) Remove recipe, 3) Add second deliverable, 4) Require reconciliation, 5) Handle existing decoys, 6) Grade artefact not self-report, 7) Replace count floors with state checks, 8) Convert judged to deterministic, 9) Increase precision, 10) Widen scope.

### 3.4 Evidence You Can Defend
- Freeze the folder while runs execute (output outside task folder)
- Keep infrastructure out of every denominator (each cause named individually)
- Voice that survives review: measure don't argue, record wrong intermediate fix, name what you didn't do, declare honest limit, write sentences that don't need numbers that move

---

## PART 4 — Reading the Runs

### 4.1 Deciding Whose Fault It Was
Every attempt below full reward gets exactly one label. Do it from the trajectory, not the mismatch shape.

- Step wrong + wrong value → **Model** (the signal)
- Step right + value right + still failed → **Your check or prompt**
- Reading you would defend → **Ambiguity** (pin definition, re-earn band)
- Grader error/crash/truncated judge/zero → **Infrastructure** (drop, replace)
- Judge quotes words model never wrote → **Judge misread** (grading defect, never model failure)
- Judge says model didn't do something trace shows → **Judge never saw evidence**
- Two judged items disagree about same fact → **Rubric contradiction**
- Judge penalizes allowed route → **Fix rubric**

### 4.2 The Failures Worth Designing For
- Enumeration/completeness gaps (paginated listings, hidden surfaces)
- Decoy acceptance/rule inversion (superficial matches)
- Interpretation of under-specified key (two defensible readings)
- Transcription/counting errors (internal consistency)
- Wrong tool/target (right content wrong place)
- Leaving summary out of reply (only if instruction asks for it)
- Applying neighbouring rule (net vs gross)
- Under-citing sources
- Stopping short of stated self-check

### 4.3 Patterns in Connector Work
- **Resemblance judgement collapse:** model classifies by surface form, gets category backwards
- **Minority-reading gold:** gold took minority reading, nothing reaches full reward — re-gold to majority
- **Question-mapping error:** superset written in subset's field
- **Over-narrow format filter:** native types only, misses cross-format
- **Count propagation:** one wrong base, all derived counts inherit error
- **Containment-axis scope error:** opposite-direction failures (subset vs superset)

### 4.4 What Accepted Work Has in Common
- Ambiguity converted, not banked
- Grading as deterministic as deliverable allows
- Identity and structure graded; vocabulary never
- Every check carries independent signal
- Structure disclosed first, then graded
- Surface closed in environment at every layer
- Each check tested against counterexample, not gold
- Evidence with frozen folder, infra excluded, numbers re-derived

### 4.5 Learning from an Accepted Task
Ground truth first, synthesis second. Five fields: name, when it shows up, how to spot it, how strong, one example. Rate as strong or weak, not "medium".

---

## PART 5 — What Goes Wrong

### 5.1 Where Reviews Actually Fail
~14 areas, ~3 dozen checks. Majority fail at least one, median ~11 failures.

| What | Tasks hit | Issue |
|---|---|---|
| Representation/tolerance | ~80% | Check rejects correct answer over format |
| Traceability | ~79% | Check grades something instruction never asked |
| Judge plumbing | ~78% | Judge misconfigured/unstable |
| Scoring arithmetic | ~71% | Declared weights ≠ actual arithmetic |
| Package coherence | ~59% | Mirror drift, stale references |
| Exploitability | ~34% | Way around connector |
| Domain/realism | ~19% | Contrived scenarios |

The two that fail most (representation + traceability) are the same defect — and the backward pass prevents both.

### 5.2 The Recurring Connector Defects
| Defect | Rate | Action |
|---|---|---|
| Connector returns less than it should | 1/2 | Run golden's query through MCP tool, compare |
| Way around connector | 4/10 | Three probes, close all doors |
| Too easy | 4/10 | Close shortcut first, then re-measure |
| Environment never comes up | 3/10 | Ineligible, replace, never count |
| Judge over empty rubric | 1/4 | Remove judge config or add rubric items |
| Unfair checks as model failures | 1/4 | Ineligible, not data points |
| Undisclosed workflow requirement | 1/7 | State in instruction or delete check |
| Weight against nothing | 1/9 | Every category needs a check |
| Same fact checked twice | 1/14 | Remove duplicates |
| Oracle failing on correct golden | 1/14 | Fix check, not golden |

### 5.3 When Write-Up Stops Matching Evidence
The largest single group of issues. Sent back tasks that were sound underneath.

**Fix:** Re-derive every number from evidence folder and manifest before finalising. Delete stale claims rather than updating them. Your own prose is graded — never ship to-dos or notes.

### 5.4 Reward Hacking
**10 ways a model passes without doing the work:** hard-code answer, read golden data, write to checked state, fabricate placeholder, emit magic string, satisfy rubric skipping side effect, exploit existing state, exploit path mismatch, inject judge instructions, claim without retrieving.

**Ways we do it to ourselves:** loosening rubrics, changing expected values to match model, adding always-pass checks, emptying required tools list, changing check count to land in band.

### 5.5 If You See This, Do This
- Exact zero → crash, not difficulty → look for exception, exclude, re-run
- Full/nothing/full/nothing → coin flip on ambiguity → fix prompt
- Everything passing → too easy → harden
- 1-2/4 passing → in band, best place → stop, write it up
- 3/4 passing → weakest position → ship if no honest lever left
- Nothing passing → submittable, lands less → prove solvability, check dispersed failures
- Steady partial, no full passes → genuinely hard → this is what good looks like
- Most runs broken by environment → battery is noise → fix environment first
- Identical results after edit → mirror never synced → run sync script
- Every run failing same format check → overfit → fix the check
- All runs agreeing with each other, not with gold → gold probably wrong → re-derive

---

## PART 6 — Reference

### 6.1 The Master Checklist (20 items)

**The task:**
- [ ] Prompt reads like a person, names decoys
- [ ] Every fork pinned or promoted, nothing ambiguous as difficulty
- [ ] Method never handed over
- [ ] Nothing leaks answer/count/field name/method

**The grading:**
- [ ] Every check traces to quotable sentence (forward + backward)
- [ ] Every check core, no duplicates, no free points
- [ ] Every declared weight category has matching check or honestly dormant
- [ ] Identity/structure graded, vocabulary not
- [ ] Headline question outweighs formality checks
- [ ] Prose structure disclosed in prompt, then graded

**The environment:**
- [ ] All three probes refused
- [ ] Declared surface = measured surface
- [ ] Mirror synced, diff clean
- [ ] Nothing from solution/ under environment mirror

**The evidence:**
- [ ] Oracle grades cleanly, every check executing, re-run after last change
- [ ] Band 1-3/4 (ideally 1-2), failures in different attributed modes
- [ ] Infrastructure failures excluded, each with named cause
- [ ] All evidence carries one fingerprint, generated outside frozen folder

**The package:**
- [ ] Every number re-derives from disk
- [ ] Review record, delivery report, change summary at task root inside zip

### 6.2 The Review Record
14 areas (12 yours, 2 run for you). 5 columns: review_check, status, review_notes, change_made, what_to_record. 3 statuses: PASS, FIXED_AND_VERIFIED, N/A (no FAIL). Write in generator, not by hand. "Looks good"/"fixed"/"reran" insufficient — cite run, path, or result.

14 areas:
1. Package consistency
2. Clarity and scope
3. Realism and leakage
4. Difficulty
5. Solvability
6. Stability (run for you)
7. Oracle mode
8. Environment and files
9. Connectors, MCPs, and CLIs
10. Deliverables and artifact quality
11. Verifier coverage and fairness
12. LLM judge consistency
13. Reward hacking and exploitability
14. Cross-trial calibration (run for you)

### 6.3 Questions People Ask
- Claim tasks only in tracker dashboard
- Local setup not required to ship but worth having
- Connector = one app; CompanyBench = multiple apps
- Static review: free, required, before runs
- 4 runs, pass = full reward only, report all 4 not average
- Band: 1-3 accepted, 4 rejected, aim 1-2
- 0/4 submittable but needs extra solvability proof
- Solvability slot: non-oracle run only (oracle there = most common return reason)
- Edited prompt, nothing changed → mirror not synced
- Re-run battery when: instruction resolves ambiguity, expected answers/inputs/checks change
- Oracle must be exact, no partial credit
- False positive: yes, with written reason + evidence
- Platform problems: tracked queue, not chat
- Rework cycles: cap at 2
- Your prose IS graded

### 6.5 Glossary
- **Connector:** one mock application served as tools (sometimes called gym)
- **Harbor:** the runner (builds container, runs agent, runs checks)
- **Oracle:** replay of known-correct answer, no model (proves gradable)
- **Solvability:** one full-reward non-oracle run (proves model can do it)
- **Difficulty:** four independent rollouts (proves how often)
- **Stability:** re-grading one frozen attempt (confirms checks are consistent)
- **Full reward:** the only result that counts as a pass
- **Band:** how many of four passed (1-3 accepted, 4 rejected, aim 1-2)
- **Mirror:** second copy under environment/_app/ that actually runs
- **Surface:** everything the model can reach; closing it = only route is connector
- **Static review:** free required read of instruction + checks without running
- **Delivery report:** packaging/evidence report client requires inside bundle
- **Finalisation:** vetting after submission that decides if task reaches client
- **Free point:** check that passes every run, measures nothing
- **Reward hacking:** earning reward without doing the work (model or trainer)
