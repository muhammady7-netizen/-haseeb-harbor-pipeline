#!/usr/bin/env python3
"""Proof suite for Harbor verifier repair - the executable behind recipe 11.

Two halves, because a verifier must be BOTH:

  * FAIR    - representation-only variants of a correct answer must PASS
  * HARD    - every meaning-changing mutant must FAIL, for the intended reason

Adapted from Junaid's mutation_probe.py / replay_verifier.py (workspace prep, symlink
refusal, unsafe-execution gating) with three additions recipe 11 requires:
representation-only variants, case-kind tagging with required-coverage enforcement,
and per-check attribution so "failed for the intended reason" is checkable.

Usage:
    python proof_suite.py <task-folder> --output-dir <dir-OUTSIDE-task> [flags]

Flags:
    --run                  actually execute the verifier (otherwise only generate)
    --allow-unsafe-local   permit host pytest. Diagnostic only; cannot certify.
    --order-required       the prompt fixes row order, so row-reorder is NOT a fair variant
    --max-mutations N      cap generated mutants (default 40)
    --timeout N            per-run seconds (default 300)

Exit: 0 gate passed or generate-only; 1 gate failed / needs decision; 2 blocked.
"""
from __future__ import annotations

import argparse, csv, io, json, os, re, shutil, subprocess, sys, time
from pathlib import Path
from typing import Any, Callable

# recipe 11 case kinds. representation-only is the fairness control and can never be excepted.
MUST_FAIL_KINDS = ("exact-fact", "set-list", "relationship-join", "scope-precedence",
                   "exclusion", "aggregate", "prose-rubric", "hardcoding")
MUST_PASS_KINDS = ("representation-only",)
# These depend on task semantics (which rule, which key, which record should be excluded).
# The harness cannot synthesise them from artifacts alone; the subagent must construct them
# from the contract, or document why the task has no such rule. Recipe 11 allows the latter.
SEMANTIC_KINDS = ("scope-precedence", "exclusion", "relationship-join")

Case = tuple[str, str, str, Callable[[Path], None]]   # (kind, name, relative_path, mutate)


# ---------------------------------------------------------------- safety / workspace

def _reject_symlinks(root: Path, label: str) -> None:
    if root.is_symlink():
        raise RuntimeError("Refusing symlinked " + label)
    if root.is_dir():
        for p in root.rglob("*"):
            if p.is_symlink():
                raise RuntimeError("Refusing symlink inside " + label + ": " + p.name)


def prepare_workspace(task_root: Path, workspace: Path) -> None:
    """Copy the golden deliverables + task inputs into a disposable workspace."""
    workspace.mkdir(parents=True, exist_ok=True)
    for rel, label in (("solution/files", "solution workspace"),
                       ("environment/input", "task inputs"),
                       ("input", "task inputs")):
        src = task_root / rel
        _reject_symlinks(src, label)
        if src.is_dir():
            dest = workspace / "input" if rel.endswith("input") else workspace
            shutil.copytree(src, dest, dirs_exist_ok=True)


def deliverables(workspace: Path) -> list[Path]:
    out = []
    for p in sorted(workspace.rglob("*")):
        if p.is_file() and "input" not in p.relative_to(workspace).parts and ".pytest" not in str(p):
            out.append(p)
    return out


# ---------------------------------------------------------------- csv helpers

def _read_csv(path: Path):
    delim = "\t" if path.suffix.lower() == ".tsv" else ","
    with path.open(newline="", encoding="utf-8-sig") as fh:
        return delim, list(csv.reader(fh, delimiter=delim))


def _write_csv(path: Path, delim, rows, quoting=csv.QUOTE_MINIMAL, newline="\r\n"):
    buf = io.StringIO()
    csv.writer(buf, delimiter=delim, quoting=quoting, lineterminator=newline).writerows(rows)
    path.write_text(buf.getvalue(), encoding="utf-8", newline="")


# ---------------------------------------------------------------- FAIR: must pass

