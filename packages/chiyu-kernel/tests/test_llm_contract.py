"""GAP-4 LLM 契约 + tier.py 对拍守卫（Batch-2a，2026-10-14）。

判据面：
  · 档位闭集/缺省档/并行槽位与 `llm/tier.py` 数值表逐项相等（漂移即红）；
  · 每档字段面恰等于契约 `LLM_TIER_FIELDS`；
  · provider 数据形态（ToolCall/LlmResponse）字段与契约一致；
  · 故事线策略 source 取值在契约闭集内；
  · tier.py 保持零项目内 import（部署侧按文件路径加载的硬约束）。
"""
from __future__ import annotations

from dataclasses import fields

from chiyu_kernel.contract import llm as llm_contract
from chiyu_kernel.llm import (
    DEFAULT_PARALLEL,
    DEFAULT_TIER,
    TIERS,
    resolve_storyline_policy,
)
from chiyu_kernel.llm.client import LlmResponse, ToolCall


def test_tier_table_parity_with_contract():
    assert set(TIERS) == set(llm_contract.LLM_TIERS)
    assert DEFAULT_TIER == llm_contract.LLM_DEFAULT_TIER
    assert DEFAULT_PARALLEL == llm_contract.LLM_DEFAULT_PARALLEL


def test_tier_fields_exactly_contract_surface():
    for t, spec in TIERS.items():
        assert set(spec) == set(llm_contract.LLM_TIER_FIELDS), (
            f"档位 {t} 字段面与契约不一致："
            f"{sorted(set(spec) ^ set(llm_contract.LLM_TIER_FIELDS))}")


def test_response_and_toolcall_fields_match_contract():
    assert {f.name for f in fields(LlmResponse)} == set(llm_contract.LLM_RESPONSE_FIELDS)
    assert {f.name for f in fields(ToolCall)} == set(llm_contract.TOOL_CALL_FIELDS)


def test_storyline_policy_sources_are_contract_values():
    out = resolve_storyline_policy(model="qwen2.5-7b-instruct", base_url="")
    assert out["source"] == "inferred-tier"
    assert out["source"] in llm_contract.LLM_STORYLINE_POLICY_SOURCES
    # 云端端点 + 未知模型 ⇒ 宽松（保持既有行为），source 必须实名
    out2 = resolve_storyline_policy(model="mystery-model", base_url="https://x.example")
    assert out2["source"] == "permissive-unknown"
    assert out2["inject"] is True


def test_tier_module_has_zero_project_imports():
    # tier.py 被部署侧按文件路径加载（spec_from_file_location），
    # 零项目内 import 是硬约束（test_llm_tier_gate.py 同族判据）。
    # 本契约设计刻意**不**把 TIERS 搬进 contract（那会破坏该约束），
    # 漂移由上面对拍守卫兜底 —— 此条防未来有人"顺手"引入 import。
    # 判定用 AST（docstring 里出现包名字样不算 import，防朴素字符串匹配假红）。
    import ast

    import chiyu_kernel.llm.tier as tier_mod
    tree = ast.parse(open(tier_mod.__file__, encoding="utf-8").read())
    bad: list = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.level or 0) > 0:
            bad.append(f"相对 import：{node.module}")
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("chiyu_kernel"):
            bad.append(f"项目内 import：{node.module}")
        if isinstance(node, ast.Import):
            bad.extend(f"项目内 import：{a.name}" for a in node.names
                       if a.name.startswith("chiyu_kernel"))
    assert bad == [], f"tier.py 必须零项目内依赖，实测：{bad}"
