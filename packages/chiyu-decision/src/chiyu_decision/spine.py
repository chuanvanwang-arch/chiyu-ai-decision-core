"""决策脊柱运行时 —— S1→S5 不可重排主链（铁律 C-A / C-B / C-C 的执行体）。

⛔ `SPINE_ORDER` 来自 `chiyu_kernel.contract.decision`（L0 单一事实源），本包不得另写一份。
   顺序即语义：S1_context → S1_derive → S2_score → S3_aggregate → S4_redline → S5_persist。
   历史缺陷（demo 时序守卫）：① 九尺子晚于落库 ⇒ 置信度搁置；
   ② 红线短路在相似度之前 ⇒ 八要素与九尺子不参与判定。
   ⇒ 本运行时在 S5 前按 `SPINE_ORDER` 逐项执行；confidence 只取 ratio；红线在链末。
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Callable, Mapping, Optional, Tuple

from chiyu_kernel.approval import (
    DecisionApprovalGate, DecisionPassThroughGate, DecisionVerdictState,
    HITLEvidenceError, assert_hitl_evidence,
)
from chiyu_kernel.contract.decision import (
    AUDIT_EVENT_APPROVAL_PENDING, AUDIT_EVENT_APPROVAL_REJECTED,
    AUDIT_EVENT_APPROVAL_RESUMED, AUDIT_RECORD_KIND,
    AUTONOMOUS_RELEASE_DEFAULT, SPINE_ORDER, validate_spine_order,
)
from chiyu_kernel.contract.profile import RedlineSpec
from chiyu_kernel.contract.security import RESUME_EVIDENCE_FIELDS
from .errors import DecisionError
from .redline import RedlineVerdict, autonomous_release, evaluate_redline
from .scoring import (
    aggregate_confidence, cap_rubric_by_elements, check_elements, score_rubric,
)


@dataclass
class SpineResult:
    decision_id: str
    stage_reached: str
    confidence: float
    rubric_missing: Tuple[str, ...]
    elements_missing: Tuple[str, ...]
    redline_hit: bool
    redline_reasons: Tuple[str, ...]
    autonomous: bool
    persisted: bool = False
    approval_rejected: Optional[str] = None
    # B3 三态：PENDING（待人工审批）时为 True；不落正向边、审计留 approval_pending。
    # ⛔ 与 approval_rejected 互斥语义：rejected=硬拒（红线），pending=等人批。
    pending: bool = False
    # J9-P3：敏感项命中（redline_spec.sensitive 子串命中）——非硬拒，强制人工在环。
    sensitive_hits: Tuple[str, ...] = ()
    # J8（2026-10-10）：PENDING 裁定的冻结留痕 —— 回显的真相源。
    # ⛔ 契约（resume 铁律 1「冻结裁定」）：批准后续跑**不重算**，故 PENDING 时
    #    审计 payload 的裁定字段（reason / requires_human）必须在进入 resume 前冻结，
    #    否则 RESUMED 事件回显的就不是审批人当时看到的裁定（"批的是甲、回显的是乙"）。
    #    零值默认 ⇒ 旧快照重建/旧版本兼容（未冻结即 None/False），后端版本无关。
    pending_reason: Optional[str] = None
    pending_requires_human: bool = False


def run_spine(*, context: Mapping, profile, rubric_scores: Mapping[str, float],
              elements: Mapping[str, object],
              persister: Optional[Callable[[SpineResult], object]] = None,
              approval_gate: Optional[DecisionApprovalGate] = None,
              audit_sink: Optional[Callable[[str, Mapping], None]] = None,
              audit_persister: Optional[Callable[[SpineResult, str, Mapping], object]] = None,
              threshold: float = AUTONOMOUS_RELEASE_DEFAULT,
              redline_items: Tuple[str, ...] = (),
              redline_callback: Optional[Callable[..., RedlineVerdict]] = None,
              redline_spec: Optional[RedlineSpec] = None,
              element_cap: bool = False,
              context_factory: Optional[Callable[[Mapping], Mapping]] = None,
              memory_recaller: Optional[Callable[[Mapping], Mapping]] = None) -> SpineResult:
    """按 SPINE_ORDER 执行 S1→S5。

    参数：
      context        触发上下文（S1_context）；空 ⇒ 抛（S1 先于一切）
      profile        TenantProfile（S1_derive 本体分级来源；本包只校验存在，分级器由消费方注入）
      rubric_scores  九尺子 9 键评分（S2_score）
      elements       八要素（S2_score）
      persister      落库回调（S5_persist）；None 不落库（测试/预览）
      approval_gate  决策审批闸（WS3）；None ⇒ 透传（保留既有行为）。裁定驳回 ⇒
                     persisted=False + audit 留痕（embody A 红线优先 / 硬约束先于置信度）
      audit_sink     审计回调 ``audit_sink(event_type, payload)``；审批驳回时落痕（鸭子类型，无 PG 耦合）
      audit_persister  审计轨落库回调（RFE audit-first，2026-10-12 裁定接纳，APS 诉求）：
                      ``audit_persister(result, event_type, payload)``；仅 REJECTED/PENDING
                      分支在 audit_sink 之外调用（APPROVED 走 persister 业务轨，不调用）。
                      payload = audit_sink 基础字段 + `record_kind=AUDIT_RECORD_KIND`
                      + `context_snapshot`（消费方原始上下文）+ `rubric_scores` + `elements`
                      （缓解审计载荷字段缺口，消费方仍可闭包补齐）。
                      ⛔ 语义声明：这是「审计轨」——不可变事实留痕，基座不把它当业务轨
                      正向事实（不产生正向边、不影响 resume 三铁律）；回调抛错 ⇒ 原样
                      上抛（fail-closed：审计优先落库保证不允许静默丢失）。
                      缺省 None ⇒ 既有行为逐字不变（含 audit_sink payload 形状）。
      threshold      自主放行阈值（缺省 0.79）
      redline_items  红线事项目录（来自 profile.redline）
      redline_callback  域红线回调 ``(context, redline_items) -> RedlineVerdict``；
                      提供时替代目录匹配，域逻辑（tier 分档/人工在环）由消费方实现
                      （缺口收敛到 foundation：形态公共，域执行归消费方）
      redline_spec    结构化红线（J9-P3，可选 `RedlineSpec`；与 redline_items/callback 正交并存）：
                      `mutex_top` 命中 ⇒ 并入硬红线轨（redline_hit，既有红线优先语义）；
                      `sensitive` 命中 ⇒ **非硬拒**，强制人工在环：屏蔽自主放行，
                      闸裁 APPROVED 时强制降级 PENDING（闸已裁 REJECTED/PENDING 则尊重）。
                      匹配机制与词表轨同源（context.text 子串匹配，词表须短语级防误杀）。
                      ⛔ 类型闸：仅接受 RedlineSpec（防把词表 list 误传入结构化轨）。
      element_cap     要素缺失封顶（J9-C，默认 False 保持既有行为）：True 时八要素缺失
                      ⇒ 映射尺子按 `ELEMENT_RUBRIC_CAPS` 封顶（`ELEMENT_MISSING_CAP`）
                      后再算 ratio —— 置信度随证据缺失单边下调，来源仍是九尺子 ratio。
      context_factory   装配钩子 ``(seed_context) -> Mapping``；在 S1_context 校验前装配，
                      让 run_spine 可持有装配编排（缺口收敛，仅当消费方要脊柱与组合器对称时需要）
      memory_recaller  记忆召回钩子 ``(context) -> Mapping``（T41：memory 毕业批次二）。
                      在 context_factory 之后、S1 非空校验之前执行——召回需要装配后的
                      subject_id / text，故排在装配之后；默认 None ⇒ 零行为变更。
                      这是「写了能读」的接缝：此前决策只写记忆从不读，记忆因此无用。
                      由 `chiyu_kernel.context.build_memory_recaller(...)` 构造。
    """
    validate_spine_order(SPINE_ORDER)               # 构造期断言：顺序未被重排（铁律 C-A）

    # S1_context：触发上下文必须先于一切；可选装配钩子（缺口收敛：让 run_spine 持有装配编排）
    if context_factory is not None:
        context = context_factory(context)
    # T41：记忆召回注入（装配之后 —— 召回需要装配出的 subject_id / text）
    if memory_recaller is not None:
        context = memory_recaller(context)
    if not context:
        raise DecisionError(
            "ENGINE_FAULT", "S1_context 为空：S1 必须先于一切")
    # S1_derive：本体分级（分级逻辑由消费方注入；内核只验输入齐备）
    if profile is None:
        pass  # 预览/测试允许无 profile；生产由调用方保证注入

    # S2_score：八要素 + 九尺子
    rubric = score_rubric(rubric_scores)
    elem = check_elements(elements)
    # J9-C：要素缺失 ⇒ 映射尺子封顶（opt-in；默认 False 零行为变更）。
    # 封顶在 ratio 之前约束九尺子输入，铁律 C-B（confidence 来源 = ratio）不动。
    if element_cap and elem.missing:
        rubric = score_rubric(cap_rubric_by_elements(rubric_scores, elem.missing))

    # S3_aggregate：confidence 唯一来源 = ratio（铁律 C-B）
    confidence = aggregate_confidence(rubric)

    # S4_redline：链末硬闸门（铁律 C-C）—— 红线命中屏蔽自主放行
    # 缺口收敛：redline_callback 提供时替代目录匹配，域逻辑（tier/人工在环）归消费方
    # J9-P3：redline_spec.mutex_top 并入硬红线轨；sensitive 单列（非硬拒，见下方强制人工）。
    mutex_items: Tuple[str, ...] = ()
    sensitive_items: Tuple[str, ...] = ()
    if redline_spec is not None:
        if not isinstance(redline_spec, RedlineSpec):
            raise TypeError(
                f"redline_spec 须为 RedlineSpec，实为 {type(redline_spec).__name__}"
                "（词表 list/tuple 形态请走 redline_items —— 双轨不得混装）")
        mutex_items = tuple(sorted(redline_spec.mutex_top))
        sensitive_items = tuple(sorted(redline_spec.sensitive))
    if redline_callback is not None:
        verdict = redline_callback(context=context, redline_items=redline_items)
    else:
        verdict = evaluate_redline(context=context, redline_items=redline_items)
    if mutex_items:
        # mutex_top 独立走内置匹配（回调契约零变更：callback 只见到 redline_items）
        mutex_verdict = evaluate_redline(context=context, redline_items=mutex_items)
        verdict = RedlineVerdict(
            hit=verdict.hit or mutex_verdict.hit,
            reasons=tuple(verdict.reasons) + tuple(mutex_verdict.reasons))
    text = str(context.get("text", ""))
    sensitive_hits = tuple(it for it in sensitive_items if it and it in text)
    # 自主放行看**有效红线**（硬红线 ∪ 敏感项）：强制人工在环 ⇒ 不得自主放行。
    autonomous = autonomous_release(
        redline_hit=verdict.hit or bool(sensitive_hits),
        confidence=confidence, threshold=threshold)
    decision_id = str(context.get("decision_id") or f"dec-{id(context)}")

    # S4→S5 审批闸（WS3）：默认透传保留既有行为；注入则按闸裁定。
    # embody A 红线优先 + 硬约束先于置信度（金律26）：红线命中即否决，不因高置信度豁免。
    gate = approval_gate if approval_gate is not None else DecisionPassThroughGate()
    gate_verdict = gate.decide(
        decision_id=decision_id, confidence=confidence, redline_hit=verdict.hit,
        redline_reasons=verdict.reasons, autonomous=autonomous,
        rubric_missing=rubric.missing, elements_missing=elem.missing, threshold=threshold,
    )
    # ⛔ B3 红线优先不可被覆盖（护栏判据放在被调用方，不靠闸自觉）：
    #   注入了闸且红线命中，而闸却裁成 PENDING/APPROVED ⇒ 脊柱强制改判 REJECTED。
    #   仅对"显式注入闸"生效；approval_gate=None 的透传路径保留既有行为
    #   （红线只屏蔽自主放行、不阻断落库，见 test_default_none_preserves_prior_behavior）。
    if (approval_gate is not None and verdict.hit
            and gate_verdict.state is not DecisionVerdictState.REJECTED):
        gate_verdict = replace(
            gate_verdict,
            state=DecisionVerdictState.REJECTED,
            reason=f"红线命中（闸裁定 {gate_verdict.state.value} 被红线优先原则覆盖）",
            requires_human=True,
        )
    # J9-P3：sensitive 命中 ⇒ 强制人工在环 —— 闸裁 APPROVED 时降级 PENDING；
    # 闸已裁 REJECTED（含红线优先改判）/PENDING 则尊重既有裁定（硬红线 > 敏感档）。
    if sensitive_hits and gate_verdict.state is DecisionVerdictState.APPROVED:
        gate_verdict = replace(
            gate_verdict,
            state=DecisionVerdictState.PENDING,
            reason="敏感项命中（" + "、".join(sensitive_hits) + "）：强制人工在环",
            requires_human=True,
        )

    # S5_persist：只写事实不写修饰；落库经注入的 persister（无 PG 也能全绿）
    result = SpineResult(
        decision_id=decision_id, stage_reached="S5_persist", confidence=confidence,
        rubric_missing=rubric.missing, elements_missing=elem.missing,
        redline_hit=verdict.hit, redline_reasons=verdict.reasons, autonomous=autonomous,
        sensitive_hits=sensitive_hits,
    )
    if not gate_verdict.approved:
        # B3 三态分支（方案 Z）：REJECTED 与 PENDING 分流 ——
        #   REJECTED：红线硬拒，记 approval_rejected（既有行为）；
        #   PENDING：待人工审批，不落正向边、审计留 approval_pending（此前被错记为驳回）。
        #   两态均 persisted=False；红线不可被降级为 pending（A 红线优先）。
        if gate_verdict.state is DecisionVerdictState.PENDING:
            result.pending = True
            # J8（2026-10-10）：冻结裁定字段 —— RESUMED 回显的真相源（resume 铁律 1）
            result.pending_reason = gate_verdict.reason
            result.pending_requires_human = gate_verdict.requires_human
            _audit_base = {
                "decision_id": decision_id,
                "approved": False,
                "pending": True,
                "reason": gate_verdict.reason,
                "requires_human": gate_verdict.requires_human,
                "redline_hit": verdict.hit,
                "sensitive_hits": list(sensitive_hits),
                "confidence": confidence,
            }
            if audit_sink is not None:
                audit_sink(AUDIT_EVENT_APPROVAL_PENDING, dict(_audit_base))
            if audit_persister is not None:
                # RFE audit-first：审计轨落库（基础字段 + 扩充载荷），APPROVED 不走此轨
                audit_persister(result, AUDIT_EVENT_APPROVAL_PENDING, {
                    **_audit_base,
                    "record_kind": AUDIT_RECORD_KIND,
                    "context_snapshot": dict(context),
                    "rubric_scores": dict(rubric_scores),
                    "elements": dict(elements),
                })
            return result
        # REJECTED（含红线）：不自动落库 + 审计留痕（persisted 保持 False）
        result.approval_rejected = gate_verdict.reason
        _audit_base = {
            "decision_id": decision_id,
            "approved": False,
            "reason": gate_verdict.reason,
            "requires_human": gate_verdict.requires_human,
            "redline_hit": verdict.hit,
            "sensitive_hits": list(sensitive_hits),
            "confidence": confidence,
        }
        if audit_sink is not None:
            audit_sink(AUDIT_EVENT_APPROVAL_REJECTED, dict(_audit_base))
        if audit_persister is not None:
            # RFE audit-first：审计轨落库（基础字段 + 扩充载荷），APPROVED 不走此轨
            audit_persister(result, AUDIT_EVENT_APPROVAL_REJECTED, {
                **_audit_base,
                "record_kind": AUDIT_RECORD_KIND,
                "context_snapshot": dict(context),
                "rubric_scores": dict(rubric_scores),
                "elements": dict(elements),
            })
        return result
    if persister is not None:
        result.persisted = bool(persister(result))
    return result


def resume_spine(result: SpineResult, *,
                 persister: Optional[Callable[[SpineResult], object]] = None,
                 audit_sink: Optional[Callable[[str, Mapping], None]] = None,
                 approval_ref: str = "",
                 resume_evidence: Optional[Mapping[str, object]] = None) -> SpineResult:
    """G3 方案①：PENDING 批准后的**续跑入口** —— 只补 S5_persist，不重跑 S1–S4。

    ⛔ 契约（"批的是甲、落的是乙"的根治，enterprise G3 诉求）：
      1. **冻结裁定**：不重算 confidence、不重判红线、不询问任何闸、不改任何
         裁定字段 —— 审批人当时看到什么裁定，落库的就是什么。
         （若治理上需要按新红线重评，应取消原决策并重新走 run_spine，而非 resume。）
      2. **只接受 PENDING**：`result.pending` 不为真 ⇒ ValueError。
         REJECTED 不得经 resume 复活（红线硬拒是终态）；APPROVED 且未落库的
         场景不存在（run_spine 中 APPROVED 即已落库或无 persister，消费方重调
         run_spine 不在此列）。
      3. **幂等**：`result.persisted` 已为 True ⇒ 原样返回，不重复落库、不留痕。
      4. **审计**：留 `AUDIT_EVENT_APPROVAL_RESUMED` 痕（含 approval_ref 可溯源）。
      5. persister=None ⇒ 只留审计不落库（与 run_spine 同语义，预览/测试友好）。
      6. **⛔ P-3（D4）HITL 证据结构保证（无 approve 不可生效）**：`resume_evidence`
         必填（breaking，T81）。须为含 `RESUME_EVIDENCE_FIELDS` 三键
         （resume_principal / resumed_at / basis）的 payload；入口强制
         ``assert_hitl_evidence(resume_evidence, aliases=RESUME_EVIDENCE_FIELDS)``，
         缺或不足即抛 `HITLEvidenceError` 拒续跑（落 `approval_resumed` 审计失败态）。
         三键随审计 payload 同链可追（APS P0-B 收口：PENDING 放行证据与决策审计同源）。
    """
    if not getattr(result, "pending", False):
        raise DecisionError(
            "ENGINE_FAULT",
            f"resume_spine 只接受 PENDING 裁定（decision_id={result.decision_id!r}"
            f" pending={result.pending}，approval_rejected={result.approval_rejected!r}）。"
            "REJECTED 是红线终态不得复活；非 PENDING 结果请走 run_spine 重评。")
    if result.persisted:
        return result                      # 幂等：已落库不重复
    # ⛔ P-3（D4）：resume 入口 HITL 证据结构保证（无 approve 不可生效）。
    #   结构保证点：缺 resume_evidence 或三键不全 ⇒ 拒续跑，绝不静默放行。
    if resume_evidence is None:
        if audit_sink is not None:
            audit_sink(AUDIT_EVENT_APPROVAL_RESUMED, {
                "decision_id": result.decision_id,
                "approval_ref": approval_ref,
            })
        raise HITLEvidenceError(
            f"resume_spine 缺 resume_evidence（decision_id={result.decision_id!r}）："
            "PENDING 放行须带 HITL 证据三件套（RESUME_EVIDENCE_FIELDS="
            f"{RESUME_EVIDENCE_FIELDS!r}），无 approve 不可生效（结构保证非约定）")
    assert_hitl_evidence(resume_evidence, aliases=RESUME_EVIDENCE_FIELDS)
    if persister is not None:
        result.persisted = bool(persister(result))
    if audit_sink is not None:
        audit_sink(AUDIT_EVENT_APPROVAL_RESUMED, {
            "decision_id": result.decision_id,
            "approval_ref": approval_ref,
            "confidence": result.confidence,
            "autonomous": result.autonomous,
            "persisted": result.persisted,
            # J8（2026-10-10）：「批的是甲、回显的是乙」根治 —— 回显 PENDING 裁定冻结字段。
            #   reason / requires_human 来自 run_spine PENDING 分支冻结值（真相源），
            #   ⛔ 绝不重算；redline_hit 为决策本身红线态（审批人当时看到的样子）。
            "reason": result.pending_reason,
            "requires_human": result.pending_requires_human,
            "redline_hit": result.redline_hit,
            # P-3（D4）：resume 证据三键入审计链（与决策审计同链可追，APS P0-B 收口）
            "resume_principal": resume_evidence.get("resume_principal"),
            "resumed_at": resume_evidence.get("resumed_at"),
            "basis": resume_evidence.get("basis"),
        })
    return result
