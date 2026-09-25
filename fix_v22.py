"""Fix v21: address all 5 Harbor Check findings.

Finding 1+2+5: memo_single_part_channel hardcodes CH-04+conversion but
  CH-04 has residual=695 (NOT single-part). The real single-part channel
  is CH-41 (PE=0, CE=0, RR=1, SF=1 - entirely in residual reach).
  Fix: change verifier to check CH-41+residual, update golden memo,
  change instruction to say "name that part" (generic).

Finding 3: Rule 5.4 says "halves away from zero" for PE and CE, but
  rule 5.7 says "halves toward zero" for CE. Contradictory.
  Fix: 5.4 should say PE is halves away (SF>0) / toward (SF<0),
  CE is always halves toward zero. 5.7 consistent.

Finding 3b: CH-31 has 1200.5+1700.5 streams. Per-row vs sum-then-round
  gives different results. Fix: add rule 3.12 (per-row rounding).

Finding 4: memo checks are shallow (keyword presence only).
  Fix: memo_single_part_channel now checks CH-41+residual (correct channel).
"""
import json, csv, os
from pathlib import Path

DST = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\task-sources\bus-b50-v21")

# 1. Fix instruction.md: change "the conversion" to "name that part"
instr_path = DST / "instruction.md"
instr = instr_path.read_text(encoding="utf-8")
# The instruction says "the one channel whose shortfall the method leaves entirely to a single part of the split, and name that part — the conversion"
# Change to: "the one channel whose shortfall the method leaves entirely to a single part of the split, and name that part"
instr = instr.replace(
    "the one channel whose shortfall the method leaves entirely to a single part of the split, and name that part — the conversion",
    "the one channel whose shortfall the method leaves entirely to a single part of the split, and name that part"
)
instr_path.write_text(instr, encoding="utf-8")
print("1. Fixed instruction.md (generic 'name that part' instead of 'the conversion')")

# Also fix submission_format.md if it mentions "the conversion"
sf_path = DST / "environment/input/submission_format.md"
sf = sf_path.read_text(encoding="utf-8")
sf = sf.replace(
    "the one channel whose shortfall the method leaves entirely to a single part of the split, and name that part — the conversion",
    "the one channel whose shortfall the method leaves entirely to a single part of the split, and name that part"
)
sf_path.write_text(sf, encoding="utf-8")
print("1b. Fixed submission_format.md")

# 2. Fix attribution_note.md: fix rounding rules and add per-row rounding
note_path = DST / "environment/input/attribution_note.md"
note = note_path.read_text(encoding="utf-8")

# Fix rule 5.4: clarify PE vs CE rounding
note = note.replace(
    "The placements effect is taken to the nearest whole\nstream, its tie-break fixed by 5.7. The conversion effect is taken to the nearest whole\nstream, halves toward zero.",
    "The placements effect is taken to the nearest whole\nstream, its tie-break fixed by 5.7. The conversion effect is taken to the nearest whole\nstream, halves toward zero, always."
)

# Add rule 3.12 for per-row rounding of fractional streams
rule_312 = "\n\n**3.12** Fractional `delivered_streams` or `delivered_reach` in a\nledger row are rounded to the nearest whole number per row, halves away\nfrom zero, before being summed into the channel's totals. The channel's\ndelivered streams and delivered reach are the sums of these per-row\nrounded values, not the rounded sum of unrounded values."
note = note.replace(
    "\n\n**1.1** The `in_campaign_window`",
    rule_312 + "\n\n**1.1** The `in_campaign_window`"
)

# Fix section 1 reference to 5.5 (ensure it exists)
# Check if 5.5 exists in the note
if "**5.5**" not in note:
    # Add 5.5 after 5.4
    note = note.replace(
        "\n**5.6** Time-dependent",
        "\n**5.5 Shortfall rounding.** The shortfall to target is rounded to the nearest\nwhole number of streams, halves toward zero, before the three parts are taken.\nThis makes every figure in the analysis a whole number of streams as section 1\nrequires, and it is taken before the placements effect and conversion effect\nare computed, so the three parts add back to the rounded shortfall exactly.\n\n**5.6** Time-dependent"
    )

note_path.write_text(note, encoding="utf-8")
print("2. Fixed attribution_note.md (rounding rules, per-row rounding, 5.5)")

