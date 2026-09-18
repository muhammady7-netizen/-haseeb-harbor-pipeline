# 9/10 JUDGMENT — Law-b39 Case Study (Sep 18, 2026)

## How to use this repo on any PC

### One-command judgment
```bash
git clone https://github.com/haseeb371/local-qc.git
cd local-qc

# Judge a zip (deterministic only, ~18 sec):
python scripts/judge.py "C:\path\to\task.zip" --no-model

# Judge a zip (with model stage, ~3 min — needs WANDB_GLM_API_KEY):
python scripts/judge.py "C:\path\to\task.zip"
```

### What judge.py does (331 checks in one pass)
1. Extracts zip, scans CRLF/BOM (P0 blocker)
2. Runs harbor_shannon_qc.py --no-model → deterministic findings, gates, packaging, review.csv
3. Runs harbor_shannon_qc.py WITH model → GLM static + runs triage (if API key set)
4. Adds 7 extra check families the engine doesn't do:
   - Gold derivability (self-contradiction, hair-splits, placeholder text)
   - Trajectory freshness (embedded counts vs gold)
   - review.csv count claims vs actual gold
   - /tests lock in Dockerfile
   - Host paths in trial metadata
   - D1-D5 linter (re-implemented)
5. De-duplicates findings, prints verdict + every finding

### Reading the verdict
```
VERDICT: FAIL / NEEDS_REVIEW / PASS
  P0: N   P1: N   P2: N   INFO: N
```
- **P0** = blocker — must fix before upload (CRLF, gold contradicts, exploitable verifier)
- **P1** = must fix or expected (solvability gate, root container, stale trajectory)
- **P2** = non-blocking weakness (stability files, review.csv paths, counterexamples)
- **INFO** = advisory (source cap, network_mode, artifacts)

## The knowledge base — read in order

1. **docs/how-qc-works.md** — the 3-layer QC engine algorithm (deterministic, static, runs)
2. **QC-SELF-TRAINING.md** — 16 findings I missed + 7-layer checklist + red flags
3. **docs/definitive-qc-checklist.md** — 331 checks across 11 layers with verdict computation
4. **docs/portal-findings-law-b39.md** — the 12 portal findings with exact evidence
5. **docs/fix-plan-law-b39.md** — 4 iterations: broken → wording fix (4/4) → reversal CL entries
6. **docs/qc-standards-summary.md** — OBI A1-A6, G1-G7, M1-M6, H1-H4, O1-O17, E1-E14, B1-B8
7. **docs/repo-overview.md** — haseeb-pipeline structure, resume.ps1, workflow, machine.json
8. **docs/all-hands-key-takeaways.md** — Sep 11 guidance on hardening
9. **scripts/judge-zip.md** — step-by-step manual judgment guide

## The 5 questions to ask before saying "ship it"
1. Can a reader with ONLY instruction + inputs derive every gold verdict?
2. Do identical inputs get identical verdicts?
3. Are GLM failures on rows where the gold is broken?
4. Does solve.sh compute the answer or copy pre-computed gold?
5. Did I run the model stage (not --no-model)?

## The law-b39 case study — 18 iterations to ship

### Iteration 1: Portal found 12 findings (my --no-model missed all)
- Gold self-contradictory (identical sentences, opposite verdicts)
- "Fully appreciate" hair-split (undisclosed distinction)
- 0/4 was fake difficulty (gold was broken)
- solve.sh is replay
- Stability lacked per-check evidence
- Regex rejected bold numbers

### Iteration 2: My wording fix → GLM 4/4 (too easy)
- Made AT_ODDS reasons visually obvious → model pattern-matched, no reasoning
- Lesson: don't make the difference obvious — put difficulty in the DATA

### Iteration 3: Reversal CL entries (smart fix)
- Added 3 new clarification entries that REVERSE the original position
- CL-307 tone: "firm, not soft" (supersedes OI-210 "soft")
- CL-308 behavioural_plan: "confidence only" (supersedes OI-207 "all three")
- CL-309 concern: "position only, not violation" (supersedes OI-206 "both limbs")
- RP-407 cross-subject citation exception: when cited_entry is CL for different subject, OI governs
- RP-408 compound position: one-limb assertion of a compound position is AT_ODDS

### Iteration 4: ST-508 gold wrong + /tests reward hacking + CRLF crash
- ST-508: gold had AT_ODDS/OI-207 but CL-308 governs → should be VERIFIED/CL-308
- /tests: agent can read verifier.json (answer key) → chmod 000 /tests + restore in test.sh
- CRLF: all 60 files had Windows line endings → Linux crashes → converted to LF

### Final state: GLM 0/4 GENUINE
- All 4 runs: verified=101, at_odds=180 (gold 100/181)
- Same 3 rows fail every time: ST-586 (RP-408), ST-587 (RP-407), ST-588 (RP-407)
- All MODEL-attributed: model missed the compound position restriction + cross-subject exception
- Tight spread: all 4 identical
- No gold defects, no ambiguity, no verifier unfairness

## Key lessons (for any task, not just law-b39)

1. **Never trust --no-model for a final ship decision** — it catches packaging, not semantics
2. **Always check CRLF before uploading** — portal crashes on `\r\n`
3. **Gold must be derivable from disclosed rules** — the blind-reader test
4. **0/4 is not automatically excellent** — check WHICH rows fail and WHY
5. **Identical inputs must get identical verdicts** — self-contradiction = unsolvable
6. **solve.sh copying pre-computed gold is replay** — not solvability proof
7. **Trajectories must match gold** — embedded counts and CSV rows
8. **review.csv counts must match the actual gold** — not the previous version
9. **/tests must be locked from the agent** — reward hacking vector
10. **Put difficulty in the DATA, not in rules/instructions** — model turns rules into code
