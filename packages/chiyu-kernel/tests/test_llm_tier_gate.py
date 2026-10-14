"""档位策略守卫 —— 档位闸、两侧共用一张表、零项目内依赖。

⛔ 为什么档位闸必须有守卫：注入故事线把 prompt 从 127 → 1055 token（×8.3），
   而本机 7B CPU 档 prefill 仅 15.52 tok/s ⇒ 单次判读从 ≈10s 推到分钟级。
   拦不拦是**性能事故**与**正常**的分界，不能靠注释。
"""
from __future__ import annotations

import ast
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

from chiyu_kernel.llm import tier as t

_TIER_SRC = Path(__file__).resolve().parents[1] / "src" / "chiyu_kernel" / "llm" / "tier.py"


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """清干净档位相关环境变量 —— 否则结果取决于跑测机器的 .env（不可复现）。"""
    for name in ("CHIYU_LLM_TIER", "CHIYU_LLM_BASE_URL", "CHIYU_LLM_MODEL",
                 "CHIYU_LLM_STORYLINE"):
        monkeypatch.delenv(name, raising=False)


LOCAL = "http://127.0.0.1:8081/v1"
CLOUD = "https://api.deepseek.com/v1"


@pytest.mark.parametrize("kw,exp_inject,exp_tier,exp_source", [
    # 本机 7B ⇒ 关（prefill 15.52 tok/s，注入成本不可接受）
    ({"model": "qwen2.5-7b-instruct", "base_url": LOCAL}, False, "7b", "inferred-tier"),
    # 本机 3B / 1.5B ⇒ 开（prefill 快 2.5~5 倍）
    ({"model": "qwen2.5-3b-instruct", "base_url": LOCAL}, True, "3b", "inferred-tier"),
    ({"tier": "1.5b"}, True, "1.5b", "explicit-tier"),
    # 显式档位优先于由模型名推断
    ({"tier": "3b", "model": "qwen2.5-7b-instruct", "base_url": LOCAL},
     True, "3b", "explicit-tier"),
    # 云端 https ⇒ 本地 CPU 前提不成立，**不推断**、不误伤
    ({"model": "deepseek-chat", "base_url": CLOUD}, True, None, "permissive-unknown"),
    ({"model": "qwen2.5-7b-instruct", "base_url": CLOUD}, True, None, "permissive-unknown"),
])
def test_storyline_policy_matrix(kw, exp_inject, exp_tier, exp_source):
    got = t.resolve_storyline_policy(**kw)
    assert got["inject"] is exp_inject
    assert got["tier"] == exp_tier
    assert got["source"] == exp_source
    assert got["reason"]


def test_explicit_storyline_flag_overrides_tier():
    on = t.resolve_storyline_policy(tier="7b", storyline="on")
    assert on["inject"] is True and on["source"] == "explicit-flag"
    off = t.resolve_storyline_policy(tier="1.5b", storyline="off")
    assert off["inject"] is False and off["source"] == "explicit-flag"


def test_invalid_values_fall_back_and_stay_visible():
    """⛔ 配错必须**出声**：`warnings` 非空即"配置写错"与"配置没问题"外观不再相同。"""
    got = t.resolve_storyline_policy(tier="13b")
    assert got["tier"] is None
    assert got["warnings"] and "13b" in got["warnings"][0]

    got2 = t.resolve_storyline_policy(tier="7b", storyline="maybe")
    assert got2["flag"] == "auto"
    assert got2["warnings"] and "maybe" in got2["warnings"][0]
    # 显式非法开关 → 按 auto 处理 ⇒ 落回档位策略（7b ⇒ 不注入）
    assert got2["inject"] is False


def test_normalize_tier_never_guesses():
    assert t.normalize_tier("7B") == "7b"
    assert t.normalize_tier("qwen2.5-1.5b-instruct") == "1.5b"
    for bad in (None, "", "auto", "none", "null", "llama-70b", "gpt-4o", "思考模型"):
        assert t.normalize_tier(bad) is None


def test_cloud_endpoint_detection():
    assert t.is_cloud_endpoint(CLOUD) is True
    assert t.is_cloud_endpoint("HTTP://127.0.0.1:8081") is False
    assert t.is_cloud_endpoint(None) is False


def test_tier_spec_defaults_and_shape():
    spec = t.tier_spec()
    assert spec["tier"] == t.DEFAULT_TIER == "7b"
    assert spec["source"] == "default"
    assert spec["parallel"] == t.DEFAULT_PARALLEL == 1     # 决定性判据优先于并发
    assert {"model", "gguf", "ctx", "parallel", "storyline"} <= set(spec)
    assert t.tier_spec("Qwen2.5-3B")["tier"] == "3b"


def test_env_override_drives_the_gate(monkeypatch):
    monkeypatch.setenv("CHIYU_LLM_TIER", "3b")
    got = t.resolve_storyline_policy()
    assert got["tier"] == "3b" and got["inject"] is True
    monkeypatch.setenv("CHIYU_LLM_STORYLINE", "off")
    assert t.resolve_storyline_policy()["inject"] is False


def test_deploy_and_app_read_the_same_table():
    """⛔ 「两侧共用一张表」的可执行判据。

    部署侧（`tools/run_llama_server.py`）用 `spec_from_file_location` **按文件路径**加载
    本模块（不经包 `__init__`）；若两处各有一份档位表，就会出现"启动器实际跑 7B、
    应用以为在跑 3B"的口径分叉。本用例真的按路径加载一次并比对。
    """
    spec = spec_from_file_location("_tier_by_path", _TIER_SRC)
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)                      # type: ignore[union-attr]
    assert mod.TIERS == t.TIERS
    assert mod.DEFAULT_TIER == t.DEFAULT_TIER
    assert mod.DEFAULT_PARALLEL == t.DEFAULT_PARALLEL


def test_tier_module_has_zero_project_internal_imports():
    """⛔ 约束②的可执行形式：本模块必须能被独立加载（只用标准库）。

    只要出现一行项目内 import，`spec_from_file_location` 式加载就会连带触发
    `chiyu_kernel/__init__` 的副作用（dotenv 等）—— 部署侧会在建连前炸掉。
    """
    tree = ast.parse(_TIER_SRC.read_text(encoding="utf-8"))
    bad: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.level or 0) > 0:
            bad.append(f"相对 import：{node.module}")
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("chiyu_kernel"):
            bad.append(f"项目内 import：{node.module}")
        if isinstance(node, ast.Import):
            bad.extend(f"项目内 import：{a.name}" for a in node.names
                       if a.name.startswith("chiyu_kernel"))
    assert bad == [], f"tier.py 必须零项目内依赖，实测：{bad}"
