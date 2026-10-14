"""影子重放 —— 应用前用历史样本 dry-run。

⛔ 为什么"无样本"必须判 reject 而不是 pass
──────────────────────────────────────────
没有重放样本的变更就是 blind patch：线上劣化只能靠事后发现。若样本空缺时返回
"通过"，守卫就成了摆设——而夜批**恰好在没攒够样本的那些天**会全量盲改。

⛔ 为什么 formula 必须是同一个可调用对象
──────────────────────────────────────
"语义相近的重写版本"必然在边界上分叉（阈值取等、空值处理、除零），而分叉只会在
线上样本暴露。故重放只接受与运行引擎**同源**的可调用对象，**不接受字符串公式**
——字符串公式必然是重写版本。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, List, Mapping, Sequence

from chiyu_kernel.contract import VERDICT_PASS, VERDICT_REJECT

BASELINE_FIELD = "__expected"


@dataclass(frozen=True)
class ReplayVerdict:
    verdict: str
    checked: int = 0
    mismatches: List[str] = field(default_factory=list)
    reason: str = ""

    @property
    def ok(self) -> bool:
        """⛔ 只认显式 pass：缺 verdict / 异常 / 空样本都不算通过。"""
        return self.verdict == VERDICT_PASS


def shadow_replay(
    samples: Sequence[Mapping[str, Any]],
    formula: Callable[[Mapping[str, Any]], Any],
    new_params: Mapping[str, Any],
    *,
    min_samples: int = 1,
) -> ReplayVerdict:
    """用 `new_params` 代入 `formula` 重算历史样本，与样本自带基线值比对。

    每条样本须含 `__expected`（该样本当时的运行结论）。缺基线的样本**计入失配**
    而非跳过——跳过会让"没有基线"伪装成"全部比对通过"。
    """
    if not callable(formula):
        return ReplayVerdict(
            VERDICT_REJECT, reason="formula 不可调用 ⇒ 拒绝（禁字符串公式）")

    n = len(samples)
    if n < min_samples:
        return ReplayVerdict(
            VERDICT_REJECT, checked=n,
            reason=f"样本量不足（{n} < {min_samples}）⇒ 无重放即 blind patch，拒绝出方")

    bad: List[str] = []
    for i, s in enumerate(samples):
        if BASELINE_FIELD not in s:
            bad.append(f"#{i}: 缺 {BASELINE_FIELD} 基线（不跳过）")
            continue
        payload = {k: v for k, v in s.items() if k != BASELINE_FIELD}
        payload.update(new_params)
        try:
            got = formula(payload)
        except Exception as exc:                     # 异常 ⇒ 保守拒绝（fail-safe）
            bad.append(f"#{i}: 重算异常 {type(exc).__name__}: {exc}")
            continue
        if got != s[BASELINE_FIELD] and not _close(got, s[BASELINE_FIELD]):
            bad.append(f"#{i}: 期望 {s[BASELINE_FIELD]!r} 实得 {got!r}")

    if bad:
        return ReplayVerdict(VERDICT_REJECT, checked=n, mismatches=bad,
                             reason=f"{len(bad)}/{n} 条重放失配")
    return ReplayVerdict(VERDICT_PASS, checked=n)


def _close(a: Any, b: Any, *, tol: float = 1e-9) -> bool:
    """数值容差比较；非数值一律不等（不猜语义）。"""
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return False


__all__ = ["ReplayVerdict", "shadow_replay", "BASELINE_FIELD"]
