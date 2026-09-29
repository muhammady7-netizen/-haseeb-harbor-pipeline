# Session Bootstrap — Connector Tasks

Paste this at the start of every new chat session. It tells the AI exactly where everything is and what to read first.

---

## You are working on Harbor/Shannon QC connector tasks.

## Step 1: Pull latest
```powershell
cd "C:\Users\Haseeb Mirza\Documents\Default Project\haseeb-harbor-pipeline"; git pull
cd "C:\Users\Haseeb Mirza\Documents\Default Project\local-qc"; git pull
```

## Step 2: Read ALL docs (in this order, every single file)
1. `docs/connector-resources/CONNECTOR-SETTLED-GUIDE.md` — THE definitive guide from Slack (shayan.a). Read FIRST. Supersedes all others.
2. `docs/connector-resources/00-CONNECTOR-RESOURCES-INDEX.md` — master index
3. `docs/connector-resources/05-foundation-guidelines-complete.md` — the full 5-tab guideline (730 lines)
4. `docs/connector-resources/07-golden-task-analysis.md` — 3 accepted tasks analyzed
5. `docs/connector-resources/08-connector-tasks-guidelines.md` — 12-stage workflow
6. `docs/connector-resources/11-common-issues-qc-playbook-full.md` — 10 P-C patterns, two-pass QC
7. `docs/connector-resources/06-consolidated-team-findings.md` — 9 gaps from 7 trainers

## Step 3: Key settled rules (memorize these)
- **JUDGE_MODEL in task.toml**: `${JUDGE_MODEL:-openai/zai-org/GLM-5.2}` (DON'T change to glm-5.2)
- **JUDGE_MODEL in manifest.json**: `openai/zai-org/GLM-5.2` (NOT `openai/glm-5.2`)
- **JUDGE_MODEL for local harbor config**: `openai/glm-5.2` (this is different from portal)
- **Image sha256 (synthetic)**: `@sha256:b1374cd8a392ea66f9a649e700a1498e8fcb03ee35776362db7cc15dc3049b89`
- **Image sha256 (real-data)**: `@sha256:926ccf1081606a438d86d861dda44e157c89396ee030f4e37aa771059c70b90c`
- **Healthcheck retries**: 150 (not 40)
- **Band**: Ship at 1/4 or 2/4. 4/4 = too easy. 0/4 = re-roll by default.
- **Oracle**: Must score exactly 1.0. Fix the check, never the golden.
- **Mirror**: Sync _app mirror after EVERY edit. Re-run oracle after every change.
- **Advisory findings**: NORMAL. Ignore if FP, move ahead. (Confirmed by lead)
- **review.csv**: 14 rows + header = 15 rows. 5 columns: review_check, status, review_notes, change_made, what_to_record. Use csv.writer with QUOTE_ALL.
- **review.csv row names** (byte-exact with middot ·):
  1. Layer 1 · Package consistency
  2. Layer 1 · Clarity and scope
  3. Layer 1 · Realism and leakage
  4. Layer 2 Difficulty
  5. Layer 2 Solvability
  6. Layer 2 Stability
  7. Layer 3 Oracle Mode
  8. Layer 4 · Environment and files
  9. Layer 4 · Connectors, MCPs, and CLIs
  10. Layer 4 · Deliverables and artifact quality
  11. Layer 5 · Verifier coverage and fairness
  12. Layer 5 · LLM judge consistency
  13. Layer 5 · Reward hacking and exploitability
  14. Cross-trial · Calibration

## Step 4: Environment
- Windows 11, PowerShell 5.1, Python 3.14
- Docker Desktop installed and running
- Portal: `https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer`
- Chrome profile: `C:/Users/Haseeb Mirza/.config/opencode/chrome-profile` (already authenticated)
- Signed in as: `muhammad.y7@turing.com`
- GLM key: Windows Credential Manager entry "TuringGLM"
- GLM gateway: `http://34.41.10.8:4000/v1`
- Session bootstrap: `. 'C:\Users\Haseeb Mirza\Documents\Codex\Tools\TuringHarbor\setup-session.ps1'`
- Local QC: `local-qc/scripts/judge.py` (D1-D22 linter wired in)
- Pipeline linter: `haseeb-harbor-pipeline/tools/verifier_defect_lint.py` (D1-D22)

## Step 5: Active tasks
### Task 1: the-answer-she-already-gave (CONN-B3-9000286)
- Portal: `content-e44be383f77a95dce3729fe2fcc4addf`
- Connector: email-calendar-gym
- Latest: v12 (Oracle PASSED 1.0, GLM running with correct synthetic sha256)
- Zip: `UPLOAD-THIS-TO-QC-the-answer-she-already-gave.zip`
- Original download: `Downloads/the-answer-she-already-gave-20260929T072048Z-1-001.zip`

### Task 2: the-thread-that-outlived-its-own-start (CONN-B3-9000370)
- Portal: `content-72cd67fdbff7ade40f82cd25d4bdff2c`
- Connector: slack-gym
- Latest: v11 (Oracle running with correct synthetic sha256 + INTERNAL_VERIFIER_SECRET gate added)
- Zip: `UPLOAD-THIS-TO-QC-the-thread-that-outlived-its-own-start.zip`
- Original download: `Downloads/the-thread-that-outlived-its-own-start-20260929T091818Z-1-001.zip`

## Step 6: Reference tasks (accepted by client)
1. `Downloads/auto-atlanta-covered-travel-roomlist-20260903t200000z-3fd10b-v1-sna-drhp-atlanta-itinerary-settlement-standing-ranked.zip`
2. `Downloads/auto-how-much-of-my-drive-is-link-only-20260826T10143-7cce8e-v1-sna-hfxx-how-much-of-my-drive-is-link-only.zip`
3. `Downloads/auto-outside-voices-in-the-locked-sales-drive-2026090-87313e-v1-sna-qygt-outside-voices-in-the-locked-sales-drive.zip` (may not be downloaded yet)

## Step 7: Portal API
```javascript
// Run PreQC
fetch('/trainer/api/run', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({task_id:'content-xxx-vN', mode:'internal'})})
// Run Oracle+GLM
fetch('/trainer/api/run', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({task_id:'content-xxx-vN', mode:'delivery'})})
```

## Step 8: What to do
1. Check portal status of both tasks
2. If Oracle passed and GLM completed: read difficulty results
3. If 4/4: harden the task (add interpretive discriminator, NOT mechanical threshold)
4. If 1-2/4: create review.csv + README + submit to pipeline
5. If Oracle failed: read the error, fix, re-upload
6. One change per test. Don't touch JUDGE_MODEL. Don't touch manifest.json models array (keep zai-org).
