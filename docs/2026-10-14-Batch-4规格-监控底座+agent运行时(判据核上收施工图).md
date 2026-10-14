# Batch-4 规格：监控底座 + agent 运行时（域无关判据核上收施工图）

> 来源：《2026-10-14-CRM两页(决策监控+智能体工作台)域无关能力上收分析.md》§三 候选 #1/#3/#4/#5/#6/#7/#10/#12（#9/#11 调度复盘归 Batch-5）。
> 范式：与前批一致——L0 契约（零依赖/零IO/零领域字面量）→ 纯函数判据核 → 双面 re-export → 登记三项 → manifest → 守卫+变异自证 → lint 四闸 → 组合回归 → T 提交。
> **IO 边界**：CRM 侧的落库/订阅/定时巡检/SSE/DB 去重查询均为 IO 编排，**留消费方**；上收的只是纯函数判据核与契约词汇。域值（GATE_SCENARIOS 八闸名、8 个 agent 名、READ_ONLY_SKILLS 三个具体 skill、矩阵 7 行域值）一律留 CRM，foundation 只收结构与机制。

## 一、子批划分

| 子批 | 内容 | CRM 锚点 |
|---|---|---|
| **4a 监控底座** | contract/observability.py + observability/ 机制包（归因四类交叉/闸门指标聚合/accuracy 三态/投递成功率防假绿/负向判据两级/富集命中率/边双口径/失败计数器） | monitorStore.js:88-97,33-57,132-165 / signalMetrics.js:31,123-199 / enrichmentMetrics.js / edgeSource.js / busFailures.js |
| **4b agent 运行时** | contract/agent_runtime.py + agent_runtime/ 机制包（三源触发匹配+只读白名单 fail-closed/去重键/冷却判决/glassBox 可解释链/契约合规三维判定/KG 收敛闸门+降级守卫） | eventTrigger.js:89-117 / glassBox.js / contractMonitor.js:21-62 / agents.js:14-64 |

## 二、4a 语义清单（逐条，file:line 为 CRM 真值）

1. **classify_attribution**（monitorStore.js:88-97）：四类交叉——必填齐+不准→inference_bias；缺+不准→input_error；缺+准/待定→input_missing；齐+warn→context_insufficient；其余→None（良性不计入）。
2. **accuracy_bucket**（monitorStore.js:138-143）：CONFIRMED/APPROVED→accurate；OVERRIDDEN/CORRECTED→inaccurate；其他非空/空→pending。
3. **gate_metrics 聚合**（monitorStore.js:49-55）：AUTONOMOUS→autonomous；HUMAN→human；REQUIRED/ESCALATED→escalated。
4. **delivery_success_rate**（signalMetrics.js:31）：attempted>0 ? sent/attempted : **null（无尝试≠100%，防假绿）**；conflict=failed+skipped。
5. **负向判据两级**（signalMetrics.js:169-182 + 注释 §F-6(a)）：启用渠道零 sent 时——attempted=0→`delivery_silent`（真静默，参与出口闸可阻断）；attempted>0→`delivery_undelivered`（有归因未送达，**刻意不参与出口闸**防闸门噪音）；附首位原因 top_error。判据 B gen_silent：fired>0 而 landed=0（signalMetrics.js:192-198）。**配置读取失败≠配置缺失**（:107-115 分别留痕，绝不回退默认全开——防假绿判据自己制造假绿）。
6. **富集命中率**（enrichmentMetrics.js）：分母恒真实——calls>0 才计率；多源累计 cost/calls/hits 分别求和再算总率。
7. **边双口径**（edgeSource.js）：DEMO_EDGE_SOURCES 闭集；NULL 来源不计入真实供给（:17）；split 双组不修改原数组；runtime-only 供合规分母。
8. **失败计数器**（busFailures.js）：record（kind 累计，返回 {kind,count}）/get 聚合/reset 测试隔离；零依赖可无 DB 单测；单一实现防判据分裂（bus 与 monitor re-export 同一 Map）。

## 三、4b 语义清单

