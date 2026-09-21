#!/usr/bin/env python3
"""Stage 2 remediation for the repackaging QC gate.

The gate detects; it has no --fix. This applies the remediations its spec prescribes, in the
order the spec requires: content fixes in a single pass (C1, C2, C3, C9, C7), identity rename
after content (C5), non-task artefact sweep LAST (C8).

Every change is recorded per package in PACKAGING-PROVENANCE.json so a reviewer can see what was
altered and on what basis. Checks the spec marks manual (C4, C6, C10, C11, C12) are reported,
never auto-resolved.
"""
import argparse, ipaddress, json, os, re, shutil, subprocess, zipfile
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------- C1 digest map
# Resolved with `docker manifest inspect` on the pilot. Basis recorded per entry.
#
# python:3.12-slim-bookworm is pinned to the CORPUS-MAJORITY digest, not the digest the tag
# resolves to today. The tag has moved: this corpus contains six distinct digests for it, and
# today it resolves to a seventh (9c47360a...) that no run in this set ever used. a116514e is
# what 255 of the pinned sibling packages record, and it is still resolvable - so it is derived
# from the delivered evidence rather than from the clock.
DIGEST_MAP = {
    "python:3.12-slim-bookworm": {
        "digest": "sha256:a116514e19457bcb7af7efe9c3dd0b9b71e85b317694e7882a1c52aa15a78134",
        "basis": "corpus-majority digest (255 sibling packages pin it); verified resolvable",
        "resolves_today_to": "sha256:9c47360a2a0355e2da18516d0b1c2126ec22c195d2185e97347c9d98398c5bef",
    },
    "kuzphi/connectors-harness:real-data-v4": {
        "digest": "sha256:f976065bf0ef919c5e259651c266967f98c8302629d3fbdc41ba2d69f8c73ebb",
        "basis": "registry resolution; matches the digest 5 sibling packages already pin",
        "resolves_today_to": "sha256:f976065bf0ef919c5e259651c266967f98c8302629d3fbdc41ba2d69f8c73ebb",
    },
}
C1_FILES = ("environment/Dockerfile", "task.toml", "environment/_app/task.toml")


def _toml_loads(text):
    """Parse TOML if we can. On 3.10 without tomli there is no reader, so the guard below
    cannot verify the edit - say nothing rather than falsely certify it."""
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            return None
    return tomllib.loads(text)

# Tags outside the curated map get resolved against the registry, so this works on any task
# rather than only the corpus the map was built from. A digest resolved now constrains future
# rebuilds; it does not retroactively describe runs already recorded under evaluations/, and
# every provenance record says so.
_RESOLVED = {}
_DOCKER = None


def docker_available():
    """Whether the docker CLI is present.

    Deliberately NOT a daemon check. `docker manifest inspect` talks to the registry
    directly and works with the engine stopped, so gating on `.Server.Version` refused to
    resolve any tag on a machine where Docker Desktop simply was not running.
    """
    global _DOCKER
    if _DOCKER is None:
        _DOCKER = bool(shutil.which("docker"))
    return _DOCKER


def resolve_digest(ref):
    """Ask the registry for a tag's linux/amd64 digest. None when it cannot be established."""
    if ref in _RESOLVED:
        return _RESOLVED[ref]
    out = None
    if docker_available():
        try:
            r = subprocess.run(["docker", "manifest", "inspect", "-v", ref],
                               capture_output=True, text=True, timeout=120)
            if r.returncode == 0 and r.stdout.strip():
                d = json.loads(r.stdout)
                for e in (d if isinstance(d, list) else [d]):
                    desc = e.get("Descriptor", {}) or {}
                    plat = desc.get("platform", {}) or {}
                    if not isinstance(d, list) or (plat.get("architecture") == "amd64"
                                                   and plat.get("os") == "linux"):
                        if desc.get("digest"):
                            out = desc["digest"]
                            break
        except Exception:
            out = None
    _RESOLVED[ref] = out
    return out

# ---------------------------------------------------------------- C3 allow-list
SERVICE_ACCOUNTS = {"rlgymagent", "harbor", "runner", "node", "user", "app", "ubuntu", "root"}
HOME_PATTERNS = [
    re.compile(r"(/Users/)([A-Za-z0-9._-]+)"),
    re.compile(r"([Cc]:\\{1,2}Users\\{1,2})([A-Za-z0-9._-]+)"),
    re.compile(r"(/home/)([A-Za-z0-9._-]+)(?=/)"),
]
PLACEHOLDER_USER = "user"

