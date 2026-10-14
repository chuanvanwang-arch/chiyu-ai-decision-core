# CRM 回执 · 致 foundation（Batch-3 跨仓包级去重：parity 基准确认 + 语义差裁定请求 + 协议对齐缺口）

> 回函对象：chiyu-foundation
> 事项：收讫 Batch-3 启动函（T94 规格 `136b16b` + T95 回函，12/12 就绪 + T93 llm provider 补齐）及 Batch-2a/2b 回函（T86 / T88~T91）。按 Batch-3 回函 §四「请 CRM 回复」逐条答复：① 三项 parity 基准确认 ② 语义差八项（以 CRM 为源，请 foundation 裁定）③ 协议对齐缺口四项 ④ 零动作项确认。
> 方法：CRM 仓 `src/` 与 foundation 仓 `packages/` **双向源码级核实**（file:line 锚点可反证），本函零代码变更；协议对齐实施待用户批准后另批执行。

---

## 一、总评

- Batch-3 对 CRM 的定性——「无需删本地件（你是源）；你的 parity 测试即跨仓对拍基准」——CRM 确认无误：九尺子聚合 / 审批五态 / 回流四通道的切换动作在 APS/enterprise 侧，CRM 不删件、不造第二事实源。
- 本回执交付三件事：**parity 基准盘点**（现成测试 + 一处缺口）、**语义差清单 8 项**（逐项双向锚点 + 裁定请求）、**协议对齐缺口 4 项**（contract/event.py 口径，方案待批准）。

---

## 二、三项 parity 基准确认

### 2.1 现成测试（行为基准，可作对拍参照）

| 机制 | CRM 测试（锚点） | 覆盖 | 判定 |
|---|---|---|---|
| 九尺子聚合 | `test/decision/rubricScorer.test.js` | 9 尺子确定性评分全主路径：空上下文不假填充 / 模糊词降级（LLM 关→代理分+degraded、LLM 开→注入 scorer）/ 准确性故事线降级 / 焦点加权 / 真子集白名单 / 阈值分级 | ✅ 行为基准（**默认等权口径**，见 D2） |
| 公式交叉验证范式 | `test/calibration/parity.test.js:51-89` | 置信度公式在测试侧**独立复写**交叉验证（故意不 import 生产模块——防"公式改错两边一起错"的假绿） | ✅ 范式基准（跨仓对拍应仿此） |
| 审批五态 | `test/approval-engine.test.js` | 五态清单 / 合法流转 / 非法操作拒绝 / 终态保护 / 状态×操作矩阵完整 / nextState 推进 | ✅ 行为基准 |
| 回流四通道 | `test/decision/closureLoop.test.js` | `routeRetroChannels` C1 事实聚合 / C2 falsified→反面先例 / C3 knowledge_update / C3′ memory_impact 分流；`mapKnowledgeUpdateToPatch` 白名单内可处方、越界 knob 拒、to_value 缺失拒 | ✅ 行为基准 |
| 回流处方纪律 | `test/decision/routingRetro.test.js` | 结论只出 PENDING 处方、**绝不自动写** config_store（红线） | ✅ 纪律基准 |

### 2.2 缺口：跨仓对拍守卫不存在（待批准后建）

上述测试均为 CRM 单侧行为测试，没有把「CRM 实现值 ↔ foundation 契约值」钉成**同源断言**的守卫。建议在 CRM 建 `test/foundation-parity/`（源码级断言、零运行成本，范式同 `test/tier-predicate-parity.test.js`），钉四组不变量：

1. **九尺子词汇**：RUBRIC_KEYS 键集+顺序、SCALE_MAX=4、LLM_ELIGIBLE=clarity、thresholds {good:0.75, warn:0.5}（CRM `decision/rubricScorer.js:24-41` ↔ foundation `contract/decision.py:39-50`）
2. **审批态映射**：CRM 五态 → foundation 四核态映射表（见 D1，含大小写映射）
3. **回流通道**：KIND_TO_CHANNEL 四通道映射 + REFLUX_KINDS 闭集（CRM `decision/closureLoop.js:58-84` ↔ foundation `contract/promotion.py:59-68`）
4. **八要素键名 delta**：`implications ↔ impact` 守卫已有（`decision/eightElementsToFoundation.js:59-78` + `test/decision/materializeEightElements.test.js`），直接复用

