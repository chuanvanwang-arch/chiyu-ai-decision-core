"""Batch-5 守卫测试：调度判决核（scheduler_core）+ 零 LLM 夜报核（nightly_report）。

判据锚点以 CRM 源码 file:line 对拍（见各用例注释）：
- next_run_at            ↔ CRM timers.js:185-190 nextRetroAt（时点参数化）
- catchup_verdict        ↔ CRM timers.js:199-207（stale/fresh/near_schedule 三态）
- run_segments           ↔ CRM timers.js:141-182 runRetroOnce（段隔离互不传染 S1-S3）
- collect_segments       ↔ CRM nightlyReport.js:27-41（null 容错 R2）
- extract_retro_metrics  ↔ CRM nightlyReport.js:57-77（双形态 summary 权威 R3）
- render_nightly_markdown ↔ CRM nightlyReport.js:80-147（零 LLM R1 + 漂移诚实 R4）
- aggregate_report_metrics ↔ CRM nightlyReport.js:161-170（insufficient 不计 drift）
"""
import asyncio

import pytest

from chiyu_kernel import api, nightly_report, scheduler_core
from chiyu_kernel.contract import (
    CATCHUP_MAX_AGE_HOURS,
    CATCHUP_NEAR_SCHEDULE_MS,
    CATCHUP_REASONS,
    CATCHUP_REASON_STALE,
    FAIL_CONFIDENCE_THRESHOLD_DEFAULT,
    NightlyReportError,
    REPORT_INVARIANTS,
    REPORT_SEGMENTS,
    RETRO_HOUR_DEFAULT,
    SchedulerError,
    SEGMENT_ISOLATION_INVARIANTS,
)
from chiyu_kernel.nightly_report import (
    aggregate_report_metrics,
    collect_segments,
    extract_retro_metrics,
    format_patch,
    render_nightly_markdown,
)
from chiyu_kernel.scheduler_core import catchup_verdict, next_run_at, run_segments

DAY = 86400000
HOUR = 3600000


