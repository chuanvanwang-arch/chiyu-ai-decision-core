"""Phase B LLM 桥：DeepSeek OpenAI 兼容端点（后端集成层，不动内核）。

设计要点：
- 内核 `DeepSeekProvider.stream_chat` 是刻意的 NotImplementedError 占位
  （守「无网络单测」纪律），故真实 HTTP 调用放在**后端桥接层**，不修改内核包。
- `DEEPSEEK_API_KEY` 存在 → 真实调用；不存在 → available=False，
  调用方回落确定性内容（内核 S1–S5 的工具与脊柱输出照常可用）。
- `deep_think` → model=deepseek-reasoner（R1）；否则 deepseek-chat（V3）。
- `web_search`：DeepSeek API 暂无官方联网检索参数 → 如实标注「本阶段未接通」，
  绝不假装搜过（本仓反假绿纪律）。
- 无第三方依赖：标准库 urllib。
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List

import llm_config

DEFAULT_BASE = "https://api.deepseek.com"
_MODEL_CHAT = "deepseek-chat"
_MODEL_REASONER = "deepseek-reasoner"
_TIMEOUT_S = 90


def _cfg() -> Dict[str, Any]:
    return llm_config.get_effective()


def llm_available() -> bool:
    return bool(_cfg()["apiKey"])


def llm_status() -> Dict[str, Any]:
    c = _cfg()
    key = c["apiKey"]
    return {
        "available": bool(key),
        "base": c["provider"],
        "baseUrl": c["baseUrl"],
        "models": {"chat": c["modelChat"], "reasoner": c["modelReasoner"]},
        "web_search": False,  # 如实：DeepSeek API 无联网检索参数，本阶段未接通
        "key_hint": llm_config.mask_key(key),
        "key_source": c["keySource"],
        "config_file": str(llm_config.CONFIG_PATH),
    }


def _endpoint(baseUrl: str) -> str:
    base = (baseUrl or DEFAULT_BASE).rstrip("/")
    return base + "/chat/completions" if not base.endswith("/chat/completions") else base


def llm_test(*, deep_think: bool = False, timeout: int = 30) -> Dict[str, Any]:
    """连通性实测：发一条最小请求，如实返回成败（用于设置面板「测试连接」）。"""
    c = _cfg()
    if not c["apiKey"]:
        return {"ok": False, "error": "未配置 API Key（UI 或环境变量 DEEPSEEK_API_KEY 均可）"}
    model = c["modelReasoner"] if deep_think else c["modelChat"]
    payload = {"model": model, "messages": [{"role": "user", "content": "ping"}],
               "max_tokens": 4, "stream": False}
    req = urllib.request.Request(
        _endpoint(c["baseUrl"]),
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {c['apiKey']}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            json.loads(resp.read().decode("utf-8"))
        return {"ok": True, "model": model, "baseUrl": c["baseUrl"]}
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", "replace")[:200]
        except Exception:
            pass
        return {"ok": False, "error": f"HTTP {e.code}: {body or e.reason}", "model": model}
    except Exception as e:
        return {"ok": False, "error": str(e), "model": model}


def llm_chat(messages: List[Dict[str, str]], *, deep_think: bool = False,
             temperature: float = 0.7, timeout: int = _TIMEOUT_S) -> Dict[str, Any]:
    """调 OpenAI 兼容 /chat/completions。返回 {available, model, content, error?, elapsed_ms?}。

    messages: [{role: system|user|assistant, content}, ...]（OpenAI 兼容格式）
    """
    c = _cfg()
    key = c["apiKey"]
    model = c["modelReasoner"] if deep_think else c["modelChat"]
    if not key:
        return {"available": False, "model": model,
                "error": "未配置 API Key（设置面板或 DEEPSEEK_API_KEY 均可），Phase B 未启用（确定性内容照常）"}

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": False,
    }
    req = urllib.request.Request(
        _endpoint(c["baseUrl"]),
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        content = ""
        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        content = (msg.get("content") or "").strip()
        usage = data.get("usage") or {}
        return {
            "available": True,
            "model": data.get("model", model),
            "content": content,
            "usage": {
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
            },
        }
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", "replace")[:300]
        except Exception:
            pass
        return {"available": False, "model": model,
                "error": f"DeepSeek HTTP {e.code}: {body or e.reason}"}
    except Exception as e:  # 网络异常等：如实回落，不吞语义
        return {"available": False, "model": model, "error": f"DeepSeek 调用异常：{e}"}


def build_phase_b_messages(*, text: str, mode: str, intent: str,
                           supply_rate: float, missing: List[Any],
                           advice: str, history: List[Dict[str, str]] | None = None,
                           web_search: bool = False) -> List[Dict[str, str]]:
    """把内核 S1–S5 的真实产出作为 system 上下文，让 LLM 基于内核事实作答。"""
    sys = (
        "你是 ChiYu（治语）AI 原生决策内核的对话面。以下是本轮内核决策脊柱的真实产出，"
        "必须严格基于这些事实作答，不得编造工具调用结果或红线状态：\n"
        f"- 工作模式：{mode}\n"
        f"- 意图：{intent}\n"
        f"- 上下文供给率：{supply_rate:.0%}\n"
        f"- 缺口项：{len(missing)} 项\n"
        f"- 内核建议：{advice}\n"
        + ("- 用户开启了联网搜索：DeepSeek API 本阶段未接通检索参数，请如实说明，不得假装检索过。\n"
           if web_search else "")
        + "回答保持简洁、专业、中文。"
    )
    msgs: List[Dict[str, str]] = [{"role": "system", "content": sys}]
    if history:
        msgs.extend({"role": m.get("role", "user"), "content": m.get("content", "")}
                    for m in history[-6:])
    msgs.append({"role": "user", "content": text})
    return msgs


__all__ = ["llm_available", "llm_status", "llm_chat", "llm_test", "build_phase_b_messages"]