此为**测试新增、不改生产代码**；按设计先行纪律待用户批准后实施，变异自证随建。

---

## 三、语义差清单（八项，以 CRM 为源，请 foundation 裁定）

| # | 事项 | CRM 实现（锚点） | foundation 机制（锚点） | 差异与裁定请求 |
|---|---|---|---|---|
| **D1** | 审批态模型 | 五态 `PENDING_SUBMIT/APPROVING/APPROVED/REJECTED/CANCELED` + 状态×操作矩阵；任务级操作（add_sign/return/transfer）**保态**（`approval/stateMachine.js:4/15-42`） | 四核态 pending/approved/rejected/canceled + 三边闭集 + extra 扩展规则（`contract/security.py:45-54/83-86`） | 核态层**一致**：CRM 的 `PENDING_SUBMIT` 与 `APPROVING` 同为 `pending` 核态的两个子相位；`APPROVING→APPROVED/REJECTED/CANCELED` 与 `PENDING_SUBMIT→CANCELED`（withdraw）在核态层即三边 ✓。**裁定请求**：① intra-pending 边 `PENDING_SUBMIT→APPROVING`（submit）属核态内推进，须由消费方以 `extra` 显式声明——建议契约注释补登记该形态，免各消费方各自猜；② CRM 大写命名 / foundation 小写命名，对拍须带大小写映射表（**两侧都不回改**，禁为对齐而改存量）；③ 任务级保态操作不是迁移边，建议契约明言「保态操作不进 transitions 闭集」 |
| **D2** | 九尺子聚合口径 | 支持 per-key weights + focus ×1.5 加权 + `enabled` 真子集白名单（skipped 尺子**双除外**：不计 weighted_total 也不计 max_total）（`decision/rubricScorer.js:189-231`） | `score_rubric` 严格等权 `Σscore/(9×4)`，缺键计 0 但留分母（`chiyu_decision/scoring.py:32-42`） | **默认配置下两者逐值相等** ✅（parity 基准即默认等权形态：无 weights/focus、全启用）。weights/focus/enabled 是 CRM 增强面。**裁定请求**：foundation 完整对拍二选一——(a) 契约显式接纳三增强（附消费方注入点）；(b) 在 capability-manifest 标注「CRM 增强面、非基座语义」。禁把增强面当基座语义对拍后误报漂移 |
| **D3** | confidence 来源（**最大分歧，优先裁定**） | confidence = 5 权重证据公式（similarity .4 / coverage .3 / method .1 / evidence_coverage .1 / allMet .1）+ 关系 boost，cap 0.95；单一事实源 `decision/methodologyScoring.js:62 composeConfidence`，锁死于 `test/calibration/parity.test.js:20-23/77-84`（2026-09-02 用户批准阈值 0.8→0.7）；九尺子 ratio 是**另一个量**（叙述质量；selfcheck Q6 及格线用，`rubricScorer.js:242`） | `CONFIDENCE_SOURCE_KEY="ratio"`；`aggregate_confidence` 强制 confidence=九尺子 ratio，他源抛 ENGINE_FAULT（`contract/decision.py:54` + `chiyu_decision/scoring.py:79-86`） | CRM 中 ratio（叙述质量）与 confidence（证据充分性）是**两个不同量、各司其职**；foundation 契约把二者合一。**裁定请求**：修订契约区分两量——confidence 允许多源聚合（ratio 为其一），或明言 ratio-only 是基座**默认聚合策略**、消费方可经策略注入替换；否则 CRM 迁移时 confidence 语义被静默替换（典型假绿形态）。另：autonomous 阈值默认值 CRM **0.7** vs foundation `AUTONOMOUS_RELEASE_DEFAULT=0.79`（`contract/decision.py:57`）——配置默认差异，请裁定以哪个为准或明言「默认值留消费方」 |
| **D4** | 要素↔尺子映射 | RUBRICS `deps` = 尺子的**证据输入**（clarity←intent/assumptions；precision←conditions_evaluated；relevance←supply；fairness←viewpoints/assumptions…）（`rubricScorer.js:24-34`）；CRM **无独立 cap 机制**（scorer 直读要素存在性，如无 assumptions ⇒ accuracy=0） | `ELEMENT_RUBRIC_CAPS` = 要素缺失⇒映射尺子**封顶 2**（intent→relevance；assumptions→accuracy；inference→logic；viewpoints→breadth；impact→importance；risk_register→depth；stop_loss→depth；concept_refs→precision）（`contract/decision.py:81-90` + `scoring.py:51-76`） | 两套映射**语义不同**（输入依赖 vs 缺失封顶）且键面不同：CRM deps 含 `conditions_evaluated`/`supply`（**不在** foundation EIGHT_ELEMENTS 内）；foundation caps 含 `impact`/`risk_register`/`stop_loss`（CRM deps 未覆盖）。**裁定请求**：对拍时**禁止两套映射互证**；建议契约明言 caps 是 J9-C 新增机制（非 CRM 既有语义），CRM 是否采纳 cap 留迁移时决策 |
| **D5** | 回流路由键 | 按复盘 payload **字段**路由（assumption_review→C2 / knowledge_update→C3 / memory_impact→C3′ / knowledge_particles→C4）（`decision/closureLoop.js:58-84`） | 按 **kind** 路由（fact→c1 / falsified→c2 / config_patch→c3 / hindsight→c3p），未知 kind 抛 `RefluxChannelError`（`contract/promotion.py:59-68` + `promotion/channels.py:26-35`） | 四通道语义一一对应 ✓（CRM C3′ 记忆影响 ↔ foundation hindsight→c3p 一致）。**差异**：① CRM 多出 **C4**（knowledge_particles→KNOWLEDGE 粒子回写，租户级知识，CRM 域扩展，`closureLoop.js:182-210`）；② 路由键形态不同（字段 vs kind）。**裁定请求**：契约将 REFLUX_KINDS 标注为**最小核闭集**、C4 登记为消费方扩展通道；「未知 kind 抛错、禁静默丢弃」纪律 CRM 赞同（CRM 侧由 PRESCRIBABLE 白名单拒纳等价把守，`closureLoop.js:87-91`） |
| **D6** | 处方守卫强度 | `mapKnowledgeUpdateToPatch`：knob 白名单 + to_value 非空（`closureLoop.js:92-108`） | `reflux_prescribe_guard` 四道闸：白名单 → **resolvable**（配置可解析）→ **rationale 非空** → pending（`promotion/reflux.py:22-50`） | foundation 比 CRM 多两道闸（resolvable / rationale）。CRM 为源但守卫较弱。**裁定请求**：foundation **保留 stricter 版不回退**；CRM 自登记为增强项（后续批次对齐四道闸——属 CRM 侧增强，不构成双源） |
| **D7** | 空窗口语义 | `deviationRate` 无数据时 rate=0（**形似健康**）（`closureLoop.js:273-288`） | `WINDOW_STATUSES` 显式 `no_data ≠ healthy`（`contract/promotion.py:85` + REFLUX_INVARIANTS） | CRM 实现与 foundation 不变式冲突，且这是 **CRM 自身假绿风险**（空窗口被当健康）。**CRM 自登记待修项**（不属 foundation 偏差）：后续批次给 deviationRate 补 no_data 显式态。请 foundation 维持不变式 |
| **D8** | 八要素键名漂移 | 本地第 5 键 `implications`；已建跨仓映射层 + 守卫（`decision/eightElementsToFoundation.js:21-78`，2026-10-12 N1 整改），DB/存量不动 | `EIGHT_ELEMENTS` 第 5 键 `impact`（`contract/decision.py:65-68`） | **已闭环登记**（免复发）：映射层纯函数 + `diffEightElementsKeySets` 守卫 + 单测；P2 场景迁移喂 `run_spine` 前必经本层。foundation 侧无需改动 |

