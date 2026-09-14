#!/usr/bin/env python3
"""Deterministic linter for the four task-bundle defect families that the
2026-09-08 client audit (Batches 1/2/3, 94 human-review FAILs) confirmed our QC
was missing.

It reads only task bytes — a ``verifier.json`` plus its sibling ``environment/``
and ``tests/`` files — costs nothing, and calls no model. Point it at a task
directory, a single task ``.zip``, a delivery ``.zip`` containing many task zips,
or a folder of any of those.

The four families, each grounded in a defect the client marked a true positive:

    D1 prose_regex_grading   a prose/memo deliverable graded by ``regex_match``
                             whose pattern is length-only (``{200}``), a
                             token-soup of ``(?=.*a)(?=.*b)`` lookaheads, or
                             ``.*`` / ``.{0,N}`` slack — a keyword-stuffed stub
                             passes, substance is never graded.
    D2 root_container        ``environment/Dockerfile`` has no ``USER`` so the
                             agent runs as root and can overwrite the read-only
                             grading fixtures the verifier trusts (reward hack).
    D3 judge_model_wiring    ``verifier.json`` ``config.models`` is an
                             unsubstituted ``${JUDGE_MODEL}`` placeholder or a
                             hard-pinned provider id while the harness is meant
                             to inject the model — the rubric item 404s / is
                             mis-scored on the client battery.
    D4 fixture_overwritable  the verifier reads a grading fixture from a path the
                             agent workspace can write (``/app/...`` etc.),
                             independent of the container user.
    D5 inert_scoring_axis    a Harbor ``manifest.json`` advertises a scoring
                             weight for an axis that cannot score — ``sql`` > 0
                             with ``sql_verifiers: []``, or ``state`` > 0 with an
                             empty ``expected_diff`` — so the weight silently
                             collapses onto the LLM rubric (fiction weights).

Both task-bundle formats are understood: the flat ``tests/verifier.json``
(rl_world_verifiers) and the Harbor ``tests/manifest.json`` whose verifier items
are nested under ``verifier_configs[].verifier_spec.verifiers[]`` with a separate
``rubric.toml``.

Findings carry a 0-3 severity on the same scale the rest of pre-QC uses, so this
can feed the same verdict overlay. Exit code is non-zero when any finding at or
above ``--fail-severity`` (default 2) is present, so it drops straight into CI.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable


# ── defect family registry ──────────────────────────────────────────────────
FAMILIES = {
    "D1": "prose_regex_grading",
    "D2": "root_container",
    "D3": "judge_model_wiring",
    "D4": "fixture_overwritable",
    "D5": "inert_scoring_axis",
}

# A source path grades *prose* (a memo / note / explanation) rather than a
# machine artifact. Regex on prose is where "token soup passes" lives.
PROSE_PATH = re.compile(r"\.(md|markdown|txt|rst)$", re.I)
PROSE_NAME = re.compile(
    r"memo|explain|explanation|substant|narrative|rationale|justif|"
    r"notes?_|cover|reason|writeup|write_up|summary_note",
    re.I,
)

# Structured-data and code targets. A regex/equals check on these is legitimate
# (JSON/CSV schema keys, grading a .py script's output), NOT the reward-hackable
# prose grading D1 is about, so they are excluded even when the name looks memo-ish
# or the verifier reads them via extract_text.
STRUCTURED_PATH = re.compile(
    r"\.(json|csv|tsv|ya?ml|xml|jsonl|ndjson|py|ipynb|sql|sh|js|ts|toml|ini|cfg)$",
    re.I,
)

# Prose-friendly source declarations in rl_world_verifiers.
PROSE_SOURCE_TYPES = {"md", "markdown", "text", "txt"}

# Regex features that make a prose check reward-hackable.
LENGTH_ONLY = re.compile(r"\{\s*\d+\s*(?:,\s*\d*\s*)?\}")   # {200} or {50,}
LOOKAHEAD = re.compile(r"\(\?=")                              # (?=.*a)
WILDCARD_SLACK = re.compile(r"\.\*|\.\{\s*\d*\s*,\s*\d+\s*\}")  # .*  or .{0,600}
# A "real" content token: a literal alphabetic word >=4 chars once regex
# metacharacter escapes are stripped. If a prose pattern has none, it grades
# form, not content.
WORD_TOKEN = re.compile(r"[A-Za-z]{4,}")
# Regex "structure" that means the pattern grades more than a bare literal
# appearing somewhere. If a prose pattern has NONE of these it is a plain
# keyword / ID-presence check (does token X occur at all).
REGEX_STRUCTURE = re.compile(r"\.\*|\.\+|\.\{|\(\?=|\(\?!|\{\s*\d+")
# How many bare keyword/ID-presence regex items on ONE prose file before we call
# it a decomposed token-soup (the memo is graded only by "were the IDs listed").
BARE_PRESENCE_CLUSTER = 3

# Judge model placeholders that must be substituted before shipping.
PLACEHOLDER = re.compile(r"\$\{[^}]+\}|\{\{[^}]+\}\}|<[A-Z_]+>|__[A-Z_]+__")
# A concrete provider/model id — a hard pin.
CONCRETE_MODEL = re.compile(r"[a-z0-9_.-]+/[A-Za-z0-9][\w.\-]*", re.I)

# Fixture paths a verifier might read that also sit in the agent's writable tree.
AGENT_WRITABLE_ROOTS = ("/app/", "app/", "./", "/workspace/", "workspace/")


@dataclass
class Finding:
    check_id: str
    family: str
    severity: int                 # 0-3
    title: str
    detail: str
    evidence: str = ""
    verifier: str = ""
    fixability: str = "fixable"   # fixable | structural
    # Origin of the finding: "bundle" for the shipped-bundle checks in this
    # module, "config" for the harness-config checks in preqc_checks. Lets
    # the report and decision bifurcate the two deterministic sources.
    source: str = "bundle"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TaskResult:
    task_id: str
    source: str                   # where the task was read from
    findings: list[Finding] = field(default_factory=list)
    features: dict[str, Any] = field(default_factory=dict)
    error: str = ""

    @property
    def max_severity(self) -> int:
        return max((f.severity for f in self.findings), default=0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "source": self.source,
            "max_severity": self.max_severity,
            "findings": [f.to_dict() for f in self.findings],
            "features": self.features,
            "error": self.error,
        }


# ── file-access abstraction ─────────────────────────────────────────────────
# A task can be a directory or a zip. Both expose the same read/list surface so
# the checks never care which they got.
class TaskFiles:
    """Read-only view over one task's files, backed by a dir or a zip."""

    def __init__(self, names: dict[str, Any], reader, source: str):
        # names maps a POSIX-relative path -> handle used by ``reader``
        self._names = names
        self._reader = reader
        self.source = source

    def list(self) -> list[str]:
        return list(self._names)

    def read(self, name: str) -> bytes:
        return self._reader(self._names[name])

    def read_text(self, name: str) -> str:
        return self.read(name).decode("utf-8", "replace")

    def find(self, suffix: str) -> str | None:
        # Prefer the shallowest match so tests/verifier.json wins over a nested
        # copy under environment/_app/.
        matches = [n for n in self._names if n.endswith(suffix)]
        matches.sort(key=lambda n: (n.count("/"), len(n)))
        return matches[0] if matches else None

    @classmethod
    def from_dir(cls, root: Path) -> "TaskFiles":
        names = {
            p.relative_to(root).as_posix(): p
            for p in root.rglob("*")
            if p.is_file()
        }
        return cls(names, lambda p: p.read_bytes(), str(root))

    @classmethod
    def from_zip_bytes(cls, raw: bytes, source: str) -> "TaskFiles":
        zf = zipfile.ZipFile(io.BytesIO(raw))
        names = {n: n for n in zf.namelist() if not n.endswith("/")}
        return cls(names, lambda n: zf.read(n), source)


