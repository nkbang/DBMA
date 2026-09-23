# PEB — Pastor End-User Bot v0.1

PEB is an external black-box acceptance harness for DBMA/NAE.

Boundary:
- PEB does not import DBMA Python modules.
- PEB does not inspect Qdrant, DBMA config, embeddings, or RetrievalEngine.
- Acceptance path: PEB -> Playwright -> DBMA UI -> visible observation -> recorder.
- PEB does not decide PASS/FAIL; CUE remains the verification authority.

v0.1:
- Scenario-driven pastor persona
- One sermon-research scenario
- Local Ollama planner
- Playwright browser driver
- JSONL session recorder
- Dry-run mode
- No agent framework

Run:
```bash
python -m venv .venv-peb
source .venv-peb/bin/activate
pip install -r peb/requirements.txt
playwright install chromium
python -m peb.peb --scenario peb/scenarios/PEB-SERMON-001.yaml --base-url http://127.0.0.1:8501 --ollama-model qwen3.6:35b-DBMAcode
```

Planner-only:
```bash
python -m peb.peb --scenario peb/scenarios/PEB-SERMON-001.yaml --dry-run
```

Runtime logs are written under peb/runs/ and are not part of the source contract.
