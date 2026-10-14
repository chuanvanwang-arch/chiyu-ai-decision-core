"""GAP-7 capability_audit 守卫（Batch-2b，2026-10-14）。

覆盖：三查法 grep 定位 / 零命中最优先分级 / 定义≠调用点 / 零外部入口判
partial / 四件套装配（缺件显式标注）/ 鉴别力探针（缺件无 reason 必 FAIL）/
operator 不代填 / 基线对比 / 门面与契约同一对象 / APS 锚点 parity 形态。

parity 锚点（APS 仓只读，file:line 可反证）：
    · ``platform/capability_audit.py:80``   three_check 定位
    · ``platform/capability_audit.py:193``  _grade 零命中最优先（A6 修复顺序）
    · ``platform/capability_audit.py:172``  _count_production_calls 定义≠调用
    · ``platform/capability_audit.py:507``  probe_four_piece_discrimination 鉴别力
    · ``platform/capability_audit.py:443``  record_operator_log 不代填
"""
from __future__ import annotations

import os

import pytest

from chiyu_kernel import api
from chiyu_kernel import capability_audit
from chiyu_kernel.contract import capability_audit as contract_ca
from chiyu_kernel.capability_audit import (
    CapabilityFinding,
    assemble_four_piece,
    build_baseline_diff,
    build_compliance_selfcheck,
    build_traceability_graph,
    count_production_calls,
    grade_capability,
    is_call_line,
    probe_piece_discrimination,
    record_operator_log,
    three_check,
)


