#!/usr/bin/env python3
"""Deterministic verifier lint for Harbor task packages.

Detects the mechanically-detectable anti-patterns from docs/Verifier_Design_Guide.md.
Runs on package bytes only - no model calls, no network.

Usage:
    python lint_verifiers.py <task-folder> [--json] [--strict]

Exit codes: 0 clean or warnings only; 1 errors found; 2 could not read package.
"""
from __future__ import annotations
import argparse, json, os, re, sys, collections

ERROR, WARN, INFO = "error", "warn", "info"


def load_spec(root):
    """Return (verifiers, kind, path). Handles both package generations."""
    cands = []
    for dirpath, _dirs, files in os.walk(root):
        parts = dirpath.replace("\\", "/").split("/")
        if "_app" in parts:
            continue
        if os.path.basename(dirpath) != "tests":
            continue
        for f in files:
            if f in ("verifier.json", "manifest.json"):
                cands.append(os.path.join(dirpath, f))
    if not cands:
        return None, None, None
    cands.sort(key=len)
    for p in cands:
        try:
            d = json.load(open(p, encoding="utf8"))
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        # legacy / variant shapes, most specific first
        if d.get("verifiers"):
            return d["verifiers"], "verifiers[]", p
        if d.get("verifier_configs"):
            return d["verifier_configs"], "verifier_configs[]", p
        spec = d.get("verifier_spec")
        if isinstance(spec, dict) and spec.get("verifiers"):
            return spec["verifiers"], "verifier_spec.verifiers[]", p
        if isinstance(d.get("verifier"), dict) and d["verifier"].get("verifiers"):
            return d["verifier"]["verifiers"], "verifier.verifiers[]", p
    return None, None, cands[0]


def reward_shape(root):
    """Inspect tests/test.sh. Returns 'binary' | 'fractional' | 'other' | None."""
    for dirpath, _dirs, files in os.walk(root):
        if "_app" in dirpath.replace("\\", "/").split("/"):
            continue
        if "test.sh" in files and os.path.basename(dirpath) == "tests":
            try:
                s = open(os.path.join(dirpath, "test.sh"), encoding="utf8", errors="replace").read()
            except Exception:
                return None
            one = re.search(r"echo\s+1\s*>.*reward\.txt", s)
            zero = re.search(r"echo\s+0\s*>.*reward\.txt", s)
            if one and zero:
                return "binary"
            if re.search(r"(passed|ratio|awk|bc)\b", s):
                return "fractional"
            return "other"
    return None


def evidence_key(v):
    """What this check actually reads - used to spot duplicate/non-independent checks."""
    src = v.get("source") or {}
    f = src.get("file") or {}
    a = v.get("assertion") or {}
    det = a.get("deterministic") or {}
    return json.dumps({
        "src": f.get("type") or src.get("type"),
        "cmd": f.get("command"),
        "args": f.get("arguments"),
        "path": det.get("path"),
        "cmp": det.get("comparison"),
        "exp": a.get("expected"),
    }, sort_keys=True, default=str)


def read_prompt(root):
    for dirpath, _dirs, files in os.walk(root):
        if "_app" in dirpath.replace("\\", "/").split("/"):
            continue
        if "instruction.md" in files:
            try:
                return open(os.path.join(dirpath, "instruction.md"),
                            encoding="utf8", errors="replace").read()
            except Exception:
                return ""
    return ""


def run_failures(root):
    """Return (Counter name -> runs failed, number of runs seen)."""
    fails, runs = collections.Counter(), 0
    for dirpath, _dirs, files in os.walk(root):
        if not dirpath.replace("\\", "/").endswith("/verifier"):
            continue
        if "test-stdout.txt" in files:
            try:
                s = open(os.path.join(dirpath, "test-stdout.txt"),
                         encoding="utf8", errors="replace").read()
            except Exception:
                continue
            runs += 1
            for n in set(re.findall(r"^FAILED .*?\[(.+?)\]", s, re.M)):
                fails[n] += 1
        elif "verifier_summary.json" in files:
            try:
                d = json.load(open(os.path.join(dirpath, "verifier_summary.json"), encoding="utf8"))
            except Exception:
                continue
            runs += 1
            rubric = (d.get("reward") or {}).get("rubric") or {}
            for item in rubric.get("items") or []:
                for a in item.get("assertion_results") or []:
                    if (a.get("result") or {}).get("success") is False:
                        fails[a.get("name")] += 1
    return fails, runs


