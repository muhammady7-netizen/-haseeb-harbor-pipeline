"""Fix c249 Harbor findings: bidirectional memo windows + scoring proportionality."""
from __future__ import annotations

import json
import re
from pathlib import Path

PACK = Path(
    r"C:\Users\Haseeb Mirza\Documents\Codex\2026-08-17\this-is-the-very-beginning-of"
    r"\tasks\code-c249-work\code-c249-recurring-report-source-selection-audit"
)

CONN = (
    r"\b(?:because|used|uses|using|should|instead|expected|required|"
    r"premature|reported|against|vs\.?|versus|although|while|whereas|over|"
    r"rather|pulled|kept|chose|selected|skipped|missing|empty|so|yet|"
    r"conflicts?|retained|became)\b"
)


def bidir_run_memo(run_alt: str, evs: list[str], conn: str = CONN) -> str:
    """Run-id + evidence within ~600 either order; connective within ~450 of run id."""
    # Forward: RUN then evidence (lookahead) then connective ahead
    fwd = (
        f"(?:{run_alt})"
        + "".join(f"(?=.{{0,600}}?(?:{e}))" for e in evs)
        + f".{{0,450}}?{conn}"
    )
    # Reverse / mixed: evidence may precede RUN; connective may precede or follow
    # Require a compact span containing RUN and all evidence (order-flexible via lookaheads
    # from a window anchored on RUN looking both ways — approximated with alternation).
    # Pattern: any-order co-occurrence in ~600 around RUN via:
    #   (ev...RUN|RUN...ev) combinations, plus connective near RUN.
    mid = f"(?:{run_alt})"
    # Lookbehind-ish via reverse alternatives
    rev_parts = []
    # all evidence then RUN
    chain = ".{0,600}?".join(f"(?:{e})" for e in evs) + f".{{0,600}}?(?:{run_alt})"
    rev_parts.append(chain)
    # first ev, RUN, remaining evs
    if len(evs) >= 2:
        rev_parts.append(
            f"(?:{evs[0]}).{{0,600}}?(?:{run_alt})"
            + "".join(f".{{0,600}}?(?:{e})" for e in evs[1:])
        )
        rev_parts.append(
            f"(?:{evs[1]}).{{0,600}}?(?:{run_alt}).{{0,600}}?(?:{evs[0]})"
            + "".join(f".{{0,600}}?(?:{e})" for e in evs[2:])
        )
    rev_body = "|".join(rev_parts)
    # Connective within 450 before RUN or after RUN for reverse forms
    rev = (
        f"(?:(?=.{{0,450}}?{conn}).{{0,450}}?(?:{rev_body})"
        f"|(?:{rev_body}).{{0,450}}?{conn}"
        f"|(?:{conn}).{{0,450}}?(?:{rev_body}))"
    )
    return f"(?is)(?:{fwd}|{rev})"


def bidir_missing_job() -> str:
    job = r"(?:week[\s-]ahead[\s-]briefing)"
    ev = r"(?:missing|MISSING_JOB|no\s+run|not\s+logged|absent|roster|required\s+recurring)"
    conn = (
        r"\b(?:because|but|logged|roster|required|absent|although|while|"
        r"whereas|rather|kept|chose|selected|so|yet)\b"
    )
    fwd = f"(?:{job})(?=.{{0,600}}?{ev}).{{0,450}}?{conn}"
    rev = (
        f"(?:(?=.{{0,450}}?{conn}).{{0,450}}?(?:{ev}).{{0,600}}?(?:{job})"
        f"|(?:{ev}).{{0,600}}?(?:{job}).{{0,450}}?{conn}"
        f"|(?:{conn}).{{0,450}}?(?:{ev}).{{0,600}}?(?:{job}))"
    )
    return f"(?is)(?:{fwd}|{rev})"


