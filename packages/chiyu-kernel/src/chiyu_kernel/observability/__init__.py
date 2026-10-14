"""observability —— 监控底座纯函数判据核（Batch-4a，上收自 CRM monitor/*）。

零 DB / 零副作用；域值（闸门名/渠道名/来源名）由消费方注入。
全部判据锚点见 contract/observability.py 模块注释与 CRM file:line。
"""
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from ..contract.observability import (
    ACCURACY_ACCURATE_FROM,
    ACCURACY_INACCURATE_FROM,
    ATTRIBUTION_BENIGN,
    DEMO_EDGE_SOURCES_DEFAULT,
    EXPORT_GATE_BLOCKING_TYPES,
    NEGATIVE_PREDICATE_TYPES,
    ObservabilityError,
)

__all__ = [
    "classify_attribution", "accuracy_bucket", "aggregate_gate_metrics",
    "delivery_success_rate", "classify_negative_predicates",
    "compute_enrichment_rate", "aggregate_enrichment",
    "is_demo_edge_source", "is_runtime_edge_source", "split_edges_by_caliber",
    "edge_caliber_count", "runtime_edges_only",
    "FailureCounter", "blocks_export_gate",
]


# ── 归因四类交叉（CRM monitorStore.js:88-97）────────────────────────────────
def classify_attribution(a: Optional[Mapping[str, Any]]) -> Optional[str]:
    """必填齐缺 × 准确率 2×2 交叉 → 四类之一或 None（良性不计入错误类）。

    - a["required_fill"]["missing"] 非空 ⇒ 必填缺
    - a["accuracy_signal"]=="inaccurate" 或 a["category"]=="inference_bias" ⇒ 不准
    - 必填齐 + level=="warn" ⇒ context_insufficient（非阻断）
    """
    rf = (a or {}).get("required_fill") or {}
    missing = len(rf.get("missing") or []) > 0
    inaccurate = ((a or {}).get("accuracy_signal") == "inaccurate"
                  or (a or {}).get("category") == "inference_bias")
    if not missing and inaccurate:
        return "inference_bias"
    if missing and inaccurate:
        return "input_error"
    if missing and not inaccurate:
        return "input_missing"
    if not missing and (a or {}).get("level") == "warn":
        return "context_insufficient"
    return ATTRIBUTION_BENIGN


# ── 准确率三态桶（CRM monitorStore.js:138-143）──────────────────────────────
def accuracy_bucket(human_disposition: Optional[str]) -> str:
    """human_disposition → accurate / inaccurate / pending（空与其他非空都算 pending）。"""
    if human_disposition in ACCURACY_ACCURATE_FROM:
        return "accurate"
    if human_disposition in ACCURACY_INACCURATE_FROM:
        return "inaccurate"
    return "pending"


# ── 闸门指标聚合（CRM monitorStore.js:49-57 纯函数化）───────────────────────
def aggregate_gate_metrics(states: Iterable[str]) -> Dict[str, int]:
    """状态行序列 → {total, autonomous, escalated, human}。

    AUTONOMOUS→autonomous；HUMAN→human；REQUIRED/ESCALATED→escalated；
    未登记状态计入 total 但不入桶（与 CRM GROUP BY 后聚合口径一致）。
    """
    agg = {"total": 0, "autonomous": 0, "escalated": 0, "human": 0}
    for s in states:
        agg["total"] += 1
        if s == "AUTONOMOUS":
            agg["autonomous"] += 1
        elif s == "HUMAN":
            agg["human"] += 1
        elif s in ("REQUIRED", "ESCALATED"):
            agg["escalated"] += 1
    return agg


# ── 投递成功率（CRM signalMetrics.js:31，防假绿 O1）─────────────────────────
def delivery_success_rate(sent: int, failed: int) -> Optional[float]:
    """attempted>0 → sent/attempted；attempted=0 → None（无尝试≠100%）。"""
    attempted = (sent or 0) + (failed or 0)
    if attempted <= 0:
        return None
    return (sent or 0) / attempted


