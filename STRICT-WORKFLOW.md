# STRICT WORKFLOW — Read this before touching any task

**Every session, every task, no exceptions. Follow this loop until the task is ACCEPTED in V2. Do not stop working until the task is accepted.**

The browser automation (Playwright MCP) is already set up with opencode — see `BROWSER-SETUP.md`. Use it. Do not stop working until the task is ACCEPTED in V2.

---

## The loop (repeat until accepted)

```
 ┌─► 1. BUILD ZIP          (resume.ps1 package --task <short>)
 │   2. JUDGE LOCALLY       (judge.py CLI  +  localhost:3001 web app)
 │   3. FIX BLOCKING        (P0/P1 findings → edit source → rebuild zip)
 │   4. PUSH TO GITHUB      (new finding patterns → train local-qc + app)
 │   5. RE-JUDGE            (back to step 2 until zero findings)
 │   6. UPLOAD TO PORTAL    (Playwright MCP → V2 trainer)
 │   7. PORTAL PreQC        (dismiss only after reading; prefer fix-source)
 │   8. VERIFY review.csv   (counts match shipped gold exactly)
 │   9. RUN Oracle+GLM×4    (~50 min, do not interrupt)
 │  10. READ RESULT         (Oracle PASS + GLM 0-3/4 + 0 findings = ship)
 └──── if any blocker → fix source → back to 1
      if clean → SUBMIT to pipeline → wait for ACCEPTED in V2
```

**Hard rule: do not stop working until the task is ACCEPTED in V2. If a step blocks, fix it and re-enter the loop. Never abandon a task mid-loop.**

---

## Step-by-step

### Step 1 — Build the zip

```powershell
.\resume.ps1 package --task <short>
```

This runs `build_qc_bundle.py` (if present), finds the produced `UPLOAD-THIS-TO-QC-<short>.zip`, mirrors it to Downloads, sets status → `ready_final`. If the build script fails → status `blocked` → fix the packager first.

Fallback (no build script): zips `pack_path` directly (DEFLATED, skips `.DS_Store`/`__pycache__`/`.git`/`.pyc`/nested `.zip`).

### Step 2 — Judge locally (TWO paths, run both)

**Path A — CLI judge:**
```powershell
python local-qc\scripts\judge.py <zip> --no-model          # fast deterministic
python local-qc\scripts\judge.py <zip>                     # full (with model stage, needs WANDB_GLM_API_KEY)
```

`judge.py` runs: the Harbor-Shannon QC engine (deterministic + optional model) PLUS 7 extra checks the engine does NOT do:
- CRLF / UTF-8 BOM byte scan (P0 blocker)
- gold derivability (self-contradiction, hair-splits, placeholder text)
- trajectory freshness (embedded counts vs current gold)
- review.csv count claims vs actual gold
- /tests lock in Dockerfile (grader must stay outside agent image)
- host home paths in bundled trial metadata
- D1-D5 verifier-defect linter (prose_regex, root_container, judge_model, fixture_overwritable, inert_axis)

Verdict: `PASS` (0 P0/P1, model ran) · `NEEDS_REVIEW` (P2 only, or model not run) · `FAIL` (any P0/P1).

**Path B — Web app (localhost:3001):**
```powershell
cd local-qc\web
npm run dev          # starts on port 3001
# open http://localhost:3001 in browser
# upload the zip → get structured verdict + findings + counts + gates + components
# toggle "use model" for the full model stage
```

The web app calls the same `judge.py` under the hood and parses the output into structured UI: verdict, P0/P1/P2/INFO counts, every finding (severity, id, where, fact, impact, fix), component verdicts, gates, reward-hacking status.

**Run BOTH paths.** The web app gives the visual overview; the CLI gives the full text report. Cross-check them.

### Step 3 — Fix blocking findings

Any P0 or P1 finding is a BLOCKER. Read it, understand it, fix the SOURCE (not the finding):

| Finding type | Fix |
|---|---|
| CRLF / BOM | Convert all files to LF, strip BOM, rebuild zip |
| Self-contradictory gold | Make gold consistent OR disclose the distinction in instruction.md |
| Hair-split | Disclose in instruction.md or remove from gold |
| Trajectory stale | Re-run oracle / regenerate trajectory to match current gold |
| review.csv stale | Update counts to match shipped gold |
| /tests lock broken | Remove the COPY from Dockerfile |
| D1 prose_regex | Migrate regex to LLM rubric or Python assertion in test_outputs.py |
| D2 root_container | Add non-root USER directive to Dockerfile |
| D3 judge_model | Use ${JUDGE_MODEL} placeholder with harness resolver |
| D4 fixture_overwritable | Move fixture into /tests, run container non-root |
| D5 inert_scoring_axis | Populate the axis or set weight to 0 |

After fixing → rebuild zip (Step 1) → re-judge (Step 2). Loop until zero P0/P1.

### Step 4 — Push to GitHub (train local-qc + app)

When you encounter a NEW finding pattern that local-qc does not yet catch:

1. Document the finding pattern in `local-qc/QC-SELF-TRAINING.md` (finding number, evidence, why it was missed, how to catch it).
2. Add the check to `local-qc/scripts/judge.py` if it can be detected deterministically.
3. Update `local-qc/docs/7-layer-checklist.md` with the new red flag.
4. Commit and push BOTH repos:
   ```powershell
   # local-qc
   cd local-qc
   git add -A
   git commit -m "Finding N: <pattern> — added check to judge.py + self-training + checklist"
   git push origin main

   # haseeb-harbor-pipeline
   cd haseeb-harbor-pipeline
   git add -A
   git commit -m "Finding N: <pattern> — updated workflow/registry/state"
   git push origin main
   ```

