#!/usr/bin/env python3
"""judge.py - one-command Harbor-Shannon task judgment.

Extracts a task zip and runs the complete Harbor-Shannon QC pipeline against it:

  1. The deterministic QC engine (harbor_shannon_qc.py --no-model) and its
     output is parsed for every deterministic finding, gate, packaging row and
     reward-hacking signal.
  2. The model QC engine (without --no-model) when WANDB_GLM_API_KEY is set, so
     the static review and run-triage findings are merged in.
  3. A set of extra deterministic checks the engine does NOT perform directly:
       - CRLF / UTF-8 BOM byte scan on every text file (Layer 0.0 / 0.0b)
       - gold derivability heuristics (self-contradiction, hair-splits,
         placeholder text) - Layer 10a
       - trajectory freshness (embedded counts in golden/oracle trajectories vs
         the current solution/files gold) - Layer 10c / 10g
       - review.csv count claims vs the ACTUAL gold results - Layer 10g
       - /tests lock in the Dockerfile (graders must stay outside the image) -
         Layer 1.2 / 5.28
       - host home paths in bundled trial metadata - Layer 5.24
       - D1-D5 verifier-defect linter (re-implemented from the checklist) -
         Layer 8

All findings are de-duplicated against the engine's findings, then a single
verdict is printed: PASS / NEEDS_REVIEW / FAIL with P0/P1/P2 counts and every
finding's severity, title and fix.

Usage:
    python judge.py <task.zip>
    python judge.py <task.zip> --no-model          # skip the model stage
    python judge.py <task.zip> --engine <path>     # custom engine location

Self-contained: stdlib only (argparse, csv, io, json, os, re, subprocess, sys,
tempfile, zipfile, pathlib, collections, hashlib, difflib, time).
Runs in under 30 seconds excluding the model stage.
"""

import argparse
import csv
import difflib
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

VERSION = "1.0"

ENGINE_DEFAULT = r"C:\Users\Haseeb Mirza\Downloads\Harbor-Shannon-QC\harbor_shannon_qc.py"
ENV_ENGINE = "JUDGE_ENGINE"
ENV_KEY = "WANDB_GLM_API_KEY"

VERDICTS = ("PASS", "NEEDS_REVIEW", "FAIL")
SEVERITIES = ("P0", "P1", "P2", "INFO")

TEXT_EXTS = {
    ".sh", ".py", ".json", ".md", ".csv", ".toml", ".txt", ".rst", ".yaml",
    ".yml", ".xml", ".tsv", ".html", ".htm", ".sql", ".go", ".rs", ".java",
    ".ts", ".js", ".cfg", ".ini", ".ps1",
}
PROSE_EXTS = {".md", ".txt", ".rst", ".markdown"}

DOCKER_COPY = re.compile(r"^\s*(?:COPY|ADD)\s+(?:--[\w=-]+\s+)*(.+?)\s*$", re.I)
DOCKER_USER = re.compile(r"^\s*USER\s+(\S+)", re.I)
HOST_PATH = re.compile(r"/Users/[A-Za-z]|C:\\Users\\|/home/[a-z]")
ENTITY_ID = re.compile(r"\b[A-Z]{1,6}[-_]\d{1,6}\b")
FILE_TOKEN = re.compile(
    r"`([^`\n]*\.[A-Za-z][A-Za-z0-9]{0,7})`|"
    r"(?<![\w/.-])([A-Za-z0-9_@+()\[\]-]+\.[A-Za-z][A-Za-z0-9]{0,7})(?![\w/.-])"
)
VERDICT_COL = re.compile(
    r"^(verdict|decision|label|status|review_status|recommendation|recommendation_id|"
    r"outcome|action|conclusion|result|flag|category|classification|approved|approve|"
    r"rejected|reject|pass|fail|yes|no|is_valid|valid|correct|score)$", re.I
)
TEXT_COL = re.compile(
    r"^(wording|text|description|line|claim|statement|content|body|message|note|"
    r"summary|item|name|title|prompt|reason|rationale|justification|entry|question|"
    r"issue|topic|observation|finding|comment)$", re.I
)
PLACEHOLDER = re.compile(
    r"\b(placeholder|todo|tbd|fixme|xxx|lorem ipsum|\[insert|<insert|wording is|"
    r"replace_me|fill_in|sample text|example text)\b", re.I
)
COUNT_KEY = re.compile(
    r"(count|total|number|verified|at_?odds|passed|failed|flagged|reviewed|"
    r"approved|rejected|open|closed|lines|rows|entries|items|findings|issues)",
    re.I
)
ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
MODEL_ID = re.compile(r'"(openai/[\w.-]+|glm/[\w.-]+|anthropic/[\w.-]+|google/[\w.-]+)"')


# --------------------------------------------------------------------------
# small utilities
# --------------------------------------------------------------------------

def log(msg):
    print(msg, file=sys.stderr, flush=True)


def rel(path, root):
    try:
        return str(path.relative_to(root)).replace(os.sep, "/")
    except ValueError:
        return str(path)


def read_text(path):
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def read_bytes(path):
    try:
        return path.read_bytes()
    except OSError:
        return b""


def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def normalize_ws(text):
    return re.sub(r"\s+", " ", text.replace("\r", "")).strip()


def word_count(text):
    return len(re.findall(r"\b[\w'-]+\b", text))


def natural_key(value):
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", str(value))]


def words_of(text):
    return re.findall(r"\b[\w'-]+\b", text.lower())


def tokens_of(pattern):
    cleaned = re.sub(r"\(\?[a-z]+\)", " ", pattern)
    cleaned = re.sub(r"\\[bBAZsSdDwW]", " ", cleaned)
    cleaned = re.sub(r"\[[^\]]*\]", " ", cleaned)
    cleaned = re.sub(r"\{\d+(?:,\d*)?\}", " ", cleaned)
    cleaned = re.sub(r"\\(.)", r"\1", cleaned)
    return [t for t in re.findall(r"[A-Za-z][A-Za-z0-9_'-]{2,}", cleaned)
            if t.lower() not in {"the", "and", "for", "with", "that", "this", "from"}]


def topic_words(title):
    return {w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9_]{3,}", title or "")}


def nested(value, *keys):
    cur = value
    for k in keys:
        if isinstance(cur, dict):
            cur = cur.get(k)
        elif isinstance(cur, list) and k.isdigit() and int(k) < len(cur):
            cur = cur[int(k)]
        else:
            return None
    return cur


# --------------------------------------------------------------------------
# findings container
# --------------------------------------------------------------------------

