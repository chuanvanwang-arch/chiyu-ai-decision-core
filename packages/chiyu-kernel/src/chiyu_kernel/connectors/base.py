"""连接器接口与结果载体（机制层 IO 边界之一）。

上迁源：APS ``platform/connectors/base.py``（living contract 明文）。

接口契约：
    · ``SourceConnector.fetch(cfg) -> ConnectorResult``：从某源系统**拉取**原始行；
    · ``rows`` 必须 ``list[dict]``（键为**外部字段名**，换算归采纳期）；
    · 连接器是**无状态工厂**：每次按传入 cfg 拉取，不持有长连接。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping

__all__ = ["ConnectorResult", "SourceConnector"]


@dataclass
class ConnectorResult:
    """连接器输出载体（与采纳期输入兼容的契约）。

    Attributes:
        rows: 外部原始行（list[dict]，键为外部字段名）。
        external_refs: 溯源引用（文件名 / 表名 / offset 等），落审计用。
        meta: 结构化元信息（扩展类型 / 拉取计数等）。
    """

    rows: List[Dict[str, Any]]
    external_refs: List[str] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)


class SourceConnector(ABC):
    """源系统连接器接口（无状态，按 cfg 拉取）。"""

    #: 连接器标记（== 注册表键；域源系统名由消费方登记）。
    name: str = ""

    @abstractmethod
    def fetch(self, cfg: Mapping[str, Any]) -> ConnectorResult:
        """从源系统拉取原始行。

        Args:
            cfg: 连接器配置（路径 / 连接串 / 查询等），由调用方传入。

        Returns:
            ConnectorResult，其 ``rows`` 必须为 ``list[dict]``（外部字段名为键）。

        Raises:
            ValueError: 配置非法（由实现决定）。
            FileNotFoundError: 源不可达（由实现决定）。
        """
        ...
