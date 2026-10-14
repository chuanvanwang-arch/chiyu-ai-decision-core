"""IAM/RBAC 判定接口契约 —— 收判定接口 + RBAC 判定核算法（D7 + Batch-1b-1）。

⛔ L0 纪律：零第三方依赖（除 dataclasses）、零 IO、零领域字面量。

设计来源（三仓交集 P1，详见 docs/plans/2026-10-13-foundation三大支柱详细设计.md D7）：
  - enterprise #5 P1（IAM 五档 + 两阶段 confirm 参考实现，贡献接口形）；
  - APS #6 P1-C（判定接口进基座；RBAC 三档 off/advisory/enforced 与 D2 同构）；
  - CRM Q2 P2 观望（角色矩阵留各仓：sales/ten_admin/channel_manager 与动作目录不入基座）。

⛔ 边界铁律（三仓共识 + Batch-1b-1 裁定）：基座收 **Principal / SecurityDecision /
   RoleGate** 判定接口、三档判定执行形态与 **RBAC 判定核算法**（别名归一 fail-closed、
   角色相等/成员判定、租户域限定、权限矩阵全函数查询）；角色-动作映射矩阵**内容**、
   身份源对接（IdP）、token 验签/过期/吊销、角色别名表**内容**留消费方注入
   （enterprise 参考实现供形，不强制上收）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Protocol, Tuple

from .security import SECURITY_MODES

# ══ 判定主体（身份最小面，不绑定具体 IdP）════════════════════════════════
PRINCIPAL_FIELDS: Tuple[str, ...] = (
    "id",      # 主体 id（人工 user_id / 系统 principal；追责锚点）
    "scopes",  # 作用域闭包（如 ("tenant:acme", "case:123")；域语义由消费方定义）
)


@dataclass(frozen=True)
class Principal:
    """判定主体（身份最小面）。scope 语义（tenant/case/...）由消费方定义，基座只收形状。"""

    id: str
    scopes: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Principal.id 必填（匿名主体不可判定，追责锚点缺失）")


# ══ 判定结果（D2.4 定型 + scope 维度补全）════════════════════════════════
SECURITY_DECISION_FIELDS: Tuple[str, ...] = (
    "mode",        # ∈ SECURITY_MODES
    "allowed",     # 是否放行
    "would_deny",  # advisory 下若 enforced 是否会拒（生产观测面）
    "reason",      # 结构化拒因（off 时显式「未启用」，杜绝静默放行）
    "scope",       # 判定作用域（与 Principal.scopes 同语义族，消费方定义）
)

# ── 扩展字段携带约定（裁定 APS ②a：消费方统一采用基座 5 字段形）────────────
# 消费方（APS）自有判定载体比基座多 3 个留痕字段（action/namespace/required_perm），
# 属审计留痕面、不上收。裁定：消费方统一使用基座 SecurityDecision 5 字段形，
# 留痕字段经 extensions Mapping 携带，避免第二份判定载体（与「不新增第二份状态机」同理）。
# 基座对 extensions 仅保证结构（Mapping 形 + 键不与核心 5 字段冲突），不解释内容。
SECURITY_DECISION_EXTENSION_RULE = (
    "SecurityDecision.extensions: Mapping[str, object] = {} — 消费方留痕槽；"
    "基座仅保证 extensions 为 Mapping 且键集与 SECURITY_DECISION_FIELDS 不相交；"
    "核心判定语义只走 SECURITY_DECISION_FIELDS 五字段，extensions 不参与不变量"
)


@dataclass(frozen=True)
class SecurityDecision:
    """三档判定结果（D2.4 形态 + scope）。

    结构不变量（__post_init__ 保证，非文档纪律）：
      - mode ∈ SECURITY_MODES（禁裸字符串升档/降档）；
      - enforced 下 would_deny == (not allowed)（D2 防漂移不变量的单对象投影：
        enforced 是真拦，不存在「allowed 但 would_deny」的矛盾判定）。
      advisory / off 的 would_deny 语义由判定执行器（内核/消费方）保证，
      本契约不强约束其取值组合（advisory 下 would_deny 独立观测才有效力）。
      extensions 为消费方留痕槽（Mapping），基座仅保证结构，不参与上述不变量。
    """

    mode: str
    allowed: bool
    would_deny: bool
    reason: str = ""
    scope: str = ""
    extensions: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.mode not in SECURITY_MODES:
            raise ValueError(
                f"SecurityDecision.mode 非法：{self.mode!r} ∉ SECURITY_MODES（禁裸字符串）")
        if self.mode == "enforced" and self.would_deny != (not self.allowed):
            raise ValueError(
                "enforced 判定自相矛盾：would_deny 必须 == (not allowed)（D2 防漂移不变量）")
        if self.mode == "off" and not self.allowed:
            raise ValueError("off 模式恒放行：allowed=False 违反 D2 缺省零破坏语义")
        if not isinstance(self.extensions, Mapping):
            raise ValueError(
                "SecurityDecision.extensions 必须为 Mapping（消费方留痕槽，基座不解释内容）")
        collide = set(self.extensions) & set(SECURITY_DECISION_FIELDS)
        if collide:
            raise ValueError(
                f"SecurityDecision.extensions 键不得与核心判定字段冲突：{sorted(collide)}")

    def __hash__(self) -> int:
        # frozen dataclass 默认 __hash__ 会因 extensions(dict) 不可哈希而失效；
        # 显式定义：核心五字段 + extensions 项 frozenset（值不可哈希时抛 TypeError，
        # 与「消费者置放不可哈希留痕值则 SecurityDecision 不可哈希」语义一致）。
        return hash((self.mode, self.allowed, self.would_deny, self.reason,
                     self.scope, frozenset(self.extensions.items())))


# ══ RBAC 判定核（Batch-1b-1 rbac_core 上迁，2026-10-14）═════════════════
# 收敛三仓 RBAC **判定算法**（CRM `http/middleware/rbac.js` 别名归一 fail-closed +
# hasAnyRole 租户域；APS `platform/security.py:80` 命名空间×角色×权限矩阵查询）。
# ⛔ 域值留消费方：角色别名表、权限矩阵内容、租户档位角色清单一律注入；
#   基座只收算法与 fail-closed 语义（与「机制上迁、域值留消费方」同律）。
RBAC_INVARIANTS: Tuple[str, ...] = (
    "unknown_role_normalizes_to_none",        # 未知角色 → None，绝不模糊放行（fail-closed）
    "role_equality_exact_after_normalize",    # 归一后精确相等，档位不相通（sysadmin ≠ ADMIN）
    "tenant_scoped_role_requires_match",      # 租户档角色指定 target 时必须与主体租户一致
    "permission_lookup_is_total",             # 矩阵查询对未登记 (ns, role) 恒拒，禁默认放行
    "empty_required_set_denies",              # 需求角色集为空 ⇒ 拒（禁空表全放行）
)

# ── 拒绝原因闭集（结构化拒因；对应 CRM DEALER_GATE 的可判别 reason 范式）──
# 同一状态码承载多种成因时，判定方必须给出可判别 reason，由消费端按 reason
# 分支渲染；判定逻辑仍留服务端（前端禁复制放行集自行预判，否则放行集漂移）。
RBAC_DENY_REASONS: Tuple[str, ...] = (
    "no_principal",      # 无有效主体（匿名不可判定）
    "unknown_role",      # 角色无法归一（别名表未登记）
    "role_not_allowed",  # 角色不符
    "tenant_mismatch",   # 跨租户（租户档角色越域）
    "permission_denied",  # 权限矩阵未授予（含未登记命名空间/角色）
)


# ══ 常驻授权凭证（Batch-1b-1 standing_credential，上迁自 CRM grantStore/grantSweeper）══
# 收判定**算法**（覆盖判定 / 用量熔断 / 巡检判决三纯函数）；凭证存储（DDL/CRUD）、
# 审批流挂接、巡检调度留消费方（CRM crm.standing_grant / grant_execution 表不在基座）。
# ⛔ 铁律（CRM B-N8 原样上收）：撤回/暂停/到期全为状态字段变更，**零 DELETE**（审计可溯源）。
STANDING_GRANT_STATUSES: Tuple[str, ...] = (
    "active",    # 生效中（覆盖判定唯一放行态）
    "paused",    # 暂停（用量达限 / 连续否决信任降级 / 人工；paused_reason 留痕）
    "revoked",   # 撤回（revoked_at + revoked_reason 留痕）
    "expired",   # 到期（巡检自动判决）
)

# 暂停原因闭集（paused_reason 结构化留痕；CRM 'usage-limit'/'consecutive-rejects' 原样上收）
PAUSE_REASONS: Tuple[str, ...] = (
    "usage-limit",           # 用量达限（used_count >= max_uses）
    "consecutive-rejects",   # 最近 N 条执行全 rejected（信任降级）
    "auto-pause",            # 人工/策略暂停（消费方默认值）
    "manual",                # 显式人工暂停
)

# 执行 HITL 裁决词汇（CRM grant_execution.hitl_verdict 原样上收；
# ⛔ 与审批核心态同源：GRANT_VERDICTS ⊆ APPROVAL_CORE_STATES（守卫测试对拍，禁漂移））
GRANT_VERDICTS: Tuple[str, ...] = ("pending", "approved", "rejected")

CREDENTIAL_INVARIANTS: Tuple[str, ...] = (
    "lifecycle_is_status_only",           # 全生命周期=状态字段变更，零 DELETE
    "coverage_requires_active_unexpired",  # 覆盖判定前提：active 且未过期
    "fields_subset_of_whitelist",          # 白名单超集语义：请求字段每元素都须被包含
    "whitelist_null_means_unlimited",      # 白名单空/缺省 ⇒ 不限字段（由上游闸兜底）
    "usage_limit_pauses",                  # 达 max_uses ⇒ paused(usage-limit)，禁继续放行
    "consecutive_rejects_pauses",          # 最近 N 条全 rejected ⇒ paused（N>0 才启用）
)

# ══ 两阶段确认令牌（Batch-1b-1 two_phase_token：机制自 mcpserver 提升至 iam/two_phase，
#    mcpserver 委托同实现——禁双源。词汇面收绑定规则，签发/验签纯函数在机制层）══
TWO_PHASE_INVARIANTS: Tuple[str, ...] = (
    "token_binds_tool_args_principal",  # 三重绑定：改工具名/改参数/换主体任一 ⇒ 失效
    "args_canonical_before_sign",       # 参数规范化（键排序）后才签名，同语义必同串
    "constant_time_compare",            # 验签恒定时间比较（防计时侧信道）
)


class RoleGate(Protocol):
    """角色闸原语（三仓共识：收接口不收角色矩阵）。

    消费方注入自有实现（enterprise IAM 五档 / APS 权限矩阵 / CRM 角色闸）；
    基座只约定判定签名与结果形状，杜绝消费方各自造 SecurityDecision 口径。
    """

    def check(self, principal: Principal, resource: str, action: str) -> SecurityDecision:
        """判定 principal 对 resource 执行 action 是否放行（结构化拒因必填于 reason）。"""
        ...


__all__ = [
    "PRINCIPAL_FIELDS", "SECURITY_DECISION_FIELDS", "SECURITY_DECISION_EXTENSION_RULE",
    "Principal", "SecurityDecision", "RoleGate",
    # Batch-1b-1 RBAC 判定核
    "RBAC_INVARIANTS", "RBAC_DENY_REASONS",
    # Batch-1b-1 常驻授权凭证 + 两阶段确认令牌
    "STANDING_GRANT_STATUSES", "PAUSE_REASONS", "GRANT_VERDICTS",
    "CREDENTIAL_INVARIANTS", "TWO_PHASE_INVARIANTS",
]
