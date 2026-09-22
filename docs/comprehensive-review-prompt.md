# Comprehensive Review — EKW / SVC-PC Harbor Task

You are performing a **Comprehensive Review** of a single harbor benchmark task using
everything produced around it: the task package, its evaluations (model-run
trajectories, rewards, DataOS/Oracle outputs), and any prior verification reports
(deterministic-checks output, a prior content-audit pass, tracker history). All of it
is laid out in your sandbox workspace — read the workspace-layout skill first for the
directory conventions and where to save any files.

Your job is **not to solve the task**. Judge whether it is a valid, high-quality
task: **complete & correct**, **unambiguous**, **aligned** (its rubric checks exactly
what the instruction asks, no more and no less), **exposure-free** (nothing about the
rubric or the answer leaked into the source material, the solver's view, or the
golden by accident), **well-covered** (the criteria together cover what the
instruction asks, without duplication or unfair bundling), and **reproducible**. Use
the evaluations and prior verifications as evidence, but form your own verdict —
prior QC passes in this corpus have been wrong before (a re-audit once found a
"golden-swap" claim was fabricated by a prior pass that never actually opened the
files; another time, the real defect was misdiagnosed as a different one entirely).
Open the files yourself.

Everything you need is in this document: the checks to apply are in §1, the process
to follow in §2, the verification bar in §3, the severity and verdict rules in §4,
and the exact output format in §5. Work through the checks, use the evaluations and
prior verifications as supporting evidence, then emit your verdict in the format §5
specifies.

If a skill this prompt references is unavailable in your workspace, say so in the
summary and mark any finding that depended on it `inconclusive` — do not substitute
a guess for the skill's guidance.

## Protect difficulty

Evaluation failures might be due to the model's inability to solve the task, not a task
defect. The task's difficulty should be preserved and not made easier to be solvable.
Only fail a check when the requirement is truly unreachable by the model/agent. Never
propose a fix whose effect is to make the task easier — remove unfairness (ambiguity,
misalignment, ungradeable handoffs, nondeterminism, leaked answers), never difficulty.
Dense or demanding source-document language that a careful reader can correctly parse
is difficulty, not ambiguity — before proposing a clarity edit, confirm the current
wording cannot be resolved by careful reading; if it can, leave it alone.

## Out of scope

The following are accepted project conventions, not defects. Do **not** flag them
under any check (including "other issues"), and do not propose "fixing" them:

- **Credentials/API keys referenced in `task.toml`** (e.g. `OPENAI_API_KEY`,
  `ANTHROPIC_API_KEY` under `[verifier.env]`). These are intentional, injected at
  grading time. Do not report these as secret exposure or reproducibility issues.
- **Judge determinism / panel-size findings at the corpus level.** `config.temperature
  != 0` with no panel, or a single-model judge panel, is a standing harness/policy
  decision for this corpus, not a per-task defect — do not fail 1.2 or 1.4 on this
  alone. It *does* become a real, per-task 1.2 finding if you have direct evidence
  (two runs of the *same* solution, or a repeated Oracle run) that disagree in
  outcome — cite the specific disagreement, don't infer it from the config alone.
- **Format-appropriate `not_applicable`/`skip` results from shared deterministic
  checks.** Checks built for SVC-PC's `judge.toml` correctly report `not_applicable`
  on EKW's `verifier.json` shape (and vice versa for a few EKW-only checks). That is
  expected, not evidence of anything.
- **A golden shipping an extra, genuinely ungraded bonus file** (not referenced by
  any rubric criterion) beyond the deliverables the instruction names. This is
  benign — only escalate under 1.6/1.7 if that extra file *is* graded by some
  criterion without ever being required of the solver.
- **Check F (Oracle) / Check G (Manual QC / Comprehensive Review) showing `NOT RUN`.**
  These are DataOS-side, deliberately out of the local/automated review loop — never
  treat their absence as a packaging or coverage defect.

---

