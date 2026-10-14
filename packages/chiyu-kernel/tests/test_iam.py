"""Batch-1b-1 iam 守卫测试——rbac_core + standing_credential + two_phase_token。

对拍锚点：
  - CRM `src/http/middleware/rbac.js`（normalizeRole/hasRole/hasAnyRole fail-closed）
  - CRM `src/authorization/grantStore.js:13` grantCovers + recordExecution 用量熔断判据
  - CRM `src/authorization/grantSweeper.js` sweepOnce（到期 + 连续否决，N>0 才启用）
  - mcpserver 两阶段确认（提升前原实现，委托后必须同对象同行为）
"""
import pytest

from chiyu_kernel import api
from chiyu_kernel.contract import iam as ciam
from chiyu_kernel.contract.iam import (
    CREDENTIAL_INVARIANTS, GRANT_VERDICTS, PAUSE_REASONS,
    RBAC_DENY_REASONS, RBAC_INVARIANTS, STANDING_GRANT_STATUSES,
    TWO_PHASE_INVARIANTS,
)
from chiyu_kernel.contract.security import APPROVAL_CORE_STATES
from chiyu_kernel.iam import (
    grant_covers, has_any_role, has_role, issue_confirm_token, normalize_role,
    permission_allows, resolve_active_grant, role_deny_reason, sweep_grant,
    usage_breaker, verify_confirm_token,
)
from chiyu_kernel.mcpserver import McpServer

# 别名表是消费方注入的**全函数**词汇表：别名与规范名都要登记（未登记恒 None fail-closed）
ALIASES = {"sales": "SALES", "ten_admin": "TAN_ADMIN", "sysadmin": "SYSADMIN",
           "SALES": "SALES", "TAN_ADMIN": "TAN_ADMIN", "SYSADMIN": "SYSADMIN",
           "OPS": "OPS"}
NOW = "2026-10-14T12:00:00"


# ── rbac_core：别名归一 fail-closed ─────────────────────────────────────────
def test_normalize_role_strips_and_maps():
    assert normalize_role(" ten_admin ", ALIASES) == "TAN_ADMIN"
    assert normalize_role("sales", ALIASES) == "SALES"


def test_normalize_role_unknown_is_none_fail_closed():
    # 未知角色归一为 None（MUTANT：改成返回原串即模糊放行）
    assert normalize_role("root", ALIASES) is None
    assert normalize_role("", ALIASES) is None
    assert normalize_role(None, ALIASES) is None
    assert normalize_role("  ", ALIASES) is None


def test_has_role_exact_after_normalize():
    assert has_role("ten_admin", "TAN_ADMIN", ALIASES)
    # 归一后精确相等：档位不相通（sysadmin ≠ ADMIN 风格和稀泥被禁）
    assert not has_role("sysadmin", "TAN_ADMIN", ALIASES)
    # 需求角色本身没登记 ⇒ 同样拒（假绿反向形态）
    assert not has_role("sales", "typo_role", ALIASES)


def test_has_any_role_and_tenant_scope():
    assert has_any_role("sales", ["SALES", "OPS"], ALIASES)
    assert not has_any_role("sales", [], ALIASES)          # 需求集空 ⇒ 拒
    assert not has_any_role("ghost", ["SALES"], ALIASES)   # 主体未知 ⇒ 拒
    # 租户档角色：跨租户越域即拒
    assert not has_any_role(
        "ten_admin", ["TAN_ADMIN"], ALIASES,
        target_tenant_id="t2", principal_tenant_id="t1",
        tenant_scoped_roles=["ten_admin"])
    assert has_any_role(
        "ten_admin", ["TAN_ADMIN"], ALIASES,
        target_tenant_id="t1", principal_tenant_id="t1",
        tenant_scoped_roles=["ten_admin"])
    # 非租户档角色不受租户域限制
    assert has_any_role(
        "sales", ["SALES"], ALIASES,
        target_tenant_id="t2", principal_tenant_id="t1",
        tenant_scoped_roles=["ten_admin"])


def test_permission_allows_total_function():
    MATRIX = {"crm": {"SALES": ("read", "write"), "OPS": ("read",)}}
    assert permission_allows(MATRIX, "crm", "SALES", "write")
    assert not permission_allows(MATRIX, "crm", "OPS", "write")   # 动作未授予
    assert not permission_allows(MATRIX, "nope", "SALES", "read")  # ns 未登记
    assert not permission_allows(MATRIX, "crm", "GHOST", "read")   # 角色未登记
    assert not permission_allows(MATRIX, "crm", "SALES", "")       # 空动作
    # 未登记 (ns, role) 恒拒，禁默认放行（MUTANT：except 分支改放行即红）
    assert not permission_allows({}, "crm", "SALES", "read")


