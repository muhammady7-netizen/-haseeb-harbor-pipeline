#!/usr/bin/env python3
"""Protected-file hashing for Harbor task repair.

Snapshots the files no repair may modify, then verifies they are unchanged.
Also rejects symlinks, which are an evidence-tampering vector.

Usage:
    python protect_hashes.py <task-folder> --write  .harbor-repair/protected.json
    python protect_hashes.py <task-folder> --verify .harbor-repair/protected.json

Exit codes: 0 ok; 1 a protected file changed, or a symlink was found; 2 bad usage.
"""
from __future__ import annotations
import argparse, hashlib, json, os, sys

# Paths no repair may modify. Prefix match against the task-relative path.
PROTECTED_PREFIXES = (
    "solution/",
    "evaluations/",
    "tests/rl_world_verifiers/",
    "environment/",
)
PROTECTED_FILES = (
    "instruction.md",
    "qc_report.html",
    "review.csv",
)
# environment/_app/tests/ IS editable (it is the mirror we must keep in sync)
EXEMPT_PREFIXES = ("environment/_app/tests/",)

# tests/rl_world_verifiers/ is the grading ENGINE and is protected - except that a task's own
# source adapter lives under sources/. These filenames are the shipped engine; anything else
# under sources/ is a task-specific adapter and is task-owned (editable).
ENGINE_SOURCE_FILES = {
    "__init__.py", "artifacts.py", "csv.py", "docx.py", "filesystem.py", "json.py",
    "md.py", "pdf.py", "pptx.py", "registry.py", "response.py", "text.py", "xlsx.py",
}


def is_task_source_adapter(rel):
    """True for a task-specific source adapter, which the repair may edit."""
    marker = "tests/rl_world_verifiers/sources/"
    if marker not in rel:
        return False
    fname = rel.rsplit("/", 1)[-1]
    return fname.endswith(".py") and fname not in ENGINE_SOURCE_FILES


def rel_paths(root):
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            full = os.path.join(dirpath, f)
            rel = os.path.relpath(full, root).replace("\\", "/")
            yield rel, full


def is_protected(rel):
    if any(rel.startswith(e) for e in EXEMPT_PREFIXES):
        return False
    if is_task_source_adapter(rel):
        return False
    if rel in PROTECTED_FILES:
        return True
    return any(rel.startswith(p) for p in PROTECTED_PREFIXES)


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def scan(root):
    out, symlinks = {}, []
    root_abs = os.path.abspath(root)
    for rel, full in rel_paths(root):
        if os.path.islink(full):
            symlinks.append(rel)
            continue
        # resolved target must stay inside the task root
        real = os.path.realpath(full)
        if not real.startswith(root_abs):
            symlinks.append(rel)
            continue
        if is_protected(rel):
            try:
                out[rel] = digest(full)
            except Exception as e:
                out[rel] = "ERR:" + repr(e)[:60]
    return out, symlinks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--write")
    ap.add_argument("--verify")
    args = ap.parse_args()
    if not os.path.isdir(args.root):
        sys.stderr.write("not a directory: " + args.root + "\n")
        sys.exit(2)
    if not (args.write or args.verify):
        sys.stderr.write("need --write or --verify\n")
        sys.exit(2)

    current, symlinks = scan(args.root)

    if symlinks:
        print("SYMLINK / ESCAPING PATH REJECTED:")
        for s in symlinks[:20]:
            print("   " + s)
        print("-> refusing to proceed; resolve these before repair")
        sys.exit(1)

    if args.write:
        os.makedirs(os.path.dirname(os.path.abspath(args.write)) or ".", exist_ok=True)
        json.dump({"root": args.root, "files": current}, open(args.write, "w"), indent=1)
        print("protected " + str(len(current)) + " files -> " + args.write)
        sys.exit(0)

    try:
        prev = json.load(open(args.verify, encoding="utf8")).get("files", {})
    except Exception as e:
        sys.stderr.write("cannot read baseline: " + repr(e)[:100] + "\n")
        sys.exit(2)

    changed = [k for k in prev if k in current and current[k] != prev[k]]
    missing = [k for k in prev if k not in current]
    added = [k for k in current if k not in prev]

    if changed or missing:
        print("PROTECTED FILES CHANGED - abort and report:")
        for k in changed:
            print("   MODIFIED " + k)
        for k in missing:
            print("   DELETED  " + k)
        sys.exit(1)

    if added:
        print("note: " + str(len(added)) + " new protected-area file(s) appeared:")
        for k in added[:10]:
            print("   " + k)
    print("ok - " + str(len(prev)) + " protected files unchanged")
    sys.exit(0)


if __name__ == "__main__":
    main()
