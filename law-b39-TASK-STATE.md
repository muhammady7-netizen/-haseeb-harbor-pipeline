# law-b39-l16 Task — Current State (18 Sept 2026)

## Portal Status: v5 — Review Required (3 blocking findings)

**Oracle: Passed 1.0 | GLM: 1/4 passed (excellent difficulty) | PreQC: 0 findings | D1-D5: clean**

## 3 Blocking Findings to Fix

### Finding 1: layer1_realism_leakage__domain_correctness (ST-508 gold wrong)
- ST-508: subject=behavioural_plan, cited_entry=OI-207 (same subject)
- RP-401 says CL-308 governs (clarification speaks to behavioural_plan)
- Gold says AT_ODDS/OI-207 but should be VERIFIED/CL-308
- **Fix**: Change ST-508 in verifier.json + solution/files/letter_line_review.csv from AT_ODDS/OI-207 to VERIFIED/CL-308
- Update counts: verified 104→105, at_odds 177→176
- Update answer_at_odds_figure regex from 177 to 176
- Update results.json, golden_results.json, golden_result.json, answer.md
- Update all artifact dirs + trajectories

### Finding 2: layer5_reward_hacking_static (verifier.json readable by agent)
- tests/verifier.json contains complete gold answer key (325 verdicts + 4 totals + figure)
- Mounted at /tests in same container where agent runs as appuser
- Agent can read /tests/verifier.json and copy gold values → reward 1.0 without doing work
- **Fix**: Make /tests unreadable by appuser during agent phase
  - Add to Dockerfile: `RUN chmod 000 /tests` or `RUN chown root:root /tests && chmod 700 /tests`
  - Or: Add to test.sh: `chmod 755 /tests` before running verifier (restore for grading)
  - Or: Mount /tests as read-only for verifier only, not for agent

### Finding 3: layer5_reward_hacking_static__sanctioned_interface_use (same root cause)
- Same as Finding 2 — /tests is not a sanctioned interface for the agent
- **Fix**: Same as Finding 2

## Files to Update
1. `tests/verifier.json` — ST-508 verdict + counts + regex
2. `solution/files/letter_line_review.csv` — ST-508 row
3. `solution/files/results.json` — counts (105/176/44/162)
4. `solution/golden_results.json` + `golden_result.json` — same counts
5. `solution/files/answer.md` — figure 176
6. `solution/golden_trajectory.json` — embedded CSV + results
7. `environment/Dockerfile` — protect /tests from appuser
8. All artifact dirs (oracle + 3 stability × app + logs/artifacts/app)
9. All trajectory.json files
10. All score.json + reward.txt files
11. `review.csv` — update notes
12. `README.md` — update counts

## Version History

| Version | PreQC | Oracle | GLM | Harbor Check | Status |
|---------|-------|--------|-----|-------------|--------|
| v1 (old) | D18 | - | - | - | JSON broken |
| v1 (new) | 0 | - | - | - | - |
| v2 (new) | 0 | Passed | 2/4 | 4 findings | Fix needed |
| v3 (new) | 0 | Passed | 3/4 | 2 findings (submission_format) | Fix needed |
| v4 (new) | 0 | Passed | 3/4 | 2 findings (instruction_verifier) | Fix needed |
| **v5** | **0** | **Passed** | **1/4** | **3 findings** | **Fix needed** |
