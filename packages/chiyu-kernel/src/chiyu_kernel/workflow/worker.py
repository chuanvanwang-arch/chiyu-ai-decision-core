"""子进程调度 realm —— dsh `workflow-worker-thread` 能力吸收（L2）。

只做**调度**：DAG 拓扑 + 并发上限（asyncio.Semaphore，忠实 dsh `AGENT_CAP`）+ 组合子纪律
+ 有界生命周期。绝不包含 LLM/工具/凭据（scrubbed env）。子智能体执行经 Queue 回传父进程。
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from chiyu_kernel.workflow import WorkflowError

DEFAULT_MAX_CONCURRENCY = 4

# 协议消息 type 常量（worker↔host，均 JSON dict）
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
                    fatal_error.append(msg.get("rendered", name))
                    for f in pending.values():
                        f.cancel()  # 取消在途 launch，避免 asyncio 未检索异常告警
                    break  # fatal 必须杀死整 run（dsh 组合子纪律）
                else:
                    fut.set_result(("null", None))
                    results[name] = None
                    for m in adj[name]:
                        indeg[m] -= 1
            elif msg["type"] == W_CANCEL:
                cancelled = True
                for f in pending.values():
                    f.cancel()
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
