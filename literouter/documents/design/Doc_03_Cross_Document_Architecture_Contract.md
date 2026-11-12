# Cross-Document Architecture Contract

**Document:** 03 --- Cross-Document Architecture Contract\
**Version:** 1.0\
**Status:** Proposed\
**Scope:** Normative contract shared by Document 01 --- Request
Lifecycle & Intelligent Routing Design and Document 02 --- Billing &
Ledger Design\
**Actual path:** `documents/design/Doc_03_Cross_Document_Architecture_Contract.md`\
**Related documents:**\
- `Doc_01_Request_Lifecycle_Intelligent_Routin.md` --- Document 01\
- `Doc_02_Billing_Ledger_Design.md` --- Document 02

------------------------------------------------------------------------

## 1. Purpose

This document defines the shared domain, lifecycle, persistence, event,
idempotency, and financial invariants that Document 01 and Document 02
must implement consistently.

It does not replace either design document. It resolves their shared
boundaries and identifies decisions that must not be independently
redefined by the Request, Routing, Execution, Usage, or Billing modules.

If a local implementation detail conflicts with this document, the
shared contract takes precedence until an Architecture Decision Record
(ADR) explicitly changes it.

The key architectural principle is:

> One logical client Request may create multiple Provider Attempts and
> Usage observations, but it has at most one customer-billable Attempt,
> one Request-level Settlement, and one immutable financial outcome.

### 1.1 Normative language

-   **MUST / MUST NOT**: mandatory invariant.
-   **SHOULD / SHOULD NOT**: recommended default; deviations require a
    documented reason.
-   **MAY**: optional behavior.

### 1.2 Scope

This contract covers:

-   Canonical domain entities and their ownership.
-   Request, Attempt, Reservation, and Billing lifecycles.
-   Customer pricing versus provider cost.
-   Idempotency and retry safety.
-   Usage finalization and settlement eligibility.
-   Database transaction boundaries.
-   Transactional Outbox and event delivery.
-   Tenant and security boundaries relevant to shared data.
-   Production billing release criteria.

Payment processor integration, tax, invoicing, subscription billing,
multi-currency conversion, and detailed enterprise RBAC remain outside
this document.

------------------------------------------------------------------------

## 2. Canonical Domain Model

### 2.1 Entity relationship

The following cardinalities are the MVP contract:

``` text
Tenant
  |
  +-- Organization / Wallet
  |
  +-- API Keys / Teams
  |
  +-- Idempotency Scope
          |
          v
       1 Request
          |
          +---- 1 Reservation
          |
          +---- 1 Customer Pricing Snapshot
          |
          +---- 1..N Provider Attempts
          |          |
          |          +---- 0..N Usage Observations
          |          |
          |          +---- 0..N Provider Cost Records
          |          |
          |          +---- 0..1 Provider Cost Schedule Snapshot
          |
          +---- 0..1 Billable Attempt ID
          |
          +---- 1 Request Settlement
                     |
                     +---- 0..1 Customer Charge
                     |
                     +---- 0..N Ledger Transactions
```

The one Reservation and one Request Settlement rules apply to every
persisted logical Request that enters the billable execution workflow. A
rejected request that never reaches reservation has no Reservation or
Settlement.

A zero-charge Request still has a Request Settlement. It does not need a
positive Customer Charge or revenue ledger posting.

### 2.2 Canonical entity ownership

| Entity | Scope | Owner / source of truth | Meaning |
|---|---|---|---|
| Tenant | Customer security boundary | Identity / Control Plane | Boundary for customer data and API idempotency |
| Organization | Customer account | Identity / Control Plane | MVP wallet owner |
| API Key | Credential and access scope | Identity / Control Plane | Authenticates a client and resolves its tenant |
| Request | Logical client operation | Request domain | Stable identity across client redelivery and provider retries |
| Routing Decision | Request decision record | Routing domain | Explains candidate filtering and selected deployment |
| Attempt | One provider execution | Execution domain | Independent provider dispatch and outcome |
| Usage Observation | One immutable usage version | Metering domain | What was observed for one Attempt |
| Customer Pricing Snapshot | Request-level | Pricing / Billing | Immutable customer price policy for the logical Model |
| Provider Cost Snapshot | Attempt-level | Pricing / Billing | Immutable provider cost schedule for the selected Deployment |
| Provider Cost Record | Attempt-level | Billing | Calculated platform cost for a specific Attempt |
| Reservation | Request-level | Billing | Customer funds held before provider execution |
| Request Settlement | Request-level | Billing | Final customer financial disposition, including zero charge |
| Customer Charge | Request-level | Billing | Positive or zero calculated amount, if represented as a separate record |
| Ledger Transaction | Financial operation | Ledger | Immutable balanced financial posting |
| Outbox Event | Aggregate transition | Owning domain | Durable event publication intent |

### 2.3 Tenant and organization terminology