MEMO_SPECS = {
    "memo_tail_merge": (
        r"RUN[-*_]*\s*0?03",
        [r"(?:tail)", r"(?:merge|MISSING_TAIL_MERGE)"],
        r"\b(?:because|should|instead|expected|required|skipped|did\s+not|missing|empty|archive\s+tail|so|yet)\b",
    ),
    "memo_missing_job": None,  # special
    "memo_run10_source_mismatch_detail": (
        r"RUN[-*_]*\s*0?10",
        [r"\blive\b", r"\b(?:archive|archived|archives)\b"],
        CONN,
    ),
    "memo_run13_source_mismatch_detail": (
        r"RUN[-*_]*\s*0?13",
        [r"\blive\b", r"\b(?:archive|archived|archives)\b"],
        CONN,
    ),
    "memo_run17_source_mismatch_detail": (
        r"RUN[-*_]*\s*0?17",
        [r"\b(?:archive|archived|archives)\b", r"\blive\b"],
        CONN,
    ),
    "memo_run02_row_count_detail": (
        r"RUN[-*_]*\s*0?02",
        [r"\b388\b", r"\b395\b"],
        CONN,
    ),
    "memo_run19_row_count_detail": (
        r"RUN[-*_]*\s*0?19",
        [r"\b410\b", r"\b405\b"],
        CONN,
    ),
    "memo_run23_source_mismatch_detail": (
        r"RUN[-*_]*\s*0?23",
        [r"\b(?:archive|archived|archives)\b", r"\blive\b"],
        CONN,
    ),
    "memo_run24_source_mismatch_detail": (
        r"RUN[-*_]*\s*0?24",
        [r"\blive\b", r"\b(?:archive|archived|archives)\b"],
        CONN,
    ),
    "memo_run29_source_mismatch_detail": (
        r"RUN[-*_]*\s*0?29",
        [r"\blive\b", r"\b(?:archive|archived|archives)\b"],
        CONN,
    ),
    "memo_run33_source_mismatch_detail": (
        r"RUN[-*_]*\s*0?33",
        [r"\b(?:archive|archived|archives)\b", r"\blive\b"],
        CONN,
    ),
    "memo_run25_row_count_detail": (
        r"RUN[-*_]*\s*0?25",
        [r"\b500\b", r"\b450\b"],
        CONN,
    ),
    "memo_run35_source_mismatch_detail": (
        r"RUN[-*_]*\s*0?35",
        [r"\b(?:archive|archived|archives)\b", r"\blive\b"],
        CONN,
    ),
    "memo_run36_row_count_detail": (
        r"RUN[-*_]*\s*0?36",
        [r"\b441\b", r"\b440\b"],
        CONN,
    ),
    "memo_run37_row_count_detail": (
        r"RUN[-*_]*\s*0?37",
        [r"\b456\b", r"\b455\b"],
        CONN,
    ),
    "memo_run38_source_mismatch_detail": (
        r"RUN[-*_]*\s*0?38",
        [r"\blive\b", r"\b(?:archive|archived|archives)\b"],
        CONN,
    ),
}


def patch_verifier_json() -> None:
    path = PACK / "tests" / "verifier.json"
    spec = json.loads(path.read_text(encoding="utf-8"))
    by = {v["name"]: v for v in spec["verifiers"]}
    for name, conf in MEMO_SPECS.items():
        if name not in by:
            raise SystemExit(f"missing verifier {name}")
        if conf is None:
            pat = bidir_missing_job()
            how = (
                "Bidirectional proximity (~600 evidence / ~450 connective around "
                "week-ahead-briefing): evidence may precede or follow the job name."
            )
        else:
            run_alt, evs, conn = conf
            pat = bidir_run_memo(run_alt, evs, conn)
            how = (
                "Bidirectional proximity: run id + evidence within ~600 either order; "
                "explanatory connective within ~450 of the run id (not forward-only)."
            )
        by[name]["assertion"]["expected"] = pat
        by[name]["metadata"]["how_justification"] = how
    # Validate regexes compile
    for name in MEMO_SPECS:
        re.compile(by[name]["assertion"]["expected"])
    path.write_text(json.dumps(spec, indent=4) + "\n", encoding="utf-8")
    print(f"patched {len(MEMO_SPECS)} memo regexes in verifier.json")


