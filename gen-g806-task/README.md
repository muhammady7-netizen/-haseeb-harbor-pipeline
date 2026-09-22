# gen-g806-leadership-brief-rhetorical-style-audit

Audit a leadership brief for rhetorical style issues. Deliverables: script_style_audit.csv, style_audit_memo.md, results.json.

## What makes this non-trivial

- Finding classification requires reading the brief and identifying rhetorical patterns
- Memo must explain each finding with domain vocabulary
- Results.json counts must match the audit CSV

## Bundle contents

- environment/input/: Leadership brief and supporting documents
- solution/files/: Gold deliverables (CSV audit, memo, results.json)
- tests/verifier.json: 14 deterministic checks
