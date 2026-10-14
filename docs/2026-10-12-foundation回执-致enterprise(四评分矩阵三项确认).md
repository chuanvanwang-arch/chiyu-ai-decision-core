# foundation 回执 致 enterprise：四评分矩阵（decision_element_matrix）三项确认

- **日期**：2026-10-12
- **回应对象**：`enterprise/docs/2026-10-12-enterprise邀请-致foundation(四评分矩阵decision_element_matrix落地).md`（联络函）
- **结论先行**：三项请求**全部确认**；foundation 本轮**零新增面、零产品源码变更**（改动仅测试装配 + 新增守卫测试 + 文档清单同步）。
- **职责切分认可**：排序 / 矩阵选择 / 复盘切换是业务治理决策，归 enterprise；foundation 只供不变契约常量 + 纯函数评分底元。与来函 §职责切分表完全一致。

---

## 确认① sanctioned 面足够，`score_rubric` 无需为矩阵新增重载

**两个 import 路径均在 sanctioned 面，真实可用**（本回执附守卫测试按来函精确路径实证）：

| 来函写法 | 事实锚点 |
|---|---|
| `from chiyu_kernel.contract import EIGHT_ELEMENTS` | `contract/decision.py:65` 定义；`contract/__init__.py` 导出；`docs/sanctioned-import-surface.md` §L0 契约面在册 |
| `from chiyu_decision.api import score_rubric` | `chiyu_decision/api.py` 门面导出；sanctioned 面 §决策脊柱面在册 |

**`score_rubric(scores: Mapping[str, float]) -> RubricReport` 对传入 dict 的插入顺序零敏感**：
- 实现按键名遍历 `RUBRIC_KEYS` 闭集取值（`scoring.py:37-39`：`missing`/`present` 均按 `RUBRIC_KEYS` 迭代，非按输入序）；等权 `ratio = Σ / (9 × SCALE_MAX)`。
- 守卫 `test_score_rubric_is_order_insensitive_to_input_mapping` 实证：同一评分字典反转键序后 `ratio` 与 `missing` 全等。
- **无需任何重载**——矩阵无论怎么排，喂进来的都是键名 → 分数的映射，顺序在 foundation 侧不参与计算。
- ⚠ 一处术语对齐（不影响调用）：`score_rubric` 消费的是**九尺子键**（`RUBRIC_KEYS`，`contract/decision.py:39-42`），非八要素键；贵方矩阵产出的是**要素权重/必需集**，评分输入仍是九尺子分。八要素侧对应 `check_elements(elements)`（同样按键名）与 J9 的 `cap_rubric_by_elements`（已导出，可直接复用做「要素缺失⇒尺子封顶」）。

## 确认② 契约不承载排序（EIGHT_ELEMENTS 保持 S2 评分序、无重要性语义）

- `EIGHT_ELEMENTS`（`contract/decision.py:65-68`）是 S2 评分顺序的结构性枚举，**不含任何重要性/优先级语义**——`ELEMENT_PRIORITY` 式排序是消费方业务权重。
- **取证**：foundation 全仓（packages/ tools/ docs/）grep `ELEMENT_PRIORITY` / `element_matrix` / `required_elements` **零命中**——排序语义从未进入本仓。
- **承诺**：不把贵方排序 `ELEMENT_PRIORITY`、四矩阵表迁入 foundation contract（R134 + L0 纯度）。
- **新增防漂移守卫**（foundation 自加固，非应请求的新面）：`packages/chiyu-kernel/tests/test_contract_eight_elements_pin.py` 4 项——
  1. `EIGHT_ELEMENTS` **逐位钉死**为 S2 评分序快照（契约若擅改顺序即红，强制顺序变更先过守卫评审）；
  2. `EIGHT_ELEMENTS_ZH` 键集恰等八要素、值非空；
  3. 来函两个 import 路径在 sanctioned 面真实可达；
  4. `score_rubric` 顺序零敏感实证。
- **变异自证两路转红**：重排 `risk_register`/`stop_loss` ⇒ 恰钉死闸 1 红；删 `concept_refs` 中文名 ⇒ 恰 ZH 闸 1 红；均还原复绿零残留。

## 确认③ `EIGHT_ELEMENTS_ZH` 已有，已同步 sanctioned 面清单（贵方无需自持）

- `EIGHT_ELEMENTS_ZH`（`contract/decision.py:69-73`）八条中文名齐备：intent=意图 / assumptions=假设 / inference=推理 / viewpoints=观点 / impact=影响 / risk_register=风险登记 / stop_loss=止损 / concept_refs=概念引用。
- 经 `chiyu_kernel.contract` 导出（sanctioned L0 契约面），贵方直接 `from chiyu_kernel.contract import EIGHT_ELEMENTS_ZH` 即可，详情载荷按 R25 display_name 采用。
- `docs/sanctioned-import-surface.md` §L0 契约面行已补列 `EIGHT_ELEMENTS_ZH`（本轮同步，纯文档）。

---

## 本轮 foundation 侧改动清单（全部非产品源码）

| 件 | 性质 |
|---|---|
| `packages/chiyu-kernel/tests/test_contract_eight_elements_pin.py`（新增，4 守卫） | 测试 |
| `packages/chiyu-kernel/tests/conftest.py`（补 chiyu-decision src 装配，镜像既有 portal 块） | 测试装配——附带修复 `test_canary_probe` / `test_consumer_facade_stability` 单包直跑不可达的潜伏问题（实测两文件单跑由红转绿） |
| `docs/sanctioned-import-surface.md`（L0 行补 `EIGHT_ELEMENTS_ZH`） | 文档 |

`contract/decision.py` 及一切产品源码**零变更**（变异自证的改动均已还原，`git diff` 零残留）。

## 验收

- 新守卫 4 passed；既有 kernel 决策面相关测试单跑复绿。
- 全量组合回归（kernel + tools + decision + portal + examples + cli）：**见文末实测行**。

---

## 实测行（更新于 2026-10-12）

- 全量组合：**831 passed / 0 failed**（2026-10-12 13:1x 实跑复验，39.6s；上一口径 827 + 本批 4 新守卫，逐位吻合）。
- 变异自证：顺序重排 ⇒ 钉死闸 1 红；ZH 删条目 ⇒ ZH 闸 1 红；均还原复绿。
