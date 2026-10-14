"""chiyu-kernel 的**唯一公开门面**。

⛔ 消费方只许 import 下列 **sanctioned 面**（成文契约，见 `docs/sanctioned-import-surface.md`，
   由 `tools/check_import_surface.py` 机械门禁，⛔ 该门禁**对 foundation 自身同样生效**）：
     · `chiyu_kernel.api`（本模块，基础内核面）
     · `chiyu_kernel.contract`（L0 契约面，含其子模块如 `chiyu_kernel.contract.decision`）
     · `chiyu_kernel.approval`（决策审批闸面）
     · `chiyu_decision.api`（决策脊柱面：**`run_spine` 在此**，⛔ 不在本模块 ——
        `chiyu-decision` 是独立分发包，kernel 不得反向依赖它 ⇒ 决策能力请用
        `from chiyu_decision.api import run_spine`）
     · `chiyu_portal.api`（门户面，若授权）
   其余内部路径（如 `chiyu_kernel.store.pg_store`、`chiyu_kernel.vector.infer`）一律不属消费面。
   守 tests/test_app_imports_contract_only.py（T2 Step 8）与 tools/check_import_surface.py。
   为什么要门面而不是"直接 import 也行"：内部实现要能在不破坏消费方的前提下
   重构（T9 的 Cython 编译会改模块布局），没有门面就只能靠"谁都不敢改"。

⛔ **接线完整性是可核验的，不是承诺**（2026-09-21 T5 收口时补）
────────────────────────────────────────────────────────────
本模块的 `__all__` 必须**覆盖每个内层子包的 `__all__` 全集**。为什么这条要写成守卫：
"模块已建好但门面没暴露" 是一种**零报错**的缺陷 —— 消费方要么违约 import 内部路径，
要么以为内核没有该能力。守 `tests/test_api_facade_covers_all_layers.py`（逐层比对，
新增符号忘记导出即红）。这正是本会话发现 audit/events/llm/orchestration 四模块
"已写好却未接线"的同一类问题，故把它固化成判据。

⛔ `experimental` 状态透出：memory 内核标 experimental（T5′），消费方可据此
   判断是否可把本包写进 G1/A7 验收判据。
"""
from __future__ import annotations

from typing import Dict, Optional, Tuple

from chiyu_kernel.contract import TenantProfile
from chiyu_kernel.errors import KernelError, KERNEL_ERROR_CODES  # noqa: F401  （门面 re-export；错误 taxonomy 单一事实源）

# ── L1 store：PG + pgvector 单一事实源 ────────────────────────────────────
# ⛔ store 的 sanctioned 面由 `store/__init__.py.__all__` 单一事实源给出，
#    门面整族 re-export（此前只导出零散 9 项 ⇒ 消费方被迫摸内部子模块）。
from chiyu_kernel.store import (  # noqa: F401  （门面 re-export）
    DB_TESTING_ENV,
    DSN_ENV,
    DSN_TEST_ENV,
    FORBIDDEN_HOSTS,
    FORBIDDEN_ROLES,
    IDENT_MAX,
    SCHEMA_ENV,
    TESTING_FLAG_ENV,
    VALID_FORMS,
    DBConfigError,
    PgVectorStore,
    assert_no_free_jsonb,
    assert_no_hard_delete,
    assert_safe_identifier,
    close_all,
    close_schema,
    connect,
    created_schemas,
    cursor,
    ddl_statements,
    driver_available,
    driver_error,
    drop_ephemeral_schemas,
    drop_test_schema,
    ensure_schema,
    ephemeral_schemas,
    get_dsn,
    get_schema,
    in_testing_context,
    make_cursor,
    mask_dsn,
    pad_to_dim,
    parse_dsn,
    pg_to_vec,
    probe_schema_isolation,
    raw_dsn,
    register_ephemeral,
    shared,
    BACKEND_APP_NAME_PREFIX,
    DEFAULT_LOCK_TIMEOUT_MS,
    own_backend_identity,
    terminate_backends_sql,
    terminate_own_backends,
    validate_dsn,
    vec_to_pg,
    vector_index_ddl,
)

# ── L0 contract 决策常量（N5：进 sanctioned 面，免消费方摸内部路径）────────
from chiyu_kernel.contract.decision import (
    AUDIT_RECORD_KIND,
    AUDIT_EVENT_APPROVAL_PENDING,
    AUDIT_EVENT_APPROVAL_REJECTED,
    AUDIT_EVENT_APPROVAL_RESUMED,
    AUTONOMOUS_RELEASE_DEFAULT,
    EIGHT_ELEMENTS,
    ELEMENT_MISSING_CAP,
    ELEMENT_RUBRIC_CAPS,
    RUBRIC_KEYS,
    RUBRIC_SCALE_MAX,
    SPINE_ORDER,
    validate_spine_order,
)

# ── L0 contract 结局/安全契约（三支柱批次一 D1-D4，2026-10-13）─────────────
# OutcomeRecord 结局采集（闭环第一环）+ 三档安全模式 + HITL/resume 证据契约；
# 消费方经 api 门面或 contract 面均可达（对齐 E9/X2 再导出纪律）。
from chiyu_kernel.contract.outcome import (
    OUTCOME_KINDS,
    OUTCOME_REQUIRED_FIELDS,
    OUTCOME_CONFIDENCE_DIRECTION,
    validate_outcome_kind,
)
from chiyu_kernel.contract.security import (
    SECURITY_MODES,
    SECURITY_MODE_DEFAULT,
    SECURITY_MODE_INVARIANTS,
    HITL_EVIDENCE_FIELDS,
    APPROVAL_CORE_STATES,
    APPROVAL_TRANSITIONS,
    RESUME_EVIDENCE_FIELDS,
    HITL_RESUME_FIELD_ALIASES,
    APPROVAL_TRANSITION_EXTENSION_RULE,
    APPROVAL_AGGREGATION_MODES,
    APPROVAL_TIERS,
    APPROVAL_ENGINE_INVARIANTS,
    ApprovalEngineError,
)

