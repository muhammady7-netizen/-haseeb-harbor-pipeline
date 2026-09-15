# Shannon Trainer Workflow — Complete Guide

## Overview
The Shannon trainer workflow has 6 steps:
1. Claim a Task
2. Trainer Guides (reference docs)
3. Upload Completed Task (Google Drive)
4. Generate review.csv (Review CSV Generator Tool)
5. QC Tool — Final Check (Shannon QC Control)
6. Report Bugs / Issues (Harbour QC Parking Lot)

---

## Step 5: QC Tool — Final Check (Shannon QC Control)

Upload your task in the QC tool and check performance. If it passes — done. If not — improve the task and re-check.

### Two QC Tools Available

| Tool | URL | Notes |
|------|-----|-------|
| QC Tool V2 (recommended) | https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer | Recommended first |
| QC Tool V1 | https://qc-api-713053229214.us-central1.run.app/ | Still available if needed |

### QC Workflow
1. Open Shannon QC Control V2 first (recommended). V1 is still available if needed.
2. Upload / submit your completed task (.zip).
3. Review the result: All Pass = good; Any Fail = fix and improve the task.
4. Re-run QC after improvements until it all passes.

### QC Gates (in order)
1. **Client PreQC** (Internal Gate, advisory but now mandatory) — GLM-5.2 reviews instruction and verifier source. Required before GLM runs. Does not consume evaluation slots.
2. **QC-Oracle-GLM** (3-task limit) — Oracle golden replay + four GLM-5.2 difficulty runs + Harbor Check. Takes ~50 minutes.
3. **Submit to pipeline** — Only when all findings resolved.

### PreQC is Mandatory
From the team: "To help our pipeline run smoother and avoid resource bottlenecks during the finalisation phase, we are making the Pre-QC step mandatory. Running these simple checks upfront catches a lot of avoidable issues early on. From now on, please ensure you are fixing all Pre-QC issues before your GLM runs."

If you feel the Pre-QC is flagging a false positive, report it in the Pre QC False Positives sheet and ping your pod lead for a review.

### What the QC Checks
The QC tool runs the `verifier_defect_lint.py` script (deterministic linter) which checks:
- **D1**: prose_regex_grading — prose/memo graded by reward-hackable regex
- **D2**: root_container — container runs as root (no non-root USER)
- **D3**: judge_model_wiring — judge model placeholder or hard-pinned
- **D4**: fixture_overwritable — grading fixture reachable from agent-writable path
- **D5**: inert_scoring_axis — scoring weight for an axis that cannot score

Note: D1-D5 are currently advisory-only (BLOCKING_CHECK_IDS = set()), but PreQC findings must be fixed.

### Reading QC Results
After QC-Oracle-GLM completes:
- **Oracle Passed** = the golden answer passes all verifiers (grading is sound)
- **GLM 0/4 passed** = excellent difficulty (task is hard enough)
- **GLM 1/4 passed** = good difficulty
- **GLM 2/4 passed** = acceptable difficulty
- **GLM 3/4 passed** = borderline — may be too easy
- **GLM 4/4 passed** = TOO_EASY — task will be rejected
- **0 trainer findings** = no issues to fix
- **N trainer findings** = issues to review (confirm as real or dismiss as false positive)

### After QC
- If clean (0 findings, Oracle passed, GLM difficulty good): task is ready for submission
- If findings: fix the source, re-upload, re-run QC
- Never **Confirm** Harbor findings as false positives — fix source, re-upload
- Skip Client PreQC is no longer allowed — PreQC is mandatory

---

## Step 6: Report Bugs / Issues (Harbour QC Parking Lot)

If you hit problems or bugs while using the QC tool (or elsewhere), log them here.

| Tool | URL |
|------|-----|
| Harbour QC Parking Lot V2 | https://script.google.com/a/macros/turing.com/s/AKfycbynPi3chsymglRXlDIlZgrreMLocnN35fHJ90-MC424cuAhkW-p2KMrzvcOLGCkNJJ4uA/exec |
| Harbour QC Parking Lot V1 | https://script.google.com/a/macros/turing.com/s/AKfycbzpJpE_d-lZrg8k7p_mDHEvpLiqKHi_TCBnbAfPf7aKvr0ZPRNfDspVL15elVc-xGab/exec |

### How to Report
1. Open the Harbour QC Parking Lot Tool and specify which QC Tool you're experiencing the issue with.
2. Search / check if your issue is already reported before creating a new one.
3. If the issue is already reported, click the + button on that issue to add your name — avoids duplicates.
4. If the issue is new, add it with clear details, then track its status from the same tool.

---

## Complete Workflow Summary

```
1. Claim Task → Tracker sheet
2. Read Guides → docs/ folder on GitHub
3. Build/Fix Task → instruction.md, verifier.json, solution/, environment/
4. Upload to Google Drive → Batch_no folder
5. Generate review.csv → Review CSV Generator Tool (14 checks)
6. Run PreQC → Shannon QC Control V2 (mandatory before GLM runs)
7. Run QC-Oracle-GLM → Shannon QC Control V2 (~50 min)
8. Fix findings if any → re-upload, re-run QC
9. Submit to pipeline → when all clean
10. Report bugs → Harbour QC Parking Lot
```

### Key URLs
| Resource | URL |
|----------|-----|
| Shannon QC Control V2 | https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer |
| Shannon QC Control V1 | https://qc-api-713053229214.us-central1.run.app/ |
| Review CSV Generator | https://script.google.com/a/macros/turing.com/s/AKfycbzi9BTJ8iVwPCCEGGaiaII9bKUwVl62mxkRpwGDfRYIKphxiDBfO-oF4B3A8Bc9AgYU/exec |
| Google Drive Upload | https://drive.google.com/drive/folders/15ULnjl1MvMNdkqLlz9wLXpxDiZzM1bDW |
| Harbour QC Parking Lot V2 | https://script.google.com/a/macros/turing.com/s/AKfycbynPi3chsymglRXlDIlZgrreMLocnN35fHJ90-MC424cuAhkW-p2KMrzvcOLGCkNJJ4uA/exec |
| Trainer Guide Portal | https://script.google.com/a/macros/turing.com/s/AKfycbxyMRTfRUJcEnm33v7yzgDWpQH8txjoZ1sYiEsk3wFAlDfZVvo5M0lzYz8kLql7CKUymA/exec |
