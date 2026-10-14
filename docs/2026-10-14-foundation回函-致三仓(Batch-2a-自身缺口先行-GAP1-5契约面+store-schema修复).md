# foundation 回函 · 致三仓（Batch-2a：自身缺口先行落地）

> 回函对象：CRM-ai-native / APS-ai-native / chiyu-enterprise
> 事项：你仓盘点报的 **foundation 自身缺口**（APS §四 GAP-1~5 + enterprise §七.3 store 真 bug）已修复落地（T86 `23a70a3`，23 文件，859 passed / 0 failed，5 个变异自证全过，lint 四闸全绿）。
> 边界纪律不变：本仓不向你仓写任何产物；下列接入动作由你仓自完成，各跑 parity 守卫全绿即达收口。

---

## 一、GAP-1~5：sanctioned 契约面已补齐（消费方免再摸内部路径）

你仓纪律面限定 import 仅 {`chiyu_kernel.api`, `chiyu_kernel.contract`}，而五个域此前只有 impl 无契约层词汇 ⇒ 被迫 import 内部路径。现已逐项建 L0 契约（零依赖/零IO/零领域字面量），并经 `contract/__init__.py` + `api.py` 双面 re-export：

| 缺口 | 新契约文件 | 词汇内容（闭集+不变式） | impl 侧变化 |
|---|---|---|---|
| GAP-1 事件 | `contract/event.py` | `EVENT_REQUIRED_FIELDS`(id/event_type)、`PAYLOAD_LAYERS`(metadata/context/impact_domain)、`EVENT_PAYLOAD_TYPES`、`PUBLISH_INVARIANTS`、`PAYLOAD_INVARIANTS` | `events/bus.py` 必填面改由契约闭集驱动；**新增 `events/payload.py`**：载荷三层结构校验机制（register_schema/validate_payload/coerce_payload，APS `event_payload.py` 机制上迁，**域契约与域键一律留消费方**） |
| GAP-2 上下文 | `contract/context.py` | `CONTEXT_LAYERS`(L1-L4)/`CONTEXT_LAYER_LABELS_ZH`/`CONTEXT_DIMENSIONS`(七维)/`GAP_KINDS`(六态)/`VTIER_ORDER`(三级降级+弃用别名)/上限阈值 | assembly/knowledge_needs/retrieval 改为从契约导入（**同名符号同一对象**，无双份漂移） |
| GAP-3 向量 | `contract/vector.py` | `EMBEDDING_BACKENDS`(auto/api/local/cpu/cuda/ascend/none)、`EMBEDDING_RESOLUTION_ORDER`(本地ONNX优先→云端闸→哈希)、`EMBEDDING_MODEL_STATUS`、`EMBEDDING_NETWORK_ENV`、`EMBEDDING_DIM_INVARIANTS` | infer 不动（闭集由对拍守卫守） |
| GAP-4 LLM | `contract/llm.py` | `LLM_TIERS`(7b/3b/1.5b)/`LLM_DEFAULT_TIER`/`LLM_TIER_FIELDS`/`TOOL_CALL_FIELDS`/`LLM_RESPONSE_FIELDS`/`LLM_STORYLINE_POLICY_SOURCES`/`LLM_CLOUD_SCHEME`/`LLM_INVARIANTS` | `llm/tier.py` **零改动**（部署侧按路径加载、零项目 import 是硬约束）⇒ 档位表留 impl，漂移由 parity 守卫对拍（闭集/字段面逐项相等） |
| GAP-5 编排 | `contract/orchestration.py` | `TASK_STATES`/`TERMINAL_STATES`/`BLOCK_KINDS`/`TASK_KINDS`/`SYSTEM_TASK_KINDS`/`ALLOWED_TRANSITIONS`/熔断重试参数/`SYSTEM_ANCHOR_PREFIX`/`AGENT_SPEC_FIELDS`/`AGENT_SPEC_REQUIRED`/`MIN_SUCCESS_LEN`/`ORCHESTRATION_INVARIANTS` | state_machine/agent_registry 改为从契约导入（同一对象）；校验与投影逻辑留 impl |

**新增守卫**（6 文件 35 用例）：`test_event_contract` / `test_context_contract` / `test_vector_contract` / `test_llm_contract` / `test_orchestration_contract` / `test_open_store_schema_isolation`。5 个变异自证：① open_store 键退化→红 ② 契约必填面删 event_type→红 ③ payload 未知层检查失效→红 ④ 转换表删 blocked→ready→红 ⑤ 契约档位删 1.5b→红；还原后全绿，`grep MUTANT` 零残留。

## 二、store schema 感知真 bug 已修（enterprise §七.3 根因）

- **根因**（api.py 原 `open_store`）：单例条件只比对 profile 身份，同一 profile 第二次传不同 schema 时 **schema 参数被静默忽略** ⇒ 进程内多租户共用一个 store 指向同一 schema（串库）。enterprise `tenant/store.py` 自建 `(profile,schema)` 双键注册表正是在绕开它。
- **修复**：`open_store` 改为按 `(profile, schema)` 键控（schema 先经 `assert_safe_identifier` 归一；store 持 profile 引用 ⇒ id 不会复用）。同一目标仍是单实例（纪律不变），多租户各得其所。
- **判据**：`test_open_store_schema_isolation.py` 三判据（异 schema 异实例 / 同键单实例 / 异 profile 隔离），TDD 红→修→绿 + 变异自证。
- **enterprise 接入点**：修好后可删 `tenant/store.py` 自建双键层，改消费 `open_store(profile, schema=...)`；删前先跑你仓 parity 守卫。

## 三、各仓接入点（去重切换，前提已具）

- **APS**：`platform/events.py`+`event_payload.py` → 消费 `chiyu_kernel.contract` 事件词汇 + `chiyu_kernel.events` 总线/载荷校验（你的 `unit.published` 等域契约经 `register_schema` 自行登记，coerce 域键经 `context_keys=` 注入）；`platform/context.py` → 契约词汇已可达；`platform/embedding.py` → `contract/vector.py` 闭集；`aps/llm.py` → `contract/llm.py` 档位口径；`platform/actions.py`/`agents/*` → `contract/orchestration.py` 状态机词汇。
- **enterprise**：`tenant/store.py` 双键层删除改消费 `open_store`（见上）；`agent_dispatch/dispatch.py` → 事件总线契约面；`llm/openai_compat.py` → provider 字段面在契约。
- **CRM**：`monitorSubscriber.js`/`signalMetrics.js` 等 Node 侧同构机制不在本批（Python 内核边界），其**协议/字段口径**可对标 `contract/event.py` 对齐；CRM 侧八闸/第0闸消费不变（Batch-1a 已落地）。

## 四、状态与下一步

- Batch-0 ✅ → Batch-1a ✅(T84) → **Batch-2a ✅(T86)** → Batch-2b（GAP-6~9 上迁：feedback_loop / capability_audit / connectors 传输层 / promotion-reflux 管道，按 APS §5.3 第三波）→ Batch-3（跨仓包级去重，**依赖 Batch-2 全量就绪**）→ Batch-4/5（监控+agent / 调度复盘）。
- 你仓若对契约闭集有异议（如档位表增删、载荷层增补），以回函或工单指明，foundation 按单一事实源修订并同步 manifest。
