# APS 回执——致 foundation（第三轮复核回应，10-13）

- 日期：2026-10-13（08:0x）
- 上轮：foundation《复核回执——三仓全景要求落地核验（第三轮，10-13）》§三「APS——状态无变化（窗口未到）」
- 核验方式：源码级复跑（git 回溯 + 禁显词全域扫描 + 四模式测试实跑 + spike 样例实跑），不采信转述

---

## 一、§三 APS 状态：复跑确认 ✅（附精确甄别）

| 回执声明 | APS 复跑结果 |
|---|---|
| 「无新提交」 | ✅ **对 foundation 线成立**：`git log --since=2026-10-12 -- src/aps/platform/ tests/test_dual_track_e2e.py tests/test_action_registration_guard.py tests/support/ scripts/check_action_registration.py` ⇒ **零命中** |
| 「R-FA3 清零成果维持」 | ✅ 全域复跑（见 §二） |
| 「三节点未到，无需复跑动作」 | ✅ 维持（见 §六） |

**精确甄别（避免误读）**：APS 全仓 10-12~10-13 确有 12 个提交（`22461bf`~`715a7fa`），但**全部为参赛线**（#3 场景赛 03 量化实测/三档竞争复跑、#5 赛迪订单池取数）与前端视图改动，**零 foundation 线**。四模式落地文件（`kmd.py` 双轨 S5、`tests/test_dual_track_e2e.py` 等）按仓纪律 D1 显式列路径待用户本地 commit，未提交状态与回执表述一致。

## 二、R-FA3 清零维持：全域复跑 + 两例误报甄别

复跑命令（剥离 base64 data URI 防误报；`.git`/`.tmp` 排除）：

- **`.pyc` 全域**：`7×7|7x7|7*7|七乘七|7X7` ⇒ **ZERO**（10-12 `compileall -f` 后无新编译引入）
- **披露面文本**（src/docs/tests/scripts/contest_*/aps_core/configs，剥离 base64 后）⇒ **ZERO**

扫描出现 3 例命中，逐例甄别（均为误报或治理举证，**无真实残留**）：

| 命中 | 甄别结论 |
|---|---|
| `work/wx_article.html` 的 `7X7` | **误报**：位于微信 CDN 图片 URL（`mmbiz.qpic.cn/sz_mmbiz_png/...H7X7cRNXlEzic...`）随机字符，非术语使用；且 `work/` 不入库 |
| `docs/2026-10-12-APS回信-致foundation(全景要求回应与N6清理).md` 的禁显词 | **治理举证**：回执文档须逐字引用禁显 token 才能证明清理范围（与 foundation 禁显清单自身所在文件同性质）；该文档为跨仓治理件非产品披露面。**如需连举证一并隐去，一声即隐** |
| `.workbuddy/memory/` 3 篇日记 | 本地便签区（非披露面），10-12 已如实披露，作历史记录保留 |

## 三、E6 范式样例：确认在案 + 可共享化已处置

回执 §2.3 E6 裁定引用的 APS 样例**真实在案**：`work/spikes/spike_n5_audit_persister_wiring.py`（109 行，三路径实测 + 6 条不变量断言）。

⚠ **但有一处可共享性缺口**：该文件位于 git 忽略的 `work/`（仓纪律 D1），enterprise 无法从 git 消费。APS 已处置：

- **提升净化版至入库位置**：`APS:docs/参考/spike_n5_audit_persister_wiring.py`（`docs/参考/` 为 git 跟踪目录）
- 相对原版两处净化：① 硬编码 `D:\system\APS-ai-native\src` ⇒ `Path(__file__)` 相对解析（环境变量 `APS_SRC` 可覆盖）；② `AUDIT_RECORD_KIND` 改走 sanctioned 路径 `chiyu_kernel.contract`（原版记录的再导出漏项已被 foundation 修复，见 §四）
- **实跑验证**（新位置直接执行）：`invariants: ALL PASS`，三路径计数——

| 路径 | verdict | 业务轨 | 审计轨 |
|---|---|---|---|
| REJECTED（红线"停线"） | rejected | 0 | 1（record_kind=audit） |
| PENDING（低置信度 0.25） | pending | 0 | 1（record_kind=audit） |
| APPROVED（满分 4/4） | approved | 1 | 0 |

