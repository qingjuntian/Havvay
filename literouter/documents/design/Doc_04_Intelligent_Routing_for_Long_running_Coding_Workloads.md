# Doc 04 --- Intelligent Routing for Long-running Coding Workloads

**Status:** Proposed\
**Version:** 0.1\
**Date:** 2026-11-11\
**Document Type:** Architecture & Product Design Proposal\
**Depends on:** Doc 01 --- Request Lifecycle & Intelligent Routing
Design; Doc 02 --- Billing & Ledger Design; Doc 03 --- Cross-Document
Architecture Contract

## 1. Executive Summary

This document defines how the Intelligent LLM Gateway supports
long-running Coding Agent workloads without becoming an Agent Runtime.

A long-running coding task is not a single prompt. It is a sequence of
planning, repository exploration, code generation, test execution,
debugging, review, and completion decisions. Some steps require LLM
calls; others are deterministic tool executions such as shell commands,
file edits, and tests.

The Agent Runtime (Agent Harness or Orchestrator) owns the task
lifecycle and decides what to do next. The Gateway handles each
individual LLM Request: it selects a suitable model and Provider,
executes the Provider Attempt, applies retry/fallback policies, records
usage and cost, and exposes routing observability.

The Gateway should understand that multiple Requests may belong to the
same long-running task. It can use task and session context, stage
information, model capabilities, historical signals, and execution
feedback to make better routing decisions across a task.

**Product principle:** optimize the economics, reliability, and
model-selection quality of all LLM calls within a long-running coding
task, while leaving task planning and execution to the Agent Runtime.

The MVP remains an Intelligent LLM Gateway. It does not include a full
Agent Runtime, repository execution environment, planner, tool executor,
checkpoint engine, or task scheduler.

## 2. Goals and Non-goals

### 2.1 Goals

1.  Route LLM Requests according to workload intent and coding stage.
2.  Associate multiple Requests with a shared task or session when the
    caller supplies correlation context.
3.  Preserve useful model/session continuity while allowing
    capability-safe model switching.
4.  Enforce Request-level routing and spending constraints within the
    Gateway's responsibility.
5.  Provide usage, cost, latency, reliability, and routing-decision
    observability.
6.  Accept execution feedback from an external Agent Runtime to support
    evaluation of routing strategies.
7.  Keep the generic routing core reusable for non-coding workloads.

### 2.2 Non-goals for MVP

The Gateway will not own the user-visible Task lifecycle, decompose user
requests, explore repositories, edit files, execute shell commands, run
tests, own Agent memory/context reconstruction/checkpointing, decide
whether generated code is correct, or act as the authoritative
controller of a Task's aggregate budget. These responsibilities remain
with the external Agent Runtime.

## 3. System Boundary and Responsibilities

### 3.1 Agent Runtime responsibilities

The Agent Runtime is authoritative for Task creation, identity,
lifecycle, and completion; planning and task decomposition; Step
scheduling; repository exploration and context assembly; tool execution;
context management and checkpoint/resume; deciding whether to retry a
coding step after a quality failure; Task-level budgets such as total
cost, maximum iterations and elapsed time; and declaring the current
coding stage and reporting outcomes.

### 3.2 Gateway responsibilities

The Gateway is authoritative for receiving and validating each LLM
Request; authenticating callers and applying tenant policies; resolving
routing strategy and eligible model/Provider candidates; applying hard
capability and policy constraints; selecting a model and Provider;
creating and managing Provider Attempts; transport-level retries and
eligible fallbacks; Request-level reservation, usage measurement and
settlement consistent with Docs 01--03; Request/Attempt observability;
associating Requests with Task/Session correlation metadata; aggregating
usage and cost by task/session where correlation metadata is available;
and accepting external evaluation signals.

### 3.3 Boundary rule

The Gateway is **Task-aware, not Task-execution-owning**. A `task_id` is
primarily a correlation and routing-context identifier. It does not
imply that the Gateway owns a full Task entity with Steps, checkpoints,
execution state, or completion semantics.

## 4. Workload Model: Task, Step, Session, Request, Attempt

