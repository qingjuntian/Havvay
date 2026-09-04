# 统一模型路由平台（类似 OpenRouter）的高层设计

> 本文档为一个以 SaaS 为优先、同时支持自托管的统一模型接入平台的高层设计说明，覆盖架构、核心组件、数据流、适配器契约、FinOps（费用管理）、安全、审计、扩展性与分阶段路线图。

## 1. 目标与非功能性需求

- 统一 API：为客户端提供单一、稳定的接口以访问多家模型提供方（OpenAI、Moonshot、Anthropic、Azure、Google、本地 LLM 等）。
- 提供可插拔的 provider-adapter，实现运行时模型选择、降级与重试策略。
- 多租户 SaaS（优先）与自托管选项：按租户隔离配额、计费与审计。
- FinOps：请求前成本预估、预算管控、成本归因与报表。
- 可审计性与合规：不可变的请求日志，支持导出与审计保留策略。
- 安全与隐私：密钥加密存储、BYOK（客户自带密钥）、数据驻留控制。
- 低延迟与可扩展：支持流式响应、自动扩缩、后压控制。

## 2. 核心组件（逻辑）

- 公共 API 网关
  - 暴露 REST（/v1/chat、/v1/completions、/v1/embeddings）与流式（SSE / WebSocket）接口。
  - 身份认证（租户 API Key、OAuth2、JWT）、限流、配额检查、使用计量埋点。

- 路由与策略引擎
  - 将（租户、model_hint、策略）映射为 provider adapter 与具体模型。
  - 策略示例：按成本、延迟、能力、地域、A/B 测试等路由。

- Provider Adapter 层（可插拔）
  - 统一适配不同厂商 API：聊天、补全、嵌入、流式等。
  - 负责厂商鉴权、重试、错误转换、限速。适配器实现小型统一接口。

- 成本估算 / FinOps 引擎
  - 基于 tokenizer 预估 token 数，结合模型价格进行请求前成本估算。
  - 支持预算策略（阻断、降级、报警）。

- 密钥管理 / Secrets Vault
  - 加密存储租户的第三方 provider key 或客户自带密钥（KMS/HSM）。
  - 支持密钥轮换、权限审计、按租户绑定 provider。

- 审计与日志
  - 不可变的追加式事件日志（可导出到 S3 / Parquet），默认不保留敏感正文（可租户开启）。

- 使用与计费存储
  - 用于聚合用量、成本计算与计费报表（可用 ClickHouse / Timescale / PostgreSQL + OLAP）。

- 管理与客户门户
  - 租户注册、API Key 管理、配额/策略控制、使用与费用仪表盘。

- Worker / 编排层
  - 处理批量任务或耗时任务（消息队列、重试、断路器）。

- 可观测性
  - 指标（Prometheus）、链路追踪（OpenTelemetry + Jaeger）、日志（ELK / Loki）。

- 自托管打包
  - 提供 Helm chart / Terraform 模块，或提供 Docker Compose 的 POC 配置。

## 3. 典型请求流程

1. 客户端调用 `/v1/chat`（包含租户 API Key）。
2. 网关鉴权、限流、配额检查并记录请求开始事件。
3. 路由引擎根据租户策略、model_hint 与预算选择 provider + model。
4. 成本估算器预估此次调用成本；若预算不足则按策略阻断或降级路由。
5. 调用 provider adapter（支持同步或流式）；adapter 负责厂商特性封装。
6. 响应返回后，记录使用量、账单事件、审计条目并更新指标。
7. 若 provider 出错或超时，路由器可触发回退策略（如换更廉价模型或另一个 provider）。

## 4. Provider Adapter 契约（最小）

- 必要调用：embed(texts), chat(messages, options), completion(prompt, options), health_check()
- 流式支持：adapter 提供异步可迭代（async iterator）以逐 token/段返回事件。
- 元数据归一化：adapter 返回统一结构 { request_id, model, provider, usage: {tokens,...}, latency_ms }
- 错误规范化：平台错误码（TEMPORARY/RETRYABLE、PERMANENT、RATE_LIMIT）

示意接口（Python）：

class Adapter:
    async def health_check(self) -> Health
    async def embed(self, texts: List[str]) -> List[List[float]]
    async def chat(self, messages, stream=False, **opts) -> ChatResponse | AsyncIterator[TokenEvent]
    def estimate_cost(self, request_spec) -> float

## 5. 数据模型（概要）

- tenants(id, name, billing_profile_id, default_policy, created_at)
- tenant_keys(tenant_id, key_id, hashed_key, created_at, revoked, metadata)
- provider_bindings(tenant_id, provider, provider_key_ref, allowed_models, priority)
- requests(id, tenant_id, endpoint, model_hint, provider, model, request_tokens, response_tokens, estimated_cost, actual_cost, status, created_at)
- audit_events(request_id, event_type, timestamp, metadata)
- billing_usages(tenant_id, period, provider, model, tokens, cost)

## 6. FinOps 与预算管理

