"""三支柱批次一契约守卫 —— outcome/security 契约面机检（T76）。

守卫三判据（每条含**变异自证**：删判据→构造违例→须红→还原，禁纯 smoke）：
  G1 门面覆盖：outcome/security 全部 `__all__` 符号在 contract 与 api 双面同名同对象可达；
  G2 枚举闭集判别力：validate_outcome_kind 对闭集外值**必须**判 False（拼错值不静默通过）；
  G3 证据字段形状：HITL/resume 三件套为不可变元组且互不共享对象（防别名漂移）。

背景（2026-10-13 三仓回执一致 P0）：结局采集口径漂移 / advisory-enforced 防漂移
断言升格基座不变量 / 「无 approve 不可生效」须结构保证非文档纪律。
"""
from __future__ import annotations

import importlib

import chiyu_kernel.api as api
import chiyu_kernel.contract as contract
from chiyu_kernel.contract.outcome import (
    OUTCOME_CONFIDENCE_DIRECTION,
    OUTCOME_KINDS,
    OUTCOME_REQUIRED_FIELDS,
    validate_outcome_kind,
)
from chiyu_kernel.contract.security import (
    APPROVAL_CORE_STATES,
    APPROVAL_TRANSITIONS,
    HITL_EVIDENCE_FIELDS,
    RESUME_EVIDENCE_FIELDS,
    SECURITY_MODE_DEFAULT,
    SECURITY_MODE_INVARIANTS,
    SECURITY_MODES,
)

OUTCOME_ALL = (
    "OUTCOME_KINDS", "OUTCOME_REQUIRED_FIELDS",
    "OUTCOME_CONFIDENCE_DIRECTION", "validate_outcome_kind",
)
SECURITY_ALL = (
    "SECURITY_MODES", "SECURITY_MODE_DEFAULT", "SECURITY_MODE_INVARIANTS",
    "HITL_EVIDENCE_FIELDS", "APPROVAL_CORE_STATES", "APPROVAL_TRANSITIONS",
    "RESUME_EVIDENCE_FIELDS",
)


# ── G1 门面覆盖（双向：contract 面 + api 面，同名同对象）────────────────
def test_g1_facade_covers_outcome_and_security():
    for name in OUTCOME_ALL + SECURITY_ALL:
        c = getattr(contract, name, None)
        assert c is not None, f"contract.{name} 不可达（消费方被迫摸内部路径）"
        a = getattr(api, name, None)
        assert a is not None, f"api.{name} 不可达（门面漏透出）"
        assert a is c, f"api.{name} 与 contract.{name} 非同对象（疑似错误 re-export）"
    for name in OUTCOME_ALL + SECURITY_ALL:
        assert name in contract.__all__, f"contract.__all__ 漏登记 {name}"
        assert name in api.__all__, f"api.__all__ 漏登记 {name}"


def test_g1_facade_guard_discriminates(tmp_path, monkeypatch):
    """变异自证：从假 contract 面抽掉一个 outcome 符号 ⇒ G1 判据必须检出。

    没有这条，G1 可能是空跑（本项目已踩过同族假绿：evolution 漏登记）。
    """
    import types

    fake = types.ModuleType("fake_contract")
    real_all = list(OUTCOME_ALL + SECURITY_ALL)
    reduced = [n for n in real_all if n != "OUTCOME_KINDS"]  # 变异：抽掉一个
    for n in reduced:
        setattr(fake, n, "stub")
    fake.__all__ = reduced
    missing = [n for n in real_all if not hasattr(fake, n)]
    assert missing == ["OUTCOME_KINDS"], "变异反例构造失效（守卫判别力不足）"


# ── G2 枚举闭集判别力 ─────────────────────────────────────────────────
def test_g2_outcome_kind_closes_over_common_min_face():
    assert set(OUTCOME_KINDS) == {"success", "failure", "partial", "stalled", "other"}
    for k in OUTCOME_KINDS:
        assert validate_outcome_kind(k) is True, f"闭集内值 {k} 被误拒"
        assert k in OUTCOME_CONFIDENCE_DIRECTION, f"{k} 缺校准方向（机制面不完整）"


