"""Repair v17 gold: remove FORCE_AT_ODDS corruption; recompute from disclosed RP-405 limb rules."""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

PACK = Path("task-sources/law-b39/law-b39-l16-custody-letter-instruction-audit-v17")

CL = {
    "addressee": "CL-301",
    "request": "CL-302",
    "enclosure": "CL-303",
    "salutation": "CL-304",
    "copies": "CL-305",
    "delivery": "CL-306",
}
OI = {
    "addressee": "OI-201",
    "right_of_first_refusal": "OI-202",
    "children_named": "OI-203",
    "overnight_stays": "OI-204",
    "inconsistent_accounts": "OI-205",
    "concern": "OI-206",
    "behavioural_plan": "OI-207",
    "request": "OI-208",
    "enclosure": "OI-209",
    "tone": "OI-210",
    "sender_signature": "OI-211",
}


def governor(subject: str) -> str:
    if subject in CL:
        return CL[subject]
    if subject in OI:
        return OI[subject]
    return "NONE"


def position_matches(subject: str, wording: str, gov: str) -> bool:
    """True when line position matches governing entry under RP-405 limb rules."""
    w = wording.lower()
    if gov == "NONE":
        return False
    # Cross-subject wording traps: wording is about a different disclosed subject than the row's subject
    # Detect when wording clearly matches another subject's canonical content while subject differs.
    if subject == "request" and ("post to counsel" in w or "by post" in w) and "overnight" not in w:
        return False
    if subject == "addressee" and ("do not copy" in w or "nobody" in w) and "attorney" not in w and "father" not in w and "mother" not in w and "catherine" not in w and "adam" not in w:
        return False
    if subject == "delivery" and w.strip().startswith("dear counsel"):
        return False
    if subject == "copies" and "custodial plan is enclosed" in w:
        return False

    if gov.startswith("CL-"):
        rules = {
            "CL-301": lambda: (("mother" in w or "catherine" in w) and "attorney" in w),
            "CL-302": lambda: "overnight" in w and ("father" in w or "adler" in w or "present" in w),
            "CL-303": lambda: "enclosed" in w and ("custodial" in w or "certified" in w),
            "CL-304": lambda: "dear counsel" in w,
            "CL-305": lambda: (
                ("do not copy" in w or "not copy anyone" in w or "nobody" in w or "no copy" in w)
                and "enclosed" not in w
            ),
            "CL-306": lambda: "post" in w and "counsel" in w,
        }
        fn = rules.get(gov)
        return bool(fn and fn())

    # Original multi-limb subjects (disclosed in OI + RP-405)
    if gov == "OI-205":
        return (
            "neighbour" in w
            and "school" in w
            and ("clinician" in w or "clinicians" in w)
            and ("sitter" in w or "babysitter" in w)
            and ("wife" in w)
            and ("partner" in w)
        )
    if gov == "OI-204":
        return "sitter" in w and "home" in w and ("several" in w or "occasions" in w)
    if gov == "OI-206":
        if "no concern" in w or "not concerned" in w:
            return False
        return (("violate" in w) or ("order" in w)) and ("position" in w)
    if gov == "OI-207":
        return "confidence" in w and "stability" in w and (
            "set it back" in w or "set back" in w or "setback" in w
        )
    if gov == "OI-210":
        return ("soft" in w) and ("formal" in w) and ("succinct" in w)
    if gov == "OI-202":
        return "first refusal" in w or ("not to be left overnight" in w)
    if gov == "OI-211":
        return "delphine" in w or "marr" in w or "own name" in w
    if gov == "OI-209":
        return "enclosed" in w and ("custodial" in w or "certified" in w)
    if gov == "OI-208":
        return "overnight" in w and ("father" in w or "adler" in w or "present" in w)
    if gov == "OI-201":
        return ("father" in w or "adler" in w) and "attorney" in w
    if gov == "OI-203":
        return None  # signal: keep prior verdict
    return None


