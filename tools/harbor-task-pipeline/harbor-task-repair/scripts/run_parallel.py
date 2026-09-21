#!/usr/bin/env python3
"""Script-driven parallel orchestrator for harbor-task-repair.

Replaces the LLM orchestrator with a deterministic Python driver, and replaces the 13-deep
sequential chain with two parallel diagnosis waves plus a serial apply.

    setup (probe, hashes, lint)
      -> wave 1  : steps 00 01 02 05 07 08 09 10   diagnose, in parallel, READ-ONLY
      -> wave 2  : steps 03 04 06                  diagnose, in parallel (need contract.json)
      -> merge   : dedupe + group intents by target file, then by check, in step order
      -> apply   : one harbor-apply agent per target file
      -> 11 proof, 12 coherence                    serial

Why waves: step 01 writes contract.json and steps 03/04/06 read it.
Why intents not patches: parallel diagnosticians touch the same checks; literal patches collide.
Why read-only is enforced, not trusted: the whole task tree is hashed around each wave.

    python run_parallel.py tasks/my-task --model wandb-glm/glm-5.2
    python run_parallel.py tasks/my-task --jobs 6 --dry-run

Exit codes: 0 clean, 1 escalations needing review, 2 precondition, 3 run failed, 4 integrity
violation (a diagnostician modified the task).

Standard library only.
"""

import argparse
import concurrent.futures as futures
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_auto  # noqa: E402  - reuse opencode_cmd/resolve_task/read_escalations

WAVE1 = ["00", "01", "02", "05", "07", "08", "09", "10"]
WAVE2 = ["03", "04", "06"]          # need contract.json from step 01
SERIAL_TAIL = ["11", "12"]          # proof gates coherence
ALWAYS_RUN = {"00", "01", "04", "11", "12"}

SKIP_HASH_DIRS = ("__pycache__", ".git", ".harbor-repair")


def log(msg):
    print(msg, flush=True)


# ---------------------------------------------------------------- integrity

def tree_hash(root):
    """sha256 per file across the task tree. This is what makes 'read-only' a guarantee
    rather than an instruction to an agent that has a bash tool."""
    out = {}
    for dp, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_HASH_DIRS]
        for f in files:
            if f.endswith(".pyc"):
                continue
            p = os.path.join(dp, f)
            try:
                with open(p, "rb") as fh:
                    out[os.path.relpath(p, root).replace("\\", "/")] = \
                        hashlib.sha256(fh.read()).hexdigest()
            except OSError:
                pass
    return out


def diff_tree(before, after):
    changed = sorted(k for k in set(before) & set(after) if before[k] != after[k])
    return {
        "modified": changed,
        "added": sorted(set(after) - set(before)),
        "removed": sorted(set(before) - set(after)),
    }


# ---------------------------------------------------------------- spawning

def recipe_for(skill_dir, nn):
    hits = sorted((skill_dir / "recipes").glob("%s-*.md" % nn))
    return hits[0] if hits else None


def affordance_text(aff):
    """Tell the diagnostician what can actually be built.

    Without this, a diagnostician proposes the architecturally ideal repair because it never
    has to implement it. Measured on code-c284: step 05 demanded a new engine source adapter,
    the applier could not legally create one, and 5 intents died unapplied - while the
    sequential fixer, which had to build its own proposal, picked a mechanism that existed.
    """
    if not aff:
        return ""
    return (
        " MECHANISMS AVAILABLE - propose only these. Registered source commands: %s. "
        "Editable targets: %s. %s %s"
        % (", ".join(aff.get("source_commands_available") or []) or "none",
           "; ".join(aff.get("editable_targets") or []) or "none",
           aff.get("fix_in_place_first", "") + " " + aff.get("escape_hatch", ""),
           aff.get("not_available", ""))
    )


