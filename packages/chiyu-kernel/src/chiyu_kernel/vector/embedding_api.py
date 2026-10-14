"""真语义向量 API 客户端 —— 抽取自 demo `features/embedding_api.py`（2026-09-21，P1 T3）。

provider：OpenAI 兼容 /v1/embeddings（默认 SiliconFlow），模型 BAAI/bge-large-zh-v1.5（dim=1024）。

⛔ 与 demo 的差异（零领域依赖原则）：
   · demo 版 `from chiyu_group.env_bootstrap import ENV_STATUS`（加载 .env）⇒ 内核**不得**
     跨包 import，故删除该依赖；.env 加载由**消费方**在进程启动时负责，本模块只从
     `os.environ` 读（纯 stdlib，无副作用）。
   · `DEFAULT_BASE_URL` / `DEFAULT_MODEL` 是 OpenAI 兼容端点通用默认，可被 env 覆盖，
     保留为**可配置默认**（不是 CRM 特定，任何域都可覆写）。

契约沿用 CRM 生产实证三条铁律：
  1) 输入 ≤480 字符截断（bge 系列 512 token 上限，超限 400 → 降级哈希）；
  2) 拒因透传（HTTP 状态 + 服务端原话），不得被中间层吞掉；
  3) 任何失败 fail-open：由调用方（InferBackend）降级哈希签名，绝不阻断主流程。

环境变量：
  CHIYU_EMBEDDING_API_KEY   必填，缺失时 available()=False（走哈希基线）
  CHIYU_EMBEDDING_ALLOW_NETWORK  出网闸（D3）：默认 `0`=禁出网；`1` 才允许云端调用。
  CHIYU_EMBEDDING_BASE_URL  默认 https://api.siliconflow.cn/v1
  CHIYU_EMBEDDING_MODEL     默认 BAAI/bge-large-zh-v1.5（1024 维）
  CHIYU_EMBEDDING_TIMEOUT   默认 20 秒
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.error  # noqa: F401  # 保留（error_class 归因）
import urllib.request

DEFAULT_BASE_URL = "https://api.siliconflow.cn/v1"
DEFAULT_MODEL = "BAAI/bge-large-zh-v1.5"          # 1024 维
MAX_CHARS = 480          # CRM 实证：≤551 字符 200、687 字符 400，480 留余量
DEFAULT_TIMEOUT = 20

_CACHE: dict[str, list[float]] = {}
_CACHE_MAX = 4096


def network_allowed() -> bool:
    """D3 出网**原语**（单一事实源）：默认 `0` = 禁出网；接受 1/true/yes/on。

    交付物默认不得联网。把默认值取 `0` 的意义是：
    "现场忘配"的结果是**安全**（不出网、降级本地/哈希），而不是偷偷联网。
    """
    return os.environ.get("CHIYU_EMBEDDING_ALLOW_NETWORK", "0").strip().lower() in (
        "1", "true", "yes", "on")


def available() -> bool:
    """云端真向量启用判据：`CHIYU_TEST≠1` **且** 显式放行出网 **且** 有 key。

    ⛔ 出网闸放在**这里**而不是各调用点（单一事实源）。

    CHIYU_TEST=1 时强制 False：测试环境零外部依赖、零调用成本、结果确定性
    （与 infer.py 同约定；.env 即便载入了真实 key 也不在测试期生效）。
    """
    if os.environ.get("CHIYU_TEST") == "1":
        return False
    if not network_allowed():
        return False
    return bool(os.environ.get("CHIYU_EMBEDDING_API_KEY"))


def error_class(msg: str | None = None) -> str | None:
    """拒因**归因**（可行动口径）。

    ⛔ `http-402 余额不足` 必须**单列**，禁止并入 `http-4xx` —— 两者的处置动作完全不同。
    返回 None 表示"没失败过"（与"失败但原因未知 unknown"**严格区分**）。
    """
    m = (msg if msg is not None else LAST_ERROR) or ""
    low = m.lower()
    if "402" in m or "payment required" in low or "insufficient" in low:
        return "payment_required"
    if "401" in m or "unauthorized" in low or "invalid api key" in low:
        return "auth_failed"
    if "429" in m or "rate limit" in low:
        return "rate_limited"
    if "404" in m or ("model" in low and ("not exist" in low or "not found" in low)):
        return "model_unavailable"
    if "timed out" in low or "timeout" in low:
        return "timeout"
    if "urlopen error" in low or "getaddrinfo" in low or "name or service" in low:
        return "network_unreachable"
    return "unknown" if m else None


def provider_info() -> dict:
    """向量通道状态（**配置态**与**运行态**分开报，禁止互相冒充）。

    - `provider`          = **配置态**（available()），回答"能不能用"；
    - `effective_provider` = **运行态**（最近一次真实调用结果），回答"实际用了什么"；
    - `last_error` / `error_class` = 拒因透传，402 单列为 `payment_required`。
    """
    return {
        "provider": "api" if available() else "hash",       # 配置态（保持旧键语义）
        "effective_provider": _LAST_PROVIDER,               # 运行态：model / hash / unknown
        "model": os.environ.get("CHIYU_EMBEDDING_MODEL", DEFAULT_MODEL),
        "base_url": os.environ.get("CHIYU_EMBEDDING_BASE_URL", DEFAULT_BASE_URL),
        "api_key_configured": available(),
        "last_error": LAST_ERROR,
        "error_class": error_class(),
        "degraded": available() and _LAST_PROVIDER == "hash",
    }


def _cache_key(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def embed(text: str, *, transport=None) -> list[float] | None:
    """单条文本 → 向量。失败/未配置返回 None（由调用方降级），拒因写入 last_error。"""
    global LAST_ERROR, _LAST_PROVIDER       # 运行态留痕：成功置 model，失败置 hash
    if not available():
        return None
    text = (text or "")[:MAX_CHARS]
    ck = _cache_key(text)
    hit = _CACHE.get(ck)
    if hit is not None:
        return hit

    base = os.environ.get("CHIYU_EMBEDDING_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    url = f"{base}/embeddings"
    model = os.environ.get("CHIYU_EMBEDDING_MODEL", DEFAULT_MODEL)
    key = os.environ["CHIYU_EMBEDDING_API_KEY"]
    timeout = float(os.environ.get("CHIYU_EMBEDDING_TIMEOUT", DEFAULT_TIMEOUT))
    body = json.dumps({"model": model, "input": text}).encode("utf-8")

    def _default_transport(u: str, b: bytes, t: float):
        req = urllib.request.Request(
            u, data=b, method="POST",
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {key}"})
        with urllib.request.urlopen(req, timeout=t) as resp:  # noqa: S310
            return resp.status, resp.read()

    try:
        status, raw = (transport or _default_transport)(url, body, timeout)
        if status != 200:
            raise RuntimeError(f"Embedding HTTP {status}：{_err_detail(raw)}")
        data = json.loads(raw.decode("utf-8"))
        vec = (data.get("data") or [{}])[0].get("embedding")
        if not isinstance(vec, list) or not vec:
            raise RuntimeError("embedding 返回空向量")
        out = [float(x) for x in vec]
        if len(_CACHE) >= _CACHE_MAX:
            _CACHE.clear()
        _CACHE[ck] = out
        LAST_ERROR = None
        _LAST_PROVIDER = "model"
        return out
    except Exception as e:  # noqa: BLE001 —— 拒因保留，降级由调用方决定
        LAST_ERROR = str(e)
        _LAST_PROVIDER = "hash"
        _warn_once(str(e))
        return None


def _warn_once(msg: str) -> None:
    """首次真向量失败**一次性出声**（stderr），不抛异常、不阻断主链。

    ⛔ 为什么必须出声：真向量失败是**静默**的 —— 调用方拿到 `None` 就降级哈希。
    """
    global _WARNED
    if _WARNED:
        return
    _WARNED = True
    cls = error_class(msg)
    hint = {
        "payment_required": "账户余额不足 ⇒ 去 Provider 充值（不是改配置能解决的）",
        "auth_failed": "API Key 无效或被吊销 ⇒ 检查 CHIYU_EMBEDDING_API_KEY",
        "rate_limited": "触发限流 ⇒ 降频或更换额度",
        "model_unavailable": "模型名不存在 ⇒ 检查 CHIYU_EMBEDDING_MODEL（勿填 chat 模型）",
        "network_unreachable": "网络不可达 ⇒ 检查 CHIYU_EMBEDDING_BASE_URL 与出网",
    }.get(cls or "", "见 last_error 原文")
    print(f"[embedding] ⚠ 真向量不可用，已降级哈希签名：{cls} —— {hint}；原文：{msg}",
          file=sys.stderr)


LAST_ERROR: str | None = None
_LAST_PROVIDER: str = "unknown"        # 运行态：model / hash / unknown（从未调用）
_WARNED: bool = False                  # 一次性告警开关


def _err_detail(raw: bytes) -> str:
    """拒因透明（铁律 2）：带出服务端原话，区分欠费/模型不存在/鉴权失败/限流。"""
    try:
        s = raw.decode("utf-8", "ignore") if raw else ""
        try:
            j = json.loads(s)
            d = j.get("message") or (j.get("error") or {}).get("message") or ""
        except Exception:
            d = s
        return " ".join(str(d).split())[:180]
    except Exception:  # noqa: BLE001
        return ""