class Findings:
    def __init__(self):
        self.items = []
        self._n = 0

    def add(self, severity, source, title, *, label="info", owner="task",
             observed_fact="", evidence=None, impact="", recommended_fix="",
             blocks=None, gate="", fix_path="", category=""):
        if severity not in SEVERITIES:
            severity = "P2"
        if blocks is None:
            blocks = "reject" if severity == "P0" and "environment" in gate else (
                "rework" if severity in ("P0", "P1") else "none")
        self._n += 1
        prefix = {"judge": "JUDGE", "d1d5": "LINT", "engine": "ENG"}.get(source, "X")
        item = {
            "id": f"{prefix}-{self._n:03d}",
            "source": source,
            "severity": severity,
            "label": label,
            "category": category,
            "owner": owner,
            "title": title,
            "observed_fact": observed_fact,
            "evidence": evidence or [],
            "impact": impact,
            "recommended_fix": recommended_fix,
            "blocks": blocks,
            "gate": gate,
            "fix_path": fix_path or ((evidence or ["task"])[0] if evidence else "task"),
        }
        self.items.append(item)
        return item

    def by_severity(self, *sevs):
        return [f for f in self.items if f["severity"] in sevs]


# --------------------------------------------------------------------------
# zip extraction + task discovery
# --------------------------------------------------------------------------

def extract_zip(zip_path, dest):
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.namelist():
            if "__MACOSX" in member or member.endswith("/.DS_Store"):
                continue
            zf.extract(member, dest)


def find_task_dir(root):
    if (root / "task.toml").is_file():
        return root
    for child in sorted(root.iterdir(), key=natural_key):
        if child.is_dir() and (child / "task.toml").is_file():
            return child
    for child in sorted(root.rglob("task.toml")):
        return child.parent
    return root


# --------------------------------------------------------------------------
# extra check 1: CRLF / BOM byte scan (Layer 0.0 / 0.0b)
# --------------------------------------------------------------------------