# ── helpers ─────────────────────────────────────────────────────────────────

def _load_verifier(tf: TaskFiles) -> tuple[str | None, dict | None]:
    """Return (path, normalized spec) for either bundle format.

    The normalized spec always exposes ``verifiers`` (flat list of items) and
    ``config`` (judge model config). A Harbor manifest additionally keeps its raw
    body under ``_manifest`` so the inert-axis check can read scoring weights.
    """
    # Flat rl_world_verifiers format first.
    path = tf.find("tests/verifier.json") or tf.find("verifier.json")
    if path:
        try:
            spec = json.loads(tf.read_text(path))
            if isinstance(spec, dict):
                return path, spec
        except (json.JSONDecodeError, UnicodeError):
            return path, None

    # Harbor manifest format: prefer the shallowest, non-eval, non-_app copy.
    mpath = None
    for cand in sorted(
        (n for n in tf.list() if n.endswith("manifest.json")),
        key=lambda n: (("/evaluations/" in n), ("_app" in n), n.count("/"), len(n)),
    ):
        mpath = cand
        break
    if not mpath:
        return None, None
    try:
        manifest = json.loads(tf.read_text(mpath))
    except (json.JSONDecodeError, UnicodeError):
        return mpath, None
    if not isinstance(manifest, dict):
        return mpath, None

    merged: list[dict] = []
    config: dict = {}
    # Layout A: manifest.verifier_configs[].verifier_spec.verifiers[]
    for vc in manifest.get("verifier_configs", []) or []:
        if not isinstance(vc, dict):
            continue
        vs = vc.get("verifier_spec", {})
        if isinstance(vs, dict):
            for v in vs.get("verifiers", []) or []:
                if isinstance(v, dict):
                    merged.append(v)
            if isinstance(vs.get("config"), dict):
                config = vs["config"] or config
    # Layout B: manifest with a flat top-level verifiers[] list (some harbor tasks).
    for v in manifest.get("verifiers", []) or []:
        if isinstance(v, dict):
            merged.append(v)
    if not config and isinstance(manifest.get("config"), dict):
        config = manifest["config"]
    return mpath, {"verifiers": merged, "config": config, "_manifest": manifest}


