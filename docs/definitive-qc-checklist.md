# The Definitive Harbor-Shannon QC Checklist

Every check, algorithm, and decision rule extracted from:
- `harbor_shannon_qc.py` v1.3.1 (5,444 lines) — deterministic layer, model prompts, validators, verdict synthesis
- `verifier_defect_lint.py` — D1-D5 bundle linter
- `REPACKAGING-QC-GATE.md` — C1-C12 repackaging gate
- Portal findings (law-b39) + QC-SELF-TRAINING — semantic checks the deterministic layer cannot catch
- QC standards summary (obi-task-quality-standard, non-connector-task-standard, shannon-task-qc-north-star)

Each check is a yes/no question. "Yes" = the defect IS present (the task FAILS that check unless noted). Severity: P0 = reject/rework, P1 = rework, P2 = non-blocking, INFO = advisory. "Manual?" = can be checked by file inspection without running the model.

---

## LAYER 0 — Pre-flight / format / package structure

Source: `harbor_format_check`, `discover`, `instruction_path`, `verifier_spec_path`, `packaging_checklist`, portal crash on CRLF

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 0.0 | Do ANY files in the zip have CRLF (`\r\n`) line endings instead of LF? | P0 | Yes (scan bytes) | all .sh/.py/.json/.md/.csv/.toml/.txt files | Convert all to LF before zipping |
| 0.0b | Do ANY files in the zip have a UTF-8 BOM (`EF BB BF`)? | P0 | Yes (scan bytes) | all text files | Strip BOM before zipping |
| 0.1 | Is `task.toml` missing or unparseable? | P0 | Yes | `task.toml` | Repair task.toml |
| 0.2 | Does Harbor's `Task.is_valid_dir()` reject the directory? | P0 | Yes (if harbor installed) | `task.toml` | Fix the task layout |
| 0.3 | Is `instruction.md` (or `instructions.md`) missing? | P0 | Yes | root | Create instruction.md |
| 0.4 | Is the prompt file named `instructions.md` instead of `instruction.md`? | P2 | Yes | root | Rename to instruction.md |
| 0.5 | Is there no `tests/verifier.json` or `tests/manifest.json`? | P0 | Yes | `tests/` | Create a verifier spec |
| 0.6 | Is the verifier spec not valid JSON? | P0 | Yes | `tests/verifier.json` | Fix JSON |
| 0.7 | Is the spec named `manifest.json` instead of `verifier.json` (Shannon convention)? | P2 | Yes | `tests/` | Rename to verifier.json |
| 0.8 | Is `environment/Dockerfile` missing? | P1 | Yes | `environment/` | Add Dockerfile |
| 0.9 | Is `tests/test.sh` missing? | P0* | Yes | `tests/` | Add test.sh |
| 0.10 | Is `solution/golden_trajectory.json` missing? | P0* | Yes | `solution/` | Add golden trajectory |
| 0.11 | Is `solution/solve.sh` (or `solve.py`) missing? | P0* | Yes | `solution/` | Add solve script |
| 0.12 | Does `solution/tests/` exist (graders must live at task-root `tests/`)? | P0* | Yes | `solution/tests/` | Move to task-root tests/ |

*These are packaging_checklist FAIL rows → promoted to P1 by derive_deterministic_findings.

---

## LAYER 1 — Deterministic checks (no model needed)

Source: `derive_deterministic_findings`, `dockerfile_info`, `harness_info`, `leakage_scan`, `verifier_inventory`, `scan_regex`, `word_order_replay`, `realism_inventory`, `solution_inventory`, `hygiene_scan`, `hygiene_grep`, `drift_inventory`, `prompt_reference_check`, `builtin_counterexamples`, `run_counterexamples`

### 1a. Environment / Dockerfile

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 1.1 | Does the Dockerfile `FROM` line lack an `@sha256:` digest (floating tag)? | P1 | Yes | `environment/Dockerfile` | Pin by digest |
| 1.2 | Does the Dockerfile COPY `tests/`, `solution/`, `verifier.json`, `manifest.json`, `golden`, or `rubric.toml` into the agent-visible image? | P0 | Yes | `environment/Dockerfile` COPY lines | Remove the COPY; keep tests/ and solution/ outside /app |
| 1.3 | Does the Dockerfile reference `connectors-harness` while task.toml declares MCP connectors (merged image, no isolation boundary)? | P0 | Yes | `environment/Dockerfile` + `task.toml` | Run gyms in isolated sidecar |
| 1.4 | Do root task files differ from the `environment/_app` mirror (content hash mismatch)? | P0 | Yes | `environment/_app/` | Regenerate the mirror or delete it |
| 1.5 | Are there `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`, `qc/`, `qc-out/`, `.git` dirs inside the task tree? | P2 | Yes | task tree | Remove before packaging |
| 1.6 | Are there `.DS_Store`, `Thumbs.db`, `.pyc`, `.pyo` files inside the task tree? | P2 | Yes | task tree | Remove before packaging |
| 1.7 | Is there a `qc/` or `qc-out/` directory inside the task tree? | P0* | Yes | task tree | Remove (QC reports upload separately) |
| 1.8 | Is there a sibling `qc/` dir next to the task inside a `-m-vN` extract folder? | P0* | Yes | parent dir | Remove (QC is not part of the task zip) |

### 1b. Harness / test.sh

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 1.9 | Does a verifier path hard-code the judge model id (e.g. `openai/glm-5.2` literal, not `JUDGE_MODEL`)? | P1 | Yes | `tests/verifier.json` or `tests/manifest.json` | Resolve through JUDGE_MODEL env var |
| 1.10 | Does `test.sh` end with unconditional `exit 0`, write `0 > reward` on any non-zero, and NOT distinguish crash (status 2-5)? | INFO | Yes | `tests/test.sh` | Exit non-zero on collection/import errors |
| 1.11 | Does the verifier engine truncate source text at `max_content_chars` and is the largest gold deliverable >= 50% of that cap? | P2 | Yes | `tests/*.py` max_content_chars | Raise the cap or fail loudly |
| 1.12 | Does `task.toml` list `artifacts = []` while file deliverables exist? | INFO | Yes | `task.toml` | List deliverables in artifacts |
| 1.13 | Are `keywords` = `offline` while `network_mode = "public"`? | INFO | Yes | `task.toml` | Set network_mode = "none" if isolation needed |

### 1c. Leakage / answer-key exposure

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 1.14 | Is a gold deliverable byte-identical (`verbatim_copy`) to an agent-visible input file under another name? | P1 | Yes | `solution/files/` vs `environment/input/` | Remove the copy from environment/input |
| 1.15 | Is >= 90% of a gold deliverable's lines present in an unrelated agent-visible input (`near_verbatim`)? | P2 | Yes | gold vs input files | Verify it's source material, not leaked answer |
| 1.16 | Is >= half of gold prose sentences present verbatim in an unrelated input (`prose_overlap`)? | P2 | Yes | gold .md vs input .md | Confirm it's quoted policy, not leaked answer |
| 1.17 | Does `solve.sh` modify files under `input/` (rm/mv/sed -i/tee/>>)? | P2 | Yes | `solution/solve.sh` | Remove forbidden route |
| 1.18 | Does `solve.sh` reference `tests/` (grader) paths? | P2 | Yes | `solution/solve.sh` | Remove tests/ references |

### 1d. Prompt quality / hygiene

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 1.19 | Does the prompt name files that are NOT on the agent-visible surface? | P2 | Yes | `instruction.md` vs Dockerfile COPY map | Confirm each name resolves in container |
| 1.20 | Does the agent-visible prompt contain a harness framing line ("Delivery conventions for this run" / "added by the eval harness")? | P2 | Yes | `instruction.md` | Drop the line |
| 1.21 | Do agent-visible files contain benchmark/harness vocabulary (harbor, harness, dockerfile, infra/, benchmark, fixture, seeded, authoring, eval task)? | P2 | Yes | `instruction.md` + visible inputs | Reword to read like a colleague's request |
| 1.22 | Is `README.md` missing at the task root? | P1 | Yes | root | Add README covering what/why/bundle |
| 1.23 | Is `README.md` a stub (< 60 words)? | P2 | Yes | `README.md` | Expand |

