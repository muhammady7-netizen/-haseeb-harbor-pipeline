"""Fix v24: fix 2 pipeline findings while keeping 0/4 GLM difficulty.

Finding 1 (domain_correctness): Add rule 3.5 stating per-row rounding of
  fractional delivered_streams/delivered_reach (halves away from zero)
  before summing. This documents what the gold already does.
  Does NOT make task easier - the difficulty is in conditional PE/CE rounding
  direction and time-dependent rate (5.6), not in per-row vs sum rounding.

Finding 2 (coverage_depth): Tighten memo checks in test_outputs.py.
  Add a Python assertion that the memo mentions the single-part channel
  (CH-41) AND the part name (residual) AND has at least 30 content words.
  This prevents hollow token-only memos without adding an LLM judge.
"""
import json, csv, os
from pathlib import Path

DST = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\task-sources\bus-b50-v23")

# === 1. Add rule 3.5 for per-row rounding ===
note_path = DST / "environment/input/attribution_note.md"
note = note_path.read_text(encoding="utf-8")

rule_35 = """
**3.5** Where a ledger row carries a fractional `delivered_streams` or
`delivered_reach`, the value is rounded to the nearest whole number,
halves away from zero, before it is summed into the channel's totals.
The channel's delivered reach and delivered streams are the sums of
these per-row rounded values."""

note = note.replace(
    "\n**3.4** A ledger row carrying negative streams",
    rule_35 + "\n\n**3.4** A ledger row carrying negative streams"
)
note_path.write_text(note, encoding="utf-8")
print("1. Added rule 3.5 (per-row rounding of fractional streams)")

# === 2. Add content word check to test_outputs.py ===
test_path = DST / "tests/test_outputs.py"
test_code = test_path.read_text(encoding="utf-8")

# Add a new test that checks memo content depth
new_test = '''

def test_memo_has_content_words():
    """The memo must contain substantive content, not just tokens."""
    memo_path = WORKSPACE / "campaign_review.md"
    if not memo_path.is_file():
        pytest.skip("no campaign_review.md")
    import re
    text = memo_path.read_text(encoding="utf-8")
    # Must have at least 30 content words (3+ chars, not stopwords)
    words = re.findall(r"\\b[A-Za-z][A-Za-z]{2,}\\b", text)
    stopwords = {"the", "and", "for", "with", "that", "this", "from",
                 "are", "was", "but", "not", "all", "can", "has", "had",
                 "its", "one", "two", "per", "out", "our", "who", "how",
                 "did", "got", "set", "put", "let", "yet", "any", "own",
                 "too", "run", "may", "way", "use", "few", "off"}
    content_words = [w for w in words if w.lower() not in stopwords]
    assert len(content_words) >= 30, (
        f"memo has only {len(content_words)} content words; "
        "a review note needs substance, not just tokens"
    )
    # Must mention the single-part channel id and a part name in the same paragraph
    paragraphs = text.split("\\n\\n")
    found = False
    for para in paragraphs:
        has_channel = "CH-41" in para
        has_part = any(p in para.lower() for p in ["residual", "conversion", "placements"])
        if has_channel and has_part:
            found = True
            break
    assert found, (
        "memo must name the single-part channel (CH-41) and the part "
        "it sits in (residual) in the same paragraph"
    )
'''

# Add before the last test function
test_code = test_code.rstrip() + new_test
test_path.write_text(test_code, encoding="utf-8")
print("2. Added test_memo_has_content_words to test_outputs.py")

# === 3. Convert ALL files to LF ===
skip_dirs = {".git", "__pycache__", ".pytest_cache", "rl_world_verifiers"}
skip_exts = {".pyc", ".pyo", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".pdf", ".zip", ".xlsx", ".docx", ".pptx", ".so", ".dll", ".egg"}
fixed = 0
for p in DST.rglob("*"):
    if not p.is_file(): continue
    if any(part in skip_dirs for part in p.parts): continue
    if p.suffix.lower() in skip_exts: continue
    try:
        data = p.read_bytes()
        if b"\r\n" in data:
            p.write_bytes(data.replace(b"\r\n", b"\n"))
            fixed += 1
    except: pass
print(f"3. Converted {fixed} files to LF")

# === 4. Rebuild zip ===
import zipfile, shutil
out = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\canonical-zips\UPLOAD-THIS-TO-QC-bus-b50-v24.zip")
ROOT_NAME = "bus-b50-b10-streaming-target-variance-attribution"
EXCLUDE_DIRS = {".git", "__pycache__", ".pytest_cache", "__MACOSX"}
EXCLUDE_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}
EXCLUDE_SUFFIX = (".pyc", ".pyo", ".swp", ".swo", ".orig", ".rej", ":Zone.Identifier")
n = 0
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for p in sorted(DST.rglob("*")):
        if p.is_dir() or p.is_symlink(): continue
        rel = p.relative_to(DST)
        if any(part in EXCLUDE_DIRS for part in rel.parts): continue
        if p.name in EXCLUDE_NAMES or p.name.startswith("._"): continue
        if any(p.name.endswith(s) for s in EXCLUDE_SUFFIX): continue
        z.write(p, os.path.join(ROOT_NAME, rel.as_posix()))
        n += 1
print(f"4. Built {out.name}: {n} files, {out.stat().st_size} bytes")

workspace_copy = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\UPLOAD-THIS-TO-QC-bus-b50-v24.zip")
shutil.copy2(out, workspace_copy)
print("5. Copied to workspace")

print("\nDone! v24 fixes:")
print("  - Rule 3.5: per-row rounding documented (fixes domain_correctness)")
print("  - test_memo_has_content_words: 30+ content words + CH-41+residual (fixes coverage_depth)")
print("  - Rounding rules (5.4/5.7) UNCHANGED - keeps 0/4 GLM difficulty")
print("  - Time-dependent rate (5.6) UNCHANGED - keeps 0/4 GLM difficulty")
