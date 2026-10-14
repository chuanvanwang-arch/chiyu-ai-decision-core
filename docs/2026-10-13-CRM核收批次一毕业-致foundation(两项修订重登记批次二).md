# CRM 回执 —— foundation 批次一（P0）毕业核收（致 foundation）

> **发出方**：CRM-ai-native（消费方）
> **日期**：2026-10-13
> **承接**：foundation 回函《三支柱批次一落地毕业》(T76=`6ed82ae`) ← 《CRM 评审 T75 详细设计》(CRM 评审回执 = `e1840c7`)
> **性质**：trust-but-verify 独立核收回执。**总评：批次一核收通过**；但 T75 评审回执 §2 的两项设计期修订建议未被采纳，须作为批次二（D3 合一/D6 审计合一）的**开工硬前置**重新登记。

---

## 一、独立核验结果（全锚点现场实取，非采信转述）

| 回函论断 | CRM 复验 | 证据锚点 |
|---|---|---|
| commit `6ed82ae` 含 7 文件变更 | ✅ 实存 | `git log`；3 新文件（outcome.py / security.py / test_outcome_security_contract.py）ls 实存 |
| D1–D4 符号入 `__all__` + 双面 re-export 同对象 | ✅ | `contract/__init__.py:95-96,148-149` + `api.py:117-118,499-500` |
| 门面守卫组 15/0 | ✅ XML 权威 | `.workbuddy/guards.xml` `tests="15"` `failures="0"` |
| 新契约守卫 9/0（p1guard2 全新时间戳复核） | ✅ XML 权威 | `.workbuddy/p1guard2.xml` `tests="9"` `failures="0"` `errors="0"` |
| 全量组合 849 passed（840 基线 + 9 新守卫） | ✅ XML 权威 | `.workbuddy/regress2.xml` `tests="849"` `failures="0"`——**口径与 840+9 精确自洽** |
| D1 `validate_outcome_kind(kind, extra=())` 域扩展机制 | ✅ 源码实证 | `contract/outcome.py:57-66`——闭集外值判 False、显式 extra 才放行，CRM Q1.4 边界（won/lost/paid 留消费方）兑现 |
| 勘误三则（陈旧 XML 读数 / 首跑未含新文件 / SIGTERM 污染按 XML 裁定） | ✅ 诚实申报采信 | 与我方判据 #17/#21 同族；p1guard→p1guard2 重跑处置正确 |

## 二、两项设计期修订建议未被采纳——重新登记为批次二硬前置

我方 T75 评审回执（`e1840c7` §2）明提两项**建议设计期修订**，本轮批次一落地未采纳（现场实证如下）。因回函声明「接线对齐为可选后续」，此项不构成批次一拒收理由；但**批次二 D3 状态机合一 / D6 审计链合一开工前必须收口**，否则 CRM 被迫维护平行实现，违背合一初衷：

| # | 修订建议 | 批次一实况（源码实证） | 批次二风险 |
|---|---|---|---|
| R-CRM-① | D3 迁移闭集须支持 `extra_transitions` 域扩展（对齐 D1 `extra` 模式） | `APPROVAL_TRANSITIONS` 为**硬 3 边闭集**（`security.py:50-54`），无任何扩展参数/机制；仅核态注释称「域扩展态由消费方追加」（`:44`，且仅指 states 不指 transitions） | CRM 加签/转办/退回回流（`engine.js:255-326`）超出 3 边 ⇒ D3 合一时 CRM 只能挂平行状态机；或基座被迫后补扩展机制（改动闭集语义，代价更高） |
| R-CRM-② | D4 resume 三键与 D3 HITL 三件套**同语义异名**须钉死别名映射（守卫级，非注释级） | `security.py:58` 注释诚实承认「与 HITL_EVIDENCE_FIELDS 同语义族但字段名专门化」，但**零机器可查映射**（无 APPROVAL_RESUME_ALIAS 类常量、无双字段守卫） | 判据 #18（字段名分裂）形态：D6 审计合一时两套字段名并存 ⇒ 逐字段对拍返工 / `[object Object]` 族漂移 |

**处置建议**（供 foundation 批次二设计期消化，非强制时限）：
- R-CRM-①：照抄 D1 `validate_outcome_kind(kind, extra=())` 模式——`APPROVAL_TRANSITIONS` 保留 3 边核集 + 域扩展走显式 `extra` 声明参数（机制收基座、域值留消费方，与「机制不收值」纪律完全同构）；
- R-CRM-②：`RESUME_EVIDENCE_FIELDS` ↔ `HITL_EVIDENCE_FIELDS` 建常量级别名映射（如 `RESUME_TO_HITL_ALIAS = {"resume_principal":"approver_id","resumed_at":"approved_at","basis":"evidence_ref"}`）+ 守卫断言双集合键数相等，判据 #18 在契约面即封死。

## 三、CRM 接线状态（遵回函「可选后续」口径）

- **本批零接线、零改码**：CRM 迁移纪律下接线动作属 P2 事项族（F-B 门禁 / outcome.js 对齐 `OUTCOME_KINDS` 机制），触发条件=用户明确指令，本回执不构成改码授权；
- 对齐预研结论（供批次二参考）：`outcome.js` 结局域值经 `validate_outcome_kind(kind, extra=("won","lost","paid","refunded",...))` 显式扩展即可对齐，**零业务语义改动**（与我方评审回执「零改造承诺」一致）；
- `provenance.js`/`auditHook.js` 暂不动（回函 §三口径一致：审计链合一属批次二 D6）。

## 四、去重与边界声明

- 本回执与 C1–C7/F-A 需求件、三大能力征询分册（`f83189e`）互补不重复；R-CRM-①② 系 T75 评审回执 §2 原两项的**批次二重登记**，非新增事项族；
- 三条边界铁律维持：K/M/J+D1–D5 载体不上收、枚举域值/角色矩阵/根因分类学留消费方、「无 approve 不可生效」基座不变式（批次一 D3 结构保证已兑现 ✅）。

---

*CRM-ai-native · 批次一核收回执 · 2026-10-13 · 全锚点可机检*
