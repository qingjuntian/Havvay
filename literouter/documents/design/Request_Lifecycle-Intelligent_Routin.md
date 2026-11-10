# Request Lifecycle & Intelligent Routing Design

**Project:** Unified LLM Gateway & AI Infrastructure Platform  
**Document:** Architecture Design 01  
**Version:** 1.0  
**Status:** Proposed  
**Architecture:** Modular Monolith + Independent Data Plane  
**Primary Stack:** Python, FastAPI, PostgreSQL, Redis, HTTPX

---

# 1. Overview

## 1.1 Purpose

This document defines the request processing lifecycle and intelligent routing architecture of the LLM Gateway platform.

The platform provides a unified API interface for multiple LLM providers, including:

- OpenAI
- Anthropic
- Google
- DeepSeek
- AWS Bedrock
- Google Vertex AI
- Self-hosted inference services such as vLLM and SGLang
- Other OpenAI-compatible providers

The Gateway must support:

1. Unified API access.
2. Authentication and authorization.
3. Organization-level policies and quotas.
4. Model resolution.
5. Intelligent provider selection.
6. Provider execution and protocol translation.
7. Retry and fallback.
8. Streaming and non-streaming responses.
9. Usage metering and request tracking.
10. Reliable asynchronous event processing.

## 1.2 Design Goals

| Goal | Description |
|---|---|
| Compatibility | Support OpenAI-compatible APIs |
| Extensibility | Add providers without changing core routing logic |
| Reliability | Handle provider failures and transient errors |
| Performance | Minimize gateway overhead |
| Observability | Trace every request and provider attempt |
| Security | Enforce tenant isolation and access policies |
| Financial Safety | Provide accurate usage information for billing |
| Scalability | Support horizontal scaling |
| Portability | Support China and global deployments |

## 1.3 Non-Goals

The initial implementation will NOT include:

- AI/ML-based routing decisions.
- Semantic caching.
- Agent execution runtime.
- Multi-region active-active routing.
- Automatic model quality evaluation.
- GPU scheduling and inference orchestration.

These capabilities can be introduced in later phases.

---

# 2. Architecture Overview

## 2.1 Logical Architecture

The system is divided into two logical planes.

### Control Plane

Responsible for configuration and management:

- Organization management
- API key management
- Provider registry
- Model registry
- Deployment configuration
- Routing policies
- Pricing configuration
- Access policies
- Administrative operations

### Data Plane

Responsible for real-time request execution:

- Request ingress
- Authentication
- Authorization
- Policy evaluation
- Budget reservation
- Model resolution
- Candidate selection
- Routing decisions
- Provider execution
- Retry and fallback
- Usage extraction
- Response delivery

## 2.2 Request Processing Architecture

```text
                         Client
                           |
                           v
                    Load Balancer
                           |
                           v
                   FastAPI Gateway
                           |
                           v
                 Request Initialization
                           |
                           v
                   Authentication
                           |
                           v
                 Authorization / Policy
                           |
                           v
                  Budget Reservation
                           |
                           v
                   Model Resolution
                           |
                           v
                  Candidate Generation
                           |
                           v
                   Policy Filtering
                           |
                           v
                    Health Filtering
                           |
                           v
                   Routing Decision
                           |
                           v
                   Provider Adapter
                           |
                           v
                    Provider API
                           |
                           v
                   Response Processing
                           |
                 +---------+---------+
                 |                   |
                 v                   v
            Client Response     Async Events
                                     |
                         +-----------+-----------+
                         |           |           |
                         v           v           v
                       Usage       Audit     Analytics
                      Billing      Events      Events
```

## 2.3 Main Components

| Component | Responsibility |
|---|---|
| API Gateway | HTTP ingress and response handling |
| Authentication Service | API key verification |
| Authorization Service | Tenant and resource permissions |
| Policy Engine | Request-level policy evaluation |
| Budget Manager | Budget reservation |
| Model Resolver | Resolve logical model identifiers |
| Candidate Generator | Find eligible deployments |
| Routing Engine | Rank and select deployments |
| Provider Adapter | Translate requests and responses |
| Provider Health Manager | Maintain deployment health |
| Retry Manager | Retry and fallback decisions |
| Usage Extractor | Extract token and usage information |
| Event Publisher | Publish asynchronous business events |

---

# 3. Core Domain Objects

## 3.1 Request

A Request represents one logical API call initiated by a client.

```python
@dataclass
class GatewayRequest:
    request_id: str
    trace_id: str

    organization_id: str
    team_id: str | None
    api_key_id: str

    requested_model: str
    messages: list

    stream: bool

    request_format: str
    parameters: dict

    created_at: datetime
```

