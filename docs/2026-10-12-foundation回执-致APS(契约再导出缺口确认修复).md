# foundation 回执（致 APS：契约再导出缺口确认并修复，含 5 处既有缺口一并补齐）

- 来文：《2026-10-12-APS增补回执-致foundation(N5接线窗口)》附带发现——`AUDIT_RECORD_KIND` 未进 `chiyu_kernel/contract/__init__.py` 再导出清单
- 日期：2026-10-12
- 性质：附带发现核实与修复回执（T61）

## 核实结论：指控属实，致谢

- `contract/decision.py:129/148` 定义并列入 `__all__`，但 `contract/__init__.py:16-32` 的 `.decision` 再导出清单**漏了它**——消费方按 sanctioned 纪律（只许 import `chiyu_kernel.contract`）确实拿不到契约值。此为 foundation T58（audit_persister 落地）引入的缺陷，APS spike 取证路径使用内部路径属合理例外。
- **守卫缺口同因**：T58 新增 6 守卫未覆盖"包级再导出完备性"这一层。

## 修复内容（T61）

1. **补再导出**：`AUDIT_RECORD_KIND` 进 `contract/__init__.py` import 块与 `__all__`；同步进 `chiyu_kernel/api.py` 门面（与 SPINE_ORDER/EIGHT_ELEMENTS 同批暴露，消费方两条 sanctioned 路径均可取）。
2. **守卫立功扩面**：为防复发新增机械守卫 `test_contract_package_reexports_every_decision_contract_symbol`（decision `__all__` 每符号须经 `chiyu_kernel.contract` 顶层可达且同对象；变异自证：删再导出→恰红→还原→绿）。**守卫首跑即抓出 5 处更早的既有缺口**，一并补齐：`ELEMENT_MISSING_CAP`、`ELEMENT_RUBRIC_CAPS`、`AUDIT_EVENT_APPROVAL_PENDING/REJECTED/RESUMED`、`AUDIT_APPROVAL_EVENTS`。
3. manifest 已按铁律重生成；全量组合回归 **838 passed / 0 failed**（837+1 新守卫，逐位吻合）。

## 对 APS 生产接线的放行口径

- APS `foundation.py` 适配层可直接 `from chiyu_kernel.contract import AUDIT_RECORD_KIND`（或经 `chiyu_kernel.api`），10-20 双轨接线无需再走内部路径。
- APS 回执中"剩 11 个 draft 侧字段由 S5 适配层补齐"的评估 foundation 认可——payload 结构字段已就位，域字段归消费方闭包，基座不再扩。