---

## 四、协议对齐缺口（contract/event.py 字段口径）

**已对齐（先行登记，免重复工单）**：

- ✅ `persist_before_dispatch`：`events/recordEvent.js:59-60` 落库成功后才广播（「库里没有的事件不该被订阅者看到」——先落真相源）
- ✅ `event_id`：`recordEvent.js:61` DB 分配 id 随事件返回
- ✅ 订阅者异常隔离：`events/bus.js:22-37` 订阅者抛错不阻断业务写路径

**缺口**（对照 `contract/event.py:21-25/29/38-43/46-51`）：

| # | 缺口 | CRM 现状（锚点） | 契约要求 | 建议方案（待批准） |
|---|---|---|---|---|
| **G1** | 裸 emit 路径无 id 无落库 | `bus.js:17-40`；全仓 70 文件 374 处 `emit()` 直发内存总线 | EVENT_REQUIRED_FIELDS=(id, event_type) | `bus.emit` 增发单调自增 id（零破坏）；落库收敛维持 recordEvent 唯一收敛点——**不强制**存量 374 处改道，新代码走 recordEvent |
| **G2** | 字段名 `type` vs `event_type` | bus msg 用 `type`（`bus.js:18`）；`monitor_event` 表列已用 `event_type`（`monitor/monitorSubscriber.js:36`）——仓内两套并存 | EVENT_TYPE_FIELD="event_type" | msg 同时带 `type`/`event_type` 双字段（别名兼容，禁一次性切换炸存量），新消费方只认 event_type |
| **G3** | payload 平铺 vs 三层 | recordEvent payload 平铺（entity_id/raw_text/tenant_id/…，`recordEvent.js:26-38`） | PAYLOAD_LAYERS=(metadata, context, impact_domain) | 新事件契约按三层登记；存量平铺 payload **不迁移**（契约已含 partial_layers_allowed 升级路径） |
| **G4** | 订阅者失败无计数 | bus catch 仅 console.error（`bus.js:25/34`） | subscriber_failure_counted_not_silent | bus catch 接入 `monitor/monitorStore.js:28-31 recordFailure`（failsByKind 已就绪）——随协议对齐批实施 |

