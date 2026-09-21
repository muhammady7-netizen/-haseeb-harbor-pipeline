#!/usr/bin/env python3
"""Harbor task pipeline - repair a task, then prove the package is shippable.

One command, three stages:

    1. REPAIR    harbor-task-repair fixes the verifier defects (needs opencode)
    2. PACKAGE   the task tree becomes a delivery .zip
    3. GATE      repackaging-qc-gate finds packaging defects, stage2_fix remediates
                 them, and the gate runs AGAIN to prove the fixes landed

Usage:

    python run.py path/to/task                 one task, everything
    python run.py tasks/*                      many tasks
    python run.py task --check-only            skip repair; gate an existing package
    python run.py task --repair-only           stop after repair
    python run.py --doctor                     check the environment and exit

Results land in ./harbor-pipeline-out/ - the shippable .zip files, a JSON report,
and a summary printed at the end. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
# run_auto.py derives the opencode project root as parents[4] of its own path, i.e. it must
# live at <project>/.opencode/skill/harbor-task-repair/scripts/run_auto.py. Pointed at the
# bundle copy instead, that arithmetic lands four levels above the bundle - on this machine
# C:\development - and it aborts with "skill not installed". So always use the INSTALLED copy.
def repair_script(cwd: Path):
    p = cwd / ".opencode" / "skill" / "harbor-task-repair" / "scripts" / "run_auto.py"
    return p if p.is_file() else None
GATE = HERE / "repackaging-qc-gate" / "qc_gates.py"
FIX = HERE / "stage2_fix.py"

# Artefacts that are never task content. Deliberately conservative: a suffix is not
# evidence of junk, and several tasks ship a real .bak as fixture data (a superseded
# plan the audit must catch). Only ever exclude what we are certain we created.
EXCLUDE_DIRS = {".harbor-repair", "__pycache__", ".git", ".pytest_cache", "__MACOSX"}
EXCLUDE_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}
EXCLUDE_SUFFIX = (".pyc", ".swp", ".swo", ".orig", ".rej", ":Zone.Identifier")

C = {"g": "\033[32m", "r": "\033[31m", "y": "\033[33m", "b": "\033[1m", "d": "\033[2m", "x": "\033[0m"}
if os.name == "nt" and not os.environ.get("ANSICON"):
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleMode(ctypes.windll.kernel32.GetStdHandle(-11), 7)
    except Exception:
        C = {k: "" for k in C}


def say(msg="", color=None):
    print((C.get(color, "") + msg + C["x"]) if color else msg, flush=True)


def rule(title):
    say()
    say("=" * 68, "d")
    say("  " + title, "b")
    say("=" * 68, "d")


# --------------------------------------------------------------------------- doctor
def which(*names):
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    return None


def doctor(verbose=True):
    """Check everything the pipeline needs. Returns (ok_for_repair, ok_for_gate)."""
    rows = []

    py_ok = sys.version_info >= (3, 10)
    rows.append(("Python >= 3.10", py_ok,
                 "%d.%d.%d" % sys.version_info[:3], True))

    oc = which("opencode", "opencode.cmd")
    rows.append(("opencode on PATH", bool(oc), oc or "not found - repair unavailable", False))

    for label, path in (("repackaging-qc-gate", GATE), ("stage2_fix", FIX)):
        rows.append((label, path.exists(), str(path.relative_to(HERE)) if path.exists()
                     else "MISSING", True))
    rs = repair_script(Path.cwd())
    rows.append(("harbor-task-repair installed", bool(rs),
                 str(rs.parent.parent.relative_to(Path.cwd())) if rs else
                 "not in ./.opencode/skill - run install.py (repair unavailable)", False))

    try:
        import tomllib  # noqa: F401
        toml_ok, toml_note = True, "tomllib"
    except ImportError:
        try:
            import tomli  # noqa: F401
            toml_ok, toml_note = True, "tomli"
        except ImportError:
            toml_ok, toml_note = False, "none - gates G01/G04/G05 degrade (needs py3.11+)"
    rows.append(("TOML reader", toml_ok, toml_note, False))

    # Only the docker CLI is needed - `docker manifest inspect` reaches the registry with the
    # engine stopped. Without it, image tags that are not in the curated map stay unpinned.
    dk = which("docker")
    rows.append(("docker CLI (optional)", bool(dk),
                 "digest pinning available" if dk else
                 "not found - unknown image tags stay unpinned (G01)", False))

    # The verifier engine's deps. Without them the repair's proof step cannot execute the
    # task's own verifier, and every run ends "repaired-unproven" WITHOUT SAYING SO LOUDLY.
    # That silence is the whole reason this check exists.
    missing = []
    for mod in ("pytest", "pydantic", "jsonpath_ng", "openpyxl", "docx", "pptx", "pypdf",
                "tenacity", "litellm"):
        try:
            __import__(mod)
        except Exception:
            missing.append({"docx": "python-docx", "pptx": "python-pptx",
                            "jsonpath_ng": "jsonpath-ng"}.get(mod, mod))
    rows.append(("verifier engine deps", not missing,
                 "all present" if not missing else "missing: " + " ".join(missing), False))

    if verbose:
        rule("environment")
        for label, ok, note, _ in rows:
            mark = C["g"] + "  ok  " + C["x"] if ok else C["y"] + " warn " + C["x"]
            say("  [%s] %-24s %s" % (mark, label, note))
        if missing:
            say()
            say("  Install the verifier engine deps so the repair can PROVE its fix:", "y")
            say("    pip install " + " ".join(missing), "y")
            say("  Without them the repair still runs, but its proof step cannot execute the", "d")
            say("  task's verifier and the result is unproven rather than certified.", "d")
        if not oc:
            say()
            say("  opencode not found - repair is unavailable. You can still run:", "y")
            say("    python run.py <task> --check-only", "y")

    hard_ok = all(ok for _, ok, _, hard in rows if hard)
    return bool(oc) and hard_ok, hard_ok


# --------------------------------------------------------------------------- package
def is_excluded(p: Path, root: Path) -> bool:
    rel = p.relative_to(root)
    if any(part in EXCLUDE_DIRS for part in rel.parts):
        return True
    if p.name in EXCLUDE_NAMES or p.name.startswith("._"):
        return True
    return any(p.name.endswith(s) for s in EXCLUDE_SUFFIX)


def package(task: Path, out_dir: Path) -> Path:
    """Zip a task tree whole. Everything ships except what we are sure we created."""
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / (task.name + ".zip")
    n = 0
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(task.rglob("*")):
            if p.is_dir() or p.is_symlink() or is_excluded(p, task):
                continue
            z.write(p, os.path.join(task.name, p.relative_to(task).as_posix()))
            n += 1
    say("    packaged %s (%d files, %.1f MB)" % (dest.name, n, dest.stat().st_size / 1e6))
    return dest


# --------------------------------------------------------------------------- gate
def run_gate(target: Path, tag: str, work: Path):
    """Run the gate over a directory of .zip packages. Returns its report dict."""
    js = work / ("gate-%s.json" % tag)
    cmd = [sys.executable, str(GATE), str(target), "--json", str(js), "--warn-only"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if not js.exists():
        say("    gate produced no report (rc=%d)" % r.returncode, "r")
        if r.stderr.strip():
            say("    " + r.stderr.strip().splitlines()[-1], "d")
        return None
    return json.loads(js.read_text(encoding="utf-8"))


def gate_counts(rep):
    if not rep:
        return {}, 0
    f = rep.get("findings", [])
    per = {}
    for x in f:
        g = x.get("gate", "?")
        per[g] = per.get(g, 0) + 1
    blocking = sum(1 for x in f if x.get("severity") == "BLOCK")
    return per, blocking


def show_gate(rep, title):
    per, blocking = gate_counts(rep)
    if rep is None:
        return
    s = rep.get("summary", {})
    say("    %s: %d findings (%d blocking) across %d packages"
        % (title, s.get("total_findings", 0), blocking, rep.get("packages", 0)))
    if per:
        names = {x["gate"]: x.get("gate_name", "") for x in rep.get("findings", [])}
        for g in sorted(per):
            say("      %-5s %-4d %s" % (g, per[g], names.get(g, "")[:44]), "d")


# --------------------------------------------------------------------------- stages
def stage_repair(tasks, args, work):
    rule("stage 1 - repair")
    cmd = [sys.executable, str(repair_script(Path.cwd()))] + [str(t) for t in tasks]
    cmd += ["--fix"] if not args.dry_run else ["--dry-run"]
    if args.model:
        cmd += ["--model", args.model]
    if args.jobs > 1:
        cmd += ["--task-jobs", str(args.jobs)]
    if args.only:
        cmd += ["--only", args.only]
    cmd += ["--timeout", str(args.timeout), "--continue-on-error"]
    say("  " + " ".join(cmd[1:3]) + " ... (%d task(s), timeout %ds)" % (len(tasks), args.timeout))
    say("  this is the slow part - the agent reads, edits and re-runs the verifier", "d")
    t0 = time.time()
    rc = subprocess.run(cmd, cwd=str(Path.cwd())).returncode
    say("  repair finished rc=%d in %s" % (rc, human(time.time() - t0)),
        "g" if rc in (0, 1) else "y")
    if rc == 1:
        say("  rc=1 means at least one task raised something needing a human look.", "y")
    return rc


def stage_gate(pkg_dir, work, out_dir):
    rule("stage 2 - packaging gate")
    say("  first pass: what is wrong")
    before = run_gate(pkg_dir, "before", work)
    show_gate(before, "before")

    say()
    say("  remediating (digest pins, internal addresses, authoring paths, READMEs, artefacts)")
    r = subprocess.run([sys.executable, str(FIX), str(pkg_dir), str(out_dir),
                        "--work", str(work / "s2work"),
                        "--report", str(work / "stage2-changes.json")],
                       capture_output=True, text=True)
    for line in (r.stdout or "").strip().splitlines():
        if line.strip():
            say("    " + line)
    if r.returncode != 0:
        say("    remediation failed rc=%d" % r.returncode, "r")
        say("    " + (r.stderr or "").strip()[-400:], "d")
        return before, None

    say()
    say("  second pass: proving the fixes landed")
    after = run_gate(out_dir, "after", work)
    show_gate(after, "after")
    return before, after


def human(sec):
    m, s = divmod(int(sec), 60)
    h, m = divmod(m, 60)
    return ("%dh%02dm" % (h, m)) if h else ("%dm%02ds" % (m, s)) if m else ("%ds" % s)


def valid_task(p: Path):
    if not p.is_dir():
        return "not a directory"
    if not (p / "instruction.md").is_file():
        return "no instruction.md"
    if not (p / "tests").is_dir():
        return "no tests/ directory"
    return None


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tasks", nargs="*", type=Path, help="task folder(s)")
    ap.add_argument("--out", type=Path, default=Path("harbor-pipeline-out"),
                    help="where results go (default: ./harbor-pipeline-out)")
    ap.add_argument("--check-only", action="store_true",
                    help="skip repair; package and gate what is already there")
    ap.add_argument("--repair-only", action="store_true", help="stop after repair")
    ap.add_argument("--dry-run", action="store_true", help="repair diagnoses, applies nothing")
    ap.add_argument("--model", help="opencode model, e.g. wandb-glm/zai-org/GLM-5.2")
    ap.add_argument("--jobs", type=int, default=1, help="tasks repaired in parallel (default 1)")
    ap.add_argument("--timeout", type=int, default=7200, help="per-task repair timeout seconds")
    ap.add_argument("--only", metavar="NN[,NN]",
                    help="run only these repair steps (e.g. 01,02). A quick smoke pass; "
                         "a subset is NOT a repair - the result is not shippable.")
    ap.add_argument("--doctor", action="store_true", help="check the environment and exit")
    args = ap.parse_args()

    if args.doctor:
        doctor()
        return 0
    if not args.tasks:
        ap.error("give me at least one task folder (or --doctor)")

    tasks, bad = [], []
    for t in args.tasks:
        why = valid_task(t)
        (bad if why else tasks).append((t, why) if why else t.resolve())
    if bad:
        rule("skipped")
        for t, why in bad:
            say("  %-50s %s" % (str(t)[:50], why), "y")
    if not tasks:
        say("nothing to do - no valid task folders given", "r")
        return 2

    can_repair, can_gate = doctor(verbose=True)
    if not can_gate:
        say("\nthe bundle is incomplete - re-copy harbor-task-pipeline/", "r")
        return 2
    do_repair = not args.check_only
    # opencode refuses to read outside the directory it was started in, so a task that sits
    # elsewhere fails on every subagent's first read - with an error that looks like a task
    # problem rather than a path problem. Catch it here, where we can say what to do.
    if do_repair:
        cwd = Path.cwd().resolve()
        outside = [t for t in tasks if not t.is_relative_to(cwd)]
        if outside:
            say()
            say("  These tasks are outside the current directory:", "r")
            for t in outside[:5]:
                say("    %s" % t, "r")
            say()
            say("  opencode only reads inside the directory it starts in, so repair would", "y")
            say("  fail on the first read. Either cd to the folder that contains them:", "y")
            say("    cd %s && python %s <task>" % (outside[0].parent, HERE / "run.py"), "y")
            say("  or copy them here first. (--check-only has no such limit.)", "y")
            return 2
    if do_repair and repair_script(Path.cwd()) is None:
        say()
        say("  harbor-task-repair is not installed in ./.opencode/skill/", "r")
        say("  Install it (one command), then re-run:", "y")
        say("    python %s" % (HERE / "install.py"), "y")
        say("  Or skip repair entirely with --check-only.", "y")
        return 2
    if do_repair and not can_repair:
        say("\nopencode is missing, so repair cannot run.", "r")
        say("Re-run with --check-only to package and gate these tasks as they are.", "y")
        return 2

    out_dir = args.out.resolve()
    work = out_dir / ".work"
    # The gate rglobs *.zip under its target, so the pre-remediation copies must not live
    # anywhere beneath out_dir - otherwise the second pass grades the unfixed packages too
    # and every fix looks like it failed to land.
    pkg_dir = Path(tempfile.mkdtemp(prefix="harbor-pipeline-staging-"))
    for d in (out_dir, work):
        d.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    result = {"started_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "tasks": [str(t) for t in tasks]}

    if do_repair:
        rc = stage_repair(tasks, args, work)
        result["repair_rc"] = rc
        # 0 = repaired, 1 = repaired with something for a human. Anything else means the repair
        # did not happen, and continuing would package the UNREPAIRED task and report it clean -
        # which is worse than failing, because it looks like success.
        if rc not in (0, 1):
            say()
            say("  Repair did not run (rc=%d) - stopping." % rc, "r")
            say("  Packaging now would ship the unrepaired task and call it clean.", "r")
            if rc == 2:
                say("  rc=2 is a precondition failure. Most often the skill is not installed:",
                    "y")
                say("    python %s" % (HERE / "install.py"), "y")
            shutil.rmtree(pkg_dir, ignore_errors=True)
            return 2
        if args.repair_only:
            say("\nstopped after repair (--repair-only)", "b")
            return 0

    rule("packaging")
    for t in tasks:
        package(t, pkg_dir)

    before, after = stage_gate(pkg_dir, work, out_dir)
    result["gate_before"] = (before or {}).get("summary")
    result["gate_after"] = (after or {}).get("summary")

    # ------------------------------------------------------------------ verdict
    rule("result")
    _, blk_before = gate_counts(before)
    per_after, blk_after = gate_counts(after)
    zips = sorted(out_dir.glob("*.zip"))
    say("  packages : %d" % len(zips))
    say("  blocking : %d -> %d" % (blk_before, blk_after),
        "g" if blk_after < blk_before else "y")

    # These classes are not ours to close, and saying so is the point: a number that
    # cannot go to zero here should never look like a failure the trainer must chase.
    residual = {
        "G06": "documentation vs evidence - the finalization pipeline regenerates both",
        "G10": "incomplete difficulty battery - needs re-running the task, not repackaging",
        "G11": "difficulty band - recompute after the battery is complete",
        "G12": "manifest - recomputed at delivery",
    }
    left = {g: n for g, n in per_after.items() if g not in residual}
    if not left:
        say("\n  Everything this pipeline can fix is fixed.", "g")
    else:
        say("\n  Still open (needs a look):", "y")
        for g in sorted(left):
            say("    %-5s %d" % (g, left[g]), "y")
    noted = {g: n for g, n in per_after.items() if g in residual}
    if noted:
        say("\n  Expected residual - not a defect in your repair:", "d")
        for g in sorted(noted):
            say("    %-5s %-4d %s" % (g, noted[g], residual[g]), "d")

    shutil.rmtree(pkg_dir, ignore_errors=True)
    result["elapsed_seconds"] = round(time.time() - t0, 1)
    (out_dir / "pipeline-report.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8")
    say()
    say("  shippable packages : %s" % out_dir, "b")
    say("  what changed       : %s" % (work / "stage2-changes.json"))
    say("  gate detail        : %s" % (work / "gate-after.json"))
    say("  total time         : %s" % human(time.time() - t0))
    return 0 if not left else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        say("\ninterrupted", "y")
        sys.exit(130)
