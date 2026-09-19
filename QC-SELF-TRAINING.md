# QC Self-Training — 16 Findings I Missed on law-b39

**Lesson date:** 2026-09-17
**Task:** law-b39-l16-custody-letter-instruction-audit
**My verdict:** "Ship it — 0/4 excellent difficulty, 1 P1 solvability (structural)"
**Portal verdict:** "Rework — 12 major findings, 0/4 is FAKE difficulty, gold is broken"

**Root cause of every miss:** I ran `harbor_shannon_qc.py --no-model` (deterministic only) and skipped the GLM semantic review. I also never read the actual content — I checked counts, ran counterexamples, and trusted the gate algorithm. I never asked "can the disclosed rules actually produce every gold verdict?"

---

## The 12 portal findings and the checks I must run

### FINDING 1 — Gold verdicts not derivable from disclosed protocol
**Portal ID:** `layer1_package_consistency__solution_instruction_consistency`
**What the portal found:** Gold `letter_line_review.csv` verdict column embeds undisclosed distinctions. "may not fully appreciate" = AT_ODDS (ST-106/164/188/331) but "may not appreciate" = VERIFIED (ST-405). The instruction (OI-206) says "may not appreciate" — never mentions "fully" as a verdict-changing distinction.
**Why I missed it:** I never compared gold verdicts against the disclosed rules. I only checked that gold passes its own verifier grid (it does — the grid encodes the contradiction).
**The check I must run:**
```
For each gold verdict row:
  1. Read the governing entry (record_entry column)
  2. Read the letter_line wording
  3. Ask: "Does the governing entry + review_protocol RP-405 determine this verdict?"
  4. If the verdict depends on a distinction the instruction/protocol never states → HIDDEN REQUIREMENT → FAIL
```
**Detection pattern:** Find wordings that differ by ONE word (e.g. "fully" inserted) where both cite the same governing entry but get different verdicts. The instruction must disclose why that word changes the verdict. If it doesn't, the gold follows a contract the instruction does not state.

---

### FINDING 2 — Identical sentences get opposite verdicts (self-contradictory gold)
**Portal ID:** `layer1_realism_leakage__workflow_realism` (consolidated)
**What the portal found:**
- ST-186 and ST-407 share "Keep the letter soft, formal and succinct." → ST-186=AT_ODDS, ST-407=VERIFIED
- ST-332 and ST-420 share "I am concerned she may not appreciate..." → ST-332=AT_ODDS, ST-420=VERIFIED
- ST-166 and ST-403 share "On several occasions both children have stayed overnight..." → ST-166=AT_ODDS, ST-403=VERIFIED
**Why I missed it:** I checked the CSV row count (231) but never read the content for duplicate sentences with contradictory gold.
**The check I must run:**
```
1. Load letter_lines.csv (line_id, wording)
2. Load gold letter_line_review.csv (line_id, verdict, record_entry)
3. Group letter_lines by identical wording text
4. For each group with >1 row, compare gold verdicts
5. Any group with MIXED verdicts → SELF-CONTRADICTORY GOLD → FAIL
   (Two identical inputs with the same governing entry MUST get the same verdict.
    RP-401 says cited_entry doesn't matter — only the governing entry's position.
    Same words + same governing entry = same verdict, always.)
```
**Detection code:**
```python
from collections import defaultdict
lines = {row.line_id: row.wording for row in csv}
gold = {row.line_id: (row.verdict, row.record_entry) for row in csv}
by_wording = defaultdict(list)
for lid, w in lines.items():
    by_wording[w].append(lid)
for wording, ids in by_wording.items():
    verdicts = {gold[i] for i in ids}
    if len(verdicts) > 1:
        print(f"CONTRADICTION: {ids} share wording but have verdicts {verdicts}")
```

---

### FINDING 3 — Duplicated sentences in letter_lines.csv (realism failure)
**Portal ID:** `layer1_realism_leakage__workflow_realism`
**What the portal found:** "Densified population: 230 draft lines turns a short letter into a toy grid with literally duplicated sentences (ST-186/ST-221/ST-329/ST-407 share one sentence; ST-103/166/191/335/403 share another) plus synthetic 'wording is copies' placeholder lines (ST-415..ST-418). No real draft letter looks like this."
**Why I missed it:** I never read the letter_lines wording column for duplicates or placeholder text.
**The check I must run:**
```
1. Read every wording in letter_lines.csv
2. Group by identical text → any group with >1 row = duplicated sentence
3. Flag any wording that reads as synthetic: "wording is X", placeholder text, non-letter content
4. Count: how many duplicated sentences? If >2-3, the densification broke realism
```
**The rule:** A real draft letter has distinct sentences. Densification by duplicating sentences with different line_ids is NOT difficulty — it's a toy grid. Per All Hands: "Adding volume is NOT difficulty. Don't give away answers in prompts."