# ── 负向判据两级分类（CRM signalMetrics.js:141-199 判据核纯函数化）────────────
def classify_negative_predicates(
    channels_enabled: Sequence[str],
    channel_stats: Mapping[str, Mapping[str, int]],
    *,
    gen_fired: int = 0,
    gen_landed: int = 0,
    top_errors: Optional[Mapping[str, str]] = None,
    top_error_counts: Optional[Mapping[str, int]] = None,
) -> List[Dict[str, Any]]:
    """渠道启用集 × 窗口统计 → 负向判据告警列表（纯函数核）。

    - 渠道启用且零 sent：attempted==0 → delivery_silent（真静默，参与出口闸）；
      attempted>0 → delivery_undelivered（附首位原因 top_error/top_error_count）。
    - gen_fired>0 且 gen_landed==0 → gen_silent（与渠道配置无关，恒判——
      CRM signalMetrics.js:185 注释：配置缺失绝不连带跳过判据 B）。
    - channels_enabled 为 None/空 时不判渠道判据（配置缺失不判、留痕由调用方），
      但 gen_silent **恒判**（O3/A 同族：判据自己制造假绿是本项目最忌讳的误归因）。
    """
    alerts: List[Dict[str, Any]] = []
    if channels_enabled:
        for name in channels_enabled:
            st = channel_stats.get(name) or {}
            sent = int(st.get("sent") or 0)
            if sent != 0:
                continue
            attempted = int(st.get("attempted") or 0)
            if attempted == 0:
                alerts.append({"type": "delivery_silent", "channel": name,
                               "sent": 0, "attempted": 0})
            else:
                top = (top_errors or {}).get(name)
                alerts.append({"type": "delivery_undelivered", "channel": name,
                               "sent": 0, "attempted": attempted,
                               "top_error": top,
                               "top_error_count": int((top_error_counts or {}).get(name) or 0)})
    if gen_fired > 0 and gen_landed == 0:
        alerts.append({"type": "gen_silent", "fired": gen_fired})
    for a in alerts:
        if a["type"] not in NEGATIVE_PREDICATE_TYPES:  # pragma: no cover - 闭集自检
            raise ObservabilityError(f"unknown predicate type: {a['type']}")
    return alerts


# ── 富集命中率（CRM enrichmentMetrics.js，防假绿 O2）────────────────────────
def compute_enrichment_rate(enriched: int, with_contacts: int) -> Dict[str, Any]:
    """分母恒真实：enriched>0 才计率；空记录不虚造命中率。"""
    denominator = enriched if (enriched or 0) > 0 else 0
    rate = (with_contacts / denominator) if denominator > 0 else 0
    return {"rate": rate, "hits": with_contacts, "denominator": denominator}


def aggregate_enrichment(records: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    """多源累计：cost/calls/hits 分别求和再算总率（聚合顺序无关，确定性）。"""
    total_cost = calls = hits = 0
    for r in records or []:
        total_cost += r.get("cost") or 0
        calls += r.get("calls") or 0
        hits += r.get("hits") or 0
    out = compute_enrichment_rate(calls, hits)
    out["total_cost"] = total_cost
    out["calls"] = calls
    return out


# ── 边来源双口径（CRM edgeSource.js，O4）────────────────────────────────────
def is_demo_edge_source(source: Any, demo_sources: Sequence[str] = DEMO_EDGE_SOURCES_DEFAULT) -> bool:
    return source in demo_sources


def is_runtime_edge_source(source: Any, demo_sources: Sequence[str] = DEMO_EDGE_SOURCES_DEFAULT) -> bool:
    """NULL/None 不计入真实供给（O4）；演示来源之外为运行时边。"""
    if source is None:
        return False
    return not is_demo_edge_source(source, demo_sources)


def split_edges_by_caliber(
    edges: Iterable[Mapping[str, Any]], demo_sources: Sequence[str] = DEMO_EDGE_SOURCES_DEFAULT,
) -> Dict[str, List[Mapping[str, Any]]]:
    """拆双组不修改原数组：{runtime: [...], demo: [...]}。"""
    runtime: List[Mapping[str, Any]] = []
    demo: List[Mapping[str, Any]] = []
    for e in edges or []:
        if is_runtime_edge_source((e or {}).get("source"), demo_sources):
            runtime.append(e)
        else:
            demo.append(e)
    return {"runtime": runtime, "demo": demo}


def edge_caliber_count(
    edges: Iterable[Mapping[str, Any]], demo_sources: Sequence[str] = DEMO_EDGE_SOURCES_DEFAULT,
) -> Dict[str, int]:
    """双口径计数 {runtime: N, demo: M}——看板分母只取 runtime（防演示边假绿）。"""
    parts = split_edges_by_caliber(edges, demo_sources)
    return {"runtime": len(parts["runtime"]), "demo": len(parts["demo"])}


def runtime_edges_only(
    edges: Iterable[Mapping[str, Any]], demo_sources: Sequence[str] = DEMO_EDGE_SOURCES_DEFAULT,
) -> List[Mapping[str, Any]]:
    return split_edges_by_caliber(edges, demo_sources)["runtime"]


# ── 失败计数器（CRM busFailures.js，O6 单一实现防判据分裂）────────────────────
class FailureCounter:
    """内存失败计数（零依赖可无 DB 单测）：失败可见可查可复盘，禁静默吞错。

    语义对齐 busFailures.js：record 累计并返回 {kind, count}；get 聚合为字典
    （无记录 kind 不出现，读方兜底 0）；reset 仅供测试隔离。
    """

    def __init__(self) -> None:
        self._by_kind: Dict[str, int] = {}

    def record(self, kind: str, error: Any = None) -> Dict[str, Any]:
        self._by_kind[kind] = self._by_kind.get(kind, 0) + 1
        return {"kind": kind, "count": self._by_kind[kind]}

    def get(self) -> Dict[str, int]:
        return dict(self._by_kind)

    def reset(self) -> None:
        self._by_kind.clear()


# 出口闸语义（O5）：供消费方判断哪些判据可阻断
def blocks_export_gate(predicate_type: str) -> bool:
    return predicate_type in EXPORT_GATE_BLOCKING_TYPES
