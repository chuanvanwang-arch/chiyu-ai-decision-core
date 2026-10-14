# 企业级 AI 平台（chiyu-enterprise）架构设计

> 设计日期：2026-09-25 · 智能体：`enterprise-platform-builder`（契约键 `ct-chiyu-enterprise`）
> 前置共识：客户端（DSH 桌面端）经 `chiyu-host` 接入 foundation 后，需要一个**企业级 AI 平台**作多租户中枢；一个平台对应多个客户端访问。
> 本设计遵循既有铁律：**chiyu-foundation 零领域字面量、消费方只 `import chiyu_kernel.contract`/`chiyu_kernel.api`、三仓严禁混写**。

---

## §0 结论（摘要）

企业级平台 = **核心 A（记忆与知识引擎）+ 核心 B（决策统一监控与调度）+ 场景层（Action 消费）+ 多租户隔离 + chiyu-host**，作为 `chiyu-foundation` 的**独立消费方仓库**（`chiyu-enterprise`）。

- 客户端（DSH）是**纯访问边缘**：只持"连哪个平台 / 哪个租户 / 何种鉴权"的连接配置，经 RPC/SSE 调用平台暴露的 `Action`，不定义任何能力、不落地租户数据。
- 企业级平台是**有状态中枢**：在其上叠多租户、场景包、治理；生产/销售/供应/质量等场景**零代码落地**为配置包（TenantProfile + Action 命名空间 + 多智能体拓扑 + 连接器实例）。
- 领域字面量**绝不进 foundation、绝不进客户端代码**，只以配置 + 租户资产形态存在于企业级平台，经 `TenantProfile` 注入。

两大核心均已映射到 foundation 已落地的真实模块（实测核实，非记忆）：

| 核心 | foundation 已落地通用机制（零领域） |
|---|---|
| A 记忆/知识 | `vector/`（BGE ONNX 离线向量·写时索引）、`ontology/`（本体图/回填/钩子）、`context/`（knowledge_needs→retrieval→assembly 四层注入）、`store/`（PG 持久化·租户隔离） |
| B 决策监控/调度 | `contract/decision.py`（决策契约·K-M-D 管线）、`orchestration/`（state_machine/dispatch/agent_registry 调度+SLA）、`events/`（决策事件总线）、`audit/`、`evolution/`、`interaction/ApprovalGate`（审批闸） |

---

## §1 背景、问题与范围

### 1.1 触发问题
- 客户端（DSH）完成 foundation 功能接入后，企业侧"后台"如何定义？
- 一个企业有大量场景需落地（生产、销售、供应、质量），需要**企业级 AI 平台与底座**。
- 呈现"一个企业级平台 ↔ 多个客户端访问"的拓扑。

### 1.2 待澄清的核心命题（用户拍板）
1. 企业级平台与 foundation 的关系模型 → **已选 A：独立消费方仓库**（守分层铁律与仓边界）。
2. 场景（销售等）如何接入 → **场景包五元组，客户端零改动**（见 §6）。
3. 企业级平台的核心 → **核心 A 记忆/知识引擎 + 核心 B 决策统一监控与调度**（见 §4、§5）。
4. 能力规范化 → **统一经 ACTION（Action 表面 / Action Registry）治理**（见 §6）。

### 1.3 范围
- **在范围**：企业级平台（chiyu-enterprise）的架构、分层、两核心、场景包机制、多智能体、集成、开发/运行区分、纪律、执行契约。
- **不在范围**：客户端（DSH）自身的 UI 实现、foundation 内部机制改动（仅消费门面）、具体业务字段的硬编码（禁止）。

---

## §2 总体拓扑（三仓三部署单元）

```
[chiyu-client ×N] ──RPC/SSE──► [chiyu-enterprise 企业级平台]
   DSH ui-* 边缘渲染                ├─ chiyu-host(FastAPI): RPC 路由器 + SSE mux
   (桌面/Web/移动, 无状态边缘)       ├─ 核心 A: 记忆与知识引擎(vector/ontology/context/store)
                                     ├─ 核心 B: 决策统一监控与调度(decision/orchestration/events/audit/evolution)
                                     ├─ 场景层: 场景包(sales/prod/supply/quality) 经 Action 消费 A+B
   └── foundation 不感知 enterprise/client ├─ 多租户隔离层(tenant-id/RBAC/租户粒子库)
                                     └─ 嵌入 chiyu_kernel(纯库, 零领域字面量)
```