@pytest.fixture()
def code_root(tmp_path):
    """构造一棵最小源码树：target.py 有定义+调用，lonely.py 只有定义。"""
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "target.py").write_text(
        "def run_audit():\n    return 1\n\n\nresult = run_audit()\n",
        encoding="utf-8",
    )
    (tmp_path / "pkg" / "lonely.py").write_text(
        "def orphan():\n    return 2\n",
        encoding="utf-8",
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text(
        "from pkg.target import run_audit\n\n\ndef test_ok():\n    assert run_audit()\n",
        encoding="utf-8",
    )
    return tmp_path


# ── 三查法 ───────────────────────────────────────────────────────────

def test_three_check_locate_with_line_evidence(code_root):
    hits = three_check(r"def run_audit", root=str(code_root))
    assert hits, "应定位到 def run_audit"
    path, lineno, line = hits[0]
    assert path.replace("\\", "/").endswith("pkg/target.py")
    assert lineno == 1
    assert "def run_audit" in line


def test_three_check_exclude_self_avoids_false_positive(code_root):
    # 排除 tests/ 后只剩 pkg 命中（自检排除 = 反假绿 AFG-4 同族）
    hits = three_check(r"run_audit", root=str(code_root), exclude=("tests/",))
    assert all("tests" not in h[0].replace("\\", "/") for h in hits)


def test_three_check_zero_hit_returns_empty(code_root):
    assert three_check(r"nonexistent_symbol_xyz", root=str(code_root)) == []


# ── 定义 ≠ 调用点 ────────────────────────────────────────────────────

def test_is_call_line_filters_definitions_and_comments():
    assert is_call_line("result = run_audit()") is True
    assert is_call_line("def run_audit():") is False
    assert is_call_line("class Foo:") is False
    assert is_call_line("__all__ = [\"run_audit\"]") is False
    assert is_call_line("    # run_audit 注释") is False
    assert is_call_line('"""run_audit 文档串"""') is False


def test_count_production_calls_excludes_definition_lines():
    hits = [
        ("a.py", 1, "def run_audit():"),
        ("a.py", 5, "x = run_audit()"),
        ("a.py", 9, "# run_audit 提及"),
    ]
    assert count_production_calls(hits) == 1


# ── 分级判定（零命中最优先 / 零入口 partial）────────────────────────

def test_grade_zero_hit_is_missing_p0():
    verdict, priority, note = grade_capability(hit_count=0, production_calls=0)
    assert (verdict, priority) == ("missing", "P0")
    assert "零命中" in note


def test_grade_zero_entry_is_partial_p0():
    # ★ 零外部入口假绿形态：符号在、生产零调用 ⇒ partial，绝不 landed
    verdict, priority, note = grade_capability(hit_count=5, production_calls=0)
    assert (verdict, priority) == ("partial", "P0")
    assert "零外部入口" in note


def test_grade_with_production_calls_is_landed():
    verdict, priority, note = grade_capability(hit_count=5, production_calls=3)
    assert (verdict, priority) == ("landed", None)
    assert "3 处" in note


def test_grade_zero_hit_not_shadowed_by_consumer_special_case():
    # A6 修复顺序的不变式：即便消费方想给"特例说明"，零命中仍须 missing
    # （grade_capability 是纯函数、无特例分支；特例只能追加 note，不能改 verdict）
    verdict, _p, _n = grade_capability(hit_count=0, production_calls=99)
    assert verdict == "missing"


# ── 四件套 ───────────────────────────────────────────────────────────

def test_record_operator_log_never_forges_operator():
    out = record_operator_log(action="run_audit")
    assert out["operator"] is None
    assert out["status"] == "missing"
    assert out["outcome"] == "DRAFT_PENDING_USER_CONFIRM"
    assert out["reason"]
    ok = record_operator_log(action="run_audit", operator="王俊", outcome="confirmed")
    assert ok["operator"] == "王俊"
    assert ok["status"] == "ok"


def test_build_baseline_diff_first_run_declared_missing():
    out = build_baseline_diff({1: "landed"}, None)
    assert out["status"] == "missing"
    assert out["reason"]
    assert out["changes"] == []


def test_build_baseline_diff_lists_changes_with_priority():
    out = build_baseline_diff({1: "landed", 2: "missing"}, {1: "partial", 2: "missing"})
    assert out["status"] == "ok"
    assert out["changes"] == [
        {"capability": 1, "from": "partial", "to": "landed", "priority": "P1"},
    ]


def test_build_traceability_graph_explicit_missing_hops():
    findings = [
        {"capability": 9, "name": "feedback", "evidence": ["pkg/target.py:1"],
         "skill_ref": "~/.workbuddy/skills/ai-feedback-loop/SKILL.md"},
        {"capability": 10, "name": "audit", "evidence": [], "skill_ref": None},
    ]
    graph = build_traceability_graph(findings)  # 无 test 映射、无部署跳 ⇒ 显式缺
    assert graph["status"] == "partial"
    assert any("架构#REQ#C10" in m for m in graph["missing"])
    assert any(m.startswith("测试#") for m in graph["missing"])
    assert any(m.startswith("部署（") for m in graph["missing"])
    assert graph["coverage"].endswith("跳落到具体实体")


def test_build_traceability_graph_full_hops_ok():
    findings = [
        {"capability": 9, "name": "feedback", "evidence": ["pkg/target.py:1"],
         "skill_ref": "SKILL:ai-feedback-loop"},
    ]
    graph = build_traceability_graph(
        findings,
        test_files_by_probe={"target": ["tests/test_target.py"]},
        deploy_hint={"entity_id": "DEPLOY:Dockerfile", "status": "ok",
                     "label": "部署落点"},
    )
    assert graph["status"] == "ok"
    assert graph["missing"] == []


def test_compliance_selfcheck_rates_gates():
    out = build_compliance_selfcheck(gates=[
        {"id": "C1", "name": "判据源", "passed": True, "detail": "1/1"},
        {"id": "C2", "name": "证据", "passed": False, "detail": "0/1"},
    ])
    assert out["rate"] == 0.5
    assert out["缺口"] and "C2" in out["缺口"][0]


def test_probe_discrimination_fails_on_silent_omission():
    # 缺件且无 reason ⇒ 探针 FAIL（静默省略 = 判红）
    pieces = {
        "traceability_graph": {"status": "ok"},
        "baseline_diff": {"status": "missing"},          # 无 reason
        "operator_log": {"status": "ok"},
        "compliance_selfcheck": {"status": "ok"},
    }
    probe = probe_piece_discrimination(pieces)
    assert probe["passed"] is False
    assert "静默省略" in probe["detail"]


def test_probe_discrimination_passes_on_declared_missing():
    # 缺件但显式标注 reason ⇒ 合规形态，探针 PASS
    pieces = {
        "traceability_graph": {"status": "ok"},
        "baseline_diff": {"status": "missing", "reason": "首次审计即基线"},
        "operator_log": {"status": "ok"},
        "compliance_selfcheck": {"status": "ok"},
    }
    probe = probe_piece_discrimination(pieces)
    assert probe["passed"] is True
    assert "已标注" in probe["detail"]


def test_probe_discrimination_fails_on_absent_piece():
    probe = probe_piece_discrimination({"traceability_graph": {"status": "ok"}})
    assert probe["passed"] is False
    assert "absent" in probe["detail"]


def test_assemble_four_piece_is_draft_with_probe():
    four = assemble_four_piece(
        traceability_graph=build_traceability_graph(
            [], test_files_by_probe={}, deploy_hint={"entity_id": "DEPLOY:x",
                                                     "status": "ok"}),
        baseline_diff=build_baseline_diff({}, None),
        operator_log=record_operator_log(action="run_audit"),
        compliance_selfcheck=build_compliance_selfcheck(gates=[]),
    )
    assert four["status"] == "DRAFT"
    assert four["C3_probe"]["passed"] is True   # 缺件均已显式标注 ⇒ 合规
    assert set(contract_ca.AUDIT_PIECE_KEYS) <= set(four)


# ── 契约词汇 + 门面同一对象 ─────────────────────────────────────────

def test_invariants_vocabulary_complete():
    assert set(contract_ca.CAPABILITY_AUDIT_INVARIANTS) == {
        "zero_hit_first_missing", "zero_entry_is_partial", "definition_is_not_call",
        "missing_piece_declared", "draft_until_user_confirms", "operator_never_forged",
    }


def test_facade_exports_all_capability_audit_symbols():
    names = [
        "CAPABILITY_VERDICTS", "VERDICT_LANDED", "VERDICT_PARTIAL", "VERDICT_MISSING",
        "CAPABILITY_PRIORITIES", "AUDIT_PIECE_KEYS", "PIECE_STATUSES",
        "NON_CALL_LINE_PREFIXES", "AUDIT_STATUS_DRAFT", "AUDIT_STATUS_OK",
        "AUDIT_STATUS_PARTIAL", "AUDIT_STATUS_MISSING",
        "CAPABILITY_AUDIT_INVARIANTS", "CapabilityAuditError",
        "three_check", "is_call_line", "count_production_calls", "grade_capability",
        "CapabilityFinding", "record_operator_log", "build_baseline_diff",
        "build_traceability_graph", "build_compliance_selfcheck",
        "probe_piece_discrimination", "assemble_four_piece",
    ]
    for n in names:
        assert hasattr(api, n), f"门面缺 {n}"
        assert n in api.__all__, f"__all__ 缺 {n}"


def test_facade_symbols_are_same_objects():
    for n in ("VERDICT_MISSING", "AUDIT_PIECE_KEYS", "NON_CALL_LINE_PREFIXES"):
        assert getattr(api, n) is getattr(contract_ca, n)
    for n in ("three_check", "grade_capability", "probe_piece_discrimination",
              "assemble_four_piece", "CapabilityFinding"):
        assert getattr(api, n) is getattr(capability_audit, n)


def test_capability_finding_to_dict_shape():
    f = CapabilityFinding(capability=9, name="feedback", verdict="partial",
                         priority="P1", evidence=["a.py:1"], note="n")
    d = f.to_dict()
    assert set(d) == {"capability", "name", "verdict", "priority", "evidence",
                      "skill_ref", "note"}
    assert d["evidence"] == ["a.py:1"]


def test_os_import_used_only_by_io_boundary():
    # 形态守卫：IO 只允许出现在 three_check 模块（本包其余模块纯函数）
    pkg_dir = os.path.dirname(capability_audit.__file__)
    for mod in ("grading.py", "finding.py", "four_piece.py"):
        with open(os.path.join(pkg_dir, mod), encoding="utf-8") as fh:
            src = fh.read()
        assert "import os" not in src, f"{mod} 不应引入 IO"
        assert "open(" not in src, f"{mod} 不应读写文件"