def diagnose_prompt(nn, task_rel, skill_rel, recipe_rel, harbor_rel, out_rel, probe_step,
                    aff=None):
    cands = (probe_step or {}).get("candidates") or []
    cand_txt = ""
    if cands:
        shown = "; ".join(str(c)[:110] for c in cands[:12])
        cand_txt = (" The pre-flight probe lists %d candidate(s) for this step as a starting "
                    "target list (hints, not verdicts): %s." % (len(cands), shown))
    cand_txt += affordance_text(aff)
    cand_txt += (" Set files_to_change on every finding to the file that must actually change.")
    contract = "%s/contract.json" % harbor_rel
    return (
        "You are the harbor-diagnose subagent for step %(nn)s. READ-ONLY: change nothing inside "
        "the task. task_path=%(task)s recipe_path=%(recipe)s probe_path=%(harbor)s/probe.json "
        "contract_path=%(contract)s out_path=%(out)s . Read the recipe at %(recipe)s in full and "
        "%(skill)s/reference/guardrails.md and %(skill)s/reference/autonomous-policy.md, then "
        "diagnose ONLY what this recipe covers.%(cands)s Emit INTENTS, not literal patches: say "
        "which check, which property, and why, quoting both the prompt and the verifier. Put any "
        "scope-changing action in escalations[] instead of findings[] - never propose editing "
        "instruction.md and never propose deleting a check. Write your JSON to %(out)s FIRST, "
        "then emit the same JSON as your final message and nothing else."
        % {"nn": nn, "task": task_rel, "recipe": recipe_rel, "harbor": harbor_rel,
           "contract": contract, "out": out_rel, "skill": skill_rel, "cands": cand_txt}
    )


def contract_prompt(task_rel, skill_rel, recipe_rel, harbor_rel, out_rel):
    return (
        "You are the harbor-diagnose subagent for step 01, the COLD READ. Read ONLY "
        "%(task)s/instruction.md - you must NOT open the verifiers, tests/, or solution/; the "
        "entire value of this step is that the requirement map was built without seeing the "
        "checks. Read the recipe at %(recipe)s in full. Write the requirement map to "
        "%(harbor)s/contract.json (that file is your product, not a task edit), then write your "
        "step summary JSON to %(out)s and emit it as your final message and nothing else."
        % {"task": task_rel, "recipe": recipe_rel, "harbor": harbor_rel, "out": out_rel}
    )


def spawn(cmd_base, project, agent, prompt, log_path, model, timeout):
    cmd = list(cmd_base) + ["run", "--auto", "--agent", agent, "--dir", str(project)]
    if model:
        cmd += ["--model", model]
    cmd += [prompt]
    env = dict(os.environ)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    started = time.time()
    try:
        with open(log_path, "wb") as fh:
            r = subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=fh,
                               stderr=subprocess.STDOUT, timeout=timeout,
                               env=env, cwd=str(project))
        return r.returncode, int(time.time() - started)
    except subprocess.TimeoutExpired:
        return 124, int(time.time() - started)
    except OSError:
        return 125, int(time.time() - started)


def recover_json(out_path, log_path):
    """Prefer the file the agent wrote; fall back to the last JSON object in its log.

    The file channel exists because a subagent that completes correctly can still emit an
    empty message - measured twice in one run, costing two full re-spawns.
    """
    p = Path(out_path)
    if p.is_file():
        try:
            return json.loads(p.read_text(encoding="utf8", errors="replace"))
        except ValueError:
            pass
    try:
        txt = Path(log_path).read_text(encoding="utf8", errors="replace")
    except OSError:
        return None
    txt = re.sub(r"\x1b\[[0-9;]*m", "", txt)
    best = None
    for m in re.finditer(r"\{.*?\}", txt, re.S):
        try:
            d = json.loads(m.group(0))
        except ValueError:
            continue
        if isinstance(d, dict) and ("findings" in d or "step" in d or "target_file" in d):
            best = d
    return best


# ---------------------------------------------------------------- merge

def merge(findings_by_step):
    """Group intents by target file, then by check, ordered by step.

    Dedupe is on (target_file, check, property, normalised intent) - the same defect seen by
    two steps is one edit. Different properties on one check are NOT duplicates; they compose.
    """
    def as_list(v, default):
        """A finding may legitimately name several checks or files - a scoring-level finding
        naturally spans many checks. Fan it out to one intent per check rather than forcing
        one-check-per-finding on the diagnostician."""
        if v is None or v == "":
            return [default]
        if isinstance(v, (list, tuple, set)):
            out = []
            for x in v:
                if x is not None and str(x) != "":
                    out.extend(as_list(x, default))
            return out or [default]
        s = str(v)
        # A diagnostician may also comma-join several names into one string instead of using a
        # list. Split only when every part looks like a bare identifier, so descriptive labels
        # such as "(meta - no specific check; routing summary)" survive intact.
        if re.fullmatch(r"[A-Za-z_][\w.\-]*(\s*,\s*[A-Za-z_][\w.\-]*)+", s.strip()):
            return [p.strip() for p in s.split(",") if p.strip()]
        return [s]

    plans, seen, n_dupes = {}, set(), 0
    for nn in sorted(findings_by_step):
        d = findings_by_step[nn] or {}
        # The older harbor-fixer contract used `findings` as a COUNT; the diagnose contract
        # uses it as a list. Agents mix them. Accept either, and look in `intents` too.
        raw = d.get("findings")
        if not isinstance(raw, list):
            raw = d.get("intents") if isinstance(d.get("intents"), list) else []
        for f in raw:
            if not isinstance(f, dict):
                continue
            prop = str(f.get("property") or "")
            norm = re.sub(r"\s+", " ", str(f.get("intent") or "")).strip().lower()[:160]
            # Routing: diagnosticians in practice emit `files_to_change` and almost never
            # `target_file`. Defaulting everything to verifier.json sent test_outputs.py
            # intents to an applier that could only refuse them. Prefer the explicit list.
            route = f.get("files_to_change") or f.get("target_file")
            for tgt in as_list(route, "tests/verifier.json"):
                for chk in as_list(f.get("check"), "<file>"):
                    key = (tgt, chk, prop, norm)
                    if key in seen:
                        n_dupes += 1
                        continue
                    seen.add(key)
                    rec = dict(f)
                    rec["step"] = nn
                    rec["check"] = chk
                    rec["target_file"] = tgt
                    plans.setdefault(tgt, {}).setdefault(chk, []).append(rec)
    ordered = {}
    for tgt, checks in plans.items():
        ordered[tgt] = {c: sorted(v, key=lambda r: r["step"]) for c, v in checks.items()}
    return ordered, n_dupes