- **foundation**：零领域字面量，仅经 `contract`/`api` 门面对外。
- **enterprise**：只 `import chiyu_kernel.contract` / `chiyu_kernel.api`，在其上叠多租户 + 两核心 + 场景包 + 治理。
- **client**：只持连接配置；多客户端共存由 `chiyu-host` 按 `tenant + client-type` 维度服务。

---

## §3 分层定位与功能划分详表

| 能力 | foundation（纯底座） | 企业级平台（enterprise） | 客户端（client） |
|---|---|---|---|
| 通用机制（会话/工具/agent-loop/workflow/插件/模式/Action 执行） | ✅ 实现 | 消费 | 消费（边缘调用） |
| 多租户隔离 / tenant-id | ❌ | ✅ | ❌（仅带 token） |
| 领域场景（生产/销售/供应/质量） | ❌（禁字面量） | ✅ 经 TenantProfile + 场景包注入 | ❌ |
| 租户数据 / 粒子库 / 记忆 / 知识索引 | ❌ | ✅ 持有（tenant-id 隔离） | ❌（不落地） |
| 记忆与知识引擎（A） | 机制：vector/ontology/context/store | ✅ 实例 + 企业 KB/数据湖连接器 | 消费检索结果 |
| 决策监控与调度（B） | 机制：decision/orchestration/events/audit/evolution | ✅ 实例 + 看板 + 调度配置 | 展示/触发 |
| 模型 provider 管理 | provider 抽象 | ✅ 注册/切换 | 选择 UI |
| RBAC / 治理 / 聚合看板 | ❌ | ✅ | 展示 |
| UI 渲染 / 本地对话展示 | ❌ | 经 host 推 SSE | ✅ DSH `ui-*` |
| 离线本地 agent-loop（降延迟，可选） | 机制在 foundation | — | ✅（sync 回平台） |

---

## §4 【核心 A】记忆与知识引擎（含企业 KB / 数据湖打通）

### 4.1 机制归属（零领域在 foundation）
- `vector/`（onnx_runner / index_vector / infer / coverage）：BGE ONNX 离线向量，写时索引。
- `ontology/`（graph / backfill / hooks）：本体图、回填、钩子。
- `context/`（knowledge_needs / retrieval / assembly）：knowledge_needs→retrieval→assembly 四层（L1–L4）注入。
- `store/`（pg_store / ddl / conn）：PG 持久化、租户隔离。

### 4.2 企业级平台新增（实例 + 集成连接器）
- **企业知识库集成（文档类）**：Confluence / SharePoint / 文件共享 → 经 §8 integration 连接器**拉取** → 归一为文档 → 走 `vector/` 写时索引（document→chunk→vector 三层）+ `ontology/backfill` 本体回填 → 落**租户级**索引（`store/` 按 tenant-id 隔离）。
- **企业数据湖集成（结构化类）**：数据仓库 / 湖仓 → 经连接器**查询** → 归一为**粒子**（`contract/particle.py`）→ 进本体图与上下文检索。
- **记忆双轨**（按 `ai-memory-lifecycle`）：每租户一套 append-only 日志 + upsert 笔记，周期性蒸馏；`context/retrieval` 做混合召回（dense+sparse）后由 `context/assembly` 注入 L1–L4。
- **知识图谱 / 词汇表**：每租户一套 `ontology/` 实例。

### 4.3 "打通"语义（关键纪律）
- 默认**拉取式 ingest**：不要求企业迁移知识，AI 侧只持有租户级**派生索引**，不搬运源数据出域。
- 可选 **write-back**：决策/洞察经 integration Action 回写数据湖（需显式授权，受零信任令牌约束）。
- 企业源系统**只读接入**优先；任何写入回源须走 §6 的 Action 护栏。

---

## §5 【核心 B】决策统一监控与调度

### 5.1 机制归属（零领域在 foundation）
- `contract/decision.py`：决策契约（K-M-D 管线）。
- `orchestration/`（state_machine / dispatch / agent_registry）：决策任务编排、调度、SLA、僵尸任务治理。
- `events/`：决策事件总线。
- `audit/`：审计留痕。
- `evolution/`：事件驱动能力自进化。
- `interaction/ApprovalGate`：审批闸（决策第 0 闸）。

