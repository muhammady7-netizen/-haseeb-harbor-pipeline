"""Final c227 path scrub + zip."""
from __future__ import annotations

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


def scrub(t: str) -> str:
    patterns = [
        (r"/workspace Mirza\\AppData\\[^\n\"']*", "/workspace"),
        (r"/workspace Mirza\\\\AppData\\\\[^\n\"']*", "/workspace"),
        (r"(?:\.\.[\\/])+user[\\/]+AppData[\\/]+[^\n\"'\s]*", "/workspace"),
        (r"rootdir: C:\\Users\b", "rootdir: /workspace"),
        (r"rootdir: C:\\\\Users\b", "rootdir: /workspace"),
        (r"/workspace Mirza(?:\\+|/)[^\n\"']*", "/workspace"),
        (r"Haseeb(?:%20| )?Mirza", "user"),
        (r"C:\\Users\b", "/workspace"),
        (r"C:\\\\Users\b", "/workspace"),
    ]
    for pat, repl in patterns:
        t = re.sub(pat, repl, t, flags=re.I)
    return t


def main() -> None:
    n = 0
    for p in (PACK / "evaluations").rglob("*"):
        if not p.is_file():
            continue
        if p.suffix not in {".json", ".txt", ".log", ".md"} and p.name not in {
            "pytest-stdout.txt",
            "trial.log",
            "opencode.txt",
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
    print("scrubbed", n)

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
                    for x in ("__pycache__", ".pytest_cache", "rl_world_verifiers", "_scratch")
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
            if re.search(
                r"/workspace Mirza|Haseeb|C:\\\\Users|C:/Users|user\\\\AppData|user/AppData|rootdir: C:",
                t,
                re.I,
            ):
                bad.append(name)
        print("bad", bad)
        assert not bad
        assert "chmod 000 /tests" in zf.read(f"{NAME}/environment/Dockerfile").decode()
        assert b"\r" not in zf.read(f"{NAME}/tests/test.sh")
        assert not any("_scratch" in n for n in zf.namelist())
    print("ZIP_OK", OUT, OUT.stat().st_size)
    print("CANON", CANON)


if __name__ == "__main__":
    main()
