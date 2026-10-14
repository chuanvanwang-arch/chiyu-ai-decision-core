# 三平台四件套落地合规盘点（foundation 裁定，2026-10-12）

- 性质：对"CRM/APS/enterprise 是否完全按本仓要求落地八要素、九尺子、四评分矩阵、决策脊柱"的源码级裁定
- 方法：三路并行 Explore 取证（file:line 锚点）+ foundation 契约锚点对拍（`contract/decision.py`：SPINE_ORDER/RUBRIC_KEYS/EIGHT_ELEMENTS/ELEMENT_RUBRIC_CAPS/AUDIT_RECORD_KIND）+ enterprise 两份主判据本机复跑
- 证据基准：2026-10-12 当日源码实查；enterprise verify_element_matrix.py PASS=39/FAIL=0、verify_u2_spine_route.py PASS=92/FAIL=0 均由 foundation 侧复跑确认

## 一、总裁定矩阵

| 能力 | CRM | APS | enterprise |
|---|---|---|---|
| ① 八要素 | ⚠️ **部分**（概念自实现，键名漂移） | ✅ 直连原生（is 同一性护栏） | ✅ 直连原生（0 重实现） |
| ② 九尺子 | ⚠️ **部分**（本地同构重写＋桥层硬编码复制） | ✅ 完全直连（C-B 铁律合规） | ✅ 锚定式自持（键序加载期硬锁） |
| ③ 四评分矩阵 | 不适用（enterprise 消费面） | 不适用（enterprise 消费面） | ✅ 全链路自有业务层＋复盘闭环 |
| ④ 决策脊柱 | ✅ 完全消费（1/27 场景试点内） | ✅ 机制采纳、编排自立（三硬判据有实测支撑） | ✅ 真直连、六阶段全委托 |
| 改善要求 | R-C1~R-C5 **5/5 落地** | R-A1/A3/A5 ✅；R-A2/A4 排期中 | R-E1~R-E5 **全闭环** |

**结论：没有一家"完全"覆盖四件套——enterprise 最接近（四项全合规）；APS 机制合规但迁移执行滞后；CRM 脊柱消费合规但八要素/九尺子是平行实现，存在 1 处键名漂移地雷。**

## 二、逐仓裁定

### enterprise —— 完全消费、原生契约优先（合规度最高）

- **八要素**：`orchestrator.py:30/67`、`strictness.py:32` 直连 `EIGHT_ELEMENTS`，不自持清单；S2 序零触碰（run_spine 只透传 elements）；`element_cap=True` 走基座原生护栏（orchestrator.py:557）；1.4-B 自闭环闸在 `_SpineApprovalGate.decide`（:166-187），V16a/b/c + U14a-d 实测。
- **九尺子**：自评器（rubric.py:191）与基座 RUBRIC_KEYS 逐字同序同刻度，`control_plane.py` 加载期 `is` 硬断言 `_ENT_RUBRIC_KEYS != RUBRIC_KEYS ⇒ RuntimeError` fail-closed。属"锚定式自持"，合规。
- **四评分矩阵**：strictness.py:73-108 定义 + M1-M4 方案 + adjacent_matrix 边界；全消费链（registry→control_plane→ctx 注入→1.4-B 闸）+ 复盘闭环（decision-element-matrix-apply 双注册）。**主判据 foundation 复跑 39/0、92/0 与回执声称一致。**
- **脊柱**：orchestrator.py:349/532-566 真直连，缺包 fail-closed（U9 实证）；双版本闸（Dockerfile version-gate + lifespan require_capabilities 六键 stable）；import 面零越界（全部落在 sanctioned 五模块内）。
- **遗留（非致命）**：
  1. E2E `verify_element_matrix_e2e.py`（16/0）本环境 SKIP（无 CHIYU_DB_DSN）——"生产接线同面"证据暂只存在于文档声称，**需带 DSN 独立复跑一次**；
  2. 九尺子各尺子 0-4 判据语义等价性无机检（硬断言只锁键序）；
  3. 邀请函文档残留首版"等权"方案表述（实现已重定义为 M1-M4，无等权方案）。

### APS —— 机制采纳、编排自立有据；主要风险是 RFE 收编后迁移滞后

