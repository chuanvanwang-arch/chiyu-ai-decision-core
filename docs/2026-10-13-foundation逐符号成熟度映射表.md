# foundation 逐符号成熟度映射表

> 日期：2026-10-13 ｜ 配套：`2026-10-12-foundation核心功能清单(全门面枚举).md` + `2026-10-13-foundation功能成熟度与消费侧接入指南.md`

## 0. 生成方法与口径

- **机器生成**：实取五个 sanctioned 门面 `__all__`，对每个符号取 `__module__` 推导能力层，再查 `chiyu_kernel.version.CAPABILITIES`（`version.py:67`，29 能力层）得状态。三包均解析自 `packages/*/src`（非 wheel），避免版本混用。
- **版本**：`PACKAGE_VERSION=0.1.0` ｜ `API_VERSION=1.0.0` ｜ `CONTRACT_VERSION=1.0.0` ｜ `__version__=0.1.0`
- **成熟度只有"层"粒度**：源码仅对 29 个能力层登记 `stable`/`experimental`/`deprecated`（`version.py:62`）。本表把每个符号**继承其所在能力层的状态**，并标出"面 sanctioned 但未单列能力层"的例外（见 §2）。
- **实验态含义**：`experimental` 符号经门面可 import（受 semver 保护），但消费方**不得写进硬验收判据**、不得对外宣称端到端跑通（§13 纪律 + `R-FE1`）。

## 1. 关键发现

1. **sanctioned 表面唯一符号数 = 499**（五门面 `__all__` 去重）；去重前合计 **525**（含门面间再导出重叠，如 `chiyu_kernel.api` 再导出 `contract`/`approval` 符号）。
   - 注：此前《核心功能清单》写"≈478"为旧口径（未含 T68 的 E9+X2 增量且按层相加有重叠）；本表实取唯一值为 **499**，以本表为准。
2. **实验态符号确实在 sanctioned 表面**：`chiyu_kernel.api` 再导出 **27 个 `evolution` 符号**（状态 `experimental`）。纠正"evolution 不在 sanctioned 面"的旧表述——它**在面内、但成熟度门控为 experimental**。
3. **portal 是 sanctioned 面但未单列能力层**：`portal` 整面（26 符号）不在 `CAPABILITIES` 29 层内（status 标"未登记(面sanctioned·非能力层)"）。这是已知登记缺口，建议补登 `portal` 能力层（见 §4）。
4. **外部类型别名不计入成熟度**：178 个 `typing`/`builtins` 再导出（如 `Any`/`Mapping`）非基础自身对象，仅类型标注，不评成熟度。

## 2. 状态分布（去重前 listed 计数）

| 成熟度 | 符号数 | 说明 |
|---|---|---|
| stable | 292 | 可写硬验收判据（1.0 承诺） |
| 未登记(?) | 176 |  |
| 未登记(面sanctioned·非能力层) | 28 | portal/version/harness_native_tools/api 等面合法但未在 29 层登记 |
| experimental | 27 | evolution 符号，禁写硬判据 |
| 外部类型别名 | 2 | typing/builtins 再导出，非基础对象 |

## 3. 各能力层分布（listed 计数 → 状态）

| 能力层 | 符号数 | 状态 |
|---|---|---|
| ? | 176 | 未登记(?) |
| store | 35 | stable |
| orchestration | 30 | stable |
| evolution | 27 | experimental |
| vector | 23 | stable |
| persist | 20 | stable |
| portal | 19 | 未登记(面sanctioned·非能力层) |
| scenario | 18 | stable |
| context | 17 | stable |
| approval | 15 | stable |
| tools | 12 | stable |
| workflow | 12 | stable |
| mcpserver | 12 | stable |
| decision | 12 | stable |
| graph | 11 | stable |
| llm | 10 | stable |
| contract | 9 | stable |
| plugins | 8 | stable |
| ontology | 7 | stable |
| plan | 6 | stable |
| version | 6 | 未登记(面sanctioned·非能力层) |
| audit | 5 | stable |
| skills | 5 | stable |
| mcp | 5 | stable |
| events | 4 | stable |
| domain | 4 | stable |
| session | 3 | stable |
| hooks | 3 | stable |
| actions | 2 | stable |
| typing | 2 | 外部类型别名 |
| interaction | 2 | stable |
| canary | 2 | stable |
| harness_native_tools | 2 | 未登记(面sanctioned·非能力层) |
| api | 1 | 未登记(面sanctioned·非能力层) |

## 4. 各门面计数

| 门面 | 符号数 | None(解析失败) |
|---|---|---|
| `chiyu_kernel.api` | 407 | 0 |
| `chiyu_kernel.contract` | 72 | 0 |
| `chiyu_kernel.approval` | 5 | 0 |
| `chiyu_decision.api` | 15 | 0 |
| `chiyu_portal.api` | 26 | 0 |

## 5. 逐符号映射

