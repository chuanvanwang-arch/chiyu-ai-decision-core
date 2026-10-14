from chiyu_kernel.llm.client import (
    StubProvider, LlmResponse, ToolCall, build_provider, DeepSeekProvider,
)


def test_stub_provider_returns_queued_responses():
    p = StubProvider(responses=[LlmResponse(content="a"), LlmResponse(content="b")])
    assert p.stream_chat([{"role": "user", "content": "x"}]).content == "a"
    assert p.stream_chat([]).content == "b"


def test_build_provider_deepseek_uses_tier():
    p = build_provider(tier="3b", provider="deepseek", api_key="k")
    assert isinstance(p, DeepSeekProvider)
    assert p.model  # 由 tier_spec 解析出模型名


def test_build_provider_rejects_unknown():
    try:
        build_provider(provider="no_such_provider")
        assert False
    except ValueError:
        pass
