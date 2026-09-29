# CompanyBench Golden Task Analysis

**Source:** docs.google.com/document/d/1W3JqkOW3Qsc… (Company Bench Golden Analysis)
**Three accepted tasks analyzed:** atlanta-itinerary-settlement-standing-ranked, how-much-of-my-drive-is-link-only, outside-voices-in-the-locked-sales-drive

---

## CURRENT — If you read one page, read this one

The three tasks differ in everything visible — deliverable, connector, verifier type, how much had to be rebuilt — and share one method. **Difficulty came from work, never from ambiguity.** Every fork a reasonable reader could take two ways was pinned in the prompt or promoted to its own graded question, and the task stayed hard.

Grading was pushed as deterministic as the deliverable allowed, graded identity and structure rather than vocabulary, and every check was tested against the artefact that motivated it. The connector surface was closed in the environment, at every layer, failing closed. Every claim in the write-up was measured rather than argued.

**The one thing all three were still sent back for was a number in the write-up that no longer matched the disk.** That is Part 5, and it is one lint away from never happening again.

---

## Part 1 — The Three Tasks

### 1.1 At a glance

| | atlanta-itinerary-settlement-standing-ranked | how-much-of-my-drive-is-link-only | outside-voices-in-the-locked-sales-drive |
|---|---|---|---|
| Connector | Chat workspace: one room, one identity | Shared drive, read-only | Shared drive with threads + sharing lists |
| Shape | Eligibility judgement — 6 people, 2 contested | Multi-hop counting along containment axis | Reconciliation — posted vs sharing list |
| Deliverable | Message posted in room | JSON of counts | Report + JSON of rosters |
| Grading | Mostly live reads; 2 judged checks kept | All exact file checks, nothing judged | All exact file checks including report structure |
| Tool surface | No allowlist; raw state path gated | 7 read-only tools pinned | Full surface, no allowlist, documented |
| Band | Inside 1-2/4 | Inside band (earlier rejected as too easy) | Below band locally; held for platform re-run |
| Rework scale | Ask replaced wholesale | One line | Rebuilt over several rounds |

**What is shared is the method:** read the runs, find where the band comes from, close every fork, add work only if still too easy, close the surface, prove it, write it so it re-derives.

### 1.3 Where each one started, and what changed

**atlanta — the ask replaced:** Started as 3-person ranking (too easy). Rebuilt as 6 eligibility verdicts with 2 contested rows. Verifiers became line-anchored mutually exclusive per-person checks. Gold re-golded to majority reading. Raw state path gated on root-only key.

**how-much-of-my-drive — one line changed:** Prompt/gold/verifiers already settled. Defect was connector surface. One line: 7-tool read-only allowlist enforced on listing, call, and raw step path. Everything else byte-identical. Took 6 revisions — each fixed one dimension.

**outside-voices — rebuilt over several rounds:** Mined baseline read in band but band was ambiguity. Closed every ambiguity. Added 2 field-level discriminators. Went wholly deterministic. Surface closed at 4 independent points. Judge precondition neutralised. Stability rebuilt as re-grades of frozen trajectory.

**The sizing rule:** A one-line hardening is complete when the defect is one line wide. A wholesale rewrite is right when the ask itself cannot discriminate. What matters is the change matches the diagnosis.

---

## Part 2 — The Genuine Hardenings

### 2.1 The prompt: ambiguity converted into scope

Every ambiguity found was either **closed in the prompt** or **promoted into a separately graded question**. None was banked as difficulty. In all three tasks, closing every fork left the task hard — proof that difficulty was never in the ambiguity.

**What the three prompts have in common:** They read like a person with a reason to ask. They name the decoys. They pin every fork. They state the deliverable shape. They never hand over the method. Instruction length tracked forks to pin, not difficulty.

**The one-line test:** If a failing run's answer is correct for its own reading of your prompt, you are measuring the prompt. Close the reading or grade it separately.

### 2.2 Difficulty: one relation over a roster already correct

None responded with more scale, enumeration, or formatting rules. The lever was **one new relation over rows the run must already have right** — a relation the evidence already contained but no earlier question rewarded.

**Three properties every added discriminator had:**
1. **Chained** — sits on a roster the run must already have right
2. **Sharp** — wrong reading produces a specific, predictable wrong answer (parent set, empty set, subset)
3. **Oracle-proven** — oracle re-scores full marks through sanctioned tools

**What they explicitly declined:** No extra enumeration, no new scale, no additional formatting rules. Never a broken connector, missing field, or judge noise to hold the band.

### 2.3 Verifiers: deterministic, structural, tested against counterexample

**Deleted:** Tool-execution floor that paid for making calls (not the right ones), duplicate trace rubric, proximity regexes, TOTAL check coupling deterministic to judgement, trajectory check grading method.

**Loosened:** Closed action vocabulary → free text. Literal-word requirement → synonyms. Closing-section length counting rest of document → counts section's own body.

