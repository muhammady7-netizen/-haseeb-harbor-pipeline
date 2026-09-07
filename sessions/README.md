# Sessions (3 tasks each)

| Chat | Folder | Tasks | Start |
|------|--------|-------|-------|
| A | sessions/A | gen-g1205, fin-f39, the-thread | PROMPT.md |
| B | sessions/B | gen-g826, code-c249, code-c227 | PROMPT.md |
| C | sessions/C | gen-g734, gen-g806, gen-g986 | PROMPT.md |
| D | sessions/D | fin-f33, fin-f44, fin-f53 | PROMPT.md |
| E | sessions/E | fin-f55, health-h34, health-h40 | PROMPT.md |
| F | sessions/F | gen-g857, code-c251 | PROMPT.md |

## How to start a chat
1. `git pull`
2. Open `sessions/<LETTER>/PROMPT.md`
3. Paste into a new Cursor chat (or say `chat <LETTER>`)
4. Agent runs assign + PreQC loop for those 3 only
5. Upload zips from `sessions/<LETTER>/zips/` when `ready_final`

Max 3 portal Oracle+GLM evals at once across all chats.
