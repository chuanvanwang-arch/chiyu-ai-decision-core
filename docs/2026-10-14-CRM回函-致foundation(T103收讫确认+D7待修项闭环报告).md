# CRM 回函 · 致 foundation（T103 收讫确认 + D7 待修项闭环报告）

> 回函对象：chiyu-foundation
> 事项：收讫 T103 回函（三仓回执核验收口 + D1-D7 全项裁定 + 第二轮盘点回执）。本函 = ① T103 各项收讫确认（CRM 侧零动作项确认）② D7 修复闭环报告（CRM `f924d47`，parity 守卫第⑥组对拍随建）。

---

## 一、T103 裁定收讫确认（CRM 侧）

| # | T103 裁定 | CRM 确认 |
|---|---|---|
| D1 | 按你方口径全部采纳（intra-pending extra / 大小写映射表 / 保态操作非边），T102 已登记 `contract/security.py` | ✅ 收讫；CRM parity 守卫第②组与此一致，无需改动 |
| D2 | 选 (b)：manifest 标注「CRM 增强面、非基座语义」 | ✅ 收讫；认同「基座最小面」理由，待第二消费方需求再升契约 |
| D3 | 确认 CRM 裁定，T100 落实（含 S3_aggregate 行「唯一来源=ratio」旧措辞连带修正） | ✅ 收讫；守卫第⑤组（0.7/0.79 各归其位）与 T100 互为镜像 |
| D4 | 同意禁互证；caps = J9-C 新增机制；CRM 是否采纳留迁移时决策 | ✅ 收讫 |
| D5 | 同意：REFLUX_KINDS 最小核闭集 + C4 留 CRM 扩展通道；路由键形态差异消费方适配 | ✅ 收讫 |
| D6 | foundation stricter 四道闸不回退；CRM 自登记增强、后续批次对齐 | ✅ 收讫；CRM 侧对齐（resolvable / rationale 两道闸补齐）列入后续批次，属增强、实施前按设计先行纪律另行报批 |
| D7 | 维持 no_data≠healthy；CRM deviationRate 补显式 no_data 态 | ✅ **本函闭环，见 §二** |
| D8 | 已闭环，foundation 零动作 | — |
| G1-G4 | 实施报告认可；两层 id 语义已按 CRM 提醒在 `contract/event.py` 登记（T102） | ✅ 收讫 |
| 第二轮盘点 | H-57~H-70 全部纳入 harvest 排期（首波 H-59/H-60/H-57/H-65）；H-58 env 参数化口径；H-62 另批评审 | ✅ 收讫；权威明细以 CRM 仓盘点账为准，排期启动时 CRM 即供对拍源 |

## 二、D7 修复闭环（CRM `f924d47`）

**修复面**（零业务行为变更，rate 数值不动）：

1. `src/decision/closureLoop.js` 新增纯函数 `windowStatus({ total, rate, rateAlarm })`：`total===0 → 'no_data'`；`rate > rateAlarm → 'alarm'`；否则 `'healthy'`（恰等于告警线不算 alarm，与处方判定 `>` 严格大于同口径）。词汇 ⊆ foundation `WINDOW_STATUSES` 闭集（CRM 用 no_data/healthy/alarm 三态，stagnant 留而不用、不做语义猜测）。
2. `deviationRate` 返回增 `status` 字段；HTTP 面（`decisionReadRoutes.js:354` 整对象返回）自动可判别「无数据 vs 零偏差」。
3. `hindsightCheck` 处方判定**显式排除 no_data**（`rate.status !== 'no_data'` && …）——不变式机制化，不依赖 rate=0 的数值巧合；返回增 `window_status` 透传。

**对拍**：parity 守卫新增第⑥组（`test/foundation-parity/contract-parity.test.js`）——CRM `windowStatus` 词汇 ⊆ `WINDOW_STATUSES`（词边界提取实际 return 值，防注释误入）+ no_data 显式在列 + 处方判定排除锚。**变异自证**：`no_data` 改 `nodata` → 红 ✓ → 回滚全绿。

**测试**：`test/decision/deviationRate.test.js`（纯函数三分支）；closureLoop / routingRetro 既有回归全绿。

## 三、状态

Batch-3 语义差 8 项全部闭环（D1-D5/D8 foundation 登记落实 + D6 排后续批次 + D7 本函闭环）；协议对齐 G1-G4 双侧收口。Batch-1b foundation 侧 1b-1~1b-3 ✅、1b-4 施工中——1b-4 落地后 CRM 按 parity 守卫切换（对拍源已就绪）。P1 出口闸四项前置未变；本函不构成给 foundation 的正式回执。
