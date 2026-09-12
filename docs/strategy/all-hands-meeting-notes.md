# All Hands Meeting - Practical Approach for Task Acceptance (Sep 11, 2026)

## Key Takeaways

### Understanding Tasks
1. Read instruction.md and policy end to end before opening data files
2. Understand what each row represents, identify unique identifiers, map file relationships
3. Run a baseline battery and READ trajectories (not just scores) to find model assumptions

### Hardening Tasks (DOs)
- Put difficulty in the DATA, not in rules/instructions
- Create realistic data situations where model assumptions are proven wrong
- Test ideas before building: name exact wrong answer, check if model catches it
- Keep all artifacts consistent (prompt, solution, tests, manifest, environment)
- Run 4 battery runs, not just 1
- Triage every failure to a step and wrong value
- Change one thing per version

### Hardening Tasks (DON'Ts)
- Adding rules/instructions is NOT hardening (model turns them into code)
- Adding volume is NOT difficulty (scripts crunch large files easily)
- Don't give away answers in prompts (e.g., exact duplicate row numbers)
- Don't make verifiers overly strict about exact phrasing (except filenames, codes, JSON keys)
- Don't change tasks for INDETERMINATE/capture failures - rerun first
- After two builds with no change, stop turning the same dial

### Verifier Fairness
- Be strict only where format is genuinely pinned (filenames, schemas, codes, JSON keys)
- Memo wording needs room for natural alternatives
- Read meaning of sentences, not just keyword presence
- Give every verifier repair a positive and negative regression test
- Don't let one shared setup phrase break multiple checks

### Finalization QC
- Start with the exact version QC reviewed
- Treat instruction and policy as public contract
- review.csv needs all 14 areas resolved with task-specific notes
- ZIP should contain exactly one task root with no caches/temp reports
- Don't confirm findings - fix in source

### Yellow-Marked Tasks
- No action required - backend automation handles them
- QC team will assist in getting tasks accepted