def _verifier_items(spec: dict) -> list[dict]:
    items = spec.get("verifiers")
    return [v for v in items if isinstance(v, dict)] if isinstance(items, list) else []


def _source_path_and_type(v: dict) -> tuple[str, str]:
    """Return (path graded, declared source type) for a verifier item."""
    src = v.get("source", {})
    fdef = src.get("file", {}) if isinstance(src, dict) else {}
    stype = str(fdef.get("type", "")).lower()
    args = fdef.get("arguments", {}) if isinstance(fdef, dict) else {}
    path = ""
    if isinstance(args, dict):
        path = str(args.get("path", ""))
    return path, stype


def _is_prose_target(name: str, path: str, stype: str) -> bool:
    # A structured-data path is never prose, regardless of name/source type: a
    # key-presence lookahead on results.json is a legitimate schema check.
    if STRUCTURED_PATH.search(path):
        return False
    return bool(
        PROSE_PATH.search(path)
        or PROSE_NAME.search(name or "")
        or stype in PROSE_SOURCE_TYPES
    )


def _regex_comparison(v: dict) -> str | None:
    asrt = v.get("assertion", {})
    if not isinstance(asrt, dict) or asrt.get("type") != "deterministic":
        return None
    det = asrt.get("deterministic", {})
    if isinstance(det, dict) and det.get("comparison") == "regex_match":
        return str(asrt.get("expected", ""))
    return None


def _strip_regex_meta(pattern: str) -> str:
    # Drop escaped metacharacters and character classes so WORD_TOKEN only sees
    # literal alphabetic runs the author actually required.
    out = re.sub(r"\\[A-Za-z]", " ", pattern)          # \s \S \d \b ...
    out = re.sub(r"\[[^\]]*\]", " ", out)               # [A-Za-z0-9]
    out = re.sub(r"\(\?[a-z]+\)", " ", out)             # inline flags (?is)
    return out


# ── the four checks ─────────────────────────────────────────────────────────

