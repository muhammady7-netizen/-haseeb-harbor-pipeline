from pathlib import Path

test_path = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\task-sources\health-h34-temp\health-h34-randomisation-balance\tests\test_outputs.py")
content = test_path.read_text(encoding="utf-8")

new_tests = "\n\ndef test_memo_has_sentences():\n    \"\"\"The findings memo must contain full sentences with verbs.\"\"\"\n    import re\n    memo_path = WORKSPACE / \"randomisation_findings.md\"\n    if not memo_path.is_file():\n        pytest.skip(\"no randomisation_findings.md\")\n    text = memo_path.read_text(encoding=\"utf-8\")\n    sentences = re.split(r\"[.!?]\\s+(?:[A-Z#]|\\n|$)\", text)\n    real_sentences = [s.strip() for s in sentences if len(s.strip()) >= 20]\n    assert len(real_sentences) >= 5, f\"need 5+ sentences, got {len(real_sentences)}\"\n    verbs = [\"is\", \"are\", \"was\", \"were\", \"shows\", \"had\", \"has\", \"exceeds\", \"falls\", \"drifted\", \"held\", \"ran\", \"names\", \"states\", \"found\", \"identified\"]\n    has_verb = any(re.search(r\"\\b\" + v + r\"\\b\", text.lower()) for v in verbs)\n    assert has_verb, \"findings memo must contain verbs\"\n\n\ndef test_memo_register_consistency():\n    \"\"\"The findings memo must be consistent with results.json.\"\"\"\n    memo_path = WORKSPACE / \"randomisation_findings.md\"\n    results_path = WORKSPACE / \"results.json\"\n    if not memo_path.is_file() or not results_path.is_file():\n        pytest.skip(\"missing deliverables\")\n    memo_text = memo_path.read_text(encoding=\"utf-8\").lower()\n    results = json.loads(results_path.read_text(encoding=\"utf-8\"))\n    pct = results.get(\"active_proportion_pct\")\n    if pct is not None:\n        assert str(int(pct)) in memo_text, f\"memo does not mention active proportion {pct}\"\n"

content = content + new_tests
test_path.write_text(content, encoding="utf-8")
print("Added test_memo_has_sentences and test_memo_register_consistency")
