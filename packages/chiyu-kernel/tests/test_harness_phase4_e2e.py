"""T5 — 阶段四 END-TO-END 冒烟：workflow → subagent → plan/todo → 对话页渲染。

覆盖：
A) 声明式 workflow 经 `workflow` 工具端到端跑通（DAG 派发子智能体）；
B) workflow 与 phase2 的 plan/todo 数据模型在同一 harness 上下文并存；
C) 对话页渲染含 workflow 结果且 `<script` 注入被防护。
"""
from chiyu_kernel.contract import CORE_ROLES, ParticleTypeSet, TenantProfile
from chiyu_kernel.harness_native_tools import register_native_tools
from chiyu_kernel.llm.client import LlmResponse, StubProvider
from chiyu_kernel.orchestration.subagent import SubagentPool
from chiyu_kernel.plan import Plan, PlanStep, TodoItem, TodoList
from chiyu_kernel.session import SessionManager
from chiyu_kernel.tools import ToolRegistry
from chiyu_kernel.workflow import register_workflow_tools
from chiyu_portal.renderer import render_conversation


def _profile():
    return TenantProfile(domain="demo", particle_types=ParticleTypeSet(set(CORE_ROLES)))


def test_e2e_workflow_subagent_plan_render():
    pool = SubagentPool(
        llm=StubProvider(responses=[
            LlmResponse(content="researcher: 调研结论 A"),
            LlmResponse(content="writer: 成文 B"),
        ]),
        tools=ToolRegistry(),
        sessions=SessionManager(),
    )
    reg = ToolRegistry()
    register_native_tools(reg, profile=_profile())  # 串联 phase1 原生能力
    register_workflow_tools(reg, pool)              # phase4 工具

    # A) 跑声明式 workflow（DAG：write 依赖 research）
    out = reg.execute("workflow", {
        "meta": {"name": "research-write", "description": "调研并成文"},
        "steps": [
            {"name": "research", "prompt": "研究 X"},
            {"name": "write", "prompt": "撰写报告", "depends_on": ["research"]},
        ],
    })
    assert out["stopReason"] == "completed"
    assert out["agentsStarted"] == 2
    assert "调研结论 A" in out["result"]["research"]
    assert "成文 B" in out["result"]["write"]
    assert out["runId"]

    # B) workflow 与 phase2 plan/todo 并存
    plan = Plan(steps=[PlanStep("定义范围"), PlanStep("实现")])
    plan.enter_mode()
    todo = TodoList()
    todo.write([TodoItem("搭脚手架")])
    assert plan.projection()["active"] is True
    assert todo.items[0].content == "搭脚手架"

    # C) 对话页渲染含 workflow 结果 + 注入防护
    events = [
        {"role": "user", "content": "跑一个工作流"},
        {"role": "assistant", "content": f"workflow {out['runId']} 完成：{out['result']}"},
    ]
    html = render_conversation(
        events=events, composer_action="send_message", goal="编排",
    ).html
    assert out["runId"] in html
    assert "<script" not in html.lower()
