"""参考消费层（WS9）—— 端到端样板：一次注入 → 跑决策 → 落库 → 派生图 → 暴露工具。

⛔ 定位：本包是**消费方侧**代码（examples/），不是内核。它演示的正是
   「消费方该写的最少代码」—— 内核零领域字面量，领域内容全在本包 `domain.py`。

五步上手（详见 README.md）：
    1. 写自己的 `domain.py`（粒子类型 / 谓词 / Action / 场景）
    2. `build_app()` —— 一次注入，拿到校验过的 DomainBundle + store + 工具面
    3. `run_decision()` —— 决策脊柱 S1→S5（含红线审批闸 + 落库 + 记忆网）
    4. 读视图 —— `relations` / `timeline` / `backlinks`（单源双视图，只读派生）
    5. `run_canary()` —— 常驻探针，证明「真落库 / 真物化 / 真派生」，不是「表有行」
"""
from __future__ import annotations

from .app import ConsumerApp, build_app, record_outcome, run_decision, sync_graph
from .probes import (
    CLOSED_LOOP_EDGES, ProbeResult, probe_closed_loop, probe_decision_really_persisted,
    probe_graph_is_derived, probe_memory_really_materialized,
    probe_redline_blocks_persist,
)
from .store import InMemoryStore

__all__ = [
    "ConsumerApp", "build_app", "run_decision", "record_outcome", "sync_graph",
    "InMemoryStore",
    "ProbeResult", "CLOSED_LOOP_EDGES",
    "probe_decision_really_persisted", "probe_memory_really_materialized",
    "probe_graph_is_derived", "probe_closed_loop", "probe_redline_blocks_persist",
]