# ---------------------------------------------------------------- C2 host-position IPv4
IP_RE = re.compile(r"(?<![\w.])((?:\d{1,3}\.){3}\d{1,3})(?![\w.])")
HOST_KEY = re.compile(
    r"(?:https?://|ftp://|@|\b(?:host|hostname|server|endpoint|base_url|baseurl|proxy|gateway)"
    r"\b[\"']?\s*[:=]\s*[\"']?)\s*$", re.I)
PLACEHOLDER_IP = "203.0.113.10"     # RFC 5737 TEST-NET-3: neutral, never routable

# ---------------------------------------------------------------- C8 artefacts
# .bak is deliberately NOT here. Three packages in this corpus ship a real .bak as fixture data
# (a superseded plan the audit must catch, an old Dockerfile) and the gate does not flag it.
ARTEFACT_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}
ARTEFACT_SUFFIX = (".orig", ".rej", ".swp", ".swo", ":Zone.Identifier")
ARTEFACT_DIRS = {"__MACOSX", "__pycache__"}

TEXT_EXT = {".py", ".md", ".txt", ".json", ".toml", ".yaml", ".yml", ".sh", ".cfg", ".ini",
            ".csv", ".html", ".htm", ".js", ".ts", ".jsonl", ".log", ".conf", ".env", "",
            ".tsv", ".xml", ".rst", ".patch", ".diff", ".sql", ".properties", ".lock",
            ".dockerfile", ".gitignore", ".bak", ".orig", ".out", ".err", ".trace"}


def is_text(p):
    if p.suffix.lower() not in TEXT_EXT:
        return False
    try:
        # trajectory.json routinely runs to tens of MB and is exactly where an authoring path
        # shows up. An 8 MB cutoff silently skipped those, so the sanitisation looked complete
        # while the largest evidence files kept the leak.
        if p.stat().st_size > 256 * 1024 * 1024:
            return False
        with open(p, "rb") as f:
            return b"\0" not in f.read(4096)
    except OSError:
        return False


def read(p):
    try:
        return p.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def routable(ip):
    try:
        a = ipaddress.IPv4Address(ip)
    except ValueError:
        return False
    return not (a.is_private or a.is_loopback or a.is_link_local or a.is_multicast
                or a.is_reserved or a.is_unspecified
                or a in ipaddress.IPv4Network("192.0.2.0/24")
                or a in ipaddress.IPv4Network("198.51.100.0/24")
                or a in ipaddress.IPv4Network("203.0.113.0/24"))


# ---------------------------------------------------------------- C1
def fix_c1(root, log):
    for rel in C1_FILES:
        p = root / rel
        if not p.is_file():
            continue
        s = read(p)
        if s is None:
            continue
        out, changed = [], False
        for line in s.splitlines(keepends=True):
            # `.` never matches a newline, so a trailing `.*` group stops before the line
            # terminator. Rebuilding the line from the groups therefore DROPS it and welds this
            # line onto the next - which produced `...c73ebb"host_port = 8016` and left task.toml
            # unparseable. Split the terminator off first and re-attach it verbatim.
            core = line.rstrip(chr(13) + chr(10))
            eol = line[len(core):]
            key, m, kind = None, None, None
            m = re.match(r"(\s*FROM\s+)(\S+)(.*)", core)
            if m:
                key, kind = m.group(2), "FROM"
            else:
                m = re.match(r"(\s*image\s*=\s*[\"'])([^\"']+)([\"'].*)", core)
                if m:
                    key, kind = m.group(2), "image"
            if key and "@sha256:" not in key:
                lookup = key[len("docker.io/"):] if key.startswith("docker.io/") else key
                ent = DIGEST_MAP.get(lookup)
                if ent:
                    repo = lookup.split(":")[0]
                    prefix = "docker.io/" if key.startswith("docker.io/") else ""
                    new = "%s%s@%s" % (prefix, repo, ent["digest"])
                    line = m.group(1) + new + m.group(3) + eol
                    changed = True
                    log.append({"check": "C1", "file": rel, "kind": kind, "from": key,
                                "to": new, "basis": ent["basis"]})
                else:
                    dig = resolve_digest(key)
                    if dig:
                        repo = lookup.split(":")[0]
                        prefix = "docker.io/" if key.startswith("docker.io/") else ""
                        new = "%s%s@%s" % (prefix, repo, dig)
                        line = m.group(1) + new + m.group(3) + eol
                        changed = True
                        log.append({"check": "C1", "file": rel, "kind": kind, "from": key,
                                    "to": new,
                                    "basis": "resolved from the registry at package time"})
                    else:
                        why = ("registry lookup failed - tag missing, or no pull access"
                               if docker_available() else
                               "docker not available to resolve the tag")
                        log.append({"check": "C1", "file": rel, "kind": kind, "unresolved": key,
                                    "action": "left unpinned - " + why})
            out.append(line)
        if changed:
            new_text = "".join(out)
            # Never hand back a file our own edit broke. A malformed task.toml is invisible to
            # the gate (G01 only looks for @sha256:) and surfaces at pipeline intake, by which
            # point the package has already shipped as "remediated".
            if rel.endswith(".toml"):
                try:
                    _toml_loads(new_text)
                except Exception as exc:
                    log.append({"check": "C1", "file": rel, "severity": "BLOCK",
                                "action": "edit REVERTED - it would not parse: %s" % exc})
                    continue
            p.write_text(new_text, encoding="utf-8")


