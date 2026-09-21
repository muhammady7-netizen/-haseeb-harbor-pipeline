# How to use on another PC

## 1. Get this repo

```powershell
git clone https://github.com/muhammady7-netizen/-haseeb-harbor-pipeline.git
cd -haseeb-harbor-pipeline
copy machine.example.json machine.json
```

Edit `machine.json` paths for that PC (PreQC script, Harbor setup, Downloads).

## 2. What the zips are for

Folder `canonical-zips\` = ready **upload** packs for V2 trainer.

- Other PC, upload-only: use `canonical-zips\UPLOAD-THIS-TO-QC-<short>.zip`
- To **fix PreQC findings**: you also need the **task source folder** (with `task.toml`). Zips alone are not enough to edit.

## 3. Run automation

```powershell
.\resume.ps1 doctor
.\resume.ps1 board
.\resume.ps1 assign --session A --tasks gen-g1205,fin-f39,the-thread
.\resume.ps1 loop --session A --package
```

Flow: PreQC → fix source → PreQC again → `package` → `ready_final` → upload zip from `canonical-zips` or new package → Dismiss portal PreQC → final QC → mark status in registry → `git push`.

## 4. Sync between PCs

Before leaving a PC: update `registry.json`, commit, push.  
On the other: `git pull`, then `.\resume.ps1 board`.