Important properties:

- One Request may contain multiple Provider Attempts.
- One Request has one final client-visible outcome.
- Request identity must remain stable across retries.
- Every Attempt must reference the parent Request.

## 3.2 RequestAttempt

An Attempt represents one actual provider execution.

```python
@dataclass
class RequestAttempt:
    attempt_id: str
    request_id: str

    attempt_number: int

    provider_id: str
    deployment_id: str
    provider_model_id: str

    status: str

    started_at: datetime | None
    completed_at: datetime | None

    error_code: str | None

    latency_ms: int | None
```

One logical request may produce multiple Attempts.

Example:

```text
Request: req_123

Attempt 1:
    Provider: Anthropic
    Deployment: anthropic-us
    Status: TIMEOUT

Attempt 2:
    Provider: Bedrock
    Deployment: bedrock-us
    Status: SUCCEEDED
```

## 3.3 RoutingDecision

A RoutingDecision records why a particular deployment was selected.

```python
@dataclass
class RoutingDecision:
    request_id: str

    strategy: str

    candidate_deployments: list[str]
    excluded_deployments: list[str]

    selected_deployment: str

    decision_reason: str

    policy_version: str

    created_at: datetime
```

Routing decisions must be auditable.

The platform should be able to explain why a particular provider was selected.

## 3.4 Unified Request and Response

Provider-specific request formats should be normalized into an internal representation.

```python
@dataclass
class UnifiedRequest:
    model: str

    messages: list

    stream: bool

    temperature: float | None
    max_tokens: int | None

    tools: list | None

    response_format: dict | None

    provider_options: dict

    metadata: dict
```

The internal representation must preserve provider-specific parameters.

Do not silently discard parameters that cannot be normalized.

Provider-specific extensions should be retained in `provider_options`.

---

# 4. Complete Request Lifecycle

## 4.1 Request State Machine

```text
CREATED
   |
   v
VALIDATING
   |
   v
AUTHENTICATING
   |
   v
AUTHORIZING
   |
   v
RESERVING_BUDGET
   |
   v
RESOLVING_MODEL
   |
   v
ROUTING
   |
   v
EXECUTING
   |
   +------------------+
   |                  |
   v                  v
SUCCEEDED           FAILED
   |
   v
SETTLEMENT_PENDING
   |
   v
COMPLETED
```

Additional terminal or exceptional states:

- REJECTED
- CANCELLED
- PARTIALLY_COMPLETED
- SETTLEMENT_FAILED

Request execution and financial settlement are separate lifecycles.

A request may successfully return a response while its billing settlement is still pending.

The platform must not silently lose that settlement.

## 4.2 Step 1: Request Ingress

Responsibilities:

1. Receive HTTP request.
2. Generate Request ID.
3. Generate Trace ID.
4. Validate basic HTTP structure.
5. Parse request format.
6. Enforce request body size limits.
7. Extract API Key.
8. Initialize request context.

Example:

```python
@app.post("/v1/chat/completions")
async def chat_completions(
    request: Request,
):
    request_id = generate_request_id()
    trace_id = get_or_create_trace_id()

    context = RequestContext(
        request_id=request_id,
        trace_id=trace_id,
    )

    return await request_service.execute(
        request,
        context,
    )
```

Request ID format:

```text
req_<unique_id>
```

Requirements:

- Globally unique.
- Stable across all provider attempts.
- Returned in response headers.
- Included in logs and events.

## 4.3 Step 2: Authentication

Authenticate the API Key.

Processing:

1. Extract Bearer Token.
2. Validate key format.
3. Compute key hash.
4. Look up cached key metadata.
5. Query database if cache misses.
6. Check key status and expiration.
7. Resolve organization and team.
8. Build authenticated principal.

Example:

```python
@dataclass
class Principal:
    user_id: str | None

    organization_id: str
    team_id: str | None

    api_key_id: str

    permissions: set[str]
```

API key metadata can be cached in Redis.

Cache invalidation must happen when:

- Key is revoked.
- Key expires.
- Key permissions change.
- Organization is suspended.

Authentication must fail closed when key validity cannot be established.

## 4.4 Step 3: Authorization and Policy Evaluation

Check whether the authenticated principal can execute the requested operation.

Policies include:

- Organization status.
- API Key permissions.
- Model access permissions.
- Team restrictions.
- Request rate limits.
- Token limits.
- Budget limits.
- Allowed provider restrictions.
- Region restrictions.
- Data retention restrictions.
- Zero Data Retention requirements.

Policy evaluation should return a structured result.

