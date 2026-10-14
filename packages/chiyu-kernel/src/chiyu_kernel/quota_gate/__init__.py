"""Token 配额闸判决核（Batch-1b-4 quota_gate）—— 纯函数，零 IO、零副作用。

收敛 CRM `billing/quotaGate.js` 的**判决算法**；套餐取数（getPlan/tokenQuota）、
平台租户豁免名单、抛错/降级行为留消费方（基座返回判决 dict，消费方据此抛错）。

⛔ 加固差异（相对 CRM 实现的报备）：CRM 未知 mode 会静默放行（既非 block 也非
bill ⇒ 落到末行 allow），基座对未知 mode **fail-closed 抛错**——配额判决禁猜测。
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from chiyu_kernel.contract.quota import (
    BILL_HARDCAP_MULTIPLIER, QUOTA_DENY_REASONS, QUOTA_MODE_UNLIMITED,
    QUOTA_MODES, QUOTA_UNLIMITED_SENTINEL, QuotaGateError,
)

__all__ = ["judge_quota"]


def _num(x: Any, *, what: str, required: bool = True,
         default: Optional[float] = None) -> float:
    """数值化（bool 不算数；None 按 required 语义处理；禁 NaN）。"""
    if x is None:
        if required:
            raise QuotaGateError(f"配额判决缺 {what}")
        return float(default)   # type: ignore[arg-type]
    if isinstance(x, bool):
        raise QuotaGateError(f"配额判决 {what} 非数值（bool 不算数）")
    try:
        v = float(x)
    except (TypeError, ValueError) as exc:
        raise QuotaGateError(f"配额判决 {what} 非数值：{x!r}") from exc
    if v != v:
        raise QuotaGateError(f"配额判决 {what} 为 NaN")
    return v


def judge_quota(*, mode: str, included: Any, used: Any,
                hard_cap: Optional[Any] = None,
                exempt: bool = False) -> Mapping[str, Any]:
    """配额判决（CRM enforceTokenQuota 预检段纯函数化）。

    :param mode: 超额模式（``QUOTA_MODES`` 闭集；未知 ⇒ 抛错 fail-closed）。
    :param included: 套餐含量（None ⇒ 0，CRM ``Number(x) || 0`` 同口径；
        ``< 0`` ⇒ 不限哨兵，直接放行避免负 hardCap 误封）。
    :param used: 已用量（必填运行时事实，None ⇒ 抛错）。
    :param hard_cap: 显式安全上限（覆盖缺省倍数；bill 缺省 = included×3，
        block 缺省 = included 本身）。
    :param exempt: 豁免（平台租户等；名单由消费方判定后传入，基座不认域租户名）。
    :returns: ``{"ok", "verdict", "mode", "used", "cap", "exempt"[, "reason"]}``；
        deny 必带 ``QUOTA_DENY_REASONS`` 闭集内 reason。
    """
    if mode not in QUOTA_MODES:
        raise QuotaGateError(
            f"未知超额模式：{mode!r} ∉ {QUOTA_MODES}（CRM 现实现会静默放行——基座加固）")
    used_n = _num(used, what="used")
    if exempt:
        return {"ok": True, "verdict": "allow", "mode": QUOTA_MODE_UNLIMITED,
                "used": used_n, "cap": None, "exempt": True}
    included_n = _num(included, what="included", required=False, default=0)
    if included_n < QUOTA_UNLIMITED_SENTINEL + 1:
        # 不限哨兵（-1 及任何负值）：直接放行，避免负 hardCap 误封
        return {"ok": True, "verdict": "allow", "mode": QUOTA_MODE_UNLIMITED,
                "used": used_n, "cap": None, "exempt": False}
    if hard_cap is not None:
        cap = _num(hard_cap, what="hard_cap")
    else:
        cap = (included_n * BILL_HARDCAP_MULTIPLIER if mode == "bill"
               else included_n)
    if mode == "block" and used_n >= included_n:
        return {"ok": False, "verdict": "deny", "mode": mode, "used": used_n,
                "cap": cap, "exempt": False, "reason": "block_exhausted"}
    if mode == "bill" and used_n >= cap:
        return {"ok": False, "verdict": "deny", "mode": mode, "used": used_n,
                "cap": cap, "exempt": False, "reason": "bill_hard_cap"}
    return {"ok": True, "verdict": "allow", "mode": mode, "used": used_n,
            "cap": cap, "exempt": False}
