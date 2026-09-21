from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow `python -m pipeline.resume` from repo root
if __name__ == "__main__" and (__package__ is None or __package__ == ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.package import package_task
from pipeline.preqc import run_preqc
from pipeline.registry_io import (
    VALID_STATUSES,
    board_counts,
    find_task,
    load_machine,
    load_registry,
    save_registry,
    set_status,
    tasks_for_session,
    utc_now,
)


def cmd_board(_: argparse.Namespace) -> int:
    reg = load_registry()
    counts = board_counts(reg)
    print(f"updated_at: {reg.get('updated_at')}")
    print(f"github: {reg.get('github', {})}")
    print("counts:", json.dumps(counts, sort_keys=True))
    print()
    print(f"{'ID':<18} {'SHORT':<10} {'STATUS':<22} {'SESSION':<8} NEXT")
    for t in reg["tasks"]:
        print(
            f"{t['id']:<18} {t.get('short',''):<10} {t.get('status',''):<22} "
            f"{str(t.get('session') or '-'):<8} {(t.get('next_action') or '')[:70]}"
        )
    return 0


def cmd_assign(args: argparse.Namespace) -> int:
    reg = load_registry()
    keys = [k.strip() for k in args.tasks.split(",") if k.strip()]
    if len(keys) > 3 and not args.force:
        print("Refusing >3 tasks per session without --force (keep sessions focused).", file=sys.stderr)
        return 2
    assigned = []
    for key in keys:
        t = find_task(reg, key)
        if t.get("session") and t["session"] != args.session and not args.force:
            print(f"Task {t['id']} locked by session {t['session']}; use --force to steal.", file=sys.stderr)
            return 2
        t["session"] = args.session
        t["updated_at"] = utc_now()
        if not t.get("next_action"):
            t["next_action"] = "Run PreQC: python -m pipeline.resume preqc --task " + t["id"]
        assigned.append(t["id"])
    save_registry(reg)
    print(f"Session {args.session} -> {', '.join(assigned)}")
    return 0


def cmd_release(args: argparse.Namespace) -> int:
    reg = load_registry()
    t = find_task(reg, args.task)
    t["session"] = None
    t["updated_at"] = utc_now()
    save_registry(reg)
    print(f"Released {t['id']}")
    return 0


def cmd_next(args: argparse.Namespace) -> int:
    reg = load_registry()
    tasks = tasks_for_session(reg, args.session) if args.session else reg["tasks"]
    priority = [
        "preqc_needs_fix",
        "pending",
        "preqc_running",
        "preqc_clean",
        "packaged",
        "ready_final",
        "needs_densify",
        "uploaded",
        "final_running",
        "ready_accept",
        "blocked",
    ]
    rank = {s: i for i, s in enumerate(priority)}
    open_tasks = [t for t in tasks if t.get("status") not in ("accepted",)]
    if not open_tasks:
        print("Nothing open.")
        return 0
    open_tasks.sort(key=lambda t: (rank.get(t.get("status", "pending"), 99), t["id"]))
    t = open_tasks[0]
    print(json.dumps({"id": t["id"], "short": t.get("short"), "status": t.get("status"), "next_action": t.get("next_action"), "pack_path": t.get("pack_path"), "canonical_zip": t.get("canonical_zip"), "last_preqc": t.get("last_preqc")}, indent=2))
    return 0


def cmd_preqc(args: argparse.Namespace) -> int:
    reg = load_registry()
    t = find_task(reg, args.task)
    result = run_preqc(t, full_model=args.full, mode=args.mode)
    save_registry(reg)
    print(json.dumps({k: v for k, v in result.items() if k not in ("stdout_tail", "stderr_tail")}, indent=2))
    if not result.get("ok"):
        print("--- stderr ---", file=sys.stderr)
        print(result.get("stderr_tail") or "", file=sys.stderr)
        return 1
    return 0 if result.get("status") == "preqc_clean" else 2


def cmd_package(args: argparse.Namespace) -> int:
    reg = load_registry()
    t = find_task(reg, args.task)
    if t.get("status") not in ("preqc_clean", "packaged", "ready_final", "needs_densify") and not args.force:
        print(f"Status is {t.get('status')}; run PreQC to clean first or pass --force.", file=sys.stderr)
        return 2
    result = package_task(t)
    save_registry(reg)
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


def cmd_loop(args: argparse.Namespace) -> int:
    """PreQC (+ optional package). Does not auto-edit task files — agent/human fixes between runs."""
    reg = load_registry()
    tasks = tasks_for_session(reg, args.session) if args.session else [find_task(reg, args.task)]
    if args.task and args.session:
        tasks = [find_task(reg, args.task)]
    exit_code = 0
    for t in tasks:
        print(f"\n=== {t['id']} ({t.get('short')}) status={t.get('status')} ===")
        if t.get("status") == "accepted":
            continue
        result = run_preqc(t, full_model=args.full)
        save_registry(reg)
        print(f"PreQC -> {result.get('status')} verdict={result.get('qc_verdict')} must_fix={result.get('must_fix_count')}")
        if result.get("status") == "preqc_clean" and args.package:
            pkg = package_task(t)
            save_registry(reg)
            print(f"Package -> {pkg}")
        elif result.get("status") == "preqc_needs_fix":
            exit_code = 2
            print("Fix findings, then re-run loop/preqc. Top fixes:")
            for row in (result.get("must_fix") or [])[:8]:
                print(f"  [{row.get('severity')}] {row.get('title')} -> {row.get('recommended_fix')}")
        elif not result.get("ok"):
            exit_code = 1
    return exit_code


def cmd_set_status(args: argparse.Namespace) -> int:
    reg = load_registry()
    t = find_task(reg, args.task)
    set_status(t, args.status, note=args.note, next_action=args.next)
    save_registry(reg)
    print(f"{t['id']} -> {args.status}")
    return 0


def cmd_mark_zip(args: argparse.Namespace) -> int:
    reg = load_registry()
    t = find_task(reg, args.task)
    t["canonical_zip"] = str(Path(args.zip).resolve())
    t["updated_at"] = utc_now()
    save_registry(reg)
    print(f"{t['id']} canonical_zip={t['canonical_zip']}")
    return 0


def cmd_watch_portal(args: argparse.Namespace) -> int:
    from pipeline.portal_watch import record_portal_check

    result = record_portal_check(
        args.task,
        phase=args.phase,
        running=not args.done,
        note=args.note or "",
        version=args.version,
        glm_pass=args.glm,
        oracle=args.oracle,
        task_url=args.url,
    )
    print(json.dumps(result, indent=2))
    return 0


def cmd_portal_status(args: argparse.Namespace) -> int:
    reg = load_registry()
    tasks = reg["tasks"] if not args.task else [find_task(reg, args.task)]
    rows = []
    for t in tasks:
        portal = t.get("portal") or {}
        if not portal and not args.all:
            continue
        rows.append(
            {
                "id": t["id"],
                "short": t.get("short"),
                "status": t.get("status"),
                "watch": portal.get("watch"),
                "phase": portal.get("phase"),
                "last_check_at": portal.get("last_check_at"),
                "glm_pass": portal.get("glm_pass"),
                "oracle": portal.get("oracle"),
                "version": portal.get("version"),
                "url": portal.get("task_url"),
            }
        )
    if not rows:
        # still show final_running even without portal blob
        rows = [
            {
                "id": t["id"],
                "short": t.get("short"),
                "status": t.get("status"),
                "next_action": t.get("next_action"),
            }
            for t in tasks
            if t.get("status") in ("final_running", "ready_accept", "needs_densify", "ready_final")
        ]
    print(json.dumps(rows, indent=2))
    return 0


def cmd_doctor(_: argparse.Namespace) -> int:
    machine = load_machine()
    reg = load_registry()
    print("machine_file:", machine.get("_path"))
    checks = {
        "preqc_script": machine.get("preqc_script"),
        "preqc_config": machine.get("preqc_config"),
        "setup_session_ps1": machine.get("setup_session_ps1"),
    }
    ok = True
    for name, path in checks.items():
        exists = Path(path).is_file() if path else False
        print(f"  {name}: {'OK' if exists else 'MISSING'} ({path})")
        ok = ok and exists
    missing_packs = []
    for t in reg["tasks"]:
        p = Path(t["pack_path"])
        if not (p.is_dir() and (p / "task.toml").is_file()):
            missing_packs.append(t["id"])
    print(f"task packs missing: {len(missing_packs)}")
    for mid in missing_packs[:20]:
        print(" ", mid)
    print("github_owner:", reg.get("github", {}).get("owner"))
    print("github_repo:", reg.get("github", {}).get("repo"))
    return 0 if ok and not missing_packs else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pipeline.resume", description="Haseeb Harbor multi-session task pipeline")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("board", help="Show all tasks / counts").set_defaults(func=cmd_board)
    sub.add_parser("doctor", help="Validate machine paths + packs").set_defaults(func=cmd_doctor)

    a = sub.add_parser("assign", help="Assign up to 3 tasks to a session")
    a.add_argument("--session", required=True)
    a.add_argument("--tasks", required=True, help="Comma-separated ids/shorts")
    a.add_argument("--force", action="store_true")
    a.set_defaults(func=cmd_assign)

    r = sub.add_parser("release", help="Clear session lock")
    r.add_argument("--task", required=True)
    r.set_defaults(func=cmd_release)

    n = sub.add_parser("next", help="Print next work item")
    n.add_argument("--session", default=None)
    n.set_defaults(func=cmd_next)

    q = sub.add_parser("preqc", help="Run local PreQC and update registry")
    q.add_argument("--task", required=True)
    q.add_argument("--full", action="store_true", help="Include GLM model review (needs API key)")
    q.add_argument("--mode", choices=("auto", "static", "runs"), default=None)
    q.set_defaults(func=cmd_preqc)

    pkg = sub.add_parser("package", help="Build QC zip and mark ready_final")
    pkg.add_argument("--task", required=True)
    pkg.add_argument("--force", action="store_true")
    pkg.set_defaults(func=cmd_package)

    loop = sub.add_parser("loop", help="PreQC session tasks; optional package when clean")
    loop.add_argument("--session", default=None)
    loop.add_argument("--task", default=None)
    loop.add_argument("--full", action="store_true")
    loop.add_argument("--package", action="store_true")
    loop.set_defaults(func=cmd_loop)

    st = sub.add_parser("set-status", help="Manual status (portal steps)")
    st.add_argument("--task", required=True)
    st.add_argument("--status", required=True, choices=VALID_STATUSES)
    st.add_argument("--note", default=None)
    st.add_argument("--next", default=None, dest="next")
    st.set_defaults(func=cmd_set_status)

    mz = sub.add_parser("mark-zip", help="Set canonical zip path")
    mz.add_argument("--task", required=True)
    mz.add_argument("--zip", required=True)
    mz.set_defaults(func=cmd_mark_zip)

    wp = sub.add_parser("watch-portal", help="Record a portal eval poll into registry")
    wp.add_argument("--task", required=True)
    wp.add_argument("--phase", required=True, help="e.g. oracle_waiting, glm_running, complete")
    wp.add_argument("--note", default="")
    wp.add_argument("--version", default=None)
    wp.add_argument("--glm", default=None, help="e.g. 2/4")
    wp.add_argument("--oracle", default=None, help="e.g. 1.0")
    wp.add_argument("--url", default=None)
    wp.add_argument("--done", action="store_true", help="Eval finished (not running)")
    wp.set_defaults(func=cmd_watch_portal)

    ps = sub.add_parser("portal-status", help="Show watched / in-flight portal evals")
    ps.add_argument("--task", default=None)
    ps.add_argument("--all", action="store_true")
    ps.set_defaults(func=cmd_portal_status)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