```python
@dataclass
class PolicyDecision:
    allowed: bool

    reason: str | None

    allowed_models: list[str] | None
    allowed_providers: list[str] | None

    max_cost: Decimal | None

    region_constraints: list[str]

    require_zdr: bool
```

Policy evaluation must happen before routing.

A routing algorithm must never override security or compliance restrictions.

## 4.5 Step 4: Budget Reservation

Before calling an external provider, reserve the estimated maximum request cost.

The reservation prevents concurrent requests from spending more than the available budget.

Conceptually:

```text
Available Budget
       |
       v
Estimate Maximum Request Cost
       |
       v
Atomic Reservation
       |
       +---- Success --> Continue
       |
       +---- Failure --> Reject Request
```

Reservation should be transactional and idempotent.

The exact reservation algorithm, database locking, settlement and reconciliation rules are defined in Design Document 02: Billing & Ledger Design.

Important:

- Do not reserve the same request twice.
- Do not release a reservation before execution has definitively finished.
- Handle crashed workers and expired reservations.
- Keep reservation state separate from posted financial transactions.

## 4.6 Step 5: Model Resolution

The client requests a logical model identifier.

Example:

```json
{
  "model": "claude-sonnet"
}
```

The Model Resolver maps the identifier to the internal Model entity.

```text
claude-sonnet
      |
      v
Model Registry
      |
      v
Model ID
      |
      v
Eligible Deployments
```

The resolver must support:

- Public model aliases.
- Versioned model identifiers.
- Organization-specific aliases.
- Deprecated model aliases.
- Model capability metadata.

If the model does not exist or is unavailable, return a clear error.

Do not silently substitute a different model unless the client has explicitly enabled that behavior.

---

# 5. Intelligent Routing Engine

## 5.1 Routing Pipeline

The Routing Engine consists of five stages.

```text
Model Resolution
      |
      v
Candidate Generation
      |
      v
Capability Filtering
      |
      v
Policy / Compliance Filtering
      |
      v
Health Filtering
      |
      v
Cost Estimation
      |
      v
Strategy Ranking
      |
      v
Routing Decision
```

Candidate filtering and candidate ranking must remain separate.

Filtering determines which deployments are eligible.

Ranking determines which eligible deployment is preferred.

## 5.2 Candidate Generation

Find all deployments associated with the logical model.

Example:

```text
Logical Model: claude-sonnet

Deployments:
    1. Anthropic US
    2. Bedrock US
    3. Vertex EU
```

Candidate generation should use the Model Registry and Deployment Registry.

Avoid querying every provider dynamically during each request.

## 5.3 Capability Filtering

A deployment must support the required request capabilities.

Examples:

- Streaming.
- Tool calling.
- Vision.
- JSON mode.
- Maximum context length.
- Maximum output tokens.
- Audio input.
- Audio output.

Example:

```python
def supports_request(
    deployment: Deployment,
    request: UnifiedRequest,
) -> bool:

    capabilities = deployment.capabilities

    if request.stream and not capabilities.streaming:
        return False

    if request.tools and not capabilities.tool_calling:
        return False

    if request.requires_vision and not capabilities.vision:
        return False

    return True
```

Capability metadata should be versioned and maintained per deployment.

## 5.4 Policy and Compliance Filtering

Exclude deployments that violate:

- Organization provider restrictions.
- Region restrictions.
- Data residency policies.
- ZDR requirements.
- Commercial availability restrictions.
- Provider-specific contractual restrictions.

For China and global deployments, Region must be a first-class routing constraint.

The router must not send a request to another region merely because that region is cheaper or faster.

## 5.5 Health Filtering

Each deployment maintains its own health state.

```text
HEALTHY
DEGRADED
UNAVAILABLE
UNKNOWN
```

Health information can include:

- Recent error rate.
- P95 latency.
- Consecutive failures.
- Circuit breaker state.
- Provider quota status.
- Last successful health check.

Health information should be maintained asynchronously and cached in Redis.

Do not perform a separate external health check for every incoming request.

## 5.6 Routing Strategies

MVP routing strategies:

### Fixed

Select a specifically configured deployment.

### Priority

Select the highest-priority eligible deployment.

### Lowest Cost

Select the deployment with the lowest estimated customer cost or configured provider cost, according to the selected pricing objective.

The optimization objective must be explicit.

### Weighted

Select a deployment according to configured weights.

Weighted routing should use a stable randomization strategy and support gradual traffic distribution.

### Balanced

Combine normalized cost, latency and error-rate information.

Example:

```python
score = (
    cost_weight * normalized_cost
    + latency_weight * normalized_latency
    + error_weight * normalized_error_rate
)
```

