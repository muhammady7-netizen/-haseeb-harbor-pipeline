#!/usr/bin/env python3
"""Deterministic pre-flight probe for harbor-task-repair.

Answers, for all 13 steps at once and without a single model call, the question each
subagent currently pays a full spawn to answer: *is there anything here for me to do,
and if so which checks are the candidates?*

Steps whose probe is fully deterministic and finds nothing are marked `skip` — the
orchestrator records `not_applicable` without spawning. Steps whose probe is semantic
are always `run`; the probe only narrows their candidate list, never decides for them.

Standard library only. Reuses lint_verifiers so the two can never disagree.

Usage:
    python probe.py <task> --json > .harbor-repair/probe.json
    python probe.py <task>                # human-readable table
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lint_verifiers import load_spec, reward_shape, read_prompt, lint  # noqa: E402

# Steps we may skip on a deterministic zero. A step earns a place here ONLY if its defect
# class is structurally impossible without the signal - not merely "usually correlates with".
#
#   02 hygiene  - mirror drift / leaked solution / missing engine are filesystem facts.
#   05 format   - the class is exactly {A2, A2b, A3, A4}; zero signal means the enumerated
#                 taxonomy is empty. Depends on those four lint detectors being correct.
#   07 prose    - prose grading requires a check that reads a prose file. No such check,
#                 no such defect.
#   09 scoring  - with a binary test.sh every check is an equal veto; there is no scoring
#                 surface a trainer owns. A5/A9 cover free points and per-row explosion.
#   10 judge    - judge instability requires a judge.
#
# 08 independence is deliberately NOT here. Measured on code-c284: lint reported A11=0 while
# step 08 legitimately dropped 5 subset checks (4 result_*_count + csv_row_count). Whether a
# count is derivable from a fuller check is a semantic question; gating on A11 is a false skip.
DETERMINISTIC = {"02", "05", "07", "09", "10"}
ALWAYS = {"00", "01", "04", "11", "12"}
SEMANTIC = {"03", "06", "08"}

# Assertion fields that carry an *expected value* rather than a pattern or a selector.
# Step 06 asks "does the prompt teach this word?" - only these fields can answer it.
EXPECTED_FIELDS = ("expected", "expected_value", "value", "equals")
PATTERN_FIELDS = ("pattern", "regex", "path", "comparison", "type", "flags")

PROSE_TYPES = {"md", "text", "docx", "pdf", "txt"}
JUDGE_ASSERTIONS = {"rubric", "agentic_llm_as_judge"}


def walk_skip_mirror(root):
    for dirpath, dirs, files in os.walk(root):
        if "_app" in dirpath.replace("\\", "/").split("/"):
            continue
        yield dirpath, dirs, files


def vname(v):
    return v.get("name") or v.get("id") or v.get("verifier_name") or "<unnamed>"


def flatten(verifiers):
    """Connector packages nest the real checks under each entry's `verifier_spec.verifiers[]`.
    Reading only the outer level sees no sources and no assertions, which a naive probe would
    read as 'nothing to do'. Expand one level so the real checks are inspected."""
    out = []
    for v in verifiers or []:
        spec = v.get("verifier_spec")
        inner = spec.get("verifiers") if isinstance(spec, dict) else None
        if inner:
            for iv in inner:
                child = dict(iv)
                child["name"] = "%s/%s" % (vname(v), vname(iv))
                for carry in ("weight", "category", "verifier_type", "rubric"):
                    child.setdefault(carry, v.get(carry))
                out.append(child)
        else:
            out.append(v)
    return out


def inspectable(verifiers):
    """How many checks actually expose something to probe. Zero means the spec is opaque to
    us - which is NOT the same as clean, and must never produce a skip."""
    n = 0
    for v in verifiers:
        if (v.get("source") or v.get("assertion") or v.get("rubric")
                or v.get("verifier_type") or v.get("expected_tools")):
            n += 1
    return n


def literals(v):
    """Every literal scalar the check demands, with where it came from."""
    out = []

    def rec(node, path):
        if isinstance(node, dict):
            for k, val in node.items():
                rec(val, path + "." + str(k))
        elif isinstance(node, list):
            for i, val in enumerate(node):
                rec(val, path + "[%d]" % i)
        elif isinstance(node, str) and node.strip():
            out.append((node, path))

    rec(v.get("assertion") or {}, "assertion")
    return out


def source_type(v):
    src = v.get("source") or {}
    f = src.get("file") or {}
    return f.get("type")


def assertion_type(v):
    return (v.get("assertion") or {}).get("type")


def probe_02_hygiene(root, verifiers, spec_path, findings):
    """Mirror drift, leaked solution, missing engine, ambiguous spec shape."""
    reasons = []
    tests_dir = mirror_dir = None
    for dp, _d, files in walk_skip_mirror(root):
        if os.path.basename(dp) == "tests" and (
            "verifier.json" in files or "manifest.json" in files or "test.sh" in files
        ):
            tests_dir = dp
            break
    cand = os.path.join(root, "environment", "_app", "tests")
    if os.path.isdir(cand):
        mirror_dir = cand

    if tests_dir and mirror_dir:
        def snap(d):
            m = {}
            for dp, _dd, ff in os.walk(d):
                for f in ff:
                    if f.endswith(".pyc") or "__pycache__" in dp:
                        continue
                    p = os.path.join(dp, f)
                    try:
                        m[os.path.relpath(p, d).replace("\\", "/")] = os.path.getsize(p)
                    except OSError:
                        pass
            return m
        a, b = snap(tests_dir), snap(mirror_dir)
        drift = sorted(set(a) ^ set(b)) + sorted(k for k in set(a) & set(b) if a[k] != b[k])
        if drift:
            reasons.append("mirror drift: %d file(s), e.g. %s" % (len(drift), ", ".join(drift[:3])))
    elif tests_dir and not mirror_dir and os.path.isdir(os.path.join(root, "environment", "_app")):
        # Only a defect when _app/ exists but its tests/ mirror is missing. Many packages use
        # root injection and ship no _app/ at all - that is a different architecture, not drift.
        # Flagging it cost a wasted step-02 spawn on 3 of 4 measured packages.
        reasons.append("environment/_app/ exists but has no tests/ mirror")

    app = os.path.join(root, "environment", "_app")
    if os.path.isdir(app):
        for entry in os.listdir(app):
            if "solution" in entry.lower():
                reasons.append("possible leaked solution in _app: %s" % entry)

    specs = []
    for dp, _d, files in walk_skip_mirror(root):
        if os.path.basename(dp) == "tests":
            for f in files:
                if f in ("verifier.json", "manifest.json"):
                    specs.append(os.path.join(dp, f))
    if len(specs) > 1:
        reasons.append("ambiguous spec shape: %d spec files" % len(specs))

    for f in findings:
        if f.get("code") in ("L0",):
            reasons.append("lint %s: %s" % (f["code"], f["message"][:70]))
    return reasons


def probe_05_format(findings):
    codes = ("A2", "A2b", "A3", "A4")
    hits = [f for f in findings if f.get("code") in codes]
    return ["%s %s: %s" % (f["code"], f.get("verifier") or "-", f["message"][:70]) for f in hits]


def probe_07_prose(verifiers):
    out = []
    for v in verifiers:
        st, at = source_type(v), assertion_type(v)
        if st in PROSE_TYPES or at in JUDGE_ASSERTIONS:
            out.append("%s (source=%s assertion=%s)" % (vname(v), st, at))
    return out


def probe_08_independence(root, verifiers, findings):
    out = ["A11 %s: %s" % (f.get("verifier") or "-", f["message"][:70])
           for f in findings if f.get("code") == "A11"]

    sol_text = ""
    for dp, _d, files in walk_skip_mirror(root):
        if os.path.basename(dp) == "solution":
            for f in files:
                if os.path.splitext(f)[1] in (".py", ".csv", ".md", ".json", ".txt", ".sh"):
                    try:
                        sol_text += open(os.path.join(dp, f), encoding="utf8",
                                         errors="replace").read()
                    except OSError:
                        pass
    if sol_text:
        seen = set()
        for v in verifiers:
            for lit, path in literals(v):
                s = lit.strip()
                # only distinctive constants; short/common strings are noise
                if len(s) < 4 or not re.search(r"[0-9]", s) or s in seen:
                    continue
                if s in sol_text:
                    seen.add(s)
                    out.append("constant %r in %s also appears in solution/" % (s[:40], vname(v)))

    # Count/total-shaped checks are the classic derivable-subset shape: the count is implied
    # by whatever check asserts the full content. This is a HINT, never a verdict - deciding
    # derivability is the subagent's job. Measured against code-c284, where the five checks
    # step 08 dropped were exactly of this shape and carried no A11 finding.
    for v in verifiers:
        nm = vname(v)
        det = (v.get("assertion") or {}).get("deterministic") or {}
        path = det.get("path") or ""
        if re.search(r"(_count|_total|_sum|_len(gth)?)$", nm) or \
           re.search(r"(_count|_total|_sum)$", path):
            out.append("count-shaped %s (path=%s) - check derivability from a fuller check"
                       % (nm, path or "-"))
    return out


def probe_09_scoring(root, findings):
    codes = ("A5", "A5b", "A9", "A9b", "A9c")
    hits = [f for f in findings if f.get("code") in codes]
    out = ["%s %s: %s" % (f["code"], f.get("verifier") or "-", f["message"][:70]) for f in hits]
    shape = reward_shape(root)
    note = None
    if shape == "binary" and not out:
        # Every check is an equal veto and tier weighting is an infrastructure change.
        # There is nothing a trainer can legitimately do here.
        note = "binary reward and no A5/A9 - tier weighting is infrastructure-owned"
    return out, shape, note


def probe_10_judge(root, verifiers):
    out = []
    for v in verifiers:
        if assertion_type(v) in JUDGE_ASSERTIONS or v.get("verifier_type") == "rubric_check":
            out.append("%s (%s)" % (vname(v), assertion_type(v) or v.get("verifier_type")))
    for dp, _d, files in walk_skip_mirror(root):
        for f in files:
            if f == "rubric.toml":
                p = os.path.join(dp, f)
                try:
                    if os.path.getsize(p) > 0:
                        out.append("rubric.toml present (%d bytes)" % os.path.getsize(p))
                except OSError:
                    pass
    return out


def expected_values(v):
    """Only the literals that are genuinely *expected values*. Patterns, JSONPath
    selectors and comparison operators are other steps' business and produced most of the
    noise when this scanned every string in the assertion."""
    out = []

    def rec(node, key):
        if isinstance(node, dict):
            for k, val in node.items():
                rec(val, k)
        elif isinstance(node, list):
            for val in node:
                rec(val, key)
        elif isinstance(node, str):
            if key in EXPECTED_FIELDS and key not in PATTERN_FIELDS:
                out.append(node)

    rec(v.get("assertion") or {}, None)
    return out


def probe_06_equivalence(verifiers, prompt):
    """Expected values the prompt never teaches. Candidates only - never a skip decision,
    because whether a synonym is acceptable is a judgement call."""
    low = re.sub(r"[^a-z0-9 ]+", " ", prompt.lower())
    out = []
    total = 0
    for v in verifiers:
        for s in expected_values(v):
            s = s.strip()
            if len(s) < 3 or s.startswith("$.") or re.fullmatch(r"[\W_\d.]+", s):
                continue
            if s.lower() in ("true", "false", "null", "none"):
                continue
            total += 1
            probe = re.sub(r"[^a-z0-9 ]+", " ", s.lower()).strip()
            if probe and probe not in low:
                out.append("%s expects %r - prompt never uses it" % (vname(v), s[:50]))
    return out, total


def probe_03_traceability(findings):
    return ["%s %s: %s" % (f["code"], f.get("verifier") or "-", f["message"][:70])
            for f in findings if f.get("code") in ("A1b", "A1c")]


ENGINE_SOURCE_FILES = {
    "__init__.py", "artifacts.py", "csv.py", "docx.py", "filesystem.py", "json.py",
    "md.py", "pdf.py", "pptx.py", "registry.py", "response.py", "text.py", "xlsx.py",
}


def affordances(root):
    """What mechanisms a repair may ACTUALLY use here.

    A diagnostician that never implements its own proposal will propose things that cannot be
    built. Measured on code-c284: step 05 demanded a parsed-field comparison via a new engine
    source adapter, the applier could not legally create one, and five intents died in
    `unapplied[]` - while the sequential run, whose fixer had to implement its own proposal,
    chose a mechanism that existed and closed the same defects.

    So state the affordances up front. The important asymmetry:

      * `tests/test_outputs.py` is TASK-OWNED - arbitrary Python, the escape hatch for any
        logic the verifier DSL cannot express. This is where parsed-CSV comparison belongs.
      * A NEW engine source adapter is NOT available: registry.py hardcodes
        SOURCE_NAMESPACE_MODULES with no auto-discovery, so registering one means editing a
        protected engine file. That is an escalation, never a repair.
    """
    src_dir = None
    for dp, dirs, files in walk_skip_mirror(root):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        if os.path.basename(dp) == "sources" and "registry.py" in files:
            src_dir = dp
            break

    commands, task_owned = [], []
    if src_dir:
        for f in sorted(os.listdir(src_dir)):
            if not f.endswith(".py") or f == "__init__.py":
                continue
            ns = f[:-3]
            try:
                txt = open(os.path.join(src_dir, f), encoding="utf8", errors="replace").read()
            except OSError:
                continue
            if f not in ENGINE_SOURCE_FILES:
                task_owned.append("%s (task-owned adapter, already registered)" % ns)
            if f == "registry.py":
                continue
            for m in re.finditer(r'name\s*(?::\s*str\s*)?=\s*"([a-z_]+)"', txt):
                commands.append("%s.%s" % (ns, m.group(1)))

    editable = ["tests/verifier.json (the spec)"]
    for dp, _d, files in walk_skip_mirror(root):
        if os.path.basename(dp) == "tests":
            for f in sorted(files):
                if f.startswith("test") and f.endswith(".py"):
                    editable.append("tests/%s (task-owned Python - arbitrary pytest assertions)" % f)
    return {
        "source_commands_available": sorted(set(commands)),
        "task_owned_adapters_present": task_owned,
        "editable_targets": editable,
        "fix_in_place_first": (
            "A brittle pattern MUST be fixed in assertion.expected itself - that is fully "
            "expressible in the DSL and is the primary repair. Remove column-count coupling "
            "(a ',.*,' segment), row-order coupling (two or more newlines in one pattern), and "
            "quote hacks ('\"?' or '\\\\x22?'). Rewriting how_justification while leaving the "
            "pattern intact is NOT a repair: it makes the spec claim a fix that did not "
            "happen, which is worse than leaving the check alone."),
        "escape_hatch": ("Only for logic the DSL genuinely cannot express - multiset equality, "
                         "duplicate-row detection, cross-field joins - add a plain pytest "
                         "assertion in the task-owned tests/test_*.py and set files_to_change "
                         "to that file. That is an ADDITION to fixing the brittle pattern, "
                         "never a SUBSTITUTE for it. Never write a bigger regex to emulate "
                         "parsing."),
        "not_available": ("A NEW engine source adapter. registry.py hardcodes "
                          "SOURCE_NAMESPACE_MODULES with no auto-discovery, so registering one "
                          "requires editing a protected engine file. Proposing one is an "
                          "ESCALATION, not a finding."),
    }


def build(root):
    raw_verifiers, kind, spec_path = load_spec(root)
    verifiers = flatten(raw_verifiers)
    n_inspectable = inspectable(verifiers)
    # No spec found is the most opaque case of all - never let it look like a clean task.
    opaque = n_inspectable == 0
    findings, stats = lint(root)
    prompt = read_prompt(root)

    steps = {}

    def add(nn, name, decision, candidates, note=None):
        # A deterministic skip is only honest when we could actually see the checks.
        # An opaque spec (connector metadata with no source/assertion) gets run, not skipped.
        if decision == "skip" and opaque:
            decision, note = "run", "spec not inspectable - probe cannot see sources/assertions"
        steps[nn] = {
            "step": nn, "name": name, "decision": decision,
            "candidates": candidates, "n_candidates": len(candidates),
        }
        if note:
            steps[nn]["note"] = note

    add("00", "route", "run", [], "always - routes ownership")
    add("01", "contract", "run", [], "always - the cold read")

    c = probe_02_hygiene(root, verifiers, spec_path, findings)
    add("02", "hygiene", "run" if c else "skip", c)

    c = probe_03_traceability(findings)
    add("03", "traceability", "run", c,
        "semantic - lint codes are hints, not proof; never auto-skipped")

    add("04", "coverage", "run", [], "semantic - depends on contract.json from step 01")

    c = probe_05_format(findings)
    add("05", "format", "run" if c else "skip", c)

    c, nlit = probe_06_equivalence(verifiers, prompt)
    if nlit == 0:
        add("06", "equivalence", "skip", c, "no literal expected values in any check")
    else:
        add("06", "equivalence", "run", c,
            "semantic - %d literal(s) scanned; candidates are unquoted ones" % nlit)

    c = probe_07_prose(verifiers)
    add("07", "prose", "run" if c else "skip", c)

    c = probe_08_independence(root, verifiers, findings)
    add("08", "independence", "run", c,
        "semantic - derivability is not syntactic; candidates are hints only")

    c, shape, note = probe_09_scoring(root, findings)
    add("09", "scoring", "run" if c else "skip", c, note or ("reward shape: %s" % shape))

    c = probe_10_judge(root, verifiers)
    add("10", "judge", "run" if c else "skip", c)

    add("11", "proof", "run", [], "always - gates step 12")
    add("12", "coherence", "run", [], "always")

    skipped = [k for k, v in steps.items() if v["decision"] == "skip"]
    return {
        "task": root.replace("\\", "/"),
        "spec": {"kind": kind, "path": (spec_path or "").replace("\\", "/"),
                 "n_verifiers": len(verifiers),
                 "n_declared": len(raw_verifiers or []),
                 "n_inspectable": n_inspectable,
                 "opaque": opaque},
        "reward_shape": reward_shape(root),
        "affordances": affordances(root),
        "lint": {
            "errors": sum(1 for f in findings if f.get("level") == "error"),
            "warnings": sum(1 for f in findings if f.get("level") == "warning"),
        },
        "steps": steps,
        "skip": sorted(skipped),
        "run": sorted(k for k in steps if k not in skipped),
        "spawns_saved": len(skipped),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if not os.path.isdir(args.root):
        sys.stderr.write("not a directory: %s\n" % args.root)
        sys.exit(2)
    r = build(args.root)
    if r["spec"]["n_declared"] == 0:
        sys.stderr.write("no verifier spec found under %s - not a task package\n" % args.root)
        sys.exit(3)
    if args.json:
        print(json.dumps(r, indent=1))
        return
    print("task            : %s" % r["task"])
    print("verifiers       : %s declared -> %s after flatten (%s)"
          % (r["spec"]["n_declared"], r["spec"]["n_verifiers"], r["spec"]["kind"]))
    print("inspectable     : %s%s" % (r["spec"]["n_inspectable"],
                                      "   *** OPAQUE - no deterministic skips ***"
                                      if r["spec"]["opaque"] else ""))
    print("reward shape    : %s" % r["reward_shape"])
    print("lint            : %d error(s), %d warning(s)"
          % (r["lint"]["errors"], r["lint"]["warnings"]))
    print("")
    print("%-4s %-14s %-5s %-5s %s" % ("step", "name", "do", "cand", "note"))
    print("-" * 78)
    for nn in sorted(r["steps"]):
        s = r["steps"][nn]
        print("%-4s %-14s %-5s %-5s %s"
              % (nn, s["name"], s["decision"], s["n_candidates"], s.get("note", "")[:34]))
    print("")
    print("SKIP (no spawn) : %s" % (", ".join(r["skip"]) or "none"))
    print("RUN  (spawn)    : %s" % ", ".join(r["run"]))
    print("spawns saved    : %d of 13" % r["spawns_saved"])


if __name__ == "__main__":
    main()
