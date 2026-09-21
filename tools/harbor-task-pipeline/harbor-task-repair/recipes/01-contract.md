# 01 · Contract — build the requirement map, cold

**Goal:** derive, from the prompt alone, the complete list of what a competent agent is actually
required to produce. Every later step compares against this.

This is the highest-value step in the run and the easiest to ruin.

## THE COLD-READ RULE — read this before anything else

> **You must NOT read `tests/`, `solution/`, or `task.toml` in this step.**

Not to "check", not to "cross-reference", not "just to see the shape". If you read the checks
before writing your list, your list becomes a restatement of the checks — and a coverage gap is
by definition something the checks do not contain. You cannot find it by reading them.

This is why this step runs in its own subagent: the isolation is the mechanism.

**If you have already seen the verifiers** for any reason, say so in `one_line` and set
`"cold_read": false` in the contract. Do not pretend.

## Applicability probe

Always applicable. Never skipped.

## What you may read

- `instruction.md` — the authored brief. **Ignore the harness-injected
  `## Working environment` tail**; it is frozen boilerplate, not a requirement.
- Any input file the prompt names, and any policy document the prompt points to.
- Nothing else.

## Procedure

**1. State the primary objective in one sentence.**
*"This task primarily measures ___."* If you cannot write it from the prompt, that is itself a
finding — record it and continue.

**2. Enumerate every discrete requirement.** One row per requirement. For each:

- `id` — `R1`, `R2`, …
- `quote` — the **exact prompt words**, verbatim. No paraphrase. If you cannot quote it, it is
  not a requirement.
- `kind` — `deliverable` | `value` | `schema` | `rule` | `explanation` | `side_effect`
- `artifact` — which file or system it lands in
- `must_be_exact` — does the prompt fix the form, or only the fact?

Cover: each artifact, each computed figure, each naming or schema constraint, each ordering
rule, each exclusion, each prohibition, each required explanation.

**3. List the open judgement calls** — everything the prompt leaves genuinely ambiguous:
date-boundary inclusivity, NULL handling, which timestamp counts, prefix vs exact status match,
whether cancelled/test/partial records are in scope, output vocabulary, rounding.

These are the fault lines. A check that silently resolves one of these is a hidden requirement,
and step 03 will need this list.

**4. Note the vocabulary the prompt teaches.** If it gives a worked example writing
`hex_registered No`, then `No` is correct by construction. Record every such example — step 06
depends on it.

**5. Propose your own verifier set**, tier by tier, in 8–20 checks. This is your independent
answer to "what would a fair grader check?", and step 04 diffs the real set against it.

**6. Check redaction readability.** If placeholders, removed text, or broken grammar obscure an
identity, relationship, constraint or required action, the prompt is damaged. Record it — no
verifier fix can compensate.

## Output

Write `.harbor-repair/contract.json`:

```json
{"cold_read": true,
 "primary_objective": "...",
 "requirements": [
   {"id":"R1","quote":"save `breaches.csv` with one row per deposit and a `finding` column",
    "kind":"deliverable","artifact":"breaches.csv","must_be_exact":false}
 ],
 "open_questions": [
   {"id":"Q1","issue":"does 'completed' include partially settled deposits?","affects":["R4"]}
 ],
 "taught_vocabulary": [{"term":"No","context":"evidence column example"}],
 "proposed_checks": [{"tier":"T1","name":"breach_set_correct","covers":["R4"]}],
 "redaction_damage": []}
```

## Prohibited

- Reading `tests/`, `solution/`, or `task.toml`.
- Paraphrasing a requirement instead of quoting it.
- Inventing a requirement the prompt does not state, however obvious it seems. "Obviously they
  meant X" means you guessed — put it in `open_questions`, not `requirements`.

## Acceptance

`contract.json` exists; every requirement carries a verbatim quote; the primary objective is one
sentence; `cold_read` honestly reflects what you read.

## Return

```json
{"step":"01","applicable":true,"verdict":"fixed",
 "files_changed":[".harbor-repair/contract.json"],"findings":0,
 "needs_decision":null,"spillover":[],
 "one_line":"contract: 11 requirements, 3 open questions, cold read intact"}
```
