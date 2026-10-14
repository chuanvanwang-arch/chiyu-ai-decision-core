# Deepseek Harness 全量 Python 移植 · 阶段四实施计划

- 日期：2026-09-25
- 形态：全量 Python 移植（忠实重写 dsh 能力词汇表，R2 能力吸收式）
- 契约：`contract/contract-ids.json`（agent = `foundation-builder`，键 `ct-chiyu-foundation`）
- 关联设计：`docs/plans/2026-09-25-deepseek-harness-python-port-design.md` §2/§4
- 关联阶段一/二/三计划：`...-plan.md` / `...-plan-phase2.md` / `...-plan-phase3.md`

## 0. 阶段四范围与边界

设计文档 §2 把 `workflow/` 列为「后续阶段」、§4 分期未含阶段四；但 §2 的架构映射表明确将
`plan/ todo/ workflow/` 并列为 L2 数据模型层（标注「阶段二」）。phase2/phase3 实施时**遗漏了 workflow**，
三个计划文件对 `workflow` 零命中。本阶段补齐该设计已界定、实施遗漏的能力。

**dsh `workflow` 真实形态（已读 `packages/workflow/` 源码锚定）**：
- `workflow` 包：核心是 `WorkflowEngine` 抽象——一个 **JS 脚本执行引擎**（Cordis 服务 + worker-thread 进程外执行），
  脚本用 `agent()`/`pipeline()`/`parallel()`/`phase()`/`log()` 钩子 fan-out 子智能体。
- `tool-workflow` 包：模型面工具，参数 `script`(JS 体) + `meta` + `args`，执行后返回 `WorkflowResult`。
- 词汇表：`WorkflowMeta`/`WorkflowPhase`/`WorkflowRunId`/`WorkflowResult`(`stopReason: completed|cancelled|error`)
  /`WorkflowError`(fatal flag + `WorkflowErrorCode` 族) / `WorkflowRun`(`id`/`meta`/`result`/`cancel`/`dispose`)。

**R2 能力吸收边界决策（严守，不重复 orchestration / 不引入 JS 运行时）**：
1. **吸收** dsh workflow 的**声明式编排词汇表与数据模型**：`WorkflowMeta`/`WorkflowPhase`/`WorkflowRunId`/
   `WorkflowStep`(含 `depends_on` DAG) / `Workflow`(拓扑排序+环检测) / `WorkflowResult` / `WorkflowError` + 错误码族。
2. **不吸收** JS 脚本执行引擎。dsh 用一串 JS 串表达编排，本仓**无 JS 运行时**；等价能力用**声明式 steps**
   （每个 step 含 `prompt` + `depends_on`）+ 复用 phase2 已建的 `SubagentPool.delegate()` 实现。
   这是 R2「能力吸收式重写」的显式偏差，在本文 §4 登记。
3. `WorkflowRunner` 是 dsh `agent()`/`pipeline()` 概念的本仓等价物：按 DAG 拓扑派发子智能体，非 fatal 子失败 → 该 step 结果 `None`，
   fatal 错误 → 整个 run `error`。

| dsh 包 | 本仓落地 | 层 | 门面 | 说明 |
|---|---|---|---|---|
| `workflow`（词汇表+数据模型） | `chiyu_kernel/workflow/`（新子包） | L2 | 加 `LAYERS` | 忠实吸收词汇表；DAG 步骤 + 状态机 |
| `workflow`（执行引擎） | 复用 `orchestration/subagent.py` 的 `SubagentPool` | L2 | orchestration 已覆盖 | 不移植 JS 沙箱（R2 偏差） |
| `tool-workflow` | `workflow.register_workflow_tools` | L2 | 加 `LAYERS` | model-facing `workflow` 工具（声明式 steps，非 JS） |

## 1. 任务清单（TDD：先红→绿→门面守卫→提交）

- **T1 — workflow 数据模型**：`chiyu_kernel/workflow/__init__.py`。
  `WorkflowStep`（含 `depends_on: list[str]`、状态机 `WORKFLOW_STEP_STATES`）、`Workflow`（steps + 拓扑排序 `topo_order()` + 环检测）、
  `WorkflowMeta`/`WorkflowPhase`、`WorkflowRunId`(branded 工厂)、`WorkflowResult`/`WorkflowStopReason`、
  `WorkflowError`(fatal flag) + `WORKFLOW_ERROR_CODES` 族 + `is_fatal_workflow_error()`。
  测试覆盖：meta 校验（name kebab-case 必填）、step `depends_on` 环检测、拓扑排序顺序、stopReason 闭环、fatal 判定。
