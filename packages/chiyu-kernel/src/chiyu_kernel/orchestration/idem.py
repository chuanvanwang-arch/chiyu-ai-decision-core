"""幂等键 —— 夜批防重跑（内核此前**无此原语**）。

⛔ 为什么必须有
   §12.3 第 7 条写「夜批沿用 `derive_idem_key`」，但取证时内核 `grep -rn "idem"`
   零命中 —— 该函数只存在于 demo 侧。"沿用"是未经验证的假设，故此处**新增**。

   缺失的后果不是"少个函数"：B 档夜间无人值守下重跑一次夜批 ⇒ 重复出方 +
   重复应用。配置被改第二遍时 `old_value` 已被第一次覆盖 ⇒ **回滚链断裂**，
   属无声的配置漂移（既无报错、也无告警，只是再也回不到原值）。
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

IDEM_PREFIX = "idem"


def derive_idem_key(scope: str, parts: Sequence[Any]) -> str:
    """由 scope + 内容派生稳定键。

    判据：内容相同 ⇒ 键相同（跨进程、跨天稳定）；内容任一字节变 ⇒ 键变。
    """
    s = (scope or "").strip()
    if not s:
        raise ValueError("idem scope 必填（空 scope 会让不同批次撞同一个键）")
    payload = json.dumps(
        [
            p if isinstance(p, str) else {k: p[k] for k in sorted(p)}
            for p in parts
        ],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    h = hashlib.sha256()
    h.update(s.encode("utf-8"))
    h.update(b"|")
    h.update(payload.encode("utf-8"))
    return f"{IDEM_PREFIX}:{s}:{h.hexdigest()[:16]}"


def nightly_idem_key(
    reason: str, *, window: str, parts: Sequence[Any]
) -> str:
    """夜批专用键：`nightly:<reason>@<window>`。

    ⛔ `window` 必须进键 —— 否则跨天重跑拿到同一个键，"换天自然换键"就无从谈起。
    """
    if not (reason or "").strip():
        raise ValueError("nightly reason 必填（否则不同原因的夜批互相覆盖）")
    if not (window or "").strip():
        raise ValueError("nightly window 必填（否则跨天重跑撞键）")
    return derive_idem_key(f"nightly:{reason}@{window}", list(parts))


__all__ = ["IDEM_PREFIX", "derive_idem_key", "nightly_idem_key"]
