"""OpenAI 兼容 Provider（T93 上迁，Batch-3 llm provider 补全）。

上迁源：enterprise ``llm/openai_compat.py``（85 行，qwen/glm/openai/kimi/
自定义兼容端点共用的真实实现）——域无关、协议级、stdlib 零依赖，按
「机制上迁、域值留消费方」收敛至此。enterprise 侧改消费本模块后删本地重造。

纪律（均有守卫测试）：
    · **fail-closed**：api_key 为空拒绝发起调用（不伪造请求、不伪造响应）；
    · **sender 注入**：生产 ``http_sender``（stdlib urllib，零新增依赖）；
      测试注入替身 ⇒ 零真网（守「无网络单测」纪律）；
    · **api_key 只过内存**（构造参数），不落盘、不打日志；
    · **禁两套 HTTP 逻辑**：DeepSeek 等 OpenAI 兼容端点一律复用本类
      （``client.DeepSeekProvider`` 即委托本类，防平行实现漂移）。
"""
from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Mapping, Optional

from .client import LlmResponse, ToolCall

__all__ = ["Sender", "http_sender", "parse_tool_calls", "OpenAICompatProvider"]

#: sender 契约：sender(url, headers, payload) -> dict（OpenAI chat.completion JSON）。
#: 消费方（含测试）可注入替身；真实网络只发生在生产 sender 内。
Sender = Callable[[str, Dict[str, str], Dict[str, Any]], Dict[str, Any]]

_DEFAULT_TIMEOUT = 60  # 秒


def http_sender(url: str, headers: Dict[str, str], payload: Dict[str, Any],
                *, timeout: int = _DEFAULT_TIMEOUT) -> Dict[str, Any]:
    """生产 sender：stdlib urllib POST JSON（零新增依赖）。"""
    import urllib.request

    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={**headers, "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def parse_tool_calls(raw_tools: Optional[List[Dict[str, Any]]]) -> List[ToolCall]:
    """OpenAI tool_calls → 内核 ToolCall（arguments JSON 串 → dict）。

    ⚠ arguments 非法 JSON / 非映射 ⇒ ``args={}`` **不抛**：上游多送一个畸形
      tool_call 不该让整轮对话失败；但也不猜内容——空 dict 即"无参数"。
    """
    out: List[ToolCall] = []
    for tc in raw_tools or []:
        fn = tc.get("function") or {}
        raw_args = fn.get("arguments")
        try:
            args = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args or {})
        except (ValueError, TypeError):
            args = {}
        out.append(ToolCall(name=fn.get("name", ""), args=args))
    return out


class OpenAICompatProvider:
    """OpenAI chat/completions 兼容 Provider（实现 ``LlmProvider`` 协议）。

    :param provider_id: 提供方标识（仅用于错误信息，如 ``"deepseek"``/``"qwen"``）。
    :param api_key:    凭据，只过内存；**为空时调用即拒**（fail-closed）。
    :param base_url:   兼容端点基址（末尾 ``/`` 自动剥除）。
    :param model:      模型名（调用方显式给定，内核不替消费方猜默认模型）。
    :param sender:     HTTP 发送替身注入点；缺省生产 ``http_sender``。
    :param ctx:        上下文长度（档位记账用，不进请求载荷）。
    """

    def __init__(self, *, provider_id: str, api_key: str, base_url: str,
                 model: str, sender: Optional[Sender] = None,
                 ctx: int = 8192) -> None:
        if not str(provider_id or "").strip():
            raise ValueError("provider_id 不得为空（错误信息要能指认提供方）")
        if not str(model or "").strip():
            raise ValueError(f"provider {provider_id} 需显式传 model（内核不替消费方猜默认模型）")
        self.provider_id = provider_id
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.ctx = ctx
        self._sender = sender or http_sender

    def stream_chat(self, messages: List[Mapping[str, Any]], *,
                    tools: Optional[List[Dict[str, Any]]] = None) -> LlmResponse:
        if not self.api_key:
            raise ValueError(
                f"provider {self.provider_id} api_key 为空：凭据未配置，"
                "拒绝发起调用（配置凭据后可用）")
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [dict(m) for m in messages],
        }
        if tools:
            payload["tools"] = tools
        headers = {"Authorization": f"Bearer {self.api_key}"}
        data = self._sender(f"{self.base_url}/chat/completions", headers, payload)
        choice = ((data.get("choices") or [{}])[0])
        message = choice.get("message") or {}
        return LlmResponse(
            content=message.get("content") or "",
            tool_calls=parse_tool_calls(message.get("tool_calls")),
        )
