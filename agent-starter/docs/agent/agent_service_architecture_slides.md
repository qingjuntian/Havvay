# Agent Service Architecture

## 1. Cover

- Agent Service: Architecture and data flows
- Current FastAPI, RAG, memory, streaming, and concurrent task design

## 2. System Architecture

- Clients call FastAPI endpoints for standard JSON, SSE streaming, and task work.
- Each request gets an isolated `Agent` instance for usage tracking.
- Interactive queries use a deterministic planner/executor: calculator and search-like steps go to tools; other steps go to the agent. Search is currently a placeholder.
- Retriever, session memory, long-term memory, response cache, Qdrant, provider, and task queue are shown as editable shapes.

## 3. Interactive Query Data Flow

- Validate, plan/execute tool steps when selected, otherwise assemble context, generate, persist, and return.
- `/query` moves blocking model work to FastAPI's thread pool.
- `/query/stream` sends UTF-8 SSE `status`, `step`, `chunk`, `final`, `error`, and `heartbeat` events, depending on the execution path.

## 4. Long-Running Task Data Flow

- Identified prompts create a task and receive a task ID.
- The task executor runs prompts concurrently using `AGENT_TASK_WORKERS` (default `4`).
- Status progresses through queued, running, progress, completed, or failed.

## 5. Concurrency and Scale Boundary

- Current concurrency is within one application process.
- Session memory, long-term-memory fallback state, and response cache are in-process and lock-protected; usage remains request-local. Qdrant is the external persistence/retrieval service when available.
- Horizontal scale requires a shared queue, cache, task state, and persistent session storage.