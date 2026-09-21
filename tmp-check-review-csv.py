import csv
import io
import zipfile
from pathlib import Path

pack = Path(
    r"C:\Users\Haseeb Mirza\Documents\Codex\2026-08-17\this-is-the-very-beginning-of\tasks\NONC-B1-1001634\gen-g806-leadership-brief-rhetorical-style-audit\review.csv"
)
raw = pack.read_text(encoding="utf-8")
print("file bytes", len(raw.encode("utf-8")))
print("lines", raw.count("\n") + 1)
rows = list(csv.DictReader(io.StringIO(raw)))
print("nrows", len(rows))
print("fields", list(rows[0].keys()) if rows else None)
for r in rows:
    st = (r.get("status") or "").strip()
    notes = (r.get("review_notes") or "").strip()
    ch = (r.get("change_made") or "").strip()
    rec = (r.get("what_to_record") or "").strip()
    issues = []
    if st not in ("PASS", "FIXED_AND_VERIFIED", "N/A"):
        issues.append("bad_status")
    if st == "N/A" and not notes:
        issues.append("na_no_reason")
    if st == "FIXED_AND_VERIFIED" and not ch:
        issues.append("fix_no_change")
    if not notes:
        issues.append("empty_notes")
    if not rec:
        issues.append("empty_record")
    print(f"{r['review_check']!r} | {st} | change_empty={not bool(ch)} | {issues or 'ok'}")

zpath = Path(r"C:\Users\Haseeb Mirza\Downloads\UPLOAD-THIS-TO-QC-gen-g806.zip")
with zipfile.ZipFile(zpath) as zf:
    zraw = zf.read("gen-g806-leadership-brief-rhetorical-style-audit/review.csv").decode("utf-8")
print("zip==disk", zraw == raw)
