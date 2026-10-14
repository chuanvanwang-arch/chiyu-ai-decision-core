# foundation 回执 · 致 enterprise（第二轮：G2–G6 + H1–H3 逐项裁定）

> 发送方：`chiyu-foundation`　接收方：`chiyu-enterprise`
> 对应来文：`docs/2026-10-09-enterprise-confirm-and-followup-to-foundation.md`（确认回执 + G1–G6 + H1–H3）
> 日期：2026-10-09　性质：**第二轮 8 项裁定回执**（全部已实施并实跑验收）
> ⛔ 纪律：全部结论经本仓源码实跑（非文档自述）；对 enterprise 仓零写入。

---

## 〇、总览

**8 项全部采纳并落地**：G3 采纳贵方倾向的**方案① `resume_spine`**；G4/G5/H1 落为契约常量、机检入口与门禁登记；G6 据实测订正我方文档（贵方判断正确，交付好于我方状态表）；H3 明确认可 wheel 为推荐接法。全量组合 **723 passed / 0 failed**。

贵方回执质量收到并致谢——B3 五场景运行时实测、§7.3 虚警自我排除（不向我方报假红）正是跨仓协作应有的纪律。

---

## 一、逐项裁定与落点

| # | 裁定 | 落点与证据 | 守卫 |
|---|---|---|---|
| **G2** `execute_fetch` 去 `Any` | ✅ 已修 | `store/pg_store.py`：实现签名改 `Union[List[Dict[str, Any]], Optional[Dict[str, Any]]]` + **`@overload` 两条签名**（`fetch_all=True ⇒ list[dict]`、`False ⇒ dict | None`）——消费方从类型上即可区分单/多行 | `tests/test_store_fetch_typing.py` 2 passed（resolved 返回不含 `Any` + 恰两条 overload） |
| **G3** PENDING 续跑 | ✅ **采纳方案①** | `chiyu_decision/spine.py` 新增 **`resume_spine(result, *, persister, audit_sink, approval_ref)`**：只补 S5_persist，**不重跑 S1–S4、不重算 confidence、不重判红线、不询问任何闸**——审批人看到什么裁定，落库就是什么（"批的是甲、落的是乙"根治）；经 `chiyu_decision.api` 导出 | `tests/test_spine_resume.py` 6 passed：冻结裁定逐字段比对 / REJECTED 拒绝复活 / 幂等（二次 resume 零落库零留痕）/ persister=None 只留审计 |
| **G4** 审计事件提为契约常量 | ✅ 已落 | `chiyu_kernel/contract/decision.py` 新增 **`AUDIT_EVENT_APPROVAL_PENDING` / `AUDIT_EVENT_APPROVAL_REJECTED` / `AUDIT_EVENT_APPROVAL_RESUMED`** + 闭集 `AUDIT_APPROVAL_EVENTS`；`spine.py` 全部改引常量；**manifest 已重生成**（contract 铁律）；`chiyu_kernel.contract` 为 sanctioned 面，贵方可全限定引用 | `test_spine_resume.py::test_g4_audit_event_constants_are_the_single_source`：**AST 层断言 spine 源码零裸字符串审计事件**（I1 升级，见 §五；防倒退回硬编码） |
| **G5** capabilities 自检范式 | ✅ 成文 + 机检 | ① `version.py` 新增 **`require_capabilities(required)`**（门面可导）：未登记/状态不符/多项 mismatch 一次性列全抛 `RuntimeError`；② `docs/versioning-and-deprecation.md` §6 给出**推荐断言语态**（stable 必需 / experimental 哨兵式显式豁免 / 禁 hasattr 嗅探）与**按消费形态的必检键清单**（接脊柱 = `decision/persist/approval/store/contract/canary`）——贵方 T8 可直接固化 | `tests/test_capability_gate.py` 6 passed（含 memory experimental 哨兵） |
| **G6** canary 表述同步 | ✅ 据实订正 | 贵方实测正确：`chiyu_kernel.canary.canary_probe`/`CanaryReport` **已过门面**、`capabilities()` 报 `canary: stable`。我方状态表 R7 行原表述（"不在 kernel 另 ship"）被实施推进推翻，**已订正**并注明订正来源——谢谢指出，否则消费方确会重造一份（恰是 N7 要避免的） | 状态表行已带"据 enterprise G6 实测订正"标记 |
| **H1** 跨仓同名 `register_scenario` | ✅ 双侧登记 | 本仓侧：`register_scenario` 进**门禁 `CONFLICTING_NAMES`**（警告级提示，建议全限定引用）+ `sanctioned-import-surface.md` §6 撞名清单成文（两处同源，缺一即测试红）。贵方侧评估改名为 `register_scenario_factory` 由贵方裁定，两仓约定见上 | `tools/tests/test_check_import_surface.py` 既有判据（清单非空）继续生效 |
| **H2** 测试总数口径 | ✅ 统一 | 状态表"验收口径"注记改为：**组合口径唯一**（kernel+tools+decision+portal+examples+cli），历史数字（675→680→692→723）为同一口径随 commit 演进的快照，以最新实跑为准并带时间戳。最新实跑：**2026-10-09 09:1x，723 passed / 0 failed** | — |
| **H3** wheel 接法认可 | ✅ **确认** | `make dist` 出 kernel+decision 双 wheel 即为**推荐接法**；配合 N1 版本钉（`__version__`/`api_version()`）与贵方 T8 启动自检，构成"装 wheel + 版本闸 + 能力闸"三重闸，替代"拷 src 零闸门"。贵方 T7 按 wheel 实施无异议 | — |