---

### FINDING 4 — 0/4 is failure_cause_validity failure, not difficulty
**Portal ID:** `layer2_difficulty`
**What the portal found:** All 4 GLM runs got 230/230 governing entries right and differ from gold on exactly the same 19 verdict rows — the cluster containing the self-contradictory gold rows and the undisclosed "fully appreciate" hair-split. The failures measure a GOLD DEFECT, not task difficulty.
**Why I missed it:** I saw 0/4 and called it "excellent difficulty" without checking WHICH rows failed and whether those rows are gold-defective.
**The check I must run:**
```
1. For each GLM run, list which rows the model got WRONG (verdict mismatch with gold)
2. Check: did GLM get the governing entries RIGHT? (record_entry column)
   - If 230/230 governing entries correct but verdicts wrong → the model understood the protocol
3. Cross-reference the failed rows against the gold-derivability check (Finding 1+2)
   - If the failed rows are the self-contradictory/undisclosed cluster → failure_cause_validity FAIL
4. The 0/4 is fake difficulty: the model can't get these rows right because the gold is broken
```
**The rule from SHANNON_RUBRIC:** "Clustered failures are an ambiguity signal, not a difficulty signal: when failed runs are near-passes that miss the SAME rows while everything else is right, open the governing policy clauses for exactly those rows and enumerate every defensible reading. If a competent alternative reading yields the agents' values, the failures are a prompt gap, not difficulty."

---

### FINDING 5 — No non-Oracle solvability trial (gate failure)
**Portal ID:** `layer2_solvability`
**What the portal found:** No non-oracle trajectory/result pair earns 1.0. The README concedes this and asks for a pod-lead waiver. The only 1.0 is the Oracle, which installs solution/files via solve.sh.
**Why I missed it:** I correctly identified this but dismissed it as "structural, not a portal blocker." I was wrong — the portal DOES block on it.
**The check I must run:**
```
1. Check evaluations/solvability/r1/ — does it exist with a non-Oracle model run at reward 1.0?
2. If no solvability trial AND GLM is 0/4 → the task has NO proof a model can solve it
3. Oracle 1.0 is NOT solvability proof if solve.sh is replay (Finding 7)
4. This is a BLOCKER, not advisory. The portal's layer2_solvability fires.
```

---

### FINDING 6 — Only Oracle 1.0 exists (eligible_strict_pass)
**Portal ID:** `layer2_solvability__eligible_strict_pass`
**What the portal found:** Only evaluations/oracle/verifier/reward.txt is 1.0 (agent 'oracle', model_name null, trajectory session 'oracle-replay'). All four glm-5.2 runs are 0.0. Passing evidence is solution replay only.
**Why I missed it:** Same as Finding 5 — I dismissed it.
**The check I must run:**
```
1. List all runs with reward == 1.0
2. For each, check: is it Oracle (agent='oracle', model_name=null)?
3. If ALL 1.0 runs are Oracle → no model has ever solved this task → solvability unproven
```

---

### FINDING 7 — solve.sh is replay, not legitimate work
**Portal ID:** `layer2_solvability__solution_legitimacy`
**What the portal found:** The sole passing run performs none of the graded reasoning. solve.sh copies pre-computed gold deliverables into /app and emits a hand-authored trajectory from golden_trajectory.json. README states it is "a hand-authored reference trajectory, not a byte-copy of a model run." That is replay, not a legitimate demonstration that the work can be done.
**Why I missed it:** I accepted Oracle 1.0 without reading solve.sh.
**The check I must run:**
```
1. Read solution/solve.sh
2. Does it:
   a. cp -r solution/files/* /app/ (copy pre-computed gold)? → REPLAY
   b. Compute the answer from inputs? → REAL WORK
3. Does it emit trajectory from golden_trajectory.json (hand-authored)? → REPLAY
4. If solve.sh is replay → Oracle 1.0 proves gold matches verifier, NOT that the task is solvable
5. Check README: does it admit the trajectory is hand-authored?
```
**Detection pattern:**
```bash
grep -E "cp .*(solution|files)" solve.sh    # copies pre-computed = replay
grep -E "golden_trajectory" solve.sh         # emits hand-authored trajectory = replay
grep -E "python.*compute|pandas|calculate" solve.sh  # real work
```