def collect_escalations(findings_by_step):
    out = []
    for nn in sorted(findings_by_step):
        d = findings_by_step[nn] or {}
        for e in d.get("escalations") or []:
            if isinstance(e, dict):
                r = dict(e)
                r.setdefault("step", nn)
                out.append(r)
    return out


# ---------------------------------------------------------------- phases

def _diagnose_one(nn, ctx):
    recipe = recipe_for(ctx["skill_dir"], nn)
    if not recipe:
        return nn, None, 0, "no recipe"
    out_rel = "%s/findings/%s.json" % (ctx["harbor_rel"], nn)
    log_path = ctx["harbor"] / "logs" / ("diagnose-%s.log" % nn)
    recipe_rel = recipe.relative_to(ctx["project"]).as_posix()
    if nn == "01":
        prompt = contract_prompt(ctx["task_rel"], ctx["skill_rel"], recipe_rel,
                                 ctx["harbor_rel"], out_rel)
    else:
        prompt = diagnose_prompt(nn, ctx["task_rel"], ctx["skill_rel"], recipe_rel,
                                 ctx["harbor_rel"], out_rel,
                                 ctx["probe"].get("steps", {}).get(nn),
                                 ctx["probe"].get("affordances"))
    rc, secs = spawn(ctx["cmd_base"], ctx["project"], "harbor-diagnose", prompt,
                     log_path, ctx["model"], ctx["timeout"])
    data = recover_json(ctx["project"] / out_rel, log_path)
    if data is None:
        # A subagent can end its turn mid-work without writing its file - measured on step 06,
        # which read inputs for 154s then stopped. One bounded retry beats losing the step.
        rc, s2 = spawn(ctx["cmd_base"], ctx["project"], "harbor-diagnose", prompt,
                       log_path, ctx["model"], ctx["timeout"])
        secs += s2
        data = recover_json(ctx["project"] / out_rel, log_path)
    return nn, data, secs, ("exit %d" % rc if rc else None)


def _resumed(nn, ctx, results, timings):
    f = ctx["harbor"] / "findings" / ("%s.json" % nn)
    if ctx.get("resume") and f.is_file():
        try:
            results[nn] = json.loads(f.read_text(encoding="utf8"))
            timings[nn] = 0
            log("  step %s  resumed from findings/%s.json" % (nn, nn))
            return True
        except ValueError:
            pass
    return False


