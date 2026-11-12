# OpenRouter 类 AI Gateway：完整技术架构设计

**状态：** ⚠️ 历史参考文档（早期设计草案）
**日期：** 2026-11-12 标记
**替代关系：** 实现规范以 `documents/design/Doc_01`–`Doc_04` 为准

---

## 文档状态说明

本文档是项目早期的完整架构设计草案，记录了产品定位、技术选型和初步设计思路。**当前实现规范已迁移至以下文档，如有冲突以它们为准：**

- **请求生命周期与路由：** `documents/design/Doc_01_Request_Lifecycle_Intelligent_Routin.md`
- **计费与账本：** `documents/design/Doc_02_Billing_Ledger_Design.md`
- **跨文档契约：** `documents/design/Doc_03_Cross_Document_Architecture_Contract.md`
- **长任务路由：** `documents/design/Doc_04_Intelligent_Routing_for_Long_running_Coding_Workloads.md`

**已提取的独立内容：**
- 产品定位与三支柱模型 → `documents/product/Product_Positioning.md`
- 双市场合规架构 → `documents/compliance/China_Global_Compliance.md`
- 12 周 MVP Roadmap → `documents/planning/MVP_Roadmap.md`

**已被取代的章节（保留作历史参考）：**
- §4.5 Financial Domain（简单 Ledger 模型）→ 见 Doc 02/03 的预留-结算-账本模型
- §7 Request Lifecycle（10 阶段简化流程）→ 见 Doc 01 的详细状态机
- §8 Intelligent Router（基础版）→ 见 Doc 01 §5 + Doc 04

**仍具参考价值的内容：**
- 技术选型与 Monorepo 结构（§2–3）
- 数据库 Schema 草案（§5）
- API 端点清单（§6）
- 安全与可观测性原则（§10）

---

产品定位已确定
 Startup / MVP

根据你的选择，我建议把项目定义为：

Unified LLM Gateway & Intelligent AI Infrastructure Platform

它既是一个面向开发者的模型聚合平台，也是一个面向企业的 LLM Gateway，同时提供智能路由、成本管理和模型基础设施服务。

我不建议一开始就做成大型微服务系统。更合理的方案是：
- 采用 Modular Monolith + 独立 Data Plane。
- 以 Python 为主要开发语言。
- API 兼容 OpenAI，尽可能兼容 Anthropic 的调用习惯。
- 支持商业模型、第三方推理服务和自建开源模型。
- 同时支持个人开发者、团队和企业客户。
- 采用预付费钱包为主、企业月结为辅的商业模式。
- 预留多区域部署，但 MVP 先部署一个主要 Region。
1. 产品定位与核心设计原则
1.1 产品的三个业务支柱









Pillar A — Model Aggregation

统一接入 OpenAI、Anthropic、Google、DeepSeek、云平台和自建模型。

解决：模型分散、接口不统一、Provider 接入成本高。












Pillar B — Intelligent Routing

根据成本、延迟、质量、可用性和用户策略选择模型及 Provider。

解决：成本高、供应商不稳定、模型选择困难。












Pillar C — Enterprise Gateway

提供认证、权限、预算、计费、审计、可观测性和企业策略。

解决：企业使用 AI 模型时的治理和成本控制问题。



1.2 五个必须坚持的架构原则
1. OpenAI Compatibility First：先做好兼容接口，不要让用户学习新 API。
2. Provider Agnostic：业务层不能直接依赖 OpenAI、Anthropic 等 SDK。
3. Financial Correctness：用量和财务账本必须可追溯、可对账。
4. Policy Before Routing：先检查权限、预算和数据策略，再决定路由。
5. Observable by Design：每一次请求、每一次 Provider Attempt 都有统一 Trace ID。
另外，因为你的目标市场是中国和海外，必须把 Region、数据驻留、Provider 合规资格、跨境数据流动和供应商转售授权作为一等设计对象，而不是上线后再补。

2. 总体技术架构
建议采用两个逻辑平面：
- Control Plane：管理用户、组织、模型、Provider、价格、策略、账单和配置。
- Data Plane：负责实时请求处理、鉴权、路由、Provider 调用、流式响应和用量采集。
System Architecture
Client Layer

Developers · AI Agents · Enterprise Applications · SDKs


API Edge
OpenAI Compatible API


Anthropic Compatible API


Authentication


Rate Limiting


Request Validation


Request ID / Trace ID





Data Plane — Request Processing
Policy Engine


Quota / Budget Check


Model Resolution


Intelligent Router


Provider Adapter


Retry / Fallback



Provider Execution

OpenAI · Anthropic · Google · DeepSeek · Cloud · vLLM · SGLang



Async Event Pipeline
Usage Events · Request Events · Provider Events · Audit Events
Billing


Analytics


Observability





Control Plane
• User / Organization

• API Key / RBAC

• Model Registry

• Provider Management

• Pricing / Billing

• Routing Policies

• Audit / Compliance

• Admin Dashboard



逻辑架构图。MVP 中不需要把每个方框都实现为独立微服务。
2.1 技术选型
组件	建议	职责
API Framework	FastAPI + Starlette	API、Async、Streaming
Language	Python 3.12+	核心业务
Database	PostgreSQL	Transactional Data
Cache	Redis	Key Cache、限流、短期状态
Event Bus	Redis Streams 起步，Redpanda 后续	异步事件
Analytics	ClickHouse	请求、Token、成本分析
ORM	SQLAlchemy 2.x	数据访问
Migration	Alembic	Schema 版本管理
Observability	OpenTelemetry	Tracing、Metrics
Frontend	Next.js + TypeScript	Developer Portal、Admin
Deployment	Docker + Kubernetes 后续	部署和扩展

我建议 MVP 不要立即引入 Kafka、Kubernetes、服务网格和复杂的分布式配置中心。

先用 PostgreSQL + Redis + 一个异步 Worker，就能完成绝大多数初期业务。
3. 服务边界与模块拆分
这里是我认为最重要的架构决策之一。

虽然前面列出了很多模块，但 MVP 阶段不应该直接拆成 12 个微服务。