---

### FINDING 8 — Inputs insufficient to reach reward 1.0
**Portal ID:** `layer2_solvability__instruction_environment_sufficiency`
**What the portal found:** All four GLM runs applied RP-401..RP-404 correctly (every governing entry right) yet failed on verdicts that the records cannot determine — identical letter sentences require opposite verdicts (ST-186/ST-407, ST-332/ST-420, ST-166/ST-403). Success depends on undisclosed gold-only distinctions.
**Why I missed it:** I never asked whether the disclosed rules + inputs can produce every gold verdict.
**The check I must run:**
```
1. Read instruction.md + all input files + review_protocol.md
2. For each gold verdict, ask: "Given ONLY these disclosed rules, can I determine this verdict?"
3. If two identical inputs get different verdicts and the rules don't explain why → inputs insufficient
4. This is the BLIND-READER TEST from the non-connector-task-standard (DIS-6):
   "Give the instruction and inputs to someone who hasn't seen the verifier.
    Ask them to list every literal the deliverables must contain.
    Compare with the literals in verifier.json.
    Anything the verifier knows and the reader does not is illegal."
```

---

### FINDING 9 — Stability repeats lack frozen identity
**Portal ID:** `layer2_stability__frozen_identity`
**What the portal found:** No hash or immutable identity of a trajectory/artifact set is shipped. Each repeat re-ran the oracle agent (agent_execution start/finish differ per repeat). The only shared identifier is task_checksum (the task tree, not the graded submission). Identity of graded evidence is asserted, not evidenced.
**Why I missed it:** I saw "3 repeats, all 1.0, all equal" and said PASS. I never checked whether the repeats carry artifact hashes or immutable identity.
**The check I must run:**
```
1. For each evaluations/stability/repeat-NN/ folder:
   a. Does it contain ONLY result.json? → no frozen identity evidence
   b. Does it contain score.json/ctrf.json/artifacts? → per-check evidence present
2. Check: are the agent_execution windows identical (clones) or distinct (re-runs)?
   - Distinct re-runs without frozen artifacts = identity asserted, not evidenced
3. The portal's frozen_identity subcheck requires:
   - A hash or immutable identifier of the graded artifact set
   - Evidence that each repeat graded the SAME submission, not just the same task tree
```

---

### FINDING 10 — Stability repeats lack per-check evidence
**Portal ID:** `layer2_stability__per_check_stability`
**What the portal found:** The repeats contain no per-check evidence at all (no score.json, ctrf.json or artifacts). README says "ship result.json only." Equal totals cannot be shown to rest on the same nine check outcomes, and offsetting flips cannot be excluded.
**Why I missed it:** I checked reward equality (all 1.0) but never checked per-check outcomes.
**The check I must run:**
```
1. For each repeat folder, list the files
2. If only result.json → no per-check evidence → per_check_stability FAIL
3. The portal requires evidence that the SAME 9 checks passed in each repeat
4. Equal reward totals are NOT sufficient — offsetting flips could produce the same total
5. Each repeat should carry: score.json (per-check pass/fail), ctrf.json (test report),
   or at minimum a hash of the graded artifact set
```

---

### FINDING 11 — Verifier fairness aggregate fails
**Portal ID:** `layer5_verifier_fairness_static`
**What the portal found:** Aggregate fails on requirement_traceability, semantic_equivalence, surface_form_brittleness and counterfactual_strength. The core register_table/results_figures expectations encode verdicts the disclosed protocol cannot yield, and the core answer_at_odds_figure regex rejects the required sentence when the number is bolded.
**Why I missed it:** I ran `--no-model` and skipped the GLM static review. I never tested the regex against surface-form variants.
**The check I must run:**
```
1. For answer_at_odds_figure regex:
   - Test against: "Letter lines at odds with the record: 124"
   - Test against: "Letter lines at odds with the record: **124**" (bold)
   - Test against: "Letter lines at odds with the record: *124*" (italic)
   - Test against: "Letter lines at odds with the record: 124.0"
   - Test against: "Letter lines at odds with the record:  124  " (extra whitespace)
   - If any correct variant is rejected → surface_form_brittleness → FAIL

2. For register_table/results_figures:
   - Do the expected values encode verdicts the disclosed protocol cannot yield?
   - If yes → requirement_traceability FAIL (verifier checks something the prompt can't produce)

3. Run the full QC WITH the model stage (--thinking disabled is fine, ~2 min)
   The model catches semantic defects no deterministic check can
```

