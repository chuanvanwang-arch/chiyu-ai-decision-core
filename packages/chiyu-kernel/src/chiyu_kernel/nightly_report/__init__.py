"""nightly_report —— 零 LLM 夜报纯函数判据核（Batch-5，上收自 CRM report/nightlyReport.js）。

零 DB / 零文件 IO / 零 LLM 调用；报告标题/日期/落盘由消费方注入。
判据锚点见 contract/nightly_report.py 与 CRM file:line。
"""
import json
from typing import Any, Dict, List, Mapping, Optional

from ..contract.nightly_report import (
    FAIL_CONFIDENCE_THRESHOLD_DEFAULT,
    RUBRIC_ITEM_PREFIX,
)

__all__ = [
    "collect_segments", "extract_retro_metrics", "format_patch",
    "aggregate_report_metrics", "render_nightly_markdown",
]


# ── 三段归一化容错（CRM nightlyReport.js:27-41，R2）──────────────────────────
def collect_segments(
    retro: Optional[Mapping[str, Any]] = None,
    routing: Optional[Mapping[str, Any]] = None,
    param: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """任一段 null → 空结构（防渲染崩）；param.items 贯穿（九尺子明细不丢）。"""
    p = param or {}
    return {
        "retro": dict(retro or {}),
        "routing": dict(routing or {"closed": 0, "patches": [],
                                    "next_arms": [], "insufficient": [], "errors": []}),
        "param": {
            "inspected": p.get("inspected", 0),
            "healthy": p.get("healthy", 0),
            "drift": p.get("drift", 0),
            "unknown": p.get("unknown", 0),
            "patches": p.get("patches") if isinstance(p.get("patches"), list) else [],
            "items": p.get("items") if isinstance(p.get("items"), list) else [],
        },
    }


# ── 复盘段统一指标（CRM nightlyReport.js:57-77，R3 双形态 summary 权威）────────
def extract_retro_metrics(
    retro: Optional[Mapping[str, Any]] = None,
    *,
    fail_confidence_threshold: float = FAIL_CONFIDENCE_THRESHOLD_DEFAULT,
) -> Dict[str, Any]:
    """实时/持久化双形态统一提取：summary.* 权威、clusters 明细、缺失回退顶层。

    fail_confidence_threshold：失败原因过滤阈值（R5 独立注入，CRM 语境缺省 0.7）。
    """
    retro = retro or {}
    summary = retro.get("summary") or {}
    clusters: List[Mapping[str, Any]] = (
        retro.get("clusters") if isinstance(retro.get("clusters"), list) else []) or []
    total = summary.get("clusters")
    if total is None:
        total = len(clusters)
    llm_eff = summary.get("llm_effective")
    if llm_eff is None:
        llm_eff = sum(1 for c in clusters if c.get("llm_used") is True)
    ok = llm_eff
    drift = max(0, total - ok)
    drafts = summary.get("drafts")
    if drafts is None:
        drafts = 0
        if isinstance(retro.get("draft_patches"), list):
            drafts += len(retro["draft_patches"])
        drafts += sum(len(c.get("draft_patches") or []) for c in clusters
                      if isinstance(c.get("draft_patches"), list))
    llm_enabled = bool(summary.get("llm_enabled", retro.get("llm_enabled")))
    fail_reasons: List[str] = []
    for c in clusters:
        conf = c.get("confidence")
        low_conf = isinstance(conf, (int, float)) and conf < fail_confidence_threshold
        if c.get("llm_used") is False or low_conf:
            fail_reasons.append(c.get("root_cause_explanation")
                                or (f"场景 {c.get('scenario_id')} 未充分分析"
                                    if c.get("scenario_id") else "LLM 降级"))
    fail_reasons = [r for r in fail_reasons if r]
    by_root_cause = summary.get("by_root_cause")
    by_root_cause = by_root_cause if isinstance(by_root_cause, dict) else {}
    scanned = retro.get("decisions_scanned")
    scanned = scanned if isinstance(scanned, (int, float)) else None
    return {"total": total, "ok": ok, "drift": drift, "draft_count": drafts,
            "llm_enabled": llm_enabled, "llm_effective": llm_eff,
            "fail_reasons": fail_reasons, "by_root_cause": by_root_cause,
            "scanned": scanned}


# ── 处方文案（CRM nightlyReport.js:44-51 fmtPatch）───────────────────────────
def _j(v: Any) -> str:
    return json.dumps(v, ensure_ascii=False, sort_keys=True)


def format_patch(p: Optional[Mapping[str, Any]]) -> str:
    if not p:
        return "方案草稿"
    target = p.get("target") if p.get("target") is not None else p.get("scenario_id", "实验")
    if "from_value" in p and "to_value" in p:
        return f"{target}：{_j(p.get('from_value'))} → {_j(p.get('to_value'))}"
    return f"{target} → {p.get('label') or p.get('knob') or '方案草稿'}"


# ── 报告聚合指标（CRM nightlyReport.js:161-170 纯化）─────────────────────────
def aggregate_report_metrics(retro_m: Mapping[str, Any],
                             routing: Mapping[str, Any],
                             param: Mapping[str, Any]) -> Dict[str, int]:
    """三段统一计数。CRM 口径：insufficient 计入 total 与失败行、**不计入 drift**
    （drift = 复盘 drift + routing errors + param drift）；patches = 复盘 drafts
    + routing patches + param patches。"""
    r_closed = routing.get("closed") or 0
    r_insufficient = len(routing.get("insufficient") or [])
    r_errors = len(routing.get("errors") or [])
    r_patches = len(routing.get("patches") or [])
    p_inspected = param.get("inspected") or 0
    p_healthy = param.get("healthy") or 0
    p_drift = param.get("drift") or 0
    p_patches = len(param.get("patches") or [])
    total_tasks = (retro_m.get("total") or 0) + (r_closed + r_insufficient + r_errors) + p_inspected
    healthy = (retro_m.get("ok") or 0) + r_closed + p_healthy
    drift = (retro_m.get("drift") or 0) + r_errors + p_drift
    patches_count = (retro_m.get("draft_count") or 0) + r_patches + p_patches
    return {"total_tasks": total_tasks, "healthy": healthy,
            "drift": drift, "patches_count": patches_count}


# ── 纯模板渲染（CRM nightlyReport.js:80-147，R1 零 LLM / R4 漂移诚实）──────────
def render_nightly_markdown(
    date: str,
    retro: Optional[Mapping[str, Any]] = None,
    routing: Optional[Mapping[str, Any]] = None,
    param: Optional[Mapping[str, Any]] = None,
    *,
    fail_confidence_threshold: float = FAIL_CONFIDENCE_THRESHOLD_DEFAULT,
    generated_at: str = "",
) -> str:
    """三段结构渲染：仅聚合既有结果，不二次调用模型（R1）。"""
    seg = collect_segments(retro, routing, param)
    R = extract_retro_metrics(seg["retro"],
                              fail_confidence_threshold=fail_confidence_threshold)
    G, P = seg["routing"], seg["param"]
    lines: List[str] = []
    lines.append(f"# 夜批运行报告 {date}")
    lines.append("")
    lines.append("> 自动生成于夜批。复盘段由 LLM 产出归因；本报告仅汇总三段既有结果，不二次调用模型。")
    lines.append("")
    # ① 决策复盘
    lines.append("## ① 决策复盘")
    lines.append(f"- 运行总数（分析簇）：{R['total']}")
    if R["scanned"] is not None:
        lines.append(f"- 扫描决策总数：{R['scanned']}")
    lines.append(f"- 成功（LLM 生效簇）：{R['ok']}（llm_enabled={R['llm_enabled']}, llm_effective={R['llm_effective']}）")
    lines.append(f"- 失败（未获 LLM / 降级簇）：{R['drift']}")
    root_cause_str = "、".join(f"{k} {v}" for k, v in R["by_root_cause"].items())
    if root_cause_str:
        lines.append(f"- 根因分布：{root_cause_str}")
    lines.append(f"- 失败原因：{'；'.join(R['fail_reasons']) or '无'}")
    retro_drafts: List[Mapping[str, Any]] = []
    for c in (seg["retro"].get("clusters") or []):
        if isinstance(c, Mapping) and isinstance(c.get("draft_patches"), list):
            retro_drafts.extend(c["draft_patches"])
    if isinstance(seg["retro"].get("draft_patches"), list):
        retro_drafts.extend(seg["retro"]["draft_patches"])
    lines.append(f"- 建议调整措施：{'；'.join(format_patch(p) for p in retro_drafts) or '无'}")
    lines.append("")
    # ② 路由收口
    lines.append("## ② 路由收口")
    r_total = (G.get("closed") or 0) + len(G.get("insufficient") or []) + len(G.get("errors") or [])
    lines.append(f"- 运行总数：{r_total}")
    lines.append(f"- 成功（收口结论）：{G.get('closed') or 0}")
    lines.append(f"- 失败（错误/样本不足）：{len(G.get('errors') or []) + len(G.get('insufficient') or [])}")
    fails = [str(e) for e in (G.get("errors") or [])]
    fails += [f"样本不足:{e.get('experiment_id', e) if isinstance(e, Mapping) else e}"
              for e in (G.get("insufficient") or [])]
    lines.append(f"- 失败原因：{'；'.join(fails) or '无'}")
    routing_labels = [
        f"{p.get('target') if isinstance(p, Mapping) else '实验'} → 收口处方"
        for p in (G.get("patches") or [])]
    lines.append(f"- 建议调整措施：{'；'.join(routing_labels) or '无'}")
    lines.append("")
    # ③ 参数体检
    lines.append("## ③ 参数体检")
    lines.append(f"- 运行总数：{P.get('inspected', 0)}")
    lines.append(f"- 成功（healthy）：{P.get('healthy', 0)}")
    lines.append(f"- 失败（drift）：{P.get('drift', 0)}")
    lines.append("- 失败原因与建议调整措施：")
    patches = P.get("patches") or []
    if not patches:
        # R4：drift>0 但无自动建议值 → 需人工研判，禁误显示「全部健康」
        if (P.get("drift") or 0) > 0:
            lines.append(f"  - 已漂移 {P.get('drift')} 项但暂无自动建议值（需人工研判；见下方参数快照）")
        else:
            lines.append("  - 无（全部健康）")
    else:
        for p in patches:
            lines.append(f"  - {p.get('target')}：当前值 {_j(p.get('from_value'))} → 建议 {_j(p.get('to_value'))}（风险 {p.get('risk') or 'LOW'}）")
    # 参数快照（rubric 前缀——基座概念非域值）
    rubric_items = [it for it in (P.get("items") or [])
                    if str((it or {}).get("key") or "").startswith(RUBRIC_ITEM_PREFIX)]
    if rubric_items:
        lines.append(f"- 参数快照（{len(rubric_items)} 项）：")
        for it in rubric_items:
            cur = it.get("current")
            cur_s = "未配置" if cur is None else (_j(cur) if isinstance(cur, (dict, list)) else str(cur))
            lines.append(f"  - {it.get('key')}.{it.get('param')}：当前={cur_s}（{it.get('health')}/{it.get('verdict')}）")
    lines.append("")
    lines.append("---")
    lines.append(f"报告生成时间：{generated_at}")
    return "\n".join(lines)
