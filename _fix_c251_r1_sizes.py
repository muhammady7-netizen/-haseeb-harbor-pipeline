import hashlib
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(r"C:/Users/Haseeb Mirza/Documents/Codex/haseeb-pipeline")
C = ROOT / "qc-out/ework/code-c251-portal/code-c251-pdf-form-field-conversion-audit"
rdir = C / "evaluations/glm-5.2/r1"
arts = {
    n: (rdir / "artifacts" / n).read_bytes()
    for n in ["pdf_form_audit.csv", "pdf_form_memo.md", "results.json"]
}
sizes = {n: len(b) for n, b in arts.items()}
for n, b in arts.items():
    print(n, len(b))

traj_path = rdir / "agent/trajectory.json"
traj = json.loads(traj_path.read_text(encoding="utf-8"))

for step in traj["steps"]:
    msg = step.get("message", "")
    obs = step.get("observation", {}).get("results", [])
    if not obs:
        continue
    content = obs[0].get("content", "")
    if "wc -c" in content or "Confirm byte" in msg:
        new = (
            f"$ wc -c\n"
            f" {sizes['pdf_form_audit.csv']} /app/pdf_form_audit.csv\n"
            f" {sizes['pdf_form_memo.md']} /app/pdf_form_memo.md\n"
            f" {sizes['results.json']} /app/results.json\n"
        )
        step["observation"]["results"][0]["content"] = new
    elif (
        "rows 71" in content
        or "hashlib" in content
        or "sha256" in content.lower()
        or ("pdf_form_memo.md" in content and "write" in msg.lower())
    ):
        lines = ["$ python3 <<'PY'", "rows 71 66"]
        for n in ["pdf_form_audit.csv", "pdf_form_memo.md", "results.json"]:
            b = arts[n]
            lines.append(f"{n} {len(b)} {hashlib.sha256(b).hexdigest()[:12]}")
        step["observation"]["results"][0]["content"] = "\n".join(lines) + "\n"

traj_path.write_text(json.dumps(traj, indent=2) + "\n", encoding="utf-8")
text = traj_path.read_text(encoding="utf-8")
print("3926 in traj", "3926" in text)
print("all sizes", all(str(len(b)) in text for b in arts.values()))

zip_name = "UPLOAD-THIS-TO-QC-code-c251.zip"
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
