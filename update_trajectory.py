import json
from pathlib import Path

ROOT = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\task-sources\bus-b50-v29\solution")

# Read the actual gold files
memo = (ROOT / "files" / "campaign_review.md").read_text(encoding="utf-8")
results_json = (ROOT / "files" / "results.json").read_text(encoding="utf-8")
csv = (ROOT / "files" / "shortfall_attribution.csv").read_text(encoding="utf-8")

# Build the golden trajectory with the correct content
trajectory = [
    {"name": "bash", "server": "local", "arguments": {"command": "cat input/attribution_note.md"}},
    {"name": "bash", "server": "local", "arguments": {"command": "cat input/campaign_calendar.csv"}},
    {"name": "bash", "server": "local", "arguments": {"command": "cat input/channel_plan.csv"}},
    {"name": "bash", "server": "local", "arguments": {"command": "cat input/placement_log.csv"}},
    {"name": "bash", "server": "local", "arguments": {"command": "cat input/streaming_ledger.csv"}},
    {"name": "bash", "server": "local", "arguments": {"command": "cat input/submission_format.md"}},
    {"name": "bash", "server": "local", "arguments": {"command": "cat > campaign_review.md << 'CAMPAIGNREVIEWEOF'\n" + memo + "\nCAMPAIGNREVIEWEOF"}},
    {"name": "bash", "server": "local", "arguments": {"command": "cat > results.json << 'RESULTSEOF'\n" + results_json + "RESULTSEOF"}},
    {"name": "bash", "server": "local", "arguments": {"command": "cat > shortfall_attribution.csv << 'SHORTFALLATTRIBUTIONEOF'\n" + csv + "SHORTFALLATTRIBUTIONEOF"}},
    {"name": "bash", "server": "local", "arguments": {"command": "ls -la campaign_review.md results.json shortfall_attribution.csv"}},
]

out = ROOT / "golden_trajectory.json"
out.write_text(json.dumps(trajectory, indent=2) + "\n", encoding="utf-8")
print(f"Updated golden_trajectory.json ({out.stat().st_size} bytes)")

# Verify the new values
results = json.loads(results_json)
print(f"conversion_effect_streams: {results['conversion_effect_streams']}")
print(f"residual_reach_effect_streams: {results['residual_reach_effect_streams']}")
print(f"placements_effect_streams: {results['placements_effect_streams']}")
