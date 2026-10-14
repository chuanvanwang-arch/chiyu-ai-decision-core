# CRM 回函 · 致 foundation（D6 增强闭环报告——处方守卫四道闸对齐）

> 回函对象：chiyu-foundation
> 事项：T103 §1.1 D6 裁定（foundation stricter 四道闸保留、CRM 自登记增强对齐）经用户批准后实施完毕。本函 = D6 闭环报告（CRM `40f0742`）。语义差 8 项自此**全部闭环**（D1-D5/D8 基座登记 + D6/D7 CRM 侧落地）。

---

## 一、实施内容（CRM `40f0742`）

`src/decision/closureLoop.js mapKnowledgeUpdateToPatch` 由两道闸扩为**四道闸**，与 `reflux_prescribe_guard` 同构：

| 闸 | foundation | CRM 实施 |
|---|---|---|
| ① 白名单 | `if key not in allowed` → REJECTED（禁降级） | 已有 `!PRESCRIBABLE.has(knob)`（不变） |
| ② resolvable | 消费方注入参数，false → REJECTED（防配置漂移空转） | 新增注入式 `{ resolvable }`（缺省 true 行为同前）；**同构声明：真实解析（knob→场景配置键映射经 configStore）属后续批次接线** |
| ③ to_value | （基座无此闸） | CRM 原有 stricter 闸保留，闸序置于 rationale 前（存量 reason 可判别不漂移） |
| ④ rationale | `str(rationale).strip()` 空 → REJECTED | 新增：三源取值 `rationale ?? reason ?? expected_impact`（复盘产出任一依据字段即可），strip 后判空拒绝 |

配套：`current` 注入回填 `from_value`（对齐基座 `from=current`）；**产物结构不变**（rationale 仅作闸判据，calibration_patch 落库面是否携带 rationale 留后续批次决策）；存量无依据知识项进入既有 `rejected` 收集通道，复盘主提交不受影响。处方恒 PENDING（savePatches + 第 0 闸 + HITL，CRM 侧由 `test/decision/routingRetro.test.js` 纪律测试把守）。

## 二、验证

- 新增四闸用例 8 项（resolvable 注入/缺省、rationale 三源与空白 strip、闸序可判别、current 回填）；既有 C3 夹具随新契约补 `reason` 字段（守卫变严是本增强目的）。
- **parity 守卫第⑦组**（`test/foundation-parity/contract-parity.test.js`）：`reflux.py` 四锚 ↔ CRM 四锚同构对拍——基座 `reflux_prescribe_guard` 四道闸任一形态变更，CRM 侧先红。**变异自证**：rationale 闸弱化为裸 truthy（丢 strip）→ 红 ✓ → 回滚全绿。
- 回归：closureLoop / routingRetro 全绿。

## 三、状态

Batch-3 全链收口：D1-D5/D8（基座 T100/T102 登记）+ **D6（本函，CRM `40f0742`）** + **D7（前函，CRM `f924d47`）** + G1-G4 双侧收口。Batch-1b-4 落地后 CRM 按守卫切换。P1 出口闸四项前置未变；本函不构成给 foundation 的正式回执。
