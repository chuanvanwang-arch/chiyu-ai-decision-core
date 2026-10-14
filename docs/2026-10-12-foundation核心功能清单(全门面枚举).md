# foundation 核心功能清单（全门面枚举）

- 日期：2026-10-12
- 权威来源：五个 sanctioned 门面的 `__all__`（本轮实取，机器可验）；子包清单实扫
- 统计口径：**符号总数 ≈ 478** —— `chiyu_kernel.api` 404 ＋ `chiyu_kernel.approval` 5 ＋ `chiyu_decision.api` 15 ＋ `chiyu_portal.api` 26 ＋ `contract.decision` 22 ＋ `contract.memory` 6（kernel.api 内含对 contract/approval 部分符号的再导出，故总数有少量重叠）
- 合法 import 通道（唯一）：`chiyu_kernel.api` / `chiyu_kernel.contract`（含子树）/ `chiyu_kernel.approval` / `chiyu_decision.api` / `chiyu_portal.api`；门禁 `tools/check_import_surface.py`
- 状态位：除 `evolution`（experimental）外全部 stable（1.0 兼容承诺）；deprecation 政策=先 warn 一版再移除

---

## 一、决策族（decision 包 + contract.decision + approval）

### 1.1 chiyu_decision.api（15 符号，全枚举）——脊柱与评分

| 符号 | 职责 |
|---|---|
| `run_spine` | 决策脊柱六阶段主入口（S1 校验→S2 评分→S3 置信→S4 红线→S5 落库→S6 审计）；支持 persister / approval_gate / audit_sink / redline_spec / element_cap / memory_recaller / **audit_persister**（T58，REJECTED/PENDING 审计轨 fail-closed） |
| `resume_spine` | 审批后脊柱续跑（PENDING → APPROVED/REJECTED 收口） |
| `score_rubric` | 九尺子评分（RUBRIC_KEYS 九键等权 0-4，按键名遍历零敏感；仅 clarity 允许 LLM 精评） |
| `aggregate_confidence` | 置信度聚合（铁律 C-B：唯一来源=ratio 等权，非 ratio source_key 抛 ENGINE_FAULT） |
| `cap_rubric_by_elements` | 要素→尺子封顶（ELEMENT_RUBRIC_CAPS + ELEMENT_MISSING_CAP=2） |
| `check_elements` | 八要素缺失检测（S2 口径） |
| `evaluate_redline` | 红线评估（返回 RedlineVerdict） |
| `autonomous_release` | 自主放行（AUTONOMOUS_GATE_EXPR 门控） |
| `validate_spine_order` | SPINE_ORDER 结构校验（末位 S5/次末位 S4） |
| 类型 | `SpineResult` / `RubricReport` / `RedlineVerdict` / `DecisionError` / `DECISION_ERROR_CODES` / `SPINE_ORDER`（再导出） |

### 1.2 contract.decision（22 符号，全枚举）——决策契约

- **八要素**：`EIGHT_ELEMENTS`（S2 契约序）、`EIGHT_ELEMENTS_ZH`
- **九尺子**：`RUBRIC_KEYS`、`RUBRIC_NAMES_ZH`、`RUBRIC_SCALE_MAX`、`RUBRIC_LLM_ELIGIBLE`、`RUBRIC_THRESHOLDS_DEFAULT`
- **封顶**：`ELEMENT_RUBRIC_CAPS`、`ELEMENT_MISSING_CAP`
- **脊柱**：`SPINE_ORDER`、`SPINE_STAGE_LABELS_ZH`、`validate_spine_order`
- **审计双轨**：`AUDIT_RECORD_KIND`（="audit"）、`AUDIT_APPROVAL_EVENTS`、`AUDIT_EVENT_APPROVAL_PENDING/REJECTED/RESUMED`
- **自主放行/置信**：`AUTONOMOUS_GATE_EXPR`、`AUTONOMOUS_RELEASE_DEFAULT`、`CONFIDENCE_SOURCE_KEY`
- **内部核查矩阵（禁显代号，对外只提 SEVEN_DIMS 契约面）**：`SEVEN_DIMS`、`SEVEN_DIM_KEYS`

### 1.3 chiyu_kernel.approval（5 符号，全枚举）——审批闸

`RedlinePriorityGate`（红线优先闸：A 红线 > B 写闸/poor > 放行）、`DecisionApprovalGate`、`DecisionPassThroughGate`、`DecisionApprovalVerdict`、`DecisionVerdictState`。

## 二、决策记忆网（memory，T44 毕业 stable，1.0 承诺）

| 函数/类型 | 职责 |
|---|---|
| `write_decision_memory_net` | graph_edge 唯一写入口（单源裁定守卫钉死） |
| `PgNoteStore` / `InMemoryNoteStore` / `NoteStore` | 粒子属性唯一写（单源裁定：particle_attribute 唯一写=PgNoteStore） |
| `build_memory_recaller` | 决策读记忆钩子（run_spine memory_recaller 形参的工厂） |
| `recall_precedents` / `RecalledItem` | 先例召回（MIN_PRECEDENTS/MIN_SUCCESS_LEN 质量阈） |
| `degraded_recall` | 降级召回（store 不可达时中性返回，不假填充） |
| `rrf_fuse` / `RRF_K_DEFAULT` | RRF 融合（FTS+vector 双通道） |
| `PgMemoryLogStore` / `MemoryLogEntry` / `MemoryLogStore` | 记忆日志轨 |
| `MemoryNote` / `note_hash` / `NOTE_ATTR_*`（5 项） | 记忆条目与属性哈希 |

