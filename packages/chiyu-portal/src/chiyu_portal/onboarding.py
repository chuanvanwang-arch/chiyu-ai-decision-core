"""引导式页面导航（对标 DeepSeek Harness 桌面版的 onboarding 向导）。

深源：登录 → 选工作区 → 选方向 → 选工作流 → 选工作模式。
本仓落点：chiyu-portal 的引导式向导，菜单与可选工作流**全部**从
`chiyu_kernel.plugins` 的 `PluginRegistry` / `MODE_PRESETS` 动态生成，门户零领域字面量。

⛔ 方向（行业/租户）经 `TenantProfile`（L4）注入，本模块不写任何领域词。
⛔ 只从 `chiyu_kernel.api` 门面取插件能力，不 import 内核内部路径。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from chiyu_kernel.api import MODE_PRESETS, PluginRegistry, register_builtins


def onboarding_steps() -> List[Dict[str, str]]:
    """四步向导（第 3 步高亮 = 当前选择工作模式）。"""
    return [
        {"n": "1", "key": "direction", "label": "选方向",
         "hint": "行业 / 租户（经 TenantProfile 注入）"},
        {"n": "2", "key": "workflow", "label": "选工作流",
         "hint": "从已注册能力动态生成"},
        {"n": "3", "key": "mode", "label": "选工作模式", "hint": "标准 / PTC / 极简 / 创造",
         "active": "true"},
        {"n": "4", "key": "workspace", "label": "进入工作台", "hint": "按模式装配能力"},
    ]


def mode_cards() -> List[Dict[str, object]]:
    """从 WorkMode 预设动态生成模式卡片（含启用插件、Phase B 后端）。"""
    reg = PluginRegistry()
    register_builtins(reg)
    cards: List[Dict[str, object]] = []
    for mid in sorted(MODE_PRESETS):
        mode = MODE_PRESETS[mid]
        enabled = [p for p in mode.plugins if reg.has(p)]
        cards.append({
            "id": mode.id,
            "label": mode.label,
            "description": mode.description,
            "plugins": enabled,
            "phase_b_backend": mode.phase_b_backend,
            "default": mode.default,
        })
    return cards


def level_cards() -> List[Dict[str, object]]:
    """场景三级分类卡片（解法分层，中性通用枚举）。

    边界判据：AI 替几个岗位、替几次 —— 而非系统数量 / 链路长短。
    ⛔ 零领域字面量：真实场景画像由消费方经 TenantProfile 覆盖注入。
    `recommended_modes` 为层级 → 工作模式联动推荐（向导第 3 步高亮依据）。
    """
    return [
        {
            "id": "single",
            "label": "单点提效",
            "criteria": "单智能体取数算出完整结果，交回一个岗位一次确认；人只提供输入 + 一次审批",
            "solution": "沉淀为可复用 SKILL / 单 Agent，低成本、快见效、易治理",
            "recommended_modes": ["ptc", "minimal"],
        },
        {
            "id": "flow",
            "label": "流程提效",
            "criteria": "AI 输出喂送下一个岗位做不同的事，多岗位接力；每环节有不同角色的独立动作 / 批准",
            "solution": "智能体编排：角色智能体 + 状态机 + 事件总线 + 审批闸门（HITL）",
            "recommended_modes": ["standard"],
        },
        {
            "id": "end2end",
            "label": "端到端增值",
            "criteria": "从开始到结束改变经营结果：感知 → 认知 → 决策 → 执行闭环，AI 完成决策、人做审核",
            "solution": "企业级 AI 决策平台：统一决策内核 + 记忆系统 + 治理（RBAC / 审计）",
            "recommended_modes": ["standard", "creative"],
        },
    ]


def workflow_cards() -> List[Dict[str, object]]:
    """工作流卡片（中性通用枚举，`level` = 归属三级分类，向导第 2 步分组依据）。"""
    return [
        {"id": "decide", "label": "决策辅助",
         "hint": "决策脊柱 · 红线校验 · 闭环审核", "level": "end2end"},
        {"id": "research", "label": "调研检索",
         "hint": "联网 + 子智能体归纳，一次交回", "level": "single"},
        {"id": "automate", "label": "任务编排",
         "hint": "跨岗位接力 · 状态机 + 审批闸门", "level": "flow"},
        {"id": "build", "label": "能力沉淀",
         "hint": "封装为 SKILL / 插件，单点复用", "level": "single"},
    ]


def direction_cards() -> List[Dict[str, str]]:
    """方向卡片（行业 / 租户演示枚举）。

    ⛔ 真实方向清单经 TenantProfile（L4）注入后由此覆盖；本枚举仅演示兜底。
    """
    return [
        {"id": "finance", "label": "金融 / 风控", "hint": "信贷、反欺诈、合规"},
        {"id": "retail", "label": "零售 / 电商", "hint": "选品、运营、客服"},
        {"id": "manufacturing", "label": "制造 / 供应链", "hint": "排程、质量、履约"},
        {"id": "generic", "label": "通用助手", "hint": "跨领域问答与任务"},
    ]


def render_onboarding() -> "OnboardingResult":
    """渲染引导式导航 HTML（自主产出，不经 NL→Schema 链路，属静态向导页）。"""
    html = _build_html(onboarding_steps(), mode_cards())
    return OnboardingResult(ok=True, html=html, errors=())


@dataclass
class OnboardingResult:
    ok: bool
    html: str
    errors: Tuple[str, ...]


# ── HTML 生成（轻量、自包含）──────────────────────────────────────────────────
# ⛔ HTML 属性统一用单引号，CSS 块不走 f-string（避免 CSS 花括号被当成表达式）。
_CSS = """
<style>
 body{font-family:-apple-system,Segoe UI,Roboto,'Microsoft YaHei',sans-serif;
   margin:0;background:#f8fafc;color:#0f172a;}
 .ob-wrap{max-width:920px;margin:0 auto;padding:28px 20px;}
 h1{font-size:20px;margin:0 0 4px;}
 .ob-sub{color:#64748b;font-size:13px;margin:0 0 18px;}
 .ob-steps{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:22px;}
 .ob-step{padding:7px 12px;border-radius:20px;background:#e0f2fe;color:#075985;
   border:1px solid #7dd3fc;font-size:13px;font-weight:600;}
 .ob-step.ob-active{background:#16a34a;color:#fff;border-color:#16a34a;
   box-shadow:0 0 0 3px rgba(22,163,74,.15);}
 .ob-cards{display:grid;grid-template-columns:repeat(2,1fr);gap:14px;}
 .ob-card{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:14px;}
 .ob-card.ob-default{border-color:#16a34a;}
 .ob-card h3{margin:0 0 6px;font-size:15px;}
 .ob-tag{font-size:10px;font-weight:600;color:#16a34a;
   border:1px solid #16a34a;border-radius:8px;padding:1px 6px;vertical-align:middle;}
 .ob-card p{margin:0 0 8px;font-size:12.5px;color:#475569;line-height:1.6;}
 .ob-plugins{display:flex;gap:5px;flex-wrap:wrap;margin-bottom:8px;}
 .ob-pill{font-size:11px;padding:2px 8px;border-radius:10px;background:#dcfce7;color:#166534;}
 .ob-pb{font-size:11px;color:#0891b2;}
</style>"""


def _build_html(steps: List[Dict[str, str]],
                cards: List[Dict[str, object]]) -> str:
    step_parts: List[str] = []
    for s in steps:
        active = " ob-active" if s.get("active") else ""
        step_parts.append(
            f"<span class='ob-step{active}'><b>{s['n']}</b> {s['label']}</span>")
    step_html = "".join(step_parts)

    card_parts: List[str] = []
    for c in cards:
        cls = "ob-card ob-default" if c["default"] else "ob-card"
        tag = " <span class='ob-tag'>DEFAULT</span>" if c["default"] else ""
        pills = "".join(f"<span class='ob-pill'>{p}</span>" for p in c["plugins"])
        if c["phase_b_backend"]:
            pb = f"<div class='ob-pb'>Phase B → {c['phase_b_backend']}</div>"
        else:
            pb = "<div class='ob-pb'>无需 LLM（确定性）</div>"
        card_parts.append(
            f"<div class='{cls}'><h3>{c['label']}{tag}</h3>"
            f"<p>{c['description']}</p>"
            f"<div class='ob-plugins'>{pills}</div>{pb}</div>")
    card_html = "".join(card_parts)

    return (
        "<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'>"
        "<title>ChiYu 引导式导航 · 选工作模式</title>" + _CSS +
        "</head><body><div class='ob-wrap'>"
        "<h1>ChiYu 引导式页面导航</h1>"
        "<p class='ob-sub'>选方向 → 选工作流 → 选工作模式 → 进入工作台。菜单与可选工作流"
        "均从插件注册表动态生成；方向经 TenantProfile 注入，门户零领域字面量。</p>"
        f"<div class='ob-steps'>{step_html}</div>"
        f"<div class='ob-cards'>{card_html}</div>"
        "</div></body></html>"
    )


__all__ = [
    "onboarding_steps", "mode_cards", "level_cards", "workflow_cards",
    "direction_cards", "render_onboarding", "OnboardingResult",
]
