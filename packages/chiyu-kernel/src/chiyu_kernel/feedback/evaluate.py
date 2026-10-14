"""加权评估闸门（B2/B7）—— 纯函数，零 IO。

上迁源：APS ``platform/feedback_loop.py`` 的 ``EvalItem`` / ``EvaluatorSpec`` /
``evaluate`` / ``_var_names`` / ``_safe_eval``（``evolution_feed`` 的安全求值）。

三条纪律（有守卫测试）：
    · **B7 资格断言**：判据所需变量缺失 ⇒ 该条 ``qualified=False``，整体结论
      ``undecidable``——"不可判"是独立第三态，绝不并入通过；
    · **fail-closed 求值**：表达式求值失败（除零/类型不符）⇒ 该条 ``passed=False``，
      绝不让"算不出的判据"偷偷算过；
    · **安全子集**：只允许算术/比较/布尔/成员运算，禁 Call/Attribute/Subscript
      （``ExpressionError``），防把评估表达式当任意代码执行面。
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from chiyu_kernel.contract.feedback_loop import (
    DEFAULT_AUTO_PASS,
    DEFAULT_HUMAN_REVIEW,
    EVAL_VERDICT_PASS,
    EVAL_VERDICT_REJECT,
    EVAL_VERDICT_REVIEW,
    EVAL_VERDICT_UNDECIDABLE,
    ExpressionError,
)

__all__ = [
    "EvalItem", "EvaluatorSpec", "expression_variables", "safe_eval", "evaluate",
]


@dataclass(frozen=True)
class EvalItem:
    """单条加权判据。``pass_rule`` 为白名单表达式（变量来自 ``inputs``）。"""

    name: str
    weight: int
    pass_rule: str


@dataclass(frozen=True)
class EvaluatorSpec:
    """评估器：判据集 + 三档阈值 + verdict→action 权利映射。"""

    name: str
    loop: str
    items: Tuple[EvalItem, ...]
    auto_pass: int = DEFAULT_AUTO_PASS
    human_review: int = DEFAULT_HUMAN_REVIEW
    actions: Mapping[str, str] = field(default_factory=dict)


def expression_variables(expr: str) -> Tuple[str, ...]:
    """从表达式中抽取变量名（供 B7 资格断言用；语法错误 ⇒ ``ExpressionError``）。"""
    try:
        tree = ast.parse(str(expr), mode="eval")
    except (SyntaxError, ValueError) as exc:
        raise ExpressionError(f"表达式语法错误：{expr!r}（{exc}）") from exc
    return tuple(sorted(
        n.id for n in ast.walk(tree) if isinstance(n, ast.Name)
    ))


_ALLOWED_BINOPS = (
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
)
_ALLOWED_CMPOPS = (
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn,
)


def _eval_node(node: ast.AST, variables: Mapping[str, Any]) -> Any:
    """白名单 AST 求值。任何不在子集内的节点 ⇒ ``ExpressionError``（fail-closed）。"""
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, variables)
    if isinstance(node, ast.Constant):
        if node.value is None or isinstance(node.value, (bool, int, float, str)):
            return node.value
        raise ExpressionError(f"不允许的常量类型：{type(node.value).__name__}")
    if isinstance(node, ast.Name):
        if node.id not in variables:
            raise ExpressionError(f"表达式引用未提供变量：{node.id!r}")
        return variables[node.id]
    if isinstance(node, ast.BoolOp) and isinstance(node.op, (ast.And, ast.Or)):
        values = [_eval_node(v, variables) for v in node.values]
        if isinstance(node.op, ast.And):
            out = True
            for v in values:
                out = out and bool(v)
            return out
        out = False
        for v in values:
            out = out or bool(v)
        return out
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.Not, ast.USub, ast.UAdd)):
        operand = _eval_node(node.operand, variables)
        if isinstance(node.op, ast.Not):
            return not operand
        if isinstance(node.op, ast.USub):
            return -operand
        return +operand
    if isinstance(node, ast.BinOp) and isinstance(node.op, _ALLOWED_BINOPS):
        left = _eval_node(node.left, variables)
        right = _eval_node(node.right, variables)
        try:
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                return left / right
            if isinstance(node.op, ast.FloorDiv):
                return left // right
            if isinstance(node.op, ast.Mod):
                return left % right
            return left ** right
        except (ArithmeticError, TypeError) as exc:
            raise ExpressionError(f"算术求值失败：{exc}") from exc
    if isinstance(node, ast.Compare):
        left = _eval_node(node.left, variables)
        for op, comparator in zip(node.ops, node.comparators):
            if not isinstance(op, _ALLOWED_CMPOPS):
                raise ExpressionError(f"不允许的比较运算：{type(op).__name__}")
            right = _eval_node(comparator, variables)
            try:
                if isinstance(op, ast.Eq):
                    ok = left == right
                elif isinstance(op, ast.NotEq):
                    ok = left != right
                elif isinstance(op, ast.Lt):
                    ok = left < right
                elif isinstance(op, ast.LtE):
                    ok = left <= right
                elif isinstance(op, ast.Gt):
                    ok = left > right
                elif isinstance(op, ast.GtE):
                    ok = left >= right
                elif isinstance(op, ast.In):
                    ok = left in right
                else:
                    ok = left not in right
            except (TypeError, ArithmeticError) as exc:
                raise ExpressionError(f"比较求值失败：{exc}") from exc
            if not ok:
                return False
        return True
    if isinstance(node, (ast.Tuple, ast.List)):
        return [_eval_node(elt, variables) for elt in node.elts]
    raise ExpressionError(
        f"表达式含不在安全子集内的节点：{type(node).__name__}"
        "（禁 Call/Attribute/Subscript 等）"
    )


def safe_eval(expr: str, variables: Mapping[str, Any]) -> bool:
    """在白名单子集内求值表达式（返回布尔化结果）。"""
    try:
        tree = ast.parse(str(expr), mode="eval")
    except (SyntaxError, ValueError) as exc:
        raise ExpressionError(f"表达式语法错误：{expr!r}（{exc}）") from exc
    return bool(_eval_node(tree, variables))


def evaluate(spec: EvaluatorSpec, inputs: Mapping[str, Any]) -> Dict[str, Any]:
    """加权评估 + 三档阈值 + 资格断言（B2/B7）。

    返回结构与 APS ``feedback_loop.evaluate`` 一致（parity）：
    ``score`` = Σ(weight·passed)/Σweight×100，仅**合格**条目计入分母；
    任一条目资格缺失 ⇒ ``verdict="undecidable"``（绝不被阈值吞掉）。
    """
    item_results: List[Dict[str, Any]] = []
    total_w = 0
    passed_w = 0
    undecidable = False
    for it in spec.items:
        needed = set(expression_variables(it.pass_rule))
        missing = needed - set(inputs.keys())
        if missing:
            # ★ B7：资格缺失 ⇒ 明确"不可判"，不假装评估通过
            item_results.append({
                "name": it.name, "qualified": False,
                "missing_vars": sorted(missing), "passed": False,
            })
            undecidable = True
            continue
        try:
            ok = bool(safe_eval(it.pass_rule, dict(inputs)))
        except ExpressionError:
            ok = False  # fail-closed：算不出的判据不得算过
        item_results.append({"name": it.name, "qualified": True, "passed": ok})
        total_w += it.weight
        passed_w += it.weight * int(ok)
    score = round(100.0 * passed_w / total_w, 2) if total_w else 0.0
    if undecidable:
        verdict = EVAL_VERDICT_UNDECIDABLE
    elif score >= spec.auto_pass:
        verdict = EVAL_VERDICT_PASS
    elif score >= spec.human_review:
        verdict = EVAL_VERDICT_REVIEW
    else:
        verdict = EVAL_VERDICT_REJECT
    actions = dict(spec.actions or {})
    return {
        "evaluator": spec.name,
        "loop": spec.loop,
        "score": score,
        "verdict": verdict,
        "undecidable": undecidable,
        "items": item_results,
        "action": actions.get(verdict, actions.get("default", "")),
    }