Document 01 uses `organization_id`, while both documents use `tenant_id`
for idempotency and tenant isolation. Document 02 recommends an
organization-level wallet.

For MVP, adopt the following mapping unless the product explicitly
supports a tenant containing multiple organizations:

-   `tenant_id` is the canonical security and uniqueness boundary.
-   `organization_id` identifies the billing account and wallet owner.
-   **Accepted decision (ADR-0301):** one Organization is one Tenant, so
    `tenant_id` and `organization_id` reference the same canonical
    organization identity.
-   `team_id` and `api_key_id` are subordinate scopes and MUST NOT
    create a separate financial wallet in MVP.
-   Client-supplied organization or tenant identifiers MUST NOT override
    the authenticated principal.

ADR-0301 scopes the one-to-one mapping to MVP. If the product later
introduces parent accounts containing multiple organizations, preserve
`tenant_id` as the isolation boundary and model the hierarchy
explicitly via a new ADR. Do not silently change the meaning of
existing IDs.

------------------------------------------------------------------------

## 3. Request and Attempt Contract

### 3.1 Request

A Request represents one logical API operation submitted by a client.

A Request MUST:

-   Have one globally unique and stable `request_id`.
-   Belong to exactly one authenticated tenant and organization.
-   Preserve the requested and resolved logical Model.
-   Preserve the applicable routing-policy version and customer pricing
    snapshot.
-   Have independent execution and billing states.
-   Have at most one `billable_attempt_id`.
-   Have at most one Reservation and one Request Settlement once it
    enters the reserved execution workflow.
-   Remain the parent of all Attempts created for its execution.

`PARTIALLY_COMPLETED` is a Request execution outcome. It is not an
Attempt status.

### 3.2 Attempt

An Attempt represents one actual or potentially actual provider
execution.

An Attempt MUST:

-   Have a unique `attempt_id` and parent `request_id`.
-   Be persisted before provider dispatch.
-   Record Provider, Deployment, provider model, and provider request
    reference where available.
-   Record transmission state separately from execution outcome.
-   Preserve usage and provider-cost references.
-   Never be treated as safely retryable solely because the Gateway
    timed out.

### 3.3 Separate Attempt dimensions

The documents currently use Attempt status, transmission state, and
outcome confidence, but do not define one complete canonical enum
contract. Adopt separate fields rather than combining all meanings into
one status.

**Attempt lifecycle status**

``` text
CREATED
DISPATCHING
RUNNING
SUCCEEDED
FAILED
CANCELLED
REJECTED_NO_EXECUTION
OUTCOME_UNKNOWN
FAILED_AFTER_EXECUTION_POSSIBLE
```

**Transmission state**

``` text
NOT_SENT
SEND_STARTED
SENT
PROVIDER_ACCEPTED
RESPONSE_RECEIVED
REJECTED_NO_EXECUTION
```

**Outcome confidence**

``` text
CONFIRMED
OUTCOME_UNKNOWN
RECONCILIATION_REQUIRED
```

The exact persistence representation may be refined, but the semantics
MUST remain separate:

-   `NOT_SENT` proves no provider execution was initiated.
-   `REJECTED_NO_EXECUTION` is terminal only when the Provider contract
    authoritatively confirms no execution.
-   `OUTCOME_UNKNOWN` and `FAILED_AFTER_EXECUTION_POSSIBLE` are
    nonterminal recovery conditions.
-   A client disconnect or Gateway timeout alone MUST NOT mark an
    Attempt terminal.
-   A provider response that proves execution completed or failed is
    terminal even if the provider generated billable usage.
-   An estimated Usage disposition does not make a nonterminal Attempt
    terminal.

An Attempt is eligible for final Request settlement only when its
provider execution outcome is terminal or authoritatively reconciled.

### 3.4 Request execution outcomes

The Request execution lifecycle remains authoritative in Document 01.

The canonical final outcomes are:

-   `SUCCEEDED`
-   `PARTIALLY_COMPLETED`
-   `FAILED`
-   `CANCELLED`
-   `REJECTED`

`OUTCOME_UNKNOWN` is a recoverable state, not a final business outcome.
It MUST resolve through provider recovery or reconciliation before the
Request can be financially finalized.

A Request with one or more unresolved Attempts MUST NOT be considered
fully execution-terminal for settlement or Reservation release.

### 3.5 Billable Attempt selection

For MVP:

1.  A Request has at most one `billable_attempt_id`.
2.  The billable Attempt is the single Attempt whose output became the
    client-visible result.
3.  For a stream that delivered partial content before failing, that
    Attempt may be billable and the Request outcome is
    `PARTIALLY_COMPLETED`.
4.  Attempts that failed or were superseded before producing the
    client-visible result remain recorded for provider-cost attribution
    but are not additionally charged to the customer.
5.  The billable Attempt's Usage must be `FINAL` or explicitly approved
    for estimated settlement.
6.  The billable Attempt selection MUST be persisted and auditable; it
    MUST NOT be independently inferred by each Usage consumer.
