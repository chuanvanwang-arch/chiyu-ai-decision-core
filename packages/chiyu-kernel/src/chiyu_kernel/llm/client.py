"""模型适配器（吸收 dsh `llm/llm`）：provider 抽象 + DeepSeek/OpenAI 兼容 provider。
复用本仓 `llm/tier` 的档位策略（tier_spec）决定 model/ctx；不强制 DEEPSEEK_API_KEY。

⛔ 真实网络调用只在 provider 的 ``stream_chat`` 内发起；单测用 StubProvider 或
   注入 sender 替身，不发任何请求（守「无网络单测」纪律）。
⛔ T93（Batch-3 provider 补全）：DeepSeek 端点为 OpenAI 兼容 ⇒ DeepSeekProvider
   委托 ``llm.openai_compat.OpenAICompatProvider`` 单一实现，**禁两套 HTTP 逻辑**。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Mapping, Optional, Protocol, runtime_checkable

from chiyu_kernel.llm import tier_spec


@dataclass
class ToolCall:
    name: str
    args: Mapping[str, Any] = field(default_factory=dict)


@dataclass
class LlmResponse:
    content: str = ""
    tool_calls: List[ToolCall] = field(default_factory=list)


@runtime_checkable
class LlmProvider(Protocol):
    def stream_chat(self, messages: List[Mapping[str, Any]], *, tools=None) -> LlmResponse:
        ...


class StubProvider:
    """测试用：按队列返回预设响应。"""
    def __init__(self, responses: Optional[List[LlmResponse]] = None) -> None:
        self._queue = list(responses or [])

    def stream_chat(self, messages, *, tools=None) -> LlmResponse:
        if not self._queue:
            return LlmResponse(content="")
        return self._queue.pop(0)


class DeepSeekProvider:
    """DeepSeek（OpenAI 兼容端点）真实 Provider。

    T93 起由桩升级为真实现：DeepSeek API 与 OpenAI chat/completions 兼容，
    直接委托 ``OpenAICompatProvider``（单一 HTTP 实现，禁平行两份漂移）。
    默认 base_url 为 DeepSeek 官方端点；测试经 ``sender`` 注入替身，零真网。
    """

    def __init__(self, *, api_key: str = "", base_url: str = "",
                 model: str = "deepseek-chat", ctx: int = 8192,
                 sender: Optional[Any] = None) -> None:
        from .openai_compat import OpenAICompatProvider, http_sender  # 延迟导入：防模块级成环
        self._impl = OpenAICompatProvider(
            provider_id="deepseek", api_key=api_key,
            base_url=base_url or "https://api.deepseek.com",
            model=model, sender=sender or http_sender, ctx=ctx)
        self.api_key = api_key
        self.base_url = self._impl.base_url
        self.model = model
        self.ctx = ctx

    def stream_chat(self, messages, *, tools=None) -> LlmResponse:
        return self._impl.stream_chat(messages, tools=tools)


def build_provider(*, tier=None, provider: str = "deepseek", **kw) -> LlmProvider:
    spec = tier_spec(tier)
    if provider == "deepseek":
        return DeepSeekProvider(
            model=kw.pop("model", None) or spec.get("model") or "deepseek-chat",
            ctx=int(spec.get("ctx", 8192)), **kw)
    if provider in ("openai", "openai_compat"):
        # 显式 model + base_url：档位表的 model 是本地 llama.cpp 部署名，
        # 不得冒充云端 OpenAI 端点模型名 ⇒ openai 分支不吃 tier 回落（fail-closed）
        model = kw.pop("model", None)
        if not model:
            raise ValueError(
                f"provider {provider!r} 需显式传 model（如 build_provider("
                "provider='openai', model='gpt-4o-mini', base_url=..., api_key=...)）")
        from .openai_compat import OpenAICompatProvider  # 延迟导入：防模块级成环
        return OpenAICompatProvider(
            provider_id=kw.pop("provider_id", None) or "openai",
            model=model,
            base_url=kw.pop("base_url", None) or "https://api.openai.com",
            **kw)
    raise ValueError(f"未知 provider：{provider!r}")


__all__ = [
    "ToolCall", "LlmResponse", "LlmProvider", "StubProvider",
    "DeepSeekProvider", "build_provider",
]
