"""L0 契约八要素钉死守卫（2026-10-12，回应 enterprise 四评分矩阵联络函请求②③）。

enterprise 落地四评分矩阵（decision_element_matrix）依赖两条 foundation 承诺：
  1. ``EIGHT_ELEMENTS`` 是 **S2 评分顺序**，不含任何重要性/优先级语义——
     要素重要性排序是消费方业务权重（enterprise strictness.py 的矩阵表），
     ⛔ 不得迁入 L0 契约。本守卫把顺序**逐位钉死**：契约若擅改顺序即红，
     强制任何顺序变更走显式评审（顺序被下游矩阵继承为默认权重序）。
  2. ``EIGHT_ELEMENTS_ZH`` 中文名映射**键集恰等**八要素且值非空
     （R25 显示=display_name，enterprise 详情载荷直接采用，无需自持）。

同时实证 sanctioned 面可按 enterprise 来函的精确 import 路径取用。
"""
import pytest

from chiyu_kernel.contract import EIGHT_ELEMENTS, EIGHT_ELEMENTS_ZH

# 逐位钉死：与 contract/decision.py EIGHT_ELEMENTS 完全一致（S2 评分序）。
# 此元组是唯一权威快照——契约顺序变更必须先改这里（评审闸），再改契约。
S2_SCORING_ORDER = (
    "intent", "assumptions", "inference", "viewpoints",
    "impact", "risk_register", "stop_loss", "concept_refs",
)


def test_eight_elements_order_pinned_to_s2_scoring_order():
    """EIGHT_ELEMENTS 逐位等于 S2 评分序；顺序即契约稳定性承诺的一部分。"""
    assert EIGHT_ELEMENTS == S2_SCORING_ORDER
    assert len(EIGHT_ELEMENTS) == 8
    # 无重复（顺序语义下重复=权重漂移隐患）
    assert len(set(EIGHT_ELEMENTS)) == 8


def test_eight_elements_zh_keys_exactly_match_and_nonempty():
    """中文名映射键集恰等八要素、值非空——enterprise 详情载荷可直接采用。"""
    assert set(EIGHT_ELEMENTS_ZH) == set(EIGHT_ELEMENTS)
    for key, zh in EIGHT_ELEMENTS_ZH.items():
        assert isinstance(zh, str) and zh.strip(), f"要素 {key} 中文名为空"


def test_importable_from_sanctioned_paths_enterprise_letter_uses():
    """enterprise 联络函请求①的精确 import 路径在 sanctioned 面真实可用。"""
    from chiyu_decision.api import score_rubric  # 决策脊柱面

    assert callable(score_rubric)
    # contract 面（本文件顶部 import 即证）＋ decision 面双路径实证
    import chiyu_kernel.contract as c

    assert c.EIGHT_ELEMENTS is EIGHT_ELEMENTS
    assert c.EIGHT_ELEMENTS_ZH is EIGHT_ELEMENTS_ZH


def test_score_rubric_is_order_insensitive_to_input_mapping():
    """score_rubric 按键名遍历 RUBRIC_KEYS——对传入 dict 插入顺序零敏感（请求①）。"""
    from chiyu_decision.api import score_rubric

    base = {
        "clarity": 3, "accuracy": 3, "precision": 3, "relevance": 3,
        "depth": 3, "breadth": 3, "logic": 3, "importance": 3,
        "fairness": 3,
    }
    reversed_input = dict(reversed(list(base.items())))
    r1 = score_rubric(base)
    r2 = score_rubric(reversed_input)
    assert r1.ratio == pytest.approx(r2.ratio)
    assert r1.missing == r2.missing == ()


def test_contract_package_reexports_every_decision_contract_symbol():
    """contract/__init__ 再导出完备性（2026-10-12，APS 增补回执附带发现）。

    消费方纪律只许 import ``chiyu_kernel.contract``——T58 曾把
    ``AUDIT_RECORD_KIND`` 加进 ``contract.decision.__all__`` 却漏了包级
    再导出，消费方被迫走内部路径（违约或拿不到）。本守卫把缝隙机械钉死：
    decision 契约 ``__all__`` 的每个符号必须经 ``chiyu_kernel.contract``
    顶层真实可达（且为同一对象）。
    """
    import chiyu_kernel.contract as pkg
    from chiyu_kernel.contract import decision as decision_mod

    missing = [
        name for name in decision_mod.__all__
        if not hasattr(pkg, name)
        or getattr(pkg, name) is not getattr(decision_mod, name)
    ]
    assert missing == [], (
        f"contract/__init__ 再导出缺口（消费方经 sanctioned 面拿不到）: {missing}"
    )
