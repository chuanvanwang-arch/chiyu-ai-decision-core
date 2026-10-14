"""回填通道（内置知识—向量通道规范 · 回填口径的内核版 —— 语义逐字保留）。

属性后登记时从日志轨（append-only memory log）回溯提取历史值回填，留痕复用日志轨
（不新增表）；抽不到值显式记录 skipped 不静默（反假绿铁律）。

与 `vector/coverage.backfill_plan` 的对接（demo 有实现无闭环）：
    · `coverage.backfill_plan(rows)` 产出「缺真向量粒子 id」清单（**只产计划不执行**，
      回填是写操作，须经决策第 0 闸 —— 本项目纪律）；
    · 本模块提供「从历史记录提取缺失属性并落痕」的通用机制，两类回填互补：
      向量回填（coverage）与属性回填（本模块）。
"""
from __future__ import annotations

from typing import Any, Callable


class BackfillChannel:
    """从给定取值函数回溯历史记录，回填缺失属性。

    fetch_history(record) -> 历史载荷；extract(value) -> 抽取目标属性；
    回填结果以 append 方式写入日志轨（不覆盖原始记忆载荷）。
    """

    def __init__(self, log_track: Any | None = None):
        self.log_track = log_track

    def backfill(self, key: str, extract: Callable[[dict], Any | None],
                 source: dict | None = None) -> dict:
        """回填单条缺失属性。

        返回 {"key":..., "value":..., "status": "filled"|"skipped", "source":...}
        """
        record = source or (self.log_track.get(key) if self.log_track else None)
        if record is None:
            return {"key": key, "value": None, "status": "skipped",
                    "reason": "no_source_record"}
        val = extract(record)
        if val is None or (isinstance(val, (list, dict, set, str)) and not val):
            return {"key": key, "value": None, "status": "skipped",
                    "reason": "no_value_extracted"}
        # 回填落痕：记一条追加记录（复用日志轨语义，不覆盖原值）
        if self.log_track is not None:
            self.log_track.append(f"{key}::backfill", {
                "type": "backfill", "target": key,
                "value": val, "source": "log_track",
            })
        return {"key": key, "value": val, "status": "filled", "source": "log_track"}


__all__ = ["BackfillChannel"]