- **T2 — WorkflowRunner（复用 SubagentPool）**：`workflow/runner.py`。
  取 `Workflow` 定义，按 DAG 拓扑派发：每个 step 调 `SubagentPool.delegate(subagent_key, prompt)`；
  非 fatal 子失败 → 该 step 结果 `None`（其余继续）；fatal 错误 → run `error` 终止；支持 `cancel()`(signal)。
  测试覆盖：DAG 顺序执行 + 依赖传递、子失败隔离为 None、fatal→run error、取消。用 `StubProvider` + `SubagentPool` 测试替身。
- **T3 — 工具暴露 `register_workflow_tools`**：`workflow/register.py`。
  注册 model-facing `workflow` 工具进本仓 `ToolRegistry`，参数 schema（`meta`{name,description,phases?} + `steps`[{name,prompt,depends_on?}] + `args?`），
  执行经 `WorkflowRunner` 跑通并返回 `WorkflowResult` JSON（runId/agentsStarted/result）。
  测试覆盖：工具注册、schema 校验（缺 name 报错）、执行跑通返回结果。
- **T4 — 门面接线**：`workflow` 加守卫测试 `LAYERS`；`api.py` import 块（紧跟 `plan` 之后或 `interaction` 附近）+ `__all__` 暴露公共 API
  （`Workflow`/`WorkflowStep`/`WorkflowRunner`/`register_workflow_tools`/`WorkflowError`/`WorkflowResult` 等）。
  子包 `__all__` 只露公共 API，`WORKFLOW_ERROR_CODES` 等常量保留定义、移出 `__all__`。
- **T5 — 阶段四 E2E 冒烟**：串联 workflow(`WorkflowRunner`) → subagent(`SubagentPool`) → plan/todo(phase2) → `render_conversation`(portal) 跑一轮声明式 workflow，
  断言各能力生效；`make test` 全绿 + 门面守卫绿。

## 2. 契约块（P7 自检用）

```contract-yaml
- task: "workflow 声明式编排数据模型（吸收 dsh workflow 词汇表，DAG 步骤+状态机）"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-multi-agent-orchestration, ai-native-action-design]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "Workflow 支持 depends_on DAG 拓扑排序与环检测；WorkflowResult/WorkflowError 语义等价 dsh；pytest 覆盖"
```
```contract-yaml
- task: "WorkflowRunner 复用 SubagentPool 派发（吸收 dsh agent()/pipeline() 概念，非 JS 沙箱）"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-multi-agent-orchestration]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "WorkflowRunner 按 DAG 委派子智能体；子失败隔离为 None；fatal→run error；pytest 覆盖"
```
```contract-yaml
- task: "workflow 模型面工具（吸收 dsh tool-workflow，声明式 steps 替代 JS 脚本）"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-native-action-design]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "workflow 工具注册进 ToolRegistry 且执行返回 WorkflowResult JSON；pytest 覆盖"
```

## 3. 纪律（沿用 phase1-3，不得放松）

- **TDD**：每个 Task 先写失败测试 → 跑红 → 实现 → 跑绿 → 门面守卫。
- **门面守卫**：新子包 `workflow` 必须进 `LAYERS`（`test_api_facade_covers_all_layers.py` line 33-35）；
  `test_no_undeclared_layer` 扫描 `chiyu_kernel` 子包，漏登记即红灯。
- **api.py import 陷阱**：phase1/3 实测——`__all__` 已加但 `from chiyu_kernel.workflow import ...` 块**静默未插入**会致残缺。
  本阶段 T4 显式在 `plan` import 块（api.py:272）附近插入 `workflow` import 块，写完即根因核验（grep）。
- **子包 `__all__`**：只露公共 API；内部常量（`WORKFLOW_ERROR_CODES`/`WORKFLOW_STEP_STATES`）保留定义、移出 `__all__`。
- **变异自证**：T2 的「fatal 错误→整个 run `error`」判据须逐一中和→测试转红→还原转绿（参照 phase1-3 纪律）。
- **AI 不 commit**：阶段四交付后给可粘贴 PowerShell 提交块（自动定位 git.exe）。

## 4. R2 偏差登记（显式，非静默改写）

