# 底座成熟度蓝图（吸收专利蓝图 + 10 ai_* SKILL 方法论）

> 状态：草案（待确认后并入 Phase 2 / Phase 3 实施）
> 日期：2026-10-09
> 方法：brainstorming（living contract，契约键复用 `ct-chiyu-foundation`）
> 受众：foundation 底座团队 + 三个消费方（CRM-ai-native / APS-ai-native / chiyu-enterprise）
> 仓边界：全落 `chiyu-foundation`（唯一事实源）；消费方文档只读、不回写。
> 披露纪律（§13）：本文件已中性化——不配对任何权属/品牌字样与专利级代号；方法论仅作跨域通用范式引用。

---

## 0. 吸收结论（已全量完成）

| 来源 | 吸收内容 | 在底座中的角色 |
|---|---|---|
| 专利族 N（单库多轨收口） | 四轨同库 + 统一向量策略注册表 + 统一降级协议 + 跨轨一致性校验 + 只读派生消费视图 | **总架构原则**，约束 WS2/WS8 的存储布局 |
| 专利族 A（决策引擎） | 九尺子混合裁决 + 红线优先 + 决策落库 + 置信度反算校准 | WS3 红线闸 + 决策持久化 schema |
| 专利族 B（双轨记忆） | append-only 日志轨 + upsert 笔记轨 + 四闸门 + 周期蒸馏 + 混合召回 + 七维校验 | WS2 记忆网 writer 的写入纪律 |
| 专利族 F（K-M-D 管道） | 供给注入契约 + 闭环回流三段改写 + 租户作用域隔离 | WS2/WS6 的闭环回写机制 |
| 专利族 G（写库即构建） | 写时三钩子 + contentHash 幂等 + 双 provider 降级显式留痕 + 受控边六映射 + backfill | WS2 persister 写通路的实现纪律 |
| 专利族 H（单源双视图） | 单源四表 + 时间线叙事视图 + 关系图谱视图 + 决策回链审计 | WS8 GraphStore 的只读派生契约 |
| 10 ai_* SKILL（#1–#10） | 粒子/向量/上下文/记忆/Action/编排/进化/门户/反馈/审计 的方法论 + 护栏 | 各 WS 的**构建方法论**与**反假绿/闭环/护栏纪律** |

> 吸收方式：中性化、抽取跨域通用方法论。绝不在可exportable 表面（门面 docstring / 展示页 / ppt）把专利级代号与权属/品牌配对（守 `tools/check_zero_residue.py` 拦截口径）。

---

## 1. I1–I3 决策（直接回应）

CRM 提出的 I1–I3 即本设计 §4 的 WS8 / WS7 / WS6。结论如下。

| 项 | 对应 WS | 决策 | 理由 |
|---|---|---|---|
| **I1 图存储 / AGE 等价** | WS8 | **做（基础能力，确认你的判断）** | 图查询是「粒子–关系–决策」单源双视图（H）的只读派生面，每个消费方都要基于关系边（受控谓词 E1–E7）做一/二跳邻居、时间线叙事、决策回链审计。把它收进底座，消费方不必各自接 AGE 或自建图库（那正是「为底层浪费时间」的典型）。**实现策略**：先纯 PG CTE 参考实现（零新扩展依赖），AGE 封装作为消费方可选；F-02 由「阻断方案」降为「能力待补」，已核实 AGE 有官方 Python 驱动、且 7 边类型与 `MEMORY_PREDICATES` 逐字一致。 |
| **I2 MCP 服务骨架** | WS7 | **做（Phase 3 输出面）** | 它是底座「稳定的输出」通道——把 `run_spine` / `PgVectorStore` / `TenantProfile` 注入等能力以 MCP 工具面暴露给消费方，消费方零改内核即可接入。今天消费方可直连 kernel，但 MCP 骨架提供**统一 auth + 工具注册守卫 + 两阶段确认零信任写入**，是「稳定的输出」的正式形态。优先级低于 I3（I2 是出口、I3 是入口胶水）。 |
| **I3 领域注入 SDK** | WS6 | **做（Phase 2 关键石，优先级最高）** | 它是「让他们不再为底层浪费时间」的**真正瓶颈**。没有 `TenantProfile` + 动态粒子/动作注册 + `ScenarioPack` 骨架，每个消费方都在各自仓里重造领域注入逻辑、重踩维度/红线/场景键分裂的坑。WS6 把「领域字面量如何注入内核」做成官方三件套 + 最小目录约定，消费方照模板填即可。**这是消除重复劳动、让消费方快速落地的最高杠杆项。** |