7.  Once a Request Settlement is committed, `billable_attempt_id` is
    immutable. Later corrections use a compensating financial
    adjustment.

A customer-initiated retry with a new Request or a new Idempotency-Key
is a new billable Request.

------------------------------------------------------------------------

## 4. Request Lifecycle and Billing Lifecycle

Execution and billing are independent state machines. Neither state may
be inferred from the other.

### 4.1 Request execution lifecycle

The execution pipeline is:

``` text
RECEIVED
  -> VALIDATING
  -> AUTHENTICATING
  -> AUTHORIZING
  -> RESOLVING_MODEL
  -> FILTERING
  -> ROUTING
  -> RESERVING_BUDGET
  -> EXECUTING
  -> SUCCEEDED | PARTIALLY_COMPLETED | FAILED | CANCELLED
```

`REJECTED` is used for validation, authentication, authorization, or
policy rejection before provider execution.

`OUTCOME_UNKNOWN` is a recoverable execution condition when provider
execution may have occurred but cannot yet be confirmed. It MUST NOT be
treated as `FAILED` merely to close the request.

### 4.2 Request billing lifecycle

The Request-level `billing_state` is:

``` text
NOT_RESERVED
    |
    v
RESERVED
    |
    v
SETTLEMENT_PENDING
    |                 \
    v                  v
SETTLED       RECONCILIATION_REQUIRED
                         |
                         v
                 SETTLEMENT_PENDING
```

The billing state is separate from `Reservation.status`.

### 4.3 Reservation lifecycle

Use the following canonical interpretation:

| Reservation status | Meaning | Request billing-state mapping |
|---|---|---|
| `PENDING` | Reservation command created but not committed | `NOT_RESERVED` |
| `RESERVED` | Funds successfully held | `RESERVED` |
| `SETTLEMENT_PENDING` | Settlement is being calculated or posted | `SETTLEMENT_PENDING` |
| `SETTLEMENT_FAILED` | A settlement attempt failed operationally; funds remain reserved | `SETTLEMENT_PENDING` or `RECONCILIATION_REQUIRED` |
| `SETTLED` | A positive or zero-amount settlement consumed the required reserved amount | `SETTLED` |
| `RELEASED` | Reservation released under a durable no-charge disposition | `SETTLED` |

`SETTLEMENT_FAILED` is not a financial terminal state.

`RELEASED` MUST NOT mean "the Gateway timed out" or "the reservation
expired." It is allowed only after all Attempts are terminal and a
durable no-charge Settlement is committed.

For a positive charge, the Reservation normally ends as `SETTLED`; any
unused amount is released in the same financial transaction.

### 4.4 Settlement eligibility

A Request may settle only when all of the following are true:

1.  Every Attempt is terminal or authoritatively reconciled.
2.  No provider execution remains potentially active.
3.  The designated billable Attempt, if any, has final Usage or an
    explicitly approved estimated-usage disposition.
4.  The immutable Customer Pricing Snapshot is available.
5.  The Reservation exists and is eligible for settlement.
6.  The Request's billable Attempt selection is stable.

If no Attempt is customer-billable, the system MUST persist an explicit
zero-charge disposition. Unknown usage MUST NOT be interpreted as zero
usage.

### 4.5 Reservation expiration

Reservation expiration is a recovery trigger, not permission to release
funds.

Before release, a worker MUST verify:

-   Request execution is terminal.
-   Every Attempt is terminal.
-   No unresolved provider execution or usage exposure remains.
-   No settlement is already committed.
-   The no-charge or settlement decision is durable and idempotent.

------------------------------------------------------------------------

## 5. Pricing, Usage, and Cost Contract

### 5.1 Customer Pricing Snapshot --- Request-level

Customer pricing is attached to the logical Model / customer Pricing
Policy.

At Request creation, persist an immutable snapshot containing at least:

-   Pricing plan and version.
-   Logical Model identifier and version where applicable.
-   Customer input, cached-input, output, and other modality prices.
-   Currency.
-   Billing units.
-   Rounding policy.
-   Applicable discounts, markups, or contractual rules.
-   Effective timestamp and snapshot identifier.

Fallback to another Provider Deployment MUST NOT change customer pricing
in MVP.

### 5.2 Provider Cost Snapshot --- Attempt-level

Provider cost depends on the selected Provider and Deployment.

Each Attempt that may incur provider cost MUST reference the applicable
immutable Provider Cost Schedule version. Its Provider Cost Record must
contain:

-   `request_id` and `attempt_id`.
-   Provider and Deployment identifiers.
-   Cost schedule identifier and version.
-   Currency.
-   Normalized usage reference(s).
-   Calculation details and calculated amount.
-   Cost status, including whether the amount is final, estimated,
    pending, or unavailable.

Do not treat a Request-level customer pricing snapshot as the
authoritative cost schedule for every Attempt.

### 5.3 Usage Observation