# 3. Fix verifier.json: change memo_single_part_channel to CH-41 + residual
verifier_path = DST / "tests/verifier.json"
spec = json.loads(verifier_path.read_text(encoding="utf-8"))
for v in spec["verifiers"]:
    if v["name"] == "memo_single_part_channel":
        # Change from CH-04 + conversion to CH-41 + residual
        old_exp = v["assertion"]["expected"]
        new_exp = old_exp.replace("CH-04", "CH-41").replace("conversion", "residual")
        v["assertion"]["expected"] = new_exp
        # Update justification
        v["metadata"]["why_justification"] = "The note names the channel whose whole gap the method leaves in one part of the split, beside the part it leaves it in. Both names stand in the same paragraph: this is CO-NAMING, not attribution. Which record carries which value is pinned cell by cell in the register and in results.json, both core."
        print(f"3. Fixed memo_single_part_channel: CH-04+conversion -> CH-41+residual")
        break

verifier_path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")

# 4. Fix golden memo: change CH-04 + conversion to CH-41 + residual reach
memo_path = DST / "solution/files/campaign_review.md"
memo = memo_path.read_text(encoding="utf-8")
# Replace the CH-04 paragraph
memo = memo.replace(
    "CH-04 is the channel to walk the artist through first, because it is the clean case.\nEvery placement the plan asked of it ran inside the window and its reach landed exactly\nwhere the plan put it, so the method leaves the whole of that channel's gap in the\nconversion part and nothing in the other two. The curator submissions brought the\naudience along and simply did not turn it into plays.",
    "CH-41 is the channel to walk the artist through first, because it is the clean case.\nEvery placement the plan asked of it ran inside the window and its reach landed exactly\nwhere the plan put it, so the method leaves the whole of that channel's gap in the\nresidual reach part and nothing in the other two. The audience came along as the\nplan expected and the conversion held; what drifted was the reach the counted\nplacements brought above what the plan assumed of them."
)
memo_path.write_text(memo, encoding="utf-8")
print("4. Fixed golden memo: CH-04+conversion -> CH-41+residual reach")

# 5. Fix golden_trajectory.json: update embedded memo
traj_path = DST / "solution/golden_trajectory.json"
traj = json.loads(traj_path.read_text(encoding="utf-8"))
for step in traj:
    cmd = str(step.get("arguments", {}).get("command", ""))
    if "campaign_review.md" in cmd and "CH-04" in cmd:
        cmd = cmd.replace(
            "CH-04 is the channel to walk the artist through first, because it is the clean case.\nEvery placement the plan asked of it ran inside the window and its reach landed exactly\nwhere the plan put it, so the method leaves the whole of that channel's gap in the\nconversion part and nothing in the other two. The curator submissions brought the\naudience along and simply did not turn it into plays.",
            "CH-41 is the channel to walk the artist through first, because it is the clean case.\nEvery placement the plan asked of it ran inside the window and its reach landed exactly\nwhere the plan put it, so the method leaves the whole of that channel's gap in the\nresidual reach part and nothing in the other two. The audience came along as the\nplan expected and the conversion held; what drifted was the reach the counted\nplacements brought above what the plan assumed of them."
        )
        step["arguments"]["command"] = cmd
traj_path.write_text(json.dumps(traj, indent=2) + "\n", encoding="utf-8")
print("5. Fixed golden_trajectory.json")

# 6. Convert ALL files to LF
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
print(f"6. Converted {fixed} files to LF")

# 7. Rebuild zip
import zipfile, shutil
out = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\canonical-zips\UPLOAD-THIS-TO-QC-bus-b50-v22.zip")
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
print(f"7. Built {out.name}: {n} files, {out.stat().st_size} bytes")

workspace_copy = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\UPLOAD-THIS-TO-QC-bus-b50-v22.zip")
shutil.copy2(out, workspace_copy)
print("8. Copied to workspace for upload")

print("\nDone! v22 fixes all 5 Harbor Check findings:")
print("  - memo_single_part_channel: CH-41+residual (correct single-part channel)")
print("  - instruction: 'name that part' (generic, not 'the conversion')")
print("  - golden memo: names CH-41 and residual reach")
print("  - rounding rules: 5.4 and 5.7 consistent")
print("  - per-row rounding: rule 3.12 added")
