"""Cross-check v18 harden against QC/fairness guidelines."""
from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path

p = Path("task-sources/law-b39/law-b39-l16-custody-letter-instruction-audit-v18")
rows = list(csv.DictReader(open(p / "environment/input/letter_lines.csv", encoding="utf-8")))
gold = list(csv.DictReader(open(p / "solution/files/letter_line_review.csv", encoding="utf-8")))
gb = {r["line_id"]: r for r in gold}
oi = (p / "environment/input/original_instruction.md").read_text(encoding="utf-8")
cl = (p / "environment/input/clarification.md").read_text(encoding="utf-8")
proto = (p / "environment/input/review_protocol.md").read_text(encoding="utf-8")
fmt = (p / "environment/input/submission_format.md").read_text(encoding="utf-8")
instr = (p / "instruction.md").read_text(encoding="utf-8")
ver = json.loads((p / "tests/verifier.json").read_text(encoding="utf-8"))
results = json.loads((p / "solution/files/results.json").read_text(encoding="utf-8"))
answer = (p / "solution/files/answer.md").read_text(encoding="utf-8")
readme = (p / "README.md").read_text(encoding="utf-8")
toml = (p / "task.toml").read_text(encoding="utf-8")

findings = []


def ok(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail else ""))
    if not cond:
        findings.append(name)


print("=== PACKAGE / COUNTS ===")
V = sum(1 for g in gold if g["verdict"] == "VERIFIED")
A = sum(1 for g in gold if g["verdict"] == "AT_ODDS")
N = sum(1 for g in gold if g["verdict"] == "NOT_IN_RECORD")
C = sum(1 for g in gold if g["record_entry"].startswith("CL-"))
ok("line/gold length equal", len(rows) == len(gold) == 290, f"lines={len(rows)}")
ok(
    "results.json matches table counts",
    results
    == {
        "verified_count": V,
        "at_odds_count": A,
        "not_in_record_count": N,
        "clarification_governed_count": C,
    },
    str(results),
)

oi_subs = set(re.findall(r"## OI-\d+ `([^`]+)`", oi))
cl_subs = set(re.findall(r"## CL-\d+ `([^`]+)`", cl))
draft_subs = set(r["subject"] for r in rows)
ok("no alias NIR subjects", not draft_subs & {"delivery_method", "carbon_copy_recipients"})
ok(
    "CL-307/308/309 present in clarification",
    {"tone", "behavioural_plan", "concern"}.issubset(cl_subs),
    f"CL subjects={sorted(cl_subs)}",
)

print("\n=== GOVERNANCE (RP-401/403/404) ===")
bad_gov = []
for r in rows:
    g = gb[r["line_id"]]
    sub = r["subject"]
    if sub in cl_subs:
        if not g["record_entry"].startswith("CL-"):
            bad_gov.append((r["line_id"], sub, g))
    elif sub in oi_subs:
        if not g["record_entry"].startswith("OI-"):
            bad_gov.append((r["line_id"], sub, g))
    else:
        if g["verdict"] != "NOT_IN_RECORD" or g["record_entry"] != "NONE":
            bad_gov.append((r["line_id"], sub, g))
ok("every row governor matches subject coverage", not bad_gov, f"bad={len(bad_gov)}")

soft_v = [
    r["line_id"]
    for r in rows
    if r["subject"] == "tone"
    and gb[r["line_id"]]["verdict"] == "VERIFIED"
    and "soft" in r["wording"].lower()
]
ok("no soft-tone VERIFIED under CL-307", not soft_v, str(soft_v))

both_v = []
for r in rows:
    if r["subject"] != "concern":
        continue
    if gb[r["line_id"]]["verdict"] != "VERIFIED":
        continue
    w = r["wording"].lower()
    if ("violate" in w or "order" in w) and "position" in w:
        both_v.append(r["line_id"])
ok("no both-limb concern VERIFIED under CL-309", not both_v, str(both_v))

