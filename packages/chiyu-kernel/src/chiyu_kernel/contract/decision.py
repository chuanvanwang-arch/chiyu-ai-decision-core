"""决策脊柱契约 —— L0 单一事实源（来自裁决主链规范·主链时序，**不是** SKILL）。

⛔ 顺序即语义
────────────
`SPINE_ORDER` 是裁决主链的**不可重排**顺序。它不来自任何 ai-* SKILL，来自裁决主链规范·主链时序 的 S1→S5，因此必须独立成契约（`chiyu-decision` 包的核心资产）。

    S1_context → S1_derive → S2_score → S3_aggregate → S4_redline → S5_persist

⛔ 两条被源码修复印证的历史缺陷（demo 的时序守卫记录）：
    ① 九尺子评分**晚于落库** ⇒ 置信度算完即搁置（评分被降级为叙述留痕）；
    ② 红线**短路在相似度之前** ⇒ 八要素与九尺子在多数单上根本不参与判定。
    故顺序是本契约的第一等公民，任何消费方都不得以"性能优化"为由重排。
"""
from __future__ import annotations

from typing import Mapping, Tuple

# ── 裁决主链顺序（不可重排；守卫见 test_spine_anchor_guard）─────────────
SPINE_ORDER: Tuple[str, ...] = (
    "S1_context",     # 接收触发上下文
    "S1_derive",      # 本体分级（S1 派生，产出 ontology_grade）
    "S2_score",       # 八要素 + 九尺子评分
    "S3_aggregate",   # 聚合综合置信度——基座缺省聚合策略=九尺子 ratio（等权；铁律 C-B，见 CONFIDENCE_SOURCE_KEY；
                      # D3 裁定：ratio-only 是缺省策略非普适语义，消费方自有 confidence 源经策略注入替换不违 S3）
    "S4_redline",     # 红线硬判定 / 自主放行（链末硬闸门）
    "S5_persist",     # 决策落库
)
SPINE_STAGE_LABELS_ZH: Mapping[str, str] = {
    "S1_context": "接收触发上下文",
    "S1_derive": "本体分级",
    "S2_score": "八要素 + 九尺子评分",
    "S3_aggregate": "按外置权重配置加权聚合",
    "S4_redline": "红线硬判定",
    "S5_persist": "决策落库",
}

# ── 九尺子（顺序固定；键名跨域恒定，评的是**决策叙述质量**）────────────
# ⚠ 边界声明：九尺子**不是**匹配度 / 意向度。
#    匹配判定禁用本模块，否则会把「叙述写得好」当成「意向高」（同名异物陷阱）。
RUBRIC_KEYS: Tuple[str, ...] = (
    "clarity", "accuracy", "precision", "relevance", "depth",
    "breadth", "logic", "importance", "fairness",
)
RUBRIC_NAMES_ZH: Mapping[str, str] = {
    "clarity": "清晰性", "accuracy": "准确性", "precision": "精确性",
    "relevance": "相关性", "depth": "深度", "breadth": "广度",
    "logic": "逻辑性", "importance": "重要性", "fairness": "公平性",
}
RUBRIC_SCALE_MAX = 4               # 0=缺失 1=弱 2=部分 3=良 4=充分
RUBRIC_LLM_ELIGIBLE: Tuple[str, ...] = ("clarity",)   # 仅 clarity 允许 LLM 精评
RUBRIC_THRESHOLDS_DEFAULT: Mapping[str, float] = {"good": 0.75, "warn": 0.5}

# ── 综合置信度的基座缺省来源 ────────────────────────────────────────────
# ⛔ 基座缺省聚合策略取九尺子 `ratio`，**禁止**用匹配分 fused 冒充（违 S3）。
# 【D3 正式裁定登记·2026-10-14，CRM 为源仓】confidence（证据充分性）与九尺子
# ratio（叙述质量）是**两个不同量、各司其职**；"ratio" 的正确读法是「S3 聚合的
# **缺省实现**取 ratio」。confidence 允许多源聚合（ratio 为其一），消费方自有
# confidence 源（如 CRM methodologyScoring 5 权重证据公式 + 关系 boost，cap 0.95）
# 经策略注入替换，**不视为违 S3**；禁把二者合一表述为不变式（否则迁移时
# confidence 语义被静默替换 = D3 类假绿）。
CONFIDENCE_SOURCE_KEY = "ratio"

