# Connector Tasks — Consolidated Team Findings

**Compiled from:** Reza Zeraat, Monty Dimkpa, Sahil Garg, Abhishek Yadav, Ahsan Raza, Amit Jadhav, Ahmed Elkholy
**Source:** docs.google.com/document/d/1W3JqkOW3Qsc… (Company Bench Golden Analysis)

---

## Summary

Seven trainers onboarded onto connector tasks. Three key findings:

1. **The guidelines are good** — every contributor said so independently. Clear, step-by-step, unambiguous. Most valuable parts: step-by-step stage breakdown, common-mistakes list, checklist, golden-solution examples.

2. **Onboarding cost far more than reading** — Reading took 2-3.5h. Setup took ~2.5h when nothing went wrong. But two contributors lost 4-5h each to access problems (Cloudflare/Context-Aware Access) — the largest single block of wasted time.

3. **The gap is hardening, not authoring** — The guide is strong on building tasks and attributing failed runs. It is weak on what happens when a sound task is changed across versions (the hardening cycle regime). Four of the highest-value findings are migration-shaped.

---

## 1 · Onboarding — Hours and the Access Blocker

| Contributor | Read/understand | Setup | Notes |
|---|---|---|---|
| Abhishek Yadav | 3.5h | 2.5h | Setup assumes no errors |
| Ahsan Raza | 3h | — | Lost ~5h to Warp Cloudflare access |
| Amit Jadhav | 3h | — | |
| Ahmed Elkholy | 2h study + 2h apply | 2.5h | Lost 4+h to "Access was blocked by Context Aware Access" |
| Sahil Garg | 2h | — | |

**THE ACCESS BLOCKER IS THE BIGGEST SINGLE TIME LOSS.** Cloudflare document not referenced in Trainer Guidelines. Should be before the twelve-stage section.

### Time from claim to submission-ready:
- Simple: 1-2h (oracle passes, battery 1-2/4, no env issues)
- Normal: ~3h (oracle passes, 1-2 hardening iterations, one battery re-run)
- Complex: 4-8h (multiple hardening rounds, env fixes, repeated batteries)

### Stage by stage:
claim/learn 15-30 min · cold read/trace 30-45 min · close surface 30-60 min · PreQC 15-30 min · oracle 30-60 min · battery 30-90 min · read runs 30-45 min · harden 1-3h · record/submit 30-60 min

### What reliably adds hours:
- Docker memory on Apple Silicon: +30-60 min
- opencode OOM (exit 137): +60 min (prevented by pre-baking)
- Swapping server.py between proxy versions: +30-90 min
- Docker daemon crash: +15-30 min each
- Disk full from eval-jobs: +15 min
- Each battery re-run after hardening: +25 min

### Six habits that save the most time:
1. Pre-bake Dockerfile (Node + opencode at build time — saves 60+ min OOM debugging)
2. Set Docker to 16 GB before first run
3. Clean eval-jobs/ after each battery
4. Sync mirror after every edit
5. Run oracle locally (5 min vs 30+ min platform queue)
6. Design coupled discriminators (one good one beats three independent ones)

---

## 2 · What the Guidelines Already Get Right

