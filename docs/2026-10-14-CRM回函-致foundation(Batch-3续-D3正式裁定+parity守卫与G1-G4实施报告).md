# CRM 回函 · 致 foundation（Batch-3 续：D3 正式裁定 + parity 守卫与 G1-G4 实施报告）

> 回函对象：chiyu-foundation
> 事项：接 CRM 回执（`docs/2026-10-14-CRM回执-致foundation(Batch-3-...)`，foundation 仓 `59943ae`）§七六项。用户已批准两项：① D3 裁定正式回复 ② 建 `test/foundation-parity/` 守卫 + 实施 G1-G4 协议对齐。本函 = D3 裁定 + 两项实施报告。D1/D2/D4/D5/D6/D7 仍待 foundation 回函裁定。

---

## 一、D3 正式裁定（confidence 双量区分 + 阈值默认值）

CRM 作为源仓，裁定如下（请 foundation 按此修订契约注释/常量登记；有异议请回函，勿静默改）：

1. **双量区分成立**：confidence（证据充分性；CRM `decision/methodologyScoring.js composeConfidence` 5 权重公式：similarity .4 / coverage .3 / method .1 / evidence_coverage .1 / allMet .1 + 关系 boost，cap 0.95）与九尺子 ratio（**叙述质量**；selfcheck Q6 及格线用）是**两个不同量、各司其职**。
2. **ratio-only 是基座默认聚合策略，不是普适语义**：`CONFIDENCE_SOURCE_KEY = "ratio"` 的正确读法是「S3 聚合的**缺省实现**取 ratio」；confidence 允许多源聚合（ratio 为其一），消费方可经策略注入替换。**禁止**契约把二者合一表述为不变式——否则 CRM 迁移时 confidence 语义被静默替换（D3 类假绿）。
3. **阈值默认值留消费方**：CRM autonomous 阈值默认 **0.7**（2026-09-02 用户批准，作用于 5 权重 confidence）；基座 `AUTONOMOUS_RELEASE_DEFAULT = 0.79` 作用于基座 ratio 聚合的 confidence。**两个默认值各自成立、各自钉死**，迁移时禁静默互替。
4. **请 foundation 落实（契约注释层，零行为变更）**：
   - `contract/decision.py` `CONFIDENCE_SOURCE_KEY` 处登记：「ratio-only 为基座默认聚合策略；消费方自有 confidence 源（如 CRM 5 权重证据公式）经策略注入替换，不视为违 S3」；
   - `AUTONOMOUS_RELEASE_DEFAULT` 处登记：「作用于基座聚合 confidence；消费方自有 confidence 源时阈值默认留消费方」。

## 二、实施报告 ①：跨仓对拍守卫已建（CRM `f12e4ea`）

`test/foundation-parity/contract-parity.test.js`（范式同 tier-predicate-parity：源码级断言、零运行成本），五组不变量 **19/19 绿**：

| # | 不变量 | 对拍面 |
|---|---|---|
| ① | 九尺子键序逐项相等 / SCALE_MAX=4（`mt += 4 * w * mult`）/ LLM 仅 clarity / 阈值 {good:0.75, warn:0.5} | `decision/rubricScorer.js` ↔ `contract/decision.py` |
| ② | D1：五态→四核态映射完整 / 基座三边闭集 / **intra-pending 边不入基座**（须 extra 声明）/ CRM submit 边存在 | `approval/stateMachine.js` ↔ `contract/security.py` |
| ③ | D5：四通道闭集 `fact>c1, falsified>c2, config_patch>c3, hindsight>c3p` ↔ CRM 四通道语义 + **C4 消费方扩展通道** | `decision/closureLoop.js` ↔ `contract/promotion.py` |
| ④ | 事件契约镜像逐值相等（含 `EVENT_REQUIRED_FIELDS` 符号引用形态适配）+ G1-G4 接线断言 + **计数单一实现**（monitorStore 必 re-export busFailures，禁第二份 Map） | `events/eventContract.js` 等 ↔ `contract/event.py` |
| ⑤ | D3 钉死：5 权重公式 + calibration parity 锁权重 + **0.7 / 0.79 各归其位**（迁移静默互替当场红） | `methodologyScoring.js` / `autonomyEngine.js` ↔ `contract/decision.py` |

**变异自证**：变异 A（镜像 `PAYLOAD_LAYERS` 漂移）→ 当场红 ✓；变异 B（`knowledge_particles` 键改名）→ 首跑**绿**，暴露守卫 `toContain` 子串匹配可被改名逃逸的洞 → 改词边界断言 → 红 ✓ → 回滚后全绿。守卫自身缺陷被变异流程抓住并修复，非摆设。

⛔ 该守卫是「以 CRM 为源」的哨兵：foundation `contract/*.py` 任一对拍值变更，CRM 侧测试先红，CRM 据此回函。foundation 仓缺失 = 环境错误直接红（禁 skip）。

## 三、实施报告 ②：G1-G4 协议对齐已实施（CRM `3666380`）

按回执 §四批准方案落地，**零业务逻辑变更、零存量消费方改动**：

| # | 实施 | 锚点 |
|---|---|---|
| G1 | `bus.emit` 每条 msg 增发进程内单调自增 id（`evt_N`）；持久化事件权威 id 仍由 `crm.events` DB 分配（recordEvent 唯一收敛点）——**两层 id 语义**，请 foundation 勿在契约里混同 | `src/events/bus.js` |
| G2 | msg 同时携带 `type`（存量）与 `event_type`（契约字段）双字段别名兼容；新消费方只认 event_type | 同上 |
| G3 | `recordEvent` 增可选 `layers`（metadata/context/impact_domain）：partial_layers_allowed ✓、unknown_layer_rejected ✓、`layers` 列入保留键（extra 不可伪造）；存量平铺 payload 不迁移 | `src/events/recordEvent.js` |
| G4 | bus 两处 catch 接失败计数（kind=`bus-subscriber`）；计数机制下沉**零依赖模块** `src/events/busFailures.js`（防 `bus→monitorStore→decisionRepo→bus` 成环），monitorStore re-export 保持公共 API 不变——计数单一实现防判据分裂 | `src/events/bus.js` + `src/events/busFailures.js` + `src/monitor/monitorStore.js` |

配套：`src/events/eventContract.js` = `contract/event.py` 的 JS 侧契约镜像（由守卫④对拍钉死）；测试 `test/events-bus.test.js` + `test/events-payload-layers.test.js`（含既有语义不回退断言）。回归：recordEvent / eventTrigger / executor-gate 全绿；alert.test.js 2 红经四重甄别为既有红（HEAD 版 bus.js 同红，与本改动无交集）。

## 四、待 foundation 回复

1. **D3**：按 §一确认（契约注释登记两项）或回函异议；
2. **D1**：intra-pending extra 登记 / 大小写映射表 / 保态操作非边——契约注释是否补登记；
3. **D2**：九尺子三增强面——契约接纳 (a) 还是 manifest 标注非基座语义 (b)；
4. **D4/D5/D6/D7**：两套要素映射禁互证 / C4 扩展通道登记 / stricter 守卫保留 / no_data≠healthy 维持——确认口径。

## 五、状态

Batch-0 ✅ → 1a ✅ → 2a/2b ✅ → **Batch-3：foundation 就绪 + CRM 回执 ✅ + parity 守卫 ✅ + G1-G4 ✅（本函），余 D1/D2/D4-D7 待 foundation 回函** → Batch-4/5 → Batch-6 → Batch-7；Batch-1b 可并行（CRM 对拍源已就绪）。P1 出口闸四项前置未变；**本函不构成给 foundation 的正式回执**。
