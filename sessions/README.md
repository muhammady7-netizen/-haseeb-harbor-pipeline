# Sessions (3 tasks each)

| Chat | Folder | Tasks | Start |
|------|--------|-------|-------|
| A | sessions/A | gen-g1205, fin-f39, the-thread | PROMPT.md |
| B | sessions/B | gen-g826, code-c249, code-c227 | PROMPT.md |
| C | sessions/C | gen-g734, gen-g806, gen-g986 | PROMPT.md |
| D | sessions/D | fin-f33, fin-f44, fin-f53 | PROMPT.md |
| E | sessions/E | health-h40 only (fin-f55 + health-h34 locked out) | PROMPT.md |
| F | sessions/F | gen-g857, code-c251 | PROMPT.md |

## How to start a chat
1. `git pull`
2. Open `sessions/<LETTER>/PROMPT.md`
3. Paste into a new Cursor chat (or say `chat <LETTER>`)
4. Agent runs assign + PreQC loop for those 3 only
5. Upload zips from `sessions/<LETTER>/zips/` when `ready_final`

Max 3 portal Oracle+GLM evals at once across all chats.

## CRITICAL RULES FOR ALL SESSIONS (read before any portal work)

1. **FIX every finding — never dismiss as false positive unless it is genuinely a framework limitation you cannot fix.** The Harbor Check findings describe real verifier defects. Fix the source (verifier.json, instruction.md, review.csv, solution/) and re-upload a new version. Do NOT mark findings as "false positive" just to unlock Submit.

2. **Common verifier fixes you WILL need to make:**
   - **Memo regex same-line constraint**: `(?mi)^.*REF.*\d.*KEYWORD.*$` rejects correct memos that use heading + paragraph layout. Relax to multi-line or remove the same-line co-occurrence requirement.
   - **Rounding tolerance**: `result_interest_due_gbp` exact-equality fails when summing unrounded vs rounded row values (371,912.33 vs 371,912.34). Add tolerance or state the convention in instruction.md.
   - **Adversarial memo passes**: regex checks accept invoice numbers + keywords with no analysis or even wrong conclusions. Make checks verify correctness, not just token presence.
   - **Ungraded instruction rules**: if instruction.md states a rule (e.g. "total row must carry an empty reference column"), add a verifier check for it.
   - **Counterexample rejection**: duplicated-row CSV passes per-row regex checks. Add a record-count / whole-file check with `\A` anchor (not `^` in multiline mode).

3. **Pipeline flow**: Upload → Run Client PreQC (advisory, skip if you want) → Run Oracle+GLM×4 → Read Harbor Check findings → **FIX each finding in source** → Rebuild zip → Re-upload → Repeat until findings are genuinely clean → Dismiss any remaining true false positives → Submit to pipeline.

4. **Never Confirm a portal PreQC finding** (that blocks eval). Dismiss advisory PreQC findings. But Harbor Check findings from the delivery eval MUST be fixed in source, not dismissed.

5. **Difficulty gate**: Oracle must be 1.0. GLM ≤2/4 at reward 1.0 is ideal; 3/4 is accepted; 4/4 means densify.
