# Billing & Ledger Design

**Document:** 02 — Billing & Ledger Design  
**Version:** 1.0  
**Status:** Proposed  
**Related document:** Request Lifecycle & Intelligent Routing Design  
**Suggested path:** `docs/architecture/billing-and-ledger.md`

---

## 1. Overview

### 1.1 Purpose

This document defines the billing, usage metering, budget reservation, settlement, and financial ledger architecture for the LLM Gateway platform.

The billing subsystem must support:

- Pay-as-you-go usage billing.
- Prepaid wallet balances.
- Organization and API-key spending limits.
- Per-model and per-provider pricing.
- Input/output token pricing.
- Cached token and reasoning token pricing.
- Image, audio, embedding, and other modalities.
- Streaming and non-streaming requests.
- Multiple providers and deployment types.
- Customer pricing and provider cost tracking.
- Refunds, adjustments, and reconciliation.
- Multi-currency support in future phases.

### 1.2 Design Principles

The billing system follows these principles:

1. **Financial correctness over convenience.** A request must not create duplicate charges, even if events are delivered multiple times.
2. **Reserve before execution.** Verify available budget and reserve a conservative amount before sending a request upstream.
3. **Settle against actual usage.** Final charges are calculated from normalized usage and the applicable pricing snapshot.
4. **Immutable financial history.** Ledger entries are append-only. Corrections use compensating entries, never destructive updates.
5. **Idempotent operations.** Repeated reservation, settlement, refund, and adjustment commands must not produce duplicate financial effects.
6. **Pricing versioning.** Every request records the exact pricing version used for its calculation.
7. **Separate customer billing from provider cost.** Customer revenue and provider expenses are different financial dimensions.
8. **Asynchronous reliability.** Usage processing and settlement can be asynchronous, but failures must be recoverable.
9. **Auditable calculations.** Every charge must be explainable from its usage, pricing snapshot, and calculation details.

### 1.3 Non-goals

This document does not fully specify:

- Payment processor integration.
- Tax calculation and tax reporting.
- Invoicing and accounting exports.
- Subscription plans and recurring payments.
- Full enterprise contract billing.
- Currency conversion and FX settlement.

These can be added without changing the core reservation and ledger model.

---

## 2. Architecture

### 2.1 Logical Components

The billing subsystem belongs to the Control Plane logically, but parts of it participate directly in the Data Plane request lifecycle.

```text
                   Data Plane
                       |
                       v
                Request Orchestrator
                       |
          +------------+-------------+
          |            |             |
          v            v             v
      Identity       Router       Provider
          |            |             |
          +------------+-------------+
                       |
                       v
                 Billing Service
                       |
          +------------+-------------+
          |            |             |
          v            v             v
      Pricing      Reservation    Usage Metering
          |            |             |
          +------------+-------------+
                       |
                       v
                 Settlement Engine
                       |
                       v
                  Ledger Engine
                       |
                       v
                  PostgreSQL
                       |
                 Transactional
                     Outbox
                       |
                       v
                  Worker Queue
                       |
          +------------+-------------+
          |            |             |
          v            v             v
     Reconciliation  Analytics    Notifications
```

### 2.2 Component Responsibilities

| Component | Responsibility |
|---|---|
| Pricing Service | Resolve customer price and provider cost |
| Reservation Service | Reserve available balance or budget |
| Usage Metering | Normalize and persist usage records |
| Settlement Engine | Calculate final charge and release excess reservation |
| Ledger Engine | Record immutable financial transactions |
| Wallet Service | Maintain customer balance projections |
| Reconciliation Worker | Detect and resolve inconsistent or missing usage |
| Billing API | Expose balances, transactions, usage, and limits |
| Analytics Pipeline | Produce usage and financial reporting |

### 2.3 Architectural Boundary

The Request Orchestrator should not directly modify wallet balances or create ledger entries.

It should call explicit billing operations:

```python
reservation = await billing_service.reserve(
    request_context=request_context,
    estimated_cost=estimated_cost,
)

result = await execution_engine.execute(request_context)

await billing_service.record_usage(result.usage)

await billing_service.settle(
    reservation_id=reservation.id,
    usage_id=result.usage.id,
)
```

The code is conceptual. The actual implementation must coordinate persistence, transactions, idempotency, and failure recovery.

---

## 3. Core Domain Model

The billing domain should not be represented by a single `Transaction` table.

The following entities have different lifecycles and responsibilities.

### 3.1 Wallet

Represents a customer's prepaid balance.

Typical ownership:

- User wallet.
- Organization wallet.
- Enterprise account wallet.

Recommended MVP approach: one organization-level wallet, with users and API keys consuming the organization's budget.

Fields:

| Field | Type | Description |
|---|---|---|
| id | UUID | Wallet identifier |
| organization_id | UUID | Owning organization |
| currency | VARCHAR(3) | Wallet currency |
| status | VARCHAR | ACTIVE / FROZEN / CLOSED |
| available_balance | BIGINT | Cached available balance |
| reserved_balance | BIGINT | Cached reserved balance |
| version | BIGINT | Optimistic concurrency version |
| created_at | TIMESTAMP | Creation time |
| updated_at | TIMESTAMP | Last update |

**Important:** Balances are stored as integer minor units, not floating-point numbers.

For a USD wallet:

- `$1.00` = `100` cents.
- `$0.01` = `1` cent.

For internal token pricing calculations, higher precision is needed. The pricing and usage calculation layer should use fixed-point decimal arithmetic, then round according to an explicitly defined currency rounding policy.

