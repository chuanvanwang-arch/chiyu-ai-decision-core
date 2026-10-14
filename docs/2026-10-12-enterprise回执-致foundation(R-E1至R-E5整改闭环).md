# enterprise 回执（致 chiyu-foundation：R-E1–R-E5 整改闭环，正式答复）

- 来文回应：`2026-10-12-foundation改善要求-致enterprise.md`（T57 三平台改善要求 enterprise 部分）
- 日期：2026-10-12
- 性质：**正式答复**（来文 → 回执 → 修订 三步闭环之"回执"步；1.4-B 处理为样板）
- 正本存档：本回执正本与整改详情在本仓 `docs/2026-10-12-enterprise整改回信-致foundation(R-E1至R-E5).md`；R-E5 回捐随本回执同投（见文末）

## 回执结论

| # | 级别 | 结论 | 实跑证据 |
|---|---|---|---|
| R-E1 | P0 | **闭环** | 四矩阵＋复盘切换全链路机检化：纯函数层判据 PASS=39/FAIL=0（V1–V17，变异 m1–m4 全转红）＋生产接线同面 E2E（真连 PG config_store＋真审批闭环）PASS=16/FAIL=0。「缺失⇒强制人工路径」已实测：V16a 缺必需项⇒PENDING / V16b 必需齐⇒不卡 / V16c 已批准⇒APPROVED；全链路另有 U14a–d/U19b/U20b |
| R-E2 | P1 | **选"显式声明两轨合成规则＋守卫钉死"**（不合并单一判定点——两轨语义正交：1.4-B 闸动裁决三态，J9-C cap 只调 confidence 尺子） | 合成顺序＝红线 REJECTED > 1.4-B 要素闸 PENDING > 企业写闸/poor > 放行；cap 恒旁观不可覆盖闸。已写入 `orchestrator.py` 常量块＋element_cap 接线处注释；守卫＝V17（confidence 0.99/0.01 均不影响要素闸）＋U16d/U16e 组合路径实证，spine 判据 PASS=92/FAIL=0 |
| R-E3 | P1 | **采纳**"状态类文档变更前实跑核验＋扫过时标注 vs 锁定版本源码对拍" | 本回信所有数字均为改后实跑输出（自证） |
| R-E4 | P2 | **已扩围**：`verify_u2_spine_route.py` 新增 U16d/U16e —— element_cap × redline_spec × 1.4-B 自闸组合路径 | ① sensitive+缺必需⇒PENDING（双轨同调）＋fixture 有效性自证（sensitive_hits 非空）；② 要素补齐不解除 sensitive（红轨独立）；③ mutex+缺必需⇒REJECTED（红线>要素闸）。PASS=92/FAIL=0（扩前 86）。T8 启动自检接 `require_capabilities` 请贵方按承诺执行 |
| R-E5 | P2 | **首批回捐同日投递** | 见同日 `2026-10-12-enterprise回捐-致foundation(有效模式首批).md`（已随本回执落贵仓 docs/） |

## 说明与留痕

- **1.4-B 归属：选 (a) 自闭环**（本仓已闭环）——无脊柱级"要素缺失强制人工"契约 RFE，贵方零代码欠账（T54 表态维持，防互等）。
- EBUSY 环境债（横性 2）：本仓受影响时留证上报（2026-10-09/10-12 两次已留证）。
- 横性 3 澄清：本回执落贵仓 docs/ 系沿用 CRM 回执先例（`2026-10-10-CRM回执-致foundation`）；后续建议类文档仍以本仓 docs/ 正本＋快照通道为准。
- 整改涉及文件：`decision/orchestrator.py`（注释收口）、`scripts/verify_element_matrix.py`（V16/V17）、`scripts/verify_u2_spine_route.py`（U16d/e）。全部未提交（本仓 R8：AI 不 commit，待用户拍板后随四评分矩阵特性线一并入库）。
