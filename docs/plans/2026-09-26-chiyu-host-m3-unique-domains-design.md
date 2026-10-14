# chiyu-host M3：本平台独有域（decision / memory / tables）设计

> 阶段：brainstorming（P8 用户批准 2026-09-26；契约校验 valid exit 0；判别力自证通过）
> 关联：M1 全量域（ffff599/22b0f24/7c292c9）、M2 goal 域（T3/3e98112）、T4 session.prompt L1–L2 装配（862c5c3）。
> 契约键：`foundation-builder` → `ct-chiyu-foundation`（授权层 L1–L2，不越界 L3/L4）。
> 校验：`node C:/Users/wangchuan08/.workbuddy/skills/brainstorming/scripts/validate-contract.mjs <doc> --registry contract/contract-ids.json`

## §1 目标与范围

把 chiyu-host 的 RPC 面补齐**本平台独有、DSH schema 不含**的三域，使 DSH client 能统一调用底座的：

- **tables**：粒子 substrate 的 schema 注册表（粒子类型 / 属性类型 / 谓词）。
- **memory**：记忆生命周期（双轨 append-only log + note，六元组寻址）。
- **decision**：决策脊柱契约（S1→S5 不可重排）反射 + 决策记录投影。

三域均**不连 pg**（沿用 M1/M2 纪律：测试环境无 pg，直接 import 内核子模块绕过 api 门面）；写域走 **session 投影桥接**（同 M2 goal 模式），只读域走 **契约常量反射**（完全真实、零 pg）。

## §2 现状盘点（源码核实，防假绿）

| 域 | 内核真实资产 | 运行时 engine？ | M3 落点 |
|---|---|---|---|
| tables | `contract/particle.py`（ParticleTypeSet / PredicateSet / CORE_ROLES / ATTR_TYPES / MEMORY_PREDICATES）、`ontology/particle.py: Particle` | 无（仅形态契约 + `PgVectorStore.upsert_particle` 需 pg） | 反射 `contract.particle` 常量，零 pg |
| memory | `contract/memory.py`（MEMORY_KINDS / MEMORY_ADDRESS_KEYS 六元组 / 双时钟） | 无（落点=粒子 substrate `particle(type='memory',layer='L2')`，需 pg） | session 投影桥接（append-only 索引 + 事件） |
| decision | `contract/decision.py`（SPINE_ORDER / RUBRIC_KEYS / EIGHT_ELEMENTS / SEVEN_DIMS / AUTONOMOUS_GATE_EXPR） | 无（K-M-D 引擎不在内核运行时；decision 是 CORE_ROLES 之一 + M 层谓词） | 只读反射 SPINE 常量 + session 投影决策记录 |

**结论**：三域内核侧皆无独立运行时 engine；M3 只能以「契约反射 + session 投影」形式暴露，不能假装调用不存在的 engine。

## §3 方案（3 候选 → 选定 A）

- **A（选定）反射 + session 投影桥接，不连 pg**：只读域直接 import `chiyu_kernel.contract.*` 反射真实常量；写域（`memory_write` / `decision_record`）用模块级 in-memory 索引 + session 事件投影，复用 M2 goal 的 `_goal_index` / `_goal_publish` 范式。优点：零 pg 依赖、测试可跑、与 M1/M2 一致、不假绿。
- **B（否决）pg 直连**：经 `PgVectorStore` 真读真写粒子表。否决理由：测试环境无 pg，会红或需起容器，破坏 M1/M2 已建立的「不连 pg」纪律；且 memory/decision 的「真实落库」应由消费方在 L4 profile 注入后由内核 store 负责，chiyu-host 不应越权直写 pg。
- **C（否决）新建内核 DecisionEngine/MemoryStore 类**：超出 chiyu-host 范围（属内核演进，须独立 brainstorming）。M3 仅做 RPC 暴露，不新增内核类。

### §3.1 新增 RPC 面（6 方法）

**tables（只读，反射 contract.particle）**
- `table_list(payload)` → 枚举 CORE_ROLES 五个规范粒子表（unstructured_asset/entity/decision/memory/knowledge），每项含 `layers`、`attr_types` 摘要、`predicates` 计数。当 chiyu-host 注入了 profile，则改枚举 `profile.particle_types.names` + `profile.predicates.all()`；未注入（测试默认）回退 L0 常量。
- `table_describe(payload)` → 单表全 schema：19 种 ATTR_TYPES 全集、`EDGE_LAYERS`/`EDGE_SOURCES`/`CARDINALITIES`、`PredicateSet` 中关联该表的谓词。