The wallet balance fields are projections. The ledger is the financial source of truth.

### 3.2 Reservation

Represents money reserved before executing an LLM request.

| Field | Type | Description |
|---|---|---|
| id | UUID | Reservation identifier |
| organization_id | UUID | Organization |
| wallet_id | UUID | Wallet |
| request_id | UUID | Gateway request |
| idempotency_key | VARCHAR | Unique reservation key |
| reserved_amount | BIGINT | Original reserved amount |
| settled_amount | BIGINT | Final customer charge |
| released_amount | BIGINT | Released amount |
| currency | VARCHAR(3) | Currency |
| status | VARCHAR | Reservation state |
| expires_at | TIMESTAMP | Expiration time |
| created_at | TIMESTAMP | Creation time |
| settled_at | TIMESTAMP | Settlement time |

Recommended reservation states:

```text
PENDING
  |
  v
RESERVED
  |
  +----------> RELEASED
  |
  v
SETTLEMENT_PENDING
  |
  +----------> SETTLED
  |
  +----------> SETTLEMENT_FAILED
```

`SETTLEMENT_FAILED` is an operational state requiring retry or reconciliation. It must not imply that the original reservation has disappeared.

A reservation must be associated with exactly one request.

For the MVP, use one reservation per billable request. If a request later supports multiple separately billable execution stages, model those as explicit reservation allocations rather than silently reusing the same reservation.

### 3.3 Usage Record

Represents normalized usage reported or estimated for a model execution.

| Field | Type | Description |
|---|---|---|
| id | UUID | Usage identifier |
| request_id | UUID | Gateway request |
| attempt_id | UUID | Provider attempt |
| organization_id | UUID | Customer organization |
| deployment_id | UUID | Selected deployment |
| provider | VARCHAR | Provider name |
| model | VARCHAR | Model identifier |
| input_tokens | BIGINT | Input tokens |
| output_tokens | BIGINT | Output tokens |
| cached_input_tokens | BIGINT | Cached input tokens |
| reasoning_tokens | BIGINT | Reasoning tokens |
| image_units | BIGINT | Image usage units |
| audio_input_units | BIGINT | Audio input units |
| audio_output_units | BIGINT | Audio output units |
| usage_source | VARCHAR | Usage source |
| usage_status | VARCHAR | Confidence / reconciliation state |
| raw_usage | JSONB | Original provider usage payload |
| normalized_usage | JSONB | Normalized usage details |
| created_at | TIMESTAMP | Creation time |

Usage source:

- `PROVIDER_REPORTED`
- `GATEWAY_ESTIMATED`
- `PROVIDER_RECONCILED`
- `UNKNOWN`

Usage status:

- `PROVISIONAL`
- `FINAL`
- `ESTIMATED`
- `DISPUTED`

Do not overwrite the original provider-reported usage when a later reconciliation produces a different value. Preserve the original observation and record a correction or a new version.

A useful distinction:

- Usage is an observation of consumption.
- Charge is a financial calculation based on usage and pricing.

They should never be treated as the same record.

### 3.4 Pricing Version

Pricing must be versioned.

A price change should affect new requests only. Historical requests must retain the original price snapshot.

Suggested model:

**PricingPlan**

| Field | Type | Description |
|---|---|---|
| id | UUID | Pricing plan |
| name | VARCHAR | Plan name |
| currency | VARCHAR(3) | Currency |
| status | VARCHAR | ACTIVE / INACTIVE |
| created_at | TIMESTAMP | Creation time |

**ModelPrice**

| Field | Type | Description |
|---|---|---|
| id | UUID | Price record |
| pricing_plan_id | UUID | Pricing plan |
| model_id | UUID | Model |
| input_price | NUMERIC | Input price per million tokens |
| output_price | NUMERIC | Output price per million tokens |
| cached_input_price | NUMERIC | Cached input price |
| reasoning_price | NUMERIC | Reasoning price, if separately billed |
| effective_from | TIMESTAMP | Start time |
| effective_until | TIMESTAMP | End time |
| version | INTEGER | Version |
| created_at | TIMESTAMP | Creation time |

For providers, maintain a separate provider cost schedule.

Customer price and provider cost must not share one pricing record.

A request should store a complete pricing snapshot, including:

- Pricing plan and version.
- Customer model price.
- Provider deployment cost schedule.
- Currency.
- Billing unit.
- Effective timestamp.
- Rounding policy.
- Any applicable markup or discount.

This ensures a future price update cannot change an already-created charge.

### 3.5 Ledger Entry

The ledger is the authoritative financial record.

Each financial transaction should be represented by balanced debit and credit entries.

| Field | Type | Description |
|---|---|---|
| id | UUID | Ledger entry identifier |
| transaction_id | UUID | Parent ledger transaction |
| account_id | UUID | Financial account |
| direction | VARCHAR | DEBIT / CREDIT |
| amount | BIGINT | Amount in minor units |
| currency | VARCHAR(3) | Currency |
| reference_type | VARCHAR | Reservation / Usage / Refund / Adjustment |
| reference_id | UUID | Related entity |
| created_at | TIMESTAMP | Creation time |

Use a parent `LedgerTransaction`:

| Field | Type | Description |
|---|---|---|
| id | UUID | Transaction identifier |
| idempotency_key | VARCHAR | Unique operation key |
| transaction_type | VARCHAR | Transaction type |
| reference_type | VARCHAR | Business reference |
| reference_id | UUID | Business reference ID |
| description | TEXT | Explanation |
| created_at | TIMESTAMP | Creation time |

