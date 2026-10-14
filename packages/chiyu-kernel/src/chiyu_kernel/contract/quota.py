"""Token 配额闸契约（Batch-1b-4 quota_gate；上迁自 CRM billing/quotaGate.js 判决核）。

⛔ L0 纪律：零第三方依赖、零 IO、零领域字面量。
套餐域值（included/hard_cap/mode 取数）、平台租户豁免名单 ⇒ 消费方注入
（基座不认 'system' 之类的域租户名——豁免以 exempt 布尔入参承载）。
"""
from __future__ import annotations
from chiyu_kernel.errors import KernelError

from typing import Tuple

# ── 超额模式闭集（配置驱动：block=超量即断 / bill=超量计费+安全上限）──────
QUOTA_MODES: Tuple[str, ...] = ("block", "bill")
#: 判决结果模式第三值：豁免租户 / 不限哨兵命中时的模式标签（非配置模式）。
QUOTA_MODE_UNLIMITED = "unlimited"

#: 不限哨兵：included < 0 ⇒ 不限量（与 seatPolicy included_seats=-1 同口径）。
QUOTA_UNLIMITED_SENTINEL = -1

#: bill 模式缺省安全上限倍数：hard_cap 未配置时 cap = included × BILL_HARDCAP_MULTIPLIER；
#: block 模式缺省 cap = included（超量即断，无第二段）。
BILL_HARDCAP_MULTIPLIER = 3

#: 判决闭集（deny 必带 reason；消费方据此抛错/降级，基座不抛——纯函数零副作用）。
QUOTA_VERDICTS: Tuple[str, ...] = ("allow", "deny")

#: deny 原因闭集（fail-closed 可审计：禁裸字符串散落）。
QUOTA_DENY_REASONS: Tuple[str, ...] = (
    "block_exhausted",   # block 模式 used ≥ included：额度用完
    "bill_hard_cap",     # bill 模式 used ≥ hard_cap：达安全上限
)

QUOTA_INVARIANTS: Tuple[str, ...] = (
    "exempt_bypasses_quota",             # 豁免租户直通（mode=unlimited, cap=None）
    "unlimited_sentinel_negative_one",   # included < 0 ⇒ 不限量（禁负 hardCap 误封）
    "block_caps_at_included",            # block 模式缺省上限 = included 本身
    "bill_caps_at_included_times_three", # bill 模式缺省上限 = included × 3
    "unknown_mode_fail_closed",          # 未知模式抛错（CRM 现实现会静默放行——基座加固，报备差异）
    "deny_reason_in_closed_set",         # deny 必带闭集内 reason
)


class QuotaGateError(KernelError):
    code = "CONTRACT_VIOLATION"
    """配额判决输入非法（未知模式 / 非法数值形态）。"""


__all__ = [
    "QUOTA_MODES", "QUOTA_MODE_UNLIMITED", "QUOTA_UNLIMITED_SENTINEL",
    "BILL_HARDCAP_MULTIPLIER", "QUOTA_VERDICTS", "QUOTA_DENY_REASONS",
    "QUOTA_INVARIANTS", "QuotaGateError",
]
