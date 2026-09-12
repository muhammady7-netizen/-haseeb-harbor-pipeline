# 03 · Traceability — hidden and unasked requirements

**The most common serious defect.** Present in 58% of audited tasks, and the highest
high-severity ratio of any category. Under binary reward, one of these zeroes a correct run.

A hidden requirement is a reward-bearing check demanding a value, column, wording or convention
that `instruction.md` — and any policy it names — never asks for.

## Applicability probe

For each check, try to quote the prompt sentence it enforces. Any check you cannot quote for is a
candidate. `contract.json.requirements[].quote` is your source of truth; the lint codes `A1b` and
`A1c` are hints, not proof.

## Diagnose

For every reward-bearing check, produce:

- `check` — its name and the exact expected value / pattern
- `claimed_requirement` — what it appears to enforce
- `prompt_basis` — the **verbatim** sentence from `instruction.md` or a named policy, or `NONE`

`NONE` means hidden. Also hidden, though subtler:

- **Wrong business grain.** The check joins at opportunity level; the prompt defines an
  account-level rule.
- **Incidental golden detail.** The check enforces a phrase the golden happened to use.
- **Silently-resolved ambiguity.** The check picks one side of a `contract.json.open_questions`
  entry that the prompt never settles — a missing-ledger-is-zero convention, a rounding rule, a
  boundary inclusivity.

**Read the golden's rationale before repairing.** Hidden requirements usually originate there:
the golden asserted a fact, and the check was written to enforce it. That tells you whether the
requirement is *real* (→ disclose) or *incidental* (→ drop).

## Fix — route each to one of four directions

Use `reference/invariant.md`. In practice:

**Drop** — no analytic weight. Most demands on exact wording, byte form, a figure the prompt
never asked the prose to state. *Needs decision.*

**Relax** — real requirement, several faithful renderings. Widen it. *Safe*, with a valid-output
regression.

**Relocate** — must be exact, but prose cannot carry it fairly. Move the assertion to a structured
surface the golden already produces. *Safe.*

**Disclose** — real requirement, form genuinely matters. Add a sentence to `instruction.md`.
*Needs decision, always.*

Disclosure rules, if the user approves one:

- Disclose **representation**, never the answer. Format, vocabulary, which topics must be
  covered — never the finding values.
- If the sentence reads as a transcription of the verifier, you have picked the wrong direction.
  Drop instead.
- Prefer renaming an ambiguous field to self-document (`preserve_count` →
  `missing_preserve_count`) over adding a paragraph of gloss.

## Prohibited

- Leaving a hidden requirement as-is.
- Editing `instruction.md` without a user decision.
- Disclosing a value the agent was supposed to derive.
- Justifying a hidden requirement as difficulty. Withheld requirements do not buy difficulty —
  measured across 301 tasks, fully-disclosed packages scored *higher* observed difficulty.

## Acceptance

Every surviving reward-bearing check cites a specific prompt or policy sentence. Deleting any
incidental golden phrase from a submission does not change reward.

## Return

```json
{"step":"03","applicable":true,"verdict":"needs_decision",
 "files_changed":["tests/verifier.json"],"findings":3,
 "needs_decision":{"what":"delete check","verifier_quote":"(?i)PR-145.{0,40}74000",
   "prompt_quote":"name the photo carrying the largest single allocation",
   "proposed":{"old":"...","new":"..."},
   "alternative_if_declined":"narrow to \bPR-145\b, dropping the undisclosed figure"},
 "spillover":[],
 "one_line":"3 hidden requirements: 2 relaxed in place, 1 needs a drop/disclose decision"}
```