---

### FINDING 12 — Counterfactual strength fails (correct submission rejected)
**Portal ID:** `layer5_verifier_fairness_static__counterfactual_strength`
**What the portal found:** A genuinely correct, protocol-faithful submission is rejected. The four GLM submissions reproduce every governing entry and differ only on rows whose gold is indeterminate. The verifier cannot separate a correct solution from the gold's arbitrary choices.
**Why I missed it:** I ran built-in counterexamples (empty, duplicated, token-stuffed) but never constructed a "correct but rejected" counterexample. The GLM runs ARE this counterexample — I should have recognized that.
**The check I must run:**
```
1. Construct a submission that follows the disclosed protocol perfectly:
   - Every governing entry correct
   - Every verdict follows from the disclosed rules
2. Run it through the verifier
3. If the verifier rejects it → counterfactual_strength FAIL
4. The GLM runs are natural counterexamples:
   - If GLM got 230/230 governing entries right but was rejected
   - AND the rejected verdict rows are ones the protocol can't determine
   - THEN a correct, protocol-faithful submission IS being rejected
```

---

### FINDING 13 — Golden trajectory contradicts gold results
**Portal ID:** `D21.notes_contradict_runs` (Client PreQC deterministic)
**What the portal found:** `solution/golden_trajectory.json` step 7 writes `results.json` with old counts (verified=17, at_odds=18, not_in_record=7, clarification_governed=15) while the actual `solution/files/results.json` has (87/154/49/168). The trajectory was never updated after densification.
**Why I missed it:** I read solve.sh and saw it copies pre-computed gold + emits trajectory from golden_trajectory.json. But I never checked whether the EMBEDDED results.json in the trajectory MATCHES the current gold results.json.
**The check I must run:**
```
1. Read golden_trajectory.json
2. Find the step that writes results.json (or answer.md, or letter_line_review.csv)
3. Compare the embedded counts to solution/files/results.json
4. If they differ → trajectory contradicts gold → FAIL
5. This is a deterministic P0 — the portal's D21 check catches it automatically
```
**Detection pattern:**
```python
import json
traj = json.load(open('solution/golden_trajectory.json'))
for step in traj:
    cmd = step.get('arguments', {}).get('command', '')
    if 'results.json' in cmd and 'verified_count' in cmd:
        # Extract the embedded JSON from the heredoc
        # Compare to solution/files/results.json
        # If counts differ → CONTRADICTION
```

---

### FINDING 14 — review.csv cites stale counts that don't match the bundle
**What I found:** review.csv Layer 5 row says "results_figures 105/176/44/163" but the actual gold results.json has 100/181/44/202. The review.csv was not updated after the last gold change.
**Why I missed it:** I never compared the counts cited in review.csv against the actual gold results.json.
**The check I must run:**
```
1. Read review.csv
2. Find every count cited (verified_count, at_odds_count, etc.)
3. Compare each to solution/files/results.json
4. If any differ → review.csv stale → FAIL
```

---

### FINDING 15 — golden_trajectory embedded CSV has wrong row count
**What I found:** golden_trajectory.json step 6 embeds letter_line_review.csv with 324 data rows, but the actual gold has 325 data rows. One row is missing from the trajectory.
**Why I missed it:** I checked the embedded results.json counts (Finding 13) but never checked the embedded CSV row count.
**The check I must run:**
```
1. Read golden_trajectory.json
2. Find the step that writes letter_line_review.csv
3. Count the embedded data rows
4. Compare to solution/files/letter_line_review.csv row count
5. If they differ → trajectory CSV is stale → FAIL
```

---

