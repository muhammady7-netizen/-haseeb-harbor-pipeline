from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from .registry_io import load_machine, set_status, utc_now


def package_task(task: dict[str, Any]) -> dict[str, Any]:
    root = Path(task["work_root"])
    short = task.get("short") or task["id"]
    pack_name = task.get("pack_name") or Path(task["pack_path"]).name

    build_script = root / "build_qc_bundle.py"
    zip_candidates_before = _list_upload_zips(root)

    if build_script.is_file():
        proc = subprocess.run(
            [sys.executable, str(build_script)],
            cwd=str(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if proc.returncode != 0:
            set_status(
                task,
                "blocked",
                note=f"build_qc_bundle failed rc={proc.returncode}",
                next_action="Fix packager and retry package",
            )
            return {
                "ok": False,
                "returncode": proc.returncode,
                "stderr_tail": (proc.stderr or "")[-3000:],
                "stdout_tail": (proc.stdout or "")[-3000:],
            }

    zip_path = _newest_upload_zip(root, short=short, pack_name=pack_name)
    if zip_path is None and zip_candidates_before:
        zip_path = max(zip_candidates_before, key=lambda p: p.stat().st_mtime)

    if zip_path is None:
        # Fallback: zip the pack directory (source-only; no harbor-jobs)
        downloads = Path(load_machine().get("downloads_dir") or Path.home() / "Downloads")
        zip_path = root / f"UPLOAD-THIS-TO-QC-{short}.zip"
        _zip_pack(Path(task["pack_path"]), zip_path)
        dest = downloads / zip_path.name
        shutil.copy2(zip_path, dest)
        zip_path = dest if dest.is_file() else zip_path

    # Mirror to Downloads if not already there
    machine = load_machine()
    downloads = Path(machine.get("downloads_dir") or Path.home() / "Downloads")
    mirrored = downloads / zip_path.name
    if zip_path.resolve() != mirrored.resolve():
        try:
            shutil.copy2(zip_path, mirrored)
        except Exception:
            mirrored = zip_path

    task["canonical_zip"] = str(mirrored if mirrored.is_file() else zip_path)
    task["packaged_at"] = utc_now()
    set_status(
        task,
        "ready_final",
        note=f"Packaged {Path(task['canonical_zip']).name}",
        next_action=(
            "Upload canonical_zip to V2 trainer, Dismiss portal PreQC, run Oracle+GLM×4. "
            f"URL: {machine.get('v2_trainer_url', '')}"
        ),
    )
    return {"ok": True, "zip": task["canonical_zip"], "status": "ready_final"}


def _list_upload_zips(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    return list(root.glob("UPLOAD-THIS-TO-QC*.zip"))


def _newest_upload_zip(root: Path, *, short: str, pack_name: str) -> Path | None:
    cands = []
    for pattern in (
        f"UPLOAD-THIS-TO-QC-{short}.zip",
        f"UPLOAD-THIS-TO-QC-{short}*.zip",
        f"UPLOAD-THIS-TO-QC-{pack_name}*.zip",
        "UPLOAD-THIS-TO-QC*.zip",
    ):
        cands.extend(root.glob(pattern))
    # Also Downloads mirrors with same short name
    downloads = Path.home() / "Downloads"
    cands.extend(downloads.glob(f"UPLOAD-THIS-TO-QC-{short}*.zip"))
    cands = [p for p in cands if p.is_file()]
    if not cands:
        return None
    return max(cands, key=lambda p: p.stat().st_mtime)


def _zip_pack(pack: Path, dest: Path) -> None:
    import zipfile

    ignore = {".DS_Store", "__pycache__", ".git"}
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in pack.rglob("*"):
            if not path.is_file():
                continue
            if any(part in ignore or part.endswith(".pyc") for part in path.parts):
                continue
            if path.name.endswith(".zip"):
                continue
            arc = Path(pack.name) / path.relative_to(pack)
            zf.write(path, arcname=str(arc).replace("\\", "/"))
