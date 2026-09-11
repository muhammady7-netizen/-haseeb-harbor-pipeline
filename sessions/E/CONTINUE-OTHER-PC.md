# Session E — continue on other PC

**Task:** health-h40 only (`NONC-B1-1000151`)  
**Do not touch:** fin-f55, health-h34

## Current portal state (as of push)

- **Version:** v20 (amendment harden)
- **Content:** `content-b63f3de295aa53405e9bd793103acffa-v1`
- **URL:** https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-b63f3de295aa53405e9bd793103acffa-v1
- **Short hash:** `#03acffa` (last 6 of content id)
- **Status:** `final_running` — Oracle **1.0**, GLM×4 was still running at last poll
- **Zip:** `canonical-zips/UPLOAD-THIS-TO-QC-health-h40.zip` and `sessions/E/zips/` (98018 bytes)

## Pack restore (qc-out is gitignored)

```powershell
$dest = "qc-out\ework\UPLOAD-THIS-TO-QC-health-h40"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Expand-Archive -Path "canonical-zips\UPLOAD-THIS-TO-QC-health-h40.zip" -DestinationPath $dest -Force
```

## Headless track (skip PreQC; Final QC only)

```powershell
# Dedicated profile if shared chrome-profile is locked:
# C:\Users\<you>\.config\opencode\chrome-profile-e-h40
node tmp-pw-h40-v20-run.js
# or strict poller after you know the content hash:
# edit SHORT/CONTENT in tmp-pw-h40-v15-track.js pattern → v20
```

## Recent version outcomes (do not re-upload these)

| Ver | Result |
|-----|--------|
| v14–v17 | TOO_EASY 4/4 (row spam / despoil insufficient) |
| v18 | **GLM 3/4** but Harbor FAIL (unfair memo ID gates + stale README/trajectory/review) |
| v19 | Harbor fairness fixed → **TOO_EASY 4/4** again (r2 only failed on those gates) |
| v20 | Amendment + R-123..134; Final QC in flight at push time |

## If v20 settles

- **TOO_EASY 4/4** → densify harder on **audit CSV** failures (not memo ID lists); keep Harbor-fair concept memo checks
- **≤3/4 + Harbor FAIL** → fix findings in source (confirm real issues); rebuild zip; re-upload Final QC only
- **≤3/4 + Harbor clean / READY** → disposition true FPs only; Submit; `accepted`

## Rebuild zip after pack edits

```powershell
python tmp-h40-rebuild-zip.py
# mirrors to Downloads, sessions/E/zips, canonical-zips
```
