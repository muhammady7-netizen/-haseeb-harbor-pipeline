#!/usr/bin/env python3
"""Launch harbor-task-repair in an interactive OpenCode terminal UI."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import sys


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description=(
            "Run harbor-task-repair with visible permission and decision prompts. "
            "Dry-run is the default."
        )
    )
    result.add_argument("task", help="Task folder inside this OpenCode project")
    mode = result.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Diagnose only (default)")
    mode.add_argument("--fix", action="store_true", help="Allow recipe-authorized repairs")
    result.add_argument("--model", help="OpenCode model as provider/model")
    result.add_argument("--agent", default="harbor-repair",
                        help="primary agent to drive the run (default: harbor-repair)")
    result.add_argument("--only", help="Run only comma-separated step numbers")
    result.add_argument("--from-step", metavar="NN", help="Start from this step number")
    return result


def fail(message: str) -> int:
    print(f"INTERACTIVE_RERUN_REQUIRED: {message}", file=sys.stderr)
    return 2


def main() -> int:
    args = parser().parse_args()
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return fail(
            "run this launcher in a visible terminal; do not pipe it or use `opencode run`."
        )

    script = Path(__file__).resolve()
    project = script.parents[4]
    skill = project / ".opencode" / "skill" / "harbor-task-repair" / "SKILL.md"
    if not skill.is_file():
        return fail(f"skill is not installed under {project / '.opencode'}." )
    agent_file = project / ".opencode" / "agent" / "harbor-repair.md"
    worker_file = project / ".opencode" / "agent" / "harbor-fixer.md"
    for required in (agent_file, worker_file):
        if not required.is_file():
            return fail(f"missing {required.name}; copy the whole .opencode/agent/ folder.")

    task = (project / args.task).resolve() if not Path(args.task).is_absolute() else Path(args.task).resolve()
    try:
        relative_task = task.relative_to(project)
    except ValueError:
        return fail("the task must be inside the OpenCode project root.")
    if not (task / "instruction.md").is_file() or not (task / "tests").is_dir():
        return fail("the task must contain instruction.md and tests/.")

    executable = shutil.which("opencode")
    if not executable:
        return fail("opencode is not available on PATH.")

    mode_text = "--fix" if args.fix else "--dry-run"
    request = (
        f"Use the harbor-task-repair skill on {relative_task} with {mode_text}. "
        "Show a short status line before and after every indexed step. "
        "Ask all permission or scope questions in this interactive UI; never wait silently."
    )
    if args.only:
        request += f" Run only steps {args.only}."
    if args.from_step:
        request += f" Start from step {args.from_step}."

    command = [executable, str(project)]
    if args.agent:
        command.extend(["--agent", args.agent])
    if args.model:
        command.extend(["--model", args.model])
    command.extend(["--prompt", request])

    print(f"Launching interactive repair for {relative_task} ({mode_text})", flush=True)
    os.execv(executable, command)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