A ledger transaction must balance:

```text
SUM(DEBIT amounts) = SUM(CREDIT amounts)
```

for each currency.

Never update or delete posted ledger entries. Use a compensating transaction for corrections.

---

## 4. Money Representation and Precision

### 4.1 Avoid Floating-Point Arithmetic

Never calculate financial charges using Python `float`.

Use `Decimal` or an equivalent fixed-point representation.

Example:

```python
from decimal import Decimal, ROUND_HALF_UP

input_price_per_million = Decimal("2.50")
input_tokens = 1_250_000

raw_charge = (
    Decimal(input_tokens)
    * input_price_per_million
    / Decimal("1000000")
)

rounded_charge = raw_charge.quantize(
    Decimal("0.01"),
    rounding=ROUND_HALF_UP,
)
```

Result:

```text
$3.13
```

The rounding policy must be explicit and consistent.

### 4.2 Internal Precision

Do not round every token component independently unless the pricing contract explicitly requires it.

A recommended process:

1. Calculate each usage component using high-precision decimal arithmetic.
2. Sum all components.
3. Apply discounts and markups according to the pricing contract.
4. Apply the defined rounding policy.
5. Convert the final amount into the wallet's minor units.
6. Persist both the calculation details and final charge.

For currencies with different minor-unit precision, use currency metadata rather than assuming two decimal places.

---

## 5. Pricing and Charge Calculation

### 5.1 Customer Charge

A typical token-based customer charge:

\[
C = \frac{T_{in}P_{in}}{10^6}
+ \frac{T_{out}P_{out}}{10^6}
+ \frac{T_{cached}P_{cached}}{10^6}
\]

Where:

- \(T_{in}\): billable input tokens.
- \(T_{out}\): billable output tokens.
- \(T_{cached}\): cached input tokens.
- \(P_{in}\): input price per million tokens.
- \(P_{out}\): output price per million tokens.
- \(P_{cached}\): cached input price per million tokens.

This is a simplified formula. Actual pricing can include:

- Reasoning tokens.
- Image processing.
- Audio input/output.
- Video frames.
- Tool execution.
- Provider-specific surcharges.
- Per-request fees.
- Discounts.
- Contractual minimum charges.

### 5.2 Avoid Double-Counting Tokens

Provider usage formats are not always identical.

For example, some providers report cached input tokens as a subset of input tokens. Others report them as separate details.

The normalization layer must define whether each usage field is:

- A subset of another field.
- An independent billable component.
- Informational only.

Do not blindly sum every provider-reported field.

Each provider adapter should translate provider-specific usage into a documented normalized representation.

### 5.3 Customer Revenue vs Provider Cost

Maintain two independent calculations.

**Customer charge:**

```text
Customer Charge =
    Customer Pricing × Actual Usage
```

**Provider cost:**

```text
Provider Cost =
    Provider Pricing × Actual Usage
```

**Gross margin:**

```text
Gross Margin = Customer Charge - Provider Cost
```

Provider cost may be zero or unavailable for self-hosted deployments until infrastructure cost allocation is implemented.

Do not assume gross margin equals net profit. It excludes infrastructure, payment processing, support, taxes, and other operational expenses.

### 5.4 Pricing Snapshot

Each billable request must preserve its resolved pricing snapshot.

Example:

```json
{
  "pricing_plan_id": "plan_123",
  "pricing_version": 7,
  "currency": "USD",
  "model": "example-model",
  "customer_price": {
    "input_per_million": "2.50",
    "output_per_million": "10.00"
  },
  "provider_cost": {
    "input_per_million": "1.80",
    "output_per_million": "8.00"
  },
  "rounding_policy": "HALF_UP",
  "resolved_at": "2026-11-09T10:00:00Z"
}
```

The values above are illustrative.

Persist the snapshot with the request's billing context. Do not resolve historical charges by querying the current pricing table.

---

## 6. Budget Reservation

### 6.1 Why Reservation Is Required

Consider this situation:

- Organization available balance: `$100`.
- Ten concurrent requests.
- Each request is estimated to cost `$20`.

If each request independently checks the balance before executing, all ten may see `$100` and proceed.

The organization could consume `$200`, despite having only `$100`.

Reservation prevents this overspending race.

### 6.2 Reservation Amount

The reservation should conservatively estimate the maximum expected customer charge.

For a token-based chat request:

```text
Estimated Reservation =
    Estimated Input Charge
    + Maximum Output Charge
    + Other Expected Charges
```

The estimate should account for:

- Input tokens.
- Maximum output tokens.
- Model-specific pricing.
- Cached input pricing where applicable.
- Reasoning tokens if separately billable.
- Image/audio modalities.
- Tool usage where billable.
- Discounts and pricing rules.
- Currency rounding.

For models with uncertain modality costs, use a conservative estimate or require a separate usage budget.

If the request does not specify a maximum output token limit, the gateway should apply a configured default or maximum. An unlimited reservation is not acceptable.

### 6.3 Reservation Algorithm

Reservation must be atomic.

A conceptual transaction:

