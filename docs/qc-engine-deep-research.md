# QC Engine Deep Research — Additional Checks Discovered

After re-reading the full 5,444-line `harbor_shannon_qc.py`, focusing on `derive_deterministic_findings`, `review_csv_audit`, `stale_bundle_audit`, `reward_hacking_audit`, and the model prompt builders, here are the additional checks the QC engine runs that I was not doing manually.

## review_csv_audit — the full algorithm

The review.csv audit does far more than check PASS/FIXED_AND_VERIFIED status:

1. **PASS row with change_made filled** → FAIL ("should be FIXED_AND_VERIFIED, or leave change_made blank")
2. **PASS row with "No change required"** → FAIL (leave blank instead)
3. **Issue-ID audit stub on PASS row** → FAIL (e.g. "confirmed issue QC1-1")
4. **FIXED_AND_VERIFIED with empty change_made** → FAIL
5. **FIXED_AND_VERIFIED citing files unchanged from baseline** → FAIL (if --baseline provided)
6. **FIXED_AND_VERIFIED but prose says "still open/unfixed/broken"** → FAIL
7. **Cited path in change_made doesn't exist in package** → WARN (e.g. "cites consistency/requirements.json which does not exist")
8. **Unknown status** → WARN
9. **Open-item phrasing** ("still investigating", "to be determined", "pending review", "needs further analysis", "not yet resolved", "under review") → FAIL
10. **Claim spot-checks against bundle:**
    - Difficulty row: extracts "N/M" pattern → compares to difficulty gate's strict_passes/valid_runs
    - Stability row: extracts "N repeats" → compares to stability gate's repeat count
    - Any row: extracts "N in total" / "all N checks" / "N deterministic" → compares to shipped check_count
    - If claim ≠ bundle → WARN
11. **All rows PASS (no FIXED_AND_VERIFIED)** → FAIL ("does not document any fixes")

**My new check:** Extract every number cited in review.csv and compare to the actual bundle (results.json counts, verifier check count, stability repeat count, difficulty pass rate).

## stale_bundle_audit — the full algorithm

1. **Graded vs shipped grid:** for each run, compares the check names that were graded against the shipped verifier names. If they differ → P1 "stale bundle"
2. **golden_check.json / summary.json count claims:** reads `evaluations/golden_check.json` and `evaluations/summary.json`, extracts `verifiers.total` and `verifiers_graded_per_run`, compares to shipped check_count. Mismatch → P2
3. **golden_check.json trial names:** compares trial names in golden_check.json against actual shipped trial folder names. Missing/extra → P2
4. **README claimed_verifier_counts:** extracts numbers from README and compares to shipped check_count. Mismatch → P2
5. **task_checksum consistency:** all runs should have the same task_checksum. If not → P2
6. **Trajectory prompt drift:** compares the prompt in each run's trajectory.json against the shipped instruction.md. If they differ → "stale evidence after task edit"
7. **Stray verifier.json.* variants:** any `verifier.json.*` files in tests/ → flagged (pre-fairness-edit copies left behind)
8. **Per-trial failure counts from golden_check.json:** if a trial failed ≤5% of checks → near_pass signal → ambiguity flag

**My new check:** Look for golden_check.json, summary.json, stray verifier.json.* variants, and compare README counts to shipped count.

## reward_hacking_audit — the full algorithm (re-confirmed)

Scans every difficulty + solvability run:
- reward 1.0 with failed checks → P0
- reward.txt ≠ result.json reward → P0
- oracle inside difficulty → P0
- identical trajectory.json across runs → P0
- same session_id across runs → P0
- reward 1.0 without trajectory → P1
- reward 1.0 but no write evidence for deliverables → P1
- no grader transcript → P1
- tiny test-stdout.txt (<200 bytes) with no CTRF → P2
- trajectory prompt differs from shipped instruction.md → P1
- golden_trajectory provenance: byte-match against any bundled 1.0 trial → if no match, P2

