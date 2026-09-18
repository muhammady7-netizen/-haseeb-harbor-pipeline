"""Structured validation for code-c227 table bloat maintenance audit.

Replaces regex-based verifier.json checks with proper CSV/JSON parsing:
- Validates exact CSV schema, unique rows, no extras
- Validates each table's finding, size_class, bloat_ratio fields
- Reconciles results.json counts with CSV content
- Checks memo for substantive explanations (not token stuffing)
- Core gate: missing deliverable = 0 reward
"""

import os
import sys
import json
import csv
import re
from pathlib import Path
from collections import Counter
import math

import pytest

WORKSPACE = Path(os.environ.get("HARBOR_TASK_WORKSPACE", "/app"))

# Expected gold answers (from policy + inputs)
def _round_half_up(n, decimals=2):
    multiplier = 10 ** decimals
    return math.floor(n * multiplier + 0.5) / multiplier

EXPECTED_TABLES = {
    "T-01": {"size_class": "large", "bloat_ratio": 0.1, "finding": "none"},
    "T-02": {"size_class": "large", "bloat_ratio": 0.35, "finding": "BLOAT_THRESHOLD_EXCEEDED"},
    "T-03": {"size_class": "large", "bloat_ratio": 0.15, "finding": "AUTOVACUUM_DISABLED"},
    "T-04": {"size_class": "large", "bloat_ratio": 0.1, "finding": "STALE_STATISTICS"},
    "T-05": {"size_class": "large", "bloat_ratio": 0.55, "finding": "BLOAT_THRESHOLD_EXCEEDED"},
    "T-06": {"size_class": "large", "bloat_ratio": 0.25, "finding": "BLOAT_THRESHOLD_EXCEEDED"},
    "T-07": {"size_class": "large", "bloat_ratio": 0.12, "finding": "none"},
    "T-08": {"size_class": "large", "bloat_ratio": 0.45, "finding": "BLOAT_THRESHOLD_EXCEEDED"},
    "T-09": {"size_class": "large", "bloat_ratio": 0.19, "finding": "none"},
    "T-10": {"size_class": "large", "bloat_ratio": 0.21, "finding": "STALE_STATISTICS"},
    "T-11": {"size_class": "large", "bloat_ratio": 0.41, "finding": "AUTOVACUUM_DISABLED"},
    "T-12": {"size_class": "large", "bloat_ratio": 0.2, "finding": "none"},
    "T-13": {"size_class": "large", "bloat_ratio": 0.5, "finding": "AUTOVACUUM_DISABLED"},
    "T-14": {"size_class": "large", "bloat_ratio": 0.4, "finding": "BLOAT_THRESHOLD_EXCEEDED"},
    "T-15": {"size_class": "large", "bloat_ratio": 0.2, "finding": "none"},
    "T-16": {"size_class": "large", "bloat_ratio": 0.2, "finding": "BLOAT_THRESHOLD_EXCEEDED"},
    "T-17": {"size_class": "large", "bloat_ratio": 0.4, "finding": "AUTOVACUUM_DISABLED"},
    "T-18": {"size_class": "large", "bloat_ratio": 0.21, "finding": "BLOAT_THRESHOLD_EXCEEDED"},
    "T-19": {"size_class": "large", "bloat_ratio": 0.41, "finding": "BLOAT_THRESHOLD_EXCEEDED"},
    "T-20": {"size_class": "large", "bloat_ratio": 0.1, "finding": "AUTOVACUUM_DISABLED"},
    "T-21": {"size_class": "large", "bloat_ratio": 0.2, "finding": "AUTOVACUUM_DISABLED"},
    "T-26": {"size_class": "large", "bloat_ratio": 0.18, "finding": "BLOAT_THRESHOLD_EXCEEDED"},
    "T-27": {"size_class": "large", "bloat_ratio": 0.38, "finding": "BLOAT_THRESHOLD_EXCEEDED"},
    "T-28": {"size_class": "large", "bloat_ratio": 0.25, "finding": "none"},
    "T-29": {"size_class": "large", "bloat_ratio": 0.25, "finding": "BLOAT_THRESHOLD_EXCEEDED"},
    "T-30": {"size_class": "large", "bloat_ratio": 0.2, "finding": "BLOAT_THRESHOLD_EXCEEDED"},
    "T-31": {"size_class": "small", "bloat_ratio": 0.3, "finding": "none"},
    "T-32": {"size_class": "small", "bloat_ratio": 0.4, "finding": "none"},
    "T-33": {"size_class": "small", "bloat_ratio": 0.21, "finding": "none"},
    "T-34": {"size_class": "large", "bloat_ratio": 0.2, "finding": "none"},
    "T-35": {"size_class": "large", "bloat_ratio": 0.22, "finding": "BLOAT_THRESHOLD_EXCEEDED"},
    "T-36": {"size_class": "large", "bloat_ratio": 0.18, "finding": "BLOAT_THRESHOLD_EXCEEDED"},
    "T-37": {"size_class": "large", "bloat_ratio": 0.25, "finding": "BLOAT_THRESHOLD_EXCEEDED"},
    "T-38": {"size_class": "small", "bloat_ratio": 0.33, "finding": "none"},
    "T-39": {"size_class": "large", "bloat_ratio": 0.05, "finding": "AUTOVACUUM_DISABLED"},
    "T-40": {"size_class": "large", "bloat_ratio": 0.05, "finding": "STALE_STATISTICS"},
    "T-41": {"size_class": "small", "bloat_ratio": 0.4, "finding": "none"},
    "T-42": {"size_class": "large", "bloat_ratio": 0.2, "finding": "BLOAT_THRESHOLD_EXCEEDED"},
    "T-43": {"size_class": "small", "bloat_ratio": 0.21, "finding": "none"},
    "T-44": {"size_class": "large", "bloat_ratio": 0.83, "finding": "BLOAT_THRESHOLD_EXCEEDED"},
    "T-45": {"size_class": "large", "bloat_ratio": 0.16, "finding": "BLOAT_THRESHOLD_EXCEEDED"},
}

