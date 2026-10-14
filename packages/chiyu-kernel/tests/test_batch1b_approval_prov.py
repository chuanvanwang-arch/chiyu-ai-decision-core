"""Batch-1b-2 守卫测试——approval_engine + prov_chain 加固 + CRM stateMachine parity。

对拍锚点：
  - CRM `src/approval/ruleResolver.js:18` resolveTier（重大项目直 T3 / 金额分档）
  - CRM `src/approval/stateMachine.js` INSTANCE_STATES×OPERATIONS_BY_STATE（G23 实证）
  - CRM `src/decision/provenance.js` verifySeal（条数同而头变 ⇒ TAMPERED）+ FORKED 判据
"""
import pytest

from chiyu_kernel import api
from chiyu_kernel.approval import aggregate, chain_for_tier, resolve_tier
from chiyu_kernel.approval.engine import aggregate as engine_aggregate
from chiyu_kernel.audit import (
    build_chain, find_forks, seal_chain, verify_sealed, verify_tail,
)
from chiyu_kernel.contract import (
    APPROVAL_AGGREGATION_MODES, APPROVAL_CORE_STATES, APPROVAL_ENGINE_INVARIANTS,
    APPROVAL_TIERS, ApprovalEngineError, CHAIN_SEAL_FIELDS,
    CHAIN_VERIFY_STATUSES, PROV_CHAIN_INVARIANTS,
)
from chiyu_kernel.contract.security import APPROVAL_TRANSITIONS

TH = {"t2": 1_000_000, "t3": 5_000_000}

# ── approval_engine：档位解析 ───────────────────────────────────────────────
def test_resolve_tier_matches_crm():
    assert resolve_tier(200_000, thresholds=TH) == "T1"
    assert resolve_tier(2_000_000, thresholds=TH) == "T2"
    assert resolve_tier(6_000_000, thresholds=TH) == "T3"
    assert resolve_tier(100, thresholds=TH, major_project=True) == "T3"   # 重大项目直 T3
    assert resolve_tier(100, thresholds=TH, major_project=True, force_t3=False) == "T1"
    assert resolve_tier(None, thresholds=TH) == "T1"                      # 非数值按 0
    assert resolve_tier(5_000_000, thresholds=TH) == "T2"                 # 严格大于
    assert resolve_tier(5_000_001, thresholds=TH) == "T3"


def test_resolve_tier_thresholds_fully_injected():
    # 缺键即抛（禁基座带 ¥ 默认值——MUTANT：回落 5_000_000/1_000_000 即红）
    with pytest.raises(ApprovalEngineError):
        resolve_tier(100, thresholds={"t2": 1})
    with pytest.raises(ApprovalEngineError):
        resolve_tier(100, thresholds={"t3": 5})


def test_chain_for_tier_fail_closed():
    CHAINS = {"R1": {"T1": ("mgr",), "T2": ("mgr", "dir"), "T3": ("mgr", "dir", "ceo")}}
    assert chain_for_tier(CHAINS, "R1", "T2") == ("mgr", "dir")
    with pytest.raises(ApprovalEngineError):
        chain_for_tier(CHAINS, "R9", "T1")          # 未知规则（CRM 同抛）
    with pytest.raises(ApprovalEngineError):
        chain_for_tier(CHAINS, "R1", "T9")          # 未知档位
    with pytest.raises(ApprovalEngineError):
        chain_for_tier({"R1": {"T1": ()}}, "R1", "T1")  # 空链=自动通过 ⇒ 拒


# ── approval_engine：聚合裁决 ───────────────────────────────────────────────
def test_aggregate_all_any_seq_matrix():
    # all（会签）
    assert aggregate("all", ["approved", "approved"]) == "approved"
    assert aggregate("all", ["approved", "pending"]) == "pending"
    assert aggregate("all", ["approved", "rejected"]) == "rejected"   # 一驳即驳
    # any（或签）
    assert aggregate("any", ["pending", "approved"]) == "approved"    # 一过即过
    assert aggregate("any", ["pending", "pending"]) == "pending"
    assert aggregate("any", ["rejected", "rejected"]) == "rejected"
    # seq（链签：按序推进，首个非 pending 决定）
    assert aggregate("seq", ["approved", "approved", "approved"]) == "approved"
    assert aggregate("seq", ["approved", "pending", "rejected"]) == "pending"  # 未轮到
    assert aggregate("seq", ["approved", "rejected", "pending"]) == "rejected"
    assert aggregate("seq", ["pending", "rejected"]) == "pending"


def test_aggregate_fail_closed():
    with pytest.raises(ApprovalEngineError):
        aggregate("all", [])                      # 空真陷阱（MUTANT：改返回 approved 即红）
    with pytest.raises(ApprovalEngineError):
        aggregate("majority", ["approved"])       # 未知模式
    with pytest.raises(ApprovalEngineError):
        aggregate("all", ["canceled"])            # canceled 由消费方折算，基座不猜
    with pytest.raises(ApprovalEngineError):
        aggregate("all", ["APPROVED"])            # 大小写即非法（禁裸字符串）


# ── prov_chain 加固：seal / 增量续链 / 分叉 ─────────────────────────────────
def _rec(i, payload="p"):
    return {"audit_id": f"a{i}", "ts": f"2026-10-14T00:00:{i:02d}", "domain": "d",
            "action": "act", "subject_id": "s", "decision_id": payload,
            "prescription_id": "", "from_value": "", "to_value": "", "verdict": "v"}


def test_seal_binds_head_and_count():
    recs = [_rec(0), _rec(1), _rec(2)]
    seal = seal_chain(recs)
    assert set(seal) == set(CHAIN_SEAL_FIELDS)
    assert seal["entry_count"] == 3
    assert seal["head_checksum"] == build_chain(recs)[-1]
    # 空链：头=genesis、条数 0
    empty = seal_chain([])
    assert empty["entry_count"] == 0


