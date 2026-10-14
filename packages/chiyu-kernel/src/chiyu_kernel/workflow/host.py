"""父进程执行器 + 生命周期 —— dsh `WorkerRun`/`host.ts` 能力吸收（L2）。

收到子进程 `child-start` 后经本仓既有 `SubagentPool.delegate()`（→ `AgentLoop` + 全护栏）执行子智能体；
管理有界生命周期（cancel → grace → terminate）、子进程崩溃合成 error、边界值 JSON 校验。

⛔ R2 守住：本进程（host）才持有 LLM/工具/凭据；子进程（worker.py）只做调度 realm，
经双向 Queue 把 `child-start` 回传本处执行，绝不新建平行 driver 框架。
"""
from __future__ import annotations

import json
import threading
import time
from typing import Any, Callable, Dict, Mapping, Optional

from chiyu_kernel.workflow import WorkflowError, WorkflowResult
from chiyu_kernel.workflow.worker import (
    W_READY, W_GO, W_CHILD_START, W_CHILD_STARTED, W_CHILD_SETTLED, W_CHILD_FAILED,
    W_CHILD_DISPOSE, W_CHILD_DISPOSED, W_RESULT, W_CANCEL,
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
        import multiprocessing
        # 真实进程路径必须用 multiprocessing.Queue（可跨 spawn 进程传递）；
        # queue.Queue 含不可 pickle 的 lock，Windows spawn 会失败。
        self._recv = multiprocessing.Queue()
        self._send = multiprocessing.Queue()
        # spawn(init, worker_recv, worker_send)：
        #   worker_recv 必须等于 host 的 _send（worker 读 host 写）
        #   worker_send 必须等于 host 的 _recv（host 读 worker 写）
        if self._spawn is not None:
            self._proc = self._spawn(self._init, self._send, self._recv)
        else:
            self._proc = _default_spawn(self._init, self._send, self._recv)
        self._proc.start()
        t = threading.Thread(target=self._pump, daemon=True)
        t.start()
        self._threads.append(t)
        # 看门狗：子进程未结算即退出 → 合成 error（忠实 dsh 崩溃合成语义）
        w = threading.Thread(target=self._watchdog, daemon=True)
        w.start()
        self._threads.append(w)

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
        if t == W_READY:
            # 子进程就绪 → 回 go，让其开始派发（worker 在 W_READY 后阻塞等 go）
            self._send.put({"type": W_GO})
        elif t == W_CHILD_START:
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
            self._send.put({"type": W_CHILD_FAILED, "callId": callId,
                            "rendered": str(e), "fatal": e.fatal})
        except Exception as e:
            self._send.put({"type": W_CHILD_FAILED, "callId": callId,
                            "rendered": str(e), "fatal": False})

    def _extract(self, res: Mapping[str, Any]) -> Any:
        """抽取 assistant 文本（dsh 的 value）。保留原始类型以便 JSON 边界校验生效。"""
        msgs = res.get("messages", []) if isinstance(res, Mapping) else []
        contents = [m.get("content") for m in msgs
                    if isinstance(m, Mapping) and m.get("role") == "assistant"
                    and m.get("content") is not None]
        if not contents:
            return None
        if len(contents) == 1:
            return contents[0]
        return "\n".join(str(c) for c in contents)

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

    def _watchdog(self) -> None:
        """子进程意外退出且未结算 → 合成 error（忠实 dsh 崩溃合成）。"""
        dead_since: Optional[float] = None
        while True:
            with self._lock:
                if self._settled:
                    return
            alive = self._proc.is_alive() if self._proc is not None else False
            now = time.monotonic()
            if not alive:
                if dead_since is None:
                    dead_since = now
                elif now - dead_since > 0.1:
                    self._settle(WorkflowResult(
                        value=None, stop_reason="error",
                        error="worker process exited unexpectedly", agents_started=0))
                    return
            else:
                dead_since = None
            time.sleep(0.02)

    def _force_terminate(self) -> None:
        with self._lock:
            if self._settled:
                return
            self._settled = True
            self._result = WorkflowResult(
                value=None, stop_reason="cancelled",
                error="workflow run cancelled (grace expired)", agents_started=0)
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