```sql
BEGIN;

SELECT *
FROM wallets
WHERE id = :wallet_id
FOR UPDATE;

-- Check wallet status and available balance.

-- Reject if available balance < reservation amount.

UPDATE wallets
SET
    available_balance = available_balance - :amount,
    reserved_balance = reserved_balance + :amount,
    version = version + 1
WHERE id = :wallet_id;

INSERT INTO reservations (
    id,
    wallet_id,
    request_id,
    idempotency_key,
    reserved_amount,
    settled_amount,
    released_amount,
    currency,
    status,
    expires_at
)
VALUES (
    :reservation_id,
    :wallet_id,
    :request_id,
    :idempotency_key,
    :amount,
    0,
    0,
    :currency,
    'RESERVED',
    :expires_at
);

COMMIT;
```

The implementation must also:

- Enforce a unique idempotency key.
- Verify the wallet currency.
- Check wallet status.
- Validate the reservation amount.
- Ensure a request cannot create multiple active reservations accidentally.
- Write the corresponding ledger transaction in the same database transaction.

The wallet row lock serializes reservations for the same wallet. If throughput later becomes a bottleneck, optimize using carefully designed atomic balance updates and optimistic concurrency without weakening financial invariants.

### 6.4 Reservation Expiration

Reservations should have an expiration time to prevent abandoned reservations from locking funds forever.

However, expiration must not release funds while the provider request may still be running.

A safe expiration process:

1. Find expired reservations.
2. Verify the associated request's execution state.
3. Confirm the request has finished, failed, or been safely cancelled.
4. Confirm there is no unresolved provider attempt.
5. Release the reservation if settlement is not required.
6. Otherwise mark it for reconciliation.

Expiration is a recovery mechanism, not permission to release funds blindly.

---

## 7. Ledger Accounting Model

### 7.1 Account Types

The ledger should support at least these account types:

| Account | Purpose |
|---|---|
| Customer Wallet Liability | Customer's stored balance |
| Reserved Funds Liability | Funds reserved for pending usage |
| Platform Revenue | Customer charges recognized by the platform |
| Provider Payable | Amount owed to model providers |
| Payment Clearing | Funds received through payment processors |
| Refund Payable | Refunds awaiting payment |
| Adjustment Account | Explicit financial corrections |

The exact accounting treatment may vary with the platform's legal and accounting structure. These are operational ledger accounts, not a substitute for a qualified accounting policy.

### 7.2 Example: Deposit $100

A customer purchases `$100` of wallet credit.

```text
DEBIT   Payment Clearing          $100
CREDIT  Customer Wallet Liability $100
```

### 7.3 Example: Reserve $20

```text
DEBIT   Customer Wallet Liability $20
CREDIT  Reserved Funds Liability  $20
```

This moves the amount from available balance to reserved balance without recognizing revenue.

### 7.4 Example: Final Charge $12

After actual usage is calculated:

```text
DEBIT   Reserved Funds Liability  $12
CREDIT  Platform Revenue          $12
```

Release the remaining `$8`:

```text
DEBIT   Reserved Funds Liability  $8
CREDIT  Customer Wallet Liability $8
```

The result:

- Customer available balance: `$88`.
- Reserved balance: `$0`.
- Platform revenue: `$12`.

### 7.5 Example: Final Charge Exceeds Reservation

Suppose:

- Reserved: `$20`.
- Actual charge: `$25`.

The additional `$5` cannot be silently charged if the customer has insufficient available balance.

Define a policy:

1. If available balance is sufficient, debit the additional amount atomically.
2. If insufficient, record the outstanding amount as a receivable or debt according to platform policy.
3. Apply account restrictions if necessary.
4. Preserve the full usage and financial obligation.
5. Do not discard actual provider usage merely because the customer has insufficient funds.

For the MVP, a simpler and safer approach is to reserve enough to cover the configured maximum charge. Requests that cannot be conservatively reserved should be rejected before provider execution.

### 7.6 Ledger Invariants

The following invariants are mandatory:

- Every posted ledger transaction balances.
- Every transaction has a unique idempotency key within its relevant scope.
- Posted ledger entries are immutable.
- Every settlement references an existing reservation.
- A reservation cannot be settled more than once.
- A refund cannot exceed the refundable amount.
- Wallet projections must be reconcilable to ledger balances.
- Currency cannot be mixed inside a transaction.
- Every financial adjustment has an explicit reason and audit reference.

---

## 8. Settlement

### 8.1 Settlement Flow

Settlement converts a reservation into a final customer charge.

```text
Provider Execution Completed
           |
           v
      Usage Received
           |
           v
    Usage Normalization
           |
           v
   Pricing Snapshot Lookup
           |
           v
     Charge Calculation
           |
           v
   Settlement Transaction
           |
      +----+----+
      |         |
      v         v
   Charge     Release
   Reserved   Excess
   Funds      Reservation
      |         |
      +----+----+
           |
           v
     Settlement Complete
```

### 8.2 Settlement Formula

Let:

- \(R\): reserved amount.
- \(C\): final customer charge.

Then:

\[
\text{Release} = \max(R-C, 0)
\]

\[
\text{Additional Charge} = \max(C-R, 0)
\]

The settlement transaction must atomically:

1. Verify the reservation is eligible for settlement.
2. Verify the usage record.
3. Verify the pricing snapshot.
4. Calculate the final charge.
5. Consume the reserved amount.
6. Release unused reservation.
7. Collect additional funds or record the debt according to policy.
8. Create balanced ledger entries.
9. Update wallet projections.
10. Mark the reservation settled.
11. Write an outbox event.

All financial effects must occur within a single database transaction.

### 8.3 Settlement Idempotency

Use a deterministic key:

```text
settlement:{reservation_id}
```

Add a unique database constraint on the idempotency key.

