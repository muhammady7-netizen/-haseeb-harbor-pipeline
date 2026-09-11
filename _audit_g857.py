"""Audit gen-g857 pack for Harbor regressions after final polish."""
from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(r"C:/Users/Haseeb Mirza/Documents/Codex/haseeb-pipeline")
C = ROOT / "qc-out/ework/gen-g857-portal/gen-g857-department-directory-categorization-audit"

issues: list[str] = []
notes: list[str] = []

# --- inputs ---
inputs = sorted(p.name for p in (C / "environment/input").iterdir() if p.is_file())
print("INPUTS:", inputs)
expected_inputs = {"g857_crosswalk.csv", "g857_people.csv", "g857_taxonomy.json"}
if set(inputs) != expected_inputs:
    issues.append(f"unexpected inputs: {inputs}")

# input row counts
people_n = sum(1 for _ in open(C / "environment/input/g857_people.csv", encoding="utf-8")) - 1
cross_n = sum(1 for _ in open(C / "environment/input/g857_crosswalk.csv", encoding="utf-8")) - 1
tax = json.loads((C / "environment/input/g857_taxonomy.json").read_text(encoding="utf-8"))
tax_n = len(tax) if isinstance(tax, list) else len(tax.get("departments", tax.get("codes", tax)))
print(f"input counts people={people_n} crosswalk={cross_n} taxonomy_entries={tax_n}")

# --- weights from verifier / test.sh ---
vj = json.loads((C / "tests/verifier.json").read_text(encoding="utf-8"))
weights = {v["name"]: float(v.get("weight", 0)) for v in vj["verifiers"]}
by_family = Counter()
for name, w in weights.items():
    if "unmapped" in name:
        fam = "unmapped"
    elif "headcount" in name or "hc_" in name:
        fam = "headcount"
    elif "mapping" in name or "map_" in name or "status" in name or "crosswalk" in name:
        fam = "mappings"
    else:
        fam = "other"
    by_family[fam] += w
print("weight families:", dict(by_family), "total", sum(weights.values()))
for fam, target, lo, hi in [
    ("mappings", 0.40, 0.30, 0.50),
    ("headcount", 0.35, 0.25, 0.45),
    ("unmapped", 0.10, 0.05, 0.20),
]:
    w = by_family[fam]
    print(f"  {fam}: {w:.4f} (target~{target})")
    if not (lo <= w <= hi):
        issues.append(f"weight family {fam}={w:.4f} outside [{lo},{hi}]")

# test.sh reward formula sniff
test_sh = (C / "tests/test.sh").read_text(encoding="utf-8")
if "passed/total" in test_sh.replace(" ", "") or "passed / total" in test_sh:
    # flat might be ok if weights unused — check
    if "weight" not in test_sh.lower() and "weighted" not in test_sh.lower():
        notes.append("test.sh may be flat passed/total — check if Harbor wants weighted")
print("test.sh has weight:", "weight" in test_sh.lower())

# --- gold artifacts ---
gold_map = C / "solution/files/g857_mappings.csv"
gold_un = C / "solution/files/g857_unmapped.csv"
gold_hc = C / "solution/files/g857_headcount.json"
print("gold present", gold_map.exists(), gold_un.exists(), gold_hc.exists())

with gold_un.open(encoding="utf-8", newline="") as f:
    gold_unmapped_rows = list(csv.DictReader(f))
gold_un_depts = {r.get("department") or r.get("dept") or r.get("source_department") or str(r) for r in gold_unmapped_rows}
print(f"gold unmapped rows={len(gold_unmapped_rows)}")

# invented dept sniff on gold
invented_pat = re.compile(r"Unknown\s*Dept|PX\d{2,}|FABRICATED|placeholder", re.I)
for r in gold_unmapped_rows:
    blob = " ".join(str(v) for v in r.values())
    if invented_pat.search(blob):
        issues.append(f"gold unmapped looks invented: {r}")

# --- per-run checks ---
runs = ["r1", "r2", "r3", "r4"]
art_names = ["g857_mappings.csv", "g857_unmapped.csv", "g857_headcount.json"]
hashes: dict[str, dict[str, str]] = {}
rewards: dict[str, float] = {}

