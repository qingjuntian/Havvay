# MVP Roadmap：从 0 到商业化

**来源：** 提取自 `documents/DesignDiscussion/Architecture_design.md` §11
**状态：** 项目计划参考文档， 不是真正的roadmap
**日期：** 2026-11-12

---

## 12 周规划

**假设：** 一位主要后端工程师，能够投入一定的前端和 DevOps 资源；如果完全一个人开发，时间需要拉长。

### Phase 0：Architecture & Foundation（Week 1）

**目标：** 先建立统一的架构基础。

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

**交付物：**
```
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
```

### Phase 1：Core Gateway（Week 2–3）

**目标：** 用户可以真正调用不同的模型。

- OpenAI-compatible API。
- Provider Adapter（OpenAI、DeepSeek、vLLM/OpenAI-compatible）。
- Model Registry。
- Provider Registry。
- Streaming。
- Timeout。
- Retry。
- Request ID。

**验收标准：** 同一个 API Endpoint 可以通过不同 Model ID 调用至少三个不同 Provider，并正确返回 Streaming 和 Non-streaming 响应。

### Phase 2：Identity & Management（Week 4）

**目标：** 用户可以注册、创建 Key 和管理组织。

- User Registration / Login。
- Organization。
- Team。
- Membership。
- API Key Management。
- API Key Hash Verification。
- RBAC。
- Rate Limiting。
- Model Access Control。

**验收：** User Registration → Create Organization → Create API Key → Call LLM API → Access Control Verified

### Phase 3：Intelligent Routing（Week 5–6）

**目标：** 实现多个 Provider 之间的智能选择。

- Deployment Registry。
- Capability Filtering。
- Priority Routing。
- Lowest Cost Routing。
- Weighted Routing。
- Provider Health Check。
- Circuit Breaker。
- Retry / Fallback。
- Routing Decision Log。

**验收：** 同一个 Logical Model 对应多个 Deployments，可以根据用户策略选择 Provider；Provider 失败时可以安全切换。

### Phase 4：Metering & Billing（Week 7–8）

**商业化关键阶段**

**目标：** 实现完整的收费闭环。

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

**验收：** Customer → Recharge $100 → Call LLM → Actual Cost = $0.02 → Wallet Debit = $0.02 → Ledger Entry Created → Usage Dashboard Updated

**重点测试：** 并发请求、重复事件、失败重试、退款和账单对账。

### Phase 5：Portal & Operations（Week 9–10）

**目标：** 客户可以自助使用平台，管理员可以运营平台。

**Developer Portal：**
- Login / Registration。
- API Key Dashboard。
- Model Catalog。
- Usage Dashboard。
- Request History。
- Wallet / Billing。
- Team Management。

**Admin Dashboard：**
- Provider Management。
- Model Management。
- Pricing Management。
- Routing Policies。
- Customer Management。
- Audit Logs。
- Financial Reports。

### Phase 6：Hardening & Beta Launch（Week 11–12）

**目标：** 从可以运行变成可以商业运营。

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

## MVP 验收指标

| 指标 | MVP 目标建议 |
|---|---|
| Gateway Availability | 99.9% |
| Gateway Internal P95 Latency | 小于 100ms（不含 Provider 推理） |
| Authentication Accuracy | 100% |
| Billing Duplicate Charge | 0 |
| Ledger Reconciliation | 100% |
| Usage Event Loss | 0（最终持久化目标） |
| Provider Fallback | 可正确执行 |
| Tenant Data Isolation | 无越权访问 |
| Request Trace Coverage | 100% |

**注意：** Gateway P95 不包含模型推理延迟，这些是初始目标，不是已经测得的性能承诺。

## 测试要求

### Concurrency Testing

1,000 个并发请求下：
- Redis 限流是否正确。
- Wallet 是否出现超额扣款。
- Provider Quota 是否被正确控制。
- Worker 是否能够处理积压事件。

### Failure Testing

主动模拟：
- Provider Timeout。
- Provider 429。
- Provider 500。
- Redis unavailable。
- PostgreSQL unavailable。
- Worker Crash。
- Client Disconnect。
- Duplicate Event。

**特别是 Billing，一定要做故障注入测试。**

## 最终建议：第一版范围控制

### MVP Feature Checklist

**Gateway**
- [ ] OpenAI-compatible Chat API
- [ ] Streaming / Non-streaming
- [ ] OpenAI / DeepSeek / Anthropic Adapter
- [ ] vLLM Adapter

**Identity & Management**
- [ ] User / Organization / Team
- [ ] API Key
- [ ] RBAC
- [ ] Rate Limiting

**Routing**
- [ ] Model Registry
- [ ] Provider Registry
- [ ] Priority Routing
- [ ] Lowest Cost Routing
- [ ] Retry / Fallback

**Billing**
- [ ] Token Metering
- [ ] Pricing Engine
- [ ] Wallet / Top-up
- [ ] Ledger
- [ ] Usage Dashboard

**Operations**
- [ ] Request Logs
- [ ] Audit Logs
- [ ] Provider Health
- [ ] Admin Dashboard
- [ ] Financial Reconciliation

### 暂时不做

- Semantic Cache。
- AI-based Routing。
- 自建 GPU 集群。
- 完整 Agent Runtime。
- 复杂企业 SSO。
- 多 Region Active-Active。
- 复杂的订阅和分级折扣系统。

这些都可以在验证商业模式后逐步增加。

---

**相关文档：**
- 技术实现规范见 `documents/design/Doc_01_Request_Lifecycle_Intelligent_Routin.md` §17（MVP Implementation Plan）
- 计费发布闸门见 `documents/design/Doc_03_Cross_Document_Architecture_Contract.md` §14（Production Billing Release Gate）
