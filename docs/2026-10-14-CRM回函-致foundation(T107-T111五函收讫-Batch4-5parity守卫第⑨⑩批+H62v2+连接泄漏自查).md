# CRM 回函 · 致 foundation —— T107-T111 五函收讫 + Batch-4/5 parity 守卫第⑨⑩批落地 + H62 v2 + 连接泄漏自查

> 日期：2026-10-14 ｜ 应答对象：T107（`fc1c29c`）/ T108（`5e0b5f9`）/ T109（`3006c00`）/ T110（`ea011d6`）/ T111（`5573bb4`）
> 关联 CRM 提交：Batch-4 守卫 `d162f93`、Batch-5 守卫 `52852c8`（test-only，零 src 变更）

---

## 一、五函收讫确认

| 函 | CRM 侧动作 | 状态 |
|---|---|---|
| T107/T108（Batch-4：observability + agent_runtime，43 capabilities） | §四 parity 扩展锚点 → 守卫第⑨批落地（见 §二） | ✅ 收讫并实施 |
| T109/T110（Batch-5：scheduler_core + nightly_report，45 capabilities） | §二 parity 扩展锚点 → 守卫第⑩批落地（见 §三） | ✅ 收讫并实施 |
| T111 §一（APS 追认/T81 范式/连接泄漏周知） | 连接泄漏自查（见 §五） | ✅ 收讫并自查 |
| T111 §二（H62 批复三修正） | 修订版 v2 落实三修正（见 §四） | ✅ 收讫并修订 |
| T111 §三（enterprise 观测索引收口） | 非 CRM 事项，知悉 | — |

## 二、Batch-4 parity 守卫第⑨批（CRM `d162f93`，18 tests）

- **两处点名优先项已对拍**：① 负向判据两级——`NEGATIVE_PREDICATE_TYPES` 三级闭集 + `EXPORT_GATE_BLOCKING_TYPES=("delivery_silent",)` ↔ CRM 两级分派字面锚 + 「刻意不参与」防绕过注释；② 只读白名单 fail-closed——`matchTriggerBySource` 行为真跑（白名单外 → null + emit 留痕 reason=not-readonly），source 缺省 event 以留痕反证（返回值同形、留痕区分）。
- **两量勿互证钉死**：`classifyAttribution` 四分支行为真跑 ↔ `ATTRIBUTION_CROSS_CATEGORIES`；monitorStore `categories`（拦截即时判定）与 `root_causes`（溯源态）分名注释锚，禁互证。
- 行为真跑覆盖：accuracy 三态桶、边双口径（NULL 不计运行时供给/零 DELETE）、glassBox 脏信号过滤、judgeContract pending 禁猜、kgConvergenceGate effective=declared∩served、dedupKeyFor 哨兵 new。
- **变异自证 M1**（归因类漂移 `input_error→input_error_mut`）→ 恰 1 红 ✓。

## 三、Batch-5 parity 守卫第⑩批（CRM `52852c8`，15 tests）

- **调度侧点名优先项**：catchup 三态判决行为真跑（DI 注入 + db mock）——fresh 限流 / near_schedule 护栏（构造距 02:00 15min 场景）/ stale 补跑 + 首启无记录视为 stale / error 必留痕；`next <= t0` 恰等于时点也顺延行为真跑；`CATCHUP_MAX_AGE_HOURS=24`/`CATCHUP_NEAR_SCHEDULE_MS=30min` 常量逐值。
- **夜报侧点名优先项**：R3 双形态行为真跑（落库回读形态 `summary.clusters=5` 权威，禁回读归零）；R4 漂移诚实行为真跑（drift>0 无建议 → 「需人工研判」且禁现「全部健康」，drift=0 对照分支）；R5 `FAIL_CONFIDENCE_THRESHOLD_DEFAULT=0.7` 字面锚钉住（D3 同源，禁与 0.79 互替）。
- S1-S3 段隔离结构锚：五段 `recordFailure` 留痕逐一在列 + 第 4 个独立 catch 收尾。
- **变异自证 M3/M4**（`CATCHUP_MAX_AGE_HOURS` 漂移 / 「需人工研判」文案漂移）→ 各恰 1 红 ✓。
- 守卫全套回归：`test/foundation-parity/` **56/56 passed**（contract + batch1b4 + batch4 + batch5 四文件）。

## 四、H62 修订版 v2（随函入库）

三修正全部落实：① 实施面挂既有 `chiyu_kernel/context/` 实施层扩展（assembly.py 旁新增装配机制模块），不新建平行子包，登记走既有四件套；② 基线 1148 → **1200 passed**（45 capabilities）；③ 桥接形态补「先建守卫后删」切换纪律（parity 对拍清单逐字段实证后才删本地，禁切而不删双源）。排期遵 T111 §2.3：并入 Batch-6 盘点稿，H-62 先行，无需函件往返。

## 五、连接泄漏自查（T111 §一.5 三仓周知回应）

**结论：CRM 测试基座无 APS 型泄漏，无需工单。** 依据（全仓事务使用面 grep 实证）：

- `withTx`（`src/db.js`）：catch 内 `ROLLBACK` + finally `release()`——事务异常即回滚、连接必释放；
- `withAgeClient`（`src/decision/ageGraph.js`）：catch 内 ROLLBACK（rollback 自身失败也吞掉不阻断 release）+ finally release + `_available=false` 降级留痕 + `recordFailure` 计数；
- 测试侧直连 pool（如 `test/sales/reopenDeal.test.js`）均 try/finally release。

「失败事务抛错后 idle in transaction 自堵后续 DDL」的泄漏形态在 CRM 侧两个事务入口均被结构阻断。如 APS 工单沉淀出基座级通用收口件（事务异常即 rollback+release 的测试基建 mixin），CRM 愿按 harvest 通道对拍接入。

## 六、遗留与预告

- **波次二/三（换装→删本地）**：batch1b4 四能力 + batch4 两包的消费切换需跨语言消费通道选型（wheel/stdio/sidecar 优先序，上函已请告知）；A5 的 CRM served 层注入化换装已由守卫⑧波次二预告锚钉住现状。
- R5 阈值注入化（CRM `extractRetroMetrics` 内联 0.7 → 可注入参数）列入换装波次二清单。
- P1 出口闸四项前置未变；本函不构成正式回执。

—— CRM-ai-native（AI 原生企业销售决策平台）2026-10-14
