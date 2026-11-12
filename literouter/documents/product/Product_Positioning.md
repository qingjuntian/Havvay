# 产品定位：统一 LLM 网关与智能 AI 基础设施平台

**来源：** 提取自 `documents/DesignDiscussion/Architecture_design.md` §1
**状态：** 产品定位参考文档
**日期：** 2026-11-12

---

## 产品定位

**Unified LLM Gateway & Intelligent AI Infrastructure Platform**

既是一个面向开发者的模型聚合平台，也是一个面向企业的 LLM Gateway，同时提供智能路由、成本管理和模型基础设施服务。

## 三个业务支柱

### Pillar A — Model Aggregation

统一接入 OpenAI、Anthropic、Google、DeepSeek、云平台和自建模型。

**解决：** 模型分散、接口不统一、Provider 接入成本高。

### Pillar B — Intelligent Routing

根据成本、延迟、质量、可用性和用户策略选择模型及 Provider。

**解决：** 成本高、供应商不稳定、模型选择困难。

### Pillar C — Enterprise Gateway

提供认证、权限、预算、计费、审计、可观测性和企业策略。

**解决：** 企业使用 AI 模型时的治理和成本控制问题。

## 五个必须坚持的架构原则

1. **OpenAI Compatibility First**：先做好兼容接口，不要让用户学习新 API。
2. **Provider Agnostic**：业务层不能直接依赖 OpenAI、Anthropic 等 SDK。
3. **Financial Correctness**：用量和财务账本必须可追溯、可对账。
4. **Policy Before Routing**：先检查权限、预算和数据策略，再决定路由。
5. **Observable by Design**：每一次请求、每一次 Provider Attempt 都有统一 Trace ID。

**额外要求：** 因为目标市场是中国和海外，必须把 Region、数据驻留、Provider 合规资格、跨境数据流动和供应商转售授权作为一等设计对象，而不是上线后再补。

---

**相关文档：**
- 技术实现规范见 `documents/design/Doc_01_Request_Lifecycle_Intelligent_Routin.md`
- 计费与账本设计见 `documents/design/Doc_02_Billing_Ledger_Design.md`
- 跨文档契约见 `documents/design/Doc_03_Cross_Document_Architecture_Contract.md`
- 长任务路由见 `documents/design/Doc_04_Intelligent_Routing_for_Long_running_Coding_Workloads.md`
