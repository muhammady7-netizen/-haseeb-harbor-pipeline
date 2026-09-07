"""Record / print portal watch state for a running final QC."""
from __future__ import annotations

import json
from typing import Any

from .registry_io import find_task, load_registry, save_registry, set_status, utc_now


def record_portal_check(
    task_key: str,
    *,
    phase: str,
    running: bool,
    note: str = "",
    version: str | None = None,
    glm_pass: str | None = None,
    oracle: str | None = None,
    task_url: str | None = None,
) -> dict[str, Any]:
    reg = load_registry()
    task = find_task(reg, task_key)
    now = utc_now()
    portal = dict(task.get("portal") or {})
    if task_url:
        portal["task_url"] = task_url
    if version:
        portal["version"] = version
    portal["watch"] = True
    portal["last_check_at"] = now
    portal["phase"] = phase
    if glm_pass is not None:
        portal["glm_pass"] = glm_pass
    if oracle is not None:
        portal["oracle"] = oracle
    checks = list(portal.get("checks") or [])
    checks.append(
        {
            "at": now,
            "phase": phase,
            "running": running,
            "note": note,
            "glm_pass": glm_pass,
            "oracle": oracle,
        }
    )
    portal["checks"] = checks[-30:]
    task["portal"] = portal
    task["updated_at"] = now

    if running:
        set_status(
            task,
            "final_running",
            note=note or f"portal {phase}",
            next_action="Keep polling portal until Oracle+GLM×4 finishes",
        )
    elif glm_pass:
        # e.g. "2/4"
        try:
            num, den = glm_pass.split("/")
            rate = int(num) / int(den) if int(den) else 1
        except Exception:
            rate = 1.0
        if rate > 0.75:  # 4/4 or >3/4 depending on den
            set_status(
                task,
                "needs_densify",
                note=f"GLM {glm_pass} too easy",
                next_action="Densify task, PreQC, package, re-upload",
            )
        else:
            set_status(
                task,
                "ready_accept",
                note=f"GLM {glm_pass} within difficulty gate",
                next_action="Dismiss remaining PreQC if needed, then Accept on portal",
            )
    else:
        set_status(task, "final_running", note=note or phase)

    save_registry(reg)
    return {"task": task["id"], "short": task.get("short"), "status": task["status"], "portal": portal}