This is an **EKW / SVC-PC harbor task**: `instruction.md` is the prompt; the
environment is `environment/data/` (EKW) or `environment/initial_workspace/`
(SVC-PC) plus a `Dockerfile`; the reference solution is `solution/golden_outputs/`
(one or more documents/spreadsheets) copied into place by `solution/solve.sh`; the
verifier is a **rubric**, not a deterministic test suite — `tests/verifier.json`
(EKW) or `tests/deliverables_*/judge.toml` (SVC-PC), a set of weighted, LLM-judged
pass/fail criteria whose weights sum to 1.0 and whose weighted mean is the reward.
Two build genres exist side by side and need different packaging checks: **native-
harbor** (Dockerfile does `COPY data/ /workspace/data/`, ships `tests/verifier_lib/`
+ `verifier_runtime.py`) and **rewardkit-hybrid** (Dockerfile does `COPY
initial_workspace/ /app/`, no `verifier_runtime.py`, grades via an installed
`harbor-rewardkit` package instead) — confirm which genre you're looking at before
flagging a "missing" file as broken; a file one genre needs is correctly absent in
the other.

## 1. Checks

Judge this task against the checks below. For **every** check, assign a severity of
`major`, `minor`, or `good` (see §4). Cite concrete evidence — file and line/cell, or
run name and exact output — rather than impressions. A non-`good` check also carries
a `suggested_fix` and a verified finding in Requirement / Evidence / Consequence form.

Where two checks could plausibly hold the same finding, file it once under the check
that owns it and cross-reference from the other (see §3.3):

- A criterion asserts something the instruction never required → **1.4**.
- A requirement has no criterion at all, criteria overlap/duplicate, bundle
  independently-checkable facts into one pass/fail, or the golden itself fails the
  rubric → **1.5**.
- Answer or rubric content was *exposed* to the golden, the source material, or the
  agent → **1.6**.
- The instruction's own claims contradict the attached source documents, or the
  golden's own prose misdescribes itself → **1.7**.

**1.1 — Solvability / correctness**
- [ ] The task is solvable as written (a correct solution exists).
- [ ] The environment / source material is consistent and internally usable — every
      file the instruction or rubric names actually exists, with an exact filename
      match, and is not sealed inside an unopened/unextracted archive or gated
      behind a missing conversion step for the task's build genre.
- [ ] The reference solution (`golden_outputs/`) satisfies the rubric on its own
      content — not just structurally, but factually: recompute at least the
      load-bearing figures independently from the source material and confirm they
      match what the golden states and what the rubric requires. A golden that
      doesn't match its own task's source data at all (wrong dataset, fabricated
      placeholder figures, mismatched entity names) is a **major**, not a metadata
      nitpick — verify this by opening the source files, not by trusting a prior
      pass's summary of them.
- [ ] If no reference solution ships with the task, judge the first two bullets on
      their own and say so in the justification — do not mark the whole check `n/a`
      for that reason.

**1.2 — Reproducibility**
- [ ] `solve.sh` runs end-to-end without error and produces exactly the deliverables
      the instruction/rubric expect (run it if you can, in a scratch workspace).
- [ ] The rubric's file-extraction path is deterministic: for spreadsheet
      deliverables, confirm formula cells carry a live, recomputed value rather than
      a stale/blank cache the grading harness would read verbatim. Where an
      automated check flags a spreadsheet-formula defect, verify it yourself
      (recompute the formula independently, e.g. from the actual source cells or
      with an XNPV/XIRR solver) before accepting the flag — third-party recompute
      engines have known false-positive classes on Excel Data Tables, XIRR over wide
      ranges, and `COLUMN()`/`ROW()`-relative references; a flagged cell that you can
      hand-verify as correct is not a defect.
- [ ] Where the evaluations contain multiple runs of the same solution (or a
      repeated Oracle run), check that their rewards agree; disagreement is direct
      evidence of judge nondeterminism (see "Out of scope" for when this is/isn't a
      per-task finding).

**1.3 — Ambiguity**
- [ ] The instruction describes a single, well-defined expected behavior.
- [ ] There are no contradictory or out-of-scope requirements.
- [ ] Inputs, outputs, and edge-case behavior are specified clearly enough that two competent solvers would converge on the same intended behavior.
- [ ] Before alleging ambiguity, identify **two materially different** reasonable interpretations of the required outcome that the full package does not resolve. Different wording alone is insufficient, and dense-but-parseable source language is not ambiguity (see "Protect difficulty").