- 建立模型价格表（cost per token），并支持按签约动态定价。
- 请求前通过 tokenizer 估算 token 数并结合模型价格得到预估费用。
- 预算执行模式：阻断（block）、降级（fallback 到更便宜模型）、报警（notify but allow）。
- 提供报表：按租户/应用/模型的成本归因、趋势与预测。

## 7. 安全、密钥与隐私

- 客户端 API Key：随机密钥存储哈希（类似 Stripe），或签名 JWT。
- Provider Key：加密存储（Cloud KMS / Vault），支持 BYOK。
- 传输加密：TLS；服务间 mTLS（可选）。
- 存储加密：数据库与对象存储加密。
- 日志/审计的敏感数据处理：默认不存储完整 Prompt/Response，需租户明确许可或开启调试模式。
- RBAC：管理台与支持人员访问受限并记录审计。

## 8. 审计与合规

- 不可变追加的审计日志（支持导出 & legal hold）。
- 数据驻留与分区：允许按地域部署或为特定租户指定存储位置。
- 合规模板：SOC2/HIPAA/GDPR 操作清单（数据删除、访客权利、审计追踪）。

## 9. 可观测性与 SLO

- 指标：请求率、成功率、每-provider & model 的延迟、队列深度、成本速率。
- 分布式追踪：完整请求链路的 trace，方便定位 provider 延迟或错误。
- 仪表盘与告警：消费突增、成本异常、配额耗尽。

## 10. 可扩展性与可靠性模式

- 网关：无状态、水平扩展。
- Adapter：维护 provider 连接池，按 provider 实施断路器与指数退避。
- 队列：使用 Kafka/RabbitMQ/SQS 处理批量/异步任务。
- 缓存：嵌入向量缓存、prompt-result 缓存以减少重复调用成本。
- 租户分片：为大客户做数据/计算分片。
- 自动扩缩：基于队列深度或 CPU/延迟指标自动扩展 worker。

## 11. 自托管注意点

- 提供 Helm chart、Terraform 模块与部署文档；支持在客户 VPC 本地部署。
- 强烈建议企业客户使用 BYOK、局部存储及本地化审计配置。
- 提供可选的 SaaS 管理模式（置于边界：遥测/更新可选启用）。

## 12. 技术选型建议（MVP，兼顾商用友好与 license 风险）

### 12.1 推荐技术栈（可商用、风险较低）

- 服务端与适配器：Python + FastAPI（MIT），快速适配 LLM 工具链；Go 也可用于高吞吐路由层
  - 优点：开发速度快、生态成熟、对于 OpenAI/Anthropic/Moonshot 等 SDK 兼容性好
  - 适合初期产品快速验证与迭代
- API 兼容层：保持对 OpenAI 兼容接口格式，减少下游客户端改造成本
- Worker：Celery / RQ / Go workers，消息队列 RabbitMQ / Kafka
  - RabbitMQ（MPL）或 Kafka（Apache 2.0）均可商用；Kafka 更适合大规模事件流
- 事务 DB：PostgreSQL（PostgreSQL License）
  - 适合用于 tenants、key、usage、audit、billing 等高一致性数据
- 分析/FinOps 存储：ClickHouse（Apache 2.0）或 BigQuery
  - 若普通 MVP 以成本优先，可先用 PostgreSQL + 轻量 OLAP 方案，再升级
- 缓存：Redis（BSD 风格）
  - 做限流、token bucket、热点缓存、短期结果缓存
- 秘钥：HashiCorp Vault（MPL）或云 KMS（AWS KMS / Alibaba Cloud KMS / GCP KMS / Azure Key Vault）
  - 对 SaaS 优先路线，托管云 KMS 往往更省心，也更容易做审计
- 向量 DB（如需内置 Embedding 检索服务）：Qdrant（Apache 2.0）
- 部署：Docker + Kubernetes + Helm
  - Docker Compose 可用于本地和演示环境；Kubernetes 适合生产落地
- 监控：Prometheus + OpenTelemetry + Loki / 自研日志中心
- 计费：Stripe（适合 SaaS 用户结算）或企业内部账单系统

### 12.2 License 选型原则（非常重要）

如果目标是规避 license 风险，建议遵循以下标准：

- 优先选择：Apache 2.0、MIT、BSD、PostgreSQL License
- 通常可商用但需注意：MPL（例如 RabbitMQ、Vault），仍可商用，但要适当做 license review
- 尽量避免：AGPL、GPL、SSPL
  - AGPL 在 SaaS 场景下可能带来源码披露风险
  - SSPL 在很多企业客户里不被接受

常见坑：
- Grafana OSS 使用 AGPL；如果直接嵌入你的 SaaS 核心能力，可能带来源代码公开风险
- Elasticsearch/Kibana 这类历史上许可较复杂的组件，适合在法务审查前谨慎使用

因此，如果你要把平台做成真正的商用 SaaS，建议采用：
- FastAPI + PostgreSQL + Redis + Kafka/RabbitMQ + Qdrant + Prometheus + OpenTelemetry
- 把 Grafana、Elastic 等组件作为独立运维工具，而不是直接嵌入产品核心逻辑中

