# Privacy-Aware Adaptive AI Companion

Research prototype: an LLM chatbot whose privacy, memory, interaction-policy,
and adaptation decisions are enforced and logged by application code.

Architecture: see `docs/architecture.md` and the Architecture Decision Report.

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your LLM_API_KEY when ready; echo mode works without one
uvicorn app.main:app --reload
# open http://127.0.0.1:8000/docs
```

## Run tests (the enforceable rules)

```bash
pytest -q
```

## Stage-1 scope

- FastAPI backend, stateless LLM backbone (echo mode offline / OpenAI-compatible with key)
- Three interaction policies as config files (DA / SRS / PAS operating mode)
- Memory manager: create / read / edit / delete / reset (SQLite)
- Privacy & consent layer (consent gate, sensitive-content tagging, schema-level
  demographic exclusion)
- Adaptation controller: proposals with logged evidence basis; accept / reject / defer;
  instant revert
- Append-only typed event log (JSONL)
- pytest rules per enforceable behaviour
