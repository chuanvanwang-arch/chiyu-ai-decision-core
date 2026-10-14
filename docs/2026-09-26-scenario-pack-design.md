# 设计文档 · 可运行场景包（ScenarioPack）—— MCP 生成 + 客户端选择/锁定

- 日期：2026-09-26
- 状态：**待批准**（P5 闸门）
- 已批决策（本轮 AskUserQuestion）：**双入口**（向导四元组自动生成初稿 + 客户端 MCP 文件调用写包）· **P1 全量**
- 参照系：DeepSeek Harness 桌面版（能力装配 + agentPreset.select 持久化先例，`chiyu-host/methods.py:815`）

## §0 背景与目标

向导（方向/工作流/层级/模式）四元组已进入后端调用链，但选择结果**随会话消散**，不能沉淀为可复用、可运行、可锁定的资产。本设计引入**场景包（ScenarioPack）**：

1. **生成**：客户端经 MCP 文件调用写包文件；向导四元组一键合成初稿包（双入口，同一校验闸）。
2. **选择/锁定**：客户端列出包、选中装载、锁定为默认（锁定 = 写操作，带 HITL 确认）。
3. **可运行**：包内声明式 DAG steps 直接转 `Workflow`，经 `WorkflowRunner` + `SubagentPool` 真执行（非演示）。

## §1 ScenarioPack 数据模型（机制层，零领域字面量）

```json
{
  "id": "kebab-case-id",
  "name": "展示名",
  "level": "single | flow | end2end",
  "direction": "方向 id（消费方注入）",
  "mode": "standard | ptc | minimal | creative",
  "plugins": ["terminal", "loop"],
  "workflow": { "steps": [ { "name": "step-a", "prompt": "...", "depends_on": [] } ] },
  "knowledge_needs": [ { "layer": "L1", "dims": ["semantics"] } ]
}
```

校验规则（`ScenarioPackError`，错误码族对齐 workflow 风格）：

| 码 | 条件 |
|---|---|
| `PACK_META_INVALID` | id 非 kebab-case / name 空 / level ∉ 三级 / mode ∉ MODE_PRESETS |
| `PACK_PLUGIN_UNKNOWN` | plugins 含注册表外插件（`PluginRegistry.has` 校验） |
| `PACK_WORKFLOW_INVALID` | steps 空 / 步骤名重复 / `depends_on` 指向不存在步骤 / DAG 成环 |
| `PACK_NEEDS_INVALID` | knowledge_needs 的 layer ∉ {L1,L2,L3,L4} |

`to_workflow()`：pack → `chiyu_kernel.workflow.Workflow`（复用其拓扑排序 + 环检测二次兜底）。

## §2 kernel `scenario` 子包（新增）

```
packages/chiyu-kernel/src/chiyu_kernel/scenario/
├── __init__.py   # 重导出，__all__ 与门面同步
├── model.py      # ScenarioPack / ScenarioPackError / LEVEL_IDS / from_dict / to_dict / to_workflow
├── store.py      # ScenarioPackStore：目录扫描(*.json) / register / get / list / lock / unlock / select 状态
└── mcp.py        # build_in_memory_server() → InMemoryMcpServer（tools: scenario-pack-write / scenario-pack-list / scenario-pack-lock）
```

- `LEVEL_IDS = ("single", "flow", "end2end")`：机制中性枚举（与 portal `level_cards` 对齐），**非领域字面量**。
- store 锁定语义：`lock(pack_id, holder)` 幂等；已锁再锁须同 holder；`unlock` 仅 holder 或显式 force。
- ⛔ 门面同步：`chiyu_kernel/api.py` import + `\_\_all\_\_` 追加；`tests/test_api_facade_covers_all_layers.py` 的 `LAYERS` **必须登记 `scenario`**（守卫铁律：新增子包三步走）。

## §3 双入口生成通道

| 入口 | 路径 | 落点 |
|---|---|---|
| 向导初稿 | web/backend 用四元组合成 pack dict → 同一 `from_dict` 校验闸 → store 落盘 | `POST /api/scenario/generate` |
| MCP 文件调用 | 客户端 → `McpBridge(InMemoryMcpServer(build_in_memory_server()))` → 工具 `scenario-pack-write` → 同一校验闸 → store 落盘 | `POST /api/scenario/mcp-call`（真实桥路径，非旁路函数） |

两个入口共用 `ScenarioPackStore` 与校验器——**不存在第二套写包逻辑**。

## §4 web 端点与 Workbench UI

| 端点 | 语义 |
|---|---|
| `GET /api/scenario/list` | 列包（含 locked_by / selected 状态） |
| `POST /api/scenario/generate` | 向导四元组 → 初稿包 |
| `POST /api/scenario/mcp-call` | MCP 工具调用（write/list/lock，经 McpBridge） |
| `POST /api/scenario/select` | 选择装载（写会话态） |
| `POST /api/scenario/lock` | 锁定（**payload 须带 `confirm: true`**，缺失→400，HITL 闸） |
| `POST /api/scenario/run` | pack → Workflow → WorkflowRunner.run → 步骤轨迹 |

UI：Workbench 顶栏新增「场景包」选择器（列出包 + 状态徽标）；锁定按钮弹确认（HITL）；运行后步骤轨迹渲染进对话区 trace。Store 落盘目录：`web/backend/scenario_packs/`（gitignore 排除运行时包，测试 fixture 入库）。

## §5 任务分解与生命契约