def check_prose_regex(tf: TaskFiles, vpath: str, spec: dict, res: TaskResult) -> None:
    """D1 — prose/memo graded by a form-only, token-soup, or bare-presence regex."""
    flagged = 0
    # For the bare-presence cluster signal: per prose file, count regex items that
    # match only a literal token appearing (no `.*`, lookahead, or quantifier).
    bare_by_file: dict[str, list[str]] = {}
    for v in _verifier_items(spec):
        name = str(v.get("name", ""))
        pattern = _regex_comparison(v)
        if pattern is None:
            continue
        path, stype = _source_path_and_type(v)
        if not _is_prose_target(name, path, stype):
            continue

        reasons = []
        has_words = bool(WORD_TOKEN.search(_strip_regex_meta(pattern)))
        if LENGTH_ONLY.search(pattern) and not has_words:
            reasons.append("length/format-only quantifier, no required content words")
        if len(LOOKAHEAD.findall(pattern)) >= 2:
            reasons.append(f"{len(LOOKAHEAD.findall(pattern))} `(?=...)` lookaheads (keyword-set membership, order/coherence ungraded)")
        if WILDCARD_SLACK.search(pattern):
            reasons.append("`.*`/`.{0,N}` slack lets arbitrary filler satisfy the match")

        # Bare presence: the whole pattern grades "does this literal token occur",
        # with no regex structure tying it to a claim. Accumulate per file; a lone
        # one may be legitimate, a cluster on one memo is decomposed token grading.
        if not REGEX_STRUCTURE.search(pattern):
            bare_by_file.setdefault(path or stype or "(memo)", []).append(name)

        if not reasons:
            continue

        flagged += 1
        weight = (v.get("metadata") or {}).get("weight")
        res.findings.append(Finding(
            check_id="D1.prose_regex_grading",
            family=FAMILIES["D1"],
            severity=2,
            title="Prose deliverable graded by reward-hackable regex",
            detail=(
                f"Verifier '{name}' grades a prose target ({path or stype or 'memo'}) "
                f"with regex_match but " + "; ".join(reasons) +
                ". A keyword-stuffed stub can pass while a genuine explanation is "
                "not checked for substance. Replace with an LLM rubric on content "
                "or a key-fact set-membership check."
            ),
            evidence=f"pattern={pattern[:160]}" + (f" | weight={weight}" if weight is not None else ""),
            verifier=name,
        ))

    # Bare-presence cluster: one prose file whose grade is a set of >=N "does this
    # literal token appear" regexes with no structure. The memo is scored only by
    # which IDs/keywords were listed, never whether the explanation is correct — the
    # client's "brittle ID-presence checks that let wrong answers pass" true positive.
    for pf, names in bare_by_file.items():
        already = {f.verifier for f in res.findings if f.check_id == "D1.prose_regex_grading"}
        cluster = [n for n in names if n not in already]
        if len(cluster) < BARE_PRESENCE_CLUSTER:
            continue
        flagged += len(cluster)
        res.findings.append(Finding(
            check_id="D1.prose_regex_grading",
            family=FAMILIES["D1"],
            severity=2,
            title="Prose deliverable graded only by keyword/ID-presence regexes",
            detail=(
                f"{len(cluster)} regex_match items grade the prose target '{pf}' by "
                "bare literal presence (no `.*`, lookahead, or quantifier), so the memo "
                "is scored only by which tokens appear, not whether the explanation is "
                "correct or coherent. A stub that lists the IDs passes. Grade the claim "
                "with an LLM rubric on content, or bind each token to its required "
                "assertion instead of mere presence."
            ),
            evidence="items=" + ", ".join(sorted(cluster)[:8]) + (f" (+{len(cluster) - 8} more)" if len(cluster) > 8 else ""),
            verifier=cluster[0],
        ))
    res.features["prose_regex_items_flagged"] = flagged


def check_root_container(tf: TaskFiles, res: TaskResult) -> None:
    """D2 — Dockerfile runs the agent as root.

    Running as root is near-universal in these bundles and is only *material* when
    a grading fixture also sits on an agent-writable path (D4). So D2 on its own is
    emitted at sev1 (advisory); D4 elevates the concrete exploit to sev3. This keeps
    a default sev>=2 gate from being swamped by the ~100%-firing root signal.
    """
    dpath = tf.find("environment/Dockerfile") or tf.find("Dockerfile")
    if not dpath:
        res.features["dockerfile_present"] = False
        return
    res.features["dockerfile_present"] = True
    text = tf.read_text(dpath)
    # The effective user is the last USER instruction. root == "root"/"0"/absent.
    users = re.findall(r"^\s*USER\s+(\S+)", text, re.M)
    effective = users[-1] if users else None
    is_root = effective is None or effective.lower() in ("root", "0")
    res.features["container_user"] = effective or "(none)"
    if is_root:
        res.findings.append(Finding(
            check_id="D2.root_container",
            family=FAMILIES["D2"],
            severity=1,
            title="Container runs as root (no non-root USER)",
            detail=(
                "environment/Dockerfile sets no non-root USER, so the agent runs "
                "as root. This is only exploitable when a grading fixture also sits "
                "on an agent-writable path (see D4); on its own it is advisory. Add "
                "a non-root USER before the agent workspace is populated, or keep "
                "grading fixtures out of the agent-reachable tree."
            ),
            evidence=f"effective USER={effective or '(none)'}",
            fixability="fixable",
        ))


