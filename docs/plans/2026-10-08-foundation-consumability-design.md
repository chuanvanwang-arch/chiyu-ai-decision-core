# 底座可消费性收口设计（统一回应 CRM / APS / enterprise 三份客户反馈）

> 状态：实施中（Phase 1 已启动：WS5 + WS4 + WS1；WS2/WS3/WS6/WS7/WS8/WS9 待 Phase 2/3）
> 日期：2026-10-08
> 方法：brainstorming（living contract）
> 受众：foundation 底座团队 + 三个消费方（CRM-ai-native / APS-ai-native / chiyu-enterprise）
> 仓边界：本设计全部落 `chiyu-foundation`（唯一事实源）；消费方文档只读、不回写。

---

## 0. 背景与总体结论

三份客户文档从三个角度描述了**同一个缺口**：foundation 是"高质量原语 + 强纪律底座"，但还不是"开箱可消费底座"。差异不在引擎逻辑缺失，而在**消费面契约、稳定承诺、标准胶水、注册表、参考实现**的缺失。逐条已做源码级核实（file:line 锚定），结论如下。

| 客户文档 | 角色 | 核心诉求 | 本设计归口 |
|---|---|---|---|
| CRM-ai-native `docs/2026-10-08-foundation-improvement-requests.md` | 生产 CRM（Node） | F-01..F-08（8 项，含 2 个 P0） | WS1 / WS4 / WS5 / WS6 / WS7 / WS8 / WS9 |
| APS-ai-native `docs/APS-治理改造/APS-对foundation改善建议.md` | 正确消费方（不平行重写） | R1..R5（5 项） | WS2 / WS4（R1/R2/R5 已落地并验证） |
| chiyu-enterprise `docs/feedback-to-foundation-2026-10-08.md` | 企业 host（平行重写） | #1..#7（7 项） | WS2 / WS3 / WS5 / WS9 |

**对客户每句话的严肃回应（含必要的诚实修正）**：

1. **CRM F-02（AGE 图=硬阻断）经核实不成立**。本仓早前已证实：Apache AGE 有官方 Python 驱动（`apache-age-python`，基于 psycopg2），且 CRM `ageGraph.js` 的 7 条边类型与 foundation `MEMORY_PREDICATES` **逐字一致**。故 F-02 是"能力待补"，不是"阻断方案 A"。WS8 提供 `GraphStore` 抽象 + 纯 PG CTE 参考实现（零新扩展依赖），AGE 封装作为消费方选项。
2. **CRM F-01 / enterprise #4 / APS R4（去 experimental）需要"建"而非"翻标志"**。`MEMORY_EXPERIMENTAL=True` 是声明态、零运行时拦截；`chiyu_kernel/memory/` 子系统当前 checkout **不在树内**（T5′ 未验收）。现在翻成 `False` 是**虚假承诺**。WS1 改为：发布"稳定子集"承诺（PgVectorStore / ontology_sync / degraded_recall / run_spine / score / redline 已 production-ready），memory-net 保持 experimental 直至 T5′ 真正建成。
3. **enterprise #1（HITL=唯一收敛阻断点）措辞过强**。企业除 HITL 外还平行重写了评分(S2)/红线(S4)。WS3 补注入式 ApprovalGate 钩子，但单靠它不会让企业弃用自建 rubric——收敛需 WS2+WS3+WS5 同时到位。
4. **APS R1/R2/R5 已落地并验证**（本会话早前完成）：`aggregate_confidence` 入门面 + `__init__` 重导出；`connect(dsn=)` 补 `validate_dsn` 拦截生产机/超级用户；`upsert_particle(dim=)` 可注入；门面 docstring 去 `⛔`。35+27 测试全绿。已并入 WS4。

---

## 1. 客户请求 → 工作流映射

