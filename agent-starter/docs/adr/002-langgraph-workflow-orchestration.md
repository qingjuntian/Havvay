# ADR-002: LangGraph for Stateful Workflow Orchestration

## Status
Accepted (Phase 2, Week 7 evaluation — brought forward ahead of Weeks 2–6)

## Context

The Phase 1 orchestrator (`src/planner.py` + `src/multi_agent.py`) is a
deterministic, heuristic planner: it splits compound prompts on "then" /
newlines, routes steps by keyword, and executes them acyclically in one
request lifecycle. Three production requirements are structurally out of its
reach:

1. **Cycles** — retry-until-success or re-plan loops require revisiting a
   node, which a plan-once-execute-once pipeline cannot express.
2. **Pause/resume** — human approval before a side-effecting tool call needs
   execution to stop mid-run and resume later, possibly after a restart.
3. **Persisted run state** — the in-process task queue loses everything on
   restart (ADR-001, single-process limitation).

Phase 2 Week 7 evaluates LangGraph as the orchestration layer for these
cases, behind a new opt-in endpoint, without disturbing the existing
`/query`, `/query/stream`, and `/query/multi-agent` paths.

## Decision

Adopt **LangGraph (pinned `langgraph==0.0.51`)** for one workflow:
`POST /query/workflow` + `POST /query/workflow/{thread_id}/resume`,
implemented in `src/graph_workflow.py`.

The workflow demonstrates each missing capability:

| Capability | Implementation |
| --- | --- |
| Branching | `classify` node + conditional edge: direct model answer vs. tool path |
| Retry policy | `answer` node loops back on itself until success or `LANGGRAPH_MAX_MODEL_ATTEMPTS` (default 2), then a shared `fallback` node |
| Human approval | `interrupt_before=["human_gate"]` pauses before tool execution; the resume endpoint writes `approved` via `update_state` and continues |
| Persisted state | `SqliteSaver` checkpointer at `LANGGRAPH_CHECKPOINT_DB` (default `data/langgraph_checkpoints.sqlite`), keyed by `thread_id` |

The graph is compiled per request but shares one process-wide checkpointer,
so an interrupted run survives an API restart and can be resumed from any
worker that can reach the SQLite file.

### Version pin rationale

The project stack is pydantic v1 + FastAPI 0.99 (FastAPI 0.99 does not
support pydantic v2). Modern LangGraph (>=0.1) requires pydantic v2, so we
pin `langgraph==0.0.51` with `langchain-core==0.1.53` / `langchain==0.1.20`,
the last line supporting pydantic v1. The 0.0.x API used here
(`set_entry_point`, `interrupt_before`, `SqliteSaver.from_conn_string`,
`update_state(as_node=...)`) differs from current releases; upgrading
LangGraph past 0.1 must be bundled with the FastAPI/pydantic v2 upgrade.

## When to use what (project guidance)

- **Direct OpenAI-compatible SDK** (`Agent.model_call`): single model calls,
  prompt caching, token accounting. Default for anything that is one request
  to a provider. Zero framework surface to debug.
- **LangChain Core**: reusable prompt/retriever/tool *components* with a
  stable interface. Useful when we want interchangeable pieces (e.g., swap
  embedding providers); does not add orchestration we lack.
- **LangGraph**: stateful, multi-step execution that needs cycles,
  branching, human-in-the-loop interrupts, or checkpointed resumption.
  Overkill for linear pipelines.

## Comparison vs. the custom planner

| Axis | `Planner` + `Executor` | LangGraph workflow |
| --- | --- | --- |
| Control flow | Linear / acyclic | Cycles and conditional branching |
| Retry | None | Graph-level retry loop with attempt budget |
| Human approval | None | Interrupt + checkpoint resume |
| State durability | In-process only | SQLite checkpoint survives restarts |
| Routing | Keyword heuristic (auditable) | Same heuristic, now in one `classify` node |
| Testability | Plain function calls | Compiled graph; needs checkpointer fixtures |
| Observability | Log lines per step | State `log` channel per run; LangSmith optional |
| Dependencies | None | langgraph + langchain-core (+ langsmith transitive) |

## Consequences

- Positive: retry loops, approval gates, and resumable runs ship without a
  bespoke state machine; the pattern generalizes to future workflows.
- Positive: checkpoint persistence covers part of the Week 6 durability
  story for workflow runs (not for the task queue).
- Negative: the dependency set grows and pins us to an old LangGraph line
  until the FastAPI/pydantic v2 upgrade.
- Negative: SQLite checkpointing is single-host; a multi-replica deployment
  needs Postgres/Redis-backed checkpoints instead.
- The deterministic planner remains the default for `/query`; LangGraph is
  opt-in at `/query/workflow` until it proves a concrete capability the
  planner cannot safely provide.

## Verification

`tests/test_graph_workflow.py` (10 tests): direct-answer branch, retry
recovery and exhaustion-to-fallback, approval pause/resume, rejection path,
checkpoint survival across graph rebuild (simulated restart), and API
coverage for both endpoints including 404 on unknown `thread_id`.
