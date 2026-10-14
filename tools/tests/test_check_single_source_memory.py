# -*- coding: utf-8 -*-
"""单源裁定守卫（T44）的判别力自证。

三判据：
1. 干净树跑真守卫 → 通过（白名单内写入口全数命中）；
2. 扫描函数对临时注入的"绕过 writer 直写 graph_edge"文件 → 报违规；
3. 白名单摘除后对合法 writer → 报违规（证明白名单真的在起作用，不是恒绿）。
"""
import importlib.util
import os

_TOOLS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "tools",
)


def _load_guard():
    spec = importlib.util.spec_from_file_location(
        "check_single_source_memory",
        os.path.join(_TOOLS, "check_single_source_memory.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_real_tree_is_clean():
    """判据 1：真实仓树全部写入口已登记。"""
    assert _load_guard().scan() == []


def test_ghost_direct_writer_is_caught(tmp_path):
    """判据 2：绕过 writer 直写 graph_edge 的幽灵文件必须被抓。"""
    pkg = tmp_path / "packages" / "ghost" / "src"
    pkg.mkdir(parents=True)
    (pkg / "ghost_writer.py").write_text(
        'def sneaky(schema):\n'
        '    return f"INSERT INTO {schema}.graph_edge VALUES (1)"\n',
        encoding="utf-8",
    )
    mod = _load_guard()
    mod.ROOT = str(tmp_path)
    hits = mod.scan()
    tables = {t for _, _, t in hits}
    assert "graph_edge" in tables, f"幽灵直写未被识别：{hits}"


def test_whitelist_removal_turns_red():
    """判据 3：摘掉白名单后合法 writer 也报红——守卫不是恒绿摆设。"""
    mod = _load_guard()
    saved = dict(mod._WHITELIST)
    try:
        mod._WHITELIST["graph_edge"] = set()
        hits = mod.scan()
        # T47：graph_edge 唯一落库点已迁 persist/graph_edges.py（受控边写原语）
        assert any(
            t == "graph_edge" and "persist/graph_edges.py" in f for f, _, t in hits
        ), f"摘白名单后未报红：{hits}"
    finally:
        mod._WHITELIST.clear()
        mod._WHITELIST.update(saved)
