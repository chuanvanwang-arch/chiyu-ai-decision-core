"""离线交付硬约束：未显式放行时，向量通道不得出网。

⛔ 判据是**行为**（monkeypatch socket 后调用不得成功），不是"读环境变量看配置"
   —— 后者拦不住"代码里自己 new 了个 http 客户端"。
"""
from __future__ import annotations

import socket

import pytest


def test_network_is_blocked_without_optin(monkeypatch):
    monkeypatch.delenv("CHIYU_EMBEDDING_ALLOW_NETWORK", raising=False)

    def _boom(*a, **k):
        raise AssertionError("离线模式下发起了网络连接")

    monkeypatch.setattr(socket.socket, "connect", _boom)
    from chiyu_kernel.vector import embedding_api
    res = embedding_api.embed("测试文本")           # 不得抛 AssertionError
    assert res is None or getattr(res, "tag", None) != "model"
