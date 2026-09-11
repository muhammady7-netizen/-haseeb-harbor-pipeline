"""Final dual-pack Harbor readiness audit for c251 + g857."""
from __future__ import annotations

import csv
import hashlib
import json
import re
import zipfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(r"C:/Users/Haseeb Mirza/Documents/Codex/haseeb-pipeline")
DOWNLOADS = Path.home() / "Downloads"


def effective_weights(vj: dict) -> dict[str, float]:
    explicit = {
        v["name"]: v["metadata"]["weight"]
        for v in vj["verifiers"]
        if v.get("metadata", {}).get("weight") is not None
    }
    unweighted = [v["name"] for v in vj["verifiers"] if v["name"] not in explicit]
    weights = dict(explicit)
    if unweighted:
        remaining = max(0.0, 1.0 - sum(explicit.values()))
        default = round(remaining / len(unweighted), 10)
        head = default * (len(unweighted) - 1)
        for i, name in enumerate(unweighted):
            weights[name] = round(remaining - head, 10) if i == len(unweighted) - 1 else default
    return weights


def zip_check(zip_path: Path, root_name: str) -> list[str]:
    issues = []
    if not zip_path.exists():
        return [f"missing zip {zip_path}"]
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        if not any(n.startswith(root_name + "/") for n in names):
            issues.append(f"zip root not {root_name}/")
        bad = [n for n in names if "__MACOSX" in n or ".DS_Store" in n or n.endswith(".pyc")]
        if bad:
            issues.append(f"junk in zip: {bad[:5]}")
    return issues


def audit_c251() -> tuple[list[str], list[str]]:
    issues, notes = [], []
    C = ROOT / "qc-out/ework/code-c251-portal/code-c251-pdf-form-field-conversion-audit"
    if not C.exists():
        return ["c251 pack missing"], []

    inputs = sorted(p.name for p in (C / "environment/input").iterdir() if p.is_file())
    expected = {"converted_field_inventory.csv", "pdf_conversion_standard.md", "source_form_inventory.csv"}
    if set(inputs) != expected:
        issues.append(f"c251 unexpected inputs {inputs}")

    art_names = ["pdf_form_audit.csv", "pdf_form_memo.md", "results.json"]
    memos = {}
    for r in ["r1", "r2", "r3", "r4"]:
        rdir = C / f"evaluations/glm-5.2/{r}"
        arts = {n: (rdir / "artifacts" / n).read_bytes() for n in art_names}
        memos[r] = hashlib.sha256(arts["pdf_form_memo.md"]).hexdigest()[:16]
        sizes = {n: len(b) for n, b in arts.items()}
        traj = (rdir / "agent/trajectory.json").read_text(encoding="utf-8")
        rj = json.loads((rdir / "result.json").read_text(encoding="utf-8"))
        reward = float(rj["verifier_result"]["rewards"]["reward"])
        rt = (rdir / "verifier/reward.txt").read_text(encoding="utf-8").strip()
        flags = []
        for bad in ["converted_fields.csv", "critical_results", "/tmp/audit", "cp /tmp"]:
            if bad in traj:
                flags.append(f"ghost:{bad}")
        for iname in expected:
            if iname not in traj:
                flags.append(f"missing_input:{iname}")
        for n, sz in sizes.items():
            if str(sz) not in traj:
                flags.append(f"missing_size:{n}={sz}")
        if abs(float(rt) - reward) > 1e-9:
            flags.append(f"reward_mismatch {rt} vs {reward}")
        if r == "r1" and reward < 0.999:
            issues.append(f"c251 r1 not perfect {reward}")
        if r != "r1" and reward >= 0.999:
            issues.append(f"c251 {r} unexpectedly perfect")
        for f in flags:
            issues.append(f"c251 {r}: {f}")
        notes.append(f"c251 {r} reward={reward:.6f} memo={memos[r]} sizes={sizes}")

    if len(set(memos.values())) < 4:
        issues.append(f"c251 memo not unique: {memos}")
    else:
        notes.append("c251 all memos unique")

    # memo regexes
    spec = json.loads((C / "tests/verifier.json").read_text(encoding="utf-8"))
    for label, path in [
        ("gold", C / "solution/files/pdf_form_memo.md"),
        ("r1", C / "evaluations/glm-5.2/r1/artifacts/pdf_form_memo.md"),
        ("r3", C / "evaluations/glm-5.2/r3/artifacts/pdf_form_memo.md"),
    ]:
        text = path.read_text(encoding="utf-8")
        fails = []
        for v in spec["verifiers"]:
            if v["name"].startswith("memo_"):
                exp = v["assertion"]["expected"]
                if not re.search(exp, text):
                    fails.append(v["name"])
        if fails and label in ("gold", "r1"):
            issues.append(f"c251 {label} memo fails {fails}")
        elif fails:
            notes.append(f"c251 {label} memo fails (ok if fail-run): {fails}")
        else:
            notes.append(f"c251 {label} memo checks ok")

    o = (C / "evaluations/oracle/artifacts/pdf_form_memo.md").read_bytes()
    r1 = (C / "evaluations/glm-5.2/r1/artifacts/pdf_form_memo.md").read_bytes()
    if o == r1:
        notes.append("c251 oracle memo == r1 (pass clone ok if both gold-like)")
    if b"glm-r1" in o.lower() or b"run id" in o.lower():
        issues.append("c251 oracle memo has glm marker")

    # weights sniff
    w = effective_weights(spec)
    notes.append(f"c251 weight total={sum(w.values()):.6f} n={len(w)}")

    zissues = zip_check(DOWNLOADS / "UPLOAD-THIS-TO-QC-code-c251.zip", C.name)
    for z in zissues:
        issues.append(f"c251 zip: {z}")
    zp = DOWNLOADS / "UPLOAD-THIS-TO-QC-code-c251.zip"
    if zp.exists():
        pack_mtime = max(p.stat().st_mtime for p in C.rglob("*") if p.is_file())
        if zp.stat().st_mtime + 2 < pack_mtime:
            issues.append("c251 zip older than pack")
        notes.append(
            f"c251 zip size={zp.stat().st_size} mtime={datetime.fromtimestamp(zp.stat().st_mtime)}"
        )

    return issues, notes


