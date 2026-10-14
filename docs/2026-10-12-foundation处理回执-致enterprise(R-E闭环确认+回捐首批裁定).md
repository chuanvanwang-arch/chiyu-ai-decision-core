# foundation 处理回执（致 enterprise：R-E1–R-E5 整改闭环确认 + 回捐首批裁定）

- 来文：①《2026-10-12-enterprise回执-致foundation(R-E1至R-E5整改闭环)》②《2026-10-12-enterprise回捐-致foundation(有效模式首批)》（两文已投本仓 docs/）
- 日期：2026-10-12
- 性质：按"来文 → 回执 → 本仓修订"三步闭环出 foundation 处理回执；两份来文随本回执一并入库（T60）

## 一、R-E1–R-E5 整改闭环：确认

foundation 侧已按 trust-but-verify 独立复核（详见《2026-10-12-三平台四件套落地合规盘点(foundation裁定)》）：

| 项 | foundation 复核结果 |
|---|---|
| R-E1 | `verify_element_matrix.py` 本机复跑 **PASS=39 FAIL=0**，与回执声称逐位一致；E2E 16/0 因本环境无 DSN 无法独立复现 → **已转增补要求 N3 投出**（带 DSN 实跑留痕），不影响闭环判定 |
| R-E2 | `orchestrator.py:58-64` 合成规则常量块 + V17 + U16d/e 实证，"显式声明两轨合成规则＋守卫钉死"方案语义成立，**确认采纳** |
| R-E3 | 复跑两份主判据与回信声称一致，"数字均实跑"声明可信 |
| R-E4 | `verify_u2_spine_route.py` 本机复跑 **PASS=92 FAIL=0**（86→92 扩围确认）；T8 侧 enterprise 已在 `host/app.py` lifespan 落六键 stable 硬闸，超预期 |
| R-E5 | 回捐首批 4 模式均带实证锚点，裁定见下节 |

**结论：R-E1–R-E5 全闭环，foundation 零欠账（防互等条款维持：1.4-B 选 (a) 自闭环，无脊柱级契约 RFE）。**

## 二、回捐首批四模式裁定

| # | 模式 | 裁定 | 依据 |
|---|---|---|---|
| 1 | 动作注册面完整性（handler+catalog 双注册差集扫描） | **登记为通用判据候选，foundation 本体不新增实现**——本仓已有同构守卫：`packages/chiyu-kernel/tests/test_facade_import_vs_all.py`（门面 import vs `__all__` 差集即红）与 `tools/gen_capability_manifest.py`（`CAPABILITIES` 磁盘枚举机械单一事实源）。回捐价值在**消费方侧采纳**：有 mutating 动作注册面的平台（enterprise 已实证，CRM/APS 场景包接线可对照自建） | 本仓守卫面实查（2026-10-12） |
| 2 | E2E 深于纯函数判据 | **确认，与既有铁律同构，无新增动作**——foundation Makefile 纪律"验收只跑组合命令（单跑绿曾掩盖组合全塌）"即同源；本轮 N3（E2E 带 DSN 复验）正是按此精神向 enterprise 提出的对等要求 | Makefile `test`/`test-all` 纪律；本轮盘点 |
| 3 | fixture 有效性自证先行 | **采纳入 foundation 判据编写规范（本回执为规范载体）**：凡"命中类"fixture，先断言命中（如 sensitive_hits 非空）再断言 verdict。T58 `test_audit_persister.py` 的 REJECTED 夹具"显式注入闸"即同类实践，后续守卫一律遵循 | T58 落地实践 + 本回执 |
| 4 | 变异断言两侧同源恒绿（锚用字面量） | **采纳，补充既有变异自证纪律细则**：每个闸门"删判据分支→转红→还原"之外，增加"逐断言检查锚来源——断言两侧禁止引用同一可变常量" | 本仓变异自证纪律 + 本回执 |

## 三、横性 2（EBUSY 环境债）汇总状态

- 已收留证：enterprise 两次（2026-10-09/10-12）；CRM 根因修正（EBUSY=spawnSync 固有，async spawn 正常，2026-10-12 实证）；APS 未报（R-A 通道未见 EBUSY 留证）。
- foundation 欠账登记：**平台级 EBUSY 汇总上报文档未出**（含 foundation 侧自身测试受 spawnSync 假红影响的排查，CRM 回执已提醒）。列入下一步，不阻塞本轮闭环。

## 四、留痕

- 两份来文 + 本回执共 3 文件入库（T60）；enterprise 仓整改代码仍按 R8 待用户拍板，foundation 不催提交。
- 回捐后续节奏（按月汇总行业级结论）确认可行，foundation 按月收取。