Usage observations are immutable and Attempt-scoped.

Enforce uniqueness on:

``` text
(attempt_id, observation_version)
```

A later provider correction or reconciliation result creates a new
observation version. It MUST NOT overwrite the original
provider-reported observation.

The normalized billable usage dimensions MUST be non-overlapping:

-   `uncached_input_tokens`
-   `cached_input_tokens`
-   `output_tokens`
-   separately priced modality units
-   reasoning tokens only under an explicit included / replacement /
    informational rule

Preserve raw provider usage and the normalization mapping version.
Invalid or ambiguous usage breakdowns are marked unknown or disputed;
they MUST NOT be silently summed.

### 5.4 Customer Charge

For MVP:

``` text
Customer Charge =
    Customer Pricing Snapshot
    × Usage of the designated billable Attempt
```

Failed or superseded Gateway retry/fallback Attempts contribute to
platform Provider Cost, not additional customer charges.

The Request Settlement records whether the charge is based on final or
approved estimated usage.

### 5.5 Provider Cost and Provider Payable

Provider Cost is an operational cost-attribution record per Attempt. It
is distinct from Customer Charge.

The current documents define a `Provider Payable` ledger account but do
not define when provider costs become payable or are posted to that
account.

**MVP contract:** Provider Cost Records are authoritative for cost
attribution and margin analytics. Do not automatically post Provider
Payable ledger entries merely because a Gateway Attempt completed.
Provider invoice reconciliation, payable recognition, and payment are
separate accounting workflows and require an explicit accounting ADR.

------------------------------------------------------------------------

## 6. Reservation and Settlement Transaction Contract

### 6.1 Reservation preconditions

Before the first provider dispatch:

1.  Authenticate and resolve the tenant.
2.  Validate the request and resolve the logical Model.
3.  Generate and filter the eligible Deployment candidate set using
    capability, authorization, compliance, region, and health
    constraints.
4.  Resolve the Customer Pricing Snapshot.
5.  Determine the maximum customer-billable exposure permitted by the
    request and fallback policy.
6.  Atomically reserve that exposure against the organization wallet.
7.  Persist the Request-to-Reservation relationship and corresponding
    ledger entries.
8.  Only after the reservation transaction commits may the Execution
    Engine dispatch a Provider Attempt.

The Router may rank candidates before reservation. No provider execution
may begin before a successful Reservation.

### 6.2 Fallback and reservation sufficiency

The eligible candidate set and the policy version used for the
reservation MUST be persisted.

Because customer pricing is stable across deployments for the same
logical Model in MVP, fallback does not independently change the
customer rate.

If a later execution path changes the maximum customer-billable
exposure, or introduces a chargeable capability not covered by the
original Reservation:

-   Atomically increase the Reservation before dispatching that path; or
-   Reject the path and return a documented platform error.

Never silently exceed the reserved exposure.

### 6.3 Reservation transaction

The Reservation transaction MUST atomically:

-   Lock or conditionally update the wallet.
-   Validate wallet status and currency.
-   Validate available balance and applicable budget limits.
-   Enforce one Reservation per Request.
-   Enforce Reservation operation idempotency.
-   Update wallet balance projections.
-   Create the Reservation.
-   Post balanced ledger entries.
-   Write the corresponding Outbox event.

Do not hold a database transaction open while waiting for a Provider.

### 6.4 Settlement transaction

The Request Settlement transaction MUST atomically:

1.  Verify all settlement eligibility conditions.
2.  Lock the Reservation and wallet in a consistent order.
3.  Verify the Customer Pricing Snapshot and billable Attempt selection.
4.  Calculate the final Customer Charge from the billable Attempt's
    Usage.
5.  Consume reserved funds.
6.  Release excess reserved funds.
7.  Apply the explicit over-reservation policy if the final charge
    exceeds the Reservation.
8.  Create balanced ledger entries.
9.  Update wallet projections.
10. Insert exactly one Request Settlement record.
11. Update Reservation and Request billing states.
12. Write the settlement Outbox event.

All financial effects above MUST commit or roll back together.

### 6.5 Over-reservation

MVP SHOULD reserve enough to cover the configured maximum charge so that
settlement does not exceed the Reservation.

If the actual charge nevertheless exceeds it, the system MUST follow one
explicit policy:

-   Atomically collect the difference from available balance, if
    permitted; or
-   Record a receivable / debt according to an approved policy and
    restrict further spending as configured.

**MVP default (aligned with Document 02 Section 7.5):** collect the
difference from available balance within the settlement transaction when
the balance is sufficient; otherwise record the difference as a
receivable / debt, restrict further spending as configured, and preserve
the full financial obligation.

Never discard actual usage or silently create an unrecorded negative
balance.

------------------------------------------------------------------------

## 7. Settlement, Charge, and Ledger Contract

### 7.1 Request Settlement is the canonical financial disposition

Document 02 describes one Request-level Settlement but its recommended
table list centers on `charges`.

