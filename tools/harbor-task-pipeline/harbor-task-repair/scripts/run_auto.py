#!/usr/bin/env python3
"""Headless launcher for harbor-task-repair. No prompts, no TTY, no user input.

Unlike run_interactive.py this is designed to be piped, cron'd, or run in CI. It drives the
`harbor-auto` agent, which has the question tool denied and every permission pre-granted, so a
run either completes or fails - it can never sit waiting for a human.

    python run_auto.py tasks/my-task
    python run_auto.py tasks/*/ --model wandb-glm/glm-5.2 --jobs 1
    python run_auto.py tasks/my-task --dry-run

Exit codes (per task, and the worst across a batch):
    0  repaired cleanly, no decisions auto-resolved
    1  repaired WITH escalations - a human should review .harbor-repair/escalations.json
    2  precondition failure (bad path, skill not installed, opencode missing)
    3  the opencode run itself failed or timed out

Standard library only.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

SKILL_DIRNAME = "harbor-task-repair"
REQUIRED_AGENTS = ("harbor-auto.md", "harbor-fixer-auto.md")


def parser():
    p = argparse.ArgumentParser(
        description="Run harbor-task-repair fully autonomously. No prompts of any kind.")
    p.add_argument("tasks", nargs="+", help="One or more task folders inside the project root")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--fix", action="store_true",
                      help="Apply repairs (default)")
    mode.add_argument("--dry-run", action="store_true",
                      help="Diagnose only, change nothing")
    p.add_argument("--model", help="opencode model as provider/model")
    p.add_argument("--agent", default="harbor-auto",
                   help="primary agent to drive the run (default: harbor-auto)")
    p.add_argument("--only", help="Run only these comma-separated step numbers")
    p.add_argument("--from-step", metavar="NN", help="Start from this step number")
    p.add_argument("--timeout", type=int, default=7200,
                   help="Per-task timeout in seconds (default 7200 = 2h)")
    p.add_argument("--log-dir", default=None,
                   help="Where to write per-task logs (default: alongside .harbor-repair)")
    p.add_argument("--no-probe", action="store_true",
                   help="Skip the deterministic pre-flight probe")
    p.add_argument("--continue-on-error", action="store_true",
                   help="Keep going through a batch after a task fails")
    p.add_argument("--task-jobs", "--jobs", dest="jobs", type=int, default=1,
                   help="Tasks to repair concurrently (default 1). For a large batch this is "
                        "the knob that matters: task-level concurrency costs 35%% less total "
                        "compute than the in-task parallel path, so it finishes a batch sooner "
                        "at any slot count.")
    return p


def err(msg):
    print("ERROR: %s" % msg, file=sys.stderr, flush=True)


def find_project(script):
    # .../<project>/.opencode/skill/harbor-task-repair/scripts/run_auto.py
    return Path(script).resolve().parents[4]


def opencode_cmd():
    """Resolve the opencode launcher to something subprocess can actually execute.

    On Windows `opencode` is a .CMD shim; CreateProcess cannot run one directly, so it has to
    go through cmd.exe. shutil.which() finds it, but the bare string "opencode" does not work.
    """
    exe = shutil.which("opencode")
    if not exe:
        return None
    if os.name == "nt" and os.path.splitext(exe)[1].lower() in (".cmd", ".bat"):
        comspec = os.environ.get("COMSPEC") or "cmd.exe"
        return [comspec, "/c", exe]
    return [exe]


def preflight(project, skill_dir):
    if not (skill_dir / "SKILL.md").is_file():
        err("skill not installed at %s" % skill_dir)
        return False
    agent_dir = project / ".opencode" / "agent"
    for a in REQUIRED_AGENTS:
        if not (agent_dir / a).is_file():
            err("missing %s - autonomous mode needs the whole .opencode/agent/ folder" % a)
            return False
    if not opencode_cmd():
        err("opencode is not on PATH")
        return False
    return True


def resolve_task(project, raw):
    p = Path(raw)
    task = p.resolve() if p.is_absolute() else (project / p).resolve()
    try:
        rel = task.relative_to(project)
    except ValueError:
        return None, None, "task must be inside the project root (%s)" % project
    if not task.is_dir():
        return None, None, "not a directory: %s" % task
    if not (task / "tests").is_dir():
        return None, None, "no tests/ under %s - not a task package" % task
    return task, rel, None


def run_probe(skill_dir, task, harbor_dir):
    probe = skill_dir / "scripts" / "probe.py"
    if not probe.is_file():
        return None
    harbor_dir.mkdir(parents=True, exist_ok=True)
    out = harbor_dir / "probe.json"
    try:
        r = subprocess.run([sys.executable, str(probe), str(task), "--json"],
                           capture_output=True, text=True, timeout=120)
    except (subprocess.TimeoutExpired, OSError) as e:
        err("probe failed to run: %s" % e)
        return None
    if r.returncode != 0:
        err("probe exited %d: %s" % (r.returncode, (r.stderr or "").strip()[:200]))
        return None
    out.write_text(r.stdout, encoding="utf8")
    try:
        return json.loads(r.stdout)
    except ValueError:
        return None


def build_prompt(rel_task, mode_text, probe_data, args, harbor_rel):
    req = (
        "Use the harbor-task-repair skill on %(task)s with %(mode)s. "
        "Run FULLY AUTONOMOUSLY: you have no question tool and no user is watching. "
        "Never ask for confirmation and never wait for input. "
        "Resolve every scope decision using reference/autonomous-policy.md and append it to "
        "%(harbor)s/escalations.json. Use %(harbor)s as the working directory for "
        "progress.json and every other artefact. DECIDE, then prove it: you may disclose a "
        "hidden requirement additively in instruction.md or drop a provably redundant check, "
        "but every such change must be verified by re-running the golden in the package's own "
        "container (reward must still be 1) - revert it if not. Never invent a business rule. "
        "Mark each escalation class:'decision' (a human must look) or class:'routing' "
        "(infrastructure/runtime context, no action needed). "
        "Spawn harbor-fixer-auto (not harbor-fixer) for each step. "
        "Print a one-line status before and after every indexed step."
    ) % {"task": rel_task.as_posix(), "mode": mode_text, "harbor": harbor_rel}
    if probe_data:
        skip = probe_data.get("skip") or []
        if skip and not probe_data.get("spec", {}).get("opaque"):
            req += (" The deterministic pre-flight in .harbor-repair/probe.json marks steps %s "
                    "as having zero candidates: record them not_applicable WITHOUT spawning a "
                    "subagent, and read each step's candidates[] as its starting target list."
                    % ", ".join(skip))
        else:
            req += (" Read .harbor-repair/probe.json for each step's candidate list before "
                    "spawning it.")
    if args.only:
        req += " Run only steps %s." % args.only
    if args.from_step:
        req += " Start from step %s." % args.from_step
    return req


# A scope decision that autonomous mode resolved on its own, or anything that reduced
# coverage, needs a human. An infrastructure routing note does not - OWN1 fires on every
# binary-reward package, and letting it drive the exit code would mark every run for review
# and make the code useless for pipeline routing.
DECISION_KEYS = ("requirement_now_ungraded", "proposed_but_not_applied", "what",
                 "action_taken", "policy")


def _records(d):
    if isinstance(d, list):
        return [r for r in d if isinstance(r, dict)]
    if isinstance(d, dict):
        for k in ("escalations", "records", "items"):
            if isinstance(d.get(k), list):
                return [r for r in d[k] if isinstance(r, dict)]
        return [d]
    return []


# Infrastructure/runtime notes that no trainer can act on. Measured on the first 680-task
# batch: 185 of 471 escalations (39%) were these, and they were why nearly every task exited 1.
import re as _re
_ROUTING = _re.compile(
    r"infrastructure|runtime[- ]owned|binary 1/0|tier weight|partial credit|"
    r"own1|l8|a9|stale[- ]evidence|never failed|routed? out|"
    r"no verifier changed verdict|weighted \(non-binary\)|scoring weights",
    _re.I)


def _actionable(rec):
    """True if this record needs a human before the task ships."""
    cls = str(rec.get("class") or rec.get("kind") or "").lower()
    if cls in ("routing", "informational", "info"):
        return False
    if cls in ("decision", "escalation"):
        return True
    # No explicit class: infer. A routing note is context, not a request.
    blob = " ".join(str(rec.get(k) or "") for k in
                    ("what", "finding", "policy", "action_taken", "note", "reason"))
    if _ROUTING.search(blob) and not rec.get("requirement_now_ungraded"):
        return False
    if rec.get("requirement_now_ungraded"):
        return True
    if rec.get("blocks"):
        return True
    # An infrastructure-owned note that blocks nothing is routing, not a decision.
    if str(rec.get("owner") or "").lower() in ("infrastructure", "infra", "runtime"):
        return False
    return any(rec.get(k) for k in DECISION_KEYS)


def read_escalations(harbor_dir):
    """Return (actionable, informational)."""
    f = harbor_dir / "escalations.json"
    if not f.is_file():
        return 0, 0
    try:
        d = json.loads(f.read_text(encoding="utf8"))
    except ValueError:
        return 0, 0
    recs = _records(d)
    act = sum(1 for r in recs if _actionable(r))
    return act, len(recs) - act


def one_task(project, skill_dir, raw, args):
    task, rel, problem = resolve_task(project, raw)
    if problem:
        err(problem)
        return 2

    # Per-task, so a batch sharing one parent folder cannot clobber itself. Still
    # BESIDE the task, never inside it - .harbor-repair must not ship in a package.
    harbor_dir = task.parent / ".harbor-repair" / task.name
    log_dir = Path(args.log_dir).resolve() if args.log_dir else harbor_dir
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / ("run-auto-%s.log" % task.name)

    probe_data = None if args.no_probe else run_probe(skill_dir, task, harbor_dir)
    if probe_data:
        saved = probe_data.get("spawns_saved", 0)
        print("  probe: %d verifier(s), %d/13 step(s) skippable%s"
              % (probe_data.get("spec", {}).get("n_verifiers", 0), saved,
                 "  [spec OPAQUE - no skips]" if probe_data.get("spec", {}).get("opaque") else ""),
              flush=True)

    mode_text = "--dry-run" if args.dry_run else "--fix"
    cmd = opencode_cmd() + ["run", "--auto", "--agent", args.agent, "--dir", str(project)]
    if args.model:
        cmd += ["--model", args.model]
    cmd += [build_prompt(rel, mode_text, probe_data, args,
                         harbor_dir.relative_to(project).as_posix())]

    print("  launching: opencode run --auto --agent %s  (%s, timeout %ds)"
          % (args.agent, mode_text, args.timeout), flush=True)
    started = time.time()
    env = dict(os.environ)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    # Nothing may read stdin: an unattended run that blocks on input is the failure we are
    # designing out. Give it a closed stdin so any attempt fails fast instead of hanging.
    try:
        with open(log_path, "wb") as log:
            proc = subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=log,
                                  stderr=subprocess.STDOUT, timeout=args.timeout,
                                  env=env, cwd=str(project))
        rc = proc.returncode
    except subprocess.TimeoutExpired:
        err("timed out after %ds - log: %s" % (args.timeout, log_path))
        return 3
    except OSError as e:
        err("could not launch opencode: %s" % e)
        return 3

    elapsed = int(time.time() - started)
    if rc != 0:
        err("opencode exited %d after %ds - log: %s" % (rc, elapsed, log_path))
        return 3

    act, info = read_escalations(harbor_dir)
    tail = " (%d informational)" % info if info else ""
    if act:
        print("  DONE in %ds WITH %d escalation(s) needing review%s -> %s"
              % (elapsed, act, tail, harbor_dir / "escalations.json"), flush=True)
        return 1
    print("  DONE in %ds, nothing needs review%s. Log: %s"
          % (elapsed, tail, log_path), flush=True)
    return 0


def main():
    args = parser().parse_args()
    project = find_project(__file__)
    skill_dir = project / ".opencode" / "skill" / SKILL_DIRNAME
    if not preflight(project, skill_dir):
        return 2

    worst = 0
    results = []
    total = len(args.tasks)
    jobs = max(1, args.jobs)

    if jobs == 1 or total == 1:
        for i, raw in enumerate(args.tasks, 1):
            print("[%d/%d] %s" % (i, total, raw), flush=True)
            rc = one_task(project, skill_dir, raw, args)
            results.append((raw, rc))
            worst = max(worst, rc)
            if rc >= 2 and not args.continue_on_error:
                err("stopping batch (use --continue-on-error to keep going)")
                break
    else:
        import concurrent.futures as _f
        print("batch: %d task(s), %d at a time" % (total, jobs), flush=True)
        done = [0]
        with _f.ThreadPoolExecutor(max_workers=jobs) as ex:
            futs = {ex.submit(one_task, project, skill_dir, raw, args): raw
                    for raw in args.tasks}
            for fut in _f.as_completed(futs):
                raw = futs[fut]
                try:
                    rc = fut.result()
                except Exception as e:  # a crashed task must not sink the batch
                    err("%s raised %s" % (raw, e))
                    rc = 3
                done[0] += 1
                results.append((raw, rc))
                worst = max(worst, rc)
                print("[%d/%d] rc=%d  %s" % (done[0], total, rc, raw), flush=True)

    if len(results) > 1:
        label = {0: "clean", 1: "escalations", 2: "precondition", 3: "failed"}
        print("\n=== batch summary ===", flush=True)
        for raw, rc in results:
            print("  %-9s %s" % (label.get(rc, rc), raw), flush=True)
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