| Concept | Owner | Meaning |
|---|---|---|
| Task | Agent Runtime | Complete unit of work requested by a user |
| Step | Agent Runtime | Logical unit in the Task plan or execution |
| Session | Integration contract / Gateway correlation | Continuity scope linking related Requests; exact relationship to Task is caller-defined |
| Request | Gateway | One logical model invocation submitted to the Gateway |
| Provider Attempt | Gateway | One concrete call attempt to a Provider for a Request |
| Route Decision | Gateway | Decision and rationale for selecting a model/Provider |
| Reservation / Settlement | Billing subsystem | Request-level financial lifecycle defined by Doc 02 |

One Step may cause zero, one, or multiple LLM Requests. A Task may
contain many Steps and Requests. A Step may execute without any LLM
Request, for example when running tests.

``` text
Task: Implement OAuth authentication
 |
 +-- Step 1: Planning
 |    +-- Request 1 -> Gateway -> Provider
 +-- Step 2: Repository exploration
 |    +-- Request 2 -> Gateway -> Provider
 |    +-- Request 3 -> Gateway -> Provider
 +-- Step 3: Code generation
 |    +-- Request 4 -> Gateway -> Provider
 +-- Step 4: Test execution
 |    +-- Terminal execution (no LLM Request necessarily)
 +-- Step 5: Debugging
 |    +-- Request 5 -> Gateway -> Provider
 +-- Step 6: Review
      +-- Request 6 -> Gateway -> Provider
```

## 5. Task Context and Session Propagation

### 5.1 Design principle

The Agent Runtime is the authoritative source of task execution context.
The Gateway should make context propagation easy, but must not assume
every third-party Agent provides complete metadata.

Adopt a hybrid context model:

1.  **Explicit Context:** caller-provided metadata is the strongest
    source of task and stage information.
2.  **Session Context:** the Gateway correlates Requests that share a
    caller-provided session identifier and retains permitted routing
    history.
3.  **Intelligent Inference:** when explicit metadata is absent, the
    Gateway may classify the current Request from available content and
    metadata, subject to privacy and policy constraints.

Explicit context takes precedence over inferred context. Inference is a
fallback signal, not an authoritative replacement for Agent state.

### 5.2 Suggested metadata contract

Illustrative only; not a finalized API schema:

``` json
{
  "metadata": {
    "task_id": "task_123",
    "session_id": "session_456",
    "task_type": "coding",
    "stage": "debugging",
    "subtask_id": "subtask_7",
    "agent_id": "agent_debugger",
    "iteration": 3,
    "routing_strategy": "coding_balanced"
  }
}
```

| Field | Required? | Semantics |
|---|---|---|
| `task_id` | Optional | Stable identifier supplied by Agent Runtime |
| `session_id` | Optional | Identifier associating a sequence of Requests |
| `task_type` | Optional | Workload class, e.g. `coding` |
| `stage` | Optional | Current stage, e.g. `planning` or `debugging` |
| `subtask_id` | Optional | Correlates a child unit of work |
| `agent_id` | Optional | Identifies Agent or Subagent |
| `iteration` | Optional | Caller-reported iteration number |
| `routing_strategy` | Optional | Requested strategy profile, subject to tenant policy |

Final field names, wire format, size limits, validation rules, and
compatibility behavior belong in a subsequent API Contract.

### 5.3 Propagation mechanisms

-   **Gateway SDK:** a task-scoped client stores immutable task-level
    context and injects it into each Request; stage is updated at stage
    transitions.
-   **Framework middleware:** integrations for Agent frameworks inject
    metadata at the LLM-call boundary.
-   **OpenAI-compatible API:** callers pass supported metadata in the
    Request body or agreed headers.
-   **Direct HTTP integration:** callers explicitly send metadata on
    each Request.

The SDK is a convenience, not a requirement. Third-party callers that do
not use it can still use ordinary Gateway routing.

### 5.4 Missing or invalid metadata

Missing task metadata must not automatically make a normal LLM Request
unusable.

| Input condition | Proposed behavior |
|---|---|
| Complete task and stage context | Apply task-aware, stage-aware routing. |
| Task context present, stage absent | Use task/session context and a generic or inferred stage. |
| Session only | Apply session continuity where supported; do not invent Task semantics. |
| No task/session metadata | Perform ordinary Request routing. |
| Unsupported stage | Use generic routing or return a clear client error, according to API policy. |
| Malformed metadata | Reject invalid fields or ignore only explicitly designated non-critical fields. |

