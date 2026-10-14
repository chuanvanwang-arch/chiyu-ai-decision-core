"""scheduler 契约（L0：零依赖 / 零 IO / 零领域字面量）。

Batch-5 调度核判据词汇。上收自 CRM scheduler/timers.js（nextRetroAt /
catchUpRetro / runRetroOnce 段隔离范式）。任务名/时区/租户域由消费方注入。

不变量（SEGMENT_ISOLATION_INVARIANTS）：
  S1 段失败隔离互不传染：任一段异常被捕获后其余段照常执行（timers.js:140 注释
     「三段各自 catch 互不传染」）。
  S2 失败必留痕禁裸 catch：补跑/段探测失败必须走注入的 on_failure 回调，否则
     「没跑」与「跑了失败」无法区分（timers.js:215 注释）。
  S3 报告/收尾段独立兜底 catch：前置段全败仍执行收尾段（:176-180 第 4 个独立 catch）。
  S4 catch-up 天然限流：MAX_AGE 内不补跑，重启再频繁也不重跑（:196 注释）。
  S5 补跑/定时双跑防：距下次调度时点不足 NEAR_SCHEDULE → 交给定时
     （护栏①，:197 注释）。
"""
from __future__ import annotations
from chiyu_kernel.errors import KernelError
from typing import Tuple

# ── 每日跑批时点（timers.js:135 RETRO_HOUR；运维调度配置非业务阈值，消费方可注入）──
RETRO_HOUR_DEFAULT = 2

# ── catch-up 判决（timers.js:199-207）───────────────────────────────────────
#: 最新报告距此刻超过该时长 → 补跑（stale）
CATCHUP_MAX_AGE_HOURS = 24
#: 距下次调度时点不足该时长 → 交给定时，不补跑（护栏①防双跑）
CATCHUP_NEAR_SCHEDULE_MS = 30 * 60 * 1000

#: 判决 reason 闭集（S4/S5/S2：ran=False 必带 reason）
CATCHUP_REASONS: Tuple[str, ...] = ("fresh", "stale", "near_schedule", "error")
#: 补跑执行 reason 哨兵
CATCHUP_REASON_STALE = "stale"

# ── 段隔离编排（runRetroOnce :141-182 结构范式；段名/段数由消费方注入）─────────
SEGMENT_ISOLATION_INVARIANTS: Tuple[str, ...] = (
    "S1_segment_fail_isolated",      # 段失败隔离互不传染
    "S2_failure_always_traced",      # 失败必留痕禁裸 catch
    "S3_finalizer_independent_catch",  # 收尾段独立兜底 catch
    "S4_catchup_rate_limited",       # catch-up MAX_AGE 内天然限流
    "S5_no_double_run_near_schedule",  # 近时点护栏防补跑/定时双跑
)


class SchedulerError(KernelError):
    code = "CONTRACT_VIOLATION"
    """scheduler 判决核参数错误（非法时点/非法 now 等）。fail-closed。"""


__all__ = [
    "RETRO_HOUR_DEFAULT", "CATCHUP_MAX_AGE_HOURS", "CATCHUP_NEAR_SCHEDULE_MS",
    "CATCHUP_REASONS", "CATCHUP_REASON_STALE",
    "SEGMENT_ISOLATION_INVARIANTS", "SchedulerError",
]
