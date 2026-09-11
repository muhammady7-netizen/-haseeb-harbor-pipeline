#!/usr/bin/env python3
"""Fix code-c249 Harbor Delivery Gate: memo window fairness + trajectory + cache."""
from __future__ import annotations

import csv
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PACK = Path(
    r"C:\Users\Haseeb Mirza\Documents\Codex\2026-08-17"
    r"\this-is-the-very-beginning-of\tasks\code-c249-work"
    r"\code-c249-recurring-report-source-selection-audit"
)

# ~400-500 disclosed window; pick mid so "few hundred" / ~400 chars match.
CONNECTIVE_WINDOW = 450
EVIDENCE_WINDOW = 600

OLD_CONN = (
    r"because|used|uses|using|should|instead|expected|"
    r"required|premature|reported|against|vs\.?|versus"
)
NEW_CONN = (
    r"because|used|uses|using|should|instead|expected|"
    r"required|premature|reported|against|vs\.?|versus|"
    r"although|while|whereas|over|rather|"
    r"pulled|kept|chose|selected|skipped|missing|empty"
)

# Also used by memo_tail_merge / memo_missing_job (were 200)
OLD_TAIL_CONN = (
    r"because|should|instead|expected|required|skipped|did\\s+not|missing|empty|archive\\s+tail"
)
NEW_TAIL_CONN = (
    r"because|should|instead|expected|required|skipped|did\\s+not|missing|empty|"
    r"archive\\s+tail|although|while|whereas|rather|pulled|kept|chose|selected|used"
)
OLD_MISS_CONN = r"because|but|logged|roster|required|absent"
NEW_MISS_CONN = (
    r"because|but|logged|roster|required|absent|"
    r"although|while|whereas|rather|kept|chose|selected"
)


def delete_pytest_cache() -> None:
    cache = PACK / ".pytest_cache"
    if cache.exists():
        shutil.rmtree(cache)
        print("deleted", cache)
    else:
        print("no .pytest_cache")


