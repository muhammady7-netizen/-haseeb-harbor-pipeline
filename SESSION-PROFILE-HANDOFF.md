# Session Profile Handoff — logged-in Harbor browser

**Updated:** 2026-09-09
**Profile dir:** `~/.config/opencode/chrome-profile` (this PC only)
**Account:** `muhammad.y7@turing.com` (Shannon IAP session SAVED)

## Status per PC

| PC | Profile logged in? | Action |
|----|-------------------|--------|
| THIS PC (Haseeb Mirza) | YES — session saved 2026-09-09 ~05:55 | Just use browser tools; no login needed |
| Other PC | NO | Run `setup-browser.ps1` then ONE-TIME login (see below) |

## For any session on THIS PC (A, B, C, D, E, F)

The opencode chrome-profile already has the Shannon session. **Do not touch it.**

```powershell
# 1. Confirm config points at the right profile (already set, just verify)
Get-Content (Join-Path $HOME ".config\opencode\opencode.jsonc") -Raw | ConvertFrom-Json | Select -Expand mcp | Select -Expand playwright
# Expected: command ends with "--user-data-dir C:/Users/Haseeb Mirza/.config/opencode/chrome-profile"

# 2. Confirm profile is logged in (should NOT redirect to accounts.google.com)
#    In the opencode chat, just say: "open the harbor trainer portal"
#    If it lands on https://harbor-trainer-...a.run.app/trainer and shows
#    "Signed in via IAP: muhammad.y7@turing.com" -> you're in. DO NOTHING.
#    If it redirects to accounts.google.com -> see "Login needed" below.
```

## CRITICAL — do NOT do these (they break the session)

- **Do NOT copy cookies / Local State / Login Data from `User Data\Profile 11` into the opencode profile.** Google's IAP OAuth treats a new browser instance as suspicious and forces password + 2FA re-auth. The copied `SID` cookies pre-fill the email but don't satisfy re-auth. This was chat F's mistake on 2026-09-09 — wasted ~30 min.
- **Do NOT re-run `setup-browser.ps1` on this PC.** It won't wipe the profile (it only creates the dir if missing), but it's unnecessary and risks confusion.
- **Do NOT close Chrome / `taskkill /F /IM chrome.exe`** — kills the user's real Chrome profiles too. Only stop Playwright Chrome by matching `CommandLine -match "chrome-profile"` (see BROWSER-SETUP.md).
- **Do NOT delete `~/.config/opencode/chrome-profile`** — that's the logged-in session.

## Login needed (other PC, or if this PC's profile gets wiped)

One-time per PC, per the existing `BROWSER-SETUP.md` flow:

```powershell
git pull
.\setup-browser.ps1        # creates empty profile + writes opencode.jsonc
# restart opencode
# say "open the harbor trainer portal"
# in the Playwright Chrome window:
#   1. Google sign-in -> muhammad.y7@turing.com (type password)
#   2. 2-Step Verification -> tap "Yes" on Vivo 1920
#   3. Lands on https://harbor-trainer-...a.run.app/trainer
# Profile saves forever after. Never sign in again on this PC.
```

## Driving rules (all sessions)

- Only ONE session drives the browser at a time (Chrome singleton lock on the profile dir).
- Open your OWN tabs; don't touch tabs other sessions opened.
- Never close Chrome.
- The config in `~/.config/opencode/opencode.jsonc` is GLOBAL — all sessions share it and share the same browser profile = same Shannon session.

## Why the cookie transplant failed (for the curious)

Google IAP (Identity-Aware Proxy) issues session cookies bound to the browser instance that completed OAuth. Copying `SID`/`HSID` from `User Data\Profile 11` pre-fills the email on the sign-in page but Google detects the new browser fingerprint + missing IAP session cookie and forces a full re-auth (password + 2FA). The only state that matters is the IAP session cookie for `harbor-trainer-...a.run.app`, which only gets created by completing OAuth *in the Playwright browser itself*. Once done, it persists in the opencode profile forever.