# ── L0 contract 度量/IAM 契约（三支柱批次二 D5/D7，2026-10-13）─────────────
# 有效性度量（诚实降级结构保证）+ IAM/RBAC 判定接口（收接口不收角色矩阵）。
from chiyu_kernel.contract.metrics import (
    SCORECARD_FIELDS,
    METRIC_SUMMARY_FIELDS,
    AGGREGATE_METRIC_KEYS,
    HONEST_DEGRADATION_INVARIANTS,
    ScoreCard,
    MetricSummary,
)
from chiyu_kernel.contract.iam import (
    PRINCIPAL_FIELDS,
    SECURITY_DECISION_EXTENSION_RULE,
    SECURITY_DECISION_FIELDS,
    Principal,
    SecurityDecision,
    RoleGate,
    RBAC_INVARIANTS,
    RBAC_DENY_REASONS,
    STANDING_GRANT_STATUSES,
    PAUSE_REASONS,
    GRANT_VERDICTS,
    CREDENTIAL_INVARIANTS,
    TWO_PHASE_INVARIANTS,
)
# D6 审计 canonical schema + 墓碑语义（跨仓 record 毕业对账面；T75 回执 P1）
from chiyu_kernel.contract.audit import (
    AUDIT_CANONICAL_SCHEMA,
    AUDIT_CHAIN_RULE,
    AUDIT_TOMBSTONE_FIELD,
    AUDIT_TOMBSTONE_REASON_FIELD,
    AUDIT_TOMBSTONE_INVARIANTS,
    CHAIN_VERIFY_STATUSES,
    CHAIN_SEAL_FIELDS,
    PROV_CHAIN_INVARIANTS,
)
# ── L0 contract 决策支撑三契约（Batch-1b-3：冲突仲裁/归因规则/四问可审计性）──
from chiyu_kernel.contract.conflict_resolver import (
    CONFLICT_INVARIANTS,
    CONFLICT_STRATEGIES,
    ConflictStrategyError,
)
from chiyu_kernel.contract.attribution import (
    ATTRIBUTION_CATEGORIES,
    ATTRIBUTION_INVARIANTS,
    AttributionError,
    HUMAN_DISPOSITIONS,
    ROOT_CAUSE_LAYERS,
)
from chiyu_kernel.contract.audit_4q import (
    AUDIT4Q_INVARIANTS,
    AUDIT4Q_KEYS,
    AUDIT4Q_STATUSES,
    Audit4QError,
    Q1_MIN_SUPPLIED_DIMS,
)
# ── L0 contract 进化四契约（Batch-1b-4：A/B 实验收口/Token 配额闸/参数健康诊断/处方组装）──
from chiyu_kernel.contract.ab_experiment import (
    AB_ARMS,
    AB_VERDICTS,
    AB_Q_EPS_DEFAULT,
    AB_O_EPS_DEFAULT,
    AB_R_EPS_DEFAULT,
    AB_MIN_ARM_SAMPLE_DEFAULT,
    AB_INVARIANTS,
    AbExperimentError,
)
from chiyu_kernel.contract.quota import (
    BILL_HARDCAP_MULTIPLIER,
    QUOTA_DENY_REASONS,
    QUOTA_INVARIANTS,
    QUOTA_MODE_UNLIMITED,
    QUOTA_MODES,
    QUOTA_UNLIMITED_SENTINEL,
    QUOTA_VERDICTS,
    QuotaGateError,
)
from chiyu_kernel.contract.param_health import (
    HIGH_RISK_FAIL_RATE,
    PARAM_RISK_LEVELS,
    RECOMMEND_INVARIANTS,
    RECOMMEND_OUTCOMES,
    ParamHealthError,
)
from chiyu_kernel.contract.evolution import (
    ASSEMBLE_AUTO_KNOBS,
    ASSEMBLE_EXPECTED_IMPACT_FIELDS,
    ASSEMBLE_INVARIANTS,
    AssembleError,
)
# ── 监控底座 + agent 运行时判据词汇（Batch-4，2026-10-14）────────────────────
from chiyu_kernel.contract.observability import (
    ACCURACY_ACCURATE_FROM,
    ACCURACY_BUCKETS,
    ACCURACY_INACCURATE_FROM,
    ATTRIBUTION_BENIGN,
    ATTRIBUTION_CROSS_CATEGORIES,
    DEMO_EDGE_SOURCES_DEFAULT,
    EDGE_CALIBER_KEYS,
    ENRICHMENT_FIELDS,
    EXPORT_GATE_BLOCKING_TYPES,
    FAILURE_COUNTER_RETURN_KEYS,
    GATE_METRIC_STATES,
    NEGATIVE_PREDICATE_TYPES,
    OBSERVABILITY_INVARIANTS,
    ObservabilityError,
)
from chiyu_kernel.contract.agent_runtime import (
    AGENT_RUNTIME_INVARIANTS,
    AgentRuntimeError,
    ASSEMBLY_GUARD_NAMES,
    COOLDOWN_VERDICTS,
    COMPLIANCE_DIMENSIONS,
    COMPLIANCE_JOIN_PRIORITY,
    COMPLIANCE_MEMORY_PHASE,
    COMPLIANCE_PENDING,
    COMPLIANCE_SKILL_PHASES,
    COMPLIANCE_SUCCESS_MARKERS,
    DEDUP_EMPTY_SENTINEL,
    DEFAULT_COOLDOWN_MS,
    GLASSBOX_AXIS_DEFAULT,
    GLASSBOX_FIELDS,
    GLASSBOX_NO_SIGNAL_SENTINEL,
    GLASSBOX_TRACE_FIELDS,
    KG_GATE_FIELDS,
    KG_LAYER_ORDER,
    KG_TARGET_UNBOUNDED,
    TRIGGER_ROW_FIELDS,
    TRIGGER_SKIP_REASONS,
    TRIGGER_SOURCES,
    TRIGGER_SOURCE_DEFAULT,
)
# ── 调度复盘判据词汇（Batch-5，2026-10-14）────────────────────────────────────
from chiyu_kernel.contract.scheduler import (
    CATCHUP_MAX_AGE_HOURS,
    CATCHUP_NEAR_SCHEDULE_MS,
    CATCHUP_REASONS,
    CATCHUP_REASON_STALE,
    RETRO_HOUR_DEFAULT,
    SEGMENT_ISOLATION_INVARIANTS,
    SchedulerError,
)
from chiyu_kernel.contract.nightly_report import (
    FAIL_CONFIDENCE_THRESHOLD_DEFAULT,
    NightlyReportError,
    REPORT_INVARIANTS,
    REPORT_SEGMENTS,
    RETRO_METRIC_FIELDS,
    RUBRIC_ITEM_PREFIX,
)
# D3 HITL 断言实现（批次二：「无 approve 不可生效」结构保证入口；E9 同族再导出）
# ⛔ assert_transition 出门面带 Approval 前缀（对齐 DecisionApprovalGate 命名纪律：
#   spine 状态机已有 assert_transition 同名 API，裸名出门面即静默覆盖）。
from chiyu_kernel.approval import (
    HITLEvidenceError,
    ApprovalTransitionError,
    missing_hitl_evidence_fields,
    assert_hitl_evidence,
    assert_transition as assert_approval_transition,
)
# ── 写操作安全闸（八闸框架）+ 第0闸决策凭证（Batch-1a，2026-10-13）────────
# 四分类范式骨架（precheck/permission/redline/traceability）+ 轻量决策凭证；
# 域闸名由消费方注入（CRM 审定 #2：零领域字面量铁律）。
from chiyu_kernel.contract.gate import (
    DECISION_CREDENTIAL_FIELDS, GATE_CHAIN_INVARIANTS, GATE_CLASSES,
    DecisionCredentialError, DecisionRequiredError, GateChainError, GateSpec,
    require_decision_id, verify_decision_credential,
)
from chiyu_kernel.gate import evaluate_chain, gate_write, run_gate_chain
from chiyu_kernel.contract.feedback_loop import (
    CALIBRATION_APPROVED, CALIBRATION_BLOCKED, CALIBRATION_MIN_COVERAGE,
    CALIBRATION_MIN_SAMPLE, CALIBRATION_PENDING, CALIBRATION_STATUSES,
    DEFAULT_AUTO_PASS, DEFAULT_HUMAN_REVIEW, EVAL_VERDICT_KINDS,
    EVAL_VERDICT_PASS, EVAL_VERDICT_REJECT, EVAL_VERDICT_UNDECIDABLE,
    EVAL_VERDICT_REVIEW, FEEDBACK_INVARIANTS, METRIC_SCOPES,
    METRIC_TEMPLATE_FIELDS, METRIC_TEMPLATE_REQUIRED, RUNTIME_SCOPE, SEED_SCOPE,
    CalibrationStateError, ExpressionError, FeedbackTemplateError,
)
# ── L1 feedback：反馈闭环纯函数核心（GAP-6，Batch-2b；落库/事件发射留消费方）─
from chiyu_kernel.feedback import (
    EvalItem, EvaluatorSpec, MetricTemplate, approve_transition,
    assert_template_complete, calibration_stats, evaluate, expression_variables,
    missing_template_keys, prescribe_guard, safe_eval,
)
from chiyu_kernel.contract.capability_audit import (
    AUDIT_PIECE_KEYS, AUDIT_STATUS_DRAFT, AUDIT_STATUS_MISSING, AUDIT_STATUS_OK,
    AUDIT_STATUS_PARTIAL, CAPABILITY_AUDIT_INVARIANTS, CAPABILITY_PRIORITIES,
    CAPABILITY_VERDICTS, NON_CALL_LINE_PREFIXES, PIECE_STATUSES,
    VERDICT_LANDED, VERDICT_MISSING, VERDICT_PARTIAL, CapabilityAuditError,
)
# ── L1 capability_audit：能力落地审计（GAP-7，Batch-2b；三查法 IO 边界在内）──
from chiyu_kernel.capability_audit import (
    CapabilityFinding, assemble_four_piece, build_baseline_diff,
    build_compliance_selfcheck, build_traceability_graph,
    count_production_calls, grade_capability, is_call_line,
    probe_piece_discrimination, record_operator_log, three_check,
)
from chiyu_kernel.contract.connector import (
    CONNECTOR_INVARIANTS, CONNECTOR_NAME_FIELD, CONNECTOR_RESULT_FIELDS,
    FILE_CONNECTOR_FORMATS, ConnectorNotRegisteredError,
)
# ── L1 connectors：连接器传输层（GAP-8，Batch-2b；域连接器留消费方）─────
from chiyu_kernel.connectors import (
    ConnectorRegistry, ConnectorResult, FileConnector, SourceConnector,
    default_registry,
)
from chiyu_kernel.contract.promotion import (
    BLOCKED, DEFAULT_CHANNEL, DEFAULT_MIN_CONSISTENCY, DEFAULT_MIN_EVIDENCE,
    DEFAULT_REFLUX_POLICY, HINDSIGHT_STATUSES, KIND_TO_CHANNEL,
    PARAMS_SOURCE_PROMOTED, PRESCRIPTION_PENDING, PROMOTED, PROMOTION_INVARIANTS,
    PROMOTION_STAGE, PROMOTION_STATUSES, PROTECTED_STAGES, REJECTED,
    REFLUX_CHANNELS, REFLUX_INVARIANTS, REFLUX_KINDS, TRUTH_TOLERANCE,
    WINDOW_STATUSES, PromotionPolicyError, RefluxChannelError,
)
# ── L1 promotion：知识升格 + 回流管道（GAP-9，Batch-2b；处方状态机在 evolution）─
from chiyu_kernel.promotion import (
    audit_drift, build_promotion_payload, default_reflux_policy, deviation,
    deviation_rate, drift_detected, extract_numeric_candidates, kind_to_channel,
    load_json_policy, positive_float, positive_int, promote_gate,
    proposal_channel, promotion_overwrite_guard, reflux_prescribe_guard,
    route_kind, should_prescribe, unit_float, window_status,
)