def scan_crlf_bom(task_dir, findings):
    bom_files, crlf_files = [], []
    for path in sorted(task_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_EXTS:
            continue
        raw = read_bytes(path)
        if not raw:
            continue
        rp = rel(path, task_dir)
        if raw.startswith(b"\xef\xbb\xbf"):
            bom_files.append(rp)
        if b"\r\n" in raw:
            crlf_files.append(rp)
    if bom_files:
        findings.add("P0", "judge", "UTF-8 BOM present in packaged files",
                     label="packaging", observed_fact=f"{len(bom_files)} file(s) start with EF BB BF: "
                     + ", ".join(bom_files[:15]),
                     evidence=bom_files[:15], impact="Some JSON parsers reject BOM; Harbor portal crashes on BOM.",
                     recommended_fix="Strip the BOM (save as UTF-8 without BOM) before zipping.",
                     gate="format", fix_path=bom_files[0] if bom_files else "task", blocks="rework")
    if crlf_files:
        findings.add("P0", "judge", "CRLF (\\r\\n) line endings in packaged files",
                     label="packaging", observed_fact=f"{len(crlf_files)} file(s) contain CRLF: "
                     + ", ".join(crlf_files[:15]),
                     evidence=crlf_files[:15], impact="Harbor portal crashes on CRLF; shell scripts may fail in Linux containers.",
                     recommended_fix="Convert all files to LF before zipping (dos2unix / editor LF setting).",
                     gate="format", fix_path=crlf_files[0] if crlf_files else "task", blocks="rework")


# --------------------------------------------------------------------------
# extra check 2: gold derivability heuristics (Layer 10a)
# --------------------------------------------------------------------------

def _one_word_diff(a, b):
    wa, wb = words_of(a), words_of(b)
    if abs(len(wa) - len(wb)) > 1:
        return False
    if len(wa) == len(wb):
        return sum(1 for x, y in zip(wa, wb) if x != y) == 1
    longer, shorter = (wa, wb) if len(wa) > len(wb) else (wb, wa)
    i = j = diff = 0
    while i < len(longer) and j < len(shorter):
        if longer[i] == shorter[j]:
            i += 1
            j += 1
        else:
            diff += 1
            i += 1
            if diff > 1:
                return False
    return True


def check_gold_derivability(task_dir, findings):
    input_dir = task_dir / "environment" / "input"
    if input_dir.is_dir():
        placeholder_hits = []
        for p in sorted(input_dir.rglob("*")):
            if not p.is_file() or p.suffix.lower() not in (TEXT_EXTS | PROSE_EXTS):
                continue
            text = read_text(p)
            if PLACEHOLDER.search(text):
                # Skip spec/format files where "placeholder" labels examples, not data
                if p.name in ("submission_format.md",):
                    continue
                placeholder_hits.append(rel(p, task_dir))
        if placeholder_hits:
            findings.add("P1", "judge", "placeholder/synthetic wording in agent-visible input data",
                         label="realism", observed_fact=f"{len(placeholder_hits)} file(s) contain placeholder markers: "
                         + ", ".join(placeholder_hits[:10]),
                         evidence=placeholder_hits[:10], impact="Synthetic/placeholder data makes the task benchmark-shaped and may not yield a defensible gold.",
                         recommended_fix="Replace placeholder text with realistic content.",
                         gate="gold_derivability", fix_path="environment/input/")

    sol = task_dir / "solution" / "files"
    if not sol.is_dir():
        return

    for csv_path in sorted(sol.glob("*.csv")):
        try:
            with csv_path.open(encoding="utf-8-sig", newline="") as fh:
                rows = list(csv.DictReader(fh))
        except (OSError, csv.Error):
            continue
        if not rows:
            continue
        cols = [c for c in rows[0].keys() if c]
        verdict_cols = [c for c in cols if VERDICT_COL.match(c)]
        text_cols = [c for c in cols if TEXT_COL.match(c)]
        if not verdict_cols or not text_cols:
            continue
        rp = rel(csv_path, task_dir)
        for tcol in text_cols:
            for vcol in verdict_cols:
                groups = defaultdict(set)
                members = defaultdict(list)
                for r in rows:
                    key = normalize_ws(str(r.get(tcol, "")))
                    val = normalize_ws(str(r.get(vcol, "")))
                    if not key or not val:
                        continue
                    groups[key].add(val)
                    members[(key, val)].append(r)
                for key, vals in groups.items():
                    if len(vals) > 1:
                        findings.add("P0", "judge",
                                     f"self-contradictory gold: identical '{tcol}' yields different '{vcol}' in {csv_path.name}",
                                     label="grading_gap", observed_fact=f"{key[:120]!r} -> {sorted(vals)}",
                                     evidence=[rp],
                                     impact="Identical inputs get different gold verdicts; the task is unsolvable as written.",
                                     recommended_fix="Make the gold consistent or disclose the distinction in instruction.md.",
                                     gate="gold_derivability", fix_path=rp, blocks="rework")
                if len(rows) <= 600:
                    seen = set()
                    keys = [normalize_ws(str(r.get(tcol, ""))) for r in rows]
                    vals = [normalize_ws(str(r.get(vcol, ""))) for r in rows]
                    for i in range(len(rows)):
                        for j in range(i + 1, len(rows)):
                            if vals[i] == vals[j] or not vals[i] or not vals[j]:
                                continue
                            if _one_word_diff(keys[i], keys[j]):
                                pair = (i, j)
                                if pair in seen:
                                    continue
                                seen.add(pair)
                                findings.add("P0", "judge",
                                             f"hair-split distinction in {csv_path.name}: one word changes the '{vcol}' verdict",
                                             label="grading_gap",
                                             observed_fact=f"row {i+1} ({vals[i]!r}) vs row {j+1} ({vals[j]!r}); texts differ by one word",
                                             evidence=[rp],
                                             impact="A single-word difference flips the verdict but the instruction does not disclose it.",
                                             recommended_fix="Disclose the distinction in instruction.md or remove the hair-split from the gold.",
                                             gate="gold_derivability", fix_path=rp, blocks="rework")
                                break


# --------------------------------------------------------------------------
# extra check 3: trajectory freshness (Layer 10c / 10g / 10.13-10.15, 10.24)
# --------------------------------------------------------------------------

def _extract_counts(obj):
    out = {}

    def walk(v):
        if isinstance(v, dict):
            for k, val in v.items():
                if isinstance(val, bool):
                    pass
                elif isinstance(val, (int, float)) and COUNT_KEY.search(str(k)):
                    out[str(k).lower()] = val
                walk(val)
        elif isinstance(v, list):
            for x in v:
                walk(x)
    walk(obj)
    return out


def _count_csv_rows(path):
    try:
        with path.open(encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.reader(fh))
        return max(0, len(rows) - 1)
    except (OSError, csv.Error):
        return None


def _check_one_trajectory(traj_path, label, gold_counts, csv_counts, sol, task_dir, findings):
    if not traj_path.is_file():
        return
    traj = load_json(traj_path)
    traj_counts = _extract_counts(traj) if traj is not None else {}
    raw = read_text(traj_path)
    mismatches = []
    for k, v in gold_counts.items():
        if k in traj_counts and traj_counts[k] != v:
            mismatches.append(f"{k}: trajectory={traj_counts[k]} vs gold={v}")
    for name, n in csv_counts.items():
        csvp = sol / name
        try:
            header = csvp.read_text(encoding="utf-8-sig", errors="replace").splitlines()[0]
        except (OSError, IndexError):
            continue
        idx = raw.find(header)
        if idx < 0:
            continue
        seg = raw[idx:idx + 200000]
        seg_lines = seg.splitlines()
        ncols = header.count(",") + 1
        embedded = 0
        for ln in seg_lines[1:]:
            if not ln.strip():
                break
            if ln.count(",") + 1 != ncols and not re.match(r"^[\w\s,.\-]+$", ln):
                break
            embedded += 1
            if embedded > n * 3 + 5:
                break
        if 0 < embedded != n:
            mismatches.append(f"{name}: trajectory embeds {embedded} data rows vs gold {n}")
    if mismatches:
        rp = rel(traj_path, task_dir)
        findings.add("P0", "judge", f"{label} embedded counts differ from the current gold",
                     label="evidence", observed_fact="; ".join(mismatches[:8]),
                     evidence=[rp],
                     impact="The shipped trajectory is stale; it does not match solution/files. Reviewers and Oracle provenance will read the wrong numbers.",
                     recommended_fix="Re-run the oracle / regenerate the trajectory so embedded counts match the current gold.",
                     gate="trajectory_freshness", fix_path=rp, blocks="rework")


def check_trajectory_freshness(task_dir, findings):
    sol = task_dir / "solution" / "files"
    gold_results = load_json(sol / "results.json") if (sol / "results.json").is_file() else None
    gold_counts = _extract_counts(gold_results) if isinstance(gold_results, dict) else {}
    csv_counts = {}
    if sol.is_dir():
        for p in sol.glob("*.csv"):
            n = _count_csv_rows(p)
            if n is not None:
                csv_counts[p.name] = n
    if not gold_counts and not csv_counts:
        return
    candidates = [
        (task_dir / "solution" / "golden_trajectory.json", "golden_trajectory.json"),
    ]
    oracle_traj = task_dir / "evaluations" / "oracle" / "agent" / "trajectory.json"
    if oracle_traj.is_file():
        candidates.append((oracle_traj, "oracle trajectory"))
    for traj_path, label in candidates:
        _check_one_trajectory(traj_path, label, gold_counts, csv_counts, sol, task_dir, findings)


# --------------------------------------------------------------------------
# extra check 4: review.csv count claims vs the ACTUAL gold (Layer 10g / 10.22)
# --------------------------------------------------------------------------

def check_review_csv_vs_gold(task_dir, findings):
    rc = task_dir / "review.csv"
    if not rc.is_file():
        return
    sol = task_dir / "solution" / "files"
    gold_results = load_json(sol / "results.json") if (sol / "results.json").is_file() else None
    gold_counts = _extract_counts(gold_results) if isinstance(gold_results, dict) else {}
    csv_counts = {}
    if sol.is_dir():
        for p in sol.glob("*.csv"):
            n = _count_csv_rows(p)
            if n is not None:
                csv_counts[p.stem] = n
    # Also count the number of verifiers from the spec
    verifier_count = None
    spec = load_json(task_dir / "tests" / "verifier.json")
    if spec and isinstance(spec.get("verifiers"), list):
        verifier_count = len(spec["verifiers"])
    try:
        with rc.open(encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))
    except (OSError, csv.Error):
        return
    mismatches = []
    gold_targets = list(gold_counts.items()) + list(csv_counts.items())
    gold_values = {actual for _, actual in gold_targets}
    if verifier_count is not None:
        gold_values.add(verifier_count)
    for row in rows:
        blob = " ".join(str(v or "") for v in row.values())
        label = str(row.get("review_check") or row.get("check") or "?")
        for m in re.finditer(r"\b(\d{2,5})\s+(?:deterministic\s+)?(?:checks|verifiers|lines|rows|items|findings|entries)\b", blob, re.I):
            claimed = int(m.group(1))
            if claimed not in gold_values:
                # Skip if preceded by descriptive context (Added N, N trap, N new, N semantic)
                start = max(0, m.start() - 40)
                context = blob[start:m.start()].lower()
                if any(w in context for w in ("added ", "trap", "new ", "semantic", "fixed ", "syn")):
                    continue
                mismatches.append(f"{label}: claims {claimed} — does not match any gold value ({sorted(gold_values)}")
    if mismatches:
        findings.add("P2", "judge", "review.csv count claims do not match the actual gold",
                     label="packaging", observed_fact="; ".join(dict.fromkeys(mismatches))[:600],
                     evidence=["review.csv"],
                     impact="The worksheet reports numbers that disagree with the shipped gold; reviewers read stale counts.",
                     recommended_fix="Update review.csv counts to match the actual solution/files gold.",
                     gate="review_csv", fix_path="review.csv")