def run_dag(independent, dependent, ctx):
    """Schedule diagnosis as a DAG, not two barriers.

    Only steps 03/04/06 depend on anything - contract.json, written by step 01 in ~78s. Making
    every other step wait for a wave boundary cost ~155s for nothing. Submit step 01 first so
    it gets a worker immediately, run the independent steps alongside it, and release the
    dependent ones the moment 01 lands.
    """
    log("")
    log("=== DIAGNOSE (DAG, jobs=%d) ===" % ctx["jobs"])
    log("  independent: %s" % (" ".join(independent) or "-"))
    log("  after 01   : %s" % (" ".join(dependent) or "-"))
    results, timings = {}, {}
    before = tree_hash(ctx["task"])

    todo_ind = [n for n in independent if not _resumed(n, ctx, results, timings)]
    todo_dep = [n for n in dependent if not _resumed(n, ctx, results, timings)]

    if todo_ind or todo_dep:
        with futures.ThreadPoolExecutor(max_workers=ctx["jobs"]) as ex:
            futs = {}
            # 01 first: it is the gate, so it must not queue behind the others.
            for nn in sorted(todo_ind, key=lambda x: (x != "01", x)):
                futs[ex.submit(_diagnose_one, nn, ctx)] = nn
            gate = next((f for f, nn in futs.items() if nn == "01"), None)
            if todo_dep:
                if gate is not None:
                    nn, data, secs, prob = gate.result()
                    results[nn], timings[nn] = data, secs
                    log("  step %s  %4ds  gate released" % (nn, secs))
                    del futs[gate]
                for nn in todo_dep:
                    futs[ex.submit(_diagnose_one, nn, ctx)] = nn
            for f in futures.as_completed(futs):
                nn, data, secs, prob = f.result()
                results[nn], timings[nn] = data, secs
                n = len((data or {}).get("findings") or []) if data else 0
                app = (data or {}).get("applicable")
                state = "no-return" if data is None else                         ("not_applicable" if app is False else "%d finding(s)" % n)
                log("  step %s  %4ds  %-16s %s" % (nn, secs, state, prob or ""))

    delta = diff_tree(before, tree_hash(ctx["task"]))
    touched = delta["modified"] + delta["added"] + delta["removed"]
    if touched:
        log("")
        log("  !! INTEGRITY VIOLATION: a read-only diagnostician modified the task:")
        for f in touched[:20]:
            log("     %s" % f)
        ctx["integrity_violation"] = touched
    else:
        log("  integrity: task tree unchanged (%d files hashed)" % len(before))
    return results, timings


SPEC_ARRAY_KEYS = ("verifiers", "verifier_configs")

# The exact markers lint_verifiers.py keys on. If a check's expected value carries one of these
# before the repair, the repaired object must not still carry it - otherwise the "fix" changed
# nothing that matters. Measured on t19: 17 lines of verifier.json changed, every one of them
# how_justification prose, while 5 of 6 column-count couplings survived and the new prose
# claimed they had been removed. Misleading documentation is worse than an untouched check.
BRITTLE_MARKERS = (
    ("A3", "column-count coupling (,.*,)",
     lambda e: (",.*," in e) or bool(re.search(r",\s*\.\*\s*,", e))),
    ("A4", "row-order coupling (>=2 newlines)", lambda e: e.count("\\n") >= 2),
    ("A2b", "quote hack", lambda e: ("\\x22?" in e) or ('"?' in e)),
)


def expected_of(v):
    a = (v or {}).get("assertion") or {}
    e = a.get("expected")
    return e if isinstance(e, str) else ""


def markers_in(expected):
    return {code for code, _label, hit in BRITTLE_MARKERS if expected and hit(expected)}


def substantive(old_obj, new_obj):
    """Guard the splice against edits that cannot be repairs. Returns (ok, reason).

    Deliberately MONOTONE: it rejects only no-ops and regressions, never partial progress.

    An earlier version demanded that every brittle marker present before be gone after. Replayed
    against real runs that was wrong in both directions - it caught nothing in the bad run, and
    rejected 6 genuinely good fixes in which `,.*,` column coupling was correctly removed while
    an unrelated `\\x22?` optional-quote was kept. Optional-quote tolerance is desirable: it
    accepts both quoted and unquoted CSV. Requiring markers to vanish punishes fixing one defect
    while retaining a construct that was never the defect.

    A prose-only edit is allowed through, because rewriting `how_justification` to describe a
    change made elsewhere (say, a new assertion in tests/test_outputs.py) is legitimate. What is
    never legitimate is claiming to have applied a change and returning the original object, or
    handing back something lint-worse than what was there.
    """
    if old_obj is None:
        return True, ""
    if json.dumps(old_obj, sort_keys=True) == json.dumps(new_obj, sort_keys=True):
        return False, "no-op: returned object is byte-identical to the original"
    before, after = markers_in(expected_of(old_obj)), markers_in(expected_of(new_obj))
    worse = after - before
    if worse:
        return False, ("regression: introduces %s into assertion.expected"
                       % ", ".join(sorted(worse)))
    return True, ""