建议使用一个 Monorepo，内部按业务领域划分模块。
3.1 建议的服务边界
模块	核心职责	是否独立部署
gateway-api	接收请求、兼容 API、Streaming	是，独立 Data Plane
identity	User、Org、Team、RBAC	否
api-keys	Key 创建、验证、撤销	否
model-registry	Model、Provider、Deployment	否
routing	Candidate Selection、Routing Policy	否
provider-adapters	Provider API 转换	否
policy-engine	权限、预算、数据策略	否
usage-metering	Token、请求量、费用计算	否
billing	Wallet、Ledger、Invoice	否
observability	Logs、Metrics、Tracing	后续可独立
audit	审计事件和查询	否
admin-api	管理后台 API	否
worker	异步事件、账单、日志	是，独立进程

注意，gateway-api 和 worker 可以独立运行，但初期仍然可以共用一套 Python 代码和数据库。
3.2 推荐 Monorepo 目录结构
llm-platform/
│
├── apps/
│   ├── gateway/
│   │   ├── main.py
│   │   ├── middleware/
│   │   └── routes/
│   │
│   ├── admin_api/
│   │   └── main.py
│   │
│   └── worker/
│       ├── main.py
│       └── handlers/
│
├── packages/
│   ├── core/
│   │   ├── config.py
│   │   ├── exceptions.py
│   │   └── ids.py
│   │
│   ├── identity/
│   ├── organizations/
│   ├── api_keys/
│   ├── models/
│   ├── providers/
│   ├── routing/
│   ├── policies/
│   ├── metering/
│   ├── billing/
│   ├── observability/
│   ├── audit/
│   └── notifications/
│
├── integrations/
│   ├── openai/
│   ├── anthropic/
│   ├── google/
│   ├── deepseek/
│   ├── openai_compatible/
│   ├── vllm/
│   └── sglang/
│
├── frontend/
│   ├── developer_portal/
│   └── admin_dashboard/
│
├── migrations/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── contract/
│   └── e2e/
│
├── infra/
│   ├── docker/
│   ├── terraform/
│   └── deployment/
│
├── docs/
│   ├── architecture/
│   ├── api/
│   └── adr/
│
├── pyproject.toml
└── README.md


建议每个业务 Package 内部遵循类似结构：
billing/
├── domain/
│   ├── entities.py
│   ├── value_objects.py
│   └── events.py
│
├── application/
│   ├── commands.py
│   ├── queries.py
│   └── services.py
│
├── infrastructure/
│   ├── repositories.py
│   └── persistence.py
│
└── api/
    └── routes.py


这是一种偏 DDD + Clean Architecture 的组织方式。

不必教条地让每个模块都拥有四层代码，但要明确 Domain 和 Infrastructure 的边界。

4. Domain Model 设计
我建议将 Domain 分成 8 个 Bounded Context。
Domain Map
1

Identity & Tenant

User · Organization · Team · Membership



2

Access Management

API Key · Role · Permission · Quota



3

Model & Provider

Model · Provider · Deployment · Pricing



4

Routing & Policy

Routing Policy · Rule · Candidate · Guardrail



5

Request & Usage

Request · Attempt · Usage Event · Token Usage



6

Financial

Wallet · Ledger · Credit · Invoice · Settlement



7

Observability & Audit

Request Log · Trace · Audit Event



8

Platform Operations

Region · Configuration · Notification · Webhook



4.1 Identity & Tenant
这里要注意一个设计：不要将 User 和 Customer 混为一谈。

推荐关系：
User
  |
  +---- Membership ---- Organization
  |                         |
  |                         +---- Team
  |                                  |
  |                                  +---- API Keys
  |
  +---- Personal Organization


核心实体：
Entity	说明
User	登录账户
Organization	付费客户 / 租户
Team	组织内部团队
Membership	用户和组织的关系
Invitation	团队邀请
Role	Owner、Admin、Developer、Billing Viewer
Permission	细粒度权限

建议每个注册用户自动创建一个 Personal Organization。

这样个人用户和企业用户可以走同一套计费、API Key 和权限模型。
4.2 Model & Provider
这是平台最核心的领域模型之一。

必须把 Model 和 Provider Deployment 分开。
Model
  |
  +---- ModelCapability
  |
  +---- Deployment
            |
            +---- Provider
            |
            +---- ProviderCredential
            |
            +---- ProviderPricing
            |
            +---- ProviderHealth


举例：
Logical Model:
  claude-sonnet

Deployments:
  ├── Anthropic API
  ├── AWS Bedrock
  └── Google Vertex AI


这里有几个重要的 Value Objects：
- ModelIdentifier
- ProviderIdentifier
- TokenPricing
- ModelCapabilities
- DeploymentEndpoint
- RegionIdentifier
Provider Adapter 则负责协议转换，不应该让业务层直接依赖 Provider SDK。

我建议定义统一的内部协议：
class ProviderAdapter(Protocol):    async def generate(        self,        request: UnifiedRequest,        deployment: Deployment,    ) -> UnifiedResponse:        ...    async def stream(        self,        request: UnifiedRequest,        deployment: Deployment,    ) -> AsyncIterator[UnifiedChunk]:        ...    async def health_check(        self,        deployment: Deployment,    ) -> HealthStatus:        ...



UnifiedRequest 应该尽可能保留原始请求信息，避免在统一格式转换中丢失 Provider 特有参数。

还要维护 Capability Matrix：
@dataclassclass ModelCapabilities:    streaming: bool    tool_calling: bool    vision: bool    json_mode: bool    embeddings: bool    audio_input: bool    audio_output: bool    max_context_tokens: int    max_output_tokens: int



不能仅仅因为两个 Provider 都支持 Chat Completions，就认为它们的所有参数、工具调用和多模态行为都相同。
4.3 Routing Domain
建议将 RoutingPolicy 设计为独立领域对象。
@dataclassclass RoutingPolicy:    strategy: str    allowed_deployments: list[str]    excluded_providers: list[str]    max_latency_ms: int | None    max_cost_per_request: Decimal | None    allow_fallback: bool    max_attempts: int    data_residency: str | None    require_zdr: bool