**建议优先级**：I3（WS6，关键石）≫ I1（WS8，基础能力）> I2（WS7，输出面）。即 Phase 2 先做 WS6/WS2/WS3，Phase 3 再做 WS8/WS7/WS9。

---

## 2. 蓝图 → WS 增强映射（客户反馈之外，蓝图补强的点）

客户反馈（CRM F-* / APS R* / enterprise #*）定义了「做什么」；专利蓝图 + 10 SKILL 定义了「做到什么程度才算成熟」。逐 WS 增强：

### WS2 · 标准 persister + 记忆网 writer（蓝图书：N/B/F/G）
客户反馈只要求「`SpineResult`→落库 + 7 谓词物化」。蓝图要求它** embody 四套纪律**：
- **N 四轨同库**：persister 落库走 `particle` / `decision` / `memory_log` / `notes` 同源事务，不另起可写存储（否则必漂移）。
- **B 双轨四闸**：`memory_log` append-only、`notes` upsert；写前过 `judgeWorthiness` 四闸门（凭证硬拒 / 显式优先 / 瞬态噪声 / 价值视界）。
- **F K-M-D 三段改写**：决策结果回流走 `closureLoop` 三段（知识校准补丁经 PRESCRIBABLE 白名单 / 复盘记忆 append / 偏差校验 `hindsight_delta`）。
- **G 写时三钩子 + 幂等 + 降级留痕**：`ensureEmbedding` / `ensureTsVector` / `ontologySync` 三钩子；`contentHash` 判变幂等；双 provider 降级必须显式 `degraded:true`，**禁伪健康**。

### WS3 · 注入式 ApprovalGate（蓝图书：A + ai-feedback-loop 金律26）
客户反馈只要求「`run_spine` 增 `approval_gate` 形参」。蓝图要求它**编码硬约束先于置信度**：
- 红线命中即强制 HITL、屏蔽自主放行，不因置信度高而豁免（金律26 顺序：硬约束闸 → 置信度 → 放行）。
- 守卫优先级高于出方规则；`persisted=False` + audit 留痕，守自主权档位（B 全自主夜批）。

### WS6 · 领域注入 SDK（蓝图书：粒子系统 #3 + Action #5）
客户反馈已对齐。蓝图补强：**粒子注册须用机制非清单**（动态 `ActionRegistry`，新增粒子/动作只注册不硬编码）；`ScenarioPack` 骨架须含受控谓词边 E1–E7 的声明位；注入值经 `TenantProfile` 单一事实源，内核零领域字面量（由 `tools/check_facade_coverage.py` + 零残留 lint 守）。

### WS7 · MCP 服务骨架（蓝图书：门户 #8 v0.2 双输出同源 + 零信任）
蓝图补强：**能力暴露面 = 机器可读 MCP Resources 与 HTML 同源**（v0.2 架构铁则①），禁止只暴露给人看的页面让 Agent 用 Computer Use 去读；两阶段 `confirm_token` 零信任写入抽为可复用装饰器；工具注册即进门面守卫（未注册即告警，防「暴露≠可调用」）。

### WS8 · GraphStore 图存储（蓝图书：H 单源双视图）
客户反馈已对齐（纯 PG 先行）。蓝图补强：**GraphStore 是只读派生**，数据来自 `particle` + `decision` + `memory_log` 同库，禁止另起可写图库；必须支持两套视图——时间线叙事视图（`DECISION_TIME_BASIS` 四源只读聚合）+ 关系图谱视图（受控边 E1–E7）；决策回链审计（Q1–Q4 可答）。

### WS9 · 参考消费层（蓝图书：反馈闭环 #9 + 审计 #10）
蓝图补强：样板不止「跑通」，须带**反假绿探针**（见 §3）——证明决策真落库、记忆真物化、图真派生，而非「表有行即判已接通」。

---

## 3. 横切成熟度闸（从 10 SKILL 提炼，写进每个 WS 收口标准）

每个 WS 在「测试绿」之外，必须过以下闸，否则判为「假绿」：