**1.4 — Instruction ↔ rubric alignment**
- [ ] Criteria check only behavior the instruction requires or clearly implies; none asserts behavior that contradicts or exceeds what the instruction can reasonably support.
- [ ] Criteria do not depend on implementation details the instruction left open (internal structure, naming, formatting it never specified).
- [ ] Every criterion is traceable to a specific requirement in the instruction; flag any criterion whose expected behavior cannot be justified from the instruction alone.
- [ ] Every criterion's `how_justification`/`why_justification` metadata (where present) genuinely describes how it's graded and why it matters — not a placeholder string, and not a truncated copy of the criterion's own prompt text. This does not affect grading (the criterion's real `assertion`/`rubric.prompt` is what's graded), so treat a broken justification field alone as at most **minor**.

**1.5 — Rubric coverage & calibration**

What this check judges is the task's rubric, not the evaluation runs — the runs are
only evidence about that rubric. A good rubric is sound (passing it implies the task
was solved) and complete (a correct solution always passes). Judge each direction by
trying to construct a counterexample rather than by impression; describing one
concretely is enough — you do not have to write or run it.

- [ ] Coverage: every behavior the instruction requires is checked by at least one criterion. Map each requirement to the criterion/criteria that verify it, and flag any requirement left unmapped.
- [ ] Exploitable criteria (soundness failure — a wrong solution passes): try to construct a solution that passes every criterion while violating the instruction — echoing rubric-adjacent language without real analysis, a criterion satisfied by boilerplate, or a value pinned so loosely it accepts a wrong answer. If one exists, report the exploit.
- [ ] Brittle criteria (completeness failure — a correct solution is rejected): try to construct a clearly correct solution a criterion would reject — a valid alternative figure, format, or characterization the instruction permits. If one exists, report the criterion and the legitimate variation it rejects.
- [ ] Duplicate or near-duplicate criteria: two criteria testing the same underlying fact (identical or near-identical prompt text) silently double- or triple-weight that fact relative to everything else in the rubric. Flag any pair you find, quoting both.
- [ ] Compound criteria: a single pass/fail bundles multiple **independently-variable** facts (e.g. two separately-assignable codes, or dispositions for several distinct line items) such that a solver could get most of them right and still fail the whole criterion with no partial credit. Distinguish this from a single criterion with several logically-dependent sub-parts of one decision (not compound) — check whether the same underlying facts are graded more granularly elsewhere in the rubric (e.g. a sibling deliverable splits the same facts into separate criteria); that asymmetry is strong evidence of a real compound-criterion problem, not just rubric style.
- [ ] Unsourced rubric content: a criterion's `Expected`/prompt text names a specific value, filename, or alternative that does not appear anywhere in the actual source material — search the real extracted text (see 1.6), not just the instruction. This is distinct from the golden simply computing a derived figure; it applies to values the rubric claims are *sourced*.
- [ ] The golden itself must pass its own rubric: for every criterion, check whether the golden's actual content satisfies it. A rubric value that contradicts what the golden legitimately computed (under a reading the instruction itself permits) is a real defect in the rubric, not the golden.
- [ ] Evidence from the evaluations: a run that scored a pass without genuinely solving the task demonstrates a soundness failure instead of merely hypothesizing one — fail this check, cite the run and the exact evidence, and treat several runs through the same gap as stronger evidence of severity. A run whose work genuinely satisfies the instruction yet was graded a fail is the same kind of evidence for brittle criteria — confirm the work really is correct first, since a failure is more often the model's inability. Finding no such run does not by itself make the rubric sound or complete; the bullets above decide that.
- [ ] If the package contains no evaluation runs, judge the static bullets above and record the evaluations-evidence bullet as `inconclusive` rather than treating absence of runs as a pass.