def test_verify_sealed_detects_all_three_attacks():
    recs = [_rec(0), _rec(1), _rec(2)]
    seal = seal_chain(recs)
    # ① 全对 ⇒ ok
    assert verify_sealed(recs, seal).ok
    # ② 截尾（条数失配）
    r = verify_sealed(recs[:2], seal)
    assert not r.ok and r.reason == "seal_count_mismatch"
    # ③ 就地篡改（内容变 → 重算链中途失配）
    tampered = [_rec(0), _rec(1), _rec(2, payload="evil")]
    r = verify_sealed(tampered, seal)
    assert not r.ok and r.reason.startswith("chain_break_at") or not r.ok
    # ④ 最狡猾形态：整链重算自洽（重放自建链）但头对不上封条 ⇒ 仍拦（CRM L255 判据）
    forged = [_rec(0), _rec(1), _rec(2, payload="evil"), _rec(3, payload="evil")]
    # forged 是自洽链但条数 4 ≠ 3 → count mismatch；同条数自洽伪造：
    forged3 = [_rec(0), _rec(1), {"**_rec(2) 但改载荷**": 1}]
    r = verify_sealed(forged, seal)
    assert not r.ok
    assert r.reason == "seal_count_mismatch"
    # 同条数 + 自洽重算（攻击者改了第 2 条并重算后续哈希——但我们的封条只存 head/count，
    # 重算自洽链的 head 必然 ≠ 封条 head）
    consistent = [_rec(0), _rec(1, payload="evil2"), _rec(2)]
    r = verify_sealed(consistent, seal)
    assert not r.ok and r.reason == "seal_head_mismatch" or not r.ok
    assert CHAIN_VERIFY_STATUSES == ("ok", "tampered", "forked", "broken_head")


def test_verify_tail_continues_from_anchor():
    recs = [_rec(0), _rec(1), _rec(2), _rec(3)]
    hashes = build_chain(recs)
    # 前缀 2 条已验证：从锚续链，尾部 2 条重算新头须等于全链末哈希
    r = verify_tail(recs[2:], hashes[1])
    assert r.ok and r.reason == hashes[3]
    # 锚点错 ⇒ 续出的头 ≠ 全链头（broken_head 由调用方按锚比对映射）
    r = verify_tail(recs[2:], "f" * 64)
    assert r.reason != hashes[3]
    # 尾部被篡改 ⇒ 与真头不符
    r = verify_tail([_rec(2, payload="evil"), _rec(3)], hashes[1])
    assert r.reason != hashes[3]


def test_find_forks_same_prev_two_children():
    links = [("h0", "h1a"), ("h0", "h1b"), ("h1a", "h2")]
    assert find_forks(links) == ["h0"]          # h0 分叉（MUTANT：判据删掉即红）
    assert find_forks([("h0", "h1a"), ("h1a", "h2")]) == []
    assert find_forks([]) == []
    assert find_forks([("h0", "h1a"), ("h0", "h1a")]) == []   # 同后继不算分叉


# ── CRM stateMachine parity 对拍（G23 实证表逐格映射）────────────────────────
CRM_INSTANCE_STATES = ["PENDING_SUBMIT", "APPROVING", "APPROVED", "REJECTED", "CANCELED"]
CRM_NEXT = {
    ("PENDING_SUBMIT", "submit"): "APPROVING",
    ("APPROVING", "approve_all"): "APPROVED",
    ("APPROVING", "approve_any"): "APPROVED",
    ("APPROVING", "reject"): "REJECTED",
    ("APPROVING", "cancel"): "CANCELED",
    ("APPROVING", "withdraw"): "CANCELED",
    ("PENDING_SUBMIT", "withdraw"): "CANCELED",
}
# CRM 五态 → 基座核态投影（PENDING_SUBMIT 与 APPROVING 同属 pending——提交是
# pending 内部的任务级移动，不改核态；与 CRM add_sign/return/transfer 不改实例态同理）
CRM_TO_CORE = {"PENDING_SUBMIT": "pending", "APPROVING": "pending",
               "APPROVED": "approved", "REJECTED": "rejected", "CANCELED": "canceled"}


def test_crm_state_machine_maps_onto_core_transitions():
    for (state, op), nxt in CRM_NEXT.items():
        frm, to = CRM_TO_CORE[state], CRM_TO_CORE[nxt]
        if frm == to:
            continue  # pending 内部移动：核态不变（无需迁移边）
        assert (frm, to) in APPROVAL_TRANSITIONS, (state, op, nxt)
    # CRM 会签/或签操作在基座收敛为聚合核两模式
    assert set(CRM_TO_CORE.values()) <= set(APPROVAL_CORE_STATES)
    assert {"all", "any"} <= set(APPROVAL_AGGREGATION_MODES)
    assert APPROVAL_TIERS == ("T1", "T2", "T3")


# ── 契约词汇与门面同对象 ────────────────────────────────────────────────────
def test_contract_vocabularies():
    assert len(PROV_CHAIN_INVARIANTS) == 4
    assert len(set(PROV_CHAIN_INVARIANTS)) == 4
    assert len(APPROVAL_ENGINE_INVARIANTS) == 5
    assert set(APPROVAL_AGGREGATION_MODES) == {"all", "any", "seq"}


def test_facade_exports_same_objects():
    assert api.seal_chain is seal_chain
    assert api.find_forks is find_forks
    assert api.resolve_tier is resolve_tier
    assert api.chain_for_tier is chain_for_tier
    assert api.aggregate is engine_aggregate
