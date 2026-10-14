"""决策层结构化错误分类（CRM R8 · 2026-10-09）。

背景：CRM 回信 R8 要求暴露统一错误码分类法（对齐未来跨语言迁移的错误语义）。
此前决策侧为泛型 `ValueError`（`spine.py:68/:166`、`scoring.py:51`），catch 侧无法机器判别。
本模块给出**中性闭集**错误码；消费方可按 `code` 路由（勿按 message 字符串匹配）。

分类原则（与 `registry.py` 的 `ScenarioRegistryError` 同纪律）：
- `code` 为顶层机器可路由字段，`message` 供人读。
- 与 CRM 侧 T0 拟引入的 `UNKNOWN_SCENARIO/DIM_MISMATCH/ENGINE_FAULT` 对齐（语义同名）。

闭集（新增须同步登记 + 补测试）：
  ENGINE_FAULT    脊柱内部不变量被破坏（如 S1 缺上下文 / 顺序被重排 / 红线终态复活）。
  UNKNOWN_SCENARIO 决策场景未登记（对应注册表 `require_scenario` 的 ValueError 语义）。
  DIM_MISMATCH    向量维度不一致（消费方写向量时维度不符——CRM A3 对齐）。
  CONTRACT_VIOLATION 契约/输入不合法（输入非法者 fail-closed）。
"""
from __future__ import annotations

__all__ = ["DecisionError", "DECISION_ERROR_CODES"]


#: 错误码闭集（只增不改；消费方按此路由，禁止按 message 匹配）。
DECISION_ERROR_CODES = frozenset(
    {"ENGINE_FAULT", "UNKNOWN_SCENARIO", "DIM_MISMATCH", "CONTRACT_VIOLATION"}
)


class DecisionError(Exception):
    """带机器可路由 `code` 的决策失败（替代泛型 ValueError）。

    `code` 必须属于 `DECISION_ERROR_CODES`；其余字段仅人读。
    """

    def __init__(self, code: str, message: str) -> None:
        if code not in DECISION_ERROR_CODES:
            raise ValueError(f"非法错误码（应属于闭集）：{code!r}")
        super().__init__(message)
        self.code = code
        self.message = message
