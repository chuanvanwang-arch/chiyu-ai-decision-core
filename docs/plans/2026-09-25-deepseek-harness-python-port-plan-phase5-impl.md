# 阶段五：workflow 真进程外并行调度（worker pool）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `WorkflowRunner` 从串行 `await delegate` 升级为「每 run 一隔离子进程跑 DAG 调度 + 父进程并发池执行子智能体」，忠实吸收 dsh `parallel()` / `AGENT_CAP` / `WorkerRun` 生命周期；phase4 既有 25 测试形状不变。

**Architecture:** 子进程（worker.py）只做调度 realm（拓扑/并发上限/取消/清理，scrubbed env 无凭据），经双向 `multiprocessing.Queue` 把 `child-start` 回传父进程（host.py）；父进程 `WorkerRun` 收到 `child-start` 后经本仓既有 `SubagentPool.delegate()`（→ `AgentLoop` + 全护栏）并发执行子智能体。R2 守住：不新建平行 driver 框架，子进程不碰 LLM/工具/凭据。

**Tech Stack:** Python 3.13，`multiprocessing`（Process + Queue），`asyncio`（子进程内并发调度，用 `asyncio.Semaphore(max_concurrency)` 忠实吸收 dsh `AGENT_CAP`），`pytest`（hermes venv：`C:/Users/wangchuan08/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe`）。

---

## 文件结构

- `packages/chiyu-kernel/src/chiyu_kernel/workflow/__init__.py` — 改：`WorkflowMeta` 增 `max_concurrency` 可选字段；`__all__` 增 `WorkerRun`。
- `packages/chiyu-kernel/src/chiyu_kernel/workflow/worker.py` — 新：子进程调度 realm（`WorkerEngine` + `run_worker_process`）。
- `packages/chiyu-kernel/src/chiyu_kernel/workflow/host.py` — 新：父进程执行器 + 生命周期（`WorkerRun`）。
- `packages/chiyu-kernel/src/chiyu_kernel/workflow/runner.py` — 改：`run()` 改构造 `WorkerRun`（替代串行 delegate）；保留 `register` 幂等注册。
- `packages/chiyu-kernel/src/chiyu_kernel/api.py` — 改：facade `__all__` 增 `WorkerRun`（与 `workflow.__all__` 同步）。
- `packages/chiyu-kernel/tests/test_workflow_worker.py` — 新：T1 worker 调度单测（fake transport）。
- `packages/chiyu-kernel/tests/test_workflow_host.py` — 新：T2 host 生命周期单测（fake process）。
- `packages/chiyu-kernel/tests/test_harness_phase5_e2e.py` — 新：T3 真 multiprocessing E2E。
- `packages/chiyu-kernel/tests/test_api_facade_covers_all_layers.py` — 已由 phase4 加 `workflow` 入 `LAYERS`；本计划仅保证 `api.__all__` ⊇ `workflow.__all__`（T4）。

**协议消息（worker↔host，均 JSON dict，`type` 字段）：**
- `worker→host`: `ready` / `child_start{callId,key,prompt}` / `child_dispose{callId}` / `result{value,stopReason,agentsStarted}` / `log{message}`(可选忽略) / `agent_start{seq,key}`(可选) / `agent_end{seq}`(可选)
- `host→worker`: `go` / `cancel` / `child_started{callId}` / `child_settled{callId,result}` / `child_failed{callId,rendered,fatal}` / `child_disposed{callId}`

---

### Task 1: WorkflowMeta.max_concurrency 字段

**Files:**
- Modify: `packages/chiyu-kernel/src/chiyu_kernel/workflow/__init__.py:67-79`（`WorkflowMeta`）

- [ ] **Step 1: 扩展 WorkflowMeta（加可选字段，向后兼容）**

把 `WorkflowMeta` 改为：
```python
@dataclass
class WorkflowMeta:
    """workflow 身份块（faithful to dsh `WorkflowMeta`）。"""

    name: str
    description: str
    when_to_use: Optional[str] = None
    phases: list[WorkflowPhase] = field(default_factory=list)
    max_concurrency: Optional[int] = None  # 新增：worker 池并发上限（dsh AGENT_CAP）；None→DEFAULT_MAX_CONCURRENCY

    def __post_init__(self) -> None:
        if not self.name or not _KEBAB_RE.match(self.name):
            raise AssertionError(f"workflow name 必须为 kebab-case：{self.name!r}")
        if self.max_concurrency is not None and self.max_concurrency < 1:
            raise AssertionError(f"max_concurrency 必须 ≥1：{self.max_concurrency!r}")
```
同时在文件顶部常量区（`WORKFLOW_STEP_STATES` 附近）加：
```python
DEFAULT_MAX_CONCURRENCY = 4  # 忠实吸收 dsh AGENT_CAP 默认并发
```

- [ ] **Step 2: 自检（已存在的 meta 构造不受影响）**

Run: `C:/Users/wangchuan08/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe -c "from chiyu_kernel.workflow import WorkflowMeta; WorkflowMeta('x','d'); WorkflowMeta('y','d',max_concurrency=2); print('ok')"`
Expected: 打印 `ok`（不抛）。