The MVP should record metadata coverage so the product team can measure
how often callers provide useful context.

### 5.5 Propagation and concurrency

SDK implementations must avoid mutable global context shared across
concurrent Tasks. Task-scoped clients or request-scoped context
propagation should be used. In asynchronous Python integrations,
mechanisms such as `contextvars` may be useful, but must be tested
across spawned tasks, background work, and Subagents.

Caller-supplied identifiers are correlation values, not authorization
credentials. Tenant scoping and access control are enforced
independently.

## 6. Coding Stage-aware Routing

### 6.1 Initial stage taxonomy

| Stage | Typical objective | Routing considerations |
|---|---|---|
| `planning` | Understand goal and decompose work | Reasoning, instruction following, structured output |
| `repository_exploration` | Understand repository and locate code | Context window, retrieval/synthesis quality, latency |
| `code_generation` | Create or modify code | Coding quality, tool calling, structured output |
| `debugging` | Diagnose errors and propose fixes | Reasoning, code understanding, iterative efficiency |
| `review` | Inspect changes and identify defects | Defect detection, reasoning, context coverage |
| `testing_analysis` | Interpret test output and failures | Log/context capacity, diagnostic quality |
| `completion_evaluation` | Assess whether work is complete | Instruction adherence, evidence-based reasoning |

This taxonomy is a routing vocabulary, not an Agent workflow
specification. Agents may use different internal step names; integration
layers map them to supported Gateway values.

### 6.2 Explicit versus inferred stage

When `stage` is supplied by the Agent Runtime, the Gateway treats it as
the authoritative declared stage, subject to validation. When absent,
the Gateway may infer a likely request class using rules or a
classifier. Inferred stage must be recorded as inferred, with provenance
and confidence where available. It must not be represented as
caller-declared fact.

### 6.3 Stage is a routing signal, not a command

Stage influences candidate ranking and strategy selection, but cannot
override hard constraints such as tenant policies, model capabilities,
context-window requirements, tool-calling or structured-output
requirements, privacy/provider restrictions, and Request-level budget
constraints.

## 7. Model Stickiness and Switching

### 7.1 Objective

Repeatedly switching models during a long-running Task can introduce
behavioral differences, incompatible tool-call schemas, context-window
mismatches, prompt-cache loss, changed reasoning/output formats, and
cold-start latency. Conversely, rigidly keeping one model may be
suboptimal when later stages need different capabilities or the current
model is unavailable.

### 7.2 Proposed policy

Use **continuity by default, capability-safe switching when justified**.

Prefer the previously selected model or compatible model family for a
Session when it remains eligible and healthy, satisfies hard
requirements, has acceptable expected cost/latency/quality, and
continuity/cache benefits are meaningful.

Switch when the current model/provider is unhealthy; a new stage
requires unsupported capabilities; context exceeds usable capacity;
policy or budget makes the current choice ineligible; or measured
expected value justifies a compatible alternative.

### 7.3 Switching safeguards

Before switching, evaluate context-window capacity; tool-calling and
tool-schema compatibility; structured-output support; streaming and
response-format compatibility; reasoning behavior; prompt-cache
compatibility and cache-loss cost; provider protocol differences; and
model availability/health.

The Gateway cannot guarantee semantic continuity merely by selecting a
similar model. The Agent Runtime remains responsible for supplying the
correct conversation and task context to each Request.

### 7.4 Stickiness scope

Session stickiness and Task identity are not assumed to be one-to-one. A
caller may use one Session for a Task, multiple Sessions for one Task,
or another mapping. The API contract must define semantics explicitly.
Message fingerprinting may be explored as a best-effort heuristic, but
must not be treated as reliable identity or authorization.

## 8. Context Compatibility

The Gateway should maintain or consume a Model Capability Registry
describing:

-   Maximum context window and output-token limit.
-   Tool/function calling support.
-   Structured-output and schema support.
-   Streaming support.
-   Multimodal input support, if relevant.
-   Reasoning capabilities and supported controls.
-   Prompt-caching support and constraints.
-   Supported API parameters and protocol differences.
-   Provider availability, health, and policy eligibility.

