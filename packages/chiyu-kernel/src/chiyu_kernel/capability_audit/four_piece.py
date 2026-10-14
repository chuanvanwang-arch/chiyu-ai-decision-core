"""审计包四件套（C5）+ 鉴别力自证探针（C3）—— 纯函数，零 IO。

上迁源：APS ``platform/capability_audit.py`` 的 ``build_traceability_graph`` /
``build_baseline_diff`` / ``record_operator_log`` / ``build_compliance_selfcheck`` /
``probe_four_piece_discrimination`` / ``build_four_piece``。

两条红线（有守卫测试）：
    · **缺件显式标注**：任一件拿不到 ⇒ ``{"status": "missing", "reason": ...}``，
      绝不写 "ok" 或省略键——静默省略 = 判红（§3.4）；
    · **operator 不代填**：身份类字段 AI 不得伪造，缺省落 ``None`` 并标
      ``DRAFT_PENDING_USER_CONFIRM``，由用户对话补全后定稿（C7）。
"""
from __future__ import annotations

import time
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from chiyu_kernel.contract.capability_audit import (
    AUDIT_PIECE_KEYS,
    AUDIT_STATUS_DRAFT,
    AUDIT_STATUS_MISSING,
    AUDIT_STATUS_OK,
    AUDIT_STATUS_PARTIAL,
)

__all__ = [
    "record_operator_log", "build_baseline_diff", "build_traceability_graph",
    "build_compliance_selfcheck", "probe_piece_discrimination",
    "assemble_four_piece",
]

_DRAFT_OUTCOME = "DRAFT_PENDING_USER_CONFIRM"


def record_operator_log(
    *, action: str, outcome: Optional[str] = None,
    operator: Optional[str] = None,
) -> Dict[str, Any]:
    """件③操作人/时间记录：``operator + timestamp + action + outcome``。

    ★ C7：**不得由本函数伪造 operator**。省略时显式落 ``None`` 并标
      ``DRAFT_PENDING_USER_CONFIRM``（AI 不代填身份信息）。
    """
    return {
        "operator": operator,
        "timestamp": time.time(),
        "action": action,
        "outcome": outcome or _DRAFT_OUTCOME,
        "status": AUDIT_STATUS_MISSING if operator is None else AUDIT_STATUS_OK,
        "reason": (None if operator is not None
                   else "operator 待用户确认（C7，AI 不代填身份信息）"),
    }


def build_baseline_diff(
    current: Mapping[int, Any], previous: Optional[Mapping[int, Any]] = None,
) -> Dict[str, Any]:
    """件②版本基线对比：本轮 vs 上一份（按 capability → verdict 映射）。

    无历史报告 ⇒ **显式** ``status="missing"`` + reason（首次审计即基线），
    不静默返回空变更清单。
    """
    out: Dict[str, Any] = {"changes": [], "status": AUDIT_STATUS_OK}
    if not previous:
        out.update(status=AUDIT_STATUS_MISSING,
                   reason="首次审计即基线：无历史报告可比对，变更项清单为空"
                          "（显式标注，非静默省略）")
        return out
    for cap in sorted(set(previous) | set(current)):
        a, b = previous.get(cap), current.get(cap)
        if a != b:
            out["changes"].append({
                "capability": cap, "from": a, "to": b,
                "priority": "P0" if (a == "missing") != (b == "missing") else "P1",
            })
    out["changes"].sort(key=lambda c: c["capability"])
    return out


def _norm(path: str) -> str:
    """路径归一：Windows 反斜杠 → ``/``（entity_id 与正则搜索统一口径）。"""
    return path.replace("\\", "/")


