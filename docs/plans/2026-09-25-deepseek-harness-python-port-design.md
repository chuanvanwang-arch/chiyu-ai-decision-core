# Deepseek Harness 全量 Python 移植设计

- 日期：2026-09-25
- 状态：已批准（P5 批准闸门通过）
- 形态决策：全量 Python 移植 · 前端 Python 化 · 大模型接本仓 llm/tier
- 关联契约键登记表：`contract/contract-ids.json`（agent = `foundation-builder`，键 `ct-chiyu-foundation`）

## 0. 背景与目标

`deepseek-harness-master`（`dsh`）是 DeepSeek 开源的智能体 harness：TS/Node 单体仓库，Cordis
「everything is a plugin」框架，含完整 Web 前端（`apps/web` Vite SPA @ :3080）与智能体运行时
（session / system-prompt / tools / agent / agent-loop）、LLM（DeepSeek provider）、skill / subagent /
workflow / plan / todo / mcp 等约 40 个包。

本仓 `chiyu-foundation` 是 Python AI 原生基础底座，L0–L3 分层：已有 `llm/tier.py`、

`orchestration/`（agent_registry / dispatch_cfg / state_machine / idem）、`actions/registry.py`、
`context/`（assembly / retrieval / knowledge_needs）、`vector/`、`ontology/`、`contract/`、`evolution/`、
`audit/`，以及 `chiyu-portal` 的 NL→Page Python 渲染器。

目标：把 dsh 的智能体运行时与对话前端用 Python 重写进本仓 L1–L3，使「dsh 式对话页」能直接调用
本仓原生 AI 能力（粒子 / KMD 决策脊柱 / 红线 / 九尺子 / 离线向量），实现无缝集成。

## 1. 集成形态决策（已与用户确认）

| 维度 | 决策 | 理由 |
|---|---|---|
| 总体形态 | 全量 Python 移植 | 目标运行时为 Python；忠实重写 dsh 架构与能力进本仓分层，而非挂第二套插件框架 |
| 前端 | 前端也 Python 化 | 把 dsh 前端架构（对话节点 / session 渲染 / composer / 目标栏）移植进 `chiyu_portal`，用 Python 渲染 HTML；单一 Python 运行时 |
| 大模型 | 接本仓 llm/tier | 大模型走本仓已有 `llm/tier` 抽象（可配多 provider）；dsh 的 DeepSeek provider 仅作参考，不强绑 `DEEPSEEK_API_KEY` |

> 说明：「全量 Python 移植」指**忠实重写 dsh 的架构与能力为 Python**，非原样运行其 TS 代码
> （目标运行时为 Python，且前端/大模型已按上表本地化）。

## 2. 架构映射（dsh 包 → 本仓分层）

| dsh 包 | 本仓落地 | 层 | 备注 |
|---|---|---|---|
| `core/session` | `chiyu_kernel/session/`（新增） | L1 | append-only `SessionEvent` 日志 + 内存态 |
| `core/system-prompt` | `chiyu_kernel/context/assembly.py` 扩展 | L1 | prompt section 与 tool schema 装配 |
| `core/tools` | `chiyu_kernel/actions/registry.py` 扩展 | L1 | 作用域工具注册 + pre/post-execute 守卫管线 |
| `core/agent` + `agent-loop` | `chiyu_kernel/orchestration/` 扩展 | L1/L2 | Agent 接口 + driver + turn/step 流 |
| `llm/llm` | `chiyu_kernel/llm/tier.py` 适配 | L1 | DeepSeek 作一 provider；不强制 |
| `skill/` | `chiyu_kernel/skills/`（新增） | L2 | skill 注册表 + catalog/loader |
| `subagent/` | `chiyu_kernel/orchestration/subagent` | L2 | 委派式子智能体 |
| `plan/` `todo/` `workflow/` | `chiyu_kernel/*`（后续） | L2 | 阶段二 |
| `apps/web` 前端 | `chiyu_portal/renderer.py` 对话页 | L3 | Python 渲染 HTML：session 日志 + composer + 目标栏 |
| `mcp/` `guard/` `fs/` `shell/` `hooks/` `interaction/` | 后续阶段 | L2/L3 | 阶段三 |

## 3. 无缝集成机制（关键）

本仓内核能力（粒子库、KMD 决策脊柱、红线、九尺子、离线向量）以**工具 / 上下文 Provider**
形式注册进移植后的 agent 工具面：agent 运行时是 dsh 式（Python），但其工具箱内含本仓原生 AI 能力。

严守分层铁律：
- 内核零领域字面量：移植代码保持通用，粒子类型取值 / 知识谓词 / 红线事项目录由 `TenantProfile` 注入。
- 单向依赖：消费方只 import `chiyu_kernel.contract` 与 `chiyu_kernel.api`。
- L3 可选：未装 `chiyu-portal` 时 L0–L2 功能完整。

## 4. 分期

- **阶段一（MVP，本次实施）**：session + tools + agent/agent-loop + llm 适配 + 门户对话页 + 本仓能力桥接 + E2E 冒烟（§5 七任务）。
- 阶段二：skill 注册表、subagent 委派、plan / todo / workflow。
- 阶段三：mcp 桥、guard 环路卫生、fs/shell/subprocess/terminal、hooks、interaction/审批。

