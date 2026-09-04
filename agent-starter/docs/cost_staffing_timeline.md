# 成本、人员与工时估算（统一模型路由平台 / OpenRouter 类产品）

> 目标：为一套以 SaaS 为优先、兼容自托管的统一模型访问平台做更现实的预算、人员配置和工期估算。本文档基于 MVP / Phase 0 的范围：统一 API、Provider Adapter、基础路由、租户鉴权、日志、基础成本管理。

## 1. 先给结论

如果目标是在 1-2 个月内交付 MVP（Phase 0），最现实的团队规模是 3–4 人全职，而不是一开始就招 8–10 人。


- 3–4 人全职
- 1 名 Tech Lead / Senior Backend
- 1–2 名 Backend / Adapter Engineer
- 1 名 DevOps / Infra（可兼职）
- 0.2–0.5 PM / 产品协同

2 个月的人力总成本大致为：
- 约 ¥260,000–¥400,000

（不含大规模的推广费用、企业售前、成熟安全审计成本；这些属于后续阶段。）


  - Senior: 30,000–¥45,000 / 月
  - Mid: ¥25,000–¥35,000 / 月
  - DevOps: 20,000–¥30,000 / 月
  - PM: ¥15,000–¥25,000 / 月
  


## 3. 额外基础成本（必须计入预算）

### 3.1 基础 infra / SaaS
- PostgreSQL / Redis / Qdrant / storage：¥1,400–¥10,800 / 月
- Cloud hosting：¥3,600–¥21,600 / 月
- Monitoring / tracing：¥1,400–¥10,800 / 月
- CI / Dev tools：¥720–¥3,600 / 月
- Secrets manager / KMS：¥1,440–¥7,200 / 月
- Stripe / billing / admin：¥360–¥3,600 / 月

通常，MVP 阶段的 infra 预算会落在：
- ¥7,200–¥36,000 / 月

### 3.2 LLM 成本
- 低流量 demo：¥720–¥14,400 / 月
- 中等流量：¥14,400–¥72,000 / 月
- 高流量：¥72,000+ / 月

对早期产品来说，LLM 费用通常不是最大成本；最大成本依然是人力。

## 4. 推荐预算（按地区分）

### 

## 5. 人员职责拆分

### 5.1 Tech Lead / Architect（0.6–1.0 FTE）
- API 设计与版本控制
- Provider adapter contract
- 路由逻辑、策略设计
- 安全/审计设计
- code review / 质量门禁

### 5.2 Backend Engineer（1–2 FTE）
- FastAPI 网关
- 租户鉴权与 API Key
- request logging / usage metering
- cost estimation & budget logic
- 路由策略实现

### 5.3 Adapter Engineer（1 FTE）
- OpenAI adapter
- Moonshot adapter
- retry / backoff / circuit breaker
- error normalization
- streaming implementation

### 5.4 DevOps / SRE（0.5–1 FTE）
- Docker / K8s / Helm
- CI/CD
- monitoring, tracing, alerts
- deployment automation

### 5.5 PM / Product（0.2–0.5 FTE）
- 验收标准
- 接口定义与优先级
- 演示脚本与交付材料

### 5.6 QA / 测试（0.2–0.5 FTE，按需）
- contract tests
- retrier / fallback tests
- integration tests

## 6. 工时估算（推荐方案）

### 6.1 以 4 人团队为例

#### Week 1：准备与设计
- 确认范围、验收标准、API 优先级
- 定义 adapter contract
- 确认 provider 列表（OpenAI / Moonshot）
- 设计数据库 schema
- 预计工作量：1–1.5 人周

#### Week 2–3：网关与路由骨架
- FastAPI 网关搭建
- API key 认证和租户校验
- 基础限流、请求日志
- 路由器框架
- 预计工作量：2–3 人周

#### Week 4：Provider Adapter
- OpenAI adapter
- Moonshot adapter
- retry / error normalization
- streaming / response format normalization
- 预计工作量：2–3 人周

#### Week 5：成本估算 + 预算策略
- token estimation
- pricing table
- budget policy
- fallback routing
- 预计工作量：1–2 人周

#### Week 6：硬化与交付
- 集成测试
- 部署脚本
- docs + demo
- 修复 bug
- 预计工作量：1–2 人周

总计约：8–12 人周

### 6.2 一个简单总结
4 人全职：大约 2 个月内能交付更完整 MVP


## 7. 风险与缓解

### 7.1 人员不足 / 单点依赖
解决方式：
- 关键角色必须存在 senior 能力
- 编写适配器和路由的设计文档
- 把 API contract 固化为测试和 OpenAPI 文件

### 7.2 需求蔓延
解决方式：
- 先锁定 Phase 0 范围
- 不在最早阶段做复杂 portal / billing / enterprise features

### 7.3 成本失控
解决方式：
- 请求前预估成本
- 默认启用 per-tenant budget cap
- provider fallback 需要有明确策略

## 8. 实际建议

基于你目前的目标，我的建议是：
- 优先做 3 人团队（APAC / EU / US 的差异取决于你们的预算）
- 1 个月的预算很紧，2 个月更稳妥
- 先交付 Phase 0，可演示功能如下：
  - /v1/chat
  - /v1/embeddings
  - /v1/models
  - tenant API key
  - basic model routing
  - request logging
  - cost estimation
  - provider fallback

这样在 1–2 个月内可以有一个可演示、可扩展的基础平台，不会在起步阶段把资源烧掉。

## 9. 结论

如果你要做一个“像 OpenRouter 一样的统一模型路由平台”，最现实的初期投入是：

- 3–4 人团队
- 1–2 个月
- 预算：
  - APAC：$30k–$50k
  - EU：$60k–$100k
  - US：$120k–$170k

其中最大的成本不是云，而是人力；而最合理的价值交付，是先做 MVP，不急着做大而全。

---

如果你愿意，我下一步可以继续把这份文档进一步整理成：
- 适合汇报给老板/投资人版（更短更精悍）
- 适合给工程团队执行版（按任务/时间表）
- 适合做预算申请版（ROI / 成本 / 人员预算表）
