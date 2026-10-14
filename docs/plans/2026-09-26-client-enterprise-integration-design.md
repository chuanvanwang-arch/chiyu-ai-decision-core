# 客户端—企业平台集成设计（M0' 增量）

> 状态：已批准（P8，2026-09-26）— 契约校验 valid，判别力自证通过
> 日期：2026-09-26
> 依赖决策：用户 2026-09-26 已确认三条（见 §2）
> 上承：`2026-09-25-dsh-client-chiyu-backend-design.md`（M0 客户端总体方案）、`2026-09-25-dsh-client-chiyu-backend-plan.md`（M0-M4 计划）、`2026-09-25-dsh-client-r3-coupling.md`（R3 耦合矩阵）

---

## 0. 目标与范围

**目标**：让 DSH 前端客户端（Electron/桌面，固定 `client_type=desktop`）通过**单一后端入口**与企业平台（chiyu-enterprise）打通——保留 DSH 前端观感（对话/选插件/模型选择），同时**复用企业平台的零信任治理**（token 认租户、读/写分流、写类两阶段 confirm、写闸 G0–G3、反 CRUD 爆炸）。

**范围边界（YAGNI）**：
- 本设计只覆盖 **M0' 接入与最小闭环**，不涉及 M1（插件清单 UI 增强）、M2（agent/workflow 调度 UI）、M3（决策/记忆/库表面板）、M4（Electron 打包）。
- 语音能力按既有决策**暂缓**。
- DSH 前端**构建产物**在本机受阻（依赖下载零进展），因此 M0' 以 **headless 契约验证**先行，不依赖 DSH 前端打包。

---

## 1. 已确认决策（用户 2026-09-26）

| # | 问题 | 决策 |
|---|------|------|
| D1 | 两个 host 是否合一？ | **以企业 host 为唯一入口**；本仓 M0 的 DSH 协议实现下沉为「协议适配层（adapter）」，不再独立起 chiyu-host 服务 |
| D2 | `client_type` 取值 | 固定 **`desktop`**（桌面 Electron 客户端），用于后续按端差异化权益 |
| D3 | DSH session/对话 映射 | **复用内核 `SessionManager`**，经 adapter 暴露为 DSH `session.*` 方法；不翻译为企业 Action |

**派生结论**：客户端只有一个后端（企业 host，默认 `:8000`），DSH 前端基址指向它；DSH 的 `/api/<method>` 与企业的 `/rpc/{tenant}/{client}/action` 同宿主、共用治理中间件。

---

## 2. 现状实勘（信任但验证）

### 2.1 两侧协议对比（实测，非假设）

| 维度 | 企业 host（chiyu-enterprise，`host/app.py`） | 本仓 DSH 协议（chiyu-foundation，`chiyu-host/app.py`，M0-T2） |
|------|----------------------------------------------|--------------------------------------------------------------|
| 入口 | `POST /rpc/{tenant_id}/{client_type}/action` | `POST /api/<method>` |
| 事件流 | `GET /rpc/{tenant_id}/{client_type}/events`（**SSE** `text/event-stream`，推送 `decision` 事件） | `WS /api/events.mux`（**WebSocket**，帧=`ServerRequest`全形+`MuxFrame`） |
| 请求体 | `action`(query) + `payload`(body) | `ClientRequest`全形（`type/rpcId/method/payload`） |
| 响应体 | `{tenant, client_type, action, ok|gate|decision_id}` | `ServerResponse`全形（`type/rpcId/result:{ok,value|error}`） |
| 鉴权 | **Bearer token → 解析 tenant+role**（URL tenant 仅路由提示） | 无 |
| 读/写分流 | 有：`_is_write_action`（guard.mutating 优先，后缀 fallback） | 无（直连内核） |
| 写类治理 | 两阶段 confirm（phase1 发 token / phase2 增补禁覆盖）+ 写闸 G0–G3 | 无 |
| 反 CRUD 爆炸 | 有（`registry.detect_crud_explosion`） | 无 |