| 偏差 | dsh 原形态 | 本仓落地 | 理由 |
|---|---|---|---|
| 编排表达 | JS 脚本串（`agent()`/`pipeline()` 钩子） | 声明式 `steps`（`name`+`prompt`+`depends_on`） | 本仓无 JS 运行时；等价能力用 DAG 步骤表达 |
| 执行体 | `WorkflowEngine`（Cordis + worker-thread 进程外） | `WorkflowRunner`（复用 `SubagentPool.delegate`） | 不重复 orchestration；进程外执行非本阶段范围 |
| 工具参数 | `script`(JS string) + `meta` + `args` | `steps`(声明式) + `meta` + `args` | 同上，参数改为声明式；保留 `meta`/`args` 词汇 |

## 5. 实施修正记录（执行中回填）

- **T1 数据模型**：`workflow/__init__.py` 17 passed。含 `WorkflowStep`(depends_on DAG)+状态机、`Workflow`(Kahn 拓扑+环检测+依赖存在性校验)、`WorkflowMeta`(kebab-case 校验)、`WorkflowRunId`(NewType branded)、`WorkflowResult`/`WorkflowStopReason`、`WorkflowError`(fatal)+`WORKFLOW_ERROR_CODES`+`is_fatal_workflow_error`。
- **T2 WorkflowRunner**：`workflow/runner.py` 4 passed。复用 `SubagentPool.delegate` 按 DAG 派发子智能体；非 fatal 子失败→step 结果 `None`（隔离），fatal `WorkflowError`→run `error`，`signal.cancelled`→`cancelled`。
- **T3 工具暴露**：`workflow/register.py` 3 passed。`register_workflow_tools(reg, pool)` 注册 model-facing `workflow` 工具（参数 `meta`+`steps`+`args?`），执行经 `WorkflowRunner` 返回 `WorkflowResult` JSON（runId/agentsStarted/result/stopReason/error）。
- **T4 门面接线**：守卫测试 `LAYERS` 加 `workflow`（前期会话预写）；`api.py` import 块 + `__all__` 暴露 `register_workflow_tools`（补前期会话遗漏）。门面守卫 **7 passed**。
- **T5 E2E**：`test_harness_phase4_e2e.py` 1 passed。串联 workflow 工具→SubagentPool→plan/todo(phase2)→`render_conversation`，断言 DAG 跑通 + 结果落渲染 + `<script` 注入防护。

**回归计数（独立实跑）**
- 全量内核 `pytest packages/chiyu-kernel/tests`：**361 passed / 0 failed**（基线 336 + phase4 新增 25：T1×17 + T2×4 + T3×3 + T5×1）。
- portal 套件：**55 passed**；tools 套件：**11 passed**。合计 **427 passed / 0 failed**。
- 门面守卫 `test_api_facade_covers_all_layers.py`：**7 passed**（`workflow` 已入 `LAYERS`，无「静默未接线」）。

**变异自证（判别力，独立复现）**
- T2 判据 `runner.py:64` `if e.fatal:` 中和（`if False:`）→ `test_fatal_error_terminates_run` 转红（`completed`≠`error`）；还原→转绿；`grep` 确认 `if e.fatal:` 原始无残留。确认非假绿。

**实测偏差（已在 phase4 范围内收口，无需再批设计）**
1. **前期会话已预写部分 phase4 门面接线但未提交**（api.py 的 workflow import 块 + `__all__` 11 符号、守卫测试 `LAYERS` 加 `workflow`）；但**遗漏 `register_workflow_tools` 暴露**，导致门面守卫会报「workflow 子包 `__all__` 未全覆盖」——已在 T4 补入 import 与 `__all__`。
2. 子包 `__all__` 只露公共 API；内部常量 `WORKFLOW_ERROR_CODES` 保留定义、未进 `__all__`（与 phase2/3 纪律一致）。
3. **R2 偏差落地**：dsh 用 JS 脚本串表达编排，本仓无 JS 运行时 → 改用声明式 `steps`（`name`+`prompt`+`depends_on`）+ 复用 `SubagentPool`，已在 §4 显式登记（非静默改写）。

**提交范围说明**
- phase4 harness 相关文件：`workflow/`(3 文件) + 4 个测试 + `api.py`(含前期预写 workflow 接线+本阶段补全) + 守卫测试(含前期预写 LAYERS) + phase4 计划文档。
- 工作树另有 chiyu-cli / chiyu-portal 其他文件 / README / .gitignore 等无关 modified/untracked 改动，已**刻意排除**在 harness 提交外。