**1.6 — Answer exposure & solver isolation**
- [ ] The golden is derivable from the instruction and the named source material alone; nothing about the rubric has been copied into it, and no rubric-only value/term appears in `environment/data/` (or `environment/initial_workspace/`) unless it's genuinely disclosed to the solver there too.
- [ ] Actively search — do not just read and hope. Extract real text from every source file (openpyxl/python-docx/pdf text extraction; never raw byte-grep on a binary xlsx/docx/pdf, which reliably misses real hits and produces false "undisclosed" findings). Check for: literal expected values from the rubric, rubric-only terminology, and any filename suggestive of an answer key.
- [ ] Check whether any file in the source material suspiciously matches or duplicates content from `golden_outputs/` — a real leak vector distinct from a simple wrong-golden mixup (see 1.1).
- [ ] No evaluation run passes by relying on rubric-only knowledge — the solver never sees `tests/`/the rubric file at agent runtime.
- [ ] For suspected exposure, establish current-task answer content **and** actual agent-runtime access (trajectory, generated artifact, or a controlled probe). Reviewer-side file presence alone is insufficient; absence of an observed read also does not prove isolation — if you cannot settle it either way, record `inconclusive`.

**1.7 — Source-document & prompt internal consistency**
- [ ] The instruction's own factual claims (dates, entity types, figures it states outright) agree with what the actual attached source documents say. Where they disagree, determine which side the *majority* of independent evidence supports — including the golden's own computation basis — before deciding which one is the error; do not assume the instruction is always right, and do not assume the source document is always right.
- [ ] The golden's own prose (a memo referencing its own companion workbook, a reasoning document citing a section/tab) accurately names what it's referencing — a stale/wrong filename or section reference in the golden's own text is a real, if usually cosmetic, defect.
- [ ] Where two source documents disagree with each other on a fact the golden/rubric depends on, and the golden/rubric adopted the wrong one, identify which document is authoritative (e.g. a primary source document vs. a summary tab quoting it) before concluding which value is correct.

**1.8 — Environment packaging & errored runs**

This check covers two independent concerns. Assess both, file them as numbered points
(1) packaging and (2) errored runs per §3.3, and give the check the more severe of the
two severities.

- [ ] (1) Environment size: measure the task directory / built context. If it exceeds ~10 MB, large data must be tracked externally rather than inlined — flag an oversized environment that bundles bulky data.
- [ ] (1) Reachability: every file the instruction, rubric, or `solve.sh` references actually exists at agent runtime, is not sealed inside an unopened archive, and is not gated behind a missing genre-specific conversion step (e.g. a rewardkit-hybrid task shipped without ever running its conversion, so `environment/initial_workspace/` — which its own Dockerfile requires — was never generated). Check `solve.sh` for hard-required files that don't exist in `golden_outputs/` and aren't actually needed by any rubric criterion — a stale copy-script requirement from an older template convention, not a real content gap; verify by running `solve.sh` and by confirming no criterion reads the missing file.
- [ ] (2) For every eval with an exception or a crash with no reward, read the full exception (do not truncate) and diagnose it with the exception-diagnosis skill **before** dismissing it as infrastructure noise. Classify each as actionable or ignore, and only propose task fixes for ones the skill marks actionable.
- [ ] Actionable failures (broken Dockerfile/build, missing runtime dependency, insufficient rubric/verifier timeout, missing reward file) are flagged with a concrete task fix.
- [ ] Infra/provider noise is ignored (not treated as a task defect). Timeouts in a small fraction of runs are likewise ignored; timeouts hitting most or all runs are *not* noise — treat them as evidence of an insufficient time limit or a hanging environment and diagnose them as actionable.

**1.9 — Task metadata correctness**
- [ ] `task.toml`'s `[metadata]` block (`domain`, `occupation`, `sector`, `subdomain`, `task_type`) is populated (not blank) and actually matches the task's real content. Classify domain/occupation/sector against the controlled vocabulary actually in use across the corpus (do not invent new category values); subdomain/task_type may be more free-text but should still describe the real content, not a copy-pasted or transposed label from an unrelated task.
- [ ] Check specifically for values that look copy-pasted from a different task (a mismatched genre label, or a `subdomain`/`task_type` pair that reads as though it belongs to a *different*, similarly-named sibling task — check the sibling directly if one exists).
- [ ] This is typically **minor** (fixable, no effect on grading/scoring) — but still a real defect to report and fix, not a cosmetic item to wave off, since it affects how the task is catalogued and discovered.

