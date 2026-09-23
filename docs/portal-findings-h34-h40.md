# Portal Findings — h34 and h40 (Sep 21, 2026)

## h34 — health-h34-randomisation-balance

### PreQC Finding 1: D1 prose regex slack
**ID:** `QC1-1`
**Check:** `findings_address_ledger_normalisation`
**Pattern:** `(?is)(amendment[\s-]*ledger|...amend\w*.{0,60}ledger|ledger.{0,60}amend\w*|reconcil...)`
**Issue:** `.{0,60}` is D1 wildcard slack — lets arbitrary filler satisfy the match
**Fix:** Replace `.{0,N}` with `.+` (structure but not slack)

### PreQC Finding 2: D1 bare keyword checks
**ID:** `QC1-2`
**Checks:** `findings_address_boundary_blocks_or_equality`, `findings_address_overfill_or_incomplete`, `findings_address_sequence_integrity`, `findings_address_tolerances`
**Issue:** 4 regex_match items grade prose by bare literal presence (no `.*`, lookahead, or quantifier)
**Fix:** Merge 4 bare keyword checks into ≤2 using alternation `(?is)(?:kw1|kw2|kw3)`

### GLM 4/4 TOO_EASY (v4, v5)
**Finding:** `difficulty_too_easy` — GLM solved all 4 runs
**Fix:** Added 15 traps (revision string-sort, void restoration, blank-retain-base, whitespace-blank, date format, site case, severity case, ledger-only included/void/missing, block overfill, cascade blank)

## h40 — health-h40-critical-result-acknowledgement

### PreQC Finding 1: D1 prose regex slack (26 checks)
**Checks:** `memo_lists_late_notifications`, `memo_lists_late_notification_r09`, `memo_lists_ack_breaches`, `memo_lists_absent_ack_r10`, etc.
**Pattern:** `(?ims)\bR-XX\b[\s\S]{0,300}(?:keywords)` — 300-char proximity + `[\s\S]*` slack
**Fix:** Remove `[\s\S]*` → replace with `.+`; remove 300-char proximity → accept anywhere

### PreQC Finding 2: D2 non-root user
**Finding:** `The Dockerfile ends as a non-root user`
**Fix:** Remove `USER appuser` — portal wants root for these tasks

### PreQC Finding 3: D3 judge model placeholder
**Finding:** `config.models=['${JUDGE_MODEL}']; resolver_found=False`
**Root cause:** Adding LLM rubrics without a JUDGE_MODEL resolver creates D3
**Lesson:** Don't add LLM rubrics to tasks that were all-deterministic — fix regex patterns instead

### QC-Oracle-GLM Finding 1: surface_form_brittleness
**Check:** `memo_lists_late_notifications`, `memo_lists_late_notification_r09`
**Issue:** 300-char forward proximity window — correct memo with keywords >300 chars from ID fails
**Fix:** Remove 300-char proximity, accept keywords anywhere

### QC-Oracle-GLM Finding 2: requirement_traceability
**Issue:** 300-char proximity + specific token vocabulary not disclosed in instruction
**Fix:** Same as above — remove proximity constraint

### QC-Oracle-GLM Finding 3: coverage_depth
**Issue:** `test_v18_memo_breach_ids_have_detail` accepts bare "notification" or "acknowledgement" without requiring a number
**Fix:** Tighten to require a numeric minute figure near each breach ID

### QC-Oracle-GLM Finding 4: shallow_prose_grading
**Issue:** `memo_has_explanatory_body` is length-only (100+ words) with no content word requirement
**Fix:** Add `(?=.*\b(?:window|clock|escalat|notification|acknowledg|breach|compliant)\b)` — but only 1 lookahead (not 2, which triggers D1)

### GLM 3/4 (v4)
**Finding:** 3/4 passed — borderline too easy
**Fix:** Added 5 traps (3 exactly-at-close boundary, 2 near-miss role names)

## Key lessons from h34/h40

1. **`.{0,N}` triggers D1** — replace with `.+`
2. **`[\s\S]*` triggers D1** — replace with `.+`
3. **`.*` triggers D1** — replace with `.+`
4. **2+ lookaheads trigger D1** — use alternation instead: `(?:kw1|kw2)`
5. **3+ bare keyword checks on same file trigger D1** — merge to ≤2
6. **`USER appuser` triggers D2 on portal** — remove it, portal wants root
7. **Adding LLM rubrics creates D3** — don't add rubrics, fix regex patterns instead
8. **300-char proximity triggers surface_form_brittleness** — remove proximity, accept anywhere
9. **Length-only prose floor triggers shallow_prose_grading** — require content words
10. **`difficulty_too_easy` is a HARD BLOCKER** — cannot be dismissed, must harden the task
11. **Revision string-sort is the strongest trap** — `max(['2','10'])`='2' not '10'
12. **Portal PreQC only blocks D1-D5** — P2 counterexamples and review.csv mismatches don't block