def test_role_deny_reason_ordering():
    # 判序：no_principal → unknown_role → tenant_mismatch → role_not_allowed
    assert role_deny_reason("sales", ["OPS"], ALIASES, has_principal=False) == "no_principal"
    assert role_deny_reason("ghost", ["OPS"], ALIASES) == "unknown_role"
    assert role_deny_reason(
        "ten_admin", ["TAN_ADMIN"], ALIASES,
        target_tenant_id="t2", principal_tenant_id="t1",
        tenant_scoped_roles=["ten_admin"]) == "tenant_mismatch"
    assert role_deny_reason("sales", ["OPS"], ALIASES) == "role_not_allowed"
    assert role_deny_reason("sales", ["SALES"], ALIASES) == ""
    # 拒因全部取自闭集
    for r in ("no_principal", "unknown_role", "role_not_allowed",
              "tenant_mismatch", "permission_denied"):
        assert r in RBAC_DENY_REASONS


# ── standing_credential：覆盖判定 ───────────────────────────────────────────
def _grant(**kw):
    base = {"status": "active", "scope_actions": ["crm.write", "crm.read"],
            "field_whitelist": ["name", "phone"], "expires_at": None,
            "max_uses": None, "used_count": 0}
    base.update(kw)
    return base


def test_grant_covers_happy_path():
    g = _grant()
    assert grant_covers(g, action="crm.write", fields=["name"], now=NOW)


def test_grant_covers_fail_paths():
    assert not grant_covers(None, action="crm.write", now=NOW)
    assert not grant_covers(_grant(status="paused"), action="crm.write", now=NOW)
    assert not grant_covers(_grant(status="revoked"), action="crm.write", now=NOW)
    # 过期：严格小于（等于不算过期，CRM new Date().getTime() < Date.now() 同口径）
    assert not grant_covers(_grant(expires_at="2026-10-14T11:00:00"),
                            action="crm.write", now=NOW)
    assert grant_covers(_grant(expires_at=NOW), action="crm.write", now=NOW)
    assert not grant_covers(_grant(scope_actions=None), action="crm.write", now=NOW)
    assert not grant_covers(_grant(scope_actions=["crm.read"]), action="crm.write", now=NOW)
    # 字段白名单超集语义：请求字段每元素都须被包含
    assert not grant_covers(_grant(), action="crm.write", fields=["name", "email"], now=NOW)
    # 白名单空/缺省 ⇒ 不限字段
    assert grant_covers(_grant(field_whitelist=None), action="crm.write",
                        fields=["anything"], now=NOW)
    assert grant_covers(_grant(field_whitelist=[]), action="crm.write",
                        fields=["anything"], now=NOW)


def test_resolve_active_grant_first_wins():
    expired = _grant(expires_at="2026-10-14T11:00:00")
    ok = _grant()
    assert resolve_active_grant([expired, ok], action="crm.write", now=NOW) is ok
    assert resolve_active_grant([expired], action="crm.write", now=NOW) is None
    assert resolve_active_grant([], action="crm.write", now=NOW) is None


def test_usage_breaker_matches_crm_judgement():
    assert usage_breaker(_grant(max_uses=3, used_count=2)) is None
    # 达限（used_count >= max_uses）⇒ usage-limit（CRM UPDATE ... used_count >= max_uses 同口径）
    assert usage_breaker(_grant(max_uses=3, used_count=3)) == "usage-limit"
    assert usage_breaker(_grant(max_uses=3, used_count=5)) == "usage-limit"
    assert usage_breaker(_grant(max_uses=None, used_count=99)) is None   # 无上限不熔断
    assert usage_breaker(_grant(status="paused", max_uses=1, used_count=9)) is None
    assert "usage-limit" in PAUSE_REASONS


def test_sweep_grant_expiry_and_trust_degrade():
    g = _grant()
    # ① 到期
    assert sweep_grant(_grant(expires_at="2026-10-14T11:00:00"),
                       consecutive_reject_limit=3, now=NOW) == "expired"
    assert sweep_grant(g, consecutive_reject_limit=3, now=NOW) is None
    # ② 连续否决：恰好 N 条全 rejected ⇒ 降级
    assert sweep_grant(g, ["rejected", "rejected", "rejected"],
                       consecutive_reject_limit=3, now=NOW) == "consecutive-rejects"
    # 混入非 rejected ⇒ 不降级
    assert sweep_grant(g, ["rejected", "approved", "rejected"],
                       consecutive_reject_limit=3, now=NOW) is None
    # 不足 N 条 ⇒ 不判（CRM verdicts.length >= N 同口径）
    assert sweep_grant(g, ["rejected", "rejected"],
                       consecutive_reject_limit=3, now=NOW) is None
    # 超过 N 条取**最近 N 条**（最新在前）：前 3 条全 rejected 即降级
    assert sweep_grant(g, ["rejected", "rejected", "rejected", "approved"],
                       consecutive_reject_limit=3, now=NOW) == "consecutive-rejects"
    # N<=0 ⇒ 关闭信任降级（CRM if (N > 0) 同口径）
    assert sweep_grant(g, ["rejected", "rejected", "rejected"],
                       consecutive_reject_limit=0, now=NOW) is None
    # 非 active 不巡检（CRM WHERE status='active' 同口径）
    assert sweep_grant(_grant(status="paused"), ["rejected"] * 5,
                       consecutive_reject_limit=3, now=NOW) is None