Distinguish **hard constraints** from **soft preferences**. A Request
requiring tool calling must not be routed to a candidate without it. A
Request exceeding a model's context capacity must not be routed there. A
preference for lower latency may be traded against cost or quality
according to the selected strategy.

Capability data should be versioned or timestamped where appropriate
because provider/model capabilities change.

## 9. Budget Awareness and Economics

### 9.1 Request-level budget

The Gateway owns Request-level controls within the established billing
architecture: Request-level reservation and settlement; maximum
cost/token constraints where supported; pricing snapshots and usage
accounting; retry/fallback cost handling according to Doc 02; and
Request-level policy enforcement.

### 9.2 Task-level budget

The Agent Runtime owns the authoritative Task budget, such as maximum
total cost, maximum LLM Requests or iterations, elapsed time, tool
executions, human-approval thresholds, and cancellation/termination
policy.

The Gateway can expose correlated usage/cost summaries and accept policy
hints, but must not silently assume ownership of the Task budget.

### 9.3 Task-level economics

A key product metric is **Cost per Successful Coding Task**, not merely
cost per token or Request. This requires an outcome definition supplied
by the Agent Runtime or evaluation harness. The Gateway aggregates
attributed costs and correlates them with reported outcomes; it cannot
independently decide that a coding task succeeded.

Useful metrics include cost per successful/failed Task; cost by stage,
model, and Provider; Requests and Attempts per Task; retry/fallback
overhead; cache impact where measurable; and time to completion where
reliable timestamps are supplied.

## 10. Retry, Fallback, and Failure Semantics

### 10.1 Transport failure versus task-quality failure

| Failure type | Example | Primary owner | Expected behavior |
|---|---|---|---|
| Transport/provider failure | Connection failure proven before send, authoritative rejection without execution, or provider-safe idempotent replay | Gateway | Retry/fallback only when the retry-safety contract allows it; timeout by itself is not sufficient |
| Rate limiting | Provider 429 | Gateway | Backoff, retry, or eligible fallback |
| Capability mismatch | Candidate lacks required tool support | Gateway | Exclude before execution |
| Invalid request | Malformed payload/unsupported parameter | Gateway/API | Return clear error; do not retry blindly |
| Coding-quality failure | Generated code fails tests | Agent Runtime | Analyze and decide next step |
| Task-level failure | Requirements unmet or budget exhausted | Agent Runtime | Stop, escalate, or request human input |

### 10.2 Fallback constraints

Fallback candidates must satisfy the same hard capability and policy
constraints as the original route. Fallback must respect tenant/provider
restrictions and billing rules.

A transport retry/fallback is a Provider Attempt concern within one
logical Request, subject to Docs 01--03. A timeout alone does not prove
that execution did not occur: when the Provider outcome is unknown, the
Gateway must keep the original Request and Reservation bound to that
Attempt and recover or reconcile it; it must not start another Attempt
unless the shared retry-safety contract permits safe replay. This is not
the same as the Agent Runtime creating a new logical Request after
reviewing a poor-quality answer.

### 10.3 Quality feedback is not a retry command

The Gateway may receive feedback that a response was associated with a
failed test or unsuccessful Task. That feedback informs future routing
evaluation; it does not authorize the Gateway to execute tests, judge
code, or autonomously restart the Task.

## 11. Routing Engine Architecture

### 11.1 Generic routing core

Proposed logical stages:

1.  Request normalization and metadata validation.
2.  Tenant policy and authorization filtering.
3.  Candidate generation.
4.  Hard capability-constraint filtering.
5.  Signal collection: health, latency, price, context, cache, and
    continuity.
6.  Strategy evaluation and candidate scoring.
7.  Route Decision with rationale.
8.  Provider execution, eligible retries, and fallback.
9.  Usage, cost, and observability recording consistent with Docs
    01--03.

### 11.2 Coding workload extension

Coding-specific signals may include declared/inferred stage; coding
capability profile; context/repository-size requirements supplied by
caller; tool-calling and structured-output requirements; session
continuity; historical performance for comparable coding stages/tasks;
external test-pass/task-completion feedback; and cost/latency per
successful task.

### 11.3 Strategy profiles

