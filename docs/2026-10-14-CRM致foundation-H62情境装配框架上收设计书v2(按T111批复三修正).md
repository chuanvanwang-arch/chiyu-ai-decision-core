# H-62 情境装配框架上收设计书 · 修订版 v2（CRM → foundation，按 T111 批复三修正）

> 日期：2026-10-14 ｜ 状态：**v2 修订版，替换 v1**（v1 原则批准于 T111 §二；本稿落实三处修正，其余条款承 v1 不变）
> 批复依据：T111《三仓反馈审阅收口》§二——原则批准 + 三修正（实施面 / 基线数字 / 桥接形态）。
> 事项：H-62「情境装配框架」（`context/` 8 框架件）上收 foundation 成公共底座——ai-context-layering 方法论（10 大能力之一）的代码实现。**本提交零代码改动**。

---

## 〇、v2 修订记录（对应 T111 三修正）

| # | 修正项 | v1 原文 | v2 修订 |
|---|---|---|---|
| 1 | **§四.2 实施面** | 「新增 `chiyu_kernel/context/`（或挂既有 impl 面）」 | **挂既有 `chiyu_kernel/context/` 实施层扩展**（assembly.py 旁新增装配机制模块），**不新建平行子包**；门面导出与 LAYERS 登记走既有登记四件套（详见 §四.2） |
| 2 | **§四.4 基线数字** | 「当前 1148 passed 基线不回退」 | 基线演进至 **1200 passed**（T109 后，45 capabilities）；施工验收以 **1200 不回退**为基线 |
| 3 | **§三 桥接形态** | 仅约定「机制层 harvest 后 CRM 切换为消费 foundation 公共件」 | 补一条：CRM 侧镜像 `contextContract.js` 除词表外，**机制层切换时须走 parity 对拍清单（§三 G-对等可测）逐字段实证后才可删本地实现——先建守卫后删，禁止「切而不删」双源** |

---

## 一、裁定（切换面 vs 不切换面）〔承 v1，批复已确认〕

| 维度 | 结论 |
|---|---|
| **上收面** | `context/` 框架件 8 个：`assembler.js`（分层装配骨架）/`routing.js`+`routingExperiment.js`（情境路由+实验）/`scope.js`（数据范围裁剪）/`injector.js`（注入器）/`snapshotStore.js`（装配快照）/`supplySpec.js`（供给规格）/`timelineSource.js`（时间线源） |
| **不切换面（留 CRM，作注入内容）** | ① `assembleContextV2.js`——脊柱 S5 域装配（CRM_ACCOUNT/CRM_DEAL 实体兜底链、`evaluateRules('CRM_DEAL','advance')`）；② `particleTypes.js`（BUSINESS_PARTICLE_TYPES 域清单）；③ `roleProfiles.js`（七要素角色 profile，config 驱动）——与 D3「两量各司其职」同款立场（T111 §2.1 确认） |
| **脱域硬点（G-域无关）** | `assembler.js:26` `ICP_MATCH: ['icp']` 映射、`:283-292` `CRM_KNOWLEDGE` SQL 硬编码——两处必须转为注入（T111 §2.1：识别准确，同意） |
| **对接锚点（foundation 已有）** | `contract/context.py`（Batch-2a GAP-2 已单源）：`CONTEXT_LAYERS=("L1","L2","L3","L4")` / `CONTEXT_LAYER_LABELS_ZH` / `KNOWLEDGE_LAYERS` / 缺口类型 / 降级档位——词汇与分层模型已 stable 化，本稿只补「装配机制」层 |

## 二、注入面设计（五件）〔承 v1，批复采纳为设计批范式样板〕

1. **LayerSupplier 协议**：`supply(layer, request) -> LayerSupply`；消费方按层注册供给函数（L1 检索/L2 知识/L3 时间线/L4 全域——语义标签复用 `CONTEXT_LAYER_LABELS_ZH`）。缺供给 = 显式 `missing`（禁静默空层，复用 GAP-2 缺口类型）。
2. **ScopePredicate 注入**：数据范围裁剪只收「谓词接口」；`CRM_KNOWLEDGE` SQL 整体留消费方。内核零 SQL、零表名（G-零IO）。
3. **粒子类型注册表注入**：type 白名单由消费方注册进装配上下文；内核不认识任何 `CRM_*` 字面量。
4. **角色 Profile 加载器注入**：七要素结构上收为 Profile 骨架（config 驱动纯结构），加载（DB 读/seed）留消费方。
5. **装配快照与降级**：`snapshotStore` 机制上收（快照写读接口，持久化留消费方）；降级档位复用 GAP-2 已有契约。