### 12.3 一套“低风险”真实落地方案

对于中国团队做 MVP，建议优先组合：

- 后端：FastAPI（MIT）
- 接口兼容：OpenAI API 兼容层
- 租户数据：PostgreSQL（PostgreSQL License）
- 限流/缓存：Redis（BSD）
- 事件/任务：Kafka（Apache 2.0）或 RabbitMQ（MPL）
- 向量/检索（如果后续需要）：Qdrant（Apache 2.0）
- 监控：Prometheus（Apache 2.0）+ OpenTelemetry（Apache 2.0）
- 日志：Loki / 自研日志中心，避免 AGPL 相关风险
- 密钥：云 KMS（阿里云 / AWS / GCP / Azure）

这样做的好处是：
- 组件成熟、开发效率高
- 商用风险较低
- 可以快速进入 MVP 阶段，不需要在开源协议上花太多时间

## 13. 中国市场主流类似产品简要总结

> 说明：这里列出的是“与统一模型调用/网关/多模型路由方向相近”的产品，目的不是对其保守估值，而是帮助判断市场格局和定位差异。

| 产品/平台 | 主要定位 | 典型特点 | 适合的用户场景 | 备注 |
|---|---|---|---|---|
| OpenRouter | 全球统一模型入口 | 模型聚合、统一 API、provider 适配、成本和路由能力较成熟 | 需要跨模型统一调用的开发者和 SaaS 场景 | 最接近“标准做法”，但本身不是中国专属市场 |
| SiliconFlow | 中国市场大模型平台 / API 集成 | 对中文场景、国内用户更友好，接口较适合国内开发者 | 国内应用、低延迟、较强中文模型场景 | 对中国开发者来说很有竞争力 |
| Moonshot / Kimi | 模型平台 + AI 能力集成 | 强中文体验，模型和 API 生态成熟 | 中文应用、企业内部大模型接入 | 更偏“单一品牌平台”，不完全是统一路由平台 |
| One API / Open Source Gateway | 开源统一模型网关 | 轻量、低门槛、适合做原型和自托管网关 | 技术团队快速验收和内部统一接入 | 更偏 DIY / 开源中间层，企业级能力层次较弱 |
| 阿里云百炼 / 火山模型服务 / 其他国内云服务 | 云厂商模型服务 | 模型生态强、云服务整合强 | 已有云上部署和企业基础设施的用户 | 更偏“云平台服务”，不是纯 OpenRouter 型架构 |

简要判断：
- 中国市场上，最接近“统一模型路由平台”核心思路的，大多是 OpenRouter 这种全局统一入口 + 部分国内平台的 API 聚合能力。
- 但多数国内平台更偏“平台服务”或“模型分发”，而不是完全按租户、API Key、预算、透明路由、审计治理的 SaaS 化思路来做。
- 这也说明：如果你们把“统一模型层 + 多租户 + 成本控制 + 审计治理”做扎实，产品差异化空间仍然存在。

## 14. MVP 范围与分阶段路线图（推荐）

- Phase 0（1–2 个月）：设计与原型
  - OpenAPI 规格、简单 FastAPI 网关
  - Provider Adapter：OpenAI 与 Moonshot（最小实现）
  - 租户鉴权、简单请求日志
  - 基础路由（租户默认 provider）与指标埋点

- Phase 1（2–3 个月）：SaaS MVP
  - 使用计量、成本预估、预算控制
  - 管理台（钥匙、使用仪表盘）
  - 计费接入（Stripe）与导出账单事件
  - 基本审计日志导出

- Phase 2（2–3 个月）：强化与功能扩展
  - 配额/限速、重试、断路器、全链路流式支持
  - 高级路由策略、动态模型选择
  - 完整可观测性（Tracing + Alerts）

- Phase 3：自托管发行
  - Helm charts、BYOK、地区驻留支持
  - 企业级 SLA 与上门支持流程

- Phase 4：FinOps 与分析
  - 详细成本分析（ClickHouse），按租户与应用的成本驱动分析
  - 自动化建议（何时使用更便宜模型）

## 14. 风险与缓解

- Provider API 频繁变化：使用适配器层并对每个适配器添加契约测试。
- 费用暴涨：请求前成本预估 + 软/硬预算上限。
- 数据泄露/合规风险：默认最小化日志，启用加密与 RBAC，提供数据删除流程。
- 延迟问题：异步流式、回退策略与按 provider 的延迟监控并路由到低延迟选项。

## 15. 可交付工件与下步建议（选一）
- OpenAPI v3 规范（/v1/chat, /v1/embeddings, /v1/models, /v1/keys, /v1/usage）
- Provider adapter 脚手架与 OpenAI/Moonshot 示例适配器（含流式）
- DB 模式與迁移脚本（tenants, keys, requests, usage）
- Helm chart 骨架（自托管）
- 成本估算微服务原型（tokenizer + 定价表）
- 参考仓库样例（FastAPI + adapter + 简单 UI + CI）

