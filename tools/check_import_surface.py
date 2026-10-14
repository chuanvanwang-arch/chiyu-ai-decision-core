"""sanctioned import 面门禁（B1 / N2，E1 双向适用）。

⛔ 存在理由（不是风格偏好）：此前"消费方只许 import chiyu_kernel.api 与 contract"
   只写在 docstring 里 ⇒ **违规不报错**，只能靠自觉。实测后果有两处：
     ① APS 被迫 import `chiyu_kernel.store.{conn,dsn,ddl,pg_store}` 四个内部路径；
     ② enterprise 想合规却拿不到 `run_spine`（决策面未成文 ⇒ 不在允许清单）。
   本脚本把"允许清单"变成**可执行门禁**，且**对 foundation 自身同样生效**（E1 双向）。

判定口径（机械，无人工白名单）：
   · 扫描 `packages/{kernel,decision,portal}/src` + `examples/`；
   · **同分发内**导入允许（实现细节，非消费关系）；
   · **跨分发**导入必须命中 SANCTIONED 前缀（相等或为其子树）；
   · `tests/` 与 `packages/chiyu-host` 为**显式豁免**，⛔ 豁免必须在输出中可见
     （静默豁免 = 假绿）。

用法：
    python tools/check_import_surface.py [--root .] [--verbose]
退出码：0=通过；1=存在违规。
"""
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path
from typing import Dict, List, Tuple

#: sanctioned 面（唯一事实源，与 docs/sanctioned-import-surface.md §2 一致）
SANCTIONED: Tuple[str, ...] = (
    "chiyu_kernel.api",
    "chiyu_kernel.contract",
    "chiyu_kernel.approval",
    "chiyu_decision.api",
    "chiyu_portal.api",
)

#: 参与门禁的分发包（跨分发导入才受约束）
DISTS: Tuple[str, ...] = ("chiyu_kernel", "chiyu_decision", "chiyu_portal")

SCAN_ROOTS: Tuple[str, ...] = (
    "packages/chiyu-kernel/src",
    "packages/chiyu-decision/src",
    "packages/chiyu-portal/src",
    "examples",
)

#: ⛔ 显式豁免（必须写明理由；脚本会打印命中数，禁止静默豁免）
EXEMPT_PATHS: Dict[str, str] = {
    "packages/chiyu-host": (
        "该包已于 2026-09-26 标记弃用并并入 chiyu-enterprise；遗留内部 import 随弃用下线，"
        "⛔ 不得新增对该包的跨面依赖"
    ),
}

#: N1 · 易冲突名清单（N1，2026-10-09）—— 会与常见消费方域取值同名/近义的门面符号。
#: 单一事实源指向 `docs/sanctioned-import-surface.md` §「易冲突名清单」；每项给建议用法。
#: 语义：消费方**扁平导入**这些名为**警告级提示**（不阻断），命名空间导入（`api.<name>`）
#: 则不受影响。⛔ 清单非空是门禁判别力前提（空清单 = 提示机制失效，测试判红）。
CONFLICTING_NAMES: Dict[str, str] = {
    "Particle": "与消费方常见的 'Particle' 领域实体同名异义；建议 `import chiyu_kernel.api as api` 后经 `api.Particle` 引用",
    "normalize": "泛用名；建议经命名空间引用，或 `from chiyu_kernel.contract import normalize as kernel_normalize` 显式改名",
    "canonical": "泛用名；建议经 `api.canonical` 引用，避免遮蔽消费方 own canonical 逻辑",
    "LAYERS": "foundation 内部层名集合，与消费方可能的 'LAYERS' 配置同名；建议显式改名或经命名空间引用",
    "ATTR_TYPES": "属性类型枚举，易与消费方 own 属性类型定义撞名；建议显式改名",
    "vector_available": "向量可用性标志（vector_ 前缀已降低撞名率，仍列出以提示）；建议经命名空间引用",
    "get_schema": "取 schema 名，易与消费方 own get_schema 撞名；建议显式改名",
    "get_dsn": "取 DSN，易与消费方 own 配置读取函数撞名；建议显式改名",
    "mask_dsn": "掩码 DSN，易与消费方 own 掩码工具撞名；建议显式改名",
    # H1（enterprise 2026-10-09）：跨仓同名异义实锤——enterprise `scenario/loader.py:269`
    # 亦有 `register_scenario(name, factory)`（登记场景包构造器），与本门面
    # `register_scenario(key, *, title, ...)`（登记决策场景 profile）签名互不兼容。
    # 两仓同名函数曾致消费方排查误判（其回执 §7.3 已自我排除）。
    "register_scenario": "⛔ 跨仓同名异义（H1）：与 enterprise scenario.loader.register_scenario(name, factory) 签名互不兼容；决策场景登记请 `import chiyu_kernel.api as api` 后经 `api.register_scenario(...)` 或 `from chiyu_kernel.scenario.registry import register_scenario` 全限定引用",
}