Lower scores indicate preferred candidates.

Initial example weights:

| Strategy | Cost | Latency | Error Rate |
|---|---:|---:|---:|
| Cheapest | 80% | 10% | 10% |
| Fastest | 10% | 80% | 10% |
| Reliable | 10% | 10% | 80% |
| Balanced | 40% | 30% | 30% |

These weights are configuration examples, not fixed industry standards.

## 5.7 Router Interface

The Router should be a pure decision component.

```python
class RoutingEngine:

    def select(
        self,
        request: UnifiedRequest,
        model: Model,
        candidates: list[Deployment],
        policy: RoutingPolicy,
        health_snapshot: dict,
    ) -> RoutingDecision:
        ...
```

The Router must NOT:

- Call external providers.
- Execute database transactions.
- Perform billing settlement.
- Modify provider credentials.
- Generate client responses.

Its responsibility is to produce a routing decision.

This separation makes the routing algorithm independently testable.

---

# 6. Provider Adapter Architecture

## 6.1 Adapter Pattern

All providers must implement a common internal interface.

```python
from typing import Protocol, AsyncIterator


class ProviderAdapter(Protocol):

    async def generate(
        self,
        request: UnifiedRequest,
        deployment: Deployment,
    ) -> UnifiedResponse:
        ...

    async def stream(
        self,
        request: UnifiedRequest,
        deployment: Deployment,
    ) -> AsyncIterator[UnifiedChunk]:
        ...
```

Provider adapters are responsible for:

- Authentication with provider credentials.
- Request translation.
- Response translation.
- Streaming translation.
- Provider error normalization.
- Provider usage extraction.
- Provider request ID extraction.

Provider-specific details must not leak into the core routing engine.

## 6.2 Adapter Implementations

```text
ProviderAdapter
    |
    +-- OpenAIAdapter
    |
    +-- AnthropicAdapter
    |
    +-- GoogleAdapter
    |
    +-- BedrockAdapter
    |
    +-- DeepSeekAdapter
    |
    +-- OpenAICompatibleAdapter
            |
            +-- vLLM
            +-- SGLang
            +-- Other Compatible Servers
```

## 6.3 Unified Error Model

Normalize provider errors.

```python
class ProviderError(Exception):

    code: str

    retryable: bool

    provider_id: str

    http_status: int | None
```

Suggested error categories:

```text
AUTHENTICATION_ERROR
PERMISSION_ERROR
INVALID_REQUEST
MODEL_NOT_FOUND
RATE_LIMITED
QUOTA_EXCEEDED
TIMEOUT
CONNECTION_ERROR
PROVIDER_UNAVAILABLE
PROVIDER_INTERNAL_ERROR
CONTENT_FILTERED
UNKNOWN_ERROR
```

Preserve the original provider error metadata for debugging, but never expose sensitive provider credentials or internal details to clients.

---

# 7. Retry, Fallback and Circuit Breaker

## 7.1 Retry Policy

Retry behavior must depend on the failure category.

| Failure | Retry | Fallback |
|---|---|---|
| Connection Error | Yes | Yes |
| Connection Timeout | Yes, bounded | Yes |
| HTTP 429 | Conditional | Yes |
| HTTP 500 | Conditional | Yes |
| HTTP 502 | Yes, bounded | Yes |
| HTTP 503 | Yes, bounded | Yes |
| HTTP 400 | No | No |
| Authentication Error | No | Conditional after operator intervention |
| Permission Error | No | No |
| Model Not Found | No | No |

Always consider:

- Retry-After.
- Total request deadline.
- Remaining retry budget.
- Provider quota.
- Retry backoff.
- Whether the request is safe to replay.

## 7.2 Retry Configuration

Example:

```python
@dataclass
class RetryPolicy:
    max_attempts: int = 3

    max_fallbacks: int = 2

    base_backoff_ms: int = 200

    max_backoff_ms: int = 2000

    total_timeout_seconds: int = 60
```

Use exponential backoff with jitter.

Do not allow retries to exceed the original request deadline.

The total attempt count includes the initial attempt.

## 7.3 Circuit Breaker

Each deployment has an independent circuit breaker.

```text
       CLOSED
          |
          | Failure Threshold Reached
          v
         OPEN
          |
          | Cooldown Expired
          v
       HALF_OPEN
          |
          +---- Success ----> CLOSED
          |
          +---- Failure ----> OPEN
```

Suggested initial parameters:

```python
@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5

    failure_window_seconds: int = 30

    open_duration_seconds: int = 30

    half_open_max_requests: int = 2
```

These parameters must be configurable.

