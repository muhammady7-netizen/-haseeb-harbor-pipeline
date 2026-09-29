# Connector Task Findings — Team Reports

**Source:** https://docs.google.com/document/d/1_bqiPgXY-3dqjdunCemyKysYrQXgub8-arurf53rObI/edit?tab=t.0
**Title:** Connector Task Findings (team findings collection)

---

## Task Time Estimates

| Scenario | Time | When |
|---|---|---|
| Simple task | 1-2 hours | Oracle passes, battery 1-2/4, no env issues |
| Normal task | 3 hours | Oracle passes, 1-2 hardening iterations, 1 battery re-run |
| Complex task | 4-8 hours | Multiple hardening rounds, env fixes, battery re-runs |

### Breakdown by stage
- Stage 1-2: Claim and learn (15-30 min)
- Stage 3-4: Read prompt, trace checks (30-45 min)
- Stage 5: Close connector surface (30-60 min)
- Stage 6: PreQC (15-30 min)
- Stage 7: Prove oracle (30-60 min)
- Stage 8: Measure/battery (30-90 min)
- Stage 9: Read runs (30-45 min)
- Stage 10: Harden (1-3 hours, iterative)
- Stage 11-12: Break, record, submit (30-60 min)

### What makes it take longer
- Docker memory on Apple Silicon: +30-60 min
- opencode OOM (exit 137): +60 min (pre-bake fixes)
- Proxy server.py incompatibility: +30-90 min
- Multiple hardening iterations: +1-2 hours per iteration
- Disk full from eval-jobs: +15 min
- Docker daemon crashes: +15-30 min per crash
- Battery re-runs after hardening: +25 min each

### Time-saving tips
1. Pre-bake Dockerfile (Node + opencode at build time)
2. Set Docker to 16GB before first run
3. Clean eval-jobs after each battery
4. Sync mirror after every edit
5. Run oracle locally (5 min vs 30+ min queue)
6. Design coupled discriminators (one good one beats three)

---

## Hardening the-edge-function-nobody-locked-down (Task A — Supabase)

### Issue A1: Mechanical threshold stayed 4/4
Original discriminator "version >= 2 + JWT disabled" = one-step lookup. GLM-5.2 applied it directly. 4/4 even after full disclosure.

**Fix:** Rewrote as "a function deployed for the first time is still in development — developer may have intentionally left JWT off." Three-step chain: understand concept → connect to field → derive threshold. Interpretation, not lookup.

Genuine violations dropped to 3 (ids 46, 86, 88).

### Issue A2: Answer migrated to assertions but not prose
Expected arrays updated but why_justification/description/rubric strings still quoted old counts (11). Package was contradictory — assertions said 3, prose said 9.

**Fix:** Rewrote every stale string to v2 counts.

### Issue A3: task.toml metadata stuck at v1
GOLD/DECOYS/HIDDEN RULES/HOPS all carried old answer. One HIDDEN RULE called a now-compliant function "a real violation."

**Fix:** Moved all metadata to v2. Reframed qz-sign as compliant public signing endpoint.

### Issue A4: Two un-pinned forks
Two exemptions (public endpoint, dev project) could both match one function. Prompt didn't say which governs.

**Fix:** Added precedence paragraph: public endpoint classification takes precedence over dev-project rule.

### Issue A5: _app mirror internally contradictory
Mirror's gym_step_state expected ids at remediated versions while assertions classified them compliant/untouched. diff -r would catch it only because root was already correct.

**Fix:** Re-ran sync_app_mirror.sh from corrected root.

### Issue A6: Packaging gate findings (G02 + G03)
G02: GLM gateway IP in eval files. G03: /Users/rezazeraat/... in 9 eval files.

**Fix:** Pipeline auto-remediates both. Recurs every time evals are regenerated.

### Issue A7: Evidence is stale
All evaluation runs predate v2 instruction edit. 4/4 reward 1.0 is against old, easier instruction.

**Fix needed:** Re-run oracle + battery against v2. Write prediction first: 11 = ignore all exemptions, 9 = apply only first-deploy, 3 = correct.

### Issue A8: review.csv is stale
Still quotes 11 violations / 35 compliant / 11 deploys.

**Fix needed:** Update — append, don't overwrite. Keep original failure notes.

---

## read-only-in-name-only (Task B — Snowflake) — ACCEPTED

### Issue B1: Started 4/4 too
Same starting point. Hardened with precision lever: counts → sorted lists of names. Textbook honest lever — chained, sharp, provable, honest.

### Issue B2: Prediction written before change
"Band drops 4/4 → 1-2/4, because a list must be exactly right." Battery matched prediction.

