# Session C — START HERE

Paste this whole file into a new Cursor chat, or say: **chat C** / **access session C**

## Lock
**gen-g806 ONLY** (`NONC-B1-1001634`). g734/g986 released — do not work them here.

## Cross-PC handoff (read first)
→ **`sessions/C/CONTINUE-OTHER-PC.md`**

Pack snapshot: `sessions/C/source-pack/`  
Zip (when packaged): `sessions/C/zips/` + `canonical-zips/UPLOAD-THIS-TO-QC-gen-g806.zip`

## Bootstrap
```powershell
$repo = "https://github.com/muhammady7-netizen/-haseeb-harbor-pipeline.git"
$dest = Join-Path $HOME "Documents\-haseeb-harbor-pipeline"
if (-not (Test-Path $dest)) { git clone $repo $dest } else { Set-Location $dest; git pull }
Set-Location $dest
.\resume.ps1 doctor
.\resume.ps1 board
# Follow CONTINUE-OTHER-PC.md — finish glm-g806-v4b-2..4, stage, package, upload v4
```

## Rules
- Never **Confirm** Harbor findings as false positives — fix source, re-upload.
- Skip Client PreQC; Final QC only.
- Harbor GLM: run **without** `-a terminus-2` (use config agents[] so model_name sticks).
- After progress: commit + push Session C handoff.

## Start now
`git pull` → open `sessions/C/CONTINUE-OTHER-PC.md` → finish GLM battery → package → upload v4.