def check_judge_wiring(tf: TaskFiles, vpath: str, spec: dict, res: TaskResult) -> None:
    """D3 — judge model placeholder left unsubstituted or hard-pinned."""
    cfg = spec.get("config") if isinstance(spec.get("config"), dict) else {}
    models = cfg.get("models") if isinstance(cfg.get("models"), list) else []
    has_rubric = any(
        (v.get("assertion", {}) or {}).get("type") == "rubric"
        for v in _verifier_items(spec)
    )
    res.features["judge_models"] = models
    res.features["has_rubric_item"] = has_rubric
    if not models:
        return

    # Does the bundle resolve an injected JUDGE_MODEL at grading time? A
    # ``${JUDGE_MODEL}`` placeholder is the CORRECT dynamic-injection pattern when a
    # harness file reads/substitutes it (run_verifier.py in these bundles does:
    # "JUDGE_MODEL wins when set" + a FALLBACK_JUDGE_MODEL). It is only a defect when
    # NO such resolver ships. Scan every plausible resolver, not just test.sh.
    RESOLVER_FILES = (
        "tests/run_verifier.py", "run_verifier.py", "tests/test.sh",
        "tests/test_outputs.py", "tests/conftest.py", "conftest.py",
    )
    RESOLVE_OP = re.compile(
        r"os\.environ|getenv|environ\.get|\.replace\(|\.sub\(|\.format\(|"
        r"envsubst|substitut|JUDGE_MODEL_PLACEHOLDER|FALLBACK_JUDGE_MODEL",
        re.I,
    )
    harness_resolves_env = False
    resolver_hit = ""
    for suffix in RESOLVER_FILES:
        hp = tf.find(suffix)
        if not hp:
            continue
        text = tf.read_text(hp)
        if "JUDGE_MODEL" in text and RESOLVE_OP.search(text):
            harness_resolves_env = True
            resolver_hit = suffix.rsplit("/", 1)[-1]
            break
    res.features["harness_resolves_judge_env"] = harness_resolves_env

    for m in models:
        ms = str(m)
        if PLACEHOLDER.search(ms):
            # Placeholder WITH a resolver == correct dynamic wiring, not a defect.
            if harness_resolves_env:
                continue
            res.findings.append(Finding(
                check_id="D3.judge_model_wiring",
                family=FAMILIES["D3"],
                severity=3,
                title="Judge-model placeholder with no resolver",
                detail=(
                    f"config.models ships the literal placeholder '{ms}' but no "
                    f"harness file (run_verifier.py / test.sh / conftest.py) reads or "
                    f"substitutes JUDGE_MODEL, so the placeholder reaches the judge "
                    f"verbatim: the call fails and the rubric item is mis-scored / "
                    f"free-rides. Add a resolver or pin a real model."
                ),
                evidence=f"config.models={models}; resolver_found=False",
                fixability="fixable",
            ))
        elif CONCRETE_MODEL.match(ms) and not harness_resolves_env and has_rubric:
            res.findings.append(Finding(
                check_id="D3.judge_model_wiring",
                family=FAMILIES["D3"],
                severity=2,
                title="Judge model hard-pinned (runner override ignored)",
                detail=(
                    f"config.models pins ['{ms}'] and no harness file reads/resolves "
                    f"JUDGE_MODEL, so a runner that overrides the judge model is "
                    f"silently ignored; on a battery without that exact model the "
                    f"rubric item 404s. Read the injected JUDGE_MODEL instead."
                ),
                evidence=f"config.models={models}; resolver_found=False",
                fixability="fixable",
            ))


