# Session E — START HERE

Paste this whole file into a new Cursor chat, or say: **chat E** / **access session E**

## Tasks (only these)
fin-f55, health-h34, health-h40

- fin-f55 (NONC-B1-1000793)
- health-h34 (NONC-B1-1000145)
- health-h40 (NONC-B1-1000151)

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
.\resume.ps1 assign --session E --tasks fin-f55,health-h34,health-h40
.\resume.ps1 next --session E
.\resume.ps1 loop --session E
.\resume.ps1 loop --session E --package
```

### Zips for this chat
Folder: `sessions/E/zips/`
Also mirrored in `canonical-zips\`.

### Rules
- Only Session **E** tasks. Do not touch other sessions' locks.
- PreQC → fix source until `preqc_clean` → `package` → `ready_final`.
- No browser automation required unless user says so. When `ready_final`, give zip path + portal checklist; wait for user portal reply; then `set-status`.
- Never **Confirm** portal PreQC (Dismiss / leave unconfirmed).
- Difficulty: ≤2/4 preferred; 3/4 OK; 4/4 densify then loop+package again.
- After progress:
```powershell
git add -A
git -c user.email="muhammad.y7@turing.com" -c user.name="Muhammad Haseeb Younas" commit -m "session E progress"
git push
```

### Portal status helpers
```powershell
.\resume.ps1 portal-status --task <short>
.\resume.ps1 watch-portal --task <short> --phase <phase> --note "..."
.\resume.ps1 set-status --task <short> --status uploaded|final_running|accepted|needs_densify|blocked --note "..."
```

## Start now
`git pull` → doctor → board → assign Session E → loop → package when clean → report board for E.
