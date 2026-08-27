# agent-starter

Minimal agent starter repo (FastAPI + agent skeleton) — designed for building a RAG + tool-using agent.

Quickstart

1. Create a Python environment (recommended: conda or venv with Python 3.11).

2. Install dependencies:

   python -m pip install -r requirements.txt

3. Run locally:

   uvicorn src.main:app --reload --port 8000

4. Health check:

   GET http://localhost:8000/health

5. Query endpoint (POST):

   POST http://localhost:8000/query
   Body: {"prompt": "Hello"}

Project layout

- src/main.py        - FastAPI app and endpoints
- src/agent.py       - Agent skeleton (retriever, tool invocation)
- src/retriever.py   - Vector DB retriever stub (Qdrant example)
- src/tools.py       - Example tool implementations
- requirements.txt   - Python dependencies
- Dockerfile         - Build image
- docker-compose.yml - (optional) compose file for local dev
- tests/             - unit tests (pytest)

Notes

This is a starting point. Replace the placeholder implementations with your preferred libraries (LangChain, LlamaIndex, etc.) and add credentials via environment variables or .env. See the 4-week daily schedule in WORKPLAN.md for suggested next steps.