EXPECTED_RESULTS = {
    "flagged_count": 28,
    "autovacuum_disabled_count": 7,
    "bloat_exceeded_count": 18,
    "stale_statistics_count": 3,
    "compliant_count": 13,
}

REQUIRED_HEADER = ["table_name", "size_class", "bloat_ratio", "finding"]
VALID_FINDINGS = {"AUTOVACUUM_DISABLED", "BLOAT_THRESHOLD_EXCEEDED", "STALE_STATISTICS", "none"}
SIZE_CLASS_CAPS = {"large": 0.2, "small": 0.4}

# Short tokens that alone are too weak to count as a "substantive concept"
_WEAK_CONCEPTS = {
    "bloat", "cap", "none", "over", "exceed", "first", "size", "class",
    "total", "large", "small", "days", "field", "wrong", "incorrect",
}

_FINDING_CANONICAL = {
    "autovacuum_disabled": "AUTOVACUUM_DISABLED",
    "bloat_threshold_exceeded": "BLOAT_THRESHOLD_EXCEEDED",
    "stale_statistics": "STALE_STATISTICS",
    "bloat": "BLOAT_THRESHOLD_EXCEEDED",  # only when concept is exactly "BLOAT" (handled below)
    "none": "none",
}


def _load_csv():
    """Load and parse bloat_audit.csv with full validation."""
    path = WORKSPACE / "bloat_audit.csv"
    if not path.is_file():
        return None, "bloat_audit.csv not found"
    try:
        with open(path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames != REQUIRED_HEADER:
                return None, f"Header mismatch: got {reader.fieldnames}, expected {REQUIRED_HEADER}"
            rows = list(reader)
            return rows, None
    except Exception as e:
        return None, f"CSV parse error: {e}"


def _load_json():
    """Load results.json."""
    path = WORKSPACE / "results.json"
    if not path.is_file():
        return None, "results.json not found"
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as e:
        return None, f"JSON parse error: {e}"


def _load_memo():
    """Load bloat_memo.md."""
    path = WORKSPACE / "bloat_memo.md"
    if not path.is_file():
        return None, "bloat_memo.md not found"
    return path.read_text(encoding="utf-8"), None


def _parse_ratio(val):
    """Parse a bloat ratio string to float, accepting 0.2 = 0.20 = 0.200."""
    try:
        return float(str(val).strip())
    except (ValueError, TypeError):
        return None


def _prose_lines(memo):
    """Return non-table prose lines (skip markdown table rows with pipes)."""
    lines = []
    for line in memo.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        # Skip markdown table rows / separators
        if stripped.startswith("|") or (stripped.count("|") >= 2):
            continue
        lines.append(stripped)
    return lines


def _normalize_finding_token(concept):
    """Return canonical finding code if concept is a finding token, else None."""
    c = concept.strip()
    cu = c.upper().replace(" ", "_").replace("-", "_")
    if cu in ("AUTOVACUUM_DISABLED", "BLOAT_THRESHOLD_EXCEEDED", "STALE_STATISTICS", "NONE"):
        return "none" if cu == "NONE" else cu
    # Exact uppercase BLOAT alias (not bare lowercase "bloat")
    if c == "BLOAT":
        return "BLOAT_THRESHOLD_EXCEEDED"
    if c == "STALE":
        return "STALE_STATISTICS"
    return None


def _is_substantive(concept):
    """True if concept is strong enough to count toward the 2-concept requirement."""
    if _normalize_finding_token(concept):
        return False
    low = concept.strip().lower()
    if low in _WEAK_CONCEPTS:
        return False
    # Very short bare tokens are not substantive on their own
    if len(low) <= 3 and not any(ch.isdigit() for ch in low):
        return False
    return True


# ============ CORE GATE TESTS (must pass for any reward) ============

def test_audit_exists():
    """bloat_audit.csv must exist."""
    rows, err = _load_csv()
    assert rows is not None, f"Core gate: {err}"


def test_memo_exists():
    """bloat_memo.md must exist."""
    memo, err = _load_memo()
    assert memo is not None, f"Core gate: {err}"


def test_results_exists():
    """results.json must exist."""
    data, err = _load_json()
    assert data is not None, f"Core gate: {err}"


def test_audit_header():
    """CSV must have exactly the required header."""
    rows, err = _load_csv()
    assert err is None, err
    # Header already validated in _load_csv via DictReader fieldnames check
    assert len(rows) > 0, "CSV has no data rows"


def test_audit_exact_row_count():
    """CSV must have exactly 41 data rows (no extra, no missing)."""
    rows, err = _load_csv()
    assert err is None, err
    assert len(rows) == 41, f"Expected 40 rows, got {len(rows)}"


def test_audit_no_duplicates():
    """Each table_name must appear exactly once."""
    rows, err = _load_csv()
    assert err is None, err
    names = [r.get("table_name", "").strip() for r in rows]
    counts = Counter(names)
    dupes = {k: v for k, v in counts.items() if v > 1}
    assert not dupes, f"Duplicate table_name entries: {dupes}"


def test_audit_all_tables_present():
    """All expected tables must be present."""
    rows, err = _load_csv()
    assert err is None, err
    actual = {r.get("table_name", "").strip() for r in rows}
    expected = set(EXPECTED_TABLES.keys())
    missing = expected - actual
    extra = actual - expected
    assert not missing, f"Missing tables: {missing}"
    assert not extra, f"Unexpected extra tables: {extra}"


def test_audit_valid_findings():
    """All findings must be valid finding codes."""
    rows, err = _load_csv()
    assert err is None, err
    for row in rows:
        finding = row.get("finding", "").strip()
        assert finding in VALID_FINDINGS, f"Invalid finding '{finding}' for {row.get('table_name')}"


# ============ PER-TABLE VALIDATION (field-level) ============

@pytest.mark.parametrize("table_id", sorted(EXPECTED_TABLES.keys()))
def test_table_finding(table_id):
    """Each table's finding must match the expected gold answer."""
    rows, err = _load_csv()
    assert err is None, err
    row = next((r for r in rows if r.get("table_name", "").strip() == table_id), None)
    assert row is not None, f"Table {table_id} not found in audit"
    expected = EXPECTED_TABLES[table_id]["finding"]
    actual = row.get("finding", "").strip()
    assert actual == expected, f"{table_id}: expected {expected}, got {actual}"


@pytest.mark.parametrize("table_id", sorted(EXPECTED_TABLES.keys()))
def test_table_size_class(table_id):
    """Each table's size_class must match the input data."""
    rows, err = _load_csv()
    assert err is None, err
    row = next((r for r in rows if r.get("table_name", "").strip() == table_id), None)
    assert row is not None, f"Table {table_id} not found"
    expected = EXPECTED_TABLES[table_id]["size_class"]
    actual = row.get("size_class", "").strip().lower()
    assert actual == expected, f"{table_id}: expected size_class={expected}, got {actual}"


@pytest.mark.parametrize("table_id", sorted(EXPECTED_TABLES.keys()))
def test_table_bloat_ratio(table_id):
    """Each table's bloat_ratio must match the input data (numeric equivalence)."""
    rows, err = _load_csv()
    assert err is None, err
    row = next((r for r in rows if r.get("table_name", "").strip() == table_id), None)
    assert row is not None, f"Table {table_id} not found"
    expected = EXPECTED_TABLES[table_id]["bloat_ratio"]
    actual = _parse_ratio(row.get("bloat_ratio"))
    assert actual is not None, f"{table_id}: cannot parse bloat_ratio '{row.get('bloat_ratio')}'"
    assert abs(actual - expected) < 1e-9, f"{table_id}: expected bloat_ratio={expected}, got {actual}"


# ============ RESULTS.JSON RECONCILIATION ============

def _csv_result_counts(rows):
    return {
        "flagged_count": sum(1 for r in rows if r.get("finding", "").strip() != "none"),
        "autovacuum_disabled_count": sum(
            1 for r in rows if r.get("finding", "").strip() == "AUTOVACUUM_DISABLED"
        ),
        "bloat_exceeded_count": sum(
            1 for r in rows if r.get("finding", "").strip() == "BLOAT_THRESHOLD_EXCEEDED"
        ),
        "stale_statistics_count": sum(
            1 for r in rows if r.get("finding", "").strip() == "STALE_STATISTICS"
        ),
        "compliant_count": sum(1 for r in rows if r.get("finding", "").strip() == "none"),
    }


def test_results_flagged_count():
    """results.json flagged_count must match gold and CSV-derived count."""
    rows, err = _load_csv()
    assert err is None, err
    data, jerr = _load_json()
    assert jerr is None, jerr
    key = "flagged_count"
    actual = data.get(key)
    assert actual == EXPECTED_RESULTS[key], f"{key}: got {actual}, expected {EXPECTED_RESULTS[key]}"
    assert actual == _csv_result_counts(rows)[key], f"{key}: json != csv"


def test_results_autovacuum_disabled_count():
    """results.json autovacuum_disabled_count must match gold and CSV-derived count."""
    rows, err = _load_csv()
    assert err is None, err
    data, jerr = _load_json()
    assert jerr is None, jerr
    key = "autovacuum_disabled_count"
    actual = data.get(key)
    assert actual == EXPECTED_RESULTS[key], f"{key}: got {actual}, expected {EXPECTED_RESULTS[key]}"
    assert actual == _csv_result_counts(rows)[key], f"{key}: json != csv"


def test_results_bloat_exceeded_count():
    """results.json bloat_exceeded_count must match gold and CSV-derived count."""
    rows, err = _load_csv()
    assert err is None, err
    data, jerr = _load_json()
    assert jerr is None, jerr
    key = "bloat_exceeded_count"
    actual = data.get(key)
    assert actual == EXPECTED_RESULTS[key], f"{key}: got {actual}, expected {EXPECTED_RESULTS[key]}"
    assert actual == _csv_result_counts(rows)[key], f"{key}: json != csv"


def test_results_stale_statistics_count():
    """results.json stale_statistics_count must match gold and CSV-derived count."""
    rows, err = _load_csv()
    assert err is None, err
    data, jerr = _load_json()
    assert jerr is None, jerr
    key = "stale_statistics_count"
    actual = data.get(key)
    assert actual == EXPECTED_RESULTS[key], f"{key}: got {actual}, expected {EXPECTED_RESULTS[key]}"
    assert actual == _csv_result_counts(rows)[key], f"{key}: json != csv"


def test_results_compliant_count():
    """results.json compliant_count must match gold and CSV-derived count."""
    rows, err = _load_csv()
    assert err is None, err
    data, jerr = _load_json()
    assert jerr is None, jerr
    key = "compliant_count"
    actual = data.get(key)
    assert actual == EXPECTED_RESULTS[key], f"{key}: got {actual}, expected {EXPECTED_RESULTS[key]}"
    assert actual == _csv_result_counts(rows)[key], f"{key}: json != csv"


def test_results_partition_invariant():
    """Structural only: required keys present and flagged+compliant == row count.

    Per-key gold values are graded solely by the five test_results_*_count tests
    above (scoring weight without double-counting the same keys).
    """
    rows, err = _load_csv()
    assert err is None, err
    data, jerr = _load_json()
    assert jerr is None, jerr

    missing = set(EXPECTED_RESULTS) - set(data)
    assert not missing, f"Missing keys in results.json: {missing}"
    assert (
        data.get("flagged_count", 0) + data.get("compliant_count", 0) == len(rows)
    ), "flagged_count + compliant_count must equal CSV row count"


# ============ MEMO SUBSTANTIVE CHECKS ============

def _decimal_near_forms(token):
    """Accept rounded and pre-round near-equivalents for ratio/cap evidence.

    Do not require an undisclosed pre-round literal when the rounded 2dp form
    is present (and vice versa). Classic pairs: 0.205↔0.21, 0.405↔0.41.
    """
    try:
        val = float(token)
    except (ValueError, TypeError):
        return {token}
    forms = {token, f"{val:g}", f"{val:.2f}", f"{val:.3f}", f"{val:.1f}"}
    rounded = _round_half_up(val, 2)
    forms.update({f"{rounded:g}", f"{rounded:.2f}", f"{rounded:.3f}", f"{rounded:.1f}"})
    pre = rounded - 0.005
    if pre > 0:
        forms.update({f"{pre:.3f}", f"{pre:g}"})
    if abs(val - rounded) < 1e-12:
        forms.add(f"{rounded - 0.005:.3f}")
    # Also accept trailing-zero variants agents commonly write
    for f in list(forms):
        try:
            fv = float(f)
            forms.add(f"{fv:g}")
            if abs(fv - round(fv, 1)) < 1e-12:
                forms.add(f"{fv:.1f}")
            if abs(fv - round(fv, 2)) < 1e-12:
                forms.add(f"{fv:.2f}")
        except ValueError:
            pass
    return {f for f in forms if f and f != "."}


def _concept_pattern(concept):
    """Build a regex for a disclosed evidence concept (allow fair paraphrases)."""
    c = concept.strip()
    low = c.lower()
    if low in {"compute", "computed", "computing"}:
        # Size-class computation stem disclosed in instruction
        return r"comput(?:e|ed|es|ing)|recalculat(?:e|ed|es|ing)|derived?\s+from\s+total_pages"
    if low == "autovacuum":
        return r"auto[\s-]?vacuum"
    if low == "reindex":
        return r"re[\s-]?index(?:ing|ed|es)?"
    if low in {"expired", "valid_until", "lapsed"}:
        # Reindex-approval expiry paraphrases (instruction-disclosed)
        return (
            r"(?:expired|lapsed|valid_until|approval\s+ended|"
            r"past\s+validity|no\s+longer\s+valid|approval\s+(?:has\s+)?expired|"
            r"validity\s+(?:ended|lapsed|expired)|before\s+audit|"
            r"past\s+(?:its\s+)?(?:valid(?:ity)?|expiry)|out\s+of\s+date|"
            r"no\s+longer\s+(?:in\s+)?force|approval\s+(?:window\s+)?(?:closed|ended))"
        )
    if low in {"tighten", "tightened", "tightens"}:
        return (
            r"tighten(?:ed|s|ing)?|reduc(?:e|ed|es|ing)\s+(?:the\s+)?"
            r"(?:cap|threshold)|lower(?:ed|s)?\s+(?:the\s+)?(?:cap|threshold)|"
            r"effective\s+cap|cap\s+(?:is\s+)?(?:reduced|lowered)"
        )
    if low in {"override", "overrides", "overriding"}:
        return r"overrid(?:e|es|ing|den)|supersede[sd]?|takes?\s+precedence|checked\s+first"
    if low == "unapproved":
        # Negative approval only — must NOT be satisfied by bare "approved"
        return (
            r"unapproved|not\s+approved|"
            r"approval\s+(?:is\s+)?false|"
            r"approved\s*=\s*[Ff]alse"
        )
    if low == "approved":
        # Positive approval — must NOT be satisfied by "unapproved" / "not approved" alone
        return (
            r"(?<!un)(?<!not )approved(?!\s*=\s*[Ff]alse)|"
            r"approval\s+(?:is\s+)?true|"
            r"approved\s*=\s*[Tt]rue"
        )
    if low == "threshold":
        return r"threshold|\bcap\b"
    if low == "disabled":
        return r"disabled|turned\s+off|not\s+enabled|\boff\b"
    if low in {"statistics", "stats"}:
        return r"statistics|\bstats\b"
    if low == "stale":
        return r"stale|staleness|out[\s-]of[\s-]date\s+stats"
    if low == "effective":
        return r"effective|tightened|reduced\s+cap"
    if low == "medium":
        return r"\bmedium\b"
    if low in {"round", "rounding", "round-half-up"}:
        return r"round(?:ing|ed|s)?(?:[\s-]?half[\s-]?up)?"
    if low == "manual":
        return r"\bmanual\b"
    if low == "vacuum":
        return r"\bvacuum(?:ing|ed)?\b"
    if low == "days_since_analyze":
        return (
            r"days_since_analyze|days[\s_-]?since[\s_-]?analyze|"
            r"legacy\s+(?:days|field)|export\s+days"
        )
    if low == "large":
        return r"\blarge\b"
    if low == "small":
        return r"\bsmall\b"
    if re.fullmatch(r"\d+\.\d+", c):
        alts = sorted(_decimal_near_forms(c), key=len, reverse=True)
        inner = "|".join(re.escape(a) for a in alts)
        return rf"(?<![\d,])(?:{inner})(?![\d])"
    if re.fullmatch(r"\d+", c):
        # Plain digits without thousands separators (instruction-disclosed)
        return rf"(?<![\d,]){re.escape(c)}(?![\d])"
    return re.escape(c)


def _finding_pattern(finding):
    if finding == "BLOAT_THRESHOLD_EXCEEDED":
        return r"(?:BLOAT_THRESHOLD_EXCEEDED|\bBLOAT\b)"
    if finding == "AUTOVACUUM_DISABLED":
        return r"AUTOVACUUM_DISABLED"
    if finding == "STALE_STATISTICS":
        return r"STALE_STATISTICS"
    if finding == "none":
        return r"(?:\bnone\b|\bcompliant\b)"
    return re.escape(finding) if finding else r"."


_MEMO_UNIT_MAX = 450  # chars: single sentence/bullet around a table id
_MEMO_CONCEPT_WINDOW = 400  # chars: each concept near table id (matches disclosed ~few-hundred window)

# Function-word glue for prose detection (not a secret ≥N threshold by itself).
_PROSE_GLUE = {
    "the", "a", "an", "of", "to", "for", "and", "or", "but", "with", "from",
    "that", "this", "its", "it", "is", "are", "was", "were", "has", "have", "had",
    "because", "since", "when", "while", "which", "their", "if", "we", "so", "as",
    "by", "on", "in", "at", "be", "been", "being", "than", "then", "also", "only",
    "still", "into", "not", "no", "over", "under", "does", "do", "out", "before",
    "after", "every", "other", "though", "despite", "even", "where", "who",
}


def _collapse_prose(blob):
    """Drop dump lines; collapse remaining text so multi-line bullets still match."""
    kept = []
    for line in blob.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.count("|") >= 2 or stripped.count(",") >= 6:
            continue
        kept.append(stripped)
    return " ".join(kept)


def _looks_like_natural_prose(unit):
    """True when the unit has clause punctuation plus a connective/framing verb.

    Used to spare natural sentences from numeric anti-bag. Does not accept a bare
    keyword list that merely contains domain verbs like 'overrides' or 'expired'.
    """
    if not re.search(r"[.,:;]|Finding\s*:", unit):
        return False
    if re.search(r"(?i)\b(?:which|because|since|though|despite)\b", unit):
        return True
    if re.search(
        r"(?i)\b(?:records|means|shows|reports|explains)\b|"
        r"\b(?:is|are|was|were)\s+\w+",
        unit,
    ):
        return True
    glue = sum(1 for w in re.findall(r"[A-Za-z]+", unit) if w.lower() in _PROSE_GLUE)
    return glue >= 3


def _is_token_dump(unit):
    """Reject undifferentiated keyword bags; accept natural prose sentences.

    Does **not** require a closed stopword-count gate of ≥3 from a narrow list
    (Harbor example with which/a/the must pass). Accepts relative clauses,
    subject–verb framing, or ordinary function-word glue. Lone keyword soups
    that stuff domain verbs (overrides/expired/computed) without framing still fail.
    """
    words = re.findall(r"[A-Za-z0-9_.=-]+", unit)
    if len(words) < 8:
        return True
    if not re.search(r"[.,:;]|Finding\s*:", unit):
        return True
    if not _looks_like_natural_prose(unit):
        return True
    # Dense ALL-CAPS finding codes without surrounding lowercase prose words
    caps = sum(1 for w in words if w.isupper() and "_" in w)
    lowerish = sum(1 for w in words if any(c.islower() for c in w))
    if caps >= 2 and lowerish < 3:
        return True
    return False


def _tying_verb_phrase(unit, table_id, finding):
    """Require a real verb phrase tying table → finding → evidence."""
    tid = re.escape(table_id)
    find_pat = _finding_pattern(finding) if finding else r"."
    # Must see table id and finding in the same small unit
    if not re.search(tid, unit, re.I):
        return False
    if finding and not re.search(find_pat, unit, re.I):
        return False
    # Bare 'is'/'cap'/'ratio' alone on a token dump is not enough — need a tying clause
    return bool(re.search(
        r"(?i)(?:"
        r"because|since|which|"
        r"records?\s+a|means?\s+(?:the|that|a)|"
        r"ratio\s+of|with\s+(?:a\s+|bloat\s+)?ratio|"
        r"is\s+(?:far\s+)?over|are\s+over|over\s+the|under\s+the|"
        r"exceeds?|equals?|"
        r"overrides?|overrid(?:e|es|ing|den)|supersede[sd]?|checked\s+first|"
        r"comput(?:e|ed|es|ing)\s+as|derived\s+from|"
        r"tighten(?:ed|s|ing)?|effective\s+cap|"
        r"expired|lapsed|not\s+exempt|unapproved|not\s+approved|"
        r"disabled|turned\s+off|"
        r"stale|days?\s+(?:old|stale)|"
        r"manual\s+vacuum|"
        r"Finding\s*:"
        r")",
        unit,
    ))


def _extract_table_units(text, table_id, max_len=_MEMO_UNIT_MAX):
    """Extract the nearest sentence/bullet unit for each table-id hit (max ~300 chars).

    Prefers markdown bullets / contiguous wrapped lines; falls back to sentence
    boundaries. Concepts are graded only inside these units so a shared global
    token bag cannot satisfy every table.
    """
    tid_re = re.compile(rf"(?i)\b{re.escape(table_id)}\b")
    lines = text.split("\n")
    units = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not tid_re.search(line):
            i += 1
            continue
        # Expand through wrapped continuation lines of the same bullet/paragraph
        block_lines = [line.strip()]
        j = i + 1
        while j < len(lines):
            nxt = lines[j]
            stripped = nxt.strip()
            if not stripped:
                break
            # New bullet / heading / other table id starts a new unit
            if re.match(r"^(?:[-*]|\d+\.)\s+", stripped) or stripped.startswith("#"):
                break
            if re.match(r"^#{1,6}\s", stripped):
                break
            if re.search(r"(?i)\bT-\d+\b", stripped) and not tid_re.search(stripped):
                break
            # Continuation: indented, or plain prose without a new table lead-in
            if nxt.startswith((" ", "\t")) or not re.match(
                r"(?i)^(?:[-*]|\*\*)?\s*T-\d+", stripped
            ):
                block_lines.append(stripped)
                j += 1
                continue
            break
        block = " ".join(block_lines)
        # Prefer the sentence that contains the table id when the block is long
        unit = _clip_unit_around_table(block, table_id, max_len)
        if unit:
            units.append(unit)
        i = j if j > i + 1 else i + 1
    # Fallback: sentence scan on collapsed text if line-based found nothing
    if not units:
        collapsed = _collapse_prose(text) or text
        for m in tid_re.finditer(collapsed):
            # Sentence boundaries around the hit
            left = collapsed.rfind(". ", 0, m.start())
            left = 0 if left < 0 else left + 2
            right_candidates = [
                collapsed.find(p, m.end())
                for p in (". ", ".\n", "; ")
            ]
            rights = [r for r in right_candidates if r >= 0]
            right = (min(rights) + 1) if rights else min(len(collapsed), m.end() + max_len)
            chunk = collapsed[left:right].strip()
            unit = _clip_unit_around_table(chunk, table_id, max_len)
            if unit:
                units.append(unit)
    return units


def _clip_unit_around_table(block, table_id, max_len):
    """Keep at most max_len chars, anchored on the table id mention."""
    if not block:
        return ""
    m = re.search(rf"(?i)\b{re.escape(table_id)}\b", block)
    if not m:
        return block[:max_len]
    if len(block) <= max_len:
        return block
    # Prefer text from a little before the id through max_len (finding often follows)
    start = max(0, m.start() - 20)
    end = min(len(block), start + max_len)
    if end - start < max_len:
        start = max(0, end - max_len)
    return block[start:end].strip()


def _evidence_numbers(unit):
    """Distinct numeric evidence tokens (ratios / page counts / day counts).

    ISO dates and table-id digits (T-39 → 39) are stripped so they do not
    inflate anti-bag checks.
    """
    cleaned = re.sub(r"\d{4}-\d{2}-\d{2}", " ", unit)
    cleaned = re.sub(r"(?i)\bT-\d+\b", " ", cleaned)
    return set(re.findall(r"(?<![\d.])\d+\.\d+(?![\d])|(?<![\d])\d{2,4}(?!\d)", cleaned))


def _needed_numeric_forms(concepts):
    forms = set()
    for c in concepts:
        raw = c.strip()
        if re.fullmatch(r"\d+\.\d+", raw) or re.fullmatch(r"\d+", raw):
            forms |= _decimal_near_forms(raw)
    return forms


def _has_numeric_bag_dump(unit, concepts):
    """Reject space-separated number dumps without prose; allow natural sentences.

    Natural prose that mentions a few ratios / page counts / day counts (beyond
    this table's required numeric concepts) is accepted. Only fail when the
    window looks like an undifferentiated numeric bag: many numbers, little or
    no alphabetic prose, and no clause punctuation / verb connectives.
    """
    if _looks_like_natural_prose(unit):
        return False

    found = _evidence_numbers(unit)
    if len(found) < 5:
        return False

    needed = _needed_numeric_forms(concepts)
    extras = 0
    for n in found:
        ok = False
        for nf in needed:
            try:
                if n == nf or abs(float(n) - float(nf)) < 1e-9:
                    ok = True
                    break
            except ValueError:
                if n == nf:
                    ok = True
                    break
        if not ok:
            extras += 1

    alpha_words = re.findall(r"[A-Za-z]+", unit)
    # High numeric density relative to alphabetic tokens → bag dump
    return extras >= 5 and extras >= max(3, len(alpha_words) // 2)


def _has_prose_sentence_structure(unit, table_id, finding):
    """Require table id + finding tied by a real verb phrase — not a token dump."""
    text = unit.strip()
    if len(text.split()) < 10:
        return False
    if _is_token_dump(text):
        return False
    if not _tying_verb_phrase(text, table_id, finding):
        return False
    tid = re.escape(table_id)
    find_pat = _finding_pattern(finding)
    # Finding may trail the explanation; keep it inside the same unit (≤300),
    # while substantive concepts still use the tighter concept window.
    return bool(re.search(
        rf"(?is)(?:{tid}.{{0,{_MEMO_UNIT_MAX}}}?{find_pat}|"
        rf"{find_pat}.{{0,{_MEMO_UNIT_MAX}}}?{tid})",
        text,
    ))


def _concept_in_unit(unit, table_id, concept, window=_MEMO_CONCEPT_WINDOW):
    """True if concept appears within a small window of the table id inside the unit."""
    tid = re.escape(table_id)
    cpat = _concept_pattern(concept)
    return bool(re.search(
        rf"(?is)(?:{tid}.{{0,{window}}}?{cpat}|{cpat}.{{0,{window}}}?{tid})",
        unit,
    ))


def _memo_mentions(table_id, *concepts):
    """Check memo discusses a table in a local prose unit with finding + concepts.

    Prefers non-table prose (skips markdown table rows with '|').
    Requires the gold finding token AND at least 2 other substantive concepts,
    each matched only inside the nearest sentence/bullet to that table id
    (max ~300 chars) — a shared global token bag cannot satisfy every table.
    Rejects undifferentiated keyword dumps and non-prose numeric bags.
    Natural sentences with clause punctuation + framing/connectives are accepted
    even when they mention a few extra ratios or page/day counts.
    """
    memo, err = _load_memo()
    if err:
        return False

    prose = "\n".join(_prose_lines(memo))
    search_text = prose if prose else memo

    if not table_id:
        concepts_alt = "|".join(_concept_pattern(c) for c in concepts)
        return bool(re.search(rf"(?is)(?:{concepts_alt})", search_text))

    finding = None
    other_concepts = []
    for c in concepts:
        ft = _normalize_finding_token(c)
        if ft and finding is None:
            finding = ft
        else:
            other_concepts.append(c)

    units = _extract_table_units(search_text, table_id)
    if not units:
        return False

    substantive = [c for c in other_concepts if _is_substantive(c)]
    needed = substantive if len(substantive) >= 2 else [
        c for c in other_concepts if c.strip().lower() not in _WEAK_CONCEPTS
        and not _normalize_finding_token(c)
    ]

    for unit in units:
        if _is_token_dump(unit):
            continue
        if _has_numeric_bag_dump(unit, list(concepts)):
            continue

        if finding is not None:
            if not _has_prose_sentence_structure(unit, table_id, finding):
                continue

        if concepts:
            if len(needed) >= 2:
                matched = sum(
                    1 for c in needed if _concept_in_unit(unit, table_id, c)
                )
                if matched < 2:
                    continue
            elif needed:
                if not _concept_in_unit(unit, table_id, needed[0]):
                    continue
            elif finding is not None:
                weak = [c for c in other_concepts if c.strip().lower() in _WEAK_CONCEPTS]
                weak_hits = sum(
                    1 for c in weak if _concept_in_unit(unit, table_id, c)
                )
                if weak_hits < 2:
                    continue
        return True

    return False


def test_memo_explains_t02():
    """Memo must explain T-02 bloat exceeded."""
    assert _memo_mentions("T-02", "BLOAT_THRESHOLD_EXCEEDED", "0.35", "threshold", "large"), "Memo must explain T-02 bloat exceeded"


def test_memo_explains_t03():
    """Memo must explain T-03 autovacuum disabled."""
    assert _memo_mentions("T-03", "AUTOVACUUM_DISABLED", "autovacuum", "disabled", "override"), "Memo must explain T-03 autovacuum disabled"


def test_memo_explains_t04():
    """Memo must explain T-04 stale statistics."""
    assert _memo_mentions("T-04", "STALE_STATISTICS", "45", "stale", "statistics"), "Memo must explain T-04 stale statistics"


def test_memo_explains_t08():
    """Memo must explain T-08 bloat exceeded (computed large)."""
    assert _memo_mentions("T-08", "BLOAT_THRESHOLD_EXCEEDED", "0.45", "large", "1000"), "Memo must explain T-08 bloat exceeded"


def test_memo_explains_t10():
    """Memo must explain T-10 stale statistics (reindex doesn't exempt stats)."""
    assert _memo_mentions("T-10", "STALE_STATISTICS", "31", "reindex", "stale"), "Memo must explain T-10 stale statistics"


def test_memo_explains_t11():
    """Memo must explain T-11 autovacuum overrides bloat (computed large)."""
    assert _memo_mentions("T-11", "AUTOVACUUM_DISABLED", "autovacuum", "large", "1000"), "Memo must explain T-11 autovacuum overrides bloat"


def test_memo_explains_t13():
    """Memo must explain T-13 AUTOVACUUM_DISABLED (precedence over bloat/stale).

    Only disclosed AUTOVACUUM_DISABLED evidence is required (autovacuum + size/pages);
    stale/override are not required because those rules do not decide the finding.
    """
    assert _memo_mentions("T-13", "AUTOVACUUM_DISABLED", "autovacuum", "large", "1000"), "Memo must explain T-13 autovacuum precedence"


def test_memo_explains_t18():
    """Memo must explain T-18: round-half-up makes 0.205 -> 0.21 (over large cap).

    Either the pre-round (0.205) or rounded (0.21) form is accepted as numeric evidence.
    """
    assert _memo_mentions("T-18", "BLOAT_THRESHOLD_EXCEEDED", "0.21", "round", "large"), "Memo must explain T-18 rounding"


def test_memo_explains_t19():
    """Memo must explain T-19: round-half-up makes 0.405 -> 0.41 (over large cap).

    Either the pre-round (0.405) or rounded (0.41) form is accepted as numeric evidence.
    """
    assert _memo_mentions("T-19", "BLOAT_THRESHOLD_EXCEEDED", "0.41", "large", "1000"), "Memo must explain T-19 rounding"


def test_memo_explains_t20():
    """Memo must explain T-20: manual vacuum overrides autovacuum_enabled=True."""
    assert _memo_mentions("T-20", "AUTOVACUUM_DISABLED", "manual", "vacuum", "override"), "Memo must explain T-20 manual vacuum override"


def test_memo_explains_t21():
    """Memo must explain T-21: manual vacuum overrides everything (boundary + stale + autovacuum)."""
    assert _memo_mentions("T-21", "AUTOVACUUM_DISABLED", "manual", "vacuum", "override"), "Memo must explain T-21 manual vacuum override"


def test_memo_explains_t26():
    """Memo must explain T-26: stale stats tighten cap -> BLOAT not STALE."""
    assert _memo_mentions("T-26", "BLOAT_THRESHOLD_EXCEEDED", "tighten", "0.15", "0.18"), "Memo must explain T-26"


def test_memo_explains_t27():
    """Memo must explain T-27: stale stats tighten large cap 0.2->0.15 -> BLOAT."""
    assert _memo_mentions("T-27", "BLOAT_THRESHOLD_EXCEEDED", "tighten", "0.15", "0.38"), "Memo must explain T-27"


def test_memo_explains_t29():
    """Memo must explain T-29: approved reindex but EXPIRED -> NOT exempt -> BLOAT.

    Reindex-expiry paraphrases (expired/lapsed/valid_until/approval ended/past validity) accepted.
    """
    assert _memo_mentions("T-29", "BLOAT_THRESHOLD_EXCEEDED", "reindex", "expired", "0.25"), "Memo must explain T-29"


def test_memo_explains_t30():
    """Memo must explain T-30: at original cap but stale tightens cap -> BLOAT not none."""
    assert _memo_mentions("T-30", "BLOAT_THRESHOLD_EXCEEDED", "tighten", "0.15", "effective"), "Memo must explain T-30"


def test_audit_date_sorted_order():
    """CSV rows must be sorted by last_analyzed date (ascending), then table_name."""
    import csv as csv_mod
    from datetime import datetime as dt
    path = WORKSPACE / "bloat_audit.csv"
    assert path.is_file(), "bloat_audit.csv not found"
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv_mod.DictReader(f))

    # Read table_health.csv to get last_analyzed dates
    health_path = WORKSPACE / "input" / "table_health.csv"
    assert health_path.is_file(), "table_health.csv not found"
    last_analyzed_map = {}
    with open(health_path, encoding="utf-8", newline="") as f:
        for row in csv_mod.DictReader(f):
            last_analyzed_map[row["table_name"]] = row["last_analyzed"]

    # Check that audit rows are in date-sorted order
    prev_key = None
    for row in rows:
        tid = row.get("table_name", "").strip()
        la = last_analyzed_map.get(tid, "9999-12-31")
        key = (la, tid)
        if prev_key is not None:
            assert key >= prev_key, f"Row {tid} (last_analyzed={la}) is out of order: prev={prev_key}, current={key}"
        prev_key = key


def test_memo_discusses_maintenance():
    """Memo must discuss reindex/maintenance exemption."""
    memo, err = _load_memo()
    assert err is None, err
    assert re.search(r"(?i)re-?index|maintenance|exempt", memo), "Memo must discuss reindex/maintenance exemption"


def test_memo_explains_t17():
    """Memo must explain T-17: computed large + autovacuum disabled -> AUTOVACUUM_DISABLED."""
    assert _memo_mentions("T-17", "AUTOVACUUM_DISABLED", "autovacuum", "large", "1000"), "Memo must explain T-17"


def test_memo_size_trap_t06():
    """Memo must explain T-06 size_class column is wrong, computed as large."""
    assert _memo_mentions("T-06", "BLOAT_THRESHOLD_EXCEEDED", "compute", "1000", "large"), "Memo must explain T-06 size_class trap"


def test_memo_size_trap_t14():
    """Memo must explain T-14 size_class column says small but computed as large -> BLOAT."""
    assert _memo_mentions("T-14", "BLOAT_THRESHOLD_EXCEEDED", "1000", "large", "compute"), "Memo must explain T-14 size_class trap"


def test_memo_size_trap_t27():
    """Memo must explain T-27 size_class column says small but computed as large -> BLOAT."""
    assert _memo_mentions("T-27", "BLOAT_THRESHOLD_EXCEEDED", "1000", "large", "0.15"), "Memo must explain T-27 size_class trap"


def test_memo_reindex_expiry_t16():
    """Memo must explain T-16 reindex expired -> BLOAT not exempt.

    Reindex-expiry paraphrases accepted; does not require the literal valid_until token.
    """
    assert _memo_mentions("T-16", "BLOAT_THRESHOLD_EXCEEDED", "reindex", "expired", "0.15"), "Memo must explain T-16 reindex expiry"


def test_memo_unapproved_t05():
    """Memo must explain T-05 unapproved reindex -> BLOAT.

    Requires unapproved + reindex + T-05-specific ratio evidence (0.55).
    Does NOT require both 'approved' and 'unapproved' (those patterns must stay distinct).
    """
    assert _memo_mentions("T-05", "BLOAT_THRESHOLD_EXCEEDED", "unapproved", "reindex", "0.55"), "Memo must explain T-05 unapproved reindex"


def test_memo_discusses_size_class():
    """Memo must discuss size class caps."""
    memo, err = _load_memo()
    assert err is None, err
    assert re.search(r"(?i)size[\s-]?class|large|small|cap|0\.[24]", memo), "Memo must discuss size class caps"


def test_memo_explains_t35():
    """Memo must explain T-35: size_class field small but computed large, over cap -> BLOAT."""
    assert _memo_mentions("T-35", "BLOAT_THRESHOLD_EXCEEDED", "500", "large", "compute"), "Memo must explain T-35"


def test_memo_explains_t36():
    """Memo must explain T-36: stale cap tightening, 0.18 over tightened 0.15 -> BLOAT."""
    assert _memo_mentions("T-36", "BLOAT_THRESHOLD_EXCEEDED", "tighten", "0.15", "0.18"), "Memo must explain T-36"


def test_memo_explains_t37():
    """Memo must explain T-37: reindex expired (valid_until < audit_date) -> NOT exempt -> BLOAT.

    Reindex-expiry paraphrases accepted; does not require the literal valid_until token.
    """
    assert _memo_mentions("T-37", "BLOAT_THRESHOLD_EXCEEDED", "reindex", "expired", "0.25"), "Memo must explain T-37 expired reindex"


def test_memo_explains_t39():
    """Memo must explain T-39: manual vacuum overrides autovacuum_enabled=True -> AUTOVACUUM_DISABLED."""
    assert _memo_mentions("T-39", "AUTOVACUUM_DISABLED", "manual", "vacuum", "override"), "Memo must explain T-39 manual vacuum"


def test_memo_explains_t40():
    """Memo must explain T-40: days_since_analyze field wrong, actual 35 days -> STALE_STATISTICS."""
    assert _memo_mentions("T-40", "STALE_STATISTICS", "35", "days_since_analyze", "stale"), "Memo must explain T-40 days mismatch"


def test_memo_explains_t42():
    """Memo must explain T-42: at normal cap 0.2 but stale tightens to 0.15 -> BLOAT."""
    assert _memo_mentions("T-42", "BLOAT_THRESHOLD_EXCEEDED", "tighten", "0.15", "stale"), "Memo must explain T-42"


def test_memo_explains_t44():
    """Memo must explain T-44: size_class field says medium but computed large -> BLOAT."""
    assert _memo_mentions("T-44", "BLOAT_THRESHOLD_EXCEEDED", "medium", "large", "compute"), "Memo must explain T-44 medium trap"


def test_memo_has_prose():
    """Memo must contain at least 5 explanatory prose windows that mention specific tables.

    Scoring uses the nearest sentence/bullet unit per table id (max ~300 chars).
    A valid prose window:
    - Has 10+ words
    - Is not a Markdown table / dense CSV dump / token bag
    - Mentions at least one table ID (T-XX) and a finding/maintenance keyword within
      a tight local span of that table id
    - Uses a tying verb phrase (because/since/ratio of/over the/…)

    Filler without table references does not count.
    """
    memo, err = _load_memo()
    assert err is None, err

    prose = "\n".join(_prose_lines(memo))
    text = prose if prose else memo
    assert text, "Memo has no usable prose"

    find_kw = (
        r"(?:bloat|autovacuum|stale|exceed|cap|threshold|disabled|none|"
        r"compliant|maintenance|re[\s-]?index|AUTOVACUUM_DISABLED|"
        r"BLOAT_THRESHOLD_EXCEEDED|STALE_STATISTICS)"
    )
    mentioned = set()
    for tid_m in re.finditer(r"T-\d+", text, re.I):
        tid = tid_m.group(0).upper()
        if tid in mentioned:
            continue
        for unit in _extract_table_units(text, tid):
            if len(unit.split()) < 10 or _is_token_dump(unit):
                continue
            if not re.search(
                rf"(?is)(?:{re.escape(tid)}.{{0,{_MEMO_CONCEPT_WINDOW}}}?{find_kw}|"
                rf"{find_kw}.{{0,{_MEMO_CONCEPT_WINDOW}}}?{re.escape(tid)})",
                unit,
            ):
                continue
            if not _tying_verb_phrase(unit, tid, None):
                continue
            mentioned.add(tid)
            break

    assert len(mentioned) >= 5, (
        f"Memo has only {len(mentioned)} valid prose windows mentioning tables "
        f"(need >= 5). Filler without table references does not count."
    )


def test_memo_explains_t45():
    """Memo must explain T-45: stale-tightened large cap (densify trap).

    Export size_class small is ignored; total_pages 1000 → large; 155/1000 → 0.16;
    33-day stale tightens cap to 0.15 → BLOAT_THRESHOLD_EXCEEDED.
    """
    assert _memo_mentions(
        "T-45", "BLOAT_THRESHOLD_EXCEEDED", "0.16", "0.15", "tighten", "large", "1000"
    ) or _memo_mentions(
        "T-45", "BLOAT_THRESHOLD_EXCEEDED", "0.16", "0.15", "tightened", "stale", "33"
    ), "Memo must explain T-45 stale-tighten densify trap"
