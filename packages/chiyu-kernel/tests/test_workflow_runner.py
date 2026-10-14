"""阶段四 T2 — WorkflowRunner（复用 SubagentPool 派发，吸收 dsh agent()/pipeline() 概念）。

TDD：先红后绿。用 StubProvider + SubagentPool 测试替身，monkeypatch `delegate` 模拟失败/取消。
"""
from __future__ import annotations

from chiyu_kernel.llm.client import LlmResponse, StubProvider
from chiyu_kernel.orchestration.subagent import SubagentPool
from chiyu_kernel.session import SessionManager
from chiyu_kernel.tools import ToolRegistry
from chiyu_kernel.workflow import (
    Workflow,
    WorkflowError,
    WorkflowMeta,
    WorkflowRunner,
    WorkflowStep,
)


def _pool(responses):
    llm = StubProvider(responses=list(responses))
    return SubagentPool(llm=llm, tools=ToolRegistry(), sessions=SessionManager())


def _chain_wf():
    return Workflow(
        meta=WorkflowMeta(name="wf", description="d"),
        steps=[
            WorkflowStep(name="a", prompt="do a"),
            WorkflowStep(name="b", prompt="do b", depends_on=["a"]),
            WorkflowStep(name="c", prompt="do c", depends_on=["b"]),
        ],
    )


def test_runner_executes_dag_in_topo_order():
    pool = _pool([
        LlmResponse(content="A 完成"),
        LlmResponse(content="B 完成"),
        LlmResponse(content="C 完成"),
    ])
    runner = WorkflowRunner(pool)
    res = runner.run(_chain_wf())
    assert res.stop_reason == "completed"
    assert res.agents_started == 3
    assert "A 完成" in res.value["a"]
    assert "B 完成" in res.value["b"]
    assert "C 完成" in res.value["c"]


def test_child_failure_isolated_to_none():
    pool = _pool([])

    def fake(task, *, subagent_key):
        if subagent_key == "b":
            return {"rejected": True, "messages": []}
        return {"rejected": False, "messages": [{"role": "assistant", "content": f"{subagent_key} ok"}]}

    pool.delegate = fake  # type: ignore[assignment]
    runner = WorkflowRunner(pool)
    res = runner.run(_chain_wf())
    assert res.stop_reason == "completed"
    assert res.value["a"] is not None
    assert res.value["b"] is None  # 子失败隔离
    assert res.value["c"] is not None


def test_fatal_error_terminates_run():
    pool = _pool([])

    def fake(task, *, subagent_key):
        if subagent_key == "b":
            raise WorkflowError("boom", "AGENT_START", fatal=True)
        return {"rejected": False, "messages": [{"role": "assistant", "content": f"{subagent_key} ok"}]}

    pool.delegate = fake  # type: ignore[assignment]
    runner = WorkflowRunner(pool)
    res = runner.run(_chain_wf())
    assert res.stop_reason == "error"
    assert "boom" in (res.error or "")
    assert res.value.get("a") is not None
    assert "b" not in res.value  # 提前终止，b 未落结果


def test_cancel_signal_stops_run():
    # 进程外模型（phase5）忠实 dsh：signal 在启动前即已取消 → 不启动子进程。
    # 运行中途取消改由 WorkerRun.cancel()（grace→terminate）承担，见 test_workflow_host。
    class Sig:
        cancelled = False

    sig = Sig()
    sig.cancelled = True  # 启动前即取消
    pool = _pool([])
    runner = WorkflowRunner(pool)
    res = runner.run(_chain_wf(), signal=sig)
    assert res.stop_reason == "cancelled"
    assert res.agents_started == 0
