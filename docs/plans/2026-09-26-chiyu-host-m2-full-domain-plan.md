# 实施计划：M2 全量域（jobs + goals + 事件帧扩展）

> 阶段：writing-plans（P0 解锁在途；M2 与 P0 并行）
> 关联：M0 总计划 `2026-09-25-dsh-client-chiyu-backend-design.md`；M1 计划 `2026-09-26-chiyu-host-m1-full-domain-plan.md`（已收口 3 提交）
> 目标：把 `chiyu-host` 的 RPC 方法面从 M1 的 16 方法扩展到 **jobs/goals 全量域**，并把 MuxBroadcaster 从单一 `session/event` 帧扩展为**多帧类型广播**（`session/jobs` + `session/projection`），对齐 DSH 客户端 `ui-jobs` / `ui-goal` 面板可消费的完整事件契约。

---

## 0. 实测契约（读 `D:/system/reference/deepseek-harness-master/packages/host/apiproxy/src/api/` 结论）

| 域 | DSH 真实契约 | chiyu-host 现状 | 需补齐 |
|---|---|---|---|
| jobs | **无独立 RPC 方法**；`JobView{id,kind,label,status:running\|stopping\|completed\|killed\|failed,detail?,startedAt,finishedAt?}` 经 `session/jobs` 帧推送（`events.ts:98`） | 无 jobs 域 | 新增 jobs 注册表 + `session/jobs` 帧推送 |
| goals | 6 个 RPC mutation：`goal.create/edit/pause/resume/complete/clear`（`rpc-map.ts:60-65`）；**无 goal.get** —— 读侧在 `session/projection` 帧（`events.ts:107`） | 无 goals 域 | 新增 goal 状态机（CAS ref）+ `session/projection` 帧 |
| workflow | **不在 RpcMethodMap**（`rpc-map.ts` 无 workflow 方法）—— 前端本地 DAG 编排 + 调 subagent/jobs 域 | phase5 `WorkerRun` 已真 | 不做 RPC；经 jobs 帧暴露运行中的 workflow 任务 |
| events 帧 | `session/jobs`（`events.ts:98`）/ `session/projection`（`events.ts:107`） | MuxBroadcaster 仅订阅 `session/event` 单帧 | 扩展多帧 type + 订阅多 event_type |

### 关键 wire 形状（防假绿锚点）

- `session/jobs` 帧：`{type:'session/jobs', sessionId, jobs: JobView[]}`
- `session/projection` 帧：`{type:'session/projection', sessionId, key, value, seq}`
- `goal.create` 请求：`{sessionId, objective, maxGoalRounds?}` → 响应 `{ref:{id,revision}}`
- `goal.clear` 响应：`{cleared:true}`
- `JobView.status` 枚举：`running|stopping|completed|killed|failed`
- `goal.edit` refine：至少给 `objective` 或 `maxGoalRounds`

---

## 1. 复用与新增（基于 M1 已收口代码）

### 复用（零改动）
- `_session_index` / `_session_manager` / `_session_meta`（M0）
- `_bus` / `_mux` / `MuxBroadcaster`（M0，需扩展）
- `_subagent_pool` / `SUBAGENT_DESC_LIST`（M1）
- `to_wire_session_event` / `build_mux_frame` / `wrap_server_request`（M0 bridge）

### 新增
- `chiyu_host/jobs.py`：JobRegistry（kind 扩展点：`bash`/`pwsh`/`subagent`/`workflow`）+ `session/jobs` 帧推送
- `chiyu_host/goals.py`：Goal 状态机（`id`/`revision`/`state:active|paused|completed|cleared`）+ 6 mutation + `session/projection` 帧
- `chiyu_host/events.py`（或扩展 `bridge.py`）：多帧 type 广播

---

## 2. 任务分解