def patch_test_outputs() -> None:
    path = PACK / "tests" / "test_outputs.py"
    text = path.read_text(encoding="utf-8")

    # Expand connectives
    old_conn = """_MEMO_CONNECTIVES = re.compile(
    r"(?i)\\b(?:because|used|uses|using|should|instead|expected|required|"
    r"premature|reported|against|vs\\.?|versus|although|while|whereas|over|"
    r"rather|pulled|kept|chose|selected|skipped|missing|empty)\\b"
)"""
    new_conn = """_MEMO_CONNECTIVES = re.compile(
    r"(?i)\\b(?:because|used|uses|using|should|instead|expected|required|"
    r"premature|reported|against|vs\\.?|versus|although|while|whereas|over|"
    r"rather|pulled|kept|chose|selected|skipped|missing|empty|so|yet|"
    r"conflicts?|retained|became)\\b"
)"""
    if old_conn not in text:
        raise SystemExit("connective block not found")
    text = text.replace(old_conn, new_conn)

    # Replace forward-only evidence helper with bidirectional
    old_fn = '''def _evidence_and_connective_near_run(
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
    return False'''

    new_fn = '''def _evidence_and_connective_near_run(
    memo: str,
    run_id: str,
    evidence_patterns: list[str],
) -> bool:
    """True if some run-id hit has evidence + connective + prose in a bidirectional window.

    Instruction grades 'within about 400 characters of the run id' — evidence may
    precede or follow the run id (not forward-only).
    """
    spans = _run_id_spans(memo, run_id)
    if not spans:
        return False
    for start, end in spans:
        broad = _window_around(memo, start, end, _MEMO_EVIDENCE_WINDOW)
        local = _window_around(memo, start, end, _MEMO_CONNECTIVE_WINDOW)
        if not all(re.search(p, broad, re.I | re.S) for p in evidence_patterns):
            continue
        if not _MEMO_CONNECTIVES.search(local):
            continue
        if not _has_prose_structure(local):
            continue
        return True
    return False'''

    if old_fn not in text:
        raise SystemExit("evidence helper not found")
    text = text.replace(old_fn, new_fn)

    # Fix missing-job forward-only in test_memo_flagged
    old_miss = '''    miss_ok = False
    for m in re.finditer(r"(?i)week[\\s-]ahead[\\s-]briefing", memo):
        start, end = m.start(), m.end()
        broad = memo[start : min(len(memo), start + _MEMO_EVIDENCE_WINDOW + 80)]
        forward = memo[start : min(len(memo), start + _MEMO_CONNECTIVE_WINDOW + 80)]
        if not re.search(
            r"(?i)(?:missing|MISSING_JOB|no\\s+run|not\\s+logged|absent|roster|required\\s+recurring)",
            broad,
        ):
            continue
        if not re.search(
            r"(?i)\\b(?:because|but|logged|roster|required|absent|although|while|"
            r"whereas|rather|kept|chose|selected)\\b",
            forward,
        ):
            continue
        local = _window_around(memo, start, end, _MEMO_CONNECTIVE_WINDOW)
        if _has_prose_structure(local):
            miss_ok = True
            break'''

    new_miss = '''    miss_ok = False
    for m in re.finditer(r"(?i)week[\\s-]ahead[\\s-]briefing", memo):
        start, end = m.start(), m.end()
        broad = _window_around(memo, start, end, _MEMO_EVIDENCE_WINDOW)
        local = _window_around(memo, start, end, _MEMO_CONNECTIVE_WINDOW)
        if not re.search(
            r"(?i)(?:missing|MISSING_JOB|no\\s+run|not\\s+logged|absent|roster|required\\s+recurring)",
            broad,
        ):
            continue
        if not re.search(
            r"(?i)\\b(?:because|but|logged|roster|required|absent|although|while|"
            r"whereas|rather|kept|chose|selected|so|yet)\\b",
            local,
        ):
            continue
        if _has_prose_structure(local):
            miss_ok = True
            break'''

    if old_miss not in text:
        raise SystemExit("missing-job block not found")
    text = text.replace(old_miss, new_miss)

    # Strengthen scoring proportionality in test_deliverable + identifying columns
    old_deliverable = '''def test_deliverable(definition):
    outcome = verify_definition(
        definition,
        REGISTRY,
        WEIGHTS[definition.name],
        config=SPEC.config,
        completion_fn=None,
    )["result"]
    detail = outcome.get("error") or outcome.get("reason") or "assertion failed"
    assert outcome["success"], f"{definition.name}: {detail}"'''

    new_deliverable = '''def _audit_row_count() -> int:
    path = WORKSPACE / "report_source_audit.csv"
    if not path.is_file():
        return -1
    with path.open(encoding="utf-8", newline="") as f:
        return sum(1 for _ in csv.DictReader(f))


def _memo_present() -> bool:
    return (WORKSPACE / "report_source_memo.md").is_file()


# Flagged run ids whose row_* checks also require a local memo mention (proportionality).
_FLAGGED_ROW_MEMO_CROSS = {
    "row_run-02_row_count_mismatch": "RUN-02",
    "row_run-03_missing_tail_merge": "RUN-03",
    "row_run-10_source_mismatch": "RUN-10",
    "row_run-13_source_mismatch": "RUN-13",
    "row_run-17_source_mismatch": "RUN-17",
    "row_run-19_row_count_mismatch": "RUN-19",
    "row_run-23_source_mismatch": "RUN-23",
    "row_run-24_source_mismatch": "RUN-24",
    "row_run-25_row_count_mismatch": "RUN-25",
    "row_run-29_source_mismatch": "RUN-29",
    "row_run-33_source_mismatch": "RUN-33",
    "row_run-35_source_mismatch": "RUN-35",
    "row_run-36_row_count_mismatch": "RUN-36",
    "row_run-37_row_count_mismatch": "RUN-37",
    "row_run-38_source_mismatch": "RUN-38",
    "row_missing_job_week_ahead_briefing": "week-ahead",
}


def test_deliverable(definition):
    name = definition.name
    # Central analytical rule: wrong row count fails every row_/result_ check, not just
    # audit_exactly_33_rows (scoring proportionality).
    if name.startswith("row_") or name.startswith("result_") or name == "audit_exactly_33_rows":
        n = _audit_row_count()
        assert n == 33, f"{name}: audit must have exactly 33 rows after de-dupe (got {n})"

    outcome = verify_definition(
        definition,
        REGISTRY,
        WEIGHTS[definition.name],
        config=SPEC.config,
        completion_fn=None,
    )["result"]
    detail = outcome.get("error") or outcome.get("reason") or "assertion failed"
    assert outcome["success"], f"{name}: {detail}"

    # Missing memo must also fail flagged row checks (deliverable omission is not cheap).
    if name in _FLAGGED_ROW_MEMO_CROSS:
        assert _memo_present(), f"{name}: report_source_memo.md required for flagged findings"
        memo = (WORKSPACE / "report_source_memo.md").read_text(encoding="utf-8")
        token = _FLAGGED_ROW_MEMO_CROSS[name]
        if token.startswith("RUN-"):
            n = int(token.split("-", 1)[1])
            assert re.search(rf"(?i)RUN[-*_]*\\s*0?{n}\\b", memo), (
                f"{name}: memo must name {token}"
            )
        else:
            assert re.search(r"(?i)week[\\s-]ahead", memo), (
                f"{name}: memo must name week-ahead-briefing"
            )'''

    if old_deliverable not in text:
        raise SystemExit("test_deliverable not found")
    text = text.replace(old_deliverable, new_deliverable)

    # Split identifying columns into per-row parametrized tests for proportionality
    old_id = '''def test_audit_identifying_columns_match_log():
    """Every non-MISSING_JOB audit row must carry log identifying columns after de-dupe."""
    expected = {
        r["run_id"]: r
        for r in _expected_audit_rows()
        if r["finding"] != "MISSING_JOB"
    }
    audit = _load_audit_rows()
    run_rows = [r for r in audit if (r.get("finding") or "") != "MISSING_JOB"]
    assert len(run_rows) == len(expected), (
        f"expected {len(expected)} run rows after de-dupe, got {len(run_rows)}"
    )
    for row in run_rows:
        rid = row.get("run_id") or ""
        assert rid in expected, f"unexpected run_id {rid!r}"
        gold = expected[rid]
        for col in ("job_name", "run_date", "source_used", "reported_row_count"):
            assert (row.get(col) or "") == gold[col], (
                f"{rid} {col}: audit={row.get(col)!r} expected_from_log={gold[col]!r}"
            )'''

    new_id = '''def _expected_run_ids() -> list[str]:
    return sorted(
        r["run_id"]
        for r in _expected_audit_rows()
        if r["finding"] != "MISSING_JOB"
    )


@pytest.mark.parametrize("run_id", _expected_run_ids())
def test_audit_identifying_columns_match_log(run_id: str):
    """Per-run identifying columns must match the de-duplicated log (proportional weight)."""
    expected = {
        r["run_id"]: r
        for r in _expected_audit_rows()
        if r["finding"] != "MISSING_JOB"
    }
    audit = _load_audit_rows()
    assert len([r for r in audit if (r.get("finding") or "") != "MISSING_JOB"]) == len(
        expected
    ), "de-dupe row count mismatch"
    matches = [r for r in audit if (r.get("run_id") or "") == run_id]
    assert len(matches) == 1, f"{run_id}: expected exactly one audit row"
    row = matches[0]
    gold = expected[run_id]
    for col in ("job_name", "run_date", "source_used", "reported_row_count"):
        assert (row.get(col) or "") == gold[col], (
            f"{run_id} {col}: audit={row.get(col)!r} expected_from_log={gold[col]!r}"
        )'''

    if old_id not in text:
        raise SystemExit("identifying columns test not found")
    text = text.replace(old_id, new_id)

    path.write_text(text, encoding="utf-8")
    print("patched test_outputs.py")


def patch_instruction() -> None:
    path = PACK / "instruction.md"
    text = path.read_text(encoding="utf-8")
    old = (
        "For each flagged finding, put the run ID (or missing job name) and the key "
        "evidence tokens in the **same short prose window** (same paragraph / within "
        "about 400 characters of the run id), not scattered as a bare token list across "
        "the file."
    )
    new = (
        "For each flagged finding, put the run ID (or missing job name) and the key "
        "evidence tokens in the **same short prose window** (same paragraph / within "
        "about 400–600 characters of the run id, **either before or after** the run id — "
        "clause order does not matter), not scattered as a bare token list across "
        "the file."
    )
    if old not in text:
        print("WARN: instruction window wording not found exactly; skipping")
        return
    path.write_text(text.replace(old, new), encoding="utf-8")
    print("patched instruction.md")


if __name__ == "__main__":
    patch_verifier_json()
    patch_test_outputs()
    patch_instruction()
    print("done")