def main() -> None:
    lines = list(csv.DictReader((PACK / "environment/input/letter_lines.csv").open(encoding="utf-8")))
    old_gold = {
        r["line_id"]: r
        for r in csv.DictReader((PACK / "solution/files/letter_line_review.csv").open(encoding="utf-8"))
    }

    new_gold = []
    changes = []
    for L in lines:
        lid = L["line_id"]
        sub = L["subject"]
        gov = governor(sub)
        old = old_gold[lid]
        if gov == "NONE":
            verdict, entry = "NOT_IN_RECORD", "NONE"
        else:
            entry = gov
            match = position_matches(sub, L["wording"], gov)
            if match is None:
                # keep prior verdict if governor already correct; else force AT_ODDS under correct gov
                if old["record_entry"] == gov:
                    verdict = old["verdict"]
                    if verdict == "NOT_IN_RECORD":
                        verdict = "AT_ODDS"
                else:
                    verdict = old["verdict"] if old["verdict"] != "NOT_IN_RECORD" else "AT_ODDS"
                    entry = gov
            else:
                verdict = "VERIFIED" if match else "AT_ODDS"
        if old["verdict"] != verdict or old["record_entry"] != entry:
            changes.append((lid, old["verdict"], verdict, old["record_entry"], entry, L["wording"][:80]))
        new_gold.append({"line_id": lid, "verdict": verdict, "record_entry": entry})

    # Sanity: identical (subject, wording) → identical verdict
    from collections import defaultdict

    groups = defaultdict(list)
    by_id = {r["line_id"]: r for r in lines}
    gmap = {r["line_id"]: r for r in new_gold}
    for L in lines:
        groups[(L["subject"], L["wording"].strip())].append(L["line_id"])
    contra = 0
    for _, lids in groups.items():
        vs = {gmap[i]["verdict"] for i in lids}
        if len(lids) > 1 and len(vs) > 1:
            contra += 1
            print("STILL CONTRA", lids, vs)
    assert contra == 0, contra

    V = sum(1 for r in new_gold if r["verdict"] == "VERIFIED")
    A = sum(1 for r in new_gold if r["verdict"] == "AT_ODDS")
    N = sum(1 for r in new_gold if r["verdict"] == "NOT_IN_RECORD")
    C = sum(1 for r in new_gold if r["record_entry"].startswith("CL-"))
    print(f"changes {len(changes)}  counts V={V} A={A} N={N} CL={C} n={len(new_gold)}")
    for c in changes[:40]:
        print(c)
    if len(changes) > 40:
        print(f"... +{len(changes)-40} more")

    # Write gold CSV
    with (PACK / "solution/files/letter_line_review.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["line_id", "verdict", "record_entry"])
        w.writeheader()
        w.writerows(new_gold)

    results = {
        "verified_count": V,
        "at_odds_count": A,
        "not_in_record_count": N,
        "clarification_governed_count": C,
    }
    (PACK / "solution/files/results.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    (PACK / "solution/golden_results.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")

    # answer.md — keep structure, rewrite figures
    answer_path = PACK / "solution/files/answer.md"
    answer = answer_path.read_text(encoding="utf-8")
    answer = re.sub(r"verified_count\s*[:=]\s*\d+", f"verified_count: {V}", answer, flags=re.I)
    answer = re.sub(r"at_odds_count\s*[:=]\s*\d+", f"at_odds_count: {A}", answer, flags=re.I)
    answer = re.sub(r"not_in_record_count\s*[:=]\s*\d+", f"not_in_record_count: {N}", answer, flags=re.I)
    answer = re.sub(
        r"clarification_governed_count\s*[:=]\s*\d+",
        f"clarification_governed_count: {C}",
        answer,
        flags=re.I,
    )
    # prose figure
    answer = re.sub(
        r"(Letter lines at odds with the record[:\s*]*)(\d+)",
        rf"\g<1>{A}",
        answer,
        count=1,
        flags=re.I,
    )
    # common patterns like **124** or : 124
    answer = re.sub(
        r"(at odds[^\n]{0,60}?)(\d{2,3})",
        lambda m: m.group(1) + str(A) if "record" in m.group(0).lower() or "odds" in m.group(0).lower() else m.group(0),
        answer,
        count=3,
        flags=re.I,
    )
    answer_path.write_text(answer, encoding="utf-8")

    # Patch verifier.json register_table + results_figures
    ver_path = PACK / "tests/verifier.json"
    ver = json.loads(ver_path.read_text(encoding="utf-8"))
    order = [r["line_id"] for r in lines]
    row_set = [
        {
            "line_id": r["line_id"],
            "verdict": r["verdict"],
            "record_entry": r["record_entry"],
        }
        for r in new_gold
    ]
    for v in ver["verifiers"]:
        if v["name"] == "register_table":
            v["assertion"]["expected"]["row_set"] = row_set
            v["assertion"]["expected"]["row_set_ordered"] = True
            if "description" in v:
                v["description"] = re.sub(r"\d+-row", f"{len(row_set)}-row", v["description"])
        if v["name"] == "results_figures":
            v["assertion"]["expected"] = results
        if v["name"] == "answer_at_odds_figure":
            # keep regex; ensure gold answer matches
            pat = v["assertion"]["expected"]
            if not re.search(pat, answer_path.read_text(encoding="utf-8")):
                print("WARN answer_at_odds_figure regex may not match; pat=", pat)
    ver_path.write_text(json.dumps(ver, indent=2) + "\n", encoding="utf-8")

    # README counts
    readme = (PACK / "README.md").read_text(encoding="utf-8")
    readme = re.sub(
        r"\d+ verified / \d+ at_odds / \d+ not_in_record / \d+ clarification-governed",
        f"{V} verified / {A} at_odds / {N} not_in_record / {C} clarification-governed",
        readme,
    )
    (PACK / "README.md").write_text(readme, encoding="utf-8")

    # Also fix test_outputs if it embeds counts
    top = PACK / "tests/test_outputs.py"
    if top.exists():
        t = top.read_text(encoding="utf-8")
        t2 = t
        # best-effort replace common literals
        t2 = re.sub(r"verified_count.?\s*==\s*\d+", f"verified_count\"] == {V}", t2)
        if t2 != t:
            print("test_outputs touched — review manually")

    print("DONE", results)


if __name__ == "__main__":
    main()
