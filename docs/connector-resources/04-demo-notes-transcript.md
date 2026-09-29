# Connector Tasks Demonstration — Full Notes + Transcript

**Source:** Gemini notes from Sep 16, 2026 meeting
**Presenters:** Reza Zeraat, Monty Dimkpa, Zein Rezky Chandra
**Attendees:** AMIT JADHAV, Md Hussain, ANEELA JAFFER, Reza Zeraat, ALLEPU NITHISHA, Abhishek Yadav, Ahsan Raza, Aditya Keshri, Monty Dimkpa, Zein Rezky Chandra, Sahil Garg, Apsiya Patan, Ahmed ELKHOLY, Navendu Mishra

---

## Key Takeaways

### 1. Difficulty testing
- Run model **exactly 4 times** (never 5)
- Count **full successes** (perfect score, not nearly perfect)
- **Shift if 1 or 2 out of 4** pass
- 0/4 = broken/unfair/beyond model; 4/4 = too easy
- **Close backdoors BEFORE measuring difficulty** — wrong order wastes a day

### 2. Three common defect types causing rejections
1. **Task too easy** (13/20 tasks) — not a single task called "too hard"
2. **Agent can cheat via backdoor** (13/28 tasks) — agent queries DB directly, gets answers without doing work. Four backdoor types; the missed one is **files on disk** — if agent can read DB file, nothing else matters
3. **Marking things never asked for** (0/28) — if you mark it, instruction must say it

### 3. How to fix backdoors
- **Test from inside the container as the agent** (not as administrator — everything looks open as admin)
- **Mark what the agent actually did** — not just what it wrote

### 4. Task hardening — difficulty from interpretation, NOT more data
Example: rule "function counts as violation if version >= 2 and security off" → model passes 4/4 (simple threshold). Rewritten as "a function deployed for the first time is still in deployment, so developer may have left security off on purpose" → now requires 3 steps (interpret "first deployment", find the field, drive threshold). Task moved into target band.

**Key rule: hard comes from having to INTERPRET something, not from more rules or more data. If you add more data, the model writes a script and fixes it.**

### 5. Connector vs Non-Connector architecture