### 5.2 企业级平台新增（控制平面）
- **统一监控**：跨租户 / 跨场景 / 跨客户端的**决策事件**经 `events/` 汇聚 → 决策第 0 闸治理 + `ApprovalGate` 审批流看板 + `audit/` 留痕 + 红线命中汇总。一处看全平台"谁在决策、依据什么、是否越权"。把现有"销售决策监控 + 7x7"泛化为平台级 control plane。
- **统一调度**：`orchestration/state_machine`+`dispatch` 做决策任务编排（周期/触发）、SLA 与僵尸任务治理；参数传播中枢（inherit/broadcast/promote + decision-0 gate + HITL）统一下发治理参数；`evolution/` 承接决策事件做能力自进化。
- 客户端只**接收监控视图 + 触发决策**，中枢逻辑全在平台。

---

## §6 场景层：场景包五元组 + ACTION 统一治理面

### 6.1 场景包 = 五元组（全部在企业级平台，零代码进 foundation）
```
ScenarioPackage = {
  ① tenant_profile   : { particle_types, knowledge_predicates, redline_items }   # 领域字面量（Action 消费的输入）
  ② action_surface   : namespace "sales" → 原生能力 Action（绑定 PluginRegistry 槽位）
  ③ agent_topology   : roles[] 各持 Action 子集；edges[] = Action 委派/移交
  ④ assets           : prompt_templates / decision_rules / particle_schema / kb  # 挂到 Action 的参数
  ⑤ integrations     : 连接器 → 暴露 integration Action（如 erp.sync_order）
  enabled_for        : [ tenant_id ]
}
```

### 6.2 ACTION 统一治理面（核心纪律）
- ② 能力槽位、③ 多智能体、⑤ 集成 三者的"能做什么"**全部表达为 Action**，统一在 `Action Registry` 注册、统一受护栏（红线 + 零信任 `confirmation_token` + RBAC）。
- foundation 提供 **Action 执行引擎 + Registry 机制**（零领域）；企业级平台按场景包**声明 Action 实例**（命名空间 + 参数 + 护栏元数据）。
- 每个 Action 携带护栏元数据：
  - `redline_guard`：红线判据放在**被调用方**（守"护栏判据放被调用方"铁律，避免忘调用即绕过）。
  - `confirmation_token`：**写类 Action 必须过零信任令牌**；仅白名单（如 `p2p-req-submit` 类免 token 入 Draft）豁免。
  - `rbac_scope`：tenant-id + role 维度鉴权。
- 客户端只经 RPC/SSE **调用** `sales.*` Action，不定义。

### 6.3 销售场景包 Action 命名空间树（实例）
```
sales.
├─ native.*                     # ② 原生能力（绑定 PluginRegistry 槽位）
│   ├─ sales.context.assemble   # L1–L4 上下文注入（消费核心 A）
│   ├─ sales.action.propose     # 动作提议（action-design）
│   └─ sales.feedback.capture   # 反馈回路
├─ agent.*                      # ③ 多智能体角色 = Action 子集
│   ├─ sales.agent.lead         # 线索 Agent：qualify
│   ├─ sales.agent.seat         # 销售坐席：consult / request_quote
│   ├─ sales.agent.quote        # 报价 Agent：generate
│   ├─ sales.agent.decision     # 决策 Agent：score（九尺子，走核心 B）
│   └─ sales.agent.manager      # 销售管理：approve / forecast
└─ integration.*                # ⑤ 外部系统集成 = 连接器 Action
    ├─ sales.integration.crm.read_opportunity   # crm-native-mcp
    ├─ sales.integration.wecom.push_approval    # 企业微信
    ├─ sales.integration.erp.sync_order         # 中标后履约
    └─ sales.integration.email.outreach
```

---

## §7 多智能体拓扑（销售实例）

角色与关系**均为配置、非代码**，由 foundation `orchestration/` 的委派/移交图引擎解释执行：

```
        [线索 Agent]──qualify──►[销售坐席]──escalate──►[销售管理]
                                  │  │                    │
                       request   │  └─consult─►[决策 Agent]│
                          ▼       │     (九尺子评分)        │approve
                        [报价 Agent]──approval──►[审批闸]──►┘(樊总/折扣权限)
```

