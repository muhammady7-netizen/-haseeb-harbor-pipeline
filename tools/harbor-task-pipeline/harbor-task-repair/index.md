# Repair index

13 steps, run in this order. The order is a dependency order, not a preference:
**route → build the contract → close gaps → convert → prune → prove → regenerate.**

Coverage is added *before* anything is removed. Conversions happen before deletions. Evidence is
regenerated last, after the proof suite passes.

| NN | Step | Fixes | Cheap applicability probe | Recipe |
|----|------|-------|---------------------------|--------|
| 00 | **Route** | Is this defect even task-owned? | Read the finding text; check `tests/test.sh` reward shape | `recipes/00-route.md` |
| 01 | **Contract** | Builds the requirement map | Always applicable | `recipes/01-contract.md` |
| 02 | **Hygiene** | Mirror drift, leaked `solution/`, missing engine files, ambiguous spec shape | `diff` root vs `environment/_app/`; `ls tests/` | `recipes/02-hygiene.md` |
| 03 | **Traceability** | Hidden / unasked requirements | Any check whose expected value has no support in `instruction.md` | `recipes/03-traceability.md` |
| 04 | **Coverage** | Missing rows, fields, joins, exclusions, totals, negative cases | Requirements in `contract.json` with no mapped check | `recipes/04-coverage.md` |
| 05 | **Format** | Regex-on-raw-text, column-count, row-order, quoting | `lint` codes `A2`, `A2b`, `A3`, `A4` | `recipes/05-format.md` |
| 06 | **Equivalence** | Synonym gaps, narrow-to-golden, correct meaning rejected | Literal expected values not quoted from the prompt | `recipes/06-equivalence.md` |
| 07 | **Prose** | Keyword-soup and gameable memo grading | Any check reading `.md`/`.txt` with a word-order regex | `recipes/07-prose.md` |
| 08 | **Independence** | Duplicate checks, subsets, expected values copied from gold | `lint` code `A11`; constants matching `solution/` | `recipes/08-independence.md` |
| 09 | **Scoring** | Free points, per-row explosion, veto shape | `lint` codes `A5`, `A9`, `OWN1` | `recipes/09-scoring.md` |
| 10 | **Judge** | LLM-rubric instability | Any `rubric` / `agentic_llm_as_judge` assertion | `recipes/10-judge.md` |
| 11 | **Proof** | Mutation matrix, paraphrase suite, anti-hardcoding | `scripts/proof_suite.py` | `recipes/11-proof.md` |
| 12 | **Coherence** | Mirror re-sync, whole-diff review, re-run list | **Always runs** | `recipes/12-coherence.md` |

## Notes for the orchestrator

- **Steps 00, 09, 10 frequently end `not_applicable` or "infrastructure-owned".** That is a
  correct and cheap outcome, not a failure.
- **Step 01 must run in an isolated subagent that sees only `instruction.md`.** The recipe
  enforces this. Do not pass it anything else — the whole value of the map is that it was built
  without seeing the checks.
- **Step 04 depends on step 01.** If `contract.json` is missing, stop; do not let step 04 guess.
- **Steps 03, 06, 07 are the three that most often need a user decision** (disclose vs drop vs
  relax). Expect `needs_decision` there.
- **Step 11 gates step 12.** If the proof suite cannot run, step 12 reports the repair as
  *unproven* rather than done.

## Expected shape of a normal run

From 117 audited tasks and a peer audit of 83 more: about **1.4 hidden requirements** and
**1.7 coverage gaps** per task is typical, and 9 in 10 flagged tasks are fixable rather than
needing redesign. **A run that finds nothing is more likely a missed step 01 than a clean task.**