def _day_start(ms: float) -> float:
    return (ms // DAY) * DAY


# ── 契约闭集 ─────────────────────────────────────────────────────────────────
def test_contract_closed_sets():
    assert CATCHUP_MAX_AGE_HOURS == 24
    assert CATCHUP_NEAR_SCHEDULE_MS == 30 * 60 * 1000
    assert set(CATCHUP_REASONS) == {"fresh", "stale", "near_schedule", "error"}
    assert RETRO_HOUR_DEFAULT == 2
    assert set(REPORT_SEGMENTS) == {"retro", "routing", "param"}
    assert FAIL_CONFIDENCE_THRESHOLD_DEFAULT == 0.7   # R5：与 D3 同源，禁换 0.79
    assert len(SEGMENT_ISOLATION_INVARIANTS) == 5     # S1-S5
    assert len(REPORT_INVARIANTS) == 5                # R1-R5


def test_facade_reexports_same_objects():
    assert api.next_run_at is scheduler_core.next_run_at
    assert api.render_nightly_markdown is nightly_report.render_nightly_markdown
    assert api.SEGMENT_ISOLATION_INVARIANTS == SEGMENT_ISOLATION_INVARIANTS
    assert api.REPORT_INVARIANTS == REPORT_INVARIANTS


# ── next_run_at（timers.js:185-190）──────────────────────────────────────────
def test_next_run_at_roll_to_next_day():
    t0 = _day_start(1000 * DAY) + 10 * HOUR      # 某日 10:00
    nxt = next_run_at(t0)                         # 缺省 02:00 已过 → 次日 02:00
    assert nxt == _day_start(1000 * DAY) + DAY + 2 * HOUR
    # 时点未过 → 今日
    t1 = _day_start(1000 * DAY) + 1 * HOUR
    assert next_run_at(t1) == _day_start(1000 * DAY) + 2 * HOUR
    # 恰好等于时点 → 顺延次日（CRM 语义 next <= t0）
    t2 = _day_start(1000 * DAY) + 2 * HOUR
    assert next_run_at(t2) == _day_start(1000 * DAY) + DAY + 2 * HOUR
    # 自定义时点 + 非法时点 fail-closed
    assert next_run_at(t1, hour=3) == _day_start(1000 * DAY) + 3 * HOUR
    with pytest.raises(SchedulerError):
        next_run_at(t1, hour=24)


# ── catchup_verdict（timers.js:199-207）──────────────────────────────────────
def test_catchup_verdict_three_states():
    now = 1000 * DAY + 10 * HOUR
    # fresh：24h 内 → 不跑（S4 天然限流）
    v = catchup_verdict(now - 5 * HOUR, now)
    assert v == {"ran": False, "reason": "fresh", "age_hours": 5.0}
    # stale：>24h 且远离下次时点 → 补跑
    nxt = next_run_at(now)
    if nxt - now >= CATCHUP_NEAR_SCHEDULE_MS:
        v = catchup_verdict(now - 48 * HOUR, now)
        assert v["ran"] is True and v["reason"] == CATCHUP_REASON_STALE
    # near_schedule：stale 但距下次时点 <30min → 交给定时（S5 防双跑）
    now2 = _day_start(now) + DAY + 2 * HOUR - 10 * 60 * 1000   # 次日 01:50
    v2 = catchup_verdict(now2 - 48 * HOUR, now2)
    assert v2 == {"ran": False, "reason": "near_schedule", "age_hours": 48.0}
    # 首启无记录 → 视为最陈旧（远离时点时补跑）
    v3 = catchup_verdict(None, now)
    assert v3["ran"] is True and v3["reason"] == "stale"


# ── run_segments 段隔离（timers.js:141-182，S1-S3）────────────────────────────
def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


def test_run_segments_isolation():
    failures = []

    async def seg_ok():
        return {"n": 1}

    async def seg_boom():
        raise RuntimeError("LLM timeout")

    async def fin(snap):
        return f"final:{len(snap['results'])}"

    out = _run(run_segments(
        {"retro": seg_boom, "routing": seg_ok, "param": seg_ok},
        on_failure=lambda name, e: failures.append((name, str(e))),
        finalizer=fin))
    # S1：复盘段失败不拖垮其余段
    assert out["results"] == {"retro": None, "routing": {"n": 1}, "param": {"n": 1}}
    assert out["failures"] == {"retro": "LLM timeout"}
    # S2：失败留痕
    assert failures == [("retro", "LLM timeout")]
    # S3：收尾段独立执行
    assert out["finalizer"] == "final:3" and out["finalizer_error"] is None


def test_run_segments_all_fail_finalizer_still_runs():
    async def boom():
        raise ValueError("x")

    async def fin(snap):
        return "saved"

    out = _run(run_segments({"a": boom, "b": boom}, finalizer=fin))
    assert out["results"] == {"a": None, "b": None}
    assert out["finalizer"] == "saved"       # 前置全败收尾仍执行
    # 收尾自身失败也兜底记录
    async def fin_boom(_snap):
        raise ValueError("io")
    out2 = _run(run_segments({"a": boom}, finalizer=fin_boom))
    assert out2["finalizer"] is None and out2["finalizer_error"] == "io"


# ── collect_segments（nightlyReport.js:27-41，R2）────────────────────────────
def test_collect_segments_null_tolerant():
    seg = collect_segments()
    assert seg["retro"] == {}
    assert seg["routing"]["errors"] == []
    assert seg["param"]["inspected"] == 0 and seg["param"]["items"] == []
    # param.items 贯穿（九尺子明细不丢）
    seg2 = collect_segments(None, None, {"inspected": 3, "items": [{"key": "rubric-x"}]})
    assert seg2["param"]["items"] == [{"key": "rubric-x"}]


# ── extract_retro_metrics（nightlyReport.js:57-77，R3）───────────────────────
def test_extract_retro_metrics_dual_form():
    # 实时形态：顶层 clusters + draft_patches + llm_enabled
    live = {"decisions_scanned": 12,
            "clusters": [{"llm_used": True, "confidence": 0.9,
                          "draft_patches": [{"target": "a", "from_value": 1, "to_value": 2}]},
                         {"llm_used": False, "root_cause_explanation": "LLM 超时"},
                         {"llm_used": True, "confidence": 0.5,
                          "root_cause_explanation": "低置信"}],
            "llm_enabled": True}
    m = extract_retro_metrics(live)
    assert m["total"] == 3 and m["ok"] == 2 and m["drift"] == 1
    assert m["draft_count"] == 1
    # fail_reasons：llm_used=False 或 confidence<0.7（缺省阈值）
    assert m["fail_reasons"] == ["LLM 超时", "低置信"]
    assert m["scanned"] == 12
    # 持久化形态（落库回读）：summary.* 权威——回读不归零（R3）
    persisted = {"run_at": "t",
                 "summary": {"clusters": 5, "llm_effective": 4, "drafts": 2,
                             "llm_enabled": True, "by_root_cause": {"R1": 1}},
                 "clusters": []}
    m2 = extract_retro_metrics(persisted)
    assert m2["total"] == 5 and m2["ok"] == 4 and m2["drift"] == 1
    assert m2["draft_count"] == 2 and m2["by_root_cause"] == {"R1": 1}
    # R5：阈值可注入——0.79 下 confidence=0.75 也算失败原因
    m3 = extract_retro_metrics(live, fail_confidence_threshold=0.79)
    assert "低置信" in m3["fail_reasons"]
    # R5 边界：confidence=0.75 恰在 0.7~0.79 区间——缺省 0.7 不得判失败
    # （D3 互替禁令：缺省阈值被静默换成 0.79 时此断言转红）
    boundary = {"clusters": [{"llm_used": True, "confidence": 0.75,
                              "root_cause_explanation": "中置信簇"}]}
    assert extract_retro_metrics(boundary)["fail_reasons"] == []


# ── format_patch / aggregate（nightlyReport.js:44-51,161-170）────────────────
def test_format_patch_and_aggregate():
    assert format_patch({"target": "a", "from_value": {"w": 1}, "to_value": {"w": 2}}) \
        == 'a：{"w": 1} → {"w": 2}'
    assert format_patch({"target": "b", "label": "调参"}) == "b → 调参"
    assert format_patch(None) == "方案草稿"
    m = {"total": 3, "ok": 2, "drift": 1, "draft_count": 2}
    routing = {"closed": 4, "patches": [{}], "insufficient": [{"experiment_id": "e1"}],
               "errors": ["x"]}
    param = {"inspected": 6, "healthy": 4, "drift": 2, "patches": [{}, {}]}
    agg = aggregate_report_metrics(m, routing, param)
    # CRM 口径：insufficient(1) 计入 total/失败行，不计入 drift
    assert agg == {"total_tasks": 3 + (4 + 1 + 1) + 6, "healthy": 2 + 4 + 4,
                   "drift": 1 + 1 + 2, "patches_count": 2 + 1 + 2}
    assert agg["drift"] == 4


# ── render_nightly_markdown（R1 零 LLM / R4 漂移诚实）────────────────────────
def test_render_nightly_drift_honest():
    retro = {"summary": {"clusters": 2, "llm_effective": 1, "drafts": 0,
                         "llm_enabled": False, "by_root_cause": {"降级": 1}},
             "clusters": [{"llm_used": False, "root_cause_explanation": "LLM 超时"},
                          {"llm_used": True, "confidence": 0.9}]}
    param = {"inspected": 3, "healthy": 1, "drift": 2, "patches": [],
             "items": [{"key": "rubric-w", "param": "weight", "current": 0.8,
                        "health": "drift", "verdict": "PENDING"}]}
    md = render_nightly_markdown("20261014", retro, None, param,
                                 generated_at="2026-10-14T08:00:00Z")
    # R1：纯模板——零额外 LLM（结构断言）
    assert md.startswith("# 夜批运行报告 20261014")
    assert "## ① 决策复盘" in md and "## ② 路由收口" in md and "## ③ 参数体检" in md
    # R4：drift=2 且 patches=[] → 必须显示「需人工研判」而非「全部健康」
    assert "已漂移 2 项但暂无自动建议值" in md
    assert "全部健康" not in md
    # 九尺子参数快照可见
    assert "rubric-w.weight" in md
    # 根因分布与失败原因
    assert "降级 1" in md and "LLM 超时" in md
    # patches 非空时正常列出建议值（此时不得出现「需人工研判」）
    param2 = dict(param, patches=[{"target": "k", "from_value": 1, "to_value": 2, "risk": "HIGH"}])
    md2 = render_nightly_markdown("d", None, None, param2)
    assert "→ 建议 2" in md2 and "需人工研判" not in md2
    # R2：全空段不崩
    md3 = render_nightly_markdown("d")
    assert "## ① 决策复盘" in md3 and "无（全部健康）" in md3
