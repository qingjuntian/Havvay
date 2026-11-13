# Day 26 — Finalize Capstone

## Goal
Use the working FastAPI agent starter as a cohesive demo: explain the architecture clearly, show the main request flows, and leave a short playbook that can be used for a screencast or portfolio handoff.

## Project summary
This project is a compact agent application built around FastAPI, an in-process planner/executor, a tool layer, retrieval context, session memory, long-term memory, and an optional background task queue.

The app provides:
- health endpoint
- standard prompt execution via `/query`
- streaming SSE responses via `/query/stream`
- background task submission via `/tasks`
- task status lookup via `/tasks/{task_id}`
- experimental multi-agent orchestration via `/query/multi-agent`

## Architecture at a glance

### 1. Request entrypoints
- `src/main.py` exposes the public API surface.
- `QueryRequest` and `TaskRequest` validate incoming JSON.
- The app isolates each request with a new `Agent` instance to keep usage and caches request-local.

### 2. Agent runtime
- `src/agent.py` holds the main orchestration logic.
- It manages:
  - session memory
  - long-term memory
  - retriever
  - tool access
  - safety validation
  - provider selection
  - response caching
  - usage/cost tracking

### 3. Planning and execution
- `src/planner.py` defines a deterministic planner and executor.
- It splits a prompt into action steps and selects tool actions such as calculator or web-search placeholders.
- This keeps tool selection inspectable and easy to expand.

### 4. Storage and retrieval
- `src/retriever.py` gathers document context.
- `src/memory.py` handles conversation and long-term memory.
- Qdrant is used as the retrieval backend when configured.

### 5. Background task processing
- `src/task_queue.py` provides a simple queue and subscriber model.
- Large or long-running prompts can be queued and observed asynchronously.

### 6. Execution modes
- `/query`: standard blocking execution
- `/query/stream`: SSE streaming with status and step events
- `/tasks`: submit a batch of prompts for asynchronous handling
- `/query/multi-agent`: experiment for coordinated tool execution

## Demo script
Use the project in the same order as the portfolio story:

### Step 1 — Health check
```bash
curl http://localhost:8000/health
```
Expected:
```json
{"status":"ok"}
```

### Step 2 — Standard query
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Calculate 17 * 23, then calculate 144 / 12","session_id":"demo-1"}'
```
This demonstrates structured agent execution and tool use.

### Step 3 — Streaming query
The file [requests.http](../requests.http) already contains a ready-made stream test.
Send the stream request and show the event flow:
- started
- executing_plan
- step events
- final response

### Step 4 — Background tasks
```bash
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"prompts":["Calculate 17 * 23","Calculate 144 / 12"],"session_id":"demo-2"}'
```
Then fetch:
```bash
curl http://localhost:8000/tasks/<task_id>
```
This demonstrates async execution and queue-based orchestration.

### Step 5 — Multi-agent path
```bash
curl -X POST http://localhost:8000/query/multi-agent \
  -H "Content-Type: application/json" \
  -d '{"prompt":"calculate 2 + 3 then search the web for FastAPI","session_id":"demo-3"}'
```
This shows the experimental parallel coordination path.

## What to say in the capstone pitch
"This project is a compact agent starter that combines a FastAPI API, deterministic planning/execution, safety checks, retrieval, memory, caching, and background orchestration. The system is designed to be understandable and extensible rather than opaque: each major flow is explicit, testable, and easy to run locally or in CI."

## Evidence to include in the demo
- [requests.http](../requests.http) contains the live API examples
- [WORKPLAN.md](../WORKPLAN.md) shows the roadmap and status
- [.github/workflows/ci.yml](../.github/workflows/ci.yml) shows CI coverage
- [README.md](../README.md) documents local startup and debugging

## Recommended closing story
Frame the project as:
- a working agent runtime with real API endpoints
- a deterministic planner and tool layer
- memory and retrieval groundwork for RAG
- background-task execution and queueing
- a CI path that verifies the service still boots

## Remaining polish
This is the final capstone polish item still left in the plan:
- create a short screencast or recording of the demo flow
- optionally add a 1-slide architecture walkthrough to the docs

That is the natural next step after the functional implementation and CI path are in place.
