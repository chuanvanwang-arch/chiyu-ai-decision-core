"""阶段二 E2E 冒烟：skill → subagent → plan/todo → 对话页渲染。

端到端验证 dsh 式能力的无缝集成：
- 父 agent 委派子 agent 完成「调研」任务（子 agent 经本仓原生工具 `native-context-assemble` 调内核能力）
- 子 agent 用 `TodoList` / `PlanMode` 记录进度
- 最终经 `render_conversation` 渲染为对话页 HTML
"""
from __future__ import annotations

from chiyu_kernel.llm.client import StubProvider, ToolCall, LlmResponse
from chiyu_kernel.tools import ToolRegistry
from chiyu_kernel.contract import TenantProfile
from chiyu_kernel.contract.particle import ParticleTypeSet
from chiyu_kernel.session import SessionManager, SessionEvent
from chiyu_kernel.harness_native_tools import register_native_tools
from chiyu_kernel.skills import load_catalog
from chiyu_kernel.orchestration.subagent import SubagentDescriptor, SubagentPool
from chiyu_kernel.plan import TodoItem, PlanStep, TodoList, Plan, PlanMode

from chiyu_portal.renderer import render_conversation


def test_phase2_e2e_skill_subagent_plan_render():
    # 1) skill 目录（dsh skill 能力）
    skills = load_catalog({
        "researcher": {"description": "调研技能", "content": "你擅长调研", "when_to_use": "需检索时"},
    })
    assert skills.get("researcher").content == "你擅长调研"

    # 2) 本仓原生工具（阶段一桥接）+ 子 agent 委派（阶段二 subagent）
    assemble_args = {
        "needs": [{"layer": "L1", "dims": ["semantics"], "key": "k"}],
        "provided": {"L1": [{"dim": "semantics", "key": "k", "value": "v"}]},
    }
    first = LlmResponse(
        content="",
        tool_calls=[ToolCall(name="native-context-assemble", args=assemble_args)],
    )
    second = LlmResponse(content="调研结论：方案可行")
    tools = ToolRegistry()
    profile = TenantProfile(
        domain="demo",
        particle_types=ParticleTypeSet(
            ("unstructured_asset", "entity", "decision", "memory", "knowledge")),
    )
    register_native_tools(tools, profile=profile)
    pool = SubagentPool(
        llm=StubProvider(responses=[first, second]),
        tools=tools,
        sessions=SessionManager(),
    )
    pool.register(SubagentDescriptor(key="researcher", role="研究员",
                                     instruction="调研", tools_scope="native"))
    res = pool.delegate("调研 X", subagent_key="researcher")
    assert any("方案可行" in m["content"]
               for m in res["messages"] if m.get("role") == "assistant")

    # 3) plan/todo 进度记录（dsh plan/todo 能力）
    todos = TodoList()
    todos.write([
        TodoItem(content="调研", status="completed"),
        TodoItem(content="方案", status="in_progress"),
    ])
    plan = Plan(steps=[PlanStep("设计")])
    plan.enter_mode()
    assert plan.projection()["active"] is True
    assert todos.items[1].status == "in_progress"

    # 4) 渲染对话页（阶段一前端 Python 化）
    events = [
        {"role": "user", "content": "调研 X"},
        {"role": "assistant", "content": "调研结论：方案可行"},
    ]
    r = render_conversation(events=events, composer_action="send_message", goal="完成调研")
    assert r.ok
    html = r.html
    assert "调研结论：方案可行" in html
    assert "完成调研" in html            # goal-bar
    assert "send_message" in html       # composer data-action
    assert "<script" not in html.lower()  # 无内联 JS