def splice_spec(path, checks_json):
    """Merge agent-returned check objects into a JSON spec, deterministically.

    This is what lets apply batches run in PARALLEL. They used to serialise only because they
    would collide writing one file; if each returns its checks instead of editing, the
    orchestrator does the single write and there is no contention. It also removes a whole
    failure class - an agent half-rewriting a 389-line file and stalling.
    """
    doc = json.loads(Path(path).read_text(encoding="utf8"))
    key = next((k for k in SPEC_ARRAY_KEYS if isinstance(doc.get(k), list)), None)
    if key is None:
        return 0, 0, ["spec has no recognised verifier array"]
    arr = doc[key]
    by_name = {}
    for i, v in enumerate(arr):
        if isinstance(v, dict) and v.get("name"):
            by_name[v["name"]] = i
    replaced = added = 0
    problems = []
    for name, obj in (checks_json or {}).items():
        if not isinstance(obj, dict) or not obj.get("name"):
            problems.append("%s: not a verifier object" % name)
            continue
        if name in by_name:
            old_obj = arr[by_name[name]]
            ok, why = substantive(old_obj, obj)
            if not ok:
                problems.append("%s: %s" % (name, why))
                continue
            arr[by_name[name]] = obj
            replaced += 1
        elif "/" in name or name not in by_name:
            # NEVER append an unrecognised name. Connector specs nest their real checks under
            # verifier_spec.verifiers[], so probe.flatten() reports them as "parent/child";
            # appending that as a top-level entry adds a junk verifier, leaves the real defect
            # untouched, and reports success. Verified: it produced a bogus
            # "lines_of_work/b1_value" entry while the nested check kept its old value.
            # A name we cannot resolve is a defect to report, never a check to invent.
            problems.append("%s: no such check in the spec - refusing to add it "
                            "(nested/connector specs are not spliceable)" % name)
    if replaced or added:
        Path(path).write_text(json.dumps(doc, indent=2) + chr(10), encoding="utf8")
    return replaced, added, problems


def run_apply(plans, ctx):
    log("")
    log("=== APPLY: %d target file(s) ===" % len(plans))
    if not plans:
        log("  nothing to apply")
        return {}, {}
    results, timings = {}, {}

    def batch_prompt(tgt, plan_rel, out_rel, names, i, nb, splice):
        common = (
            "You are the harbor-apply agent. task_path=%(task)s target_file=%(tgt)s "
            "plan_path=%(plan)s out_path=%(out)s mode=%(mode)s . This is batch %(i)d of "
            "%(nb)d and covers ONLY these check(s): %(names)s. Read %(plan)s and "
            "%(skill)s/reference/guardrails.md. Compose all intents on one check into a "
            "single coherent change, in step order. Never delete a check, never edit "
            "instruction.md, never invent a value. If an intent cannot be done legally, put "
            "it in unapplied with a reason and continue with the rest - do not stop."
            % {"task": ctx["task_rel"], "tgt": tgt, "plan": plan_rel, "out": out_rel,
               "mode": ctx["mode"], "i": i, "nb": nb, "names": ", ".join(names),
               "skill": ctx["skill_rel"]})
        if splice:
            return common + (
                " DO NOT EDIT ANY FILE. Instead return the COMPLETE corrected spec object "
                "for each check under a top-level key named checks, a JSON map keyed by "
                "check name, alongside a key named unapplied. The orchestrator splices them "
                "in - that is what lets batches run in parallel. Write that JSON to %s "
                "FIRST, then emit it as your final message." % out_rel)
        return common + (
            " EDIT %s now - do not stop after reading. Touch no other file. Verify it still "
            "parses. Write your JSON result to %s FIRST, then emit it." % (tgt, out_rel))

    def one_batch(tgt, slug, i, nb, slice_, splice):
        tag = "%s-b%d" % (slug, i)
        plan_rel = "%s/plans/%s.json" % (ctx["harbor_rel"], tag)
        out_rel = "%s/applied/%s.json" % (ctx["harbor_rel"], tag)
        (ctx["project"] / plan_rel).write_text(
            json.dumps({"target_file": tgt, "checks": slice_}, indent=1), encoding="utf8")
        prompt = batch_prompt(tgt, plan_rel, out_rel, sorted(slice_), i, nb, splice)
        log_path = ctx["harbor"] / "logs" / ("apply-%s.log" % tag)
        rc, secs = spawn(ctx["cmd_base"], ctx["project"], "harbor-apply", prompt,
                         log_path, ctx["model"], ctx["timeout"])
        data = recover_json(ctx["project"] / out_rel, log_path)
        if data is None:
            rc, s2 = spawn(ctx["cmd_base"], ctx["project"], "harbor-apply", prompt,
                           log_path, ctx["model"], ctx["timeout"])
            secs += s2
            data = recover_json(ctx["project"] / out_rel, log_path)
        return data, secs

    def one_file(item):
        tgt, checks = item
        slug = re.sub(r"[^A-Za-z0-9]+", "_", tgt).strip("_")
        names = sorted(checks)
        size = max(1, ctx["batch"])
        groups = [names[i:i + size] for i in range(0, len(names), size)]
        # Splice mode only for JSON specs: batches never touch the file, so they can run
        # concurrently. Python code files need a real editor, so those stay serial.
        splice = tgt.endswith(".json")
        merged = {"target_file": tgt, "verdict": "applied",
                  "mode": "splice" if splice else "direct", "intents_applied": 0,
                  "checks_changed": [], "unapplied": [], "batches": []}
        total = 0
        collected = {}

        def do(i_grp):
            i, grp = i_grp
            return i, grp, one_batch(tgt, slug, i, len(groups),
                                     {c: checks[c] for c in grp}, splice)

        jobs = ctx["jobs"] if splice else 1
        with futures.ThreadPoolExecutor(max_workers=max(1, jobs)) as ex:
            for i, grp, (data, secs) in ex.map(do, list(enumerate(groups, 1))):
                total = max(total, secs) if splice else total + secs
                v = (data or {}).get("verdict", "no-return")
                merged["batches"].append({"batch": i, "checks": grp, "verdict": v,
                                          "secs": secs})
                log("    batch %d/%d  %4ds  %-9s %d check(s)"
                    % (i, len(groups), secs, v, len(grp)))
                if data:
                    merged["unapplied"] += (data.get("unapplied") or [])
                    if splice:
                        for k, obj in (data.get("checks") or {}).items():
                            collected[k] = obj
                    else:
                        merged["intents_applied"] += int(data.get("intents_applied") or 0)
                        merged["checks_changed"] += (data.get("checks_changed") or [])
                if v in ("no-return", "blocked"):
                    merged["verdict"] = "partial"

        if splice and collected:
            full = Path(ctx["project"]) / ctx["task_rel"] / tgt
            rep, add, probs = splice_spec(full, collected)
            merged["intents_applied"] = rep + add
            merged["checks_changed"] = sorted(collected)
            merged["unapplied"] += [{"reason": p} for p in probs]
            log("    spliced: %d replaced, %d added%s"
                % (rep, add, (", %d problem(s)" % len(probs)) if probs else ""))
        if merged["unapplied"]:
            merged["verdict"] = "partial"
        return tgt, merged, total

    with futures.ThreadPoolExecutor(max_workers=max(1, len(plans))) as ex:
        for tgt, data, secs in ex.map(one_file, sorted(plans.items())):
            timings[tgt] = secs
            results[tgt] = data
            log("  %-40s %4ds  %-8s %-7s (%d applied, %d unapplied)"
                % (tgt[:40], secs, data["verdict"], data["mode"],
                   data["intents_applied"], len(data["unapplied"])))
    return results, timings