### 2.2 关键事实（决定设计必须补的环）

1. **企业 host 当前是治理门面，无 action 执行体**：`rpc_action` 中读类直接返回 `ok:True`、写类 confirm 后返回 `decision_id`，**均未真正执行 action 业务体**；`registry.py` 仅有 `register/audit/guard_of`，**无 `execute` 分发**。场景包 `sales.py` 声明了 `sales.native.*` / `sales.agent.*` / `sales.integration.*` Action，但**暂无 handler 接到执行层**。
2. **本仓 M0-T2 桥接已落地且验证通过**：14 个 DSH 方法 handler 字段对齐 DSH schema，单测 16 passed，实测 RPC 通路真活（session.list/llm.models/skill.list/agentPreset.list 均 200 ok）。
3. **`subagent.list` 在内核无公共 list 接口**，M0-T2 用静态目录兜底；`llm.*` 静态占位 `deepseek-v4-flash`（多 LLM 在 Phase B）。

**结论**：D1「合一」在技术上可行——把本仓 `chiyu-host` 的 14 个 handler 作为 adapter 迁入企业 host，复用其治理中间件；同时需在企业 host 补齐 action 执行分发（§6）。

---

## 3. 集成架构（路线 A + 合一）

```
┌─────────────────────────────────────────────────────────────┐
│ 桌面客户端（DSH 前端观感，Electron，client_type=desktop）      │
│   ui-conversation / ui-model-selection / ui-settings-plugins  │
└───────────────┬─────────────────────────────────────────────┘
                │  POST /api/<method>  (ClientRequest 全形)
                │  WS  /api/events.mux
                │  Authorization: Bearer <token>  ← 含 tenant+role
                ▼
┌─────────────────────────────────────────────────────────────┐
│  企业 host  :8000   （唯一入口，chiyu-enterprise）             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 共享治理中间件（抽出自 app.py，供两路由复用）            │   │
│  │   parse_bearer → resolve_tenant/role                  │   │
│  │   _is_write_action → 读类直连 / 写类 confirm+写闸     │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────┐        ┌──────────────────────────────┐   │
│  │ DSH 适配层    │        │ 企业 Action 路由              │   │
│  │ /api/<method>│        │ /rpc/{t}/{c}/action          │   │
│  │ WS mux       │        │ /rpc/{t}/{c}/events (SSE)    │   │
│  │ (adapter)    │        │                              │   │
│  └──────┬───────┘        └──────────────┬───────────────┘   │
│         │ 14 方法映射                    │ Action FQN        │
│         ▼                                ▼                   │
│  ┌──────────────┐        ┌──────────────────────────────┐   │
│  │ 内核能力       │        │ Action Executor（待补 §6）     │   │
│  │ SessionManager│        │ sales.native.* 等 → handler  │   │
│  │ SkillRegistry │        │                              │   │
│  │ SubagentPool  │        │                              │   │
│  └──────────────┘        └──────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**要点**：
- 客户端**只认一个后端**（`:8000`），DSH `/api/<method>` 与 企业 `/rpc/.../action` 同宿主。
- adapter 与企业 Action 路由**共用同一治理中间件**——DSH 方法不会绕过写闸（消除路线 C 的零信任漏洞）。
- DSH 方法是「内核能力暴露面」，企业 Action 是「业务治理面」，两者并存、互不替换。

---

## 4. 适配层（adapter）契约

### 4.1 路由与线格式
- 新增 `POST /api/<method>`：解析 `ClientRequest` 全形 → 提取 `method`+`payload` → 调治理中间件 → 分发到对应 handler → 返回 `ServerResponse` 全形（`type:'server-response'`, `rpcId`, `result:{ok,value|error}`）。
- 新增 `WS /api/events.mux`：帧为 `ServerRequest` 全形 + `MuxFrame`（`{sessionId, event}`），内部订阅企业 `EventBus` 的决策事件 → 归一推送。
- `rpcId` 透传（DSH 前端据此配对请求/响应）。

### 4.2 14 方法映射表（DSH → 内核/静态）

| DSH method | 映射目标 | 治理 | 备注 |
|------------|----------|------|------|
| `session.list` | `SessionManager.list()` | 读类 | 返回 `items:[{sessionId,updatedAt,running,blank}]` |
| `session.create` | `SessionManager.create()` | 读类（新建会话，非业务写） | 生成 sessionId |
| `session.history` | `SessionManager.history(sid)` | 读类 | 返回消息数组 |
| `session.prompt` | `SessionManager.prompt(sid, text)` | 读类（内核原生对话，D3） | **真执行**内核对话，返回助手消息 |
| `session.cancel` | `SessionManager.cancel(sid)` | 读类 | 取消进行中推理 |
| `llm.providers` | 静态 `["deepseek"]` | 读类 | Phase B 扩多 LLM |
| `llm.models` | 静态 `[{id:"deepseek-v4-flash",...}]` | 读类 | Phase B 接真实 provider |
| `agentPreset.list` | 静态 `MODE_PRESETS`（standard/ptc/minimal/creative） | 读类 | |
| `skill.list` | `SkillRegistry.list()` | 读类 | 内核技能清单 |
| `subagent.list` | 静态目录（兜底） | 读类 | 内核 SubagentPool 无公共 list，待补 |
| `host.describe` | adapter 自述（版本/能力/协议） | 读类 | 客户端启动探测 |
| `event.subscribe` / `event.unsubscribe`（如 DSH 需要） | 注册到 WS mux | 读类 | 会话级事件订阅 |

> 全部 14 方法响应形状**逐字段对齐** DSH `apiproxy/*.schema.ts`（M0-T2 已验证，迁移时携带其对照测试）。

### 4.3 鉴权与 token
- DSH 前端每个 RPC 带 `Authorization: Bearer <token>`；token 形态复用企业 `parse_bearer_token`（含 `tenant`+`role` 段）。
- **M0' 验证期**：用本机单租户 dev token（`t-default-desktop-<id>`，role=`admin`）跑通；生产接真实登录/鉴权模块（不在本范围）。
- `client_type` 固定 `desktop`，由 adapter 路由硬编码或从 token 解析，不做端差异化权益（预留位）。

### 4.4 SSE/WS 归一
- DSH 前端要 WebSocket mux；企业 host 现有 SSE `events`。
- adapter 的 `WS /api/events.mux` 作为「WS 适配壳」：内部订阅企业 `EventBus` 决策事件 + 内核 session 事件 → 转 `MuxFrame` 推给前端。
- 企业原生 SSE `events` 端点保留（供 headless / 监控视图用）。

---

## 5. 企业侧需补齐的环（属「打通」必要项）

1. **治理中间件抽取（T1）**：将 `app.py` 中 `_auth_ctx` / `_is_write_action` / confirm / 写闸调用抽为 `host/middleware.py`（或依赖注入），供 `/api/<method>` 与 `/rpc/.../action` 两路由**同一实例复用**。约束：抽取后既有 enterprise 106 测试 + foundation 测试**不破坏**（回归基线）。
2. **Action Executor（T3）**：补齐 `registry.execute(action_fqn, params, ctx)`（或 `scenario_loader.dispatch`），把 Action FQN 路由到内核对应能力 / 场景包 handler。约束：写类 Action 经 confirm+写闸后**真执行**（返回执行结果，而非仅 `decision_id`）。`sales.native.action_propose` 等需有 handler 落地（哪怕是最小实现）。

> 这两环在 chiyu-enterprise 仓实现，本设计在 chiyu-foundation 侧以「adapter 迁入 + 对照测试」配合。

---

## 6. 落地计划（M0' 增量，含可验证成功标准）

> 简化版「生命契约」：本项目无 CRM agentSpec 注册表，故以**判定式成功标准**承载可监控性。每步一个可验证判据。

| Task | 内容 | 成功标准（判定式） |
|------|------|-------------------|
| **T1** | 企业 host 抽治理中间件，供 adapter 复用 | 抽取后 `pytest enterprise`（106）+ `pytest chiyu_kernel` 全绿；新增单测证明 `/api/<method>` 与 `/rpc/.../action` 调用同一 `_auth_ctx`/`_is_write_action` 实例 |
| **T2** | 企业 host 新增 DSH 适配层（`/api/<method>` + `WS /api/events.mux`），迁入本仓 14 handler | 用 `TestClient` 验证 14 方法返回 `ServerResponse` 全形，字段逐一对齐 DSH schema；`session.prompt` **真执行**内核对话并返回助手消息；`WS mux` 收到 `MuxFrame` |
| **T3** | 补企业 Action Executor，接 `sales.native.*` 等 handler | `/rpc/t/c/action` 写类 Action（如 `sales.integration.erp.sync_order`）经 confirm+写闸后**真执行**并返回执行结果；反 CRUD 爆炸检测仍有效 |
| **T4** | headless 契约验证（绕过 DSH 构建，直接对企业 host 打 RPC/SSE） | headless 脚本：① 14 方法全 200 + 形状对齐；② 1 个写类 Action 全链路（401 无 token → 200 confirm → 400 重复 confirm → 200 执行）；③ WS mux 收到 1 帧；④ 不变异自证（改一处契约字段→测试转红→还原转绿） |

**提交纪律**：每 Task 一 commit；显式 `git add` 单文件/目录；AI 不 commit；chiyu-foundation 与 chiyu-enterprise 分别提交。

---

## 7. 风险与降级

| 风险 | 降级 |
|------|------|
| DSH 前端构建在本机受阻（依赖下载零进展，已三次尝试） | **headless 契约验证先行（T4）**，不经 DSH 打包即可证明后端闭环；DSH 真渲染留待联网环境构建产物回传 |
| adapter 映射表是单点，新增 Action 需同步 | 映射表 + schema 对照测试（T2 携带 M0-T2 的 13 测试），CI 防漂移 |
| 企业 executor 尚未实现，T3 范围可能膨胀 | T3 仅做最小 executor + 1 个 sales Action handler 落地，证明链路；其余 Action handler 后续按需 |
| token 注入依赖 DSH 前端鉴权层 | M0' 用 dev token；生产鉴权模块不在本范围，标注为后续依赖 |

---

## 8. 批准记录（P8，2026-09-26 闸门解除）

```contract-yaml
- task: "M0' 客户端—企业平台集成（本仓 chiyu-host adapter 迁入企业 host + 企业仓治理抽取 + executor）"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-native-action-design, ai-multi-agent-orchestration, ai-context-layering]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "14 类 DSH 方法经企业 host /api/<method> 返回 ServerResponse 全形且字段对齐 DSH schema；写类 Action 经 confirm+写闸后真执行返回 result（非仅 decision_id）；headless 契约验证全绿"
```

本设计经用户 P8 批准（2026-09-26），覆盖 D1/D2/D3 已确认决策，契约校验 `valid:true`、判别力自证通过（错契约键 + 越界 L3/L4 被 exit 1 逐条检出）。批准后进入 writing-plans（计划 `docs/plans/2026-09-26-client-enterprise-integration-plan.md`）并落执行：

1. T1 企业仓抽治理中间件（governance.py）供 adapter 与企业 Action 路由共用；
2. T2 本仓 `chiyu-host` handler 迁入企业 host 适配层（`/api/<method>` + `WS /api/events.mux`）；
3. T3 补 Action executor 使写类 Action 真执行；
4. T4 headless 契约验证（绕过 DSH 构建受阻）。

⛔ 跨仓纪律：设计稿/计划落本仓 `docs/plans`（唯一事实源）；实现跨仓写 `chiyu-enterprise`（D1 授权企业 host 为唯一入口），企业仓本地零 remote、禁 DELETE、显式 `git add`、AI 不 commit。
