# 统一模型网关平台设计方案（SaaS 优先，兼顾企业自托管）

## 1. 项目背景

随着大模型生态快速演进，企业和开发者面临两个关键问题：

1. 不同模型提供商的 API 形式、定价、能力和稳定性差异较大；
2. 企业希望通过统一接口接入不同模型，并统一管理鉴权、成本、审计和使用控制。

因此，构建一个“统一模型网关平台”非常有价值：

- 对上层业务提供统一 API
- 对底层多个模型提供商提供适配能力
- 对租户、调用、预算和审计进行集中管理
- 为后续企业级 AI 能力扩展（如知识库、Agent、RAG 等）预留空间

该平台目标为 SaaS 优先，同时保留企业自托管能力，以支持后续自建部署需求。

---

## 2. 业务目标

### 2.1 核心目标

- 统一模型访问：通过单一 API 接入 OpenAI、Moonshot、Anthropic、Azure 等模型服务
- 多租户能力：按租户进行隔离、API Key 管理、调用控制
- 成本控制：支持请求前成本估算、预算控制、Spending Alert
- 审计能力：记录每次调用的请求元数据、模型信息、token、成本、状态和响应时间
- 运行稳定性：支持重试、熔断、降级和 provider fallback
- 后续扩展：为知识库、RAG、Agent 能力预留扩展空间

### 2.2 非功能需求

- 高可用：网关层需具备无状态扩展能力
- 可观测：需要监控、链路追踪和告警
- 安全：密钥管理、访问控制、审计日志和数据最小化
- 合规：支持租户级数据驻留与审计策略
- 可扩展：适配器层必须允许快速增减 provider

---

## 3. 产品定位

该平台不等同于某个具体模型提供商，也不是单纯的 SDK 封装，而是一个“统一模型入口层”：

- 面向应用开发者：提供统一接口
- 面向企业：提供租户管理、API Key、成本控制和审计
- 面向平台运营：提供路由策略、预算策略和指标监控
- 面向后续产品：为知识库和 Agent 能力打基础

---

## 4. 业务场景

### 4.1 场景一：统一模型调用

应用开发者不再依赖不同厂商 SDK，而是统一调用平台的 API：

- /v1/chat
- /v1/completions
- /v1/embeddings
- /v1/models

平台内部决定走哪个 provider，每个 provider 通过 adapter 统一接入。

### 4.2 场景二：多租户 API 管理

- 一个租户对应一个或多个 API Key
- 不同租户调用不同模型授权范围
- 按租户限流、配额和预算

### 4.3 场景三：模型平台运营

- 监控 provider 成功率、延迟和成本
- 按模型、租户、调用量进行统计
- 在成本过高时进行降级或报警

### 4.4 场景四：企业级治理

- 权限分层
- 审计日志留痕
- 租户白名单/黑名单
- BYOK（Bring Your Own Key）
- 人员和敏感访问监控

---

## 5. 总体架构

### 5.1 逻辑架构

- API Gateway：统一对外暴露接口
- Auth & Tenant Layer：鉴权、授权、限流、配额
- Routing Engine：根据租户策略选择 provider / model
- Provider Adapter Layer：统一对接各模型提供商
- Usage & Billing Layer：统计使用量、成本和计费
- Audit & Metrics Layer：日志、监控、告警、审计
- Secret Management：密钥与配置管理
- Deployment Layer：实现 SaaS / self-hosted 两种部署模式

### 5.2 核心数据流

1. 客户端携带 API Key 请求网关
2. 网关校验租户与权限
3. 路由引擎根据策略选择 provider 和 model
4. 成本估算器评估本次调用预估成本
5. 适配器发起实际调用
6. 返回响应并记录：token、延迟、成本、状态
7. 写入使用数据和审计日志

---

## 6. 组件设计

### 6.1 API Gateway

职责：

- 提供统一 API 接口
- 执行请求体校验
- 对租户、key、模型、限流和配额执行控制
- 转发给内部路由器和 provider adapter

推荐接口：

- /v1/chat
- /v1/completions
- /v1/embeddings
- /v1/models
- /v1/keys
- /v1/usage

接口风格：

- 兼容 OpenAI API Request / Response 格式，以降低业务侧迁移成本
- 支持流式响应

### 6.2 Auth / Tenant / Quota Layer

职责：

- 认证客户端身份
- 根据租户绑定 provider 与 allowed models
- 限流和配额管理
- 支持组织级和用户级访问控制

典型数据：

- tenant
- tenant_key
- provider_binding
- quota_policy
- access_policy

### 6.3 Routing Engine

职责：

- 根据 model_hint、tenant policy、provider health、成本和延迟做选择
- 实现 fallback / retry / degrade
- 支持按成本、延迟、地域或能力所需策略

示例策略：

- 如果某 provider 超时，则回退至更稳的 provider
- 如果某租户设置了“成本优先”，则优先低价模型
- 如果访问是批量任务，则可走更稳定但不一定最优的模型

### 6.4 Provider Adapter Layer

职责：

- 对接不同模型提供商
- 规范请求参数和响应字段
- 统一错误类型
- 统一调用成本和 token 统计

适配器接口建议：

- health_check()
- chat()
- completion()
- embeddings()
- stream_chat()
- estimate_cost()

适配器必须统一输出结构：

- provider
- model
- request_id
- usage
- latency_ms
- error_code

### 6.5 Usage & Billing Layer

职责：