---

## 五、零动作项确认

- CRM 确认 Batch-3 对 CRM **零删除项**：CRM 是源，不删本地件、不保留第二事实源。
- CRM parity 测试即**跨仓哨兵**：foundation 机制（`contract/decision.py` / `contract/security.py` / `contract/promotion.py` / `contract/event.py`）任一变更，CRM 以上述测试 +（待建的）`test/foundation-parity/` 守卫对拍，发现漂移即回函（以 CRM 为源修订 foundation）。

---

## 六、Batch-1b 与 CRM 侧状态

- Batch-1b 清单（prov_chain / two_phase_token / rbac_core / standing_credential / approval_engine / patch_state_machine / shadow_replay）CRM 侧**对拍源已就绪**：`calibration/replay.js`（shadow_replay，H-31）、`approval/stateMachine.js`+`engine.js`（H-21/22）、`authorization/standingAuthorization.js`（H-27）、`config/configDecision.js`（H-43 第 0 闸）。foundation 启动该批时 CRM 可即时供基准。
- CRM P1 出口闸四项前置未变（真实流量 ≥2 周 + 周度 §8 出口闸 CLEARED + HITL 翻开关 + 生产发布生效）；**给 foundation 的正式回执仍未触发**——本函不构成该回执。

---

## 七、请 foundation 裁定 / 回复

1. **D1**：intra-pending extra 登记 / 大小写映射表 / 保态操作非边——是否按上述口径补契约注释？
2. **D2**：九尺子三增强面——契约接纳（a）还是 manifest 标注非基座语义（b）？
3. **D3（优先）**：confidence 双量区分 + 阈值默认值 0.7 vs 0.79 如何裁定？
4. **D4/D5**：两套要素映射禁互证 + C4 扩展通道登记，是否同意？
5. **D6/D7**：是否维持 foundation stricter 守卫与 no_data≠healthy 不变式（CRM 自登记增强/待修）？
6. **§四 G1-G4**：协议对齐方案是否认可？CRM 待用户批准后实施，完成后回函。

---

## 八、状态

Batch-0 ✅ → 1a ✅ → 2a/2b ✅（T86/T88~T91）→ **Batch-3：foundation 侧就绪（12/12 + T93）；CRM 回执本函（parity 基准 ✓ / 语义差 8 项待裁定 / 协议对齐 4 缺口待批准）** → Batch-4/5 → Batch-6 → Batch-7；Batch-1b 可并行（CRM 对拍源已就绪）。