# --------------------------------------------------------------------------
# extra check 5: /tests lock in Dockerfile (Layer 1.2 / 5.28)
# --------------------------------------------------------------------------

def check_tests_lock_dockerfile(task_dir, findings):
    df = task_dir / "environment" / "Dockerfile"
    if not df.is_file():
        return
    text = read_text(df)
    exposed = []
    for line in text.splitlines():
        m = DOCKER_COPY.match(line)
        if not m:
            continue
        parts = m.group(1).split()
        if len(parts) < 2:
            continue
        dst = parts[-1]
        for src in parts[:-1]:
            if re.search(r"(^|/)(tests|solution|verifier\.json|manifest\.json|golden|rubric\.toml|evaluations)", src) \
               or re.search(r"/tests/?$|verifier\.json|manifest\.json", dst):
                exposed.append({"source": src, "destination": dst})
    if exposed:
        findings.add("P0", "judge", "Dockerfile copies tests/solution/verifier into the agent-visible image (/tests lock broken)",
                     label="integrity", observed_fact=json.dumps(exposed[:6]),
                     evidence=["environment/Dockerfile"],
                     impact="The agent can read the grader or the answer key directly.",
                     recommended_fix="Remove the COPY; keep tests/ and solution/ outside /app so the agent cannot reach them.",
                     gate="golden_isolation", fix_path="environment/Dockerfile", blocks="rework")


# --------------------------------------------------------------------------
# extra check 5b: /tests lock breaks verifier (P0 — causes RewardFileNotFoundError)
# --------------------------------------------------------------------------

def check_tests_lock_breaks_verifier(task_dir, findings):
    """Detect chmod 700 /tests in Dockerfile that breaks test.sh when run as non-root."""
    df = task_dir / "environment" / "Dockerfile"
    test_sh = task_dir / "tests" / "test.sh"
    if not df.is_file():
        return
    df_text = read_text(df)
    test_text = read_text(test_sh) if test_sh.is_file() else ""

    # Check if Dockerfile locks /tests
    locks_tests = bool(re.search(r"chmod\s+(700|000|770)\s+/tests", df_text))
    if not locks_tests:
        return

    # Check if test.sh tries to restore access
    restores_in_test = bool(re.search(r"chmod\s+\d+\s+/tests", test_text))

    # Check last USER directive in Dockerfile
    user_lines = [m.group(1) for m in re.finditer(r"^\s*USER\s+(\S+)", df_text, re.I | re.M)]
    last_user = user_lines[-1] if user_lines else "root"
    is_non_root = last_user.lower() not in ("root", "0", "")

    if restores_in_test and is_non_root:
        findings.add("P0", "judge",
                     "Dockerfile locks /tests (chmod 700) but test.sh runs as non-root user — chmod restore in test.sh will FAIL, verifier crashes, no reward file written",
                     label="environment",
                     observed_fact=f"Dockerfile: chmod 700 /tests; test.sh: chmod restore; last USER: {last_user} (non-root). "
                                  f"Harbor runs test.sh as the agent user ({last_user}), not root, so chmod 755 /tests fails. "
                                  f"pytest cannot read /tests/test_outputs.py -> crash -> RewardFileNotFoundError.",
                     evidence=["environment/Dockerfile", "tests/test.sh"],
                     impact="Oracle and all GLM trials die before grading. Portal error: 'RewardFileNotFoundError: No reward file found'. "
                            "This is a P0 blocker — the task cannot be graded at all.",
                     recommended_fix="Remove the 'chmod 700 /tests' line from the Dockerfile. "
                                    "The /tests reward-hacking finding is theoretical (GLM 0/4 proves no cheating). "
                                    "Dismiss it as a false positive on the portal instead of breaking the verifier.",
                     gate="environment", fix_path="environment/Dockerfile", blocks="reject")
    elif locks_tests and not restores_in_test:
        findings.add("P0", "judge",
                     "Dockerfile locks /tests (chmod 700) but test.sh has no restore command — verifier cannot read /tests",
                     label="environment",
                     observed_fact="Dockerfile: chmod 700 /tests; test.sh: no chmod restore found. "
                                  "pytest cannot read /tests/test_outputs.py -> crash -> no reward file.",
                     evidence=["environment/Dockerfile", "tests/test.sh"],
                     impact="Oracle and all GLM trials die before grading.",
                     recommended_fix="Remove the 'chmod 700 /tests' line from the Dockerfile, "
                                    "or add 'chmod 755 /tests' at the top of test.sh (only works if test.sh runs as root).",
                     gate="environment", fix_path="environment/Dockerfile", blocks="reject")


# --------------------------------------------------------------------------
# extra check 5c: test.sh requires root but Dockerfile drops to non-root (P0)
# --------------------------------------------------------------------------

def check_testsh_root_commands(task_dir, findings):
    """Detect commands in test.sh that require root when run as non-root user."""
    df = task_dir / "environment" / "Dockerfile"
    test_sh = task_dir / "tests" / "test.sh"
    if not df.is_file() or not test_sh.is_file():
        return
    df_text = read_text(df)
    test_text = read_text(test_sh)

    # Get last USER
    user_lines = [m.group(1) for m in re.finditer(r"^\s*USER\s+(\S+)", df_text, re.I | re.M)]
    last_user = user_lines[-1] if user_lines else "root"
    if last_user.lower() in ("root", "0", ""):
        return  # running as root, no issue

    # Check for root-only commands in test.sh
    root_cmds = []
    for line in test_text.splitlines():
        line_stripped = line.strip()
        if line_stripped.startswith("#"):
            continue
        # chmod/chown on system dirs
        if re.match(r"(chmod|chown)\s+\d+\s+/(tests|app|usr|opt|var|etc)", line_stripped):
            root_cmds.append(line_stripped)
        # apt-get, pip install, etc.
        if re.match(r"(apt-get|apt|yum|dnf)\s", line_stripped):
            root_cmds.append(line_stripped)

    if root_cmds:
        findings.add("P0", "judge",
                     f"test.sh uses root-only commands but Dockerfile runs as non-root user ({last_user})",
                     label="environment",
                     observed=f"Root-only commands in test.sh: {root_cmds[:3]}; last USER in Dockerfile: {last_user}",
                     evidence=["tests/test.sh", "environment/Dockerfile"],
                     impact="test.sh fails when run as non-root user -> no reward file -> RewardFileNotFoundError.",
                     recommended_fix="Remove root-only commands from test.sh, or ensure test.sh runs as root.",
                     gate="environment", fix_path="tests/test.sh", blocks="reject")


# --------------------------------------------------------------------------
# extra check 6: host home paths in bundled trial metadata (Layer 5.24)
# --------------------------------------------------------------------------

