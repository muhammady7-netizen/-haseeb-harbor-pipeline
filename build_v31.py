import json, zipfile, os, shutil
from pathlib import Path

ROOT = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\task-sources\bus-b50-v29")

# 1. Remove memo figure checks from verifier.json
verifier_path = ROOT / "tests" / "verifier.json"
spec = json.loads(verifier_path.read_text(encoding="utf-8"))
names_to_remove = {"memo_conversion_effect", "memo_counted_placements"}
spec["verifiers"] = [v for v in spec["verifiers"] if v["name"] not in names_to_remove]
verifier_path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
count = len(spec["verifiers"])
print(f"Removed {len(names_to_remove)} memo figure checks ({count} remaining)")

# 2. Revert bare-digit disclosure
sf_path = ROOT / "environment/input/submission_format.md"
sf = sf_path.read_text(encoding="utf-8")
sf = sf.replace(
    "Each figure stands beside its label once, stated as the finding in bare digits with no thousands separators (e.g. 38831, not 38,831)",
    "Each figure stands beside its label once, stated as the finding"
)
sf_path.write_text(sf, encoding="utf-8")
print("Reverted bare-digit disclosure")

# 3. Convert to LF
for p in ROOT.rglob("*"):
    if not p.is_file(): continue
    try:
        data = p.read_bytes()
        if b"\r\n" in data:
            p.write_bytes(data.replace(b"\r\n", b"\n"))
    except: pass

# 4. Build zip
out = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\canonical-zips\UPLOAD-THIS-TO-QC-bus-b50-v31.zip")
ROOT_NAME = "bus-b50-b10-streaming-target-variance-attribution"
n = 0
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for p in sorted(ROOT.rglob("*")):
        if p.is_dir() or p.is_symlink(): continue
        rel = p.relative_to(ROOT)
        if any(part in {".git", "__pycache__", ".pytest_cache", "__MACOSX"} for part in rel.parts): continue
        if p.name in {".DS_Store", "Thumbs.db", "desktop.ini"} or p.name.startswith("._"): continue
        if any(p.name.endswith(s) for s in (".pyc", ".pyo", ".swp", ".swo", ".orig", ".rej", ":Zone.Identifier")): continue
        z.write(p, os.path.join(ROOT_NAME, rel.as_posix()))
        n += 1
print(f"Built {out.name}: {n} files, {out.stat().st_size} bytes")

shutil.copy2(out, Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\UPLOAD-THIS-TO-QC-bus-b50-v31.zip"))
print("Copied to workspace")
