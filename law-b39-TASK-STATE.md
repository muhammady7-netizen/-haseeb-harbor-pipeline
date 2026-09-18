# law-b39-l16 Task — Current State (18 Sept 2026)

## Summary

Fixed all original portal findings and iterated through multiple versions to achieve:
- Oracle Passed 1.0
- GLM 1/4 passed (excellent difficulty)
- PreQC 0 findings
- D1-D5 clean
- Harbor Check running (no findings so far)

## Versions Uploaded

| Version | PreQC | Oracle | GLM | Harbor Check | Status |
|---------|-------|--------|-----|-------------|--------|
| v1 (old content) | D18 finding | - | - | - | JSON broken |
| v1 (new) | 0 findings | - | - | - | - |
| v2 (new) | 0 findings | Passed | 2/4 | 4 findings | Fix needed |
| v3 (new) | 0 findings | Passed | 3/4 | 2 findings | Fix needed |
| v4 (new) | 0 findings | Passed | 3/4 | 2 findings (submission_format) | Fix needed |
| **v5 (current)** | **0 findings** | **Passed** | **1/4** | **Running** | **Waiting** |

## Fixes Applied

1. **RP-404**: Clarified that nonexistent cited_entry doesn't make NOT_IN_RECORD if subject is covered
2. **RP-407**: Cross-subject citation exception (OI governs when cited_entry is CL for different subject)
3. **RP-408**: Compound positions rule (dropping a limb = narrower = AT_ODDS)
4. **Regex boundary**: `(?!\d)` → `(?!\d|[.,]\d)` in answer_at_odds_figure
5. **Prose floor**: 1 lookahead + 100 words (D1 clean)
6. **submission_format.md**: Removed domain keyword requirement (matched verifier)
7. **31 gold rows**: Fixed for RP-407 consistency (record_entry CL→OI)
8. **JSON paths**: All Windows backslash paths anonymized to /workspace
9. **review.csv**: Proper QUOTE_MINIMAL quoting, correct header
10. **325 rows, 104/177/44/162** gold counts
11. **20 new rows** (CL-310/311 conditional exceptions + RP-407 trap rows)
