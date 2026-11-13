# ADR-001: Phase 1 Architecture Baseline and Contracts

## Status
Accepted (Phase 1 Baseline)

## Context
The `agent-starter` repository was built as a clean, transparent Python & FastAPI AI-agent runtime to demonstrate core agent mechanics without heavy framework abstractions. Before beginning Phase 2 (Production Agent Engineering), this document establishes the baseline architecture, public API contracts, state lifecycle, and explicit single-process limitations.

---

## 1. System Architecture & Components

```
                +-----------------------------------------+
                |         Client (HTTP JSON / SSE)        |
                +--------------------+--------------------+
                                     |
                                     v
                       +-----------------------------+
                       |       FastAPI Router        |
                       |        (src/main.py)        |
                       +--------------+--------------+
                                      |
                     +----------------+----------------+
                     |                                 |
                     v                                 v
        +--------------------------+     +---------------------------+
        |   Interactive Executor   |     |    TaskQueue (In-Process) |
        |  (Planner / Agent / SSE) |     | (ThreadPoolExecutor / SSE)|
        +------------+-------------+     +-------------+-------------+
                     |                                 |
                     +----------------+----------------+
                                      |
            +-------------------------+-------------------------+
            |                         |                         |
            v                         v                         v
+-----------------------+ +-----------------------+ +-----------------------+
|  Safety & Tools Layer | |    Memory & RAG       | |    Model Providers    |
| (SafetyLayer, Tools)  | |(Session, LongTerm,    | | (Moonshot, OpenAI,    |
| - AST Calculator      | | Retriever, Qdrant)    | |  Local HuggingFace)   |
| - WebSearch (stub)    | |                       | | - Response Cache (LRU)|
+-----------------------+ +-----------------------+ +-----------------------+
```

### Component Boundaries
- **API Boundary (`src/main.py`)**: Exposes FastAPI endpoints for health checks, synchronous queries, SSE streaming, and background task dispatch. Uses `new_request_agent()` to instantiate request-scoped agent containers.
- **Agent Orchestrator (`src/agent.py`)**: Central orchestrator managing prompt construction, session/long-term memory integration, retriever calls, LLM provider routing, token/cost estimation, and LRU response caching.
- **Planner & Executor (`src/planner.py`)**: Heuristic/rule-based planner that decomposes compound instructions (delimited by "then", "and then", newlines) into structured `PlanStep` sequences.
- **Multi-Agent Coordinator (`src/multi_agent.py`)**: Worker-message dispatcher that executes adjacent tool steps concurrently using thread workers and aggregates outputs in original plan order.
- **Task Queue (`src/task_queue.py`)**: In-process `ThreadPoolExecutor` queue with publish-subscribe event queues for long-running batch or streaming tasks.
- **Retrieval & Vector Store (`src/retriever.py`, `src/vector_store.py`)**: Document search backed by Qdrant (`agent_docs` collection) with SHA-256 deterministic pseudo-embedding fallback when provider API keys are absent.
- **Memory System (`src/memory.py`)**:
  - `SessionMemory`: In-memory thread-safe dictionary holding the last $N$ turns per session.
  - `LongTermMemory`: Vector-indexed semantic store backed by Qdrant (`agent_memories` collection) with an in-memory list fallback.
- **Safety Layer (`src/safety.py`)**: Regex denylist validator that checks prompt length and blocks dangerous keywords (e.g. exploit, weapon creation).
- **Tools (`src/tools.py`)**:
  - `calc`: Restricted AST expression evaluator supporting basic arithmetic and `sqrt`.
  - `search_web`: Placeholder/stub returning mocked search strings.

---

## 2. Public API Contracts

### `GET /health`
- **Purpose**: Liveness probe.
- **Response**: `200 OK` `{"status": "ok"}`

### `POST /query`
- **Request**:
  ```json
  {
    "prompt": "string",
    "session_id": "string (optional, default: 'default')"
  }
  ```