Do not use one provider-wide circuit breaker for all regions and deployments.

## 7.4 Fallback Safety

A critical rule:

**Transparent cross-provider fallback is allowed only before the client receives irreversible partial output.**

For non-streaming requests, fallback is relatively straightforward.

For streaming requests:

- Before the first downstream content event, fallback may be possible.
- After content has been sent to the client, do not transparently restart on another provider.
- After partial output, terminate the stream and record the attempt outcome.
- Never concatenate outputs from two providers into one apparently continuous response.

This avoids duplicated or inconsistent model output.

## 7.5 Retry Idempotency

LLM generation requests are not necessarily idempotent.

A provider may have processed a request even when the Gateway did not receive its response.

Therefore:

- Distinguish connection failure before request transmission from ambiguous failures after transmission.
- Use provider idempotency support where available.
- Record each attempt independently.
- Do not assume a timeout means the provider did not execute the request.
- Account for possible duplicate provider charges.

The Gateway must not blindly retry every timeout.

---

# 8. Streaming Architecture

## 8.1 Streaming Requirements

Streaming is a first-class feature, not an optimization added later.

The platform must support:

- Server-Sent Events (SSE).
- Incremental response forwarding.
- Provider-specific stream translation.
- Client cancellation.
- Upstream cancellation.
- Heartbeats.
- Timeouts.
- Usage extraction.
- Backpressure.

## 8.2 Streaming Data Flow

```text
Client
  |
  v
FastAPI StreamingResponse
  |
  v
Unified Stream Processor
  |
  v
Provider Adapter
  |
  v
Provider SSE / HTTP Stream
  |
  v
Chunk Translation
  |
  v
Client
```

The Gateway should forward chunks as they arrive.

Do not buffer the entire generated response in application memory.

## 8.3 Streaming Lifecycle

```python
async def stream_response(
    request: UnifiedRequest,
    deployment: Deployment,
):

    adapter = adapter_registry.get(deployment.adapter_type)

    try:
        async for chunk in adapter.stream(
            request,
            deployment,
        ):
            yield serialize_sse(chunk)

    except asyncio.CancelledError:
        raise

    except ProviderError as exc:
        yield serialize_error_event(exc)

    finally:
        await finalize_attempt()
```

Production implementation must also explicitly close upstream response resources and release reservations or schedule settlement.

## 8.4 Client Disconnect

When the client disconnects:

1. Detect cancellation.
2. Cancel the upstream provider stream.
3. Close the HTTP response.
4. Finalize the attempt.
5. Record any available usage.
6. Settle or estimate the corresponding cost.
7. Release unused reservation.

Do not assume that disconnecting the client automatically stops provider billing.

## 8.5 Streaming Usage Extraction

Different providers report usage differently.

Some report usage in the final streaming event.

Others may not return complete usage information.

Support three usage sources:

1. Provider-reported usage.
2. Gateway-observed usage estimates.
3. Reconciled usage from provider-side records, where available.

Each UsageRecord must indicate its source and accuracy status:

```text
PROVIDER_REPORTED
GATEWAY_ESTIMATED
RECONCILED
UNKNOWN
```

Never silently treat estimated usage as provider-reported usage.

---

# 9. Request Orchestration

## 9.1 Application Service

The Request Service coordinates the complete lifecycle.

```python
class RequestService:

    async def execute(
        self,
        raw_request,
        context,
    ):

        request = await self.validator.validate(
            raw_request
        )

        principal = await self.auth.authenticate(
            context.api_key
        )

        policy = await self.policy.evaluate(
            principal,
            request,
        )

        reservation = await self.budget.reserve(
            principal,
            request,
        )

        model = await self.model_resolver.resolve(
            request.model
        )

        candidates = await self.candidate_service.find(
            model,
            request,
            policy,
        )

        decision = self.router.select(
            request,
            model,
            candidates,
            policy,
            await self.health.snapshot(candidates),
        )

        return await self.execution.execute(
            request,
            decision,
            reservation,
        )
```

This is a conceptual orchestration example.

The production implementation must include:

- Persistent Request creation.
- Attempt lifecycle management.
- Deadline propagation.
- Reservation cleanup.
- Structured error handling.
- Settlement event publication.
- Request cancellation.
- Idempotency.

Do not implement all these responsibilities inside a single FastAPI endpoint.

## 9.2 Separation of Responsibilities

```text
API Layer
   |
   v
Request Application Service
   |
   +-- Authentication
   |
   +-- Authorization
   |
   +-- Policy Engine
   |
   +-- Budget Manager
   |
   +-- Model Resolver
   |
   +-- Routing Engine
   |
   +-- Execution Engine
   |       |
   |       +-- Provider Adapter
   |       |
   |       +-- Retry Manager
   |
   +-- Usage Extractor
   |
   +-- Event Publisher
```

