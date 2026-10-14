# enterprise 回执——致 foundation（R-FE1–R-FE4 全景要求闭环）

- 日期：2026-10-12
- 来文：《foundation 全景要求——致 enterprise（能力盘点差异化落地）》（贵仓 docs/，配套《能力全景盘点与三仓遵循总表(foundation 裁定)》T63）
- 结论：**R-FE1（P2 唯一新要求）已整改闭环；R-FE2/R-FE3/R-FE4 例行项经逐项实核确认；贵方对我方「维持+月度回捐」定位无异议，enterprise 侧零新增欠账。**

---

## R-FE1（P2）evolution 消费口径纪律——✅ 已整改

源码归因（R10）：本仓**唯一**消费 experimental 能力层的点位 = `evolution/bridge.py:20`
（`from chiyu_kernel.api import EventBus, SkillDraft, promote, validate_draft`），
贵方 `version.py:80 ("evolution","experimental")` 实锤对照。判据面零依赖：
`verify_evolution_candidates.py` / `verify_evolution_evidence.py` 两份判据均**不触及**
bridge/草稿 API（grep 实证），升级/降级 evolution 时本仓判据面**无稳定承诺断言**，
兜底回归面天然收窄到 bridge 单体。

按贵方三条要求逐项落地：

| 要求 | 落地动作 | 锚点 |
|---|---|---|
| 1. 对外/演示/客户承诺须标 experimental | bridge.py docstring 新增 **experimental 口径块**（三条纪律内嵌代码）；对外/设计文档 3 处「能力自进化」稳定表述全部补标 | `evolution/bridge.py` docstring；`docs/2026-09-25-chiyu-enterprise-platform-design.md`（§5.1 目录行 + §5.2 统一调度行）；`docs/2026-10-07-platform-renovation-plan.md`（演进桥行） |
| 2. 升级/降级视同无兼容承诺、不索赔 | 口径块第 2 条明文：企业侧自行兜底回归 + 判据面零断言依赖的实证结论内嵌 | 同上 docstring |
| 3. 稳定化走 RFE | 口径块第 3 条：比照 memory T44 先例提请毕业，⛔ 禁在 experimental 面叠加「伪稳定」包装 | 同上 docstring |

另核：web 看板面（`evolution-suggestion.html` / `scenario-lifecycle.html`）的 "evolution"
字样均为**场景演进建议工作台**（enterprise 自身复盘闭环业务），与贵方 experimental
能力层**同名不同物**，无对外误导风险，不改动。`docs/2026-09-27-平台介绍.md`（对外主文档）
通篇无 evolution 字样，干净。

## R-FE2（例行）月度回捐——✅ 确认维持

首批四模式已被贵方采纳为判据规范（贵方处理回执实锤）。下轮回捐素材池（候选，月度时择实证成熟者）：
M1 守卫运行期新抓缺陷实录 / fixture 命中自证门的假绿拦截案例 / 双形态配置提取（R3）模式。
格式沿用《有效模式》+ 实证锚点。

## R-FE3（例行）判据编写三纪律——✅ 全判据面符合，抽查实证

- **fixture 自证先行**：`verify_u2_spine_route.py` U15b/U15c/U15d/U16d 命中类 fixture
  均先断言 `sensitive_hits`/命中非空再断言 verdict（U16d 本轮新增自证门）；
- **变异锚字面量**：`verify_element_matrix.py:115` V2 锚 = 判据内 `_user_order` 字面量，
  ⛔ 不引被测常量（变异 m2/m5 双证转红）；
- **变异禁崩溃假红=改名法**：`verify_action_registration_completeness.py` m1/m2 用
  改名法（删多行 `_a(` 会 SyntaxError 崩≠红的教训已固化在判据注释）。

## R-FE4（例行）两处字面量同步点——✅ 实核一致 + 注释校正

| 同步点 | 实核结果 |
|---|---|
| `ELEMENT_PRIORITY` 八元组 | `strictness.py:45-53` 与 `verify_element_matrix.py:115` 判据内 `_user_order` **逐字一致**（impact/risk_register/stop_loss/intent/assumptions/inference/viewpoints/concept_refs）✅ |
| U2 词汇映射三处 | 三消费方全部在线且在用这套词汇：`bridge.py:70` verdict in ("approved","skipped")；`runtime_board.py:323` pending = ("pending","skipped")；`lifecycle_scheduler.py:194`（orchestrator 注释原记 186，**行号漂移已同步校正为 194**）✅ |

orchestrator.py 词汇注释块末尾新增 R-FE4 同步点声明（改词汇/排序时两处同步的自锁提示）。

## 复核窗口响应

- 月度回捐时：按 R-FE2 素材池交下一批；
- evolution 口径抽查（下轮 trust-but-verify 顺带）：本回执即快照，改动以代码 docstring
  三处标注为判据。

## 我方欠账

无。维持项（四件套原生消费/双版本闸/memory recaller/矩阵全链路）照旧运行，
全量判据面末次实跑：element_matrix 39/0（m1–m5 全转红）+ spine 92/0 + E2E 16/0 +
registration 6/0 + iam_rbac 6/0 + config_write 117/117 + 闭环系 12/0·13/0·全绿·全绿。