## 三、数据族（store / persist / graph / vector）

- **PG 存取**：`PgVectorStore` / `PgVectorStorePersister` / `open_store` / `connect` / `make_cursor` / `parse_dsn` / `validate_dsn` / `mask_dsn` / `ensure_schema` / `ensure_tsvector` / `drop_test_schema` / `drop_ephemeral_schemas` / `probe_schema_isolation` / `terminate_backends_sql` / `terminate_own_backends` / `in_testing_context` / `driver_available` / `ddl_statements`
- **审计链（hash chain）**：`chain_hash` / `verify_chain` / `build_chain` / `VerifyResult` / `content_hash` / `hash_signature`
- **受控图写（A-1 通道）**：`open_graph_write_store`（T54 sanctioned 工厂）/ `build_graph_write_server` / `make_graph_write_profile` / `write_controlled_edges`（MCP 工具，两阶段 confirm）/ `allow_principals` / `EdgeWrite` / `EdgeWriteReport` / `GraphStore` / `GraphEdge` / `InMemoryGraphStore` / `PgCteGraphStore` / `decision_backlinks` / `relation_view` / `timeline_view` / `fold_history`
- **向量检索**：`TIER_*`/`VTIER_*`（分层常量与别名，normalize_tier/tier_spec）/ `vector_available` / `vector_backend` / `vector_resolve` / `vector_info` / `vector_index_ddl` / `ensure_embedding` / `cosine` / `pad_to_dim` / `hash_vector` / `OnnxRunner` / `pg_to_vec` / `vec_to_pg`

## 四、运行族（actions / events / workflow / orchestration / plan / scenario / session）

- **动作**：`ActionRegistry` / `ActionSpec` / `ACTION_MAX` / `ACTION_MIN` / `ALLOWED_TRANSITIONS` / `assert_transition` / `TaskStateError` / `TERMINAL_STATES` / `TASK_STATES` / `TASK_KINDS` / `SharedTask` / `WorkerRun`
- **事件**：`EventBus` / `PublishReport` / `SessionEvent` / `Subscriber` / `counting_subscriber` / `log_subscriber` / `EVENT_TYPE_DECISION` / `EVENT_TYPE_MEMORY_LOG`
- **工作流**：`Workflow` / `WorkflowStep` / `WorkflowPhase` / `WorkflowMeta` / `WorkflowResult` / `WorkflowRunner` / `WorkflowError` / `WorkflowStateError` / `WorkflowStopReason` / `WORKFLOW_STEP_STATES` / `is_fatal_workflow_error` / `is_stuck` / `ZOMBIE_STALE_SECONDS`
- **编排/多智能体**：`Agent` / `AgentLoop` / `AgentSpec` / `AgentRegistry`（+Live）/ `TeamMember` / `TeamRegistry` / `TeamSpec` / `SubagentDescriptor` / `SubagentPool` / `LoopGuard` / `FAILURE_LIMIT` / `MAX_REDO` / `GuardViolation` / `GuardDenied`
- **计划/待办**：`Plan` / `PlanStep` / `PlanMode` / `PlanStateError` / `backfill_plan` / `TodoItem` / `TodoList`
- **场景包**：`ScenarioPack` / `ScenarioPackStore` / `ScenarioStep` / `scenario_from_dict` / `scenario_build_in_memory_server` / `DecisionScenarioProfile` / `DecisionIOField`（决策 I/O 契约：kind∈`IO_KINDS` 闭集、闸⊆`GATE_KINDS`）/ `register_scenario` / `is_registered` / `get_scenario` / `require_scenario` / `list_scenarios` / `MAX_REQUIRED_FIELDS`
- **会话/交互**：`SessionManager` / `SessionLog` / `TerminalSession` / `WorkMode` / `resolve_work_mode` / `MODE_PRESETS` / `resolve_storyline_policy`

## 五、集成族（llm / mcp / mcpserver / tools / plugins / hooks）

- **LLM**：`LlmProvider` / `LlmResponse` / `ToolCall` / `build_provider` / `DeepSeekProvider` / `StubProvider`
- **MCP 双层**：mcp（客户端桥）`McpBridge` / `McpTransport` / `StdioTransport` / `normalize_mcp_name`；mcpserver（服务端）`McpServer` / `InMemoryMcpServer` / `McpToolDef` / `ToolRegistry` / `ToolSpec` / `ExposedTool` / `register_builtins` / `register_fs_tools` / `register_native_tools` / `register_shell_tools` / `register_workflow_tools` / `run_command`
- **两阶段确认（零信任写）**：`issue_confirm_token` / `verify_confirm_token` / `ConfirmRequired` / `ConfirmTokenInvalid` / `CommandRejected`
- **沙箱/防护**：`SandboxedFs` / `PathEscapeError` / `ScopeDenied` / `READONLY_PATH_PREFIXES` / `FORBIDDEN_HOSTS` / `FORBIDDEN_ROLES` / `assert_safe_identifier` / `assert_no_free_jsonb` / `assert_no_hard_delete`（禁 DELETE 判据面）
- **插件/钩子**：`PluginRegistry` / `PluginSpec` / `BUILTIN_PLUGINS` / `active_plugins` / `disabled_plugins` / `HookBus` / `HookResult`

