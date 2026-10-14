# M2 实施计划：chiyu-host 接入 `goal.*` 域（session 投影真实现）

> 关联：总计划 `docs/plans/2026-09-25-dsh-client-chiyu-backend-plan.md` §M2；R3 探针 `docs/plans/2026-09-25-dsh-client-r3-coupling.md` §5（ui-goal → `goal.*`）。
> 范围决策（已盘点内核）：`chiyu_kernel` 有 `workflow`(WorkflowRunner) + `plan`(Plan/PlanStep/TodoList)，**无 `Goal` 实体**；`jobs` 在 DSH 走 `session.*` 事件（R3 §5 已注），无需独立 RPC。

## 0. 为什么 goal 用 session 投影（不造内核 Goal 类）

实读 `packages/host/apiproxy/src/api/goals.schema.ts`：
- `goal.*` 全部 7 方法（create/edit/pause/resume/complete/clear）**仅回 `{ref:{id,revision}}` 或 `{cleared:true}`**（mutation-only acknowledgement）。
- 注释原文：*"The current goal state travels exclusively on the 'goal' session projection."* —— 状态经 session 事件流传递，RPC 不做状态查询返回。
- 即 DSH 的 goal 是**会话级目标投影**，天然适配「桥接层维护 goal 状态 + append goal/* 事件到 session log + publish 到 mux」。

**纪律合规**：不新建内核 `Goal` 类（内核零领域字面量 + 不假绿）；纯桥接层 session 投影即可对齐 DSH 契约。内核 `plan`(PlanStep 状态机) 语义不同（多步骤推进），**不复用**为 goal 载体（避免语义错位假绿）。

## 1. 实现设计

### 1.1 状态索引（桥接层，内存态，不连 pg）
```python
_goal_index: Dict[str, Dict[str, Any]] = {}  # sessionId -> {id, revision, objective, status}
```
- `id`：每 session 单一 goal，`f"goal:{sessionId}"`（DSH 单 active goal 语义）
- `revision`：从 1 起，每次 mutation +1（乐观锁版本，对齐 GoalRef）
- `status`：`running` / `paused` / `completed`（clear 后从索引删除）

### 1.2 RPC 方法（对齐 goals.schema.ts 字段）
| 方法 | payload | 返回 | 行为 |
|---|---|---|---|
| `goal.create` | `{sessionId, objective, maxGoalRounds?}` | `{ref:{id,revision}}` | 校验 session → 建 goal(revision=1,status=running) → append `goal/state` 事件 → publish mux |
| `goal.edit` | `{sessionId, ref, objective?, maxGoalRounds?}` | `{ref}` | revision+1 → 更新 objective/maxGoalRounds → append 事件 |
| `goal.pause` | `{sessionId, ref}` | `{ref}` | status=paused → append |
| `goal.resume` | `{sessionId, ref}` | `{ref}` | status=running → append |
| `goal.complete` | `{sessionId, ref}` | `{ref}` | status=completed → append |
| `goal.clear` | `{sessionId, ref}` | `{cleared:true}` | 删索引 → append `goal/cleared` |

### 1.3 session 投影（对齐 DSH "state travels on session projection"）
- 每次 mutation：`_session_index[sid].append("goal/state", {ref, objective, status})` + `_bus.publish(session/event)`。
- 前端（DSH client ui-goal）从 session 事件流读 goal 投影；即使前端暂未渲染，RPC 契约已对齐（不崩、不假绿）。

### 1.4 错误路径
- session 不存在 → `session-not-found`（create 先 `_session_or_raise`）
- goal 不存在/ref 不匹配 → `goal-not-found`

## 2. 测试（test_rpc_m1_full_domain.py 风格，含变异自证）
- `goal.create` 返回 `{ref:{id,revision:1}}`；session log 出现 `goal/state` 事件
- `goal.edit` revision+1；`goal.pause/resume/complete` 改 status 且返回 `{ref}`
- `goal.clear` 返回 `{cleared:true}`；clear 后 `goal.pause` → `goal-not-found`（变异自证）
- `goal.create` 对未知 session → `session-not-found`

## 3. 提交
- 显式路径 add（methods.py + 测试）；单行 -m `T3: ...`；计入 passed 数。
- R3 文档 §6.4 更新：goal 域已真对接（原标记「留给 M2」）。

## 4. 范围外（记录阻断点，不假实现）
- `jobs`：DSH 走 `session.*`（R3 §5），无独立 RPC，M1 session.* 已覆盖 → 不通独立 job RPC。
- `workflow`：DSH ui-workflow-run 走 `subagent.*`（M1 已真委派）→ 不新增独立 workflow RPC。
- 内核 `plan`(PlanStep) 留待本平台 `ui-plan`（M3 本平台独有域）。
