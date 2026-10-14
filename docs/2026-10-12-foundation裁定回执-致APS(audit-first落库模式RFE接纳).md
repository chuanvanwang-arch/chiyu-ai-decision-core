# foundation 裁定回执：audit-first 落库模式 RFE —— **接纳**

- 收文：APS-ai-native `docs/RFE-audit-first落库模式-致foundation.md`（2026-10-12，附件 B 于《APS回信-正式答复》）
- 裁定方：chiyu-foundation
- 裁定日期：2026-10-12（**当日裁定**，早于 2 工作日承诺）
- 裁定结果：**接纳**，已落地实现（本回执即为落地凭证，非纸面承诺）

## 一、裁定理由

1. **诉求与基座哲学一致**：审计轨 ≠ 业务轨的诉求与三态闸「PENDING 不落正向边」同源——审计是不可变事实留痕，不是业务裁定；基座 S5 现有单一语义（REJECTED/PENDING 均 `persisted=False`，`spine.py:198`）确实无法表达「无条件落库留痕」，APS E2 实证（16 字段缺口）成立。
2. **最小侵入形态成立**：`run_spine(audit_persister=...)` 正交形参，缺省 None 零行为变更（对齐 `element_cap` 惯例）；与 `persister`/`audit_sink`/`resume_spine` 三者全部正交。
3. **收编收益双向**：APS 逐步迁回基座 `run_spine`（S2–S4 → S5），foundation 获得消费方真实跑在基座链上的生产实证；消费方放弃自扛 S5 后共享 resume/冻结裁定/审批闸护栏的演进红利。

## 二、落地内容（T58）

### 契约层（chiyu_kernel.contract.decision，manifest 已重生成）
- 新增 **`AUDIT_RECORD_KIND = "audit"`**：审计轨记录的契约级区分标记——消费方审计轨记录必须携带 `record_kind="audit"`；审计轨不得产生 DECIDED_ON 类正向边。

### 脊柱层（run_spine 新增正交形参）
- **`audit_persister: Optional[Callable[[SpineResult, str, Mapping], object]] = None`**
  - **触发时机**：仅 REJECTED / PENDING 分支，在 `audit_sink` 之外调用；**APPROVED 走 `persister` 业务轨，审计轨绝不触发**（守卫钉死）。
  - **payload** = audit_sink 基础字段（形状不变，既有消费方零破坏）+ `record_kind="audit"` + `context_snapshot`（消费方原始上下文）+ `rubric_scores` + `elements`（缓解 16 字段缺口的主干，余量可闭包补齐）。
  - **第一形参传 `SpineResult`**：消费方当场可补齐 decision_id 之外的裁定字段。
  - **fail-closed**：审计轨回调抛错 ⇒ 原样上抛——「审计优先落库」保证不允许静默丢失。
  - **resume 不受影响**：`resume_spine` 不引入该接缝（签名级守卫钉死），三铁律原样。

### 裁定对 APS 边谓词的回应
APS 提问「边谓词名服从基座裁定」：审计轨记录以 `record_kind="audit"` 标记区分（见上）；`RECORDED_FOR` 类审计边谓词由消费方域模型自定（基座不收域边谓词词汇，与 R134 契约不收域语义一致）。

## 三、守卫与验收（全部实跑）

| 判据 | 守卫（`test_audit_persister.py`，6 项） |
|---|---|
| REJECTED/PENDING 双轨各就各位（扩展载荷逐键断言） | ✅ |
| APPROVED 绝不触发审计轨 | ✅ |
| audit_sink 载荷零破坏（不含扩展键，逐键一致） | ✅ |
| 缺省 None 行为不变 | ✅ |
| 审计轨抛错 fail-closed 上抛 | ✅ |
| resume 无审计轨接缝（签名级） | ✅ |

- **变异自证两路转红**：剥离 PENDING 分支审计轨调用 ⇒ 恰 1 红；audit_sink 载荷混入 `record_kind`（轨道分离破坏）⇒ 恰 2 红；还原复绿零残留。
- 门面完整性 0 未暴露 + §13 零残留 0 处 + 能力清单 29 项（decision 语义补 audit-first 描述）；全量组合回归见文末更新行。

## 四、APS 侧后续（按 RFE §5 承诺执行）

1. `kmd.py` S5 拆双轨：APPROVED 走基座 `persister`；REJECTED/PENDING 走 `audit_persister`（记录携带 `record_kind="audit"`，不写正向边）。
2. 编排按 E1/E2/E3 复验结论排期迁回基座 `run_spine`（先 S2–S4 后 S5）；迁移后补判定一致率实测（E5 口径）。
3. 升级基座版本锚点（api_version 锁定处）后，`require_capabilities({"decision": "stable"})` 可读到含 audit-first 的最新能力语义。

---
*实现锚点：`spine.py`（run_spine 签名 + 两分支 + docstring）；`contract/decision.py:123-131`（AUDIT_RECORD_KIND）；守卫 `test_audit_persister.py`（6 项）。*