1. **反假绿探针（ai-capability-audit）**：每个落地能力带一个**可证伪探针**——真缺陷时必 FAIL、修复后必 PASS；「字段非空 / count>0 / 无报错」恒绿禁止作唯一判据。须做**变异自证**（故意删判据分支→探针变红，再还原）。
2. **闭环连通性（ai-feedback-loop 八边）**：WS2/WS6 须验 K-M-D 八边（K→D / M→D / D→M / D→K / 结果→D / 校准 / 参数生效 / M→K）逐边接通，非空即绿判据排除。
3. **写时物化归因（G / ai-memory-lifecycle）**：`contentHash` 幂等判变；双 provider 降级显式 `degraded:true` 留痕；归因写时物化，禁事后重算（金律20）。
4. **硬约束先于置信度（A / 金律26）**：WS3 红线命中即 HITL，不因置信度豁免；任一自动放行决策须能答「过了哪几道硬闸 / 置信度多少 / 不过闸会怎样」。
5. **单源双视图（H）**：WS8 只读派生，禁另起可写存储；跨轨一致性校验 missing 禁止脑补（N）。
6. **真实供给驱动（金律23）**：健康度/覆盖率由真实命中数据驱动，声明即绿（已注册≠已供给）判缺口。

---

## 4. 执行顺序与收口标准

```
Phase 0（就绪，已完成）：F-02 AGE 核实 / MEMORY_EXPERIMENTAL 声明态核实 / APS R1-R2-R5 落地
Phase 1（已启动）：WS5 + WS4 + WS1（420 测试绿）
Phase 2（建议立即开始）：
   WS6 领域注入SDK（关键石，I3）           ← 最高杠杆
   → WS2 标准persister + 记忆网writer（I3 的落库侧，embody N/B/F/G）
   → WS3 注入式ApprovalGate（I1 红线闸，embody A + 金律26）
Phase 3（Phase 2 稳定后）：
   WS8 GraphStore（I1，embody H 单源双视图）
   → WS7 MCP 服务骨架（I2，embody 零信任 + v0.2 双输出）
   → WS9 参考消费层（端到端样板 + 反假绿探针）
```

**每个 WS 收口三件套**：① 测试绿（幂等写 / 维度约束 / 召回降级）② 反假绿探针绿（变异自证）③ 零领域字面量 grep=0（守 P-A 内核纪律）。

---

## 5. 范围研判：是否需要扩大底座边界？（2026-10-09 追加）

### 5.1 结论

**不需要扩大子系统范围。** 需要做的是「补全一个真缺口 + 加深已有模块的纪律 + 把稳定子集暴露出来」。

判定依据（已对内核树 `packages/chiyu-kernel/src/chiyu_kernel/` 全量盘点）：专利族 N/A/F/G/H 的**运行期模块骨架大多已在树内**，并非空白。

| 专利族 | 在树模块（已存在） | 状态 |
|---|---|---|
| N 单库多轨收口 | `store/`（conn/ddl/dsn/pg_store，四轨同库 DDL） | 在树 |
| A 决策引擎 | `llm/`（tier=九尺子分层）+ `contract/decision`（redline/score）+ `audit/chain`（决策落库回链）+ `api.run_spine` | 在树（WS3 加深 ApprovalGate） |
| B 双轨记忆 | **`memory/` 不在树**（capability-matrix §2：T5′ 未验收、checkout 缺失） | **唯一真缺口 → WS2** |
| F K-M-D 管道 | `evolution/`（guard/knob/prescription=校准补丁/replay=回测/readiness/skill_draft） | 在树（待 WS2 核实与 memory 写回接线） |
| G 写库即构建 | `ontology/`（backfill/hooks/graph）+ `vector/`（embedding/onnx_runner/coverage）+ `store/ddl`（ensureEmbedding/ensureTsVector） | 在树 |
| H 单源双视图 | `ontology/graph.py`（图谱视图）+ `store/`（同源四表） | 在树（WS8 形式化为只读 GraphStore） |

**10 ai_* SKILL 的方法论落点**：#1 向量(#1)/#2 记忆(#2)/#3 粒子(#3)/#4 上下文(#4)/#5 Action(#5) 已在树；#6 编排/#8 进化/#9 反馈/#10 审计 由 `orchestration/`+`workflow/`+`events/`+`evolution/`+`tools/check_*` 提供**原语**（方法论是消费方组合期裁决，非运行期代码）；#7 门户页面为**消费方层**，内核仅给 `plugins/modes` + WS7 暴露面。