def write_gitignore() -> None:
    path = PACK / ".gitignore"
    lines = [
        ".pytest_cache/",
        "__pycache__/",
        "*.py[cod]",
        ".mypy_cache/",
        ".ruff_cache/",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote .gitignore")


def update_golden_trajectory() -> None:
    path = PACK / "solution" / "golden_trajectory.json"
    payload = {
        "schema_version": "ATIF-v1.7",
        "agent": {"name": "oracle", "version": "harbor-0.21"},
        "steps": [
            {
                "step_id": 1,
                "source": "user",
                "message": (
                    "Audit recurring reporting pipeline against source-selection "
                    "standard (REPORTING-OPS-2)."
                ),
            },
            {
                "step_id": 2,
                "source": "oracle",
                "message": (
                    "Load standard and run log; parse 34 physical log rows; collapse "
                    "duplicate RUN-29/RUN-35/RUN-37 by ordered finding-precedence "
                    "(non-none over none, then live over archive on ties) → 31 unique "
                    "run_ids; add MISSING_JOB for week-ahead-briefing → 32 audit rows."
                ),
            },
            {
                "step_id": 3,
                "source": "oracle",
                "message": (
                    "Apply weekly cutover (2026-07-06 inclusive archive), row-count "
                    "consistency (empty snapshot=skip), monthly tail-merge for first "
                    "post-cutover monthly (RUN-03), ordered finding-precedence de-dupe."
                ),
            },
            {
                "step_id": 4,
                "source": "oracle",
                "message": (
                    "Wrote report_source_audit.csv (exact header + 32 newline-terminated "
                    "rows), memo explaining all 15 findings with local connective prose, "
                    "results.json (flagged=15, source_mismatch=8, row_count=5, "
                    "tail_merge=1, missing_job=1). 59 graded checks."
                ),
            },
        ],
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    # Align companion golden_results if needed
    gr = PACK / "solution" / "golden_results.json"
    expected = {
        "flagged_count": 15,
        "source_mismatch_count": 8,
        "row_count_mismatch_count": 5,
        "missing_tail_merge_count": 1,
        "missing_job_count": 1,
    }
    gr.write_text(json.dumps(expected, indent=2) + "\n", encoding="utf-8")
    print("updated golden_trajectory.json + golden_results.json")


def update_instruction() -> None:
    path = PACK / "instruction.md"
    text = path.read_text(encoding="utf-8")
    old = (
        "For each flagged finding, put the run ID (or missing job name) and the key "
        "evidence tokens in the **same short prose window** (roughly the same paragraph "
        "/ within a few hundred characters)—not scattered as a bare token list across "
        "the file. Use explanatory connective wording such as *because*, *used*, "
        "*should*, *instead*, *expected*, or *reported*. Token-only dumps without that "
        "connective prose do not satisfy the memo checks."
    )
    new = (
        "For each flagged finding, put the run ID (or missing job name) and the key "
        "evidence tokens in the **same short prose window** (same paragraph / within "
        "about 400 characters of the run id)—not scattered as a bare token list across "
        "the file. Use explanatory connective wording such as *because*, *used*, "
        "*should*, *instead*, *expected*, *reported*, *although*, *while*, *whereas*, "
        "*rather*, *over*, *pulled*, *kept*, *chose*, or *selected*. Write real sentences "
        "with normal verbs and punctuation; space-separated token dumps do not satisfy "
        "the memo checks."
    )
    if old not in text:
        if "within about 400 characters of the run id" in text:
            print("instruction.md already updated")
            return
        raise SystemExit("instruction.md memo style block not found")
    path.write_text(text.replace(old, new), encoding="utf-8")
    print("updated instruction.md")


def _patch_expected(expected: str) -> str:
    """Widen connective proximity and expand whitelist in a memo regex."""
    out = expected
    # Detail checks used 160; tail/missing used 200
    out = out.replace(".{0,160}?", f".{{0,{CONNECTIVE_WINDOW}}}?")
    out = out.replace(".{0,200}?", f".{{0,{CONNECTIVE_WINDOW}}}?")
    if OLD_CONN in out:
        out = out.replace(OLD_CONN, NEW_CONN)
    if OLD_TAIL_CONN in out:
        out = out.replace(OLD_TAIL_CONN, NEW_TAIL_CONN)
    out = out.replace(
        r"\b(?:because|but|logged|roster|required|absent)\b",
        rf"\b(?:{NEW_MISS_CONN})\b",
    )
    return out


def update_verifier() -> int:
    path = PACK / "tests" / "verifier.json"
    spec = json.loads(path.read_text(encoding="utf-8"))
    n_patched = 0
    for v in spec["verifiers"]:
        name = v.get("name", "")
        if not name.startswith("memo_"):
            continue
        if name in {"memo_exists", "memo_substantive_body"}:
            continue
        how = v.get("metadata", {}).get("how_justification", "")
        expected = v["assertion"]["expected"]
        new_expected = _patch_expected(expected)
        if new_expected != expected:
            v["assertion"]["expected"] = new_expected
            n_patched += 1
        # Refresh how_justification window wording
        how2 = how
        how2 = re.sub(r"within\s*~?\s*160", f"within ~{CONNECTIVE_WINDOW}", how2)
        how2 = re.sub(r"within\s*~?\s*200", f"within ~{CONNECTIVE_WINDOW}", how2)
        how2 = how2.replace("~160", f"~{CONNECTIVE_WINDOW}").replace(
            "~200", f"~{CONNECTIVE_WINDOW}"
        )
        if "Proximity+prose:" in how2 and "prose-structure" not in how2.lower():
            how2 = how2.rstrip(".") + (
                f". Connective+evidence co-located with run id; graded prose "
                f"structure enforced in test_outputs.py."
            )
        v["metadata"]["how_justification"] = how2
    path.write_text(json.dumps(spec, indent=4) + "\n", encoding="utf-8")
    print(f"patched {n_patched} memo regexes in verifier.json; total={len(spec['verifiers'])}")
    return len(spec["verifiers"])


def patch_test_outputs() -> None:
    path = PACK / "tests" / "test_outputs.py"
    text = path.read_text(encoding="utf-8")
    if "_MEMO_CONNECTIVE_WINDOW" in text and "test_memo_flagged_findings_local_prose" in text:
        print("test_outputs.py already has memo prose helpers")
        return

    if "\nimport re\n" not in text:
        text = text.replace(
            "import csv\nimport os\nimport sys\n",
            "import csv\nimport os\nimport re\nimport sys\n",
            1,
        )

    marker = "def test_missing_job_row_empty_identifying_fields"
    insert_at = text.find(marker)
    if insert_at < 0:
        raise SystemExit("could not find insertion point in test_outputs.py")

    helpers = r'''
# Memo fairness: evidence + connective co-located with run id; real prose, not token soup.
_MEMO_CONNECTIVE_WINDOW = 450
_MEMO_EVIDENCE_WINDOW = 600
_MEMO_CONNECTIVES = re.compile(
    r"(?i)\b(?:because|used|uses|using|should|instead|expected|required|"
    r"premature|reported|against|vs\.?|versus|although|while|whereas|over|"
    r"rather|pulled|kept|chose|selected|skipped|missing|empty)\b"
)
_MEMO_PROSE_GLUE = re.compile(
    r"(?i)\b(?:the|a|an|of|for|from|with|that|this|was|were|is|are|on|to|by|"
    r"as|into|than|then|but|and|or|its|their|which|when|where|who|whom)\b"
)
_MEMO_PUNCT = re.compile(r"[,.:;!?()\[\]\—\–\-`]")

_DUMP_VOCAB = {
    "run", "source", "mismatch", "row", "count", "missing", "tail", "merge",
    "job", "live", "archive", "archived", "archives", "none", "finding",
    "because", "used", "uses", "using", "should", "instead", "expected",
    "required", "premature", "reported", "against", "vs", "versus",
    "although", "while", "whereas", "over", "rather", "pulled", "kept",
    "chose", "selected", "snapshot", "cutover", "weekly", "monthly",
    "journal", "brief", "ahead", "briefing", "report", "and", "or", "the",
}


def _load_memo_text() -> str:
    path = WORKSPACE / "report_source_memo.md"
    assert path.is_file(), "report_source_memo.md missing"
    return path.read_text(encoding="utf-8")


def _run_id_spans(memo: str, run_id: str) -> list[tuple[int, int]]:
    n = int(run_id.split("-", 1)[1])
    pat = re.compile(rf"(?i)RUN[-*_]*\s*0?{n}\b")
    return [(m.start(), m.end()) for m in pat.finditer(memo)]


def _window_around(memo: str, start: int, end: int, radius: int) -> str:
    lo = max(0, start - radius)
    hi = min(len(memo), end + radius)
    return memo[lo:hi]


def _has_prose_structure(window: str) -> bool:
    """Reject space-separated token soup; require punctuation + grammatical glue."""
    words = re.findall(r"[A-Za-z0-9']+", window)
    if len(words) < 8:
        return False
    if not _MEMO_PUNCT.search(window):
        return False
    glue = sum(1 for w in words if _MEMO_PROSE_GLUE.fullmatch(w))
    if glue < 2:
        return False
    contentish = [
        w
        for w in words
        if w.lower() not in _DUMP_VOCAB
        and not w.isdigit()
        and not re.fullmatch(r"(?i)run-?\d+", w)
    ]
    if len(contentish) < 3:
        return False
    return True


def _evidence_and_connective_near_run(
    memo: str,
    run_id: str,
    evidence_patterns: list[str],
) -> bool:
    """True if some run-id hit has evidence + connective + prose in the local window."""
    spans = _run_id_spans(memo, run_id)
    if not spans:
        return False
    for start, end in spans:
        forward = memo[start : min(len(memo), start + _MEMO_CONNECTIVE_WINDOW + 80)]
        broad = memo[start : min(len(memo), start + _MEMO_EVIDENCE_WINDOW + 80)]
        if not all(re.search(p, broad, re.I | re.S) for p in evidence_patterns):
            continue
        if not _MEMO_CONNECTIVES.search(forward):
            continue
        local = _window_around(memo, start, end, _MEMO_CONNECTIVE_WINDOW)
        if not _has_prose_structure(local):
            continue
        return True
    return False


'''

    new_test = r'''

# Flagged-finding memo windows (shared with verifier proximity intent).
_FLAGGED_MEMO_CASES = [
    ("RUN-10", [r"\blive\b", r"\b(?:archive|archived|archives)\b"]),
    ("RUN-13", [r"\blive\b", r"\b(?:archive|archived|archives)\b"]),
    ("RUN-17", [r"\b(?:archive|archived|archives)\b", r"\blive\b"]),
    ("RUN-23", [r"\b(?:archive|archived|archives)\b", r"\blive\b"]),
    ("RUN-24", [r"\blive\b", r"\b(?:archive|archived|archives)\b"]),
    ("RUN-29", [r"\blive\b", r"\b(?:archive|archived|archives)\b"]),
    ("RUN-33", [r"\b(?:archive|archived|archives)\b", r"\blive\b"]),
    ("RUN-35", [r"\b(?:archive|archived|archives)\b", r"\blive\b"]),
    ("RUN-02", [r"\b388\b", r"\b395\b"]),
    ("RUN-19", [r"\b410\b", r"\b405\b"]),
    ("RUN-25", [r"\b500\b", r"\b450\b"]),
    ("RUN-36", [r"\b441\b", r"\b440\b"]),
    ("RUN-37", [r"\b456\b", r"\b455\b"]),
    ("RUN-03", [r"(?i)tail", r"(?i)(?:merge|MISSING_TAIL_MERGE)"]),
]


def test_memo_flagged_findings_local_prose():
    """Each flagged run must have evidence+connective in a prose window near the run id.

    Strengthens verifier.json proximity regexes: rejects content-free whitelist token
    dumps even when connective tokens are present. Gold natural prose must still pass.
    """
    memo = _load_memo_text()
    failures = []
    for run_id, patterns in _FLAGGED_MEMO_CASES:
        if not _evidence_and_connective_near_run(memo, run_id, patterns):
            failures.append(run_id)
    # Missing job: job name + paraphrase + connective + prose
    miss_ok = False
    for m in re.finditer(r"(?i)week[\s-]ahead[\s-]briefing", memo):
        start, end = m.start(), m.end()
        broad = memo[start : min(len(memo), start + _MEMO_EVIDENCE_WINDOW + 80)]
        forward = memo[start : min(len(memo), start + _MEMO_CONNECTIVE_WINDOW + 80)]
        if not re.search(
            r"(?i)(?:missing|MISSING_JOB|no\s+run|not\s+logged|absent|roster|required\s+recurring)",
            broad,
        ):
            continue
        if not re.search(
            r"(?i)\b(?:because|but|logged|roster|required|absent|although|while|"
            r"whereas|rather|kept|chose|selected)\b",
            forward,
        ):
            continue
        local = _window_around(memo, start, end, _MEMO_CONNECTIVE_WINDOW)
        if _has_prose_structure(local):
            miss_ok = True
            break
    if not miss_ok:
        failures.append("week-ahead-briefing")
    assert not failures, (
        "memo lacks local evidence+connective prose for: " + ", ".join(failures)
    )
'''

    if "_MEMO_CONNECTIVE_WINDOW" not in text:
        text = text[:insert_at] + helpers + "\n" + text[insert_at:]
    if "test_memo_flagged_findings_local_prose" not in text:
        text = text.rstrip() + "\n" + new_test + "\n"

    path.write_text(text, encoding="utf-8")
    print("patched test_outputs.py with memo prose helpers + test")


def remove_memo_substantive_body() -> None:
    """Drop weak file-level sentence check; replaced by per-finding prose gate (keep 59)."""
    path = PACK / "tests" / "verifier.json"
    spec = json.loads(path.read_text(encoding="utf-8"))
    before = len(spec["verifiers"])
    spec["verifiers"] = [
        v for v in spec["verifiers"] if v.get("name") != "memo_substantive_body"
    ]
    after = len(spec["verifiers"])
    path.write_text(json.dumps(spec, indent=4) + "\n", encoding="utf-8")
    print(f"removed memo_substantive_body: {before} -> {after}")


def update_review() -> None:
    path = PACK / "review.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8", newline="")))
    fieldnames = list(rows[0].keys())

    def set_row(check: str, **kwargs) -> None:
        for r in rows:
            if r["review_check"] == check:
                r.update(kwargs)
                return
        rows.append({"review_check": check, **kwargs})

    set_row(
        "Layer 1 - Clarity and scope",
        status="FIXED_AND_VERIFIED",
        review_notes=(
            "Memo proximity disclosed as ~400 chars of the run id (same paragraph); "
            "connective whitelist expanded (although/while/whereas/over/rather/pulled/"
            "kept/chose/selected); graded checks use ~450-char connective window. "
            "Prose-structure gate requires punctuation + grammatical glue so token dumps fail."
        ),
        change_made=(
            "Widened verifier connective window 160→450; expanded whitelist; updated "
            "instruction.md; added test_memo_flagged_findings_local_prose helpers."
        ),
        what_to_record=(
            "instruction.md Memo explanation style; verifier.json memo_* windows; "
            "tests/test_outputs.py prose gate."
        ),
    )
    set_row(
        "Layer 2 Difficulty",
        status="NEEDS_RERUN",
        review_notes=(
            "Prior sub-1.0 GLM trials were memo-window brittleness (connective at "
            "194–236 chars vs 160-char matcher). Window widened + whitelist expanded; "
            "will re-run GLM×4 after this fix. Do not invent GLM evals."
        ),
        change_made=(
            "Fairness fix for memo proximity; left evaluations/glm-5.2 for parent re-run."
        ),
        what_to_record="Parent re-run Harbor GLM×4 after memo-window fix.",
    )
    set_row(
        "Layer 5 - Verifier coverage and fairness",
        status="FIXED_AND_VERIFIED",
        review_notes=(
            "Connective proximity now ~450 chars (disclosed ~400); evidence remains "
            "~600. Per-finding memo prose gate in test_outputs.py rejects whitelist "
            "token-soup while gold and natural long-paragraph memos pass. Removed "
            "redundant memo_substantive_body to keep 56 verifier + 3 pytest = 59."
        ),
        change_made=(
            "verifier.json window+whitelist; test_outputs.py local prose gate; "
            "golden_trajectory densified; deleted .pytest_cache."
        ),
        what_to_record="59 checks; memo fairness fixed; trajectory+cache cleaned.",
    )
    set_row(
        "Layer 5 - Reward hacking and exploitability",
        status="FIXED_AND_VERIFIED",
        review_notes=(
            "Content-free connective/evidence token dumps no longer score: require "
            "evidence+connective in the same local window as the run id AND "
            "sentence-like prose (punctuation + glue words + non-dump content)."
        ),
        change_made="Strengthened memo checks with shared prose helpers in test_outputs.py.",
        what_to_record="Token-soup counterfactual fails; gold still 59/59.",
    )
    set_row(
        "Layer 1 - Package consistency",
        status="FIXED_AND_VERIFIED",
        review_notes=(
            "Densified pack: 34 log / 31 unique / 32 audit; results 15/8/5/1/1; 59 checks. "
            "golden_trajectory.json updated to match; .pytest_cache deleted and gitignored."
        ),
        change_made="Regenerated golden_trajectory; removed .pytest_cache; added .gitignore.",
        what_to_record="solution/golden_trajectory.json; .gitignore excludes .pytest_cache.",
    )

    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print("updated review.csv")