def build_traceability_graph(
    findings: Iterable[Mapping[str, Any]], *,
    test_files_by_probe: Optional[Mapping[str, Sequence[str]]] = None,
    deploy_hint: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """件①全链路追溯图：正向 需求→架构→代码→测试→部署，反向 缺陷→需求。

    每跳落到**具体实体 ID**（``REQ#C{cap}`` / ``SKILL:…`` / ``CODE:path:line`` /
    ``TEST:file`` / ``DEPLOY:…``）——链接非复制。测试跳与部署跳由调用方经
    ``test_files_by_probe`` / ``deploy_hint`` 注入（域枚举留消费方）；缺跳
    **显式标注**进 ``missing``，不得静默省略。
    """
    test_map = dict(test_files_by_probe or {})
    forward: Dict[str, List[Dict[str, Any]]] = {
        "需求": [], "架构": [], "代码": [], "测试": [], "部署": [],
    }
    missing: List[str] = []
    code_to_cap: Dict[str, set] = {}

    for f in findings:
        cap = f.get("capability")
        rid = f"REQ#C{cap}"
        forward["需求"].append({"entity_id": rid, "label": f"能力 {cap} {f.get('name') or ''}",
                                "status": AUDIT_STATUS_OK})
        sr = f.get("skill_ref")
        if sr:
            forward["架构"].append({"entity_id": f"SKILL:{sr}",
                                    "label": f"能力 {cap} 判据源（动态引用）",
                                    "status": AUDIT_STATUS_OK})
        else:
            missing.append(f"架构#{rid}（无 skill_ref）")

        evidence = [e for e in (f.get("evidence") or []) if isinstance(e, str) and e]
        for e in evidence[:3]:
            ep = _norm(e)
            forward["代码"].append({"entity_id": f"CODE:{ep}", "cap": cap,
                                    "label": "代码证据（file:line）", "status": AUDIT_STATUS_OK})
            code_to_cap.setdefault(ep.split(":", 1)[0], set()).add(rid)
            code_to_cap.setdefault(ep.split(":", 1)[0].rsplit("/", 1)[-1], set()).add(rid)

        # 测试跳：以该能力首条代码证据的模块名反查（映射由消费方注入）
        probe = ""
        if evidence:
            probe = _norm(evidence[0].split(":", 1)[0]).rsplit("/", 1)[-1]
            if probe.endswith(".py"):
                probe = probe[:-3]
        test_files = list(test_map.get(probe or "\0", ()))
        if test_files:
            for p in test_files[:3]:
                forward["测试"].append({"entity_id": f"TEST:{p}", "cap": cap,
                                        "label": f"覆盖 {rid} 的测试文件",
                                        "status": AUDIT_STATUS_OK})
        else:
            missing.append(f"测试#{rid}（未提供模块 {probe!r} 的测试文件映射）")

    dep = dict(deploy_hint) if deploy_hint else {
        "entity_id": "DEPLOY:<未提供>", "status": AUDIT_STATUS_MISSING,
        "reason": "未提供部署跳实体（调用方须经 deploy_hint 注入或显式标注）",
    }
    forward["部署"] = [dep]

    reverse: List[Dict[str, Any]] = []
    for item in forward["代码"][:6]:
        path = item["entity_id"][len("CODE:"):].split(":")[0]
        back = sorted(code_to_cap.get(path, set()))
        reverse.append({
            "from": item["entity_id"], "to": back,
            "label": "反向链：缺陷落在此代码点 → 归属需求号（空集 = 无需求归属，须补追溯）",
            "status": AUDIT_STATUS_OK if back else AUDIT_STATUS_MISSING,
        })

    hops_ok = sum(1 for lst in forward.values() for x in lst if x.get("status") == AUDIT_STATUS_OK)
    hops_all = sum(len(lst) for lst in forward.values())
    missing = list(missing)
    if dep.get("status") != AUDIT_STATUS_OK:
        missing.append(f"部署（{dep.get('reason', '无实体可落')}）")
    return {
        "entity_hops": forward,
        "reverse_links": reverse,
        "missing": missing,
        "status": AUDIT_STATUS_OK if not missing else AUDIT_STATUS_PARTIAL,
        "coverage": f"{hops_ok}/{hops_all} 跳落到具体实体",
    }


def build_compliance_selfcheck(
    *, gates: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    """件④合规自查：闸门列表（每项含 id/name/passed/detail）→ 通过率 + 未达标项。

    恒返回结构化结果（含缺口清单），**不**因未达标而抛——审计的价值在暴露缺口。
    """
    gates = list(gates or [])
    passed = sum(1 for g in gates if g.get("passed"))
    short = [f"[{g.get('id')}] {g.get('name')} —— {g.get('detail')}"
             for g in gates if not g.get("passed")]
    return {
        "gates": gates, "passed": passed, "total": len(gates),
        "rate": round(passed / len(gates), 4) if gates else 0.0,
        "未达标项": short,
        "status": AUDIT_STATUS_OK,
        "缺口": short,
    }


def probe_piece_discrimination(pieces: Mapping[str, Any]) -> Dict[str, Any]:
    """★ C3 自证鉴别力探针：四件套**缺件且无 reason** 时本探针 FAIL。

    注入缺陷（某件改 missing 且抹掉 reason）→ FAIL；显式标注补齐 → PASS。
    恒绿 == 无鉴别力（判红，见反假绿铁律）。

    ⚠ 入参是**已装配的四件套本体**（不是包它的 report）——否则装配期自举
    读到空，探针恒 FAIL 变成一个永远红的假失败。
    """
    pieces = pieces if isinstance(pieces, Mapping) else {}
    broken = False
    detail_parts: List[str] = []
    declared: List[str] = []
    for key in AUDIT_PIECE_KEYS:
        piece = pieces.get(key)
        if piece is None:
            broken = True
            detail_parts.append(f"{key}=absent（缺件且无任何记录）")
            continue
        if not isinstance(piece, Mapping):
            continue
        if piece.get("status") == AUDIT_STATUS_MISSING:
            # ★ 判红的是**静默省略**；显式标注 reason 是合规形态，不得判 FAIL。
            reason = piece.get("reason")
            if reason:
                declared.append(f"{key}=missing（已标注：{reason}）")
            else:
                broken = True
                detail_parts.append(f"{key}=missing 但无 reason（静默省略 = C5 判红）")
    return {
        "passed": not broken,
        "detail": "判定为缺陷：" + (", ".join(detail_parts) or "无")
                  + "；｜合规显式标注：" + (", ".join(declared) or "无"),
        "note": "鉴别力：注入『缺件且无 reason』→ 本探针 FAIL；显式标注补齐 → PASS（恒绿即判红）",
    }


def assemble_four_piece(
    *,
    traceability_graph: Mapping[str, Any],
    baseline_diff: Mapping[str, Any],
    operator_log: Mapping[str, Any],
    compliance_selfcheck: Mapping[str, Any],
) -> Dict[str, Any]:
    """总装四件套。先装配四件，再对**本装配体**做鉴别力探针（自举）。"""
    pieces = {
        "traceability_graph": dict(traceability_graph),
        "baseline_diff": dict(baseline_diff),
        "operator_log": dict(operator_log),
        "compliance_selfcheck": dict(compliance_selfcheck),
    }
    return {
        **pieces,
        "C3_probe": probe_piece_discrimination(pieces),
        "status": AUDIT_STATUS_DRAFT,
        "note": "★ C5：四件套齐备；任一件缺件已显式标注 reason（禁静默省略）。"
                "★ C7：DRAFT，operator 待用户确认。",
    }
