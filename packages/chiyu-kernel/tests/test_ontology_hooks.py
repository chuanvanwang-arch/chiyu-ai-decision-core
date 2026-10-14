"""T4 守卫（δ1）：本体三钩子 —— 幂等判变 + 双通道 + 写库即图 + 降级留痕。

⛔ 不连真 DB / 不装 ONNX/torch：`ensure_embedding` 的向量来源是
`vector.index_vector.resolve()`（T3 写读单一事实源），测试用
monkeypatched `_FakeBackend`（确定性、离线）—— 手法与 test_pad_ledger.py 对齐。
"""
from __future__ import annotations

import numpy as np
import pytest

from chiyu_kernel.contract.particle import VECTOR_DIM, PredicateSet, PredicateSpec
from chiyu_kernel.ontology import (
    OntologyGraph,
    ensure_embedding,
    ensure_tsvector,
    ontology_sync,
)
from chiyu_kernel.ontology.particle import Particle
from chiyu_kernel.vector import index_vector

VCOL = VECTOR_DIM
TEXT = "物业服务合同纠纷：业主反映物业服务质量与收费不匹配要求整改"

_REFS = ("甲物业公司", "某小区")


class _FakeBackend:
    """确定性假 backend（与 test_pad_ledger.py 同型）：512 维真向量。"""

    def __init__(self, dim: int = 512, backend: str = "cpu"):
        self._fake_dim = dim
        self.backend = backend
        self._dim = dim
        self.last_error = None
        self._runner = object()          # 使 model_status != "hash"

    @property
    def model_status(self) -> str:
        return "onnx" if self.backend != "none" else "hash"

    def encode(self, text: str) -> np.ndarray:
        v = np.zeros(self._fake_dim, dtype=np.float32)
        for i, ch in enumerate(text):
            v[i % self._fake_dim] = float((ord(ch) % 100) / 100.0)
        n = float(np.linalg.norm(v))
        return (v / n) if n > 0 else v


@pytest.fixture()
def fake_backend(monkeypatch):
    """把 index_vector 的后端替换成 `_FakeBackend`（不连 ONNX/torch）。"""
    index_vector.reset()
    monkeypatch.setattr(index_vector, "backend", lambda: _FakeBackend(dim=512))
    yield
    index_vector.reset()


def _particle(refs: tuple | None = _REFS, fulltext: str = TEXT) -> Particle:
    return Particle(
        particle_id="p001",
        type="unstructured_asset",
        subject_id="subj-1",
        raw_refs=refs,
        fulltext=fulltext,
    )


# ── δ1a：ensure_embedding 幂等判变（内容未变 ⇒ 二次调用不重算）──────────────
def test_ensure_embedding_is_idempotent(fake_backend):
    p = _particle()
    first = ensure_embedding(p, column_dim=VCOL)
    second = ensure_embedding(p, column_dim=VCOL)
    assert second == first, "内容未变 ⇒ 已物化则跳过重算（幂等）"
    assert p.provider in ("model", "model-p512"), f"provider 应为真向量标记：{p.provider}"
    assert p.content_hash, "判变键必须已回写"


# ── δ1b：降级不中断 + provider 显式留痕（无真通道 ⇒ hash，不抛异常）─────────
def test_ensure_embedding_degrades_without_raising(monkeypatch):
    index_vector.reset()
    monkeypatch.setattr(index_vector, "backend",
                        lambda: _FakeBackend(dim=512, backend="none"))
    p = _particle()
    provider = ensure_embedding(p, column_dim=VCOL)   # 不抛异常
    assert provider == "hash", f"无真通道必须降级哈希并留痕：{provider}"
    assert p.embedding is None
    assert p.content_hash, "即使降级，判变键仍应写（保证幂等判变键存在）"


# ── δ1c：三钩子按序可跑（ensure_tsvector 双通道 + ontology_sync 写即图）──────
def test_hooks_chain_runs(fake_backend):
    onto = OntologyGraph(predicates=PredicateSet(knowledge=(
        PredicateSpec(predicate="mentions", from_type="unstructured_asset",
                      to_type="entity", layer="K", source="rule"),
    )))
    p = _particle()
    ensure_embedding(p, column_dim=VCOL)
    fts = ensure_tsvector(p)
    assert fts == p.fulltext, "钩子2：全文文本与向量双通道同步（返回当前全文）"
    ontology_sync(p, onto)                       # 钩子3：写入即图
    nbr = onto.neighbors("p001")
    out_mentions = nbr["out"].get("mentions", [])
    assert set(out_mentions) == set(_REFS), f"引用型字段写入即建受控边：{out_mentions}"


# ── δ1d：graph 受控谓词有界（未注入 profile ⇒ 无受控边；非受控谓词拒绝）──────
def test_graph_rejects_uncontrolled_predicate(fake_backend):
    onto = OntologyGraph()                        # 未注入 profile.predicates
    assert onto.controlled() == (), "未注入 profile ⇒ 无受控谓词（不伪造）"
    with pytest.raises(ValueError, match="未受控谓词"):
        onto.link("mentions", "p001", "e001")


# ── δ1e：normalize 默认空后缀不剥（内核零领域默认）─────────────────────────
def test_normalize_default_no_suffix():
    from chiyu_kernel.ontology import normalize

    assert normalize("某公司") == "某公司"              # 默认不剥
    assert normalize("某某公司", suffixes=("公司",)) == "某某"  # 注入后缀才剥
    # 有界守卫：剥后剩余 < 2 字符 ⇒ 拒绝剥离（防把主体名剥光/剥错）
    assert normalize("某公司", suffixes=("公司",)) == "某公司"