### 5.2 战略重判：痛点是「包装/稳定性」，不是「范围」

消费方（chiyu-enterprise）重造决策编排器与 store，根因是**内核已在树模块未暴露为稳定子集、未打包**（见 enterprise 反馈文档 #7）：消费方直连 kernel 时找不到官方 `PgVectorStorePersister`/`TenantProfile` 注入样例/`McpServer` 骨架，被迫自建。

⇒ 「让他们不再为底层浪费时间」的杠杆 = **WS6/WS7/WS8 把已在树能力打包成稳定、有 SLA、零改内核即可用的输出面**，而非新增子系统。

### 5.3 纳入边界（动词/机制 ∈ 底座，名词/内容 ∈ 消费方）

**纳入（且已在树，需加深/补完）**：
- 领域无关底层机制：存储、向量、本体、记忆、决策脊柱、情境装配、Action 注册、场景注册、事件总线、进化/闭环、审计链、MCP/门户暴露面。

**不纳入（边界外）**：
1. **SKILL 的交互流程本身** → 保持为方法论 SKILL，不转译成代码模块。它们是设计期裁决智慧，不是运行期原语；其原则通过 §3 横切成熟度闸渗进代码，而非 import 进内核。
2. **领域内容**（粒子取值 / 红线目录 / 知识谓词取值）→ 消费方经 `TenantProfile` 注入，内核零领域字面量（铁律）。
3. **应用组合层**（多智能体拓扑 / 门户页面渲染 / 具体事件排程）→ 消费方在其仓组合，内核只给原语。
4. **具体场景决策逻辑**（rubric 权重 / 红线项）→ 消费方注入；内核只给裁决框架（九尺子求值器 + 红线检查器 + 置信度反算）。

**边界判据（一句话）**：内核拥有「动词/机制」（每个 AI-native 应用都需要的领域无关底层）；消费方拥有「名词/内容」（领域取值 + 应用组合）。越此界即违反内核零领域字面量铁律，且把底座膨胀成又一个应用。

### 5.4 对「尽量纳入」的修正

不取「尽量纳入」——盲目扩大范围会 ① 违反内核零领域字面量铁律 ② 把底座膨胀成应用 ③ 与已在树模块重复。
正确做法：**该纳入的已在树内、需补的只有一个（B 记忆运行时）、其余靠「暴露稳定子集（WS6/7/8）+ 加深纪律（§3 横切闸）」兜底。**

---

## 6. 确认记录（2026-10-09 用户「同意」）

- **§5 范围边界已采纳**：不扩大子系统范围；只补 B 记忆运行时（WS2）+ 加深已有模块纪律 + 暴露稳定子集（WS6/7/8）。SKILL 交互流程与方法论不转译进内核代码；领域内容经 `TenantProfile` 注入，内核零领域字面量。
- **Q1 已采纳**：执行顺序 Phase 2（WS6→WS2→WS3）先于 Phase 3（WS8→WS7→WS9）。
- **Q2 已采纳**：I1 图存储「纯 PG CTE 先行、AGE 封装可选」，零新扩展依赖。
- **Q3 已采纳**：横切成熟度闸（§3 六条）作为 WS2–WS9 统一收口门槛（反假绿探针 + 变异自证 + 零领域字面量 grep）。

> 确认后并入 `2026-10-08-foundation-consumability-design.md` 的 Phase 2/3 路线，移交实施（writing-plans 拆 Phase 2 任务）。

---

## 7. 执行记录（Phase 2 启动）

### 7.1 WS6 领域注入 SDK（关键石）— 已完成 2026-10-09

- 新建 `packages/chiyu-kernel/src/chiyu_kernel/domain/__init__.py`：
  - `profile_from_dict(d)`：dict → `TenantProfile`（L4 域内容经此进入内核唯一通道；机制非清单，具体取值由消费方提供）。
  - `inject_domain(*, profile, actions=(), scenarios=(), plugin_registry=None)`：唯一注入闸，四道闸（profile 构造 / ActionRegistry 注册+audit R1–R6 / ScenarioPack from_dict / 跨一致性），返回 `DomainBundle`。
  - `DomainBundle`、`DomainInjectionError`（聚合错误，机器可路由）。