for r in runs:
    rdir = C / f"evaluations/glm-5.2/{r}"
    arts = {n: (rdir / "artifacts" / n).read_bytes() for n in art_names}
    hashes[r] = {n: hashlib.sha256(b).hexdigest()[:16] for n, b in arts.items()}
    sizes = {n: len(b) for n, b in arts.items()}

    rj = json.loads((rdir / "result.json").read_text(encoding="utf-8"))
    reward = float(rj["verifier_result"]["rewards"]["reward"])
    rewards[r] = reward
    start = rj.get("started_at")
    finish = rj.get("finished_at")

    traj_text = (rdir / "agent/trajectory.json").read_text(encoding="utf-8")
    traj = json.loads(traj_text)

    flags = []
    # wrong / ghost names
    for bad in ["critical_results", "converted_fields.csv", "pdf_form", "people.csv", "taxonomy.json", "crosswalk.csv"]:
        # allow g857_people etc; flag bare names without g857_
        if bad in traj_text and f"g857_{bad}" not in traj_text and bad not in ("people.csv", "taxonomy.json", "crosswalk.csv"):
            flags.append(f"ghost:{bad}")
    for bare in ["people.csv", "taxonomy.json", "crosswalk.csv"]:
        if bare in traj_text and f"g857_{bare}" not in traj_text:
            # check if mentioned as basename wrongly
            if re.search(rf"(?<!g857_){re.escape(bare)}", traj_text):
                flags.append(f"bare_input:{bare}")

    for iname in expected_inputs:
        if iname not in traj_text:
            flags.append(f"missing_input_mention:{iname}")

    if "/tmp/" in traj_text and "cp /tmp" in traj_text:
        flags.append("tmp_copy")

    # size consistency
    for n, sz in sizes.items():
        if str(sz) not in traj_text:
            flags.append(f"missing_size_{n}_{sz}")

    # invented depts in unmapped artifact
    with (rdir / "artifacts/g857_unmapped.csv").open(encoding="utf-8", newline="") as f:
        urows = list(csv.DictReader(f))
    invented = []
    for row in urows:
        blob = " ".join(str(v) for v in row.values())
        if invented_pat.search(blob):
            invented.append(blob[:80])
    if invented and r != "r2":  # any invented is bad except if intentional fail — still Harbor hates fabricated
        flags.append(f"invented_unmapped:{invented[:3]}")

    # r4 special: should have correct unmapped + broken headcount (from polish intent)
    if r == "r4":
        # compare unmapped to gold
        gold_bytes = gold_un.read_bytes()
        un_bytes = arts["g857_unmapped.csv"]
        # normalize newlines for compare
        if gold_bytes.replace(b"\r\n", b"\n") != un_bytes.replace(b"\r\n", b"\n"):
            # allow if same rows different order
            with gold_un.open(encoding="utf-8", newline="") as f:
                gset = {tuple(sorted(row.items())) for row in csv.DictReader(f)}
            uset = {tuple(sorted(row.items())) for row in urows}
            if gset != uset:
                flags.append("r4_unmapped_!=_gold")
            else:
                notes.append("r4 unmapped rows match gold (order may differ)")
        else:
            notes.append("r4 unmapped == gold bytes")
        hc = json.loads(arts["g857_headcount.json"])
        # expect some zeroed / wrong headcount
        print(f"  r4 headcount sample keys={list(hc)[:5] if isinstance(hc, dict) else type(hc)}")

    # reward vs reward.txt
    rt = (rdir / "verifier/reward.txt").read_text(encoding="utf-8").strip()
    try:
        if abs(float(rt) - reward) > 1e-9:
            flags.append(f"reward_mismatch_txt:{rt} vs {reward}")
    except ValueError:
        flags.append(f"bad_reward_txt:{rt!r}")

    # timestamps round?
    if start and start.endswith("T00:00:00.000000Z"):
        flags.append("round_midnight_start")
    if start and re.search(r"T\d{2}:00:00\.000000Z$", start or ""):
        notes.append(f"{r} start on the hour: {start}")

    print(f"{r} reward={reward:.6f} start={start} sizes={sizes} flags={flags or 'ok'}")
    for f in flags:
        if f.startswith("missing_size") or f.startswith("bare_input") or f.startswith("invented") or f.startswith("r4_") or f.startswith("reward") or f.startswith("ghost") or f.startswith("tmp") or f.startswith("missing_input"):
            issues.append(f"{r}: {f}")

# uniqueness of artifacts across runs
for n in art_names:
    hs = [hashes[r][n] for r in runs]
    print(f"unique {n}: {len(set(hs))}/4 -> {dict(zip(runs, hs))}")
    if len(set(hs)) < 3:
        notes.append(f"low diversity on {n}: only {len(set(hs))} unique")

# oracle vs r1
o_map = (C / "evaluations/oracle/artifacts/g857_mappings.csv").read_bytes()
r1_map = (C / "evaluations/glm-5.2/r1/artifacts/g857_mappings.csv").read_bytes()
print("oracle mappings == r1?", o_map == r1_map)
print("oracle == gold?", o_map == gold_map.read_bytes())
if o_map == r1_map:
    # Harbor often wants oracle identical to gold and r1 can equal oracle for pass — ok
    notes.append("oracle mappings == r1 (pass clone — usually OK if both match gold)")

# r1 should be near 1.0
if rewards["r1"] < 0.999:
    issues.append(f"r1 reward not perfect: {rewards['r1']}")
if rewards["r1"] <= max(rewards[r] for r in ["r2", "r3", "r4"]):
    # r1 should be highest
    if rewards["r1"] < 1.0 - 1e-9:
        issues.append("r1 not clearly best pass")

# fail runs should be < 1
for r in ["r2", "r3", "r4"]:
    if rewards[r] >= 0.999:
        issues.append(f"{r} unexpectedly perfect reward")

# review.csv
rev = (C / "review.csv").read_text(encoding="utf-8", errors="replace")
print("review.csv lines", len(rev.splitlines()))

# instruction mentions
instr = (C / "instruction.md").read_text(encoding="utf-8")
for token in ["no_pipe", "unmapped", "headcount", "g857_"]:
    if token not in instr and token != "g857_":
        notes.append(f"instruction missing token? {token}")

print("\n=== ISSUES ===")
for i in issues:
    print("!", i)
print("=== NOTES ===")
for n in notes:
    print("-", n)
print("summary:", f"{len(issues)} issues, {len(notes)} notes")
