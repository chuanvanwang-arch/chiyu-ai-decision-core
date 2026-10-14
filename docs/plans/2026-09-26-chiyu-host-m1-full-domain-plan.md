# 实施计划：M1 全量域接入真实 chiyu_kernel（skills+subagents+agentPreset）

> 阶段：writing-plans（用户已选「全量域」）
> 关联：M0 总计划 `2026-09-25-dsh-client-chiyu-backend-plan.md`、R3 矩阵、T2 桥接 `chiyu-host`（已收口 3 提交）、T3 重建 clientModules（`web.py` 已入库，本机真渲染被沙箱环境拦，延后）
> 目标：把 `methods.py` 的 **M0 静态占位**（`SUBAGENT_DEFS` 硬编码 / `_build_default_skills` 演示目录 / 模型静态）升级为**接入真实 chiyu_kernel 注册表**：skills 真实 `SkillRegistry`（phase2）+ subagents 真实 `SubagentPool.delegate`（phase2）+ agentPreset 映射工作模式（plugins）。

---

## 0. 现状（实测 `methods.py`）

- `skill.list` → 演示目录 `_build_default_skills()`（summarizer/translator/code-reviewer 硬编码）。
- `subagent.list` → 静态 `SUBAGENT_DEFS`（researcher/coder/reviewer 硬编码），**无 delegate 能力**。
- `agentPreset.list` → 已映射 `MODE_PRESETS`（plugins），**已真**，但 `isDefault` 用 `DEFAULT_MODE_ID`、无 `select/read` 等后续域。
- 需新增：`subagent.history` / `subagent.prompt` / `subagent.interrupt`（对齐 `subagents.schema.ts`）。

## 1. 真实接口（实测，M1 依据）

- `SubagentPool(llm=..., tools=..., sessions=..., redline_guard=None)`；`.delegate(task, *, subagent_key)` → `AgentLoop.run_turn(...)` 返回 `Mapping`。
  - **不 import `chiyu_kernel.api` 门面**（门面触发 `store.pg_store` 的 pg 依赖，M1 桥接层不连库）——直接消费 `chiyu_kernel.orchestration.subagent` / `chiyu_kernel.skills` / `chiyu_kernel.plugins` 子模块（同仓内部桥接层有权，与 M0 同策略）。
- `SkillRegistry.register(spec)` / `.list()` → `list[SkillSpec]`；`load_catalog(catalog)` 批量注册。
- `SkillSpec` 字段：`name/description/content/when_to_use/model_invocable/user_invocable/source/provider/rank/metadata`。
- `MODE_PRESETS` / `DEFAULT_MODE_ID`（plugins）已真。

## 2. 任务分解

### M1-T1 真实 SkillRegistry 注入（替换 `_build_default_skills`）
- 建模块级真实 `_skill_registry = load_catalog({真实目录})`——目录从本仓 skills 的**同 shape** 注入（消费方应注入 TenantProfile；桥接层默认用 `chiyu_kernel.skills` 自带的 catalog 或一个中性示例目录）。
- `skill.list` 改为读 `_skill_registry.list()`（保持字段对齐 `skills.schema.ts`：`name/description/whenToUse/modelInvocable`）。
- 单测：skill.list 返回真实注册表项（非硬编码演示目录）。

### M1-T2 真实 Subagent 委派 + 增 subagent.* 方法
- 建 `SubagentPool` 实例（`llm=StubProvider`（或 `build_provider('stub')`）、`tools=ToolRegistry()`、`sessions=SessionManager()`——**共用一个 SessionManager，与 M0 `_session_manager` 同一实例**，保证 parent/child 会话可见）。
- 注册真实 `SubagentDescriptor`（对齐 M0 已有 researcher/coder/reviewer，但改挂真实注册表，非静态）。
- `subagent.list` 改读 pool 的 `_descs`（或维护同名索引），字段对齐 `subagentListEntrySchema`（`kind/id/mode/activity/hasChildren/label`）。
- 新增：
  - `subagent.history(childSessionId, ...)` → 读该 child 的 `SessionLog`，`events[event{type,seq,time,data}], hasMore`（对齐 `subagentHistoryValueSchema`）。
  - `subagent.prompt(childSessionId, content)` → `pool.delegate(task, subagent_key=child)` → 返回 `{messageId}`（对齐 `subagentPromptValueSchema`）。
  - `subagent.interrupt(childSessionId)` → `{accepted:true}`（对齐 `subagentInterruptValueSchema`）。
- 单测：真实 delegate 跑通一次（StubProvider）+ history/interrupt 返回对齐。

### M1-T3 agentPreset 补 select/read（若 M1 定义含后续域）
- 计划默认：**M1 只做 list 域对齐 M0**（select/read 属 M2「agentPreset 可浏览/启停」，留在 M1 计划外，回填矩阵）。
- 若用户要全量，则在 M1 追加 `agentPreset.select/read`（对齐 `agent-presets.schema.ts`，映射 MODE_PRESETS）。

### M1-T4 回归 + 提交
- 全量：`chiyu-host` 测试 + `chiyu-kernel` 相关子集（skills/plugins/subagent 已有）不回归。
- 变异自证：`subagent.prompt` 的 delegate 接线（故意错 key→报错）转红验证。
- 提交：每 Task 一 commit，显式 add 路径。

## 3. 文件布局
- `packages/chiyu-host/src/chiyu_host/methods.py`：替换静态占位 + 增 3 方法。
- `packages/chiyu-host/tests/test_rpc_schema.py`：增 M1 用例。
- 复用现有 `_session_manager`/`_bus`/`_mux`。

## 4. 风险与门
- R1：`SubagentPool` 构造是否触发 pg → **不 import api 门面**（M0 已验证路径），单测即暴露。
- R2：真实 `SkillRegistry.list()` 是否含演示项 → 注入真实目录，单测断言「非 hardcoded」。
- R3：subagent 委派是否真跑 AgentLoop（非静态返回）→ 单测断言 delegate 有真实回显。
- 门：M1 全绿 + 变异自证 + 不假绿（subagent.prompt 不真 delegate 则红）。

## 5. 完成判据
- skill.list/subagent.list 返回真实注册表；subagent.prompt 真实委派一次并回 messageId；history/interrupt 对齐 schema；chiyu-host 测试全绿；M1 阻断点回填 R3 矩阵。