def check_host_paths(task_dir, findings):
    eval_dir = task_dir / "evaluations"
    if not eval_dir.is_dir():
        return
    hits = []
    for p in sorted(eval_dir.rglob("*")):
        if not p.is_file() or p.name not in ("result.json", "config.json", "lock.json"):
            continue
        if HOST_PATH.search(read_text(p)):
            hits.append(rel(p, task_dir))
    if hits:
        findings.add("P2", "judge", "host home paths in bundled trial metadata",
                     label="packaging", observed_fact=", ".join(hits[:10]),
                     evidence=hits[:10],
                     impact="Personal paths leak into the submit package and may break reproducibility.",
                     recommended_fix="Replace /Users/<name>, C:\\Users\\<name>, /home/<name> with /workspace in result.json, config.json and lock.json.",
                     gate="packaging", fix_path="evaluations/")


# --------------------------------------------------------------------------
# extra check 7: D1-D5 verifier-defect linter (Layer 8)
# --------------------------------------------------------------------------

def _parse_spec_checks(data):
    checks, scoring = [], {}
    if not isinstance(data, dict):
        return checks, scoring
    if isinstance(data.get("scoring"), dict):
        scoring = data["scoring"]
    configs = None
    for key in ("verifiers", "verifier_configs", "checks"):
        if isinstance(data.get(key), list):
            configs = data[key]
            break
    if not configs:
        return checks, scoring
    for i, c in enumerate(configs):
        if not isinstance(c, dict):
            continue
        assertion = c.get("assertion") if isinstance(c.get("assertion"), dict) else {}
        det = assertion.get("deterministic") if isinstance(assertion.get("deterministic"), dict) else {}
        src = c.get("source") if isinstance(c.get("source"), dict) else {}
        fcmd = src.get("file") if isinstance(src.get("file"), dict) else {}
        args = fcmd.get("arguments") if isinstance(fcmd.get("arguments"), dict) else {}
        comp = str(det.get("comparison") or c.get("comparison") or c.get("op") or "")
        expected = assertion.get("expected", c.get("expected"))
        path = str(args.get("path") or c.get("path") or "")
        ftype = str(fcmd.get("type") or c.get("source_type") or "")
        kind = str(c.get("verifier_type") or c.get("type") or assertion.get("type") or "")
        is_llm = assertion.get("type") == "rubric" or bool(assertion.get("rubric")) or "llm" in kind.lower() or "judge" in kind.lower()
        checks.append({
            "name": str(c.get("name") or c.get("id") or f"check:{i}"),
            "comparison": comp,
            "expected": expected,
            "path": path,
            "file_type": ftype,
            "kind": "llm" if is_llm else ("deterministic" if det or expected is not None else kind),
            "definition": c,
        })
    return checks, scoring


def _is_prose(check):
    return (check["file_type"] in ("md", "txt", "text")
            or check["path"].endswith((".md", ".txt", ".rst", ".markdown")))


