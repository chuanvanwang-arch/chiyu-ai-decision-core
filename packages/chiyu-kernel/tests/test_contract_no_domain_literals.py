"""契约层零领域字面量守卫（T1 准入闸）。

判据：`contract/` 下所有 .py 的**字符串常量**不得命中黑名单。
为什么必须脚本化：文档条款不会在有人写下 `PARTICLE_TYPES = ("cluster",)` 时变红，
这个测试会。若不守，内核装到第二个项目就会带着第一个项目的领域模型。

⛔ 两条实现要点（都是防假绿/假红）
──────────────────────────────
① ascii 词用 `\\b` **整词匹配**，非 ascii 词用子串：
   子串匹配会把 `snake_case` 里的 `case`、`replacement` 里的 `place` 判成命中，
   守卫天天误报 ⇒ 被绕过。整词匹配仍能抓到 `("cluster", "place")` 这种真命中。
② 只检查 `ast.Constant` 的字符串值，**豁免 docstring**：
   docstring 里为了说明「为什么不许出现某个领域词」而写出该词是必要的。
③ 反向自证：若契约目录不存在或文件数 < 6，本模块**主动失败**——
   否则 `glob` 返回空会把参数化测试变成"零用例静默通过"（经典假绿）。
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest

PKG = Path(__file__).resolve().parents[1]              # packages/chiyu-kernel/
REPO = Path(__file__).resolve().parents[3]             # chiyu-foundation/
CONTRACT = PKG / "src" / "chiyu_kernel" / "contract"
DENYLIST = REPO / "config" / "domain-literal-denylist.json"

MIN_CONTRACT_MODULES = 6


def _deny_terms() -> list[str]:
    data = json.loads(DENYLIST.read_text(encoding="utf-8"))
    terms: list[str] = []
    for key, values in data.items():
        if key.startswith("_"):
            continue
        terms.extend(values)
    return sorted(set(terms))


def _docstring_nodes(tree: ast.AST) -> set[int]:
    """收集全部 docstring 的节点 id（这些字符串豁免）。"""
    out: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                if isinstance(body[0].value.value, str):
                    out.add(id(body[0].value))
    return out


def _string_constants(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    exempt = _docstring_nodes(tree)
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) in exempt:
                continue
            found.append((node.lineno, node.value))
    return found


def _matches(value: str, term: str) -> bool:
    if term.isascii():
        return re.search(rf"\b{re.escape(term)}\b", value, flags=re.IGNORECASE) is not None
    return term in value


def test_contract_tree_is_present_and_non_trivial():
    """防假绿：契约目录缺失/文件过少 ⇒ 参数化测试会零用例静默通过。"""
    assert CONTRACT.is_dir(), f"契约目录不存在：{CONTRACT}"
    n = len(list(CONTRACT.glob("*.py")))
    assert n >= MIN_CONTRACT_MODULES, (
        f"契约模块仅 {n} 个（应 ≥ {MIN_CONTRACT_MODULES}）⇒ 本守卫已失去覆盖面"
    )


@pytest.mark.parametrize("path", sorted(CONTRACT.glob("*.py")), ids=lambda p: p.name)
def test_contract_has_no_domain_literals(path: Path):
    terms = _deny_terms()
    hits: list[str] = []
    for lineno, value in _string_constants(path):
        for t in terms:
            if _matches(value, t):
                hits.append(f"{path.name}:{lineno} 命中领域词 {t!r}（{value!r}）")
    assert not hits, (
        "契约层出现领域字面量 ⇒ 底座退化为单域框架：\n  " + "\n  ".join(hits)
    )


def test_denylist_is_not_empty_and_has_shape():
    """反向自证：黑名单为空会让上面的测试永远绿（经典假绿）。"""
    terms = _deny_terms()
    assert len(terms) >= 15, f"黑名单过小（{len(terms)}），守卫已失去鉴别力"
    assert "cluster" in terms and "slab" in terms


def test_matcher_whole_word_boundary_avoids_false_positive():
    """判别力自证的**反面**：整词匹配不得把 snake_case 判成命中 case。"""
    assert _matches("snake_case", "case") is False
    assert _matches("replacement", "place") is False
    assert _matches("cluster", "cluster") is True
    assert _matches("partOf: cluster", "cluster") is True


def test_guard_catches_injected_literal(tmp_path):
    """突变自证：造一个含领域字面量的契约模块于**CONTRACT 之外**的临时目录，
    断言守卫会红。

    ⛔ 为何不能用 CONTRACT / \"_tmp_bad_contract.py\"（既有版本，已证有害）：
       临时文件放 CONTRACT 目录 ⇒ 被 `CONTRACT.glob(\"*.py\")` 收集到 ⇒
       下一次 pytest 进程（收集期早于运行期）把该残留纳入参数化
       `test_contract_has_no_domain_literals[_tmp_bad_contract.py]` ⇒
       即使 finally 已删除，上次进程被中断（如管道 SIGPIPE）时残留仍会在
       下次收集触发假红。用 tmp_path（pytest 自动清理、不在 CONTRACT 下）消除该污染。
    """
    bad = tmp_path / "bad.py"                      # 位于测试临时目录，非 CONTRACT
    bad.write_text('PARTICLE_TYPES = ("cluster", "place")\n', encoding="utf-8")
    terms = _deny_terms()
    hits = [
        (ln, v) for ln, v in _string_constants(bad)
        if any(_matches(v, t) for t in terms)
    ]
    assert hits, "守卫对注入的领域字面量无反应 ⇒ 无鉴别力"