**1.10 — Other issues (optional)**
- [ ] Flag any other problem not covered by the checks above that undermines the task's validity, correctness, fairness, or reproducibility. Mark `good` if nothing else is wrong. Cosmetic/hygiene issues with no established content or scoring effect stay out of the rework count unless they change grading.

## 2. Process

1. Read the instruction and restate, in one sentence, the single intended behavior.
2. Identify the build genre (native-harbor vs rewardkit-hybrid) from the Dockerfile
   before assessing packaging — a file one genre needs is correctly absent in the
   other.
3. Inspect the environment / source material and confirm it is consistent and
   reachable. Confirm required inputs were available at **agent runtime** (not
   sealed in an archive, not behind a missing conversion step).
4. Map each rubric criterion to the requirement it covers; note any requirement with
   no criterion, any criterion with no requirement, any duplicate/near-duplicate
   pair, and any criterion bundling independently-variable facts. Try to construct a
   wrong solution that still passes and a correct solution a criterion would reject.
5. Open `golden_outputs/` and independently recompute at least the load-bearing
   figures from the actual source material. Confirm the golden satisfies the rubric
   on its own content, is reproducible (`solve.sh` runs clean), and is free of
   exposure. An Oracle/golden pass shows compatibility with the grader; it does
   **not** by itself prove the golden matches this task's real source data — verify
   that directly.
6. Check task.toml metadata against the corpus's real controlled vocabulary and
   against sibling tasks for signs of copy-paste or transposition.
7. Check the instruction's own factual claims against the source documents, and the
   golden's own prose against its own referenced filenames/sections, for internal
   contradictions.
8. Measure the environment size and confirm large data is tracked externally and
   every referenced file is actually reachable.
9. Review the evaluations (trajectories, rewards, outputs) and prior verifications,
   watching for runs that scored a pass without doing the real work and for capable
   agents failing or disagreeing. Diagnose any errored runs as described in 1.8(2).
10. For each suspected defect, **verify** it (§3) before assigning severity —
    including re-deriving any figure an automated check flagged, since spreadsheet
    recompute engines have known false-positive classes. Adjudicate once per root
    cause — do not count every downstream symptom as a new finding.
11. Decide a severity per check (`major` / `minor` / `good`), then an overall verdict (§4).

## 3. Verify every issue (required)

Severity is separate from evidence status. Do not file a defect you have not checked
against the package and runs. Do not turn an evidence gap into a fictional defect.
Do not accept a prior review's finding (including this task's own tracker history)
without independently opening the files it claims to describe — this corpus has
already had at least one confirmed case of a review fabricating a "golden-swap"
finding that direct inspection disproved.

### 3.1 Evidence status (per finding)

For each distinct claim, record one of:

- **confirmed** — you opened the cited files/runs (or ran a decisive probe) and the
  observation holds.
- **refuted** — counterevidence shows the claim is wrong; drop it from the active
  findings (you may note it briefly as overturned).
- **inconclusive** — a required check could not be completed (missing artifact, scorer
  unavailable, blocked access). Keep the question explicit. An inconclusive gap is
  **not** a `minor` defect and must not be invented into a `pass`/`fail` story.
- **not_applicable** — the check genuinely does not apply to this task, so there was
  nothing to verify. Pair it with `result: "n/a"`.

Only **confirmed** defects may receive `major` or `minor`.

**Recording an inconclusive check.** Report it as `severity: "good"`, `result: "pass"`,
`evidence_status: "inconclusive"`, and state in the `justification` exactly what could
not be verified and why. You must also name it in `summary`. If the verification is
verdict-relevant (it could plausibly have produced a `major`/`minor`), it blocks
`accept` — see §4. If the verification was impossible because the environment, rubric,
or required inputs are broken, that is itself a **confirmed** packaging defect under 1.8,
not an inconclusive gap.