def run_d1_d5_linter(task_dir, findings):
    spec_path = task_dir / "tests" / "verifier.json"
    if not spec_path.is_file():
        spec_path = task_dir / "tests" / "manifest.json"
    spec = load_json(spec_path) if spec_path.is_file() else None
    checks, scoring = _parse_spec_checks(spec) if spec is not None else ([], {})

    def add_lint(linter_id, sev, title, **kw):
        psev = "P1" if sev == "sev1" else "P2"
        kw.setdefault("label", "grading_gap")
        kw.setdefault("gate", f"d1d5:{linter_id}")
        kw.setdefault("fix_path", str(spec_path.relative_to(task_dir)) if spec_path.is_file() else "tests/")
        findings.add(psev, "d1d5", f"[{linter_id} {sev}] {title}", **kw)

    regex_checks = [c for c in checks
                    if c["comparison"] in ("regex_match", "not_regex_match")
                    and isinstance(c["expected"], str) and _is_prose(c)]

    for c in regex_checks:
        exp = c["expected"]
        if re.search(r"\{\d{2,}\}", exp) and len(tokens_of(exp)) < 2:
            add_lint("D1", "sev2",
                     f"prose check {c['name']} uses a length-only quantifier with no required content words",
                     observed_fact=f"regex: {exp[:120]}",
                     evidence=[rel(spec_path, task_dir)],
                     recommended_fix="Replace with an LLM rubric on content, or require substantive tokens.")
        if exp.count("(?=") >= 2:
            add_lint("D1", "sev2",
                     f"prose check {c['name']} uses >= 2 independent lookaheads (keyword-set membership, order/coherence ungraded)",
                     observed_fact=f"regex: {exp[:120]}",
                     evidence=[rel(spec_path, task_dir)],
                     recommended_fix="Replace with an LLM rubric or bind tokens to assertions.")
        if ".*" in exp or re.search(r"\.\{0,\d*\}", exp):
            add_lint("D1", "sev2",
                     f"prose check {c['name']} uses .* / .{{0,N}} slack letting arbitrary filler satisfy it",
                     observed_fact=f"regex: {exp[:120]}",
                     evidence=[rel(spec_path, task_dir)],
                     recommended_fix="Replace with an LLM rubric on meaning.")
        # D6: unescaped dots in numeric alternatives (e.g. 197.0 matches 19700)
        num_alts = re.findall(r"\((\d+)\.(\d+)\)", exp)
        for full_int, frac in num_alts:
            if not re.search(r"\\\.", exp):
                add_lint("D6", "sev2",
                         f"prose check {c['name']} has unescaped dot in {full_int}.{frac} — matches {full_int}{frac[0]} or {full_int} {frac}",
                         observed_fact=f"regex contains {full_int}.{frac} (unescaped dot matches any char)",
                         evidence=[rel(spec_path, task_dir)],
                         recommended_fix=f"Escape the dot: use {full_int}\\.{frac} instead of {full_int}.{frac}")
                break

    by_file = defaultdict(list)
    for c in regex_checks:
        if ".*" in c["expected"] or "(?=" in c["expected"] or re.search(r"\{", c["expected"]):
            continue
        if len(tokens_of(c["expected"])) >= 1:
            by_file[Path(c["path"]).name].append(c["name"])
    for fname, names in by_file.items():
        if len(names) >= 3:
            add_lint("D1", "sev2",
                     f">= 3 bare keyword/ID regex checks on one prose file ({fname}): {', '.join(names[:6])}",
                     observed_fact=f"{len(names)} presence-only checks on {fname}",
                     evidence=[rel(spec_path, task_dir)],
                     recommended_fix="Grade the claim, not mere keyword presence.")

    df = task_dir / "environment" / "Dockerfile"
    if df.is_file():
        dft = read_text(df)
        user_match = None
        for line in dft.splitlines():
            m = DOCKER_USER.match(line)
            if m:
                user_match = m.group(1)
        if not user_match or user_match.lower() in ("root", "0"):
            add_lint("D2", "sev3", "Dockerfile runs the agent as root (no non-root USER directive)",
                     label="environment", gate="d1d5:D2", fix_path="environment/Dockerfile",
                     observed_fact=f"USER={user_match or 'root'}",
                     evidence=["environment/Dockerfile"],
                     recommended_fix="Add a non-root USER directive (e.g. USER app).")

    spec_text = read_text(spec_path) if spec_path.is_file() else ""
    harness_files = []
    tests_dir = task_dir / "tests"
    if tests_dir.is_dir():
        harness_files = [p for p in tests_dir.rglob("*") if p.is_file() and p.suffix in (".py", ".sh", ".toml")]
    harness_text = "\n".join(read_text(p) for p in harness_files)
    has_judge_placeholder = "${JUDGE_MODEL}" in spec_text or "JUDGE_MODEL" in spec_text
    harness_resolves = "JUDGE_MODEL" in harness_text
    has_rubric = any(c["kind"] == "llm" for c in checks) or "rubric.toml" in spec_text.lower()
    model_literal = MODEL_ID.search(spec_text)
    if has_judge_placeholder and not harness_resolves:
        add_lint("D3", "sev3",
                 "config.models ships a ${JUDGE_MODEL} placeholder but no harness file reads/substitutes JUDGE_MODEL",
                 observed_fact="placeholder present, no resolver in tests/",
                 evidence=[rel(spec_path, task_dir)] + [rel(p, task_dir) for p in harness_files[:3]],
                 recommended_fix="Add a resolver that reads the injected JUDGE_MODEL env var, or pin a real model id.")
    if model_literal and not harness_resolves and has_rubric:
        add_lint("D3", "sev2",
                 f"config.models hard-pins {model_literal.group(1)} with no harness resolver and a rubric item exists",
                 observed_fact=f"literal {model_literal.group(1)} in spec; rubric present",
                 evidence=[rel(spec_path, task_dir)],
                 recommended_fix="Read the injected JUDGE_MODEL instead of hard-pinning a provider id.")

    test_out = task_dir / "tests" / "test_outputs.py"
    if test_out.is_file():
        to_text = read_text(test_out)
        uses_agent_fixture = bool(re.search(
            r"open\(\s*['\"]/(?:app|workspace)/|read_csv\(\s*['\"]/(?:app|workspace)/|"
            r"Path\(\s*['\"]/(?:app|workspace)/|expected\s*=\s*.*['\"]/(?:app|workspace)/",
            to_text))
        is_root = True
        if df.is_file():
            for line in read_text(df).splitlines():
                m = DOCKER_USER.match(line)
                if m and m.group(1).lower() not in ("root", "0"):
                    is_root = False
                    break
        if uses_agent_fixture and is_root:
            add_lint("D4", "sev3",
                     "test_outputs.py uses an agent-reachable path (/app/ or /workspace/) as grading ground truth and the container runs as root",
                     observed_fact="agent-reachable fixture + root user",
                     evidence=["tests/test_outputs.py", "environment/Dockerfile"],
                     recommended_fix="Move the fixture into /tests and run the container non-root.")

    weights = scoring.get("weights") if isinstance(scoring.get("weights"), (dict, list)) else None
    weight_map = {}
    if isinstance(weights, dict):
        weight_map = {str(k).lower(): float(v) for k, v in weights.items()
                      if isinstance(v, (int, float)) and not isinstance(v, bool)}
    elif isinstance(weights, list):
        for w in weights:
            if isinstance(w, dict) and isinstance(w.get("weight"), (int, float)):
                weight_map[str(w.get("axis") or w.get("name") or "").lower()] = float(w["weight"])
    flat = bool(scoring.get("flat_verifier_scoring"))
    sql_verifiers = scoring.get("sql_verifiers")
    sql_empty = (not sql_verifiers) or (isinstance(sql_verifiers, list) and not sql_verifiers)
    if weight_map.get("sql", 0) > 0 and sql_empty and not flat:
        add_lint("D5", "sev2",
                 "scoring advertises sql weight > 0 but sql_verifiers is empty and flat_verifier_scoring is off",
                 observed_fact=f"sql weight={weight_map.get('sql')}, sql_verifiers empty",
                 evidence=[rel(spec_path, task_dir)],
                 recommended_fix="Populate the sql axis or set its weight to 0.")
    state_snapshot = nested(scoring, "state", "snapshot", "mode") or nested(scoring, "state", "snapshot_mode")
    expected_diff = scoring.get("expected_diff")
    diff_empty = (not expected_diff) or (isinstance(expected_diff, (list, dict, str)) and not expected_diff)
    if weight_map.get("state", 0) > 0 and not state_snapshot and diff_empty:
        add_lint("D5", "sev2",
                 "scoring advertises state weight > 0 but no state.snapshot.mode and expected_diff is empty",
                 observed_fact=f"state weight={weight_map.get('state')}, no snapshot mode, empty diff",
                 evidence=[rel(spec_path, task_dir)],
                 recommended_fix="Populate the state axis or set its weight to 0.")


# --------------------------------------------------------------------------
# run the Harbor-Shannon QC engine
# --------------------------------------------------------------------------

def resolve_engine(custom):
    candidates = []
    if custom:
        candidates.append(Path(custom))
    env_engine = os.environ.get(ENV_ENGINE)
    if env_engine:
        candidates.append(Path(env_engine))
    candidates.append(Path(ENGINE_DEFAULT))
    for c in candidates:
        if c.is_file():
            return c
    return None


def run_engine(engine_path, task_dir, out_dir, no_model, timeout, log_fn):
    cmd = [sys.executable, str(engine_path), "--task", str(task_dir),
           "--output-dir", str(out_dir), "--quiet"]
    if no_model:
        cmd.append("--no-model")
    log_fn(f"running engine ({'no-model' if no_model else 'model'}) ...")
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"engine timed out after {timeout}s"}
    except OSError as exc:
        return {"ok": False, "error": f"engine launch failed: {exc}"}
    report_path = out_dir / "qc-report.json"
    if not report_path.is_file():
        tail = (proc.stderr or proc.stdout or "")[-1500:]
        return {"ok": False, "error": f"engine produced no qc-report.json. stderr tail:\n{tail}"}
    report = load_json(report_path)
    if not isinstance(report, dict):
        return {"ok": False, "error": "qc-report.json is not a JSON object"}
    return {"ok": True, "report": report, "returncode": proc.returncode,
            "stdout": proc.stdout, "stderr": proc.stderr}