| Strategy | Primary objective | Typical behavior |
|---|---|---|
| `coding_balanced` | Balance quality, cost, latency | Default weighted trade-off |
| `coding_quality_first` | Prioritize expected coding quality | Prefer stronger eligible candidates within policy/budget |
| `coding_cost_optimized` | Reduce expected cost | Prefer lower-cost candidates satisfying guardrails |
| `coding_long_context` | Support large-context workloads | Initially a capability constraint/profile, not necessarily a distinct strategy |

Exact weights, thresholds, and rankings must be established empirically,
not asserted by this proposal.

### 11.4 Explainability

For each Route Decision, expose selected model/Provider; applied
strategy; explicit and inferred context used; key decision signals;
candidates excluded by hard constraints and reasons, subject to safe
disclosure; whether stickiness influenced the choice; whether a switch
occurred and why; and fallback history.

## 12. Observability and Evaluation

### 12.1 Request-level observability

Reuse the Request and Provider Attempt model in Doc 01. Relevant
dimensions include Request/Attempt IDs, tenant and timestamps;
Task/Session correlation identifiers when supplied; task type and stage
with provenance; selected strategy/model/Provider; latency and
time-to-first-token where applicable; token usage and cost;
retry/fallback count and reasons; and error category/outcome confidence
as defined by the lifecycle contract.

### 12.2 Task-level aggregation

Where valid correlation identifiers are available, provide aggregated
Requests and Attempts per Task/Session; cost and token usage by stage;
model distribution and switching events; retry/fallback overhead;
latency distribution; and reported Task outcome/test status.

This is an analytical view over correlated Requests, not proof that the
Gateway owns Task lifecycle.

### 12.3 External feedback contract

The Agent Runtime or benchmark harness may report Task started, stage
entered/completed, tests passed/failed, Task completed/failed, human
intervention required, and failure category/completion reason.

A future API specification should define an authenticated feedback
contract. Feedback must be correlated to the tenant and Task/Session,
and its source and timestamp retained. Arbitrary unauthenticated outcome
claims must not be treated as ground truth.

### 12.4 Evaluation metrics

Primary metrics:

1.  Task Completion Rate.
2.  Test Pass Rate.
3.  Cost per Successful Task.
4.  Time to Completion.
5.  Human Intervention Rate.
6.  Retry/Fallback Rate.
7.  Regression Rate.
8.  Cost and latency by stage.

Benchmarks must hold Agent Harness, tools, task inputs, context policy,
and budgets constant. Compare static model selection with Gateway
strategies. The product hypothesis is supported if the Gateway achieves
better coding outcomes at comparable cost, or comparable outcomes at
lower cost, without unacceptable latency/reliability regression.

## 13. Security, Privacy, and Tenant Isolation

Task and Session metadata are untrusted caller input unless
authenticated and validated. They must not be used as authorization
credentials.

The Gateway must scope records and aggregates to the authenticated
tenant; prevent cross-tenant access through guessed/reused identifiers;
apply existing PII, secret, retention, and logging policies; avoid
storing full prompts or repository content solely for routing when
derived signals or caller metadata suffice; subject content
classification to tenant privacy policy; prevent cross-tenant exposure
of routing history/outcomes; and authenticate/validate external outcome
feedback.

Detailed authentication, authorization, tenant, and data-retention
requirements remain consistent with Doc 03 and the security design
owner.

## 14. MVP Scope and Roadmap

### 14.1 MVP

This MVP builds on the Gateway and billing foundation defined in Docs
01--03 (Request lifecycle, Reservation, Settlement, and Ledger). The
items below are only the capabilities this coding-workload scenario adds;
billing invariants are unchanged and governed by the shared release gate
in Doc 03 Section 14.

-   Multi-provider Gateway API and Model Capability Registry.
-   Generic candidate filtering and routing engine.
-   Coding workload profile with a small stage taxonomy.
-   Optional `task_id`, `session_id`, `task_type`, and `stage` metadata.
-   Session correlation and basic model stickiness.
-   Explicit metadata precedence and basic missing-metadata behavior.
-   Capability-safe retry/fallback.
-   Request-level usage/cost tracking and task/session aggregation when
    IDs are supplied.
-   Routing decision explanations.
-   Basic benchmark harness comparing static routing and Gateway
    strategies.

### 14.2 Deferred / future

