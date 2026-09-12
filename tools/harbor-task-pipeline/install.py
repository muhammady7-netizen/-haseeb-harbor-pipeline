#!/usr/bin/env python3
"""Install the pipeline into the repo where you work on tasks.

    python install.py                 install into the current directory
    python install.py path/to/repo    install somewhere else
    python install.py --global        install for every project (~/.config/opencode)
    python install.py --check         report what is installed, change nothing

After this you can either run the pipeline directly:

    python run.py <task>

or start opencode in that repo and just ask:

    "fix and package the task in ./my-task"

Both do the same work. The command is scriptable; the agent route is conversational.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC_SKILL_REPAIR = HERE / "harbor-task-repair"
SRC_AGENTS = HERE / "opencode" / "agent"
SRC_CONFIG = HERE / "opencode" / "opencode.json"

# run_auto.py refuses to start without these two.
REQUIRED_AGENTS = ("harbor-auto.md", "harbor-fixer-auto.md")

C = {"g": "\033[32m", "r": "\033[31m", "y": "\033[33m", "b": "\033[1m", "d": "\033[2m", "x": "\033[0m"}


def say(m="", c=None):
    print((C.get(c, "") + m + C["x"]) if c else m, flush=True)


def pipeline_skill_files():
    """The orchestrator skill: SKILL.md plus everything it drives, minus the vendored repair
    skill (installed separately so opencode sees it as a skill in its own right)."""
    keep = ["SKILL.md", "README.md", "run.py", "stage2_fix.py", "install.py"]
    return [(HERE / n, n) for n in keep if (HERE / n).exists()]


def install(oc: Path, check_only=False):
    skills, agents = oc / "skill", oc / "agent"
    report, problems = [], []

    def state(label, path, present_note="installed", missing_note="not installed"):
        ok = path.exists()
        report.append((label, ok, present_note if ok else missing_note))
        return ok

    if check_only:
        state("harbor-task-repair skill", skills / "harbor-task-repair")
        state("harbor-task-pipeline skill", skills / "harbor-task-pipeline")
        for a in REQUIRED_AGENTS:
            state("agent " + a, agents / a)
        state("opencode.json", oc / "opencode.json")
        say()
        for label, ok, note in report:
            mark = C["g"] + " ok " + C["x"] if ok else C["y"] + "  - " + C["x"]
            say("  [%s] %-32s %s" % (mark, label, note))
        return 0 if all(ok for _, ok, _ in report) else 1

    skills.mkdir(parents=True, exist_ok=True)
    agents.mkdir(parents=True, exist_ok=True)

    # 1. the repair skill, whole
    dest = skills / "harbor-task-repair"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(SRC_SKILL_REPAIR, dest,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    say("  installed skill  harbor-task-repair", "g")

    # 2. the orchestrator skill - SKILL.md plus the scripts it runs
    dest = skills / "harbor-task-pipeline"
    dest.mkdir(parents=True, exist_ok=True)
    for src, name in pipeline_skill_files():
        shutil.copy2(src, dest / name)
    gate_dest = dest / "repackaging-qc-gate"
    if gate_dest.exists():
        shutil.rmtree(gate_dest)
    shutil.copytree(HERE / "repackaging-qc-gate", gate_dest,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    # run.py resolves its tools relative to itself, so the repair skill has to be reachable
    # from the installed copy too. A copy, not a symlink: Windows needs a privilege for those.
    repair_dest = dest / "harbor-task-repair"
    if repair_dest.exists():
        shutil.rmtree(repair_dest)
    shutil.copytree(SRC_SKILL_REPAIR, repair_dest,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    say("  installed skill  harbor-task-pipeline", "g")

    # 3. agents
    n = 0
    for f in sorted(SRC_AGENTS.glob("*.md")):
        shutil.copy2(f, agents / f.name)
        n += 1
    say("  installed %d agents (incl. %s)" % (n, ", ".join(REQUIRED_AGENTS)), "g")

    # 4. permissions - never clobber an existing config silently
    target = oc / "opencode.json"
    if not target.exists():
        shutil.copy2(SRC_CONFIG, target)
        say("  installed opencode.json (permissions)", "g")
    else:
        try:
            cur = json.loads(target.read_text(encoding="utf-8"))
            new = json.loads(SRC_CONFIG.read_text(encoding="utf-8"))
        except Exception as e:
            problems.append("could not read opencode.json (%s) - merge the permission block "
                            "from opencode/opencode.json by hand" % e)
            cur = new = None
        if cur is not None:
            if "permission" in cur:
                problems.append(
                    "%s already has a `permission` block - left untouched. Without the "
                    "pipeline's permissions the repair will stop on approval prompts. Merge "
                    "the block from %s if that happens."
                    % (target, SRC_CONFIG.relative_to(HERE)))
            else:
                cur["permission"] = new.get("permission", {})
                target.write_text(json.dumps(cur, indent=2) + "\n", encoding="utf-8")
                say("  merged permissions into your existing opencode.json", "g")

    say()
    say("  installed into %s" % oc, "b")
    say()
    say("  Now either:", "b")
    say("    python %s <task>" % (HERE / "run.py"))
    say("    ...or start opencode here and say: \"fix and package the task in ./my-task\"")
    if problems:
        say()
        for p in problems:
            say("  ! " + p, "y")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", nargs="?", type=Path, default=Path.cwd())
    ap.add_argument("--global", dest="glob", action="store_true",
                    help="install for every project instead of one repo")
    ap.add_argument("--check", action="store_true", help="report what is installed")
    a = ap.parse_args()

    # Globally, ~/.config/opencode IS the .opencode equivalent - it does not get a nested
    # .opencode inside it, which is why this passes the directory rather than its parent.
    oc = (Path.home() / ".config" / "opencode") if a.glob else (a.target.resolve() / ".opencode")

    for src, label in ((SRC_SKILL_REPAIR, "harbor-task-repair/"),
                       (SRC_AGENTS, "opencode/agent/"),
                       (SRC_CONFIG, "opencode/opencode.json")):
        if not src.exists():
            say("bundle is incomplete: %s is missing" % label, "r")
            return 2
    return install(oc, check_only=a.check)


if __name__ == "__main__":
    sys.exit(main())
