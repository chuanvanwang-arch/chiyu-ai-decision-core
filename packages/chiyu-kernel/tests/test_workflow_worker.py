import time

from chiyu_kernel.workflow.worker import WorkerEngine, W_READY, W_GO, W_CHILD_START, W_RESULT, W_CANCEL
from chiyu_kernel.workflow import WorkflowError


class FakeTransport:
    """脚本化执行器：按 child_start 的 key 返回预设结果；可模拟 fatal/cancel/延迟。"""

    def __init__(self, script, *, delay=0.0, cancel_after=None):
        self._script = script          # dict[key] -> ("ok", value) | ("fatal", msg) | ("null", None)
        self._delay = delay
        self._cancel_after = cancel_after  # 收到第 N 个 child_start 后由测试侧发 cancel
        self._sent = []                # worker 发出的消息
        self._recv_q = []              # 待回给 worker 的消息
        self._started = 0
        self.child_calls = []          # 记录收到的 child_start（含顺序）

    def send(self, msg):
        self._sent.append(msg)
        if msg["type"] == W_READY:
            self._recv_q.append({"type": W_GO})  # 模拟 host：收到 ready 即发 go
        if msg["type"] == W_CHILD_START:
            self._started += 1
            self.child_calls.append(msg["key"])
            if self._cancel_after is not None and self._started == self._cancel_after:
                self._recv_q.append({"type": W_CANCEL})
            else:
                res = self._script.get(msg["key"], ("null", None))
                if self._delay:
                    time.sleep(self._delay)
                if res[0] == "ok":
                    self._recv_q.append({"type": "child_settled", "callId": msg["callId"], "result": res[1]})
                elif res[0] == "null":
                    self._recv_q.append({"type": "child_failed", "callId": msg["callId"], "rendered": "x", "fatal": False})
                else:  # fatal
                    self._recv_q.append({"type": "child_failed", "callId": msg["callId"], "rendered": res[1], "fatal": True})

    def recv(self):
        if not self._recv_q:
            while not self._recv_q:
                time.sleep(0.001)
        return self._recv_q.pop(0)


def _init(steps, max_concurrency=None):
    return {"steps": steps, "max_concurrency": max_concurrency}


def _result(transport):
    return [m for m in transport._sent if m["type"] == W_RESULT][0]


def test_independent_steps_run_concurrently_within_cap():
    ft = FakeTransport({"A": ("ok", "ra"), "B": ("ok", "rb")}, delay=0.05)
    WorkerEngine(ft).run(_init([
        {"name": "A", "prompt": "p", "depends_on": []},
        {"name": "B", "prompt": "p", "depends_on": []},
    ], max_concurrency=2))
    assert set(ft.child_calls) == {"A", "B"}
    res = _result(ft)
    assert res["stopReason"] == "completed"
    assert res["value"] == {"A": "ra", "B": "rb"}


def test_dependency_orders_execution():
    ft = FakeTransport({"A": ("ok", "ra"), "B": ("ok", "rb"), "C": ("ok", "rc")})
    WorkerEngine(ft).run(_init([
        {"name": "A", "prompt": "p", "depends_on": []},
        {"name": "B", "prompt": "p", "depends_on": []},
        {"name": "C", "prompt": "p", "depends_on": ["A", "B"]},
    ]))
    assert ft.child_calls.index("C") > ft.child_calls.index("A")
    assert ft.child_calls.index("C") > ft.child_calls.index("B")


def test_non_fatal_child_resolves_to_none_others_continue():
    ft = FakeTransport({"A": ("ok", "ra"), "B": ("null", None), "C": ("ok", "rc")})
    WorkerEngine(ft).run(_init([
        {"name": "A", "prompt": "p", "depends_on": []},
        {"name": "B", "prompt": "p", "depends_on": []},
        {"name": "C", "prompt": "p", "depends_on": ["A", "B"]},
    ]))
    res = _result(ft)
    assert res["stopReason"] == "completed"
    assert res["value"] == {"A": "ra", "B": None, "C": "rc"}


def test_fatal_child_kills_whole_run():
    ft = FakeTransport({"A": ("ok", "ra"), "B": ("fatal", "boom"), "C": ("ok", "rc")})
    WorkerEngine(ft).run(_init([
        {"name": "A", "prompt": "p", "depends_on": []},
        {"name": "B", "prompt": "p", "depends_on": []},
        {"name": "C", "prompt": "p", "depends_on": ["A", "B"]},
    ]))
    res = _result(ft)
    assert res["stopReason"] == "error"
    assert "boom" in (res.get("error") or "")


def test_cancel_stops_and_reports_cancelled():
    ft = FakeTransport({"A": ("ok", "ra"), "B": ("ok", "rb")}, cancel_after=1)
    WorkerEngine(ft).run(_init([
        {"name": "A", "prompt": "p", "depends_on": []},
        {"name": "B", "prompt": "p", "depends_on": []},
    ]))
    res = _result(ft)
    assert res["stopReason"] == "cancelled"