- 记录每次调用的 token / cost / latency / status
- 汇总租户、provider、model 的用量
- 支持按月、按天、按应用统计
- 支持预算限制和预警

典型字段：

- tenant_id
- request_id
- provider
- model
- input_tokens
- output_tokens
- estimated_cost
- actual_cost
- status
- created_at

### 6.6 Audit & Observability Layer

职责：

- 保存请求审计日志和配置变更日志
- 记录 provider 调用状态和链路追踪
- 通过 metrics 和 alert 发现问题

建议监控指标：

- request rate
- success rate
- latency
- token consumption
- estimated_cost
- fallback rate
- queue depth

### 6.7 Secret Management

职责：

- 管理租户自己的 provider key
- 管理平台级 secret
- 支持 key rotation
- 支持审计追踪

推荐方案：

- 云 KMS：AWS / Alibaba / GCP / Azure
- 或 HashiCorp Vault（如对企业部署更重视）

---

## 7. 数据模型设计（摘要）

### 7.1 事务型核心表

- tenants
- tenant_keys
- provider_bindings
- models
- requests
- request_usage
- billing_records
- quota_policies
- audit_logs

### 7.2 关键字段说明

- tenants：租户信息、配置、计费策略
- tenant_keys：API Key 及其 hash / 批次信息
- provider_bindings：租户可访问的 provider、模型和授权规则
- requests：每次调用记录主表
- request_usage：token、成本、状态等结构化结果
- billing_records：按月或按租户的计费数据
- quota_policies：配额、限流和预算策略

---

## 8. 安全设计

### 8.1 认证与授权

- API Key 或 JWT 认证
- 按租户、用户和应用维度做权限隔离
- 支持 admin / support / developer / viewer 等角色

### 8.2 密钥管理

- API Key 不明文存储
- provider key 加密存储
- 支持旋转和撤销
- 支持每个租户独立管理 provider account

### 8.3 数据安全

- TLS 全链路加密
- 服务间 mTLS（可选）
- 日志中避免直接留存敏感 Prompt/Response 内容
- 企业版支持数据驻留和存储分区

### 8.4 审计与合规

- 记录请求元数据和关键状态
- 提供可导出日志
- 支持企业客户的审计要求

---

## 9. FinOps / 成本控制设计

### 9.1 需求

- 成本透明：每次调用可测量成本
- 成本可控：支持预算阈值、超额报警
- 成本优化：在满足质量需求下优先选择低成本 provider/model

### 9.2 实现方式

- 请求前估算：根据输入长度和模型定价估算 cost
- 提前阻断：超过预算则拒绝或转向更便宜模型
- 实时观察：按 provider / model / tenant 统计支出
- 曝光和报表：形成 cost dashboard 和月度账单

---

## 10. 可靠性设计

### 10.1 失败处理

- retry（指数退避）
- fallback（切到另一个 provider）
- circuit breaker（防止雪崩）
- timeout 和 rate limit 处理

### 10.2 扩展性

- 网关层无状态，可横向扩展
- adapter 层独立部署可升级
- 可将 queue 和 worker 解耦异步处理任务

---

## 11. 技术选型与许可证考虑

### 11.1 推荐技术栈

- 后端：FastAPI（MIT）或 Go
- API 兼容：OpenAI 兼容接口格式
- 数据库：PostgreSQL（PostgreSQL License）
- 缓存/限流：Redis（BSD-style）
- 队列：Kafka（Apache 2.0）或 RabbitMQ（MPL）
- 监控：Prometheus + OpenTelemetry
- 部署：Docker + Kubernetes + Helm
- 密钥：云 KMS 或 Vault

### 11.2 许可证风险控制原则

优先选择：

- Apache 2.0
- MIT
- BSD
- PostgreSQL License

尽量避免：

- AGPL
- GPL
- SSPL

原因：

- 这类许可证在 SaaS 场景下可能带来源码公开风险，尤其是当平台直接嵌入核心业务代码时
- 对于客户与企业部署来说，商用友好度更差

建议：

- 把 Grafana / Elastic 等更复杂许可证组件作为独立运维工具使用
- 避免将 AGPL 组件直接作为平台核心业务代码的一部分

---

## 12. 项目实施路径

### Phase 0：MVP（建议 2 个月）

核心目标：

- 统一 API 网关
- 租户认证与 key 管理
- provider adapter（至少 OpenAI + Moonshot）
- 简单路由和 fallback
- request logging 和 budget 报表

输出：

- 可演示的统一模型 API
- 可运行的路由与调用链
- 可展示租户和用量管理能力

### Phase 1：SaaS 能力增强

- 多租户 dashboard
- quota / rate limit
- billing integration
- usage analytics
- admin portal

### Phase 2：企业版

- 自托管部署
- BYOK
- 部署隔离和高可用
- 更强审计和合规能力

---

## 13. 结论

统一模型网关平台的核心价值在于：

- 将不同模型提供商统一成一个标准接口
- 让企业能统一管控 key、成本、审计和使用权限
- 为后续企业 AI 助手和知识库能力形成良好的技术基座

从工程实现看，最稳妥的路线是：

- 先做统一网关与 provider adapter
- 再在需要时扩展知识库和 RAG 能力
- 选型以 Apache/MIT/BSD/PostgreSQL 等商用友好许可证为主，避免 AGPL 等高风险组件

这样的方案既保留了快速迭代的优势，也能在后续升级时自然扩展到更强的 AI 平台能力。
