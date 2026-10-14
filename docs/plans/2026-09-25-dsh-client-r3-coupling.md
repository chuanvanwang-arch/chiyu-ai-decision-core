# M0-T1 R3 耦合探针：DSH client → 后端契约矩阵

> 探测对象：`D:/system/reference/deepseek-harness-master`（DSH 参考实现）
> 目的：去风险——确定「复用 DSH client UI 换 chiyu_kernel 后端（路线 A）」所需最小后端契约面
> 方法：纯只读 grep + 源码核验，未改动任何文件

---

## 1. 架构分层（实测，纠正早期假设）

```
ui-* 模块 (ui-conversation/ui-model-selection/ui-settings-plugins/...)
   │  消费 Cordis 客户端服务（ctx.get('conversation')、ctx.slots.inject ...）
   ▼
Cordis 客户端服务包（dsh-client-ui-conversation / dsh-client-runtime / dsh-client-ui-slots ...）
   │  ← ui-* 对 apiproxy 零直接依赖（grep 证实仅 connection/19、runtime/6 引用 apiproxy）
   ▼
connection (web-api-client.ts / rpc.ts) + runtime (cordis-client-runner)
   │  仅 import apiproxy/api/rpc + apiproxy/api/events
   ▼
host apiproxy：① 单一 RPC 端点（RpcMethodMap 方法） ② SSE /api/events/mux
```

**关键结论**：`ui-*` 通过 Cordis 客户端服务解耦，传输层收敛为 **1 个 RPC 端点 + 1 个 SSE mux 流**。后端契约面不是「37 个 REST 控制器」，而是「**52 个 RPC 方法的路由器 + SSE mux + boot 注入**」。

---

## 2. RPC 方法面（实读 `packages/host/apiproxy/src/api/rpc-map.ts`）

共 **52 个方法**，按域归属：

| 域 | 方法（节选关键） |
|---|---|
| session (12) | `session.list/create/history/models/selectModel/prompt/rename/fork/attachment/updateQueue/cancel/search` |
| subagent (4) | `subagent.list/history/prompt/interrupt` |
| host (5) | `host.describe/pickDirectory/listDirectory/createDirectory/openPath` |
| workspace (7) | `workspace.list/create/rename/delete/insertBefore/insertSessionBefore/archiveSession` |
| skill (1) | `skill.list` |
| agentPreset (6) | `agentPreset.list/select/read/copy/openDocument/remove` |
| goal (7) | `goal.create/edit/pause/resume/complete/clear` (+1) |
| settings (5) | `settings.describe/openDocument/update/replace/mutate` |
| credentials (3) | `credentials.describe/set/unset` |
| llm (3) | `llm.providers/models/discoverModels` |

> 注释原文：`map keys are the wire path segments (POST /api/session.list)`。即每个方法对应 `POST /api/<method>`。

---

## 3. M0 目标 UI 模块 → 最小后端契约子集