### 3.2 How to verify

1. Reconstruct the contract from the instruction and agent-visible files **before**
   trusting the rubric, the golden, or prior QC prose.
2. Open the actual artifacts (agent outputs, `test-stdout.txt`/`runtime.log`,
   `reward.txt`/`reward.json`, `verifier-report.json`) — a trajectory saying "done"
   does not establish completion; a criterion name alone does not establish what was
   graded. For spreadsheet deliverables, open them directly (openpyxl/formulas) and
   recompute — do not trust a memo's stated figure or an automated check's verdict
   without independently deriving the number yourself.
3. Trace the active grading path: which criterion fired, what it expected, and how
   that maps to a prompt requirement.
4. When the concern is decisive (false rejection, false credit, or blocker), use a
   recorded run or a **focused probe** that changes one fact and preserves the rest.
   Save what you changed, what was graded, and what the result proves. One stochastic
   result does not establish a guaranteed exploit.
5. Attribute cause correctly before severity:
   - **task defect** (prompt ambiguity, prompt↔rubric misalignment, coverage/soundness gap,
     golden/rubric wrong or mismatched, packaging blocker, answer exposure, source
     document internal contradiction);
   - **agent error** (supported requirement violated — do not rework the task for this alone);
   - **infrastructure** (provider, network, harness — do not force into ambiguity).
6. Write each retained finding as **Requirement → Evidence → Consequence**:
   - Requirement: governing instruction/rubric/source rule and locator.
   - Evidence: exact file:line/cell, evaluation/run id, criterion name, observed value or probe result.
   - Consequence: why this changes the score, blocks completion, or invalidates the judgment.

### 3.3 Root cause before count

If one missing input or one unstated rule causes several failing criteria, record
**one** root cause and list affected checks — do not file six independent coverage
findings. Write the finding in full under the check that owns it (§1 routing rules),
list the other affected check ids in that check's `related_checks`, and from each
affected check reference the owning id instead of restating the finding. Independent
defects (e.g. a missing input **and** an unrelated metadata error) may still share a
check id as numbered points (1)/(2).

Note the two different things being counted: `major_count` / `minor_count` count
**checks** at that severity, while `summary` reports the number of distinct **root
causes**. A single root cause spanning three checks is one root cause and up to three
non-`good` checks.

## 4. Severity and overall verdict

Use **exactly** these three severity values. Do **not** use low / medium / high /
critical / NA. (`n/a` and `not_applicable` are values of `result` and `evidence_status`
respectively — never of `severity`.)

| Severity | Meaning | Effect on the task |
|---|---|---|
| **major** | A **confirmed** defect that materially changes validity of the central deliverable or its grading: rejects a substantially valid, instruction-compliant result; rewards central wrong/missing content; the golden fails to satisfy the rubric on its own actual content (including a golden-swap); breaks the packaging/environment/rubric so grading cannot be trusted; or otherwise blocks source-grounded completion. | **Task failure.** Overall verdict cannot be accept. |
| **minor** | A **confirmed** localized defect with limited impact on an otherwise assessable task. It still requires correction. Typical minors: unexploited soundness/hardening gaps, blank/wrong/transposed task metadata, broken justification metadata, a stale filename reference in golden prose, reference-quality issues that did not fail a legitimate run, narrow underspecification that no compliant run lost to. | **Fixable; may still fail shipping.** Overall is at best `needs_revision`. |
| **good** | No confirmed issue on this check after the relevant verification (or the check is genuinely `n/a`, or the verification is `inconclusive` per §3.1). | No rework from this check. |

### Decisive test for major vs minor

Look at the actual evaluation runs and your verification. A defect is **major** if
either direction below holds:

- **False rejection.** Agents (or a constructed correct alternative) that satisfy the
  instruction **as written** were failed by the rubric because of the defect.
- **False credit.** A run scored a pass without doing the central work, or you
  demonstrated a concrete exploit that passes every criterion while violating the
  instruction, or answer exposure undermines the success evidence, or the golden
  itself does not actually satisfy its own rubric. Note that "all relevant runs
  passed" is *not* reassurance here — passing runs are exactly the symptom of this
  direction.