支持以下策略：
Strategy	MVP
Fixed Provider	必须
Priority	必须
Lowest Cost	必须
Weighted	必须
Latency Based	第二阶段
Availability Based	第二阶段
Quality Based	后续

我特别建议把 Router 做成纯决策组件。

例如：
decision = router.select(    request=request,    model=model,    candidates=candidates,    policy=policy,    provider_health=health_snapshot,)# decision 不负责调用 Provider# 它只负责返回选择结果



这样测试 Routing Algorithm 会容易得多，也可以单独进行离线模拟和策略评估。
4.4 Request & Usage Domain
这部分建议使用三个不同的实体：

Request：用户的一次逻辑请求。

RequestAttempt：实际调用某个 Provider 的一次尝试。

UsageRecord：一次调用产生的用量和成本记录。

例如：
Request
  id: req_123
  requested_model: claude-sonnet
  status: succeeded

  Attempts:
    ├── Attempt 1
    │     Provider: Anthropic
    │     Status: timeout
    │
    └── Attempt 2
          Provider: Bedrock
          Status: succeeded

  Usage:
    input_tokens: 1000
    output_tokens: 500
    customer_cost: $0.015
    provider_cost: $0.012


建议 Request 状态：
CREATED
  |
  v
VALIDATING
  |
  v
ROUTING
  |
  v
EXECUTING
  |
  +---- SUCCEEDED
  |
  +---- FAILED
  |
  +---- CANCELLED


Attempt 则有自己的状态和生命周期。

一个逻辑请求可能对应多个 Attempt，但通常只能有一个最终成功的 Attempt。对于流式输出和已经产生副作用的请求，还要额外考虑部分响应和重试安全性。

4.5 Financial Domain

> **⚠️ 已过时：** 本节的简单 Ledger 模型已被 `documents/design/Doc_02_Billing_Ledger_Design.md` 和 `documents/design/Doc_03_Cross_Document_Architecture_Contract.md` 的预留-结算-账本-幂等模型取代。此处保留作历史参考。

这里建议使用 Ledger-based Architecture。
Organization
    |
    +---- Wallet
    |       |
    |       +---- Ledger Entries
    |
    +---- Billing Account
    |       |
    |       +---- Invoice
    |       +---- Payment
    |
    +---- Pricing Plan


主要实体：
Entity	作用
Wallet	用户可用余额
LedgerEntry	不可变资金流水
UsageCharge	请求对应的客户费用
ProviderCost	供应商成本
Credit	赠送额度或促销额度
Payment	充值或付款
Invoice	对账和开票
Settlement	结算状态
PricingPlan	用户价格方案

这里有两个不同的财务概念：
- Customer Ledger：客户欠款或余额变化。
- Provider Cost Ledger：你的供应商成本。
不要把两者混成一个 balance 字段。

建议的计费流程：
1. 请求到达，估算最大可能费用。
2. 在事务中创建 Budget Reservation。
3. 执行 Provider 请求。
4. 获得实际 Token Usage。
5. 根据价格版本计算费用。
6. 将 Reservation 转为实际 Debit。
7. 释放未使用的预留额度。
8. 写入 Provider Cost。
9. 异步生成报表。
所有金融事件都需要 Idempotency Key，避免消息重复消费导致重复扣款。

另外，建议把客户余额拆成：
\[
Available = PostedBalance - ReservedBalance
\]

其中预留额度与实际扣费不能重复计算。