def representation_cases(rel: str, src: Path, order_required: bool) -> list[Case]:
    """Variants of a CORRECT answer that only change representation. These must PASS."""
    if src.suffix.lower() not in (".csv", ".tsv"):
        return []
    try:
        delim, rows = _read_csv(src)
    except Exception:
        return []
    if len(rows) < 2:
        return []
    cases: list[Case] = []

    def quote_all(p: Path) -> None:
        d, r = _read_csv(p); _write_csv(p, d, r, quoting=csv.QUOTE_ALL, newline="\n")
    cases.append(("representation-only", "quote-all", rel, quote_all))

    def crlf(p: Path) -> None:
        d, r = _read_csv(p); _write_csv(p, d, r, newline="\r\n")
    cases.append(("representation-only", "crlf-line-endings", rel, crlf))

    def pad(p: Path) -> None:
        d, r = _read_csv(p)
        r = [[(" " + c + " ") if c else c for c in row] for row in r]
        _write_csv(p, d, r, newline="\n")
    cases.append(("representation-only", "surrounding-whitespace", rel, pad))

    # numeric notation: 1234.5 -> 1,234.50 where a column is wholly numeric
    numeric_cols = []
    for ci in range(len(rows[0])):
        vals = [r[ci] for r in rows[1:] if ci < len(r) and r[ci].strip()]
        if vals and all(re.fullmatch(r"-?\d+(\.\d+)?", v.strip()) for v in vals):
            numeric_cols.append(ci)
    if numeric_cols:
        def renotate(p: Path, cols=tuple(numeric_cols)) -> None:
            d, r = _read_csv(p)
            for row in r[1:]:
                for ci in cols:
                    if ci < len(row) and row[ci].strip():
                        try:
                            row[ci] = "{:,.2f}".format(float(row[ci]))
                        except ValueError:
                            pass
            _write_csv(p, d, r, newline="\n")
        cases.append(("representation-only", "numeric-notation", rel, renotate))

    if not order_required and len(rows) > 2:
        def reorder(p: Path) -> None:
            d, r = _read_csv(p)
            body = r[1:]; body.reverse()
            _write_csv(p, d, [r[0]] + body, newline="\n")
        cases.append(("representation-only", "row-order-reversed", rel, reorder))
    return cases


# ---------------------------------------------------------------- HARD: must fail

