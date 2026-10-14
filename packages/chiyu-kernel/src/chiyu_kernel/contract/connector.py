"""连接器传输层契约 —— L0 单一事实源（零第三方依赖、零 IO、零领域字面量）。

上迁源（GAP-8，Batch-2b，2026-10-14）：APS ``platform/connectors/``
（base.py 接口 + file.py csv/json/xlsx + registry.py 注册表）。

**机制上迁、域值留消费方**：
    · 上迁：无状态工厂接口 / 结果载体契约 / 文件传输（csv/json/xlsx）/
      注册表单一事实源（注册即承诺可拉取）；
    · 留 APS：``legacy_aps`` 域连接器（含 order/排程语义）/ DB·消息类连接器
      （W-5.2 未批源）/ 源系统枚举。

⛔ 本层零 IO。连接器实现（``chiyu_kernel.connectors``）是传输机制的
   sanctioned IO 边界——拉取与格式归一是它的职责本身；但**换算/归一不进
   连接器**（归采纳期，``no_conversion_in_connector``）。
"""
from __future__ import annotations

from typing import Tuple

__all__ = [
    "CONNECTOR_RESULT_FIELDS", "CONNECTOR_NAME_FIELD",
    "FILE_CONNECTOR_FORMATS",
    "CONNECTOR_INVARIANTS",
    "ConnectorNotRegisteredError",
]

# ── 结果载体字段面（与消费方采纳期输入兼容）─────────────────────────
CONNECTOR_RESULT_FIELDS: Tuple[str, ...] = ("rows", "external_refs", "meta")
#: 连接器标记字段（== 注册表键；域源系统名由消费方登记）。
CONNECTOR_NAME_FIELD: str = "name"

# ── 文件连接器支持格式（按扩展名分发）────────────────────────────────
FILE_CONNECTOR_FORMATS: Tuple[str, ...] = ("csv", "json", "xlsx")

# ── 不变式（每条均有守卫测试，不是注释）─────────────────────────────
CONNECTOR_INVARIANTS: Tuple[str, ...] = (
    "stateless_factory",          # fetch(cfg) 每次按传入配置拉取，不持长连接
    "rows_are_list_of_dicts",     # rows 必须 list[dict]（键为外部字段名）
    "no_conversion_in_connector",  # 只拉取+格式归一；换算归采纳期
    "registration_is_promise",    # 注册即承诺可拉取，未实装不得虚假登记
    "unregistered_fails_closed",  # 未注册源系统 ⇒ 抛错，不静默降级
)


class ConnectorNotRegisteredError(KeyError):
    """请求的源系统无已注册连接器（fail-closed：不静默返回空结果）。

    继承 ``KeyError``：与 APS ``get_connector`` 的既有契约一致
    （消费方 ``except KeyError`` 不需改写）。
    """
