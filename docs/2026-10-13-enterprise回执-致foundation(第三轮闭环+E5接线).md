# enterprise 回执——第三轮复核闭环 + E5 接线落地（10-13）

- 来文：《foundation 复核回执——三仓全景要求落地核验（第三轮）》（10-13）
- 对应：enterprise 侧对 2.2 边界事项处置、2.3 六项 RFE 裁定、2.4 扩展建议裁定的逐项确认与补证。

---

## 一、2.2 边界事项：已处置 ✅

完全接受 foundation 的边界裁定。处置动作：

1. **`facade_usage_audit.py` 已移出 foundation 仓**：从 `chiyu-foundation/scripts/`（新建、未跟踪）移回 `chiyu-enterprise/scripts/`（该脚本硬编码 enterprise 仓路径、属消费方自身证据件，本应落消费方）。
2. **`chiyu-foundation/scripts/` 目录已删除**：foundation 工作区恢复干净（剩余未跟踪项均为 foundation 自身的 docs）。
3. **纪律确认**：消费方证据脚本落消费方仓；foundation 仓只收经正式通道的**文档/契约产物**——本轮回执及前两轮回执（R-FE 全景闭环、消费对照报告）均属文档件，合规。

> 注：该脚本现作为 enterprise 侧可复跑的消费对拍工具保留（`chiyu-enterprise/scripts/facade_usage_audit.py`），foundation 下轮自产「消费面对拍」正式件（`tools/` + 参数化消费方根 + 守卫 + lint）时，enterprise 可配合提供现有扫描逻辑作参考，⛔ 不沿用此未审件。

---

## 二、2.3 六项 RFE 裁定：逐项对齐

### E5（裁定：已满足，无需新能力）—— ✅ enterprise 侧接线已落地

foundation 裁定准确：**能力缺口在 enterprise 接线消费，不在 foundation**。本轮已完成 enterprise 侧接线，源码级实证如下：

| 项 | 落点 | 说明 |
|---|---|---|
| 取代旧 `audit_sink`（2 参） | `orchestrator.py:479-522` 新增 `_audit_persister`（3 参，SpineResult+event_type+payload） | `audit_persister` 是 `audit_sink` 超集（同触发条件 PENDING/REJECTED，多 `record_kind`/`context_snapshot`/`rubric_scores`/`elements`）⇒ **取代而非并存**（并存会双写审计记录 U7 计数翻倍） |
| 双 inputs 进审计 canonical | `orchestrator.py:435`（result dict `rubric_scores`）、`:520-521`（`_write_audit(rubric_scores=..., elements=...)`） | `rubric_scores`＝九尺子全量数值（⛔ 非 `{score,...}` dict 透传）、`elements`＝声明快照（复算「当时声明了哪些」） |
| 轨身份硬断言（R79 fail-loud） | `orchestrator.py:506-510` | `payload.record_kind != AUDIT_RECORD_KIND`（chiyu_kernel.api，`:30` 引入）⇒ 抛 RuntimeError，**⛔ 不静默写账**（业务/审计串轨＝账实不符） |
| run_spine 接线 | `orchestrator.py:586` `audit_persister=_audit_persister` | 取代 `:582` 注释所述旧 `audit_sink` |

**判据实证**（`scripts/verify_u2_spine_route.py`，R126 禁拆、U18 自然归属）：
- U18 新增 5 断言：a/b 双 inputs 进 canonical（PENDING+REJECTED 两分支齐接线）、c pending 只落 1 条（⛔ 双写）、d 剥 `record_kind`⇒RuntimeError fail-loud、e 放行态双 inputs 如实为空（两轨互斥 ⛔ 不伪造）。
- 变异⑧（`scripts/verify_u2_spine_route.py:977-981`，self-test `:1038-1041`）：剥掉 `audit_persister`（模拟「T58 审计轨未接线」）⇒ U18a/b 转红 + U7/U18c pending 零记录转红，**FAIL=10>0**，判据鉴别力成立。

**回归**：U2 spine route 真值态 **101/0**（含 U18 新增 9 闸）；八变异全红；`verify_element_matrix.py` **39/0**；`verify_retro_evidence_realstore.py` **8/0**；`verify_local_closure_t1236.py` 全绿。
**待办（用户硬约束）**：host 8000 仍在跑旧代码，重启属「启停动作必须由用户手动执行」（2026-10-03 立）⇒ E2E 留待你重启后复跑；U18 已由 in-process 判据 101/0 + 八变异证明接线有效。

### E6（裁定：以样例满足）—— ✅ 上游契约缺口已闭环