This trains the local QC tool so future sessions catch the same pattern before upload. Every new finding the portal surfaces that local QC missed → add to local-qc → push → the tool gets smarter each iteration.

### Step 5 — Re-judge after fixes

Back to Step 2. Run both CLI and web app. The goal is **zero P0, zero P1** before uploading to the portal. P2 are advisory (NEEDS_REVIEW) — fix them if fast, otherwise note and proceed.

### Step 6 — Upload to portal (browser automation)

The Playwright MCP browser is already set up (see `BROWSER-SETUP.md`). Use it — do not manually click:

```
open the harbor trainer portal
upload <zip> to V2 trainer
```

Or via the headless queue:
```powershell
python -m pipeline.qc_queue --session <X> --max-eval 4
```

Rules:
- Only ONE session drives the browser at a time (Chrome singleton lock)
- Never kill chrome.exe
- Cap concurrent Oracle+GLM at 4

### Step 7 — Portal PreQC

PreQC is **mandatory** before GLM runs. It runs `verifier_defect_lint.py` (D1-D5).

- If PreQC finds blocking issues → **fix the source** (Step 3), rebuild, re-upload. Do NOT dismiss as false positive unless you are certain and have logged it in the Pre QC False Positives sheet + pinged your pod lead.
- If PreQC is clean → proceed to Oracle+GLM.

### Step 8 — Verify review.csv in portal

Before running GLM, confirm the portal's review.csv matches the shipped package:
- Every count cited in review.csv matches the actual gold (results.json, CSV row counts)
- Every path cited in change_made exists in the package
- No stale counts from a prior version

If review.csv is wrong → fix it in source → rebuild → re-upload. Do not run GLM with a stale review.csv.

### Step 9 — Run Oracle + GLM×4

```
run QC-Oracle-GLM
```

Takes ~50 minutes. Do not interrupt. The run does:
1. Oracle golden replay (proves the gold passes its own verifier)
2. 4× GLM-5.2 difficulty runs (proves the task is hard enough)
3. Harbor Check (semantic review by GLM-5.2)

### Step 10 — Read the result

| Signal | Meaning | Action |
|---|---|---|
| Oracle PASS | Gold passes its own verifier — grading is sound | Good |
| Oracle FAIL | Gold does not pass its own verifier — grading broken | Fix verifier/gold → rebuild → re-upload |
| GLM 0/4 | Excellent difficulty | Good (verify failures are MODEL-attributed, not gold-defect) |
| GLM 1/4 | Good difficulty | Good |
| GLM 2/4 | Acceptable difficulty | Good |
| GLM 3/4 | Borderline — may be too easy | Consider densify |
| GLM 4/4 | TOO_EASY — **rejected** | Densify (add DATA traps, not hidden rules) → rebuild → re-upload |
| 0 findings | No issues | Good |
| N findings | Issues to review | Read each → fix source → re-upload → re-run |

**If any blocking finding → fix the source (Step 3) → back to Step 1. Never dismiss as false positive.**

**If GLM 4/4 (too easy):** Per All Hands guidance — "If a task runs locally with a pass but yields a 4/4 score online after addressing setup issues once, pass the task to partlets for spot checks and move on." After two densify builds with no change, stop turning the same dial. Put difficulty in the DATA, not in hidden rules or hair-splits.

### Step 11 — Submit to pipeline

When ALL of these are true:
- Oracle PASS
- GLM 0/4 to 3/4 (not 4/4)
- 0 blocking findings
- review.csv verified
- PreQC clean

→ Submit to the pipeline. Wait for the pipeline verdict. If the pipeline rejects → read the rejection → fix → re-upload → re-run. **Do not stop until the task is ACCEPTED in V2.**

---

## The 5 questions (ask before every "ship it")

1. Can a reader with ONLY the instruction + inputs derive every gold verdict? → if no, hidden requirement, task is broken
2. Do identical inputs get identical verdicts? → if no, self-contradictory gold, task is unsolvable
3. Are the GLM failures on rows where the gold is broken? → if yes, 0/4 is fake difficulty
4. Does solve.sh compute the answer or copy pre-computed gold? → if copies, Oracle 1.0 is replay
5. Did I run the model stage of the QC tool? → if no, I will miss semantic findings

## The 7 layers (run on every zip)

0. Read the content (instruction, inputs, gold, solve.sh, verifier.json)
1. Gold derivability (blind-reader test, group identical wording, hair-splits, placeholders)
2. Failure cause validity (GLM failures on broken-gold rows? clustered failures?)
3. Surface-form fairness (regex rejects bold/italic/decimal/words?)
4. Solvability legitimacy (solve.sh computes or copies? trajectory earned or hand-authored?)
5. Stability evidence (per-check identical across repeats? frozen artifacts?)
6. Run the FULL QC tool WITH the model stage (not --no-model)
7. Realism (duplicated sentences? placeholder text? difficulty in DATA not rules?)

## Hard rules

- **Never dismiss Harbor Check / QC findings as "False positive".** Fix the source, repackage, re-upload, re-run.
- **One session drives the browser at a time** (Chrome singleton lock).
- **Put difficulty in the DATA, not in hidden rules or hair-splits.**
- **Never stop working until the task is ACCEPTED in V2.** If a step blocks, fix it and re-enter the loop.
- **Browser automation is already set up** (Playwright MCP + opencode) — use it, do not manually click.
- **Push new finding patterns to GitHub** (both repos) so local-qc and the web app learn from every portal finding.

## Key URLs

| Resource | URL |
|---|---|
| V2 Trainer (portal) | https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer |
| Local QC web app | http://localhost:3001 |
| Local QC CLI | `python local-qc/scripts/judge.py <zip>` |
| Pipeline driver | `.\resume.ps1 <command>` |
