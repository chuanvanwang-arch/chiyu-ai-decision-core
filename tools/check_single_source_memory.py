#!/usr/bin/env python3
"""memory 单源裁定守卫（T44，memory 毕业批次五）。

背景：memory 毕业后，PG 侧记忆写路径有三条合法通道，任何绕过通道的直写
都会把"单源纪律"退化为双写（同一条边/同一条笔记两个写入口，漂移不可察）：

1. 记忆网回链边（``graph_edge`` 表）：唯一写入口
   ``chiyu_kernel.persist``（``write_decision_memory_net``）。
2. 双轨 NOTE 笔记属性（``particle_attribute`` 表）：唯一写入口
   ``chiyu_kernel.persist.pg_memory_stores``（``PgNoteStore``）。

本守卫用文本扫描 ``packages/*/src`` 下所有 Python 源文件，发现对上述表的
``INSERT INTO`` 直写而文件不在白名单即退出码 1（fail-closed）。白名单按
"文件 + 表"二元组精确登记；新增合法写入口必须先改本守卫再改代码——
让"多一个写入口"成为一次显式的、可评审的决策，而不是悄悄溜进来的回归。

用法：``python tools/check_single_source_memory.py``（Makefile lint 目标调用）。
"""
from __future__ import annotations

import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# "表名 -> 允许出现 INSERT INTO 的文件（相对仓库根，POSIX 风格）"
# T47：graph_edge 唯一落库点收窄到 persist/graph_edges.py（受控边写原语，
# write_decision_memory_net 经 upsert_graph_edge 委托同一份 SQL）。
_WHITELIST: dict = {
    "graph_edge": {
        "packages/chiyu-kernel/src/chiyu_kernel/persist/graph_edges.py",
    },
    "particle_attribute": {
        "packages/chiyu-kernel/src/chiyu_kernel/persist/pg_memory_stores.py",
    },
}

# 行级判法：同一行出现 INSERT INTO 且出现表名即算直写（fail-closed）。
# 不用精确解析 f-string 拼接——真实写法形如
# ``INSERT INTO {_q(schema, 'graph_edge')}`` / ``INSERT INTO {schema}.graph_edge``，
# 表名可能落在插值参数里，精确解析 SQL 拼接反而漏报（首版即栽在这）。
_INSERT_RE = re.compile(r"INSERT\s+INTO", re.IGNORECASE)
_TABLES = ("graph_edge", "particle_attribute")


def scan() -> list:
    """返回违规列表：[(file, line_no, table)]；无违规返回空表。

    只扫 ``packages/*/src``（运行时写入口面）；``tests/`` 的 INSERT 是测试
    夹具种子数据（如 ``test_pg_e2e.py``），不构成生产双写风险，不在裁定面。
    """
    violations = []
    packages_root = os.path.join(ROOT, "packages")
    for pkg in sorted(os.listdir(packages_root)):
        src_root = os.path.join(packages_root, pkg, "src")
        if not os.path.isdir(src_root):
            continue
        for dirpath, dirnames, filenames in os.walk(src_root):
            dirnames[:] = [d for d in dirnames if d not in ("build", "__pycache__")]
            for fn in filenames:
                if not fn.endswith(".py"):
                    continue
                path = os.path.join(dirpath, fn)
                rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
                with io.open(path, "r", encoding="utf-8", errors="replace") as fp:
                    for lineno, line in enumerate(fp, 1):
                        if not _INSERT_RE.search(line):
                            continue
                        for table in _TABLES:
                            if table in line and rel not in _WHITELIST.get(table, set()):
                                violations.append((rel, lineno, table))
    return violations


def main() -> int:
    violations = scan()
    if violations:
        print("memory 单源裁定守卫：发现未登记的直写入口", file=sys.stderr)
        for rel, lineno, table in violations:
            print(f"  {rel}:{lineno}  表 {table}", file=sys.stderr)
        print(
            "合法写入口见 tools/check_single_source_memory.py _WHITELIST；"
            "新增写入口须先改守卫白名单再改代码。",
            file=sys.stderr,
        )
        return 1
    print("memory 单源裁定守卫：通过（graph_edge / particle_attribute 写入口均唯一）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
