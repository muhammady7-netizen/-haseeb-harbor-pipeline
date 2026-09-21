# Session B — continue on other PC

**Pushed:** after Harbor v3 (c249) / v2 (c227) Delivery Gate. **Do not Confirm any finding.**

## Immediate reality

Both packs fail Harbor because **evaluations/ evidence was packaging-substituted** (gold CSV/results into GLM slots; hand-patched solvability; stale pre-densify trajectories). Source verifiers may be OK; **Layer-2/4/5 fail until fresh real Harbor runs**.

| Task | Portal | Core blockers |
|------|--------|----------------|
| **code-c249** | v3 Review required (16 findings) | Need **fresh GLM×4 on shipped densified pack** (agent’s own artifacts, full pytest -rA/ctrf). **Real solvability 1.0** (no RUN-38 sentence graft / gold CSV). **3 distinct oracle trials** (repeat-02 ≠ oracle). Memo must match audit totals. Fix input spoofing (`_input_log_path` digest / non-root). Sync README 61→92. |
| **code-c227** | v2 Review required (21 findings) | Fix **README + gold memo** stale “40 tables / 27 flagged / 166 checks” → **41 / 28 / 170**. **Remove/replace fake GLM+solvability**; run **fresh Harbor GLM×4 + oracle×3** on T-45 pack; pack **agent’s real artifacts** only. Align all reward.txt/result.json/ctrf. |

## Upload zips (current, still need rebuild after fixes)

- `canonical-zips/UPLOAD-THIS-TO-QC-code-c227.zip`
- `canonical-zips/UPLOAD-THIS-TO-QC-code-c249.zip`

Also under `sessions/B/zips/`.

## Source packs (edit these — not inside this git repo)

```
.../tasks/code-c227-work/code-c227-table-bloat-maintenance-audit
.../tasks/code-c249-work/code-c249-recurring-report-source-selection-audit
```

Point `registry.json` `pack_path` / `work_root` to these on the other PC. Or unpack the zip into a work folder and retarget registry.

## Rules (non-negotiable)

1. **Never Confirm** Harbor findings — fix in source, rebuild zip, re-upload as next version (“Yes, this is vN”).
2. Session B only: **c227 + c249** (not gen-g826).
3. **No gold install / memo graft / trajectory reuse** for solvability or difficulty.
4. Legitimate difficulty = `harbor job start` GLM×4 → copy trials into `evaluations/glm-5.2/r1–r4` (strip xdg/snapshot), keep agent artifacts + full verifier logs.
5. Solvability = unrepaired agent 1.0 with matching digests, trajectory, and pytest -rA/ctrf.

## Other PC bootstrap

```powershell
git pull
cd -haseeb-harbor-pipeline   # or your clone path
# read this file
.\resume.ps1 board
.\resume.ps1 next --session B
```

GLM key: ensure `OPENAI_API_KEY` is set for harbor (gateway `http://34.41.10.8:4000/v1`). Job templates under `tmp-pw/glm-job-c249-v8.json` / prior c227 jobs — use `{env:OPENAI_API_KEY}`, never empty apiKey.

## After fixes

Rebuild both zips → Downloads + `canonical-zips` + `sessions/B/zips` → upload → update `registry.json` → **git push** again before leaving the PC.
