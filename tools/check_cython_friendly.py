"""内核「可编译友好」静态检查（设计 §6.1 五条规范的可执行形式）。

为什么是脚本而不是文档条款：
    文档条款不会在有人写下 `type("X", (), {})` 时变红，这个脚本会，
    且它可被突变证伪（tools/tests/test_check_cython_friendly.py）。

检查项：
    C1 禁运行时造类：`type(...)` 三参数调用、`types.new_class`、`__build_class__`
    C2 禁 **kwargs 动态派发：任何函数的形参含 `**kwargs`
       （理由：Cython 无法为动态关键字派发生成静态绑定，编译期直接失败）
    C3 禁反射取用：`importlib` 导入、`getattr(obj, <变量>)`
       （`getattr(obj, "常量名")` 允许 —— 它是静态可解析的）
    C4 契约静态声明：`contract/` 下**定义了类**的模块必须 import dataclasses / pydantic
    C5 退出码即闸门：0=通过 / 1=有违规 / 2=用法错误

⛔ C4 的判据修正（对设计稿字面的精确化）
──────────────────────────────────────
设计稿字面是「`contract/` 下**每个**模块必须 import dataclasses 或 pydantic」。
按字面执行会把两类**合法**模块误判为违规：
    ① 纯 re-export 模块（`contract/__init__.py`）—— 它只汇总导出，没有类；
    ② 纯常量模块（`contract/memory.py` / `contract/audit.py`）—— 它们比 dataclass
       **更静态**（只有字面量常量），却因没 import dataclasses 被判违规。
C4 的真靶子是「用运行时手段造类 / 动态声明契约」，故判据改为：
    **含 ClassDef 且未 import dataclasses/pydantic ⇒ 违规**；无 ClassDef ⇒ 天然合规。
该判据仍可被突变证伪（见 tools/tests/test_check_cython_friendly.py 的 C4 两条用例）。

用法：
    python tools/check_cython_friendly.py packages/
    python tools/check_cython_friendly.py --json packages/
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Iterable

CODE_C1 = "C1-runtime-class"
CODE_C2 = "C2-kwargs-dispatch"
CODE_C3 = "C3-reflection"
CODE_C4 = "C4-contract-not-static"

# C3 豁免：加载动作发生在 tools/ 内的脚本需要反射
_REFLECTION_ALLOWLIST: tuple[str, ...] = ("tools/",)


class Finding(dict):
    """违规记录：{code, file, line, detail}。"""


def _rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def check_file(path: Path, root: Path) -> list[Finding]:
    findings: list[Finding] = []
    rel = _rel(path, root)
    allow_reflection = any(rel.startswith(p) for p in _REFLECTION_ALLOWLIST)

    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        return [Finding(code="SYNTAX", file=rel, line=exc.lineno or 0, detail=str(exc))]

    imports_dataclass = False
    imports_pydantic = False
    defines_class = False

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name == "dataclasses":
                    imports_dataclass = True
                if a.name.startswith("pydantic"):
                    imports_pydantic = True
                if a.name == "importlib" and not allow_reflection:
                    findings.append(Finding(
                        code=CODE_C3, file=rel, line=node.lineno,
                        detail="import importlib（反射式取用，Cython 不可静态解析）"))
        elif isinstance(node, ast.ImportFrom):
            if node.module == "dataclasses":
                imports_dataclass = True
            if (node.module or "").startswith("pydantic"):
                imports_pydantic = True
            if node.module == "importlib" and not allow_reflection:
                findings.append(Finding(
                    code=CODE_C3, file=rel, line=node.lineno,
                    detail="from importlib import ...（反射式取用）"))
        elif isinstance(node, ast.ClassDef):
            defines_class = True

        # C1 运行时造类
        if isinstance(node, ast.Call):
            fn = node.func
            if isinstance(fn, ast.Name) and fn.id == "type" and len(node.args) >= 3:
                findings.append(Finding(
                    code=CODE_C1, file=rel, line=node.lineno,
                    detail="type(name, bases, dict) 运行时造类"))
            if isinstance(fn, ast.Name) and fn.id == "__build_class__":
                findings.append(Finding(
                    code=CODE_C1, file=rel, line=node.lineno,
                    detail="__build_class__ 运行时造类"))
            if (isinstance(fn, ast.Attribute) and fn.attr == "new_class"
                    and isinstance(fn.value, ast.Name) and fn.value.id == "types"):
                findings.append(Finding(
                    code=CODE_C1, file=rel, line=node.lineno,
                    detail="types.new_class 运行时造类"))
            # C3 getattr 变量名
            if isinstance(fn, ast.Name) and fn.id == "getattr" and len(node.args) >= 2:
                name_arg = node.args[1]
                if not isinstance(name_arg, ast.Constant) and not allow_reflection:
                    findings.append(Finding(
                        code=CODE_C3, file=rel, line=node.lineno,
                        detail="getattr(obj, <变量>) 反射式取用（仅允许字符串常量名）"))

        # C2 **kwargs（⛔ 属性在 node.args.kwarg，不是 node.kwarg）
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            kw = getattr(node.args, "kwarg", None)
            if kw is not None:
                findings.append(Finding(
                    code=CODE_C2, file=rel, line=node.lineno,
                    detail=f"def {node.name}(**{kw.arg}) 动态关键字派发"))

    # C4 契约静态声明（仅当定义了类）
    if "/contract/" in f"/{rel}" and defines_class and not (imports_dataclass or imports_pydantic):
        findings.append(Finding(
            code=CODE_C4, file=rel, line=1,
            detail="契约模块定义了类但未用 dataclasses / pydantic 静态声明"))
    return findings


def scan(paths: Iterable[Path], root: Path) -> list[Finding]:
    out: list[Finding] = []
    for p in paths:
        if p.is_dir():
            for f in sorted(p.rglob("*.py")):
                out.extend(check_file(f, root))
        else:
            out.extend(check_file(p, root))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="内核可编译友好检查（设计 §6.1）")
    ap.add_argument("paths", nargs="+", help="待检查的文件或目录")
    ap.add_argument("--root", default=None, help="仓库根（默认取当前目录）")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    args = ap.parse_args(argv)

    targets = [Path(p) for p in args.paths]
    root = Path(args.root) if args.root else Path.cwd()
    findings = scan(targets, root)

    if args.json:
        print(json.dumps([dict(f) for f in findings], ensure_ascii=False, indent=2))
    else:
        if not findings:
            print(f"OK: 可编译友好检查通过（{len(targets)} 个目标）")
        for f in findings:
            print(f"[{f['code']}] {f['file']}:{f['line']} {f['detail']}")
        print(f"\n合计违规 {len(findings)} 条")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
