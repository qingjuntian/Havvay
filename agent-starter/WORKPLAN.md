4-week Day-by-Day Plan and Implementation Status

Status snapshot: 2026-10-08. `[x]` means implemented, `[~]` means partially
implemented or configured but not fully verified, `[ ]` means the planned
deliverable is not present yet, `[>]` marks the current focus, and `[D]` means
deferred. These statuses describe this repository, not production readiness.

This plan is an intensive, hands-on ramp intended to make you productive building agents quickly. Each day has a focused goal plus a short exercise and deliverable.

Week 1 — Foundation & prompt engineering
Day 1: Environment + Hello-agent
  - [x] Task: Create repo (this skeleton), set up Python env, run uvicorn and endpoint.
  - Deliverable: repo runs locally and GET /health returns ok.
Day 2: Prompt fundamentals
  - [ ] Task: Build a prompt playground script to test temperature, top_p, and system messages.
  - Deliverable: prompt_playground.py with 5 sample prompts and notes.
Day 3: Few-shot & chain-of-thought
  - [ ] Task: Implement few-shot examples and a simple chain-of-thought prompt for arithmetic reasoning.
  - Deliverable: prompts.md with examples and results.
Day 4: ReAct / tool patterns
  - [~] Task: Tools and heuristic planner-based tool selection exist; the search tool remains a stub and the planned example prompts are not documented.
  - Deliverable: example prompts demonstrating tool calls.
Day 5: Retrieval basics
  - [~] Task: Qdrant integration and a document indexing script exist; a retriever demo and sample queries are still needed.
  - Deliverable: retriever demo script and sample queries.
Day 6: RAG pipeline
  - [~] Task: Retrieval context is assembled into agent prompts; top-1/top-3 evaluation has not been added.
  - Deliverable: rag_demo.ipynb or script.
Day 7: Buffer day (catch up / write notes)

Week 2 — Memory, safety, and tooling
Day 8: Session memory
  - [x] Task: Implement short-term session memory (in-memory) for conversation context.
Day 9: Long-term memory
  - [~] Task: Long-term memory is stored in Qdrant with an in-memory fallback; current summarization keeps the response text rather than condensing it.
Day 10: Safety layer
  - [~] Task: Input validation and a denylist exist; output sanitation and the red-team prompt suite remain outstanding.
Day 11: Tool sandboxing
  - [~] Task: Calculator expressions use a restricted AST evaluator with size/exponent checks; timeout and dry-run support are not implemented, and web search is a placeholder.
Day 12: Observability basics
  - [~] Task: Request logs include duration and usage; token estimation and configurable cost estimates exist, but structured logging and broader observability are not implemented.
Day 13: Testing harness
  - [x] Task: Add unit tests for agent logic and integration tests mocking external services.
  - Deliverable: tests/test_agent.py and tests/test_api.py with mocked API, agent, and SSE coverage.
Day 14: Buffer / doc day

Week 3 — Scaling, serving, and model choices
Day 15: Model selection
  - [x] Task: Wire in Moonshot, OpenAI-compatible, and optional local Hugging Face providers switchable by config.
  - Deliverable: MODEL_PROVIDER selects Moonshot, OpenAI-compatible, or optional local Hugging Face execution.
Day 16: Containerize + Docker Compose
  - [~] Task: Dockerfile and Compose services for the API and Qdrant are configured; a successful image/Compose run is not recorded here.
Day 17: Load testing
  - [ ] Task: Run a small load test (wrk or locust) to understand latency and concurrency.
Day 18: Caching & token optimization
  - [x] Task: Implement prompt result caching and token counting instrumentation.
Day 19: Cost analysis
  - [x] Task: Simulate cost per 1k requests and identify hot paths to optimize.
Day 20: Orchestration overview
  - [x] Task: Prototype a simple orchestrator (FastAPI + background worker queue) for long-running tasks.
Day 21: Buffer / write-up

Week 4 — Advanced patterns & capstone
Day 22: Planner + executor
  - [x] Task: Implement a deterministic planner that decomposes tasks and an executor that calls supported tools or the agent. It is heuristic-based, not an LLM planner.
Day 23: Red-team + safety eval
  - [D] Deferred: return to this before treating the safety layer as production-ready.
Day 24: Multi-agent coordination
  - [x] Implemented planner -> worker messages -> ordered aggregation via `Agent.multi_agent_plan_and_execute()` and the opt-in `POST /query/multi-agent` endpoint; API coverage passes (13 tests).
  - [D] Distinct specialist-agent personas deferred; current workers share one agent and tool set.
Day 25: CI/CD + infra
  - [~] Task: GitHub Actions runs the test suite and validates the Docker image build; deployment-specific notes remain outstanding.
Day 26: Finalize capstone
  - [~] Task: Architecture notes are assembled and a demo script is in place; the screencast remains the last polish item.
Day 27-28: Buffer & wrap-up

Notes:
- Keep daily commits and short PR-style notes; this will help building a portfolio.
- Adjust pace if you need deeper study on model fine-tuning or hardware setup.

## Phase 2 - Production Agent Engineering (8 weeks)

Goal: evolve this starter into a reliable, observable, and deployable agent
service. The capstone remains the working baseline; Phase 2 prioritizes
engineering evidence over adding agent-framework features indiscriminately.

### Week 1 - Establish the production baseline

Goal: Lock down architecture contracts, fix Docker packaging/indexing flaws, and record baseline metrics (test suite + load/latency report).