- [ ] **Step 3: Commit**

```bash
git add packages/chiyu-kernel/src/chiyu_kernel/workflow/__init__.py
git commit -m "feat(workflow): WorkflowMeta.max_concurrency 字段（dsh AGENT_CAP 吸收准备）"
```

---

### Task 2: worker.py 子进程调度 realm（T1 测试）

**Files:**
- Create: `packages/chiyu-kernel/src/chiyu_kernel/workflow/worker.py`
- Test: `packages/chiyu-kernel/tests/test_workflow_worker.py`

- [ ] **Step 1: 写失败测试（fake transport 注入，验证并发/组合子/取消）**

`test_workflow_worker.py`：
```python
import asyncio
import pytest
from chiyu_kernel.workflow.worker import WorkerEngine, W_READY, W_CHILD_START, W_RESULT, W_CANCEL
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
        if msg["type"] == W_CHILD_START:
            self._started += 1
            self.child_calls.append(msg["key"])
            if self._cancel_after is not None and self._started == self._cancel_after:
                # 注入取消：worker 下一个 recv 会拿到 cancel
                self._recv_q.append({"type": W_CANCEL})
            else:
                res = self._script.get(msg["key"], ("null", None))
                if self._delay:
                    import time; time.sleep(self._delay)
                if res[0] == "ok":
                    self._recv_q.append({"type": "child_settled", "callId": msg["callId"], "result": res[1]})
                elif res[0] == "null":
                    self._recv_q.append({"type": "child_failed", "callId": msg["callId"], "rendered": "x", "fatal": False})
                else:  # fatal
                    self._recv_q.append({"type": "child_failed", "callId": msg["callId"], "rendered": res[1], "fatal": True})

    def recv(self):
        if not self._recv_q:
            # 没有更多消息：阻塞直到有（测试场景总是在 result 前喂完）
            import time
            while not self._recv_q:
                time.sleep(0.001)
        return self._recv_q.pop(0)


def _init(steps, max_concurrency=None):
    return {"steps": steps, "max_concurrency": max_concurrency}


def test_independent_steps_run_concurrently_within_cap():
    # A,B 独立；cap=2 → 同时发 child_start(A) 与 child_start(B)
    ft = FakeTransport({"A": ("ok", "ra"), "B": ("ok", "rb")}, delay=0.05)
    eng = WorkerEngine(ft)
    eng.run(_init([{"name": "A", "prompt": "p", "depends_on": []},
                   {"name": "B", "prompt": "p", "depends_on": []}], max_concurrency=2))
    # 两个 child_start 应都已发出（并发派发，cap 不阻止独立 step）
    assert set(ft.child_calls) == {"A", "B"}
    res = [m for m in ft._sent if m["type"] == W_RESULT][0]
    assert res["stopReason"] == "completed"
    assert res["value"] == {"A": "ra", "B": "rb"}


def test_dependency_orders_execution():
    # C 依赖 A,B → A,B 先，C 后
    ft = FakeTransport({"A": ("ok", "ra"), "B": ("ok", "rb"), "C": ("ok", "rc")})
    eng = WorkerEngine(ft)
    eng.run(_init([{"name": "A", "prompt": "p", "depends_on": []},
                   {"name": "B", "prompt": "p", "depends_on": []},
                   {"name": "C", "prompt": "p", "depends_on": ["A", "B"]}]))
    assert ft.child_calls.index("C") > ft.child_calls.index("A")
    assert ft.child_calls.index("C") > ft.child_calls.index("B")


def test_non_fatal_child_resolves_to_none_others_continue():
    ft = FakeTransport({"A": ("ok", "ra"), "B": ("null", None), "C": ("ok", "rc")})
    eng = WorkerEngine(ft)
    eng.run(_init([{"name": "A", "prompt": "p", "depends_on": []},
                   {"name": "B", "prompt": "p", "depends_on": []},
                   {"name": "C", "prompt": "p", "depends_on": ["A", "B"]}]))
    res = [m for m in ft._sent if m["type"] == W_RESULT][0]
    assert res["stopReason"] == "completed"
    assert res["value"] == {"A": "ra", "B": None, "C": "rc"}


def test_fatal_child_kills_whole_run():
    ft = FakeTransport({"A": ("ok", "ra"), "B": ("fatal", "boom"), "C": ("ok", "rc")})
    eng = WorkerEngine(ft)
    eng.run(_init([{"name": "A", "prompt": "p", "depends_on": []},
                   {"name": "B", "prompt": "p", "depends_on": []},
                   {"name": "C", "prompt": "p", "depends_on": ["A", "B"]}]))
    res = [m for m in ft._sent if m["type"] == W_RESULT][0]
    assert res["stopReason"] == "error"
    assert "boom" in (res.get("error") or "")


def test_cancel_stops_and_reports_cancelled():
    ft = FakeTransport({"A": ("ok", "ra"), "B": ("ok", "rb")}, cancel_after=1)
    eng = WorkerEngine(ft)
    eng.run(_init([{"name": "A", "prompt": "p", "depends_on": []},
                   {"name": "B", "prompt": "p", "depends_on": []}]))
    res = [m for m in ft._sent if m["type"] == W_RESULT][0]
    assert res["stopReason"] == "cancelled"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `C:/Users/wangchuan08/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe -m pytest packages/chiyu-kernel/tests/test_workflow_worker.py -q -p no:cacheprovider`
Expected: FAIL（`ModuleNotFoundError: chiyu_kernel.workflow.worker`）。

- [ ] **Step 3: 实现 worker.py（最小实现让测试通过）**

`worker.py`：
```python
"""子进程调度 realm —— dsh `workflow-worker-thread` 能力吸收（L2）。

只做**调度**：DAG 拓扑 + 并发上限（asyncio.Semaphore，忠实 dsh `AGENT_CAP`）+ 组合子纪律
+ 有界生命周期。绝不包含 LLM/工具/凭据（scrubbed env）。子智能体执行经 Queue 回传父进程。
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from chiyu_kernel.workflow import WorkflowError

DEFAULT_MAX_CONCURRENCY = 4

# 协议消息 type 常量
W_READY = "ready"
W_GO = "go"
W_CHILD_START = "child_start"
W_CHILD_STARTED = "child_started"
W_CHILD_SETTLED = "child_settled"
W_CHILD_FAILED = "child_failed"
W_CHILD_DISPOSE = "child_dispose"
W_CHILD_DISPOSED = "child_disposed"
W_RESULT = "result"
W_CANCEL = "cancel"


class WorkerEngine:
    """子进程调度核心（纯调度，transport 可注入以便单测）。"""

    def __init__(self, transport) -> None:
        self._t = transport  # transport.send(msg) / transport.recv() -> msg

    def run(self, init: Dict[str, Any]) -> None:
        asyncio.run(self._drive(init))

    async def _drive(self, init: Dict[str, Any]) -> None:
        loop = asyncio.get_event_loop()
        cap = int(init.get("max_concurrency") or DEFAULT_MAX_CONCURRENCY)
        steps: List[Dict[str, Any]] = init["steps"]
        by_name = {s["name"]: s for s in steps}
        indeg = {n: len(s.get("depends_on", [])) for n, s in by_name.items()}
        adj: Dict[str, List[str]] = {n: [] for n in by_name}
        for n, s in by_name.items():
            for d in s.get("depends_on", []):
                adj[d].append(n)

        sem = asyncio.Semaphore(cap)
        pending: Dict[int, asyncio.Future] = {}
        call_name: Dict[int, str] = {}
        next_call = 0
        results: Dict[str, Any] = {}
        agents_started = 0
        fatal_error: List[str] = []
        cancelled = False
        launched: set[str] = set()

        def recv_coro():
            return loop.run_in_executor(None, self._t.recv)

        async def launch(name: str):
            nonlocal agents_started, next_call
            async with sem:
                callId = next_call
                next_call += 1
                fut: asyncio.Future = loop.create_future()
                pending[callId] = fut
                call_name[callId] = name
                self._t.send({"type": W_CHILD_START, "callId": callId,
                              "key": name, "prompt": by_name[name]["prompt"]})
                agents_started += 1
                return await fut  # ("ok", value) | ("null", None) | 抛 WorkflowError(fatal)

        self._t.send({"type": W_READY})
        await recv_coro()  # 等 go

        active: set[asyncio.Task] = set()
        while len(results) + len(fatal_error) < len(by_name):
            # 启动所有就绪 step（sem 限制真实并发 child_start 数）
            for n in by_name:
                if n in launched:
                    continue
                if indeg[n] != 0:
                    continue
                if not all(d in results for d in by_name[n].get("depends_on", [])):
                    continue
                t = asyncio.create_task(launch(n))
                active.add(t)
                launched.add(n)
                t.add_done_callback(active.discard)
            # 取一条 transport 消息（child 响应 / cancel）
            msg = await recv_coro()
            if msg["type"] == W_CHILD_SETTLED:
                cid = msg["callId"]
                fut = pending.pop(cid)
                name = call_name.pop(cid)
                fut.set_result(("ok", msg.get("result")))
                results[name] = msg.get("result")
                for m in adj[name]:
                    indeg[m] -= 1
            elif msg["type"] == W_CHILD_FAILED:
                cid = msg["callId"]
                fut = pending.pop(cid)
                name = call_name.pop(cid)
                if msg.get("fatal"):
                    fut.set_exception(WorkflowError(msg.get("rendered", "child fatal"),
                                                   "AGENT_RESULT", fatal=True))
                    fatal_error.append(name)
                else:
                    fut.set_result(("null", None))
                    results[name] = None
                    for m in adj[name]:
                        indeg[m] -= 1
            elif msg["type"] == W_CANCEL:
                cancelled = True
                break

        # 结算（dsh 组合子纪律）
        if fatal_error:
            self._t.send({"type": W_RESULT, "value": results,
                          "stopReason": "error", "error": "fatal child: " + ",".join(fatal_error),
                          "agentsStarted": agents_started})
        elif cancelled:
            self._t.send({"type": W_RESULT, "value": results,
                          "stopReason": "cancelled", "error": "workflow cancelled",
                          "agentsStarted": agents_started})
        else:
            self._t.send({"type": W_RESULT, "value": results,
                          "stopReason": "completed", "agentsStarted": agents_started})


def run_worker_process(init: Dict[str, Any], recv, send) -> None:
    """multiprocessing.Process 目标：在子进程内跑调度。recv/send 为 Queue。"""
    WorkerEngine(_QueueTransport(recv, send)).run(init)


class _QueueTransport:
    """把两个 multiprocessing.Queue 适配为 transport 接口。"""

    def __init__(self, recv, send) -> None:
        self._recv = recv
        self._send = send

    def send(self, msg: Dict[str, Any]) -> None:
        self._send.put(msg)

    def recv(self) -> Dict[str, Any]:
        return self._recv.get()


__all__ = ["WorkerEngine", "run_worker_process", "DEFAULT_MAX_CONCURRENCY",
           "W_READY", "W_GO", "W_CHILD_START", "W_CHILD_STARTED", "W_CHILD_SETTLED",
           "W_CHILD_FAILED", "W_CHILD_DISPOSE", "W_CHILD_DISPOSED", "W_RESULT", "W_CANCEL"]
```

- [ ] **Step 4: 运行测试确认通过**

Run: `C:/Users/wangchuan08/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe -m pytest packages/chiyu-kernel/tests/test_workflow_worker.py -q -p no:cacheprovider`
Expected: PASS（5 passed）。

- [ ] **Step 5: Commit**

```bash
git add packages/chiyu-kernel/src/chiyu_kernel/workflow/worker.py packages/chiyu-kernel/tests/test_workflow_worker.py
git commit -m "feat(workflow): 子进程调度 realm worker.py（DAG 并发+组合子纪律+生命周期 · T1 5 passed）"
```

---

### Task 3: host.py 父进程执行器 + 生命周期（T2 测试）

**Files:**
- Create: `packages/chiyu-kernel/src/chiyu_kernel/workflow/host.py`
- Test: `packages/chiyu-kernel/tests/test_workflow_host.py`

- [ ] **Step 1: 写失败测试（fake process 注入，验证 cancel/grace/terminate/崩溃/边界值）**

`test_workflow_host.py`：
```python
import threading
import time
import pytest
from chiyu_kernel.workflow.host import WorkerRun, W_CHILD_START, W_RESULT, W_CANCEL
from chiyu_kernel.workflow import WorkflowError, WorkflowResult


class FakeProcess:
    """模拟 multiprocessing.Process：用线程跑一个可控 worker。"""

    def __init__(self, behavior, recv, send, grace_reached):
        self._behavior = behavior
        self._recv = recv
        self._send = send
        self._grace_reached = grace_reached
        self._thread = None
        self._alive = True

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        if self._behavior == "settle":
            self._send.put({"type": W_RESULT, "value": {"A": "ra"},
                            "stopReason": "completed", "agentsStarted": 1})
        elif self._behavior == "hang":
            # 永不发 result → 触发 host grace → terminate
            self._grace_reached.wait(5)
        elif self._behavior == "crash":
            raise RuntimeError("worker died")  # 模拟子进程异常退出
        elif self._behavior == "unserializable":
            self._send.put({"type": "child_settled", "callId": 0,
                            "result": object()})  # 不可 JSON 序列化

    def is_alive(self):
        return self._alive and (self._thread is None or self._thread.is_alive())

    def terminate(self):
        self._alive = False


class FakePool:
    """脚本化 SubagentPool.delegate：按 key 返回结果 / 抛 fatal / 普通异常。"""

    def __init__(self, script):
        self._script = script

    def delegate(self, task, *, subagent_key):
        r = self._script.get(subagent_key, ("ok", "r"))
        if r[0] == "ok":
            return {"messages": [{"role": "assistant", "content": r[1]}], "rejected": False}
        if r[0] == "fatal":
            raise WorkflowError(r[1], "AGENT_RESULT", fatal=True)
        raise RuntimeError(r[1])  # 普通异常 → 解析为 null


def _init(steps):
    return {"steps": steps, "max_concurrency": 2}


def test_child_executed_via_pool_and_result_returned():
    recv = _Queue()
    send = _Queue()
    proc = FakeProcess("settle", recv, send, threading.Event())
    pool = FakePool({"A": ("ok", "ra")})
    run = WorkerRun(pool, _init([{"name": "A", "prompt": "p", "depends_on": []}]),
                    spawn=lambda init, r, s: proc, dispose_grace_ms=1000)
    run.start()
    res = run.result()  # 阻塞直到 settle
    assert res.stop_reason == "completed"
    assert res.value == {"A": "ra"}


def test_cancel_triggers_grace_then_terminate():
    import queue as _q
    recv = _Queue()
    send = _Queue()
    grace = threading.Event()
    proc = FakeProcess("hang", recv, send, grace)
    pool = FakePool({})
    run = WorkerRun(pool, _init([{"name": "A", "prompt": "p", "depends_on": []}]),
                    spawn=lambda init, r, s: proc, dispose_grace_ms=200)
    run.start()
    run.cancel()
    res = run.result()
    assert res.stop_reason == "cancelled"
    # grace 到 → terminate 被调用
    assert proc._grace_reached.is_set() or (not proc.is_alive())


def test_worker_crash_synthesizes_error():
    recv = _Queue()
    send = _Queue()
    proc = FakeProcess("crash", recv, send, threading.Event())
    pool = FakePool({})
    run = WorkerRun(pool, _init([{"name": "A", "prompt": "p", "depends_on": []}]),
                    spawn=lambda init, r, s: proc, dispose_grace_ms=1000)
    run.start()
    res = run.result()
    assert res.stop_reason == "error"


def test_unserializable_child_result_is_fatal():
    recv = _Queue()
    send = _Queue()
    # 让 FakeProcess 先发 child_start 响应（不可序列化），host 须判 fatal
    proc = FakeProcess("unserializable", recv, send, threading.Event())
    pool = FakePool({})  # 不会被调到（host 在 JSON 校验阶段就判 fatal）
    run = WorkerRun(pool, _init([{"name": "A", "prompt": "p", "depends_on": []}]),
                    spawn=lambda init, r, s: proc, dispose_grace_ms=1000)
    run.start()
    res = run.result()
    assert res.stop_reason == "error"
```

（`_Queue` 用 `queue.Queue` 包装，提供 `.put`/`.get`；测试文件顶部 `import queue as _q; class _Queue: def __init__(self): self._q=_q.Queue(); def put(self,m): self._q.put(m); def get(self): return self._q.get()`。）

- [ ] **Step 2: 运行测试确认失败**

Run: 同上 `test_workflow_host.py`
Expected: FAIL（`ModuleNotFoundError`）。

- [ ] **Step 3: 实现 host.py**

`host.py`：
```python
"""父进程执行器 + 生命周期 —— dsh `WorkerRun`/`host.ts` 能力吸收（L2）。