| 客户请求 | 优先级 | 归口 WS | 处置 |
|---|---|---|---|
| CRM F-05 决策场景注册表单一事实源 | P1 | WS5 | 接受，Phase 1 先做（成本最低、杠杆最高） |
| CRM F-08 §13 零残留 lint | P1 | WS4 | 接受，Phase 1 |
| CRM F-01 记忆层去 experimental | P0 | WS1 | 接受（改发稳定子集承诺，不翻标志） |
| CRM F-02 图存储/AGE 等价 | P0 | WS8 | 接受（降为能力待补，非阻断） |
| CRM F-03 MCP 服务骨架 | P1 | WS7 | 接受，Phase 3 |
| CRM F-04 领域注入 SDK | P1 | WS6 | 接受，Phase 2 |
| CRM F-06 门面守卫模板 | P2 | WS4 | 接受，Phase 1 |
| CRM F-07 参考消费层 | P2 | WS9 | 接受，Phase 3 |
| APS R1 导出 aggregate_confidence | 高 | WS4 | **已落地并验证** |
| APS R2 PgVectorStore 三坑 | 中 | WS4 | **已落地并验证**（dim 可注 + connect 校验） |
| APS R3 记忆谓词 canonical writer | 中 | WS2 | 接受，Phase 2 |
| APS R4 memory experimental 边界显式化 | 低 | WS1 | 接受，并入稳定子集文档 |
| APS R5 门面 docstring 去 ⛔ | 低 | WS4 | **已落地并验证** |
| enterprise #1 HITL/ApprovalGate | P0 | WS3 | 接受（注入式可选，守自主权档位） |
| enterprise #2 谓词物化 | P1 | WS2 | 接受，Phase 2 |
| enterprise #3 标准 persister | P1 | WS2 | 接受，Phase 2 |
| enterprise #4 MEMORY_EXPERIMENTAL 对齐 | P1 | WS1 | 接受，并入稳定子集文档 |
| enterprise #5 host 参考范式 | P2 | WS9 | 接受，Phase 3 |
| enterprise #6 决策点注册表 | P2 | WS5 | 接受，并入 WS5 |
| enterprise #7 跨仓断言准确性 | 流程 | — | 已采纳：本设计所有锚点均 grep 核实 |

---

## 2. 设计原则（铁律，不可放宽）

- **P-A 内核零领域字面量**：所有 WS 新增能力不得把 CRM/APS/企业领域词焊进内核。领域经 `TenantProfile` / 场景包注入。WS2 的 `write_decision_memory_net` 以"谓词类型 + 端点"为形参，不硬编码业务边。
- **P-B 仓边界（只读消费方）**：本仓不向 `CRM-ai-native` / `APS-ai-native` / `chiyu-enterprise` 任何路径写产物。消费方经契约 `register_scenario` / `TenantProfile` / `McpServer` 接入，自行在其仓内 adopt。
- **P-C 稳定承诺 vs 实验态**：可承诺的子集必须真有测试守护（幂等写、维度约束、召回降级语义）；实验态不得进硬验收判据/对外交付承诺。
- **P-D 注入式、默认透传**：脊柱/store 的所有"消费方钩子"（ApprovalGate、persister、auth）默认 `None`/透传，绝不强制，以守自主权档位（B 全自主夜批）。

---

## 3. 分阶段路线

```
Phase 0（就绪性，已完成）
  ├─ F-02 AGE Python 等价核实（非阻断）
  ├─ MEMORY_EXPERIMENTAL 声明态核实（去实验=建 T5′，非翻标志）
  └─ APS R1/R2/R5 已落地验证
Phase 1（低险高杠杆，先做）  → WS5 + WS4 + WS1
Phase 2（标准胶水）          → WS2 + WS3 + WS6
Phase 3（能力补全）          → WS8 + WS7 + WS9
```

---

## 4. 逐工作流设计（含 living contract）

### WS1 · 稳定子集承诺与实验态边界（foundation-builder）

发布 `docs/capability-matrix.md`：列 stable 子集（PgVectorStore / ontology_sync / degraded_recall / run_spine / score_rubric / evaluate_redline / aggregate_confidence）与 experimental 子集（memory-net / M 层闭环，T5′ 未验收）。`MEMORY_EXPERIMENTAL` 保持 `True`，注释补边界清单。对外文案纪律已在 `MEMORY.md` 固化（提"决策记忆网"须声明 experimental）。

```contract-yaml
- task: "WS1 发布稳定/实验子集能力矩阵"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-capability-audit, ai-memory-lifecycle]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "docs/capability-matrix.md 发布且列出 stable/experimental 两栏；MEMORY_EXPERIMENTAL 仍为 True 且注释列明边界；grep 全仓无 '决策记忆网已落地' 类越权表述"
```