def proof_executable(task, timeout=90):
    """Can the task's verifier actually run here? Answer in seconds, not in an agent.

    Step 11 costs ~328s and, on a host where the suite cannot execute, produces nothing but a
    RUNTIME_ERROR that proof_suite.py already knows how to detect. Spawning an agent to
    rediscover that is pure waste - the same argument as the probe skipping steps 02 and 10.
    """
    tests = None
    for dp, dirs, files in os.walk(task):
        dirs[:] = [d for d in dirs if d not in SKIP_HASH_DIRS and d != "_app"]
        if os.path.basename(dp) == "tests" and any(
                f.startswith("test") and f.endswith(".py") for f in files):
            tests = dp
            break
    if not tests:
        return False, "no tests/test_*.py to execute"
    try:
        r = subprocess.run([sys.executable, "-c", "import pytest"],
                           capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            return False, "pytest is not installed in this interpreter"
    except (subprocess.TimeoutExpired, OSError) as e:
        return False, "cannot probe pytest: %s" % e
    try:
        # os.walk(task) yields paths relative to the CURRENT directory, but we run pytest with
        # cwd=task - so a relative tests path gets resolved against the task dir and double
        # prefixed ("file or directory not found", exit 4). That made this function report
        # "cannot execute" for every relative task path, which is how run_parallel calls it.
        r = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q",
                            os.path.abspath(tests)],
                           capture_output=True, text=True, timeout=timeout,
                           cwd=os.path.abspath(task))
    except subprocess.TimeoutExpired:
        return False, "pytest collection timed out"
    except OSError as e:
        return False, "pytest could not start: %s" % e
    out = (r.stdout or "") + (r.stderr or "")
    for pat, why in ((r"WinError\s*\d+", "asyncio/socket unavailable on this host (WinError)"),
                     (r"\bINTERNALERROR\b", "pytest internal error"),
                     (r"ModuleNotFoundError", "verifier imports failed"),
                     (r"no tests ran|collected 0 items", "no tests collected")):
        if re.search(pat, out):
            return False, why
    if r.returncode not in (0, 5):
        return False, "pytest collection exited %d" % r.returncode
    return True, "collection succeeded"