def mutation_cases(rel: str, src: Path) -> list[Case]:
    suf = src.suffix.lower()
    cases: list[Case] = []

    if suf in (".csv", ".tsv"):
        try:
            delim, rows = _read_csv(src)
        except Exception:
            return []
        if len(rows) < 2:
            return []

        def drop_row(p: Path) -> None:
            d, r = _read_csv(p); r.pop(1); _write_csv(p, d, r, newline="\n")
        cases.append(("set-list", "drop-required-row", rel, drop_row))

        def dup_row(p: Path) -> None:
            d, r = _read_csv(p); r.insert(2, list(r[1])); _write_csv(p, d, r, newline="\n")
        cases.append(("set-list", "duplicate-row", rel, dup_row))

        def extra_row(p: Path) -> None:
            d, r = _read_csv(p)
            r.append(["ZZ-EXTRA"] + ["x"] * (len(r[0]) - 1)); _write_csv(p, d, r, newline="\n")
        cases.append(("set-list", "add-extra-row", rel, extra_row))

        # exact-fact + aggregate, per column
        for ci, header in enumerate(rows[0][:12]):
            vals = [r[ci] for r in rows[1:] if ci < len(r) and r[ci].strip()]
            numeric = bool(vals) and all(re.fullmatch(r"-?\d+(\.\d+)?", v.strip()) for v in vals)
            kind = "aggregate" if numeric else "exact-fact"

            def alter(p: Path, ci=ci, numeric=numeric) -> None:
                d, r = _read_csv(p)
                if ci < len(r[1]):
                    if numeric:
                        try:
                            r[1][ci] = str(float(r[1][ci]) + 1)
                        except ValueError:
                            r[1][ci] = r[1][ci] + "9"
                    else:
                        r[1][ci] = (r[1][ci] or "x") + "__WRONG__"
                _write_csv(p, d, r, newline="\n")
            cases.append((kind, "alter-" + (header or ("col" + str(ci))), rel, alter))

        # relationship-join: swap the key column between two rows
        if len(rows) > 2:
            def swap_key(p: Path) -> None:
                d, r = _read_csv(p)
                r[1][0], r[2][0] = r[2][0], r[1][0]
                _write_csv(p, d, r, newline="\n")
            cases.append(("relationship-join", "swap-join-keys", rel, swap_key))

    elif suf == ".json":
        try:
            data = json.loads(src.read_text(encoding="utf-8"))
        except Exception:
            return []
        if isinstance(data, dict):
            for key in list(data)[:12]:
                v = data[key]
                kind = "aggregate" if isinstance(v, (int, float)) and not isinstance(v, bool) else "exact-fact"

                def alter(p: Path, key=key) -> None:
                    d = json.loads(p.read_text(encoding="utf-8"))
                    cur = d.get(key)
                    if isinstance(cur, bool):      d[key] = not cur
                    elif isinstance(cur, (int, float)): d[key] = cur + 1
                    elif isinstance(cur, str):     d[key] = cur + "__WRONG__"
                    elif isinstance(cur, list):    d[key] = cur[:-1]
                    else:                          d[key] = "__WRONG__"
                    p.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")
                cases.append((kind, "alter-" + str(key), rel, alter))

                def drop(p: Path, key=key) -> None:
                    d = json.loads(p.read_text(encoding="utf-8")); d.pop(key, None)
                    p.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")
                cases.append(("exclusion", "drop-" + str(key), rel, drop))

    elif suf in (".md", ".txt", ".html"):
        def keyword_soup(p: Path) -> None:
            """The gameability control: expected tokens, no reasoning, no structure."""
            text = p.read_text(encoding="utf-8", errors="replace")
            toks = re.findall(r"[A-Z][A-Z0-9_\-]{2,}|\b\d[\d,\.]{2,}\b", text)
            uniq = list(dict.fromkeys(toks))[:120]
            p.write_text(" ".join(uniq) + "\n", encoding="utf-8")
        cases.append(("prose-rubric", "keyword-soup-memo", rel, keyword_soup))

        def invert(p: Path) -> None:
            text = p.read_text(encoding="utf-8", errors="replace")
            for a, b in (("is not", "@@X@@"), ("is ", "is not "), ("@@X@@", "is"),
                         ("compliant", "non-compliant"), ("cleared", "blocked"),
                         ("passed", "failed"), ("eligible", "ineligible")):
                text = text.replace(a, b)
            p.write_text(text, encoding="utf-8")
        cases.append(("prose-rubric", "invert-claims", rel, invert))

        def truncate(p: Path) -> None:
            t = p.read_text(encoding="utf-8", errors="replace")
            p.write_text(t[: max(1, len(t) // 4)], encoding="utf-8")
        cases.append(("prose-rubric", "truncate-memo", rel, truncate))

    # universal: applies to every deliverable
    def blank(p: Path) -> None:
        p.write_bytes(b"")
    cases.append(("exact-fact", "empty-artifact", rel, blank))
    return cases


def hardcoding_case(workspace_input: Path) -> list[Case]:
    """Change an input fixture. A hardcoded answer survives; a real solution's output would differ."""
    if not workspace_input.is_dir():
        return []
    for src in sorted(workspace_input.rglob("*.csv")):
        rel = src.relative_to(workspace_input.parent).as_posix()

        def perturb(p: Path) -> None:
            d, r = _read_csv(p)
            if len(r) > 1:
                r.pop(1)
            _write_csv(p, d, r, newline="\n")
        return [("hardcoding", "input-fixture-changed", rel, perturb)]
    return []


# ---------------------------------------------------------------- verifier execution

def discover_suites(task_root: Path):
    tests = task_root / "tests"
    suites = sorted(p for p in tests.glob("test*.py") if not p.is_symlink())
    return suites


# pytest reports parametrised tests as  FAILED path::test_name[case]  and plain ones as
# FAILED path::test_name. Capture both, or non-parametrised failures become unattributable
# and every such mutant is misreported as "inconclusive".
FAILED_PARAM_RE = re.compile(r"^FAILED\s+\S*?::\S*?\[(.+?)\]", re.M)
FAILED_PLAIN_RE = re.compile(r"^FAILED\s+\S*?::([A-Za-z_]\w*)", re.M)


def _failed_checks(out: str) -> list:
    names = set(FAILED_PARAM_RE.findall(out))
    for m in FAILED_PLAIN_RE.finditer(out):
        line = out[m.start():m.end() + 2]
        if "[" not in line:
            names.add(m.group(1))
    return sorted(names)


def docker_available() -> bool:
    try:
        p = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=60)
        return p.returncode == 0
    except Exception:
        return False


def build_task_image(task_root: Path, tag: str, timeout: int) -> tuple:
    """Build the package's own environment/ image. Returns (ok, message).

    Layer caching means this is paid once per task, not once per case - the verifier itself
    runs in a couple of seconds afterwards.
    """
    env_dir = task_root / "environment"
    if not (env_dir / "Dockerfile").is_file():
        return False, "no environment/Dockerfile - package declares no sandbox"
    try:
        p = subprocess.run(["docker", "build", "-q", "-t", tag, str(env_dir)],
                           capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, "docker build timed out"
    except Exception as e:
        return False, repr(e)[:160]
    if p.returncode != 0:
        return False, ((p.stderr or p.stdout or "").strip()[-300:] or "docker build failed")
    return True, "built " + tag


def run_verifier_docker(task_root: Path, workspace: Path, image: str,
                        timeout: int) -> dict:
    """Run the package's verifier inside its declared sandbox - the certifying path.

    Contract, taken from the package itself (environment/Dockerfile + tests/test.sh):
      * the image sets WORKDIR /app and bakes in the read-only /app/input
      * tests are mounted at /tests
      * test.sh does `cd /app`, runs pytest, and writes 1 or 0 to /logs/verifier/reward.txt
    So the candidate deliverables are copied into /app and the reward file is the verdict.
    """
    suites = discover_suites(task_root)
    if not suites:
        return {"status": "INSUFFICIENT_EVIDENCE", "gate_eligible": False,
                "reason": "no tests/test*.py suites found", "failed_checks": []}
    logs = workspace.parent / (workspace.name + ".logs")
    if logs.exists():
        shutil.rmtree(logs, ignore_errors=True)
    logs.mkdir(parents=True, exist_ok=True)
    cmd = [
        "docker", "run", "--rm", "--network=none",
        "-v", str((task_root / "tests").resolve()) + ":/tests:ro",
        "-v", str(workspace.resolve()) + ":/candidate:ro",
        "-v", str(logs.resolve()) + ":/logs",
        image,
        "bash", "-c",
        "cp -r /candidate/. /app/ 2>/dev/null; bash /tests/test.sh",
    ]
    t0 = time.time()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                              encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        return {"status": "RUNTIME_ERROR", "gate_eligible": False,
                "reason": "container timed out", "failed_checks": []}
    except Exception as e:
        return {"status": "RUNTIME_ERROR", "gate_eligible": False,
                "reason": repr(e)[:160], "failed_checks": []}
    out = (proc.stdout or "") + chr(10) + (proc.stderr or "")
    failed = _failed_checks(out)

    # An engine/environment error is NEVER a rejected mutant, in a container either.
    engine_error = None
    if re.search(r"No module named (pytest|_pytest)", out):
        engine_error = "pytest missing inside the image"
    elif re.search(r"INTERNALERROR", out):
        engine_error = "pytest internal error"
    elif re.search(r"collected 0 items|no tests ran", out):
        engine_error = "no tests collected in the container"
    if engine_error:
        return {"status": "RUNTIME_ERROR", "gate_eligible": False, "reason": engine_error,
                "failed_checks": [], "excerpt": out.strip()[-600:]}

    # The container runs as root, so everything it wrote under the mounted /logs is root-owned
    # and the invoking user cannot delete it. Over a batch that silently accumulates
    # undeletable artifacts and breaks re-runs of the same task. Hand ownership back before
    # reading. Best-effort: a failure here must not fail the case.
    if os.name != "nt":
        try:
            subprocess.run(["docker", "run", "--rm", "--network=none",
                            "-v", str(logs.resolve()) + ":/logs", image,
                            "chown", "-R", "%d:%d" % (os.getuid(), os.getgid()), "/logs"],
                           capture_output=True, timeout=60)
        except Exception:
            pass

    reward_file = logs / "verifier" / "reward.txt"
    reward = None
    try:
        reward = reward_file.read_text(encoding="utf-8").strip()
    except Exception:
        pass
    if reward not in ("0", "1"):
        return {"status": "RUNTIME_ERROR", "gate_eligible": False,
                "reason": "no reward.txt produced - the container did not complete test.sh",
                "failed_checks": failed, "excerpt": out.strip()[-600:]}
    return {
        "status": "PASSED" if reward == "1" else "REJECTED",
        "gate_eligible": True, "sandboxed": True, "reward": reward,
        "failed_checks": failed, "duration_s": round(time.time() - t0, 2),
        "excerpt": "" if reward == "1" else out.strip()[-600:],
    }


def run_verifier(task_root: Path, workspace: Path, python: str, timeout: int,
                 allow_unsafe: bool) -> dict[str, Any]:
    suites = discover_suites(task_root)
    if not suites:
        return {"status": "INSUFFICIENT_EVIDENCE", "gate_eligible": False,
                "reason": "no tests/test*.py suites found", "failed_checks": []}
    if not allow_unsafe:
        return {"status": "BLOCKED_UNSAFE_EXECUTION", "gate_eligible": False,
                "reason": ("Local pytest executes task code with host permissions. Use the "
                           "sandbox the package declares for certification, or pass "
                           "--allow-unsafe-local for a NON-CERTIFYING diagnostic."),
                "failed_checks": []}
    cmd = [python, "-m", "pytest", *[str(p) for p in suites], "-q", "-rA",
           "-p", "no:cacheprovider", "--basetemp", str(workspace / ".pytest-tmp")]
    env = {"PATH": os.environ.get("PATH", ""), "PYTHONUTF8": "1",
           "LANG": os.environ.get("LANG", "C.UTF-8")}
    t0 = time.time()
    try:
        proc = subprocess.run(cmd, cwd=str(workspace), capture_output=True, text=True,
                              timeout=timeout, env=env, encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        return {"status": "RUNTIME_ERROR", "gate_eligible": False,
                "reason": "verifier timed out", "failed_checks": []}
    except Exception as e:
        return {"status": "RUNTIME_ERROR", "gate_eligible": False,
                "reason": repr(e)[:160], "failed_checks": []}
    out = (proc.stdout or "") + "\n" + (proc.stderr or "")
    failed = _failed_checks(out)
    excerpt = out.strip()[-600:]

    # An engine/environment error is NEVER a rejected mutant. Guardrails are explicit, and
    # getting this wrong silently converts a broken harness into fake evidence.
    engine_error = None
    if re.search(r"No module named (pytest|_pytest)", out):
        engine_error = "pytest is not installed in this interpreter"
    elif re.search(r"INTERNALERROR", out):
        engine_error = "pytest internal error"
    elif re.search(r"(ModuleNotFoundError|ImportError)", out):
        engine_error = "verifier imports failed"
    elif re.search(r"collected 0 items|no tests ran", out):
        engine_error = "no tests collected"
    elif proc.returncode not in (0, 1):
        engine_error = "pytest exited " + str(proc.returncode) + " (not a pass/fail code)"

    if engine_error:
        return {"status": "RUNTIME_ERROR", "gate_eligible": False, "reason": engine_error,
                "failed_checks": [], "returncode": proc.returncode, "excerpt": excerpt}

    if proc.returncode == 1 and not failed:
        return {"status": "RUNTIME_ERROR", "gate_eligible": False,
                "reason": "verifier failed but named no check - cannot attribute the rejection",
                "failed_checks": [], "returncode": 1, "excerpt": excerpt}

    return {"status": "PASSED" if proc.returncode == 0 else "REJECTED",
            "gate_eligible": True, "returncode": proc.returncode,
            "failed_checks": failed, "duration_s": round(time.time() - t0, 1)}


# ---------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("task_root", type=Path)
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--allow-unsafe-local", action="store_true")
    ap.add_argument("--order-required", action="store_true",
                    help="prompt fixes row order; row-reorder is not a fair variant")
    ap.add_argument("--max-mutations", type=int, default=40)
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--docker", action="store_true",
                    help="run the verifier inside the package's own environment/ image. "
                         "This is the ONLY certifying mode: test.sh does `cd /app`, which "
                         "exists only in the container.")
    ap.add_argument("--docker-image", default=None,
                    help="reuse an already-built image tag instead of building one")
    args = ap.parse_args()

    task_root, out = args.task_root.resolve(), args.output_dir.resolve()
    if not task_root.is_dir():
        sys.stderr.write("task root not found: " + str(task_root) + "\n"); return 2
    if out == task_root or task_root in out.parents:
        sys.stderr.write("output dir must be OUTSIDE the task root\n"); return 2
    if out.exists() and any(out.iterdir()):
        sys.stderr.write("output dir must be empty or absent\n"); return 2
    out.mkdir(parents=True, exist_ok=True)

    image = None
    if args.docker:
        if not docker_available():
            print(json.dumps({"status": "BLOCKED_NO_DOCKER",
                              "reason": "--docker given but the docker daemon is not reachable "
                                        "(is your user in the docker group? re-login after "
                                        "being added)"}, indent=1)); return 2
        image = args.docker_image
        if not image:
            image = "harbor-proof-" + re.sub(r"[^a-z0-9_.-]+", "-", task_root.name.lower())[:48]
            ok, msg = build_task_image(task_root, image, max(args.timeout, 900))
            if not ok:
                print(json.dumps({"status": "BLOCKED_IMAGE_BUILD", "reason": msg}, indent=1))
                return 2

    baseline = out / "baseline"
    try:
        prepare_workspace(task_root, baseline)
    except RuntimeError as e:
        print(json.dumps({"status": "BLOCKED_UNSAFE_PATH", "reason": str(e)}, indent=1)); return 2

    dels = deliverables(baseline)
    if not dels:
        print(json.dumps({"status": "INSUFFICIENT_COVERAGE",
                          "reason": "no golden deliverables found under solution/files",
                          "hint": "the task may produce side effects rather than files"},
                         indent=1)); return 1

    fair: list[Case] = []
    hard: list[Case] = []
    for p in dels:
        rel = p.relative_to(baseline).as_posix()
        fair += representation_cases(rel, p, args.order_required)
        hard += mutation_cases(rel, p)
    hard += hardcoding_case(baseline / "input")
    # cap, but keep at least one case of every kind we managed to generate
    if len(hard) > args.max_mutations:
        keep, seen = [], set()
        for c in hard:
            if c[0] not in seen:
                keep.append(c); seen.add(c[0])
        for c in hard:
            if len(keep) >= args.max_mutations: break
            if c not in keep: keep.append(c)
        hard = keep

    def _verify(ws):
        if args.docker:
            return run_verifier_docker(task_root, ws, image, args.timeout)
        return run_verifier(task_root, ws, args.python, args.timeout,
                            args.allow_unsafe_local)

    baseline_result = _verify(baseline) if args.run else None
    if args.run and baseline_result and baseline_result["status"] != "PASSED":
        print(json.dumps({"status": "REQUIRES_RERUN",
                          "reason": ("verifier could not execute here - fix the environment or use "
                                     "the task's declared sandbox"
                                     if baseline_result.get("status") == "RUNTIME_ERROR" else
                                     "the verifier REJECTS its own golden - that is a V6 defect, "
                                     "fix it before proving anything"),
                          "baseline": baseline_result}, indent=1)); return 1

    def execute(cases, expect):
        rows = []
        for i, (kind, name, rel, fn) in enumerate(cases, 1):
            ws = out / (expect + "-" + str(i).zfill(3) + "-" + re.sub(r"[^a-zA-Z0-9_.-]+", "-", name)[:50])
            shutil.copytree(baseline, ws)
            target = ws / rel
            try:
                if target.exists() or expect == "mutant":
                    fn(target)
            except Exception as e:
                rows.append({"kind": kind, "name": name, "file": rel,
                             "outcome": "generate_error", "detail": repr(e)[:120]}); continue
            res = _verify(ws) if args.run else None
            row = {"kind": kind, "name": name, "file": rel, "workspace": str(ws), "result": res}
            if res is None:
                row["outcome"] = "generated"
            elif not res.get("gate_eligible"):
                row["outcome"] = "inconclusive"
            elif expect == "variant":
                row["outcome"] = "ok" if res["status"] == "PASSED" else "FAIR_VIOLATION"
                row["failed_checks"] = res.get("failed_checks", [])
            else:
                row["outcome"] = "ok" if res["status"] == "REJECTED" else "SURVIVED"
                row["failed_checks"] = res.get("failed_checks", [])
            rows.append(row)
        return rows

    variants = execute(fair, "variant")
    mutants = execute(hard, "mutant")

    kinds_present = {c[0] for c in hard} | {c[0] for c in fair}
    absent = [k for k in MUST_FAIL_KINDS + MUST_PASS_KINDS if k not in kinds_present]
    # representation-only can never be excepted - it is the fairness control
    missing_kinds = [k for k in absent if k not in SEMANTIC_KINDS]
    requires_manual = [k for k in absent if k in SEMANTIC_KINDS]

    fair_violations = [r for r in variants if r.get("outcome") == "FAIR_VIOLATION"]
    survivors = [r for r in mutants if r.get("outcome") == "SURVIVED"]
    inconclusive = [r for r in variants + mutants if r.get("outcome") == "inconclusive"]

    if not args.run:
        status = "GENERATED_ONLY"
    elif inconclusive:
        status = "INCONCLUSIVE"
    elif fair_violations:
        status = "FAIRNESS_FAILED"
    elif survivors:
        status = "HARDNESS_FAILED"
    elif missing_kinds:
        status = "INSUFFICIENT_COVERAGE"
    else:
        status = "PROOF_PASSED"

    payload = {
        "status": status,
        "certifying": bool(status == "PROOF_PASSED" and args.run and args.docker),
        "note": ("sandboxed in the package's own image; certifying" if args.docker
                 else "host-executed diagnostic; NOT certifying - test.sh needs /app, "
                      "which only exists in the container. Use --docker."
                 if args.allow_unsafe_local
                 else "no verifier execution attempted" if not args.run else ""),
        "baseline": baseline_result,
        "counts": {"variants": len(variants), "mutants": len(mutants),
                   "fair_violations": len(fair_violations), "survivors": len(survivors),
                   "inconclusive": len(inconclusive)},
        "missing_case_kinds": missing_kinds,
        "requires_manual_construction": requires_manual,
        "variants": variants,
        "mutants": mutants,
    }
    (out / "proof.json").write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")

    print("== proof suite: " + str(task_root))
    print("   status            " + status)
    print("   fair variants     " + str(len(variants)) + "  violations: " + str(len(fair_violations)))
    print("   mutants           " + str(len(mutants)) + "  survivors:  " + str(len(survivors)))
    print("   inconclusive      " + str(len(inconclusive)))
    if missing_kinds:
        print("   MISSING KINDS     " + ", ".join(missing_kinds) + "   <- gap, must be covered")
    if requires_manual:
        print("   MANUAL KINDS      " + ", ".join(requires_manual) +
              "   <- construct from contract, or document as N/A")
    for r in fair_violations[:5]:
        print("   FAIR VIOLATION    " + r["name"] + " -> rejected by " + ", ".join(r.get("failed_checks", [])[:3]))
    for r in survivors[:5]:
        print("   SURVIVED          " + r["kind"] + "/" + r["name"])
    print("   report            " + str(out / "proof.json"))
    return 0 if status in ("PROOF_PASSED", "GENERATED_ONLY") else 1


if __name__ == "__main__":
    raise SystemExit(main())