def check_fixture_overwritable(tf: TaskFiles, vpath: str, spec: dict, res: TaskResult) -> None:
    """D4 — verifier reads a grading fixture from an agent-writable path."""
    # Gather grading fixtures the tests copy/read (custom test_outputs.py).
    tpath = tf.find("tests/test_outputs.py")
    if not tpath:
        return
    tsrc = tf.read_text(tpath)
    # Files copied from /app/input or read from the agent tree as ground truth.
    copied = re.findall(r"""["']((?:/app/|app/|/workspace/)[\w./-]+\.py)["']""", tsrc)
    reads_fixture = bool(copied) or "input/" in tsrc and "copy" in tsrc.lower()
    if not reads_fixture:
        return
    # Only material if the container is root OR the fixture path is writable.
    container_root = res.features.get("container_user", "(none)") in ("(none)", "root", "0")
    writable = any(c.startswith(AGENT_WRITABLE_ROOTS) for c in copied)
    if copied and (container_root or writable):
        res.findings.append(Finding(
            check_id="D4.fixture_overwritable",
            family=FAMILIES["D4"],
            severity=3,
            title="Grading fixture reachable from agent-writable path",
            detail=(
                "tests/test_outputs.py uses a fixture from an agent-reachable path "
                "as grading ground truth. If the container is root or the path is "
                "writable the agent can replace the fixture to force a pass. Move "
                "the fixture into /tests (copied in at grade time) and run non-root."
            ),
            evidence="fixtures=" + ", ".join(sorted(set(copied))[:5]),
            fixability="fixable",
        ))


def check_inert_scoring_axis(tf: TaskFiles, spec: dict, res: TaskResult) -> None:
    """D5 — Harbor manifest advertises a scoring weight for an axis that is inert.

    Only fires for a genuinely DEAD axis. Two things make an empty-looking axis
    legitimate and must be excluded to avoid false positives:
      * ``flat_verifier_scoring: true`` — the per-axis weights are descriptive; the
        real score is a flat weighted pool over the actual verifier items, so a
        0-item axis is not "fiction weight".
      * state snapshotting (``state.snapshot.mode`` set, e.g. full_hash) — the state
        diff is computed at RUNTIME from the DB snapshot, so a shipped-empty
        solution/expected_diff.json is the normal read-only-audit pattern, not a
        dead axis. (Confirmed: these bundles carry 45-49 non-empty per-run diffs.)
    """
    manifest = spec.get("_manifest")
    if not isinstance(manifest, dict):
        return
    scoring = manifest.get("scoring", {}) if isinstance(manifest.get("scoring"), dict) else {}
    weights = scoring.get("weights", {}) if isinstance(scoring.get("weights"), dict) else {}
    if not weights:
        return
    res.features["scoring_weights"] = weights
    # Flat scoring makes per-axis weights descriptive, not the grading mechanism.
    if scoring.get("flat_verifier_scoring"):
        res.features["flat_verifier_scoring"] = True
        return

    inert: list[str] = []
    # SQL axis weighted but no sql_verifiers AND no rubric/verifier item targets a DB.
    sql_w = float(weights.get("sql", 0) or 0)
    sql_verifiers = manifest.get("sql_verifiers") or []
    if sql_w > 0 and not sql_verifiers:
        inert.append(f"sql weight {sql_w} but sql_verifiers is empty")

    # State axis weighted but state is NOT snapshotted (so no runtime diff can score
    # it) and the shipped expected diff is empty. If snapshot.mode is set, state is
    # computed at grade time -> legitimate, do not flag.
    state = manifest.get("state", {}) if isinstance(manifest.get("state"), dict) else {}
    snapshot_mode = (state.get("snapshot", {}) or {}).get("mode")
    state_w = float(weights.get("state", 0) or 0)
    if state_w > 0 and not snapshot_mode:
        diff_file = state.get("expected_diff_file")
        diff_empty = True
        if diff_file:
            dpath = tf.find(diff_file) or tf.find(diff_file.split("/")[-1])
            if dpath:
                try:
                    diff = json.loads(tf.read_text(dpath))
                    diff_empty = not diff
                except (json.JSONDecodeError, UnicodeError):
                    diff_empty = False
        if diff_empty:
            inert.append(f"state weight {state_w}, no snapshot mode, and {diff_file or 'expected_diff'} is empty")

    if not inert:
        return
    live = float(weights.get("rubric", 0) or 0)
    inert_total = sum(
        float(weights.get(k, 0) or 0)
        for k, present in (("sql", any("sql weight" in x for x in inert)),
                           ("state", any("state weight" in x for x in inert)))
        if present
    )
    res.findings.append(Finding(
        check_id="D5.inert_scoring_axis",
        family=FAMILIES["D5"],
        severity=2,
        title="Advertised scoring axis is inert (fiction weights)",
        detail=(
            "manifest.json scoring.weights advertise axes that cannot score: "
            + "; ".join(inert)
            + f". That {inert_total:g} of the weight silently collapses onto the "
            f"remaining axes (rubric weight {live:g}), so the task is graded almost "
            "entirely by the LLM rubric while claiming a mixed split. Either populate "
            "the axis or set its weight to 0."
        ),
        evidence=f"weights={weights}; sql_verifiers={len(sql_verifiers)}; snapshot_mode={snapshot_mode}",
        fixability="fixable",
    ))


