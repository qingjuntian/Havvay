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
  - [~] Task: GitHub Actions runs the test suite; Docker image build in CI and deployment-specific notes remain outstanding.
Day 26: Finalize capstone
  - [~] Task: Architecture notes exist; demo polish and screencast remain outstanding.
Day 27-28: Buffer & wrap-up

Notes:
- Keep daily commits and short PR-style notes; this will help building a portfolio.
- Adjust pace if you need deeper study on model fine-tuning or hardware setup.
