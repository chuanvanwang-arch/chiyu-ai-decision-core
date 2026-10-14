"""连接器注册表（单一事实源，域源系统名由消费方登记）。

上迁源：APS ``platform/connectors/registry.py``（CONNECTORS 唯一权威映射 +
``get_connector`` 命中断言）。

与 APS 版的差异（机制上收、域值留消费方）：
    · APS 模块级 ``CONNECTORS`` 字典内嵌 ``legacy_aps`` 域连接器 —— 上收为
      **可实例化的 ``ConnectorRegistry``**（消费方自建自注册，零域字面量）；
    · ``default_registry()`` 只预注册域无关的 ``file`` 传输（格式非源系统）；
    · 未注册 ⇒ ``ConnectorNotRegisteredError``（``unregistered_fails_closed``）——
      「注册即承诺可拉取，未选型前不得虚假登记」。
"""
from __future__ import annotations

from typing import Dict, Iterator, List, Type

from chiyu_kernel.contract.connector import ConnectorNotRegisteredError

from .base import SourceConnector
from .file import FileConnector

__all__ = ["ConnectorRegistry", "default_registry"]


class ConnectorRegistry:
    """源系统 → 连接器的注册表（进程内单一事实源）。"""

    def __init__(self) -> None:
        self._connectors: Dict[str, Type[SourceConnector]] = {}

    def register(self, connector: Type[SourceConnector]) -> None:
        """登记一个连接器类（键取其 ``name`` 标记）。"""
        name = str(getattr(connector, "name", "") or "").strip()
        if not name:
            raise ValueError("连接器必须带非空 name 标记才能登记")
        self._connectors[name] = connector

    def names(self) -> List[str]:
        """已登记源系统集合（排序，稳定可对拍）。"""
        return sorted(self._connectors)

    def __contains__(self, source_system: object) -> bool:
        return str(source_system) in self._connectors

    def __iter__(self) -> Iterator[str]:
        return iter(self.names())

    def get(self, source_system: str) -> SourceConnector:
        """按源系统取连接器**实例**（无状态工厂：每次新实例）。

        Raises:
            ConnectorNotRegisteredError: 该源系统尚无已注册连接器。
        """
        cls = self._connectors.get(str(source_system))
        if cls is None:
            raise ConnectorNotRegisteredError(
                f"无已注册连接器：{source_system!r}；已注册 = {self.names()}"
            )
        return cls()


def default_registry() -> ConnectorRegistry:
    """预注册域无关 ``file`` 传输的注册表（消费方在此之上追加域连接器）。"""
    registry = ConnectorRegistry()
    registry.register(FileConnector)
    return registry
