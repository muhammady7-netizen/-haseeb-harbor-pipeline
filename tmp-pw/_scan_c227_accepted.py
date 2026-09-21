from pathlib import Path
import hashlib

root = Path(r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline")
t = (root / "tmp-pw/trainer-c227-task.txt").read_text(encoding="utf-8")
key_lines = [
    l
    for l in t.splitlines()
    if any(
        x in l.lower()
        for x in [
            "landed",
            "accepted",
            "submitted",
            "version",
            "code-c227",
            "final qc",
            "obi/",
            "sha",
            "bundle",
            "pipeline",
        ]
    )
]
(root / "tmp-pw/c227-accepted-extract.txt").write_text(
    "HEAD\n" + "\n".join(t.splitlines()[:60]) + "\n\nKEY\n" + "\n".join(key_lines),
    encoding="utf-8",
)

wanted = {
    "9bb150064defada5e0afe23a95c36d0470d0854e4fb1f8c512b2b36d7e2a8a62",
    "3c613cd18fc23ab4724f29e3dc24ca0da91c3887a528e0923a234fff23c6bcef",
}
zips = []
for base in [
    Path.home() / "Downloads",
    root / "canonical-zips",
    Path(r"C:\Users\Haseeb Mirza\Documents\Codex\2026-08-17"),
]:
    if base.exists():
        zips.extend(base.rglob("*c227*.zip"))

lines = []
for p in zips:
    if not p.is_file():
        continue
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    tag = "MATCH" if h in wanted else "----"
    lines.append(f"{tag} {h} {p.stat().st_size} {p}")

(root / "tmp-pw/c227-hash-scan.txt").write_text("\n".join(lines), encoding="utf-8")
print("key_lines", len(key_lines))
print("zips", len(lines))
print("matches", sum(1 for x in lines if x.startswith("MATCH")))