- **Responses**:
  - `200 OK` (Foreground execution):
    ```json
    {
      "response": "string",
      "session_id": "string",
      "usage": {
        "provider": "moonshot|openai|local|null",
        "model": "string",
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "estimated_cost_usd": 0.0,
        "cache_hit": false
      }
    }
    ```
  - `202 Accepted` (Recognized as long-running prompt):
    ```json
    {
      "task_id": "uuid-string",
      "status": "queued",
      "execution_mode": "background",
      "session_id": "string"
    }
    ```
  - `400 Bad Request`: Unsafe prompt rejected by `SafetyLayer`.
  - `502 Bad Gateway`: Upstream LLM provider runtime failure.

### `POST /query/stream`
- **Content-Type**: `text/event-stream; charset=utf-8`
- **SSE Events emitted**:
  - `{"type": "status", "status": "started|retrieving_context|generating|executing_plan"}`
  - `{"type": "step", "step_id": "step-N", "action": "tool", "tool": "calc|search_web", "content": "..."}`
  - `{"type": "chunk", "content": "token delta"}`
  - `{"type": "final", "content": "full text", "session_id": "...", "usage": {...}}`
  - `{"type": "heartbeat", "task_id": "..."}` (every 15s during queued tasks)
  - `{"type": "error", "message": "..."}`

### `POST /query/multi-agent`
- **Purpose**: Opt-in concurrent tool execution and ordered result aggregation for planned tool steps.
- **Request/Response**: Identical structure to `POST /query`.

### `POST /tasks`
- **Request**:
  ```json
  {
    "prompts": ["string"],
    "session_id": "string (optional)"
  }
  ```
- **Response**: `202 Accepted` `{"task_id": "uuid-string", "status": "queued"}`

### `GET /tasks/{task_id}`
- **Responses**:
  - `200 OK`:
    ```json
    {
      "task_id": "uuid-string",
      "status": "queued|running|completed|failed",
      "session_id": "string",
      "total": 2,
      "completed": 2,
      "failed": 0,
      "results": [
        {"prompt": "string", "response": "string"}
      ],
      "error": null
    }
    ```
  - `404 Not Found`: Task does not exist or was pruned.

---

## 3. Current Implementation Limits & Production Gaps

1. **Process-Local State**:
   - `SessionMemory`, `TaskQueue`, and `_response_cache` are in-process Python data structures protected by threading locks.
   - Restarting the process drops all active/queued tasks, session histories, and cache entries. Running multiple Uvicorn workers causes state fragmentation.
2. **Heuristic Planning**:
   - Tool selection relies on string matching (e.g. checking for "calculate" or "search"). There is no native LLM tool-calling loop or function schema definition.
3. **Session & Tenant Isolation**:
   - `LongTermMemory.search()` queries vector similarity across the collection without filtering by `session_id` or tenant ID.
4. **Tool Sandboxing & Integration**:
   - `search_web` is a stub. `calc` uses AST inspection but lacks timeout isolation and dry-run execution mechanisms.
5. **Safety Depth**:
   - Input validation relies on a simple denylist. Output guardrails, prompt injection defenses, and red-team evaluation suites are not implemented.

---

## 4. Phase 2 Evolution Directives

- **Week 2**: Introduce typed tool schemas (Pydantic / JSON schema), OpenAI-compatible function calling, and bounded tool execution loops.
- **Week 3**: Enforce session-filtered vector memory, chunked RAG with source attribution, and document evaluation.
- **Week 4**: Implement automated safety evaluations, red-team test suites, and regression guards in CI.
- **Week 5**: Add OpenTelemetry tracing and structured telemetry for token cost, latency, and error attribution.
- **Week 6**: Migrate `TaskQueue` and session state to durable external stores (Redis / Celery / Temporal).
- **Week 7**: Introduce LangGraph for complex stateful workflows while retaining clean FastAPI service boundaries.
- **Week 8**: Ship an end-to-end production vertical slice.