# ── 自主放行（裁决主链规范·红线条款：缺省时回退内置默认值）───────────────────────
# 【D3 登记续】本默认值作用于**基座聚合** confidence；消费方自有 confidence 源时
# 阈值默认留消费方（如 CRM autonomous 0.7，2026-09-02 用户批准）——两个默认值
# 各自成立、各自钉死，迁移时禁静默互替（CRM parity 守卫 ⑤ 逐值钉住）。
AUTONOMOUS_RELEASE_DEFAULT = 0.79
# ⛔ 判据是**一整行**：红线命中 ⇒ 短路为 False；否则按 confidence >= threshold。
#    只实现一半（屏蔽了红线但不看置信度）属于名存实亡，守卫见 test_spine_anchor_guard。
AUTONOMOUS_GATE_EXPR = (
    "autonomous_release = (not redline_hit) and confidence >= autonomous_threshold"
)

# ── 八要素（内置八要素骨架）──────────────────────────────────────────
EIGHT_ELEMENTS: Tuple[str, ...] = (
    "intent", "assumptions", "inference", "viewpoints",
    "impact", "risk_register", "stop_loss", "concept_refs",
)
EIGHT_ELEMENTS_ZH: Mapping[str, str] = {
    "intent": "意图", "assumptions": "假设", "inference": "推理",
    "viewpoints": "观点", "impact": "影响", "risk_register": "风险登记",
    "stop_loss": "止损", "concept_refs": "概念引用",
}

# ── 八要素→九尺子 封顶映射（J9-C：要素缺失 ⇒ 叙述质量证据不足，映射尺子封顶）──
# 语义边界：九尺子评的是**决策叙述质量**，八要素是叙述的**证据声明**；
# 某要素缺失 ⇒ 其映射尺子的叙述最多记「部分」档（封顶 2），置信度经 ratio 单边下调。
# ⛔ 与铁律 C-B 相容：confidence 唯一来源仍是九尺子 ratio —— 封顶只约束 ratio 的
#    **输入**，不引入第二来源。⛔ 单向下调（min，永不升分）；要素齐备 ⇒ 逐键原样。
ELEMENT_MISSING_CAP = 2            # 要素缺失时映射尺子的封顶档（0=缺失 1=弱 2=部分）
ELEMENT_RUBRIC_CAPS: Mapping[str, Tuple[str, ...]] = {
    "intent": ("relevance",),          # 意图未声明 ⇒ 相关性存疑
    "assumptions": ("accuracy",),      # 假设未声明 ⇒ 准确性存疑
    "inference": ("logic",),           # 推理缺失 ⇒ 逻辑性存疑
    "viewpoints": ("breadth",),        # 观点缺失 ⇒ 广度不足
    "impact": ("importance",),         # 影响未评估 ⇒ 重要性存疑
    "risk_register": ("depth",),       # 风险未登记 ⇒ 深度不足
    "stop_loss": ("depth",),           # 止损缺失 ⇒ 深度不足（与风险登记同源）
    "concept_refs": ("precision",),    # 概念引用缺失 ⇒ 精确性存疑
}
# fairness（公平性）无要素映射：它评的是利益平衡，八要素无对应物 —— 显式留白，防凑满。
if set(ELEMENT_RUBRIC_CAPS) != set(EIGHT_ELEMENTS):
    raise ValueError("ELEMENT_RUBRIC_CAPS 键必须恰为 EIGHT_ELEMENTS（防要素漂移漏封顶）")
_unknown_rulers = ({k for ks in ELEMENT_RUBRIC_CAPS.values() for k in ks}
                   - set(RUBRIC_KEYS))
if _unknown_rulers:
    raise ValueError(f"ELEMENT_RUBRIC_CAPS 出现未知尺子：{sorted(_unknown_rulers)}")