# ── per-task orchestration ──────────────────────────────────────────────────

def lint_task(tf: TaskFiles, task_id: str) -> TaskResult:
    res = TaskResult(task_id=task_id, source=tf.source)
    try:
        vpath, spec = _load_verifier(tf)
        # D2 first so D4 can read the resolved container user.
        check_root_container(tf, res)
        if spec is not None:
            check_prose_regex(tf, vpath or "", spec, res)
            check_judge_wiring(tf, vpath or "", spec, res)
            check_fixture_overwritable(tf, vpath or "", spec, res)
            check_inert_scoring_axis(tf, spec, res)
        elif vpath:
            res.error = f"verifier.json present but unparseable: {vpath}"
        else:
            res.features["verifier_json_present"] = False
    except Exception as exc:  # a malformed bundle must not abort the batch
        res.error = f"{type(exc).__name__}: {exc}"
    return res


def _task_id_from_files(tf: TaskFiles, fallback: str) -> str:
    vpath, spec = _load_verifier(tf)
    if isinstance(spec, dict) and spec.get("task_id"):
        return str(spec["task_id"])
    return fallback


# ── input discovery ─────────────────────────────────────────────────────────
# A task zip is one whose contents look like a task bundle (has a verifier.json
# or an environment/ dir). A delivery zip is a zip of task zips.

def _looks_like_task_zip(zf: zipfile.ZipFile) -> bool:
    names = zf.namelist()
    return any(n.endswith("verifier.json") for n in names) or any(
        "/environment/" in n or n.startswith("environment/") for n in names
    )


def iter_tasks(target: Path) -> Iterable[TaskFiles]:
    """Yield a TaskFiles for every task found under ``target``."""
    if target.is_dir():
        # A directory that itself is a task bundle?
        if (target / "tests" / "verifier.json").exists() or (target / "environment").is_dir() \
                or any(target.rglob("verifier.json")):
            # If it holds exactly one bundle at root, treat as one task; else
            # walk for nested task dirs and zips.
            direct = list(target.glob("*/tests/verifier.json")) + list(target.glob("tests/verifier.json"))
            if (target / "tests" / "verifier.json").exists():
                yield TaskFiles.from_dir(target)
                return
        for zp in sorted(target.rglob("*.zip")):
            yield from _iter_zip(zp)
        for vp in sorted(target.rglob("tests/verifier.json")):
            yield TaskFiles.from_dir(vp.parent.parent)
        return
    if target.suffix.lower() == ".zip":
        yield from _iter_zip(target)
        return
    raise SystemExit(f"unsupported target: {target}")


def _iter_zip(zp: Path) -> Iterable[TaskFiles]:
    raw = zp.read_bytes()
    zf = zipfile.ZipFile(io.BytesIO(raw))
    if _looks_like_task_zip(zf):
        yield TaskFiles.from_zip_bytes(raw, str(zp))
        return
    # Delivery zip: recurse into nested task zips.
    inner = [n for n in zf.namelist() if n.lower().endswith(".zip")]
    if inner:
        for n in inner:
            yield TaskFiles.from_zip_bytes(zf.read(n), f"{zp}!{n}")
        return
    # A flat archive that is neither a task nor a bag of task zips.
    if any(n.endswith("verifier.json") for n in zf.namelist()):
        yield TaskFiles.from_zip_bytes(raw, str(zp))


# ── reporting ───────────────────────────────────────────────────────────────