## derive_deterministic_findings — all P0/P1 checks I must verify

### P0 (blocks: reject)
- task.toml missing/invalid
- Harbor loader rejects directory
- instruction.md missing
- No verifier.json or manifest.json
- Verifier spec not valid JSON
- Dockerfile copies tests/solution/verifier into agent image (golden isolation)
- Root task files differ from environment/_app mirror
- Verifier regex doesn't compile
- Gold deliverables fail shipped checks in local replay (and no bundled Oracle 1.0)
- reward 1.0 but failed checks recorded (reward hacking)
- reward.txt ≠ result.json reward
- Oracle inside difficulty evidence
- Identical trajectory.json across runs
- Same session_id across runs
- Agent and connector gyms share one merged image without isolation

### P1 (blocks: rework)
- Dockerfile base image not pinned by @sha256
- Dockerfile missing
- Hard-coded judge model id
- Gold deliverable byte-identical to input file (answer key shipped)
- Memo regex enforces token order (word_order_replay fails)
- Instruction lists JSON keys no check grades (Missing)
- JSON keys graded that prompt never names (Extra)
- Memo checks require heading the prompt doesn't state
- Checks read deliverable paths the prompt never names
- LLM-judged task with <3 stability repeats
- Difficulty gate fails
- Solvability gate fails
- Stability gate fails
- Stale bundle (runs graded on different grid)
- review.csv worksheet integrity fails
- Bundled GLM/solvability trials not full Harbor copies

## The model prompts — what they check that I must do manually

### Static review (stage 1) — SHANNON_RUBRIC
9 Layer 1 hard checks:
1. JSON types pinned before strict equals
2. Named entities: grader literal must be uniquely identified by the task paragraph
3. Aliases/exact strings must be pinned or both accepted
4. Memo regex may not demand one synonym, token order, or unreachable alternation
5. No hidden process: no trace-only conclusions, tool-call patterns
6. Every instructed deliverable graded; every check has a prompt ask
7. Golden isolation: tests/, answer keys not agent-visible
8. Coding-green/memo-red is not difficulty
9. Structured facts belong on JSON/CSV fields, not prose regex

Plus: prompt gate (soundness Q1-Q4, quality Q5-Q10), 2a checklist from prompt alone, verifier classification (Missing/Extra/Different), brittleness with replays, representation contract, specification ambiguity, coverage depth with counterexamples, 7 audit dimensions, instruction_verifier_consistency.

### Run triage (stage 2) — mandatory subchecks
1. **instruction_verifier_consistency** — does the verifier enforce something the instruction never asked for?
2. **failure_cause_validity** — is every failed rollout used as difficulty evidence agent-owned, not an instruction/verifier/infra defect?

Both must pass or overall verdict is FAIL. Cannot be averaged away.

### The clustered-failure rule (critical)
"When failed runs are near-passes that miss the SAME rows while everything else is right, open the governing policy clauses for exactly those rows and enumerate every defensible reading. If a competent alternative reading yields the agents' values, the failures are a prompt gap, not difficulty."

## New checks I must add to my 7-layer checklist

1. **review.csv count audit:** extract every number cited in review.csv, compare to actual gold/verifier/stability/difficulty
2. **review.csv cited path audit:** every path cited in change_made must exist in the package
3. **golden_check.json/summary.json audit:** if these files exist, their counts must match the shipped verifier
4. **Stray verifier.json.* variants:** check tests/ for verifier.json.* files (pre-fairness-edit copies left behind)
5. **Trajectory prompt drift:** compare the prompt in each run's trajectory to the shipped instruction.md
6. **README count audit:** extract numbers from README and compare to shipped check_count
7. **task_checksum consistency:** all runs must have the same checksum

## Additional checks from deep research (round 2)