# ── L0 contract 事件/上下文/向量/LLM/编排契约（GAP-1~5，Batch-2a）──────
# 此前这五个域只有 impl 无 sanctioned contract 面（APS 盘点 §四 GAP-1~5：
# 消费方被迫 import 内部路径）。契约词汇自此经 `chiyu_kernel.contract` 可达。
# ⛔ 与 impl 重名的符号（TASK_STATES / CONTEXT_LAYERS / TIERS /
#    KNOWLEDGE_NEEDS_DEFAULT_DIMS / MIN_SUCCESS_LEN…）仍由 impl 路径导出
#    （契约与 impl 是**同一对象**），此处只导契约独有的新符号 —— 避免门面
#    重复绑定同一名字（Python import 后者静默覆盖前者）。
from chiyu_kernel.contract.event import (
    EVENT_ID_FIELD, EVENT_PAYLOAD_SCHEMA_VERSION, EVENT_PAYLOAD_TYPES,
    EVENT_REQUIRED_FIELDS, EVENT_TYPE_FIELD, PAYLOAD_INVARIANTS, PAYLOAD_LAYERS,
    PUBLISH_INVARIANTS,
)
from chiyu_kernel.contract.context import CONTEXT_INVARIANTS, GAP_KINDS
from chiyu_kernel.contract.vector import (
    EMBEDDING_BACKENDS, EMBEDDING_DIM_INVARIANTS, EMBEDDING_MODEL_STATUS,
    EMBEDDING_NETWORK_ENV, EMBEDDING_RESOLUTION_ORDER,
)
from chiyu_kernel.contract.llm import (
    LLM_CLOUD_SCHEME, LLM_DEFAULT_PARALLEL, LLM_DEFAULT_TIER, LLM_INVARIANTS,
    LLM_RESPONSE_FIELDS, LLM_STORYLINE_POLICY_SOURCES, LLM_TIER_FIELDS,
    LLM_TIERS, TOOL_CALL_FIELDS,
)
from chiyu_kernel.contract.orchestration import (
    AGENT_SPEC_FIELDS, AGENT_SPEC_REQUIRED, ORCHESTRATION_INVARIANTS,
)

# ── 版本与能力出口（N1/R11 + R4 合流：experimental 边界可机检）────────────
from chiyu_kernel.version import (
    API_VERSION,
    CAPABILITIES,
    CONTRACT_VERSION,
    DEPRECATIONS,
    VALID_STATUSES,
    api_version,
    capabilities,
    capability_status,
    contract_version,
    deprecations,
    require_capabilities,
)
# ⛔ N1 `PACKAGE_VERSION` 只作兜底常量导入；门面真正透出的是 `__version__`
#    （动态取已装分发包版本，未装时回退 PACKAGE_VERSION）。
from chiyu_kernel.version import __version__, PACKAGE_VERSION  # noqa: F401

# ── L1 vector：离线向量（零 torch）───────────────────────────────────────
from chiyu_kernel.vector import (
    DEFAULT_MIN_COVERAGE,
    HASH_DIM,
    HASH_PROVIDER,
    InferBackend,
    OnnxRunner,
    OnnxUnavailable,
    CoverageReport,
    artifact_info,
    available as vector_available,
    backend as vector_backend,
    backfill_plan,
    clear_cache,
    compute_coverage,
    config_dim,
    content_hash,
    cosine,
    get_runner,
    hash_signature,
    hash_vector,
    info as vector_info,
    is_available as vector_is_available,
    is_padded_tag,
    resolve as vector_resolve,
    resolve_model_dir,
    stable_stringify,
    tag_for_dim,
)

# ── L0/L1 ontology：粒子运行时 + 写时三钩子 + 受控关系图 ──────────────────
from chiyu_kernel.ontology import (
    BackfillChannel,
    OntologyGraph,
    Particle,
    ensure_embedding,
    ensure_tsvector,
    normalize,
    ontology_sync,
)

# ── L0/L1 context：需求侧编码 + L1–L4 装配 + 三级降级召回 ────────────────
from chiyu_kernel.context import (
    CONTEXT_DIMENSIONS,
    CONTEXT_LAYERS,
    GAP_INSUFFICIENT_EXPERIENCE,
    GAP_LOW_COVERAGE,
    GAP_MISSING_DATA,
    GAP_MISSING_ENTITY,
    GAP_MISSING_GATE,
    GAP_MISSING_HITL,
    KNOWLEDGE_LAYERS,
    KNOWLEDGE_NEEDS_DEFAULT_DIMS,
    LAYER_LABELS_ZH,
    LAYER_NAMES,
    MAX_DATASOURCES,
    MAX_ENTITIES,
    MAX_QUERY_TERMS,
    MAX_REQUIRED_FIELDS,
    MIN_EMBEDDING_COVERAGE,
    MIN_PRECEDENTS,
    TIER_FTS,
    TIER_FTS_VECTOR,
    TIER_NONE,
    TIER_ORDER,
    TIER_VECTOR,
    VTIER_FTS,
    VTIER_FTS_VECTOR,
    VTIER_NONE,
    VTIER_ORDER,
    VTIER_VECTOR,
    AssemblyResult,
    KnowledgeNeed,
    KnowledgeNeeds,
    RecalledItem,
    RetrievalEvidence,
    RetrievalResult,
    SupplyDemandGap,
    SupplyReport,
    assemble,
    build_knowledge_needs,
    check_supply_demand,
    degraded_recall,
    missing_context_dimensions,
    to_supply_layer,
    # T41：记忆召回消费点（记忆网回链 + 双轨 NOTE → 三级降级；打通写了能读）
    RECALL_REFERENCE_PREDICATE,
    RECALL_FRAME_PREDICATE,
    recall_precedents,
    build_memory_recaller,
    # T42：多源 RRF 融合（跨源量纲不同 ⇒ 用名次而非分数）
    RRF_K_DEFAULT,
    rrf_fuse,
)

# ── L0 actions：R1–R6 注册表（机制，非 Action 清单）──────────────────────
from chiyu_kernel.actions import ACTION_MAX, ACTION_MIN, ActionRegistry, ActionSpec

# ── L0/L1 orchestration：任务状态机 + 派发参数 + 智能体注册闸 ──────────────
from chiyu_kernel.orchestration import (
    ALLOWED_TRANSITIONS,
    BLOCK_KINDS,
    DISPATCH_CFG_DEFAULTS,
    DISPATCH_CFG_SECTION,
    FAILURE_LIMIT,
    IDEM_PREFIX,
    MAX_REDO,
    MIN_SUCCESS_LEN,
    SYSTEM_ANCHOR_PREFIX,
    SYSTEM_TASK_KINDS,
    TASK_KINDS,
    TASK_STATES,
    TERMINAL_STATES,
    ZOMBIE_STALE_SECONDS,
    AgentRegistry,
    AgentRegistryError,
    AgentSpec,
    TaskStateError,
    assert_anchor,
    assert_block_kind,
    assert_reset,
    assert_result_ref,
    assert_state,
    assert_transition,
    derive_idem_key,
    dispatch_cfg_report,
    fold_history,
    is_stuck,
    is_terminal,
    nightly_idem_key,
    read_dispatch_cfg,
    summarize,
    system_anchor,
)

# ── L1 orchestration（运行时）：Agent 接口 + AgentLoop（harness 移植）──────
from chiyu_kernel.orchestration.agent_runtime import Agent, LiveAgentRegistry
from chiyu_kernel.orchestration.agent_loop import AgentLoop
from chiyu_kernel.orchestration.loop_guard import LoopGuard, StepVerdict
from chiyu_kernel.orchestration.subagent import SubagentDescriptor, SubagentPool
from chiyu_kernel.orchestration.team import (
    SharedTask, TeamMember, TeamRegistry, TeamSpec,
)

# ── L1 evolution：平台自进化闸（§12 机制层，★ 内核新建）──────────────────
from chiyu_kernel.evolution import (
    BASELINE_FIELD,
    READONLY_PATH_PREFIXES,
    GuardViolation,
    KnobError,
    KnobSpec,
    KnobTable,
    Prescription,
    PrescriptionError,
    ReplayVerdict,
    SkillDraft,
    SkillDraftError,
    apply_atomic,
    assert_not_baseline_skill,
    assert_prescription_transition,
    assert_writable,
    begin_replay,
    classify_change,
    g2_suspend_on_redline,
    is_forbidden_change,
    meta_redline_hits,
    promote,
    roll_back,
    shadow_replay,
    validate_draft,
    ChannelNotReadyError,
    CheckResult,
    ReadinessReport,
    assert_channel_may_open,
    readiness_report,
)

# ── L1 events：进程内事件总线（★ 内核新建）───────────────────────────────
from chiyu_kernel.events import (
    EventBus,
    PublishReport,
    Subscriber,
    counting_subscriber,
    log_subscriber,
    # payload（GAP-1：载荷三层结构校验机制；域契约由消费方登记）
    clear_schemas,
    coerce_payload,
    has_schema,
    payload_schema,
    register_schema,
    validate_payload,
)

