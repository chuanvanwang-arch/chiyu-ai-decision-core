# foundation 复核回执——三仓全景要求落地核验（第二轮 trust-but-verify）

- 日期：2026-10-12（21:0x）
- 来文：三仓对《foundation 全景要求——致 CRM/APS/enterprise（能力盘点差异化落地）》（T63 配套分册）的落地与回信
- 核验方式：源码级 grep/对拍 + 本机实跑（junitxml/vitest 计数）+ 基座契约值直接比对

---

## 一、APS（R-FA1–R-FA4）——R-FA3 落地证实，其余按窗口

| # | 核验动作 | 结果 |
|---|---|---|
| R-FA3 | 禁显 token 全域扫描（.py/.md/.html/.json 文本 + 全仓 .pyc 二进制扫描四变体）+ kmd.py:462 上下文 + 测试实跑 | ✅ **通过**：文本零命中（仅回执文档自身引用为证）、.pyc 0 命中、docstring 已中性化、门户页已重生成；`test_kmd_spine.py`+`test_kmd_portal.py` **63 passed/0 failed**（与声称 58+5 吻合） |
| R-FA1 | 双轨接线现状 | ⏳ 机制就绪待批准：`kmd_spine()` 不传闸待用户批准（10-20 窗口）；M2 双轨 opt-in 已落地（三路径 E2E 绿，11 断言）；E5 未出 |
| R-FA2 | 禁一步换 spine 纪律 | ⏳ 承诺分步+E5 等值+漂移回退，当前未启动迁移——登记在案 |
| R-FA4 | R7 transport 排期 | ⏳ 10-23 stdio / 11-06 HTTP，未到窗口 |

APS 回执质量加分：边界甄别如实（「七边」不在禁显清单未动、base64 误报剥离后零命中、内部便签区按 foundation 自身实践保留并披露）。

## 二、enterprise（R-FE1–R-FE4）——全闭环，本机复跑确认

| # | 核验动作 | 结果 |
|---|---|---|
| R-FE1 | bridge.py 口径块 + 两份文档 3 处标注 | ✅ 通过：`evolution/bridge.py:15-24` experimental 口径三条内嵌；设计文档 §5.1/§5.2 +  renovation 计划演进桥行均已补标 |
| R-FE2 | 月度回捐 | ✅ 维持，素材池已列（M1 抓缺陷实录/假绿拦截/双形态配置提取） |
| R-FE3 | 三纪律抽查 | ✅ 锚点在案（U15b-d/U16d 命中自证、V2 字面量锚+变异双证、改名法） |
| R-FE4 | 字面量逐字比对 + U2 三站点 | ✅ 通过：`ELEMENT_PRIORITY`(strictness.py:45-52) 与 `_user_order`(verify:115) 八项逐字一致；U2 三站点在线（bridge.py:81 / runtime_board.py:323 / scenario/lifecycle_scheduler.py:194——**回执所记 decision/ 路径实为 scenario/，行号 194 内容属实**，轻微路径笔误无影响） |
| 主判据 | 本机复跑 | ✅ `verify_element_matrix.py` **PASS=39 FAIL=0**；`verify_u2_spine_route.py` **PASS=92 FAIL=0**（与声称一致） |

enterprise 结论：R-FE1–R-FE4 全部闭环，维持+月度回捐定位有效。

## 三、CRM（R-FC1–R-FC4）——R-FC2 落地、R-FC3 半幅（未提交、无回执）

| # | 现状（工作区未提交） | 核验结果 |
|---|---|---|
| R-FC2 | 5 个 decision 文件注释清理（`7×7`→中性表述：autonomyEngine.js/closure.js/decisionRepo.js×3 处/traceRootCause.js） | ✅ **已落地**：三源 grep 零命中，纯注释级改动 |
| R-FC3 | `edgeDimensionSpec.js` DIMENSIONS 对齐基座 SEVEN_DIM_KEYS | ⚠️ **半幅**：键表已与契约**逐项同序一致**（identity/structure/semantics/time_config/decision_history/operational_state/governance 七项，过程中出现 `structure→semantics` 重复 key 已由其自行修正并补 governance）；相关守卫测试实跑 **8/8 绿**；**但守卫未引用基座契约**（grep `SEVEN_DIM`/`chiyu_kernel.contract` 在测试面零命中）⇒ 对应关系是手工对齐、无机检钉死，foundation 改 SEVEN_DIM_KEYS 时 CRM 将静默漂移 |
| R-FC1 | P2 扩面 26 场景 | ⏳ 排期项；N1 映射层已交付未接线（设计如此，P2 触发） |
| R-FC4 | sidecar 版本握手 | ❌ 未动 |

**CRM 需补**（建议随回执一并）：
1. R-FC3 补契约钉死：Node 侧无法直连 python 门面，可用**快照钉**（把 SEVEN_DIM_KEYS 当前值+来源注释+取得日期写进守卫断言，两侧不同源防恒绿）或经既有桥（quote_approval_shadow.py 同款）取契约值对拍；
2. 出正式回执（R-FC2/R-FC3 落地证据 + R-FC1/R-FC4 排期）；
3. 当前改动入库前跑一次相关全量（edgeBindings/db-relation 等已绿，注意 config_store 覆盖路径）。

## 四、裁定与后续

1. **enterprise 维持+月度回捐**（无新增动作）；
2. **APS 盯三节点**（10-20 接线待用户批准+E5 / 10-27 破零 / 11-06 综合回执）；
3. **CRM 进收口**：R-FC3 补钉死 + 回执 + R-FC1/R-FC4 排期书面化；
4. foundation 侧无欠账新增；EBUSY 平台汇总（F1）仍挂账。
