"""LLM 运行配置持久化（web/backend 本地文件，不改内核）。

优先级：llm_config.local.json（本文件，UI 可写） > 环境变量 DEEPSEEK_API_KEY > 未配置。
文件内 apiKey 为明文（本机开发用途）；对外一律经 mask_key() 脱敏。
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

CONFIG_PATH = Path(__file__).resolve().parent / "llm_config.local.json"

DEFAULTS: Dict[str, Any] = {
    "provider": "deepseek",
    "baseUrl": "https://api.deepseek.com",
    "apiKey": "",
    "modelChat": "deepseek-chat",
    "modelReasoner": "deepseek-reasoner",
}


def load() -> Dict[str, Any]:
    """读本地配置文件；不存在/损坏时返回空 dict（由 get_effective 兜底）。"""
    if not CONFIG_PATH.exists():
        return {}
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """合并写入配置文件（只接受已知字段），返回保存后的完整配置（未脱敏）。"""
    clean = {k: str(cfg.get(k, "")).strip() for k in DEFAULTS}
    clean["provider"] = clean["provider"] or DEFAULTS["provider"]
    CONFIG_PATH.write_text(json.dumps(clean, ensure_ascii=False, indent=2),
                           encoding="utf-8")
    return clean


def get_effective() -> Dict[str, Any]:
    """生效配置：文件字段优先，空字段回落默认/环境变量。"""
    f = load()
    env_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    api_key = (f.get("apiKey") or "").strip() or env_key
    return {
        "provider": (f.get("provider") or "").strip() or DEFAULTS["provider"],
        "baseUrl": (f.get("baseUrl") or "").strip() or DEFAULTS["baseUrl"],
        "apiKey": api_key,
        "modelChat": (f.get("modelChat") or "").strip() or DEFAULTS["modelChat"],
        "modelReasoner": (f.get("modelReasoner") or "").strip() or DEFAULTS["modelReasoner"],
        "keySource": "file" if (f.get("apiKey") or "").strip()
                     else ("env" if env_key else "none"),
    }


def mask_key(key: str) -> str:
    if not key:
        return "未配置"
    return (key[:3] + "…" + key[-4:]) if len(key) > 8 else "已配置"


__all__ = ["CONFIG_PATH", "DEFAULTS", "load", "save", "get_effective", "mask_key"]