def stem(name):
    return re.sub(r"[_-]?[a-z]{0,4}?\d+[a-z0-9_]*$", "", name or "")


def classify_tier(v):
    src = v.get("source") or {}
    f = src.get("file") or {}
    a = v.get("assertion") or {}
    det = a.get("deterministic") or {}
    ftype, cmd, path = f.get("type"), f.get("command"), det.get("path") or ""
    if cmd == "check_path_exists" or path in ("$.is_file", "$.exists"):
        return "T0"
    if a.get("type") in ("rubric", "agentic_llm_as_judge"):
        return "T4"
    if v.get("verifier_type") == "rubric_check":
        return "T4"
    if ftype in ("md", "text", "docx", "pdf"):
        return "T4"
    return "T2"


def lint(root):
    findings = []

    def add(level, code, msg, verifier=None, detail=None):
        findings.append({"level": level, "code": code, "message": msg,
                         "verifier": verifier, "detail": detail})

    verifiers, kind, path = load_spec(root)
    if verifiers is None:
        add(ERROR, "L0", "No parseable verifier spec found under " + str(root))
        return findings, {}
    prompt = read_prompt(root)
    fails, nruns = run_failures(root)

    n = len(verifiers)
    tiers = collections.Counter()
    names = []
    ekeys = collections.defaultdict(list)

    shape = reward_shape(root)
    if shape == "binary":
        add(INFO, "OWN1",
            "tests/test.sh emits binary 1/0 reward - tier weighting is an INFRASTRUCTURE change, "
            "not a trainer fix. Every check is an equal veto.")
    elif shape == "fractional":
        add(INFO, "OWN2", "tests/test.sh appears to emit a fractional reward - weighting may be honoured")

    for v in verifiers:
        if not isinstance(v, dict):
            continue
        nm = v.get("name")
        names.append(nm)
        tiers[classify_tier(v)] += 1
        ekeys[evidence_key(v)].append(nm)

        a = v.get("assertion") or {}
        det = a.get("deterministic") or {}
        src = v.get("source") or {}
        f = src.get("file") or {}
        cmp_ = det.get("comparison") or a.get("type")
        exp = a.get("expected")
        why = ((v.get("metadata") or {}).get("why_justification")) or ""

        if isinstance(exp, str) and cmp_ in ("regex_match", "not_regex_match"):
            if re.search(r",\s*\.\*\s*,", exp) or ",.*," in exp:
                add(ERROR, "A3",
                    "Column-count coupling: pattern encodes how many CSV columns exist",
                    nm, exp[:160])
            if exp.count("\\n") >= 2:
                add(ERROR, "A4",
                    "Row-order coupling: pattern requires rows in a fixed sequence",
                    nm, exp[:160])
            if "\\x22?" in exp or '"?' in exp:
                add(WARN, "A2b",
                    "Quote hack: pattern hand-handles CSV quoting - parse instead",
                    nm, exp[:160])
            if f.get("type") in ("csv", "json", "xlsx"):
                add(WARN, "A2",
                    "Regex over raw " + str(f.get("type")) + " text - parse the file and compare the field",
                    nm, exp[:160])

        if cmp_ == "approx_equals" and det.get("tolerance") in (None, ""):
            add(WARN, "P6", "Numeric comparison with no tolerance set", nm)

        if a.get("type") in ("rubric", "agentic_llm_as_judge"):
            add(WARN, "P7",
                "LLM-judged check - must be graded twice on one trajectory before shipping", nm)

        if not why.strip():
            add(WARN, "A1b", "No why_justification - cannot trace this check to the prompt", nm)
        elif prompt:
            toks = re.findall(r"[A-Za-z_][A-Za-z0-9_\-]{4,}", why)[:12]
            if toks and not any(t.lower() in prompt.lower() for t in toks):
                add(INFO, "A1c",
                    "why_justification shares no vocabulary with the prompt - check traceability", nm)

    dupes = [(k, v) for k, v in ekeys.items() if len(v) > 1]
    for _k, group in sorted(dupes, key=lambda kv: -len(kv[1]))[:6]:
        add(WARN, "A11",
            "Duplicate evidence: " + str(len(group)) +
            " checks read the same source and assert the same thing - one requirement, double weight",
            None, ", ".join([str(g) for g in group[:6]]))

    fam = collections.Counter(stem(x) for x in names if x)
    big = {k: c for k, c in fam.items() if c >= 5 and k}
    for k, c in sorted(big.items(), key=lambda kv: -kv[1])[:6]:
        add(WARN if c < 20 else ERROR, "A5",
            "Per-row explosion: " + str(c) + " verifiers share the stem '" + k +
            "' - collapse into one table check", None, str(c) + " checks")

    if n > 50:
        add(ERROR, "A5b", str(n) + " verifiers declared - target is 8-20; above 50 is unreviewable")
    elif n > 20:
        add(WARN, "A5b", str(n) + " verifiers declared - target is 8-20; justify each one above 20")
    elif n < 5:
        add(WARN, "A9b", "only " + str(n) + " verifiers declared - check the task is actually graded")

    if tiers.get("T4") and tiers["T4"] < 5:
        add(WARN, "T4min", "only " + str(tiers["T4"]) +
            " prose/T4 checks - declare >=5 so one wording miss cannot dominate")

    if nruns >= 3:
        free = [x for x in names if x and fails.get(x, 0) == 0]
        if free:
            share = 100.0 * len(free) / max(1, len(names))
            add(WARN if share < 50 else ERROR, "A9",
                str(len(free)) + "/" + str(len(names)) + " verifiers (" + format(share, ".0f") +
                "%) never failed in " + str(nruns) + " runs - free points",
                None, ", ".join([x for x in free[:8]]))
        always = [x for x in names if x and fails.get(x, 0) == nruns]
        if always:
            add(INFO, "A9c", str(len(always)) + " verifiers failed in every run - verify they are fair",
                None, ", ".join([x for x in always[:8]]))
        if not any(0 < fails.get(x, 0) < nruns for x in names if x):
            add(ERROR, "L8", "no verifier changed verdict across " + str(nruns) +
                " runs - this task measures nothing")

    stats = {"n_verifiers": n, "spec": kind, "spec_path": path, "tiers": dict(tiers),
             "runs_seen": nruns, "prompt_chars": len(prompt)}
    return findings, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true", help="exit 1 on warnings too")
    args = ap.parse_args()
    if not os.path.isdir(args.root):
        sys.stderr.write("not a directory: " + args.root + "\n")
        sys.exit(2)
    findings, stats = lint(args.root)
    if args.json:
        print(json.dumps({"stats": stats, "findings": findings}, indent=1))
    else:
        print("== verifier lint: " + args.root)
        print("   spec=" + str(stats.get("spec")) +
              " verifiers=" + str(stats.get("n_verifiers")) +
              " tiers=" + str(stats.get("tiers")) +
              " runs_seen=" + str(stats.get("runs_seen")))
        order = {ERROR: 0, WARN: 1, INFO: 2}
        for f in sorted(findings, key=lambda x: order[x["level"]]):
            who = " [" + str(f["verifier"]) + "]" if f.get("verifier") else ""
            print("   " + f["level"].upper().ljust(5) + " " + f["code"].ljust(5) + who + " " + f["message"])
            if f.get("detail"):
                print("         " + str(f["detail"])[:150])
        ne = sum(1 for f in findings if f["level"] == ERROR)
        nw = sum(1 for f in findings if f["level"] == WARN)
        print("   -> " + str(ne) + " error(s), " + str(nw) + " warning(s)")
    ne = sum(1 for f in findings if f["level"] == ERROR)
    nw = sum(1 for f in findings if f["level"] == WARN)
    sys.exit(1 if (ne or (args.strict and nw)) else 0)


if __name__ == "__main__":
    main()
