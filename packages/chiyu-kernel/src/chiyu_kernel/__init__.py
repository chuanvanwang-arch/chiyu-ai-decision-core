"""chiyu-kernel —— ChiYu AI Native Foundation 的 L0 契约 + L1 基础设施内核。

授权分级
────────
    kernel    基础授权（本包）—— L0 契约 + L1 基础设施
    decision  核心授权（`chiyu-decision`，阶段 P2）—— KMD 裁决时序 / 九尺子 / 红线
    portal    可选装（`chiyu-portal`，阶段 P2）—— NL→PageSpec→渲染器

⛔ 消费方使用纪律
──────────────────
只许 import `chiyu_kernel.contract` 与 `chiyu_kernel.api`。import 内部实现路径
（如 `chiyu_kernel.store.pg_store`）即违约——守 `tests/test_app_imports_contract_only.py`。
理由：内部实现要能在不破坏消费方的前提下重构（对外轨的 Cython 编译会改模块布局）。

⛔ 本包零领域字面量
────────────────────
粒子类型取值、知识谓词、红线事项目录全部由消费方注入 `TenantProfile`，内核只声明形态。
守卫：`tests/test_contract_no_domain_literals.py`。
"""
from __future__ import annotations

__version__ = "0.1.0"
AUTHORIZATION_LEVEL = "kernel"
LICENSE_SCOPE = ("kernel",)

__all__ = ["__version__", "AUTHORIZATION_LEVEL", "LICENSE_SCOPE"]