To make the zero-charge requirement explicit, add a canonical
`request_settlements` record with:

-   `id`
-   `request_id` (unique)
-   `reservation_id` (unique)
-   `billable_attempt_id` (nullable)
-   `customer_pricing_snapshot_id`
-   `usage_observation_id` or approved usage-version reference (nullable
    for zero charge)
-   `charge_amount`
-   `currency`
-   `usage_disposition` (`FINAL`, `ESTIMATED_APPROVED`, `NO_CHARGE`)
-   `settlement_status`
-   `calculation_details`
-   `idempotency_key`
-   `created_at` / `settled_at`

A positive Customer Charge may be stored as a separate `charges` record
or as a one-to-one financial detail of the Settlement. If `charges`
remains separate, it MUST reference the Settlement and MUST be unique
per Request.

A zero-charge Settlement is a durable financial disposition; it MUST NOT
be represented as missing data.

### 7.2 Ledger invariants

Every posted Ledger Transaction MUST:

-   Balance debits and credits per currency.
-   Have a unique operation-scoped idempotency key.
-   Reference a durable business operation.
-   Be immutable after posting.
-   Be corrected only through compensating transactions.
-   Be committed atomically with its corresponding wallet projection and
    business-state update.

The wallet projection is a cache/materialized view. The ledger is the
financial source of truth.

### 7.3 Idempotency scopes

Keep the following scopes separate:

| Operation | Idempotency scope |
|---|---|
| Client Request | `(tenant_id, endpoint, idempotency_key)` |
| Reservation | One Reservation operation per `request_id`; enforce a unique Request relationship |
| Request Settlement | `settlement:{request_id}` and unique `request_id` |
| Ledger mutation | `(transaction_type, reference_type, reference_id, idempotency_key)` |
| Usage Observation | `(attempt_id, observation_version)` |
| Event consumption | `(consumer_name, event_id)` |

Database constraints MUST enforce these scopes. Application-level "check
then insert" logic alone is insufficient.

------------------------------------------------------------------------

## 8. Client Idempotency and Orchestration Order

### 8.1 Client Request Idempotency

For a supplied client key:

-   The key is unique within `(tenant_id, endpoint)`.
-   Persist the canonical payload hash and Request ID.
-   Same key + same payload resolves to the original Request.
-   Same key + different payload returns `409 Conflict`.
-   In-progress or uncertain Requests MUST NOT start a second execution.
-   Completed requests may replay the retained response or return a
    documented result reference.
-   The key-to-Request tombstone MUST outlive the maximum execution,
    retry, and recovery window and MUST NOT expire while execution or
    billing is unresolved.
-   Expiring replay content MUST NOT expire the idempotency tombstone or
    financial records.

If the client omits the key, every HTTP submission is a new logical
Request. The API documentation MUST state that no client-retry
deduplication guarantee exists in this case.

### 8.2 Recommended orchestration order

The conceptual code in Document 01 evaluates policy before
`resolve_or_create`, while its ingress description claims the
idempotency record after authentication. Adopt one explicit order:

``` text
HTTP ingress / basic parsing
        |
        v
Authenticate API Key
        |
        v
Resolve tenant and principal
        |
        v
Validate canonical request representation
        |
        v
Atomically claim or look up Idempotency-Key
        |
        +---- Existing Request
        |       |
        |       +--> Re-authorize access to replay/status data
        |       +--> Replay, return in-progress, or recover
        |       +--> Never create another execution
        |
        v
New logical Request
        |
        v
Authorization and policy evaluation
        |
        v
Model resolution and candidate filtering
        |
        v
Routing decision and pricing snapshot
        |
        v
Atomic Reservation
        |
        v
Persist Attempt before dispatch
        |
        v
Provider execution / streaming
        |
        v
Usage and Provider Cost observations
        |
        v
Request Settlement
```

Authentication and access authorization MUST be checked before
disclosing an existing Request's response or status. A revoked or
unauthorized credential MUST NOT gain access merely by knowing an
Idempotency-Key.

The current documents do not fully specify whether a policy change after
Request creation affects a replay. Recommended contract: current
authorization controls access to the replay, while execution policy and
pricing are the immutable decisions captured for the original Request. A
policy change MUST NOT silently cause a second execution or rewrite
historical pricing.

### 8.3 Provider retry safety

Retry or fallback is allowed only when:

-   The Attempt is proven `NOT_SENT`; or
-   The Provider authoritatively rejected it without execution; or
-   A stable provider idempotency mechanism or documented safe-replay
    guarantee applies.

When execution may have occurred and the outcome is unknown:

-   Do not create another Attempt by default.
-   Keep the original Request and Idempotency-Key bound to the
    unresolved operation.
-   Retain the Reservation.
-   Reconcile provider execution, usage, and cost.
-   Do not settle or release until the uncertainty is resolved.

------------------------------------------------------------------------

## 9. Streaming and Cancellation Contract

