"""Replay verifier.json against gold for g857 and c251."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline")


def replay(pack: Path, files: list[str]) -> None:
    tests = pack / "tests"
    # isolate import path
    for mod in list(sys.modules):
        if mod.startswith("rl_world_verifiers"):
            del sys.modules[mod]
    sys.path.insert(0, str(tests))
    from rl_world_verifiers.models import VerifierSpec, effective_weights
    from rl_world_verifiers.sources.registry import SourceRegistry
    from rl_world_verifiers.verifiers import verify_definition

    ws = Path(tempfile.mkdtemp(prefix="harbor-gold-"))
    for name in files:
        data = (pack / "solution/files" / name).read_bytes()
        (ws / name).write_bytes(data)
    os.environ["HARBOR_TASK_WORKSPACE"] = str(ws)
    spec = VerifierSpec.model_validate_json((tests / "verifier.json").read_text(encoding="utf-8"))
    weights = effective_weights(spec.verifiers)
    reg = SourceRegistry(ws)
    failed = []
    for d in spec.verifiers:
        out = verify_definition(d, reg, weights[d.name], config=spec.config, completion_fn=None)["result"]
        if not out["success"]:
            failed.append((d.name, out.get("error") or out.get("reason")))
    print(pack.name, "passed", len(spec.verifiers) - len(failed), "/", len(spec.verifiers))
    for n, e in failed[:20]:
        print(" FAIL", n, e)


if __name__ == "__main__":
    replay(
        ROOT / "qc-out/ework/gen-g857-portal/gen-g857-department-directory-categorization-audit",
        ["g857_mappings.csv", "g857_unmapped.csv", "g857_headcount.json"],
    )
    replay(
        ROOT / "qc-out/ework/code-c251-portal/code-c251-pdf-form-field-conversion-audit",
        ["pdf_form_audit.csv", "pdf_form_memo.md", "results.json"],
    )