- Day 1: Architecture Baseline & Container Packaging Fixes
  - [x] Create ADR-001 (`docs/adr/001-phase1-architecture-baseline.md`) documenting API contracts, component boundaries, and single-process limitations.
  - [x] Fix Docker packaging flaws: update `.dockerignore` to block `.env*` secret leaks, and update `Dockerfile` / `docker-compose.yml` so `scripts/` and `data/` can be accessed for document indexing.
  - Deliverable: ADR-001 document and sanitized Docker packaging configuration.

- Day 2: Compose Verification & End-to-End Smoke Testing
  - [>] Start Compose stack (`web` + `qdrant`), run document indexing into Qdrant container, and verify persistence.
  - [ ] Create an automated smoke test script (`scripts/smoke_test.py`) covering `/health`, `/query`, `/query/stream`, `/tasks`, and `/query/multi-agent`.
  - Deliverable: Automated smoke test script and verified Compose startup runbook in README.

- Day 3: Baseline Load Testing & Production Metrics Report
  - [ ] Build a lightweight asynchronous load testing script (`scripts/load_test.py`) supporting concurrent `/query` and `/query/stream` workloads.
  - [ ] Execute baseline performance runs against mocked provider endpoints to measure p50/p95 latency, RPS, concurrency behavior, and memory usage.
  - [ ] Compile `docs/baseline_report.md` capturing test count (47 unit/API tests), benchmark results, and production gap analysis.
  - Deliverable: Reproducible load testing tool and completed baseline report.

- Exit criterion: A clean checkout can be launched in Docker Compose, pass the smoke test and benchmark, and match the documented baseline metrics.

### Week 2 - Typed tools and native tool calling

- [ ] Define explicit input/output schemas for every supported tool.
- [ ] Replace keyword-only tool routing with OpenAI-compatible native tool
  calling, including strict server-side argument validation.
- [ ] Add a real, configurable web-search provider; keep the stub available
  only for tests.
- [ ] Enforce a maximum number of tool calls, timeouts, and clear tool errors.
- Deliverable: calculator and web-search tool loop with unit and API tests.
- Exit criterion: a model can select and call tools from schemas, while invalid
  arguments and loop-limit failures return safe, observable errors.

### Week 3 - Trustworthy RAG and memory isolation

- [ ] Add document chunking, stable source metadata, and citations in answers.
- [ ] Create a small retrieval evaluation set with expected documents and
  measure recall at k.
- [ ] Filter long-term memory retrieval by session or tenant identity.
- [ ] Add retention/deletion behavior for session and long-term memory.
- Deliverable: evaluated RAG path with source citations and tenant isolation
  tests.
- Exit criterion: evaluation results are recorded and a session cannot retrieve
  another session's long-term memory.

### Week 4 - Safety and evaluation

- [ ] Build a versioned red-team prompt suite covering prompt injection,
  unsafe tool requests, data exfiltration, and malformed tool arguments.
- [ ] Add output checks for tool results and model responses where required.
- [ ] Define task-level quality checks: expected tool use, citation presence,
  refusal behavior, and answer correctness for a focused domain.
- Deliverable: automated evaluation command and a documented quality baseline.
- Exit criterion: the evaluation suite runs in CI and blocks regressions in the
  agreed safety and quality checks.

### Week 5 - Observability and operations

- [ ] Emit structured logs with request ID, session/tenant-safe identifiers,
  model, tool calls, latency, token use, cache behavior, and failures.
- [ ] Add distributed traces through OpenTelemetry or a managed platform such
  as LangSmith; do not log sensitive prompt content by default.
- [ ] Add metrics and alerts for provider errors, tool errors, latency, queue
  depth, and cost.
- Deliverable: one traceable request flow and an operations dashboard or
  documented local equivalent.
- Exit criterion: a failed request can be traced from API request through model
  and tool calls with enough context to diagnose it.

### Week 6 - Durable asynchronous execution

- [ ] Replace the in-process task queue with a durable queue and shared task
  state, such as Redis plus Celery, Dramatiq, or Temporal.
- [ ] Make task status, cancellation, retries, idempotency, and result
  retention explicit API behavior.
- [ ] Verify service restart recovery and multi-worker API access to task state.
- Deliverable: durable background processing with integration tests.
- Exit criterion: a task remains inspectable after an API restart and does not
  execute twice when a client retries submission.

### Week 7 - Workflow orchestration and framework comparison

- [ ] Model one non-trivial workflow with LangGraph: branching, retry policy,
  human approval, and persisted state where appropriate.
- [ ] Keep the FastAPI service boundary and compare the LangGraph workflow
  against the custom planner on clarity, tests, observability, and operations.
- [ ] Document when this project should use direct SDK calls, LangChain Core,
  or LangGraph.
- Deliverable: one LangGraph-backed endpoint plus an architecture decision
  record explaining the framework choice.
- Exit criterion: the new workflow has tests and delivers a concrete capability
  that the deterministic planner cannot safely provide.

### Week 8 - Portfolio-quality vertical slice

- [ ] Choose one backend-focused use case: incident triage, internal knowledge
  support, API documentation assistant, or pull-request risk review.
- [ ] Ship it end to end: authenticated API, evaluated retrieval/tools,
  observability, durable work, deployment instructions, and a short demo.
- [ ] Write a concise case study covering architecture, tradeoffs, test and
  evaluation results, cost profile, and remaining risks.
- Deliverable: deployable portfolio project and README walkthrough.
- Exit criterion: a reviewer can run the demo, inspect the tests/evaluations,
  and understand why each production boundary exists.

### Operating cadence

- Start each week by naming one measurable hypothesis and its acceptance test.
- Keep changes small: implement one vertical slice, validate it, then expand.
- Run unit tests, relevant integration tests, and the evaluation suite before
  each milestone.
- Publish one short architecture or incident-style note weekly; this becomes
  evidence of engineering judgment for interviews.
