"""agent_runtime —— agent 运行时纯函数判据核（Batch-4b，上收自 CRM agent/*）。

零 DB / 零副作用 / 零总线接线；agent 名、skill 白名单、矩阵行、KG 服务层集合
全部由消费方注入。判据锚点见 contract/agent_runtime.py 与 CRM file:line。
"""
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence

from ..contract.agent_runtime import (
    AgentRuntimeError,
    COMPLIANCE_JOIN_PRIORITY,
    COMPLIANCE_MEMORY_PHASE,
    COMPLIANCE_PENDING,
    COMPLIANCE_SKILL_PHASES,
    COMPLIANCE_SUCCESS_MARKERS,
    DEDUP_EMPTY_SENTINEL,
    DEFAULT_COOLDOWN_MS,
    GLASSBOX_AXIS_DEFAULT,
    KG_LAYER_ORDER,
    TRIGGER_SOURCES,
    TRIGGER_SOURCE_DEFAULT,
)

__all__ = [
    "match_trigger", "dedup_key_for", "cooldown_verdict",
    "build_glass_box", "join_keys_of", "judge_contract",
    "kg_convergence_gate", "l3_degraded_guard", "resolve_runtime_layers",
]


# ── 三源触发匹配（CRM eventTrigger.js:89-103，A1 fail-closed）────────────────
def match_trigger(
    desc: Mapping[str, Any],
    matrix: Sequence[Mapping[str, Any]],
    allowed_skills: Sequence[str],
    *,
    enabled: bool = True,
) -> Optional[Mapping[str, Any]]:
    """source+domain+type+entity_type 四元组精确匹配；命中后只读白名单闸。

    - enabled=False 或空矩阵 → None
    - 行 source 缺省视为 'event'（向后兼容，CRM :89 注释）
    - 命中但 skill 不在 allowed_skills → None（**留痕由调用方**：reason=not-readonly；
      foundation 纯函数不触总线，fail-closed 语义在契约 A1 登记）
    """
    if not enabled or not matrix:
        return None
    src = desc.get("source") or TRIGGER_SOURCE_DEFAULT
    if src not in TRIGGER_SOURCES:
        raise AgentRuntimeError(f"unknown trigger source: {src!r}")
    for row in matrix:
        if ((row.get("source") or TRIGGER_SOURCE_DEFAULT) == src
                and row.get("domain") == desc.get("domain")
                and row.get("type") == desc.get("type")
                and row.get("entity_type") == desc.get("entity_type")):
            if row.get("skill_slug") not in set(allowed_skills):
                return None  # A1：非只读白名单，拒绝（留痕在调用方接线层）
            return row
    return None


# ── 去重键（CRM eventTrigger.js:114-117）────────────────────────────────────
def dedup_key_for(match: Mapping[str, Any], payload: Mapping[str, Any]) -> str:
    """`entity_id:intent:val`；dedup_field 取尾段，空值→'new'（每次都算新）。"""
    field = match.get("dedup_field")
    val = ""
    if field:
        tail = str(field).split(".")[-1]
        val = payload.get(tail)
        val = "" if val is None else str(val)
    return f"{payload.get('entity_id')}:{match.get('intent')}:{val or DEDUP_EMPTY_SENTINEL}"


# ── 冷却判决（CRM eventTrigger.js:123-129，A6）──────────────────────────────
def cooldown_verdict(
    last_ts: Optional[float],
    now_ms: Optional[float] = None,
    cooldown_ms: int = DEFAULT_COOLDOWN_MS,
) -> Dict[str, Any]:
    """内存冷却纯判决：窗口内 → skip_cooldown（留痕由调用方）；否则 dispatch。

    last_ts=None（首见/进程重启后 Map 失效）→ dispatch（DB 去重为主，语义 A2）。
    """
    now = now_ms if now_ms is not None else time.time() * 1000
    if last_ts is not None and (now - last_ts) < cooldown_ms:
        return {"verdict": "skip_cooldown", "reason": "cooldown",
                "remaining_ms": cooldown_ms - (now - last_ts)}
    return {"verdict": "dispatch", "reason": None, "remaining_ms": 0}


# ── glassBox 可解释推理链（CRM glassBox.js:10-20，A3）────────────────────────
def build_glass_box(
    *,
    score: Any,
    rule_ref: str,
    signals: Optional[Sequence[Any]] = None,
    axis: str = GLASSBOX_AXIS_DEFAULT,
) -> Dict[str, Any]:
    """脏信号过滤（非 str 且无 type 丢弃，trace 项数=有效信号数）；无信号不抛错。"""
    names: List[str] = []
    for sg in (signals or []):
        if isinstance(sg, str):
            if sg:
                names.append(sg)
        elif isinstance(sg, Mapping) and sg.get("type"):
            names.append(str(sg["type"]))
    trace = [{"signal": n, "rule_ref": rule_ref, "j_score": score} for n in names]
    joined = "、".join(names) if names else "无信号"
    return {
        "judge": {"axis": axis, "rule_ref": rule_ref, "j_score": score},
        "trace": trace,
        "why_narrative": f"因 {joined} 命中 {rule_ref} 判定为目标客户（j_score={score}）",
    }