If a worker processes the same settlement event twice:

- The first transaction posts the ledger entries.
- The second detects the existing settlement.
- It returns the existing result.
- It does not create another charge.

Idempotency must be enforced by database constraints and transaction logic, not only by an application-level lookup.

### 8.4 Settlement vs Request Lifecycle

Do not put all billing states into the request's lifecycle state field.

Keep these lifecycles separate:

**Request lifecycle:**

```text
CREATED
  |
VALIDATING
  |
EXECUTING
  |
SUCCEEDED / FAILED / CANCELLED
```

**Billing lifecycle:**

```text
NOT_RESERVED
  |
RESERVED
  |
SETTLEMENT_PENDING
  |
SETTLED
```

A request can be successfully completed while billing settlement is still pending.

The client response should not need to wait for every downstream analytics task, but the platform must reliably preserve the settlement obligation.

---

## 9. Streaming and Interrupted Requests

Streaming creates additional billing challenges because the gateway may not receive a complete usage report.

### 9.1 Normal Streaming

1. Reserve the estimated maximum charge.
2. Start provider streaming.
3. Forward chunks to the client.
4. Collect provider usage if available.
5. Finalize usage when the stream ends.
6. Settle the reservation.

Do not write a database record for every token chunk.

Aggregate usage in memory or in a bounded execution context, then persist at appropriate lifecycle boundaries.

### 9.2 Client Disconnect

If the client disconnects:

1. Detect the disconnect.
2. Cancel or close the upstream provider stream.
3. Record the execution termination reason.
4. Capture usage if the provider provides it.
5. Otherwise mark usage as estimated or unknown.
6. Settle conservatively according to the configured policy.
7. Schedule reconciliation if necessary.

A client disconnect does not necessarily mean the provider stopped generating immediately.

### 9.3 Provider Failure During Streaming

If a provider fails after some output has been delivered:

- Preserve the partial output status.
- Record any known usage.
- Do not transparently switch providers and append unrelated output.
- Settle known billable usage according to the provider's pricing and contract.
- Mark uncertain usage for reconciliation.

### 9.4 Missing Usage

Recommended policy:

| Situation | Usage handling |
|---|---|
| Provider reports final usage | Use provider-reported usage |
| Provider omits usage but prompt is known | Estimate input usage |
| Provider stream ends unexpectedly | Use available usage; otherwise mark unknown |
| Provider provides usage asynchronously | Reconcile when available |
| Self-hosted provider exposes metrics | Use normalized deployment usage |

The system should distinguish a charge calculated from final usage from one calculated using an estimate.

For the MVP, avoid silently treating estimated usage as confirmed usage.

---

## 10. Refunds and Adjustments

### 10.1 Refund

A refund reverses some or all of a previously recognized customer charge.

Example:

Original charge: `$12`.

Refund: `$3`.

```text
DEBIT   Platform Revenue $3
CREDIT  Customer Wallet  $3
```

If the refund is being returned through the payment processor rather than wallet credit, use the appropriate refund payable and payment-clearing accounts.

A refund must reference:

- Original settlement.
- Original charge.
- Refund amount.
- Reason.
- Initiating user or system actor.
- Idempotency key.

### 10.2 Adjustment

Adjustments are used when a financial correction is required.

Examples:

- Provider reports corrected usage.
- A pricing configuration was incorrect.
- Customer receives a service credit.
- An operational incident requires compensation.

Never edit the original charge.

Instead, create a compensating transaction.

Example:

Original charge: `$12`.

Correct charge: `$10`.

Adjustment:

```text
DEBIT   Platform Revenue $2
CREDIT  Customer Wallet  $2
```

The original settlement remains unchanged and fully auditable.

### 10.3 Refund and Adjustment Permissions

Define explicit permissions:

- `billing.read`
- `billing.refund`
- `billing.adjust`
- `billing.manage_pricing`
- `billing.manage_wallet`
- `billing.view_ledger`
- `billing.export`

High-value refunds and manual adjustments should support approval workflows and audit records.

---

## 11. Database Schema and Constraints

Recommended MVP tables:

| Table | Purpose |
|---|---|
| wallets | Wallet metadata and balance projections |
| wallet_accounts | Optional account-level ledger mapping |
| reservations | Pre-execution budget reservations |
| usage_records | Normalized usage observations |
| pricing_plans | Customer pricing plans |
| model_prices | Versioned customer model prices |
| provider_cost_prices | Versioned provider cost schedules |
| billing_snapshots | Immutable per-request pricing context |
| charges | Calculated customer charges |
| provider_cost_records | Provider cost calculations |
| ledger_transactions | Financial transaction headers |
| ledger_entries | Double-entry financial records |
| refunds | Refund requests and results |
| adjustments | Manual or automated corrections |
| outbox_events | Reliable event delivery |
| reconciliation_jobs | Reconciliation workflow |

### 11.1 Important Database Constraints

At minimum:

```sql
CREATE UNIQUE INDEX uq_reservation_idempotency
ON reservations (idempotency_key);

CREATE UNIQUE INDEX uq_settlement_reference
ON charges (reservation_id);

CREATE UNIQUE INDEX uq_ledger_idempotency
ON ledger_transactions (idempotency_key);

CREATE UNIQUE INDEX uq_usage_attempt
ON usage_records (attempt_id);
```

The exact constraints depend on whether a request can contain multiple billable attempts or usage components.

For more complex billing, use explicit usage versions and charge components rather than relying on a single usage row per attempt.

