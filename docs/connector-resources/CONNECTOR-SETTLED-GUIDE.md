# Connector Tasks — Settled Guide (from Slack)

This is the definitive guide posted by shayan.a in the Slack channel. It supersedes all earlier docs where they conflict.

## Key settled rules (from §0):

1. **JUDGE_MODEL**: Use `openai/glm-5.2` (NOT `openai/zai-org/GLM-5.2`). The proxy doesn't serve zai-org. If unset, judge defaults to gpt-5.5 which scores 0 on every rubric.
   - Wait — the PreQC error said "judge model openai/glm-5.2 is not one the runner can serve" and told us to use "openai/zai-org/GLM-5.2" or the passthrough "${JUDGE_MODEL:-openai/zai-org/GLM-5.2}".
   - The Slack guide says JUDGE_MODEL=openai/glm-5.2 is correct for the judge.
   - The portal PreQC says use zai-org.
   - RESOLUTION: The portal PreQC is the authority for what passes. Use `${JUDGE_MODEL:-openai/zai-org/GLM-5.2}` in task.toml, and in manifest.json use `openai/zai-org/GLM-5.2`. The Slack guide is about the local harbor config, not the portal.

2. **Band**: Ship at 1/4 or 2/4. 4/4 = too easy (rejected). 0/4 = re-roll by default.

3. **Oracle**: Must score exactly 1.0. Below that, fix the check, never the golden.

4. **Solvability**: Oracle does NOT prove solvability. Need a non-oracle run at 1.0.

5. **Mirror**: Sync _app mirror after every edit. Re-run oracle after every change.

6. **Prediction**: Write the prediction before hardening.

7. **Advisory findings**: Normal. Ignore if FP, move ahead. (Confirmed by lead shayan.a)

8. **Healthcheck retries**: 150 (not 40).

9. **Image**: Must pin with @sha256. Correct synthetic sha256 = b1374cd8a392ea66f9a649e700a1498e8fcb03ee35776362db7cc15dc3049b89

10. **Connector surface**: Must close all 4 doors (state route, step route, files on disk, gym port). Add tool_execution check naming sanctioned MCP tools.

## What I was doing wrong:
- Using wrong sha256 (real-data image sha256 instead of synthetic)
- Changing JUDGE_MODEL in task.toml when I should have kept ${JUDGE_MODEL:-openai/zai-org/GLM-5.2}
- Not properly quoting review.csv (csv module with QUOTE_ALL)
- Touching too many files at once instead of one change per test
