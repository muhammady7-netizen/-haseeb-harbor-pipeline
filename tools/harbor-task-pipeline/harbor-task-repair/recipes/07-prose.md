# 07 · Prose — grade claims, not tokens

**The largest single concentration of defects: 88% of audited tasks touch memo grading.** It
fails in both directions at once — rejecting correct prose *and* accepting keyword soup. A check
that does both has negative value.

Two audited verdicts, verbatim: *"keyword-salad memo passes all checks"*; *"memo verification
strategy is fundamentally gameable"*.

## Applicability probe

Any check whose source is `.md`, `.txt`, `.docx` or `.pdf`, or any `rubric` assertion over prose.
None → `not_applicable`.

## Diagnose

For each prose check ask three questions:

1. **Would a correct paraphrase fail?** → contract gap.
2. **Would a bag of the expected tokens, with no reasoning, pass?** → coverage gap. Test this
   literally: concatenate the expected literals into one line and run the check.
3. **Does it demand a value the prompt never asked the prose to state?** → that is step 03's
   hidden requirement; record it in `spillover`.

## Fix

**Grade the claim, order-independent, synonym-aware:**

```python
def memo_states_breach(memo_text, dep_id, status_words):
    t = memo_text.lower()
    return dep_id.lower() in t and any(w in t for w in status_words)
```

**Use an atomic rubric structure**, one claim per check, with an explicit failure branch:

```
PASS only if the memo states, for <entity>, that <relationship/outcome> AND gives <the reason>.
FAIL if: a bare label with no reason; the wrong entity; the entity is silently omitted.
```

Four properties that make a prose check sound:

- **Atomic** — one claim. Diagnosable, and stable across gradings.
- **Requires a reason, not a token.** If the memo must justify something, check for the value
  only correct reasoning produces — never for the word "because".
- **Phrase-agnostic** — the fact, not the wording.
- **Names the artifact it reads.**

**Declare at least 5 prose checks if you declare any.** With three, one wording miss costs 1.7%
of the run; with eight, 0.6%. Below five, prose variance starts to dominate the score.

**Rubric phrasing:** never write a check invertibly ("avoid X (means Y)"). A judge reads that
backwards under normal operation. Write `PASS only if … FAIL otherwise`.

## Prohibited

- Word-order regexes over prose.
- Requiring a figure the prompt did not ask the prose to state.
- Replacing one keyword regex with a larger keyword regex.
- Token presence standing in for reasoning.
- Letting form decide reward: prose variance must not zero a correct audit.

## Acceptance

Every correct paraphrase you tried passes. **A keyword-soup memo fails.** An inverted claim
fails. At least 5 T4 checks exist, or none do.

## Return

```json
{"step":"07","applicable":true,"verdict":"fixed",
 "files_changed":["tests/verifier.json"],"findings":6,
 "needs_decision":null,"spillover":["03: memo check required the figure 74000, undisclosed"],
 "one_line":"6 memo regexes -> atomic claim checks; keyword-soup memo now fails, 4 paraphrases pass"}
```