### 11.2 Decimal and Integer Columns

Recommended:

- Token counts: `BIGINT`.
- Wallet amounts: `BIGINT` in currency minor units.
- Pricing rates: `NUMERIC` with sufficient precision.
- Calculation intermediates: Python `Decimal`.
- Raw provider payload: `JSONB`.

Never use PostgreSQL `REAL` or `DOUBLE PRECISION` for financial amounts.

### 11.3 Data Retention

Keep financial records for the legally and contractually required period.

Usage analytics can have different retention policies from ledger entries.

Avoid storing full prompts and responses as a billing requirement. The billing system should normally need usage counts, pricing snapshots, identifiers, and calculation details—not customer content.

---

## 12. API Design

### 12.1 Customer APIs

Suggested endpoints:

| Method | Endpoint | Description |
|---|---|---|
| GET | `/v1/billing/balance` | Get available and reserved balance |
| GET | `/v1/billing/usage` | Query usage history |
| GET | `/v1/billing/transactions` | Query wallet transactions |
| GET | `/v1/billing/charges` | Query request charges |
| GET | `/v1/billing/limits` | Get organization and key limits |
| GET | `/v1/billing/pricing` | View applicable customer pricing |

### 12.2 Admin APIs

| Method | Endpoint | Description |
|---|---|---|
| POST | `/admin/billing/pricing` | Create a pricing version |
| POST | `/admin/billing/refunds` | Create refund |
| POST | `/admin/billing/adjustments` | Create adjustment |
| POST | `/admin/billing/wallets/{id}/freeze` | Freeze wallet |
| GET | `/admin/billing/reconciliation` | View reconciliation jobs |

All administrative operations require RBAC and audit logging.

### 12.3 Gateway API Error Handling

Insufficient balance is a platform billing error.

Possible response:

```json
{
  "error": {
    "type": "billing_error",
    "code": "insufficient_balance",
    "message": "Insufficient balance to execute this request.",
    "request_id": "req_123"
  }
}
```

HTTP `402 Payment Required` is a reasonable platform-specific option, but it is not universally handled by OpenAI-compatible clients.

For compatibility, document the error behavior and consider a configurable compatibility policy. Do not pretend that every client interprets HTTP 402 consistently.

Other billing errors should be distinguishable:

- `insufficient_balance`
- `wallet_frozen`
- `budget_exceeded`
- `reservation_failed`
- `pricing_unavailable`
- `settlement_pending`

A pending settlement is normally an internal lifecycle condition, not a reason to fail an already completed model response.

---

## 13. Event-Driven Processing

### 13.1 Events

Suggested event types:

```text
billing.reservation.created
billing.reservation.released
billing.usage.recorded
billing.settlement.requested
billing.settlement.completed
billing.settlement.failed
billing.refund.created
billing.refund.completed
billing.adjustment.created
billing.reconciliation.required
```

### 13.2 Transactional Outbox

Whenever a database transaction changes financial state, insert the corresponding outbox event in the same transaction.

Example:

```text
BEGIN;

UPDATE reservations
SET status = 'SETTLED'
WHERE id = :reservation_id;

INSERT INTO ledger_transactions (...);

INSERT INTO ledger_entries (...);

INSERT INTO outbox_events (
    event_type,
    aggregate_id,
    payload,
    created_at
)
VALUES (
    'billing.settlement.completed',
    :reservation_id,
    :payload,
    NOW()
);

COMMIT;
```

A separate worker publishes pending events.

This avoids the dual-write problem where a database transaction succeeds but message publishing fails.

### 13.3 Delivery Semantics

Assume at-least-once event delivery.

Do not assume exactly-once message delivery.

Instead, enforce exactly-once financial effects through:

- Unique idempotency keys.
- Database transactions.
- Unique constraints.
- Idempotent event consumers.
- Durable event processing status.

Redis Streams can be sufficient for the initial implementation, provided that pending messages, consumer recovery, retries, and dead-letter handling are implemented.

The outbox table remains the durable source for unpublished events.

---

## 14. Reconciliation

Reconciliation is not optional.

It is the mechanism that detects and repairs discrepancies between gateway execution, provider usage, reservations, charges, and ledger balances.

### 14.1 Reconciliation Scenarios

| Scenario | Expected action |
|---|---|
| Request completed but no usage record | Recover or estimate usage |
| Usage recorded but no settlement | Retry settlement |
| Settlement event delivered twice | Return existing settlement |
| Reservation expired but request still running | Keep reservation; investigate |
| Provider reports corrected usage | Create adjustment |
| Wallet projection differs from ledger | Rebuild or correct projection |
| Outbox event remains unpublished | Retry publishing |
| Provider cost differs from expected | Record variance and investigate |

### 14.2 Reconciliation Jobs

Run scheduled jobs for:

1. Reservations stuck in `RESERVED`.
2. Reservations stuck in `SETTLEMENT_PENDING`.
3. Usage records without charges.
4. Charges without matching ledger transactions.
5. Outbox events that have not been published.
6. Wallet balance projection mismatches.
7. Provider usage discrepancies.

Every reconciliation action must be idempotent and auditable.

### 14.3 Rebuild Wallet Balances

Because ledger entries are immutable, wallet projections can be rebuilt from the ledger.

Conceptually:

```sql
SELECT
    account_id,
    currency,
    SUM(
        CASE
            WHEN direction = 'CREDIT' THEN amount
            ELSE -amount
        END
    ) AS balance
FROM ledger_entries
GROUP BY account_id, currency;
```