1.  Reserve before upstream execution.
2.  Persist the Attempt before dispatch.
3.  Forward chunks without buffering the entire response.
4.  Before the first irreversible downstream content, an eligible
    failure may use bounded retry/fallback.
5.  After content is delivered, do not transparently restart on another
    Provider or concatenate another generation.
6.  A provider failure after partial content produces a
    `PARTIALLY_COMPLETED` Request when applicable.
7.  A client disconnect triggers upstream cancellation and resource
    cleanup, but does not itself prove that provider execution stopped.
8.  Do not mark an Attempt terminal solely because the client
    disconnected or the Gateway task was cancelled.
9.  Persist final, estimated-approved, or unknown Usage observations
    with explicit provenance.
10. Settle only after every Attempt is terminal and the billable
    Attempt's Usage disposition is eligible.
11. If any provider outcome or usage exposure remains unresolved, retain
    the Reservation and enter reconciliation.

The Gateway MUST NOT write a database record for every token chunk.
Persist usage at bounded lifecycle boundaries.

------------------------------------------------------------------------

## 10. Event and Outbox Contract

### 10.1 Delivery guarantee

Use at-least-once event delivery. Do not claim exactly-once delivery
across PostgreSQL, Redis, and external systems.

The business requirement is exactly-once financial effect, achieved
through database constraints, idempotent consumers, and reconciliation.

### 10.2 Canonical event envelope

Every durable domain event SHOULD use a common envelope:

``` json
{
  "event_id": "evt_<unique_id>",
  "event_type": "billing.settlement.completed",
  "schema_version": 1,
  "occurred_at": "2026-11-10T00:00:00Z",
  "aggregate_type": "request",
  "aggregate_id": "req_<unique_id>",
  "aggregate_version": 12,
  "tenant_id": "org_<unique_id>",
  "request_id": "req_<unique_id>",
  "attempt_id": null,
  "correlation_id": "trace_or_workflow_id",
  "causation_id": "source_event_or_command_id",
  "idempotency_key": "settlement:req_<unique_id>",
  "data": {}
}
```

The example is illustrative. Do not put API keys, provider secrets, full
prompts, or full model responses in event payloads.

`event_id` is globally unique. `aggregate_version` is monotonically
increasing within the aggregate. Consumers MUST deduplicate by
`(consumer_name, event_id)` and SHOULD detect stale or out-of-order
aggregate versions.

### 10.3 Required event families

**Request / Execution**

``` text
request.created
request.routed
request.attempt.started
request.attempt.completed
request.attempt.failed
request.outcome.unknown
request.completed
request.failed
request.cancelled
```

**Usage / Cost**

``` text
usage.observation.recorded
usage.observation.finalized
provider_cost.recorded
provider_cost.reconciled
```

**Billing**

``` text
billing.reservation.created
billing.reservation.increased
billing.reservation.released
billing.settlement.requested
billing.settlement.completed
billing.settlement.failed
billing.reconciliation.required
```

Names may be adjusted, but semantics and identifiers MUST remain stable.

### 10.4 Transactional Outbox

When a business state transition and an event must be durable together,
write both in the same PostgreSQL transaction.

Examples:

-   Request / Attempt state transition + corresponding Request event.
-   Usage observation insert + usage event.
-   Reservation / ledger mutation + reservation event.
-   Settlement / ledger / wallet mutation + settlement event.

Outbox publishing is asynchronous. Failed publication is retried.
Consumers must be idempotent. Dead-letter handling and operator-visible
recovery are required before real-money release.

------------------------------------------------------------------------

## 11. Persistence and Database Constraints

The following constraints are the shared minimum. Exact table names may
differ.

| Invariant | Required database enforcement |
|---|---|
| Client idempotency | Unique `(tenant_id, endpoint, idempotency_key)` when key is present |
| One Reservation per Request | Unique `reservations.request_id` |
| One Request Settlement | Unique `request_settlements.request_id` |
| One billable Attempt | FK from Request to Attempt plus same-Request validation; enforce consistency transactionally |
| Attempt identity | Unique `attempt_id`; unique `(request_id, attempt_number)` |
| Usage versions | Unique `(attempt_id, observation_version)` |
| Provider Cost attribution | FK to Attempt and cost schedule version |
| Ledger operation | Unique operation-scoped idempotency key; required scope columns non-null |
| Event identity | Unique `event_id` |
| Consumer deduplication | Unique `(consumer_name, event_id)` |
| Currency integrity | One currency per ledger transaction |
| Ledger balance | Validate balanced posting in the posting transaction or a deferred database constraint/controlled posting procedure |

A composite foreign key or equivalent database constraint SHOULD ensure
that `Request.billable_attempt_id` references an Attempt belonging to
that same Request.

Wallet projections, Request usage summaries, Request customer-cost
summaries, and Attempt provider-cost fields are derived projections.
They MUST NOT become independent sources of truth.

------------------------------------------------------------------------

