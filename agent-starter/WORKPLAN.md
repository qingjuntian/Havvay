4-week Day-by-Day Intensive Plan (weeks 1-4)

This plan is an intensive, hands-on ramp intended to make you productive building agents quickly. Each day has a focused goal plus a short exercise and deliverable.

Week 1 — Foundation & prompt engineering
Day 1: Environment + Hello-agent
  - Task: Create repo (this skeleton), set up Python env, run uvicorn and endpoint.
  - Deliverable: repo runs locally and GET /health returns ok.
Day 2: Prompt fundamentals
  - Task: Build a prompt playground script to test temperature, top_p, and system messages.
  - Deliverable: prompt_playground.py with 5 sample prompts and notes.
Day 3: Few-shot & chain-of-thought
  - Task: Implement few-shot examples and a simple chain-of-thought prompt for arithmetic reasoning.
  - Deliverable: prompts.md with examples and results.
Day 4: ReAct / tool patterns
  - Task: Implement Tools (already stubbed) and add an agent path that calls a tool based on simple heuristics.
  - Deliverable: example prompts demonstrating tool calls.
Day 5: Retrieval basics
  - Task: Integrate a local vector store (Qdrant as Docker) and index a small doc set.
  - Deliverable: retriever demo script and sample queries.
Day 6: RAG pipeline
  - Task: Assemble retrieval + prompt template; evaluate top-1/top-3 accuracy on sample queries.
  - Deliverable: rag_demo.ipynb or script.
Day 7: Buffer day (catch up / write notes)

Week 2 — Memory, safety, and tooling
Day 8: Session memory
  - Task: Implement short-term session memory (in-memory) for conversation context.
Day 9: Long-term memory
  - Task: Implement summary-condensation pipeline to store long-term memory in vector DB.
Day 10: Safety layer
  - Task: Add input/output sanitation and a denylist for unsafe content; create red-team prompts.
Day 11: Tool sandboxing
  - Task: Harden Tools: input validation, timeout wrapper, and a dry-run mode.
Day 12: Observability basics
  - Task: Add structured logging and capture tokens/cost for each request.
Day 13: Testing harness
  - Task: Add unit tests for agent logic and integration tests mocking external services. (completed)
  - Deliverable: tests/test_agent.py and tests/test_api.py with mocked API, agent, and SSE coverage.
Day 14: Buffer / doc day

Week 3 — Scaling, serving, and model choices
Day 15: Model selection
  - Task: Wire in both openai and a local HF model switchable by config. (completed)
  - Deliverable: MODEL_PROVIDER selects Moonshot, OpenAI-compatible, or optional local Hugging Face execution.
Day 16: Containerize + Docker Compose
  - Task: Build Docker image and run with compose (include qdrant if needed).
Day 17: Load testing
  - Task: Run a small load test (wrk or locust) to understand latency and concurrency.
Day 18: Caching & token optimization
  - Task: Implement prompt result caching and token counting instrumentation.
Day 19: Cost analysis
  - Task: Simulate cost per 1k requests and identify hot paths to optimize.
Day 20: Orchestration overview
  - Task: Prototype a simple orchestrator (FastAPI + background worker queue) for long-running tasks.
Day 21: Buffer / write-up

Week 4 — Advanced patterns & capstone
Day 22: Planner + executor
  - Task: Implement a planner agent that decomposes tasks and an executor that calls tools.
Day 23: Red-team + safety eval
  - Task: Run extensive adversarial prompt tests and document mitigations.
Day 24: Multi-agent coordination
  - Task: Prototype agent-to-agent message passing (planner -> workers -> aggregator).
Day 25: CI/CD + infra
  - Task: Add CI (already included), add Docker image build in CI, and create deployment notes.
Day 26: Finalize capstone
  - Task: Polish demo, record short screencast, and write architecture notes.
Day 27-28: Buffer & wrap-up

Notes:
- Keep daily commits and short PR-style notes; this will help building a portfolio.
- Adjust pace if you need deeper study on model fine-tuning or hardware setup.
