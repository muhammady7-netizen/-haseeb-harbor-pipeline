# Session C — continue on other PC (gen-g806 ONLY)

**Lock:** Chat C = `gen-g806` / `NONC-B1-1001634` only. Do not touch g734/g986.

## Portal now
- Task: `obi/gen-g806-leadership-brief-rhetorical-style-audit`
- Latest uploaded: **v3** (Review required — 7 findings). **Never Confirm as FP.** Fix + re-upload.
- Family: `content-58a3a86e…`

## What Harbor still rejects (v3)
1. **r1 difficulty invalid** — old r1 was max_tokens harness abort, not task failure. Need 4 real GLM attempts.
2. **Artifact export** — relative `task.toml artifacts` docker-cp failed; pane dumps had `root@` contamination + offline rescore vs 131-check `reward_meta`.
3. **Reward provenance** — must ship **in-trial** `reward.txt` + `reward_meta.txt` + `test-stdout` for the **83-check** verifier (no post-hoc rewrite).

## Fixes already in pack source (synced under `sessions/C/source-pack/`)
- `artifacts = []` in `task.toml` (stop broken relative docker cp).
- `tests/test.sh` copies graded `/app/*` → `/logs/artifacts/app/` (Harbor exports under `trial/artifacts/logs/artifacts/app/`).
- Verifier **83** fair checks; memo + `question_count=6` disclosed; symmetric omits; no double-counts.
- `review.csv` fully quoted; every row has non-empty `change_made`.
- Packager: `build_qc_bundle.py` at work_root — jobs `oracle-g806-v4` + `oracle-g806-v4-s{1,2,3}` + `glm-g806-v4b-{1..4}`; never gold-fill GLM snapshots; prefer `/logs/artifacts/app`.

## Harbor jobs status (this PC at handoff)
| Job | Reward | Notes |
|-----|--------|-------|
| oracle-g806-v4 | 1.0 | artifacts under `artifacts/logs/artifacts/app/` ✅ |
| oracle-g806-v4-s1/s2/s3 | 1.0 each | 3 distinct stability ✅ |
| glm-g806-v4b-1 | **1.0** | META `passed=83 failed=0 total=83` ✅ clean export |
| glm-g806-v4b-2 | **running / pending** | continue or re-run |
| glm-g806-v4b-3 | pending | |
| glm-g806-v4b-4 | pending | |

**Do not use** old `glm-g806-coherence-*` (pane contamination + 131-check meta mismatch).

## On other PC — do this
```powershell
cd $HOME\Documents\-haseeb-harbor-pipeline   # or your clone path
git pull

# Restore pack from repo snapshot if local Codex tree missing:
$src = ".\sessions\C\source-pack\gen-g806-leadership-brief-rhetorical-style-audit"
$work = ".\sessions\C\work\NONC-B1-1001634"
New-Item -ItemType Directory -Force $work | Out-Null
Copy-Item -Recurse -Force $src "$work\gen-g806-leadership-brief-rhetorical-style-audit"
Copy-Item -Force ".\sessions\C\source-pack\build_qc_bundle.py" $work
Copy-Item -Force ".\sessions\C\source-pack\glm-harbor-config.json" $work
Copy-Item -Force ".\sessions\C\source-pack\oracle-harbor-config.json" $work
# Edit paths inside those JSON/py files to THIS machine's $work absolute path.

. 'C:\Users\Haseeb Mirza\Documents\Codex\Tools\TuringHarbor\setup-session.ps1'  # or your Tools path
$Harbor = (Get-Command harbor -EA SilentlyContinue).Source
# Prefer: harbor run WITHOUT -a so config agents[] keep model_name
#   harbor run -c glm-harbor-config.json --job-name glm-g806-v4b-2 -n 1 -k 1 -y --force-build
```

### Finish GLM×4 then package
1. Ensure `glm-g806-v4b-1..4` each have `reward.txt` + matching `reward_meta.txt` (`total=83`) + clean CSVs under `artifacts/logs/artifacts/app/` (no `root@` in file text).
2. `python sessions/C/source-pack/tmp-stage-g806-v4.py` (after fixing JOBS path) — stages clean manifests.
3. `$env:USE_LOCAL_CHECKSUM='1'; python build_qc_bundle.py` from work_root.
4. Copy zip → `Downloads\UPLOAD-THIS-TO-QC-gen-g806.zip` and `sessions/C/zips/` + `canonical-zips/`.
5. Update `review.csv` Difficulty/Solvability/Deliverables to describe **v4b** real failures only (no “r1 timeout”).
6. Upload **v4** → Final QC only → Confirm none → Accept only if clean.

### GLM config tip
`glm-harbor-config.json` must include terminus-2 `model_name` + `llm_call_kwargs.max_tokens=16384`. **Never** pass bare `-a terminus-2` (drops model_name → crash).

## Rules
- Never dismiss Harbor findings.
- Skip Client PreQC; Final QC only.
- Session C locked to g806.
