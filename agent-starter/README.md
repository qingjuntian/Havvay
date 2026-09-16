# agent-starter

Minimal FastAPI agent starter for RAG, memory, tools, and model calls.

## Prerequisites

- macOS, Linux, or Windows with VS Code
- Python 3.11
- Docker Desktop, including Docker Compose
- The **Dev Containers** VS Code extension, if you use the Dev Container workflow
- A model provider API key, unless you use the test suite or a local model

## First-time setup

Open this repository as the workspace folder in VS Code. From the integrated
terminal, create and activate the virtual environment:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows PowerShell, activate with:

```powershell
.venv\Scripts\Activate.ps1
```

Copy `.env.example` to `.env` and add the credentials for the model provider
you want to use. The application loads `.env` automatically.

In VS Code, select the project interpreter with **Python: Select Interpreter**
and choose `.venv/bin/python` (or `.venv\Scripts\python.exe` on Windows).

## Debug with VS Code and Docker

This is the recommended setup. Docker Compose starts both the FastAPI service
and Qdrant, and debugpy exposes the FastAPI process on port `5678`.

1. Start Docker Desktop.
2. In the VS Code terminal, run:

   ```bash
   docker compose up --build
   ```

3. Open **Run and Debug** in VS Code.
4. Select **Attach to Docker FastAPI** from the configuration menu.
5. Press the green **Start Debugging** button.
6. Set a breakpoint in files such as `src/main.py`, `src/agent.py`, or
   `src/memory.py` by clicking beside a line number.
7. Send a request while the containers are running. The debugger will stop at
   the breakpoint and show local variables, the call stack, and the debug
   console.

The API is available at `http://localhost:8000`. FastAPI's interactive API
documentation is at `http://localhost:8000/docs`.

Use **Attach to Docker FastAPI** only when you started the project with
`docker compose up`. Use **Attach to Dev Container FastAPI** only after
running **Dev Containers: Reopen in Container**. The two configurations use
different source paths for breakpoint mapping.

To stop the containers:

```bash
docker compose down
```

To stop them and remove the Qdrant data volume as well:

```bash
docker compose down -v
```

## Debug with a Dev Container

The Dev Container workflow opens the repository inside the `web` container at
`/app`.
It starts the FastAPI service and Qdrant together, installs the Python
dependencies from `requirements.txt`, and mounts your local source files so
edits and breakpoints are available immediately.

1. Install the **Dev Containers** extension in VS Code.
2. Open the repository folder in VS Code.
3. Open the Command Palette and run **Dev Containers: Reopen in Container**.
4. Wait for the container to build and for the `web` and `qdrant` services to
  start.
5. Open **Run and Debug** and select **Attach to Dev Container FastAPI**.
6. Press the green **Start Debugging** button.
7. Set breakpoints in `src/main.py`, `src/agent.py`, or `src/memory.py` and
  call the API at `http://localhost:8000`.

The Dev Container forwards these ports to your computer:

- `8000` - FastAPI
- `5678` - debugpy
- `6333` - Qdrant

To leave the Dev Container, run **Dev Containers: Reopen Folder Locally**
from the Command Palette. VS Code stops the Compose services according to the
`shutdownAction` in `.devcontainer/devcontainer.json`.

### Troubleshoot a refused debug connection

If VS Code reports `connect to 127.0.0.1:5678 was refused`, the `web`
container is not currently running. In a terminal, check both services:

```bash
docker compose ps
```

The `web` row should show `Up` and publish ports `8000` and `5678`. If it is
missing or exited, restart the services:

```bash
docker compose up -d web qdrant
curl http://localhost:8000/health
```

Wait for the health check to return `{"status":"ok"}`, then attach with
**Attach to Docker FastAPI**. If the container exits again, inspect its
startup logs:

```bash
docker compose logs --tail=100 web
```

If the app responds but breakpoints remain hollow, check the container's
source mount:

```bash
docker inspect agent-starter-web-1 --format '{{range .Mounts}}{{println .Source "->" .Destination}}{{end}}'
```

An `/app/src` mount means this is the regular Docker workflow, so select
**Attach to Docker FastAPI**. An `/app` mount with the repository opened at
`/app` means this is the Dev Container workflow, so select **Attach to Dev
Container FastAPI**.

After running **Dev Containers: Reopen in Container**, wait for the container
to finish starting before launching the debugger. Do not run `python
src/main.py`; use the Compose workflow or `python -m uvicorn src.main:app`.

## Debug a local Python process

This option runs FastAPI from your `.venv` while Qdrant still runs in Docker.
Start Qdrant in one terminal:

```bash
docker compose up -d qdrant
```

Start the app with debugpy in a second terminal:

```bash
source .venv/bin/activate
  python -Xfrozen_modules=off -m debugpy --listen 5678 --wait-for-client \
  -m uvicorn src.main:app --port 8000
```

The process waits until VS Code attaches. Use **Run and Debug**, choose an
attach configuration, and connect to `localhost:5678`. If you run the app
directly, use `python -m uvicorn src.main:app`; do not run `python src/main.py`.
The latter breaks the package-relative imports such as `from .agent import Agent`.

## Try the API

Health check:

```bash
curl http://localhost:8000/health
```

Regular query:

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Hello","session_id":"demo"}'
```

Streaming query:

```bash
curl -N -X POST http://localhost:8000/query/stream \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Hello","session_id":"demo"}'
```

## Run tests

Always invoke pytest through the project interpreter so VS Code and the test
runner use the same environment:

```bash
.venv/bin/python -m pytest -q
```

On Windows PowerShell:

```powershell
.venv\Scripts\python.exe -m pytest -q
```

## Model providers

The default provider is Moonshot:

```text
MODEL_PROVIDER=moonshot
MOONSHOT_API_KEY=...
MOONSHOT_MODEL=kimi-k3
```

OpenAI-compatible APIs can be selected with:

```text
MODEL_PROVIDER=openai
OPENAI_API_KEY=...
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

An optional local Hugging Face pipeline is available with:

```text
MODEL_PROVIDER=local
LOCAL_MODEL=google/flan-t5-small
```

The local provider requires the optional `transformers` and `torch` packages.

## Project layout

- src/main.py        - FastAPI app and endpoints
- src/agent.py       - Agent skeleton (retriever, tool invocation)
- src/retriever.py   - Vector DB retriever stub (Qdrant example)
- src/tools.py       - Example tool implementations
- requirements.txt   - Python dependencies
- Dockerfile         - Build image
- docker-compose.yml - (optional) compose file for local dev
- tests/             - unit tests (pytest)

## Notes

This is a starting point. Replace the placeholder implementations with your preferred libraries (LangChain, LlamaIndex, etc.) and add credentials via environment variables or .env. See the 4-week daily schedule in WORKPLAN.md for suggested next steps.