- 每个角色 = 一个 `orchestration/agent_registry` 槽位实例，绑定 §6.3 的能力 Action（如销售坐席绑定 `context-layering` L1–L4 + `action-design` 动作面 + `feedback-loop`）。
- 关系边（qualify/escalate/request/approval）= 委派/移交图；"谁是销售、谁管报价"不写进 foundation。

---

## §8 外部系统集成（连接器）

- foundation 提供通用 `mcp/`（McpBridge + 连接器接口）；企业级平台提供**连接器实例 + 领域映射 + 鉴权**作为租户资产。
- 销售场景包声明的连接器实例（平台侧治理为主）：

| 外部系统 | 用途 | 形态 |
|---|---|---|
| `crm-native-mcp` | 客户/商机/报价读写（已有连接器） | 平台侧连接器 + 领域映射 |
| 企业微信/钉钉 | 审批推送、待办提醒 | 平台侧连接器 |
| ERP | 中标后订单/回款同步（履约链） | 平台侧连接器 |
| 邮件/BI | 触达、跨租户聚合看板 | 平台侧连接器 |

- 仅当确属边缘本地系统（桌面端本地文件/本地 ERP）才下放客户端连接器，但仍须登记进平台连接器注册表受治理。
- 连接器机制=通用；SAP/企业微信/ERP 的具体字段映射=租户资产，**不得带领域字面量进 foundation**。

---

## §9 开发阶段区分（靠仓库边界，不靠 flag）

- **三仓独立**：`chiyu-foundation` / `chiyu-enterprise` / `chiyu-client`。
- foundation 不 import 另两者；enterprise 只 import `chiyu_kernel.contract`/`api`；client 只 import RPC/SSE 客户端 + `ui-*`。
- 依赖方式：enterprise 以**钉版本**方式依赖 foundation（git 依赖或子模块），仅消费门面。
- 可测性：foundation 单独跑 `make test`（零领域）；enterprise 跑多租户/场景包隔离/两核心测试；client 跑连接契约测试。
- 辨识点：import 图天然区分三层，无需 `if is_enterprise` 之类运行时开关。

---

## §10 运行阶段区分（靠部署拓扑 + 鉴权 scope）

| 维度 | 客户端 | 企业级平台 | foundation |
|---|---|---|---|
| 形态 | 无状态边缘进程 | 有状态中枢服务 | 嵌在平台进程内的库 |
| 鉴权 | user/device token | tenant-id token | 不感知租户 |
| 数据归属 | 不落地租户数据（仅本地缓存） | 独占租户数据/粒子库/知识索引 | 无状态 |
| 编排执行 | 可选离线本地 loop | 跑编排/决策/审批（核心 B） | 被调用 |
| 多接入 | 支持 N 个客户端共存 | 按 tenant+client-type 维度服务 | — |

---

## §11 纪律与风险

- ⛔ **守分层铁律**：企业级平台若把领域字面量写进 foundation，即违规；必须经 TenantProfile 注入。
- ⛔ **守仓边界**：三仓严禁混写（呼应 demo 只读快照纪律）。
- ⛔ **配置驱动差异化**：场景差异靠配置，禁代码分支 / 新增粒子类型污染多租户纯度（呼应 acme-auto 纪律）。
- ⛔ **护栏判据放被调用方**：红线判据写在 Action 被调用方，忘调用即报错，不静默绕过。
- ⛔ **零信任令牌**：写类 Action 必须 `confirmation_token`；仅白名单豁免。
- ⚠️ **chiyu-host 须支持多客户端共存**（tenant + client-type 维度），避免"一个平台只服务一个桌面端"的隐性假设。
- ⚠️ **企业源只读优先**：KB/数据湖默认拉取式 ingest，write-back 需显式授权 + 令牌。

---

## §12 执行契约（Living Contract · 双轨）

> 本设计引入新消费方智能体 `enterprise-platform-builder`（契约键 `ct-chiyu-enterprise`），已在 `contract/contract-ids.json` 登记后方可校验通过。

```contract-yaml
- task: "登记 ct-chiyu-enterprise 契约键 + 建立 chiyu-enterprise 独立消费方仓库"
  contract_task_id: ct-chiyu-enterprise
  agent: enterprise-platform-builder
  skills: [ai-native-action-design, ai-capability-audit]
  memory: [chiyu-foundation, enterprise-platform]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "新仓仅 import chiyu_kernel.api 成功，门面返回 LAYERS 清单，零内部路径 import；contract-ids.json 含 ct-chiyu-enterprise"
```

