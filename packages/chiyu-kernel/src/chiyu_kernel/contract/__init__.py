"""L0 契约层 —— 单一事实源。

⛔ 本层零第三方依赖（除 dataclasses）、零 IO、零领域字面量。
   消费方**只许** import 本层与 `chiyu_kernel.api`，import 内部实现即违约
   （守卫见 tests/test_app_imports_contract_only.py，T2 建）。

⚠ 本模块为**纯 re-export**（无类定义），故 `tools/check_cython_friendly.py` 的
   C4「契约须静态声明」对其豁免——C4 的靶子是"用运行时手段造类"，不是"汇总导出"。
"""
from .audit import (
    AUDIT_CANONICAL_SCHEMA,
    AUDIT_CHAIN_RULE,
    AUDIT_GENESIS_HASH,
    AUDIT_HASH_ALGO,
    AUDIT_REQUIRED_FIELDS,
    AUDIT_TOMBSTONE_FIELD,
    AUDIT_TOMBSTONE_INVARIANTS,
    AUDIT_TOMBSTONE_REASON_FIELD,
    CHAIN_SEAL_FIELDS,
    CHAIN_VERIFY_STATUSES,
    PROBE_ASSERTIONS,
    PROV_CHAIN_INVARIANTS,
)
from .decision import (
    AUDIT_APPROVAL_EVENTS,
    AUDIT_EVENT_APPROVAL_PENDING,
    AUDIT_EVENT_APPROVAL_REJECTED,
    AUDIT_EVENT_APPROVAL_RESUMED,
    AUDIT_RECORD_KIND,
    AUTONOMOUS_GATE_EXPR,
    AUTONOMOUS_RELEASE_DEFAULT,
    CONFIDENCE_SOURCE_KEY,
    EIGHT_ELEMENTS,
    EIGHT_ELEMENTS_ZH,
    ELEMENT_MISSING_CAP,
    ELEMENT_RUBRIC_CAPS,
    RUBRIC_KEYS,
    RUBRIC_LLM_ELIGIBLE,
    RUBRIC_NAMES_ZH,
    RUBRIC_SCALE_MAX,
    RUBRIC_THRESHOLDS_DEFAULT,
    SEVEN_DIM_KEYS,
    SEVEN_DIMS,
    SPINE_ORDER,
    SPINE_STAGE_LABELS_ZH,
    validate_spine_order,
)
from .evolution import (
    ASSEMBLE_AUTO_KNOBS,
    ASSEMBLE_EXPECTED_IMPACT_FIELDS,
    ASSEMBLE_INVARIANTS,
    AssembleError,
    BASELINE_SKILL_PREFIX,
    DIR_FLAT,
    DIR_TIGHTEN,
    DIR_WIDEN,
    DIRECTIONS,
    EVOLUTION_OBJECTS,
    FAIL_SAFE_VERDICT,
    META_REDLINES,
    PRESCRIPTION_AUDIT_FIELDS,
    PRESCRIPTION_STATES,
    PRESCRIPTION_TERMINAL,
    PRESCRIPTION_TRANSITIONS,
    RISK_TIERS,
    TIER_AUTO,
    TIER_FORBIDDEN,
    TIER_GUARDED,
    VERDICT_PASS,
    VERDICT_REJECT,
    VERDICTS,
)
from .memory import (
    BUSINESS_CLOCK_FIELD,
    MEMORY_ADDRESS_KEYS,
    MEMORY_DEFAULTS,
    MEMORY_KINDS,
    PROVENANCE_SOURCES,
    RECORD_CLOCK_FIELD,
)
# ── metrics：有效性度量契约（三支柱批次二 D5，2026-10-13）────────────────
# 跨仓统计口径统一最小面 + 诚实降级结构保证（未评不掩盖为绿）。
from .metrics import (  # noqa: F401
    AGGREGATE_METRIC_KEYS, HONEST_DEGRADATION_INVARIANTS, MetricSummary,
    METRIC_SUMMARY_FIELDS, SCORECARD_FIELDS, ScoreCard,
)
# ── iam：IAM/RBAC 判定接口 + RBAC 判定核（三支柱批次二 D7 + Batch-1b-1）────
# 收判定接口（Principal/SecurityDecision/RoleGate）与 RBAC 判定核算法；
# 角色矩阵内容/别名表内容/租户档清单留消费方注入。
from .iam import (  # noqa: F401
    PRINCIPAL_FIELDS, Principal, RoleGate, SECURITY_DECISION_EXTENSION_RULE,
    SECURITY_DECISION_FIELDS, SecurityDecision,
    RBAC_INVARIANTS, RBAC_DENY_REASONS,
    STANDING_GRANT_STATUSES, PAUSE_REASONS, GRANT_VERDICTS,
    CREDENTIAL_INVARIANTS, TWO_PHASE_INVARIANTS,
)
from .particle import (
    ATTR_SOURCES,
    ATTR_TYPES,
    CARDINALITIES,
    CORE_ROLES,
    EDGE_LAYERS,
    EDGE_SOURCES,
    HASH_DIM,
    LAYERS,
    MEMORY_PREDICATES,
    ParticleTypeSet,
    PredicateSet,
    PredicateSpec,
    VALUE_SLOTS,
    VECTOR_DIM,
)
from .profile import RedlineSpec, TenantProfile
# ── outcome：结局采集契约（三支柱批次一 D1，2026-10-13）──────────────────
# 决策→执行→结局→复盘 闭环的第一环；只收枚举机制不收域值（CRM Q1.4 边界）。
from .outcome import (  # noqa: F401
    OUTCOME_CONFIDENCE_DIRECTION, OUTCOME_KINDS, OUTCOME_REQUIRED_FIELDS,
    validate_outcome_kind,
)
# ── gate：写操作安全闸（八闸框架）+ 第0闸决策凭证（Batch-1a，2026-10-13）──
# 四分类范式骨架 + 轻量决策凭证；域闸名由消费方注入（零领域字面量铁律）。
from .gate import (  # noqa: F401
    DECISION_CREDENTIAL_FIELDS, GATE_CHAIN_INVARIANTS, GATE_CLASSES,
    DecisionCredentialError, DecisionRequiredError, GateChainError, GateSpec,
    require_decision_id, verify_decision_credential,
)
# ── event：事件必填面 + 载荷三层词汇（GAP-1，Batch-2a，2026-10-14）──────
# 进程内事件总线/载荷校验的词汇单一事实源；域事件契约由消费方登记。
from .event import (  # noqa: F401
    EVENT_ID_FIELD, EVENT_PAYLOAD_SCHEMA_VERSION, EVENT_PAYLOAD_TYPES,
    EVENT_REQUIRED_FIELDS, EVENT_TYPE_FIELD, PAYLOAD_INVARIANTS, PAYLOAD_LAYERS,
    PUBLISH_INVARIANTS,
)
# ── context：四层模型/七维/缺口类型/降级档位（GAP-2，Batch-2a）──────────
# 上下文装配词汇单一事实源；impl 同名符号即本层对象（无双份漂移）。
from .context import (  # noqa: F401
    CONTEXT_DIMENSIONS, CONTEXT_INVARIANTS, CONTEXT_LAYER_LABELS_ZH,
    CONTEXT_LAYERS, GAP_INSUFFICIENT_EXPERIENCE, GAP_KINDS, GAP_LOW_COVERAGE,
    GAP_MISSING_DATA, GAP_MISSING_ENTITY, GAP_MISSING_GATE, GAP_MISSING_HITL,
    KNOWLEDGE_LAYERS, KNOWLEDGE_NEEDS_DEFAULT_DIMS, MAX_DATASOURCES,
    MAX_ENTITIES, MAX_QUERY_TERMS, MAX_REQUIRED_FIELDS, MIN_EMBEDDING_COVERAGE,
    MIN_PRECEDENTS, TIER_FTS, TIER_FTS_VECTOR, TIER_NONE, TIER_ORDER,
    TIER_VECTOR, VTIER_FTS, VTIER_FTS_VECTOR, VTIER_NONE, VTIER_ORDER,
    VTIER_VECTOR,
)
# ── vector：推理后端闭集/解析顺序/维度纪律（GAP-3，Batch-2a）────────────
# HASH_DIM/VECTOR_DIM 已由 .particle 导出（同一对象），此处不重复绑定。
from .vector import (  # noqa: F401
    EMBEDDING_BACKENDS, EMBEDDING_DIM_INVARIANTS, EMBEDDING_MODEL_STATUS,
    EMBEDDING_NETWORK_ENV, EMBEDDING_RESOLUTION_ORDER,
)
# ── llm：档位闭集/provider 字段面/故事线策略口径（GAP-4，Batch-2a）─────
# 档位数值表留 llm/tier.py（零项目 import 硬约束），漂移由 parity 守卫对拍。
from .llm import (  # noqa: F401
    LLM_CLOUD_SCHEME, LLM_DEFAULT_PARALLEL, LLM_DEFAULT_TIER, LLM_INVARIANTS,
    LLM_RESPONSE_FIELDS, LLM_STORYLINE_POLICY_SOURCES, LLM_TIER_FIELDS,
    LLM_TIERS, TOOL_CALL_FIELDS,
)
# ── orchestration：任务状态机词汇/Agent 契约字段面（GAP-5，Batch-2a）────
# 状态集/转换表/参数上收本层；校验与投影逻辑留 orchestration impl。
from .orchestration import (  # noqa: F401
    AGENT_SPEC_FIELDS, AGENT_SPEC_REQUIRED, ALLOWED_TRANSITIONS, BLOCK_KINDS,
    FAILURE_LIMIT, MAX_REDO, MIN_SUCCESS_LEN, ORCHESTRATION_INVARIANTS,
    SYSTEM_ANCHOR_PREFIX, SYSTEM_TASK_KINDS, TASK_KINDS, TASK_STATES,
    TERMINAL_STATES, ZOMBIE_STALE_SECONDS,
)
# ── feedback_loop：反馈闭环契约（GAP-6，Batch-2b，2026-10-14）───────────
# 指标模板要素面/双口径观测/三档评估/拒绝出方守卫/HITL 校准闸的词汇与不变式；
# 机制层（chiyu_kernel.feedback）为纯函数，落库与事件发射留消费方。
from .feedback_loop import (  # noqa: F401
    CALIBRATION_APPROVED, CALIBRATION_BLOCKED, CALIBRATION_MIN_COVERAGE,
    CALIBRATION_MIN_SAMPLE, CALIBRATION_PENDING, CALIBRATION_STATUSES,
    DEFAULT_AUTO_PASS, DEFAULT_HUMAN_REVIEW, EVAL_VERDICT_KINDS,
    EVAL_VERDICT_PASS, EVAL_VERDICT_REJECT, EVAL_VERDICT_UNDECIDABLE,
    EVAL_VERDICT_REVIEW, FEEDBACK_INVARIANTS, METRIC_SCOPES,
    METRIC_TEMPLATE_FIELDS, METRIC_TEMPLATE_REQUIRED, RUNTIME_SCOPE, SEED_SCOPE,
    CalibrationStateError, ExpressionError, FeedbackTemplateError,
)
# ── capability_audit：能力落地审计契约（GAP-7，Batch-2b，2026-10-14）─────
# 三查法判定次序/调用点计数纪律/分级词汇/四件套装配的词汇与不变式；
# 文件遍历（IO）在机制层，域能力映射由消费方注入。
from .capability_audit import (  # noqa: F401
    AUDIT_PIECE_KEYS, AUDIT_STATUS_DRAFT, AUDIT_STATUS_MISSING, AUDIT_STATUS_OK,
    AUDIT_STATUS_PARTIAL, CAPABILITY_AUDIT_INVARIANTS, CAPABILITY_PRIORITIES,
    CAPABILITY_VERDICTS, NON_CALL_LINE_PREFIXES, PIECE_STATUSES,
    VERDICT_LANDED, VERDICT_MISSING, VERDICT_PARTIAL, CapabilityAuditError,
)
# ── connector：连接器传输层契约（GAP-8，Batch-2b，2026-10-14）──────────
# 无状态工厂接口/结果载体/文件传输格式/注册表纪律的词汇与不变式；
# 域连接器（如 APS legacy_aps）与 DB·消息传输留消费方。
from .connector import (  # noqa: F401
    CONNECTOR_INVARIANTS, CONNECTOR_NAME_FIELD, CONNECTOR_RESULT_FIELDS,
    FILE_CONNECTOR_FORMATS, ConnectorNotRegisteredError,
)
# ── promotion：知识升格 + 回流管道契约（GAP-9，Batch-2b，2026-10-14）────
# 升格三态闸门/产物形态红线/覆盖守卫/漂移判定/回流四通道/后见之明判据的
# 词汇与不变式；处方状态机单一事实源在 evolution，域键白名单留消费方。
from .promotion import (  # noqa: F401
    BLOCKED, DEFAULT_CHANNEL, DEFAULT_MIN_CONSISTENCY, DEFAULT_MIN_EVIDENCE,
    DEFAULT_REFLUX_POLICY, HINDSIGHT_STATUSES, KIND_TO_CHANNEL, PARAMS_SOURCE_PROMOTED,
    PRESCRIPTION_PENDING, PROMOTED, PROMOTION_INVARIANTS, PROMOTION_STAGE,
    PROMOTION_STATUSES, PROTECTED_STAGES, REJECTED, REFLUX_CHANNELS, REFLUX_INVARIANTS,
    REFLUX_KINDS, TRUTH_TOLERANCE, WINDOW_STATUSES, PromotionPolicyError,
    RefluxChannelError,
)

