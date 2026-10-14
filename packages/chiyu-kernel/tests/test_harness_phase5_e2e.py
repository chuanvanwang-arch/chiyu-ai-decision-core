"""T3 — 阶段五 END-TO-END 冒烟：真实 multiprocessing 子进程跑并行调度。

证明：
A) 两个独立 step 经「子进程调度 + 父进程并发池」真正并行——同环境对照
   `max_concurrency=1`（串行）vs `=4`（并发），并发明显更快（消除 spawn 固定开销方差，
   且能鉴别「并发回退为串行」的回归）。
B) 真实子进程下，fatal 子智能体结果 → 整 run error（组合子纪律跨进程成立）。
"""
import time

from chiyu_kernel.llm.client import LlmResponse, StubProvider
from chiyu_kernel.orchestration.subagent import SubagentPool
from chiyu_kernel.session import SessionManager
from chiyu_kernel.tools import ToolRegistry
from chiyu_kernel.workflow import (
    WorkflowMeta, WorkflowStep, Workflow, WorkflowRunner, WorkflowError,
)


class SleepProvider(StubProvider):
    """每轮 stream_chat 睡眠 delay 秒，用于证明跨进程并发执行。"""

    def __init__(self, delay: float = 0.3, responses=None) -> None:
        super().__init__(responses=responses)
        self._delay = delay

    def stream_chat(self, messages, *, tools=None) -> LlmResponse:
        time.sleep(self._delay)
        return super().stream_chat(messages, tools=tools)


class FatalSubagentPool(SubagentPool):
    """delegate 对任意子智能体抛 fatal，用于验证跨进程组合子纪律。"""

    def delegate(self, task, *, subagent_key):
        raise WorkflowError("boom", "AGENT_RESULT", fatal=True)


def _run_two_independent(delay: float, cap: int) -> float:
    """跑 A,B 两个独立 step（cap 控制并发上限），返回耗时（秒）。"""
    llm = SleepProvider(delay=delay, responses=[
        LlmResponse(content="done"), LlmResponse(content="done"),
    ])
    pool = SubagentPool(llm=llm, tools=ToolRegistry(), sessions=SessionManager())
    runner = WorkflowRunner(pool, grace_ms=2000)
    wf = Workflow(
        WorkflowMeta("p5-e2e", "d", max_concurrency=cap),
        [WorkflowStep("A", "p"), WorkflowStep("B", "p")],
    )
    t0 = time.perf_counter()
    res = runner.run(wf)
    dt = time.perf_counter() - t0
    assert res.stop_reason == "completed", res
    assert res.value == {"A": "done", "B": "done"}, res.value
    return dt


def test_independent_steps_run_in_parallel_not_serial():
    delay = 0.3
    # 同一对独立 step：cap=1 串行、cap=4 并发（固定 spawn 开销相同，差异纯为 sleep 重叠）
    serial = _run_two_independent(delay, cap=1)
    parallel = _run_two_independent(delay, cap=4)
    # 并发应明显快于串行（gap≈delay）；回退为串行时 parallel≈serial，断言翻红。
    assert parallel < serial - 0.1, (
        f"未并发：parallel={parallel:.3f}s ≥ serial={serial:.3f}s "
        f"（cap=4 应并行，省去一次 {delay}s sleep）"
    )


def test_fatal_kills_whole_run_via_real_process():
    llm = SleepProvider(delay=0.1, responses=[LlmResponse(content="done")])
    pool = FatalSubagentPool(llm=llm, tools=ToolRegistry(), sessions=SessionManager())
    runner = WorkflowRunner(pool, grace_ms=2000)
    wf = Workflow(
        WorkflowMeta("p5-e2e2", "d"),
        [WorkflowStep("A", "p"), WorkflowStep("B", "p")],
    )
    res = runner.run(wf)
    assert res.stop_reason == "error"
    assert "boom" in (res.error or "")