以下 6 个任务由 `foundation-builder` 单智能体承接（注册表逆覆盖：本文档仅覆盖 1 个登记 agent，不触发全 roster 断言）。

### T1 kernel scenario 模型

```contract-yaml
- task: "T1 kernel scenario 数据模型（ScenarioPack/校验/错误码/to_workflow）"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-multi-agent-orchestration]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "packages/chiyu-kernel/src/chiyu_kernel/scenario/model.py 存在；from_dict 对 4 类非法输入分别抛 ScenarioPackError 且码正确；to_workflow 输出通过 Workflow 自身校验"
```

契约说明：本任务由 `foundation-builder` 承接（键 `ct-chiyu-foundation`），调用 `ai-multi-agent-orchestration`（复用 workflow 编排词汇表）、读本仓记忆（L1/L2 ≤2 跳）；成功标准 = 四类非法输入逐一抛对应错误码，合法 pack 转 Workflow 零异常。

### T2 kernel scenario store

```contract-yaml
- task: "T2 ScenarioPackStore（目录扫描/注册/锁定幂等）"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-multi-agent-orchestration]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "store.save→list→get 往返一致；lock 重复锁异 holder 抛错；unlock 非 holder 无 force 抛错"
```

契约说明：由 `foundation-builder` 承接（同键）；调用 `ai-multi-agent-orchestration`；成功标准 = 落盘往返字节级一致 + 锁定幂等/互斥语义按 §2 判据逐条可测。

### T3 MCP 工具面 + 门面同步

```contract-yaml
- task: "T3 scenario MCP 工具面（InMemory 替身）+ kernel 门面 __all__ 与 LAYERS 守卫登记"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-native-action-design]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "McpBridge.connect 后 registry 含 3 个 mcp__scenario__* 工具；经 bridge.call_tool 写包成功落盘；test_api_facade_covers_all_layers 全绿（scenario 已入 LAYERS）"
```

契约说明：由 `foundation-builder` 承接（同键）；调用 `ai-native-action-design`（MCP 工具面收敛为 3 个动作，防 CRUD 爆炸）；成功标准 = MCP 真桥路径写包落盘 + 门面守卫零红。

### T4 单测与变异自证

```contract-yaml
- task: "T4 test_scenario_pack.py 全量单测 + 变异自证"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-capability-audit]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "新增测试 ≥12 例全绿；故意删除 DAG 环检测分支后至少 1 例转红（变异自证），还原后复绿"
```

契约说明：由 `foundation-builder` 承接（同键）；调用 `ai-capability-audit`（审计判据：只跑绿不算验收）；成功标准 = 变异自证记录进测试文件注释，全量 `make test` 无回归。

### T5 web/backend 场景包端点

```contract-yaml
- task: "T5 web/backend 六端点（list/generate/mcp-call/select/lock/run）"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-native-action-design]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "curl 实测：generate→list 可见；lock 无 confirm 返回 400；run 返回每步 done/failed 轨迹"
```

契约说明：由 `foundation-builder` 承接（同键）；调用 `ai-native-action-design`（6 端点对应 6 个明确动作，拒绝进一步 CRUD 膨胀）；成功标准 = §6 验收 curl 全部通过。

### T6 Workbench 场景包选择器 UI

```contract-yaml
- task: "T6 Workbench 包选择器 + 锁定 HITL 确认 + 运行轨迹渲染"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-portal-page-generation]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "UI 选包→顶栏徽标更新；锁定弹确认后方可调用；npm run typecheck + build 全绿"
```

契约说明：由 `foundation-builder` 承接（同键）；调用 `ai-portal-page-generation`（受控组件，非 NL 直出）；成功标准 = 选择/锁定/运行三交互在预览页可复现且 typecheck/build 零错。

## §6 验收判据（全部 curl/pytest 实测，不接受「应該可以」）

1. `pytest packages/chiyu-kernel/tests -q` 全绿（含新增 ≥12 例）。
2. 门面守卫：`test_api_facade_covers_all_layers` 含 scenario 层全绿。
3. 变异自证：删 DAG 环检测 → ≥1 例红 → 还原绿。
4. 端到端 curl（经 5173 代理）：generate → list → lock(无 confirm=400 / 有 confirm=200) → run 步骤轨迹 → mcp-call 写包落盘。
5. `npm run typecheck && npm run build` 全绿。

## §7 红线（偏离即推翻）

- 内核 scenario 模块**零领域字面量**：level/mode 为机制枚举，领域 pack 只作测试 fixture。
- 写包仅一条校验闸（`from_dict`），向导入口与 MCP 入口共用。
- 锁定为写操作：无 `confirm:true` 拒绝；lock/unlock 产生审计事件（events 总线）。
- 不新增粒子类型、不改 `contract/*.py`（不触发 manifest 重生成）。
- MCP 真实 transport（stdio/HTTP）仍留 Phase 后，P1 用 InMemory 替身——与 `mcp/__init__.py` 现状一致，不虚报。

## §8 闭环回写

| task | gap_type | observed | expected | severity | ts |
|---|---|---|---|---|---|
| （待 workbench 监控回填） | | | | | |

## §9 不做（YAGNI）

- 包版本管理 / 多版本共存（P2）。
- pack 内嵌红线目录（红线仍由 TenantProfile 注入，不进包文件）。
- host RPC `scenario.pack.*` 四方法（chiyu-host 侧接线，P2 单独立项——本 P1 的「客户端」= web 门户工作台）。
- 真实 MCP stdio/HTTP transport。