The API layer should remain thin.

The Application Service coordinates operations.

Domain services implement business decisions.

Infrastructure components handle databases, Redis, HTTP clients and message delivery.

---

# 10. Data Persistence and Event Processing

## 10.1 Request Persistence

Persist the following information:

### Request

- Request ID.
- Organization ID.
- API Key ID.
- Requested Model.
- Resolved Model.
- Request Status.
- Stream Flag.
- Usage.
- Customer Cost.
- Latency.
- Region.
- Trace ID.
- Created At.
- Completed At.

### Request Attempt

- Attempt ID.
- Request ID.
- Attempt Number.
- Provider ID.
- Deployment ID.
- Provider Request ID.
- Attempt Status.
- Error Code.
- Usage.
- Provider Cost.
- Latency.
- Start Time.
- Completion Time.

### Routing Decision

- Strategy.
- Candidate List.
- Excluded Candidates.
- Selected Deployment.
- Decision Reason.
- Policy Version.
- Decision Timestamp.

## 10.2 Event Architecture

Use a Transactional Outbox pattern.

```text
Gateway
   |
   v
PostgreSQL Transaction
   |
   +-- Request Update
   |
   +-- Attempt Update
   |
   +-- Outbox Event
           |
           v
       Event Worker
           |
     +-----+------+------+
     |            |      |
     v            v      v
   Usage         Audit  Analytics
  Consumer      Consumer Consumer
```

Recommended events:

```text
request.created
request.routed
request.attempt.started
request.attempt.failed
request.attempt.succeeded
request.completed
request.failed
request.cancelled

usage.recorded
billing.settlement.requested

provider.degraded
provider.recovered
```

Events should contain identifiers and necessary metadata rather than full prompts or responses.

Consumers must be idempotent.

## 10.3 Event Delivery Guarantees

Use at-least-once delivery with idempotent consumers.

Do not claim exactly-once delivery across PostgreSQL, Redis and external systems.

The business requirement is exactly-once financial effect, implemented through idempotency and reconciliation, not an assumption about message transport.

---

# 11. Security and Multi-Region Routing

## 11.1 Tenant Isolation

Every request must be associated with an Organization.

All database queries must enforce tenant scope.

The Gateway must never trust client-supplied organization IDs.

Resolve tenant identity from authenticated credentials.

## 11.2 Credential Security

Provider credentials must:

- Be encrypted at rest.
- Be accessed through a secure credential reference.
- Never appear in application logs.
- Support rotation.
- Be scoped by Provider and Region.

## 11.3 Region-aware Routing

Deployment metadata must include:

```python
@dataclass
class DeploymentRegion:
    provider_region: str
    processing_region: str
    data_residency_region: str
```

The router must enforce:

- Tenant region requirements.
- Data residency constraints.
- Provider processing location.
- Approved cross-region transfers.
- Provider contractual restrictions.

Region filtering happens before cost and latency ranking.

Cost optimization must never override compliance constraints.

---

# 12. Performance and Scalability

## 12.1 Technology Stack

| Layer | Technology |
|---|---|
| API | FastAPI |
| ASGI | Uvicorn |
| HTTP Client | HTTPX AsyncClient |
| Database | PostgreSQL |
| ORM | SQLAlchemy Async |
| Cache | Redis |
| Event Processing | Redis Streams / Worker |
| Observability | OpenTelemetry |

## 12.2 Async I/O Requirements

All network I/O in the Gateway hot path must be asynchronous.

Avoid:

- Synchronous HTTP clients.
- Blocking database calls.
- Blocking Redis calls.
- CPU-heavy calculations inside request handlers.
- Creating a new HTTP client for every request.

Reuse HTTP connection pools.

## 12.3 Connection Management

Each Gateway process owns its own HTTP and database pools.

Connection limits must be calculated across all deployed processes.

Example:

```text
3 Gateway Instances
    |
    +-- 2 Workers per Instance
            |
            +-- HTTP Connection Pool
            |
            +-- DB Connection Pool
```

Pool sizing must account for:

- Number of instances.
- Number of workers.
- Database maximum connections.
- Provider connection limits.
- Streaming concurrency.

## 12.4 Horizontal Scaling

Gateway instances should be stateless.

Shared state belongs in PostgreSQL or Redis.

```text
Load Balancer
    |
    +-- Gateway Instance 1
    |
    +-- Gateway Instance 2
    |
    +-- Gateway Instance N
             |
       +-----+------+
       |            |
    Redis       PostgreSQL
       |
    Event Workers
```