**Added:** Line-anchored mutually exclusive per-person verdict checks (anti-hedging). Heading checks for prompt-named sections. Field discipline: record on one line, identifier in first field, one address per field.

**Kept everywhere:** Every check category = "core". No duplicates, no correlated regexes, no dead-weight buckets. Every regex linear-time. Rubrics phrased "PASS only if… FAIL if…" never invertibly.

**The anti-stub finding:** Client's recurring finding was a run scoring full marks with an empty deliverable. Fix: disclose structure in prompt first (so grading is traceable), then grade the structure. Grading a structure the prompt never stated is a hidden requirement. Stating it and not grading it is a free pass.

**Gold passing proves nothing about a new check.** Every added/changed check was replayed against the specific artefact that exposed the defect.

### 2.4 The connector surface

Three postures, all closed:
- **No allowlist:** raw state path gated on root-only key file, gate fails closed
- **7-tool allowlist:** enforced on listing, call, and raw step path; raw state route not registered; gym bound to loopback
- **Full surface, documented:** store unreadable to agent; token minted at start from config agent cannot read; every route token-gated, gates return false on empty token

**Close it in the environment.** A rubric asking what the agent did without asking through what interface is not a gate. The fix that passed was a permission change, not a better rubric sentence.

**Fail closed, everywhere.** An empty expected token means no. A mis-built container fails its healthcheck instead of running open.

**Declared equals measured.** An allowlist is one way to close a surface, not the definition. Required: no ungated path, no readable store, declared surface equal to measured.

### 2.5 Gold, oracle and the judge precondition

- **Gold harvested, not guessed** — probe queries through oracle, rows read back into solution/
- **Gold kept where it belongs** — solution/ at task root, never under app mirror
- **Mirror byte-identical** — synced and diffed after every edit
- **Oracle re-run after every change** — exactly full marks with every verifier executing
- **The judge precondition closed** — removing judged checks does NOT remove the judge configuration precondition. Scorer returns zero before building verifier list if judge model/key resolves empty. `${VAR:-default}` does not help: fires only when absent, never when present and empty. **Test: run oracle with judge variables injected empty (not merely unset), require full marks with non-zero executed-item count.**

### 2.6 Evidence: one checksum, frozen re-grades, honest denominators

- **Freeze the task folder** — runs generated with output directory outside task folder; README/review/evaluations copied in only at packaging. Every run carries one checksum.
- **Stability is re-grades, not re-runs** — three independent oracle executions prove oracle is repeatable, not that graded submission was identical. Passing form: ≥3 gradings of one frozen trajectory, same digest, checks equal re-graded checks, built by script that aborts unless per-check identical.
- **Solvability from non-oracle run** — one genuine model run at exactly full marks through sanctioned tools
- **Infra excluded, each cause named** — crashed attempts excluded from every denominator, each cause identified individually

---

## Part 3 — What the Trainers Did Well (Nine Behaviours)

1. **Read runs, not rewards** — every non-passing run classified from trajectory reasoning, not mismatch shape
2. **Measured, didn't argue** — defect reproduced in-container before fix, re-tested after, hostile condition tested at worst
3. **Recorded the wrong intermediate fix** — proves final fix was reasoned, not stumbled into; strongest trust signal
4. **Named what they did not do** — pre-empts reviewer's obvious next question
5. **Declared the honest limit** — bounded claim that concedes what it cannot prove survives review
6. **Treated every finding as correct until disproved** — each review row is 4-part: finding, root cause, change made, how verified
7. **Sized the rework to the defect** — one line for one-line defect; new ask where ask couldn't discriminate
8. **Made narration battery-invariant** — rewrote to name golden path's deterministic tools, describe rest as examples
9. **Changed one thing, predicted first, checked disk** — one change per battery with expected outcome on record before run

