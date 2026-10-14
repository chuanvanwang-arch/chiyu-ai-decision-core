"""SKILL 草稿闸（自变对象②）—— 命名空间隔离 + 所调动作必须已注册。

⛔ 为什么基线前缀写死而不接受覆盖
────────────────────────────────
基线方法论是审计可复现的前提（不得新增/删除/重编号）。若命名空间前缀可配，
"改一下配置"就能绕过该约束——而这种绕过每一步单独看都是合法的配置变更。

⛔ 为什么"未声明所调动作"要判拒绝而不是放行
──────────────────────────────────────────
空草稿若判通过，则任何半成品草稿都能晋升。校验必须**默认拒绝**：
没有可校验对象 = 不具备可校验性，而不是"没有错"。
"""
from __future__ import annotations
from chiyu_kernel.errors import KernelError

from dataclasses import dataclass
from typing import Iterable, List, Tuple

from chiyu_kernel.contract import BASELINE_SKILL_PREFIX, VERDICT_PASS, VERDICT_REJECT


class SkillDraftError(KernelError):
    code = "CONTRACT_VIOLATION"
    """草稿违规 ⇒ 抛（草稿绝不静默生效）。"""


@dataclass(frozen=True)
class SkillDraft:
    name: str
    calls_actions: Tuple[str, ...] = ()
    status: str = "draft"          # draft → validated（晋升后仍需交付闸）
    namespace: str = "method"      # ⛔ 默认新命名空间，非基线

    def fq_name(self) -> str:
        return f"{self.namespace}-{self.name}"

    def is_baseline(self) -> bool:
        return self.fq_name().startswith(BASELINE_SKILL_PREFIX)


def validate_draft(
    draft: SkillDraft,
    *,
    action_names: Iterable[str],
    allowed_namespaces: Iterable[str] = ("method", "domain"),
) -> Tuple[str, List[str]]:
    """返回 (verdict, errors)。errors 为空且 verdict=pass 才允许继续。"""
    errs: List[str] = []
    if draft.is_baseline():
        errs.append(
            f"⛔ 自生成产物不得写入基线命名空间 {BASELINE_SKILL_PREFIX}*"
            "（基线不得新增/删除/重编号）")
    allowed = tuple(allowed_namespaces)
    if allowed and draft.namespace not in allowed:
        errs.append(f"命名空间 {draft.namespace!r} 不在允许集 {allowed} 内")
    known = set(action_names)
    for a in draft.calls_actions:
        if a not in known:
            errs.append(f"所调动作未注册：{a!r}（草稿不得引用不存在的动作）")
    if not draft.calls_actions:
        errs.append("草稿未声明所调动作 ⇒ 无可校验对象，按拒绝处理")
    if not (draft.name or "").strip():
        errs.append("草稿名为空 ⇒ 拒绝")
    return (VERDICT_REJECT if errs else VERDICT_PASS), errs


def promote(draft: SkillDraft, *, verdict: str) -> SkillDraft:
    """草稿晋升。**verdict != pass ⇒ 抛**（"草稿绝不自动生效"的机器形式）。"""
    if verdict != VERDICT_PASS:
        raise SkillDraftError(f"草稿 {draft.fq_name()!r} 未通过校验 ⇒ 禁止晋升")
    if draft.status != "draft":
        raise SkillDraftError(f"仅 draft 可晋升（当前 {draft.status!r}）")
    return SkillDraft(name=draft.name, calls_actions=draft.calls_actions,
                      status="validated", namespace=draft.namespace)


__all__ = ["SkillDraftError", "SkillDraft", "validate_draft", "promote"]