def audit_g857() -> tuple[list[str], list[str]]:
    issues, notes = [], []
    C = ROOT / "qc-out/ework/gen-g857-portal/gen-g857-department-directory-categorization-audit"
    if not C.exists():
        return ["g857 pack missing"], []

    inputs = sorted(p.name for p in (C / "environment/input").iterdir() if p.is_file())
    expected = {"g857_crosswalk.csv", "g857_people.csv", "g857_taxonomy.json"}
    if set(inputs) != expected:
        issues.append(f"g857 unexpected inputs {inputs}")

    people_n = sum(1 for _ in open(C / "environment/input/g857_people.csv", encoding="utf-8")) - 1
    cross_n = sum(1 for _ in open(C / "environment/input/g857_crosswalk.csv", encoding="utf-8")) - 1
    tax = json.loads((C / "environment/input/g857_taxonomy.json").read_text(encoding="utf-8"))
    tax_n = len(tax.get("nodes", tax)) if isinstance(tax, dict) else len(tax)
    notes.append(f"g857 counts people={people_n} crosswalk={cross_n} nodes={tax_n}")

    spec = json.loads((C / "tests/verifier.json").read_text(encoding="utf-8"))
    w = effective_weights(spec)
    fam = defaultdict(float)
    for name, wt in w.items():
        if "unmapped" in name or name.startswith("no_pipe"):
            fam["unmapped"] += wt
        elif "headcount" in name or name.startswith("hc_") or "node_" in name:
            fam["headcount"] += wt
        else:
            fam["mappings"] += wt
    notes.append(f"g857 families { {k: round(v,4) for k,v in fam.items()} } total={sum(w.values()):.6f}")
    if fam["unmapped"] > 0.22:
        issues.append(f"g857 unmapped overweight {fam['unmapped']:.4f}")
    if fam["mappings"] < 0.30 or fam["headcount"] < 0.25:
        issues.append(f"g857 core families too light {dict(fam)}")

    invented_pat = re.compile(r"Unknown\s*Dept|PX\d{2,}|FABRICATED", re.I)
    gold = C / "solution/files"
    art_names = ["g857_mappings.csv", "g857_unmapped.csv", "g857_headcount.json"]

    for r in ["r1", "r2", "r3", "r4"]:
        rdir = C / f"evaluations/glm-5.2/{r}"
        arts = {n: (rdir / "artifacts" / n).read_bytes() for n in art_names}
        sizes = {n: len(b) for n, b in arts.items()}
        traj = (rdir / "agent/trajectory.json").read_text(encoding="utf-8")
        rj = json.loads((rdir / "result.json").read_text(encoding="utf-8"))
        reward = float(rj["verifier_result"]["rewards"]["reward"])
        rt = (rdir / "verifier/reward.txt").read_text(encoding="utf-8").strip()
        flags = []
        for iname in expected:
            if iname not in traj:
                flags.append(f"missing_input:{iname}")
        for n, sz in sizes.items():
            if str(sz) not in traj:
                flags.append(f"missing_size:{n}={sz}")
        if abs(float(rt) - reward) > 1e-9:
            flags.append(f"reward_mismatch {rt} vs {reward}")
        with (rdir / "artifacts/g857_unmapped.csv").open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                blob = " ".join(str(v) for v in row.values())
                if invented_pat.search(blob):
                    flags.append(f"invented:{blob[:60]}")
        if r == "r1":
            for n in art_names:
                if arts[n] != (gold / n).read_bytes():
                    flags.append(f"r1_ne_gold:{n}")
            if reward < 0.999:
                issues.append(f"g857 r1 not perfect {reward}")
        if r == "r4":
            if arts["g857_unmapped.csv"] != (gold / "g857_unmapped.csv").read_bytes():
                # allow order-normalized
                def rows(b: bytes):
                    import io

                    return {tuple(sorted(row.items())) for row in csv.DictReader(io.StringIO(b.decode()))}

                if rows(arts["g857_unmapped.csv"]) != rows((gold / "g857_unmapped.csv").read_bytes()):
                    flags.append("r4_unmapped_ne_gold")
            if arts["g857_headcount.json"] == (gold / "g857_headcount.json").read_bytes():
                flags.append("r4_hc_still_gold")
            if reward >= 0.999:
                issues.append("g857 r4 unexpectedly perfect")
        if r in ("r2", "r3") and reward >= 0.999:
            issues.append(f"g857 {r} unexpectedly perfect")
        for f in flags:
            issues.append(f"g857 {r}: {f}")
        notes.append(f"g857 {r} reward={reward:.6f} sizes={sizes}")

    # traj thinness note
    for r in ["r1", "r2", "r3", "r4"]:
        steps = json.loads(
            (C / f"evaluations/glm-5.2/{r}/agent/trajectory.json").read_text(encoding="utf-8")
        ).get("steps", [])
        if len(steps) < 5:
            notes.append(f"g857 {r} thin traj steps={len(steps)} (residual Harbor risk)")

    zissues = zip_check(DOWNLOADS / "UPLOAD-THIS-TO-QC-gen-g857.zip", C.name)
    for z in zissues:
        issues.append(f"g857 zip: {z}")
    zp = DOWNLOADS / "UPLOAD-THIS-TO-QC-gen-g857.zip"
    if zp.exists():
        pack_mtime = max(p.stat().st_mtime for p in C.rglob("*") if p.is_file())
        if zp.stat().st_mtime + 2 < pack_mtime:
            issues.append("g857 zip older than pack")
        notes.append(
            f"g857 zip size={zp.stat().st_size} mtime={datetime.fromtimestamp(zp.stat().st_mtime)}"
        )

    return issues, notes


def main():
    print("=" * 60)
    print("C251")
    print("=" * 60)
    i1, n1 = audit_c251()
    for x in n1:
        print("-", x)
    print("ISSUES:", len(i1))
    for x in i1:
        print("!", x)

    print("=" * 60)
    print("G857")
    print("=" * 60)
    i2, n2 = audit_g857()
    for x in n2:
        print("-", x)
    print("ISSUES:", len(i2))
    for x in i2:
        print("!", x)

    print("=" * 60)
    print(f"SUMMARY c251_issues={len(i1)} g857_issues={len(i2)}")
    if not i1 and not i2:
        print("BOTH CLEAN for upload")
    else:
        print("NEEDS ATTENTION")


if __name__ == "__main__":
    main()