# ── L1 audit：SHA-256 链式审计（★ 内核新建）+ 链加固（Batch-1b-2 prov_chain）──
from chiyu_kernel.audit import (
    EMPTY_PLACEHOLDER,
    VerifyResult,
    build_chain,
    canonical,
    chain_hash,
    find_forks,
    seal_chain,
    verify_chain,
    verify_sealed,
    verify_tail,
)

# ── L1 iam：RBAC 判定核 + 常驻授权凭证（Batch-1b-1；别名表/矩阵/凭证存储留消费方）
#    two_phase 令牌三函数经 chiyu_kernel.mcpserver 导出（机制在 iam.two_phase，禁重复导出）
from chiyu_kernel.iam import (
    normalize_role,
    has_role,
    has_any_role,
    permission_allows,
    role_deny_reason,
    grant_covers,
    resolve_active_grant,
    usage_breaker,
    sweep_grant,
)

# ── L1 llm：档位策略（网关属消费方域内容，见 REFERENCE §K 待批项）────────
from chiyu_kernel.llm import (
    DEFAULT_PARALLEL,
    DEFAULT_TIER,
    TIERS,
    is_cloud_endpoint,
    normalize_tier,
    resolve_storyline_policy,
    tier_spec,
)

# ── L1 llm（运行时）：provider 抽象（harness 移植）─────────────────────────
from chiyu_kernel.llm.client import (
    ToolCall, LlmResponse, LlmProvider, StubProvider, DeepSeekProvider, build_provider,
)
from chiyu_kernel.llm.openai_compat import (
    OpenAICompatProvider, Sender, http_sender, parse_tool_calls,
)

# ── L1 harness 原生桥：内核能力暴露为 agent 工具（harness 移植）─────────────
from chiyu_kernel.harness_native_tools import (
    register_native_tools, native_redline_guard,
)

# ── L1 plugins：Phase A「Everything is a Plugin」能力注册表 ─────────────────
from chiyu_kernel.plugins import (
    BUILTIN_PLUGINS,
    DEFAULT_MODE_ID,
    MODE_PRESETS,
    PluginRegistry,
    PluginSpec,
    WorkMode,
    active_plugins,
    disabled_plugins,
    mode_ids,
    register_builtins,
    resolve_work_mode,
)

# ── L1 session：会话日志（harness 移植）───────────────────────────────────
from chiyu_kernel.session import SessionEvent, SessionLog, SessionManager

# ── L1 tools：模型面工具注册 + 守卫管线（harness 移植）────────────────────
from chiyu_kernel.tools import (ToolSpec, ToolRegistry, ToolNotFound, ScopeDenied, GuardDenied)
from chiyu_kernel.tools.fs import SandboxedFs, PathEscapeError, register_fs_tools
from chiyu_kernel.tools.shell import (
    CommandRejected, run_command, TerminalSession, register_shell_tools,
)

# ── L2 skills：技能注册表（harness 移植 · dsh skill 能力吸收）─────────────
from chiyu_kernel.skills import (
    SkillSpec, SkillRegistry, SkillConflict, is_skill_name, load_catalog,
)

# ── L2 plan/todo：计划与待办数据模型（harness 移植 · dsh plan/todo 能力吸收）─
from chiyu_kernel.plan import (
    TodoItem, TodoList, PlanStep, Plan, PlanMode, PlanStateError,
)

# ── L2 mcp：MCP 工具桥（harness 移植 · dsh mcp-client 能力吸收）────────────
from chiyu_kernel.mcp import (
    McpToolDef, McpTransport, InMemoryMcpServer, McpBridge, normalize_mcp_name,
)
# ── L2 hooks：钩子总线（harness 移植 · dsh hook-protocol 能力吸收）──────────
from chiyu_kernel.hooks import HookBus, HookResult, matches
# ── L2 interaction：审批闸门（harness 移植 · dsh interaction 能力吸收）──────
from chiyu_kernel.interaction import ApprovalGate, ApprovalRequest
# ── L2 workflow：声明式编排数据模型（harness 移植 · dsh workflow 能力吸收）─
from chiyu_kernel.workflow import (
    WORKFLOW_STEP_STATES, WorkflowRunId, WorkflowPhase, WorkflowMeta,
    WorkflowStep, WorkflowResult, WorkflowStopReason, WorkflowError,
    is_fatal_workflow_error, WorkflowStateError, Workflow, WorkflowRunner,
    register_workflow_tools, WorkerRun,
)

# ── L2 scenario：可运行场景包（模型 / 存储 / MCP 工具面，双入口共用同一写闸）─
from chiyu_kernel.scenario import (
    LEVEL_IDS, KNOWLEDGE_LAYERS, ScenarioPack, ScenarioPackError,
    ScenarioStep, from_dict as scenario_from_dict,
    ScenarioPackStore, ScenarioPackLockDenied, build_in_memory_server
    as scenario_build_in_memory_server,
)
# ── L0 domain：领域注入 SDK（WS6 关键石；TenantProfile + ActionRegistry + ScenarioPack 统一校验聚合）
from chiyu_kernel.domain import (
    DomainBundle, DomainInjectionError, inject_domain, profile_from_dict,
)
# ── L2 persist：标准 persister + 记忆网 canonical writer（WS2；决策落库机制 + 7 谓词边）
from chiyu_kernel.persist import (
    EVENT_TYPE_DECISION, DecisionRecord, judge_worthiness,
    write_decision_memory_net, PgVectorStorePersister,
    # B 双轨记忆运行时（LOG/NOTE 双轨 + 蒸馏侧两闸）+ F 闭环回流白名单
    DistillReport, InMemoryMemoryLog, InMemoryNoteStore, MemoryLogEntry,
    MemoryLogStore, MemoryNote, NoteStore, PRESCRIBABLE_PREDICATES,
    distill, is_prescribable, note_hash, parse_ts,
    # T40：双轨记忆 PG 落库（复用既有三表，零新增 DDL；memory 毕业批次一）
    EVENT_TYPE_MEMORY_LOG, PgMemoryLogStore, PgNoteStore,
    NOTE_ATTR_CONTENT, NOTE_ATTR_CONTENT_HASH, NOTE_ATTR_EXPLICIT,
    NOTE_ATTR_HORIZON_DAYS, NOTE_ATTR_SOURCE_ENTRY_IDS,
    # T47：R9 方案 A 受控边写原语（graph_edge 唯一落库点；谓词闭集 M∪K fail-fast）
    EdgeWrite, EdgeWriteReport, write_controlled_edges,
)
# ── L2 graph：图存储抽象（WS8；单源双视图只读派生，纯 PG CTE 参考实现）
from chiyu_kernel.graph import (
    DECISION_TIME_BASIS, MAX_TRAVERSAL_HOPS, TIMELINE_SOURCES,
    GraphEdge, TraversalResult, GraphStore,
    InMemoryGraphStore, PgCteGraphStore,
    relation_view, timeline_view, decision_backlinks,
    WRITE_CONTROLLED_EDGES_TOOL, build_graph_write_server,
    make_graph_write_profile, open_graph_write_store,
)
# ── L2 mcpserver：MCP 服务端骨架（WS7；注册守卫 + 零信任鉴权 + 两阶段确认）
from chiyu_kernel.mcpserver import (
    RISKS, McpServerError, ToolNotExposed, AuthDenied, ConfirmRequired,
    ConfirmTokenInvalid, ExposedTool, canonical_args, issue_confirm_token,
    verify_confirm_token, McpServer, StdioTransport, allow_principals,
)
# ── L2 approval：决策脊柱审批闸（WS3；硬约束先于置信度 / A 红线优先）
#    ⛔ 与 L2 interaction.ApprovalGate 不同层（决策落库前裁定 vs 工具执行前人工确认），
#       命名加 Decision 前缀防门面静默覆盖（同 vector_* 前缀纪律）。
from chiyu_kernel.approval import (
    DecisionApprovalGate, DecisionApprovalVerdict, DecisionVerdictState,
    RedlinePriorityGate, DecisionPassThroughGate,
)
# ── 审批聚合裁决核（Batch-1b-2 approval_engine；会签/或签/链签 + 档位解析 fail-closed）
from chiyu_kernel.approval import (
    aggregate,
    chain_for_tier,
    resolve_tier,
)
# ── 决策支撑三机制（Batch-1b-3：冲突仲裁判决核 / 归因分类树 / 四问评分核）────
from chiyu_kernel.conflict_resolver import (
    adopt_verdict,
    detect_conflicts,
    mark_conflict,
    pick_winner,
    resolve_conflict,
)
from chiyu_kernel.attribution import (
    apply_human_disposition,
    apply_outcome,
    classify_root_cause,
    compute_edge_compliance,
    required_edges_for_dims,
)
from chiyu_kernel.audit_4q import (
    aggregate_4q,
    evaluate_4q,
)
# ── 进化四机制（Batch-1b-4：A/B 判据收口 / 配额判决 / 参数健康推荐 / 处方组装）──
from chiyu_kernel.ab_experiment import (
    JUDGE_CFG_DEFAULTS,
    apply_arm,
    close_decision,
    judge_arms,
)
from chiyu_kernel.quota_gate import judge_quota
from chiyu_kernel.param_health_check import (
    recommend_prescription,
    split_red_line,
)
from chiyu_kernel.evolution.assemble import assemble_prescription
# ── 监控底座 + agent 运行时判据核（Batch-4：纯函数，零 DB 零总线）─────────────
from chiyu_kernel.observability import (
    FailureCounter,
    accuracy_bucket,
    aggregate_enrichment,
    aggregate_gate_metrics,
    blocks_export_gate,
    classify_attribution,
    classify_negative_predicates,
    compute_enrichment_rate,
    delivery_success_rate,
    edge_caliber_count,
    is_demo_edge_source,
    is_runtime_edge_source,
    runtime_edges_only,
    split_edges_by_caliber,
)
from chiyu_kernel.agent_runtime import (
    build_glass_box,
    cooldown_verdict,
    dedup_key_for,
    join_keys_of,
    judge_contract,
    kg_convergence_gate,
    l3_degraded_guard,
    match_trigger,
    resolve_runtime_layers,
)
# ── 调度复盘判据核（Batch-5：纯函数判决 + 零 LLM 渲染；IO 留消费方）────────────
from chiyu_kernel.scheduler_core import (
    catchup_verdict,
    next_run_at,
    run_segments,
)
from chiyu_kernel.nightly_report import (
    aggregate_report_metrics,
    collect_segments,
    extract_retro_metrics,
    format_patch,
    render_nightly_markdown,
)
# ── L2 canary：决策落库三判据统一判定式（N7；判据口径收归基座，消费方只注接线）
from chiyu_kernel.canary import CanaryReport, canary_probe  # noqa: F401
# ── L2 scenario：决策场景注册表（WS5 单一事实源；全局可变，未注册键首调抛 ValueError）
from chiyu_kernel.scenario.registry import (
    ScenarioRegistryError, DecisionIOField, IO_KINDS, GATE_KINDS,
    DecisionScenarioProfile, register_scenario,
    get_scenario, require_scenario, list_scenarios, is_registered,
    clear_registry, set_key_format, key_format,
)

