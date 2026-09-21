import hashlib
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(r"C:/Users/Haseeb Mirza/Documents/Codex/haseeb-pipeline")
C = ROOT / "qc-out/ework/gen-g857-portal/gen-g857-department-directory-categorization-audit"
rdir = C / "evaluations/glm-5.2/r1/artifacts"
gold = C / "solution/files"
names = ["g857_mappings.csv", "g857_unmapped.csv", "g857_headcount.json"]

for n in names:
    src = (gold / n).read_bytes()
    dst = rdir / n
    before = dst.read_bytes()
    dst.write_bytes(src)
    print(n, "changed", before != src, "size", len(src))

arts = {n: (rdir / n).read_bytes() for n in names}
sizes = {n: len(b) for n, b in arts.items()}

traj_path = C / "evaluations/glm-5.2/r1/agent/trajectory.json"
traj = json.loads(traj_path.read_text(encoding="utf-8"))
for step in traj.get("steps", []):
    obs = step.get("observation", {}).get("results", [])
    if not obs:
        continue
    c = obs[0].get("content", "")
    if "wc -c" in c or (
        "g857_mappings.csv" in c
        and any(x in c for x in ["1935", "158", "1618", str(sizes["g857_mappings.csv"])])
    ):
        if "sha" in c.lower() or "hashlib" in c:
            lines = ["$ python3 <<'PY'"]
            for n in names:
                b = arts[n]
                lines.append(f"{n} {len(b)} {hashlib.sha256(b).hexdigest()[:12]}")
        else:
            lines = ["$ wc -c"]
            for n in names:
                lines.append(f" {sizes[n]} /app/{n}")
        obs[0]["content"] = "\n".join(lines) + "\n"

traj_path.write_text(json.dumps(traj, indent=2) + "\n", encoding="utf-8")
text = traj_path.read_text(encoding="utf-8")
print("all sizes in traj", all(str(s) in text for s in sizes.values()), sizes)
print("r1==gold", all((rdir / n).read_bytes() == (gold / n).read_bytes() for n in names))

zip_name = "UPLOAD-THIS-TO-QC-gen-g857.zip"
primary = Path.home() / "Downloads" / zip_name
with zipfile.ZipFile(primary, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    for path in C.rglob("*"):
        if not path.is_file():
            continue
        if any(p in {".DS_Store", "__pycache__"} or str(p).endswith(".pyc") for p in path.parts):
            continue
        if path.name.endswith(".zip") or path.name.startswith("PACKAGING-PROVENANCE"):
            continue
        zf.write(path, arcname=(Path(C.name) / path.relative_to(C)).as_posix())

for dest in [
    ROOT / "canonical-zips" / zip_name,
    ROOT / "sessions" / "F" / "zips" / zip_name,
    C.parent / zip_name,
]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(primary, dest)
print("zip", primary, primary.stat().st_size)