### FINDING 16 — Oracle trajectory shows stale counts (run before gold update)
**What I found:** The oracle trajectory's embedded results.json shows `104/177/44/162` but the current gold has `100/181/44/202`. The oracle was run BEFORE golden_trajectory.json was updated. The oracle artifacts/app/ has the correct gold (100/181/44/202) because solve.sh copies solution/files/ at run time. But the trajectory was emitted from the old golden_trajectory.json.
**Why I missed it:** I checked the golden_trajectory.json file itself (Finding 13) but never checked the ORACLE'S trajectory.json to see if it matches the current golden_trajectory.json.
**The check I must run:**
```
1. Read evaluations/oracle/agent/trajectory.json
2. Find the step that writes results.json
3. Compare the embedded counts to solution/files/results.json
4. If they differ → oracle was run with a stale golden_trajectory → re-oracle needed
5. Also check: do the oracle artifacts/app/results.json match the gold? (they will if solve.sh copies solution/files/)
```

---

### FINDING 14 — Regex boundary `(?!\d)` accepts decimal continuations

**Portal ID:** `layer5_verifier_fairness_static__surface_form_brittleness` + `layer5_verifier_fairness_static__counterfactual_strength`
**What the portal found:** The `answer_at_odds_figure` regex uses `(?!\d)` as the only boundary guard after the figure. This rejects a following digit (so "1755" fails) but accepts a decimal point or comma: "175.5" and "175,5" both match because "175" matches the alternation and the next character (".") is not a digit, so `(?!\d)` passes. A submission with "175.5" in answer.md returns reward 1.0 — a wrong figure scores the same as the correct one. README.md claimed `(?!\d|[.,]\d)` but the verifier.json had `(?!\d)` — the fix never landed.
**Why I missed it:** I thought I fixed the regex boundary but the fix didn't land in the actual zip. I never re-verified the regex in the packaged zip against the decimal continuation test.
**The check I must run:**
```
1. Read the answer_at_odds_figure regex from tests/verifier.json
2. Test against: "Letter lines at odds with the record: 175.5"
3. Test against: "Letter lines at odds with the record: 175,5"
4. If either matches → surface_form_brittleness → FAIL
5. The correct guard is (?!\d|[.,]\d) not (?!\d)
```
**Detection pattern:** Any regex with `(?!\d)` as a boundary guard should be tested against decimal/comma continuations. If the figure is "175" and "175.5" also matches, the guard is too weak.

---

## THE 7-LAYER CHECK I MUST RUN EVERY TIME

### Layer 0 — Read the content (5 min)
- [ ] Read instruction.md end to end
- [ ] Read every environment/input/ file end to end
- [ ] Read solution/files/ gold deliverables end to end
- [ ] Read solution/solve.sh — replay or real work?
- [ ] Read tests/verifier.json — every check's expected value

### Layer 1 — Gold derivability (5 min)
- [ ] Can every gold verdict be derived from disclosed rules? (blind-reader test)
- [ ] Are there identical wordings with different verdicts? (self-contradiction)
- [ ] Are there hair-split distinctions the instruction doesn't disclose?
- [ ] Are there placeholder/synthetic wordings in the data?

### Layer 2 — Failure cause validity (5 min)
- [ ] Which rows did GLM get wrong?
- [ ] Did GLM get governing entries right? (if 230/230, model understood protocol)
- [ ] Are the failed rows the self-contradictory/undisclosed cluster?
- [ ] Is the 0/4 measuring a gold defect, not difficulty?

### Layer 3 — Surface-form fairness (2 min)
- [ ] Test answer_at_odds_figure regex against bold/italic/format variants
- [ ] Test every regex against reversed token order, synonyms, format variants
- [ ] Does any correct alternative get rejected?

### Layer 4 — Solvability legitimacy (2 min)
- [ ] Read solve.sh — does it copy pre-computed gold or compute the answer?
- [ ] Does any non-Oracle model run score 1.0?
- [ ] If solve.sh is replay AND no model 1.0 → solvability FAIL (not waivable)
- [ ] Read golden_trajectory.json — does the embedded results.json match solution/files/results.json? (Finding 13)
- [ ] Does the embedded answer.md have the correct at-odds figure?
- [ ] Does the embedded letter_line_review.csv have the correct row count and verdicts?

### Layer 5 — Stability evidence (2 min)
- [ ] Do repeat folders carry per-check evidence (score.json/ctrf.json/artifacts)?
- [ ] Or only result.json (total only, per-check stability not evidenced)?
- [ ] Are repeats frozen artifacts or re-runs (frozen_identity check)?

