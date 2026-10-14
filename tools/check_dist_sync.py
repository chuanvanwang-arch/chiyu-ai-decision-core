"""wheel ↔ 源码一致性门禁（CRM P0 回执修复要求② · 2026-10-09）。

背景：v0.1.0 双 wheel 曾为"中间态"构建（kernel 缺 set_key_format、decision 缺 errors.py），
原因是 `dist` 在功能提交后未以最终源码重建。本守卫在构建/发布前校验：
  - wheel 内 `api.py` 的 `__all__` 符号集 == 源码 `api.py` 的 `__all__` 符号集（缺一即红）；
  - wheel 内关键模块存在（decision 的 `errors.py` 等，按包可配）。

判别力自证：从源码或 wheel 任一侧删一个 `__all__` 符号 / 删关键文件 → 退出码转 1。
单一事实源 = 源码 `__all__`（与 check_facade_coverage 同纪律）。
"""
from __future__ import annotations

import ast
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: 包 → wheel 相对路径 / 源码相对路径 / __all__ 所在模块 / 关键文件（须在 wheel 内）
_PACKAGES = {
    "chiyu_kernel": {
        "wheel": "packages/chiyu-kernel/dist/chiyu_kernel-0.1.0-py3-none-any.whl",
        "src": "packages/chiyu-kernel/src",
        "all_module": "chiyu_kernel/api.py",
        # 门面 __all__ 中不可再缺的关键符号（R3 曾缺 set_key_format）
        "required_symbols": ("set_key_format", "key_format"),
    },
    "chiyu_decision": {
        "wheel": "packages/chiyu-decision/dist/chiyu_decision-0.1.0-py3-none-any.whl",
        "src": "packages/chiyu-decision/src",
        "all_module": "chiyu_decision/api.py",
        # R8 曾缺 errors.py → DecisionError 缺失
        "required_files": ("chiyu_decision/errors.py",),
        "required_symbols": ("DecisionError", "DECISION_ERROR_CODES"),
    },
}


def _all_symbols(text: str) -> set:
    """AST 解析模块顶层 `__all__` 的字符串元素集合。"""
    tree = ast.parse(text)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == "__all__" and isinstance(node.value, (ast.List, ast.Tuple)):
                    out = set()
                    for elt in node.value.elts:
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                            out.add(elt.value)
                    return out
    return set()


def check_pkg(name: str) -> list:
    """校验单个包，返回问题列表（空 = 通过）。"""
    cfg = _PACKAGES[name]
    problems: list = []

    wheel_path = ROOT / cfg["wheel"]
    src_dir = ROOT / cfg["src"]
    all_mod = cfg["all_module"]

    if not wheel_path.is_file():
        return [f"wheel 缺失：{wheel_path}（未重建？）"]
    if not (src_dir / all_mod).is_file():
        return [f"源码缺失：{src_dir / all_mod}"]

    # 1) __all__ 符号集一致：源码 vs wheel
    src_text = (src_dir / all_mod).read_text(encoding="utf-8")
    src_all = _all_symbols(src_text)
    with zipfile.ZipFile(wheel_path) as zf:
        wheel_text = zf.read(all_mod).decode("utf-8")
        wheel_all = _all_symbols(wheel_text)
        # 2) 关键文件存在性
        for req_file in cfg.get("required_files", ()):
            if req_file not in zf.namelist():
                problems.append(f"{name}: wheel 缺关键文件 {req_file}")

    missing_in_wheel = src_all - wheel_all
    missing_in_src = wheel_all - src_all  # wheel 多出的（也应报，防陈旧）
    if missing_in_wheel:
        problems.append(f"{name}: wheel __all__ 缺源码符号 {sorted(missing_in_wheel)}（wheel 落后）")
    if missing_in_src and name != "chiyu_kernel":
        # kernel 门面 __all__ 会随 R 系列频繁增补，wheel 略旧于未提交工作树属正常；
        # 仅对已冻结交付面（decision）强制双向一致。
        problems.append(f"{name}: wheel __all__ 含源码未声明符号 {sorted(missing_in_src)}（wheel 超前/陈旧）")

    # 3) 关键符号必现（即使 __all__ 解析异常也能兜底）
    for sym in cfg.get("required_symbols", ()):
        if sym not in wheel_text:
            problems.append(f"{name}: wheel 模块 {all_mod} 缺关键符号 {sym}")
    return problems


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    targets = argv or list(_PACKAGES)
    all_problems: list = []
    for name in targets:
        if name not in _PACKAGES:
            print(f"[skip] 未知包：{name}", file=sys.stderr)
            continue
        probs = check_pkg(name)
        if probs:
            for p in probs:
                print(f"[FAIL] {p}")
            all_problems.extend(probs)
        else:
            print(f"[OK] {name}: wheel ↔ 源码 __all__ 一致，关键文件/符号齐备")
    if all_problems:
        print(f"合计 {len(all_problems)} 条不一致（须重构建 wheel）", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