### dockerfile_info — exposed grader paths
The engine scans every `COPY`/`ADD` line in the Dockerfile for sources matching `tests/`, `solution/`, `verifier.json`, `manifest.json`, `golden`, `rubric.toml`, `evaluations`. Also checks destinations matching `/tests/`, `verifier.json`, `manifest.json`. If found → P0 "golden isolation" finding.

**My check:** `grep -E 'COPY|ADD' Dockerfile | grep -E 'tests|solution|verifier|manifest|golden|rubric'`

### trajectory_digest — prompt_matches_instruction
The engine compares the user prompt in each run's trajectory.json against the shipped instruction.md using `difflib.SequenceMatcher` with a 0.98 ratio threshold. If they don't match → "trajectory prompt differs from shipped instruction.md (stale evidence after task edit)" → P1.

**My check:** Read trajectory.json's first user message, compare to instruction.md. If different → stale evidence.

### trajectory_digest — deliverables_missing_write_evidence
The engine scans every tool call in the trajectory for write operations matching deliverable names. If a deliverable was never written → "reward 1.0 but trajectory shows no write evidence for [deliverable]" → P1.

**My check:** For each deliverable, grep the trajectory for write operations (write, edit, bash with >, cat >, json.dump, to_csv). If a deliverable that was "graded" was never written → reward hacking signal.

### trajectory_digest — length_stop_signal
The engine checks for `"finish_reason": "length"` or `"stop_reason": "length"` in the raw trajectory. If found → token_cap signal → failure_layer = token_cap, not model_fault.

**My check:** `grep -E 'finish_reason.*length|stop_reason.*length' trajectory.json`

### trial_record — near_pass detection
A run is "near_pass" if reward < 1.0 AND failed_count == 1 AND graded_count >= 10. If the CTRF report is collapsed (first_failure_only), near_pass is set to False (unknown). When ALL failed runs are near-pass → specification-ambiguity signal → P2.

**My check:** For each failing run, count how many checks failed. If exactly 1 out of ≥10 → near-pass. If all failed runs are near-pass → ambiguity.

### trial_record — host_paths_in
The engine scans result.json, config.json, and lock.json for `/Users/[A-Za-z]`, `C:\\Users\\`, `/home/[a-z]`. If found → P2 "host home paths not anonymized" (QC R7).

**My check:** `grep -rE '/Users/[A-Za-z]|C:\\Users|/home/[a-z]' evaluations/*/result.json evaluations/*/config.json evaluations/*/lock.json`

### packaging_checklist — full list (20+ checks)
1. instruction.md present
2. task.toml parses
3. environment/Dockerfile present
4. Dockerfile FROM pinned by @sha256
5. task-root README.md present (not stub)
6. tests/verifier.json present (not manifest.json)
7. tests/test.sh present
8. no __pycache__/.pytest_cache/.DS_Store/qc/ in task tree
9. solution/golden_trajectory.json present
10. solution/solve.sh present
11. no solution/tests/ (graders at task-root tests/)
12. evaluations/difficulty/r1..rN with 4-5 GLM trials
13. GLM/solvability trials are full Harbor copies (agent/, reward, transcript)
14. evaluations/solvability/r1 = one full model trial at 1.0
15. evaluations/stability/repeat-01..NN each 1.0 (≥3, recommended 5)
16. evaluations/oracle reward 1.0
17. bundled runs graded against shipped verifier grid
18. task_checksum consistent
19. golden_check.json/summary.json/README counts match
20. stray verifier variants under tests/
21. host home paths anonymized
22. review.csv worksheet integrity
23. environment/_app mirror matches root (if exists)
24. Dockerfile doesn't copy graders/solution into image
25. no sibling qc/ or glm-5x-* dirs inside extract wrapper
26. no qc/ or qc-out/ inside task tree