# memory 毕业声明（T44，2026-10-10 转 stable）：False = 已进入 1.0 兼容承诺。
# 该标志保留为机器可检出口（R4），历史消费方判 True 的分支须随毕业同步更新。
MEMORY_EXPERIMENTAL = False

# evolution 毕业声明（T78，2026-10-13 转 stable）：False = 已进入 1.0 兼容承诺。
# 验收 = readiness 十闸全绿（§12.3 七闸 + §12.4 G1/G2/G3，10/10 含对抗判别力）。
# 对齐 MEMORY_EXPERIMENTAL 形态：保留机器可检出口，历史消费方判 True 的分支
# 须随毕业同步更新（⛔ 外部表述不再需要声明实验态）。
EVOLUTION_EXPERIMENTAL = False

__all__ = [
    # 错误 taxonomy（KernelError 单一事实源 + 闭集码表）
    "KernelError", "KERNEL_ERROR_CODES",
    # contract（门面只透出消费方构造 profile 所需的最小面）
    "TenantProfile",
    # store
    "PgVectorStore", "ddl_statements", "vector_index_ddl",
    "assert_no_free_jsonb", "created_schemas", "close_schema", "pad_to_dim",
    "vec_to_pg", "open_store",
    # store 整族 sanctioned 面（机械推导自 store.__all__，见守卫测试）
    "DB_TESTING_ENV", "DSN_ENV", "DSN_TEST_ENV", "FORBIDDEN_HOSTS",
    "FORBIDDEN_ROLES", "IDENT_MAX", "SCHEMA_ENV", "TESTING_FLAG_ENV",
    "VALID_FORMS",
    "DBConfigError", "assert_no_hard_delete", "assert_safe_identifier",
    "close_all", "connect", "cursor", "driver_available", "driver_error",
    "drop_ephemeral_schemas", "drop_test_schema", "ensure_schema",
    "ephemeral_schemas", "get_dsn", "get_schema", "in_testing_context",
    "make_cursor", "mask_dsn", "parse_dsn", "pg_to_vec",
    "probe_schema_isolation", "raw_dsn", "register_ephemeral", "shared",
    "validate_dsn",
    # conn R9：驱动解耦 + 两条硬知识
    "BACKEND_APP_NAME_PREFIX", "DEFAULT_LOCK_TIMEOUT_MS",
    "own_backend_identity", "terminate_backends_sql", "terminate_own_backends",
    # N5：L0 决策契约常量进 sanctioned 面
    "SPINE_ORDER", "validate_spine_order", "RUBRIC_KEYS", "RUBRIC_SCALE_MAX",
    "EIGHT_ELEMENTS", "AUTONOMOUS_RELEASE_DEFAULT", "AUDIT_RECORD_KIND",
    "AUDIT_EVENT_APPROVAL_PENDING", "AUDIT_EVENT_APPROVAL_REJECTED",
    "AUDIT_EVENT_APPROVAL_RESUMED",
    # 三支柱批次一（D1-D4，2026-10-13）：结局采集 + 三档安全 + HITL/resume 证据
    "OUTCOME_KINDS", "OUTCOME_REQUIRED_FIELDS",
    "OUTCOME_CONFIDENCE_DIRECTION", "validate_outcome_kind",
    "SECURITY_MODES", "SECURITY_MODE_DEFAULT", "SECURITY_MODE_INVARIANTS",
    "HITL_EVIDENCE_FIELDS", "APPROVAL_CORE_STATES", "APPROVAL_TRANSITIONS",
    "RESUME_EVIDENCE_FIELDS",
    # 三支柱批次二（D5-D7 + CRM 修订，2026-10-13）：度量/判定接口/审计合一
    "HITL_RESUME_FIELD_ALIASES", "APPROVAL_TRANSITION_EXTENSION_RULE",
    # Batch-1b-2 approval_engine 契约 + prov_chain 链加固契约
    "APPROVAL_AGGREGATION_MODES", "APPROVAL_TIERS",
    "APPROVAL_ENGINE_INVARIANTS", "ApprovalEngineError",
    "CHAIN_VERIFY_STATUSES", "CHAIN_SEAL_FIELDS", "PROV_CHAIN_INVARIANTS",
    # Batch-1b-3 决策支撑契约（冲突仲裁/归因规则/四问可审计性）
    "CONFLICT_STRATEGIES", "CONFLICT_INVARIANTS", "ConflictStrategyError",
    "ATTRIBUTION_CATEGORIES", "ROOT_CAUSE_LAYERS", "HUMAN_DISPOSITIONS",
    "ATTRIBUTION_INVARIANTS", "AttributionError",
    "AUDIT4Q_KEYS", "AUDIT4Q_STATUSES", "Q1_MIN_SUPPLIED_DIMS",
    "AUDIT4Q_INVARIANTS", "Audit4QError",
    # Batch-1b-4 进化契约（A/B 实验收口/配额闸/参数健康/处方组装）
    "AB_ARMS", "AB_VERDICTS", "AB_Q_EPS_DEFAULT", "AB_O_EPS_DEFAULT",
    "AB_R_EPS_DEFAULT", "AB_MIN_ARM_SAMPLE_DEFAULT", "AB_INVARIANTS",
    "AbExperimentError",
    "QUOTA_MODES", "QUOTA_MODE_UNLIMITED", "QUOTA_UNLIMITED_SENTINEL",
    "BILL_HARDCAP_MULTIPLIER", "QUOTA_VERDICTS", "QUOTA_DENY_REASONS",
    "QUOTA_INVARIANTS", "QuotaGateError",
    "PARAM_RISK_LEVELS", "RECOMMEND_OUTCOMES", "HIGH_RISK_FAIL_RATE",
    "RECOMMEND_INVARIANTS", "ParamHealthError",
    "ASSEMBLE_AUTO_KNOBS", "ASSEMBLE_EXPECTED_IMPACT_FIELDS",
    "ASSEMBLE_INVARIANTS", "AssembleError",
    # Batch-4a 监控底座契约 + 机制（归因交叉/accuracy 桶/闸门聚合/负向判据/边双口径/失败计数）
    "ATTRIBUTION_CROSS_CATEGORIES", "ATTRIBUTION_BENIGN",
    "ACCURACY_BUCKETS", "ACCURACY_ACCURATE_FROM", "ACCURACY_INACCURATE_FROM",
    "GATE_METRIC_STATES", "NEGATIVE_PREDICATE_TYPES", "EXPORT_GATE_BLOCKING_TYPES",
    "DEMO_EDGE_SOURCES_DEFAULT", "EDGE_CALIBER_KEYS", "ENRICHMENT_FIELDS",
    "FAILURE_COUNTER_RETURN_KEYS", "OBSERVABILITY_INVARIANTS", "ObservabilityError",
    "classify_attribution", "accuracy_bucket", "aggregate_gate_metrics",
    "delivery_success_rate", "classify_negative_predicates",
    "compute_enrichment_rate", "aggregate_enrichment",
    "is_demo_edge_source", "is_runtime_edge_source", "split_edges_by_caliber",
    "edge_caliber_count", "runtime_edges_only", "FailureCounter", "blocks_export_gate",
    # Batch-4b agent 运行时契约 + 机制（三源触发/只读白名单/glassBox/合规三维/KG 收敛）
    "TRIGGER_SOURCES", "TRIGGER_SOURCE_DEFAULT", "TRIGGER_ROW_FIELDS",
    "DEDUP_EMPTY_SENTINEL", "DEFAULT_COOLDOWN_MS", "COOLDOWN_VERDICTS",
    "TRIGGER_SKIP_REASONS", "GLASSBOX_FIELDS", "GLASSBOX_TRACE_FIELDS",
    "GLASSBOX_AXIS_DEFAULT", "GLASSBOX_NO_SIGNAL_SENTINEL",
    "COMPLIANCE_DIMENSIONS", "COMPLIANCE_PENDING", "COMPLIANCE_SUCCESS_MARKERS",
    "COMPLIANCE_JOIN_PRIORITY", "COMPLIANCE_SKILL_PHASES", "COMPLIANCE_MEMORY_PHASE",
    "KG_LAYER_ORDER", "KG_GATE_FIELDS", "KG_TARGET_UNBOUNDED",
    "ASSEMBLY_GUARD_NAMES", "AGENT_RUNTIME_INVARIANTS", "AgentRuntimeError",
    "match_trigger", "dedup_key_for", "cooldown_verdict", "build_glass_box",
    "join_keys_of", "judge_contract", "kg_convergence_gate",
    "l3_degraded_guard", "resolve_runtime_layers",
    # Batch-5 调度复盘契约 + 机制（判决核/段隔离/零 LLM 渲染）
    "RETRO_HOUR_DEFAULT", "CATCHUP_MAX_AGE_HOURS", "CATCHUP_NEAR_SCHEDULE_MS",
    "CATCHUP_REASONS", "CATCHUP_REASON_STALE",
    "SEGMENT_ISOLATION_INVARIANTS", "SchedulerError",
    "REPORT_SEGMENTS", "RETRO_METRIC_FIELDS", "FAIL_CONFIDENCE_THRESHOLD_DEFAULT",
    "RUBRIC_ITEM_PREFIX", "REPORT_INVARIANTS", "NightlyReportError",
    "next_run_at", "catchup_verdict", "run_segments",
    "collect_segments", "extract_retro_metrics", "format_patch",
    "aggregate_report_metrics", "render_nightly_markdown",
    "SCORECARD_FIELDS", "METRIC_SUMMARY_FIELDS", "AGGREGATE_METRIC_KEYS",
    "HONEST_DEGRADATION_INVARIANTS", "ScoreCard", "MetricSummary",
    "PRINCIPAL_FIELDS", "SECURITY_DECISION_EXTENSION_RULE", "SECURITY_DECISION_FIELDS",
    "Principal", "SecurityDecision", "RoleGate",
    "RBAC_INVARIANTS", "RBAC_DENY_REASONS",
    "STANDING_GRANT_STATUSES", "PAUSE_REASONS", "GRANT_VERDICTS",
    "CREDENTIAL_INVARIANTS", "TWO_PHASE_INVARIANTS",
    # iam 机制（Batch-1b-1：rbac_core 判定核 + standing_credential 判决核；纯函数 fail-closed）
    "normalize_role", "has_role", "has_any_role", "permission_allows",
    "role_deny_reason",
    "grant_covers", "resolve_active_grant", "usage_breaker", "sweep_grant",
    "AUDIT_CANONICAL_SCHEMA", "AUDIT_CHAIN_RULE",
    "AUDIT_TOMBSTONE_FIELD", "AUDIT_TOMBSTONE_REASON_FIELD",
    "AUDIT_TOMBSTONE_INVARIANTS",
    # 三支柱批次二 D3 实现：HITL 断言（无 approve 不可生效，结构保证）
    "HITLEvidenceError", "ApprovalTransitionError",
    "missing_hitl_evidence_fields", "assert_hitl_evidence",
    "assert_approval_transition",
    # gate（Batch-1a：八闸框架 + 第0闸决策凭证，去重收口）
    "GATE_CLASSES", "GATE_CHAIN_INVARIANTS", "DECISION_CREDENTIAL_FIELDS",
    "DecisionRequiredError", "DecisionCredentialError", "GateChainError",
    "require_decision_id", "verify_decision_credential", "GateSpec",
    "gate_write", "run_gate_chain", "evaluate_chain",
    # contract GAP-1~5（Batch-2a：事件/上下文/向量/LLM/编排契约面；
    # 与 impl 重名符号由 impl 路径导出，同一对象，不在此重复列）
    "EVENT_ID_FIELD", "EVENT_TYPE_FIELD", "EVENT_REQUIRED_FIELDS",
    "PAYLOAD_LAYERS", "EVENT_PAYLOAD_SCHEMA_VERSION", "EVENT_PAYLOAD_TYPES",
    "PUBLISH_INVARIANTS", "PAYLOAD_INVARIANTS",
    "CONTEXT_INVARIANTS", "GAP_KINDS",
    "EMBEDDING_BACKENDS", "EMBEDDING_RESOLUTION_ORDER", "EMBEDDING_MODEL_STATUS",
    "EMBEDDING_NETWORK_ENV", "EMBEDDING_DIM_INVARIANTS",
    "LLM_TIERS", "LLM_DEFAULT_TIER", "LLM_DEFAULT_PARALLEL", "LLM_TIER_FIELDS",
    "TOOL_CALL_FIELDS", "LLM_RESPONSE_FIELDS", "LLM_STORYLINE_POLICY_SOURCES",
    "LLM_CLOUD_SCHEME", "LLM_INVARIANTS",
    "AGENT_SPEC_FIELDS", "AGENT_SPEC_REQUIRED", "ORCHESTRATION_INVARIANTS",
    # feedback_loop（GAP-6：反馈闭环契约 + 纯函数机制，Batch-2b）
    "METRIC_TEMPLATE_FIELDS", "METRIC_TEMPLATE_REQUIRED", "METRIC_SCOPES",
    "RUNTIME_SCOPE", "SEED_SCOPE", "EVAL_VERDICT_KINDS", "EVAL_VERDICT_PASS",
    "EVAL_VERDICT_REVIEW", "EVAL_VERDICT_REJECT", "EVAL_VERDICT_UNDECIDABLE",
    "CALIBRATION_STATUSES", "CALIBRATION_PENDING", "CALIBRATION_APPROVED",
    "CALIBRATION_BLOCKED", "CALIBRATION_MIN_SAMPLE", "CALIBRATION_MIN_COVERAGE",
    "DEFAULT_AUTO_PASS", "DEFAULT_HUMAN_REVIEW", "FEEDBACK_INVARIANTS",
    "FeedbackTemplateError", "CalibrationStateError", "ExpressionError",
    "MetricTemplate", "assert_template_complete", "missing_template_keys",
    "EvalItem", "EvaluatorSpec", "evaluate", "expression_variables", "safe_eval",
    "prescribe_guard", "approve_transition", "calibration_stats",
    # capability_audit（GAP-7：能力落地审计契约 + 三查法机制，Batch-2b）
    "CAPABILITY_VERDICTS", "VERDICT_LANDED", "VERDICT_PARTIAL", "VERDICT_MISSING",
    "CAPABILITY_PRIORITIES", "AUDIT_PIECE_KEYS", "PIECE_STATUSES",
    "NON_CALL_LINE_PREFIXES", "AUDIT_STATUS_DRAFT", "AUDIT_STATUS_OK",
    "AUDIT_STATUS_PARTIAL", "AUDIT_STATUS_MISSING",
    "CAPABILITY_AUDIT_INVARIANTS", "CapabilityAuditError",
    "three_check", "is_call_line", "count_production_calls", "grade_capability",
    "CapabilityFinding", "record_operator_log", "build_baseline_diff",
    "build_traceability_graph", "build_compliance_selfcheck",
    "probe_piece_discrimination", "assemble_four_piece",
    # connector（GAP-8：连接器传输层契约 + 机制，Batch-2b）
    "CONNECTOR_RESULT_FIELDS", "CONNECTOR_NAME_FIELD", "FILE_CONNECTOR_FORMATS",
    "CONNECTOR_INVARIANTS", "ConnectorNotRegisteredError",
    "ConnectorResult", "SourceConnector", "FileConnector",
    "ConnectorRegistry", "default_registry",
    # promotion（GAP-9：知识升格 + 回流管道契约 + 机制，Batch-2b）
    "PROMOTION_STATUSES", "PROMOTED", "BLOCKED", "REJECTED",
    "PROMOTION_STAGE", "PARAMS_SOURCE_PROMOTED", "PROTECTED_STAGES",
    "DEFAULT_MIN_EVIDENCE", "DEFAULT_MIN_CONSISTENCY", "TRUTH_TOLERANCE",
    "PROMOTION_INVARIANTS",
    "REFLUX_CHANNELS", "REFLUX_KINDS", "KIND_TO_CHANNEL", "DEFAULT_CHANNEL",
    "PRESCRIPTION_PENDING", "DEFAULT_REFLUX_POLICY", "REFLUX_INVARIANTS",
    "HINDSIGHT_STATUSES", "WINDOW_STATUSES",
    "RefluxChannelError", "PromotionPolicyError",
    "promote_gate", "extract_numeric_candidates", "drift_detected",
    "audit_drift", "promotion_overwrite_guard", "build_promotion_payload",
    "kind_to_channel", "route_kind", "proposal_channel", "reflux_prescribe_guard",
    "default_reflux_policy", "deviation", "should_prescribe", "window_status",
    "deviation_rate", "load_json_policy", "positive_int", "positive_float",
    "unit_float",
    # events payload（GAP-1：载荷三层结构校验机制，域契约消费方自登记）
    "register_schema", "has_schema", "payload_schema", "clear_schemas",
    "validate_payload", "coerce_payload",
    "ELEMENT_MISSING_CAP", "ELEMENT_RUBRIC_CAPS",
    # vector
    "CoverageReport", "compute_coverage", "backfill_plan",
    "DEFAULT_MIN_COVERAGE", "HASH_PROVIDER", "HASH_DIM",
    "InferBackend", "cosine", "hash_signature", "stable_stringify",
    "content_hash", "hash_vector",
    "OnnxRunner", "OnnxUnavailable", "artifact_info", "clear_cache",
    "config_dim", "get_runner", "resolve_model_dir",
    "vector_available", "vector_backend", "vector_info", "vector_is_available",
    "vector_resolve", "is_padded_tag", "tag_for_dim",
    # ontology
    "Particle", "OntologyGraph", "normalize",
    "ensure_embedding", "ensure_tsvector", "ontology_sync", "BackfillChannel",
    # context
    "CONTEXT_LAYERS", "KnowledgeNeed", "SupplyReport", "AssemblyResult",
    "assemble", "LAYER_LABELS_ZH", "KNOWLEDGE_NEEDS_DEFAULT_DIMS",
    "KNOWLEDGE_LAYERS", "LAYER_NAMES", "KnowledgeNeeds", "SupplyDemandGap",
    "build_knowledge_needs", "check_supply_demand", "missing_context_dimensions",
    "MAX_ENTITIES", "MAX_DATASOURCES", "MAX_REQUIRED_FIELDS", "MAX_QUERY_TERMS",
    "MIN_PRECEDENTS", "MIN_EMBEDDING_COVERAGE", "CONTEXT_DIMENSIONS",
    "GAP_MISSING_ENTITY", "GAP_INSUFFICIENT_EXPERIENCE", "GAP_LOW_COVERAGE",
    "GAP_MISSING_DATA", "GAP_MISSING_HITL", "GAP_MISSING_GATE",
    "VTIER_FTS_VECTOR", "VTIER_VECTOR", "VTIER_FTS", "VTIER_NONE", "VTIER_ORDER",
    "TIER_FTS_VECTOR", "TIER_VECTOR", "TIER_FTS", "TIER_NONE", "TIER_ORDER",
    "RecalledItem", "RetrievalEvidence", "RetrievalResult",
    "degraded_recall", "to_supply_layer",
    # context/T41：记忆召回消费点（记忆网回链 + 双轨 NOTE 两源 → 三级降级）
    "RECALL_REFERENCE_PREDICATE", "RECALL_FRAME_PREDICATE",
    "recall_precedents", "build_memory_recaller",
    # context/T42：多源 RRF 融合（跨源量纲不同 ⇒ 用名次而非分数）
    "RRF_K_DEFAULT", "rrf_fuse",
    # actions
    "ActionSpec", "ActionRegistry", "ACTION_MIN", "ACTION_MAX",
    # orchestration
    "MIN_SUCCESS_LEN", "AgentRegistry", "AgentRegistryError", "AgentSpec",
    "TASK_STATES", "TERMINAL_STATES", "BLOCK_KINDS", "TASK_KINDS",
    "SYSTEM_TASK_KINDS", "FAILURE_LIMIT", "MAX_REDO", "ZOMBIE_STALE_SECONDS",
    "SYSTEM_ANCHOR_PREFIX", "ALLOWED_TRANSITIONS", "TaskStateError",
    "is_terminal", "assert_state", "assert_block_kind", "assert_transition",
    "assert_reset", "assert_anchor", "system_anchor", "assert_result_ref",
    "fold_history", "is_stuck", "summarize",
    "DISPATCH_CFG_SECTION", "DISPATCH_CFG_DEFAULTS", "read_dispatch_cfg",
    "dispatch_cfg_report",
    "IDEM_PREFIX", "derive_idem_key", "nightly_idem_key",
    # orchestration runtime
    "Agent", "LiveAgentRegistry", "AgentLoop", "LoopGuard", "StepVerdict",
    # ⛔ 以下 6 项此前**已 import 却未登记 __all__**（2026-10-09 机械比对发现）：
    #   门面 import 了但没导出 ⇒ 消费方 `from api import X` 不可用、只能摸内部路径
    #   （与 R8 四符号同族缺陷）。由 tests/test_facade_import_vs_all.py 机械守住。
    "SharedTask", "SubagentDescriptor", "SubagentPool",
    "TeamMember", "TeamRegistry", "TeamSpec",
    # evolution
    "KnobError", "KnobSpec", "KnobTable", "classify_change",
    "is_forbidden_change",
    "ReplayVerdict", "shadow_replay", "BASELINE_FIELD",
    "PrescriptionError", "Prescription", "assert_prescription_transition",
    "begin_replay", "apply_atomic", "roll_back",
    "GuardViolation", "READONLY_PATH_PREFIXES", "assert_writable",
    "assert_not_baseline_skill", "g2_suspend_on_redline", "meta_redline_hits",
    "SkillDraftError", "SkillDraft", "validate_draft", "promote",
    "ChannelNotReadyError", "ReadinessReport", "assert_channel_may_open",
    "readiness_report", "CheckResult",
    # events
    "EventBus", "PublishReport", "Subscriber",
    "counting_subscriber", "log_subscriber",
    # audit
    "canonical", "chain_hash", "build_chain", "verify_chain", "VerifyResult",
    "EMPTY_PLACEHOLDER",
    # prov_chain 链加固（Batch-1b-2：seal / 增量续链 / 分叉检出）
    "seal_chain", "verify_sealed", "verify_tail", "find_forks",
    # llm
    "TIERS", "DEFAULT_TIER", "DEFAULT_PARALLEL", "normalize_tier",
    "is_cloud_endpoint", "resolve_storyline_policy", "tier_spec",
    # llm client（同族漏出：已 import 未登记；StubProvider 是消费方离线联调必需）
    "ToolCall", "LlmResponse", "LlmProvider", "StubProvider",
    "DeepSeekProvider", "build_provider",
    # llm openai 兼容 provider（T93 上迁：enterprise 实现收敛，禁两套 HTTP 逻辑）
    "OpenAICompatProvider", "Sender", "http_sender", "parse_tool_calls",
    # session
    "SessionEvent", "SessionLog", "SessionManager",
    # tools
    "ToolSpec", "ToolRegistry", "ToolNotFound", "ScopeDenied", "GuardDenied",
    "SandboxedFs", "PathEscapeError", "register_fs_tools",
    "CommandRejected", "run_command", "TerminalSession", "register_shell_tools",
    # skills
    "SkillSpec", "SkillRegistry", "SkillConflict", "is_skill_name", "load_catalog",
    # plan/todo
    "TodoItem", "TodoList", "PlanStep", "Plan", "PlanMode", "PlanStateError",
    # mcp bridge
    "McpToolDef", "McpTransport", "InMemoryMcpServer", "McpBridge", "normalize_mcp_name",
    # hooks bus
    "HookBus", "HookResult", "matches",
    # interaction / approval
    "ApprovalGate", "ApprovalRequest",
    # workflow（声明式编排数据模型）
    "WORKFLOW_STEP_STATES", "WorkflowRunId", "WorkflowPhase", "WorkflowMeta",
    "WorkflowStep", "WorkflowResult", "WorkflowStopReason", "WorkflowError",
    "is_fatal_workflow_error", "WorkflowStateError", "Workflow", "WorkflowRunner",
    "register_workflow_tools", "WorkerRun",
    # scenario（可运行场景包；from_dict→scenario_from_dict、
    # build_in_memory_server→scenario_build_in_memory_server，防语义不明裸名。
    # KNOWLEDGE_LAYERS 与 context 层同形同值，门面不重复登记）
    "LEVEL_IDS", "ScenarioPack", "ScenarioPackError",
    "ScenarioStep", "scenario_from_dict", "ScenarioPackStore",
    "ScenarioPackLockDenied", "scenario_build_in_memory_server",
    # scenario 决策场景注册表（WS5：单一事实源；键格式闸可插拨 set_key_format，
    # 支持跨语言消费方命名族共存——2026-10-09 双方核验更正：「根治 CRM 三态键分裂」
    # 表述作废：config_change ≢ config-change，语义不同必须共存；全局可变，未注册
    # 键首调抛 ValueError）
    "ScenarioRegistryError", "DecisionScenarioProfile", "register_scenario",
    "DecisionIOField", "IO_KINDS", "GATE_KINDS",
    "get_scenario", "require_scenario", "list_scenarios", "is_registered",
    "clear_registry", "set_key_format", "key_format",
    # domain（领域注入 SDK；profile_from_dict/inject_domain 是 L4 域内容进入内核的
    # 统一校验闸，机制非清单）
    "DomainBundle", "DomainInjectionError", "profile_from_dict", "inject_domain",
    # persist（标准 persister：SpineResult→event/particle/记忆网 映射 shim；机制非清单）
    "EVENT_TYPE_DECISION", "DecisionRecord", "judge_worthiness",
    "write_decision_memory_net", "PgVectorStorePersister",
    # persist/B 双轨记忆运行时（LOG append-only + notes upsert + 蒸馏两闸）+ F 白名单
    "DistillReport", "InMemoryMemoryLog", "InMemoryNoteStore", "MemoryLogEntry",
    "MemoryLogStore", "MemoryNote", "NoteStore", "PRESCRIBABLE_PREDICATES",
    "distill", "is_prescribable", "note_hash", "parse_ts",
    # persist/T40：双轨记忆 PG 落库（LOG→event 追加、NOTE→particle+attribute 幂等 upsert）
    "EVENT_TYPE_MEMORY_LOG", "PgMemoryLogStore", "PgNoteStore",
    "NOTE_ATTR_CONTENT", "NOTE_ATTR_CONTENT_HASH", "NOTE_ATTR_EXPLICIT",
    "NOTE_ATTR_HORIZON_DAYS", "NOTE_ATTR_SOURCE_ENTRY_IDS",
    # persist/T47：R9 方案 A 受控边写原语（graph_edge 唯一落库点；谓词闭集 M∪K）
    "EdgeWrite", "EdgeWriteReport", "write_controlled_edges",
    # graph（图存储抽象：单源双视图只读派生；协议禁写方法）
    "DECISION_TIME_BASIS", "MAX_TRAVERSAL_HOPS", "TIMELINE_SOURCES",
    "GraphEdge", "TraversalResult", "GraphStore",
    "InMemoryGraphStore", "PgCteGraphStore",
    "relation_view", "timeline_view", "decision_backlinks",
    "WRITE_CONTROLLED_EDGES_TOOL", "build_graph_write_server",
    "make_graph_write_profile", "open_graph_write_store",
    # mcpserver（MCP 服务端：注册守卫 + 默认拒绝鉴权 + 写操作两阶段确认）
    "RISKS", "McpServerError", "ToolNotExposed", "AuthDenied", "ConfirmRequired",
    "ConfirmTokenInvalid", "ExposedTool", "canonical_args",
    "issue_confirm_token", "verify_confirm_token", "McpServer",
    "StdioTransport", "allow_principals",
    # canary（N7 探针件：决策落库三判据的统一判定式，foundation 单一事实源）
    "CanaryReport", "canary_probe",
    # approval（决策脊柱审批闸 / WS3+B3 三态；与 interaction.ApprovalGate 不同层，命名加 Decision 前缀防静默覆盖）
    "DecisionVerdictState", "DecisionApprovalGate", "DecisionApprovalVerdict",
    "RedlinePriorityGate", "DecisionPassThroughGate",
    # approval_engine 聚合裁决核（Batch-1b-2）
    "resolve_tier", "chain_for_tier", "aggregate",
    # 决策支撑三机制（Batch-1b-3：冲突仲裁/归因/四问；纯函数证据注入）
    "detect_conflicts", "mark_conflict", "pick_winner", "adopt_verdict",
    "resolve_conflict",
    "classify_root_cause", "apply_human_disposition", "apply_outcome",
    "compute_edge_compliance", "required_edges_for_dims",
    "evaluate_4q", "aggregate_4q",
    # 进化四机制（Batch-1b-4：纯函数判据核；重放/红线前缀/豁免名单注入）
    "JUDGE_CFG_DEFAULTS",
    "judge_arms", "apply_arm", "close_decision",
    "judge_quota",
    "recommend_prescription", "split_red_line",
    "assemble_prescription",
    # store 注册表观测/测试面（enterprise 增补建议采纳）
    "registered_store_schemas", "reset_store_registry",
    # harness native bridge
    "register_native_tools", "native_redline_guard",
    # plugins
    "PluginSpec", "PluginRegistry", "BUILTIN_PLUGINS", "register_builtins",
    "WorkMode", "MODE_PRESETS", "DEFAULT_MODE_ID",
    "mode_ids", "active_plugins", "disabled_plugins", "resolve_work_mode",
    # 状态透出
    "MEMORY_EXPERIMENTAL", "EVOLUTION_EXPERIMENTAL",
    # N1/R11 版本与能力出口（消费方可用版本断言替代 hasattr 嗅探）
    "API_VERSION", "CONTRACT_VERSION", "CAPABILITIES", "DEPRECATIONS",
    "VALID_STATUSES", "api_version", "capabilities", "capability_status",
    "require_capabilities",
    "contract_version", "deprecations",
    # N1：分发包版本（消费方可版本钉 + 构建期断言），与 pyproject 一致由测试守
    "__version__", "PACKAGE_VERSION",
]