def run_tail(ctx):
    """Steps 11 and 12, concurrently.

    Step 12 consumes step 11 VERDICT ("repaired-unproven whenever step 11 could not run"),
    not its artifacts - and that verdict is held by this orchestrator, not by step 12. The
    gate is bookkeeping, not a data dependency, so the two can run at the same time.
    """
    log("")
    results, timings = {}, {}
    steps = list(SERIAL_TAIL)
    ok, why = proof_executable(ctx["task"])
    if not ok:
        log("=== TAIL: step 11 pre-check FAILED (%s) -> skipped, no spawn ===" % why)
        results["11"] = {"step": "11", "verdict": "blocked", "applicable": True,
                         "one_line": "proof suite cannot execute here: " + why,
                         "escalations": [{"step": "11", "owner": "runtime", "blocks": [],
                                         "finding": "proof suite not executable: " + why}]}
        timings["11"] = 0
        steps = ["12"]
    else:
        log("=== TAIL: 11 || 12 in parallel (proof executable: %s) ===" % why)

    def one(nn):
        recipe = recipe_for(ctx["skill_dir"], nn)
        if not recipe:
            return nn, None, 0
        out_rel = "%s/findings/%s.json" % (ctx["harbor_rel"], nn)
        log_path = ctx["harbor"] / "logs" / ("step-%s.log" % nn)
        prompt = (
            "You are the harbor-fixer-auto agent for step %(nn)s. task_path=%(task)s "
            "recipe_path=%(recipe)s contract_path=%(harbor)s/contract.json mode=%(mode)s . "
            "Read the recipe in full and %(skill)s/reference/guardrails.md and "
            "%(skill)s/reference/autonomous-policy.md. Diagnosis and apply are already done - "
            "review the CURRENT state of the task. Do not wait for any other step; the "
            "orchestrator composes the final proven/unproven verdict itself. Never ask; "
            "resolve scope decisions from the autonomous policy into escalations[]. Write "
            "your JSON to %(out)s FIRST, then emit it as your final message and nothing else."
            % {"nn": nn, "task": ctx["task_rel"], "recipe": recipe.relative_to(
                ctx["project"]).as_posix(), "harbor": ctx["harbor_rel"], "mode": ctx["mode"],
               "skill": ctx["skill_rel"], "out": out_rel})
        rc, secs = spawn(ctx["cmd_base"], ctx["project"], "harbor-fixer-auto", prompt,
                         log_path, ctx["model"], ctx["timeout"])
        return nn, recover_json(ctx["project"] / out_rel, log_path), secs

    with futures.ThreadPoolExecutor(max_workers=max(1, len(steps))) as ex:
        for nn, data, secs in ex.map(one, steps):
            results[nn] = data
            timings[nn] = secs
            log("  step %s  %4ds  %s" % (nn, secs, (data or {}).get("verdict", "no-return")))
    return results, timings

# ---------------------------------------------------------------- main

def lint_json(skill_dir, task):
    try:
        r = subprocess.run([sys.executable, str(skill_dir / "scripts" / "lint_verifiers.py"),
                            str(task), "--json"], capture_output=True, text=True, timeout=180)
        d = json.loads(r.stdout)
        return (sum(1 for f in d["findings"] if f["level"] == "error"),
                sum(1 for f in d["findings"] if f["level"] == "warning"),
                d["stats"].get("n_verifiers"))
    except Exception:
        return None, None, None


def parser():
    p = argparse.ArgumentParser(description="Parallel, script-driven harbor-task-repair.")
    p.add_argument("task")
    m = p.add_mutually_exclusive_group()
    m.add_argument("--fix", action="store_true", help="apply repairs (default)")
    m.add_argument("--dry-run", action="store_true", help="diagnose only")
    p.add_argument("--model")
    p.add_argument("--jobs", type=int, default=6,
                   help="max concurrent agents (default 6; measured 69%% efficiency)")
    p.add_argument("--timeout", type=int, default=1800, help="per-agent timeout seconds")
    p.add_argument("--no-probe", action="store_true")
    p.add_argument("--batch", type=int, default=4,
                   help="checks per applier batch (default 4; a single 17-check batch stalls)")
    p.add_argument("--resume", action="store_true",
                   help="reuse findings/*.json already on disk instead of re-diagnosing")
    return p