- `scenario/model.py`：`ScenarioPack` 补 `controlled_edges` 声明位（受控谓词边形状校验）+ `to_dict` 回写；跨一致性闸在 `inject_domain` 统一校验（from_dict 拿不到 profile，故不放进场景层）。
- 门面 `api.py`：`domain` 四符号进 `__all__`；`Makefile` lint `--layers` 与 `test_api_facade_covers_all_layers.LAYERS` 增 `domain`（pytest 守卫自动枚举磁盘子包，强制登记）。
- 测试 `tests/test_domain_injection.py`（7 个）：happy path + 4 个反假绿探针（profile 缺核心角色 / R5 capability 冲突 / 边谓词不在 profile / 边类型不在 particle_types）。
- **变异自证**：临时禁用跨一致性闸 → 两探针转红（DID NOT RAISE）→ 还原。证明探针非恒绿。
- 验收：全量回归 **427 passed**；`make lint` 门面覆盖「0 处未暴露」、零残留「0 处」、判别力自证通过。
- 越界守护：未碰 `contract/`（不触发 `manifest.json` 重生成）；零领域字面量 grep 通过。

### 7.2 WS2 标准 persister + 记忆网 writer — 已完成 2026-10-09

- 新建 `packages/chiyu-kernel/src/chiyu_kernel/persist/__init__.py`：
  - `PgVectorStorePersister(store, profile, *, onto=None, event_bus=None, materialize=True)`：S5_persist 回调 shim。`persist(result, *, policy_version, concept_refs, disposition, subject_id, tenant_id, occurred_at, references)` 经同一 `PgVectorStore` 落 **event（event_type='decision'，payload jsonb）** + upsert **particle（type='decision'，L1 锚点）** + `write_decision_memory_net` 写 **7 谓词边（graph_edge）**。决策落库走现有 `event` 表（H 单源双视图、禁另起可写存储、符合零建表铁则）。
  - **不反向依赖 `chiyu_decision`**：`persist` 用 `getattr` 鸭子类型接 `SpineResult`；另提供内核原生 `DecisionRecord`（`.from_spine` 转换）。
  - `write_decision_memory_net(decision_id, *, references, profile, write_edge, record=None, judge=judge_worthiness)`：7 `MEMORY_PREDICATES` canonical writer（edge_source='engine'），受 `judge` 闸 + F 闭环。
  - `judge_worthiness(record, *, value_horizon_days, transient)`：B 双轨四闸的两道可落库闸（凭证硬拒=红线命中不建正向先例边；瞬态噪声）。明确边界：价值视界/显式优先两闸属 memory LOG/NOTE 蒸馏（独立 WS），不在决策网层假装有。
- embody：
  - **N 四轨同库**：particle + event + graph_edge 全部经同一 `PgVectorStore`（同 schema 同事务边界）。
  - **B 双轨四闸**：`judge_worthiness` 拦记忆网（红线命中 ⇒ event 仍落、边不写）。
  - **F K-M-D 三段改写**：7 谓词边即 knowledge↔memory↔decision 的 M 层闭环链。
  - **G 写时三钩子**：`content_hash` 幂等判变（相同内容二次落库跳过重落）+ `provider`/`degraded` 显式留痕（禁伪健康）+ `ensure_tsvector`/`ontology_sync` 降级不中断。
- 门面 `api.py`：`persist` 五符号进 `__all__`；`Makefile` lint `--layers` 与 `test_api_facade_covers_all_layers.LAYERS` 增 `persist`。
- 测试 `tests/test_persist_ws2.py`（7 个）：happy path（7 边全写 + provider=hash 降级留痕）/ SpineResult 鸭子类型 / 红线命中只落 event 不写边 / **两处变异自证**（禁用幂等闸→新 event 行断言转红；judge 闸失效→红线决策也写边断言转红）/ payload 带 content_hash / judge 瞬态。
- 验收：全量回归 **434 passed**（427+7）；`make lint` 门面覆盖「0 处未暴露」、零残留「0 处」；领域字面量守卫 13 passed（`decision`/`knowledge`/`memory` 均 CORE_ROLES 免罪）。⚠️ `check_cython_friendly` 仍报 1 条**历史既有**违规 `llm/client.py:60`（C2-kwargs-dispatch，与 WS2 无关）。

### 7.3 WS3 脊柱注入式 ApprovalGate — 已完成 2026-10-09

embody A 红线优先 + 反馈闭环金律26（硬约束先于置信度）。`run_spine` 增可选 `approval_gate` 形参（默认 None 透传），S4→S5 间触发；拒绝时 `persisted=False` + audit 留痕。