| Aspect | Non-Connector | Connector |
|---|---|---|
| Input source | Static files in `app/input/` | Live gym server (database-backed) |
| Agent interaction | Reads files, processes, writes output | Calls MCP tools through proxy |
| Verifier | File checks (JSON path on output files) | Gym step state verifiers + file checks + rubric |
| State | Static — agent can spoof files | Live — gym maintains state, verifier queries it directly |
| Cheating | Possible (agent writes wrong values to files) | Impossible (gym is source of truth, agent can't fake) |
| Base image | `python:3.12-slim` with SHA digest | `connectors-harness` pre-configured image |
| Data seeding | Optional (add columns/data to static files) | **Required** — seed DB at build time via scripts |
| Timeouts | Standard | **3x longer** (API calls, DB hops, multi-step reasoning) |
| task.toml | Small, simple | Extensive metadata (intent, connector, hidden rules, gold, decoys) |
| MCP servers | Empty | Defined with image, ports, health checks |
| Proxy port | N/A | **7000** (never 8027 — that's gym direct) |
| Gym port | N/A | 8027/8016 |

### 6. Three-user isolation (CRITICAL)

| User | Role | Privileges | Port |
|---|---|---|---|
| `rlgymagent` | Runs AI agent process | Limited (UID 1000), can't access DB or privileged resources | — |
| `gym` | Runs gym server (live service) | Full DB + filesystem access, isolated from agent | 8027 |
| `mcproxy` | Runs MCP proxy server | Routes between agent and gym, handles auth + logging | 7000 |

### 7. task.toml connector sections

**MCP Server Block:**
- Server name (must match header in task file)
- Docker image with digest
- Host/container ports
- `reset_on_run = true` (reset gym state between trials for reproducibility)
- Proxy URL must point to **port 7000** on localhost (NOT 8027)

**Health Check Block:**
- Heartbeat to verify MCP proxy + gym are ready before agent starts
- Configured on port 7000
- Interval timers, 5-second timeouts, retry limits

**Metadata sections:**
- **Intent** — what the task is about (usually pre-defined)
- **Connector** — gym type, acting user, token info
- **Hidden Rules** — requirements inferable from context but not stated explicitly. Must be **provable/contestable** — can be shown to derive from the instruction. Examples: "EU region" = literal 'EU' string prefix; cluster writes require active/healthy status.
- **Gold** — human-solvable target that stays constant across task variations. Example: 81 projects reviewed, 24 remediated UUIDs.
- **Decoys** — plausible but wrong answers that trap agents. Example: "set of all even numbers" is subset of "set of all positive integers" — doesn't need to be stated but agent should know.

### 8. MCP proxy bootstrap anchor (11-line YAML block)
- **CRITICAL configuration** — if wrong, agent can't communicate with gym
- Exactly **12 spaces** indentation on first line
- Server name must match task file header
- Port must be **7000** (not 8027)
- No trailing whitespaces
- Wrong port (8027) → agent bypasses proxy, connects directly to gym → fails
- Wrong indentation (10 spaces instead of 12) → YAML parsing fails, config not recognized

### 9. Data seeding
- Happens at **build time** (not runtime) — ensures every trial starts with identical data
- Copy seed scripts to temp build directory → run to append SQL inserts → delete temp folder
- **Build-time assertion scripts** check for seed corruption/drift:
  - If patch marker present → exit 0 (good)
  - If unpatched/drifted → non-zero exit (aborts build)
- Without seeding, there's no experiment (data changes every run)

### 10. Four acceptance criteria (all tasks)

| Criterion | Meaning |
|---|---|
| **Solvability** | At least one model (human) can solve it. Oracle reward = exactly 1. |
| **Difficulty** | Models score 1-2/4 (occasionally 3/4 accepted). Not 4/4 (trivial) or 0/4 (too hard/broken). |
| **Stability** | Solution replayed 3x produces identical results (determinism). |
| **Verifier accuracy** | Verifier catches bad solutions as fail, valid solutions as pass. No false positives/negatives. |

### 11. Hardening strategies (connector-specific)

1. **Hidden rules** — inferable from context, not stated, must be provable
2. **Decoys** — plausible wrong answers, trap agents into logic errors
3. **Multi-hop query chains** — chain depth >= 3 (e.g., 53 tool calls: list projects → filter EU → update eligible). Don't exhaust reasoning tokens or create 6-hour QC runs.
4. **Edge cases** — subtle state transitions (pausing must pair with restoring/resuming)

### 12. Verifier types in connectors

| Type | What it does | Can agent fake? |
|---|---|---|
| **File check** | Reads output file, JSON path assertion on values | YES (only checks what agent wrote) |
| **Gym step state** | Queries trusted proxy endpoint, inspects live gym DB state | NO (gym is source of truth) |
| **Rubric (LLM judge)** | Qualitative assessment of how something was done | NO (judges actual trajectory) |

### 13. Connector file structure
```
task-folder/
  task.toml              (extensive metadata, MCP servers, health checks)
  instruction.md
  review.csv             (same as non-connector)
  environment/
    Dockerfile           (connectors-harness base, 3-user isolation, seed scripts)
    entrypoint.sh         (starts proxy + gym services)
    mcp/proxy/server.py   (MCP proxy — use Atlanta example as base)
    _app/                 (mirror of task files for build context)
  tests/
    manifest.json         (verifier configs — file check + gym step state + rubric)
    rubric.toml           (LLM judge rubric config)
    test_outputs.py       (pytest harness)
    test.sh               (test runner)
    rl_world_verifiers/   (vendored engine — do not modify)
  solution/
    solve.sh, solve.py    (oracle solution)
    golden_trajectory.json
  consistency/             (consistency harness — can omit, platform runs it for stability)
```

### 14. Quick identification: connector vs non-connector
- MCP servers field empty → non-connector
- MCP metadata + MCP servers extended → connector
- Port 7000 → connector proxy
- Port 8027 → gym direct (never use this for agent)

### 15. QC pipeline issues
- Score discrepancies between local and QC: LLM non-determinism + distributed environment differences
- QC does cross-calibration runs + retries that local doesn't
- 0/4 from QC = will fail at pipeline finalization
- 4/4 from QC = reliable pass, task is too easy
- Harbor check failures are infrastructure issues (high pipeline traffic)
- Use local validation scripts (Andrew's check script + harbor agent repair tool) to fix locally before uploading

### 16. Cloudflare access
- Implemented by security team after breach
- Must login with Turing email accounts
- Post email in designated channel thread if authorization fails

### 17. QC version 2
- Same QC version 2 used for both connector and non-connector tasks

### 18. Key next steps from meeting
1. Read Handbook pages 1 and 2 before next task
2. Check backdoors before modifying difficulty
3. Bring or discard tasks if model consistently passes without clear reasoning path
4. Implement seed scripts with build-time assertions
5. Ensure proxy URL points to 7000 on localhost
6. Report Cloudflare access issues in channel thread
7. Use shared scripts + zip files for local analysis before QC upload
8. Review documentation for non-connector to connector transition

---

## Full Transcript (Key Excerpts)

### Reza Zeraat — Difficulty and Defects

"Testing difficulty requires running models 4 times and counting successful completions. Tasks succeeding 1 or 2 times out of 4 are shifted for difficulty adjustment."

"Three common defects: overly easy paths (13/20), database backdoors (13/28), and unrequested marking (0/28)."

"Agents exploit database backdoors to retrieve answers directly without executing required tasks. Four backdoor types — the one people miss is files on disk. If the agent can read the database file, nothing else you did matters."

"Test from inside the container as the agent, not as an administrator. As an administrator, everything looks open. And mark what the agent actually did, not just what it wrote."

"Close backdoors first, measure again, then decide if it's too easy. The wrong order wastes a day."

"Hard comes from having to interpret something, not from more rules and not from more data. If you add more data, the model will write a script and fix it."

### Monty Dimkpa — Architecture and Configuration

"Connector tasks interact with live services through MCP proxy. The gym server is isolated behind the proxy. Proxy on port 7000, gym on port 8027."

"The gym maintains live state of all operations. Verifiers independently query the live state directly. The agent cannot fake success — the gym is the source of truth."

"Three users required: rl_gym_agent (AI agent, limited privileges, UID 1000), gym (live service, full DB access, isolated from agent), mcproxy (MCP proxy, routes between agent and gym)."

"Connector timeouts are about 3x longer than non-connector due to API calls, database hops, and multi-step reasoning."

"Hidden rules: requirements inferable from context, not stated explicitly, but must be provable. Example: 'EU region' means literal 'EU' prefix on region code. Cluster writes require active/healthy status."

"Decoys: plausible but wrong answers. Example: 'set of all even numbers' is subset of 'set of all positive integers' — doesn't need to be stated but agent should know."

"Gold: human-solvable target, stays constant across task variations. Example: 81 projects reviewed, 24 remediated UUIDs."

"MCP proxy bootstrap: 11-line YAML block, exactly 12 spaces indentation, server name must match header, port must be 7000 (not 8027), no trailing whitespace. Wrong port = agent bypasses proxy. Wrong indentation = YAML parsing fails."

"Data seeding at build time: copy seed scripts to temp dir → run to append SQL inserts → delete temp folder. Build-time assertions check for drift: patch marker present = exit 0 (good), unpatched = non-zero exit (aborts build)."

### Hardening strategies

"Hidden rules, decoys, multi-hop query chains (chain depth >= 3, e.g., 53 tool calls), edge cases with subtle state transitions (pausing must pair with restoring)."

"Don't make it so hard that you exhaust reasoning tokens or create 6-hour QC runs."

### Q&A Highlights

**Q: Same QC version 2 for connectors?**
A: Yes, same QC version 2.

**Q: Score discrepancies between local and QC?**
A: LLM non-determinism + distributed environment differences. QC does cross-calibration runs + retries that local doesn't. 0/4 from QC = will fail at pipeline. 4/4 from QC = reliable pass (task too easy).

**Q: Harbor check infrastructure failures?**
A: QC team working on it. High pipeline traffic causing queue bottlenecks. Use local validation scripts (Andrew's check script + harbor agent repair zip from announcements) to fix locally before uploading.

**Q: End-to-end video for connector tasks?**
A: No end-to-end video exists. Workflows are identical to non-connector with primary difference being MCP server interaction and altered file structure.

**Q: Cloudflare access?**
A: Security team implemented after breach. Login with Turing email. Post email in channel thread if auth fails.