# ── Batch-1b-3：冲突仲裁 + 归因规则 + 四问可审计性（2026-10-14）────────────
# 上迁自 CRM conflict.js G4 / attribution.js T29+rootCauseClassifier R0-R3 /
# auditability.js 四问；判据算法与口径常量在基座，证据与域词表留消费方。
from .conflict_resolver import (  # noqa: F401
    CONFLICT_INVARIANTS, CONFLICT_STRATEGIES, ConflictStrategyError,
)
from .attribution import (  # noqa: F401
    ATTRIBUTION_CATEGORIES, ATTRIBUTION_INVARIANTS, AttributionError,
    HUMAN_DISPOSITIONS, ROOT_CAUSE_LAYERS,
)
from .audit_4q import (  # noqa: F401
    AUDIT4Q_INVARIANTS, AUDIT4Q_KEYS, AUDIT4Q_STATUSES, Audit4QError,
    Q1_MIN_SUPPLIED_DIMS,
)
# ── Batch-1b-4：A/B 实验收口 + Token 配额闸 + 参数健康诊断（2026-10-14）────
# 上迁自 CRM routingReview.js 三取二判据 / quotaGate.js 判决核 / diagnosis.js
# recommend 三档；阈值常量在基座（口径永不漂移），场景/轨道/红线前缀/豁免名单留消费方。
from .ab_experiment import (  # noqa: F401
    AB_ARMS, AB_VERDICTS, AB_Q_EPS_DEFAULT, AB_O_EPS_DEFAULT, AB_R_EPS_DEFAULT,
    AB_MIN_ARM_SAMPLE_DEFAULT, AB_INVARIANTS, AbExperimentError,
)
from .quota import (  # noqa: F401
    BILL_HARDCAP_MULTIPLIER, QUOTA_DENY_REASONS, QUOTA_INVARIANTS,
    QUOTA_MODE_UNLIMITED, QUOTA_MODES, QUOTA_UNLIMITED_SENTINEL,
    QUOTA_VERDICTS, QuotaGateError,
)
from .param_health import (  # noqa: F401
    HIGH_RISK_FAIL_RATE, PARAM_RISK_LEVELS, RECOMMEND_INVARIANTS,
    RECOMMEND_OUTCOMES, ParamHealthError,
)
# ── Batch-4：监控底座 + agent 运行时判据词汇（2026-10-14）────────────────────
# 上收自 CRM monitor/*（归因四类/accuracy 三态/闸门聚合/负向判据两级/边双口径）
# 与 agent/*（三源触发/只读白名单/glassBox/契约合规三维/KG 收敛）；
# 渠道名/闸门名/agent 名/skill 白名单/矩阵行域值/KG 服务层集合由消费方注入。
from .observability import (  # noqa: F401
    ACCURACY_ACCURATE_FROM, ACCURACY_BUCKETS, ACCURACY_INACCURATE_FROM,
    ATTRIBUTION_BENIGN, ATTRIBUTION_CROSS_CATEGORIES, DEMO_EDGE_SOURCES_DEFAULT,
    EDGE_CALIBER_KEYS, ENRICHMENT_FIELDS, EXPORT_GATE_BLOCKING_TYPES,
    FAILURE_COUNTER_RETURN_KEYS, GATE_METRIC_STATES, NEGATIVE_PREDICATE_TYPES,
    OBSERVABILITY_INVARIANTS, ObservabilityError,
)
from .agent_runtime import (  # noqa: F401
    AGENT_RUNTIME_INVARIANTS, AgentRuntimeError, ASSEMBLY_GUARD_NAMES,
    COOLDOWN_VERDICTS, COMPLIANCE_DIMENSIONS, COMPLIANCE_JOIN_PRIORITY,
    COMPLIANCE_MEMORY_PHASE, COMPLIANCE_PENDING, COMPLIANCE_SKILL_PHASES,
    COMPLIANCE_SUCCESS_MARKERS, DEDUP_EMPTY_SENTINEL, DEFAULT_COOLDOWN_MS,
    GLASSBOX_AXIS_DEFAULT, GLASSBOX_FIELDS, GLASSBOX_NO_SIGNAL_SENTINEL,
    GLASSBOX_TRACE_FIELDS, KG_GATE_FIELDS, KG_LAYER_ORDER, KG_TARGET_UNBOUNDED,
    TRIGGER_ROW_FIELDS, TRIGGER_SOURCES, TRIGGER_SKIP_REASONS,
    TRIGGER_SOURCE_DEFAULT,
)
# ── Batch-5：调度复盘判据词汇（2026-10-14）────────────────────────────────────
# 上收自 CRM scheduler/timers.js（nextRetroAt/catchUp 三态/段隔离范式）与
# report/nightlyReport.js（三段容错/双形态指标/零 LLM 渲染）；
# 任务名/时区/报告标题/落盘路径由消费方注入。
from .scheduler import (  # noqa: F401
    CATCHUP_MAX_AGE_HOURS, CATCHUP_NEAR_SCHEDULE_MS, CATCHUP_REASONS,
    CATCHUP_REASON_STALE, RETRO_HOUR_DEFAULT, SchedulerError,
    SEGMENT_ISOLATION_INVARIANTS,
)
from .nightly_report import (  # noqa: F401
    FAIL_CONFIDENCE_THRESHOLD_DEFAULT, NightlyReportError, REPORT_INVARIANTS,
    REPORT_SEGMENTS, RETRO_METRIC_FIELDS, RUBRIC_ITEM_PREFIX,
)
# ── security：三档安全模式 + HITL 证据 + resume 证据（三支柱批次一 D2-D4）──
# APS security.py 形态升格基座默认；HITL 闸基座结构保证（三仓一致 P0）。
from .security import (  # noqa: F401
    APPROVAL_CORE_STATES, APPROVAL_TRANSITIONS, APPROVAL_TRANSITION_EXTENSION_RULE,
    APPROVAL_AGGREGATION_MODES, APPROVAL_TIERS, APPROVAL_ENGINE_INVARIANTS,
    ApprovalEngineError,
    HITL_EVIDENCE_FIELDS, HITL_RESUME_FIELD_ALIASES, RESUME_EVIDENCE_FIELDS,
    SECURITY_MODE_DEFAULT, SECURITY_MODE_INVARIANTS, SECURITY_MODES,
)
# ── L2 approval：决策脊柱审批闸（WS3+B3 三态）──────────────────────────────
# ⛔ E9（2026-10-13，APS 增补 RFE）：approval 是 foundation sanctioned 面，
#   但消费方（APS）纪律限定 import 仅 {chiyu_decision.api, chiyu_kernel.contract}，
#   被迫直连 chiyu_kernel.approval 内部模块 ⇒ 破口同型 AUDIT_RECORD_KIND（T61）。
#   故在 L0 契约面再导出审批闸符号，使消费方经 sanctioned 面即可达。
#   环安全：approval 不反向依赖 contract/api（grep 实证），纯再导出零行为变更。
# ⛔ 批次二（2026-10-13）：hitl 断言再导出（E9 同族）——assert_hitl_evidence /
#   assert_transition 是「无 approve 不可生效」的基座结构保证入口；APS/CRM 纪律面
#   contract-only，若无此再导出则消费方被迫摸 approval 内部路径（破口同型 T61）。
#   assert_transition 出门面带 Approval 前缀（DecisionApprovalGate 同纪律：
#   spine 状态机既有同名 API，裸名出门面即静默覆盖）。
from chiyu_kernel.approval import (  # noqa: F401
    ApprovalTransitionError, DecisionApprovalGate, DecisionApprovalVerdict,
    DecisionVerdictState, HITLEvidenceError, RedlinePriorityGate,
    DecisionPassThroughGate, assert_hitl_evidence,
    assert_transition as assert_approval_transition,
    missing_hitl_evidence_fields,
)