### M2-T1：JobRegistry + session/jobs 帧
- `JobRegistry.add(kind, label)` → 返回 `JobView`（id=`<kind>-N`，startedAt=now，status=running）
- `JobRegistry.set_status(job_id, status, detail?)` → 更新 finishedAt（终态时）
- `JobRegistry.list(session_id)` → 该会话可见的 `JobView[]`
- 每 add/set_status → 推 `session/jobs` 帧（`{type:'session/jobs', sessionId, jobs}`）
- 单测：add→running；set_status(completed)→finishedAt 出现；帧推送对

### M2-T2：Goal 状态机 + 6 mutation
- `GoalStore.create(session_id, objective, max_goal_rounds?)` → `{id, revision:1, state:'active'}`
- `GoalStore.apply(session_id, ref, verb)` → CAS 校验（ref 不匹配→RpcError `goal-not-found`/`goal-conflict`）+ 状态迁移（pause/resume/complete 各限态）+ revision++
- `goal.edit`：refine 校验（至少 one field）
- `goal.clear`：保留 tombstone（id 仍可寻址、history 保留）
- 每次状态变更 → 推 `session/projection` 帧（key=`goal`, value=目标视图, seq=revision）
- 单测：CAS 失败转红；状态机非法迁移转红；clear 留 tombstone

### M2-T3：多帧广播扩展
- `MuxBroadcaster` 支持 `subscribe_type(event_type, name, fn)` 或注册多个帧型
- 新增帧型：`session/jobs`、`session/projection` 走同一 WS 下发（ServerRequest 全形）
- 保持 `session/event` 兼容（M0/M1 测试不回归）
- 单测：多帧型在同一连接依次下发；字段与 schema 对齐

### M2-T4：workflow → jobs 帧接线（phase5 复用）
- 将 phase5 `WorkerRun` 的启动/结束映射为 `JobView`（kind=`workflow`，status=running→completed/failed/killed）
- WorkflowRunner 运行生命周期钩子回写 JobRegistry（不新建框架，仅登记）
- 单测：workflow 运行期间 jobs.list 含 `workflow-N`，结束后状态终态

### M2-T5：回归 + 变异自证 + 提交
- 全量 `chiyu-host` 测试 + `chiyu-kernel` 相关子集不回归
- 变异自证：CAS 校验分支中性化→转红；`session/jobs` 帧 type 改错→转红；还原转绿
- 每 Task 一 commit，显式 add 路径

---

## 3. 文件布局
- `packages/chiyu-host/src/chiyu_host/jobs.py`（新）
- `packages/chiyu-host/src/chiyu_host/goals.py`（新）
- `packages/chiyu-host/src/chiyu_host/bridge.py`（扩展多帧）
- `packages/chiyu-host/src/chiyu_host/methods.py`（注册 goal.* 6 方法）
- `packages/chiyu-host/src/chiyu_host/app.py`（如需要挂载新路由，预计无需）
- `packages/chiyu-host/tests/test_jobs_domain.py` / `test_goals_domain.py` / `test_mux_multi_frame.py`（新）
- `packages/chiyu-host/tests/test_rpc_schema.py`（补 goal.* 用例）

---

## 4. 风险与门
- R1：Goal CAS 语义与 DSH `GoalRef{id,revision}` 严格对齐（revision 从 1 起，每次 mutation ++）
- R2：`session/projection` 帧 seq 语义 —— DSH 用 projection 完成 seq；本仓映射 goal revision（文档登记，非静默）
- R3：workflow→jobs 映射是**登记**非驱动（phase5 WorkerRun 不受影响）
- 门：M2 全绿 + 变异自证 + 不假绿（jobs 帧只发不发→红；goal CAS 不校验→红）

---

## 5. 完成判据
- `goal.*` 6 方法全部注册并按 DSH schema 对齐；`session/jobs`+`session/projection` 帧可从 WS 收到；workflow 运行映射为 jobs 条目；chiyu-host 测试新增 ≥15 且全绿；M2 阻断点回填 R3 矩阵。
