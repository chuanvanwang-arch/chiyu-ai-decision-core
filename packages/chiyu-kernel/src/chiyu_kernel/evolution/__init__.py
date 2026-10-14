"""自进化层 —— 平台改自己的闸门（设计稿 §12 的机制层）。

⛔ 为什么与 `orchestration` 分家
──────────────────────────────
`orchestration` 回答「任务怎么跑」，`evolution` 回答「**平台改自己**」。
二者失败语义相反：任务失败是业务损失，自变失败是**平台把验证自己的标尺改错**。
混在一个包里，只读护栏的边界就划不清。

职责划分（避免第二份判据表）
────────────────────────────
    knob         参数白名单 + 风险分档 + **G1**（放宽永不自动）
    replay       影子重放（无样本即拒，禁字符串公式）
    prescription 处方状态机（事务原子 + 挂起 + 一键回滚）
    guard        **G2**（红线挂起）+ **G3**（只读路径，不可豁免）
    skill_draft  方法论草稿闸 + 命名空间隔离（禁写基线前缀）
"""
from .guard import (
    READONLY_PATH_PREFIXES,
    GuardViolation,
    assert_not_baseline_skill,
    assert_writable,
    g2_suspend_on_redline,
    meta_redline_hits,
)
from .knob import (
    KnobError,
    KnobSpec,
    KnobTable,
    classify_change,
    is_forbidden_change,
)
from .prescription import (
    Prescription,
    PrescriptionError,
    apply_atomic,
    assert_prescription_transition,
    begin_replay,
    roll_back,
)
from .replay import BASELINE_FIELD, ReplayVerdict, shadow_replay
from .skill_draft import SkillDraft, SkillDraftError, promote, validate_draft
from .readiness import (
    ChannelNotReadyError,
    CheckResult,
    ReadinessReport,
    assert_channel_may_open,
    readiness_report,
)

__all__ = [
    # knob
    "KnobError", "KnobSpec", "KnobTable", "classify_change", "is_forbidden_change",
    # replay
    "ReplayVerdict", "shadow_replay", "BASELINE_FIELD",
    # prescription
    "PrescriptionError", "Prescription", "assert_prescription_transition",
    "begin_replay", "apply_atomic", "roll_back",
    # guard
    "GuardViolation", "READONLY_PATH_PREFIXES", "assert_writable",
    "assert_not_baseline_skill", "g2_suspend_on_redline", "meta_redline_hits",
    # skill_draft
    "SkillDraftError", "SkillDraft", "validate_draft", "promote",
    # readiness（开闸前置认证器）
    "ChannelNotReadyError", "CheckResult", "ReadinessReport",
    "assert_channel_may_open", "readiness_report",
]