# ---------------------------------------------------------------- C2 + C3
def fix_c2_c3(root, log):
    for p in root.rglob("*"):
        if not p.is_file() or p.is_symlink() or not is_text(p):
            continue
        s = read(p)
        if s is None:
            continue
        rel = p.relative_to(root).as_posix()
        orig = s
        buf = {"s": s}

        def ip_sub(m):
            ip = m.group(1)
            if not routable(ip):
                return ip
            cur = buf["s"]
            before = cur[max(0, m.start() - 40):m.start()]
            after = cur[m.end():m.end() + 6]
            if HOST_KEY.search(before) or re.match(r":\d{2,5}\b", after):
                log.append({"check": "C2", "file": rel, "from": "<redacted routable IPv4>",
                            "to": PLACEHOLDER_IP})
                return PLACEHOLDER_IP
            return ip

        s = IP_RE.sub(ip_sub, s)

        for pat in HOME_PATTERNS:
            def home_sub(m):
                name = m.group(2)
                if name.lower() in SERVICE_ACCOUNTS:
                    return m.group(0)
                # Record WHAT was replaced, never the name itself: writing the original path
                # into the provenance file re-introduces into the package the exact string C3
                # exists to remove, and the gate then flags our own record.
                log.append({"check": "C3", "file": rel, "from": m.group(1) + "<redacted>",
                            "to": m.group(1) + PLACEHOLDER_USER})
                return m.group(1) + PLACEHOLDER_USER
            s = pat.sub(home_sub, s)

        if s != orig:
            p.write_text(s, encoding="utf-8")


# ---------------------------------------------------------------- C9
def fix_c9(root, log):
    for name in ("tests/verifier.json", "environment/_app/tests/verifier.json"):
        p = root / name
        if not p.is_file():
            continue
        s = read(p)
        if s is None:
            continue
        try:
            d = json.loads(s)
        except json.JSONDecodeError:
            continue
        vs = d.get("verifiers")
        if not isinstance(vs, list):
            continue
        changed = False
        for v in vs:
            if not isinstance(v, dict):
                continue
            src, hj = v.get("source"), v.get("how_justification")
            if not isinstance(src, str) or not isinstance(hj, str):
                continue
            stem, real = Path(src).stem, Path(src).suffix
            if not stem or not real:
                continue
            m = re.search(re.escape(stem) + r"\.([A-Za-z0-9]{1,6})\b", hj)
            if m and ("." + m.group(1)) != real:
                v["how_justification"] = hj[:m.start()] + stem + real + hj[m.end():]
                log.append({"check": "C9", "file": name, "verifier": v.get("id") or stem,
                            "from": m.group(0), "to": stem + real})
                changed = True
        if changed:
            p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- C7