def parse_engine_report(report):
    verdicts = report.get("verdicts") or {}
    findings = report.get("findings") or []
    return {
        "model_ran": bool(report.get("model_ran")),
        "qc_verdict": verdicts.get("qc_verdict"),
        "review_verdict": verdicts.get("review_verdict"),
        "task_quality_verdict": verdicts.get("task_quality_verdict"),
        "human_review_required": bool(verdicts.get("human_review_required")),
        "counts": verdicts.get("counts") or {},
        "components": verdicts.get("components") or {},
        "mode": report.get("mode"),
        "findings": findings,
        "gates": report.get("evaluation_gates") or {},
        "packaging": report.get("packaging") or [],
        "reward_hacking": report.get("reward_hacking") or {},
        "static_review": report.get("static_review"),
        "runs_review": report.get("runs_review"),
    }


# --------------------------------------------------------------------------
# merge + dedup
# --------------------------------------------------------------------------

_DEDUPE_TOPICS = {
    "golden_isolation": ("golden isolation", "copies tests", "copy tests", "/tests lock", "tests lock", "copies graders", "answer key"),
    "host_paths": ("host path", "host home", "anonymi"),
    "review_csv": ("review.csv", "worksheet"),
    "trajectory_freshness": ("trajectory", "embedded count", "stale"),
    "gold_derivability": ("self-contradict", "hair-split", "placeholder", "derivab"),
    "format": ("crlf", "bom", "line ending"),
    "d1d5": ("d1", "d2", "d3", "d4", "d5", "sev1", "sev2", "sev3"),
}


def _topics(finding):
    blob = " ".join([finding.get("title", ""), finding.get("observed_fact", ""),
                     " ".join(str(e) for e in finding.get("evidence", []))]).lower()
    return {t for t, needles in _DEDUPE_TOPICS.items() if any(n in blob for n in needles)}


def dedup_extra(extra_findings, engine_findings):
    pool = [(f, _topics(f)) for f in engine_findings if not f.get("duplicate_of")]
    for f in extra_findings:
        ftopics = _topics(f)
        keeper = None
        for other, otopics in pool:
            shared = ftopics & otopics
            if not shared:
                continue
            tshared = topic_words(f["title"]) & topic_words(other.get("title", ""))
            if tshared or (f.get("gate") and other.get("gate") == f.get("gate")):
                keeper = other
                break
        if keeper is not None:
            f["duplicate_of"] = keeper.get("id") or keeper.get("title", "")
            keeper.setdefault("also_flagged_by", []).append(f["id"])


def compute_verdict(findings, model_ran):
    live = [f for f in findings if not f.get("duplicate_of")]
    p0 = sum(1 for f in live if f["severity"] == "P0")
    p1 = sum(1 for f in live if f["severity"] == "P1")
    p2 = sum(1 for f in live if f["severity"] == "P2")
    info = sum(1 for f in live if f["severity"] == "INFO")
    if p0 or p1:
        verdict = "FAIL"
    elif (not model_ran) or p2:
        verdict = "NEEDS_REVIEW"
    else:
        verdict = "PASS"
    return verdict, p0, p1, p2, info


# --------------------------------------------------------------------------
# report rendering
# --------------------------------------------------------------------------