# ── 七维（M 层顶点；决策七边 serves_dims 的取值域）─────────────────────
SEVEN_DIMS: Tuple[Tuple[str, str, str], ...] = (
    ("identity", "身份", "决策针对的诉求主体是谁"),
    ("structure", "结构", "结构化属性是否齐备"),
    ("semantics", "语义", "语义与上下文是否一致、无歧义"),
    ("time_config", "时间配置", "时效与时机窗口"),
    ("decision_history", "决策历史", "是否引用了正确且有效的先例"),
    ("operational_state", "运行状态", "生命周期 / 人工池状态是否支撑该决策"),
    ("governance", "治理", "是否符合权限、合规与红线治理要求"),
)
SEVEN_DIM_KEYS: Tuple[str, ...] = tuple(k for (k, _n, _m) in SEVEN_DIMS)


# ── 审批审计事件常量（G4：消费方 match 只准引用常量，禁裸字符串）─────────
# 与脊柱实际审计事件一一对应；闭集枚举，新增事件类型须先落本契约。
AUDIT_EVENT_APPROVAL_PENDING: str = "approval_pending"    # 待人工审批（B3 PENDING 分支）
AUDIT_EVENT_APPROVAL_REJECTED: str = "approval_rejected"  # 审批驳回（含红线强制改判）
AUDIT_EVENT_APPROVAL_RESUMED: str = "approval_resumed"    # PENDING 批准后续跑落库（G3 resume_spine）
AUDIT_APPROVAL_EVENTS: Tuple[str, ...] = (
    AUDIT_EVENT_APPROVAL_PENDING,
    AUDIT_EVENT_APPROVAL_REJECTED,
    AUDIT_EVENT_APPROVAL_RESUMED,
)

# RFE audit-first（2026-10-12，APS 提出.foundation 裁定接纳）：审计轨记录标记。
# 消费方经 run_spine(audit_persister=...) 落审计轨事实（REJECTED/PENDING）时，
# 记录必须携带 record_kind=AUDIT_RECORD_KIND —— 「审计轨 ≠ 业务轨」的契约级
# 区分标记：审计轨是不可变事实留痕（谁/何时/何种裁定/多少置信度/为何），
# ⛔ 不得据此产生 DECIDED_ON 类正向边、不影响 resume 语义（与三态闸
# 「pending 不落正向边」哲学一致）。APPROVED 走既有 persister 业务轨。
AUDIT_RECORD_KIND: str = "audit"


def validate_spine_order(order: Tuple[str, ...]) -> None:
    """构造期校验：顺序必须与契约**逐项相等**，不是"包含"、不是"子集"。"""
    if tuple(order) != SPINE_ORDER:
        raise ValueError(
            f"裁决主链顺序被改动：期望 {SPINE_ORDER}，实际 {tuple(order)}。"
            "⛔ S1→S5 顺序不可重排（裁决主链规范·主链时序）"
        )


__all__ = [
    "SPINE_ORDER", "SPINE_STAGE_LABELS_ZH", "RUBRIC_KEYS", "RUBRIC_NAMES_ZH",
    "RUBRIC_SCALE_MAX", "RUBRIC_LLM_ELIGIBLE", "RUBRIC_THRESHOLDS_DEFAULT",
    "CONFIDENCE_SOURCE_KEY", "AUTONOMOUS_RELEASE_DEFAULT", "AUTONOMOUS_GATE_EXPR",
    "EIGHT_ELEMENTS", "EIGHT_ELEMENTS_ZH", "SEVEN_DIMS", "SEVEN_DIM_KEYS",
    "ELEMENT_MISSING_CAP", "ELEMENT_RUBRIC_CAPS",
    "AUDIT_EVENT_APPROVAL_PENDING", "AUDIT_EVENT_APPROVAL_REJECTED",
    "AUDIT_EVENT_APPROVAL_RESUMED", "AUDIT_APPROVAL_EVENTS", "AUDIT_RECORD_KIND",
    "validate_spine_order",
]