# ⛔ 五处 `vector` 符号在门面加 `vector_` 前缀（`available`→`vector_available`、
#   `backend`→`vector_backend`、`info`→`vector_info`、`resolve`→`vector_resolve`、
#   `is_available`→`vector_is_available`）。理由是**读性与防静默覆盖**，不是避让
#   现有冲突：门面是唯一公共命名空间，裸名 `resolve`/`info` 在消费方代码里语义
#   不明（"解析什么"）；而门面一旦出现两个同名符号，后者会**静默**覆盖前者
#   （Python 的 import 不报错），与"禁静默中间态"同族。前缀把该风险前置消除。
#   守卫 `test_api_facade_covers_all_layers.py` 用显式改名表核对这 5 个名字。

# ⛔ schema 感知单例（Batch-2a，2026-10-14；enterprise 盘点 §七.3 报的根因）：
#   此前的单例条件只比对 profile 身份（`_store.profile is not profile`），
#   同一 profile 第二次传不同 schema 时 **schema 参数被静默忽略**，返回第一个
#   store ⇒ 进程内多租户共用一个 store 指向同一 schema（串库）。enterprise
#   `tenant/store.py` 自建 (profile,schema) 双键注册表正是在绕开这个缺陷 ——
#   修在这里，消费方即可删副本（去重，非保留第二事实源）。
#   键含 id(profile)：store 持有 profile 引用 ⇒ 已入键的 profile 不会被 GC、
#   id 不会被复用（安全）；同一目标只开一个门面（单实例纪律不变）。
_stores: Dict[Tuple[int, str], PgVectorStore] = {}


