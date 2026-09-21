# 05 · Format — stop grading text, start grading values

**The highest-volume defect: 85% of audited tasks.** 64.7% of all shipped non-connector
verifiers are regexes over raw file text, which binds grading to column count, column order,
quoting, whitespace and line endings — none of which the prompt constrains.

## Applicability probe

```bash
python scripts/lint_verifiers.py <task> --json
```

Codes `A2` (regex over structured source), `A2b` (quote hack), `A3` (column-count coupling),
`A4` (row-order coupling). Zero of all four → `not_applicable`.

## The four shapes

| Shape | Tell | Why it fails correct work |
|---|---|---|
| Regex on structured source | `regex_match` + source type `csv`/`json`/`xlsx` | Grades presentation |
| Column-count coupling | `,.*,` in the pattern | Encodes an undeclared schema — two commas means three columns required |
| Row-order coupling | 2+ `\n` in the pattern | Requires a row order the prompt never asked for |
| Quote hack | `\x22?` or `"?` | The author is hand-implementing CSV quoting — wrong layer |

## Fix — in order of preference

**1. Evaluator module (best).** Move comparison into a task-specific source adapter returning
named typed fields; the spec then asserts on those.

> **Scope note.** `tests/rl_world_verifiers/` is the protected grading engine, but a **task's own
> adapter** under `sources/` is task-owned and editable. Adding or editing
> `sources/<task>_program.py` is in scope; editing the generic adapters (`csv.py`, `json.py`,
> `registry.py`, …) is not.

```python
# tests/rl_world_verifiers/sources/<task>_program.py
class EvaluateOutput(StrictModel):
    audit_rows_match: bool
    findings_correct: bool
    details: dict[str, str]
```

```json
{"name": "audit_findings_correct",
 "metadata": {"why_justification": "Prompt: 'flag any that breach the settlement-window policy'."},
 "source": {"type": "file", "file": {"type": "settlement_program", "command": "evaluate"}},
 "assertion": {"type": "deterministic", "expected": true,
               "deterministic": {"path": "$.findings_correct", "comparison": "equals"}}}
```

Keep a `details` payload so a failure names the offending rows — that is the diagnostic value the
old per-row checks were really providing, and one check preserves it.

**2. Parsed field comparison**, where the harness offers it: parse the CSV, select the row by
key, compare the field.

**3. Regex mitigation, last resort.** If the regex genuinely must stay: drop the `$` anchor,
remove separator counting, remove quote hacks, never span rows with `\n`. Say in your return that
this is a mitigation, not a fix.

## Normalise only what the prompt allows to vary

Line endings (CRLF/LF), surrounding whitespace, CSV quoting style, and — where the prompt does
not fix them — case, unit notation, and decimal/percentage form. Do **not** normalise away a
distinction the prompt actually requires.

## The mandatory proof — this is what makes conversion safe

One source skill forbids automatic regex rewriting outright, on the grounds that a silent rewrite
can narrow the valid set. That objection is answered by evidence, not by assertion:

> **Valid-output regression.** Produce at least one genuinely valid, non-golden submission
> — different quoting, different column order, equivalent numeric notation — and show it passes
> with zero rejections. Also confirm a wrong answer still fails.

**Conversion without this regression is prohibited.** With it, the change is provably
`equivalence_preserving`.

## Prohibited

- Converting without the valid-output regression.
- Widening a matcher so far it accepts wrong or missing answers. "Don't gut difficulty."
- Replacing one keyword regex with a bigger keyword regex.
- Working around a missing parser with a larger pattern — that is an infrastructure request.

## Acceptance

QUOTE_ALL-quoted CSV, CRLF line endings, reordered permitted columns and equivalent numeric
notation all produce the same verdict as the canonical artifact — and a wrong answer still fails.

## Return

```json
{"step":"05","applicable":true,"verdict":"fixed",
 "files_changed":["tests/rl_world_verifiers/sources/settlement_program.py","tests/verifier.json"],
 "findings":14,"needs_decision":null,"spillover":[],
 "one_line":"14 regex-on-CSV checks -> evaluator module; QUOTE_ALL+CRLF regression passes"}
```
