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

Model responses are cached in-process for repeated prompts. Configure the
cache with `AGENT_CACHE_TTL_SECONDS` (default `300`) and
`AGENT_CACHE_MAX_ENTRIES` (default `256`); set either value to `0` to disable
the cache. Query responses include `usage.cache_hit` and estimated token
counts when the provider does not return usage metadata.

In VS Code, select the project interpreter with **Python: Select Interpreter**
and choose `.venv/bin/python` (or `.venv\Scripts\python.exe` on Windows).

## Debug with VS Code and Docker

This is the recommended setup. Docker Compose starts both the FastAPI service
and Qdrant. The API runs normally by default; debugpy is opt-in.

1. Start Docker Desktop.
2. In the VS Code terminal, run:

   ```bash
   docker compose up --build
   ```

  To enable the debugger for the regular Compose workflow, run:

  ```bash
  DEBUGPY_ENABLED=1 docker compose up --build
  ```

  Debugpy is published only on the host loopback interface at port `5678`.

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
`DEBUGPY_ENABLED=1 docker compose up`. Use **Attach to Dev Container FastAPI** only after
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

Qdrant is a separate Compose service. Docker publishes its port `6333` directly
to your computer; it is intentionally not listed in `forwardPorts` because that
would forward port `6333` from the `web` container instead of the Qdrant service.

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
**Attach to Docker FastAPI** for the regular Compose workflow or
**Attach to Dev Container FastAPI** for the Dev Container workflow. If the
container exits again, inspect its startup logs:

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

Background batch task:

```bash
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"prompts":["First question","Second question"],"session_id":"batch-demo"}'
```

The response returns a `task_id` immediately with status `queued`. Poll its
status and results with:

```bash
curl http://localhost:8000/tasks/<task_id>
```

The queue is an in-process prototype. Tasks are lost if the process restarts;
a production deployment should replace it with a durable queue and shared
task store.

## Index documents into Qdrant

The retriever reads the `agent_docs` collection. Index `.txt` and `.md` files
from `data/docs` with the web service's Compose-network connection to Qdrant:

```bash
docker compose exec web python scripts/index_docs.py --dir data/docs
```

To replace the collection contents instead of upserting into the existing
collection, add `--recreate`:

```bash
docker compose exec web python scripts/index_docs.py \
  --dir data/docs \
  --recreate
```

When running the script outside Docker, set `QDRANT_HOST=127.0.0.1` and use
the host-published Qdrant port `6333`. The script uses provider embeddings when
an embedding-capable API key is configured and otherwise uses deterministic
local embeddings. Qdrant data persists in the `qdrant-data` Compose volume.

Interactive requests also pass through a deterministic planner. It splits
tasks on "then" / "and then" or newlines, routes calculation and search-like
steps to the example tools, and sends other steps to the agent. Later response
steps receive the previous step's output. The calculator is a restricted
expression evaluator; web search currently returns a placeholder response.
This is heuristic planning, not an LLM planner or production search integration.
`/query/stream` reports planned tool work with `executing_plan`, `step`, and
`final` SSE events.

## Concurrency

Regular `/query` requests run blocking model calls in FastAPI's thread pool,
so multiple requests can make progress concurrently. Each request receives an
isolated `Agent` instance for usage tracking while sharing the cache and
thread-safe memory backends.

Long-running tasks use `AGENT_TASK_WORKERS` concurrent in-process workers
(default `4`). The queue, task status, session memory, and cache remain local
to one application process. Keep Uvicorn at one worker with this prototype;
multiple Uvicorn workers require replacing the in-process queue and memory
with shared durable services.

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

The default provider is Moonshot. If `MOONSHOT_MODEL` is unset, the code uses
`kimi-k3`; the `.env.example` file sets it explicitly to `kimi-k2.6`:

```text
MODEL_PROVIDER=moonshot
MOONSHOT_API_KEY=...
MOONSHOT_MODEL=kimi-k2.6
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

## Cost analysis

Project cost for the default 1,000-request mix with configured prices:

```bash
.venv/bin/python scripts/cost_analysis.py \
  --input-cost-per-1m 1 \
  --output-cost-per-1m 2
```

The report includes uncached cost, cache savings, average cost per request,
and the highest-cost request profiles. The defaults are illustrative; use the
provider's current prices and adjust the profiles in
`scripts/cost_analysis.py` for production traffic.

## Project layout

- `src/main.py` - FastAPI health, query, SSE, and background-task endpoints
- `src/agent.py` - RAG context, memory, provider calls, usage, and response cache
- `src/planner.py` - deterministic planner and tool/agent executor
- `src/task_queue.py` - in-process task queue and event subscriptions
- `src/retriever.py`, `src/memory.py`, `src/vector_store.py` - retrieval and memory backends
- `src/tools.py` - restricted calculator and placeholder web search
- `requirements.txt` - Python dependencies
- `Dockerfile`, `docker-compose.yml` - API and Qdrant local container setup
- `tests/` - pytest unit and API tests

## Current implementation limits

The planner uses keyword heuristics, web search is a stub, and session/task
state and the response cache are process-local. Long-term memory uses Qdrant
when available and falls back to process memory. The safety layer validates
inputs against a small denylist; it is not a comprehensive safety system.
Run one Uvicorn worker with the current in-process task and memory services.

## Notes

This is a starting point. Replace the placeholder implementations with your preferred libraries (LangChain, LlamaIndex, etc.) and add credentials via environment variables or .env. See the 4-week daily schedule in WORKPLAN.md for suggested next steps.