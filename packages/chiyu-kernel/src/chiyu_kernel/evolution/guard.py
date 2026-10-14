"""只读护栏（G2 / G3）的**可执行形式**。

⛔ 为什么本模块不重复实现 G1
────────────────────────────
G1（放宽自主权永不自动）的判据需要参数规格，已在 `knob.is_forbidden_change` 落地。
这里再写一份就是第二份判据表——本项目因"双份清单"出过多次同族事故。
故本模块只承载**不依赖参数规格**的两条：红线挂起（G2）与只读路径（G3）。

⛔ 为什么这些函数不接受"豁免"入参
──────────────────────────────────
追认记录（设计稿 §12.7）写明：**护栏任一被绕过 ⇒ 追认自动失效**。
一个 allow_override=True 的参数就等于给绕过留一个合法入口，而调用那一步
看起来只是"传了个参数"。故只读前缀不可配置、不可豁免。
"""
from __future__ import annotations
from chiyu_kernel.errors import KernelError

from typing import List, Sequence, Tuple

from chiyu_kernel.contract import BASELINE_SKILL_PREFIX, META_REDLINES

# G3：自主写入通道对这些前缀**物理只读**（不可配置、不可豁免）
READONLY_PATH_PREFIXES: Tuple[str, ...] = (
    "chiyu_kernel.contract",                        # L0 契约（改它 = 改验证自己的标尺）
    f"skills/{BASELINE_SKILL_PREFIX}",              # 基线方法论目录
)


class GuardViolation(KernelError):
    code = "CONTRACT_VIOLATION"
    """护栏命中 ⇒ 抛。挂起是调用方的处置，不是本模块的静默分支。"""


def assert_writable(path: str) -> str:
    """G3：写入前判据。命中只读前缀 ⇒ 抛。"""
    p = (path or "").strip()
    if not p:
        raise GuardViolation("写入路径为空 ⇒ 拒绝（空路径无法判定归属）")
    for pre in READONLY_PATH_PREFIXES:
        if p.startswith(pre):
            raise GuardViolation(
                f"G3：{p!r} 属只读路径（{pre}）⇒ 自主通道禁写"
                "（绕过即 §12.7 追认失效）")
    return p


def assert_not_baseline_skill(fq_name: str) -> str:
    """G3：产物命名空间判据。"""
    n = (fq_name or "").strip()
    if n.startswith(BASELINE_SKILL_PREFIX):
        raise GuardViolation(
            f"G3：{n!r} 属基线命名空间 ⇒ 自生成产物禁写此处"
            "（基线不得新增/删除/重编号）")
    return n


def g2_suspend_on_redline(redline_hit: bool) -> bool:
    """G2：红线命中 ⇒ 挂起。

    其"强制人工"由**次日报告批量处置**满足（异步人工，非在线阻塞）——
    以异步形式保留红线条款的结构，同时满足夜间无人审批的实际诉求。
    """
    return bool(redline_hit)


def meta_redline_hits(actions: Sequence[str]) -> List[str]:
    """从一批自变动作里检出元红线命中项，供次日报告直接列出。"""
    return [a for a in actions if a in META_REDLINES]


__all__ = ["GuardViolation", "READONLY_PATH_PREFIXES", "assert_writable",
           "assert_not_baseline_skill", "g2_suspend_on_redline", "meta_redline_hits"]