5. PostgreSQL 数据库 Schema
不建议一开始建立几十张表。下面是我建议的 MVP 核心 Schema。
5.1 Identity Tables
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE organizations (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    org_type VARCHAR(32) NOT NULL,
    region VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE memberships (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    role VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    UNIQUE(user_id, organization_id)
);

CREATE TABLE teams (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES organizations(id),
    name VARCHAR(255) NOT NULL
);


5.2 API Keys
CREATE TABLE api_keys (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES organizations(id),
    team_id UUID REFERENCES teams(id),

    name VARCHAR(255) NOT NULL,
    key_prefix VARCHAR(32) NOT NULL,
    key_hash VARCHAR(255) NOT NULL UNIQUE,

    status VARCHAR(32) NOT NULL DEFAULT 'active',

    rpm_limit INTEGER,
    tpm_limit BIGINT,
    max_budget NUMERIC(20, 10),

    expires_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


安全建议：
- API Key 使用高熵随机值生成。
- 数据库存储 Hash，不存储明文。
- 只在创建时展示完整 Key。
- 使用独立的 Pepper 或 HMAC Secret 做 Key 验证。
- 支持撤销、轮换和过期。
- 对 Provider Credentials 使用 KMS 或 Secret Manager 加密存储。
API Key 和 Provider Key 是两种不同的凭证，必须分开管理。
5.3 Model & Provider Tables
CREATE TABLE providers (
    id UUID PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    adapter_type VARCHAR(64) NOT NULL,
    region VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL
);

CREATE TABLE models (
    id UUID PRIMARY KEY,
    slug VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(255) NOT NULL,

    context_window INTEGER,
    max_output_tokens INTEGER,

    capabilities JSONB NOT NULL DEFAULT '{}',
    status VARCHAR(32) NOT NULL DEFAULT 'active'
);

CREATE TABLE deployments (
    id UUID PRIMARY KEY,
    model_id UUID NOT NULL REFERENCES models(id),
    provider_id UUID NOT NULL REFERENCES providers(id),

    provider_model_id VARCHAR(255) NOT NULL,
    endpoint TEXT,

    region VARCHAR(32) NOT NULL,
    credential_ref TEXT NOT NULL,

    priority INTEGER NOT NULL DEFAULT 100,
    weight INTEGER NOT NULL DEFAULT 100,

    status VARCHAR(32) NOT NULL DEFAULT 'active'
);

CREATE TABLE pricing_versions (
    id UUID PRIMARY KEY,
    deployment_id UUID NOT NULL REFERENCES deployments(id),

    input_price NUMERIC(20, 12) NOT NULL,
    output_price NUMERIC(20, 12) NOT NULL,
    cached_input_price NUMERIC(20, 12),

    currency CHAR(3) NOT NULL DEFAULT 'USD',
    unit VARCHAR(32) NOT NULL DEFAULT 'per_1m_tokens',

    effective_from TIMESTAMPTZ NOT NULL,
    effective_until TIMESTAMPTZ
);


特别注意 pricing_versions。

不要直接修改原价格记录，因为历史请求必须能够根据当时的价格版本重新计算和审计。

另外，真实模型价格不一定只有 Input 和 Output Tokens。还可能有 cached tokens、reasoning tokens、image tokens、audio seconds、tool calls 等不同计价维度。建议后续将价格维度扩展成独立的 pricing_components 表。
5.4 Request & Usage Tables
CREATE TABLE requests (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES organizations(id),
    api_key_id UUID REFERENCES api_keys(id),

    requested_model VARCHAR(255) NOT NULL,
    resolved_model VARCHAR(255),

    status VARCHAR(32) NOT NULL,

    input_tokens BIGINT DEFAULT 0,
    output_tokens BIGINT DEFAULT 0,

    customer_cost NUMERIC(20, 12) DEFAULT 0,
    currency CHAR(3) DEFAULT 'USD',

    latency_ms INTEGER,

    region VARCHAR(32) NOT NULL,
    trace_id VARCHAR(128),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE request_attempts (
    id UUID PRIMARY KEY,
    request_id UUID NOT NULL REFERENCES requests(id),

    deployment_id UUID REFERENCES deployments(id),
    attempt_number INTEGER NOT NULL,

    status VARCHAR(32) NOT NULL,
    error_code VARCHAR(100),

    input_tokens BIGINT DEFAULT 0,
    output_tokens BIGINT DEFAULT 0,

    provider_cost NUMERIC(20, 12) DEFAULT 0,
    latency_ms INTEGER,

    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    UNIQUE(request_id, attempt_number)
);


5.5 Financial Tables
CREATE TABLE wallets (
    id UUID PRIMARY KEY,
    organization_id UUID UNIQUE NOT NULL
        REFERENCES organizations(id),

    currency CHAR(3) NOT NULL,
    posted_balance NUMERIC(20, 10) NOT NULL DEFAULT 0,
    reserved_balance NUMERIC(20, 10) NOT NULL DEFAULT 0,

    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE wallet_reservations (
    id UUID PRIMARY KEY,
    wallet_id UUID NOT NULL REFERENCES wallets(id),
    request_id UUID NOT NULL UNIQUE REFERENCES requests(id),

    amount NUMERIC(20, 10) NOT NULL,
    status VARCHAR(32) NOT NULL,

    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE ledger_entries (
    id UUID PRIMARY KEY,
    wallet_id UUID NOT NULL REFERENCES wallets(id),

    transaction_id UUID NOT NULL,
    entry_type VARCHAR(32) NOT NULL,

    amount NUMERIC(20, 10) NOT NULL,
    currency CHAR(3) NOT NULL,

    reference_type VARCHAR(32),
    reference_id UUID,

    idempotency_key VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


这里的 ledger_entries 必须遵循：
- 只追加，不直接 UPDATE 或 DELETE。
- 每笔资金变化都有唯一业务引用。
- 退款通过反向流水完成。
- 同一 Idempotency Key 不能重复入账。
- 定期通过 Ledger 汇总值与 Wallet 投影值核对。
生产环境还建议采用双重记账（Double-entry Bookkeeping），引入账户科目和借贷分录，而不是只依赖钱包余额字段。
5.6 Audit & Events Tables
CREATE TABLE audit_events (
    id UUID PRIMARY KEY,

    organization_id UUID,
    actor_user_id UUID,

    action VARCHAR(128) NOT NULL,
    resource_type VARCHAR(128) NOT NULL,
    resource_id VARCHAR(128),

    before_state JSONB,
    after_state JSONB,

    ip_address INET,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE outbox_events (
    id UUID PRIMARY KEY,
    aggregate_type VARCHAR(128) NOT NULL,
    aggregate_id UUID NOT NULL,

    event_type VARCHAR(128) NOT NULL,
    payload JSONB NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published_at TIMESTAMPTZ
);


Audit Event 和 Outbox Event 不要混为一谈：
- Audit Event：谁在什么时候修改了什么。
- Outbox Event：哪些业务事件需要异步发布。
使用 Transactional Outbox 可以解决数据库事务成功、消息却没有成功发送的问题。

数据库设计的几个生产级要求：
1. 所有租户业务表都要有 organization_id，并建立适当的索引。
2. 使用 PostgreSQL Row-Level Security 作为额外的租户隔离保护，但不能替代应用层授权。
3. Request 和 Attempt 表需要预留按时间分区的方案。
4. 原始 Prompt 和 Response 默认不要写入普通业务日志。
5. 财务数据、请求数据和审计数据采用不同的保留策略。
6. 所有金额使用 Decimal / NUMERIC，禁止使用浮点数做财务计算。
这份 SQL 是核心实体的起点，不是最终生产 DDL；还需要补齐外键索引、CHECK Constraints、状态约束、更新审计和迁移策略。

6. 核心 API 设计
API 建议分成三类：
- Public API：客户调用。
- Management API：客户管理自己的账户和资源。
- Internal API：后台管理和内部服务之间使用。
6.1 Public LLM API
建议 MVP 先实现：
Method	Endpoint	功能
POST	/v1/chat/completions	Chat Completion
POST	/v1/embeddings	Embeddings
GET	/v1/models	Model List
POST	/v1/responses	Responses API，后续
POST	/v1/messages	Anthropic Messages API，后续
GET	/v1/health	Gateway Health

OpenRouter 当前也提供 Responses API 和 Chat Completions API，并通过统一格式处理不同 Provider。

GitHub

6.2 Chat Completion 请求
建议兼容标准 OpenAI 请求，并添加自己的路由扩展：
{
  "model": "deepseek-chat",
  "messages": [
    {
      "role": "user",
      "content": "Hello"
    }
  ],
  "stream": true,
  "max_tokens": 1024,
  "temperature": 0.7,
  "routing": {
    "strategy": "lowest_cost",
    "allow_fallback": true
  }
}


routing 是你的自定义扩展，必须做到不影响普通 OpenAI SDK 的兼容性。

还可以支持：
{
  "model": "claude-sonnet",
  "messages": [],
  "routing": {
    "strategy": "priority",
    "providers": [
      "anthropic",
      "bedrock"
    ],
    "allow_fallback": true
  }
}


注意：如果未来需要兼容 OpenAI 原生的 provider 或类似路由字段，应明确字段优先级，避免两个配置系统冲突。
6.3 Management API
Method	Endpoint	功能
POST	/v1/organizations	创建组织
GET	/v1/organizations/me	当前组织
POST	/v1/teams	创建 Team
GET	/v1/teams	Team 列表
POST	/v1/keys	创建 API Key
GET	/v1/keys	API Key 列表
DELETE	/v1/keys/{id}	撤销 Key
GET	/v1/usage	用量查询
GET	/v1/usage/daily	每日用量
GET	/v1/billing/balance	余额
GET	/v1/billing/transactions	交易流水
POST	/v1/billing/topups	充值
GET	/v1/audit-events	审计查询

6.4 Admin API
建议统一使用 /admin/v1 前缀。
/admin/v1/providers
/admin/v1/providers/{id}/credentials
/admin/v1/providers/{id}/health

/admin/v1/models
/admin/v1/models/{id}/deployments

/admin/v1/pricing
/admin/v1/routing-policies

/admin/v1/organizations
/admin/v1/users

/admin/v1/requests
/admin/v1/financial-reports
/admin/v1/audit-events


Admin API 必须使用独立的管理权限，不要让普通用户 API Key 有机会访问管理端点。
6.5 Webhooks
企业客户可能需要接收：
request.completed
request.failed

wallet.low_balance
wallet.depleted

usage.budget_exceeded

api_key.expiring
provider.degraded
provider.recovered


Webhook 应该支持：
- HMAC 签名。
- Timestamp 防重放。
- Retry。
- Delivery Log。
- Idempotency。
- Secret Rotation。

7. 核心 Request Lifecycle

> **⚠️ 已过时：** 本节的 10 阶段简化流程已被 `documents/design/Doc_01_Request_Lifecycle_Intelligent_Routin.md` 的详细状态机（含独立执行/计费生命周期、OUTCOME_UNKNOWN、PARTIALLY_COMPLETED 等状态）取代。此处保留作历史参考。

这部分是整个架构真正的核心。

我建议把每次请求分成 10 个阶段。
Request Execution Flow
1. API Ingress
   
   生成 Request ID / Trace ID，解析协议和请求。
2. Authentication
   
   验证 API Key，取得 User、Organization、Team。
3. Authorization & Policy
   
   验证模型权限、Region、数据策略和调用限制。
4. Budget Reservation
   
   原子预留用户预算，防止并发超额消费。
5. Model Resolution
   
   找到逻辑 Model 和可用 Deployments。
6. Intelligent Routing
   
   根据策略排序候选 Deployment。
7. Provider Execution
   
   转换请求、调用 Provider、处理 Streaming。
8. Usage Metering
   
   提取真实用量和 Provider 成本。
9. Financial Settlement
   
   将预算预留转换为实际扣款，记录 Provider Cost。
10. Event Publishing
    
    通过 Outbox 发布 Usage、Audit 和 Analytics 事件。

7.1 哪些操作必须同步？
这是一个重要的性能设计问题。
操作	同步 / 异步	原因
API Key 验证	同步	安全要求
Model Access Check	同步	权限要求
Rate Limit Check	同步	保护系统
Budget Reservation	同步	防止超额消费
Model Resolution	同步	路由前置条件
Provider Call	同步	用户需要结果
Usage Event	异步	避免阻塞响应
Analytics	异步	非实时关键路径
Audit Event	持久化后异步投递	不能丢失
Billing Settlement	持久化任务，异步可重试	需要可靠结算

这里有一个细节：异步不等于不可靠。比如结算可以在请求响应后由 Worker 执行，但必须保证最终完成，且可以重复执行而不会重复扣款。

对于流式请求，还应考虑：
- Provider 连接中断。
- 客户端主动取消。
- 部分 Token 已经输出。
- Provider 没有返回最终 Usage。
- 超时后是否允许重试。
建议对不同情况设计不同的结算策略。没有可信的 Provider Usage 时，可以根据已观测内容估算，并标记为 estimated，而不能伪装成精确费用。
7.2 Request ID 设计
我建议统一以下标识：
request_id
  |
  +---- trace_id
  |
  +---- organization_id
  |
  +---- api_key_id
  |
  +---- attempt_id
  |
  +---- provider_request_id
  |
  +---- billing_transaction_id


用户拿到一个 request_id，就应该可以在 Dashboard 中查看请求完整生命周期。

LiteLLM 的请求处理架构也采用了缓存优先的鉴权、预算和限流检查、Router 调用以及响应后的异步用量记录，值得作为实现参考。

liteLLM+2

8. Intelligent Router 的详细设计

> **⚠️ 已过时：** 本节的基础路由设计已被 `documents/design/Doc_01_Request_Lifecycle_Intelligent_Routin.md` §5（Intelligent Routing Engine）和 `documents/design/Doc_04_Intelligent_Routing_for_Long_running_Coding_Workloads.md`（长任务路由）取代。此处保留作历史参考。

我建议把 Router 单独设计成一个可以不断演进的领域模块，而不是在 API Handler 里面写一堆 if/else。
8.1 Routing Pipeline
                    User Request
                         |
                         v
                  Model Resolution
                         |
                         v
                 Candidate Generation
                         |
                         v
                  Capability Filter
                         |
                         v
                  Policy Filtering
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
                 Select Deployment
                         |
                         v
                 Provider Execution
                         |
                  +------+------+
                  |             |
                Success       Failure
                  |             |
                  v             v
                Return       Retry / Fallback


Candidate Generation 和 Filtering 要分开。

例如，用户请求：
model = claude-sonnet
region = us
strategy = lowest_cost


系统先找到所有能够提供这个逻辑模型的 Deployment，再过滤掉：
- 不符合用户 Region 要求的。
- 不符合数据处理策略的。
- 不支持所需参数的。
- 已经不可用的。
- 超出用户预算的。
剩下的才交给排序算法。
8.2 Routing Score
第一版不需要 Machine Learning。

可以使用加权评分：
\[
Score(d)=w_cC(d)+w_lL(d)+w_eE(d)+w_uU(d)
\]

其中：
- \(C\)：归一化成本。
- \(L\)：归一化延迟。
- \(E\)：错误率。
- \(U\)：不稳定程度或负载指标。
分数越低越优先。

不同策略使用不同权重：
策略	Cost	Latency	Error Rate
Cheapest	80%	10%	10%
Fastest	10%	80%	10%
Most Reliable	10%	10%	80%
Balanced	40%	30%	30%

这些权重只是初始配置示例，不是行业标准。

另外，Reliability 不能只看历史错误率。建议综合：
- 最近 N 分钟错误率。
- 最近 N 分钟 P95 Latency。
- 连续失败次数。
- 当前 Circuit Breaker 状态。
- Provider Quota 状态。
8.3 Circuit Breaker
每个 Deployment 都应该有独立的 Circuit Breaker。
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
  +---- Failure ---> OPEN


不要把某个 Provider 的一个 Deployment 失败直接视为整个 Provider 故障。

例如：
Anthropic
  ├── US Deployment: Healthy
  ├── EU Deployment: Degraded
  └── APAC Deployment: Unavailable


故障隔离应该尽可能精细。
8.4 Retry 和 Fallback
建议第一版实现：
- Connection Error：可以重试。
- Timeout：满足安全条件时重试。
- HTTP 429：遵守 Retry-After，考虑 Provider Quota。
- HTTP 500/502/503：有限重试。
- HTTP 400：一般不重试。
- Authentication Error：通常应熔断或告警，不要无限重试。
必须设置：
MAX_ATTEMPTS = 3TOTAL_REQUEST_TIMEOUT = 60MAX_FALLBACKS = 2



这里只是配置示例，实际应该根据模型类型和产品 SLA 调整。

一个非常容易犯的错误： 已经向客户端输出部分 Stream 内容后，再自动切换另一个 Provider。

这可能造成重复内容、断流或语义不一致。

所以我建议：
- Provider 首个有效 Token 之前，可以尝试 Fallback。
- 已经输出内容后，不做透明的跨 Provider Fallback。
- 对客户端断开连接，要取消上游请求。
- 对每次 Attempt 单独记录费用。
OpenRouter 的 Provider Selection 文档也提供了 Provider Order、Fallback、参数兼容性以及数据保留约束等路由选项，可以作为功能设计参考。

GitHub

8.5 自建模型接入
因为你选择了 Mixed Provider，我建议定义三类 Adapter：
Adapter 类型	代表	方式
Native Adapter	OpenAI、Anthropic	原生 API
Cloud Adapter	Bedrock、Vertex	云厂商 API
OpenAI-compatible Adapter	vLLM、SGLang、第三方推理服务	标准化 API

自建模型不要直接进入 Router 的特殊逻辑。

只要它实现统一 Adapter 接口，就应该能够参与 Model Resolution、Capability Filtering 和 Routing。

例如 vLLM 已经提供 OpenAI-compatible HTTP Server，并支持多种推理接口，可以显著降低自建模型接入成本。

vLLM


9. 中国与海外双市场架构
这是你这个项目和普通 OpenRouter Clone 最大的架构区别之一。

我建议从第一天就把 Region 作为一个核心概念。
9.1 Region-aware Architecture
Global Control / Management Layer

Tenant Configuration · Model Catalog · Pricing Metadata · Admin

China Region
CN
CN Gateway

CN Database

CN Cache

CN Providers

CN Logs / Billing


Global Region
Global
Global Gateway

Regional Database

Regional Cache

Global Providers

Regional Logs / Billing



逻辑隔离示意图。不是说所有控制面数据都可以跨境同步。
我建议遵循：
1. Tenant 创建时确定主 Region。
2. 请求只能进入允许的数据处理 Region。
3. Provider Deployment 带有 Region 属性。
4. 请求日志默认保存在所属 Region。
5. Prompt、Response 不默认跨 Region 复制。
6. 密钥按 Region 管理。
7. Region 之间通过受控 API 交换必要的非敏感配置。
9.2 中国市场需要特别考虑的事情
需要区分两种商业模式：

模式 A：向中国开发者销售海外 Provider API 的转售服务。

模式 B：在中国境内提供 AI API Gateway，并接入境内模型服务。

这两种模式涉及的合同、数据处理和合规要求可能完全不同。

在产品设计阶段至少要研究：
- Provider 是否允许商业转售。
- 是否允许代理或转发其 API。
- 数据是否会跨境传输。
- 个人信息处理与跨境数据流动要求。
- 面向境内公众提供生成式 AI 服务时的适用要求。
- 境内云资源、域名、备案和网络服务要求。
- 不同 Provider 的数据保留和训练政策。
特别是不能因为 Provider 提供了 API，就默认你拥有再销售该 API 的权利。

这里建议在上线前分别让熟悉中国个人信息保护、数据出境和生成式 AI 监管的律师，以及目标海外市场的律师进行业务模式审查。具体义务要根据实际运营主体、客户、用户、数据类型和服务范围判断。
9.3 Provider Registry 增加合规字段
建议增加：
ProviderCompliance
  ├── commercial_resale_allowed
  ├── proxy_access_allowed
  ├── supported_regions
  ├── data_processing_region
  ├── data_retention_policy
  ├── training_data_policy
  ├── zdr_supported
  ├── compliance_review_status
  ├── contract_reference
  └── review_expiry_date


这些字段应该参与 Router 的 Candidate Filtering，而不只是展示给管理员。

10. Security、Observability 和 Operations
这三个领域不能等产品上线后再补。
10.1 Security Architecture
我建议至少做四层安全保护：
层次	功能
Authentication	API Key、OAuth、SSO
Authorization	RBAC、Organization Scope、Model ACL
Protection	Rate Limit、Quota、Budget、IP Restriction
Data Security	Encryption、Secret Management、PII Masking

特别关注：
- Provider Credential 使用 KMS 加密。
- 数据库密码和 JWT Secret 使用 Secret Manager。
- API Key 不以明文形式保存。
- Admin 操作强制审计。
- 用户只能访问所属 Organization 的数据。
- 避免日志记录 Authorization Header。
- 对恶意请求和异常高频使用进行检测。
10.2 Observability
建议使用 OpenTelemetry 建立统一 Trace。

一次请求的 Trace 可以是：
HTTP Request
  |
  +---- Authentication
  |
  +---- Policy Evaluation
  |
  +---- Budget Reservation
  |
  +---- Model Resolution
  |
  +---- Router Decision
  |
  +---- Provider Attempt #1
  |
  +---- Provider Attempt #2
  |
  +---- Usage Extraction
  |
  +---- Billing Settlement


推荐监控指标：
Metric	说明
gateway_requests_total	总请求数
gateway_request_duration	请求延迟
provider_latency	Provider 延迟
provider_error_rate	Provider 错误率
routing_fallback_total	Fallback 次数
input_tokens_total	输入 Token
output_tokens_total	输出 Token
billing_amount_total	客户收费
provider_cost_total	供应商成本
gross_margin	毛利

Python 的 OpenTelemetry 实现支持 Traces、Metrics 和 Logs，其中 Traces 和 Metrics 已经是稳定组件，可以作为统一可观测性的基础。

OpenTelemetry

10.3 Dashboard 应该分成两套
Developer Portal
- API Keys
- Model Catalog
- API Usage
- Token Usage
- Request History
- Billing
- Wallet
- Organization Management
Platform Admin
- Total Requests
- Active Users
- Provider Health
- Provider Spend
- Customer Revenue
- Gross Margin
- Error Rate
- Routing Performance
- Abuse Detection
- Financial Reconciliation
我认为管理后台最值得重视的三个指标是：
\[
GrossMargin = Revenue - ProviderCost
\]

\[
GrossMarginRate = \frac{Revenue-ProviderCost}{Revenue}
\]

\[
FallbackRate = \frac{FallbackRequests}{TotalRequests}
\]

不过要明确 Gross Margin 不等于最终净利润，还没有扣除支付手续费、基础设施、客服和运营成本。

11. MVP Roadmap：从 0 到商业化
我的建议是按 12 周规划第一个可收费版本。

这里假设你有一位主要后端工程师，能够投入一定的前端和 DevOps 资源；如果完全一个人开发，可以把时间拉长。
Phase 0：Architecture & Foundation（Week 1）
必须完成
目标：先建立统一的架构基础。
- 确定 Domain Model。
- 确定 API Contract。
- 建立 Monorepo。
- 建立 FastAPI 项目。
- 配置 PostgreSQL、Redis。
- 配置 Docker Compose。
- 建立 Alembic Migration。
- 建立统一异常和日志格式。
- 建立 OpenTelemetry。
- 定义 Provider Adapter Protocol。
交付物：
docs/
  architecture/
    system-architecture.md
    domain-model.md
    request-lifecycle.md
    billing-design.md
    routing-design.md
    security-design.md

docs/adr/
  001-modular-monolith.md
  002-control-data-plane.md
  003-provider-adapter.md
  004-ledger-based-billing.md


Phase 1：Core Gateway（Week 2–3）
目标：用户可以真正调用不同的模型。
- OpenAI-compatible API。
- Provider Adapter。
- OpenAI Adapter。
- DeepSeek Adapter。
- vLLM / OpenAI-compatible Adapter。
- Model Registry。
- Provider Registry。
- Streaming。
- Timeout。
- Retry。
- Request ID。
验收标准
同一个 API Endpoint 可以通过不同 Model ID 调用至少三个不同 Provider，并正确返回 Streaming 和 Non-streaming 响应。
Phase 2：Identity & Management（Week 4）
目标：用户可以注册、创建 Key 和管理组织。
- User Registration / Login。
- Organization。
- Team。
- Membership。
- API Key Management。
- API Key Hash Verification。
- RBAC。
- Rate Limiting。
- Model Access Control。
验收：
User Registration
       |
       v
Create Organization
       |
       v
Create API Key
       |
       v
Call LLM API
       |
       v
Access Control Verified


Phase 3：Intelligent Routing（Week 5–6）
目标：实现多个 Provider 之间的智能选择。
- Deployment Registry。
- Capability Filtering。
- Priority Routing。
- Lowest Cost Routing。
- Weighted Routing。
- Provider Health Check。
- Circuit Breaker。
- Retry / Fallback。
- Routing Decision Log。
验收：

同一个 Logical Model 对应多个 Deployments，可以根据用户策略选择 Provider；Provider 失败时可以安全切换。
Phase 4：Metering & Billing（Week 7–8）
商业化关键阶段
目标：实现完整的收费闭环。
- Token Usage Extraction。
- Pricing Engine。
- Pricing Versioning。
- Wallet。
- Budget Reservation。
- Ledger。
- Usage Settlement。
- Customer Cost。
- Provider Cost。
- Top-up。
- Billing Dashboard。
验收：
Customer
   |
   v
Recharge $100
   |
   v
Call LLM
   |
   v
Actual Cost = $0.02
   |
   v
Wallet Debit = $0.02
   |
   v
Ledger Entry Created
   |
   v
Usage Dashboard Updated


重点测试并发请求、重复事件、失败重试、退款和账单对账。
Phase 5：Portal & Operations（Week 9–10）
目标：客户可以自助使用平台，管理员可以运营平台。

Developer Portal：
- Login / Registration。
- API Key Dashboard。
- Model Catalog。
- Usage Dashboard。
- Request History。
- Wallet / Billing。
- Team Management。
Admin Dashboard：
- Provider Management。
- Model Management。
- Pricing Management。
- Routing Policies。
- Customer Management。
- Audit Logs。
- Financial Reports。
Phase 6：Hardening & Beta Launch（Week 11–12）
目标：从可以运行变成可以商业运营。
- Security Review。
- Tenant Isolation Test。
- Billing Consistency Test。
- Load Test。
- Streaming Stability Test。
- Provider Failure Simulation。
- Backup / Restore。
- Rate Limit Verification。
- Provider Contract Review。
- Region Compliance Review。
- Status Page。
- Customer Support Workflow。
Roadmap 总览
12-Week Development Timeline
Phase 0

W1

Architecture & Foundation



Phase 1

W2–3

Core Gateway



Phase 2

W4

Identity & Management



Phase 3

W5–6

Intelligent Routing



Phase 4

W7–8

Metering & Billing



Phase 5

W9–10

Portal & Operations



Phase 6

W11–12

Hardening & Beta



这是开发计划的时间分配示意，不代表每个阶段的实际工作量完全相同。

12. MVP 必须有的验收指标
我建议在项目开始时就定义 Engineering SLO 和 Business KPI。
指标	MVP 目标建议
Gateway Availability	99.9%
Gateway Internal P95 Latency	小于 100ms（不含 Provider 推理）
Authentication Accuracy	100%
Billing Duplicate Charge	0
Ledger Reconciliation	100%
Usage Event Loss	0（最终持久化目标）
Provider Fallback	可正确执行
Tenant Data Isolation	无越权访问
Request Trace Coverage	100%

注意，Gateway P95 不包含模型推理延迟，而且这些是初始目标，不是已经测得的性能承诺。

建议增加以下测试：

Concurrency Testing

例如 1,000 个并发请求下：
- Redis 限流是否正确。
- Wallet 是否出现超额扣款。
- Provider Quota 是否被正确控制。
- Worker 是否能够处理积压事件。
Failure Testing

主动模拟：
- Provider Timeout。
- Provider 429。
- Provider 500。
- Redis unavailable。
- PostgreSQL unavailable。
- Worker Crash。
- Client Disconnect。
- Duplicate Event。
特别是 Billing，一定要做故障注入测试。

13. 我认为最重要的 7 个 Architecture Decisions
最后把容易影响未来重构成本的决定单独列出来。
决策	我的建议
Monolith vs Microservices	Modular Monolith
Control Plane vs Data Plane	逻辑和部署边界分离
Provider Integration	Adapter Pattern
Routing	Policy + Candidate Filtering + Scoring
Billing	Ledger + Reservation + Settlement
Event Processing	Transactional Outbox + Worker
Multi-region	从数据模型和策略上支持，逐步部署

这里还有两个建议：

第一，不要把 LLM Gateway 和 Agent Runtime 混在一起。

未来你可以扩展 Agent Gateway、MCP Gateway、Agent Observability，但第一版只负责模型调用、路由、计费和治理。

第二，不要让智能路由直接调用 LLM 来决定每一次路由。

第一版采用规则和实时指标就够了。基于机器学习的模型选择应该在积累足够多的真实调用数据后再考虑。
14. 最终建议：第一版到底应该做什么？
如果我是这个项目的技术负责人，我会把 MVP 的范围控制在下面这些能力：
MVP Feature Checklist
Gateway
- [ ] OpenAI-compatible Chat API
- [ ] Streaming / Non-streaming
- [ ] OpenAI / DeepSeek / Anthropic Adapter
- [ ] vLLM Adapter

Identity & Management
- [ ] User / Organization / Team
- [ ] API Key
- [ ] RBAC
- [ ] Rate Limiting

Routing
- [ ] Model Registry
- [ ] Provider Registry
- [ ] Priority Routing
- [ ] Lowest Cost Routing
- [ ] Retry / Fallback

Billing
- [ ] Token Metering
- [ ] Pricing Engine
- [ ] Wallet / Top-up
- [ ] Ledger
- [ ] Usage Dashboard

Operations
- [ ] Request Logs
- [ ] Audit Logs
- [ ] Provider Health
- [ ] Admin Dashboard
- [ ] Financial Reconciliation

暂时不做：
- Semantic Cache。
- AI-based Routing。
- 自建 GPU 集群。
- 完整 Agent Runtime。
- 复杂企业 SSO。
- 多 Region Active-Active。
- 复杂的订阅和分级折扣系统。
这些都可以在验证商业模式后逐步增加。
推荐优先阅读的技术资料
项目	重点研究内容	文档
OpenRouter	API、模型、路由	Documentation
LiteLLM	Proxy、Virtual Keys、Billing	Architecture
vLLM	自建推理服务	Serving
OpenTelemetry	Tracing 和 Metrics	Python Docs


15. 下一步：我建议先完成三个核心设计文档
整个项目最容易出问题的不是 FastAPI 怎么写，而是三个领域的设计：
1. Request Lifecycle & Routing Design：保证不同 Provider 的调用、切换、流式处理和故障恢复正确。
2. Billing & Ledger Design：保证费用准确、并发安全、可追溯、可对账。
3. Tenant & Security Design：保证用户、组织、Key、权限和跨 Region 数据隔离。
我的开发优先级是：

最高优先级
 Billing Consistency

最高优先级
 Provider Adapter Abstraction

最高优先级
 Request Lifecycle
一个最终的架构判断： 这个项目真正值得投入精力的不是做出一个可以调用 100 个模型的 API，而是建立一个能够准确控制成本、稳定调度 Provider、保证企业数据安全的 AI Infrastructure Platform。

另外，后续可以每周跟踪主要 Provider 的 API、模型价格、调用限制和协议变化，及时更新你的 Model Registry 和 Adapter 设计。
🔎每周追踪 AI Provider 技术与价格变化Tap to set up