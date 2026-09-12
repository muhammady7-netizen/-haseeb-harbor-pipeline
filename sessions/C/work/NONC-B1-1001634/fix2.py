import json
from pathlib import Path
VJ = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\-haseeb-harbor-pipeline\sessions\C\work\NONC-B1-1001634\gen-g806-leadership-brief-rhetorical-style-audit\tests\verifier.json")
spec = json.loads(VJ.read_text(encoding="utf-8"))

# Fix results checks
for v in spec["verifiers"]:
    if v["name"] == "results_passing_briefs":
        v["assertion"]["expected"] = 2
    elif v["name"] == "results_failing_briefs":
        v["assertion"]["expected"] = 6
    elif v["name"] == "results_avg_score":
        v["assertion"]["expected"] = 65.63
    elif v["name"] == "results_total_breaches":
        v["assertion"]["expected"] = 33
    elif v["name"] == "memo_omits_b03":
        # Remove this check - B-03 is now failing and should be in memo
        v["name"] = "memo_excludes_b01"
        v["assertion"]["expected"] = r"(?ms)(?!.*^#{1,3}\s*B[\-_–\s]?01\b).*"
        v["metadata"]["how_justification"] = "Checks that B-01 (passing) does NOT appear as a memo heading."
        v["metadata"]["why_justification"] = "B-01 passes and must not be in the memo."

VJ.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
print("Fixed 5 verifier checks")

# Verify gold
import sys
sys.path.insert(0, str(Path(VJ).parent))
from rl_world_verifiers.models import VerifierSpec, effective_weights
from rl_world_verifiers.sources.registry import SourceRegistry
from rl_world_verifiers.verifiers import verify_definition
WORKSPACE = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\-haseeb-harbor-pipeline\sessions\C\work\NONC-B1-1001634\gen-g806-leadership-brief-rhetorical-style-audit\solution\files")
SPEC = VerifierSpec.model_validate_json(VJ.read_text(encoding="utf-8"))
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

# Rebuild zip
import zipfile, shutil
src = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\-haseeb-harbor-pipeline\sessions\C\work\NONC-B1-1001634\gen-g806-leadership-brief-rhetorical-style-audit")
out = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\-haseeb-harbor-pipeline\sessions\C\work\NONC-B1-1001634\UPLOAD-THIS-TO-QC-gen-g806.zip")
if out.exists(): out.unlink()
excludes = ["_app","opencode.db","opencode.db-wal","opencode.db-shm","xdg-data","xdg-state","__pycache__",".pytest_cache",".DS_Store","qc/","harbor-jobs"]
count = 0
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
    for p in sorted(src.rglob("*")):
        if p.is_dir(): continue
        rel = p.relative_to(src).as_posix()
        if any(x in rel for x in excludes): continue
        zf.write(p, arcname=rel)
        count += 1
print(f"Built: {count} entries, {out.stat().st_size} bytes")
dl = Path.home() / "Downloads" / out.name
shutil.copy2(out, dl)
print(f"Copied to {dl}")