- The "four things" frame (grades cleanly, model can solve, most attempts don't, nothing unfair)
- The cold read (read instruction.md with gold hidden — highest-value half hour, most often skipped)
- The backward pass (every verifier → instruction sentence, or delete)
- The three-probe surface closing (state route, step route, files on disk)
- The seventeen check-rejection patterns
- The failure-attribution tree
- The voice that survives review
- The step-by-step process, common-mistakes list, checklist, golden-solution examples

---

## 3 · The Nine Gaps That Actually Blocked Work

### 3.0 The principle: shift difficulty from discovery to reasoning
Difficulty must come from **interpreting and reasoning** about information, not from finding it. Models discover hidden information easily; they struggle with nuanced interpretation. Present all data openly, require judgement, mix clear-cut anchors with ambiguous items, avoid discovery traps.

### 3.1 A disclosed rule can still be too easy — THE DEEPEST GAP
The "survives full disclosure" test misses a third state: a rule that is disclosed, survives disclosure, and is still trivial because it's a **mechanical threshold** (field >= N). GLM-5.2 applies it in one step.

Rewritten as interpretation ("a function deployed for the first time is still in development") → three-step chain: understand concept, connect to field, derive threshold. Interpretation, not lookup.

**Rule:** If your discriminator is `field >= N` or `field == X`, a strong model applies it in one step whether or not you disclosed it. Restate it as a policy the model must connect to data.

### 3.2 When the answer moves, everything moves with it
When hardening moved 11→3 violations, the new answer had to land in: instruction.md, manifest.json (expected arrays AND every why_justification/description/rubric string), task.toml (GOLD/HOPS/DECOYS/HIDDEN RULES), solution/ (including golden_trajectory.json), environment/_app/, review.csv.

**The manifest prose was the easiest miss.** Expected arrays fail loudly if stale. why_justification strings fail silently — a stale "the 9 real violations are…" sat beside a correct expected: ["46","86","88"]. A package where assertions say 3 and prose says 9 is contradictory.

### 3.3 A clean diff -r does not mean the mirror is correct
diff -r confirms the mirror matches the root, **not that the root is correct**. After hardening that touches expected values, confirm the root manifest is internally consistent with its own assertions before syncing.

### 3.4 A rule can migrate to a different check
Hardening moved a "violating" function to compliant. The same-slug collision rule looked dead — it had migrated to the population count (46, not 43). Signal: population count short by exactly the number of same-slug pairs while every other check passes.

### 3.5 When two exemptions both match one record, say which governs
A function that is a public integration endpoint (exempt) AND lives in a development project (also exempt). Left open → model over-remediates. State precedence as a principle: "a public endpoint is treated as a public endpoint regardless of which project it lives in."

The accepted task does this in four words: "can write" → "are granted write" (excludes ownership and task control in one move).

### 3.6 A battery can be measuring an instruction you no longer have
Four difficulty runs at 03:15 all reward 1.0; instruction edited at 10:52. The 03:15 runs measured the old, easier task. Undetectable from the reward file alone — needed run timestamp vs instruction mtime.

**Rule:** Before quoting a pass count, confirm the run timestamp postdates the last edit to instruction.md, tests/manifest.json, and the _app mirror.

### 3.7 Sometimes nothing will move it — that is a ceiling, not a patch
If all levers tried and still 4/4, the task is below the model population's floor. Needs a **new data relation**, not a prompt sentence. Ten easy checks are still ten easy checks.

### 3.8 The review record is a history, not a final-state summary
Keep the original failure note and append the new state + evidence. Overwriting loses provenance — a reviewer cannot tell the problem was real and was fixed.

### 3.9 A finding that fails your task but also fails an accepted task
A harbor check failed tests_or_solution_in_image — but the accepted sibling ships the identical Dockerfile pattern. Neither automatically blocking nor automatically safe. Record the sibling shares it, state whether finalisation changed, let the gate decide.

### Priority order if only a few adopted:
1. 3.1 (interpretive vs mechanical) — difference between shipping and coming back
2. 3.2 (cross-file migration) — between migrated and self-contradictory
3. 3.6 (battery predates edit) — between real evidence and stale 4/4
4. 3.3 (self-contradictory root) — prevents shipping broken image
5. Then a worked hardening trace using the accepted task's decoy tables

---

## 4 · Two Things the Accepted Task Does That the Guide Never Mentions

### A deliberately ungraded ask
Instruction says "state your conclusion in your reply" — nothing grades it, on purpose. Adding a response_check would put a judged verifier on an otherwise 100% deterministic bundle. The sentence exists for framing. **An ask may legitimately stay ungraded when grading it would force a judge onto an otherwise-deterministic bundle. Record the decision; do not force the check.**

### A consistency harness as a shipped deliverable
The accepted task ships a `consistency/` folder:
- `gold_sql.py` — re-derives every gold figure from seeded database, exits non-zero on any decoy/gold collision
- `shortcut_audit.md` — records lazy paths actually run and what each scored
- `readers.json` — independent cold-read pass with instruction_sha256 stamped for staleness detection

**Ship a gold_sql.py equivalent. A decoy table without it is an assertion, not evidence.**

---

## 5 · Package and QC Requirements

### Root files: task.toml, instruction.md, README.md (changelog), review.csv

### Required contents by directory:

| Directory | Required contents |
|---|---|
| tests/ | manifest.json, rubric.toml, verifier_engine.py, test.sh, task_inputs.py, test_outputs.py |
| solution/ | solve.py, solve.sh, golden_trajectory.json, golden_results.json, expected_diff.json, final_answer.md, emit_oracle_trajectory.py, files/ |
| environment/ | Dockerfile, entrypoint.sh, sync_app_mirror.sh, seed scripts, _app/, mcp/ |
| evaluations/ | solvability/ (≥1 run at reward 1.0), difficulty/r1-r4 (at most 2/4 at 1.0), stability/repeat-01-03 (3 identical rewards) |

### task.toml sections:
[task] name/description/keywords · [metadata] scenario, source_task_id, mcp_servers_extended · [agent] timeout_sec, user · [verifier] timeout_sec · [environment] build_timeout, cpus, memory, allow_internet · [environment.healthcheck] command, interval, retries · [environment.env]

### Each MCP server needs:
name (gym identifier) · digest-pinned image · host_port/container_port · auth_header_name · access_token · reset_on_run · persist_db_id · dataset (real or synthetic)

### Seeding:
Place at environment/seed_<scenario>.py. Connect to gym's SQLite under /gyms/<connector>/app/data/. Assert at build time:
- No seeded timestamp collides with existing row
- Every seeded row is visible at the level the task expects
- Exactly one data point per entity under test
- No answer or verdict words in seeded content (would leak gold)
- Build must fail if any assertion fails

### The MCP Proxy Bootstrap Anchor
A package can be rejected at upload with "server.py could not be schema-repaired: no known bootstrap anchor" — after passing everything else.

The pipeline looks for a **fixed 11-line block at exactly 12-space indentation** inside bootstrap(): tool-catalog assignment, logging, warning block with specific comment, call to _warn_schema_issues(...), allowlist size check.

**It matches text, not behaviour.** Same calls at 16-space indentation or reworded comments = rejected.

Fix: copy byte-for-byte from an accepted package. Never reimplement.

```bash
grep -c "HARBOR-LOCAL: warn loudly when any tool carries a schema" \
  environment/mcp/proxy/server.py      # must return 1
```

Validate against the final zip, not your working tree.

---

## 6 · The Consolidated Ask (to guideline owners, in priority order)

1. Reference the Cloudflare access document from Trainer Guidelines (before twelve-stage section)
2. Add interpretive-vs-mechanical distinction to difficulty guidance (§3.1) — **single highest-value change**
3. Add cross-file consistency sweep to hardening stage (§3.2), naming manifest prose as silent failure
4. Add evidence-freshness check (§3.6) — confirm run timestamp postdates last edit
5. Add one-line mirror guard (§3.3) and exemption-precedence shape (§3.5)
6. Say when a task is simply too easy for the model population (§3.7) — needs different data, not more rules
7. Say review notes are a history, not final-state summary (§3.8)
8. Add glossary entries for "hardening" and "discriminator"
9. Re-check external links

**The one sentence worth handing to the guide:** A task that clears QC is one whose difficulty lives in **deciding what to count** — inheritance direction, ALL IN SCHEMA, REFERENCES-is-not-a-write — not in applying a disclosed threshold like version >= 2. The "survives full disclosure" test passes both, and that is the false negative to fix.
