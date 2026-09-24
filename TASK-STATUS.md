# Task Status — 24 Sept 2026

## bus-b50-b10-streaming-target-variance-attribution

### Current state: TOO_EASY (4/4 GLM passed) — needs redesign

- **PreQC:** PASS (0 findings)
- **Oracle:** PASS (1.0)
- **GLM-5.2 x4:** 4/4 passed (TOO_EASY)
- **Harbor Check:** Not reached (difficulty blocks first)
- **Uploads:** v15 (content-3975ac70), portal content hash 3975ac7058d876c7b98235ec929c1dbc

### What was done
1. Verifier repair: register_header regex-on-CSV -> parsed csv.inspect_table (A2/A2b); 5 memo_* row-order regexes -> order-independent (A4)
2. Source fixes: removed rule 5.6 (time-dependent rate), added rule 3.8 (per-row rounding), fixed CRLF, tightened memo regex patterns
3. Densified: added 10 new trap channels (CH-49 to CH-58), 54 channels total
4. Restored rules 5.6+5.7 and recomputed golden to be consistent — still 4/4

### Root cause
The task is a pure computation exercise. GLM-5.2 correctly follows clearly-stated rules no matter how complex. Three builds confirmed 4/4. Per All Hands guidance: stop after two builds. Needs task redesign or different difficulty approach.

### Zip: canonical-zips/UPLOAD-THIS-TO-QC-bus-b50-v15.zip

---

## gen-g806-leadership-brief-rhetorical-style-audit

### Current state: Review required — 9 blocking findings

- **PreQC:** PASS (0 findings)
- **Oracle:** PASS (1.0)
- **GLM-5.2 x4:** 1/4 passed (good difficulty)
  - Run 1: reward 1.0 (passed)
  - Run 2: reward 0.997
  - Run 3: reward 0.998
  - Run 4: reward 0.997
- **Harbor Check:** FAIL — 9 blocking findings
- **Upload:** v15 (content-14c9f7cc360ba6f6a411f5c3914cb27e), portal evaluation-4892f3e169c24eae

### 9 blocking findings
1. layer1_package_consistency__declared_executed_verifier_consistency
2. layer1_package_consistency__instruction_verifier_consistency
3. layer1_realism_leakage__domain_correctness
4. layer1_realism_leakage__golden_isolation
5. layer5_verifier_fairness_static (general)
6. layer5_verifier_fairness_static__coverage_depth
7. layer5_verifier_fairness_static__requirement_traceability
8. layer5_verifier_fairness_static__semantic_equivalence
9. layer5_verifier_fairness_static__surface_form_brittleness

### What was fixed from v13 (7 findings)
1. Errata priority: swapped RUNTIME_OUT_OF_BAND and UNCITED_SCRIPTURE_REF to match gold
2. Deleted stale golden_results.json (wrong counts)
3. Regenerated golden_trajectory.json to match current instruction
4. Updated README.md (84 -> 2022 scripts)
5. Added memo_min_length check (800 chars) — then removed (PreQC blocks regex on .md)
6. Changed memo_discusses_third_party to accept "third-party testimony" (hyphen)
7. Added required memo tokens + script count + SC-NN casing to instruction.md
8. Fixed CRLF in all .sh files

### Next steps for g806
- Read the 9 new Harbor Check findings in detail
- Fix each one (likely similar issues: errata priority still wrong, memo checks still shallow, etc.)
- Re-upload as v16, re-run Oracle+GLM
- If clean: submit to pipeline

### Zip: canonical-zips/UPLOAD-THIS-TO-QC-gen-g806-v15.zip

---

## Portal URLs
- g806 v15: https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-14c9f7cc360ba6f6a411f5c3914cb27e-v1
- g806 v13 (previous): https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-e53704e30c83f3e29fb2506cf189a555-v13
- bus-b50 v15: https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-3975ac7058d876c7b98235ec929c1dbc-v1