落地：
- 新建 `chiyu_kernel/approval/` 包（`RedlinePriorityGate` + `ApprovalRequest`/`ApprovalVerdict`），接门面 `__all__`；`approval` 登记进 lint `--layers` 与门面守卫 `LAYERS`。
- `run_spine`（`chiyu-decision`）增 `approval_gate`/`audit_sink` 形参 + `SpineResult.approval_rejected` 字段。`approval_gate=None` 时**行为与改动前完全一致**（既有脊柱测试未破）。
- 命名守门面防静默覆盖纪律：与既有 `interaction.ApprovalGate`（工具执行前 HITL 闸）分层，用 `Redline`/`Decision` 前缀区分。
- 判据顺序即语义：红线命中 → **立即否决**（高置信度不豁免）→ 判据缺失 → 转人工；只有"硬约束全过 + 置信度达标"才放行。
- **两处变异自证**：① 禁闸内红线分支 → 内核探针转红；② 禁脊柱接线分支 `if not gate_verdict.approved` → 脊柱探针转红（`persisted=True` 暴露闸门被绕过）。
  - 探针设计教训：脊柱探针首版传 `elements={}`，missing 分支与红线分支同时拦截 ⇒ 无法鉴别"红线分支失效"；改用全 8 要素 + 满分使红线成为**唯一**拦截点。且闸内红线分支被 `autonomous_release` 冗余掩盖，脊柱层须针对**接线**变异而非闸内变异。
- 验收：`test` 等价 **464 passed** / `test-all` 等价 **476 passed**；门面覆盖「0 处未暴露」、§13 零残留「0 处」、领域字面量守卫 13 passed、门面守卫 7 passed。⚠️ `check_cython_friendly` 仍 1 条**历史既有**违规 `llm/client.py:60`（未触碰）。

### 7.4 顺手修掉一处「守卫覆盖度」假绿（同族新例，重要）

发现：`make test` 长期只跑 `packages/chiyu-kernel/tests tools/tests` ⇒ **`chiyu-decision` 的 24 个测试（含 WS3 接线测试）从未进入回归闸门**，脊柱层判据处于「存在但无人跑」状态。这是本项目「守卫自身的覆盖度也要被守卫」纪律的又一实例（此前 `LAYERS` 硬编码漏 `evolution` 同族）。

已修：`test` 目标并入 `$(DECISION_TESTS)`；新增 `test-all`（再含根 `tests/` 的 12 个）。

**pytest 路径根因（实测，勿再凭猜）**：组合跑报 5 个 `ModuleNotFoundError: chiyu_decision`，真因**不是**缺 conftest，而是 **rootdir 落在 `packages/chiyu-kernel`**（首个含 `[tool.pytest.ini_options]` 的 pyproject.toml）⇒ `confcutdir == rootdir` ⇒ **仓库根 `conftest.py` 落在其之上不被加载**，而根 conftest 正是四个兄弟包 src 上 `sys.path` 的唯一装置。单跑 decision 之所以绿，是命中其包 pyproject 的 `pythonpath` ⇒ **"单跑绿"长期掩盖了"组合跑全塌"**。

修复：① 新建仓库根 `pytest.ini`，把 rootdir 钉在仓库根（注释写明存在理由，避免后人误删）；② 新建 `packages/chiyu-decision/src/chiyu_decision/tests/conftest.py`，仅在不可导入时插 `src`（与 kernel 侧同款"不覆盖 A/B 副本"纪律）。

⚠️ 另注：`test_harness_phase5_e2e.py::test_independent_steps_run_in_parallel_not_serial` 是**墙钟计时断言**（`parallel < serial - 0.1`，固定 0.1s 余量），本机多会话并发负载下会误报（单跑 3/3 绿、组合重跑全绿）⇒ 判为计时抖动非回归，**本次未改**（避免混入无关变更），后续应改判定式。

### 7.5 WS8 GraphStore 图存储抽象（I1）— 已完成 2026-10-09

定位：**单源双视图的只读派生面**。`particle` + `graph_edge` + `event` 是唯一事实源，⛔ 禁另起可写图库。

落地（`chiyu_kernel/graph/`，接门面 `__all__`，登记进 lint `--layers` 与门面守卫 `LAYERS`）：
- `GraphStore` **只读协议**：`controlled()` / `out_edges` / `in_edges` / `traverse`。
  ⛔ 协议内**无任何写方法** —— 图可写即事实源分裂；由 `test_protocol_has_no_write_methods` + 探针守着。
