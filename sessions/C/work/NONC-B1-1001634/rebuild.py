import sys, json, zipfile, shutil
from pathlib import Path

PACK = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\-haseeb-harbor-pipeline\sessions\C\work\NONC-B1-1001634\gen-g806-leadership-brief-rhetorical-style-audit")

# Verify gold
sys.path.insert(0, str(PACK / "tests"))
from rl_world_verifiers.models import VerifierSpec, effective_weights
from rl_world_verifiers.sources.registry import SourceRegistry
from rl_world_verifiers.verifiers import verify_definition

WORKSPACE = PACK / "solution" / "files"
SPEC = VerifierSpec.model_validate_json((PACK / "tests" / "verifier.json").read_text(encoding="utf-8"))
WEIGHTS = effective_weights(SPEC.verifiers)
REGISTRY = SourceRegistry(WORKSPACE)
passed = failed = 0
failures = []
for v in SPEC.verifiers:
    result = verify_definition(v, REGISTRY, WEIGHTS[v.name], config=SPEC.config, completion_fn=None)
    if result["result"]["success"]: passed += 1
    else:
        failed += 1
        err = result["result"].get("error") or result["result"].get("reason") or "unknown"
        failures.append(f"{v.name}: {str(err)[:100]}")
print(f"Gold: {passed} passed, {failed} failed")
for f in failures: print(f"  FAIL: {f}")

# Build zip
out = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\-haseeb-harbor-pipeline\sessions\C\work\NONC-B1-1001634\UPLOAD-THIS-TO-QC-gen-g806.zip")
if out.exists(): out.unlink()
excludes = ["_app","opencode.db","opencode.db-wal","opencode.db-shm","xdg-data","xdg-state","__pycache__",".pytest_cache",".DS_Store","qc/","harbor-jobs"]
count = 0
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
    for p in sorted(PACK.rglob("*")):
        if p.is_dir(): continue
        rel = p.relative_to(PACK).as_posix()
        if any(x in rel for x in excludes): continue
        zf.write(p, arcname=rel)
        count += 1
print(f"Built: {count} entries, {out.stat().st_size} bytes")
dl = Path.home() / "Downloads" / out.name
shutil.copy2(out, dl)
print(f"Copied to {dl}")