# ── two_phase_token：三重绑定 + 委托同实现 ─────────────────────────────────
def test_confirm_token_triple_binding():
    tok = issue_confirm_token("s3cret", "crm.write", {"a": 1}, "alice")
    assert verify_confirm_token("s3cret", "crm.write", {"a": 1}, "alice", tok)
    # 改工具名 / 改参数 / 换主体 ⇒ 失效（MUTANT：任一绑定项从签名消息中移除即红）
    assert not verify_confirm_token("s3cret", "crm.read", {"a": 1}, "alice", tok)
    assert not verify_confirm_token("s3cret", "crm.write", {"a": 2}, "alice", tok)
    assert not verify_confirm_token("s3cret", "crm.write", {"a": 1}, "bob", tok)
    assert not verify_confirm_token("other", "crm.write", {"a": 1}, "alice", tok)
    # 空参数与 None 参数同串（canonical_args 语义）
    assert issue_confirm_token("s", "n", None, "p") == issue_confirm_token("s", "n", {}, "p")


def test_canonical_args_key_order_independent():
    from chiyu_kernel.iam import canonical_args
    assert canonical_args({"b": 1, "a": 2}) == canonical_args({"a": 2, "b": 1})
    assert canonical_args(None) == canonical_args({})


def test_mcpserver_delegates_to_iam_same_object():
    # 禁双源：mcpserver 导出的三个令牌函数必须与 iam.two_phase 同一对象
    from chiyu_kernel import mcpserver as m
    from chiyu_kernel.iam import two_phase as tp
    assert m.issue_confirm_token is tp.issue_confirm_token
    assert m.verify_confirm_token is tp.verify_confirm_token
    assert m.canonical_args is tp.canonical_args
    # 门面同对象（api 经 mcpserver 导出）
    assert api.issue_confirm_token is tp.issue_confirm_token


def test_mcpserver_two_phase_write_flow_end_to_end():
    srv = McpServer(auth=lambda ctx: True, secret="k")
    srv.expose("save_thing", lambda args, ctx: {"saved": args},
               description="写", risk="write")
    # 第一阶段：不执行，返回 confirmation_required + token
    r1 = srv.call("save_thing", {"x": 1}, ctx={"principal": "u1"})
    assert r1["result"]["status"] == "confirmation_required"
    tok = r1["result"]["confirm_token"]

    def call_with_token(args, token, principal="u1"):
        return srv.handle_request(
            {"id": 2, "method": "tools/call",
             "params": {"name": "save_thing", "arguments": args,
                        "confirm_token": token}},
            ctx={"principal": principal})

    # 拿 token 后改参数 ⇒ 失效（三重绑定）
    r2 = call_with_token({"x": 2}, tok)
    assert r2["error"]["code"] == -32000
    # 同参数同主体 ⇒ 执行
    r3 = call_with_token({"x": 1}, tok)
    assert r3["result"] == {"saved": {"x": 1}}
    # 换主体 ⇒ 失效
    r4 = call_with_token({"x": 1}, tok, principal="bob")
    assert r4["error"]["code"] == -32000


# ── 契约词汇面与跨契约一致性 ───────────────────────────────────────────────
def test_contract_vocabularies():
    assert STANDING_GRANT_STATUSES == ("active", "paused", "revoked", "expired")
    assert set(PAUSE_REASONS) >= {"usage-limit", "consecutive-rejects"}
    assert len(RBAC_INVARIANTS) == 5 and len(CREDENTIAL_INVARIANTS) == 6
    assert len(TWO_PHASE_INVARIANTS) == 3
    assert len(set(RBAC_INVARIANTS)) == len(RBAC_INVARIANTS)
    assert len(set(CREDENTIAL_INVARIANTS)) == len(CREDENTIAL_INVARIANTS)


def test_grant_verdicts_subset_of_approval_core_states():
    # 跨契约对拍：GRANT_VERDICTS ⊆ APPROVAL_CORE_STATES（禁第二份状态词汇）
    assert set(GRANT_VERDICTS) <= set(APPROVAL_CORE_STATES)


def test_facade_exports_same_objects():
    assert api.normalize_role is normalize_role
    assert api.grant_covers is grant_covers
    assert api.sweep_grant is sweep_grant
    for name in ("RBAC_INVARIANTS", "RBAC_DENY_REASONS", "STANDING_GRANT_STATUSES",
                 "PAUSE_REASONS", "GRANT_VERDICTS", "CREDENTIAL_INVARIANTS",
                 "TWO_PHASE_INVARIANTS"):
        assert getattr(api, name) is getattr(ciam, name)
