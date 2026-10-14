"""内核结构化错误基类（Batch-7a · 2026-10-14）。

背景：此前内核契约层错误类普遍继承泛型 ``ValueError``（见 Batch-6 §二 G1），
导致 ``except ValueError`` 无差别吞掉全部契约错误、机器不可路由。本模块给出
中性闭集 ``KERNEL_ERROR_CODES``，消费方可按 ``code`` 路由（勿按 message 匹配）。

分类原则（与决策层 ``chiyu_decision/errors.py`` 同纪律，但扩为内核级）：
- ``code`` 为顶层机器可路由字段，``message`` 供人读。
- ``KernelError`` **不继承** ``ValueError`` ⇒ 泛型 ``except ValueError`` 无法再误吞
  契约错误（这正是 Batch-6 §二 G1 点名要消灭的反模式：决策层已修，契约层补齐）。
- ``ValueError`` 仅保留给纯输入形态错误（不进机器路由，不继承 ``KernelError``）。

闭集（新增须同步登记 + 补测试）：
  CONTRACT_VIOLATION  契约/输入不合法（不变量被破坏、结构非法者 fail-closed）。
  ENGINE_FAULT        内核内部不变量被破坏（非消费方输入导致）。
  NOT_FOUND           查找目标不存在。
  PERMISSION_DENIED   权限/授权被拒。
  CONFIRM_REQUIRED    需要二次确认/凭证（如写操作缺决策凭证）。
  CONFIG_ERROR        配置缺失/非法（缺必填键等，替代散落 KeyError）。
"""
from __future__ import annotations

__all__ = ["KernelError", "KERNEL_ERROR_CODES"]


#: 内核错误码闭集（只增不改；消费方按此路由，禁止按 message 匹配）。
KERNEL_ERROR_CODES = frozenset(
    {
        "CONTRACT_VIOLATION",
        "ENGINE_FAULT",
        "NOT_FOUND",
        "PERMISSION_DENIED",
        "CONFIRM_REQUIRED",
        "CONFIG_ERROR",
    }
)


class KernelError(Exception):
    """带机器可路由 ``code`` 的内核失败（替代泛型 ValueError）。

    ``code`` 必须属于 ``KERNEL_ERROR_CODES``；其余字段仅人读。子类以类属性
    ``code`` 给出默认码（见各契约错误类），构造亦可显式覆盖。
    """

    #: 子类覆盖此默认码（默认：契约/输入不合法）。
    code = "CONTRACT_VIOLATION"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        c = code or self.code
        if c not in KERNEL_ERROR_CODES:
            raise ValueError(f"非法内核错误码（应属于闭集）：{c!r}")
        super().__init__(message)
        self.code = c
        self.message = message
