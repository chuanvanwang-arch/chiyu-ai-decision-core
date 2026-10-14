"""自进化契约 —— L0 单一事实源（零第三方依赖、零 IO、零领域字面量）。

⛔ 本层只有**判据形态**，没有取值
──────────────────────────────
具体参数名 / 红线条目 / 命名空间清单由消费方注入（见下），内核不内置：
    · 参数白名单与取值区间 → `KnobTable`（消费方构造后传入）
    · 红线条目             → `TenantProfile.redline`（已有 `RedlineSpec`）
    · SKILL 允许命名空间   → `profile.extras`
若内核内置任何一项，第二个消费方就会带着第一个消费方的取值跑起来。

⚠️ 唯一例外：`BASELINE_SKILL_PREFIX`
────────────────────────────────────
它是**护栏判据**（基线命名空间不可写），不是领域值。若允许消费方覆盖，
"改一下配置"就能绕过护栏——而这种绕过每一步单独看都是合法的配置变更。

为什么"方向"必须由消费方声明而不是内核推断
──────────────────────────────────────────
阈值变小在 `autonomous_threshold` 上是放宽，在冷却天数上却是收紧。内核推断必错，
错了就是自我扩权（平台逐步下调自己的阈值，把人工在环静默架空）。
故 `widen_direction` 必须显式声明，且声明缺失在**构造期**即抛。
"""
from __future__ import annotations
from chiyu_kernel.errors import KernelError

from typing import Tuple

# ── 三类自变对象 ──────────────────────────────────────────────────────
EVOLUTION_OBJECTS: Tuple[str, ...] = ("agent", "skill", "knob")

# ── 风险分档（非对称护栏的落点）──────────────────────────────────────
# auto      低风险：过正确性闸后可自动生效（全链留痕、可回滚）
# guarded   需影子重放 + 冷却，仍可自动，但审计等级更高
# forbidden 永不自动：红线命中 / 基线写入 / 阈值放宽
RISK_TIERS: Tuple[str, ...] = ("auto", "guarded", "forbidden")
TIER_AUTO, TIER_GUARDED, TIER_FORBIDDEN = "auto", "guarded", "forbidden"

# ── 变更方向 ──────────────────────────────────────────────────────────
# widen = 放宽自主权（永不自动）；tighten = 收紧（可自动）；flat = 与自主权无关
DIRECTIONS: Tuple[str, ...] = ("widen", "tighten", "flat")
DIR_WIDEN, DIR_TIGHTEN, DIR_FLAT = "widen", "tighten", "flat"

# ── 处方状态机（与任务状态机刻意分家）─────────────────────────────────
# 任务失败 = 业务损失；处方失败 = 平台把标尺改错。失败语义相反 ⇒ 不共用状态集。
PRESCRIPTION_STATES: Tuple[str, ...] = (
    "pending",       # 已出方，未判定
    "replaying",     # 影子重放中
    "auto_applied",  # 自动生效（低风险，全链留痕）
    "suspended",     # 挂起：红线命中 / 阈值放宽 / 重放不通过（次日报告处置）
    "rolled_back",   # 已回滚（逆动作，同样留痕）
)
PRESCRIPTION_TERMINAL: Tuple[str, ...] = ("auto_applied", "rolled_back")
PRESCRIPTION_TRANSITIONS: dict[str, frozenset[str]] = {
    "pending":      frozenset({"replaying", "suspended"}),
    "replaying":    frozenset({"auto_applied", "suspended"}),
    "auto_applied": frozenset({"rolled_back"}),
    "suspended":    frozenset({"pending", "rolled_back"}),  # 挂起可人工放行后重走
    "rolled_back":  frozenset(),
}

# ── 元红线类别（自进化系统**对自己**的红线，非业务红线）──────────────
META_REDLINES: Tuple[str, ...] = (
    "threshold_widen",   # 放宽自主权阈值
    "baseline_write",    # 写入基线命名空间或 L0 契约目录
    "redline_auto",      # 红线命中项被自动应用
)

# ⛔ 基线命名空间前缀：自生成产物不得落此处（基线不得新增/删除/重编号）
BASELINE_SKILL_PREFIX = "ai-"

# ── verdict（纯方法论默认不抛异常 ⇒ 必须显式给结论）───────────────────
# 用"没抛错"判成功是假阳性：异常被吞、分支没走到，都不抛错。
VERDICT_PASS = "pass"
VERDICT_REJECT = "reject"
VERDICTS: Tuple[str, ...] = (VERDICT_PASS, VERDICT_REJECT)

# 缺 verdict / 执行异常 ⇒ 一律按 reject（fail-safe 默认保守）
FAIL_SAFE_VERDICT = VERDICT_REJECT

# 处方记录参与审计链的字段（沿用审计契约字段，不另立一套口径）
PRESCRIPTION_AUDIT_FIELDS: Tuple[str, ...] = (
    "audit_id", "ts", "domain", "action", "subject_id", "decision_id",
    "prescription_id", "from_value", "to_value", "verdict",
)

# ── 处方组装（Batch-1b-4 assemble_prescription；上迁自 CRM calibration/patchAssembler.js）──
#: 自动产出仅认的 knob 闭集（CRM：非 threshold/weight 不自动产出，走消费方手动分支；
#: 域 knob 名不入基座——闭集是**机制形态**：只认标量阈值与单键权重两种变更形态）。
ASSEMBLE_AUTO_KNOBS: Tuple[str, ...] = ("threshold", "weight")
#: 重放预期影响必含字段（replay 可调用对象产出投影；缺一即 fail-closed 拒绝组装）。
ASSEMBLE_EXPECTED_IMPACT_FIELDS: Tuple[str, ...] = (
    "autonomy", "escalated", "estimated_override_rate",
)
ASSEMBLE_INVARIANTS: Tuple[str, ...] = (
    "guards_hit_no_prescription",             # 守卫命中 ⇒ blocked_by，不出任何处方
    "non_auto_knob_never_produced",           # 白名单外 knob 不自动产出（禁硬凑）
    "replay_callable_same_source",            # 重放必须同源可调用对象（与 shadow_replay 同纪律）
    "idempotency_key_deterministic",          # 幂等键由 knob/target/from/to 规范化派生（同输入同键）
    "expected_impact_requires_before_after",  # 预期影响必须带重放前后对照（无对照即盲改）
    "from_value_is_current_config",           # from_value 取当前配置原值（禁猜回滚目标）
)


class AssembleError(KernelError):
    code = "CONTRACT_VIOLATION"
    """处方组装输入非法（replay 不可调用/缺指标投影 / conf 缺键 / delta 形态非法）。"""


__all__ = [
    "EVOLUTION_OBJECTS", "RISK_TIERS", "TIER_AUTO", "TIER_GUARDED", "TIER_FORBIDDEN",
    "DIRECTIONS", "DIR_WIDEN", "DIR_TIGHTEN", "DIR_FLAT",
    "PRESCRIPTION_STATES", "PRESCRIPTION_TERMINAL", "PRESCRIPTION_TRANSITIONS",
    "META_REDLINES", "BASELINE_SKILL_PREFIX",
    "VERDICT_PASS", "VERDICT_REJECT", "VERDICTS", "FAIL_SAFE_VERDICT",
    "PRESCRIPTION_AUDIT_FIELDS",
    "ASSEMBLE_AUTO_KNOBS", "ASSEMBLE_EXPECTED_IMPACT_FIELDS",
    "ASSEMBLE_INVARIANTS", "AssembleError",
]