```contract-yaml
- task: "实现多租户隔离层（tenant-id scope / RBAC / 租户粒子库隔离）"
  contract_task_id: ct-chiyu-enterprise
  agent: enterprise-platform-builder
  skills: [ai-particle-system-design, ai-context-layering]
  memory: [chiyu-foundation, enterprise-platform]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "同一 foundation 实例服务 N 租户，A 租户粒子对 B 不可见（tenant-id 过滤），RBAC 拒绝越权读写"
```

```contract-yaml
- task: "核心 A：企业 KB/数据湖集成连接器 + 租户级记忆/知识索引"
  contract_task_id: ct-chiyu-enterprise
  agent: enterprise-platform-builder
  skills: [ai-ontology-vector-build, ai-memory-lifecycle, ai-context-layering]
  memory: [chiyu-foundation, enterprise-platform]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "连接器拉取企业 KB/数据湖→写时索引→落 tenant-id 隔离索引；context/retrieval 召回含该租户知识且不串租户"
```

```contract-yaml
- task: "核心 B：决策统一监控看板 + 调度/参数传播"
  contract_task_id: ct-chiyu-enterprise
  agent: enterprise-platform-builder
  skills: [ai-multi-agent-orchestration, ai-feedback-loop, ai-event-driven-evolution]
  memory: [chiyu-foundation, enterprise-platform]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "跨租户决策事件经 events/ 汇聚，监控看板显示决策第0闸/审批/红线汇总；调度按 state_machine 跑通且 SLA 可见"
```

```contract-yaml
- task: "场景包机制：TenantProfile + Action 命名空间 + 多智能体拓扑 + 连接器实例（销售零代码落地）"
  contract_task_id: ct-chiyu-enterprise
  agent: enterprise-platform-builder
  skills: [ai-particle-system-design, ai-native-action-design, ai-multi-agent-orchestration]
  memory: [chiyu-foundation, enterprise-platform]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "加载 sales 场景包后暴露 sales.* Action 命名空间与 agent 拓扑；切换生产包零代码改动生效；foundation 无新增领域字面量"
```

```contract-yaml
- task: "chiyu-host（RPC/SSE）供多客户端接入 + 治理（审批/审计/provider/聚合看板）"
  contract_task_id: ct-chiyu-enterprise
  agent: enterprise-platform-builder
  skills: [ai-capability-audit, ai-feedback-loop]
  memory: [chiyu-foundation, enterprise-platform]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "N 个客户端经 RPC/SSE 接入同一平台不同租户；决策经审批闸留痕；provider 切换对全租户生效"
```

---

## §13 实施路线（移交 writing-plans 的任务拆解）

1. **E1 仓库与契约基座**：建立 `chiyu-enterprise` 独立消费方仓库，钉版本依赖 foundation，仅消费 `contract`/`api` 门面；登记 `ct-chiyu-enterprise`。
2. **E2 多租户隔离层**：tenant-id scope / RBAC / 租户粒子库与记忆隔离。
3. **E3 核心 A（记忆/知识引擎）**：企业 KB/数据湖集成连接器 + 租户级 vector/ontology/context/store 实例。
4. **E4 核心 B（决策监控/调度）**：决策事件汇聚监控看板 + orchestration 调度/参数传播 + SLA。
5. **E5 场景包机制 + ACTION 治理面**：TenantProfile + Action 命名空间 + 多智能体拓扑 + 连接器实例（销售先行，零代码落地）。
6. **E6 chiyu-host + 多客户端接入**：RPC/SSE 服务端、tenant+client-type 维度、治理闭环。

---

## §14 闭环回写（runtime 监控 → 下一轮 P0 吸收）

| task | agent | gap_type | observed | expected | severity | ts |
|---|---|---|---|---|---|---|
| （待 workbench 运行时写入） | | | | | | |

> 本表由 `enterprise-platform-builder` 在 `/agents` workbench 运行时监控填充；同一 `(task, gap_type)` 复发 ≥ 2 次 → 提出 SKILL/设计改进提案（须用户批准方可改动）。