### validate_static_review — what the model MUST return
The static review must return ALL of:
- `prompt_gate` with `soundness` (q1-q4) and `quality` (q5-q10) and a `verdict`
- `layer1_hard_checks` with 9 named checks (json_types_pinned, named_entity_unique_no_extra, alias_exact_string, memo_regex_not_word_order, no_hidden_process, instructed_graded_no_extra, scope_complete_coverage, golden_isolation_solution_match, structured_facts_not_prose_regex)
- `checklist_2a` — a non-empty list of checks the reviewer would run from the prompt alone
- `verifier_classification` with `missing`, `extra`, `different` arrays
- `whole_set_2c` — covers_everything, checks_nothing_unasked, passes_good_fails_bad, deterministic
- `brittleness_findings` — per regex family with replay tests
- `representation_contract` verdict
- `specification_ambiguity` — clauses with multiple readings
- `coverage_depth` — structural, semantic, cross_artifact
- `audit_dimensions` — 7 dimensions (clarity_and_disclosure, requirement_coverage, verifier_fairness, brittleness, scoring_integrity, format_and_schema_enforcement, static_exploitability)
- `instruction_verifier_consistency` verdict
- `issues` — ≤10 with severity, label, owner, blocks, evidence
- `for_the_author` and `minimal_fix`
- `scope` — exactly `{"saved_runs_reviewed": 0, "oracle_status": "NOT_AN_ORACLE_RUN", "runtime_claims": "NOT_ASSESSED"}`

### validate_runs_review — what the model MUST return
- `mandatory_subchecks` with `instruction_verifier_consistency` and `failure_cause_validity` (both must pass or FAIL)
- `run_behavioral_assessment` — one per run with ownership, failure_layer, triage_sentence, failed_checks, explicit_vs_derived, near_pass, quality_label
- `cross_run_analysis` with shared_failure_patterns, verifier_behavior, false_positive/negative_risks, reward_hacking_signals, which_traps_fired, difficulty_validity, calibration_profile
- `raw_difficulty_gate` with strict_passes and total_runs (enforced — model cannot change these)
- `reward_hacking_audit` verdict
- `solvability_assessment`
- `secondary_issues` (≤8)
- The model CANNOT change observed rewards, strict_pass status, or counts

### The 9 Layer 1 hard checks (from SHANNON_RUBRIC)
1. JSON types pinned before strict equals when key name is ambiguous (NOT for *_count, *_total, is_*)
2. Named entities: grader literal must be uniquely identified by the task paragraph
3. Aliases/exact strings must be pinned or both accepted (Option A vs A, Sheet1 vs first sheet)
4. Memo regex may not demand one synonym, token order, or unreachable alternation
5. No hidden process: no trace-only conclusions, tool-call patterns, or markers only in task.toml
6. Every instructed deliverable graded; every check has a prompt ask
7. Golden isolation: tests/, answer keys not agent-visible
8. Coding-green/memo-red is not difficulty: zeros that fail only type/alias/Extra name/memo regex are task faults
9. Structured facts (counts, ids, dates, amounts, booleans) belong on JSON/CSV fields, not prose regex

### The 7 audit dimensions (from STATIC_SCHEMA)
1. `clarity_and_disclosure` — is the prompt clear and complete?
2. `requirement_coverage` — does the verifier cover every ask?
3. `verifier_fairness` — does the verifier grade the work, not the wording?
4. `brittleness` — does the regex reject correct alternatives?
5. `scoring_integrity` — is the reward aggregation sound?
6. `format_and_schema_enforcement` — are formats pinned correctly?
7. `static_exploitability` — can the agent cheat?

### The clustered-failure rule (critical for failure_cause_validity)
"When failed runs are near-passes that miss the SAME rows while everything else is right, open the governing policy clauses for exactly those rows and enumerate every defensible reading. If a competent alternative reading yields the agents' values, the failures are a prompt gap, not difficulty."

This means: if all 4 GLM runs fail on the same 2-3 rows, and those rows are ones where the gold is debatable → failure_cause_validity = NEEDS_REVIEW or INVALID, even if the gold's reading is also defensible. Only label "model_fault" after quoting the clause that makes the agents' reading indefensible.