### Issue B3: Oracle re-verified after change
Re-ran oracle — reward 1.0, 10/10 checks. Change didn't break grading.

### Issue B4: Exemption-precedence fork pinned
"How many roles can write" → "are granted write" (excludes ownership and task-control). Four words.

### Issue B5: Decoy table with proof harness
Shipped consistency/ folder: gold_sql.py (re-derives gold, exits non-zero on decoy collision), shortcut_audit.md, readers.json.

### Issue B6: Difficulty in deciding what to count
Every naive reading yields a named wrong number. Interpretive, not threshold.

### Issue B7: Infrastructure fought through
- Upload rejection on server.py (hash match, not behavior)
- Snowflake-gym client-mode trap (HARBOR_CONNECTOR_CONTROL_CAPABILITY)
- Docker OOM (8-12 GB sweet spot, not all 16 GB)
- Apple Silicon + amd64-only image (DOCKER_DEFAULT_PLATFORM)
- G10 is expected residual
- Re-zip from sanitized tree

---

## The Contrast That Matters

Both started 4/4. Task B had a real lever (precision: counts → lists), applied honestly with written prediction, re-verified oracle, landed in band. Task A hit a mechanical-threshold false negative (version >= 2 rule), reworked to interpretive discriminator.

**Shared lessons:** sync mirror after every edit, run oracle after every change, write prediction before hardening.

---

## Connector Task Guide — Quick Reference

### Required Files
- **Root:** task.toml, instruction.md, README.md, review.csv
- **tests/:** manifest.json, rubric.toml, verifier_engine.py, test.sh, task_inputs.py, test_outputs.py
- **solution/:** solve.py, solve.sh, golden_trajectory.json, golden_results.json, expected_diff.json, final_answer.md, emit_oracle_trajectory.py, files/
- **environment/:** Dockerfile, entrypoint.sh, sync_app_mirror.sh, seed scripts, _app/, mcp/
- **evaluations/:** solvability/ (≥1 run reward=1.0), difficulty/r1-r4 (max 2/4 at 1.0), stability/repeat-01-03 (3 identical)

### Seeding Rules
- Place at environment/seed_<scenario>.py
- Connect to gym SQLite under /gyms/<connector>/app/data/
- No timestamp collisions
- All seeded rows visible at expected level
- One data point per entity under test
- No answer/verdict words in seeded content
- Build must fail if any assertion fails

### MCP Proxy Bootstrap Anchor
- Fixed 11-line block at exactly 12-space indentation inside bootstrap()
- Must contain: tool catalog assignment, HARBOR-LOCAL warning comment, _warn_schema_issues() call, allowlist size check
- Matches TEXT, not behavior — same calls at 16-space = rejected
- Copy byte-for-byte from accepted package
- Verify: `grep -c "HARBOR-LOCAL: warn loudly when any tool carries a schema" environment/mcp/proxy/server.py` must return 1

### task.toml Sections
- [task] name/description/keywords
- [metadata] scenario_name, source_task_id, mcp_servers_extended
- [agent] timeout_sec, user
- [verifier] timeout_sec
- [environment] build_timeout_sec, cpus, memory_mb, allow_internet
- [environment.healthcheck] command, interval_sec, retries
- [environment.env]

### MCP Server Config
- name (gym identifier)
- image (digest-pinned)
- host_port / container_port
- auth_header_name
- access_token
- reset_on_run
- persist_db_id
- dataset (real or synthetic)

---

## Individual Trainer Reports

### Abhishek Yadav (3.5h read, 2.5h setup)
Guidelines clear and straightforward. Step-by-step process, common mistakes, checklist, golden examples most useful.
Suggests: more guidance on hardening/iteration, distinguish interpretive vs mechanical, cross-file consistency check, fresh test results, exemption precedence, ceiling detection, review notes as history.

### Ahsan Raza (3h read, lost ~5h to Cloudflare access)
Guidelines solid. Suggests same improvements as Abhishek.
Findings: Cloudflare access delay, task claimed Sep 15, troubleshooting GLM errors, working on softening task complexity.

### Amit Jadhav (3h read)
Guidelines solid. Same suggestions.

### Ahmed Elkholy (2h study + 2h apply, 2.5h setup, lost 4+h to Context Aware Access)
Findings: 4+ hours on access block, oracle/battery run 2h, Cloudflare document should be referenced in Trainer Guidelines, CompanyBench guidelines should reference Trainer Guidelines before 12-stage section.

### Sahil Garg (2h read)
Guidelines solid. Same suggestions.
