"""RBAC 判定核（Batch-1b-1 rbac_core）—— 纯函数，零 IO。

收敛三仓判定**算法**（CRM `http/middleware/rbac.js` + APS `platform/security.py:80`）；
角色别名表内容、权限矩阵内容、租户档角色清单由消费方注入（域值留消费方）。

⛔ fail-closed 四则（RBAC_INVARIANTS 的机制投影，变异自证着力点）：
  ① 未知角色归一为 None —— 别名表未登记 ⇒ 不可判定 ⇒ 拒（禁模糊放行）；
  ② 归一后精确相等 —— 档位不相通（sysadmin ≠ ADMIN），禁「都是管理员」式和稀泥；
  ③ 租户档角色越域即拒 —— 指定 target_tenant_id 时必须与主体租户一致；
  ④ 权限矩阵全函数 —— 未登记 (namespace, role) 恒拒，禁默认放行；
  ⑤ 需求角色集为空 ⇒ 拒 —— 空表全放行是经典的假绿形态。
"""
from __future__ import annotations

from typing import Iterable, Mapping, Optional, Sequence

from chiyu_kernel.contract.iam import RBAC_DENY_REASONS

__all__ = [
    "normalize_role", "has_role", "has_any_role", "permission_allows",
    "role_deny_reason",
]


def normalize_role(role: object, aliases: Mapping[str, str]) -> Optional[str]:
    """角色别名归一（CRM `normalizeRole` 的域无关化）。

    :param role:    原始角色名（任意大小写/历史变体；None/空串 ⇒ None）。
    :param aliases: 别名表（消费方注入；如 {"ten_admin": "TAN_ADMIN", ...}）。
    :returns: 归一角色名；**未登记 ⇒ None**（fail-closed，绝不模糊放行）。

    ⚠ 表查询前 strip：前后空格是会话token/手工录入的常见噪声，但不因此放行——
      strip 后仍须命中别名表，否则 None。
    """
    if role is None:
        return None
    key = str(role).strip()
    if not key:
        return None
    return aliases.get(key)


def has_role(role: object, required: object, aliases: Mapping[str, str]) -> bool:
    """单角色判定：归一后**精确相等**（CRM `hasRole`）。

    两侧任一无法归一（未知/空）⇒ False——「需求角色本身没登记」同样拒，
    避免消费方把拼错的需求角色名静默变成恒假判定（假绿反向形态）。
    """
    r = normalize_role(role, aliases)
    req = normalize_role(required, aliases)
    return r is not None and req is not None and r == req


def has_any_role(
    role: object,
    roles: Iterable[object],
    aliases: Mapping[str, str],
    *,
    target_tenant_id: object = None,
    principal_tenant_id: object = None,
    tenant_scoped_roles: Iterable[str] = (),
) -> bool:
    """多角色判定（CRM `hasAnyRole` 的域无关化）。

    :param tenant_scoped_roles: 租户档角色清单（消费方注入，如 ("TAN_ADMIN",)）。
        主体角色归入该档 **且** 指定了 target_tenant_id 时，要求主体租户与目标
        一致，否则越域即拒（CRM §15.1：tan_admin 限本租户）。
    :returns: 命中任一需求角色（且租户域合规）⇒ True；需求集空 ⇒ False。
    """
    r = normalize_role(role, aliases)
    if r is None:
        return False
    scoped = {normalize_role(x, aliases) or str(x) for x in tenant_scoped_roles}
    if r in scoped and target_tenant_id is not None:
        if principal_tenant_id is None or principal_tenant_id != target_tenant_id:
            return False
    wanted = {normalize_role(x, aliases) for x in roles}
    wanted.discard(None)
    return r in wanted


def permission_allows(
    matrix: Mapping[str, Mapping[str, Iterable[str]]],
    namespace: str,
    role: object,
    action: str,
    *,
    aliases: Optional[Mapping[str, str]] = None,
) -> bool:
    """权限矩阵查询（APS PERMISSION_MATRIX 的域无关化）—— 全函数，未登记恒拒。

    :param matrix: {namespace: {role: (action, ...)}}（消费方注入）。
    :param aliases: 角色别名表（缺省不做归一，矩阵键即规范名）。
    :returns: (namespace, role) 已登记 **且** action ∈ 授予集 ⇒ True；
        命名空间未登记 / 角色未登记 / 动作未授予 ⇒ False（禁默认放行）。
    """
    r = str(role).strip() if role is not None else ""
    if aliases:
        r = normalize_role(r, aliases) or ""
    if not r or not action:
        return False
    by_role = matrix.get(namespace)
    if not isinstance(by_role, Mapping):
        return False
    granted = by_role.get(r)
    if granted is None:
        return False
    return str(action) in {str(a) for a in granted}


def role_deny_reason(
    role: object,
    roles: Iterable[object],
    aliases: Mapping[str, str],
    *,
    has_principal: bool = True,
    target_tenant_id: object = None,
    principal_tenant_id: object = None,
    tenant_scoped_roles: Iterable[str] = (),
) -> str:
    """结构化拒因（CRM DEALER_GATE 范式的域无关化；放行时返回 ""）。

    判序（可判别性优先：先主体后角色后租户，与 CRM canManageDealersDetailed 同序）：
      no_principal → unknown_role → tenant_mismatch → role_not_allowed。
    拒因取自 RBAC_DENY_REASONS 闭集（禁裸字符串扩散）。
    """
    if not has_principal:
        return "no_principal"
    r = normalize_role(role, aliases)
    if r is None:
        return "unknown_role"
    scoped = {normalize_role(x, aliases) or str(x) for x in tenant_scoped_roles}
    if (r in scoped and target_tenant_id is not None
            and (principal_tenant_id is None or principal_tenant_id != target_tenant_id)):
        return "tenant_mismatch"
    wanted = {normalize_role(x, aliases) for x in roles}
    wanted.discard(None)
    if r not in wanted:
        return "role_not_allowed"
    return ""