- `InMemoryGraphStore`：语义参考实现（受控谓词构造注入；多跳 + 环检测 + 深度上限）。
- `PgCteGraphStore`：**纯 PG 递归 CTE，零新扩展依赖** = **AGE 等价能力**。
  SQL 三要素缺一不可：`WITH RECURSIVE` + `w.depth < %s`（深度上限）+ `NOT (e.to_id = ANY(w.path))`（环检测）。
  ⛔ **内核不内置 AGE 适配器**：无 AGE 服务即不可测，ship 不可测代码 = 假绿 ⇒ 留在消费方；协议即接缝。
- 三视图：① `relation_view`（受控边多跳 + 路径 + `truncated` 诚实标记）② `timeline_view`
  （四源只读聚合，`DECISION_TIME_BASIS = COALESCE(decided_at, created_at)`，缺失源即无行不脑补）
  ③ `decision_backlinks`（决策回链审计四问）。
- 零领域字面量：受控谓词**全由 profile 注入**，请求未受控谓词 ⇒ 抛（有界，不静默返回空）。

**三处变异自证（均实测转红后还原）**：① 禁受控谓词闸 → 2 条转红；② 禁深度上界闸 → 越界不再抛；
③ 删 CTE `w.depth < %s` → 2 条转红。测试另含两后端对拍（同输入须同结果，防两套语义漂移）。

踩坑：`test_relation_view_shape` 首版断言 `max_hops=2 ⇒ truncated False` 失败，**是断言错非代码缺陷**——
二跳时前沿确被截断，标 True 才诚实；已改为按语义分断言，反而更严。

验收：**488 passed**（464+24）；门面覆盖「0 处未暴露」、§13 零残留「0 处」、领域字面量 13 passed、门面守卫 7 passed；
⚠️ `check_cython_friendly` 仍 1 条**历史既有**违规 `llm/client.py:60`（未触碰）。

### 7.6 WS7 MCP 服务端骨架（I2）— 已完成 2026-10-09

⛔ **分工别混**：`chiyu_kernel.mcp` = **客户端桥**（连外部 server）；新增 `chiyu_kernel/mcpserver/` = **服务端**（把底座能力稳定输出）。

- `McpServer`：`expose()` 注册守卫（名式 `^[a-z][a-z0-9_]{0,63}$` / `risk ∈ read|write` / handler 可调用 /
  **重名禁静默覆盖**）+ `handle_request()` **传输无关** JSON-RPC 派发 + `list_tools()`。
- **零信任**：`auth=None` ⇒ **一律拒绝**（不是"先放行再说"）；鉴权为可插拔函数 `auth(ctx)->bool`，
  内核不发明账号体系，`allow_principals()` 仅为助手。
- **两阶段确认**：写类工具首次调用**不执行**，返回 `confirmation_required` + `confirm_token`；
  二次带 token 才执行。token = HMAC-SHA256(secret, `name|canonical_args|principal`)，
  **绑定工具名+参数+主体**，改任一即失效（防"拿 token 再改参数"重放）；恒定时间比较。
- `StdioTransport`：行分隔 JSON，构造参数是**类文件对象** ⇒ 无需真实端口即可测。
  ⛔ **HTTP 适配器不在内核**：消费方把 http body 喂给 `handle_request()` 即可——传输无关派发器本身就是 http 接入面。

**三处变异自证（均实测转红后还原）**：① 禁鉴权闸 → 探针报 `leaked`（默认放行即泄密）；
② 禁两阶段闸 → 写操作无确认即执行；③ token 解绑参数 → `amount 100→999999` 被放行（重放攻击）。

自查：首版 `test_probe_duplicate_guard_discriminates` 含 `if False else None` **死代码**（断言空转 = 假绿），
已改为实质断言（重名抛错后原处理器仍生效）。

验收：**508 passed**（488+20）；门面覆盖「0 处未暴露」、§13 零残留「0 处」、领域字面量 13 passed、门面守卫 7 passed；
⚠️ `check_cython_friendly` 仍 1 条**历史既有**违规 `llm/client.py:60`（未触碰）。

### 7.7 下一步：WS9 参考消费层（端到端样板 + 常驻 canary）