### Layer 6 — Run the FULL QC tool (2 min)
- [ ] Run harbor_shannon_qc.py WITH model stage (NOT --no-model)
- [ ] Read verdict.md top to bottom
- [ ] Check instruction_verifier_consistency (mandatory subcheck)
- [ ] Check failure_cause_validity (mandatory subcheck)

### Layer 7 — Realism (2 min)
- [ ] Read letter_lines wording — duplicated sentences? placeholder text?
- [ ] Does the task read like a real request or a benchmark-shaped puzzle?
- [ ] Are the traps in the DATA (good) or in hidden rules/hair-splits (bad)?

---

## THE 5 QUESTIONS I MUST ASK BEFORE SAYING "SHIP IT"

1. **"Can a reader with ONLY the instruction + inputs derive every gold verdict?"**
   If no → hidden requirement → the task is broken, not hard.

2. **"Do identical inputs get identical verdicts?"**
   If no → self-contradictory gold → the task is unsolvable.

3. **"Are the GLM failures on rows where the gold is broken?"**
   If yes → 0/4 is fake difficulty → failure_cause_validity FAIL.

4. **"Does solve.sh compute the answer or copy pre-computed gold?"**
   If copies → Oracle 1.0 is replay → solvability unproven.

5. **"Did I run the model stage of the QC tool?"**
   If no → I skipped semantic analysis → I will miss findings.

---

## WHAT THE DETERMINISTIC LAYER CANNOT CATCH (and I must do manually)

| Check | Why deterministic can't | What I must do |
|---|---|---|
| Gold derivability | Requires reading content semantically | Read each gold verdict, ask if disclosed rules produce it |
| Self-contradiction | Requires comparing letter_lines to gold | Group by identical wording, compare verdicts |
| Failure cause validity | Requires cross-referencing failed rows against gold | List GLM failed rows, check if they're gold-defective |
| Solve.sh legitimacy | Requires reading the script | Read solve.sh, check for cp/copy of pre-computed files |
| Surface-form fairness | Requires generating format variants | Test regex against bold/italic/format variants of correct answers |
| Stability per-check | Requires checking folder contents | List files in each repeat, check for score.json/ctrf.json |
| Realism | Requires reading content | Read letter_lines, check for duplicates/placeholder text |

---

## RED FLAGS THAT MEAN "STOP — THE GOLD IS BROKEN"

- GLM gets 230/230 governing entries right but 0/4 verdicts → the protocol is understood, the verdicts are indeterminate
- All 4 GLM runs fail on the SAME rows → clustered failure → ambiguity signal, not difficulty
- Two identical sentences in letter_lines.csv → if they get different verdicts, the gold is self-contradictory
- A one-word difference in wording ("fully" inserted) changes the verdict → undisclosed hair-split
- solve.sh copies pre-computed files → Oracle is replay, not solvability proof
- README says "hand-authored reference trajectory" → the golden trajectory is not earned by work
- Duplicated sentences in the data → densification broke realism
- "wording is X" placeholder text → synthetic, not a real letter
- golden_trajectory.json embeds old counts that differ from solution/files/results.json → trajectory contradicts gold
- golden_trajectory.json embedded CSV has fewer rows than solution/files/letter_line_review.csv → trajectory CSV is stale
- review.csv cites counts that don't match solution/files/results.json → review.csv is stale
- review.csv cites paths that don't exist in the package → review.csv references stale files

---

## REMEMBER

**The deterministic QC engine checks whether the gold passes its own grid. It does NOT check whether the grid itself is fair.** A self-contradictory gold passes its own verifier because the verifier encodes the same contradictions. The model stage catches this by reading the content and asking "can the disclosed rules produce these verdicts?"

**0/4 is NOT automatically excellent difficulty.** It is excellent ONLY IF every failure is MODEL-attributed — the model had everything it needed and still got it wrong. If the model got the governing entries right but the verdicts wrong, and the verdicts the model chose are defensible from the disclosed rules, then the gold is broken, not the model.

**Oracle 1.0 is NOT proof of solvability.** It is proof that the gold matches the verifier. If solve.sh copies pre-computed files, Oracle 1.0 proves nothing about whether the task can be solved by reasoning from the inputs.

**Never run --no-model and trust the result for a final ship decision.** The deterministic layer catches packaging, hygiene, reward-hacking, and counterexamples. It CANNOT catch gold-derivability, self-contradiction, failure-cause-validity, or surface-form fairness. Those require the model stage or manual semantic analysis.
