"""Fix ST-354 / ST-134 gold defects + sync counts + trajectory + classifiers."""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

PACK = Path("task-sources/law-b39/law-b39-l16-custody-letter-instruction-audit-v17")


def main() -> None:
    gold_path = PACK / "solution/files/letter_line_review.csv"
    rows = list(csv.DictReader(gold_path.open(encoding="utf-8")))
    by = {r["line_id"]: r for r in rows}

    for lid in ("ST-354", "ST-134"):
        print(lid, "before", by[lid])
        assert by[lid]["verdict"] == "VERIFIED", by[lid]
        by[lid]["verdict"] = "AT_ODDS"
        print(lid, "after", by[lid])

    for r in rows:
        r["verdict"] = by[r["line_id"]]["verdict"]
        r["record_entry"] = by[r["line_id"]]["record_entry"]

    V = sum(1 for r in rows if r["verdict"] == "VERIFIED")
    A = sum(1 for r in rows if r["verdict"] == "AT_ODDS")
    N = sum(1 for r in rows if r["verdict"] == "NOT_IN_RECORD")
    C = sum(1 for r in rows if r["record_entry"].startswith("CL-"))
    print("counts", V, A, N, C)
    assert (V, A, N, C) == (85, 156, 49, 168), (V, A, N, C)

    with gold_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["line_id", "verdict", "record_entry"])
        w.writeheader()
        w.writerows(rows)

    results = {
        "verified_count": V,
        "at_odds_count": A,
        "not_in_record_count": N,
        "clarification_governed_count": C,
    }
    (PACK / "solution/files/results.json").write_text(
        json.dumps(results, indent=2) + "\n", encoding="utf-8"
    )
    (PACK / "solution/golden_results.json").write_text(
        json.dumps(results, indent=2) + "\n", encoding="utf-8"
    )

    ans_path = PACK / "solution/files/answer.md"
    ans = ans_path.read_text(encoding="utf-8")
    ans = re.sub(
        r"(Letter lines at odds with the record:\s*)\d+",
        rf"\g<1>{A}",
        ans,
        count=1,
    )
    ans_path.write_text(ans, encoding="utf-8")

    ver = json.loads((PACK / "tests/verifier.json").read_text(encoding="utf-8"))
    order = [r["line_id"] for r in rows]
    for v in ver["verifiers"]:
        if v["name"] == "register_table":
            exp = v["assertion"]["expected"]
            exp["rows"] = {
                r["line_id"]: {"verdict": r["verdict"], "record_entry": r["record_entry"]}
                for r in rows
            }
            exp["row_set"] = order
            exp["row_set_ordered"] = True
        if v["name"] == "results_figures":
            keys = v["assertion"]["expected"]["keys"]
            keys["verified_count"]["value"] = V
            keys["at_odds_count"]["value"] = A
            keys["not_in_record_count"]["value"] = N
            keys["clarification_governed_count"]["value"] = C
        if v["name"] == "answer_at_odds_figure":
            v["assertion"]["expected"] = (
                rf"(?is)Letter\s+lines\s+at\s+odds\s+with\s+the\s+record\s*:\s*"
                rf"(?:\*\*|__|\*)?(?:{A}|{A}\.0|{A}\.00)(?:\*\*|__|\*)?(?!\d)"
            )
    (PACK / "tests/verifier.json").write_text(json.dumps(ver, indent=2) + "\n", encoding="utf-8")

    readme = (PACK / "README.md").read_text(encoding="utf-8")
    readme = re.sub(
        r"\d+ verified / \d+ at_odds / \d+ not_in_record / \d+ clarification-governed",
        f"{V} verified / {A} at_odds / {N} not_in_record / {C} clarification-governed",
        readme,
    )
    (PACK / "README.md").write_text(readme, encoding="utf-8")

    # Fix golden_trajectory count drift (PreQC D21)
    gt_path = PACK / "solution/golden_trajectory.json"
    gto = json.loads(gt_path.read_text(encoding="utf-8"))

    def walk(o):
        if isinstance(o, dict):
            return {k: walk(v) for k, v in o.items()}
        if isinstance(o, list):
            return [walk(x) for x in o]
        if isinstance(o, str):
            s = o
            s = re.sub(r"verified_count\s*[:=]\s*\d+", f"verified_count: {V}", s)
            s = re.sub(r"at_odds_count\s*[:=]\s*\d+", f"at_odds_count: {A}", s)
            s = re.sub(r"not_in_record_count\s*[:=]\s*\d+", f"not_in_record_count: {N}", s)
            s = re.sub(
                r"clarification_governed_count\s*[:=]\s*\d+",
                f"clarification_governed_count: {C}",
                s,
            )
            s = re.sub(
                r"Letter lines at odds with the record:\s*\d+",
                f"Letter lines at odds with the record: {A}",
                s,
            )
            # JSON snippets inside strings
            s = re.sub(r'"verified_count"\s*:\s*\d+', f'"verified_count": {V}', s)
            s = re.sub(r'"at_odds_count"\s*:\s*\d+', f'"at_odds_count": {A}', s)
            s = re.sub(r'"not_in_record_count"\s*:\s*\d+', f'"not_in_record_count": {N}', s)
            s = re.sub(
                r'"clarification_governed_count"\s*:\s*\d+',
                f'"clarification_governed_count": {C}',
                s,
            )
            return s
        return o

    gto = walk(gto)
    gt_path.write_text(json.dumps(gto, indent=2) + "\n", encoding="utf-8")

    # Patch classifiers in harden script so future recomputes don't regress
    h = Path("tmp-pw/harden_b39_v18_max.py")
    txt = h.read_text(encoding="utf-8")
    old_cl303 = '''    if governor == "CL-303":
        return has(w, "certified") and any_has(w, "custodial plan", "custody plan") and any_has(
            w, "enclos", "enclosed", "enclose"
        )'''
    new_cl303 = '''    if governor == "CL-303":
        # "uncertified" contains substring "certified" — require word-boundary certified, reject uncertified
        wl = w.lower()
        return (
            re.search(r"(?<![a-z])certified(?![a-z])", wl) is not None
            and "uncertified" not in wl
            and any_has(w, "custodial plan", "custody plan")
            and any_has(w, "enclos", "enclosed", "enclose")
        )'''
    if old_cl303 in txt:
        txt = txt.replace(old_cl303, new_cl303)
    old_oi202 = '''    if governor == "OI-202":
        return (
            any_has(w, "right of first refusal")
            and any_has(w, "father", "mr adler")
            and any_has(w, "overnight")
            and any_has(w, "agreed", "agree")
            and not any_has(w, "ms corwin agreed", "mother agreed")
        )'''
    new_oi202 = '''    if governor == "OI-202":
        # Must state the overnight restriction (not permitted without him). Reversals like
        # "overnight stays without him are still permitted" are AT_ODDS.
        wl = w.lower()
        if any_has(w, "still permitted", "are permitted", "may stay overnight without"):
            return False
        return (
            any_has(w, "right of first refusal")
            and any_has(w, "father", "mr adler")
            and any_has(w, "overnight")
            and any_has(w, "agreed", "agree")
            and ("not" in wl or "without him" in wl or "without the father" in wl)
            and not any_has(w, "ms corwin agreed", "mother agreed")
        )'''
    if old_oi202 in txt:
        txt = txt.replace(old_oi202, new_oi202)
    # ensure `re` imported in harden file
    if "import re" not in txt.split("def has")[0]:
        txt = txt.replace("from __future__ import annotations\n", "from __future__ import annotations\n\nimport re\n", 1)
    h.write_text(txt, encoding="utf-8")

    # Sanity: classifiers agree
    import sys

    sys.path.insert(0, "tmp-pw")
    import harden_b39_v18_max as v18

    lines = {r["line_id"]: r for r in csv.DictReader((PACK / "environment/input/letter_lines.csv").open(encoding="utf-8"))}
    for lid in ("ST-354", "ST-134"):
        v, e = v18.classify(lines[lid]["subject"], lines[lid]["wording"])
        print("classifier", lid, v, e, lines[lid]["wording"][:80])
        assert v == "AT_ODDS", (lid, v, e)

    print("DONE", results)


if __name__ == "__main__":
    main()