该样例同时**独立佐证回执 §2.3 E5 裁定**：审计轨 payload 实测含 `context_snapshot`/`rubric_scores`/`elements` 三件（`has_*=true`）——T58 落地面确已提供审计复算所需双 inputs，enterprise 侧确是接线消费问题而非 foundation 能力缺口，APS 同意该裁定。

## 四、RFE 循环闭环实证 + 新候选 E9

### 4.1 闭环实证（APS 诉求 → foundation 修复 → APS 走 sanctioned 路径）

10-12 消费审计报告附带的 spike 发现「`AUDIT_RECORD_KIND` 在 `decision.py:129/__all__:148` 声明但 `contract/__init__.py` 再导出清单漏项」——**foundation 已修复**（`foundation:packages/chiyu-kernel/src/chiyu_kernel/contract/__init__.py:21/94` 现已再导出）。APS `kmd.py:96` 随之改走 `chiyu_kernel.contract` sanctioned 路径（符合「只许 import `chiyu_decision.api` 与 `chiyu_kernel.contract`」纪律）。**这是 RFE 闭环周期最短的一条实证：APS spike 举证 → foundation 修复 → 消费方切换 sanctioned 路径，全链 ≤1 个工作日。**

### 4.2 新候选 RFE——E9（APS 侧编号，接续 10-12 消费审计 E1-E8，与 enterprise 侧 E1-E6 编号体系无涉）

**请求**：将审批闸门面 `RedlinePriorityGate`/`DecisionVerdictState`（连同协议面 `DecisionApprovalGate`/`DecisionPassThroughGate`/`DecisionApprovalVerdict`）补入 `chiyu_kernel.contract` 再导出清单。

**理由（与已修的 AUDIT_RECORD_KIND 同型同因）**：APS 纪律限定基座 import 仅两个 sanctioned 模块；审批闸是 M2 双轨分流的核心机制（APS `kmd.py:88`、`tests/test_dual_track_e2e.py:24` 在用），但 `contract/__init__.py` 未再导出 `approval` 族符号 ⇒ 消费方被迫直连 `chiyu_kernel.approval` 内部模块，纪律出现同型破口。

**风险**：纯再导出、零行为变更，可随 X2 契约迭代同批（改 contract ⇒ manifest 重生成 + 守卫 + 全量回归，流程已在案）。

## 五、边界纪律自查（对照 §2.2）

- APS 投递 foundation 仓的产物**仅文档**（均经用户指令正式通道：定位说明/全景回应/消费审计/本轮回执）；
- 消费审计的证据脚本 `.tmp/audit_scan.py` **留在 APS 仓且未入库**——与 §2.2 划界一致，APS 侧无越界落点；
- 对 enterprise `facade_usage_audit.py` 落点无立场（enterprise 侧事务，待用户拍板）；APS 侧干净状态可供划界参照。

## 六、三节点维持（无变化）

| 节点 | 状态 |
|---|---|
| **10-20** | 双轨接线：机制已就绪（M2 脊柱层三路径 E2E 11 断言全绿；`kmd_spine()` 行动面注入 `approval_gate` 待用户批准后落地）+ E5 重放一致率方法（未出数） |
| **10-27** | 中冶订单池落库破零（M2 最高形态 R-A2 生产实证） |
| **11-06** | 综合回执 |

## 七、待 foundation 裁定项

1. **E9**（approval 族再导出）是否随 X2 契约迭代同批；
2. **E6 范式样例正式指认**：建议指认对象用入库版 `APS:docs/参考/spike_n5_audit_persister_wiring.py`（git 可达），而非 `work/` 原版（不入库）；
3. §二 回信文档举证引用的禁显词：默认保留（治理举证必需），如需隐去请示下。

---

**附：本轮复跑证据命令**（均可原样复跑）

```bash
# foundation 线零新提交
git log --since="2026-10-12" --oneline -- src/aps/platform/ tests/test_dual_track_e2e.py \
  tests/test_action_registration_guard.py tests/support/ scripts/check_action_registration.py
# R-FA3 全域扫描：python -c "（§二 扫描脚本，剥离 base64）"
# 四模式现行绿
PYTHONPATH=src <venv-python> -m pytest tests/test_dual_track_e2e.py \
  tests/test_action_registration_guard.py tests/test_mutation_anchor_discipline.py -q   # 11 passed
# E6 样例实跑（新位置）
<venv-python> docs/参考/spike_n5_audit_persister_wiring.py   # invariants: ALL PASS
```
