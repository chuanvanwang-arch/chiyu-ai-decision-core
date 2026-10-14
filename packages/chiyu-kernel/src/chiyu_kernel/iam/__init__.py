"""IAM 机制层（Batch-1b-1）—— RBAC 判定核 + 常驻授权凭证 + 两阶段确认令牌。

⛔ 域值留消费方：角色别名表、权限矩阵内容、租户档角色清单、凭证存储与
   审批流挂接一律由消费方注入；本包只收判定算法与 fail-closed 语义。
"""

from chiyu_kernel.iam.rbac import (
    normalize_role, has_role, has_any_role, permission_allows, role_deny_reason,
)
from chiyu_kernel.iam.standing import (
    grant_covers, resolve_active_grant, usage_breaker, sweep_grant,
)
from chiyu_kernel.iam.two_phase import (
    canonical_args, issue_confirm_token, verify_confirm_token,
)

__all__ = [
    # rbac_core
    "normalize_role", "has_role", "has_any_role", "permission_allows",
    "role_deny_reason",
    # standing_credential
    "grant_covers", "resolve_active_grant", "usage_breaker", "sweep_grant",
    # two_phase_token
    "canonical_args", "issue_confirm_token", "verify_confirm_token",
]
