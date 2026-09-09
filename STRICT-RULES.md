# STRICT RULES — Read before any portal action

## NEVER dismiss Harbor Check / QC findings as "False positive"
When the portal's Harbor Check or QC-Oracle-GLM reports blocking findings:
1. **READ the finding** — understand what the check says is wrong
2. **FIX the source** — edit instruction.md, standard, verifier.json, gold files, or review.csv to resolve the real issue
3. **Repackage** — rebuild the zip with `.\resume.ps1 package --task <short>`
4. **Re-upload** — upload the new zip to the portal
5. **Re-run eval** — Run QC-Oracle-GLM again
6. **Re-submit** — only after all blocking issues are actually fixed

### Why
"False positive · Undo" dismisses a finding WITHOUT fixing it. The pipeline still sees the defect and will reject the submission. Every dismissed finding must instead be **fixed in the source** and the task re-uploaded.

### Common fixes
- **Standard contradicts gold**: Rewrite the standard paragraph to match the verifier/gold
- **Hidden verifier requirement**: Remove the check from verifier.json OR add the requirement to instruction.md
- **Missing stability evidence**: Add evaluations/stability/ with 3+ repeat runs
- **CSV regex brittleness**: Make instruction explicitly state format requirements
- **Stale review.csv**: Update to match the shipped package's actual counts

## PreQC is optional
You may skip local PreQC (`.\resume.ps1 preqc`) and go straight to package + upload.

## One session drives the browser at a time
Chrome singleton lock — don't close Chrome, don't kill chrome.exe.