| 门面 | 符号 | 源模块 | 能力层 | 成熟度 |
|---|---|---|---|---|
| `chiyu_kernel.api` | `TenantProfile` | `chiyu_kernel.contract.profile` | contract | stable |
| `chiyu_kernel.api` | `PgVectorStore` | `chiyu_kernel.store.pg_store` | store | stable |
| `chiyu_kernel.api` | `ddl_statements` | `chiyu_kernel.store.ddl` | store | stable |
| `chiyu_kernel.api` | `vector_index_ddl` | `chiyu_kernel.store.ddl` | store | stable |
| `chiyu_kernel.api` | `assert_no_free_jsonb` | `chiyu_kernel.store.ddl` | store | stable |
| `chiyu_kernel.api` | `created_schemas` | `chiyu_kernel.store.conn` | store | stable |
| `chiyu_kernel.api` | `close_schema` | `chiyu_kernel.store.conn` | store | stable |
| `chiyu_kernel.api` | `pad_to_dim` | `chiyu_kernel.store.conn` | store | stable |
| `chiyu_kernel.api` | `vec_to_pg` | `chiyu_kernel.store.conn` | store | stable |
| `chiyu_kernel.api` | `open_store` | `chiyu_kernel.api` | api | 未登记(面sanctioned·非能力层) |
| `chiyu_kernel.api` | `DB_TESTING_ENV` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `DSN_ENV` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `DSN_TEST_ENV` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `FORBIDDEN_HOSTS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `FORBIDDEN_ROLES` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `IDENT_MAX` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `SCHEMA_ENV` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `TESTING_FLAG_ENV` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `VALID_FORMS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `DBConfigError` | `chiyu_kernel.store.dsn` | store | stable |
| `chiyu_kernel.api` | `assert_no_hard_delete` | `chiyu_kernel.store.pg_store` | store | stable |
| `chiyu_kernel.api` | `assert_safe_identifier` | `chiyu_kernel.store.dsn` | store | stable |
| `chiyu_kernel.api` | `close_all` | `chiyu_kernel.store.conn` | store | stable |
| `chiyu_kernel.api` | `connect` | `chiyu_kernel.store.conn` | store | stable |
| `chiyu_kernel.api` | `cursor` | `chiyu_kernel.store.conn` | store | stable |
| `chiyu_kernel.api` | `driver_available` | `chiyu_kernel.store.conn` | store | stable |
| `chiyu_kernel.api` | `driver_error` | `chiyu_kernel.store.conn` | store | stable |
| `chiyu_kernel.api` | `drop_ephemeral_schemas` | `chiyu_kernel.store.conn` | store | stable |
| `chiyu_kernel.api` | `drop_test_schema` | `chiyu_kernel.store.conn` | store | stable |
| `chiyu_kernel.api` | `ensure_schema` | `chiyu_kernel.store.conn` | store | stable |
| `chiyu_kernel.api` | `ephemeral_schemas` | `chiyu_kernel.store.conn` | store | stable |
| `chiyu_kernel.api` | `get_dsn` | `chiyu_kernel.store.dsn` | store | stable |
| `chiyu_kernel.api` | `get_schema` | `chiyu_kernel.store.dsn` | store | stable |
| `chiyu_kernel.api` | `in_testing_context` | `chiyu_kernel.store.dsn` | store | stable |
| `chiyu_kernel.api` | `make_cursor` | `chiyu_kernel.store.conn` | store | stable |
| `chiyu_kernel.api` | `mask_dsn` | `chiyu_kernel.store.dsn` | store | stable |
| `chiyu_kernel.api` | `parse_dsn` | `chiyu_kernel.store.dsn` | store | stable |
| `chiyu_kernel.api` | `pg_to_vec` | `chiyu_kernel.store.conn` | store | stable |
| `chiyu_kernel.api` | `probe_schema_isolation` | `chiyu_kernel.store.conn` | store | stable |
| `chiyu_kernel.api` | `raw_dsn` | `chiyu_kernel.store.dsn` | store | stable |
| `chiyu_kernel.api` | `register_ephemeral` | `chiyu_kernel.store.conn` | store | stable |
| `chiyu_kernel.api` | `shared` | `chiyu_kernel.store.conn` | store | stable |
| `chiyu_kernel.api` | `validate_dsn` | `chiyu_kernel.store.dsn` | store | stable |
| `chiyu_kernel.api` | `BACKEND_APP_NAME_PREFIX` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `DEFAULT_LOCK_TIMEOUT_MS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `own_backend_identity` | `chiyu_kernel.store.conn` | store | stable |
| `chiyu_kernel.api` | `terminate_backends_sql` | `chiyu_kernel.store.conn` | store | stable |
| `chiyu_kernel.api` | `terminate_own_backends` | `chiyu_kernel.store.conn` | store | stable |
| `chiyu_kernel.api` | `SPINE_ORDER` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `validate_spine_order` | `chiyu_kernel.contract.decision` | contract | stable |
| `chiyu_kernel.api` | `RUBRIC_KEYS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `RUBRIC_SCALE_MAX` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `EIGHT_ELEMENTS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `AUTONOMOUS_RELEASE_DEFAULT` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `AUDIT_RECORD_KIND` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `AUDIT_EVENT_APPROVAL_PENDING` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `AUDIT_EVENT_APPROVAL_REJECTED` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `AUDIT_EVENT_APPROVAL_RESUMED` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `ELEMENT_MISSING_CAP` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `ELEMENT_RUBRIC_CAPS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `CoverageReport` | `chiyu_kernel.vector.coverage` | vector | stable |
| `chiyu_kernel.api` | `compute_coverage` | `chiyu_kernel.vector.coverage` | vector | stable |
| `chiyu_kernel.api` | `backfill_plan` | `chiyu_kernel.vector.coverage` | vector | stable |
| `chiyu_kernel.api` | `DEFAULT_MIN_COVERAGE` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `HASH_PROVIDER` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `HASH_DIM` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `InferBackend` | `chiyu_kernel.vector.infer` | vector | stable |
| `chiyu_kernel.api` | `cosine` | `chiyu_kernel.vector.infer` | vector | stable |
| `chiyu_kernel.api` | `hash_signature` | `chiyu_kernel.vector.infer` | vector | stable |
| `chiyu_kernel.api` | `stable_stringify` | `chiyu_kernel.vector.infer` | vector | stable |
| `chiyu_kernel.api` | `content_hash` | `chiyu_kernel.vector.infer` | vector | stable |
| `chiyu_kernel.api` | `hash_vector` | `chiyu_kernel.vector.infer` | vector | stable |
| `chiyu_kernel.api` | `OnnxRunner` | `chiyu_kernel.vector.onnx_runner` | vector | stable |
| `chiyu_kernel.api` | `OnnxUnavailable` | `chiyu_kernel.vector.onnx_runner` | vector | stable |
| `chiyu_kernel.api` | `artifact_info` | `chiyu_kernel.vector.onnx_runner` | vector | stable |
| `chiyu_kernel.api` | `clear_cache` | `chiyu_kernel.vector.onnx_runner` | vector | stable |
| `chiyu_kernel.api` | `config_dim` | `chiyu_kernel.vector.onnx_runner` | vector | stable |
| `chiyu_kernel.api` | `get_runner` | `chiyu_kernel.vector.onnx_runner` | vector | stable |
| `chiyu_kernel.api` | `resolve_model_dir` | `chiyu_kernel.vector.onnx_runner` | vector | stable |
| `chiyu_kernel.api` | `vector_available` | `chiyu_kernel.vector.index_vector` | vector | stable |
| `chiyu_kernel.api` | `vector_backend` | `chiyu_kernel.vector.index_vector` | vector | stable |
| `chiyu_kernel.api` | `vector_info` | `chiyu_kernel.vector.index_vector` | vector | stable |
| `chiyu_kernel.api` | `vector_is_available` | `chiyu_kernel.vector.onnx_runner` | vector | stable |
| `chiyu_kernel.api` | `vector_resolve` | `chiyu_kernel.vector.index_vector` | vector | stable |
| `chiyu_kernel.api` | `is_padded_tag` | `chiyu_kernel.vector.index_vector` | vector | stable |
| `chiyu_kernel.api` | `tag_for_dim` | `chiyu_kernel.vector.index_vector` | vector | stable |
| `chiyu_kernel.api` | `Particle` | `chiyu_kernel.ontology.particle` | ontology | stable |
| `chiyu_kernel.api` | `OntologyGraph` | `chiyu_kernel.ontology.graph` | ontology | stable |
| `chiyu_kernel.api` | `normalize` | `chiyu_kernel.ontology.graph` | ontology | stable |
| `chiyu_kernel.api` | `ensure_embedding` | `chiyu_kernel.ontology.hooks` | ontology | stable |
| `chiyu_kernel.api` | `ensure_tsvector` | `chiyu_kernel.ontology.hooks` | ontology | stable |
| `chiyu_kernel.api` | `ontology_sync` | `chiyu_kernel.ontology.hooks` | ontology | stable |
| `chiyu_kernel.api` | `BackfillChannel` | `chiyu_kernel.ontology.backfill` | ontology | stable |
| `chiyu_kernel.api` | `CONTEXT_LAYERS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `KnowledgeNeed` | `chiyu_kernel.context.assembly` | context | stable |
| `chiyu_kernel.api` | `SupplyReport` | `chiyu_kernel.context.assembly` | context | stable |
| `chiyu_kernel.api` | `AssemblyResult` | `chiyu_kernel.context.assembly` | context | stable |
| `chiyu_kernel.api` | `assemble` | `chiyu_kernel.context.assembly` | context | stable |
| `chiyu_kernel.api` | `LAYER_LABELS_ZH` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `KNOWLEDGE_NEEDS_DEFAULT_DIMS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `KNOWLEDGE_LAYERS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `LAYER_NAMES` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `KnowledgeNeeds` | `chiyu_kernel.context.knowledge_needs` | context | stable |
| `chiyu_kernel.api` | `SupplyDemandGap` | `chiyu_kernel.context.knowledge_needs` | context | stable |
| `chiyu_kernel.api` | `build_knowledge_needs` | `chiyu_kernel.context.knowledge_needs` | context | stable |
| `chiyu_kernel.api` | `check_supply_demand` | `chiyu_kernel.context.knowledge_needs` | context | stable |
| `chiyu_kernel.api` | `missing_context_dimensions` | `chiyu_kernel.context.knowledge_needs` | context | stable |
| `chiyu_kernel.api` | `MAX_ENTITIES` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `MAX_DATASOURCES` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `MAX_REQUIRED_FIELDS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `MAX_QUERY_TERMS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `MIN_PRECEDENTS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `MIN_EMBEDDING_COVERAGE` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `CONTEXT_DIMENSIONS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `GAP_MISSING_ENTITY` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `GAP_INSUFFICIENT_EXPERIENCE` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `GAP_LOW_COVERAGE` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `GAP_MISSING_DATA` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `GAP_MISSING_HITL` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `GAP_MISSING_GATE` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `VTIER_FTS_VECTOR` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `VTIER_VECTOR` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `VTIER_FTS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `VTIER_NONE` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `VTIER_ORDER` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `TIER_FTS_VECTOR` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `TIER_VECTOR` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `TIER_FTS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `TIER_NONE` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `TIER_ORDER` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `RecalledItem` | `chiyu_kernel.context.retrieval` | context | stable |
| `chiyu_kernel.api` | `RetrievalEvidence` | `chiyu_kernel.context.retrieval` | context | stable |
| `chiyu_kernel.api` | `RetrievalResult` | `chiyu_kernel.context.retrieval` | context | stable |
| `chiyu_kernel.api` | `degraded_recall` | `chiyu_kernel.context.retrieval` | context | stable |
| `chiyu_kernel.api` | `to_supply_layer` | `chiyu_kernel.context.retrieval` | context | stable |
| `chiyu_kernel.api` | `RECALL_REFERENCE_PREDICATE` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `RECALL_FRAME_PREDICATE` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `recall_precedents` | `chiyu_kernel.context.recall_memory` | context | stable |
| `chiyu_kernel.api` | `build_memory_recaller` | `chiyu_kernel.context.recall_memory` | context | stable |
| `chiyu_kernel.api` | `RRF_K_DEFAULT` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `rrf_fuse` | `chiyu_kernel.context.fuse` | context | stable |
| `chiyu_kernel.api` | `ActionSpec` | `chiyu_kernel.actions.registry` | actions | stable |
| `chiyu_kernel.api` | `ActionRegistry` | `chiyu_kernel.actions.registry` | actions | stable |
| `chiyu_kernel.api` | `ACTION_MIN` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `ACTION_MAX` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `MIN_SUCCESS_LEN` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `AgentRegistry` | `chiyu_kernel.orchestration.agent_registry` | orchestration | stable |
| `chiyu_kernel.api` | `AgentRegistryError` | `chiyu_kernel.orchestration.agent_registry` | orchestration | stable |
| `chiyu_kernel.api` | `AgentSpec` | `chiyu_kernel.orchestration.agent_registry` | orchestration | stable |
| `chiyu_kernel.api` | `TASK_STATES` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `TERMINAL_STATES` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `BLOCK_KINDS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `TASK_KINDS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `SYSTEM_TASK_KINDS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `FAILURE_LIMIT` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `MAX_REDO` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `ZOMBIE_STALE_SECONDS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `SYSTEM_ANCHOR_PREFIX` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `ALLOWED_TRANSITIONS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `TaskStateError` | `chiyu_kernel.orchestration.state_machine` | orchestration | stable |
| `chiyu_kernel.api` | `is_terminal` | `chiyu_kernel.orchestration.state_machine` | orchestration | stable |
| `chiyu_kernel.api` | `assert_state` | `chiyu_kernel.orchestration.state_machine` | orchestration | stable |
| `chiyu_kernel.api` | `assert_block_kind` | `chiyu_kernel.orchestration.state_machine` | orchestration | stable |
| `chiyu_kernel.api` | `assert_transition` | `chiyu_kernel.orchestration.state_machine` | orchestration | stable |
| `chiyu_kernel.api` | `assert_reset` | `chiyu_kernel.orchestration.state_machine` | orchestration | stable |
| `chiyu_kernel.api` | `assert_anchor` | `chiyu_kernel.orchestration.state_machine` | orchestration | stable |
| `chiyu_kernel.api` | `system_anchor` | `chiyu_kernel.orchestration.state_machine` | orchestration | stable |
| `chiyu_kernel.api` | `assert_result_ref` | `chiyu_kernel.orchestration.state_machine` | orchestration | stable |
| `chiyu_kernel.api` | `fold_history` | `chiyu_kernel.orchestration.state_machine` | orchestration | stable |
| `chiyu_kernel.api` | `is_stuck` | `chiyu_kernel.orchestration.state_machine` | orchestration | stable |
| `chiyu_kernel.api` | `summarize` | `chiyu_kernel.orchestration.state_machine` | orchestration | stable |
| `chiyu_kernel.api` | `DISPATCH_CFG_SECTION` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `DISPATCH_CFG_DEFAULTS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `read_dispatch_cfg` | `chiyu_kernel.orchestration.dispatch_cfg` | orchestration | stable |
| `chiyu_kernel.api` | `dispatch_cfg_report` | `chiyu_kernel.orchestration.dispatch_cfg` | orchestration | stable |
| `chiyu_kernel.api` | `IDEM_PREFIX` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `derive_idem_key` | `chiyu_kernel.orchestration.idem` | orchestration | stable |
| `chiyu_kernel.api` | `nightly_idem_key` | `chiyu_kernel.orchestration.idem` | orchestration | stable |
| `chiyu_kernel.api` | `Agent` | `chiyu_kernel.orchestration.agent_runtime` | orchestration | stable |
| `chiyu_kernel.api` | `LiveAgentRegistry` | `chiyu_kernel.orchestration.agent_runtime` | orchestration | stable |
| `chiyu_kernel.api` | `AgentLoop` | `chiyu_kernel.orchestration.agent_loop` | orchestration | stable |
| `chiyu_kernel.api` | `LoopGuard` | `chiyu_kernel.orchestration.loop_guard` | orchestration | stable |
| `chiyu_kernel.api` | `StepVerdict` | `chiyu_kernel.orchestration.loop_guard` | orchestration | stable |
| `chiyu_kernel.api` | `SharedTask` | `chiyu_kernel.orchestration.team` | orchestration | stable |
| `chiyu_kernel.api` | `SubagentDescriptor` | `chiyu_kernel.orchestration.subagent` | orchestration | stable |
| `chiyu_kernel.api` | `SubagentPool` | `chiyu_kernel.orchestration.subagent` | orchestration | stable |
| `chiyu_kernel.api` | `TeamMember` | `chiyu_kernel.orchestration.team` | orchestration | stable |
| `chiyu_kernel.api` | `TeamRegistry` | `chiyu_kernel.orchestration.team` | orchestration | stable |
| `chiyu_kernel.api` | `TeamSpec` | `chiyu_kernel.orchestration.team` | orchestration | stable |
| `chiyu_kernel.api` | `KnobError` | `chiyu_kernel.evolution.knob` | evolution | experimental |
| `chiyu_kernel.api` | `KnobSpec` | `chiyu_kernel.evolution.knob` | evolution | experimental |
| `chiyu_kernel.api` | `KnobTable` | `chiyu_kernel.evolution.knob` | evolution | experimental |
| `chiyu_kernel.api` | `classify_change` | `chiyu_kernel.evolution.knob` | evolution | experimental |
| `chiyu_kernel.api` | `is_forbidden_change` | `chiyu_kernel.evolution.knob` | evolution | experimental |
| `chiyu_kernel.api` | `ReplayVerdict` | `chiyu_kernel.evolution.replay` | evolution | experimental |
| `chiyu_kernel.api` | `shadow_replay` | `chiyu_kernel.evolution.replay` | evolution | experimental |
| `chiyu_kernel.api` | `BASELINE_FIELD` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `PrescriptionError` | `chiyu_kernel.evolution.prescription` | evolution | experimental |
| `chiyu_kernel.api` | `Prescription` | `chiyu_kernel.evolution.prescription` | evolution | experimental |
| `chiyu_kernel.api` | `assert_prescription_transition` | `chiyu_kernel.evolution.prescription` | evolution | experimental |
| `chiyu_kernel.api` | `begin_replay` | `chiyu_kernel.evolution.prescription` | evolution | experimental |
| `chiyu_kernel.api` | `apply_atomic` | `chiyu_kernel.evolution.prescription` | evolution | experimental |
| `chiyu_kernel.api` | `roll_back` | `chiyu_kernel.evolution.prescription` | evolution | experimental |
| `chiyu_kernel.api` | `GuardViolation` | `chiyu_kernel.evolution.guard` | evolution | experimental |
| `chiyu_kernel.api` | `READONLY_PATH_PREFIXES` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `assert_writable` | `chiyu_kernel.evolution.guard` | evolution | experimental |
| `chiyu_kernel.api` | `assert_not_baseline_skill` | `chiyu_kernel.evolution.guard` | evolution | experimental |
| `chiyu_kernel.api` | `g2_suspend_on_redline` | `chiyu_kernel.evolution.guard` | evolution | experimental |
| `chiyu_kernel.api` | `meta_redline_hits` | `chiyu_kernel.evolution.guard` | evolution | experimental |
| `chiyu_kernel.api` | `SkillDraftError` | `chiyu_kernel.evolution.skill_draft` | evolution | experimental |
| `chiyu_kernel.api` | `SkillDraft` | `chiyu_kernel.evolution.skill_draft` | evolution | experimental |
| `chiyu_kernel.api` | `validate_draft` | `chiyu_kernel.evolution.skill_draft` | evolution | experimental |
| `chiyu_kernel.api` | `promote` | `chiyu_kernel.evolution.skill_draft` | evolution | experimental |
| `chiyu_kernel.api` | `ChannelNotReadyError` | `chiyu_kernel.evolution.readiness` | evolution | experimental |
| `chiyu_kernel.api` | `ReadinessReport` | `chiyu_kernel.evolution.readiness` | evolution | experimental |
| `chiyu_kernel.api` | `assert_channel_may_open` | `chiyu_kernel.evolution.readiness` | evolution | experimental |
| `chiyu_kernel.api` | `readiness_report` | `chiyu_kernel.evolution.readiness` | evolution | experimental |
| `chiyu_kernel.api` | `CheckResult` | `chiyu_kernel.evolution.readiness` | evolution | experimental |
| `chiyu_kernel.api` | `EventBus` | `chiyu_kernel.events.bus` | events | stable |
| `chiyu_kernel.api` | `PublishReport` | `chiyu_kernel.events.bus` | events | stable |
| `chiyu_kernel.api` | `Subscriber` | `typing` | typing | 外部类型别名 |
| `chiyu_kernel.api` | `counting_subscriber` | `chiyu_kernel.events.subscribers` | events | stable |
| `chiyu_kernel.api` | `log_subscriber` | `chiyu_kernel.events.subscribers` | events | stable |
| `chiyu_kernel.api` | `canonical` | `chiyu_kernel.audit.chain` | audit | stable |
| `chiyu_kernel.api` | `chain_hash` | `chiyu_kernel.audit.chain` | audit | stable |
| `chiyu_kernel.api` | `build_chain` | `chiyu_kernel.audit.chain` | audit | stable |
| `chiyu_kernel.api` | `verify_chain` | `chiyu_kernel.audit.chain` | audit | stable |
| `chiyu_kernel.api` | `VerifyResult` | `chiyu_kernel.audit.chain` | audit | stable |
| `chiyu_kernel.api` | `EMPTY_PLACEHOLDER` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `TIERS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `DEFAULT_TIER` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `DEFAULT_PARALLEL` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `normalize_tier` | `chiyu_kernel.llm.tier` | llm | stable |
| `chiyu_kernel.api` | `is_cloud_endpoint` | `chiyu_kernel.llm.tier` | llm | stable |
| `chiyu_kernel.api` | `resolve_storyline_policy` | `chiyu_kernel.llm.tier` | llm | stable |
| `chiyu_kernel.api` | `tier_spec` | `chiyu_kernel.llm.tier` | llm | stable |
| `chiyu_kernel.api` | `ToolCall` | `chiyu_kernel.llm.client` | llm | stable |
| `chiyu_kernel.api` | `LlmResponse` | `chiyu_kernel.llm.client` | llm | stable |
| `chiyu_kernel.api` | `LlmProvider` | `chiyu_kernel.llm.client` | llm | stable |
| `chiyu_kernel.api` | `StubProvider` | `chiyu_kernel.llm.client` | llm | stable |
| `chiyu_kernel.api` | `DeepSeekProvider` | `chiyu_kernel.llm.client` | llm | stable |
| `chiyu_kernel.api` | `build_provider` | `chiyu_kernel.llm.client` | llm | stable |
| `chiyu_kernel.api` | `SessionEvent` | `chiyu_kernel.session` | session | stable |
| `chiyu_kernel.api` | `SessionLog` | `chiyu_kernel.session` | session | stable |
| `chiyu_kernel.api` | `SessionManager` | `chiyu_kernel.session` | session | stable |
| `chiyu_kernel.api` | `ToolSpec` | `chiyu_kernel.tools` | tools | stable |
| `chiyu_kernel.api` | `ToolRegistry` | `chiyu_kernel.tools` | tools | stable |
| `chiyu_kernel.api` | `ToolNotFound` | `chiyu_kernel.tools` | tools | stable |
| `chiyu_kernel.api` | `ScopeDenied` | `chiyu_kernel.tools` | tools | stable |
| `chiyu_kernel.api` | `GuardDenied` | `chiyu_kernel.tools` | tools | stable |
| `chiyu_kernel.api` | `SandboxedFs` | `chiyu_kernel.tools.fs` | tools | stable |
| `chiyu_kernel.api` | `PathEscapeError` | `chiyu_kernel.tools.fs` | tools | stable |
| `chiyu_kernel.api` | `register_fs_tools` | `chiyu_kernel.tools.fs` | tools | stable |
| `chiyu_kernel.api` | `CommandRejected` | `chiyu_kernel.tools.shell` | tools | stable |
| `chiyu_kernel.api` | `run_command` | `chiyu_kernel.tools.shell` | tools | stable |
| `chiyu_kernel.api` | `TerminalSession` | `chiyu_kernel.tools.shell` | tools | stable |
| `chiyu_kernel.api` | `register_shell_tools` | `chiyu_kernel.tools.shell` | tools | stable |
| `chiyu_kernel.api` | `SkillSpec` | `chiyu_kernel.skills` | skills | stable |
| `chiyu_kernel.api` | `SkillRegistry` | `chiyu_kernel.skills` | skills | stable |
| `chiyu_kernel.api` | `SkillConflict` | `chiyu_kernel.skills` | skills | stable |
| `chiyu_kernel.api` | `is_skill_name` | `chiyu_kernel.skills` | skills | stable |
| `chiyu_kernel.api` | `load_catalog` | `chiyu_kernel.skills` | skills | stable |
| `chiyu_kernel.api` | `TodoItem` | `chiyu_kernel.plan` | plan | stable |
| `chiyu_kernel.api` | `TodoList` | `chiyu_kernel.plan` | plan | stable |
| `chiyu_kernel.api` | `PlanStep` | `chiyu_kernel.plan` | plan | stable |
| `chiyu_kernel.api` | `Plan` | `chiyu_kernel.plan` | plan | stable |
| `chiyu_kernel.api` | `PlanMode` | `chiyu_kernel.plan` | plan | stable |
| `chiyu_kernel.api` | `PlanStateError` | `chiyu_kernel.plan` | plan | stable |
| `chiyu_kernel.api` | `McpToolDef` | `chiyu_kernel.mcp` | mcp | stable |
| `chiyu_kernel.api` | `McpTransport` | `chiyu_kernel.mcp` | mcp | stable |
| `chiyu_kernel.api` | `InMemoryMcpServer` | `chiyu_kernel.mcp` | mcp | stable |
| `chiyu_kernel.api` | `McpBridge` | `chiyu_kernel.mcp` | mcp | stable |
| `chiyu_kernel.api` | `normalize_mcp_name` | `chiyu_kernel.mcp` | mcp | stable |
| `chiyu_kernel.api` | `HookBus` | `chiyu_kernel.hooks` | hooks | stable |
| `chiyu_kernel.api` | `HookResult` | `chiyu_kernel.hooks` | hooks | stable |
| `chiyu_kernel.api` | `matches` | `chiyu_kernel.hooks` | hooks | stable |
| `chiyu_kernel.api` | `ApprovalGate` | `chiyu_kernel.interaction` | interaction | stable |
| `chiyu_kernel.api` | `ApprovalRequest` | `chiyu_kernel.interaction` | interaction | stable |
| `chiyu_kernel.api` | `WORKFLOW_STEP_STATES` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `WorkflowRunId` | `chiyu_kernel.workflow` | workflow | stable |
| `chiyu_kernel.api` | `WorkflowPhase` | `chiyu_kernel.workflow` | workflow | stable |
| `chiyu_kernel.api` | `WorkflowMeta` | `chiyu_kernel.workflow` | workflow | stable |
| `chiyu_kernel.api` | `WorkflowStep` | `chiyu_kernel.workflow` | workflow | stable |
| `chiyu_kernel.api` | `WorkflowResult` | `chiyu_kernel.workflow` | workflow | stable |
| `chiyu_kernel.api` | `WorkflowStopReason` | `typing` | typing | 外部类型别名 |
| `chiyu_kernel.api` | `WorkflowError` | `chiyu_kernel.workflow` | workflow | stable |
| `chiyu_kernel.api` | `is_fatal_workflow_error` | `chiyu_kernel.workflow` | workflow | stable |
| `chiyu_kernel.api` | `WorkflowStateError` | `chiyu_kernel.workflow` | workflow | stable |
| `chiyu_kernel.api` | `Workflow` | `chiyu_kernel.workflow` | workflow | stable |
| `chiyu_kernel.api` | `WorkflowRunner` | `chiyu_kernel.workflow.runner` | workflow | stable |
| `chiyu_kernel.api` | `register_workflow_tools` | `chiyu_kernel.workflow.register` | workflow | stable |
| `chiyu_kernel.api` | `WorkerRun` | `chiyu_kernel.workflow.host` | workflow | stable |
| `chiyu_kernel.api` | `LEVEL_IDS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `ScenarioPack` | `chiyu_kernel.scenario.model` | scenario | stable |
| `chiyu_kernel.api` | `ScenarioPackError` | `chiyu_kernel.scenario.model` | scenario | stable |
| `chiyu_kernel.api` | `ScenarioStep` | `chiyu_kernel.scenario.model` | scenario | stable |
| `chiyu_kernel.api` | `scenario_from_dict` | `chiyu_kernel.scenario.model` | scenario | stable |
| `chiyu_kernel.api` | `ScenarioPackStore` | `chiyu_kernel.scenario.store` | scenario | stable |
| `chiyu_kernel.api` | `ScenarioPackLockDenied` | `chiyu_kernel.scenario.mcp` | scenario | stable |
| `chiyu_kernel.api` | `scenario_build_in_memory_server` | `chiyu_kernel.scenario.mcp` | scenario | stable |
| `chiyu_kernel.api` | `ScenarioRegistryError` | `chiyu_kernel.scenario.registry` | scenario | stable |
| `chiyu_kernel.api` | `DecisionScenarioProfile` | `chiyu_kernel.scenario.registry` | scenario | stable |
| `chiyu_kernel.api` | `register_scenario` | `chiyu_kernel.scenario.registry` | scenario | stable |
| `chiyu_kernel.api` | `DecisionIOField` | `chiyu_kernel.scenario.registry` | scenario | stable |
| `chiyu_kernel.api` | `IO_KINDS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `GATE_KINDS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `get_scenario` | `chiyu_kernel.scenario.registry` | scenario | stable |
| `chiyu_kernel.api` | `require_scenario` | `chiyu_kernel.scenario.registry` | scenario | stable |
| `chiyu_kernel.api` | `list_scenarios` | `chiyu_kernel.scenario.registry` | scenario | stable |
| `chiyu_kernel.api` | `is_registered` | `chiyu_kernel.scenario.registry` | scenario | stable |
| `chiyu_kernel.api` | `clear_registry` | `chiyu_kernel.scenario.registry` | scenario | stable |
| `chiyu_kernel.api` | `set_key_format` | `chiyu_kernel.scenario.registry` | scenario | stable |
| `chiyu_kernel.api` | `key_format` | `chiyu_kernel.scenario.registry` | scenario | stable |
| `chiyu_kernel.api` | `DomainBundle` | `chiyu_kernel.domain` | domain | stable |
| `chiyu_kernel.api` | `DomainInjectionError` | `chiyu_kernel.domain` | domain | stable |
| `chiyu_kernel.api` | `profile_from_dict` | `chiyu_kernel.domain` | domain | stable |
| `chiyu_kernel.api` | `inject_domain` | `chiyu_kernel.domain` | domain | stable |
| `chiyu_kernel.api` | `EVENT_TYPE_DECISION` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `DecisionRecord` | `chiyu_kernel.persist` | persist | stable |
| `chiyu_kernel.api` | `judge_worthiness` | `chiyu_kernel.persist` | persist | stable |
| `chiyu_kernel.api` | `write_decision_memory_net` | `chiyu_kernel.persist` | persist | stable |
| `chiyu_kernel.api` | `PgVectorStorePersister` | `chiyu_kernel.persist` | persist | stable |
| `chiyu_kernel.api` | `DistillReport` | `chiyu_kernel.persist.memory_tracks` | persist | stable |
| `chiyu_kernel.api` | `InMemoryMemoryLog` | `chiyu_kernel.persist.memory_tracks` | persist | stable |
| `chiyu_kernel.api` | `InMemoryNoteStore` | `chiyu_kernel.persist.memory_tracks` | persist | stable |
| `chiyu_kernel.api` | `MemoryLogEntry` | `chiyu_kernel.persist.memory_tracks` | persist | stable |
| `chiyu_kernel.api` | `MemoryLogStore` | `chiyu_kernel.persist.memory_tracks` | persist | stable |
| `chiyu_kernel.api` | `MemoryNote` | `chiyu_kernel.persist.memory_tracks` | persist | stable |
| `chiyu_kernel.api` | `NoteStore` | `chiyu_kernel.persist.memory_tracks` | persist | stable |
| `chiyu_kernel.api` | `PRESCRIBABLE_PREDICATES` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `distill` | `chiyu_kernel.persist.memory_tracks` | persist | stable |
| `chiyu_kernel.api` | `is_prescribable` | `chiyu_kernel.persist.memory_tracks` | persist | stable |
| `chiyu_kernel.api` | `note_hash` | `chiyu_kernel.persist.memory_tracks` | persist | stable |
| `chiyu_kernel.api` | `parse_ts` | `chiyu_kernel.persist.memory_tracks` | persist | stable |
| `chiyu_kernel.api` | `EVENT_TYPE_MEMORY_LOG` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `PgMemoryLogStore` | `chiyu_kernel.persist.pg_memory_stores` | persist | stable |
| `chiyu_kernel.api` | `PgNoteStore` | `chiyu_kernel.persist.pg_memory_stores` | persist | stable |
| `chiyu_kernel.api` | `NOTE_ATTR_CONTENT` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `NOTE_ATTR_CONTENT_HASH` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `NOTE_ATTR_EXPLICIT` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `NOTE_ATTR_HORIZON_DAYS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `NOTE_ATTR_SOURCE_ENTRY_IDS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `EdgeWrite` | `chiyu_kernel.persist.graph_edges` | persist | stable |
| `chiyu_kernel.api` | `EdgeWriteReport` | `chiyu_kernel.persist.graph_edges` | persist | stable |
| `chiyu_kernel.api` | `write_controlled_edges` | `chiyu_kernel.persist.graph_edges` | persist | stable |
| `chiyu_kernel.api` | `DECISION_TIME_BASIS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `MAX_TRAVERSAL_HOPS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `TIMELINE_SOURCES` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `GraphEdge` | `chiyu_kernel.graph` | graph | stable |
| `chiyu_kernel.api` | `TraversalResult` | `chiyu_kernel.graph` | graph | stable |
| `chiyu_kernel.api` | `GraphStore` | `chiyu_kernel.graph` | graph | stable |
| `chiyu_kernel.api` | `InMemoryGraphStore` | `chiyu_kernel.graph` | graph | stable |
| `chiyu_kernel.api` | `PgCteGraphStore` | `chiyu_kernel.graph` | graph | stable |
| `chiyu_kernel.api` | `relation_view` | `chiyu_kernel.graph` | graph | stable |
| `chiyu_kernel.api` | `timeline_view` | `chiyu_kernel.graph` | graph | stable |
| `chiyu_kernel.api` | `decision_backlinks` | `chiyu_kernel.graph` | graph | stable |
| `chiyu_kernel.api` | `WRITE_CONTROLLED_EDGES_TOOL` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `build_graph_write_server` | `chiyu_kernel.graph.mcp` | graph | stable |
| `chiyu_kernel.api` | `make_graph_write_profile` | `chiyu_kernel.graph.mcp` | graph | stable |
| `chiyu_kernel.api` | `open_graph_write_store` | `chiyu_kernel.graph.mcp` | graph | stable |
| `chiyu_kernel.api` | `RISKS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `McpServerError` | `chiyu_kernel.mcpserver` | mcpserver | stable |
| `chiyu_kernel.api` | `ToolNotExposed` | `chiyu_kernel.mcpserver` | mcpserver | stable |
| `chiyu_kernel.api` | `AuthDenied` | `chiyu_kernel.mcpserver` | mcpserver | stable |
| `chiyu_kernel.api` | `ConfirmRequired` | `chiyu_kernel.mcpserver` | mcpserver | stable |
| `chiyu_kernel.api` | `ConfirmTokenInvalid` | `chiyu_kernel.mcpserver` | mcpserver | stable |
| `chiyu_kernel.api` | `ExposedTool` | `chiyu_kernel.mcpserver` | mcpserver | stable |
| `chiyu_kernel.api` | `canonical_args` | `chiyu_kernel.mcpserver` | mcpserver | stable |
| `chiyu_kernel.api` | `issue_confirm_token` | `chiyu_kernel.mcpserver` | mcpserver | stable |
| `chiyu_kernel.api` | `verify_confirm_token` | `chiyu_kernel.mcpserver` | mcpserver | stable |
| `chiyu_kernel.api` | `McpServer` | `chiyu_kernel.mcpserver` | mcpserver | stable |
| `chiyu_kernel.api` | `StdioTransport` | `chiyu_kernel.mcpserver` | mcpserver | stable |
| `chiyu_kernel.api` | `allow_principals` | `chiyu_kernel.mcpserver` | mcpserver | stable |
| `chiyu_kernel.api` | `CanaryReport` | `chiyu_kernel.canary` | canary | stable |
| `chiyu_kernel.api` | `canary_probe` | `chiyu_kernel.canary` | canary | stable |
| `chiyu_kernel.api` | `DecisionVerdictState` | `chiyu_kernel.approval` | approval | stable |
| `chiyu_kernel.api` | `DecisionApprovalGate` | `chiyu_kernel.approval` | approval | stable |
| `chiyu_kernel.api` | `DecisionApprovalVerdict` | `chiyu_kernel.approval` | approval | stable |
| `chiyu_kernel.api` | `RedlinePriorityGate` | `chiyu_kernel.approval` | approval | stable |
| `chiyu_kernel.api` | `DecisionPassThroughGate` | `chiyu_kernel.approval` | approval | stable |
| `chiyu_kernel.api` | `register_native_tools` | `chiyu_kernel.harness_native_tools` | harness_native_tools | 未登记(面sanctioned·非能力层) |
| `chiyu_kernel.api` | `native_redline_guard` | `chiyu_kernel.harness_native_tools` | harness_native_tools | 未登记(面sanctioned·非能力层) |
| `chiyu_kernel.api` | `PluginSpec` | `chiyu_kernel.plugins.contract` | plugins | stable |
| `chiyu_kernel.api` | `PluginRegistry` | `chiyu_kernel.plugins.contract` | plugins | stable |
| `chiyu_kernel.api` | `BUILTIN_PLUGINS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `register_builtins` | `chiyu_kernel.plugins.builtins` | plugins | stable |
| `chiyu_kernel.api` | `WorkMode` | `chiyu_kernel.plugins.modes` | plugins | stable |
| `chiyu_kernel.api` | `MODE_PRESETS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `DEFAULT_MODE_ID` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `mode_ids` | `chiyu_kernel.plugins.modes` | plugins | stable |
| `chiyu_kernel.api` | `active_plugins` | `chiyu_kernel.plugins.modes` | plugins | stable |
| `chiyu_kernel.api` | `disabled_plugins` | `chiyu_kernel.plugins.modes` | plugins | stable |
| `chiyu_kernel.api` | `resolve_work_mode` | `chiyu_kernel.plugins.modes` | plugins | stable |
| `chiyu_kernel.api` | `MEMORY_EXPERIMENTAL` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `API_VERSION` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `CONTRACT_VERSION` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `CAPABILITIES` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `DEPRECATIONS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `VALID_STATUSES` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `api_version` | `chiyu_kernel.version` | version | 未登记(面sanctioned·非能力层) |
| `chiyu_kernel.api` | `capabilities` | `chiyu_kernel.version` | version | 未登记(面sanctioned·非能力层) |
| `chiyu_kernel.api` | `capability_status` | `chiyu_kernel.version` | version | 未登记(面sanctioned·非能力层) |
| `chiyu_kernel.api` | `require_capabilities` | `chiyu_kernel.version` | version | 未登记(面sanctioned·非能力层) |
| `chiyu_kernel.api` | `contract_version` | `chiyu_kernel.version` | version | 未登记(面sanctioned·非能力层) |
| `chiyu_kernel.api` | `deprecations` | `chiyu_kernel.version` | version | 未登记(面sanctioned·非能力层) |
| `chiyu_kernel.api` | `__version__` | `?` | ? | 未登记(?) |
| `chiyu_kernel.api` | `PACKAGE_VERSION` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `AUDIT_GENESIS_HASH` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `AUDIT_HASH_ALGO` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `AUDIT_REQUIRED_FIELDS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `PROBE_ASSERTIONS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `AUDIT_APPROVAL_EVENTS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `AUDIT_EVENT_APPROVAL_PENDING` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `AUDIT_EVENT_APPROVAL_REJECTED` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `AUDIT_EVENT_APPROVAL_RESUMED` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `AUDIT_RECORD_KIND` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `AUTONOMOUS_GATE_EXPR` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `AUTONOMOUS_RELEASE_DEFAULT` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `CONFIDENCE_SOURCE_KEY` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `ELEMENT_MISSING_CAP` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `ELEMENT_RUBRIC_CAPS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `EIGHT_ELEMENTS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `EIGHT_ELEMENTS_ZH` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `RUBRIC_KEYS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `RUBRIC_LLM_ELIGIBLE` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `RUBRIC_NAMES_ZH` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `RUBRIC_SCALE_MAX` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `RUBRIC_THRESHOLDS_DEFAULT` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `SEVEN_DIM_KEYS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `SEVEN_DIMS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `SPINE_ORDER` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `SPINE_STAGE_LABELS_ZH` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `validate_spine_order` | `chiyu_kernel.contract.decision` | contract | stable |
| `chiyu_kernel.contract` | `EVOLUTION_OBJECTS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `RISK_TIERS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `TIER_AUTO` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `TIER_GUARDED` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `TIER_FORBIDDEN` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `DIRECTIONS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `DIR_WIDEN` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `DIR_TIGHTEN` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `DIR_FLAT` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `PRESCRIPTION_STATES` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `PRESCRIPTION_TERMINAL` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `PRESCRIPTION_TRANSITIONS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `META_REDLINES` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `BASELINE_SKILL_PREFIX` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `VERDICT_PASS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `VERDICT_REJECT` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `VERDICTS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `FAIL_SAFE_VERDICT` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `PRESCRIPTION_AUDIT_FIELDS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `BUSINESS_CLOCK_FIELD` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `MEMORY_ADDRESS_KEYS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `MEMORY_DEFAULTS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `MEMORY_KINDS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `PROVENANCE_SOURCES` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `RECORD_CLOCK_FIELD` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `ATTR_SOURCES` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `ATTR_TYPES` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `CARDINALITIES` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `CORE_ROLES` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `EDGE_LAYERS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `EDGE_SOURCES` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `HASH_DIM` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `LAYERS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `MEMORY_PREDICATES` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `ParticleTypeSet` | `chiyu_kernel.contract.particle` | contract | stable |
| `chiyu_kernel.contract` | `PredicateSet` | `chiyu_kernel.contract.particle` | contract | stable |
| `chiyu_kernel.contract` | `PredicateSpec` | `chiyu_kernel.contract.particle` | contract | stable |
| `chiyu_kernel.contract` | `VALUE_SLOTS` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `VECTOR_DIM` | `?` | ? | 未登记(?) |
| `chiyu_kernel.contract` | `RedlineSpec` | `chiyu_kernel.contract.profile` | contract | stable |
| `chiyu_kernel.contract` | `TenantProfile` | `chiyu_kernel.contract.profile` | contract | stable |
| `chiyu_kernel.contract` | `DecisionVerdictState` | `chiyu_kernel.approval` | approval | stable |
| `chiyu_kernel.contract` | `DecisionApprovalGate` | `chiyu_kernel.approval` | approval | stable |
| `chiyu_kernel.contract` | `DecisionApprovalVerdict` | `chiyu_kernel.approval` | approval | stable |
| `chiyu_kernel.contract` | `RedlinePriorityGate` | `chiyu_kernel.approval` | approval | stable |
| `chiyu_kernel.contract` | `DecisionPassThroughGate` | `chiyu_kernel.approval` | approval | stable |
| `chiyu_kernel.approval` | `DecisionVerdictState` | `chiyu_kernel.approval` | approval | stable |
| `chiyu_kernel.approval` | `DecisionApprovalVerdict` | `chiyu_kernel.approval` | approval | stable |
| `chiyu_kernel.approval` | `DecisionApprovalGate` | `chiyu_kernel.approval` | approval | stable |
| `chiyu_kernel.approval` | `RedlinePriorityGate` | `chiyu_kernel.approval` | approval | stable |
| `chiyu_kernel.approval` | `DecisionPassThroughGate` | `chiyu_kernel.approval` | approval | stable |
| `chiyu_decision.api` | `SPINE_ORDER` | `?` | ? | 未登记(?) |
| `chiyu_decision.api` | `validate_spine_order` | `chiyu_kernel.contract.decision` | contract | stable |
| `chiyu_decision.api` | `run_spine` | `chiyu_decision.spine` | decision | stable |
| `chiyu_decision.api` | `resume_spine` | `chiyu_decision.spine` | decision | stable |
| `chiyu_decision.api` | `SpineResult` | `chiyu_decision.spine` | decision | stable |
| `chiyu_decision.api` | `score_rubric` | `chiyu_decision.scoring` | decision | stable |
| `chiyu_decision.api` | `RubricReport` | `chiyu_decision.scoring` | decision | stable |
| `chiyu_decision.api` | `check_elements` | `chiyu_decision.scoring` | decision | stable |
| `chiyu_decision.api` | `evaluate_redline` | `chiyu_decision.redline` | decision | stable |
| `chiyu_decision.api` | `cap_rubric_by_elements` | `chiyu_decision.scoring` | decision | stable |
| `chiyu_decision.api` | `RedlineVerdict` | `chiyu_decision.redline` | decision | stable |
| `chiyu_decision.api` | `autonomous_release` | `chiyu_decision.redline` | decision | stable |
| `chiyu_decision.api` | `aggregate_confidence` | `chiyu_decision.scoring` | decision | stable |
| `chiyu_decision.api` | `DecisionError` | `chiyu_decision.errors` | decision | stable |
| `chiyu_decision.api` | `DECISION_ERROR_CODES` | `?` | ? | 未登记(?) |
| `chiyu_portal.api` | `SCHEMA_VERSION` | `?` | ? | 未登记(?) |
| `chiyu_portal.api` | `PAGE_TYPES` | `?` | ? | 未登记(?) |
| `chiyu_portal.api` | `COMPONENT_KINDS` | `?` | ? | 未登记(?) |
| `chiyu_portal.api` | `THEMES` | `?` | ? | 未登记(?) |
| `chiyu_portal.api` | `FILTER_OPS` | `?` | ? | 未登记(?) |
| `chiyu_portal.api` | `AGG_FUNCS` | `?` | ? | 未登记(?) |
| `chiyu_portal.api` | `DEFAULT_ALLOWED_ACTIONS` | `?` | ? | 未登记(?) |
| `chiyu_portal.api` | `GuardResult` | `chiyu_portal.guardrails` | portal | 未登记(面sanctioned·非能力层) |
| `chiyu_portal.api` | `guard_nl_input` | `chiyu_portal.guardrails` | portal | 未登记(面sanctioned·非能力层) |
| `chiyu_portal.api` | `ParseResult` | `chiyu_portal.nl_parser` | portal | 未登记(面sanctioned·非能力层) |
| `chiyu_portal.api` | `parse_nl_to_schema` | `chiyu_portal.nl_parser` | portal | 未登记(面sanctioned·非能力层) |
| `chiyu_portal.api` | `RenderResult` | `chiyu_portal.renderer` | portal | 未登记(面sanctioned·非能力层) |
| `chiyu_portal.api` | `render_page` | `chiyu_portal.renderer` | portal | 未登记(面sanctioned·非能力层) |
| `chiyu_portal.api` | `render_conversation` | `chiyu_portal.renderer` | portal | 未登记(面sanctioned·非能力层) |
| `chiyu_portal.api` | `ValidationError` | `chiyu_portal.schema` | portal | 未登记(面sanctioned·非能力层) |
| `chiyu_portal.api` | `validate_page_schema` | `chiyu_portal.schema` | portal | 未登记(面sanctioned·非能力层) |
| `chiyu_portal.api` | `CreateResult` | `chiyu_portal.page_store` | portal | 未登记(面sanctioned·非能力层) |
| `chiyu_portal.api` | `PageDraft` | `chiyu_portal.page_store` | portal | 未登记(面sanctioned·非能力层) |
| `chiyu_portal.api` | `PageStore` | `chiyu_portal.page_store` | portal | 未登记(面sanctioned·非能力层) |
| `chiyu_portal.api` | `onboarding_steps` | `chiyu_portal.onboarding` | portal | 未登记(面sanctioned·非能力层) |
| `chiyu_portal.api` | `mode_cards` | `chiyu_portal.onboarding` | portal | 未登记(面sanctioned·非能力层) |
| `chiyu_portal.api` | `level_cards` | `chiyu_portal.onboarding` | portal | 未登记(面sanctioned·非能力层) |
| `chiyu_portal.api` | `workflow_cards` | `chiyu_portal.onboarding` | portal | 未登记(面sanctioned·非能力层) |
| `chiyu_portal.api` | `direction_cards` | `chiyu_portal.onboarding` | portal | 未登记(面sanctioned·非能力层) |
| `chiyu_portal.api` | `render_onboarding` | `chiyu_portal.onboarding` | portal | 未登记(面sanctioned·非能力层) |
| `chiyu_portal.api` | `OnboardingResult` | `chiyu_portal.onboarding` | portal | 未登记(面sanctioned·非能力层) |

---
— foundation（chiyu-foundation 仓），2026-10-13 ｜ 机器生成自 src，可复跑 `.workbuddy/gen_symbol_maturity.py`