def update_readme(v_count: int) -> None:
    path = PACK / "README.md"
    text = path.read_text(encoding="utf-8")
    total = v_count + 3  # 2 original field tests + 1 memo prose test
    # Soft replace the verifier paragraph if present
    new_para = (
        f"{total} graded pytest checks: {v_count} deterministic assertions in "
        f"`tests/verifier.json` (file existence, unique-run finding rows + missing-job "
        f"row, `audit_exactly_32_rows`, proximity+prose memo checks with ~450-char "
        f"connective window including densify traps RUN-35/36/37, five `results.json` "
        f"equals checks) plus 3 checks in `tests/test_outputs.py` (identifying columns, "
        f"MISSING_JOB empty fields, per-finding local memo prose gate). Fractional "
        f"reward via pytest passed/total.\n"
    )
    if "## Verifier" in text:
        # replace from ## Verifier through next ## or end densify notes carefully
        import re as _re

        text2 = _re.sub(
            r"## Verifier\n\n.*?(?=\nDensify notes|\n## |\Z)",
            "## Verifier\n\n" + new_para + "\n",
            text,
            count=1,
            flags=_re.S,
        )
        path.write_text(text2, encoding="utf-8")
        print("updated README.md verifier section", total)
    else:
        print("README.md missing Verifier section; skipped")