# ── 契约合规三维（CRM contractMonitor.js:21-62，A4）─────────────────────────
def _facts(episode: Mapping[str, Any]) -> Dict[str, Any]:
    cf = episode.get("context_facts")
    if cf is None:
        return {}
    if isinstance(cf, str):
        import json
        try:
            return json.loads(cf)
        except (ValueError, TypeError):
            return {}
    return dict(cf)


def join_keys_of(contract: Mapping[str, Any]) -> List[str]:
    """稳定键优先回退标题（CRM :21-28；去重保序）。"""
    keys: List[str] = []
    for f in COMPLIANCE_JOIN_PRIORITY:
        v = contract.get(f)
        if v and v not in keys:
            keys.append(v)
    return keys


def judge_contract(
    contract: Mapping[str, Any],
    episodes: Sequence[Mapping[str, Any]],
    success_marker: Optional[str] = None,
) -> Dict[str, Any]:
    """三维判定：skill_ok / memory_ok / success（无人工标记恒 'pending'，A4）。

    - skill_ok：契约声明 skills ⊆ skill phase episodes 的 facts.skill 并集
    - memory_ok：knowledge_scope.layers ⊆ context-injected episodes 的
      knowledge_layers_read 并集
    - success：marker∈{pass,fail} 时取 marker，否则 'pending'
    """
    if success_marker is not None and success_marker not in COMPLIANCE_SUCCESS_MARKERS:
        raise AgentRuntimeError(f"invalid success marker: {success_marker!r}")
    skill_eps = [e for e in (episodes or []) if e.get("phase") in COMPLIANCE_SKILL_PHASES]
    skill_ok = all(
        any(_facts(e).get("skill") == s for e in skill_eps)
        for s in (contract.get("skills") or [])
    )
    ctx_eps = [e for e in (episodes or []) if e.get("phase") == COMPLIANCE_MEMORY_PHASE]
    read_layers = set()
    for e in ctx_eps:
        kl = _facts(e).get("knowledge_layers_read")
        if isinstance(kl, (list, tuple, set)):
            read_layers.update(kl)
    required = ((contract.get("knowledge_scope") or {}).get("layers") or [])
    memory_ok = all(l in read_layers for l in required)
    keys = join_keys_of(contract)
    return {
        "task": contract.get(COMPLIANCE_JOIN_PRIORITY[0]) or contract.get(COMPLIANCE_JOIN_PRIORITY[1]),
        "agent": contract.get("agent"),
        "skill_ok": skill_ok,
        "memory_ok": memory_ok,
        "success": success_marker if success_marker in COMPLIANCE_SUCCESS_MARKERS else COMPLIANCE_PENDING,
        "join_key": keys[0] if keys else None,
    }


# ── KG 收敛闸门（CRM agents.js:14-64，A5）───────────────────────────────────
def _kg_ceiling(spec: Mapping[str, Any]) -> int:
    t = ((spec.get("capabilities") or {}).get("kgTarget"))
    if not t:
        return len(KG_LAYER_ORDER) - 1
    top = t[-1] if isinstance(t, (list, tuple)) else t
    idx = KG_LAYER_ORDER.index(top) if top in KG_LAYER_ORDER else -1
    return idx if idx != -1 else len(KG_LAYER_ORDER) - 1


def kg_convergence_gate(
    spec: Mapping[str, Any], kg_served: Sequence[str],
) -> Dict[str, Any]:
    """运行时层级收敛：effective = declared ∩ served（served 注入，A5）。

    served 内部再按 kg_target 天花板截断；dropped 非空 → triggered（装配失败）。
    """
    declared = list(((spec.get("capabilities") or {}).get("knowledgeScope") or {}).get("layers") or [])
    ceiling = _kg_ceiling(spec)
    served = [l for l in (kg_served or []) if l in KG_LAYER_ORDER
              and KG_LAYER_ORDER.index(l) <= ceiling]
    effective = [l for l in declared if l in served]
    dropped = [l for l in declared if l not in effective]
    triggered = len(dropped) > 0
    target = (spec.get("capabilities") or {}).get("kgTarget")
    return {
        "ok": not triggered,
        "declared": declared,
        "target": target,
        "effective": effective,
        "dropped": dropped,
        "triggered": triggered,
        "detail": (f"收敛 {('/'.join(dropped))}（served={'/'.join(kg_served or [])},"
                   f"kg_target={target if target is not None else '无'}）"
                   if triggered else "ok"),
    }


def l3_degraded_guard(
    spec: Mapping[str, Any], kg_served: Sequence[str],
) -> Dict[str, Any]:
    """降级一致性守护：声明层含 L3 且 L3 ∉ served → ok:False（CRM :14-18）。"""
    layers = ((spec.get("capabilities") or {}).get("knowledgeScope") or {}).get("layers") or []
    l3_stated = "L3" in layers
    l3_served = "L3" in set(kg_served or ())
    bad = l3_stated and not l3_served
    return {"ok": not bad, "detail": "声明L3但KG降级" if bad else "ok"}


def resolve_runtime_layers(
    spec: Mapping[str, Any], kg_served: Sequence[str],
) -> List[str]:
    """运行时强制注入层 = 收敛闸门 effective（防契约层静默误判，CRM :62-64）。"""
    return kg_convergence_gate(spec, kg_served)["effective"]
