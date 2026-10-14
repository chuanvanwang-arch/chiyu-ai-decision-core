# Foundation 回函 —— P-1 结局采集 API 落地 + P-3 resume_spine breaking 变更（致 CRM / APS / enterprise）

> 裁定方：chiyu-foundation（本仓，AI 原生底座唯一事实源）
> 致：CRM / APS / enterprise（三仓消费方）
> 背景：T79 实现排期 P-1 / P-3 + APS ②a 裁定（T80）收口后，按用户指令**选项 1**
>      实现 P-1 + P-3（P-3 按设计做 breaking 强校验）。
> ⛔ 仓边界：本仓**严禁向三仓仓库写任何产物**，故三仓调用点改造由各自仓库完成；
>   本函为调用点改造指引 + 对接面说明。

---

## 一、P-1 落地：结局采集 API（解 CRM writeOutcome 六字段适配阻塞）

**新增（chiyu_decision 内核实现，契约在 `chiyu_kernel.contract.outcome`）**：
- `append_outcome(outcome: Mapping, *, extra_kinds=()) -> str`：校验 `OUTCOME_REQUIRED_FIELDS`
  六字段（outcome_id / decision_id / outcome_kind / recorded_ts / recorded_by / evidence_ref）
  + `outcome_kind ∈ OUTCOME_KINDS ∪ extra_kinds`，落 foundation 内核 **append-only 结局台账**，
  返回 outcome_id；重复 id / 缺字段 / 非法 kind 均 fail-fast 抛错。
- `list_outcomes(decision_id: str) -> Tuple[Mapping, ...]`：按采集顺序返回该 decision 全部结局；
  无记录返回 `()` 诚实降级（支持 CRM won/lost/paid 时间序列多结局并存）。
- 门面：`chiyu_decision.api`（消费方纪律面）已 re-export `append_outcome` / `list_outcomes`。

**对接面（CRM 专项）**：CRM `writeOutcome` 六字段可直接映射 `OUTCOME_REQUIRED_FIELDS`
（won/lost/paid → 经 `extra_kinds=("won","lost","paid")` 声明，禁裸字符串）；`recorded_by`
填 user_id、 `evidence_ref` 填订单/结算单 id。CRM 此前卡在 P-1（append_outcome 未落）的
适配阻塞**本实现即解药**。

**持久化边界**：内核台账为**进程内** ledger（与 foundation `persister` 鸭子类型哲学一致——
内核校验 + 落账，落库耐久由消费方经返回记录自行承接）；不引入 PG 耦合。

---

## 二、P-3 落地（breaking）：resume_spine 入口 HITL 证据结构保证

**变更（chiyu_decision.spine.resume_spine）**：
- 新增必填入参 `resume_evidence: Mapping[str, object]`（**breaking**，T81）。
- 入口（PENDING 校验后、persist 前）强制
  `assert_hitl_evidence(resume_evidence, aliases=RESUME_EVIDENCE_FIELDS)`；
  缺或三键不全即抛 `HITLEvidenceError` **拒续跑**（落 `approval_resumed` 审计失败态），
  绝不静默放行——「无 approve 不可生效」结构保证点（D4）。
- 成功审计 payload 随附 `resume_principal` / `resumed_at` / `basis` 三键，与决策审计**同链可追**
  （APS P0-B 收口：PENDING 放行证据与决策审计同源）。

**调用点改造（三仓各自仓库执行）**：原 `resume_spine(result, persister=..., approval_ref=...)`
须补传：
```python
resume_spine(result, persister=save, approval_ref="AP-2026-0001",
             resume_evidence={"resume_principal": "<审批人>",
                              "resumed_at": "<ISO-8601>",
                              "basis": "<决策 id / 证据 ref>"})
```
`approval_ref`（审批单号）保留为可选溯源字段；`resume_evidence` 为强制证据三件套。

**附带修复（同批）**：`assert_hitl_evidence` 别名语义 bug——`aliases=RESUME_EVIDENCE_FIELDS`
时原实现 `required` 为空致断言**恒放行（no-op）**，违背「判据等价切换为 RESUME_EVIDENCE_FIELDS
语义」文档约定（旧测试只验 happy-path 掩盖）。已修复并补「缺字段即红」变异自证。

---

## 三、验收（trust-but-verify，junitxml 直读）

- 新增守卫：`test_outcome_collection.py`（P-1，9 用例）/ `test_spine_resume.py` 增补
  P-3 缺/不足证据即红 + 证据校验在 persister 前 / `test_batch2_contracts.py` 增补
  hitl 别名缺字段即红。
- 变异自证×2：① 删 hitl `+tuple(aliases)` → 别名校验转红 → 还原；② 删 resume 入口
  `assert_hitl_evidence` → 不足证据续跑转红 → 还原。
- 组合全量回归：**797 passed / 0 failed**（chiyu-kernel 690 + chiyu-decision 82 +
  chiyu-cli 13 + 根 tests 12）。

---

## 四、三仓对齐动作

| 仓 | 动作 |
|---|---|
| CRM | ① `writeOutcome` 六字段对接 `append_outcome`（P-1 解阻塞）；② `resume_spine` 调用点补 `resume_evidence`（影子台账 resume 三键解阻塞）；③ 此前 T79 已确认的两项设计评审修订已吸收 |
| APS | ① `reflux_record_outcome` 对接 `append_outcome`；② `resume_spine` 调用点补 `resume_evidence` |
| enterprise | ① `retro_backend` / `decision_memory_store` 接 `append_outcome`（此前 Q1.1 缺口二次实锤）；② `persist_resume` 经 `resume_spine` + `resume_evidence` 等价断言（保留域复算逻辑） |

> 本函为对接面说明；三仓源码改造由各仓在其仓库完成（本仓不越界写产物）。改造完成并回
> hold-good 后，T79 实现排期 P-1 / P-3 完全闭合。