def verify_gold_and_counterfactuals() -> None:
    """Gold 59/59; token-soup fails; long-paragraph (~200 char connective) passes."""
    gold_files = PACK / "solution" / "files"
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        for f in gold_files.iterdir():
            shutil.copy2(f, td_path / f.name)
        inp = td_path / "input"
        inp.mkdir()
        shutil.copy2(
            PACK / "environment" / "input" / "report_run_log.csv",
            inp / "report_run_log.csv",
        )
        shutil.copy2(
            PACK / "environment" / "input" / "report_source_standard.md",
            inp / "report_source_standard.md",
        )
        env = {**dict(os.environ), "HARBOR_TASK_WORKSPACE": str(td_path)}
        r = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                str(PACK / "tests" / "test_outputs.py"),
                "-q",
                "--tb=line",
            ],
            cwd=str(PACK),
            env=env,
            capture_output=True,
            text=True,
        )
        out = (r.stdout or "") + (r.stderr or "")
        print("=== GOLD PYTEST ===")
        print(out[-2500:] if len(out) > 2500 else out)
        if r.returncode != 0:
            raise SystemExit("GOLD FAILED")

    with tempfile.TemporaryDirectory() as td2:
        td2p = Path(td2)
        for f in gold_files.iterdir():
            shutil.copy2(f, td2p / f.name)
        (td2p / "input").mkdir()
        shutil.copy2(
            PACK / "environment" / "input" / "report_run_log.csv",
            td2p / "input" / "report_run_log.csv",
        )
        os.environ["HARBOR_TASK_WORKSPACE"] = str(td2p)

        spec = importlib.util.spec_from_file_location(
            "c249_tests", PACK / "tests" / "test_outputs.py"
        )
        mod = importlib.util.module_from_spec(spec)
        # Avoid collecting pytest during import side effects — module defines tests only
        spec.loader.exec_module(mod)

        gold_memo = (td2p / "report_source_memo.md").read_text(encoding="utf-8")
        assert mod._evidence_and_connective_near_run(
            gold_memo, "RUN-10", [r"\blive\b", r"\b(?:archive|archived|archives)\b"]
        ), "gold RUN-10 should pass"

        # Token soup: whitelist dump
        soup = (
            "RUN-10 live archive used should because expected reported against vs "
            "SOURCE_MISMATCH RUN-13 live archive used should because expected "
            "RUN-17 archive live used should because "
            "RUN-02 388 395 used should because reported "
            "RUN-19 410 405 used should because "
            "RUN-25 500 450 used should because "
            "RUN-23 archive live used should "
            "RUN-24 live archive used should "
            "RUN-29 live archive used should "
            "RUN-33 archive live used should "
            "RUN-35 archive live used should "
            "RUN-36 441 440 used should because "
            "RUN-37 456 455 used should because "
            "RUN-03 tail merge MISSING_TAIL_MERGE skipped because "
            "week-ahead-briefing missing MISSING_JOB roster required because logged"
        )
        soup_fail = 0
        for rid, pats in mod._FLAGGED_MEMO_CASES:
            if not mod._evidence_and_connective_near_run(soup, rid, pats):
                soup_fail += 1
        print(f"token-soup failures: {soup_fail}/{len(mod._FLAGGED_MEMO_CASES)} (want all fail)")
        assert soup_fail == len(mod._FLAGGED_MEMO_CASES), "token soup must fail all"

        # Natural long paragraph: connective ~200 chars from run id
        pad = "x" * 180
        long_para = (
            f"For RUN-10 {pad} the job used live on the cutover date when archive "
            f"was required, so this is SOURCE_MISMATCH because the recorded source "
            f"does not match the weekly cutover rule."
        )
        # Measure connective offset
        m = re.search(r"RUN-10", long_para)
        fwd = long_para[m.start() :]
        cm = mod._MEMO_CONNECTIVES.search(fwd)
        print("long-para first connective", cm.group(0), "at", cm.start())
        assert cm.start() >= 160, "test setup should place connective beyond old 160"
        assert cm.start() <= 450
        assert mod._evidence_and_connective_near_run(
            long_para, "RUN-10", [r"\blive\b", r"\b(?:archive|archived|archives)\b"]
        ), "long-paragraph memo must pass"
        print("long-paragraph PASS")

        # GLM-like r3 RUN-29 sentence (connective 'used' at ~200)
        glm29 = (
            "RUN-29 is a weekly-journal-brief run dated 2026-06-20 whose log carried "
            "two rows for the same run ID; the `live` row was kept over the compliant "
            "`archive` row by finding-precedence, and that kept row used `live`, but "
            "because the date is on or before the 2026-07-06 cutover it should have "
            "used `archive` instead."
        )
        assert mod._evidence_and_connective_near_run(
            glm29, "RUN-29", [r"\blive\b", r"\b(?:archive|archived|archives)\b"]
        ), "GLM-like RUN-29 must pass after widen"
        print("GLM-like RUN-29 PASS")

    print("ALL COUNTERFACTUAL CHECKS OK")


def main() -> None:
    delete_pytest_cache()
    write_gitignore()
    update_golden_trajectory()
    update_instruction()
    update_verifier()
    patch_test_outputs()
    remove_memo_substantive_body()
    v_count = len(json.loads((PACK / "tests" / "verifier.json").read_text(encoding="utf-8"))["verifiers"])
    update_readme(v_count)
    update_review()
    verify_gold_and_counterfactuals()
    print("DONE v_count", v_count, "total_expected", v_count + 3)


if __name__ == "__main__":
    main()