def render_report(task_name, zip_path, det, model, extra_findings, all_findings,
                  model_ran, verdict, p0, p1, p2, info, engine_path):
    lines = []
    bar = "=" * 70
    lines.append(bar)
    lines.append(f"  HARBOR-SHANNON TASK JUDGMENT  (judge.py v{VERSION})")
    lines.append(bar)
    lines.append(f"Task     : {task_name}")
    lines.append(f"Zip      : {zip_path}")
    lines.append(f"Engine   : {engine_path or '<not found>'}")
    lines.append("")
    det_state = "ran" if det and det.get("ok") else f"FAILED ({det.get('error','')[:120]})" if det else "skipped"
    det_verdict = det["qc_verdict"] if det and det.get("ok") else "n/a"
    det_counts = det["counts"] if det and det.get("ok") else {}
    lines.append(f"Deterministic stage : {det_state}  qc_verdict={det_verdict}  counts={det_counts}")
    if model is not None:
        if model.get("ok"):
            mc = model["report"]
            lines.append(f"Model stage         : ran  qc_verdict={mc.get('qc_verdict','n/a')}  "
                         f"review={mc.get('review_verdict','n/a')}  counts={mc.get('counts',{})}")
        else:
            lines.append(f"Model stage         : FAILED ({model.get('error','')[:120]})")
    else:
        key_set = bool(os.environ.get(ENV_KEY))
        lines.append(f"Model stage         : skipped ({'key not set' if not key_set else '--no-model'})")
    lines.append(f"Extra checks        : CRLF/BOM, gold-derivability, trajectory-freshness, "
                  f"review.csv-vs-gold, /tests-lock, host-paths, D1-D5 linter")
    lines.append("")
    lines.append(bar)
    if verdict == "FAIL":
        vlabel = "FAIL"
    elif verdict == "NEEDS_REVIEW":
        vlabel = "NEEDS_REVIEW"
    else:
        vlabel = "PASS"
    lines.append(f"  VERDICT: {vlabel}")
    lines.append(bar)
    lines.append(f"  P0: {p0}   P1: {p1}   P2: {p2}   INFO: {info}   (live, de-duplicated)")
    human_review = (verdict == "NEEDS_REVIEW") or (model is None) or (model is not None and not model.get("ok")) or not model_ran
    lines.append(f"  Human review required: {'yes' if human_review else 'no'}")
    if det and det.get("ok"):
        lines.append(f"  Engine review_verdict: {det.get('review_verdict','n/a')}")
    if model and model.get("ok"):
        lines.append(f"  Model  review_verdict: {model['report'].get('review_verdict','n/a')}")
    lines.append("")
    live = [f for f in all_findings if not f.get("duplicate_of")]
    order = {"P0": 0, "P1": 1, "P2": 2, "INFO": 3}
    live.sort(key=lambda f: (order.get(f["severity"], 4), str(f.get("source", "")), f["title"]))
    lines.append(f"  FINDINGS ({len(live)} live, {len(all_findings) - len(live)} duplicate)")
    lines.append("-" * 70)
    if not live:
        lines.append("  (no findings)")
    for f in live:
        sev = f["severity"]
        marker = "P0" if sev == "P0" else sev
        src = f.get("source", "?")
        fid = f.get("id", "?")
        title = f.get("title", "untitled")
        lines.append(f"[{marker}] [{fid}] ({f.get('label','?').replace('_',' ')}) {title}")
        where = ", ".join(str(e) for e in f.get("evidence", [])[:4]) or f.get("fix_path", "task")
        lines.append(f"    where : {where[:200]}")
        if f.get("observed_fact"):
            lines.append(f"    fact  : {str(f['observed_fact'])[:240]}")
        if f.get("impact"):
            lines.append(f"    impact: {str(f['impact'])[:200]}")
        fix = f.get("recommended_fix") or f.get("impact") or "(no fix recorded)"
        lines.append(f"    fix   : {str(fix)[:240]}")
        also = f.get("also_flagged_by")
        if also:
            lines.append(f"    also  : {', '.join(also)}")
    dupes = [f for f in all_findings if f.get("duplicate_of")]
    if dupes:
        lines.append("")
        lines.append(f"  DUPLICATES ({len(dupes)} - suppressed, merged into earlier findings)")
        for f in dupes:
            lines.append(f"    [{f.get('id')}] {f.get('title','')} -> dup of {f.get('duplicate_of')}")
    lines.append("")
    lines.append(bar)
    lines.append("Component verdicts:")
    if det and det.get("ok"):
        comps = det.get("components") or {}
        for k in ("deterministic", "static_model", "runs_model", "evidence_gates", "packaging", "review_csv", "reward_hacking"):
            v = comps.get(k)
            if v is not None:
                lines.append(f"  {k:18s}: {v}")
        gates = det.get("gates") or {}
        for g in ("difficulty", "solvability", "stability"):
            if g in gates and isinstance(gates[g], dict):
                lines.append(f"  gate {g:13s}: {gates[g].get('status','n/a')}")
        rh = det.get("reward_hacking") or {}
        if rh:
            lines.append(f"  reward_hacking     : {rh.get('verdict','n/a')} ({len(rh.get('flags',[]))} signals)")
    lines.append(bar)
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def parse_args(argv):
    p = argparse.ArgumentParser(description="One-command Harbor-Shannon task judge: extracts a zip, runs the full QC engine (deterministic + model) plus extra checks, prints a single verdict.")
    p.add_argument("zip", type=Path, help="Path to the task .zip")
    p.add_argument("--engine", type=Path, help="Path to harbor_shannon_qc.py (default: Downloads/Harbor-Shannon-QC/harbor_shannon_qc.py or $JUDGE_ENGINE)")
    p.add_argument("--no-model", action="store_true", help="Skip the model QC stage (deterministic + extra checks only)")
    p.add_argument("--model-timeout", type=int, default=1800, help="Timeout in seconds for the model stage (default 1800)")
    p.add_argument("--det-timeout", type=int, default=60, help="Timeout in seconds for the deterministic stage (default 60)")
    p.add_argument("--keep", action="store_true", help="Keep the extracted task + qc-out dirs (for inspection)")
    p.add_argument("--stage", type=Path, help="Directory to extract into (default: a temp dir)")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    zip_path = args.zip.expanduser().resolve()
    if not zip_path.is_file():
        print(f"error: zip not found: {zip_path}", file=sys.stderr)
        return 2

    engine_path = resolve_engine(args.engine)
    if engine_path is None:
        log(f"warning: harbor_shannon_qc.py not found at default location or --engine; "
            f"engine stages will be skipped (extra checks still run)")

    if args.stage:
        stage = args.stage.expanduser().resolve()
        stage.mkdir(parents=True, exist_ok=True)
        cleanup = False
    else:
        stage = Path(tempfile.mkdtemp(prefix="judge_"))
        cleanup = not args.keep

    try:
        log(f"extracting {zip_path} -> {stage}")
        extract_zip(zip_path, stage)
        task_dir = find_task_dir(stage)
        log(f"task dir: {task_dir}")

        det = None
        model = None
        engine_findings = []

        if engine_path is not None:
            det_out = stage / "qc-det"
            det_out.mkdir(exist_ok=True)
            det_raw = run_engine(engine_path, task_dir, det_out, no_model=True,
                                 timeout=args.det_timeout, log_fn=log)
            det = det_raw
            if det_raw.get("ok"):
                parsed = parse_engine_report(det_raw["report"])
                det = parsed
                det["ok"] = True
                engine_findings = list(parsed["findings"])
                log(f"deterministic: qc_verdict={parsed.get('qc_verdict')} "
                    f"counts={parsed.get('counts')} findings={len(parsed['findings'])}")
            else:
                log(f"!! deterministic engine failed: {det_raw.get('error','')[:200]}")

            run_model = (not args.no_model) and bool(os.environ.get(ENV_KEY))
            if run_model:
                model_out = stage / "qc-model"
                model_out.mkdir(exist_ok=True)
                model_raw = run_engine(engine_path, task_dir, model_out, no_model=False,
                                        timeout=args.model_timeout, log_fn=log)
                model = model_raw
                if model_raw.get("ok"):
                    mparsed = parse_engine_report(model_raw["report"])
                    model = mparsed
                    model["ok"] = True
                    engine_findings = list(mparsed["findings"])
                    log(f"model: qc_verdict={mparsed.get('qc_verdict')} "
                        f"review={mparsed.get('review_verdict')} counts={mparsed.get('counts')} "
                        f"findings={len(mparsed['findings'])}")
                else:
                    log(f"!! model engine failed: {model_raw.get('error','')[:200]}")
            else:
                if not args.no_model and not os.environ.get(ENV_KEY):
                    log(f"model stage skipped: {ENV_KEY} not set (set it to run the model review)")

        extra = Findings()
        scan_crlf_bom(task_dir, extra)
        check_gold_derivability(task_dir, extra)
        check_trajectory_freshness(task_dir, extra)
        check_review_csv_vs_gold(task_dir, extra)
        check_tests_lock_dockerfile(task_dir, extra)
        check_tests_lock_breaks_verifier(task_dir, extra)
        check_testsh_root_commands(task_dir, extra)
        check_host_paths(task_dir, extra)
        run_d1_d5_linter(task_dir, extra)
        log(f"extra checks: {len(extra.items)} findings")

        dedup_extra(extra.items, engine_findings)
        all_findings = list(engine_findings) + list(extra.items)

        model_ran = bool(model and model.get("ok"))
        verdict, p0, p1, p2, info = compute_verdict(all_findings, model_ran)

        task_name = task_dir.name
        report = render_report(task_name, str(zip_path), det, model, extra.items,
                                all_findings, model_ran, verdict, p0, p1, p2, info, engine_path)
        print(report)

        report_path = stage / "judge-report.json"
        summary = {
            "tool": "judge.py", "version": VERSION, "task": task_name, "zip": str(zip_path),
            "verdict": verdict, "counts": {"P0": p0, "P1": p1, "P2": p2, "INFO": info},
            "model_ran": model_ran, "human_review_required": verdict == "NEEDS_REVIEW" or not model_ran,
            "engine_available": engine_path is not None,
            "engine_findings": len(engine_findings), "extra_findings": len(extra.items),
            "findings": all_findings,
        }
        try:
            report_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
            log(f"full report written to {report_path}")
        except OSError as exc:
            log(f"could not write report: {exc}")

        if cleanup:
            try:
                import shutil
                shutil.rmtree(stage, ignore_errors=True)
            except Exception:
                pass

        return 0 if verdict == "PASS" else 1
    finally:
        pass


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (KeyboardInterrupt, BrokenPipeError):
        sys.exit(130)