Defer full Agent Runtime or proprietary planner; Gateway-managed
Task/Step lifecycle and checkpointing; sophisticated learned routing
trained on task outcomes; reliable Task identity inference from message
fingerprints; autonomous quality-driven Task retries; deep Agent-state
adaptive switching; provider payable accounting beyond Doc 02; and broad
workload profiles beyond Coding until the generic core is validated.

### 14.3 MVP success criteria

1.  A caller can route ordinary LLM Requests without task metadata.
2.  A caller can optionally provide Task/Session/Stage context.
3.  Related Requests can be aggregated without Gateway ownership of Task
    lifecycle.
4.  Hard capability constraints are never violated by normal routing or
    fallback.
5.  Routing decisions and Request costs are auditable.
6.  Controlled benchmarks show at least one strategy measurably improves
    cost, quality, latency, or reliability against a static baseline.

Thresholds and acceptance targets belong in the implementation/benchmark
plan.

## 15. Architecture Decisions (Proposed ADRs)

These decisions are proposed for review. They are not accepted contracts
until approved and reconciled with Docs 01--03.

### ADR-0401 --- Agent Runtime Owns Task Lifecycle

**Decision:** Agent Runtime owns Task creation, planning, Step
execution, context management, checkpointing, and completion. Gateway
owns individual LLM Requests and Provider Attempts.

**Rationale:** Keeps Gateway focused on model access/routing and avoids
duplicating Agent orchestration.

### ADR-0402 --- Task, Step, Request, and Attempt Are Distinct

**Decision:** A Task may contain many Steps and Requests; a Request may
contain multiple Provider Attempts. A Step may require no LLM call.

**Rationale:** Prevents task execution semantics from being conflated
with request execution and billing semantics.

### ADR-0403 --- Agent Runtime Is Authoritative for Explicit Task Context

**Decision:** Caller-provided `task_id`, `task_type`, `stage`, and
related metadata are authoritative declarations after validation.
Gateway may infer missing request classification but must preserve
provenance and must not silently override explicit values.

**Rationale:** Agent Runtime knows its execution state; Gateway should
not claim certainty it does not have.

### ADR-0404 --- Support Hybrid Context Propagation

**Decision:** Support explicit metadata, session-based correlation, and
best-effort intelligent inference. No single mechanism is mandatory for
all callers.

**Rationale:** Balances routing quality with low integration friction
and compatibility with third-party Agents.

### ADR-0405 --- Session Is a Correlation and Continuity Scope, Not Necessarily a Task

**Decision:** Do not assume `session_id` and `task_id` are one-to-one.
Their relationship is defined by caller/integration contract. Message
fingerprinting, if explored, is heuristic only.

**Rationale:** Agent frameworks differ in session/task semantics;
inferred identity is not reliable enough for accounting or
authorization.

### ADR-0406 --- Continuity by Default, Capability-Safe Switching

**Decision:** Prefer model/session continuity when beneficial, but
switch when health, hard capability requirements, policy, budget, or
measured expected value justifies it. Never violate hard constraints to
preserve stickiness.

**Rationale:** Balances cache/behavioral continuity against
stage-specific needs and Provider reliability.

### ADR-0407 --- Gateway Owns Request Economics; Agent Runtime Owns Task Budget

**Decision:** Gateway enforces Request-level billing and policy
controls. Agent Runtime remains authoritative for aggregate Task budgets
and termination.

**Rationale:** Preserves billing boundaries in Docs 01--03 and avoids
hidden ownership of Agent execution.

### ADR-0408 --- Separate Transport Recovery from Coding-Quality Iteration

**Decision:** Gateway handles eligible transport/provider retries and
fallback within a Request. Agent Runtime handles quality-driven new
Steps or Requests after evaluating output/tests.

**Rationale:** Provider availability is a Gateway concern; code
correctness and task progress are Agent concerns.

### ADR-0409 --- Evaluate Routing Using External Execution Outcomes

**Decision:** Accept authenticated Task/Stage outcome feedback from
Agent Runtimes or benchmark harnesses. Use it for correlation and
strategy evaluation, not to execute or complete Tasks.

**Rationale:** Cost per successful Task requires execution outcomes,
while task execution remains outside Gateway.

## 16. Open Questions

1.  What exact API field/header carries `task_id`, `session_id`,
    `task_type`, and `stage`?
