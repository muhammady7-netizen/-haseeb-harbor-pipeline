# law-b39-l16 Task — Current State (18 Sept 2026)

## Portal Status: READY FOR QC UPLOAD

**Oracle:** 4/4 @ 1.0 (local v6c)  
**GLM-5.2:** **0/4** (in band — excellent difficulty)  
**Gold:** 100/181/44/202 · 325 rows · trajectories synced  

## Zip
`C:\Users\Haseeb Mirza\Downloads\law-b39-l16-custody-letter-instruction-audit.zip`

## Notes
- `/tests` chmod lock removed (Harbor verifier runs as appuser — 000/700 blocked grading)
- solve.sh/test.sh converted to LF
- Content findings 1–16 closed per Shannon PASS

## 2026-09-18 evening push
- RP-407 gold: ST-137/138/139 use OI-210/206/207; results 100/168/57/149; answer_prose_floor domain keyword fixed.
- c227 synced under task-sources/code-c227 (score.py 76-check grid; Harbor oracle 4x1.0; GLM terminus-2 mean 0.94, 0/4 at 1.0).
- Not uploaded to QC from this zip; pushing GitHub for other PC/QC track.

## 2026-09-18 RP-407 protocol restore (pushed)
Correct gold from Harbor-validated pack: **104 / 177 / 44 / 162**. ST-137/138/139 = OI-210/206/207. Oracle 4x1.0, GLM 2/4 (1.0/1.0/0/0). Zip: Downloads/law-b39-l16-custody-letter-instruction-audit-v5-rp407-protocol.zip. Earlier GitHub push had overwritten 100/168/57/149 — restored.
