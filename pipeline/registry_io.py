from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PIPELINE_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = PIPELINE_ROOT / "registry.json"
MACHINE_PATH = PIPELINE_ROOT / "machine.json"
MACHINE_EXAMPLE = PIPELINE_ROOT / "machine.example.json"

VALID_STATUSES = (
    "pending",
    "preqc_running",
    "preqc_needs_fix",
    "preqc_clean",
    "packaged",
    "ready_final",
    "uploaded",
    "portal_preqc_dismissed",
    "final_running",
    "needs_densify",
    "ready_accept",
    "accepted",
    "blocked",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_machine() -> dict[str, Any]:
    path = MACHINE_PATH if MACHINE_PATH.is_file() else MACHINE_EXAMPLE
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    data["_path"] = str(path)
    return data


def load_registry() -> dict[str, Any]:
    if not REGISTRY_PATH.is_file():
        raise FileNotFoundError(f"Missing registry: {REGISTRY_PATH}")
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8-sig"))


def save_registry(reg: dict[str, Any]) -> None:
    reg["updated_at"] = utc_now()
    REGISTRY_PATH.write_text(json.dumps(reg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def find_task(reg: dict[str, Any], key: str) -> dict[str, Any]:
    key_l = key.strip().lower()
    for task in reg["tasks"]:
        aliases = {
            task["id"].lower(),
            task.get("short", "").lower(),
            task.get("pack_name", "").lower(),
            task.get("name", "").lower(),
        }
        if key_l in aliases or key_l in task["id"].lower() or key_l in task.get("short", "").lower():
            return task
    raise KeyError(f"Task not found: {key}")


def set_status(task: dict[str, Any], status: str, *, note: str | None = None, next_action: str | None = None) -> None:
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status {status}; expected one of {VALID_STATUSES}")
    task["status"] = status
    task["updated_at"] = utc_now()
    if note is not None:
        task["notes"] = note
    if next_action is not None:
        task["next_action"] = next_action
    hist = task.setdefault("history", [])
    hist.append({"at": task["updated_at"], "status": status, "note": note or ""})
    if len(hist) > 40:
        del hist[:-40]


def board_counts(reg: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for task in reg["tasks"]:
        st = task.get("status", "pending")
        counts[st] = counts.get(st, 0) + 1
    return counts


def tasks_for_session(reg: dict[str, Any], session: str) -> list[dict[str, Any]]:
    sid = session.strip()
    return [t for t in reg["tasks"] if str(t.get("session") or "") == sid]


def snapshot_task(task: dict[str, Any]) -> dict[str, Any]:
    return deepcopy(task)