def fix_c7(root, log):
    p = root / "README.md"
    if p.exists():
        return
    name, desc = root.name, ""
    tt = root / "task.toml"
    if tt.is_file():
        s = read(tt) or ""
        m = re.search(r'^\s*name\s*=\s*["\']([^"\']+)', s, re.M)
        if m:
            name = m.group(1)
        m = re.search(r'^\s*description\s*=\s*["\']([^"\']+)', s, re.M)
        if m:
            desc = m.group(1)
    nver = 0
    vj = root / "tests/verifier.json"
    if vj.is_file():
        try:
            d = json.loads(read(vj) or "{}")
            nver = len(d.get("verifiers") or d.get("checks") or [])
        except json.JSONDecodeError:
            pass
    runs = sorted(q.name for q in (root / "evaluations").glob("*")) \
        if (root / "evaluations").is_dir() else []
    body = ["# %s" % name, ""]
    if desc:
        body += [desc, ""]
    body += ["_This README was generated from the contents of this package, not authored._", "",
             "## Contents", "",
             "- `instruction.md` - the task brief given to the agent.",
             "- `tests/` - the verifier set (%d verifiers)." % nver,
             "- `environment/` - the container definition and input tree.",
             "- `evaluations/` - recorded run evidence: %s."
             % (", ".join("`%s`" % r for r in runs) or "none"),
             ""]
    p.write_text("\n".join(body), encoding="utf-8")
    log.append({"check": "C7", "file": "README.md", "action": "generated from package evidence"})


# ---------------------------------------------------------------- C8 (last)
def fix_c8(root, log):
    cand = []
    for p in root.rglob("*"):
        if p.is_dir():
            if p.name in ARTEFACT_DIRS:
                cand.append(p)
            continue
        if p.name in ARTEFACT_NAMES or p.name.startswith("._") \
           or any(p.name.endswith(x) for x in ARTEFACT_SUFFIX):
            cand.append(p)
    if not cand:
        return
    candset = set(cand)
    names = {p.name for p in cand if p.is_file()}
    referenced = set()
    if names:
        for p in root.rglob("*"):
            if p.is_file() and p not in candset and is_text(p):
                s = read(p)
                if s:
                    for n in names:
                        if n in s:
                            referenced.add(n)
    for p in cand:
        rel = p.relative_to(root).as_posix()
        if p.is_file() and p.name in referenced:
            log.append({"check": "C8", "file": rel,
                        "action": "KEPT - referenced elsewhere in the package"})
            continue
        try:
            shutil.rmtree(p) if p.is_dir() else p.unlink()
            log.append({"check": "C8", "file": rel, "action": "removed"})
        except OSError as e:
            log.append({"check": "C8", "file": rel, "action": "remove failed: %s" % e})


# ---------------------------------------------------------------- C5 identity
def task_leaf(root):
    tt = root / "task.toml"
    if not tt.is_file():
        return None
    m = re.search(r'^\s*name\s*=\s*["\']([^"\']+)', read(tt) or "", re.M)
    if not m:
        return None
    return m.group(1).strip().strip("/").split("/")[-1] or None


# ---------------------------------------------------------------- report-only
def report_manual(root, log):
    dd = root / "evaluations" / "difficulty"
    rewards = []
    if dd.is_dir():
        for r in sorted(d for d in dd.glob("r*") if d.is_dir()):
            # the reward sits under the run's verifier/ subtree, not at the run root - looking
            # only at r/reward.txt reports a complete battery as missing, which is exactly the
            # false positive that made G10 fire on 340 of 341 packages
            f = next(iter(sorted(r.rglob("reward.txt"))), None)
            if f is not None:
                m = re.search(r"-?\d+\.?\d*", read(f) or "")
                if m:
                    rewards.append(float(m.group(0)))
                    continue
            for cand in sorted(r.rglob("reward.json")) + sorted(r.rglob("result.json")):
                try:
                    d = json.loads(read(cand) or "{}")
                except json.JSONDecodeError:
                    continue
                if isinstance(d, dict) and isinstance(d.get("reward"), (int, float)):
                    rewards.append(float(d["reward"]))
                    break
    if len(rewards) != 4:
        log.append({"check": "C10", "severity": "BLOCK", "manual": True,
                    "found_rewards": len(rewards),
                    "action": "route to review - do not ship without the four-run battery"})
    else:
        npass = sum(1 for r in rewards if r == 1.0)
        band = "out-of-band(4/4)" if npass == 4 else ("light(3/4)" if npass == 3 else "full(0-2/4)")
        log.append({"check": "C11", "manual": True, "rewards": rewards, "passes": npass,
                    "recomputed_band": band})


