"""Build LF-normalized QC upload zip for code-c227.

Excludes stale evaluations/ (prompt/grid drift). Includes tests/verifier.json.
Emits packaging report; does not delete source evaluations.
"""
from __future__ import annotations

import json
import re
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BUNDLE = "code-c227-table-bloat-maintenance-audit"
OUT_NAME = "UPLOAD-THIS-TO-QC-code-c227.zip"

IGNORE_DIR = {
    ".git",
    "__pycache__",
    ".venv",
    "node_modules",
    ".cursor",
    "_stale_evaluations_bak_20260918",
    "harbor-jobs-c227",
}
IGNORE_FILE_PREFIX = ("_",)  # local helper scripts
IGNORE_SUFFIX = {".zip", ".pyc", ".pyo"}
BINARY_SUFFIX = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".gz", ".xlsx"}


def should_skip(path: Path) -> bool:
    rel_parts = path.relative_to(ROOT).parts
    if any(p in IGNORE_DIR for p in rel_parts):
        return True
    if path.name.startswith(IGNORE_FILE_PREFIX) and path.suffix == ".py":
        return True
    if path.suffix.lower() in IGNORE_SUFFIX:
        return True
    if path.name in {".DS_Store", "Thumbs.db"}:
        return True
    return False


def normalize_bytes(data: bytes, *, binary: bool) -> tuple[bytes, bool]:
    if binary:
        return data, False
    changed = b"\r" in data
    if changed:
        data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return data, changed


def main() -> None:
    vpath = ROOT / "tests" / "verifier.json"
    if not vpath.is_file():
        raise SystemExit("P0: tests/verifier.json missing — refuse to pack")

    v = json.loads(vpath.read_text(encoding="utf-8"))
    vcount = len(v.get("verifiers", []))
    src = (ROOT / "tests" / "test_outputs.py").read_text(encoding="utf-8")
    tcount = len(re.findall(r"^def test_", src, re.M))

    destinations = [
        ROOT / OUT_NAME,
        Path.home() / "Downloads" / OUT_NAME,
        Path.home() / "Downloads" / "UPLOAD-THIS-TO-QC-code-c227-judge.zip",
        ROOT.parent.parent / "canonical-zips" / OUT_NAME,
        ROOT.parent.parent / "sessions" / "B" / "zips" / OUT_NAME,
    ]

    files: list[tuple[Path, str, bytes]] = []
    crlf_fixed = 0
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or should_skip(path):
            continue
        rel = path.relative_to(ROOT).as_posix()
        raw = path.read_bytes()
        binary = path.suffix.lower() in BINARY_SUFFIX
        data, changed = normalize_bytes(raw, binary=binary)
        if changed:
            crlf_fixed += 1
            # Keep source tree LF-clean when we normalize
            path.write_bytes(data)
        arc = f"{BUNDLE}/{rel}"
        files.append((path, arc, data))

    # evaluations/ must already contain fresh oracle (and later GLM/stability).
    eval_summary = ROOT / "evaluations" / "EVIDENCE_SUMMARY.json"
    if not eval_summary.is_file():
        raise SystemExit("evaluations/EVIDENCE_SUMMARY.json missing — run _pack_oracle_eval.py first")

    primary = destinations[0]
    with zipfile.ZipFile(primary, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for _, arc, data in files:
            # ZipInfo with explicit LF content; Unix perms
            info = zipfile.ZipInfo(arc)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, data)

    # Verify package
    with zipfile.ZipFile(primary) as zf:
        names = zf.namelist()
        has_v = any(n.endswith("tests/verifier.json") for n in names)
        crlf = 0
        for n in names:
            if n.endswith("/") or any(n.lower().endswith(s) for s in BINARY_SUFFIX):
                continue
            if b"\r" in zf.read(n):
                crlf += 1
        if not has_v:
            raise SystemExit("Pack verify failed: verifier.json missing from zip")
        if crlf:
            raise SystemExit(f"Pack verify failed: {crlf} CRLF files in zip")

    mirrored = []
    for dest in destinations[1:]:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(primary, dest)
        mirrored.append(str(dest))

    report = {
        "ok": True,
        "zip": str(primary),
        "size": primary.stat().st_size,
        "entries": len(files),
        "pytest_test_count": tcount,
        "verifier_json_count": vcount,
        "source_crlf_normalized": crlf_fixed,
        "zip_crlf": 0,
        "has_verifier": True,
        "evaluations_shipped": sorted(
            {
                Path(arc).parts[1]
                for _, arc, _ in files
                if arc.startswith(f"{BUNDLE}/evaluations/") and len(Path(arc).parts) > 2
            }
        ),
        "mirrored": mirrored,
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
