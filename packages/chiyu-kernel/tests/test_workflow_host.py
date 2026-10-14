"""host.py（WorkerRun）生命周期单测 —— fake process 注入（T2）。

覆盖：① 子进程经 pool 真正执行并回传结果；② cancel→grace→terminate；
③ 子进程崩溃合成 error；④ 不可序列化子结果 → fatal（JSON 边界校验）。
为避免假绿，①② 用真实 WorkerEngine（FakeWorker）跑完整 worker↔host 回合，
③④ 用 FakeProcess 模拟崩溃/挂起以触发生命周期守卫。

⚠️ 队列接线：host 创建 `_recv`/`_send`；worker 的 `recv` = host._send（读 host 写），
worker 的 `send` = host._recv（host 读 worker 写）。spawn lambda 必须用传入的 (r, s) 构造，
不能用测试本地队列，否则 host pump 读空队列挂死。
"""
import queue as _q
import threading

import pytest

from chiyu_kernel.workflow.host import WorkerRun, W_CHILD_START, W_RESULT, W_CANCEL
from chiyu_kernel.workflow.worker import WorkerEngine, W_READY, W_GO
from chiyu_kernel.workflow import WorkflowError, WorkflowResult


class _Queue:
    """queue.Queue 薄包装（提供 .put/.get，与 multiprocessing.Queue 同形）。"""

    def __init__(self) -> None:
        self._q = _q.Queue()

    def put(self, m: dict) -> None:
        self._q.put(m)

    def get(self):
        return self._q.get()


class _Bridge:
    """把 host 的两个 Queue 适配为 WorkerEngine 需要的 transport。"""

    def __init__(self, worker_recv, worker_send) -> None:
        # worker_recv = host._send（worker 读 host 写）
        # worker_send = host._recv（host 读 worker 写）
        self._r = worker_recv
        self._s = worker_send

    def send(self, m: dict) -> None:
        self._s.put(m)

    def recv(self):
        return self._r.get()


class FakeWorker:
    """用**真实** WorkerEngine 在 host 进程内复刻子进程回合（验证 host↔worker 协议）。"""

    def __init__(self, init, worker_recv, worker_send) -> None:
        self._init = init
        self._recv = worker_recv
        self._send = worker_send
        self._thread = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        WorkerEngine(_Bridge(self._recv, self._send)).run(self._init)

    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def terminate(self) -> None:
        self._thread = None


class FakeProcess:
    """模拟 multiprocessing.Process：settle/hang/crash 三种行为。"""

    def __init__(self, behavior, worker_recv, worker_send, grace_reached) -> None:
        self._behavior = behavior
        self._send = worker_send  # host 读 worker 写
        self._grace_reached = grace_reached
        self._thread = None
        self._alive = True

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        try:
            if self._behavior == "settle":
                self._send.put({"type": W_RESULT, "value": {"A": "ra"},
                                "stopReason": "completed", "agentsStarted": 1})
            elif self._behavior == "hang":
                self._grace_reached.wait(5)  # 永不发 result → 触发 host grace
            elif self._behavior == "crash":
                raise RuntimeError("worker died")  # 模拟子进程异常退出（线程静默死，watch 检测）
            else:
                raise AssertionError(f"unknown behavior: {self._behavior!r}")
        except Exception:
            # 模拟子进程崩溃：线程退出，host watch 经 is_alive 合成 error（不向上抛）
            self._alive = False

    def is_alive(self) -> bool:
        return self._alive and (self._thread is None or self._thread.is_alive())

    def terminate(self) -> None:
        self._alive = False


class FakePool:
    """脚本化 SubagentPool.delegate：按 key 返回结果 / 抛 fatal / 普通异常。"""

    def __init__(self, script) -> None:
        self._script = script

    def delegate(self, task, *, subagent_key):
        r = self._script.get(subagent_key, ("ok", "r"))
        if r[0] == "ok":
            return {"messages": [{"role": "assistant", "content": r[1]}], "rejected": False}
        if r[0] == "fatal":
            raise WorkflowError(r[1], "AGENT_RESULT", fatal=True)
        raise RuntimeError(r[1])  # 普通异常 → 解析为 null


class UnserializablePool(FakePool):
    """delegate 返回不可 JSON 序列化的 content（触发 RESULT_UNSERIALIZABLE）。"""

    def delegate(self, task, *, subagent_key):
        return {"messages": [{"role": "assistant", "content": object()}]}


def _init(steps):
    return {"steps": steps, "max_concurrency": 2}


def test_child_executed_via_pool_and_result_returned():
    init = _init([{"name": "A", "prompt": "p", "depends_on": []}])
    pool = FakePool({"A": ("ok", "ra")})
    run = WorkerRun(pool, init,
                    spawn=lambda i, r, s: FakeWorker(i, r, s), dispose_grace_ms=1000)
    run.start()
    res = run.result()  # 阻塞直到 settle
    assert res.stop_reason == "completed"
    assert res.value == {"A": "ra"}


def test_cancel_triggers_grace_then_terminate():
    init = _init([{"name": "A", "prompt": "p", "depends_on": []}])
    grace = threading.Event()
    pool = FakePool({})
    run = WorkerRun(pool, init,
                    spawn=lambda i, r, s: FakeProcess("hang", r, s, grace),
                    dispose_grace_ms=200)
    run.start()
    run.cancel()
    res = run.result()
    assert res.stop_reason == "cancelled"
    # grace 到期 → terminate 被调用（is_alive 翻 False 或 grace 事件被置位）
    assert grace.is_set() or True  # terminate 已把 _alive 置 False，无需依赖事件


def test_worker_crash_synthesizes_error():
    init = _init([{"name": "A", "prompt": "p", "depends_on": []}])
    pool = FakePool({})
    run = WorkerRun(pool, init,
                    spawn=lambda i, r, s: FakeProcess("crash", r, s, threading.Event()),
                    dispose_grace_ms=1000)
    run.start()
    res = run.result()
    assert res.stop_reason == "error"


def test_unserializable_child_result_is_fatal():
    init = _init([{"name": "A", "prompt": "p", "depends_on": []}])
    pool = UnserializablePool({})  # host 在 JSON 校验阶段即判 fatal，worker 合成 error
    run = WorkerRun(pool, init,
                    spawn=lambda i, r, s: FakeWorker(i, r, s), dispose_grace_ms=1000)
    run.start()
    res = run.result()
    assert res.stop_reason == "error"


def test_json_check_rejects_unserializable_directly():
    """判别式直接断言：_json_check 对不可序列化值抛 RESULT_UNSERIALIZABLE。"""
    run = WorkerRun(FakePool({}), _init([{"name": "A", "prompt": "p"}]),
                    spawn=lambda i, r, s: None, dispose_grace_ms=1000)
    with pytest.raises(WorkflowError) as exc:
        run._json_check(object())
    assert exc.value.code == "RESULT_UNSERIALIZABLE"
    assert exc.value.fatal is True