This example assumes a defined account normal balance convention. In production, debit/credit interpretation should be account-type aware.

Do not blindly apply one sign convention to every ledger account.

---

## 15. Concurrency and Failure Handling

### 15.1 Concurrent Requests

Multiple requests may reserve and settle against the same wallet simultaneously.

Use:

- Row-level locking or atomic conditional updates.
- Database transactions.
- Unique idempotency constraints.
- Consistent lock ordering.
- Bounded transaction duration.

Do not hold a database transaction open while waiting for an upstream model response.

The reservation transaction should finish before provider execution begins.

### 15.2 Provider Timeout

A provider timeout does not always prove that no usage occurred.

Possible cases:

1. Request never reached provider.
2. Provider received the request but did not execute it.
3. Provider executed it but response was lost.
4. Provider partially generated output before timeout.

Record the attempt outcome and usage confidence separately.

Do not automatically release the full reservation just because the gateway timed out.

### 15.3 Worker Crash

If a worker crashes during settlement:

- If the database transaction did not commit, retry the settlement.
- If the transaction committed, the retry must detect the existing idempotency key.
- If the event was not published, the outbox publisher will retry.
- If the event was published but not acknowledged, the consumer must tolerate redelivery.

### 15.4 Database Availability

If PostgreSQL is unavailable:

- Do not execute a billable request without a valid reservation, unless an explicitly designed credit policy permits it.
- Return a retryable platform error.
- Do not rely on Redis alone as the financial source of truth.
- Recover through durable database state once availability returns.

---

## 16. Security and Audit

Billing is a sensitive subsystem.

Required controls:

- Tenant-scoped database access.
- Organization-level authorization.
- Strict separation of customer and admin permissions.
- Immutable ledger history.
- Audit trail for manual financial operations.
- Encryption of payment-provider credentials.
- No API keys or payment secrets in logs.
- Idempotency key validation.
- Rate limits on refund and adjustment endpoints.
- Approval requirements for high-value adjustments.
- Export access control.

Audit records should include:

- Actor ID.
- Organization ID.
- Operation.
- Resource ID.
- Previous and new state where appropriate.
- Reason.
- Timestamp.
- Request ID.
- Approval metadata.

Never expose internal provider cost or margin information to ordinary customers unless the commercial contract explicitly permits it.

---

## 17. Observability

### 17.1 Metrics

Recommended metrics:

| Metric | Description |
|---|---|
| `billing_reservation_total` | Total reservation attempts |
| `billing_reservation_failed_total` | Failed reservations |
| `billing_settlement_total` | Completed settlements |
| `billing_settlement_failed_total` | Failed settlements |
| `billing_settlement_latency_seconds` | Settlement processing latency |
| `billing_usage_missing_total` | Missing usage reports |
| `billing_reconciliation_total` | Reconciliation operations |
| `billing_wallet_projection_mismatch_total` | Wallet projection discrepancies |
| `billing_outbox_pending` | Pending outbox events |

Use bounded-cardinality labels such as status, currency, and operation type.

Do not use request IDs, organization IDs, API keys, or arbitrary model names as unrestricted Prometheus labels.

### 17.2 Alerts

Important alerts:

- Settlement failure rate increases.
- Reservations remain pending too long.
- Outbox backlog grows.
- Wallet projection mismatches occur.
- Missing provider usage increases.
- Reconciliation jobs fail.
- Unexpected negative balances appear.
- Ledger transactions fail balance validation.

A financial invariant violation should be treated as a high-priority incident.

---

## 18. Testing Strategy

### 18.1 Unit Tests

Test:

- Token charge calculation.
- Pricing version selection.
- Cached-token normalization.
- Multi-modal pricing.
- Rounding.
- Reservation amount estimation.
- Settlement amount calculation.
- Refund limits.
- Ledger balance validation.

### 18.2 Integration Tests

Test:

- Concurrent reservation against one wallet.
- Duplicate reservation requests.
- Duplicate settlement events.
- Reservation release.
- Settlement after provider failure.
- Worker crash during settlement.
- Outbox redelivery.
- Wallet projection rebuild.
- Pricing changes during active requests.

### 18.3 Property-Based Tests

Useful financial properties:

1. Every posted ledger transaction balances.
2. A repeated settlement does not change the final balance.
3. A reservation never consumes more than its permitted amount without an explicit debt policy.
4. A refund never exceeds the refundable amount.
5. Rebuilding wallet projections from the ledger produces the same balance.
6. Reordering duplicate event deliveries does not create duplicate financial effects.

### 18.4 Concurrency Tests

Example:

- Wallet balance: `$100`.
- 20 concurrent requests.
- Each request reserves `$10`.

Expected result:

- At most 10 reservations succeed.
- Total reserved amount never exceeds `$100`.
- No negative available balance.
- Repeating the same idempotency key does not create a second reservation.

Run these tests against PostgreSQL, not only mocked repositories.

---

## 19. MVP Implementation Plan

Do not build a complete enterprise billing platform in the first release.

Implement the minimum reliable financial foundation.

### Phase 1 — Basic Wallet and Usage

- Organization wallet.
- USD only.
- Prepaid balance.
- Model token pricing.
- Usage records.
- Balance query API.
- Basic billing dashboard.

### Phase 2 — Reservation and Settlement

- Atomic budget reservation.
- Idempotent reservation.
- Pricing snapshots.
- Final usage calculation.
- Settlement.
- Reservation release.
- Double-entry ledger.

