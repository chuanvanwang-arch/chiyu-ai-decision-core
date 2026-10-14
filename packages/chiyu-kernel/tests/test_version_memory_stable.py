# -*- coding: utf-8 -*-
"""memory 毕业守卫（T44）。

三判据：
1. ``memory`` 在 CAPABILITIES 中为 ``stable``（进 1.0 兼容承诺）；
2. ``MEMORY_EXPERIMENTAL is False``（声明态机器可检，R4）；
3. 单源裁定守卫对真实仓树通过（graph_edge / particle_attribute 直写入口唯一）。
"""
import importlib.util
import os
import subprocess
import sys

from chiyu_kernel import api, version as V

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))


def test_memory_is_stable():
    assert V.capability_status("memory") == "stable"


def test_memory_flag_flipped():
    assert api.MEMORY_EXPERIMENTAL is False


def test_single_source_guard_passes_on_real_tree():
    tool = os.path.join(_REPO, "tools", "check_single_source_memory.py")
    assert os.path.isfile(tool), f"守卫工具缺失：{tool}"
    proc = subprocess.run(
        [sys.executable, tool], capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, f"单源裁定守卫未通过：\n{proc.stdout}\n{proc.stderr}"
