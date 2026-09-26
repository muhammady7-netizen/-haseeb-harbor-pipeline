import json, os, zipfile, shutil
from pathlib import Path

ROOT = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\task-sources\bus-b50-v29")

# 1. Add memo figure checks back to verifier.json with comma-grouped acceptance
verifier_path = ROOT / "tests" / "verifier.json"
spec = json.loads(verifier_path.read_text(encoding="utf-8"))

ce_value = 38831
cp_value = 114

ce_pattern = "(?is)(?:\\bconversion\\b.+\\b(?:38831|38,831)\\b|\\b(?:38831|38,831)\\b.+\\bconversion\\b)"
cp_pattern = "(?is)(?:\\bcounted\\b.+\\b(?:114|114)\\b|\\b(?:114|114)\\b.+\\bcounted\\b)"

memo_ce = {
    "name": "memo_conversion_effect",
    "metadata": {
        "how_justification": "Opens campaign_review.md with md.extract_text and applies regex_match to verify the conversion effect figure appears beside its label. Accepts both bare digits and comma-grouped numbers.",
        "why_justification": "The campaign total of the conversion part is a material disclosed requirement the memo must state.",
        "tag": "incidental"
    },
    "source": {"type": "file", "file": {"type": "md", "command": "extract_text", "arguments": {"path": "campaign_review.md"}}},
    "assertion": {"type": "deterministic", "expected": ce_pattern, "deterministic": {"path": "$.text", "comparison": "regex_match"}}
}

memo_cp = {
    "name": "memo_counted_placements",
    "metadata": {
        "how_justification": "Opens campaign_review.md with md.extract_text and applies regex_match to verify the counted placements figure appears beside its label. Accepts both bare digits and comma-grouped numbers.",
        "why_justification": "The number of placements counted across every channel is a material disclosed requirement the memo must state.",
        "tag": "incidental"
    },
    "source": {"type": "file", "file": {"type": "md", "command": "extract_text", "arguments": {"path": "campaign_review.md"}}},
    "assertion": {"type": "deterministic", "expected": cp_pattern, "deterministic": {"path": "$.text", "comparison": "regex_match"}}
}

# Insert before results_figures
for i, v in enumerate(spec["verifiers"]):
    if v["name"] == "results_figures":
        spec["verifiers"].insert(i, memo_ce)
        spec["verifiers"].insert(i + 1, memo_cp)
        break

verifier_path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
count = len(spec["verifiers"])
print("Added memo figure checks to verifier.json (" + str(count) + " total) - accepts comma-grouped numbers")

# 2. Add conversion effect rounding rule to attribution_note.md
note_path = ROOT / "environment" / "input" / "attribution_note.md"
note = note_path.read_text(encoding="utf-8")

addition = """

**5.8** Each ledger row's conversion effect contribution is computed as
the row's (per-row rounded) delivered_reach multiplied by the applicable
rate and planned_streams_per_1000_reach, divided by one thousand. The
conversion effect is the sum of these per-row contributions less the
channel's delivered streams, rounded once to the nearest whole stream
per 5.4. Per-row contributions are NOT individually rounded; only the
final total is rounded.
"""

note = note.rstrip() + addition
note_path.write_text(note, encoding="utf-8")
print("Added rule 5.8: conversion effect per-row contributions not individually rounded, total rounded once")

# 3. Build zip
out = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\canonical-zips\UPLOAD-THIS-TO-QC-bus-b50-v32.zip")
ROOT_NAME = "bus-b50-b10-streaming-target-variance-attribution"
# Convert to LF
for p in ROOT.rglob("*"):
    if not p.is_file():
        continue
    try:
        data = p.read_bytes()
        if b"\r\n" in data:
            p.write_bytes(data.replace(b"\r\n", b"\n"))
    except:
        pass
n = 0
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for p in sorted(ROOT.rglob("*")):
        if p.is_dir() or p.is_symlink():
            continue
        rel = p.relative_to(ROOT)
        if any(part in {".git", "__pycache__", ".pytest_cache", "__MACOSX"} for part in rel.parts):
            continue
        if p.name in {".DS_Store", "Thumbs.db", "desktop.ini"} or p.name.startswith("._"):
            continue
        if any(p.name.endswith(s) for s in (".pyc", ".pyo", ".swp", ".swo", ".orig", ".rej", ":Zone.Identifier")):
            continue
        z.write(p, os.path.join(ROOT_NAME, rel.as_posix()))
        n += 1
print("Built v32: " + str(n) + " files, " + str(out.stat().st_size) + " bytes")
shutil.copy2(out, Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\UPLOAD-THIS-TO-QC-bus-b50-v32.zip"))
print("Copied to workspace")