### The review record as a unit of trust
Each row does four things in order: **The finding** (as gate stated it), **The root cause** (where defect actually lived), **The change made** (specific enough to find in bundle), **How it was verified** (measurement, gate's own way, hostile case included).

**Claims that do not re-derive are themselves a gate failure.** If the record says the run failed because of a broader filter, the trajectory must show a broader filter.

---

## Part 4 — Patterns Worth Reusing

### 4.1 Model failures that discriminate honestly

| Pattern | When it shows up | How to tell from verifier defect |
|---|---|---|
| Same instrument, different name | Judgement task requiring category bridge | One per-item check fails same way across runs; format/placement pass |
| Superset written in subset's field | Multi-part count with containment nesting | Failing value equals different field's correct value |
| Format filter too narrow | Listing task defining category in words | Count short by exactly that family's size |
| One wrong base, every derived count moves | Several counts over same enumerated set | All value checks fail by small correlated amounts = one failure |
| Scope error both directions | Two related who-can-reach questions | Per-check fails cluster in one named family |
| Field-blind permission reading | Permission task turning on row field | Wrong answers are unfiltered parent set or empty, never near miss |
| Reach conflated with grant | Remediation question over mixed owned/granted | Answer equals parent roster exactly |
| Identifier transcribed wrong | Report carrying identifier from free text | Exactly one per-record check fails, same misspelling recurs |

**Partial credit is signal; exact zero is suspicious.** A real attempt usually passes at least one check.

### 4.2 Task shapes that produced the band

- **Eligibility judgement with contested rows** — binary verdicts, hedging impossible, contested rows on real bridge
- **Multi-hop counting along containment axis** — shared enumerated base, fields nest, hold definitions apart
- **Reconciliation across two populations** — one by behaviour, one by grant, requires both rosters + difference + relations

### 4.3 Anti-patterns these tasks avoided

| Anti-pattern | What golden tasks did instead |
|---|---|
| Banking ambiguity as difficulty | Closed every fork or graded separately; task stayed hard |
| Counting crashes as difficulty | Excluded from every denominator, each cause named |
| Re-running until number looks right | One change, written prediction, one run, result accepted |
| Propping band with brittle check | New relation with real gold — or task discarded |
| Declared but not enforced | Enforced at every layer, failing closed, store unreadable |
| Grading vocabulary | Ids/addresses/counts matched exactly; wording left open |
| Presence-only grading | Structure disclosed in prompt, then graded |
| Stopping at trainer QC | Submitted to Final QC; finished only when marked delivered |

---

## Part 5 — What Still Got Sent Back

All three had sound underlying tasks. The rework verdict was **documentation and packaging, every time.**

### 5.1 Documentation freshness

- README/review quoting rewards, pass counts, checksums, verifier counts from a battery later runs replaced
- Stability mis-narrated on count and nature (fresh oracle repeats where disk holds re-grades)
- Oracle evidence in one place, narrated as in another
- QC report and client delivery artefacts absent; stray system files present
- A review-record claim that does not re-derive

**The fix:** Re-derive every figure — rewards, strict-pass count, checksum, verifier counts, stability count and nature, tool-call counts, oracle location — from evaluations/ and tests/manifest.json. Fail the build on any mismatch. Add presence check for QC report and client artefacts. Every gap was detectable this way; none needed judgement.

---

## Part 6 — Reference

### 6.1 The readiness test (14 checks)

1. Prompt reads like a person with reason to ask, names decoys
2. Every fork pinned or promoted to own graded question
3. Method never handed over
4. Difficulty in target band (1-2/4) with every failure attributed
5. Every added discriminator is new relation over already-correct roster (chained, sharp, oracle-proven)
6. Infra crashes excluded from every denominator, each with own cause
7. Verifiers: all core, none duplicated/coupled, identity and structure only, no free points
8. Prose deliverable structure disclosed in prompt then graded
9. Connector surface closed in environment, fail-closed, store unreadable
10. Oracle scores exactly full marks with every verifier executing (including judge config injected empty)
11. Gold harvested from real system; solution/ at task root; mirror byte-identical
12. All evidence carries one checksum, generated outside frozen task folder
13. Stability: ≥3 re-grades of one frozen submission, proven per-check identical
14. Every number in README and review record re-derives from disk

### 6.2 A five-minute read of any bundle

1. Open manifest — every check core, deterministic, no duplicates, regexes short and anchored
2. Open instruction — reads like a person, decoys named, forks pinned, deliverable shape stated, no method
3. Diff the mirror — instruction, config, tests identical between root and app mirror
4. Open environment — raw paths gated or absent, gates false on empty token, store unreadable
5. Check checksums — one value across every result in evaluations
6. Read one failing run — walk to step where it went wrong; is attribution in review record the one you would give?
7. Read review record — finding, root cause, change, verification — every number matches disk

### 6.3 Glossary

- **Band:** Strict passes out of 4. Client accepts 1-3; target 1-2. 4/4 rejected as too easy; 0 = broken/unproven.
- **Fork:** Point where reasonable reader could take two readings. Pinned = prompt settles it; promoted = becomes own graded question.
- **Decoy:** Something in corpus resembling the answer but not it. Named in prompt.
- **Discriminator:** Graded requirement separating capable runs. Sound when chained, sharp, oracle-proven.
- **Oracle:** Known-correct solution replayed through environment. Must score exactly full marks.
- **Solvability:** Evidence that genuine non-oracle model reaches full marks through sanctioned tools.
- **Stability:** Repeated gradings of one frozen submission returning identical per-verifier verdicts. Property of grader, not model.
- **Checksum:** Identity of task bundle at moment run was produced. One value across all evidence.
- **Connector surface:** Every path agent can reach system behind connector.
- **Fail closed:** Gate that denies when inputs missing/empty, rather than allowing.
- **Judge precondition:** Scoring engine's requirement for judge config, enforced before any verifier runs — present even with no judged checks.
- **Attribution:** Single cause assigned to failing run: model limitation, ambiguity, verifier defect, or grading infrastructure.
- **Re-derive:** Recompute stated figure from files on disk rather than trust the sentence stating it.