def _dist_of(rel: Path) -> str | None:
    """按路径判定文件所属分发包；`examples/` 等消费侧返回 None（无自有分发 ⇒ 全部受约束）。"""
    parts = rel.parts
    if len(parts) >= 3 and parts[0] == "packages":
        pkg = parts[1].replace("chiyu-", "chiyu_")
        if pkg in DISTS:
            return pkg
    return None


def _is_exempt(rel: Path) -> bool:
    s = rel.as_posix()
    return any(s.startswith(p) for p in EXEMPT_PATHS)


def _is_test(rel: Path) -> bool:
    return "tests" in rel.parts or rel.name.startswith("test_") or rel.name == "conftest.py"


def _imported_roots(node: ast.AST) -> List[Tuple[str, int]]:
    """抽出该文件 import 的顶层模块名（含行号）。"""
    out: List[Tuple[str, int]] = []
    if isinstance(node, ast.Import):
        for a in node.names:
            out.append((a.name, node.lineno))
    elif isinstance(node, ast.ImportFrom):
        if node.level == 0 and node.module:      # 相对导入属同包内部，不受约束
            out.append((node.module, node.lineno))
    return out


def scan(root: Path) -> Tuple[List[str], Dict[str, int]]:
    violations: List[str] = []
    stats: Dict[str, int] = {"files": 0, "exempt": 0, "tests": 0, "imports": 0,
                             "flat_imports": 0, "conflict_warnings": 0}

    for rel_dir in SCAN_ROOTS:
        base = root / rel_dir
        if not base.exists():
            continue
        for f in sorted(base.rglob("*.py")):
            rel = f.relative_to(root)
            if _is_exempt(rel):
                stats["exempt"] += 1
                continue
            if _is_test(rel):
                stats["tests"] += 1
                continue
            stats["files"] += 1
            own = _dist_of(rel)
            try:
                tree = ast.parse(f.read_text(encoding="utf-8"), filename=str(f))
            except SyntaxError as e:                      # pragma: no cover - 语法错由编译器守
                violations.append(f"{rel}: 解析失败 {e}")
                continue
            for node in ast.walk(tree):
                for mod, lineno in _imported_roots(node):
                    top = mod.split(".")[0]
                    if top not in DISTS:
                        continue
                    stats["imports"] += 1
                    if top == own:                         # 同分发内：实现细节，放行
                        continue
                    if any(mod == s or mod.startswith(s + ".") for s in SANCTIONED):
                        continue
                    violations.append(
                        f"{rel}:{lineno}: import {mod} —— 非 sanctioned 面"
                        f"（合法面见 docs/sanctioned-import-surface.md §2）")
                # N1 · 扁平导入易冲突名 → 警告级提示（不阻断，sanctioned 违规才是阻断）
                # 语义：`from <sanctioned> import <易冲突名>` 提示消费方改用命名空间引用，
                # 但**不**因命中清单而把合法导入判为违规。
                if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    sfx = node.module
                    if any(sfx == s or sfx.startswith(s + ".") for s in SANCTIONED):
                        for alias in node.names:
                            nm = alias.asname or alias.name
                            stats["flat_imports"] += 1
                            if nm in CONFLICTING_NAMES:
                                stats["conflict_warnings"] += 1
    return violations, stats


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="sanctioned import 面门禁")
    ap.add_argument("--root", default=".", help="仓库根（默认当前目录）")
    ap.add_argument("--verbose", action="store_true", help="打印扫描统计与豁免项")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    violations, stats = scan(root)

    if args.verbose:
        print(f"扫描文件 {stats['files']} 个 · 跨面 import {stats['imports']} 条")
        print(f"豁免：tests {stats['tests']} 个 · 弃用包 {stats['exempt']} 个")
        for p, why in EXEMPT_PATHS.items():
            print(f"  - {p}：{why}")
        if stats.get("flat_imports"):
            print(f"扁平导入 {stats['flat_imports']} 条 · 其中命中易冲突名 {stats['conflict_warnings']} 条"
                  f"（警告级；清单见 docs/sanctioned-import-surface.md §易冲突名清单）")
            if stats["conflict_warnings"]:
                print("  ⚠ 以下易冲突名建议改用命名空间引用（api.<name>）：")
                for name in CONFLICTING_NAMES:
                    print(f"  - {name}：{CONFLICTING_NAMES[name]}")

    if violations:
        print(f"⛔ sanctioned import 面违规 {len(violations)} 处：", file=sys.stderr)
        for v in violations:
            print("  " + v, file=sys.stderr)
        return 1
    print("OK: 跨分发 import 全部落在 sanctioned 面内")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