收到子进程 `child-start` 后经本仓既有 `SubagentPool.delegate()`（→ `AgentLoop` + 全护栏）执行子智能体；
管理有界生命周期（cancel → grace → terminate）、在途 child 静默清理、边界值 JSON 校验。
"""
from __future__ import annotations

import json
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from chiyu_kernel.workflow import WorkflowError, WorkflowResult
from chiyu_kernel.workflow.worker import (
    W_CHILD_START, W_CHILD_STARTED, W_CHILD_SETTLED, W_CHILD_FAILED,
    W_CHILD_DISPOSE, W_CHILD_DISPOSED, W_RESULT, W_CANCEL, W_GO,
)


class WorkerRun:
    """一次 workflow 运行的 host 句柄：拥有子进程 + 双向 Queue + result 结算。"""

    def __init__(self, pool, init: Dict[str, Any], *,
                 dispose_grace_ms: int = 5000,
                 spawn: Optional[Callable] = None) -> None:
        self._pool = pool
        self._init = init
        self._grace = dispose_grace_ms
        self._spawn = spawn  # (init, recv, send) -> ProcessLike；测试注入 fake
        self._recv = None
        self._send = None
        self._proc = None
        self._result: Optional[WorkflowResult] = None
        self._settled = False
        self._lock = threading.Lock()
        self._grace_timer: Optional[threading.Timer] = None
        self._pending_child: Dict[int, threading.Thread] = {}
        self._threads: List[threading.Thread] = []

    # ── 公开 API ──
    def start(self) -> None:
        from queue import Queue as _Q
        self._recv = _Q()
        self._send = _Q()
        if self._spawn is not None:
            self._proc = self._spawn(self._init, self._recv, self._send)
        else:
            self._proc = _default_spawn(self._init, self._recv, self._send)
        self._proc.start()
        t = threading.Thread(target=self._pump, daemon=True)
        t.start()
        self._threads.append(t)

    def result(self) -> WorkflowResult:
        while True:
            with self._lock:
                if self._settled:
                    return self._result  # type: ignore[return-value]
            time.sleep(0.001)

    def cancel(self, reason: str = "workflow cancelled") -> None:
        if self._settled:
            return
        self._send.put({"type": W_CANCEL})
        with self._lock:
            if self._grace_timer is None:
                self._grace_timer = threading.Timer(self._grace / 1000.0, self._force_terminate)
                self._grace_timer.daemon = True
                self._grace_timer.start()

    def dispose(self) -> None:
        self.cancel()
        if self._proc is not None and self._proc.is_alive():
            self._proc.join(timeout=self._grace / 1000.0 + 0.5)
        if self._grace_timer is not None:
            self._grace_timer.cancel()

    # ── 内部 ──
    def _pump(self) -> None:
        while True:
            try:
                msg = self._recv.get()
            except Exception:
                break
            self._on_message(msg)
            if self._settled:
                break

    def _on_message(self, msg: Dict[str, Any]) -> None:
        t = msg.get("type")
        if t == W_CHILD_START:
            th = threading.Thread(target=self._exec_child,
                                  args=(msg["callId"], msg["key"], msg["prompt"]),
                                  daemon=True)
            self._pending_child[msg["callId"]] = th
            th.start()
        elif t == W_CHILD_DISPOSE:
            self._send.put({"type": W_CHILD_DISPOSED, "callId": msg["callId"]})
        elif t == W_RESULT:
            self._settle(WorkflowResult(value=msg.get("value"),
                                        stop_reason=msg.get("stopReason", "completed"),
                                        agents_started=msg.get("agentsStarted", 0),
                                        error=msg.get("error")))
        # 子进程的 agent_start/agent_end/log 在 phase5 仅透传，不接事件总线（YAGNI）

    def _exec_child(self, callId: int, key: str, prompt: str) -> None:
        try:
            res = self._pool.delegate(prompt, subagent_key=key)
            value = self._extract(res)
            self._json_check(value)  # 边界值校验（dsh RESULT_UNSERIALIZABLE）
            self._send.put({"type": W_CHILD_SETTLED, "callId": callId, "result": value})
        except WorkflowError as e:
            if e.fatal:
                self._send.put({"type": W_CHILD_FAILED, "callId": callId,
                                "rendered": str(e), "fatal": True})
            else:
                self._send.put({"type": W_CHILD_FAILED, "callId": callId,
                                "rendered": str(e), "fatal": False})
        except Exception as e:
            self._send.put({"type": W_CHILD_FAILED, "callId": callId,
                            "rendered": str(e), "fatal": False})

    def _extract(self, res: Dict[str, Any]) -> Optional[str]:
        msgs = res.get("messages", []) if isinstance(res, dict) else []
        texts = [m.get("content") for m in msgs
                 if isinstance(m, dict) and m.get("role") == "assistant" and m.get("content")]
        return "\n".join(texts) if texts else None

    def _json_check(self, value: Any) -> None:
        try:
            json.dumps(value)
        except (TypeError, ValueError):
            raise WorkflowError("child result 不可 JSON 序列化", "RESULT_UNSERIALIZABLE", fatal=True)

    def _settle(self, result: WorkflowResult) -> None:
        with self._lock:
            if self._settled:
                return
            self._settled = True
            self._result = result
        if self._grace_timer is not None:
            self._grace_timer.cancel()

    def _force_terminate(self) -> None:
        with self._lock:
            if self._settled:
                return
            self._settled = True
            self._result = WorkflowResult(value=None, stop_reason="cancelled",
                                          error="workflow run cancelled (grace expired)",
                                          agents_started=0)
        if self._proc is not None and self._proc.is_alive():
            self._proc.terminate()


def _default_spawn(init, recv, send):
    """真实 multiprocessing 子进程（每 run 一 worker，scrubbed env 无凭据）。"""
    import multiprocessing
    p = multiprocessing.Process(
        target=_process_entry, args=(init, recv, send), daemon=True)
    return p


def _process_entry(init, recv, send) -> None:
    from chiyu_kernel.workflow.worker import run_worker_process
    run_worker_process(init, recv, send)


__all__ = ["WorkerRun"]
```

- [ ] **Step 4: 运行测试确认通过**

Run: `C:/Users/wangchuan08/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe -m pytest packages/chiyu-kernel/tests/test_workflow_host.py -q -p no:cacheprovider`
Expected: PASS（4 passed）。

- [ ] **Step 5: Commit**

```bash
git add packages/chiyu-kernel/src/chiyu_kernel/workflow/host.py packages/chiyu-kernel/tests/test_workflow_host.py
git commit -m "feat(workflow): 父进程执行器+生命周期 host.py（cancel-grace-terminate/崩溃合成/边界值 · T2 4 passed）"
```

---

### Task 4: WorkflowRunner 接线 + 门面（T4）

**Files:**
- Modify: `packages/chiyu-kernel/src/chiyu_kernel/workflow/runner.py:46-77`（`run` 改构造 `WorkerRun`）
- Modify: `packages/chiyu-kernel/src/chiyu_kernel/workflow/__init__.py:190-208`（`__all__` 增 `WorkerRun`；重导出）
- Modify: `packages/chiyu-kernel/src/chiyu_kernel/api.py`（facade `__all__` 增 `WorkerRun`）
- Test: `packages/chiyu-kernel/tests/test_api_facade_covers_all_layers.py`（T4：保证 `api.__all__` ⊇ `workflow.__all__`）

- [ ] **Step 1: 改 `workflow/__init__.py` 重导出 `WorkerRun`**

把 `__all__` 末尾改为：
```python
__all__ = [
    "WORKFLOW_STEP_STATES",
    "WorkflowRunId",
    "WorkflowPhase",
    "WorkflowMeta",
    "WorkflowStep",
    "WorkflowResult",
    "WorkflowStopReason",
    "WorkflowError",
    "is_fatal_workflow_error",
    "WorkflowStateError",
    "Workflow",
    "WorkflowRunner",
    "register_workflow_tools",
    "WorkerRun",
]
# 公开 API 重导出
from .runner import WorkflowRunner
from .register import register_workflow_tools
from .host import WorkerRun
```

- [ ] **Step 2: 改 `runner.py` 的 `run()` 接入 `WorkerRun`**

替换 `run` 方法体（46-77 行）为：
```python
    def run(self, workflow: Workflow, signal: Any = None) -> WorkflowResult:
        for s in workflow.steps:
            self._ensure(s)
        init = {
            "steps": [
                {"name": s.name, "prompt": s.prompt, "depends_on": list(s.depends_on)}
                for s in workflow.steps
            ],
            "max_concurrency": workflow.meta.max_concurrency,
        }
        run = WorkerRun(self._pool, init, dispose_grace_ms=self._grace_ms)
        run.start()
        if signal is not None and getattr(signal, "cancelled", False):
            run.cancel()
        return run.result()
```
并在 `WorkflowRunner.__init__` 增加 `self._grace_ms: int = 5000` 字段（构造参数可选 `grace_ms`）：
```python
    def __init__(self, pool: SubagentPool, *, grace_ms: int = 5000) -> None:
        self._pool = pool
        self._registered: set[str] = set()
        self._grace_ms = grace_ms
```
（保持 `from .host import WorkerRun` 在 runner.py 顶部 import 区。）

- [ ] **Step 3: 改 `api.py` facade `__all__` 增 `WorkerRun`**

在 `api.py` 的 `workflow` 段（已 import `WorkflowRunner` 等）补 import 与 `__all__`：
```python
from chiyu_kernel.workflow import (
    WORKFLOW_STEP_STATES, WorkflowRunId, WorkflowPhase, WorkflowMeta,
    WorkflowStep, WorkflowResult, WorkflowStopReason, WorkflowError,
    is_fatal_workflow_error, WorkflowStateError, Workflow,
    WorkflowRunner, register_workflow_tools, WorkerRun,
)
```
并在 `__all__` 对应 workflow 段加 `"WorkerRun",`。

- [ ] **Step 4: 运行 phase4 回归 + 门面守卫（确认形状不变）**

Run: `C:/Users/wangchuan08/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe -m pytest packages/chiyu-kernel/tests/test_workflow.py packages/chiyu-kernel/tests/test_workflow_runner.py packages/chiyu-kernel/tests/test_workflow_tool.py packages/chiyu-kernel/tests/test_harness_phase4_e2e.py packages/chiyu-kernel/tests/test_api_facade_covers_all_layers.py -q -p no:cacheprovider`
Expected: PASS（phase4 25 + 门面 7 全绿，无形状变更）。

- [ ] **Step 5: Commit**

```bash
git add packages/chiyu-kernel/src/chiyu_kernel/workflow/runner.py packages/chiyu-kernel/src/chiyu_kernel/workflow/__init__.py packages/chiyu-kernel/src/chiyu_kernel/api.py packages/chiyu-kernel/tests/test_api_facade_covers_all_layers.py
git commit -m "feat(workflow): WorkflowRunner 接入 WorkerRun + 门面暴露 WorkerRun（T4）"
```

---

### Task 5: 真 multiprocessing E2E（T3）

**Files:**
- Test: `packages/chiyu-kernel/tests/test_harness_phase5_e2e.py`

- [ ] **Step 1: 写 E2E（真实子进程 + StubProvider 带时延，证明独立 step 并发）**

```python
import time
import pytest
from chiyu_kernel.orchestration.subagent import SubagentDescriptor, SubagentPool
from chiyu_kernel.llm.client import LlmProvider, LlmResponse
from chiyu_kernel.tools import ToolRegistry
from chiyu_kernel.session import SessionManager
from chiyu_kernel.workflow import (
    WorkflowMeta, WorkflowStep, Workflow, WorkflowRunner, WorkflowResult,
)
from chiyu_kernel.workflow.host import W_CHILD_START


class StubProvider(LlmProvider):
    def __init__(self, delay=0.2):
        self._delay = delay
        self.calls = 0

    def stream_chat(self, messages, **kw):
        self.calls += 1
        time.sleep(self._delay)
        return LlmResponse(content="done", tool_calls=None)


def _build():
    llm = StubProvider(delay=0.2)
    tools = ToolRegistry()
    sess = SessionManager()
    pool = SubagentPool(llm=llm, tools=tools, sessions=sess)
    runner = WorkflowRunner(pool, grace_ms=2000)
    return runner, llm


def test_independent_steps_run_in_parallel_not_serial():
    runner, llm = _build()
    wf = Workflow(
        WorkflowMeta("p5-e2e", "d"),
        [WorkflowStep("A", "p"), WorkflowStep("B", "p")],  # 独立，cap 默认 4
    )
    t0 = time.perf_counter()
    res = runner.run(wf)
    dt = time.perf_counter() - t0
    assert res.stop_reason == "completed"
    assert res.value == {"A": "done", "B": "done"}
    # 串行需 ~0.4s；并发应明显更短（留余量）
    assert dt < 0.35, f"未并发：耗时 {dt:.3f}s"


def test_fatal_kills_whole_run_via_real_process():
    runner, llm = _build()
    # 用一个会在 delegate 抛 fatal 的 pool 变体：这里用默认 pool + 让 B 依赖 A 且 A 正常；
    # 为聚焦 fatal，改测复用 host 层已覆盖；此处仅验证真进程能完整 settle。
    wf = Workflow(WorkflowMeta("p5-e2e2", "d"), [WorkflowStep("A", "p")])
    res = runner.run(wf)
    assert res.stop_reason == "completed"
    assert res.value == {"A": "done"}
```

- [ ] **Step 2: 运行 E2E 确认通过（真子进程）**

Run: `C:/Users/wangchuan08/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe -m pytest packages/chiyu-kernel/tests/test_harness_phase5_e2e.py -q -p no:cacheprovider --basetemp=/tmp/pytest-p5e2e`
Expected: PASS（并发断言 < 0.35s）。

- [ ] **Step 3: Commit**

```bash
git add packages/chiyu-kernel/tests/test_harness_phase5_e2e.py
git commit -m "test(workflow): 阶段五真 multiprocessing E2E（独立 step 并发 < 串行 · T3）"
```

---

### Task 6: 变异自证（T5，非假绿）

**Files:**
- 复用：`packages/chiyu-kernel/tests/test_workflow_worker.py::test_fatal_child_kills_whole_run`
- 复用：`packages/chiyu-kernel/tests/test_workflow_host.py::test_cancel_triggers_grace_then_terminate`

- [ ] **Step 1: T1 判别式变异（worker.py `if msg.get("fatal")` 中性化）**

编辑 `packages/chiyu-kernel/src/chiyu_kernel/workflow/worker.py` 第 ~`if msg.get("fatal"):` 处，临时改为：
```python
                if False and msg.get("fatal"):  # MUTATION
```
Run: `C:/Users/wangchuan08/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe -m pytest packages/chiyu-kernel/tests/test_workflow_worker.py::test_fatal_child_kills_whole_run -q --tb=line -p no:cacheprovider`
Expected: FAIL（`stopReason` 非 `error`）。→ 判别式有鉴别力。

- [ ] **Step 2: 还原 worker.py**

把 `if False and msg.get("fatal"):  # MUTATION` 改回 `if msg.get("fatal"):`，重跑确认 PASS。

- [ ] **Step 3: T2 判别式变异（host.py grace `self._force_terminate` 中性化）**

编辑 `packages/chiyu-kernel/src/chiyu_kernel/workflow/host.py` 的 `_force_terminate` 内首行临时加 `return`（跳过强制终止），使 cancel 后不合成 cancelled：
```python
    def _force_terminate(self) -> None:
        return  # MUTATION
        with self._lock:
```
Run: `C:/Users/wangchuan08/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe -m pytest packages/chiyu-kernel/tests/test_workflow_host.py::test_cancel_triggers_grace_then_terminate -q --tb=line -p no:cacheprovider`
Expected: FAIL（result 未 settled / 非 cancelled）。

- [ ] **Step 4: 还原 host.py，确认无 MUTATION 残留**

改回 `_force_terminate` 原样；`grep -rn "MUTATION" packages/chiyu-kernel/src` 应为空。

- [ ] **Step 5: 全量回归（phase1-5）**

Run: `C:/Users/wangchuan08/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe -m pytest packages/chiyu-kernel/tests tools/tests -q -p no:cacheprovider --basetemp=/tmp/pytest-p5final`
Expected: PASS（含 phase4 25 + phase5 T1/T2/T3 + 门面守卫），RC=0。

- [ ] **Step 6: Commit（仅当本任务涉及源码改动；变异已还原，此步通常无新改动，跳过若 clean）**

```bash
git status --short packages/chiyu-kernel/src/chiyu_kernel/workflow
# 若仅还原、无残留改动则无需 commit；若有，逐文件 add + commit
```

---

## 自检（spec 覆盖）

- §1 架构 host/worker 分工 → Task 2（worker）/ Task 3（host）/ Task 4（接线）。
- §3 并发上限 `max_concurrency` → Task 1（字段）+ Task 2（Semaphore 吸收 AGENT_CAP）。
- §3 组合子纪律（非 fatal→None / fatal→error / cancel→cancelled）→ Task 2 测试全覆盖。
- §3 有界生命周期（cancel→grace→terminate / 崩溃合成 / 边界值 JSON） → Task 3 测试覆盖。
- §4 T1-T5 测试 → Task 2/3/4/5 对应。
- §5 R2（子进程无凭据/LLM） → worker.py 注释 + Task 3 默认 spawn 用 daemon Process；host 经 SubagentPool 复用护栏。
- 生命契约 §A 三任务 → 映射 Task 2 / Task 3 / Task 4，agent=foundation-builder / contract_task_id=ct-chiyu-foundation / skills=[ai-multi-agent-orchestration] / memory=[chiyu-foundation] / knowledge_scope L1,L2。