## 5. 阶段一任务（含生命契约 §A 双轨）

**契约说明：** 以下任务均由 `foundation-builder` 承接（契约键 `ct-chiyu-foundation`），受
`contract/contract-ids.json` 登记约束；`skills` 取自其 `skillCalls` 子集，`memory` 读 `chiyu-foundation`，
`knowledge_scope` 限 L1/L2。

```contract-yaml
- task: "移植 session 会话日志到 chiyu_kernel/session"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-memory-lifecycle, ai-context-layering]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1], max_hops: 2 }
  success: "启动一个 session；模型请求可由 SessionEvent 日志重建；pytest 覆盖 append/deriveMessages"
```
**契约说明：** 由 `foundation-builder` 承接（键 `ct-chiyu-foundation`），调用 `ai-memory-lifecycle` /
`ai-context-layering`，读 `chiyu-foundation` 记忆（L1，≤2 跳）；成功标准为 session 可启动且模型请求可自日志重建。

```contract-yaml
- task: "移植工具注册与守卫管线到 actions"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-native-action-design]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1], max_hops: 2 }
  success: "actions/registry 支持作用域注册+pre/post-execute 守卫；pytest 覆盖越权拒绝"
```
**契约说明：** 由 `foundation-builder` 承接（键 `ct-chiyu-foundation`），调用 `ai-native-action-design`，
读 `chiyu-foundation` 记忆（L1，≤2 跳）；成功标准为作用域注册与守卫管线就位且越权被拒。

```contract-yaml
- task: "移植 Agent 接口与 agent-loop 轮次流到 orchestration"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-multi-agent-orchestration]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "orchestration 驱动 turn/step 流；agent/pre-step 可改写/拒绝；pytest 覆盖单步与多步"
```
**契约说明：** 由 `foundation-builder` 承接（键 `ct-chiyu-foundation`），调用 `ai-multi-agent-orchestration`，
读 `chiyu-foundation` 记忆（L1/L2，≤2 跳）；成功标准为 turn/step 流与 pre-step 拦截生效。

```contract-yaml
- task: "接入本仓 llm/tier 作为模型适配器"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-context-layering]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1], max_hops: 2 }
  success: "agent-loop 经 llm/tier 发请求；DeepSeek 可作 provider 切换；pytest 覆盖流式与失败重试"
```
**契约说明：** 由 `foundation-builder` 承接（键 `ct-chiyu-foundation`），调用 `ai-context-layering`，
读 `chiyu-foundation` 记忆（L1，≤2 跳）；成功标准为模型请求经本仓 tier 发出且 provider 可切换。

```contract-yaml
- task: "移植对话前端到 chiyu_portal 渲染器"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-portal-page-generation]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "renderer 产出对话页 HTML（session 日志渲染+composer+目标栏）；从 session/event 渲染"
```
**契约说明：** 由 `foundation-builder` 承接（键 `ct-chiyu-foundation`），调用 `ai-portal-page-generation`，
读 `chiyu-foundation` 记忆（L1/L2，≤2 跳）；成功标准为对话页 HTML 可从 session/event 渲染。

```contract-yaml
- task: "将本仓决策/粒子能力暴露为 agent 工具(无缝集成)"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-native-action-design, ai-capability-audit]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "对话中可调用本仓决策/粒子工具；红线命中经 guard 拦截；pytest 覆盖工具接线"
```
**契约说明：** 由 `foundation-builder` 承接（键 `ct-chiyu-foundation`），调用 `ai-native-action-design` /
`ai-capability-audit`，读 `chiyu-foundation` 记忆（L1/L2，≤2 跳）；成功标准为原生能力经工具面可达且红线拦截生效。

```contract-yaml
- task: "阶段一 END-TO-END 冒烟"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-capability-audit]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "dsh 式对话页跑通 问→调本仓决策工具→渲染；make test 全绿"
```
**契约说明：** 由 `foundation-builder` 承接（键 `ct-chiyu-foundation`），调用 `ai-capability-audit`，
读 `chiyu-foundation` 记忆（L1/L2，≤2 跳）；成功标准为端到端对话页闭环跑通且全量测试绿。

## 6. 风险与验收

- **风险 R1**：dsh 的 Cordis `effect` / 瀑布事件（`agent/*`、`tools/*`）模型精密，Python 重写需保证扩展点语义等价。
  缓解：以 dsh 的 e2e / snapshot 行为契约作参照基线，逐能力写 pytest 对照。
- **风险 R2**：与本仓既有 `orchestration` / `actions` / `llm` 重复。缓解：采用能力吸收式（思路 B），扩展既有原语而非新建平行框架。
- **验收**：每个任务带 `contract-yaml` 成功标准；阶段一结束 `make test` 全绿 + 对话页端到端跑通。

## 闭环回写

（P10 落点；当前无运行反馈，表为空）

| task | agent | gap_type | observed | expected | ts | severity |
|---|---|---|---|---|---|---|
| （暂无） | | | | | | |