def zip_dir(src, dest, arcroot):
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(src.rglob("*")):
            if p.is_symlink():
                continue
            z.write(p, os.path.join(arcroot, p.relative_to(src).as_posix()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", type=Path, help="directory of input .zip packages")
    ap.add_argument("out", type=Path, help="directory for remediated .zip packages")
    ap.add_argument("--work", type=Path, default=Path.home() / "s2work")
    ap.add_argument("--report", type=Path, default=Path.home() / "stage2_report.json")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--only", default=None, help="comma-separated package stems")
    a = ap.parse_args()

    a.out.mkdir(parents=True, exist_ok=True)
    a.work.mkdir(parents=True, exist_ok=True)
    zips = sorted(a.src.glob("*.zip"))
    if a.only:
        want = set(a.only.split(","))
        zips = [z for z in zips if z.stem in want]
    if a.limit:
        zips = zips[:a.limit]

    # C5 renames the archive to the name task.toml declares. Two packages in this corpus can
    # declare the SAME name (a clean name and a "-v1-fixed2" variant of it), and renaming both
    # writes one archive over the other - silent data loss. Work out the intended names first
    # and refuse to rename any that collide; a duplicate is a decision for a human, not a
    # filename clash to resolve by overwriting.
    intended = {}
    for z in zips:
        leaf = None
        try:
            with zipfile.ZipFile(z) as zf:
                for n in zf.namelist():
                    if n.count("/") == 1 and n.endswith("/task.toml"):
                        m = re.search(r'^\s*name\s*=\s*["\']([^"\']+)',
                                      zf.read(n).decode("utf-8", "replace"), re.M)
                        if m:
                            leaf = m.group(1).strip().strip("/").split("/")[-1]
                        break
        except (zipfile.BadZipFile, OSError):
            pass
        intended.setdefault(leaf or z.stem, []).append(z.stem)
    collide = {k for k, v in intended.items() if len(v) > 1}
    if collide:
        print("C5: %d colliding target name(s); those archives keep their original names"
              % len(collide), flush=True)

    report = {}
    for i, z in enumerate(zips, 1):
        stem = z.stem
        wd = a.work / stem
        if wd.exists():
            shutil.rmtree(wd, ignore_errors=True)
        wd.mkdir(parents=True)
        try:
            with zipfile.ZipFile(z) as zf:
                zf.extractall(wd)
        except zipfile.BadZipFile:
            report[stem] = [{"check": "-", "error": "bad zip"}]
            shutil.rmtree(wd, ignore_errors=True)
            continue
        tops = [d for d in wd.iterdir() if d.is_dir()]
        root = tops[0] if len(tops) == 1 else wd
        log = []

        fix_c1(root, log)          # 1. content fixes, single pass
        fix_c2_c3(root, log)
        fix_c9(root, log)
        fix_c7(root, log)
        report_manual(root, log)

        leaf = task_leaf(root)     # 2. identity rename after content
        arcname = stem
        if leaf and leaf in collide:
            log.append({"check": "C5", "severity": "BLOCK", "manual": True,
                        "declared_name": leaf, "also_declared_by": intended[leaf],
                        "action": "rename REFUSED - two packages declare this name; "
                                  "kept original filename so neither is overwritten. "
                                  "Route to review: decide which variant ships."})
            leaf = None
        if leaf and root != wd and leaf != root.name:
            new = root.parent / leaf
            if not new.exists():
                root.rename(new)
                log.append({"check": "C5", "from": root.name, "to": leaf,
                            "action": "root directory renamed to task.toml name"})
                root = new
        if leaf and leaf != stem:
            log.append({"check": "C5", "from": stem + ".zip", "to": leaf + ".zip",
                        "action": "archive renamed to task.toml name"})
            arcname = leaf

        fix_c8(root, log)          # 3. artefact sweep LAST

        prov = {
            "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source_archive": z.name,
            "tool": "stage2_fix.py (repackaging QC gate remediation)",
            "note": ("Digest pins constrain future rebuilds. They do not retroactively describe "
                     "the historical runs recorded under evaluations/, which were produced before "
                     "this pin was applied."),
            "changes": log,
        }
        (root / "PACKAGING-PROVENANCE.json").write_text(
            json.dumps(prov, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        zip_dir(root, a.out / (arcname + ".zip"), arcname)
        shutil.rmtree(wd, ignore_errors=True)
        report[stem] = log
        if i % 20 == 0:
            print("[%s] %d/%d" % (datetime.now().strftime("%H:%M:%S"), i, len(zips)), flush=True)

    a.report.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    tot = {}
    for log in report.values():
        for e in log:
            tot[e.get("check", "?")] = tot.get(e.get("check", "?"), 0) + 1
    print("packages: %d" % len(report))
    for k in sorted(tot):
        print("  %-4s %d changes" % (k, tot[k]))
    print("report: %s" % a.report)


if __name__ == "__main__":
    main()