It is usually **minor** when every agent failure is ordinary skill shortfall, and the
gap is real but unexploited and non-score-driving (no run took it, and no concrete
exploit was constructed — only a hypothetical weakness), or when the defect (e.g.
metadata) has no scoring effect at all.

Explain **impact**, not criterion count. Multiple failing criteria from one root
premise remain one finding.

### Overall verdict (apply in order; take the first that matches)

- `invalid` — a **major** environment/packaging/harness defect: Dockerfile/build broken,
  required runtime inputs missing or unreachable, the rubric cannot run or never writes a
  reward for non-infra reasons, committed starting state contradicts the instruction. The task
  could not be fairly evaluated as shipped.
- `reject` — environment is fine enough to grade, but at least one **major** design defect
  remains (unsolvable as written; core misalignment or brittleness that failed compliant
  work; central false credit / exploitable criteria; the golden fails its own rubric; answer
  exposure that undermines success evidence).
- `needs_revision` — **no** major findings, but either at least one **minor** remains, or a
  verdict-relevant verification is `inconclusive` (§3.1). Minors must be fixed under the batch
  rubric and may still prevent accepting the task until addressed. This verdict is legitimate
  with `minor_count: 0` when it is driven by an inconclusive verification — say so in `summary`.
- `accept` — every check is `good` with `evidence_status` of `confirmed` or `not_applicable`,
  and no verdict-relevant verification is outstanding.

Summary rule of thumb: **any major → task fails** (`invalid` or `reject`); **only minors or an
unresolved verdict-relevant gap → needs_revision**; **all good and fully verified → accept**.

## 5. Output

Write your review as prose first — reasoning, evidence, and probes. Then close the
message with the JSON object below as the **final content**, with no text after it and
no code fence around it. (The fence in the example is illustration only; do not
reproduce it.)

```json
{
  "benchmark": "ekw | svc-pc",
  "task_id": "<id of the task being verified; take it from task.toml, or the task directory name if absent>",
  "overall_verdict": "accept | reject | invalid | needs_revision",
  "summary": "<1-3 sentence explanation of the overall verdict, including major/minor check counts, the number of distinct root causes, and any incomplete verification>",
  "major_count": 0,
  "minor_count": 0,
  "checks": [
    {
      "id": "1.1",
      "name": "Solvability / correctness",
      "result": "pass | fail | n/a",
      "severity": "major | minor | good",
      "evidence_status": "confirmed | refuted | inconclusive | not_applicable",
      "related_checks": [],
      "justification": "<Requirement / Evidence / Consequence for each retained finding; empty or brief pass note if good>",
      "suggested_fix": "<how to fix; null when severity is good>"
    }
  ]
}
```

Rules:
- `checks` must contain one entry for every check above (1.1–1.10), in order, with
  every field present on each entry.
- `severity` is the primary judgment and is required on every check. Use `major` or `minor`
  only with `evidence_status: confirmed`. Use `good` when no concern survived verification,
  when all raised concerns were `refuted`, when the check is `n/a`, or when the verification
  is `inconclusive` (§3.1).
- `result` is derived from `severity`: `fail` when severity is `major` or `minor`; `n/a` when
  the check genuinely does not apply; otherwise `pass`.
- `related_checks` lists the ids of other checks affected by the same root cause (§3.3);
  use `[]` when there are none.
- `major_count` / `minor_count` must equal the number of **checks** with that severity.
- `overall_verdict` must follow §4: any `major` → `invalid` or `reject`; else any `minor`
  or outstanding verdict-relevant `inconclusive` → `needs_revision`; else `accept`.
- `suggested_fix` is required for `major`/`minor`, and `null` for `good`. A fix must remove
  unfairness without reducing difficulty ("Protect difficulty").
- Use `n/a` only when a check genuinely does not apply — not as a way to avoid deciding, and
  not as a substitute for `inconclusive`.
- Every non-good `justification` cites verifiable evidence (file:line/cell and/or run id +
  observed output) and states consequence for grading or completion.