| 前端模块 | 需要的 RPC 方法 | SSE | 本平台现有能力（chiyu_kernel） |
|---|---|---|---|
| **ui-conversation** | `session.list` `session.create` `session.history` `session.prompt` `session.cancel` `session.models` `session.selectModel` | `events.mux`（session/* 帧） | `session`（本仓有）/ `render_conversation`（phase 已有，纯函数）✅ |
| **ui-model-selection** + **ui-settings-models** | `llm.providers` `llm.models` `agentPreset.list` `session.selectModel` | — | `llm` 抽象已就位，**provider 待接（Phase B）** → M0 静态返回 `deepseek-v4-flash` ⚠️ |
| **ui-settings-plugins** + **ui-settings-plugin-inventory** | `skill.list` `subagent.list` `host.describe` | — | `skills`（phase2 注册表）✅ `subagent`（phase2 委派）✅ → 即「集中封装后台插件」首落地 |

**M0 最小桥接契约 = 上述 ~14 个 RPC 方法 + `events.mux` SSE + `window.__DSH_BOOT__` 注入。**

---

## 4. 风险与下一步（M0-T2 依据）

- **R3 已收敛**：后端契约面从「37 域」收窄为「52 方法的 RPC 路由器 + SSE mux」。M0 只需实现其中 ~14 个方法即可跑通对话/模型/插件清单三块 UI。
- **R4（llm provider 未接）**：`llm.*` 方法 M0 返回静态模型列表占位，真实多 LLM 切换待 Phase B 接 provider 后激活。
- **boot 注入**：`apps/web` 非独立 vite（rejectStandaloneServe），须由 launcher 注入 `window.__DSH_BOOT__`（modules 插件扫描 client 树生成）。M0 用 thin launcher 注入，验证后再考虑复用 `dsh web` 启动链。
- **M0-T2 实现形态修正**：`chiyu-host`（Python/FastAPI）应实现 **单一 RPC 路由器**（`POST /api/<method>` → 按 `RpcMethodMap` 分发到 chiyu_kernel 处理函数）+ **WebSocket `/api/events.mux`**（实测 DSH client 经 `readWebSocket(MUX_EVENTS_PATH)` 下行 MuxFrame，路径 `packages/client/connection/src/api-path.ts`：`MUX_EVENTS_PATH = '/api/events.mux'`，**非 SSE**），而非 37 个独立 REST 控制器。每个实现的方法须与对应 `apiproxy/src/api/<domain>.ts` 的 `XxxApi` 接口逐字段对齐（防假绿）。

> ⚠️ **契约修正（实测，2026-09-25 M0-T2 落地）**：早期计划/R3 假设 mux 为 SSE（`GET /api/events/mux`）。实测 DSH client `web-api-client.ts` 的 `openMux` 走 `readWebSocket`，即 **WebSocket 下行**。为保证 T3 零改复用 DSH client，chiyu-host 采用 WebSocket `/api/events.mux`，帧形态为 `ServerRequest` 全形（`{type:'server-request', rpcId, method:'events.mux', payload: MuxFrame}`），MuxFrame 见 `events.schema.ts` 的 `muxFrameSchema` 联合。

---

## 5. 耦合矩阵（ui-* → 方法，全量参考）

> 以下为扩展参考：除 M0 三块外，其余 ui-* 依赖的方法（供 M1-M4 排期）。

- ui-subagent / ui-workflow-run → `subagent.*` + `session.prompt`
- ui-plan → `session.*` + `goal.*`（plan 在 DSH 由 goal/session 承载）
- ui-goal → `goal.*`
- ui-jobs → `session.*`（jobs 经 session 事件）
- ui-workspace → `workspace.*` + `host.*`
- ui-settings (general) → `settings.*` + `host.describe`
- ui-agent-preset → `agentPreset.*`
- ui-user-questions / ui-message-feedback → `events.mux` 帧 + `session.prompt`
- ui-directory-picker-* → `host.pickDirectory/listDirectory`
- ui-permission-presets → `settings.*`

---

## 6. M1 回填（2026-09-26，真实落地，非占位）

> M1 计划：`docs/plans/2026-09-26-chiyu-host-m1-full-domain-plan.md`。本节点把 M0-T1 探针里「⚠️ phase2 注册表/委派」的占位升级为**真实 chiyu_kernel 接线**，回填 R3 矩阵「本平台现有能力」列。

### 6.1 回填判据（逐条，防假绿）

| §3 表项 | M0 状态 | M1 回填后真实状态 |
|---|---|---|
| `skill.list`（ui-settings-plugins） | phase2 注册表占位 | ✅ 真实 `load_catalog` 注入 5 项（含 `memory-curator`），`skill.list` 走真实 `SkillRegistry.list()` |
| `subagent.list`（ui-settings-plugins） | phase2 委派占位 | ✅ 真实 `SubagentDescriptor` ×3 + `SubagentPool` 注册，`subagent.list` 精确匹配注册集 |
| `host.describe`（ui-settings-plugins） | — | 保持 M0 静态（cwd/version/plugins），未变 |
| `subagent.history/prompt/interrupt`（ui-subagent） | 未覆盖 | ✅ **新增 3 方法**，字段对齐 `subagents.schema.ts`（`childSessionId`/`content`/`messageId`/`accepted`）；`subagent.prompt` 真实委派 `pool.delegate → AgentLoop.run_turn`，child 会话落 `user→assistant→turn/end` 事件 |
| `agentPreset.*`（ui-agent-preset） | 仅 `list` | ⚠️ M1 仅 `agentPreset.list`（映射 `MODE_PRESETS`）；`select/read/copy/openDocument/remove` 见 §6.3 + 任务 #8 |

### 6.2 新增能力（M1 自证）

- **元红线硬闸门**：`_subagent_pool` 注入 `native_redline_guard(profile=None)` → `AgentLoop → tools.execute(redline_guard=...)`；命中 `META_REDLINES`（`threshold_widen`/`baseline_write`/`redline_auto`）→ 抛 `GuardDenied`（被调用方硬闸门，不误拦普通动作）。
- **native 工具注册**：`register_native_tools(ToolRegistry, profile=None)` → `native-context-assemble`（`context.assemble` L1–L2 装配，返回 `facts`+`missing` supply_report）+ `native-redline-check` 真实注册且可调用。
- **纪律守恒**：profile 传 None（中性），从 `harness_native_tools` 直接 import，**绕过 api 门面不触发 pg**，与 M0/M1 同策略。

### 6.3 验证与提交

- `pytest packages/chiyu-host/tests` = **25 passed**（原 16 + M1 新增 9，零回归）。
- 变异自证：删 `memory-curator` → skill 判别项转红；`threshold_widen` → GuardDenied；native 工具直调返回 facts（非空接线）。
- 提交：`ffff599`（M1 全量域）/ `22b0f24`（redline_guard）/ `7c292c9`（native 工具判别项）。
- R3 去风险最终判定：**达成**。DSH client `ui-*` 经「52 方法 RPC 路由器 + WebSocket mux + boot 注入」对接 chiyu_kernel 的最小契约面已在本仓真实实现并单测绿，路线 A「DSH client 零改对接」在 skills/subagents/agentPreset.list 域闭环。

### 6.4 进度回填（2026-09-26 更新）

- ✅ `agentPreset.select/read`（任务 #8，提交 `c2d3a27`）。
- ✅ `goal.*`（M2，session 投影真实现）：6 方法（create/edit/pause/resume/complete/clear）对齐 DSH `goals.schema.ts` 的 mutation-only 语义；goal 状态经 `goal/state` 事件投影到 session 事件流；revision 乐观锁冲突检测；clear 后索引删除并阻断后续 mutation。提交见 §6.5。
- ⚠️ 留给后续：`workflow`（DSH `ui-workflow-run` 走 `subagent.*`，M1 已真委派，**不新增独立 workflow RPC**）、`jobs`（DSH 走 `session.*`，M1 已覆盖）。
- ✅ `decision`/`memory`/`tables`（M3 本平台独有域，提交见 §6.6）：设计 `docs/plans/2026-09-26-chiyu-host-m3-unique-domains-design.md` 经用户 P8 批准（2026-09-26，契约校验 valid，判别力自证通过）。6 方法（table.list/table.describe 只读反射 `contract.particle` 常量·零 pg；memory.write/memory.read 六元组严写 session 投影桥接；decision.spine 只读反射 `contract.decision` 脊柱常量 + decision.record session 投影桥接）。写域走 goal 同款 in-memory 索引 + 事件投影，不连 pg、不碰内核 baseline、不触发 `META_REDLINES`。变异自证：卸掉 memory 六元组校验 → 缺项不再拒写（测试转红）；卸掉 decision 事件 emit → history 无 `decision/record`（测试转红）。
- ✅ `session.prompt` 接入 L1–L2 上下文装配（任务 #T4，提交见 §6.5）：设计 `docs/2026-09-26-chiyu-host-session-context-layering-design.md` 经用户 P8 批准（2026-09-26，契约校验 valid）；实施计划 `docs/plans/2026-09-26-chiyu-host-session-prompt-context-plan.md`。`session.prompt` 由「仅 append 不调 LLM」升级为**复用 AgentLoop 同步委派**真跑一轮 LLM，pre_step 钩子 `assemble(L1–L2, provided={})` 把装配 facts 注入模型上下文首部、并把缺口结构化落档 `context/assemble` 事件（provided 空 → missing 含 L1/L2，fail-safe 不抛错）；总线保留 `user/message` 首帧 + 补发 `assistant/message`；返回契约不变 `{accepted:true}`。变异自证：移除 pre_step 钩子 → `context/assemble` 判别项转红。

### 6.5 验证与提交（session.prompt L1–L2 装配，2026-09-26）

- `pytest packages/chiyu-host/tests` = **39 passed**（原 36 + T4 新增 3，零回归）。
- 变异自证：移除 pre_step 装配钩子 → 会话缺 `context/assemble` 事件（判别项转红）。
- 提交：`T4`（session.prompt 接入 L1–L2 上下文装配，复用 AgentLoop 同步委派，39 passed）。

### 6.6 验证与提交（M3 本平台独有域 decision/memory/tables，2026-09-26）

- `pytest packages/chiyu-host/tests` = **45 passed**（原 39 + M3 新增 6，零回归）。
- 变异自证（判别力，非假绿）：① 卸掉 memory 六元组 strict 校验 → 缺项不再拒写（缺项测试转红）；② 卸掉 `decision/record` 事件 emit → session history 无该事件（投影测试转红）。
- 提交：`T5`（M3 三域 6 方法：table.list/describe 反射·memory.write/read 六元组桥接·decision.spine/record 投影·45 passed）+ `docs`（R3 §6.4/§6.6 回填 + 设计批准标记）。
