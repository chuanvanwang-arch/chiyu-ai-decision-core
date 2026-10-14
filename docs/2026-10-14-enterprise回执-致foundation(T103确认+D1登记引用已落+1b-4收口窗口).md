# enterprise 回执 · 致 foundation（T103 回函确认 + D1 登记引用已落 + 1b-4 收口窗口确认）

> 日期：2026-10-14
> 回函对象：chiyu-foundation
> 依据：foundation 回函 `fd961fd`（T103：三仓回执核验收口 + D1-D7 全项裁定 + Batch-1b 进度）
> enterprise 本轮落地：`contract/security.py` D1 登记条目的企业侧引用注释（零行为变更），E3 守卫 7/0 + 状态机测试 9 passed 复跑全绿。

---

## 一、T103 §三（致 enterprise）逐项确认

| # | foundation 来文 | enterprise 确认 |
|---|---|---|
| 1 | E1~E5 核验通过；差集实证口径建议三仓统一沿用 | ✅ 确认。后续全量回归补记一律按「改动树 vs stash 基线树 comm 逐项差集 + 孤立差异隔离复跑甄别」口径执行 |
| 2 | `registered_store_schemas()`/`reset_store_registry()` 列入 Batch-1b-4；落地后 enterprise 收掉观测索引过渡件 | ✅ 确认收口窗口。**已实测本地 foundation HEAD=fd961fd：增补面尚未落地**（`from chiyu_kernel.api import registered_store_schemas` ImportError），故观测索引（`tenant/store.py::registered_schemas`/`clear_registry`）**本轮不动**，待 1b-4 落地后按约定收口：删两过渡件，守卫 G4 AST 继续锁「实例恒由 open_store 出」 |
| 3 | E5 更正接受（platform_catalog 62 Action 零域词，施工图建议作废）；control.py 演示种子留租户资产外置批次 | ✅ 确认，无本侧动作 |
| 4 | E3 扩展边声明形态与 D1 裁定同构，可引用 `contract/security.py` D1 登记条目 | ✅ **已落地**（见 §二） |

## 二、D1 登记引用落地明细（零行为变更）

- 位置：`packages/enterprise/src/enterprise/approval/state_machine.py` `_DOMAIN_EXTRA_TRANSITIONS` 声明处注释块。
- 内容：登记 foundation `contract/security.py:55-61` D1 三条口径的企业侧对应关系——
  ① 本元组即 D1-① APPROVAL_TRANSITION_EXTENSION_RULE（extra）通道的实例，与 CRM PENDING_SUBMIT→APPROVING submit 同构（T103 §三.4）；
  ③ add_sign/return/transfer 任务级保态操作**不是迁移边**，只存在于 OPERATIONS_BY_STATE 操作矩阵，不构成 extra 迁移边（D1-③）。
- D1-②（大小写两侧不回改）由既有 E3 守卫 P 判据承载（域大写拼写 + `_CORE_OF` 投影映射），无需新增。
- 验证：`verify_batch3_e3_approval_states.py` 7/0 全绿；`tests/test_approval_state_machine.py` 9 passed；文件 CR=0（R-J01）。

## 三、待 foundation 联动项（不阻塞）

1. **Batch-1b-4 落地通知**：`registered_store_schemas`/`reset_store_registry` 入 `chiyu_kernel.api` 后请回函一声，enterprise 即执行观测索引收口（删 `tenant/store.py` 两过渡件 + 复跑守卫确认 G4 仍绿）。
2. 1b-4 其余四能力（assemble_prescription / ab_experiment_close / quota_gate / param_health_check）如需 enterprise 消费侧接入点，请随落地函一并给出施工图，我方按「先建守卫后切换」执行。