### 1e. Verifier static signals (`scan_regex` + per-check scan)

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 1.24 | Does any verifier regex fail to compile? | P0 | Yes | `tests/verifier.json` expected field | Fix the regex |
| 1.25 | Does any memo/prose regex enforce token order (word-order replay: forward matches, reversed doesn't)? | P1 | Yes | `tests/verifier.json` regex | Use order-independent lookaheads `(?=.*a)(?=.*b)` |
| 1.26 | Does the instruction list JSON keys that NO check grades (Missing)? | P1 | Yes | `instruction.md` json keys vs `tests/verifier.json` | Add an equals check per key or drop the key |
| 1.27 | Does the instruction pin section headings that NO check verifies? | P2 | Yes | `instruction.md` headings vs verifier | Add heading checks or drop the pin |
| 1.28 | Are there boolean JSON `equals` checks on keys whose type the prompt may not pin (`boolean_type_unpinned`)? | P2 | Yes | verifier + instruction | Pin boolean type in instruction |
| 1.29 | Are there JSON keys graded that the prompt never names (Extra)? | P1 | Yes | verifier jsonpath keys vs instruction | Name the key in instruction.md or drop the check |
| 1.30 | Do memo checks require a section heading the prompt does not state (`heading_not_in_prompt`)? | P1 | Yes | verifier regex heading vs instruction | State the heading in instruction or drop the check |
| 1.31 | Do checks read deliverable paths the prompt never names (`graded_path_not_in_prompt`)? | P1 | Yes | verifier paths vs instruction | Name the path in instruction or drop the check |
| 1.32 | Do prose checks hard-code entity IDs not stated in the prompt? | INFO | Yes | verifier regex entity IDs vs instruction | Verify uniqueness; expected when IDs derive from inputs |
| 1.33 | Do >= 2 regex checks use independent lookaheads `(?=..)(?=..)` (id not associated with reason)? | INFO | Yes | verifier regex | Token-stuffed memo may pass |
| 1.34 | Do checks match whole CSV rows exactly (surface-form pins: 78 vs 78.0)? | INFO | Yes | verifier regex | Representation contract concern |
| 1.35 | Does a prose regex contain a hard-coded ISO date literal (e.g. `2026-07-08`) the prompt never asks for? | P1 | Yes | verifier regex + instruction | Delete the check or ask for the date in instruction |
| 1.36 | Does a prose regex contain a hard-coded ISO date literal AND the prompt asks for a date (but not this format)? | P2 | Yes | verifier regex + instruction | Accept any unambiguous date format |

### 1f. Gold replay + counterexamples (executed by the runner)

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 1.37 | Do gold deliverables in `solution/files/` FAIL any shipped spec check in local replay (spec IS executed, oracle NOT passed)? | P0 | Yes (replay) | `solution/files/` vs `tests/verifier.json` | Align gold and verifier |
| 1.38 | Do gold deliverables fail shipped checks but a bundled Oracle run scored 1.0 (gold is stale)? | P2 | Yes | `solution/files/` + `evaluations/oracle/` | Refresh solution/files from a solve.sh run |
| 1.39 | Do gold deliverables fail spec checks but the spec is NOT executed by test.sh (declared intent only)? | P2 | Yes | `solution/files/` + `tests/test.sh` | Reconcile spec with gold or execute the spec |
| 1.40 | Is the `empty_deliverables` counterexample exploitable (all content checks pass on empty files)? | P1* | Yes (replay) | runner counterexample | Add a check that rejects empty |
| 1.41 | Is the `headings_only_memo` counterexample exploitable (memo checks pass on headings-only)? | P1* | Yes (replay) | runner counterexample | Add substance checks |
| 1.42 | Is the `token_stuffed_memo` counterexample weak (substantive checks still pass on token-stuffed)? | P2 | Yes (replay) | runner counterexample | Associate ids with reasons |
| 1.43 | Is the `duplicated_rows` counterexample exploitable (CSV checks pass on doubled rows)? | P1* | Yes (replay) | runner counterexample | Add record-count / whole-file check |
| 1.44 | Is the `rotated_grounds` counterexample exploitable (memo checks pass with reasons rotated between clauses)? | P1* | Yes (replay) | runner counterexample | Scope each reason to its clause |
| 1.45 | Is the `float_formatted` counterexample `surface_form_brittle` (checks reject N.0 where N is identical) AND the format is NOT pinned in the prompt? | P1 | Yes (replay) | runner counterexample + instruction | Pin whole-number format or accept `\d+(\.0+)?` |
| 1.46 | Is the `float_formatted` counterexample `surface_form_brittle` AND the format IS pinned in the prompt? | INFO | Yes (replay) | runner counterexample + instruction | No action needed |

*Severity is P1 when spec is executed and fully replayed; P2 when partially replayed; INFO when spec is not executed.

### 1g. Realism inventory

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 1.47 | Is the task body > 400 words (real prompts are ~90 words, top 1% ~480)? | INFO | Yes | `instruction.md` word count | Shorten toward a natural request |
| 1.48 | Does the task body read as step-by-step instructions (>= 3 numbered steps with imperative verbs)? | INFO | Yes | `instruction.md` | Reframe as "what" not "how" |
| 1.49 | Does the scenario metadata contain `=== HIDDEN RULES ===`? | INFO | Yes | `task.toml` metadata | Difficulty should be in data, not hidden rules |
| 1.50 | Are there redacted names or opaque seeded identifiers (>= 9 char uppercase) in the instruction? | INFO | Yes | `instruction.md` | Improve workplace readability |
| 1.51 | Are exact required filenames and machine-graded fields constraining otherwise flexible output? | INFO | Yes | `instruction.md` | Only informational |

---

## LAYER 2 — Model static review (requires GLM model stage)

Source: `build_static_prompt`, `validate_static_review`, `SHANNON_RUBRIC`, `STATIC_SCHEMA`

The model must return JSON matching `STATIC_SCHEMA`. The runner derives `static_verdict` = worst of: all 7 audit dimensions, all issue verdicts, `instruction_verifier_consistency`, all 9 Layer 1 hard check verdicts, `prompt_gate.verdict`, and FAIL if any soundness answer is "no".

### 2a. Prompt Gate 1 — Soundness (Q1-Q4)

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 2.1 | Q1: Do any files/folders the prompt names NOT exist on the agent-visible surface? | P0* | Partly | `instruction.md` vs Dockerfile COPY | Add missing file to environment/input |
| 2.2 | Q2: Does any file NOT hold the data the prompt says it holds? | P0* | Partly | `instruction.md` vs input files | Fix the data or the prompt |
| 2.3 | Q3: Is anything needed missing/hidden/presumed (not findable from prompt + files)? | P0* | No (semantic) | `instruction.md` | State the missing requirement |
| 2.4 | Q4: Could a skilled person NOT finish with only the prompt and those files? | P0* | No (semantic) | `instruction.md` | Add what's needed |

*If Q1 or Q2 = "no" → `environment_broken` = true → blocks = reject. If any soundness = "no" → FAIL.

### 2b. Prompt Gate 1 — Quality (Q5-Q10)

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 2.5 | Q5: Does the task NOT need several steps and real thinking? | FAIL | No (semantic) | `instruction.md` | Add complexity to the data |
| 2.6 | Q6: Is the work NOT what this kind of user really needs? | FAIL | No (semantic) | `instruction.md` | Reframe the ask |
| 2.7 | Q7: Does the prompt NOT sound like a message a person typed? | FAIL | No (semantic) | `instruction.md` | Rewrite in natural voice |
| 2.8 | Q8: Does it NOT look like real prompts (~80-150 words, symptom-first)? | FAIL | Partly | `instruction.md` | Shorten, make symptom-first |
| 2.9 | Q9: Does the prompt explain HOW step by step (want NO)? | FAIL | No (semantic) | `instruction.md` | Remove how-to steps |
| 2.10 | Q10: Does the prompt give exact file names/numbers/words that only exist to help verifiers pass (want NO)? | FAIL | No (semantic) | `instruction.md` | Remove verifier-shaped specifics |

### 2c. Layer 1 hard checks (9 mandatory, model-judged)

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 2.11 | `json_types_pinned`: Are JSON types (bool vs int) NOT pinned before strict equals when the key name is ambiguous? (Do NOT flag `*_count`/`*_total`→int, `is_*`/`*_passed`→bool) | FAIL | Partly | verifier + instruction | Pin the type or rename the key |
| 2.12 | `named_entity_unique_no_extra`: Does a grader literal require a name/topic/count the prompt never asked (Extra)? | FAIL | Partly | verifier literals vs instruction | Name the entity in instruction or drop the check |
| 2.13 | `alias_exact_string`: Are aliases/exact strings (Option A vs A, Sheet1 vs first sheet, bare token vs header, invented IDs) NOT pinned or both accepted? | FAIL | Partly | verifier + instruction | Pin both forms or accept both |
| 2.14 | `memo_regex_not_word_order`: Does a memo/notes regex demand one synonym, a token order, or an unreachable alternation? | FAIL | Partly | verifier regex | Use order-independent patterns |
| 2.15 | `no_hidden_process`: Are there trace-only conclusions, tool-call patterns, or markers only in task.toml? | FAIL | Partly | verifier vs instruction | Move the requirement into the prompt |
| 2.16 | `instructed_graded_no_extra`: Is every instructed deliverable graded AND every check has a prompt ask? | FAIL | Partly | verifier vs instruction | Add missing checks or remove unasked |
| 2.17 | `scope_complete_coverage`: Do full-scope asks lack structural + semantic + cross-artifact coverage (isolated examples only)? | FAIL | No (semantic) | verifier + instruction | Add structural/semantic/cross-artifact checks |
| 2.18 | `golden_isolation_solution_match`: Are tests/, answer keys, or scenario comments agent-visible? Does solution/ satisfy the shipped prompt and reach 1.0 by an allowed route? | FAIL | Yes | `environment/Dockerfile` + `solution/` | Remove from agent-visible image |
| 2.19 | `structured_facts_not_prose_regex`: Are structured facts (counts, ids, dates, amounts, booleans) graded by prose regex instead of JSON/CSV fields? | FAIL | Partly | verifier regex on .md/.txt | Move to JSON/CSV field checks |

### 2d. Verifier classification (Missing / Extra / Different)

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 2.20 | Are there critical asks the prompt makes that NO shipped check grades (Missing)? | P1 | No (semantic) | `checklist_2a` vs verifier | Add the missing check |
| 2.21 | Are there shipped checks that grade something the prompt never asked (Extra)? | P1 | No (semantic) | verifier vs instruction | Drop the check or add the ask |
| 2.22 | Are there shipped checks that are a proxy for the ask (Different — grades something other than what's asked)? | P1 | No (semantic) | verifier vs instruction | Align the check to the ask |

### 2e. Whole set (2c)

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 2.23 | Does the whole set NOT cover everything asked? | FAIL | No (semantic) | verifier + instruction | Add missing checks |
| 2.24 | Does the whole set grade something unasked? | FAIL | No (semantic) | verifier + instruction | Remove unasked checks |
| 2.25 | Does the whole set NOT pass good work written differently and fail bad work? | FAIL | No (semantic) | verifier predicates | Widen acceptance / tighten rejection |
| 2.26 | Is the whole set NOT deterministic (dates, live web, random order, exact wording luck)? | FAIL | No (semantic) | verifier predicates | Remove non-deterministic dependencies |

### 2f. Brittleness / representation contract

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 2.27 | Does any check enforce word order (`token1.*token2`)? | P1 | Partly | verifier regex | Use order-independent lookaheads |
| 2.28 | Do independent lookaheads fail to associate an id with its reason (token-stuffed memo passes)? | P1 | Partly | verifier regex | Scope each reason to its clause |
| 2.29 | Are there hard-coded entity IDs in the regex? | P2 | Yes | verifier regex | Derive from data or pin in prompt |
| 2.30 | Is there an instruction-echo regex (literal 'looks overstated' while 'apparently' fails)? | P1 | No (semantic) | verifier regex vs instruction | Accept synonyms |
| 2.31 | Are there undefined JSON aggregates (counting rule only in verifier)? | P1 | No (semantic) | verifier | Define the counting rule in prompt |
| 2.32 | Is there an undisclosed rounding tie-break? | P1 | No (semantic) | verifier | Disclose rounding in prompt |
| 2.33 | Are there exact CSV cell strings (78 vs 78.0) when the prompt only says "populate"? | P1 | Partly | verifier regex | Accept `\d+(\.0+)?` or pin format |
| 2.34 | Is there an HTML text-node vs datetime attribute mismatch? | P1 | No (semantic) | verifier | Pin which to read |
| 2.35 | Is the memo date format unstated? | P1 | Partly | verifier regex | Ask for the date or delete the check |
| 2.36 | Are there per-ticket proximity windows the prompt never requires? | P1 | No (semantic) | verifier regex | Remove or disclose in prompt |
| 2.37 | Does the verifier read a different/stale/truncated source than the prompt names? | P1 | No (semantic) | verifier paths vs instruction | Align paths |
| 2.38 | Are there declared checks that never execute? | P1 | Yes | `tests/test.sh` | Execute or remove the checks |
| 2.39 | Is there aggregation drift from declared weights? | P1 | No (semantic) | verifier scoring | Fix the aggregation |

### 2g. Coverage counterexample (mandatory)

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 2.40 | Can you describe a materially wrong but plausible deliverable that the grader would pass? | P1 | No (semantic) | counterexample | Add a check that rejects it |
| 2.41 | Does the model propose a counterexample the runner confirms as `coverage_gap_confirmed`? | P1 | Yes (runner executes) | `model_counterexamples` | Add a check that rejects it |

### 2h. Specification ambiguity

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 2.42 | Do visible sources conflict with two defensible readings where the prompt does NOT pin precedence? | P1 | No (semantic) | `instruction.md` + policies | Pin the reading in instruction |

### 2i. Seven audit dimensions

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 2.43 | `clarity_and_disclosure` FAIL? | FAIL | No (semantic) | all sources | Clarify instruction |
| 2.44 | `requirement_coverage` FAIL? | FAIL | No (semantic) | all sources | Add missing checks |
| 2.45 | `verifier_fairness` FAIL? | FAIL | No (semantic) | all sources | Fix verifier predicates |
| 2.46 | `brittleness` FAIL? | FAIL | No (semantic) | all sources | Fix brittle checks |
| 2.47 | `scoring_integrity` FAIL? | FAIL | No (semantic) | all sources | Fix scoring |
| 2.48 | `format_and_schema_enforcement` FAIL? | FAIL | No (semantic) | all sources | Fix format checks |
| 2.49 | `static_exploitability` FAIL? | FAIL | No (semantic) | all sources | Close exploit |

### 2j. Mandatory consistency subcheck

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 2.50 | `instruction_verifier_consistency` FAIL? (If FAIL → overall static verdict is FAIL) | FAIL | No (semantic) | instruction vs verifier | Reconcile instruction and verifier |

---

## LAYER 3 — Model runs review (requires GLM model stage + bundled evaluations)

Source: `build_runs_prompt`, `make_runs_validator`, `RUNS_SCHEMA`, triage rules

The model must return JSON matching `RUNS_SCHEMA` with `run_behavioral_assessment` containing exactly the difficulty run IDs. The runner enforces observed rewards, strict-pass status, and counts — the model cannot change them.

### 3a. Mandatory subchecks (cannot be averaged away)

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 3.1 | `instruction_verifier_consistency` FAIL? (If FAIL → overall runs verdict is FAIL) | FAIL | No (semantic) | instruction vs verifier vs runs | Reconcile |
| 3.2 | `failure_cause_validity` FAIL? — Is any failed rollout used as difficulty evidence NOT agent-owned (i.e. an instruction/verifier/infra defect)? (If FAIL → overall runs verdict is FAIL) | FAIL | No (semantic) | per-run triage | Fix the task/verifier, re-run GLM |

### 3b. Per-run behavioral assessment (every difficulty run)

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 3.3 | Is the run's failure ownership `task_verifier` with failure_layer `layer1_blocker`? | P1 | No (semantic) | run triage | Pin the prompt or widen the grader |
| 3.4 | Is the run's failure ownership `task_verifier` with failure_layer `brittle`? | P1 | No (semantic) | run triage | Fix brittle checks, re-run GLM |
| 3.5 | Is the run's failure ownership `task_verifier` with failure_layer `deliverable_format`? | P1 | No (semantic) | run triage | Fix format checks, re-run GLM |
| 3.6 | Is the run's failure ownership `task_verifier` with failure_layer `ambiguity`? | P1 | No (semantic) | run triage | Pin the reading, re-run GLM |
| 3.7 | Is a failed check classified as `derived` (only in verifier.json/gold, not in instruction or agent-visible policy)? | — | No (semantic) | `explicit_vs_derived` | Do not credit as coding hardness; it's a prompt/grading gap |
| 3.8 | Is a lexical regex failure attributed to a substantive mistake when the delivered content actually has the substance? | — | No (semantic) | `explicit_vs_derived` | Reclassify as grading gap |

### 3c. Cross-run analysis

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 3.9 | Is `difficulty_validity` INVALID (failures are task/verifier/infra, not model reasoning)? | FAIL | No (semantic) | cross_run_analysis | Fix the task, re-run |
| 3.10 | Is `difficulty_validity` NEEDS_REVIEW? | NEEDS_REVIEW | No (semantic) | cross_run_analysis | Investigate |
| 3.11 | Are clustered failures (all runs miss the SAME rows) a possible ambiguity signal, not difficulty? | P2 | No (semantic) | cross_run_analysis | Open governing policy clauses; if a competent reading yields agents' values, it's a prompt gap |
| 3.12 | Does fixing one brittle check move the pass rate materially? | P2 | No (semantic) | calibration_profile | Restate raw vs after-fix |
| 3.13 | Is `reward_hacking_audit.verdict` CONFIRMED? | P0 | No (semantic) | runs review | Discard affected trials |
| 3.14 | Is `reward_hacking_audit.verdict` SUSPECT? | NEEDS_REVIEW | No (semantic) | runs review | Investigate |
| 3.15 | Does the solvability assessment find the reward-1.0 agent guessed grader wording instead of deriving from prompt/inputs? | FAIL | No (semantic) | solvability_assessment | Fix the environment |

### 3d. Near-pass hard stop

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 3.16 | Is there a near-pass (one failed check or >= 95% passing) with golden/substance layers green, labelled model fault from the check name alone? | — | No (semantic) | run triage | Do not label as model fault; investigate the clause |
| 3.17 | Is the grader report a collapsed parametrized pytest (first failure only) and is the first failure inferred as the only failure? | — | Yes | `ctrf.parametrized_collapse` | Say so; do not infer |

### 3e. Quality label per trial

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 3.18 | Is the quality label `Brittle` (reward 0 but only brittle/unasked checks failed)? | — | No (semantic) | run triage | Name each and say why brittle |
| 3.19 | Is the quality label `Misjudgement` (skipped a named input / inverted a stated rule / stopped early)? | — | No (semantic) | run triage | Genuine model fault |

---

## LAYER 4 — Evidence gates (deterministic, no model)

Source: `difficulty_gate`, `solvability_gate`, `stability_gate`, `trial_record`

### 4a. Difficulty gate

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 4.1 | Are there 0 difficulty runs under `evaluations/difficulty` (or legacy `glm-5.2`)? | P1 | Yes | `evaluations/difficulty/` | Provide 4-5 runs |
| 4.2 | Are there fewer than min (4) or more than max (5) difficulty runs? | P1 | Yes | run count | Provide 4-5 runs |
| 4.3 | Is any difficulty run's `result.json` malformed? | P1 | Yes | `result.json` | Fix the JSON |
| 4.4 | Is any difficulty run missing `trajectory.json` (infra — excluded from pass rate)? | P1 | Yes | `agent/trajectory.json` | Re-run or copy trajectory |
| 4.5 | Is any difficulty run missing a parseable reward? | P1 | Yes | `result.json` / `reward.txt` | Fix reward |
| 4.6 | Are there Oracle/reference runs inside difficulty evidence? | P1 | Yes | `agent_info.name` | Remove oracle runs from difficulty |
| 4.7 | Is agent/model/environment provenance incomplete on any run? | P1 | Yes | `config.json` | Complete provenance |
| 4.8 | Does provenance (agent/model/environment) differ across difficulty runs? | P1 | Yes | `config.json` | Make consistent |
| 4.9 | Is any difficulty run recorded with a model other than the target (glm-5.2)? | P1 | Yes | `config.json` model_name | Re-run with target model |
| 4.10 | Is the strict pass rate > max_pass_rate (50%) on valid trials (task too easy)? | P1 | Yes | reward values | Harden the task |
| 4.11 | Are there 0 strict passes (acceptable only if every failure is a genuine model fault and task is proven solvable)? | WARN | Yes | reward values | Verify solvability |
| 4.12 | Does `task_checksum` differ across difficulty runs? | P2 | Yes | `result.json` | Re-run on same task tree |

### 4b. Solvability gate

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 4.13 | Is there NO complete reward-1.0 non-Oracle model result/trajectory pair with exact provenance and executed verifier? | P1 | Yes | `evaluations/solvability/` or difficulty fallback | Attach one full model trial at reward 1.0 |
| 4.14 | Is the solvability run an Oracle replay (oracle != solvability)? | P1 | Yes | `agent_info.name` | Replace with a model run |
| 4.15 | Is the solvability run reward != 1.0? | P1 | Yes | reward | Re-run until 1.0 |
| 4.16 | Does the solvability run lack trajectory/provenance/finished/verifier evidence? | P1 | Yes | run files | Complete the evidence |
| 4.17 | Is there no `evaluations/solvability/r1` slot but a reward-1.0 difficulty trial exists? | WARN | Yes | `evaluations/solvability/` | Copy to solvability/r1 |

### 4c. Stability gate

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 4.18 | Are there 0 `repeat-NN`/`result.json` records under `evaluations/stability`? | P1 | Yes | `evaluations/stability/` | Ship repeat-01..05 |
| 4.19 | Are there fewer than min (3) `repeat-NN` folders with parseable `result.json`? | P1 | Yes | repeat count | Ship at least 3 |
| 4.20 | Are there between min (3) and recommended (5) repeats? | P2 | Yes | repeat count | Ship 5 recommended |
| 4.21 | Is any repeat's `result.json` malformed? | P1 | Yes | `result.json` | Fix the JSON |
| 4.22 | Does any repeat lack a parseable reward? | P1 | Yes | `result.json` | Fix reward |
| 4.23 | Do repeat rewards disagree across repeats? | P1 | Yes | reward values | Re-run from one frozen job |
| 4.24 | Are repeat rewards not 1.0? | P1 | Yes | reward values | Re-run until 1.0 |
| 4.25 | Do `verifier/reward.txt` and `result.json` disagree in any repeat? | P1 | Yes | reward sources | Fix the disagreement |
| 4.26 | Are there folders under stability NOT named `repeat-NN` (not counted)? | P2 | Yes | dir names | Rename to repeat-NN |
| 4.27 | Are there stray files directly under `evaluations/stability`? | P2 | Yes | stray files | Remove |
| 4.28 | Are there repeat folders without `result.json`? | P1 | Yes | missing files | Add result.json |
| 4.29 | Do repeat folders carry entries beyond `result.json`? | P2 | Yes | extra files | Keep only result.json |
| 4.30 | Does `config.json` differ across repeats beyond trial identity fields? | P2 | Yes | `config.json` | Freeze the config |
| 4.31 | Does `lock.json` differ across repeats? | P2 | Yes | `lock.json` | Freeze the lock |
| 4.32 | Does the frozen trajectory identity differ across repeats? | P2 | Yes | trajectory hashes | Re-run from one frozen job |
| 4.33 | Does the declared frozen-trajectory hash not match the saved trajectory? | P2 | Yes | trajectory hashes | Fix the hash |
| 4.34 | Do criterion-level check vectors differ across repeats (hidden instability)? | P2 | Yes | `checks_hash` | Re-run from one frozen job |
| 4.35 | Are repeats graded against a different check grid than the shipped verifier? | P1 | Yes | graded vs shipped names | Re-run on shipped grid |

### 4d. LLM-judge stability

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 4.36 | Does the task have LLM rubric checks and fewer than 3 stability repeats? | P1 | Yes | `verifier.json` rubrics + stability count | Grade byte-identical deliverables >= 3 times |

---

## LAYER 5 — Packaging (deterministic, no model)

Source: `packaging_checklist` (26+ checks, all produce PASS/FAIL/WARN rows)

All FAIL rows are promoted to P1 by `derive_deterministic_findings`. All WARN rows contribute to `packaging_verdict = NEEDS_REVIEW`.

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 5.1 | Is `instruction.md` missing? | P1 | Yes | root | Add it |
| 5.2 | Does `task.toml` fail to parse? | P1 | Yes | `task.toml` | Fix it |
| 5.3 | Is `environment/Dockerfile` missing? | P1 | Yes | `environment/` | Add it |
| 5.4 | Is the Dockerfile FROM not pinned by `@sha256` (export gate)? | P1 | Yes | `environment/Dockerfile` | Pin by digest |
| 5.5 | Is `README.md` missing or a stub? | P1/P2 | Yes | `README.md` | Add/expand |
| 5.6 | Is `tests/verifier.json` missing (or named manifest.json)? | P1/P2 | Yes | `tests/` | Create/rename |
| 5.7 | Is `tests/test.sh` missing? | P1 | Yes | `tests/` | Add it |
| 5.8 | Are there cache/junk dirs or files inside the task tree? | P1 | Yes | task tree | Remove |
| 5.9 | Is `solution/golden_trajectory.json` missing? | P1 | Yes | `solution/` | Add it |
| 5.10 | Is `solution/solve.sh` (or `.py`) missing? | P1 | Yes | `solution/` | Add it |
| 5.11 | Is there a duplicate `golden_trajectory.json` at task root? | P2 | Yes | root | Remove (handoff hygiene) |
| 5.12 | Does `solution/tests/` exist? | P1 | Yes | `solution/tests/` | Move graders to task-root tests/ |
| 5.13 | Does the difficulty gate fail? | P1 | Yes | gates | Fix difficulty evidence |
| 5.14 | Are GLM/solvability trials NOT full Harbor copies (missing trajectory, reward file, or grader transcript)? | P1 | Yes | `evaluations/` run dirs | Copy complete Harbor trial folders |
| 5.15 | Is there a trial layout variant (reward.json + verifier_summary.json instead of reward.txt + test-stdout.txt)? | P2 | Yes | run files | Use standard layout |
| 5.16 | Does the solvability gate fail? | P1 | Yes | gates | Fix solvability evidence |
| 5.17 | Does the stability gate fail? | P1 | Yes | gates | Fix stability evidence |
| 5.18 | Is `evaluations/oracle` present but not all rewards are 1.0? | P1 | Yes | oracle rewards | Fix oracle |
| 5.19 | Is `evaluations/oracle` absent? | P2 | Yes | `evaluations/` | Confirm oracle 1.0 via gold |
| 5.20 | Were bundled runs graded against a different check grid than the shipped verifier? | P1 | Yes | graded vs shipped names | Re-run on shipped grid |
| 5.21 | Is `task_checksum` inconsistent across bundled trials? | P2 | Yes | checksums | Re-run on same task tree |
| 5.22 | Do `golden_check.json`/`summary.json`/README counts mismatch the shipped verifier? | P2 | Yes | metadata files | Regenerate from shipped trials |
| 5.23 | Are there stray `verifier.json.*` variants under `tests/`? | P2 | Yes | `tests/` | Remove before submit |
| 5.24 | Are host home paths (`/Users/<name>`, `C:\Users\`, `/home/<name>`) present in `result.json`/`config.json`/`lock.json`? | P2 | Yes | run metadata | Replace with /workspace |
| 5.25 | Does `review.csv` integrity fail? | P1 | Yes | `review.csv` | Re-fill the worksheet |
| 5.26 | Is `review.csv` not bundled? | P2 | Yes | root | Bundle for channel submit |
| 5.27 | Does the `environment/_app` mirror NOT match root task files? | P1 | Yes | `environment/_app/` | Regenerate mirror |
| 5.28 | Does the Dockerfile copy graders/solution into the image (golden isolation)? | P1 | Yes | Dockerfile COPY | Remove the COPY |
| 5.29 | Is there a sibling `qc/` next to the task inside a `-m-vN` extract folder? | P1 | Yes | parent dir | Remove |
| 5.30 | Are there sibling `glm-5x-*` job folders next to the task? | P2 | Yes | parent dir | GLM evidence belongs in evaluations/ only |
| 5.31 | Is there a `qc/` or `qc-out/` inside the task tree? | P1 | Yes | task tree | Remove |

---

## LAYER 6 — review.csv worksheet audit (deterministic, no model)

Source: `review_csv_audit`

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 6.1 | Does a PASS row have "No change required" in `change_made`? | P1 | Yes | `review.csv` | Leave change_made blank |
| 6.2 | Does a PASS row have an issue-ID audit stub (confirmed/identified/logged/tracked issue)? | P1 | Yes | `review.csv` | Remove the stub |
| 6.3 | Does a `FIXED_AND_VERIFIED` row have empty `change_made`? | P1 | Yes | `review.csv` | Document the fix |
| 6.4 | Does `FIXED_AND_VERIFIED` cite files that are byte-identical to the baseline (no actual change)? | P1 | Yes | `review.csv` + baseline diff | Cite files that actually changed |
| 6.5 | Does `FIXED_AND_VERIFIED` prose say the issue is "still open"/"remains unfixed"? | P1 | Yes | `review.csv` | Fix or change status |
| 6.6 | Does `FIXED_AND_VERIFIED` cite a path that does NOT exist in the package? | P2 | Yes | `review.csv` + task tree | Fix the path |
| 6.7 | Is there an unknown status value (not PASS/FIXED_AND_VERIFIED/N/A)? | P2 | Yes | `review.csv` | Use a valid status |
| 6.8 | Does any row contain open-item phrasing (open item, left unattended, outstanding, unresolved, still open, not yet addressed, needs follow-up, deferred, TBD, TODO, will need to, should be fixed later, remains unfixed, issue remains, pending fix, to be fixed/addressed)? | P1 | Yes | `review.csv` | Close the item |
| 6.9 | Does a difficulty row claim "x/N" that does NOT match the bundle's strict_passes/valid_runs? | P2 | Yes | `review.csv` vs gates | Fix the claim |
| 6.10 | Does a stability row claim N repeats that does NOT match the bundle's repeat count? | P2 | Yes | `review.csv` vs stability | Fix the claim |
| 6.11 | Does any row claim a check count that does NOT match the shipped `check_count`? | P2 | Yes | `review.csv` vs verifier | Fix the claim |
| 6.12 | Do PASS rows describe a change in `change_made` (should be `FIXED_AND_VERIFIED` or blank)? | P1 | Yes | `review.csv` | Re-label or blank the field |
| 6.13 | Are ALL scored rows PASS (worksheet documents no fixes)? | P1 | Yes | `review.csv` | Document fixes as FIXED_AND_VERIFIED |

---

## LAYER 7 — Standards (semantic, require reading content)

Source: obi-task-quality-standard (A1-A6, G1-G7, M1-M6, H1-H4), non-connector-task-standard (15 stages, DIS/DIF/VER/HAR/ENV rules), shannon-task-qc-north-star, all-hands key takeaways

### 7a. The Ask (A1-A6)

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 7.1 | A1: Would a real person NOT actually ask this (unrealistic, benchmark-shaped)? | P1 | No (semantic) | `instruction.md` | Reframe as a real request |
| 7.2 | A1: Does the prompt sound AI-voiced rather than human? | P1 | No (semantic) | `instruction.md` | Rewrite in natural voice |
| 7.3 | A2: Is there NOT one defensible right answer (range of acceptable outputs)? | P1 | No (semantic) | `instruction.md` | Pin the answer or accept the range |
| 7.4 | A3: Does the prompt give away something the model should find (stated answers, field-name leakage, method spelled out)? | P1 | No (semantic) | `instruction.md` | Remove the giveaway |
| 7.5 | A4: Is there a decision the model must make that the prompt does NOT decide (boundaries, NULL handling, column choice, scope matching, deliverable form, inclusion rules)? | P1 | No (semantic) | `instruction.md` | Decide it in the prompt |
| 7.6 | A5: Is the deliverable NOT worth producing (trivial answer dressed up)? | P1 | No (semantic) | `instruction.md` | Make it valuable |
| 7.7 | A6: Does the task reference something that does NOT exist (tables, pages, tickets, channels)? | P0 | Yes | `instruction.md` + inputs | Fix or add the reference |

### 7b. The Grading (G1-G7)

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 7.8 | G1: Is the primary goal NOT verified? | P0 | No (semantic) | verifier | Add a check for the main thing |
| 7.9 | G2: Is any stated requirement NOT checked? | P1 | No (semantic) | verifier vs instruction | Add the missing check |
| 7.10 | G3: Does any verifier demand something the prompt never asked? | P1 | No (semantic) | verifier vs instruction | Drop the check or add the ask |
| 7.11 | G4: Do verifiers grade the model's account of the work instead of the artifact? | P1 | No (semantic) | verifier | Check the artifact, not the report |
| 7.12 | G5: Do verifiers NOT accept every correct route (narrow-to-golden, single-tool traps, synonym gaps)? | P1 | No (semantic) | verifier | Widen acceptance |
| 7.13 | G6: Does the verifier set NOT discriminate (free points, denominator gaming)? | P1 | No (semantic) | verifier | Remove free points |
| 7.14 | G7: Are there judgment-based checks where a deterministic check was possible? | P2 | No (semantic) | verifier | Make it json_match or database_state |

### 7c. The Measurement (M1-M6)

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 7.15 | M1: Does Oracle NOT score 1.00 reproducibly? | P0 | Yes (replay) | gold replay | Align gold and verifier |
| 7.16 | M2: Is the mean NOT in band (pass rate NOT in [0.0, 0.5))? | P1 | Yes | difficulty rewards | Harden or simplify |
| 7.17 | M3: Is the spread bimodal (coin flip, not difficulty)? | P1 | Yes | reward distribution | Investigate |
| 7.18 | M4: Are failures NOT MODEL-attributed (VERIFIER/SPEC/INFRA)? | P1 | No (semantic) | run triage | Fix the task/verifier |
| 7.19 | M5: Is the verifier profile NOT stable across runs (same verifiers pass, not just same mean)? | P2 | Yes | per-check outcomes | Fix stability |
| 7.20 | M6: Is the score inflated by free points (check the floor)? | P1 | No (semantic) | verifier | Remove free points |

### 7d. Hygiene (H1-H4)

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 7.21 | H1: Are prompt and verifiers OUT of sync with their mirror (root vs environment/_app)? | P0 | Yes | hash comparison | Regenerate mirror |
| 7.22 | H2: Does the answer key ship to the model (anything from solution/ under environment/_app/)? | P0 | Yes | `environment/_app/` | Remove |
| 7.23 | H3: Can the package NOT grade itself (grading engine files missing)? | P1 | Yes | `tests/` | Include engine files |
| 7.24 | H4: Does the reported number NOT come from the submitted package (checksums mismatch)? | P1 | Yes | checksums | Regenerate from submitted |

### 7e. Key rules (DIS/DIF/VER/HAR/ENV)

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 7.25 | DIS-1: Does the verifier enforce something NOT derivable from the disclosed set (instruction.md + environment/input/)? | P0 | No (semantic) | verifier vs disclosed set | Remove the check or disclose |
| 7.26 | DIS-6: Does the blind-reader test FAIL (give instruction+inputs to someone who hasn't seen the verifier; ask them to list every literal; anything the verifier knows and the reader does not is illegal)? | P0 | No (semantic) | blind-reader test | Disclose in instruction or remove from verifier |
| 7.27 | DIF-1: Does the difficulty NOT survive full disclosure (once everything is disclosed, is it still hard)? | P0 | No (semantic) | task analysis | Put difficulty in the data |
| 7.28 | DIF-6: Is the "difficulty" actually volume, ambiguity, or hair-thin tolerances? | P0 | No (semantic) | task analysis | Real difficulty, not volume/ambiguity |
| 7.29 | VER-24: Is there NO discrimination harness that verifies wrong candidates fail for the correct reason? | P1 | No (semantic) | breaking suite | Add wrong-candidate tests |
| 7.30 | HAR-10: Does the oracle NOT reproduce exactly 1.0 locally? | P0 | Yes (replay) | gold replay | Fix gold/verifier alignment |
| 7.31 | ENV-1: Does the Dockerfile COPY anything other than `input/` from the environment? | P1 | Yes | Dockerfile COPY | Copy input/ only |

### 7f. Verifier pitfalls (O1-O17) — representation contract

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 7.32 | O1: Numeric format graded by string compare? | P1 | Yes | verifier | Accept format variants |
| 7.33 | O2: Float exact equality (no tolerance)? | P1 | Yes | verifier | Add tolerance |
| 7.34 | O3: Unstated rounding? | P1 | Yes | verifier | State rounding in prompt |
| 7.35 | O4: Date format required but unstated? | P1 | Yes | verifier | State or accept any format |
| 7.36 | O5: Enum case sensitivity? | P1 | Yes | verifier | Accept case-insensitively or pin |
| 7.37 | O6: Boolean/null representation (true vs 1, null vs "")? | P1 | Yes | verifier | Accept both or pin |
| 7.38 | O7: Currency decoration ($ vs no $)? | P1 | Yes | verifier | Accept both or pin |
| 7.39 | O8: Row order dependence? | P1 | Yes | verifier | Sort before compare or accept any order |
| 7.40 | O9: Column order dependence? | P1 | Yes | verifier | Compare by column name |
| 7.41 | O10: JSON key order or value type sensitivity? | P1 | Yes | verifier | Parse and compare semantically |
| 7.42 | O11: Encoding and line endings (CRLF vs LF)? | P1 | Yes | verifier | Normalize before compare |
| 7.43 | O12: CSV quoting style? | P1 | Yes | verifier | Parse with csv module |
| 7.44 | O13: Whitespace and trailing newline? | P1 | Yes | verifier | Strip/normalize |
| 7.45 | O14: Prose graded by keyword (not meaning)? | P1 | Yes | verifier | Use LLM rubric on content |
| 7.46 | O15: Unstated tie-break? | P1 | Yes | verifier | State the tie-break |
| 7.47 | O16: Unstated boundary? | P1 | Yes | verifier | State the boundary |
| 7.48 | O17: Extra files or intermediates rejected? | P1 | Yes | verifier | Only check required files |

### 7g. Equivalence suite (E1-E14) — must still pass

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 7.49 | Does the verifier FAIL when rows are shuffled? | P1 | Yes (test) | verifier | Sort before compare |
| 7.50 | Does the verifier FAIL when columns are reordered? | P1 | Yes (test) | verifier | Compare by column name |
| 7.51 | Does the verifier FAIL when JSON keys are reordered? | P1 | Yes (test) | verifier | Parse and compare semantically |
| 7.52 | Does the verifier FAIL when CSV fields are quoted? | P1 | Yes (test) | verifier | Parse with csv module |
| 7.53 | Does the verifier FAIL on LF→CRLF? | P1 | Yes (test) | verifier | Normalize newlines |
| 7.54 | Does the verifier FAIL when trailing newline is added/removed? | P1 | Yes (test) | verifier | Strip trailing whitespace |
| 7.55 | Does the verifier FAIL when BOM is prepended? | P1 | Yes (test) | verifier | Strip BOM |
| 7.56 | Does the verifier FAIL when integers are reformatted? | P1 | Yes (test) | verifier | Parse numerically |
| 7.57 | Does the verifier FAIL when trailing decimal zeros are added (5 → 5.0)? | P1 | Yes (test) | verifier | Accept `\d+(\.0+)?` |
| 7.58 | Does the verifier FAIL when fields are padded? | P1 | Yes (test) | verifier | Strip before compare |
| 7.59 | Does the verifier FAIL when JSON numbers are strings? | P1 | Yes (test) | verifier | Coerce types |
| 7.60 | Does the verifier FAIL when prose is paraphrased? | P1 | Yes (test) | verifier | Use LLM rubric on meaning |
| 7.61 | Does the verifier FAIL when an unrequired intermediate is deleted? | P1 | Yes (test) | verifier | Only check required deliverables |
| 7.62 | Does the verifier FAIL when an unrelated scratch file is added? | P1 | Yes (test) | verifier | Only check required files |

### 7h. Breaking suite (B1-B8) — must now fail

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 7.63 | Does the verifier PASS when one classification is flipped? | P0 | Yes (test) | verifier | Add the check |
| 7.64 | Does the verifier PASS when one row is deleted? | P0 | Yes (test) | verifier | Add row-count check |
| 7.65 | Does the verifier PASS when one spurious row is appended? | P0 | Yes (test) | verifier | Add row-count check |
| 7.66 | Does the verifier PASS when one summary count is changed? | P0 | Yes (test) | verifier | Add summary-count check |
| 7.67 | Does the verifier PASS when a boundary-case row is flipped? | P0 | Yes (test) | verifier | Add boundary check |
| 7.68 | Does the verifier PASS when every file is emptied? | P0 | Yes (test) | verifier | Add content check |
| 7.69 | Does the verifier PASS when one deliverable is deleted? | P0 | Yes (test) | verifier | Add existence check |
| 7.70 | Does the verifier PASS when all output is replaced with `{}`? | P0 | Yes (test) | verifier | Add content check |

### 7i. All-hands rules

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 7.71 | Is difficulty in rules/instructions instead of in the DATA? | P1 | No (semantic) | `instruction.md` | Put difficulty in data |
| 7.72 | Does the prompt give away exact duplicate row numbers or answers? | P1 | No (semantic) | `instruction.md` | Remove giveaways |
| 7.73 | Are verifiers overly strict about exact phrasing (except filenames, codes, JSON keys)? | P1 | No (semantic) | verifier | Give room for natural alternatives |

---

## LAYER 8 — D1-D5 bundle linter (deterministic, no model)

Source: `verifier_defect_lint.py`

Note: All D1-D5 checks are currently advisory-only (`BLOCKING_CHECK_IDS = set()`), but they still run and report.

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 8.1 | D1: Is a prose/memo deliverable graded by `regex_match` with a length-only quantifier (`{200}`) and no required content words? | sev2 | Yes | `tests/verifier.json` regex | Replace with LLM rubric on content |
| 8.2 | D1: Is a prose deliverable graded by `regex_match` with >= 2 `(?=...)` lookaheads (keyword-set membership, order/coherence ungraded)? | sev2 | Yes | `tests/verifier.json` regex | Replace with LLM rubric or bind tokens to assertions |
| 8.3 | D1: Is a prose deliverable graded by `regex_match` with `.*`/`.{0,N}` slack (lets arbitrary filler satisfy the match)? | sev2 | Yes | `tests/verifier.json` regex | Replace with LLM rubric |
| 8.4 | D1: Are >= 3 regex items on ONE prose file bare keyword/ID-presence checks (no `.*`, lookahead, or quantifier) — decomposed token-soup? | sev2 | Yes | `tests/verifier.json` regex items | Grade the claim, not mere presence |
| 8.5 | D2: Does `environment/Dockerfile` set no non-root `USER` (agent runs as root)? | sev1 | Yes | `environment/Dockerfile` | Add a non-root USER |
| 8.6 | D3: Does `config.models` ship a `${JUDGE_MODEL}` placeholder but NO harness file reads/substitutes JUDGE_MODEL? | sev3 | Yes | `verifier.json` config + harness files | Add a resolver or pin a real model |
| 8.7 | D3: Does `config.models` hard-pin a concrete provider/model id with NO harness resolver AND a rubric item exists? | sev2 | Yes | `verifier.json` config + harness files | Read the injected JUDGE_MODEL |
| 8.8 | D4: Does `tests/test_outputs.py` use a fixture from an agent-reachable path (`/app/`, `/workspace/`) as grading ground truth AND the container is root or the path is writable? | sev3 | Yes | `tests/test_outputs.py` + Dockerfile | Move fixture into /tests, run non-root |
| 8.9 | D5: Does the manifest advertise `sql` scoring weight > 0 but `sql_verifiers` is empty AND no flat_verifier_scoring? | sev2 | Yes | `manifest.json` scoring + sql_verifiers | Populate the axis or set weight to 0 |
| 8.10 | D5: Does the manifest advertise `state` scoring weight > 0 but no `state.snapshot.mode` AND the shipped expected_diff is empty? | sev2 | Yes | `manifest.json` scoring + state | Populate the axis or set weight to 0 |

---

## LAYER 9 — Repackaging gate (C1-C12)

Source: `REPACKAGING-QC-GATE.md`

These run AFTER upstream acceptance (every package already passed QC). They catch what survives that verdict.

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 9.1 | C1: Is there a `FROM` line or `image =` value with no `@sha256:` digest in Dockerfile, task.toml, or `environment/_app/task.toml`? | BLOCK | Yes | 3 config locations | Pin all three by digest |
| 9.2 | C2: Is there a routable IPv4 in a host position (after URL scheme, after @, after host/hostname/server/endpoint/base_url/proxy/gateway key, or carrying :port) — excluding private/loopback/link-local/multicast/RFC5737 ranges? | BLOCK | Yes | task files | Replace with neutral placeholder |
| 9.3 | C3: Is there a personal home-directory path (`/Users/<name>`, `C:\Users\<name>`, `/home/<name>/`) where the name is NOT in the allow-list (rlgymagent, harbor, runner, node, user, app, ubuntu, root)? | BLOCK | Yes | task files | Replace with neutral placeholder |
| 9.4 | C4: Does the task have MCP servers, NO `dataset` on any declared server, and exactly one distinct `GYM_DATASET` value under `environment/`? | BLOCK | Yes | `task.toml` + `environment/` | Declare the dataset provenance |
| 9.5 | C5: Do the archive filename, internal root directory, and `task.name` in `task.toml` NOT all agree? | BLOCK | Yes | archive + task.toml | Rename paths only (keep bytes/CRC/timestamp/mode) |
| 9.6 | C6: Does a document (`review.csv`, `README.md`, `qc_report.html`) claim a pass rate (matching `pass\s*rate` or `N/4 passes`) that differs from the count of difficulty rewards == exactly 1.0? | BLOCK | Yes | documents vs rewards | Reconcile document to evidence |
| 9.7 | C7: Is there NO `README.md` at the package root? | WARN | Yes | root | Generate from in-package evidence |
| 9.8 | C8: Are there non-task artefacts (`:Zone.Identifier`, `.DS_Store`, `._*`, `__MACOSX`, `.swp`, `.swo`, `.orig`, `.rej`, `Thumbs.db`, `desktop.ini`, editor backups)? | BLOCK | Yes | task tree | Remove (sweep last, before handover) |
| 9.9 | C9: Does a verifier `how_justification` name `<stem>.<extA>` where the verifier's `source` reads `<stem>.<extB>`? | WARN | Yes | `verifier.json` how_justification vs source | Correct the description string only |
| 9.10 | C10: Are there NOT exactly 4 recorded rewards under `evaluations/difficulty/r1..r4`? | BLOCK | Yes | difficulty rewards | Do not ship; route to review |
| 9.11 | C11: Does the band recomputed from raw rewards differ from the folder/manifest? (A pass = reward exactly 1.0; 3/4 = lighter band, 0-2 = full, 4/4 = out of band) | BLOCK | Yes | rewards vs band | Recompute from delivered bytes |
| 9.12 | C12: Does the manifest disagree with disk (either direction), or is a hash/size/id/name wrong or duplicated? | BLOCK | Yes | manifest vs tree | Recompute from delivered bytes |

---

## LAYER 10 — Portal-derived semantic checks (require reading content)

Source: portal-findings-law-b39, QC-SELF-TRAINING

These are the checks the deterministic layer CANNOT catch — they require reading content semantically. The GLM model stage catches most of them; manual inspection catches the rest.

### 10a. Gold derivability

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 10.1 | Can a reader with ONLY the instruction + inputs NOT derive every gold verdict? (blind-reader test) | P0 | Yes (read) | instruction + inputs + gold | Disclose the rule or remove the check |
| 10.2 | Do identical inputs (same wording, same governing entry) get DIFFERENT gold verdicts (self-contradictory gold)? | P0 | Yes (group by wording) | gold deliverable + input data | Fix the gold to be consistent |
| 10.3 | Are there hair-split distinctions (one word changes the verdict) the instruction does NOT disclose? | P0 | Yes (read) | gold + instruction | Disclose the distinction or remove |
| 10.4 | Are there placeholder/synthetic wordings in the data ("wording is X")? | P1 | Yes (read) | input data | Replace with real content |
| 10.5 | Are gold counts (verified/at_odds/etc.) self-inconsistent (don't sum to total)? | P1 | Yes (sum) | gold deliverable | Fix the counts |

### 10b. Failure cause validity

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 10.6 | Did GLM get all governing entries right (e.g. 230/230) but verdicts wrong → are the failed rows the self-contradictory/undisclosed cluster? | P0 | Yes (cross-ref) | GLM runs + gold | 0/4 is fake difficulty; fix the gold |
| 10.7 | Do all 4 GLM runs fail on the SAME rows (clustered failure = ambiguity signal, not difficulty)? | P1 | Yes (compare) | GLM run failures | Open governing clauses; if a competent reading yields agents' values, it's a prompt gap |
| 10.8 | Are the GLM failures MODEL-attributed (model had everything, still wrong) or SPEC-attributed (prompt/verifier/gold wrong)? | P0 | Yes (read) | run triage | Fix the task if SPEC-attributed |

### 10c. Solvability legitimacy

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 10.9 | Does `solve.sh` copy pre-computed gold into /app (`cp -r solution/files/* /app/`)? | P0 | Yes (read) | `solution/solve.sh` | Compute the answer from inputs |
| 10.10 | Does `solve.sh` emit trajectory from `golden_trajectory.json` (hand-authored)? | P0 | Yes (read) | `solution/solve.sh` | Run a real model |
| 10.11 | Does the README admit the trajectory is "hand-authored reference, not a byte-copy of a model run"? | P0 | Yes (read) | `README.md` | Run a real model |
| 10.12 | Does NO non-Oracle model run score 1.0? | P1 | Yes (check) | `evaluations/` | Run GLM until 1.0 or fix the task |
| 10.13 | Does `golden_trajectory.json` embed results with counts that DIFFER from `solution/files/results.json`? | P0 | Yes (compare) | `golden_trajectory.json` vs gold | Update the trajectory |
| 10.14 | Does `golden_trajectory.json` embed a CSV with a row count that DIFFERS from `solution/files/*.csv`? | P0 | Yes (count) | `golden_trajectory.json` vs gold | Update the trajectory |
| 10.15 | Does the Oracle trajectory embed counts that DIFFER from the current gold? | P0 | Yes (compare) | `evaluations/oracle/agent/trajectory.json` vs gold | Re-run the oracle |

### 10d. Stability evidence (portal)

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 10.16 | Do stability repeat folders carry NO per-check evidence (only `result.json`, no `score.json`/`ctrf.json`/artifacts)? | P1 | Yes (list files) | `evaluations/stability/repeat-NN/` | Add per-check evidence |
| 10.17 | Are the repeats re-runs (distinct agent_execution windows) without frozen artifacts (identity asserted, not evidenced)? | P1 | Yes (compare) | repeat metadata | Ship frozen artifacts or hash |

### 10e. Surface-form fairness (portal)

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 10.18 | Does the `answer_at_odds_figure` regex reject the required sentence when the number is bolded (`**124**`)? | P1 | Yes (test) | regex test | Accept markdown formatting |
| 10.19 | Does any regex reject a correct answer in italic, decimal, extra whitespace, or different format? | P1 | Yes (test) | regex test | Accept format variants |
| 10.20 | Does the verifier encode verdicts the disclosed protocol cannot yield (register_table/results_figures expected values)? | P0 | No (semantic) | verifier vs protocol | Fix the expected values |

### 10f. Counterfactual strength (portal)

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 10.21 | Is a genuinely correct, protocol-faithful submission REJECTED by the verifier? | P0 | Yes (construct) | construct + run | Fix the verifier to separate correct from gold's arbitrary choices |

### 10g. Trajectory / review.csv freshness (portal + PreQC)

| # | Yes/no question (defect present?) | Sev | Manual? | Evidence | Fix |
|---|---|---|---|---|---|
| 10.22 | Does `review.csv` cite counts that DON'T match the actual gold `results.json`? | P1 | Yes (compare) | `review.csv` vs `solution/files/results.json` | Update review.csv |
| 10.23 | Does `review.csv` cite paths that DON'T exist in the package? | P2 | Yes (check) | `review.csv` vs task tree | Fix the paths |
| 10.24 | Does the Oracle trajectory's embedded results.json show counts that differ from current gold? | P0 | Yes (compare) | oracle trajectory vs gold | Re-run the oracle |

---

## VERDICT COMPUTATION (how the final pass/fail is decided)

Source: `compute_verdicts`

### Component verdicts

| Component | How computed |
|---|---|
| `deterministic_verdict` | FAIL if any deterministic P0/P1; NEEDS_REVIEW if any deterministic P2; else PASS |
| `static_verdict` | worst of: 7 audit dimensions, all issue verdicts, `instruction_verifier_consistency`, 9 Layer 1 hard checks, `prompt_gate.verdict`, and FAIL if any soundness answer = "no" |
| `runs_verdict` | worst of: 2 mandatory subcheck verdicts, `difficulty_validity` mapped, `raw_difficulty_gate.verdict`, `reward_hacking` mapped, `solvability_assessment.verdict` |
| `evidence_verdict` | (runs mode only) FAIL if any gate (difficulty/solvability/stability) fails; NEEDS_REVIEW if any gate warns; else PASS |
| `packaging_verdict` | FAIL if any packaging row is FAIL; NEEDS_REVIEW if any WARN; else PASS |
| `review_csv_verdict` | FAIL if review.csv status = fail; NEEDS_REVIEW if warn; else PASS |
| `reward_hacking_verdict` | (runs mode only) OK→PASS, SUSPECT→NEEDS_REVIEW, CONFIRMED→FAIL |

### Final verdict

| Verdict | Condition |
|---|---|
| `qc_verdict` | worst of all component verdicts (deterministic, static_model, runs_model, evidence_gates, packaging, review_csv, reward_hacking) |
| `task_quality_verdict` | worst of (deterministic, static_model, runs_model) — the model's quality assessment |
| `review_verdict` = **Reject** | any finding with `blocks = "reject"` |
| `review_verdict` = **Rework** | any finding with `blocks = "rework"` OR `qc_verdict = FAIL` |
| `review_verdict` = **Pass** | none of the above |

### Blocking severity → blocks mapping

| Severity | blocks |
|---|---|
| P0 | "reject" if model explicitly says so (e.g. environment broken); otherwise "rework" |
| P1 | "rework" |
| P2 | "none" |

### Human review required

`human_review_required = true` if:
- `qc_verdict = NEEDS_REVIEW`, OR
- model did not run, OR
- calibration shows `first_failure_only_evidence` (collapsed parametrized report), OR
- evaluation surface is incomplete (core sources were truncated)

---

## SUMMARY: What can be checked manually (no model)?

**Fully manual (file inspection only):**
- All Layer 0 (format/package structure)
- All Layer 1 (deterministic): format, Dockerfile, harness, leakage, hygiene, verifier regex compilation, gold replay, counterexamples (if you run the Python replay), realism counts
- All Layer 4 (gates): difficulty/solvability/stability evidence checks
- All Layer 5 (packaging): all 31 checks
- All Layer 6 (review.csv): all 13 checks
- All Layer 8 (D1-D5 linter): all 10 checks
- All Layer 9 (C1-C12 repackaging): all 12 checks
- Layer 7 standards: O1-O17 pitfalls, E1-E14 equivalence suite, B1-B8 breaking suite (all testable by constructing variants)
- Portal checks 10.2-10.17, 10.18-10.19, 10.22-10.24 (all require reading content but not a model)

**Requires the model stage (semantic):**
- Layer 2 (static): soundness Q3-Q4, quality Q5-Q10, Layer 1 hard checks (judgment), Missing/Extra/Different classification, whole set 2c, brittleness findings, representation contract, specification ambiguity, coverage counterexample, 7 audit dimensions, instruction_verifier_consistency
- Layer 3 (runs): failure_cause_validity, per-run ownership/failure_layer, explicit_vs_derived, near-pass hard stop, cross-run difficulty_validity, reward hacking confirmation, solvability sufficiency, quality labels
- Layer 7 standards: A1-A6, G1-G7, M4, DIS-1, DIS-6, DIF-1, DIF-6 (all require semantic reading)
- Portal checks 10.1, 10.3, 10.8, 10.20, 10.21 (require semantic analysis)

**The critical lesson from law-b39:** Running `--no-model` (deterministic only) catches packaging, hygiene, reward-hacking, and counterexamples. It CANNOT catch gold-derivability, self-contradiction, failure-cause-validity, or surface-form fairness. Those require the model stage or manual semantic analysis. Never trust a `--no-model` result for a final ship decision.