__all__ = [
    # audit
    "AUDIT_GENESIS_HASH", "AUDIT_HASH_ALGO", "AUDIT_REQUIRED_FIELDS",
    "PROBE_ASSERTIONS",
    # audit D6（三支柱批次二：canonical schema + 墓碑语义）
    "AUDIT_CANONICAL_SCHEMA", "AUDIT_CHAIN_RULE",
    "AUDIT_TOMBSTONE_FIELD", "AUDIT_TOMBSTONE_REASON_FIELD",
    "AUDIT_TOMBSTONE_INVARIANTS",
    # audit D6+ 链加固（Batch-1b-2 prov_chain）
    "CHAIN_VERIFY_STATUSES", "CHAIN_SEAL_FIELDS", "PROV_CHAIN_INVARIANTS",
    # decision
    "AUDIT_APPROVAL_EVENTS",
    "AUDIT_EVENT_APPROVAL_PENDING", "AUDIT_EVENT_APPROVAL_REJECTED",
    "AUDIT_EVENT_APPROVAL_RESUMED", "AUDIT_RECORD_KIND",
    "AUTONOMOUS_GATE_EXPR", "AUTONOMOUS_RELEASE_DEFAULT", "CONFIDENCE_SOURCE_KEY",
    "ELEMENT_MISSING_CAP", "ELEMENT_RUBRIC_CAPS",
    "EIGHT_ELEMENTS", "EIGHT_ELEMENTS_ZH", "RUBRIC_KEYS", "RUBRIC_LLM_ELIGIBLE",
    "RUBRIC_NAMES_ZH", "RUBRIC_SCALE_MAX", "RUBRIC_THRESHOLDS_DEFAULT",
    "SEVEN_DIM_KEYS", "SEVEN_DIMS", "SPINE_ORDER", "SPINE_STAGE_LABELS_ZH",
    "validate_spine_order",
    # evolution
    "EVOLUTION_OBJECTS", "RISK_TIERS", "TIER_AUTO", "TIER_GUARDED", "TIER_FORBIDDEN",
    "DIRECTIONS", "DIR_WIDEN", "DIR_TIGHTEN", "DIR_FLAT",
    "PRESCRIPTION_STATES", "PRESCRIPTION_TERMINAL", "PRESCRIPTION_TRANSITIONS",
    "META_REDLINES", "BASELINE_SKILL_PREFIX",
    "VERDICT_PASS", "VERDICT_REJECT", "VERDICTS", "FAIL_SAFE_VERDICT",
    "PRESCRIPTION_AUDIT_FIELDS",
    # memory
    "BUSINESS_CLOCK_FIELD", "MEMORY_ADDRESS_KEYS", "MEMORY_DEFAULTS",
    "MEMORY_KINDS", "PROVENANCE_SOURCES", "RECORD_CLOCK_FIELD",
    # particle
    "ATTR_SOURCES", "ATTR_TYPES", "CARDINALITIES", "CORE_ROLES", "EDGE_LAYERS",
    "EDGE_SOURCES", "HASH_DIM", "LAYERS", "MEMORY_PREDICATES",
    "ParticleTypeSet", "PredicateSet", "PredicateSpec", "VALUE_SLOTS", "VECTOR_DIM",
    # profile
    "RedlineSpec", "TenantProfile",
    # approval（决策脊柱审批闸 / WS3+B3 三态；E9：经 L0 契约面再导出，消费方免摸内部路径）
    "DecisionVerdictState", "DecisionApprovalGate", "DecisionApprovalVerdict",
    "RedlinePriorityGate", "DecisionPassThroughGate",
    # approval hitl 断言（三支柱批次二 D3 实现：无 approve 不可生效，结构保证）
    "HITLEvidenceError", "ApprovalTransitionError",
    "missing_hitl_evidence_fields", "assert_hitl_evidence",
    "assert_approval_transition",
    # outcome（三支柱批次一 D1：结局采集契约，闭环第一环）
    "OUTCOME_KINDS", "OUTCOME_REQUIRED_FIELDS",
    "OUTCOME_CONFIDENCE_DIRECTION", "validate_outcome_kind",
    # gate（Batch-1a：八闸框架 + 第0闸决策凭证）
    "GATE_CLASSES", "GATE_CHAIN_INVARIANTS", "DECISION_CREDENTIAL_FIELDS",
    "DecisionRequiredError", "DecisionCredentialError", "GateChainError",
    "require_decision_id", "verify_decision_credential", "GateSpec",
    # event（GAP-1：事件必填面 + 载荷三层词汇，Batch-2a）
    "EVENT_ID_FIELD", "EVENT_TYPE_FIELD", "EVENT_REQUIRED_FIELDS",
    "PAYLOAD_LAYERS", "EVENT_PAYLOAD_SCHEMA_VERSION", "EVENT_PAYLOAD_TYPES",
    "PUBLISH_INVARIANTS", "PAYLOAD_INVARIANTS",
    # context（GAP-2：四层模型/七维/缺口类型/降级档位，Batch-2a）
    "CONTEXT_LAYERS", "CONTEXT_LAYER_LABELS_ZH", "KNOWLEDGE_LAYERS",
    "KNOWLEDGE_NEEDS_DEFAULT_DIMS", "CONTEXT_DIMENSIONS", "CONTEXT_INVARIANTS",
    "MAX_ENTITIES", "MAX_DATASOURCES", "MAX_REQUIRED_FIELDS", "MAX_QUERY_TERMS",
    "MIN_PRECEDENTS", "MIN_EMBEDDING_COVERAGE",
    "GAP_MISSING_ENTITY", "GAP_INSUFFICIENT_EXPERIENCE", "GAP_LOW_COVERAGE",
    "GAP_MISSING_DATA", "GAP_MISSING_HITL", "GAP_MISSING_GATE", "GAP_KINDS",
    "VTIER_FTS_VECTOR", "VTIER_VECTOR", "VTIER_FTS", "VTIER_NONE", "VTIER_ORDER",
    "TIER_FTS_VECTOR", "TIER_VECTOR", "TIER_FTS", "TIER_NONE", "TIER_ORDER",
    # vector（GAP-3：推理后端闭集/解析顺序/维度纪律，Batch-2a）
    "EMBEDDING_BACKENDS", "EMBEDDING_RESOLUTION_ORDER", "EMBEDDING_MODEL_STATUS",
    "EMBEDDING_NETWORK_ENV", "EMBEDDING_DIM_INVARIANTS",
    # llm（GAP-4：档位闭集/provider 字段面/故事线策略口径，Batch-2a）
    "LLM_TIERS", "LLM_DEFAULT_TIER", "LLM_DEFAULT_PARALLEL", "LLM_TIER_FIELDS",
    "TOOL_CALL_FIELDS", "LLM_RESPONSE_FIELDS", "LLM_STORYLINE_POLICY_SOURCES",
    "LLM_CLOUD_SCHEME", "LLM_INVARIANTS",
    # orchestration（GAP-5：任务状态机词汇/Agent 契约字段面，Batch-2a）
    "TASK_STATES", "TERMINAL_STATES", "BLOCK_KINDS", "TASK_KINDS",
    "SYSTEM_TASK_KINDS", "FAILURE_LIMIT", "MAX_REDO", "ZOMBIE_STALE_SECONDS",
    "SYSTEM_ANCHOR_PREFIX", "ALLOWED_TRANSITIONS",
    "AGENT_SPEC_FIELDS", "AGENT_SPEC_REQUIRED", "MIN_SUCCESS_LEN",
    "ORCHESTRATION_INVARIANTS",
    # feedback_loop（GAP-6：反馈闭环契约，Batch-2b）
    "METRIC_TEMPLATE_FIELDS", "METRIC_TEMPLATE_REQUIRED", "METRIC_SCOPES",
    "RUNTIME_SCOPE", "SEED_SCOPE", "EVAL_VERDICT_KINDS", "EVAL_VERDICT_PASS",
    "EVAL_VERDICT_REVIEW", "EVAL_VERDICT_REJECT", "EVAL_VERDICT_UNDECIDABLE",
    "CALIBRATION_STATUSES", "CALIBRATION_PENDING", "CALIBRATION_APPROVED",
    "CALIBRATION_BLOCKED", "CALIBRATION_MIN_SAMPLE", "CALIBRATION_MIN_COVERAGE",
    "DEFAULT_AUTO_PASS", "DEFAULT_HUMAN_REVIEW", "FEEDBACK_INVARIANTS",
    "FeedbackTemplateError", "CalibrationStateError", "ExpressionError",
    # capability_audit（GAP-7：能力落地审计契约，Batch-2b）
    "CAPABILITY_VERDICTS", "VERDICT_LANDED", "VERDICT_PARTIAL", "VERDICT_MISSING",
    "CAPABILITY_PRIORITIES", "AUDIT_PIECE_KEYS", "PIECE_STATUSES",
    "NON_CALL_LINE_PREFIXES", "AUDIT_STATUS_DRAFT", "AUDIT_STATUS_OK",
    "AUDIT_STATUS_PARTIAL", "AUDIT_STATUS_MISSING",
    "CAPABILITY_AUDIT_INVARIANTS", "CapabilityAuditError",
    # connector（GAP-8：连接器传输层契约，Batch-2b）
    "CONNECTOR_RESULT_FIELDS", "CONNECTOR_NAME_FIELD", "FILE_CONNECTOR_FORMATS",
    "CONNECTOR_INVARIANTS", "ConnectorNotRegisteredError",
    # promotion（GAP-9：知识升格 + 回流管道契约，Batch-2b）
    "PROMOTION_STATUSES", "PROMOTED", "BLOCKED", "REJECTED",
    "PROMOTION_STAGE", "PARAMS_SOURCE_PROMOTED", "PROTECTED_STAGES",
    "DEFAULT_MIN_EVIDENCE", "DEFAULT_MIN_CONSISTENCY", "TRUTH_TOLERANCE",
    "PROMOTION_INVARIANTS",
    "REFLUX_CHANNELS", "REFLUX_KINDS", "KIND_TO_CHANNEL", "DEFAULT_CHANNEL",
    "PRESCRIPTION_PENDING", "DEFAULT_REFLUX_POLICY", "REFLUX_INVARIANTS",
    "HINDSIGHT_STATUSES", "WINDOW_STATUSES",
    "RefluxChannelError", "PromotionPolicyError",
    # security（三支柱批次一 D2-D4：三档模式 + HITL 证据 + resume 证据）
    "SECURITY_MODES", "SECURITY_MODE_DEFAULT", "SECURITY_MODE_INVARIANTS",
    "HITL_EVIDENCE_FIELDS", "APPROVAL_CORE_STATES", "APPROVAL_TRANSITIONS",
    "RESUME_EVIDENCE_FIELDS",
    # security CRM 评审修订（T75 回执：别名映射 + 域扩展机制）
    "HITL_RESUME_FIELD_ALIASES", "APPROVAL_TRANSITION_EXTENSION_RULE",
    # security Batch-1b-2（approval_engine 聚合裁决核词汇）
    "APPROVAL_AGGREGATION_MODES", "APPROVAL_TIERS",
    "APPROVAL_ENGINE_INVARIANTS", "ApprovalEngineError",
    # metrics（三支柱批次二 D5：有效性度量 + 诚实降级）
    "SCORECARD_FIELDS", "METRIC_SUMMARY_FIELDS", "AGGREGATE_METRIC_KEYS",
    "HONEST_DEGRADATION_INVARIANTS", "ScoreCard", "MetricSummary",
    # iam（三支柱批次二 D7 判定接口 + Batch-1b-1 RBAC 判定核）
    "PRINCIPAL_FIELDS", "SECURITY_DECISION_EXTENSION_RULE", "SECURITY_DECISION_FIELDS",
    "Principal", "SecurityDecision", "RoleGate",
    "RBAC_INVARIANTS", "RBAC_DENY_REASONS",
    "STANDING_GRANT_STATUSES", "PAUSE_REASONS", "GRANT_VERDICTS",
    "CREDENTIAL_INVARIANTS", "TWO_PHASE_INVARIANTS",
    # Batch-1b-3：冲突仲裁 + 归因规则 + 四问可审计性
    "CONFLICT_STRATEGIES", "CONFLICT_INVARIANTS", "ConflictStrategyError",
    "ATTRIBUTION_CATEGORIES", "ROOT_CAUSE_LAYERS", "HUMAN_DISPOSITIONS",
    "ATTRIBUTION_INVARIANTS", "AttributionError",
    "AUDIT4Q_KEYS", "AUDIT4Q_STATUSES", "Q1_MIN_SUPPLIED_DIMS",
    "AUDIT4Q_INVARIANTS", "Audit4QError",
    # Batch-1b-4：A/B 实验收口 + 配额闸 + 参数健康诊断 + 处方组装
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
    # Batch-4a：监控底座判据词汇
    "ATTRIBUTION_CROSS_CATEGORIES", "ATTRIBUTION_BENIGN",
    "ACCURACY_BUCKETS", "ACCURACY_ACCURATE_FROM", "ACCURACY_INACCURATE_FROM",
    "GATE_METRIC_STATES", "NEGATIVE_PREDICATE_TYPES", "EXPORT_GATE_BLOCKING_TYPES",
    "DEMO_EDGE_SOURCES_DEFAULT", "EDGE_CALIBER_KEYS", "ENRICHMENT_FIELDS",
    "FAILURE_COUNTER_RETURN_KEYS", "OBSERVABILITY_INVARIANTS", "ObservabilityError",
    # Batch-4b：agent 运行时判据词汇
    "TRIGGER_SOURCES", "TRIGGER_SOURCE_DEFAULT", "TRIGGER_ROW_FIELDS",
    "DEDUP_EMPTY_SENTINEL", "DEFAULT_COOLDOWN_MS", "COOLDOWN_VERDICTS",
    "TRIGGER_SKIP_REASONS", "GLASSBOX_FIELDS", "GLASSBOX_TRACE_FIELDS",
    "GLASSBOX_AXIS_DEFAULT", "GLASSBOX_NO_SIGNAL_SENTINEL",
    "COMPLIANCE_DIMENSIONS", "COMPLIANCE_PENDING", "COMPLIANCE_SUCCESS_MARKERS",
    "COMPLIANCE_JOIN_PRIORITY", "COMPLIANCE_SKILL_PHASES", "COMPLIANCE_MEMORY_PHASE",
    "KG_LAYER_ORDER", "KG_GATE_FIELDS", "KG_TARGET_UNBOUNDED",
    "ASSEMBLY_GUARD_NAMES", "AGENT_RUNTIME_INVARIANTS", "AgentRuntimeError",
    # Batch-5：调度复盘判据词汇
    "RETRO_HOUR_DEFAULT", "CATCHUP_MAX_AGE_HOURS", "CATCHUP_NEAR_SCHEDULE_MS",
    "CATCHUP_REASONS", "CATCHUP_REASON_STALE",
    "SEGMENT_ISOLATION_INVARIANTS", "SchedulerError",
    "REPORT_SEGMENTS", "RETRO_METRIC_FIELDS", "FAIL_CONFIDENCE_THRESHOLD_DEFAULT",
    "RUBRIC_ITEM_PREFIX", "REPORT_INVARIANTS", "NightlyReportError",
]
