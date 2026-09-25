# QC Self-Training — 9 Findings (gen-g806, Sep 22, 2026)

**Lesson date:** 2026-09-22
**Task:** gen-g806-leadership-brief-rhetorical-style-audit
**My verdict:** "Ship it" after multiple PreQC passes
**Portal verdict:** "Rework" — 7 blocker findings from QC-Oracle-GLM

### FINDING 1 — Gold contradicts disclosed errata (ambiguous_rule_contested_gold)
**Portal ID:** layer1_realism_leakage__domain_correctness
**What:** band_definition.csv has last active row standard=4-7, but gold had SC-30/34/50 as `none` (not RUNTIME_OUT_OF_BAND). The gold contradicted the errata v4 last-wins rule.
**Why I missed it:** I never independently verified that the gold follows the disclosed errata rules. I trusted the gold because it passed the verifier grid.
**The check I must run:** For each gold finding, verify it can be derived from the disclosed rules. Especially for band boundary cases where last-wins changes the bounds.
**Detection:** Compute the expected finding from the rules and compare to gold. Any mismatch = gold defect.

### FINDING 2 — Internal inconsistency in gold (SC-96 vs SC-30)
**Portal ID:** layer2_difficulty__failure_cause_validity
**What:** SC-96 (standard, effective=8) was gold RUNTIME_OUT_OF_BAND but SC-30 (standard, effective=8) was gold `none`. Same band, same effective minutes, opposite findings.
**Why I missed it:** I never checked for internal consistency across scripts with the same band and effective minutes.
**The check I must run:** Group scripts by (band, effective_minutes). Any group with mixed findings = internal inconsistency.

### FINDING 3 — 0/4 is fake difficulty (gold defect, not model failure)
**Portal ID:** layer2_difficulty__failure_cause_validity
**What:** All 4 GLM runs correctly applied the errata last-wins rule and got SC-30/34/50 as RUNTIME_OUT_OF_BAND. The gold said `none`. The model was RIGHT and was penalized.
**Why I missed it:** I saw 0/4 and called it difficulty without checking WHICH scripts failed and whether the gold was correct for those scripts.
**The check I must run:** List which scripts GLM got wrong. Check if the gold is correct for those scripts. If the gold is wrong, 0/4 is fake difficulty.

### FINDING 4 — Empty memo passes (memo_exists only, no content check)
**Portal ID:** layer5_verifier_fairness_static__coverage_depth
**What:** Only `memo_exists` (check_path_exists) graded the memo. A 0-byte memo gets reward 1.0. The instruction requires 800+ chars and per-finding explanations.
**Why I missed it:** I removed memo content checks to avoid "reward-hackable regex" findings, but went too far — removing ALL content checks.
**The check I must run:** Verify that a 0-byte memo fails at least one check. If not, coverage depth is insufficient.

### FINDING 5 — CRLF in zip files
**Portal ID:** JUDGE-001
**What:** Windows Python writes CRLF (\r\n) to files. The Harbor portal crashes on CRLF.
**Why I missed it:** I converted files to LF but the Python json.dumps/csv.writer re-introduced CRLF on Windows.
**The check I must run:** After building the zip, check EVERY file for \r\n. Use `zf.writestr(name, data.replace(b'\r\n', b'\n'))` during zip write, not just before.

### FINDING 6 — task.toml artifacts must be absolute paths
**Portal ID:** QC1-2
**What:** `artifacts = ["script_style_audit.csv", ...]` — relative paths. Must be `"/app/script_style_audit.csv"`.
**Why I missed it:** I used relative paths because the task.toml schema examples showed relative. The portal requires absolute container paths.
**The check I must run:** Verify all artifacts in task.toml start with `/app/`.

### FINDING 7 — Dockerfile USER directive is platform-dependent
**Portal ID:** QC1-5 + LINT-002
**What:** Platform PreQC says "Keep as root" (remove USER app). Local QC says "Add non-root USER" (add USER app). Contradictory requirements.
**Why I missed it:** I didn't check which requirement applies. The platform PreQC is the authority.
**The check I must run:** Follow the platform PreQC guidance. If it says remove USER, remove it. If it says add USER, add it. Don't trust local QC for Dockerfile USER.

### FINDING 8 — review.csv counts must match gold exactly
**Portal ID:** JUDGE-001
**What:** review.csv mentioned "99" (verifier count) but the judge compared it against gold script_count=73. Any number in review.csv is checked against gold values.
**Why I missed it:** I put verifier counts in review.csv that don't match gold counts.
**The check I must run:** Only mention gold values in review.csv. Don't mention verifier counts, script counts from inventory, or any number that isn't in results.json.

### FINDING 9 — Prose regex on .md files is always flagged
**Portal ID:** QC1-1, QC1-2, QC1-3 (repeated across versions)
**What:** ANY regex_match on a .md file triggers "Prose deliverable graded by reward-hackable regex". Even length checks, even proximity checks with content words.
**Why I missed it:** I kept trying to make the regex "fair enough" but the platform blocks ALL regex on prose.
**The check I must run:** Don't use regex_match on .md files AT ALL. Use filesystem.check_path_exists only. Let the platform's GLM review grade memo content.
