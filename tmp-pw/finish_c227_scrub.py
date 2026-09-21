"""Finish c227 host-path scrub (space in username) and rebuild judge zip."""
from __future__ import annotations

import csv
import io
import json
import re
import shutil
import zipfile
from pathlib import Path

PACK = Path(
    r"C:\Users\Haseeb Mirza\Documents\Codex\2026-08-17\this-is-the-very-beginning-of\tasks\code-c227-work\code-c227-table-bloat-maintenance-audit"
)
NAME = "code-c227-table-bloat-maintenance-audit"
OUT = Path.home() / "Downloads" / "UPLOAD-THIS-TO-QC-code-c227-judge.zip"
CANON = Path(r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline\canonical-zips") / f"{NAME}.zip"
STAGE = Path(r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline\tmp-pw\c227-judge-stage")


def scrub(text: str) -> str:
    # Broken partial anonymizations first
    text = re.sub(
        r"/workspace Mirza(?:\\+|/)Documents(?:\\+|/)Codex(?:\\+|/)[^\"'\s]*",
        "/workspace",
        text,
        flags=re.I,
    )
    text = re.sub(
        r"workspace Mirza(?:\\+|/)Documents(?:\\+|/)Codex(?:\\+|/)[^\"'\n]*",
        "workspace",
        text,
        flags=re.I,
    )
    text = re.sub(
        r"(?:\.\.[\\/])+user[\\/]+Documents[\\/]+Codex[\\/]+[^\"'\s]*",
        "/workspace",
        text,
        flags=re.I,
    )
    text = re.sub(
        r"user(?:\\+|/)Documents(?:\\+|/)Codex(?:\\+|/)[^\"'\s]*",
        "/workspace",
        text,
        flags=re.I,
    )
    # Full Windows paths with spaces
    text = re.sub(
        r"C:\\\\Users\\\\[^\\\"']+\\\\Documents\\\\Codex\\\\[^\"']*",
        "/workspace",
        text,
        flags=re.I,
    )
    text = re.sub(
        r"C:\\Users\\[^\"'\n]+\\Documents\\Codex\\[^\"'\n]*",
        "/workspace",
        text,
        flags=re.I,
    )
    text = re.sub(
        r"C:/Users/[^\"'\s]+/Documents/Codex/[^\"'\s]*",
        "/workspace",
        text,
        flags=re.I,
    )
    text = re.sub(r"file:///C:/[^\"'\s]+", "file:///workspace", text, flags=re.I)
    text = re.sub(r"/Users/[^\"'\s]+", "/workspace", text)
    text = re.sub(r"Haseeb(?:%20| )?Mirza", "user", text, flags=re.I)
    # Any leftover Codex absolute fragments
    text = re.sub(
        r"[A-Za-z]:(?:\\+|/)Users(?:\\+|/)[^\"'\n]+(?:\\+|/)Codex(?:\\+|/)[^\"'\n]*",
        "/workspace",
        text,
        flags=re.I,
    )
    return text


def main() -> None:
    n = 0
    for p in (PACK / "evaluations").rglob("*"):
        if not p.is_file() or p.suffix == ".cast":
            continue
        if p.suffix not in {".json", ".txt", ".log", ".md", ".toml"} and p.name not in {
            "oracle.txt",
            "trial.log",
            "opencode.txt",
            "pytest-stdout.txt",
        }:
            continue
        try:
            raw = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        new = scrub(raw)
        if new != raw:
            p.write_text(new, encoding="utf-8", newline="\n")
            n += 1
            print("scrubbed", p.relative_to(PACK).as_posix())
    print("scrubbed", n)

    # rebuild stage/zip from pack (reuse Dockerfile/test.sh/review already fixed)
    if STAGE.exists():
        shutil.rmtree(STAGE)
    staged = STAGE / NAME
    shutil.copytree(
        PACK,
        staged,
        ignore=shutil.ignore_patterns(
            "__pycache__",
            ".pytest_cache",
            "*.pyc",
            "rl_world_verifiers",
            "_scratch",
            "xdg-data",
            "xdg-cache",
            "xdg-config",
            "xdg-state",
        ),
    )
    for zpath in (OUT, CANON):
        zpath.parent.mkdir(parents=True, exist_ok=True)
        if zpath.exists():
            zpath.unlink()
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in staged.rglob("*"):
                if not p.is_file():
                    continue
                if any(
                    x in p.parts
                    for x in (
                        "__pycache__",
                        ".pytest_cache",
                        "rl_world_verifiers",
                        "_scratch",
                    )
                ):
                    continue
                zf.write(p, (Path(NAME) / p.relative_to(staged)).as_posix())

    with zipfile.ZipFile(OUT) as zf:
        bad = []
        for name in zf.namelist():
            if "evaluations/" not in name:
                continue
            if not name.endswith((".json", ".txt", ".log", ".md")):
                continue
            t = zf.read(name).decode("utf-8", "ignore")
            # dates like 2026-08-17 in CSV data are OK; flag path-like
            if re.search(
                r"/workspace Mirza|Haseeb|C:/Users|C:\\\\Users|(?<![0-9])Documents\\\\Codex|(?<![0-9])Documents/Codex",
                t,
                re.I,
            ):
                # allow CSV dates 2026-08-17 alone
                if re.search(
                    r"/workspace Mirza|Haseeb|C:/Users|Users\\\\|user\\\\Documents|user/Documents",
                    t,
                    re.I,
                ):
                    bad.append(name)
        print("bad", len(bad), bad[:8])
        assert not bad, bad[:5]
        rev = zf.read(f"{NAME}/review.csv").decode()
        for row in csv.DictReader(io.StringIO(rev)):
            if row["status"] == "PASS":
                assert not (row.get("change_made") or "").strip()
        df = zf.read(f"{NAME}/environment/Dockerfile").decode()
        assert "chmod 000 /tests" in df and "USER appuser" in df
        assert b"\r" not in zf.read(f"{NAME}/tests/test.sh")
    print("ZIP_OK", OUT, OUT.stat().st_size)


if __name__ == "__main__":
    main()