print("\n=== VERIFIER / KEY ALIGNMENT ===")
rt = next(v for v in ver["verifiers"] if v["name"] == "register_table")
exp_rows = rt["assertion"]["expected"]["rows"]
exp_set = rt["assertion"]["expected"]["row_set"]
mism = [
    lid
    for lid, g in gb.items()
    if exp_rows.get(lid) != {"verdict": g["verdict"], "record_entry": g["record_entry"]}
]
ok("verifier table == gold csv", not mism, f"mismatches={len(mism)}")
ok("row_set == letter order", exp_set == [r["line_id"] for r in rows])
rf = next(v for v in ver["verifiers"] if v["name"] == "results_figures")
keys = {k: rf["assertion"]["expected"]["keys"][k]["value"] for k in rf["assertion"]["expected"]["keys"]}
ok(
    "results_figures == counts",
    keys
    == {
        "verified_count": V,
        "at_odds_count": A,
        "not_in_record_count": N,
        "clarification_governed_count": C,
    },
    str(keys),
)
pat = next(v for v in ver["verifiers"] if v["name"] == "answer_at_odds_figure")["assertion"]["expected"]
ok("answer.md matches at-odds figure regex", bool(re.search(pat, answer)))

print("\n=== DISCLOSURE / NO HIDDEN RULES ===")
ok("instruction points at protocol+records", all(x in instr for x in ["review_protocol", "clarification", "original_instruction", "letter_lines"]))
ok("submission_format discloses record vocab", "record" in fmt.lower())
ok("submission_format allows mid-paragraph figure", "mid" in fmt.lower() or "anywhere" in fmt.lower())
ok("protocol states narrower = AT_ODDS", "narrower" in proto.lower())
ok("clarification text states new governors", "CL-307" in cl and "CL-308" in cl and "CL-309" in cl)
ok("README line count mentions current size", "290" in readme or "draft lines" in readme.lower())

print("\n=== LEAKAGE ===")
agent_visible = list((p / "environment").rglob("*")) + [p / "instruction.md", p / "task.toml"]
leak = []
for path in agent_visible:
    if not path.is_file():
        continue
    if path.suffix.lower() not in {".md", ".csv", ".json", ".txt", ".toml"}:
        continue
    t = path.read_text(encoding="utf-8", errors="ignore")
    if path.name == "letter_lines.csv" and ("VERIFIED" in t or "AT_ODDS" in t):
        leak.append(str(path))
    if "letter_line_review.csv" in path.name and "environment" in str(path):
        leak.append(str(path))
ok("no gold table in agent-visible inputs", not leak, str(leak))
ok("gold only under solution/", (p / "solution/files/letter_line_review.csv").exists())

print("\n=== VERIFIER STRUCTURE ===")
tags = {v["name"]: v["metadata"].get("tag") for v in ver["verifiers"]}
for name, tag in tags.items():
    print(f"  {name}: {tag}")
incidental = [n for n, t in tags.items() if t == "incidental"]
ok("structured grading on CSV/JSON present", "register_table" in tags and "results_figures" in tags)
print(f"  note: incidental checks = {incidental} (north-star prefers all-core; pack historically keeps 2 incidental)")

print("\n=== FAIRNESS / AMBIGUITY SPOT-CHECKS ===")
# Keyword classifier risk: copies VERIFIED requires negative words; edge cases
edge = []
for r in rows:
    g = gb[r["line_id"]]
    if r["subject"] == "copies" and g["verdict"] == "VERIFIED":
        if not any(x in r["wording"].lower() for x in ("nobody", "no one", "do not copy", "not copy", "no copy")):
            edge.append(r["line_id"])
ok("copies VERIFIED rows have clear no-copy wording", not edge, str(edge))

# NIR subjects not near-aliases of covered
near = [s for s in (draft_subs - oi_subs - cl_subs) if any(k in s for k in ("deliver", "cop", "enclos", "address", "tone"))]
ok("uncovered subjects not near-aliases of covered", not near, str(near))

print("\n=== DIFFICULTY EVIDENCE (PRIOR + CURRENT) ===")
print("  prior 138-line GLM: 4/4 (too easy)")
print("  prior 207-line GLM: 4/4 (too easy)")
print("  v18 GLM: not run yet")
print("  guideline target: <=2/4 (ideally 0-1/4); <=50% pass rate")

print("\n=== SOLVABILITY ===")
ok("solve.sh present", (p / "solution/solve.sh").exists())
ok("oracle not packed on v18 yet", not (p / "evaluations/oracle").exists())

print("\n===== SUMMARY =====")
if findings:
    print("FAILS:", len(findings))
    for f in findings:
        print(" -", f)
else:
    print("Static guideline cross-check: no FAIL items.")
print("WARN: incidental verifiers remain; v18 needs oracle+GLM before ship.")