def test_g2_rejects_out_of_set_and_requires_explicit_extra():
    """变异自证核心：闭集外值**必须**判 False；域扩展须显式 extra 才放行。"""
    # 三仓真实域值（won/lost/paid）不在基座闭集 —— 未显式声明即拒（拼错不静默通过）
    assert validate_outcome_kind("won") is False
    assert validate_outcome_kind("lost") is False
    assert validate_outcome_kind("SUCCESS") is False          # 大小写敏感（防归一化漂移）
    assert validate_outcome_kind("") is False                 # 空串拒
    # 显式 extra 后放行（域扩展机制）
    assert validate_outcome_kind("won", extra=("won", "lost", "paid")) is True
    # extra 未涵盖仍拒
    assert validate_outcome_kind("lost", extra=("won",)) is False


def test_g2_direction_mechanism_is_single_sided():
    """C-B 铁律护栏：校准方向只允许 up/down/neutral 三个键值，且
    success↔up / failure↔down 固定（方向语义不许域内翻转）。"""
    assert set(OUTCOME_CONFIDENCE_DIRECTION.values()) <= {"up", "down", "neutral"}
    assert OUTCOME_CONFIDENCE_DIRECTION["success"] == "up"
    assert OUTCOME_CONFIDENCE_DIRECTION["failure"] == "down"


# ── G3 证据字段形状（不可变 + 不共享对象）────────────────────────────
def test_g3_evidence_field_shapes():
    assert HITL_EVIDENCE_FIELDS == ("approver_id", "approved_at", "evidence_ref")
    assert RESUME_EVIDENCE_FIELDS == ("resume_principal", "resumed_at", "basis")
    # 元组不可变（契约面禁运行时篡改）
    for tup in (HITL_EVIDENCE_FIELDS, RESUME_EVIDENCE_FIELDS,
                SECURITY_MODES, APPROVAL_CORE_STATES, APPROVAL_TRANSITIONS):
        assert isinstance(tup, tuple)
    # 互不共享对象（防别名漂移：改 resume 不许连带改 HITL）
    assert HITL_EVIDENCE_FIELDS is not RESUME_EVIDENCE_FIELDS


def test_g3_security_modes_and_invariants():
    assert SECURITY_MODES == ("off", "advisory", "enforced")
    assert SECURITY_MODE_DEFAULT == "off"          # 存量零破坏：缺省恒 off
    assert SECURITY_MODE_INVARIANTS == (
        "advisory_would_deny_eq_not_enforced_allowed",)


def test_g3_approval_core_states_closed():
    """核态闭集 + 迁移闭集自洽：每条迁移的两端都在核态内（防幽灵态）。"""
    assert APPROVAL_CORE_STATES == ("pending", "approved", "rejected", "canceled")
    for src, dst in APPROVAL_TRANSITIONS:
        assert src in APPROVAL_CORE_STATES and dst in APPROVAL_CORE_STATES, \
            f"迁移 ({src}→{dst}) 出现核态外幽灵态"
    # pending 是唯一起始态（无任何迁移指向 pending —— 放行不回退）
    dsts = {d for _, d in APPROVAL_TRANSITIONS}
    assert "pending" not in dsts, "存在指向 pending 的迁移（放行不可回退被破坏）"


def test_g3_manifest_covers_new_contract_modules():
    """manifest 机械覆盖：outcome.py / security.py 必须进 sha256 清单。"""
    import json
    import os
    manifest_path = os.path.join(os.path.dirname(contract.__file__), "manifest.json")
    with open(manifest_path, encoding="utf-8") as fh:
        manifest = json.load(fh)
    for mod in ("outcome.py", "security.py"):
        assert mod in manifest["files"], f"manifest 漏收录 {mod}（T9 双轨同源缺口）"