Long-lived streams require appropriate load balancer idle timeouts and graceful shutdown behavior.

---

# 13. Observability

## 13.1 Trace Structure

Every request should generate a distributed trace.

```text
HTTP Request
    |
    +-- Authentication
    |
    +-- Authorization
    |
    +-- Policy Evaluation
    |
    +-- Budget Reservation
    |
    +-- Model Resolution
    |
    +-- Candidate Filtering
    |
    +-- Routing Decision
    |
    +-- Provider Attempt #1
    |
    +-- Provider Attempt #2
    |
    +-- Usage Extraction
    |
    +-- Settlement Event
```

## 13.2 Metrics

Recommended metrics:

| Metric | Description |
|---|---|
| gateway_requests_total | Total logical requests |
| gateway_request_duration | Gateway processing duration |
| gateway_active_requests | Active requests |
| gateway_active_streams | Active streaming connections |
| provider_requests_total | Provider attempts |
| provider_latency | Provider response latency |
| provider_error_rate | Provider error rate |
| routing_fallback_total | Fallback count |
| routing_decision_duration | Routing computation time |
| input_tokens_total | Input token count |
| output_tokens_total | Output token count |
| usage_event_lag | Event processing lag |

Use bounded-cardinality labels.

Do not use Request ID, API Key ID or arbitrary user identifiers as Prometheus metric labels.

These identifiers belong in traces and structured logs.

## 13.3 Structured Logs

Example:

```json
{
  "timestamp": "2026-11-09T10:00:00Z",
  "level": "INFO",
  "request_id": "req_123",
  "trace_id": "trace_123",
  "organization_id": "org_123",
  "model": "claude-sonnet",
  "provider": "anthropic",
  "deployment": "anthropic-us",
  "attempt": 1,
  "status": "succeeded",
  "latency_ms": 1500
}
```

Never log:

- API Keys.
- Provider Secrets.
- Authorization Headers.
- Unredacted sensitive prompts.
- Unredacted sensitive responses.

---

# 14. Error Handling

## 14.1 Client-facing Errors

The Gateway should return a consistent error structure.

```json
{
  "error": {
    "message": "No available provider deployment",
    "type": "provider_unavailable",
    "code": "NO_AVAILABLE_DEPLOYMENT"
  }
}
```

Suggested error codes:

| Error | HTTP Status |
|---|---:|
| Invalid API Key | 401 |
| Permission Denied | 403 |
| Rate Limit Exceeded | 429 |
| Budget Exceeded | 402 or documented platform-specific error |
| Invalid Model | 400 |
| Model Unavailable | 503 |
| Provider Unavailable | 503 |
| Gateway Timeout | 504 |
| Internal Error | 500 |

Maintain a stable error contract across provider adapters.

Do not expose internal stack traces or provider secrets.

## 14.2 Failure Isolation

A single provider failure must not crash the Gateway.

Requirements:

- Per-provider timeout.
- Per-deployment circuit breaker.
- Bounded retry.
- Connection pool limits.
- Bulkhead isolation.
- Graceful degradation.

---

# 15. API Compatibility

## 15.1 MVP Endpoints

| Method | Endpoint | Priority |
|---|---|---|
| POST | /v1/chat/completions | P0 |
| GET | /v1/models | P0 |
| POST | /v1/embeddings | P1 |
| POST | /v1/messages | P1 |
| POST | /v1/responses | P2 |

## 15.2 Routing Extensions

Example:

```json
{
  "model": "claude-sonnet",
  "messages": [
    {
      "role": "user",
      "content": "Hello"
    }
  ],
  "stream": true,
  "routing": {
    "strategy": "lowest_cost",
    "allow_fallback": true
  }
}
```

Routing extensions must be optional.

Ordinary OpenAI-compatible requests must work without additional Gateway-specific fields.

## 15.3 Routing Configuration Precedence

Define a clear precedence model:

1. Organization-enforced security and compliance policies.
2. Organization routing policy.
3. API Key restrictions.
4. Explicit request-level routing preferences.
5. Platform defaults.

A lower-level preference cannot override a higher-level restriction.

---

# 16. Testing Strategy

## 16.1 Unit Tests

Test independently:

- Model Resolver.
- Capability Filter.
- Policy Filter.
- Health Filter.
- Routing Algorithms.
- Retry Decision Engine.
- Error Normalization.
- Usage Extraction.

Routing algorithms should be testable without network access.

## 16.2 Integration Tests

Test:

- API Key authentication with Redis.
- Organization authorization with PostgreSQL.
- Deployment lookup.
- Provider Adapter integration.
- Streaming translation.
- Budget reservation integration.
- Outbox publishing.

## 16.3 Failure Injection Tests

Simulate:

- Provider timeout.
- Provider 429.
- Provider 500.
- Provider authentication failure.
- Redis unavailable.
- PostgreSQL unavailable.
- Worker crash.
- Duplicate event delivery.
- Client disconnect.
- Partial streaming response.
- Ambiguous provider execution timeout.

## 16.4 Load Tests

Use k6 or Locust.

Initial targets:

| Metric | Target |
|---|---:|
| Gateway Internal P95 | < 100 ms |
| Gateway Internal P99 | < 200 ms |
| Concurrent Streaming | 1,000 |
| Request Throughput | 100–500 RPS |
| Routing Decision P95 | < 10 ms |

These are initial engineering targets, not performance guarantees.

Benchmark with realistic request sizes, connection durations and provider latency distributions.

---

# 17. MVP Implementation Plan

## Phase 1: Gateway Foundation

- FastAPI application.
- Request Context.
- Request ID / Trace ID.
- OpenAI-compatible endpoint.
- Unified Request / Response models.
- Async HTTP client management.

## Phase 2: Provider Integration

- Provider Adapter Protocol.
- OpenAI Adapter.
- DeepSeek Adapter.
- Anthropic Adapter.
- OpenAI-compatible Adapter.
- Streaming translation.

## Phase 3: Model and Deployment Registry

- Model Registry.
- Provider Registry.
- Deployment Registry.
- Capability metadata.
- Provider credentials.

## Phase 4: Routing Engine

- Candidate Generation.
- Capability Filtering.
- Policy Filtering.
- Health Filtering.
- Priority Routing.
- Lowest Cost Routing.
- Weighted Routing.

## Phase 5: Reliability

- Retry Manager.
- Circuit Breaker.
- Fallback.
- Timeout Management.
- Cancellation.
- Error Normalization.

## Phase 6: Observability and Usage Integration

- Request Logs.
- Attempt Logs.
- Routing Decision Logs.
- OpenTelemetry.
- Usage Events.
- Transactional Outbox.

---

# 18. Architecture Decisions

| ID | Decision | Rationale |
|---|---|---|
| ADR-001 | Modular Monolith | Reduce initial operational complexity |
| ADR-002 | Separate Data and Control Planes | Independent scaling and responsibilities |
| ADR-003 | Provider Adapter Pattern | Provider independence |
| ADR-004 | Pure Routing Decision Component | Testability and extensibility |
| ADR-005 | Policy Before Routing | Security and compliance |
| ADR-006 | Per-Deployment Circuit Breaker | Failure isolation |
| ADR-007 | Streaming as First-class Capability | Core LLM Gateway requirement |
| ADR-008 | Transactional Outbox | Reliable event publication |
| ADR-009 | At-least-once Event Delivery | Practical distributed processing |
| ADR-010 | Region-aware Deployment | China and global market support |

---

# 19. MVP Acceptance Criteria

The first implementation is considered complete when:

1. A client can call at least three different providers through one unified API.
2. Both streaming and non-streaming requests work.
3. API Key authentication and tenant authorization work.
4. Logical model identifiers resolve to multiple deployments.
5. Routing supports Priority and Lowest Cost.
6. Provider failures trigger bounded retry or fallback where safe.
7. Circuit Breakers isolate unhealthy deployments.
8. Every logical request has a stable Request ID.
9. Every provider execution has a distinct Attempt ID.
10. Routing decisions are recorded and explainable.
11. Client cancellation propagates upstream.
12. Usage data can be reliably delivered to the billing subsystem.
13. Duplicate event delivery does not produce duplicate financial effects.
14. Sensitive credentials and prompt content are not exposed in logs.
15. Region and compliance constraints cannot be overridden by routing preferences.

---

# 20. Future Extensions

After MVP validation:

- Latency-aware routing.
- Quality-aware routing.
- Adaptive routing based on historical performance.
- Semantic caching.
- Provider quota optimization.
- Multi-region routing.
- Advanced fallback policies.
- Automatic provider benchmarking.
- Model performance evaluation.
- AI-based routing recommendations.

These features must not compromise deterministic security and financial controls.

---

# Final Architecture Principle

The LLM Gateway should separate three fundamental responsibilities:

**Policy decides what is allowed.**

**Router decides where the request should go.**

**Execution Engine decides how the request is executed and recovered from failures.**

This separation is the foundation of an extensible, reliable and commercially viable AI Gateway platform.