def render_text(results: list[TaskResult], fail_severity: int) -> str:
    lines: list[str] = []
    fam_counts: dict[str, int] = {}
    tasks_with = 0
    for r in results:
        if r.findings:
            tasks_with += 1
        for f in r.findings:
            fam_counts[f.family] = fam_counts.get(f.family, 0) + 1

    lines.append("=" * 78)
    lines.append(f"verifier_defect_lint — {len(results)} task(s) scanned, "
                 f"{tasks_with} with >=1 finding")
    for fam, cid in FAMILIES.items():
        lines.append(f"    {fam} {cid:24s} {fam_counts.get(cid, 0):4d}")
    lines.append("=" * 78)

    for r in sorted(results, key=lambda x: (-x.max_severity, x.task_id)):
        if not r.findings and not r.error:
            continue
        lines.append("")
        lines.append(f"### {r.task_id}   (max severity {r.max_severity})")
        lines.append(f"    source: {r.source}")
        if r.error:
            lines.append(f"    ERROR: {r.error}")
        for f in sorted(r.findings, key=lambda x: -x.severity):
            mark = "BLOCK" if f.severity >= fail_severity else "warn "
            lines.append(f"    [{mark} sev{f.severity}] {f.check_id}  ({f.verifier or '-'})")
            lines.append(f"        {f.title}")
            lines.append(f"        {f.detail}")
            if f.evidence:
                lines.append(f"        evidence: {f.evidence}")
    return "\n".join(lines)


# ── QC-platform integration ─────────────────────────────────────────────────
# These check IDs block a run on their own (feed preqc_decision.BLOCKING_CHECKS).
# D2 (root, sev1) is advisory; the real exploit is D4 (root + writable fixture).
#
# TEMPORARILY DISABLED: all D1-D5 bundle-lint checks are advisory-only for now.
# They still run and report findings, but do not gate a run. Re-enable by
# adding the check IDs back here (and in preqc_decision.BLOCKING_CHECKS) once
# the checks are calibrated against live outcomes.
BLOCKING_CHECK_IDS = set()


def scan_bundle_records(target: Path) -> dict[str, dict]:
    """Lint every task under ``target`` and return overlay-shaped records keyed by
    task id, ready to merge into the QC verdict overlay.

    Each record mirrors what run_qc writes per task: a ``static_findings`` list of
    Finding dicts plus a ``features`` block, so the existing report_html and
    preqc_decision machinery render and gate on them with no special-casing.
    """
    records: dict[str, dict] = {}
    for tf in iter_tasks(Path(target)):
        tid = _task_id_from_files(tf, Path(tf.source).stem)
        res = lint_task(tf, tid)
        records[tid] = {
            "task_id": tid,
            "title": tid,
            "source": "bundle_lint",
            "mode": "bundle",
            "verdict": "",
            "one_line": (f"{len(res.findings)} deterministic bundle defect(s)"
                         if res.findings else "no deterministic bundle defect"),
            "top_issues": [],
            "static_findings": [f.to_dict() for f in res.findings],
            "features": dict(res.features),
            "max_severity": res.max_severity,
            "bundle_source": res.source,
            "error": res.error,
        }
    return records


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Deterministically flag the client-audit task-bundle defect "
                    "families (prose-regex grading, root container, judge wiring, "
                    "overwritable fixture, inert scoring axis).")
    ap.add_argument("targets", nargs="+", type=Path,
                    help="task dir(s), task .zip(s), delivery .zip(s), or a folder of them")
    ap.add_argument("--json", dest="json_out", type=Path, default=None,
                    help="write full findings as JSON to this path")
    ap.add_argument("--fail-severity", type=int, default=2,
                    help="exit non-zero if any finding is at or above this severity (default 2)")
    ap.add_argument("--quiet", action="store_true", help="suppress the text report")
    args = ap.parse_args(argv)

    results: list[TaskResult] = []
    seen = 0
    for target in args.targets:
        if not target.exists():
            print(f"warning: target does not exist: {target}", file=sys.stderr)
            continue
        for tf in iter_tasks(target):
            seen += 1
            tid = _task_id_from_files(tf, Path(tf.source).stem)
            results.append(lint_task(tf, tid))

    if not args.quiet:
        print(render_text(results, args.fail_severity))

    if args.json_out:
        args.json_out.write_text(
            json.dumps([r.to_dict() for r in results], indent=2),
            encoding="utf-8",
        )
        if not args.quiet:
            print(f"\nwrote {args.json_out}")

    worst = max((r.max_severity for r in results), default=0)
    return 1 if worst >= args.fail_severity else 0


if __name__ == "__main__":
    raise SystemExit(main())