### Phase 3 — Reliability

- Transactional Outbox.
- Settlement worker.
- Retry and dead-letter handling.
- Reservation expiration.
- Reconciliation jobs.
- Wallet projection rebuild.
- Billing audit log.

### Phase 4 — Advanced Billing

- API-key spending limits.
- Organization-level budgets.
- Model-specific pricing.
- Cached token pricing.
- Multi-modal usage.
- Refunds and adjustments.
- Provider cost and gross margin analytics.

### Recommended MVP Scope

| Feature | Priority |
|---|---|
| Organization wallet | P0 |
| Prepaid balance | P0 |
| Token-based pricing | P0 |
| Pricing snapshots | P0 |
| Usage records | P0 |
| Budget reservation | P0 |
| Idempotent settlement | P0 |
| Double-entry ledger | P0 |
| Transactional Outbox | P0 |
| Basic reconciliation | P0 |
| Provider cost tracking | P1 |
| Refunds and adjustments | P1 |
| Multi-currency | P2 |
| Subscription billing | P2 |
| Enterprise invoicing | P2 |

**Important:** Do not postpone the ledger or idempotency until after launch. A minimal double-entry ledger is much cheaper to implement early than to retrofit after real customer balances and payments exist.

---

## 20. Suggested Python Module Structure

Keep the billing domain independent from FastAPI route handlers.

```text
app/
├── billing/
│   ├── domain/
│   │   ├── models.py
│   │   ├── enums.py
│   │   ├── money.py
│   │   ├── pricing.py
│   │   ├── usage.py
│   │   └── ledger.py
│   │
│   ├── services/
│   │   ├── wallet_service.py
│   │   ├── pricing_service.py
│   │   ├── reservation_service.py
│   │   ├── usage_service.py
│   │   ├── settlement_service.py
│   │   └── refund_service.py
│   │
│   ├── repositories/
│   │   ├── wallet_repository.py
│   │   ├── reservation_repository.py
│   │   ├── usage_repository.py
│   │   └── ledger_repository.py
│   │
│   ├── workers/
│   │   ├── settlement_worker.py
│   │   ├── reconciliation_worker.py
│   │   └── outbox_worker.py
│   │
│   ├── api/
│   │   ├── customer_routes.py
│   │   └── admin_routes.py
│   │
│   └── tests/
│       ├── test_pricing.py
│       ├── test_reservation.py
│       ├── test_settlement.py
│       ├── test_ledger.py
│       └── test_concurrency.py
│
└── infrastructure/
    ├── database.py
    └── outbox.py
```

The billing domain should not import FastAPI request objects or depend on provider-specific SDKs.

Provider-specific usage normalization belongs in the provider adapter or metering integration layer. The billing domain consumes normalized usage.

---

## 21. Key Architecture Decisions

| ADR | Decision |
|---|---|
| ADR-021 | Use prepaid wallet as the initial billing model |
| ADR-022 | Use reservation before billable execution |
| ADR-023 | Use immutable double-entry ledger |
| ADR-024 | Use integer minor units for wallet balances |
| ADR-025 | Use Decimal/fixed-point arithmetic for pricing |
| ADR-026 | Version all customer and provider pricing |
| ADR-027 | Separate usage observations from financial charges |
| ADR-028 | Use Transactional Outbox for financial events |
| ADR-029 | Use idempotency keys for all financial mutations |
| ADR-030 | Reconcile asynchronously and preserve audit history |

---

## 22. Acceptance Criteria

The billing subsystem is ready for MVP when:

1. A customer can purchase or receive wallet credit.
2. A request cannot execute without a successful reservation under the prepaid policy.
3. Concurrent requests cannot overspend the same wallet.
4. Every request has an identifiable usage record or an explicit missing/unknown usage state.
5. Customer charges use immutable pricing snapshots.
6. A completed request can be settled exactly once financially.
7. Unused reserved funds are released correctly.
8. Ledger transactions always balance.
9. Duplicate events do not produce duplicate charges.
10. Refunds and adjustments preserve the original financial history.
11. Worker crashes do not permanently lose settlement work.
12. Wallet balances can be rebuilt and reconciled from ledger records.
13. Streaming cancellation and provider failure have explicit billing behavior.
14. Admin billing operations are auditable.
15. Financial data is isolated between organizations.

---

## 23. Future Extensions

The design should leave room for:

- Subscription and monthly credit plans.
- Organization-wide and per-user spending policies.
- Per-model and per-deployment budgets.
- Customer-specific negotiated prices.
- Volume discounts.
- Provider contract pricing.
- Multi-currency wallets.
- FX conversion and settlement.
- Payment processor integration.
- Invoices and tax handling.
- Enterprise postpaid credit.
- Usage-based billing for non-token modalities.
- Self-hosted inference infrastructure cost allocation.
- Financial reporting and accounting exports.

These extensions should reuse the same reservation, usage, pricing snapshot, settlement, and ledger foundations.

---

## 24. Final Design Principles

The billing subsystem should follow five clear boundaries:

- **Pricing decides how much usage costs.**
- **Reservation decides whether the customer can afford to execute.**
- **Usage Metering records what actually happened.**
- **Settlement determines the final financial effect.**
- **Ledger preserves the authoritative financial history.**

The most important architectural rule:

**Never let request execution directly mutate financial balances.**

All financial changes must go through explicit, transactional, idempotent billing operations.

This separation allows the gateway to scale its request execution independently while keeping customer balances and financial records correct.  