- **八要素**：foundation.py:179-180 直连契约（模块头明文"抄一份即第二事实源"）；kmd.py:167-172 构造期校验 elements ⊆ EIGHT_ELEMENTS，未知键即 ValueError。
- **九尺子**：kmd.py:75-83 import 期 `is` 同一性断言四个机制函数必须是基座门面对象；S3 闸门置信度唯一来源=基座 score_rubric 等权 ratio（kmd.py:464-466），自有加权仅诊断且 configs/ 无权重配置节——**C-B 铁律零违规**。
- **四评分矩阵**：不适用（foundation 契约未下发该能力，属 enterprise R-E1 消费面）。
- **脊柱**：KmdSpine 同源自实现（kmd.py:343），阶段键集 import 期逐项等于基座 SPINE_ORDER（kmd.py:647-660）；不调基座 run_spine 的三硬判据均有 E1/E2 实测支撑（e1_result.json：supply_rate 0.7778→0.8333 跨 0.79 翻转=HARD BLOCKER；S4 双档红线语义压缩；S5 语义相反），差异在 routes_views.py:525-547 公开登记，非隐藏漂移。
- **改善要求**：R-A1 ✅（E1/E2/E3 当日实跑）；R-A3 ✅（RFE 已提，foundation T58 已裁定接纳并落地 audit_persister）；R-A5 ✅（E4 扫描机制化，过时标注已修，复跑 exit=0）；R-A2 生产破零排期 10-27 中冶订单池/11-06 回执；R-A4 MCP 排期 10-23 stdio spike。
- **最重要缺口**：**基座 audit_persister（T58）已可用但 APS src/ 零调用**——仍自扛 S5 无条件落库（kmd.py:493-550）；RFE §5 承诺（S5 拆双轨 record_kind、编排逐步迁回 run_spine、E5 一致率）均未动工。需盯 10-20 / 11-06 两个排期节点。

### CRM —— 脊柱消费合规、R-C 整改全落地；但八要素/九尺子是平行实现

- **八要素** ⚠️：src/ 零处引用基座 EIGHT_ELEMENTS；本地 `materializeEightElements()`（decisionRepo.js:180）落 8 个 JSONB 列，**第 5 要素键名漂移：CRM `implications` vs 基座 `impact`**（decisionRepo.js:363 ↔ foundation contract/decision.py:68）。当前不炸仅因唯一 spine 调用点强制 elements={}（quote_approval_shadow.py:72 ⇒ 恒 PENDING）；P2 场景迁移若喂本地 elements，会被判缺 `impact`——**隐形地雷，须整改或登记对拍**。
- **九尺子** ⚠️：rubricScorer.js:24-34 九键同序同刻度但属重写非引用；桥层 quote_approval_shadow.py:26-29 手抄 RUBRIC_KEYS 元组（契约复制，改 import chiyu_kernel.contract 零成本）。
- **四评分矩阵**：不适用。
- **脊柱** ✅：QUOTE_PRICING 场景完全消费——Python 直调 run_spine（未重造审批闸，复用 RedlinePriorityGate）+ 影子对拍台账（五级 MATCH/P0-P3）+ HTTP sidecar 权威接管（REJECTED 硬拒/degraded 显式告警/开关三态 node/dual/spine）；A-1 图写走 T54 sanctioned 工厂 open_graph_write_store，无绕门面直连 PG。其余 26 场景按迁移计划 P2 扩面。
- **改善要求**：R-C1~R-C5 **5/5 落地**，代码+守卫测试+回执三证齐（R-C4 还附带根因纠偏：EBUSY=spawnSync 固有，async spawn 正常，已上报）。

## 三、本轮新发现（待处置清单）

| # | 级别 | 项 | 处置建议 |
|---|---|---|---|
| N1 | P1 | CRM 八要素键名漂移 `implications`≠`impact` | CRM 侧整改（改列名或映射层）+ 补契约键集守卫；或经 RFE 通道申请字段映射底元 |
| N2 | P2 | CRM 桥层 RUBRIC_KEYS 硬编码复制（quote_approval_shadow.py:26-29） | 改 import chiyu_kernel.contract.decision，零成本 |
| N3 | P1 | enterprise 矩阵 E2E 16/0 无法独立复验（SKIP 无 DSN） | enterprise 带 CHIYU_DB_DSN 实跑一次并回执留痕 |
| N4 | P2 | enterprise 邀请函残留首版"等权"方案表述 | 文档口径订正（R-E3 纪律自查项） |
| N5 | P1 | APS audit_persister 未接线（T58 已落地待消费） | 盯 APS 10-20 E5+V3 / 11-06 落库两个排期节点；逾期未动工再催办 |

## 四、foundation 侧已到位的对应能力（供三仓对表）

- audit_persister 正交形参 + AUDIT_RECORD_KIND 契约（T58，`contract/decision.py:129`、`spine.py` REJECTED/PENDING 分支）——APS 接线对象。
- EIGHT_ELEMENTS 钉序守卫 4 条（T55，test_contract_eight_elements_pin）——CRM/APS/enterprise 可参照自建键集对拍。
- sanctioned 工厂 open_graph_write_store / build_graph_write_server（T54）——CRM 已消费。
