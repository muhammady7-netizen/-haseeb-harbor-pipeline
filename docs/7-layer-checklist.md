# The 7-Layer Checklist — Run This On Every Zip

Before saying "ship it," run ALL 7 layers. Do not skip any. Do not run only the deterministic engine.

## Layer 0 — Read the content (5 min)
- [ ] Read `instruction.md` end to end
- [ ] Read every `environment/input/` file end to end
- [ ] Read `solution/files/` gold deliverables end to end
- [ ] Read `solution/solve.sh` — is it replay (copies pre-computed files) or real work?
- [ ] Read `tests/verifier.json` — every check's expected value and predicate

## Layer 1 — Gold derivability (5 min)
- [ ] Can every gold verdict be derived from disclosed rules? (blind-reader test)
- [ ] Group `letter_lines.csv` by identical wording. Compare gold verdicts within each group. Any mixed verdicts → self-contradictory gold → FAIL
- [ ] Check for hair-splits: wordings that differ by one word with different verdicts, where the instruction doesn't disclose the distinction
- [ ] Check for placeholder/synthetic wording in the data ("wording is X" etc.)
- [ ] Check that gold counts (verified/at_odds/not_in_record/clarification_governed) are self-consistent

## Layer 2 — Failure cause validity (5 min)
- [ ] For each GLM run, list which rows the model got WRONG (verdict mismatch)
- [ ] Did GLM get the governing entries RIGHT? (record_entry column)
  - If all governing entries correct but verdicts wrong → model understood the protocol
- [ ] Cross-reference failed rows against the gold-derivability check (Layer 1)
  - If the failed rows are the self-contradictory/undisclosed cluster → failure_cause_validity FAIL
- [ ] Is the 0/4 measuring a gold defect, not difficulty?
  - Check: did all 4 runs fail on the SAME rows? → clustered failure → ambiguity signal
- [ ] Are the failures MODEL-attributed? (model had everything, still wrong) or SPEC-attributed? (prompt/verifier/gold wrong)

## Layer 3 — Surface-form fairness (2 min)
- [ ] Take the `answer_at_odds_figure` regex. Test against:
  - plain number
  - bold `**124**`
  - italic `*124*`
  - bold `__124__`
  - decimal `124.0`
  - words `one hundred twenty-four`
  - newline
  - heading before
  - mid-sentence
- [ ] If any correct variant is rejected → surface_form_brittleness → FAIL
- [ ] Take every regex predicate. Test reversed token order, synonym substitution, format variants
- [ ] Does any correct alternative get rejected? → grading gap

## Layer 4 — Solvability legitimacy (2 min)
- [ ] Read `solve.sh`. Does it:
  - `cp -r solution/files/. /app/` → REPLAY (not proof of solvability)
  - Compute the answer from inputs → REAL WORK (proof of solvability)
- [ ] Does it emit trajectory from `golden_trajectory.json` (hand-authored)? → REPLAY
- [ ] Does any non-Oracle model run score 1.0?
  - If no model 1.0 AND solve.sh is replay → solvability FAIL
  - If no model 1.0 AND solve.sh computes → solvability still unproven but task is legitimate
- [ ] Check `evaluations/solvability/r1/` — does it exist with a non-Oracle model run at reward 1.0?

## Layer 5 — Stability evidence (2 min)
- [ ] List files in each `evaluations/stability/repeat-NN/` folder
  - Only `result.json` → no per-check evidence → per_check_stability FAIL
  - Has `score.json`/`ctrf.json`/`test-stdout.txt` → per-check evidence present
- [ ] Check per-check outcomes: are they identical across all repeats?
  - Equal reward totals are NOT sufficient — offsetting flips could produce the same total
- [ ] Are the repeats frozen artifacts or re-runs?
  - Distinct agent_execution windows without frozen artifacts = identity asserted, not evidenced

## Layer 6 — Run the FULL QC tool (2 min)
- [ ] Run `harbor_shannon_qc.py` WITH the model stage (NOT `--no-model`)
- [ ] Read `verdict.md` top to bottom
- [ ] Check `instruction_verifier_consistency` (mandatory subcheck — cannot be averaged away)
- [ ] Check `failure_cause_validity` (mandatory subcheck — cannot be averaged away)
- [ ] Every P1 is a blocker. Every P2 is a weakness.
- [ ] **review.csv count audit:** extract every number cited in review.csv, compare to actual gold/verifier/stability/difficulty (Finding 14)
- [ ] **review.csv cited path audit:** every path cited in change_made must exist in the package
- [ ] **README count audit:** extract numbers from README and compare to shipped check_count
- [ ] **Stray verifier.json.* variants:** check tests/ for verifier.json.* files
- [ ] **golden_check.json/summary.json audit:** if these exist, their counts must match shipped verifier
- [ ] **task_checksum consistency:** all runs must have the same checksum

## Layer 7 — Realism (2 min)
- [ ] Read `letter_lines.csv` wording column. Are there:
  - Duplicated sentences? → realism concern
  - Placeholder text? → realism FAIL
  - Synthetic "wording is X" entries? → realism FAIL
- [ ] Does the task read like a real person's request, or a benchmark-shaped puzzle?
- [ ] Are the traps in the DATA (good) or in hidden rules/hair-splits (bad)?
- [ ] Per All Hands: "Put difficulty in the DATA, not in rules/instructions."

---

## The 5 questions to ask before saying "ship it"

1. **Can a reader with ONLY the instruction + inputs derive every gold verdict?**
   If no → hidden requirement → the task is broken, not hard.

2. **Do identical inputs get identical verdicts?**
   If no → self-contradictory gold → the task is unsolvable.

3. **Are the GLM failures on rows where the gold is broken?**
   If yes → 0/4 is fake difficulty → failure_cause_validity FAIL.

4. **Does solve.sh compute the answer or copy pre-computed gold?**
   If copies → Oracle 1.0 is replay → solvability unproven.

5. **Did I run the model stage of the QC tool?**
   If no → I skipped semantic analysis → I will miss findings.

---

## Red flags that mean "STOP — the gold is broken"

- GLM gets 230/230 governing entries right but 0/4 verdicts → the protocol is understood, the verdicts are indeterminate
- All 4 GLM runs fail on the SAME rows → clustered failure → ambiguity signal, not difficulty
- Two identical sentences in letter_lines.csv → if they get different verdicts, the gold is self-contradictory
- A one-word difference in wording changes the verdict → undisclosed hair-split
- solve.sh copies pre-computed files → Oracle is replay, not solvability proof
- README says "hand-authored reference trajectory" → the golden trajectory is not earned by work
- Duplicated sentences in the data → densification broke realism
- "wording is X" placeholder text → synthetic, not a real letter
- Regex rejects bold/italic numbers → surface_form_brittleness
