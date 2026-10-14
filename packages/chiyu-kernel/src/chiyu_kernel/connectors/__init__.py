"""连接器传输层机制（GAP-8，Batch-2b）——  sanctioned IO 边界。

上迁源：APS ``platform/connectors/``（base/file/registry）。
域连接器（如 APS legacy_aps）与 DB/消息类传输（W-5.2）留消费方；
本包只提供域无关的文件传输 + 注册表机制。
"""
from .base import ConnectorResult, SourceConnector
from .file import FileConnector
from .registry import ConnectorRegistry, default_registry

__all__ = [
    "ConnectorResult", "SourceConnector", "FileConnector",
    "ConnectorRegistry", "default_registry",
]
