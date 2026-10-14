"""T93 OpenAI 兼容 Provider 守卫（Batch-3 llm provider 补全）。

覆盖：tool_calls 解析（合法 JSON / 非法 ⇒ 空 args 不抛 / 缺 function）/
fail-closed 空 api_key / 载荷形态（model+messages，tools 仅在非空）/
Authorization 头与 /chat/completions 路径 / base_url 尾斜杠剥除 /
sender 注入零真网 / DeepSeekProvider 委托单一实现（禁两套 HTTP 逻辑）/
build_provider openai 分支显式 model / 门面与机制同一对象 / 协议一致性。

上迁源（enterprise 只读锚点）：``llm/openai_compat.py:24`` http_sender /
``:36`` parse_tool_calls / ``:50`` OpenAICompatProvider。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import pytest

from chiyu_kernel import api
from chiyu_kernel.llm import client as llm_client
from chiyu_kernel.llm.openai_compat import (
    OpenAICompatProvider,
    http_sender,
    parse_tool_calls,
)


class FakeSender:
    """记录调用的替身 sender（零真网）。"""

    def __init__(self, response: Optional[Dict[str, Any]] = None) -> None:
        self.calls: List[tuple] = []
        self.response = response if response is not None else {
            "choices": [{"message": {"content": "ok", "tool_calls": None}}]}

    def __call__(self, url, headers, payload):
        self.calls.append((url, headers, payload))
        return self.response


def _provider(sender: FakeSender, **kw) -> OpenAICompatProvider:
    base = {"provider_id": "qwen", "api_key": "k", "base_url": "https://api.x.test/v1",
            "model": "m1", "sender": sender}
    base.update(kw)
    return OpenAICompatProvider(**base)


# ── tool_calls 解析 ─────────────────────────────────────────────────

def test_parse_tool_calls_valid_json_args():
    out = parse_tool_calls([
        {"function": {"name": "f", "arguments": '{"a": 1}'}},
        {"function": {"name": "g", "arguments": {"b": 2}}},
    ])
    assert [(t.name, dict(t.args)) for t in out] == [("f", {"a": 1}), ("g", {"b": 2})]


def test_parse_tool_calls_invalid_json_yields_empty_args_not_crash():
    # 畸形 tool_call 不让整轮对话失败，但不猜内容
    out = parse_tool_calls([{"function": {"name": "f", "arguments": "{oops"}}])
    assert out[0].name == "f"
    assert out[0].args == {}


def test_parse_tool_calls_missing_function_and_name():
    out = parse_tool_calls([{}, {"function": {"arguments": '{"x": 1}'}}])
    assert out[0].name == ""
    assert out[1].name == ""


def test_parse_tool_calls_empty_and_none():
    assert parse_tool_calls(None) == []
    assert parse_tool_calls([]) == []


# ── fail-closed ─────────────────────────────────────────────────────

def test_empty_api_key_refuses_call():
    sender = FakeSender()
    p = _provider(sender, api_key="")
    with pytest.raises(ValueError, match="api_key 为空"):
        p.stream_chat([{"role": "user", "content": "x"}])
    assert sender.calls == []          # 未发起任何请求（不伪造请求）


def test_provider_id_and_model_required():
    with pytest.raises(ValueError, match="provider_id"):
        OpenAICompatProvider(provider_id="", api_key="k", base_url="https://x.test",
                             model="m", sender=FakeSender())
    with pytest.raises(ValueError, match="model"):
        OpenAICompatProvider(provider_id="qwen", api_key="k",
                             base_url="https://x.test", model="",
                             sender=FakeSender())


# ── 载荷形态 ────────────────────────────────────────────────────────

def test_payload_shape_and_auth_header():
    sender = FakeSender()
    p = _provider(sender)
    resp = p.stream_chat([{"role": "user", "content": "hi"}])
    url, headers, payload = sender.calls[0]
    assert url == "https://api.x.test/v1/chat/completions"
    assert headers["Authorization"] == "Bearer k"
    assert payload == {"model": "m1", "messages": [{"role": "user", "content": "hi"}]}
    assert resp.content == "ok"
    assert resp.tool_calls == []


def test_tools_included_only_when_present():
    sender = FakeSender()
    p = _provider(sender)
    p.stream_chat([{"role": "user", "content": "hi"}], tools=None)
    assert "tools" not in sender.calls[0][2]
    p.stream_chat([{"role": "user", "content": "hi"}], tools=[{"type": "function"}])
    assert sender.calls[1][2]["tools"] == [{"type": "function"}]


def test_tool_calls_parsed_into_response():
    sender = FakeSender({"choices": [{"message": {
        "content": "", "tool_calls": [
            {"function": {"name": "f", "arguments": '{"a": 1}'}}]}}]})
    resp = _provider(sender).stream_chat([{"role": "user", "content": "x"}])
    assert resp.tool_calls[0].name == "f"
    assert dict(resp.tool_calls[0].args) == {"a": 1}


def test_base_url_trailing_slash_stripped():
    sender = FakeSender()
    p = _provider(sender, base_url="https://api.x.test/v1/")
    p.stream_chat([{"role": "user", "content": "x"}])
    assert sender.calls[0][0] == "https://api.x.test/v1/chat/completions"


def test_empty_choices_yields_empty_response():
    sender = FakeSender({"choices": []})
    resp = _provider(sender).stream_chat([{"role": "user", "content": "x"}])
    assert resp.content == ""
    assert resp.tool_calls == []


# ── DeepSeekProvider 委托单一实现 ───────────────────────────────────

def test_deepseek_provider_delegates_single_impl():
    sender = FakeSender()
    p = llm_client.DeepSeekProvider(api_key="k", sender=sender)
    assert p.base_url == "https://api.deepseek.com"
    resp = p.stream_chat([{"role": "user", "content": "x"}])
    url, headers, payload = sender.calls[0]
    assert url == "https://api.deepseek.com/chat/completions"
    assert payload["model"] == "deepseek-chat"
    assert headers["Authorization"] == "Bearer k"
    assert resp.content == "ok"


def test_deepseek_provider_custom_base_url_and_fail_closed():
    sender = FakeSender()
    p = llm_client.DeepSeekProvider(api_key="", base_url="https://proxy.test/",
                                    sender=sender)
    assert p.base_url == "https://proxy.test"
    with pytest.raises(ValueError, match="api_key 为空"):
        p.stream_chat([{"role": "user", "content": "x"}])


def test_build_provider_openai_requires_explicit_model():
    with pytest.raises(ValueError, match="model"):
        llm_client.build_provider(provider="openai", api_key="k",
                                  base_url="https://api.x.test")


def test_build_provider_openai_wires_provider():
    sender = FakeSender()
    p = llm_client.build_provider(provider="openai", api_key="k", model="m9",
                                  base_url="https://api.x.test/v1", sender=sender)
    assert isinstance(p, OpenAICompatProvider)
    assert p.provider_id == "openai"
    p.stream_chat([{"role": "user", "content": "x"}])
    assert sender.calls[0][2]["model"] == "m9"


def test_build_provider_deepseek_still_uses_tier():
    p = llm_client.build_provider(tier="3b", provider="deepseek", api_key="k")
    assert isinstance(p, llm_client.DeepSeekProvider)
    assert p.model  # 由 tier_spec 解析出模型名


# ── 门面同对象 + 协议一致性 ─────────────────────────────────────────

def test_facade_reexports_same_objects():
    for name in ("OpenAICompatProvider", "http_sender", "parse_tool_calls", "Sender"):
        assert getattr(api, name) is globals()[name] if name in globals() else True
    assert api.OpenAICompatProvider is OpenAICompatProvider
    assert api.http_sender is http_sender
    assert api.parse_tool_calls is parse_tool_calls


def test_provider_conforms_to_llm_provider_protocol():
    p = _provider(FakeSender())
    assert isinstance(p, api.LlmProvider)


def test_production_sender_is_lazy_import_zero_top_level_urllib():
    # 生产 sender 的 urllib 导入在函数内（import 期零网络栈）；测试替身可注入
    import inspect
    src = inspect.getsource(http_sender)
    assert "import urllib.request" in src
    body = src.split("def http_sender", 1)[1]
    assert body.index("import urllib.request") < body.index("urllib.request.Request")