def open_store(profile: TenantProfile, schema: str = "") -> PgVectorStore:
    """进程级单例（按 (profile, schema) 键控；单实例 + 跨进程锁纪律不变）。

    ⛔ `schema=""` ⇒ 由 env `CHIYU_DB_SCHEMA` 决定，内核**不提供**默认域 schema
       （demo 的 `bj` 是该域取值，焊进内核即单域化）。
    ⛔ 键必须含 schema：只按 profile 键控会让第二次调用的 schema 被静默忽略
       （进程内多租户串库；enterprise 双键注册表的根因，判据见
       tests/test_open_store_schema_isolation.py）。
    """
    resolved = assert_safe_identifier(schema or get_schema(), what="schema")
    key = (id(profile), resolved)
    store = _stores.get(key)
    if store is None:
        store = PgVectorStore(profile=profile, schema=resolved)
        _stores[key] = store
    return store


def registered_store_schemas() -> Tuple[str, ...]:
    """已键控 store 的 schema 快照（enterprise 增补建议采纳，2026-10-14）。

    ⛔ 观测面：仅用于展示/测试断言；**禁用于隔离裁决**——隔离判据恒以
    open_store 实测为准（同键单实例/异 schema 异实例，判据见
    tests/test_open_store_schema_isolation.py）。
    """
    return tuple(sorted({schema for _, schema in _stores}))


def reset_store_registry() -> None:
    """清空 store 注册表（仅测试消费；生产禁用）。

    既有实例对象**不关闭**（实例由底座键控持有，调用方须自行确保无在用句柄）；
    清空后同键重取仍经 open_store 单实例路径重建。
    """
    _stores.clear()
