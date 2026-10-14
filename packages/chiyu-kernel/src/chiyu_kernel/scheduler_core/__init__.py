"""scheduler_core —— 定时调度纯函数判决核（Batch-5，上收自 CRM scheduler/timers.js）。

零 DB / 零定时器注册；任务名/时区/callable 全由消费方注入。
判据锚点见 contract/scheduler.py 与 CRM file:line。
"""
from typing import Any, Awaitable, Callable, Dict, Mapping, Optional
from ..contract.scheduler import (
    CATCHUP_MAX_AGE_HOURS,
    CATCHUP_NEAR_SCHEDULE_MS,
    CATCHUP_REASON_STALE,
    RETRO_HOUR_DEFAULT,
    SchedulerError,
)

__all__ = ["next_run_at", "catchup_verdict", "run_segments"]


# ── 下一个每日时点（CRM timers.js:185-190 nextRetroAt 参数化）────────────────
def next_run_at(now_ms: float, hour: int = RETRO_HOUR_DEFAULT, *,
                tz_offset_minutes: int = 0) -> float:
    """每日 hour:00 时点；今日已过 → 顺延次日（毫秒 epoch）。

    tz_offset_minutes：调用方时钟若为 UTC 而调度时点按本地时区，可传偏移
    （如 UTC+8 传 480）；缺省 0=now_ms 已是调度时区口径。
    """
    if not 0 <= hour <= 23:
        raise SchedulerError(f"invalid hour: {hour!r}")
    ms = now_ms + tz_offset_minutes * 60 * 1000
    day_start = (ms // 86400000) * 86400000
    target = day_start + hour * 3600000
    if target <= ms:
        target += 86400000
    return target - tz_offset_minutes * 60 * 1000


# ── catch-up 三态判决（CRM timers.js:199-207 判决核纯化）─────────────────────
def catchup_verdict(
    last_run_at: Optional[float],
    now_ms: float,
    hour: int = RETRO_HOUR_DEFAULT,
    *,
    max_age_hours: int = CATCHUP_MAX_AGE_HOURS,
    near_schedule_ms: int = CATCHUP_NEAR_SCHEDULE_MS,
) -> Dict[str, Any]:
    """补跑判决（IO——查最新 run_at——留消费方；此处只判决）。

    - last_run_at 距今 > max_age → {'ran': True, 'reason': 'stale'}（补跑）
    - < max_age → {'ran': False, 'reason': 'fresh'}（S4 天然限流）
    - stale 但距下次时点 < near_schedule → {'ran': False, 'reason': 'near_schedule'}
      （S5 护栏①：交给定时防双跑）
    - last_run_at=None（首启无记录）→ 视为 stale（「没跑过」是最陈旧状态）
    """
    age_ms = now_ms - (last_run_at or 0)
    if age_ms < max_age_hours * 3600000:
        return {"ran": False, "reason": "fresh",
                "age_hours": round(age_ms / 3600000, 1)}
    if next_run_at(now_ms, hour) - now_ms < near_schedule_ms:
        return {"ran": False, "reason": "near_schedule",
                "age_hours": round(age_ms / 3600000, 1)}
    return {"ran": True, "reason": CATCHUP_REASON_STALE,
            "age_hours": round(age_ms / 3600000, 1)}


# ── 段隔离编排范式（CRM timers.js:141-182 runRetroOnce 结构保证）──────────────
async def run_segments(
    segments: Mapping[str, Callable[[], Awaitable[Any]]],
    on_failure: Optional[Callable[[str, BaseException], Any]] = None,
    *,
    finalizer: Optional[Callable[[Dict[str, Any]], Awaitable[Any]]] = None,
) -> Dict[str, Any]:
    """N 段依次执行，每段独立 catch 互不传染（S1）；失败必留痕（S2）。

    - segments：{段名: 零参 async callable}（业务实现由消费方注入）
    - on_failure：失败留痕回调（注入 recordFailure 类实现；None 时仅收集）
    - finalizer：收尾段（S3 独立兜底 catch——前置段全败仍执行），接收
      {results, failures} 快照
    - 返回 {"results": {段名: 值|None}, "failures": {段名: str(错误)},
      "finalizer": 值|None, "finalizer_error": str|None}
    """
    results: Dict[str, Any] = {}
    failures: Dict[str, str] = {}
    for name, fn in segments.items():
        try:
            results[name] = await fn()
        except BaseException as e:  # noqa: BLE001 —— 段隔离即为此语义（S1）
            results[name] = None
            failures[name] = str(e)
            if on_failure is not None:
                try:
                    on_failure(name, e)
                except BaseException:  # 留痕回调自身失败不得传染（S1）
                    pass
    out: Dict[str, Any] = {"results": results, "failures": failures,
                           "finalizer": None, "finalizer_error": None}
    if finalizer is not None:
        try:
            out["finalizer"] = await finalizer({"results": results,
                                                "failures": failures})
        except BaseException as e:  # noqa: BLE001 —— S3 兜底
            out["finalizer_error"] = str(e)
    return out
