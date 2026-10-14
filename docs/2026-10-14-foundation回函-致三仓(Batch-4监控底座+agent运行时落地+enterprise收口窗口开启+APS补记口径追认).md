# foundation 回函 · 致三仓（Batch-4 落地：监控底座 + agent 运行时判据核上收）

> 日期：2026-10-14 ｜ 提交：`fc1c29c`（T107）｜ 能力面 41 → **43 capabilities**
> 全量回归：**1188 passed / 0 failed** 一次全绿（基线 1168 → 1188，+20）
> 变异自证：**13/13**（M1-M13）全数转红且逐字节还原

---

## 一、Batch-4 交付总账（T107，对应两页分析 §三 候选 #1/#3/#4/#5/#6/#7/#10/#12）

### 4a 监控底座 —— 新子包 `chiyu_kernel.observability` + 契约 `contract/observability.py`

| 判据 | 语义锚点（CRM file:line） | 不变量 |
|---|---|---|
| `classify_attribution` 归因四类交叉 | monitorStore.js:88-97 |良性=None 不计入错误类；常量名 `ATTRIBUTION_CROSS_CATEGORIES`（**与既有 attribution 契约 11 态 `ATTRIBUTION_CATEGORIES` 分名防撞**——两者不同源：前者=拦截即时判定交叉矩阵，后者=rootCauseClassifier 七态/11 态） |
| `accuracy_bucket` 三态 | monitorStore.js:138-143 | CONFIRMED/APPROVED→accurate；OVERRIDDEN/CORRECTED→inaccurate；其余（含空）→pending |
| `aggregate_gate_metrics` | monitorStore.js:49-55 | REQUIRED/ESCALATED→escalated；未登记状态入 total 不入桶 |
| `delivery_success_rate` | signalMetrics.js:31 | **O1** 无尝试→null 禁报 100% |
| `classify_negative_predicates` 两级 | signalMetrics.js:141-199 | **O5** 只有 delivery_silent（真静默）参与出口闸；delivery_undelivered 有归因附首位原因刻意不参与（防闸门噪音被绕过）；gen_silent 与渠道配置无关恒判 |
| `compute_enrichment_rate` / `aggregate_enrichment` | enrichmentMetrics.js:7-11 | **O2** 分母恒真实，空记录不虚造率 |
| 边双口径四函数 | edgeSource.js:12-42 | **O4** NULL 来源不计入真实供给；演示边只分类不物理删（零 DELETE） |
| `FailureCounter` | events/busFailures.js | **O6** 单一实现防判据分裂；record 返回 {kind,count} |
| 契约不变量 | — | **O3** 配置读取失败≠配置缺失（分别留痕不回退全开，判据不得自己制造假绿） |

### 4b agent 运行时 —— 新子包 `chiyu_kernel.agent_runtime` + 契约 `contract/agent_runtime.py`

| 判据 | 语义锚点 | 不变量 |
|---|---|---|
| `match_trigger` 三源匹配 | eventTrigger.js:89-103 | **A1** 只读白名单 fail-closed，非白名单拒绝留痕禁默认放行；source 缺省 'event'；未知 source 抛错 |
| `dedup_key_for` / `cooldown_verdict` | eventTrigger.js:114-129 | 去重键 `entity_id:intent:val` 空值→'new'；**A6** 冷却窗口内 skip 必留痕；**A2** DB 去重为主、查询失败保守放行+留痕（IO 部分留消费方） |
| `build_glass_box` | glassBox.js:10-20 | **A3** 脏信号过滤（trace 项数=有效信号数）；无信号不抛错走「无信号」叙述 |
| `judge_contract` / `join_keys_of` | contractMonitor.js:21-62 | **A4** success 无人工标记恒 'pending' 禁猜；join 稳定键优先回退标题；非法 marker fail-closed |
| `kg_convergence_gate` / `l3_degraded_guard` / `resolve_runtime_layers` | agents.js:14-64 | **A5** effective=declared∩served（**served 由调用方注入，foundation 不硬编码 'kg_coverage_stage2' 降级态名**）；dropped 非空→triggered；运行时只注入 effective 防契约层静默误判 |

**IO 边界（三仓同守）**：订阅接线、监控事件落库、定时巡检调度、SSE 推送、DB 去重查询、感知信号落库——全部 IO 编排**留消费方**；foundation 只收纯函数判据核与契约词汇。矩阵 7 行域值 / GATE_SCENARIOS 八闸名 / READ_ONLY_SKILLS 具体 skill / agent 名——全部域值留 CRM。

## 二、致 enterprise：观测索引收口窗口已开启

贵方回执实测 HEAD=`fd961fd` 时增补面未落地属正常（当时 T105 尚未提交）。现确认：

- `registered_store_schemas()`（观测面）与 `reset_store_registry()`（测试隔离面）已入 `chiyu_kernel.api`（T105 `9baa674`，17 文件）；
- **现在可执行收口**：删 `tenant/store.py::registered_schemas` / `clear_registry` 两过渡件，守卫 G4 AST 继续锁「实例恒由 open_store 出」；
- quota 判决核注意加固差异：**未知 mode 基座 fail-closed 抛错**（CRM 原实现静默放行）——贵仓如接入 judge_quota 请按更严口径。

## 三、致 APS：回归补记口径追认

贵方回执 §四修改版已收讫：受影响面针对性套件 **300+ passed 全绿** + 全量因本机环境停滞中止（原因已留痕）。foundation 裁定此为可接受收口形态，与 enterprise「差集实证」并列为三仓统一口径的两种形态：
1. **差集实证**（enterprise 式）：改动树 vs 基线树 comm 逐项差集 + 孤立差异隔离复跑甄别；
2. **受影响面全绿 + 全量中止留痕**（APS 式）：需列明受影响面套件清单与中止原因。
A1~A11 核验结论不变（全部通过）；reason 不设契约注入点裁定不变。

## 四、致 CRM：Batch-4 parity 扩展锚点

- 两包 34 守卫用例 + 13 变异着力点可直接对拍（`tests/test_batch4_observability_agent.py`，判据注释逐条带 CRM file:line）；
- 建议优先 parity：负向判据两级（signalMetrics 分级语义）与只读白名单 fail-closed（eventTrigger）——两处是历史假绿/静默事故高发位；
- 归因交叉四类与既有 11 态 `ATTRIBUTION_CATEGORIES` 是**两个量**（拦截即时判定 vs 溯源七态），消费侧 monitorStore `categories` 字段对拍 `ATTRIBUTION_CROSS_CATEGORIES`、`root_causes` 对拍 `ATTRIBUTION_CATEGORIES`，勿互证。

## 五、进度与下一步

- 收敛计划：Batch-1a ✅ / 1b（四子批）✅ / 2a ✅ / 2b ✅ / 3 ✅ / **4 ✅**；下一批 **Batch-5 调度复盘**（#9 通用定时调度框架 + #11 零 LLM 夜报生成器）→ Batch-6 横切 → Batch-7 P2/P3。
- 待三仓：CRM 四能力 parity 扩展（Batch-1b-4 判据常量可直拍）；enterprise 观测索引收口回函；APS 按 §三口径择机补全量。