1. **三源触发匹配**（eventTrigger.js:89-103）：source(缺省'event')+domain+type+entity_type 四元组精确匹配；命中后**只读白名单 fail-closed**——非白名单 skill 拒绝并留痕（reason:not-readonly）；config.enabled=false 或无矩阵→null。
2. **去重键**（eventTrigger.js:114-117）：`entity_id:intent:val`，dedup_field 取尾段，空值→'new'（每次都算新）。
3. **冷却判决**（eventTrigger.js:123-129）：now-last<cooldown→skip 留痕（reason:cooldown）；match 级 cooldown 覆盖缺省 300000ms。DB 去重（主，重启有效）与查失败保守放行+留痕（:143-145）留消费方，但「查失败→放行」语义在契约登记。
4. **glassBox**（glassBox.js:10-20）：脏信号过滤（非 str 且无 type 丢弃，trace 项数=有效信号数）；无信号不抛错走「无信号」叙述分支；ruleRef/axis 可覆盖禁硬编码；输出 {judge, trace, why_narrative}。
5. **契约合规三维**（contractMonitor.js:44-62）：skill_ok=契约声明 skills ⊆ episodes(loop-started/done) 的 facts.skill 并集；memory_ok=knowledge_scope.layers ⊆ context-injected episodes 的 knowledge_layers_read 并集；success=人工标记或 'pending'；join_key 稳定键优先回退标题（:21-28）。
6. **KG 收敛闸门**（agents.js:14-64）：KG_LAYER_ORDER=['L1','L2','L3','L4'] 全序；kg_target 天花板（无 target 开放最高层）；降级可服务层 {L1,L2}；effective=declared∩served，dropped 非空→triggered（装配失败）；resolve_runtime=effective（运行时强制注入防契约层静默误判）。服务层集合由调用方注入（foundation 不硬编码 'kg_coverage_stage2'）。

## 四、契约与机制包形态

- `contract/observability.py`：ATTRIBUTION_CATEGORIES(4) / ACCURACY_BUCKETS(3) / GATE_METRIC_STATES 映射 / NEGATIVE_PREDICATE_TYPES(delivery_silent,delivery_undelivered,gen_silent) / DELIVERY_SILENT_BLOCKS_EXPORT=True(语义登记) / OBSERVABILITY_INVARIANTS(防假绿条目：无尝试→null、分母恒真实、读失败≠配置缺失、NULL 来源不计入) / ObservabilityError。
- `contract/agent_runtime.py`：TRIGGER_SOURCES(event,timer,external) / TRIGGER_ROW_FIELDS / DEDUP_EMPTY_SENTINEL='new' / DEFAULT_COOLDOWN_MS=300000 / GLASSBOX_FIELDS(judge,trace,why_narrative) / COMPLIANCE_DIMENSIONS(skill_ok,memory_ok,success) / COMPLIANCE_PENDING='pending' / KG_LAYER_ORDER / ASSEMBLY_GUARD_NAMES(l3_degraded,kg_convergence) / AGENT_RUNTIME_INVARIANTS(只读白名单 fail-closed、查失败保守放行必留痕、脏信号过滤、无信号不抛错) / AgentRuntimeError。
- 机制包 `observability/`：classify_attribution / accuracy_bucket / aggregate_gate_metrics / delivery_success_rate / classify_negative_predicates(channels_stats,enabled,top_errors→alerts 纯函数核) / compute_enrichment_rate / aggregate_enrichment / is_demo_edge_source / split_edges_by_caliber / edge_caliber_count / runtime_edges_only / FailureCounter 类。
- 机制包 `agent_runtime/`：match_trigger(desc,rows,allowed_skills,enabled) / dedup_key_for / cooldown_verdict(last_ts,now,cooldown_ms) / build_glass_box / join_keys_of / judge_contract / kg_convergence_gate(spec,kg_served) / l3_degraded_guard(spec,kg_served) / resolve_runtime_layers。

## 五、判据面与登记

- 守卫测试：`tests/test_batch4_observability_agent.py`（两包 parity 锚点 + CRM 语义对拍注释锚点）。
- 登记三项：version.py CAPABILITIES（41→43）、test LAYERS、Makefile --layers 追加 observability,agent_runtime。
- gen_capability_manifest.py：两行 VERIFY + 两行 SEMANTICS。
- 变异自证着力点（≥8）：inference_bias 判序互换 / accuracy 待定吞成 accurate / REQUIRED 漏出 escalated / attempted=0 报 100% / silent↔undelivered 合并 / 富集空记录造率 / demo 边计入分母 / 非白名单放行 / 冷却反向 / 脏信号入 trace / 越界层不收敛。