## 六、语义族（ontology / context / domain / canary / audit）

- **本体**：`OntologyGraph` / `ontology_sync` / `PRESCRIBABLE_PREDICATES` / `is_prescribable` / `MEMORY_PREDICATES`（contract）
- **情境分层**：`CONTEXT_LAYERS` / `CONTEXT_DIMENSIONS` / `LAYER_NAMES` / `LAYER_LABELS_ZH` / `missing_context_dimensions` / `KNOWLEDGE_LAYERS`
- **领域注入**：`DomainBundle` / `inject_domain` / `assemble` / `AssemblyResult` / `DomainInjectionError`
- **金丝雀（G2/G3 防线）**：`canary_probe`（三判据：event+particle 成对 / engine 边恰好相等 / 红线挡落库）/ `CanaryReport` / `g2_suspend_on_redline` / `BLOCK_KINDS` / `assert_block_kind` / `assert_anchor` / `assert_result_ref` / `assert_writable` / `apply_atomic`
- **审计规范**：`canonical` / `canonical_args` / `stable_stringify` / `meta_redline_hits` / `is_forbidden_change` / `classify_change` / `BASELINE_FIELD` / `assert_not_baseline_skill`
- **幂等/派发**：`derive_idem_key` / `nightly_idem_key` / `IDEM_PREFIX` / `read_dispatch_cfg` / `dispatch_cfg_report`

## 七、进化族（evolution，**experimental**——排除 1.0 承诺）

`SkillDraft` / `promote` / `validate_draft` / `SkillRegistry` / `SkillSpec` / `SkillDraftError` / `SkillConflict` / `readiness_report` / `ReadinessReport` / `Prescription` / `KnobSpec` / `KnobTable` / `begin_replay` / `shadow_replay` / `ReplayVerdict` / `distill` / `DistillReport` / `judge_worthiness` / `check_supply_demand` / `SupplyDemandGap` / `build_knowledge_needs` / `KnowledgeNeed` / `compute_coverage` / `CoverageReport` / `BackfillChannel` / `TraversalResult`

> enterprise 已在用（bridge.py），对外口径必须标 experimental（R-FE1）；毕业须走 RFE（先例：memory T44）。

## 八、版本出口（kernel.api）

`__version__`（动态取分发元数据）/ `api_version` / `API_VERSION` / `CONTRACT_VERSION` / `PACKAGE_VERSION` / `capabilities()` / `capability_status` / `deprecations()` / `require_capabilities`（消费方 fail-closed 能力闸，三仓均已接）

## 九、portal（chiyu_portal.api，26 符号，全枚举）——页面生成

- **NL→页面**：`parse_nl_to_schema` / `guard_nl_input` / `validate_page_schema` / `ValidationError` / `ParseResult`
- **渲染**：`render_page` / `render_conversation` / `render_onboarding` / `direction_cards` / `level_cards` / `mode_cards` / `workflow_cards` / `onboarding_steps` / `RenderResult` / `CreateResult` / `OnboardingResult` / `GuardResult`
- **存储/常量**：`PageDraft` / `PageStore` / `SCHEMA_VERSION` / `PAGE_TYPES` / `COMPONENT_KINDS` / `AGG_FUNCS` / `FILTER_OPS` / `THEMES` / `DEFAULT_ALLOWED_ACTIONS`
- 消费现状：三仓零消费（foundation 观察项 F2）

## 十、契约补遗（contract 子树其余高频符号）

`TenantProfile`（租户档）/ `ParticleTypeSet` / `Particle`（粒子契约）/ `LAYERS`（能力分层登记）/ `MEMORY_KINDS` / `MEMORY_ADDRESS_KEYS` / `MEMORY_DEFAULTS` / `PROVENANCE_SOURCES` / `BUSINESS_CLOCK_FIELD` / `RECORD_CLOCK_FIELD` / `GATE_KINDS` / `IO_KINDS` / `RISKS` / `LEVEL_IDS` / `TIERS`

---

## 附：使用与核对方式

1. 本清单为**核心功能口径**；完整 404 符号逐一枚举以各门面 `__all__` 为权威（机器可验：`python -c "from chiyu_kernel.api import __all__"`）。
2. 消费方新增使用任何符号前，先确认在本清单/`__all__` 内且路径为五门面之一；门面 import 了却没进 `__all__` 会被 `test_facade_import_vs_all.py` 判红。
3. 能力级状态与分层登记见 `version.py::CAPABILITIES`（29 项）与 `tools/gen_capability_manifest.py`（磁盘枚举机械守卫）。