### WS2 · 决策持久化与记忆网标准胶水（foundation-builder）

ship `PgVectorStorePersister`（`SpineResult`→`particle`/`SpineResult`/audit 映射 shim）+ `write_decision_memory_net(...)`（7 谓词 canonical writer，形参化、零领域字面量）。域 Agnostic。

```contract-yaml
- task: "WS2 标准 persister + 记忆网 writer"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-ontology-vector-build, ai-memory-lifecycle, ai-native-action-design]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "PgVectorStorePersister 与 write_decision_memory_net 落库 examples/reference-consumer 可跑；新测试断言 SpineResult 经 persister 落 particle 表、7 谓词经 writer 物化；源码零领域字面量（grep 契约外业务词=0）"
```

### WS3 · 脊柱注入式 ApprovalGate（foundation-builder）

`run_spine` 增可选 `approval_gate` 形参（默认 `None`=透传），在 S4→S5 间触发；配 audit 留痕 + event hook。守自主权档位。

```contract-yaml
- task: "WS3 脊柱注入式 ApprovalGate 钩子"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-multi-agent-orchestration, ai-event-driven-evolution]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "run_spine 新增 approval_gate 形参（默认 None 透传）；注入式 gate 拒绝时 persisted=False 且 audit 留痕；新测试断言 gate 注入/不注入两路径均绿"
```

### WS4 · 门面完整性、守卫模板与 §13 lint（foundation-builder）

APS R1/R2/R5 已落地验证。补：`tools/check_facade_coverage.py`（可复用门面守卫模板，输入=消费层暴露面清单，未暴露即红）+ `tools/check_zero_residue.py`（§13 禁用标记词表扫描，命中即非零残留）。接入 `make lint`。

```contract-yaml
- task: "WS4 门面守卫模板 + §13 零残留 lint"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-capability-audit]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1], max_hops: 2 }
  success: "tools/check_facade_coverage.py 与 tools/check_zero_residue.py 落地并接入 make lint；新测试断言守卫自身有判别力（故意删一个导出→判红、注入 ⛔ 标记→判红）"
```

### WS5 · 决策场景注册表单一事实源（foundation-builder）

`register_scenario(key, profile)` + `list_scenarios()` 落地于 contract；未注册键在 `produceDecision` 首调抛 `ValueError`（非运行期静默 throw）；键格式（连字符）门面守卫。根治 CRM 三态键分裂（`config_change`/`config-change`/`llm-config-change`）。

```contract-yaml
- task: "WS5 决策场景注册表单一事实源"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-native-action-design, ai-particle-system-design]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "register_scenario/list_scenarios 落地；未注册键首调抛 ValueError；键格式守卫接门面；examples/reference-consumer 经注册表驱动决策，无散落硬编码键"
```

### WS6 · 领域注入 SDK / TenantProfile 模式（foundation-builder）

官方"领域注入三件套"：`TenantProfile` 载体 + 动态粒子/动作注册 API（`ActionRegistry` 机制非清单）+ `ScenarioPack` 骨架。给出消费层最小目录约定（哪些放 kernel、哪些放消费层）。

```contract-yaml
- task: "WS6 领域注入三件套 SDK"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-particle-system-design, ai-native-action-design]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "TenantProfile + 动态粒子/动作注册 API + ScenarioPack 骨架落地 examples/；参考消费层经 TenantProfile 注入示例域、零改内核；新测试断言内核无新增领域字面量"
```

### WS7 · MCP 服务骨架（foundation-builder）

`McpServer` 骨架：transport http/stdio、可插拔 auth 中间件（Bearer/api_token/OAuth2）、工具注册守卫（注册即进门面、未注册即告警）、两阶段 confirm + 零信任写入抽为可复用装饰器。

```contract-yaml
- task: "WS7 生产级 McpServer 骨架"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-native-action-design, ai-multi-agent-orchestration]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "McpServer 骨架落地（http/stdio + 可插拔 auth + 工具注册守卫 + 两阶段 confirm 装饰器）；examples/reference-consumer 经它暴露工具；守卫断言未注册工具告警"
```

