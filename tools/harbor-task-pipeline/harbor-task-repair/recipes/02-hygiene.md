# 02 · Hygiene — structural defects that void everything downstream

**Goal:** catch the package-level faults that make every later measurement meaningless.

## Applicability probe

```bash
diff -rq <task>/tests <task>/environment/_app/tests 2>/dev/null
ls <task>/tests/
ls <task>/environment/_app/ | grep -i solution
python scripts/lint_verifiers.py <task> --json
```

## What to check

**1. Mirror drift.** Root `instruction.md` and `tests/` exist twice: at the package root and
under `environment/_app/`. The `_app/` copy is what is built into the container. If they differ,
either a past change never reached the container, or the two copies mean different things.

**CRITICAL:** if root and `_app` already disagree **on arrival**, do **not** silently sync them.
You do not know which is authoritative, and picking one changes what the task grades. Report both
versions and return `needs_decision`. You may only propagate divergences *you* create.

**2. Leaked answer key.** Nothing from `solution/` may appear under `environment/_app/`. If it
does, the model can read the golden trajectory and every score is void.

**3. Missing engine files.** `tests/` must carry the grading engine it needs — typically
`test_outputs.py`, `verifier_engine.py` or `rl_world_verifiers/`, `test.sh`,
`test_requirements.txt`, plus the verifier spec. A package that cannot grade itself fails intake.

**4. Ambiguous spec shape.** If both `tests/verifier.json` and `tests/manifest.json` exist and
declare *different* check sets, do not guess which is authoritative. Report it.

**5. Symlinks and escaping paths.** Already enforced by `scripts/protect_hashes.py`; if it
refused to run, stop here.

**6. Artifact-name drift.** Deliverable filenames the checks reference must exactly match the
filenames `instruction.md` discloses. A check reading `audit.csv` when the prompt says
`seo_audit.csv` fails every correct run.

## Fix

- **Missing engine file** → restore it from the package's own generation template. Do not
  hand-write engine code.
- **Leaked `solution/` under `_app/`** → remove the leaked copy. `coverage_strengthening`.
- **Artifact-name drift** → change the *check* to match the prompt, never the reverse. The prompt
  is the contract.
- **Mirror drift you created** → propagate root → `_app`.
- **Mirror drift on arrival** → `needs_decision`.
- **Two conflicting spec files** → `needs_decision`.

## Prohibited

- Auto-syncing a pre-existing mirror divergence.
- Choosing silently between conflicting `verifier.json` and `manifest.json`.
- Editing `instruction.md` to match a check's filename. Fix the check.
- Adding a file to `environment/` other than restoring a mirror of `tests/`.

## Acceptance

`diff -rq` between root `tests/` and `_app/tests/` is clean; no `solution/` content under
`_app/`; the engine files are present; exactly one authoritative spec; every referenced artifact
name appears verbatim in `instruction.md`.

## Return

```json
{"step":"02","applicable":true,"verdict":"fixed",
 "files_changed":["environment/_app/tests/verifier.json"],"findings":1,
 "needs_decision":null,"spillover":[],
 "one_line":"re-synced _app mirror after root verifier.json drift; no leaked solution/"}
```
