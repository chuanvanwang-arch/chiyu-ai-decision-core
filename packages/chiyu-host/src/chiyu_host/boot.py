"""Boot manifest 生成（供 T3 thin launcher 注入 window.__DSH_BOOT__）。

DSH client 经 `apps/web` 启动器注入 boot manifest 才能脱离 standalone vite 启动；
M0 用 thin launcher 注入本 manifest，将 client 的 connection base URL 指向 chiyu-host。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def build_boot_manifest(base_url: str, modules: Optional[List[str]] = None) -> Dict[str, Any]:
    """生成 DSH client 启动所需的 __DSH_BOOT__ 内容结构。

    base_url 指向本 chiyu-host；modules 为 client 树扫描得到的 ui-* 模块列表，
    M0 给最小占位（对话/模型/插件清单三块 UI），T3 按实际 client 树填充。
    """
    return {
        "version": "0.1.0",
        "baseUrl": base_url,
        "apiPath": "/api",
        "muxPath": "/api/events.mux",
        "modules": modules or [
            "ui-conversation",
            "ui-model-selection",
            "ui-settings-plugins",
        ],
    }
