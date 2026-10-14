"""内核桥：把 chiyu_kernel 的真实原生工具暴露给前端 composer。

设计要点（与内核铁律一致）：
- 仅经 `chiyu_kernel.api` 门面 import，绝不碰内核内部路径。
- composer 的一次「发送」= 一次确定性 mini agent loop：
    S1 目标锚定 → S2 上下文装配(native-context-assemble)
                 → S3 红线校验(native-redline-check, 经 redline_guard 硬闸门)
                 → S4 九尺子评分 → S5 决策产出
- S3 若命中冻结红线集(META_REDLINES)，`redline_guard` 在工具执行前抛 GuardDenied，
  对话闭环**真实拦截**，与内核运行时行为一致（非前端模拟）。
- 零数据库依赖：`assemble()` 与 `meta_redline_hits()` 均为纯函数（机制层）。
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── 自包含路径：无论 cwd 在何处都能 import 内核/门户门面 ─────────────────────
_ROOT = Path(__file__).resolve().parent.parent.parent  # web/backend -> chiyu-foundation
for _p in (_ROOT / "packages" / "chiyu-kernel" / "src",
           _ROOT / "packages" / "chiyu-portal" / "src"):
    _pp = str(_p)
    if _pp not in sys.path:
        sys.path.insert(0, _pp)

from chiyu_kernel.api import register_native_tools, native_redline_guard  # noqa: E402
from chiyu_kernel.tools import ToolRegistry, GuardDenied  # noqa: E402

# ⛔ 仅门面 + 门户门面（渲染层唯一出口）
from chiyu_portal.api import (  # noqa: E402
    render_onboarding, render_conversation, mode_cards,
    level_cards, workflow_cards, direction_cards,
)

from chiyu_kernel.api import MODE_PRESETS  # noqa: E402  (门面已导出)

import llm_bridge  # noqa: E402  (Phase B LLM 桥，同目录模块)


# ── 四种模式 → 装配需求层（演示用，机制层映射）─────────────────────────────
_MODE_NEEDS: Dict[str, List[Dict[str, Any]]] = {
    "standard": [
        {"layer": "L1", "dims": ("semantics",)},
        {"layer": "L2", "dims": ("precedent",)},
        {"layer": "L3", "dims": ("operation",)},
        {"layer": "L4", "dims": ("governance",)},
    ],
    "creative": [
        {"layer": "L1", "dims": ("semantics",)},
        {"layer": "L2", "dims": ("precedent",)},
        {"layer": "L3", "dims": ("operation",)},
        {"layer": "L4", "dims": ("governance",)},
    ],
    "ptc": [
        {"layer": "L1", "dims": ("semantics",)},
        {"layer": "L3", "dims": ("operation",)},
    ],
    "minimal": [
        {"layer": "L1", "dims": ("semantics",)},
    ],
}

# 演示性供给侧：注入 L1 语义 + L3 操作，刻意缺 L2 历史 / L4 治理 → 体现真实缺口
_PROVIDED: Dict[str, List[Dict[str, str]]] = {
    "L1": [{"dim": "semantics", "key": "domain", "value": "已注入领域语义底座"}],
    "L3": [{"dim": "operation", "key": "task_state", "value": "任务态已就绪"}],
}


def _classify_actions(text: str) -> List[str]:
    """把用户消息映射为候选「动作名」（仅机制标识，零领域字面量）。

    命中 META_REDLINES 任一即触发内核红线硬闸门。
    """
    t = text
    actions: List[str] = []
    if any(k in t for k in ("放宽", "阈值", "放开", "打开限制", "调高自主权", "扩大权限")):
        actions.append("threshold_widen")
    if any(k in t for k in ("基线", "基座", "内核契约", "写入内核", "改契约")):
        actions.append("baseline_write")
    if any(k in t for k in ("自动应用红线", "绕过红线", "忽略红线", "放行红线", "跳过红线")):
        actions.append("redline_auto")
    if not actions:
        # 安全动作：仅读/装配，不触碰红线
        actions.extend(["run_report", "assemble_context"])
    return actions


# 工作流 id → 意图（由向导真实选择驱动，替代关键词猜测）
_WORKFLOW_INTENT: Dict[str, str] = {
    "decide": "决策辅助",
    "research": "调研检索",
    "automate": "任务编排",
    "build": "能力沉淀",
}

# 层级 id → 展示名（与 chiyu_portal.level_cards 对齐）
_LEVEL_LABEL: Dict[str, str] = {
    "single": "单点提效",
    "flow": "流程提效",
    "end2end": "端到端增值",
}


def _run_turn(text: str, mode: str, deep_think: bool, web_search: bool,
              direction: Optional[str] = None, workflow: Optional[str] = None,
              level: Optional[str] = None) -> Dict[str, Any]:
    """执行一次 mini agent loop，真实调用内核原生工具。"""
    reg = ToolRegistry()
    # profile 预留；当前原生工具不依赖领域档案
    register_native_tools(reg, profile=None)
    guard = native_redline_guard(profile=None)

    needs = _MODE_NEEDS.get(mode, _MODE_NEEDS["standard"])
    tool_calls: List[Dict[str, Any]] = []
    trace: List[Dict[str, Any]] = []

    # 意图：向导工作流真实选择优先；未选择时回退关键词推断
    if workflow and workflow in _WORKFLOW_INTENT:
        intent = _WORKFLOW_INTENT[workflow]
        intent_src = f"工作流={workflow}"
    else:
        intent = "决策辅助" if any(k in text for k in ("决策", "建议", "评估", "辅助")) else "通用任务"
        intent_src = "关键词推断"

    # S1 目标锚定：记录向导真实选择（方向 · 工作流 · 层级 · 模式四元组）
    sel_parts = []
    if direction:
        sel_parts.append(f"方向={direction}")
    if workflow:
        sel_parts.append(f"工作流={workflow}")
    if level:
        sel_parts.append(f"层级={_LEVEL_LABEL.get(level, level)}")
    sel_note = (" · " + " · ".join(sel_parts)) if sel_parts else " · 向导未透传"
    trace.append({
        "label": "S1 目标锚定",
        "note": f"模式={mode} · 意图={intent}({intent_src}){sel_note}"
                + (" · 深度思考" if deep_think else "")
                + (" · 联网搜索" if web_search else ""),
        "status": "pass",
    })

    # ── S2 上下文装配（native-context-assemble，high_risk=False）──
    ctx_args = {"needs": needs, "provided": _PROVIDED}
    ctx_result: Dict[str, Any] = {}
    try:
        ctx_result = dict(reg.execute("native-context-assemble", ctx_args,
                                      redline_guard=guard) or {})
        tool_calls.append({
            "name": "native-context-assemble",
            "args": ctx_args,
            "status": "ok",
            "result": ctx_result,
        })
        missing = list(ctx_result.get("missing", []))
        sup = ctx_result.get("supply_report", {})
        rate = sup.get("context_supply_rate") if isinstance(sup, dict) else None
        note = f"供给率 {rate}" if rate is not None else ""
        trace.append({
            "label": "S2 上下文装配",
            "note": (f"缺口 {len(missing)} 项" if missing else "全层命中") + (f" · {note}" if note else ""),
            "status": "warn" if missing else "pass",
        })
    except GuardDenied as e:  # 理论上 context 工具不会触发，保留一致性
        tool_calls.append({
            "name": "native-context-assemble",
            "args": ctx_args, "status": "blocked", "note": str(e),
        })
        trace.append({"label": "S2 上下文装配", "note": "被拦截", "status": "fail"})
        return _finalize(text, tool_calls, trace, blocked=True,
                         content="上下文装配被红线硬闸门拦截，已中止决策流程。")

    # ── S3 红线校验（native-redline-check，high_risk=True）──
    actions = _classify_actions(text)
    rl_args = {"actions": actions}
    redline_hit = False
    try:
        rl_result = dict(reg.execute("native-redline-check", rl_args,
                                     redline_guard=guard) or {})
        tool_calls.append({
            "name": "native-redline-check",
            "args": rl_args, "status": "ok", "result": rl_result,
            "note": "high_risk 工具经 redline_guard 硬闸门复核",
        })
        redline_hit = bool(rl_result.get("redline_hit"))
        trace.append({
            "label": "S3 红线校验",
            "note": f"{len(actions)} 个动作 · 命中 {len(rl_result.get('hits', []))}",
            "status": "pass" if not redline_hit else "fail",
        })
    except GuardDenied as e:
        redline_hit = True
        tool_calls.append({
            "name": "native-redline-check",
            "args": rl_args, "status": "blocked", "note": str(e),
        })
        trace.append({"label": "S3 红线校验", "note": "命中冻结红线集 · 已拦截", "status": "fail"})
        return _finalize(
            text, tool_calls, trace, blocked=True,
            content=("该操作命中本仓冻结红线集（meta_redline），内核 redline_guard 在工具执行前"
                     "直接抛 GuardDenied，对话闭环不予放行。请用合规路径替代。"))

    if redline_hit:
        return _finalize(text, tool_calls, trace, blocked=True,
                         content="红线命中，已中止后续评分与决策产出。")

    # ── S4 九尺子评分（演示性确定性映射，基于真实供给率）──
    # 原生工具返回 {facts, missing}（不含嵌套 supply_report），故由 missing/needs 推导
    n_needs = len(needs)
    n_missing = len(missing)
    rate = round((n_needs - n_missing) / n_needs, 4) if n_needs else 1.0
    safe = round(min(9.0, 6.5 + rate * 2.5), 1)
    risk = round(max(1.0, 4.0 - rate * 2.5), 1)
    trace.append({
        "label": "S4 九尺子评分",
        "note": f"safe {safe} / risk {risk}",
        "status": "pass",
    })

    # ── S5 决策产出（层级影响建议措辞）──
    missing = [m for m in ctx_result.get("missing", [])]
    if missing:
        advice = (f"建议：当前缺 {len(missing)} 项上下文（"
                  + "、".join(f"{m[0]}.{m[1]}" for m in missing)
                  + "），补全后进入人工复核。")
    else:
        advice = "上下文齐备，可直接进入自动决策路径（Phase B 接 LLM）。"
    level_hint = {
        "single": "单点场景：建议把本次取数-计算-输出沉淀为可复用 SKILL。",
        "flow": "跨岗位流程：建议启用编排与审批闸门（HITL）路由下一岗位。",
        "end2end": "端到端场景：建议走决策平台闭环（感知→认知→决策→执行）并保留人工审核。",
    }.get(level or "", "")
    if level_hint:
        advice += level_hint
    trace.append({"label": "S5 决策产出", "note": "已生成建议", "status": "pass"})
    content = (f"已为你装配分层上下文并跑通决策脊柱（模式={mode}）。"
               f"共调用 2 个本仓原生工具：上下文装配（供给率 {rate}）"
               f"与红线校验（0 命中）。{advice}")

    # ── Phase B：LLM 基于内核真实产出作答（DEEPSEEK_API_KEY 存在时启用）───────
    llm_info = llm_bridge.llm_chat(llm_bridge.build_phase_b_messages(
        text=text, mode=mode, intent=intent, supply_rate=rate,
        missing=missing, advice=advice, web_search=web_search))
    if llm_info.get("available") and llm_info.get("content"):
        content = llm_info["content"]
        tool_calls.append({
            "name": "phase-b-llm",
            "args": {"model": llm_info["model"],
                     "usage": llm_info.get("usage", {})},
            "status": "ok",
            "note": "LLM 基于内核 S1–S5 真实产出作答（deep_think="
                    + ("deepseek-reasoner" if deep_think else "deepseek-chat") + "）",
        })
    elif llm_info.get("error"):
        # 如实回落：确定性内容已在 content 中，不吞错误
        tool_calls.append({
            "name": "phase-b-llm",
            "args": {"model": llm_info.get("model")},
            "status": "skipped",
            "note": str(llm_info["error"])[:200],
        })
    if web_search:
        # 如实标注：DeepSeek API 无联网检索参数，本阶段未接通
        tool_calls.append({
            "name": "web-search",
            "args": {"enabled": True},
            "status": "skipped",
            "note": "联网搜索本阶段未接通（DeepSeek API 无检索参数），未执行检索",
        })

    return _finalize(text, tool_calls, trace, blocked=False, content=content,
                     llm={"used": bool(llm_info.get("available")),
                          "model": llm_info.get("model", ""),
                          "error": llm_info.get("error")})


def _finalize(text: str, tool_calls: List[Dict[str, Any]],
             trace: List[Dict[str, Any]], *, blocked: bool, content: str,
             llm: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "content": content,
        "toolCalls": tool_calls,
        "trace": trace,
        "blocked": blocked,
        "echo": text,
        "llm": llm or {"used": False, "model": ""},
    }


def run_turn(text: str, mode: str = "standard",
             deep_think: bool = False, web_search: bool = False,
             direction: Optional[str] = None, workflow: Optional[str] = None,
             level: Optional[str] = None) -> Dict[str, Any]:
    try:
        return _run_turn(text, mode, deep_think, web_search,
                         direction=direction, workflow=workflow, level=level)
    except Exception as e:  # 兜底：不让内核异常冒泡成 500 吞掉语义
        return {
            "content": f"内核调用异常：{e}",
            "toolCalls": [],
            "trace": [{"label": "内核调用", "note": str(e), "status": "fail"}],
            "blocked": True,
            "echo": text,
        }


# ── 引导式 / 对话页：复用 chiyu_portal 真实渲染层（打通证据）─────────────────
def portal_onboarding_html() -> str:
    res = render_onboarding()
    return res.html if res.ok else "<p>onboarding 渲染失败</p>"


def portal_conversation_html(goal: str, messages: List[Dict[str, str]]) -> str:
    events = [{"role": m.get("role", "user"), "content": m.get("content", "")}
              for m in messages]
    res = render_conversation(events=events, goal=goal)
    return res.html if res.ok else "<p>conversation 渲染失败</p>"


# ── Bootstrap：把内核真实能力序列化给前端 ──────────────────────────────────
def get_bootstrap() -> Dict[str, Any]:
    cards = mode_cards()  # 来自 chiyu_portal.onboarding，动态生成
    accent_map = {"standard": "green", "ptc": "amber",
                  "minimal": "cyan", "creative": "violet"}
    modes = []
    for c in cards:
        modes.append({
            "id": c["id"],
            "label": c["label"],
            "description": c["description"],
            "plugins": list(c["plugins"]),
            # 内核 minimal 模式 phase_b_backend 为 None；归一为展示文案，防前端对 null 调字符串方法
            "phaseBBackend": c["phase_b_backend"] or "无需 LLM（确定性）",
            "default": bool(c.get("default")),
            "accent": accent_map.get(c["id"], "green"),
        })

    # 原生工具清单（与 harness_native_tools 对齐）
    native_tools = [
        {"name": "native-context-assemble", "description": "装配 L1–L4 分层上下文",
         "high_risk": False},
        {"name": "native-redline-check", "description": "元红线命中检查（high_risk）",
         "high_risk": True},
    ]

    # 向导三卡：三级分类 / 工作流 / 方向（portal 渲染层动态生成，消费方可覆盖注入）
    levels = [dict(c) for c in level_cards()]
    workflows = [dict(c) for c in workflow_cards()]
    directions = [dict(c) for c in direction_cards()]
    return {
        "modes": modes,
        "nativeTools": native_tools,
        "levels": levels,
        "workflows": workflows,
        "directions": directions,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(get_bootstrap(), ensure_ascii=False, indent=2))
