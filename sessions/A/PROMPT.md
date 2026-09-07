# Session A — START HERE

Paste this whole file into a new Cursor chat, or say: **chat A** / **access session A**

## Tasks (only these)
gen-g1205, fin-f39, the-thread

- gen-g1205 (NONC-B1-1002016)
- fin-f39 (NONC-B1-1000070)
- the-thread (CONNECTOR-THREAD)

## You MUST use repo automation (do not invent scripts)

Repo: https://github.com/muhammady7-netizen/-haseeb-harbor-pipeline

### Bootstrap (you run)
```powershell
$repo = "https://github.com/muhammady7-netizen/-haseeb-harbor-pipeline.git"
$dest = Join-Path $HOME "Documents\-haseeb-harbor-pipeline"
if (-not (Test-Path $dest)) { git clone $repo $dest } else { Set-Location $dest; git pull }
Set-Location $dest
if (-not (Test-Path ".\machine.json")) { Copy-Item ".\machine.example.json" ".\machine.json" }
# Fix machine.json paths on this PC if doctor fails
.\resume.ps1 doctor
.\resume.ps1 board
git pull
.\resume.ps1 assign --session A --tasks gen-g1205,fin-f39,the-thread
.\resume.ps1 next --session A
.\resume.ps1 loop --session A
.\resume.ps1 loop --session A --package
```

### Zips for this chat
Folder: `sessions/A/zips/`
Also mirrored in `canonical-zips\`.

### Rules
- Only Session **A** tasks. Do not touch other sessions' locks.
- PreQC → fix source until `preqc_clean` → `package` → `ready_final`.
- No browser automation required unless user says so. When `ready_final`, give zip path + portal checklist; wait for user portal reply; then `set-status`.
- Never **Confirm** portal PreQC (Dismiss / leave unconfirmed).
- Difficulty: ≤2/4 preferred; 3/4 OK; 4/4 densify then loop+package again.
- After progress:
```powershell
git add -A
git -c user.email="muhammad.y7@turing.com" -c user.name="Muhammad Haseeb Younas" commit -m "session A progress"
git push
```

### Portal status helpers
```powershell
.\resume.ps1 portal-status --task <short>
.\resume.ps1 watch-portal --task <short> --phase <phase> --note "..."
.\resume.ps1 set-status --task <short> --status uploaded|final_running|accepted|needs_densify|blocked --note "..."
```

## Start now
`git pull` → doctor → board → assign Session A → loop → package when clean → report board for A.