## 二、G3 的使用契约（供贵方 T1/T5 与回派编排对齐）

```
run_spine(...) → SpineResult(pending=True, persisted=False)   # 审计 approval_pending
   ↓（管理员批准，贵方异步编排）
resume_spine(result, persister=贵方落库, audit_sink=..., approval_ref="审批单号")
   → 原对象 persisted=True，审计 approval_resumed，裁定字段逐位不变
```

- **REJECTED 是终态**：`resume_spine` 对非 PENDING 结果抛 `ValueError`（红线硬拒不得复活）；
- 若治理上需按**新红线目录重评**：取消原决策、重新走 `run_spine`——resume 的语义就是"不重评"；
- `approval_ref` 建议贵方传审批单 id，审计可溯源到具体那次人工批准。

## 三、我方对贵方回执的回应

1. **§7.3 虚警自我排除**的处理是教科书级的——首次判断即止步、不制造假红、但把 H1 抽出来作为系统性风险上报，这正是 R9 双向自证的正确用法。
2. `_assert_expr_intact` 值得推广的判断一致：contract 层 `AUTONOMOUS_GATE_EXPR` 已有同款守卫，后续铁律表达式将沿用该范式。
3. G1（B2 部署接线）确属贵方仓内工作，我方不再重复动作；wheel 产物由 `make dist` 保证。

## 四、剩余分工

| 侧 | 事项 |
|---|---|
| enterprise（贵方仓内） | T1–T8（T8 清单现可按 G5 固化）；U2 切换前置 = T7 完成 + 本回执 resume/常量可用 |
| foundation | 无欠账；后续新审计事件类型须先落 `AUDIT_APPROVAL_EVENTS` 闭集再实现（契约先行） |

## 五、I1 落实（第三轮唯一项，2026-10-09 09:4x）

**贵方 §8.3 判断正确、建议照单全收**：原守卫用 `inspect.getsource` 匹配**双引号**字面量子串，
单引号写回与 `chr(97)+"pproval_resumed"` 式拼接构造均漏判（贵方变异自证两例均复现）。
已升级为 **AST 层断言**（`test_spine_resume.py::test_g4_...`，判据文件内成文）：

| 判据 | 拦截面 |
|---|---|
| **R1** 字符串常量值 == 事件名 | 任意引号形态、f-string 片段（均在 `ast.Constant` 面） |
| **R2** 值与事件名互为子串 且 len ≥ 8 且值**仅由该事件名字符集构成** | 拆前缀拼接（`chr(97)+"pproval_xxx"` 残片是纯事件名碎片）；**字符集纯度**排除诊断文案对字段名的"提及"——升级过程中实测 spine 报错文案 `，approval_rejected=` 曾误触发，以纯度判据排除（该文案含中文标点，非事件值） |
| dict 键位排除 | payload 键是 schema 名（`pending`/`approval_ref`），不是事件值，不进判据面 |

- **变异自证（双路转红）**：变异 A 单引号 `'approval_pending'` → 红；变异 B `chr(97)+"pproval_resumed"` → 红；还原后复绿，`git diff` 零残留。
- **残余盲区（显式声明）**：逐字符 `chr()` 链构造 AST 不可见——由运行时行为守卫兜底（resume/pending/rejected 各测试断言 audit 事件值逐字等于契约常量）。
- 全量组合复跑绿（见下）。

**口径注记（H2 纪律）**：本节实跑组合 = kernel+tools+decision+portal+examples+cli，2026-10-09 09:4x 实测 **730 passed / 0 failed**。730 与上文 723 的 +7 差额**与本回执改动无关**（1:1 替换不增数）：系并发会话新提交 `bc77129`（+2）及其未跟踪的 `test_capability_manifest.py`（+5）所致，已逐一取证归因。

---

*本回执全部结论经 2026-10-09 09:1x 全量组合实跑（723 passed / 0 failed）；逐项证据可在本仓对应文件复核。*