2.  What are canonical stage values and their versioning policy?
3.  What are the semantics and retention policy for Session state?
4.  Should Session stickiness be tenant-configurable,
    strategy-configurable, or both?
5.  What minimum signals justify a model switch?
6.  How should prompt-cache value be estimated when Provider telemetry
    is incomplete?
7.  What outcome-feedback schema and authentication mechanism should be
    standardized?
8.  Which capability fields are mandatory in the initial registry?
9.  What benchmark suite and acceptance thresholds represent meaningful
    product value?
10. Which principal, API Key, role/permission, audit, and secret-management
    contracts must be covered by the planned Document 05 --- Tenant & Security Design?

These questions do not block this architecture proposal. Resolve them
before finalizing corresponding production API and implementation
contracts.

### ADRs Requiring Confirmation

The following are proposed decisions, not accepted contracts. Confirm or
revise them before finalizing the corresponding production API and
runtime contracts:

| ADR | Decision to confirm | Recommended default |
|---|---|---|
| ADR-0306 (Doc 03) | Provider Payable recognition | Keep provider costs as operational attribution; defer payable posting to an accounting ADR. |
| ADR-0308 (Doc 03) | Shared event envelope | Adopt the event identifiers, schema and aggregate versions, tenant/request/attempt IDs, and causation/correlation IDs defined in Doc 03. |
| ADR-0309 (Doc 03) | Policy changes and replay | Re-authorize replay access under current permissions; preserve the original execution and pricing decisions. |
| ADR-0310 (Doc 03) | Over-reservation handling | Collect from available balance if sufficient; otherwise record receivable/debt and apply spending restrictions. |
| ADR-0401-0409 (Doc 04) | Task-aware routing and Runtime/Gateway ownership | Review the individual proposals in Section 15; accept after confirming API and operational consequences. |
| ADR-0410 (Doc 04) | Task cancellation and active Requests | Runtime cancellation is idempotent and identifies active Request IDs; Gateway resolves each Attempt and retains funds until safe settlement or reconciliation. |
| ADR-0411 (Doc 04) | Aggregate Task budget under concurrency | Runtime is authoritative and atomically coordinates concurrent Request budget consumption; Gateway enforces Request-level reservations and any explicit per-Request cap. |
| ADR-0412 (Doc 04) | Idempotency across retry and resume | Transport redelivery of the same logical Request reuses its key and payload; a changed prompt or step after checkpoint resume creates a new Request and key, correlated to the same Task. |
| ADR-0413 (Doc 04) | Long-running Request reservation recovery | Expiration triggers reconciliation and alerting, never automatic release; define renewal, maximum operational age, escalation, and manual recovery before launch. |
| ADR-0414 (Doc 04) | Task/Session ownership and identity | Bind correlation records and feedback to authenticated tenant and authorized Runtime/principal scope; define same-tenant sharing and collision behavior. |

Doc 03 P0 decisions ADR-0301-0305 and ADR-0307 are already accepted.
Doc 04 ADR-0401-0414 and Doc 03 P1 ADR-036/038/039/040 require explicit
confirmation or documented disposition. Doc 04 uses the `ADR-04xx`
numbering scheme (document 04 + sequence) to avoid colliding with
Doc 03's `ADR-03xx` range.

## 17. Cross-Document Consistency Requirements

Doc 04 extends routing behavior but must not redefine foundational
contracts in Docs 01--03.

-   **Doc 01:** Request lifecycle, Provider Attempt lifecycle, routing
    decision records, retry/fallback execution, and observability remain
    authoritative.
-   **Doc 02:** Request-level reservation, usage, settlement, pricing
    snapshots, and ledger semantics remain authoritative.
-   **Doc 03:** Cross-document identifiers, tenant boundaries,
    idempotency, event envelope, and shared contracts remain
    authoritative.
-   **Doc 04:** Adds workload/task context, coding-stage routing,
    session continuity, context compatibility, and Task-level evaluation
    aggregation.

Any conflict must be resolved through an explicit cross-document
decision or ADR. Doc 04 must not silently change the meaning of Request,
Attempt, Reservation, Settlement, Tenant, or idempotency.

**Document status:** Proposed. This document establishes architecture
direction and MVP scope. Detailed API schemas, database changes,
algorithm weights, and operational SLOs require subsequent
specifications and review.
