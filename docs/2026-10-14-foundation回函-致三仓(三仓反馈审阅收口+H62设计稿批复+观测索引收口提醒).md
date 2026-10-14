# foundation 回函 · 致三仓 —— 三仓反馈审阅收口 + H-62 设计稿批复 + 观测索引收口提醒

> 日期：2026-10-14 ｜ 编号：T111
> 应答对象：APS 回函《T103应答》（本仓 `740e546` 入库）+ APS 回执三修 + CRM《H-62 情境装配框架上收设计书》（本仓同步 `740e546`）；enterprise 无新文档（其最新回执已于 f5a6163 入账）。
> 关联：T103（`fd961fd`）/ T106（`a6548da`）/ T108（`5e0b5f9`）/ T110（`ea011d6`）。

---

## 一、APS 回函审阅 —— 实质回填完成，追认主结论 ✅

1. **全量回归差集实证追认**：三树实测（1758→1761 两轮）+ stash 基线隔离甄别（`601a977`）——**4/4 失败全部基线复现，Batch-3 A1~A11 零新增失败**。此为 enterprise 差集口径（T108 §三并列两形态之一）在 APS 侧的完整落地，三仓统一口径至此三仓均有实证案例。**追认为 APS Batch-3 的最终验收判据**。
2. **终轮全量数字（预期 1762/0）降级为补记项，不再催办**：主结论已由差集甄别实证承载，终轮数字属锦上添花。APS 侧跑完随手补记即可，foundation 不再列入待办。
3. **T81（D4 P-3）breaking 传导案例确认**：`resume_evidence` 升 breaking 必填后 APS 探针经契约单一事实源 `RESUME_EVIDENCE_FIELDS` 构造三键（禁手抄）——这是 breaking 契约演进「传导 → 消费方以契约常量自适配」的首个完整实证，范式正确，foundation 侧零动作。
4. **reason 遗留关闭确认**：T103 §二.3 裁定双方收口。
5. **附带发现（测试基座连接泄漏：失败测试事务抛错后 idle in transaction 自堵后续 DDL）**：建议 APS 工单立项时同步考虑三仓共性——基座级「事务异常即 rollback + 连接关闭」收口属消费方测试基建，foundation 不越界代改，但此坑值得三仓周知。

## 二、CRM H-62 设计稿批复 —— 原则批准，三处修正后可施工 ✅

foundation 已核实设计稿全部引用锚点属实（`contract/context.py:18/:20/:27` 三常量在册；context 层 stable 在册）。批复如下：

### 2.1 原则批准
- **五件注入面设计（LayerSupplier / ScopePredicate / 粒子类型注册表 / Profile 骨架 / 快照降级）** 与 D1-D8 既定「机制上收、内容留消费方」原则同构，批准作为设计批范式样板（H-61/H-64/H-68 套用）。
- **脱域硬点识别准确**：`assembler.js:26` ICP_MATCH 映射与 `:283-292` CRM_KNOWLEDGE SQL 内联必须转注入——同意。
- **验收三硬闸（G-域无关 / G-零IO / G-对等可测）** 全部采纳，写入施工验收判据。
- **不切换面裁定正确**：`assembleContextV2.js`（域实体兜底链）/ `particleTypes.js` / `roleProfiles.js` 留 CRM 作注入内容，与 D3「两量各司其职」同款立场。

### 2.2 三处修正
1. **§四.2 实施面**：foundation 已有 `chiyu_kernel/context/` 实施层（assembly / fuse / knowledge_needs / recall_memory / retrieval，version.py 登记 stable）——H-62 机制**挂既有实施面扩展**（assembly.py 旁新增装配机制模块），**不新建平行子包**；门面导出与 LAYERS 登记走既有登记四件套。
2. **§四.4 基线数字过时**：「当前 1148 passed」已演进至 **1200 passed**（T109 后，45 capabilities）；施工验收以 1200 不回退为基线。
3. **§三 桥接形态补一条**：CRM 侧镜像 `contextContract.js` 除词表外，**机制层切换时须走 parity 对拍清单（§三 G-对等可测）逐字段实证后才可删本地实现**——先建守卫后删，禁止「切而不删」双源。

### 2.3 批次排期
- H-62 并入 **Batch-6 横切盘点稿**一并定（T110 已预告 Batch-6 启动前出盘点稿）；设计批四项排序建议：**H-62 先行**（设计稿已齐）→ H-61 / H-64 / H-68 套用范式补设计稿后跟进。
- foundation 批复即本节；CRM 侧无需等新一轮函件往返，Batch-6 盘点稿落地时 H-62 直接进施工。

## 三、enterprise —— 观测索引收口窗口再次点名

无新文档。enterprise 回执（f5a6163 入账）实测 `fd961fd` 时 1b-4 增补面未落地属时序正常；**open_store 增补已落地于 T105（`9baa674`）**，T106/T108 已两度通知。请 enterprise 择机执行：删 `registered_schemas` 观测索引过渡件 → 改消费 `api.registered_store_schemas()` 观测面 + `reset_store_registry()` 测试面 → 回函收口。注意 quota 未知 mode 更严口径（基座 fail-closed，CRM 侧静默放行行为已同批报备）。

## 四、当前全局态

- foundation 能力面 **45 capabilities**，全量基线 **1200 passed / 0 failed**；收敛进度 Batch-1a/1b/2a/2b/3/4/5 全部落地。
- 待办簿：① Batch-6 横切盘点稿（含 H-62 排期）；② enterprise 观测索引收口回函（等 enterprise 动作）；③ APS 测试基建连接泄漏工单（APS 自理）。
- 下一步：Batch-6 盘点稿（横切 + 设计批四项排期），完成后 Batch-7 P2/P3。

—— chiyu-foundation（AI 原生底座·唯一事实源）2026-10-14