**memory（session 投影桥接，仿 goal）**
- `memory_write(payload)` → 六元组寻址（`topic/layer/anchor_kind/anchor_id/actor/occurred_at`）严写：缺任一项 ⇒ 拒写（strict，不静默兜底）；追加到 `_memory_index[sid]`（append-only 日志 + note 双轨），emit `memory/write` 事件到 session log。
- `memory_read(payload)` → 按 `topic`/`anchor_id` 过滤回读该 session 记忆；emit `memory/read` 事件。

**decision（只读反射 + 投影桥接）**
- `decision_spine(payload)` → 只读反射 `contract.decision`：`SPINE_ORDER`（S1→S5 不可重排）、`RUBRIC_KEYS`、`EIGHT_ELEMENTS`、`SEVEN_DIMS`、`AUTONOMOUS_GATE_EXPR`、`AUTONOMOUS_RELEASE_DEFAULT`。完全真实，零 pg。
- `decision_record(payload)` → 创建/读取决策记录（session 投影，仿 goal）：`id=f"decision:{sid}"` + revision 乐观锁；`objective`/`rationale`/`stage` 字段；emit `decision/record` 事件。诚实声明：本 RPC 是决策**记录投影**，不运行 K-M-D 引擎。

### §3.2 红线与护栏

- M3 写域（memory_write / decision_record）是 **session 局部投影**，不触碰内核 baseline ⇒ 不触发 `META_REDLINES`（threshold_widen/baseline_write/redline_auto）；`redline_guard` 不接线（与 goal 同）。
- 契约 scope 收敛 L1–L2（foundation-builder 授权层），不暴露 L3/L4。
- 复用 `to_wire_session_event` + `_bus.publish` 做事件扇出（同 T4）。

## §4 双轨契约（living contract）

```contract-yaml
- task: "M3-tables 粒子 schema 反射 RPC（table_list/table_describe）"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-particle-system-design, ai-ontology-vector-build]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "table_list 返回 ≥5 个 CORE_ROLES 粒子表且 table_describe 含 attr_types 与 predicates（零 pg 依赖）"
```

```contract-yaml
- task: "M3-memory session 投影桥接（memory_write/memory_read）"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-memory-lifecycle]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "memory_write 按六元组严写并 emit memory/write 事件；memory_read 回读且缺项拒写（变异：去掉六元组校验→测试转红）"
```

```contract-yaml
- task: "M3-decision 脊柱反射 + 记录桥接（decision_spine/decision_record）"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-context-layering, ai-capability-audit]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "decision_spine 反射 SPINE_ORDER+RUBRIC 常量；decision_record 创建/读取经 session 投影且 emit decision/record 事件"
```

## §5 测试方法（判别力自证，防假绿）

- tables：断言 `table_list` 含全部 5 个 CORE_ROLES；`table_describe('decision')` 含 `DECIDED_ON` 等 M 层谓词。
- memory：**变异自证**——移除六元组缺项拒写分支 → `memory_write` 缺项测试转红；再还原。
- decision：**变异自证**——移除 `decision/record` 事件 emit → 判别项转红；`decision_spine` 断言 `SPINE_ORDER[0]=='S1_context'` 且长度 6。
- 全量目标：`pytest packages/chiyu-host/tests` 由 39 → **45 passed**（原 39 + 6 新增判别项，零回归）。

## §6 提交计划（分层、显式路径、单行 -m）

- `T5` 实现：methods.py 三域 6 方法 + 模块级 `_memory_index` / `_decision_index` 索引 + dispatch 注册 → `git add` 仅 methods.py 与新增测试。
- `docs` 回填：R3 矩阵 `docs/plans/2026-09-25-dsh-client-r3-coupling.md` §6 回填 M3 已真对接。
- 提交纪律：每 Task 一 commit，前缀 `T5:`/`docs:`，尾部附实测计数；禁用 `git add -A`；零 remote。

## §7 闭环回写（P10 监控矩阵占位）

| task | gap_type | observed | expected | ts | severity |
|---|---|---|---|---|---|
| M3-tables / memory / decision | success | （待 workbench 监控） | 6 方法全绿 + 变异自证通过 | — | — |
