# Haseeb Harbor Pipeline

Multi-session tracker + local PreQC → package → **ready_final** automation.

**GitHub:** https://github.com/muhammady7-netizen/-haseeb-harbor-pipeline  
**Owner:** Muhammad Haseeb Younas (`muhammad.y7@turing.com`)

## Quick start (this PC)

```powershell
cd "C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline"
.\resume.ps1 doctor
.\resume.ps1 board
.\resume.ps1 assign --session A --tasks gen-g1205,fin-f39,the-thread
.\resume.ps1 loop --session A --package
```

After PreQC fails with findings: fix the task pack, then re-run `preqc` / `loop` until `preqc_clean` → zip → `ready_final`.

Portal steps (upload / Dismiss PreQC / Oracle+GLM×4 / Accept) are **manual**; mark them:

```powershell
.\resume.ps1 set-status --task gen-g1205 --status uploaded --note "uploaded v12"
.\resume.ps1 set-status --task gen-g1205 --status portal_preqc_dismissed
.\resume.ps1 set-status --task gen-g1205 --status final_running
.\resume.ps1 set-status --task gen-g1205 --status accepted
```

## Commands

| Command | Meaning |
|---------|---------|
| `board` | All tasks + status counts |
| `doctor` | Check PreQC paths + packs exist |
| `assign --session X --tasks a,b,c` | Lock ≤3 tasks to a chat |
| `next --session X` | What to do next |
| `preqc --task ID` | Deterministic PreQC (add `--full` for GLM) |
| `package --task ID` | Build zip → `ready_final` |
| `loop --session X --package` | PreQC all session tasks; package if clean |
| `set-status` / `mark-zip` | Portal / zip bookkeeping |

## What is automated vs not

- **Automated:** registry, PreQC, package, status, session locks  
- **Not automated:** editing task to fix findings, V2 browser upload/Dismiss/Accept  

See `TAKE-TO-OTHER-PC.md` and `HANDOFF.md`.
