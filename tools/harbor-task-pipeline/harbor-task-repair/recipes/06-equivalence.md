# 06 · Equivalence — correct meaning rejected

**53% of audited tasks.** The check grades a surface expression instead of the fact,
relationship or invariant the prompt asked for, so a correct answer phrased differently fails.

## Applicability probe

For every literal expected value, ask: **does this exact string appear in `instruction.md`?**
Use `contract.json.taught_vocabulary`. Any status word, verdict token or phrase the check demands
but the prompt never uses is a candidate.

## The three shapes

**1. Synonym gap.** The prompt's own worked example writes `hex_registered No`; the check demands
the literal `False`. A model that followed the prompt exactly is marked wrong. This is the purest
form and always a defect.

Also: `takes priority` rejected where `has priority` is correct; `extension` rejected where
`extend…` was matched; a policy's own wording (`strictly between 0 and 1`) rejected.

**2. Narrow-to-golden.** The check accepts only the reference route — an undisclosed tag
ordering, a decimal format, a fixed finding order, one specific method where an equivalent
reaches the same outcome.

> Ask of every check: **does this require *how* the model got there, or only *that* it got to the
> right place?**

**3. Representation coupling.** The fact is right but expressed in another valid form: `1,234.50`
vs `1234.5`, `50%` vs `0.5`, ISO vs written date, a set in a different order.

## Fix — in order of preference

**1. Grade the prompt's vocabulary.** If the prompt teaches `No`, accept `No`. This is not a
widening; it is a correction.

**2. Normalise in code**, inside the evaluator module — casefold, strip, map a documented synonym
table, canonicalise numeric notation. Best option: the synonym set lives where it can be
reviewed, rather than sprawling inside a pattern.

**3. Explicit alternation**, only when a parser is not available:
`(?i)\b(no|false|not registered)\b`.

**4. Compare parsed sets, not ordered strings**, for anything order-independent.

Keep relationship direction explicit so keyword presence alone cannot pass: an inverted or
contradictory statement must still fail.

If order genuinely matters, keep the constraint — but as a **separate, clearly named** check
(`basis_tags_in_policy_order`) so its failure is legible and deliberate.

## Prohibited

- Grading a literal that does not appear in the prompt.
- Widening until a wrong answer passes. Every widening keeps a rejection case.
- Replacing a narrow keyword regex with a broader keyword regex — that is the same defect,
  larger.
- Normalising away a distinction the prompt requires.

## Acceptance

A reviewed set of correct paraphrases passes; an inverted or contradictory statement fails.
State which paraphrases you actually tried — a clean verdict is a claim, not a default.

## Return

```json
{"step":"06","applicable":true,"verdict":"fixed",
 "files_changed":["tests/verifier.json"],"findings":4,
 "needs_decision":null,"spillover":[],
 "one_line":"4 synonym gaps fixed to prompt vocabulary; 3 paraphrases pass, inverted claim fails"}
```
