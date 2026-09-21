# Browser Automation Setup (Playwright MCP)

Enables opencode to drive the V2 Harbor trainer portal (upload, PreQC, Dismiss, Oracle+GLMx4, Submit) via browser automation.

## What this does

- Installs `@playwright/mcp` globally + Chromium browser
- Configures opencode's global MCP config to expose 25 browser tools (navigate, click, type, upload, snapshot, etc.)
- Uses real Chrome (`--browser chrome`) with a persistent profile (`--user-data-dir`) so the Shannon login is saved forever after a one-time sign-in
- All opencode sessions (A-F) share the same global config = same browser profile = same Shannon session

## One-time setup (per PC)

```powershell
git pull
.\setup-browser.ps1
# restart opencode
# first time: sign into Shannon (muhammad.y7@turing.com) in the Playwright Chrome window
# session saves forever - never sign in again
```

## For other sessions (B-F)

No special command needed. The config is global. Just say:
```
open the harbor trainer portal and work on my tasks
```

The Shannon login is already saved. All sessions share the same browser profile.

## Rules

- Only ONE session drives the browser at a time (Chrome singleton lock)
- Never run `taskkill /F /IM chrome.exe` (kills user's real Chrome profiles too)
- User's regular Chrome profiles are never touched (Playwright uses its own separate instance)
- On other PC: run `.\setup-browser.ps1` then one-time Shannon login
- **Do not** launch a second Playwright/`launchPersistentContext` from Cursor while opencode MCP already owns the profile — that fights the singleton and pops extra Chrome. Either:
  - drive via the **one** Playwright MCP Chrome (opencode), or
  - stop that MCP browser, then run the **headless queue** below (no on-screen window)

## Headless QC queue (Cursor / all sessions)

This is the **OpenCode-style** path: **one** shared Shannon profile, **headless** Playwright, upload via `setInputFiles` (no visible window — looks like an API submit). There is **no separate Harbor trainer REST upload API** in this repo; the portal UI is driven headlessly. Cap concurrent Oracle+GLM at **4**.

**Rules that match OpenCode:**
- Launch Chrome **once**; **do not** close/reopen every poll (use `*-keepchrome.js` for long watches).
- Do not thrash with many `launchPersistentContext` loops — that steals the singleton and pops/kills tabs.
- Queue jobs; when slots are full, wait and retry in the **same** browser.

```powershell
cd "C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline"
# Only ONE driver should own chrome-profile at a time
python -m pipeline.qc_queue --dry-run
python -m pipeline.qc_queue --session F --max-eval 4
# Long poll without close/reopen (Session F):
node tmp-pw-f-keepchrome.js
```

GLM for portal PreQC/eval is the **cloud** LiteLLM endpoint already in `opencode.jsonc` / Harbor (`http://34.41.10.8:4000/v1`) — not a local model.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Browser tools not loaded | Restart opencode (config not hot-reloaded) |
| `npx.ps1` blocked by Execution Policy | setup-browser.ps1 uses `node <global-cli.js>` not npx |
| Shannon session lost | Re-login once; profile saves it forever |
| CDP / remote-debugging-port not working | Turing org policy blocks it; use `--user-data-dir` approach instead |
