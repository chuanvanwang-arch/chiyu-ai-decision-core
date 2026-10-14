"""常驻授权凭证判决核（Batch-1b-1 standing_credential）—— 纯函数，零 IO、零 DB。

收敛 CRM `authorization/grantStore.js`（grantCovers + 用量熔断）与
`authorization/grantSweeper.js`（到期 + 连续否决巡检）的**判定算法**；
凭证存储（DDL/CRUD）、审批流挂接、巡检调度留消费方。

⛔ 铁律（CREDENTIAL_INVARIANTS 的机制投影，变异自证着力点）：
  ① 全生命周期=状态字段变更，零 DELETE；
  ② 覆盖判定前提 active 且未过期（expires_at < now 严格小于；等于不算过期，CRM 同口径）；
  ③ 字段白名单超集语义：请求字段每元素都须被白名单包含；
  ④ 白名单空/缺省 ⇒ 不限字段（由上游闸兜底，基座不代替 T3 判级）；
  ⑤ 用量达限 ⇒ paused(usage-limit)，禁继续放行；
  ⑥ 连续否决信任降级仅在 N>0 时启用，N 条取**最近 N 条**（与 CRM LIMIT N 同序）。
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping, Optional, Sequence

from chiyu_kernel.contract.iam import PAUSE_REASONS

__all__ = [
    "grant_covers", "resolve_active_grant", "usage_breaker", "sweep_grant",
]


def grant_covers(grant: Optional[Mapping[str, Any]], *, action: str,
                 fields: Iterable[str] = (), now: Any) -> bool:
    """凭证是否覆盖某动作 + 字段集（CRM `grantCovers` 的域无关化）。

    :param grant: 凭证行（Mapping；None/空 ⇒ False）。
    :param now:   当前时刻（与 ``expires_at`` **同型可比较**：datetime/epoch/同构 ISO 串；
                  不可比较的 TypeError 直接冒泡——禁静默猜测，类型错是调用方 bug）。
    :returns: status=active 且未过期 且 action ∈ scope_actions 且 字段集 ⊆ field_whitelist。
    """
    if not grant:
        return False
    if grant.get("status") != "active":
        return False
    expires_at = grant.get("expires_at")
    if expires_at is not None and expires_at < now:
        return False
    scope_actions = grant.get("scope_actions")
    if not isinstance(scope_actions, (list, tuple, set, frozenset)):
        return False
    if action not in scope_actions:
        return False
    whitelist = grant.get("field_whitelist")
    if whitelist:  # None / 空集 ⇒ 不限字段（不变式④）
        for f in fields:
            if f not in whitelist:
                return False
    return True


def resolve_active_grant(grants: Iterable[Mapping[str, Any]], *, action: str,
                         fields: Iterable[str] = (), now: Any
                         ) -> Optional[Mapping[str, Any]]:
    """按给定顺序返回首个覆盖该动作+字段的活跃未过期凭证（CRM `resolveActiveGrant`
    的域无关化；排序（ORDER BY created_at）由调用方负责，本函数保序取首个）。"""
    for g in grants or ():
        if grant_covers(g, action=action, fields=fields, now=now):
            return g
    return None


def usage_breaker(grant: Optional[Mapping[str, Any]]) -> Optional[str]:
    """用量熔断判决（CRM recordExecution 的暂停 UPDATE 判据纯函数化）。

    :returns: 应暂停 ⇒ ``"usage-limit"``（∈ PAUSE_REASONS）；否则 None。
      判据与 CRM 同口径：status=active 且 max_uses 非 null 且 used_count >= max_uses。
    """
    if not grant or grant.get("status") != "active":
        return None
    max_uses = grant.get("max_uses")
    if max_uses is None:
        return None
    used = grant.get("used_count") or 0
    if used >= max_uses:
        assert "usage-limit" in PAUSE_REASONS
        return "usage-limit"
    return None


def sweep_grant(grant: Optional[Mapping[str, Any]],
                recent_verdicts: Sequence[str] = (), *,
                consecutive_reject_limit: int, now: Any) -> Optional[str]:
    """单凭证巡检判决（CRM `sweepOnce` 的逐凭证纯函数化；调度/落库留消费方）。

    :param recent_verdicts: 最近执行 HITL 裁决（**最新在前**，与 CRM ORDER BY
        created_at DESC 同序）；调用方负责 LIMIT。
    :param consecutive_reject_limit: 连续否决阈值 N（N<=0 ⇒ 关闭信任降级，CRM 同口径）。
    :returns: 应处置 ⇒ ``"expired"``（到期）或 ``"consecutive-rejects"``（暂停降级）；
        无动作 ⇒ None。仅 active 凭证参与巡检（与 CRM WHERE status='active' 同口径）。
    """
    if not grant or grant.get("status") != "active":
        return None
    # ① 到期
    expires_at = grant.get("expires_at")
    if expires_at is not None and expires_at < now:
        return "expired"
    # ② 连续否决信任降级（取最近 N 条；不足 N 条不判——CRM verdicts.length >= N 同口径）
    n = consecutive_reject_limit
    if n and n > 0:
        window = list(recent_verdicts or ())[:n]
        if len(window) >= n and all(v == "rejected" for v in window):
            assert "consecutive-rejects" in PAUSE_REASONS
            return "consecutive-rejects"
    return None