## 三、桥接与守卫（防「收敛变分叉」）〔v2 补修正 #3〕

- **桥接形态**：契约平行实现——CRM 侧 `src/context/contextContract.js` 镜像 `CONTEXT_LAYERS`/`KNOWLEDGE_LAYERS` 词表（与 A-evolution 的 `icpEvolutionContract.js` 同族）；机制层 harvest 后 CRM 切换为消费 foundation 公共件。
- **〔v2 新增〕切换纪律（先建守卫后删）**：镜像 `contextContract.js` 除词表外，**机制层切换时须走 parity 对拍清单（G-对等可测）逐字段实证后才可删本地实现——先建守卫后删，禁止「切而不删」双源**。对拍清单承载于 `test/foundation-parity/`（与 batch4/batch5/contract-parity 同族，七组哨兵已有先例）；删本地实现须以对拍清单全绿 + 变异自证为前置，杜绝双源漂移窗口。
- **对拍守卫**：`test/foundation-parity/h62-context-parity.test.js`——程序化提取两侧源码字面量（rfc3/d7 范式）、foundation 不可达 fail-closed、含变异自证；另加「接线三查」（镜像是被真实消费，防判据 #20 形态未触达假绿）。
- **验收硬闸**：G-域无关（内核 grep 禁 `CRM_*`/`icp`/`ICP_MATCH`/`CRM_KNOWLEDGE`）/ G-零IO（内核禁 DB 读写，快照与 SQL 留消费方）/ G-对等可测（harvest 后 CRM 行为对拍：装配产物结构逐字段 parity 清单）——三闸全部采纳入施工验收判据（T111 §2.1）。

## 四、实施步骤（foundation 侧施工图，v2 修订）

1. `contract/context.py` 增补装配机制契约注释（LayerSupplier/ScopePredicate/Profile 骨架签名——注释先行，与 T100/T102 体例一致，零行为变更）；
2. **〔v2 修正 #1〕挂既有实施层扩展**：不新建平行子包——在既有 `chiyu_kernel/context/`（assembly / fuse / knowledge_needs / recall_memory / retrieval，version.py 登记 stable）内**assembly.py 旁新增装配机制模块**（分层装配器 + 注入器 + 快照接口 + 缺口/降级计算）；门面导出与 LAYERS 登记走既有登记四件套；
3. manifest `context` 能力条目补语义（机制上收边界：域 SQL/粒子类型/角色加载留消费方）；
4. 变异自证 + 全量基线复跑（**〔v2 修正 #2〕基线 1200 passed 不回退**，45 capabilities）；
5. CRM 切换消费（本仓后续任务）：按 §三 v2 切换纪律执行——先建 parity 对拍清单 → 逐字段实证 → 删本地实现（先建守卫后删）；届时走盘点账 H-62 核销三态。

## 五、批次与依赖（v2 更新排期）

- **批次归属**：**H-62 并入 Batch-6 横切盘点稿一并定**（T111 §2.3）；设计批四项排序：**H-62 先行**（设计稿已齐且批复通过）→ H-61 / H-64 / H-68 套用本范式补设计稿后跟进。
- **foundation 批复即施工依据**：CRM 无需等新一轮函件往返，Batch-6 盘点稿落地时 H-62 直接进施工（T111 §2.3）。
- **依赖**：仅 `contract/context.py`（stable 面，Batch-2a）；不依赖 P-1 采集 API / P-3 resume；不阻塞 P1 出口闸（增强非修复）。
- **对 H-61/H-64/H-68 的复用**：本稿「机制上收/内容注入/Profile 骨架」模式作为设计批范式样板（T111 §2.1 批准），三稿可直接套用。

—— CRM-ai-native（AI 原生企业销售决策平台）2026-10-14 · v2
