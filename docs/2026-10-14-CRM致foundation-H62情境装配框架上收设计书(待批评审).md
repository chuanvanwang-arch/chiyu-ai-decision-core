# H-62 情境装配框架上收设计书（CRM → foundation，设计先行·零 src 改动）

> 日期：2026-10-14 ｜ 状态：**设计稿，待 foundation 批评审**（T103 §1.3.3 约定：正式设计稿另批评审后再动）
> 事项：H-62「情境装配框架」（`context/` 8 框架件）上收 foundation 成公共底座——ai-context-layering 方法论（10 大能力之一）的代码实现。
> 立场：CRM 为源仓/首个落地项目；本稿与 A-evolution 立项（`docs/2026-10-13-crm-A-evolution-design.md`）同族体例。**本提交零代码改动**。

---

## 一、裁定（切换面 vs 不切换面）

| 维度 | 结论 |
|---|---|
| **上收面** | `context/` 框架件 8 个：`assembler.js`（分层装配骨架）/`routing.js`+`routingExperiment.js`（情境路由+实验）/`scope.js`（数据范围裁剪）/`injector.js`（注入器）/`snapshotStore.js`（装配快照）/`supplySpec.js`（供给规格）/`timelineSource.js`（时间线源） |
| **不切换面（留 CRM，作注入内容）** | ① `assembleContextV2.js`——脊柱 S5 域装配（CRM_ACCOUNT/CRM_DEAL 实体兜底链 `:57/:122`、`evaluateRules('CRM_DEAL','advance')` `:113`）；② `particleTypes.js`（BUSINESS_PARTICLE_TYPES 域清单）；③ `roleProfiles.js`（七要素角色 profile，config 驱动） |
| **脱域硬点（G-域无关）** | `assembler.js:26` `ICP_MATCH: ['icp']` 映射、`:283-292` `CRM_KNOWLEDGE` SQL 硬编码（scopePredicate 内联 `WHERE type='CRM_KNOWLEDGE' AND tenant_id=$1 AND state='registered'`）——两处必须转为注入 |
| **对接锚点（foundation 已有）** | `contract/context.py`（Batch-2a GAP-2 已单源）：`CONTEXT_LAYERS=("L1","L2","L3","L4")` / `CONTEXT_LAYER_LABELS_ZH` / `KNOWLEDGE_LAYERS` / 缺口类型 / 降级档位——**词汇与分层模型已 stable 化，本稿只补「装配机制」层** |

## 二、注入面设计（foundation 侧新增机制，五件）

> 原则：内核收「装配机制」（分层顺序/供给协议/快照/降级/缺口计算），域内容全走注入；与 D1-D8 契约层同款「机制上收、内容留消费方」。

1. **LayerSupplier 协议**（每层一个供给钩子）：`supply(layer: "L1"|"L2"|"L3"|"L4", request) -> LayerSupply`；消费方按层注册供给函数（L1 检索/L2 知识/L3 时间线/L4 全域——语义标签复用 `CONTEXT_LAYER_LABELS_ZH`，不在内核重写）。缺供给 = 显式 `missing`（禁静默空层，复用 GAP-2 缺口类型）。
2. **ScopePredicate 注入**：数据范围裁剪只收「谓词接口」；`assembler.js:292` 的 `CRM_KNOWLEDGE` SQL 整体留消费方（CRM 以 provider 注入同语义 SQL）。内核零 SQL、零表名（G-零IO）。
3. **粒子类型注册表注入**：`BUSINESS_PARTICLE_TYPES` 等 type 白名单由消费方注册进装配上下文；内核不认识任何 `CRM_*` 字面量。
4. **角色 Profile 加载器注入**：七要素（core_focus/default_query_pref/l2c_workflow/kpi_baseline/cross_role_collab/permission_boundary/role_subtype）结构上收为 Profile 骨架（config 驱动的纯结构），加载（DB 读/seed）留消费方。
5. **装配快照与降级**：`snapshotStore` 机制上收（快照写读接口，持久化留消费方）；降级档位复用 GAP-2 已有契约。

## 三、桥接与守卫（防「收敛变分叉」）

- **桥接形态**：契约平行实现——CRM 侧 `src/context/contextContract.js` 镜像 `CONTEXT_LAYERS`/`KNOWLEDGE_LAYERS` 词表（与 A-evolution 的 `icpEvolutionContract.js` 同族）；机制层 harvest 后 CRM 切换为消费 foundation 公共件。
- **对拍守卫**：`test/scripts/h62-context-contract-parity.test.js`——程序化提取两侧源码字面量（rfc3/d7 范式）、foundation 不可达 fail-closed、含变异自证；另加「接线三查」（镜像是被真实消费，防判据 #20 形态未触达假绿）。
- **验收硬闸**：G-域无关（内核 grep 禁 `CRM_*`/`icp`/`ICP_MATCH`/`CRM_KNOWLEDGE`）/ G-零IO（内核禁 DB 读写，快照与 SQL 留消费方）/ G-对等可测（harvest 后 CRM 行为对拍：装配产物结构逐字段 parity 清单）。

## 四、实施步骤（foundation 侧施工图，供排期评审）

1. `contract/context.py` 增补装配机制契约注释（LayerSupplier/ScopePredicate/Profile 骨架签名——注释先行，与 T100/T102 体例一致，零行为变更）；
2. 新增 `chiyu_kernel/context/`（或挂既有 impl 面）机制实现：分层装配器 + 注入器 + 快照接口 + 缺口/降级计算；
3. manifest `context` 能力条目补语义（机制上收边界：域 SQL/粒子类型/角色加载留消费方）；
4. 变异自证 + 全量基线复跑（当前 1148 passed 基线不回退）；
5. CRM 切换消费（本仓后续任务，届时走盘点账 H-62 核销三态）。

## 五、批次与依赖

- **批次归属**：foundation 设计批（T103 §1.3.1：H-61/H-62/H-64/H-68 设计批）——本稿即 H-62 设计输入，**不抢跑**（foundation 批评审通过后才施工）。
- **依赖**：仅 `contract/context.py`（stable 面，Batch-2a）；不依赖 P-1 采集 API / P-3 resume；不阻塞 P1 出口闸（增强非修复）。
- **对 H-61/H-64/H-68 的复用**：本稿的「机制上收/内容注入/Profile 骨架」模式可直接套用于告警框架（H-61）、技能注册表（H-64）、AI 属性评估协议（H-68）——建议 foundation 以本稿为设计批的范式样板。

—— CRM-ai-native（AI 原生企业销售决策平台）2026-10-14
