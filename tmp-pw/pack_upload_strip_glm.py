"""Strip stale GLM evidence and rebuild ship zip from current v17 pack."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline")
PACK = ROOT / "task-sources/law-b39/law-b39-l16-custody-letter-instruction-audit-v17"
GLM = PACK / "evaluations" / "glm-5.2"

# Strip stale GLM (graded on old 87/154 gold) — portal runs fresh QC-Oracle-GLM
if GLM.exists():
    shutil.rmtree(GLM)
    print("removed", GLM)
else:
    print("no glm-5.2 to remove")

# Placeholder so evaluations/ is intentional, not accidental omission
GLM.mkdir(parents=True)
(GLM / "README.md").write_text(
    "# GLM-5.2 evidence\n\n"
    "Stale terminus-2 ×4 runs (graded against prior 87/154 gold) were removed after "
    "ST-354/ST-134 gold corrections (now 85/156). Portal QC-Oracle-GLM runs a fresh "
    "Oracle + GLM×4 on the uploaded package; do not treat absence of local r1–r4 as a content defect.\n",
    encoding="utf-8",
)
print("wrote glm-5.2/README.md")

# Update review.csv difficulty / calibration lines without rewriting whole file
review = PACK / "review.csv"
text = review.read_text(encoding="utf-8")
# light touch already has 85/156 in Layer 1 from earlier; ensure difficulty notes pending portal
if "GLM evidence regenerating" not in text and "portal QC-Oracle-GLM" not in text:
    text = text.replace(
        "GLM evidence pending after fair harden",
        "Stale local GLM stripped; portal QC-Oracle-GLM runs fresh ×4",
    )
    text = text.replace(
        "Difficulty from clarification precedence and multi-limb RP-405 traps",
        "Local GLM stripped after gold fix; difficulty from portal fresh GLM; traps remain CL precedence + ST-354/ST-134 limbs",
    )
    review.write_text(text, encoding="utf-8")
    print("review.csv notes refreshed")

sys.path.insert(0, str(ROOT / "tmp-pw"))
import rebuild_b39_zip as z

z.PACK = PACK
z.NAME = "law-b39-l16-custody-letter-instruction-audit"
# Keep pack's review.csv as authored
z.write_review_csv = lambda path: print("keep existing review.csv")
zip_path = z.build_zip()
print("ZIP", zip_path)
print("CANON", z.CANON, "exists", z.CANON.exists())
