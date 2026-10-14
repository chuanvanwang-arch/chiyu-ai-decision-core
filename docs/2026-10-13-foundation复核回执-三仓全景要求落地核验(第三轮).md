# foundation 复核回执——三仓全景要求落地核验（第三轮，10-13）

- 日期：2026-10-13（06:3x）
- 上轮：《foundation 复核回执——三仓全景要求落地核验》（T65，10-12）
- 核验方式：源码级 grep/git 回溯 + 本机实跑（vitest 计数 + 自做变异实证 + enterprise 盘点脚本复跑）

---

## 一、CRM——R-FC1~R-FC4 全部落地，本轮实跑确认 ✅

| # | 实跑核验 | 结果 |
|---|---|---|
| R-FC2 | `grep -rn "7×7\|7x7\|7X7" src/ scripts/ db/` | ✅ **0 命中**；清理范围 9 文件（`789c107`） |
| R-FC2 勘误 | `git show 789c107^:src/web/sales-decision-monitor.html` 回溯 | ✅ **勘误成立**：清理前确有 10 处（3 处用户可见）——foundation 上轮「展示页零命中」表述**有误，认账**；CRM 保留 test/docs 历史文件的边界决策合理（不返改 dated 记录） |
| R-FC3 | 守卫 `rfc3-seven-dims-consistency.test.js` 实跑 | ✅ **5/5**；两侧源码程序化提取（非手抄） |
| R-FC3 变异 | **foundation 自做变异**：本地 DIMENSIONS 一键改名 | ✅ **2 用例转红 → 还原复绿 5/5**（守卫真实有效，非恒绿） |
| R-FC4 | `quotePricingSidecar.test.js` + 真实 spawn 集成两文件 | ✅ **18/18 + 11/11**；/healthz 回传 api_version+capabilities、Node 侧握手先于裁定、版本不符不触达 /judge、不计熔断——实现抽查属实 |
| R-FC1 | 迁移计划 P2 行 | ✅ 已登记（dd01bcd），三判据+27/26 口径对账项在案，未静默取值 |

**存量红登记**：CRM 全量 62 失败已四重甄别为存量（与本轮无关），按纪律不顺手修——建议 CRM 单列排查任务；foundation 不背书其归因，仅登记。

## 二、enterprise——消费对照文档 + 6 项 RFE，foundation 初步裁定

### 2.1 文档数字复跑确认

- enterprise 投来证据脚本，foundation **本机复跑**：499 符号 / 已用 99（19%）/ 未用 400——与其文档逐位吻合 ✅
- 口径差解释成立（我方清单 ≈478 只列 contract 两节，其扫 contract 全子树 499）
- 400 未用四类归因（架构替代/工厂封装/自建并存/业务不涉足）逐条有锚，**无「该用没用」缺口**的结论可信

### 2.2 ⚠ 边界事项：证据脚本落点越界（需处置）

enterprise 将 `facade_usage_audit.py` **直接投进 foundation 仓工作区**（新建 `scripts/` 目录，git 未跟踪）。按仓边界纪律，消费方证据脚本应落**消费方自身仓**；foundation 仓只接受经正式通道的文档/契约产物。
- **临时处置建议**（待你拍板）：① 移入 `chiyu-enterprise/scripts/`（该脚本本为 enterprise 侧证据，硬编码路径亦为其仓形态）；② 若 foundation 欲自有「消费面对拍」能力，另起 `tools/` 正式件（参数化消费方根+守卫测试+make lint），⛔ 不沿用此未审脚本。
- foundation 工作区当前不受污染（未跟踪、未入库）。

### 2.3 六项增强需求（RFE 候选）初步裁定

| # | 裁定 | 理由 |
|---|---|---|
| **E5** | **已满足，无需新能力** | T58 audit_persister payload 已含 `rubric_scores`+`elements`——审计复算所需双 inputs 在审计轨内；enterprise 缺的是**接线消费**（接 audit_persister 并在审计落库记录明细），非 foundation 能力缺口 |
| **E6** | **以样例满足，不新增件** | APS `work/spikes/spike_n5_audit_persister_wiring.py` 即最小消费样例（三路径实测在案）；foundation 可在下轮回执中正式指认其为范式样例 |
| **E2**（P1） | **双轨划界维持，不强制迁移** | foundation confirm token 是 MCP 工具写面的 sanctioned 零信任协议（CRM 在消费）；enterprise host 侧两阶段（46 动作）是其宿主策略层，允许并存。纪律：① host 侧不得对外声称即 foundation 协议；② 跨仓一致性诉求走 RFE 再议收敛 |
| **E3**（P1） | **分层维持** | foundation 出 provider 契约（LlmProvider/LlmResponse）+ build_provider 基础件；enterprise 多 provider 运行时切换（provider_switch）是其编排层，允许自建——前提是实现 foundation provider 接口（已满足，类型已 import） |
| **E4**（P1） | **契约主路径=DecisionIOField/register_scenario，存储形态不裁** | 1.0 承诺覆盖 I/O 契约（IO_KINDS/GATE_KINDS），ScenarioPackStore 是文件包部署形态，enterprise DB 化（particles/handler_registry）是架构替代——**只要 I/O 契约守住即合规**，不裁主存储形态，不出迁移说明 |
| **E1**（P2） | **以文档满足** | 工厂封装边界可入《核心功能清单》增补节（下轮 foundation 自产，不占 enterprise 排期） |

### 2.4 扩展建议裁定

- **X2**（红线>要素闸合成常量入 contract）：**采纳候选**——确有跨仓共识价值（R-E2 合成规则现为企业注释级）；入 contract 须走标准流程（改 contract ⇒ manifest 重生成+守卫+全量回归），排下轮契约迭代
- **X1/X3**：同意——priority/矩阵/权重留企业侧（R134），⛔ 不入 foundation
- **X4**：portal 观察期成立（F2 已登记）

## 三、APS——状态无变化（窗口未到）

- 无新提交；10-20 双轨接线（待用户批准）+E5、10-27 破零、11-06 综合回执三节点未到；R-FA3 清零成果维持。无需复跑动作。

## 四、结论与待办

1. CRM：R-FC1~R-FC4 **全部闭环**，转入 P2 开工盯办（等 P1 出口闸 CLEARED）；
2. enterprise：维持+月度回捐；E5/E6 以「接线+样例指认」满足，E2/E3/E4 划界维持，X2 排契约迭代；
3. **待用户拍板**：facade_usage_audit.py 落点处置（移 enterprise 仓 or 本仓另起正式件）；
4. foundation 自产待办：E1 工厂边界清单增补（并入核心功能清单文档）、X2 契约迭代评估。