## 12. Security and Tenant Contract

Detailed Authentication and Authorization design belongs in the planned
Document 05 --- Tenant & Security Design. The following minimum rules
are nevertheless shared architecture invariants:

-   Resolve tenant identity from authenticated credentials, never from
    client-supplied organization IDs.
-   Enforce tenant scope on every Request, Attempt, Usage, Reservation,
    Settlement, Wallet, and Ledger query.
-   API Key authentication MUST fail closed when validity cannot be
    established.
-   API Key revocation, expiration, permission changes, and organization
    suspension require cache invalidation or bounded cache freshness.
-   Provider credentials are stored encrypted, accessed through secure
    references, scoped by Provider and Region, and rotated without
    exposing secret material.
-   Do not log API keys, authorization headers, provider secrets, or
    unredacted sensitive prompts/responses.
-   Customer and administrative billing permissions remain separate.
-   Refund, adjustment, pricing, wallet, and ledger-export operations
    require explicit authorization and audit records.
-   Region, residency, ZDR, and contractual restrictions are enforced
    before routing preferences and cost ranking.

Document 05 must define the full principal model, role/permission
matrix, API Key lifecycle, admin authorization, audit schema, secret
management, and abuse controls before production security approval.

------------------------------------------------------------------------

## 13. Error and Recovery Contract

The following conditions MUST have explicit, observable handling:

| Condition | Required behavior |
|---|---|
| PostgreSQL unavailable before reservation | Do not execute a billable request |
| Reservation fails | Do not dispatch an Attempt |
| Provider outcome unknown | Keep Request bound to original Attempt; retain Reservation; reconcile |
| Usage missing or disputed | Do not treat as zero; retain Reservation if exposure remains unresolved |
| Worker crashes before settlement commit | Retry settlement |
| Worker crashes after settlement commit | Return existing Settlement on retry |
| Duplicate event | Consumer deduplicates; no duplicate financial effect |
| Outbox publication failure | Retry from durable Outbox |
| Reservation appears expired while Request is active | Do not release |
| Wallet projection mismatch | Rebuild or reconcile from Ledger |
| Provider reports corrected Usage | Append observation version and create financial adjustment if needed |
| Client disconnect during stream | Cancel upstream; determine actual Attempt outcome; retain funds until safe settlement |

Every recovery action MUST be idempotent, auditable, and observable.

------------------------------------------------------------------------

## 14. Production Billing Release Gate

Document 01 and Document 02 both prohibit real-money traffic before
Phase 5 approval. This shared gate is authoritative.

Real-money traffic MUST remain disabled until all criteria pass:

### 14.1 Domain and lifecycle

-   One Request can have multiple Attempts and immutable Usage
    observations.
-   Request execution and billing states are independent.
-   Attempt terminality and uncertain outcomes are tested.
-   At most one billable Attempt is selected and validated.
-   One Request has at most one Reservation and exactly one Request
    Settlement after entering the reserved execution workflow.
-   Zero-charge Settlement is durable and distinguishable from unknown
    Usage.

### 14.2 Financial correctness

-   Customer Pricing Snapshot is immutable and Request-scoped.
-   Provider Cost Schedule Snapshot is immutable and Attempt-scoped.
-   Cached/input/output/reasoning and modality usage buckets are
    non-overlapping.
-   Reservation is atomic and concurrent requests cannot overspend.
-   Settlement is atomic and idempotent.
-   Ledger transactions balance and are immutable.
-   Wallet projections can be rebuilt from the ledger.
-   Refunds and adjustments, if enabled, use compensating transactions
    and audit trails.

### 14.3 Reliability and recovery

-   Duplicate client requests cannot create duplicate execution or
    charges.
-   Ambiguous Provider timeouts do not trigger unsafe retries.
-   Client disconnect does not prematurely release funds.
-   Worker crash before/after commit is tested.
-   Duplicate and out-of-order event delivery is tested.
-   Outbox recovery and dead-letter operations are tested.
-   Reconciliation can recover unresolved Attempts, Usage, Reservations,
    and Settlements.

### 14.4 Security and operations

-   Tenant isolation tests pass across all customer-owned entities.
-   API Key revocation and authorization behavior are tested.
-   Secrets and sensitive prompts are absent from logs and event
    payloads.
-   Region and compliance policies cannot be overridden by routing
    preferences.
-   Load, streaming concurrency, and latency targets are measured.
-   Alerts exist for stuck Reservations, unresolved Attempts, settlement
    lag/failure, outbox lag, and ledger/projection mismatches.
-   An explicit release approval is recorded.

Passing unit tests alone is not sufficient. The gate requires end-to-end
PostgreSQL integration, concurrency tests, failure injection,
reconciliation tests, and security review.

------------------------------------------------------------------------

## 15. Required Updates to Document 01 and Document 02

Before implementation, update the companion documents to reference this
contract and remove duplicated or divergent definitions.

