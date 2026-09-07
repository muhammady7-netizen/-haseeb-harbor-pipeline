# Take to other PC

## Minimum (no big zips)

1. This repo: `haseeb-harbor-pipeline` (clone from GitHub `muhammady7-netizen`)
2. Each **task pack** you will work on (folder with `task.toml`) — via git submodule / separate task repos / OneDrive / zip of **source only**
3. Tools once per machine:
   - `Harbor-Shannon-QC\` (`harbor_shannon_qc.py` + `config.json`)
   - Harbor + `setup-session.ps1` (or equivalent)
   - API key in Credential Manager / env (`WANDB_GLM_API_KEY` / `OPENAI_API_KEY`)

## Do **not** need to copy

- `UPLOAD-THIS-TO-QC-*.zip` (rebuild with `package`)
- `harbor-jobs\` GLM run trees
- `qc-out\` (regenerated)
- `machine.json` (recreate from `machine.example.json`)

## On the other PC

```powershell
git clone https://github.com/muhammady7-netizen/haseeb-harbor-pipeline.git
cd haseeb-harbor-pipeline
copy machine.example.json machine.json
# edit machine.json paths + registry.json pack_path/work_root for this PC
.\resume.ps1 doctor
.\resume.ps1 board
```

## Sync rule

Before you leave a PC: update `registry.json` (status / next_action / notes) and `git push`.  
On the new PC: `git pull` then continue from `board` / `next`.
