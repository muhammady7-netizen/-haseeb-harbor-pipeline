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

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Browser tools not loaded | Restart opencode (config not hot-reloaded) |
| `npx.ps1` blocked by Execution Policy | setup-browser.ps1 uses `node <global-cli.js>` not npx |
| Shannon session lost | Re-login once; profile saves it forever |
| CDP / remote-debugging-port not working | Turing org policy blocks it; use `--user-data-dir` approach instead |