**Status:** the updates listed in this section have been applied to the
current revisions of Document 01 and Document 02. Retain this list as
the change record; any future divergence must be reconciled against it.

### 15.1 Document 01 updates

1.  Reference this document as the authority for shared Request /
    Attempt / Billing semantics.
2.  Replace the current conceptual Attempt status ambiguity with the
    separate lifecycle, transmission, and outcome-confidence dimensions
    in Section 3.3.
3.  Align the RequestService pseudocode with the idempotency order in
    Section 8.2.
4.  Persist the frozen eligible candidate set and policy version used
    for Reservation.
5.  Clarify that the selected billable Attempt is immutable after
    Settlement.
6.  Align Request and Reservation state mapping with Section 4.
7.  Use the shared event envelope and event idempotency rules.
8.  Ensure Request projections are derived from Usage observations and
    Request Settlement.

### 15.2 Document 02 updates

1.  Add `request_settlements` or explicitly define an equivalent
    canonical Settlement entity.
2.  Clarify the relationship between Settlement and Charge, including
    zero-charge Settlement.
3.  Separate Request-level Customer Pricing Snapshot from Attempt-level
    Provider Cost Schedule Snapshot.
4.  Make one Reservation per Request a database-enforced invariant, not
    merely one active Reservation.
5.  Align Reservation state mapping with Section 4.3.
6.  Define Provider Cost Records as operational cost attribution; defer
    Provider Payable posting until an accounting ADR exists.
7.  Adopt the shared Outbox event envelope and consumer deduplication
    contract.
8.  Ensure the Settlement transaction updates Reservation, wallet
    projection, ledger, Request billing state, Settlement record, and
    Outbox atomically.

### 15.3 Shared wording

Both documents should contain the same short cross-document statement:

> Document 01 defines Request execution, routing, and Provider Attempt
> behavior. Document 02 defines Usage, Reservation, Request Settlement,
> and Ledger behavior. Document 03 defines the shared contract. Request
> execution and billing are independent lifecycles; Usage and Provider
> Cost are Attempt-scoped; Customer Charge and Settlement are
> Request-scoped. Real-money traffic is prohibited until the shared
> Billing Release Gate passes.

------------------------------------------------------------------------

## 16. Architecture Decisions

The following decisions govern the shared contract. Accepted decisions
are binding on Documents 01 and 02; changes require a new ADR.

| ID | Decision / question | Decision detail | Priority | Status |
|---|---|---|---|---|
| ADR-0301 | Tenant vs Organization | One Organization equals one Tenant in MVP; keep IDs conceptually distinct | P0 | Accepted |
| ADR-0302 | Settlement persistence | Add canonical `request_settlements`; Charge is a result/detail, not a substitute for zero-charge disposition | P0 | Accepted |
| ADR-0303 | Attempt status dimensions | Separate lifecycle status, transmission state, and outcome confidence | P0 | Accepted |
| ADR-0304 | Customer vs provider pricing snapshots | Customer snapshot per Request; provider cost schedule snapshot per Attempt | P0 | Accepted |
| ADR-0305 | Idempotency order | Authenticate, resolve tenant, canonicalize, claim/lookup key, then authorize replay or process new Request | P0 | Accepted |
| ADR-0306 | Provider payable recognition | Keep Provider Cost operational in MVP; define payable posting in a separate accounting ADR | P1 | Open |
| ADR-0307 | Reservation count | Enforce exactly one Reservation per reserved Request; do not permit a second Reservation after release | P0 | Accepted |
| ADR-0308 | Event envelope | Standardize event ID, schema version, aggregate version, tenant/request/attempt IDs, causation and correlation IDs | P1 | Open |
| ADR-0309 | Policy changes and replay | Current authorization controls access to replay; original execution and pricing decisions remain immutable | P1 | Open |
| ADR-0310 | Over-reservation default policy | Collect the difference from available balance when sufficient; otherwise record a receivable and restrict spending | P1 | Open |

A P0 item blocks implementation of the affected contract until accepted.
All six P0 decisions are now Accepted (2026-11-11), so no architectural
blocker remains for implementation.

A P1 item remains open but has a documented default; during
implementation, follow the default behavior in this document unless a
new ADR supersedes it.

------------------------------------------------------------------------

## 17. Final Architecture Principle

The system has four independent but coordinated responsibilities:

-   **Identity and Policy** decide who may perform an operation and what
    constraints apply.
-   **Router** decides which eligible Deployment should be attempted.
-   **Execution Engine** performs and recovers Provider Attempts without
    unsafe replay.
-   **Billing** reserves funds, records Usage and Provider Cost, settles
    the Request, and preserves immutable financial history.

The central invariant is:

> A Request may have many Provider Attempts, but it must never create
> more than one customer financial settlement. Unknown provider
> execution is neither a successful retry opportunity nor a zero-cost
> outcome.

This contract is the shared foundation for implementing Documents 01 and
02 and for the subsequent Document 05 --- Tenant & Security Design.