### WS8 · 图存储抽象 / AGE 等价（foundation-builder）

`GraphStore` 抽象（节点/边/属性/遍历）+ 纯 PG CTE 参考实现（零新扩展依赖），可选 AGE 封装文档。覆盖 CRM 关系图最小算子（节点/边增删、一/二跳邻居、属性过滤）。

```contract-yaml
- task: "WS8 GraphStore 抽象 + 纯 PG 参考实现"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-ontology-vector-build, ai-particle-system-design]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "GraphStore 抽象 + 纯 PG CTE 实现（节点/边/一二跳邻居/属性过滤）落地；CRM 7 边类型映射样例；可选 AGE 封装文档；新测试断言最小算子集可跑"
```

### WS9 · 参考消费层（foundation-builder）

`examples/reference-consumer`：端到端最小闭环（run_spine + TenantProfile 注入 + McpServer 暴露 + PgVectorStore 持久化）。同时作为 WS5/WS6/WS7 样板。

```contract-yaml
- task: "WS9 参考消费层端到端样板"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-particle-system-design, ai-native-action-design, ai-event-driven-evolution]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "examples/reference-consumer 跑通 run_spine+TenantProfile+McpServer+PgVectorStore 闭环；作为 WS5/WS6/WS7 落地样板；新测试端到端绿"
```

### 消费方接入契约 · APS（consumer-integrator）

APS 经新能力 adopt：移除 `kmd.py:455-458` 差异登记注释、切到 `aggregate_confidence`；经 `PgVectorStorePersister` 持久化；不消费 foundation memory 为 deliberate 选择（文档记录，非缺口）。

```contract-yaml
- task: "consumer-integrator APS 侧 adopt"
  contract_task_id: ct-aps-consume
  agent: consumer-integrator
  skills: [ai-particle-system-design, ai-context-layering, ai-capability-audit]
  memory: [APS-ai-native]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "APS kmd.py:455-458 差异登记注释移除并切到 aggregate_confidence；经 PgVectorStorePersister 持久化；memory 不消费为 deliberate 记录在案（APS 仓内自改，本仓不回写）"
```

### 消费方接入契约 · enterprise（enterprise-platform-builder）

enterprise 经新能力收敛：run_spine 接线 + persister 接 PgVectorStore + ApprovalGate 注入 + 决策点经 `register_scenario` 注册；平行 `orchestrator` 退化为薄封装或移除。

```contract-yaml
- task: "enterprise-platform-builder 侧 adopt"
  contract_task_id: ct-chiyu-enterprise
  agent: enterprise-platform-builder
  skills: [ai-particle-system-design, ai-ontology-vector-build, ai-memory-lifecycle, ai-native-action-design, ai-multi-agent-orchestration, ai-event-driven-evolution, ai-capability-audit]
  memory: [chiyu-foundation, enterprise-platform]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "enterprise 经 run_spine+PgVectorStorePersister+ApprovalGate+register_scenario 收敛；平行 orchestrator 退化为薄封装；enterprise 仓内自改，本仓不回写"
```

---

## 5. 决策与待确认

- **D1（去实验态）**：不翻 `MEMORY_EXPERIMENTAL=False`；改发稳定子集承诺，memory-net 保持 experimental 至 T5′ 真正建成。（诚实，避免虚假承诺）
- **D2（F-02 图）**：先行纯 PG CTE 参考实现（零新扩展依赖），AGE 封装作为消费方选项；F-02 由"阻断"降为"能力待补"。
- **D3（已落地）**：APS R1/R2/R5 本会话已落地验证（35+27 测试绿），并入 WS4，不再重复实施。
- **D4（仓边界）**：所有代码/文档落本仓；consumer-integrator / enterprise-platform-builder 两块为"消费方接入契约"，由消费方在其仓内自改，本仓不回写。

---

## 6. 闭环回写（待实施期填充）

| task | agent | gap_type | observed | expected | ts | severity |
|---|---|---|---|---|---|---|
| （实施期由 agent-workbench 监控写入） | | | | | | |

---

## 7. 移交

设计批准后，移交 `writing-plans` 按 Phase 1→3 拆任务；每个任务继承上述 §4 living contract（契约键不变）。