def main():
    args = parser().parse_args()
    project = Path(__file__).resolve().parents[4]
    skill_dir = project / ".opencode" / "skill" / "harbor-task-repair"
    if not run_auto.preflight(project, skill_dir):
        return 2
    for a in ("harbor-diagnose.md", "harbor-apply.md"):
        if not (project / ".opencode" / "agent" / a).is_file():
            log("ERROR: missing .opencode/agent/%s" % a)
            return 2

    task, task_rel, problem = run_auto.resolve_task(project, args.task)
    if problem:
        log("ERROR: %s" % problem)
        return 2

    harbor = task.parent / ".harbor-repair"
    for sub in ("findings", "plans", "applied", "logs"):
        (harbor / sub).mkdir(parents=True, exist_ok=True)
    harbor_rel = harbor.relative_to(project).as_posix()

    t0 = time.time()
    log("task    : %s" % task_rel.as_posix())
    probe = {} if args.no_probe else (run_auto.run_probe(skill_dir, task, harbor) or {})
    skip = set(probe.get("skip") or [])
    e0, w0, n0 = lint_json(skill_dir, task)
    log("lint    : %s error(s), %s warning(s), %s verifiers" % (e0, w0, n0))
    log("probe   : %d/13 step(s) skippable -> %s" % (len(skip), ", ".join(sorted(skip)) or "none"))
    subprocess.run([sys.executable, str(skill_dir / "scripts" / "protect_hashes.py"), str(task),
                    "--write", str(harbor / "protected.json")],
                   capture_output=True, text=True)

    ctx = {"project": project, "task": task, "task_rel": task_rel.as_posix(),
           "skill_dir": skill_dir,
           "skill_rel": skill_dir.relative_to(project).as_posix(),
           "harbor": harbor, "harbor_rel": harbor_rel, "probe": probe,
           "model": args.model, "jobs": max(1, args.jobs), "timeout": args.timeout,
           "cmd_base": run_auto.opencode_cmd(),
           "mode": "dry-run" if args.dry_run else "fix",
           "resume": args.resume, "batch": args.batch, "_nbatches": 1,
           "integrity_violation": None}

    def wanted(steps):
        return [s for s in steps if s not in skip or s in ALWAYS_RUN]

    r1, t1 = run_dag(wanted(WAVE1), wanted(WAVE2), ctx)
    if ctx["integrity_violation"]:
        log("ABORTING: diagnosis phase must be read-only.")
        return 4
    r2, t2 = {}, {}

    allf = dict(r1); allf.update(r2)
    plans, n_dupes = merge(allf)
    n_int = sum(len(v) for c in plans.values() for v in c.values())
    log("\n=== MERGE ===")
    log("  %d intent(s) across %d file(s), %d duplicate(s) collapsed"
        % (n_int, len(plans), n_dupes))
    for tgt, checks in sorted(plans.items()):
        log("  %-44s %d check(s), %d intent(s)"
            % (tgt[:44], len(checks), sum(len(v) for v in checks.values())))

    ra, ta = ({}, {}) if args.dry_run else run_apply(plans, ctx)
    if args.dry_run:
        log("\n(dry-run: nothing applied)")
    rt, tt = run_tail(ctx)

    esc = collect_escalations(allf)
    for nn, d in sorted(rt.items()):
        for e in (d or {}).get("escalations") or []:
            if isinstance(e, dict):
                r = dict(e); r.setdefault("step", nn); esc.append(r)
    (harbor / "escalations.json").write_text(json.dumps(esc, indent=1), encoding="utf8")
    act, info = run_auto.read_escalations(harbor)

    e1, w1, n1 = lint_json(skill_dir, task)
    total = int(time.time() - t0)
    log("\n" + "=" * 62)
    log("TOTAL %ds (%.1f min)   jobs=%d" % (total, total / 60.0, ctx["jobs"]))
    log("  wave1 critical path %ss (sum %ss)" % (max(t1.values() or [0]), sum(t1.values())))
    log("  wave2 critical path %ss (sum %ss)" % (max(t2.values() or [0]), sum(t2.values())))
    if ta:
        log("  apply %ss   tail %ss" % (sum(ta.values()), sum(tt.values())))
    log("  lint %s->%s error(s), verifiers %s->%s" % (e0, e1, n0, n1))
    log("  escalations: %d needing review, %d informational" % (act, info))
    (harbor / "timings.json").write_text(json.dumps(
        {"total_s": total, "wave1": t1, "wave2": t2, "apply": ta, "tail": tt,
         "jobs": ctx["jobs"], "lint_before": e0, "lint_after": e1}, indent=1), encoding="utf8")
    return 1 if act else 0


if __name__ == "__main__":
    raise SystemExit(main())
