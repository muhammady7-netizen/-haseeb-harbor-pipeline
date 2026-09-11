"""Audit Session F packs for remaining Harbor issues."""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline")
G857 = ROOT / "qc-out/ework/gen-g857-portal/gen-g857-department-directory-categorization-audit"
C251 = ROOT / "qc-out/ework/code-c251-portal/code-c251-pdf-form-field-conversion-audit"


def audit_g857() -> list[str]:
    P = G857
    issues: list[str] = []
    spec = json.loads((P / "tests/verifier.json").read_text(encoding="utf-8"))
    if "task_id" not in spec:
        issues.append("missing task_id")
    for v in spec["verifiers"]:
        c = v["assertion"]["deterministic"].get("comparison")
        if c == "eq":
            issues.append(f"eq in {v['name']}")
        f = v["source"]["file"]
        if f.get("type") == "filesystem" and f.get("command") != "check_path_exists":
            issues.append(f"bad fs cmd {v['name']}:{f.get('command')}")
    maps = list(csv.DictReader((P / "solution/files/g857_mappings.csv").open(encoding="utf-8")))
    un = [r for r in maps if r["status"] == "NO_ROLE_MATCH"]
    gr = json.loads((P / "solution/golden_results.json").read_text(encoding="utf-8"))
    if gr.get("total_people") != len(maps):
        issues.append(f"golden total {gr.get('total_people')} != {len(maps)}")
    if gr.get("unmapped_count") != len(un):
        issues.append(f"golden unmapped {gr.get('unmapped_count')} != {len(un)}")
    to = (P / "tests/test_outputs.py").read_text(encoding="utf-8")
    extras = re.findall(r"^def test_", to, re.M)
    if extras != ["test_deliverable"]:
        issues.append(f"extra tests {extras}")
    np = next(v for v in spec["verifiers"] if v["name"] == "no_pipe_chars")
    if np["assertion"]["expected"] == r"^[^\r\n|]*$":
        issues.append("old no_pipe regex")
    if not (P / "evaluations/glm-5.2/r1").exists():
        issues.append("no evals r1")
    if not (P / "evaluations/stability/repeat-03").exists():
        issues.append("no stab3")
    if (P / "PACKAGING-PROVENANCE.json").exists():
        issues.append("PACKAGING-PROVENANCE still present")
    r1 = (P / "evaluations/glm-5.2/r1/artifacts/g857_mappings.csv").read_bytes()
    gold = (P / "solution/files/g857_mappings.csv").read_bytes()
    r1h = (P / "evaluations/glm-5.2/r1/artifacts/g857_headcount.json").read_bytes()
    gh = (P / "solution/files/g857_headcount.json").read_bytes()
    if r1 == gold and r1h == gh:
        issues.append("r1 artifacts byte-identical to solution/files")
    trajs = []
    for p in sorted((P / "evaluations/glm-5.2").glob("r*/agent/trajectory.json")):
        t = json.loads(p.read_text(encoding="utf-8"))
        trajs.append(json.dumps(t, sort_keys=True))
        if t.get("schema_version") != "ATIF-v1.7":
            issues.append(f"bad traj schema {p.parent.parent.name}")
        if "steps" not in t:
            issues.append(f"no steps {p.parent.parent.name}")
        if not any(s.get("tool_calls") for s in t.get("steps", []) if isinstance(s, dict)):
            issues.append(f"no tool_calls {p.parent.parent.name}")
    if len(set(trajs)) < 4:
        issues.append(f"traj uniqueness {len(set(trajs))}/4")
    for p in (P / "evaluations").rglob("result.json"):
        d = json.loads(p.read_text(encoding="utf-8"))
        if d.get("started_at") == d.get("finished_at"):
            issues.append(f"identical start/finish {p.relative_to(P)}")
        rj = json.loads((p.parent / "verifier/reward.json").read_text(encoding="utf-8"))
        if "passed" not in rj or "total" not in rj:
            issues.append(f"thin reward.json {p.parent.name}")
        if not (p.parent / "verifier/ctrf.json").exists():
            issues.append(f"missing ctrf {p.parent.name}")
        if not (p.parent / "lock.json").exists():
            issues.append(f"missing lock {p.parent}")
    docker = (P / "environment/Dockerfile").read_text(encoding="utf-8")
    if "6c57c1a3a3" in docker:
        issues.append("fake docker digest")
    if "pip install" not in docker:
        issues.append("no pip deps")
    sys.path.insert(0, str(P / "tests"))
    for mod in list(sys.modules):
        if mod.startswith("rl_world_verifiers"):
            del sys.modules[mod]
    try:
        from rl_world_verifiers.models import VerifierSpec

        VerifierSpec.model_validate_json((P / "tests/verifier.json").read_text(encoding="utf-8"))
    except Exception as e:
        issues.append(f"VerifierSpec load fail: {e}")
    # instruction encoding?
    instr = (P / "instruction.md").read_text(encoding="utf-8")
    if "Output encoding" not in instr and "blank" not in instr.lower():
        issues.append("instruction may lack encoding disclosure")
    print("G857", "people", len(maps), "checks", len(spec["verifiers"]), "issues", len(issues))
    for i in issues:
        print(" -", i)
    return issues