foundation 指认 APS `work/spikes/spike_n5_audit_persister_wiring.py` 为范式样例，enterprise 接受。补充实证：APS spike 附带发现的**契约再导出缺口**（`AUDIT_RECORD_KIND` 漏登于 `chiyu_kernel/contract/__init__.py` 再导出清单）已由 foundation 在 **T61（c80b728）** 修复，且连带抓出 5 处既有缺口并加「再导出完备性守卫」——enterprise 侧复测：`AUDIT_RECORD_KIND` 现已同时可达于 `chiyu_kernel.api` 与 `chiyu_kernel.contract`（`:30` import 实证）。E6 消费者侧缺口已清。

### E2 / E3 / E4（P1 双轨/分层/契约主路径维持）—— ✅ 纪律合规，源码确认

| # | foundation 裁定 | enterprise 侧实证 |
|---|---|---|
| **E2** | 双轨划界维持；纪律① host 侧不得自称即 foundation 协议 | `platform_handlers.py` 两阶段 confirm 自称「**两阶段 confirm 协议位**」，**非** foundation 协议（源码无 `foundation/kernel/协议` 自称）；跨仓一致性诉求走 RFE 再议收敛 |
| **E3** | 分层维持；enterprise 须实现 foundation provider 接口 | `orchestrator.py` 显式 `import` `LlmProvider`/`LlmResponse`（类型已 import，E1 只经 `chiyu_kernel.api` 门面，未绕过契约） |
| **E4** | 契约主路径=`DecisionIOField`/`register_scenario`，存储形态不裁 | enterprise DB 化（`particles`/`handler_registry`）为架构替代，I/O 契约（`register_scenario` 等）守住所依赖闭包已核验；无迁移说明需求 |

### E1（P2，以文档满足）—— 知悉，无 enterprise 动作

foundation 将工厂封装边界入《核心功能清单》增补节，enterprise 待其落地后可复跑 `facade_usage_audit.py` 核验边界清单与实际封装一致。

---

## 三、2.4 扩展建议裁定：采纳确认 + 一处可 actionable 发现

- **X1 / X3**：同意。priority profile / 四评分矩阵 / 权重本体留 enterprise（R134），⛔ 不入 foundation，防污染 L0。
- **X4**：portal 观察期成立（F2 已登记），enterprise 侧 `web/` 无 portal 门面消费（消费对照报告 Ⅳ 类已核实），维持「暂不涉足」判定。
- **X2（合成语义常量入 contract）**：采纳候选，enterprise 提供一处**可 actionable 补强**：
  - 实测（本回执复跑）：`AUDIT_RECORD_KIND` 已同时可达于 `chiyu_kernel.api` 与 `chiyu_kernel.contract` ✅；
  - 但 **`AUDIT_EVENT_*` 审计事件常量族（APPROVAL_PENDING / APPROVAL_REJECTED / APPROVAL_RESUMED）仅入 `chiyu_kernel.contract`，未再导出至 `chiyu_kernel.api` 门面**（实测 `api=False, contract=True`）；`AUDIT_EVENT_DECISION` 则 api/contract 均不存在。
  - **建议 X2 迭代纳入**：将跨仓共识的审计语义常量（`AUDIT_RECORD_KIND` 已是、`AUDIT_EVENT_*` 族）统一经 `chiyu_kernel.api` 再导出，使消费方经门面即可达，⛔ 不直触 `contract` 内部——与 E2/E3「只经门面」纪律同构。此补强与 foundation 既有「再导出完备性守卫」（T61）天然衔接。

---

## 四、结论与对齐待办

1. **2.2 边界事项**：已处置（脚本移回 enterprise，foundation 仓恢复干净）。
2. **E5**：enterprise 接线已落地 + 判据 101/0 + 八变异全红 + 关联回归全绿；E2E host 重启待你手动执行。
3. **E6**：上游契约缺口 T61 已闭环，接受 APS spike 为范式样例。
4. **E2/E3/E4**：纪律合规，源码实证的双轨/分层/契约主路径维持。
5. **X2**：采纳，并补「`AUDIT_EVENT_*` 经 api 门面再导出」的可 actionable 建议。
6. **enterprise 自产待办**（随四评分矩阵特性线提交，R8）：本轮 orchestrator E5 接线 4 处编辑 + `_audit_persister` 替换 + U18 闸/变异⑧ 均**未提交**，待你执行此前已给的提交命令（第 ② 笔或单独一笔）。

> 全仓未提交状态维持（R8：AI 不 commit）。本轮新增/修改：orchestrator.py（E5）、verify_u2_spine_route.py（U18+变异⑧）、facade_usage_audit.py（移回 enterprise）、本回执（foundation/enterprise 各一份）。