def audit_c251() -> list[str]:
    P = C251
    issues: list[str] = []
    instr = (P / "instruction.md").read_text(encoding="utf-8")
    if "500 characters" in instr:
        issues.append("instruction still 500 memo floor")
    if "1000" not in instr:
        issues.append("instruction missing 1000 floor")
    if "trimmed" not in instr.lower():
        issues.append("MISSING trim not disclosed")
    readme = (P / "README.md").read_text(encoding="utf-8")
    if "flagged_count=32" in readme:
        issues.append("stale README counts")
    if "flagged_count=42" not in readme:
        issues.append("README missing 42")
    gr = json.loads((P / "solution/golden_results.json").read_text(encoding="utf-8"))
    if gr.get("flagged_count") != 42:
        issues.append(f"gold flagged {gr.get('flagged_count')}")
    spec = json.loads((P / "tests/verifier.json").read_text(encoding="utf-8"))
    by = {v["name"]: v for v in spec["verifiers"]}
    exp = by["f01"]["assertion"]["expected"]
    if "applicant_name" not in exp:
        issues.append("f01 missing full row content")
    gold = list(csv.DictReader((P / "solution/files/pdf_form_audit.csv").open(encoding="utf-8")))
    by_id = {r["field_id"]: r for r in gold}
    loose = 0
    for v in spec["verifiers"]:
        if not (v["name"].startswith("f") or v["name"].startswith("field")):
            continue
        e = v["assertion"].get("expected", "")
        if not isinstance(e, str):
            continue
        m = re.search(r"FIELD[-\\]*0*(\d+)", e)
        if not m:
            continue
        num = int(m.group(1))
        fid = f"FIELD-{num:02d}" if num < 10 else f"FIELD-{num}"
        row = by_id.get(fid)
        if row and row["field_name"].strip():
            if row["field_name"] not in e and re.escape(row["field_name"]) not in e:
                loose += 1
                if loose <= 8:
                    issues.append(f"loose {v['name']} missing field_name={row['field_name']!r}")
    print("c251 loose full-row misses", loose)
    memo = (P / "solution/files/pdf_form_memo.md").read_text(encoding="utf-8")
    audit = (P / "solution/files/pdf_form_audit.csv").read_text(encoding="utf-8")
    for name in [
        "memo_has_min_length",
        "memo_explains_signature_exempt",
        "memo_explains_required_flag_token",
        "memo_explains_whitespace_trim",
        "audit_no_pipe_chars",
    ]:
        e = by[name]["assertion"]["expected"]
        text = memo if "memo" in name else audit
        if not re.search(e, text):
            issues.append(f"gold fails {name}")
    if (P / "PACKAGING-PROVENANCE.json").exists():
        issues.append("PACKAGING-PROVENANCE present")
    if not (P / "evaluations/glm-5.2/r1").exists():
        issues.append("no evals")
    r1a = (P / "evaluations/glm-5.2/r1/artifacts/pdf_form_audit.csv").read_bytes()
    ga = (P / "solution/files/pdf_form_audit.csv").read_bytes()
    if r1a == ga:
        issues.append("r1 audit byte-identical to gold")
    trajs = []
    for p in sorted((P / "evaluations/glm-5.2").glob("r*/agent/trajectory.json")):
        t = json.loads(p.read_text(encoding="utf-8"))
        trajs.append(json.dumps(t, sort_keys=True))
        if t.get("schema_version") != "ATIF-v1.7":
            issues.append(f"bad traj {p.parent.parent.name}")
    if len(set(trajs)) < 4:
        issues.append(f"traj uniqueness {len(set(trajs))}/4")
    for p in (P / "evaluations").rglob("result.json"):
        d = json.loads(p.read_text(encoding="utf-8"))
        if d.get("started_at") == d.get("finished_at"):
            issues.append(f"identical timestamps {p.relative_to(P)}")
        if not (p.parent / "lock.json").exists():
            issues.append(f"missing lock {p.parent}")
        if not (p.parent / "verifier/ctrf.json").exists():
            issues.append(f"missing ctrf {p.parent}")
    # extras in test_outputs?
    to = (P / "tests/test_outputs.py").read_text(encoding="utf-8")
    extras = re.findall(r"^def test_", to, re.M)
    if extras != ["test_deliverable"]:
        issues.append(f"extra tests {extras}")
    print("C251 issues", len(issues))
    for i in issues:
        print(" -", i)
    return issues


if __name__ == "__main__":
    g = audit_g857()
    print("---")
    c = audit_c251()
    print("--- TOTAL", len(g) + len(c))
