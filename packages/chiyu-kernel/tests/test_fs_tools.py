"""T3 — 沙箱文件系统工具（吸收 dsh `fs/fs` + `fs/fs-local`）：root 沙箱 + write 高危险。

TDD：先红（chiyu_kernel.tools.fs 尚不存在）→ 绿。
"""
import tempfile

from chiyu_kernel.tools import ScopeDenied, ToolRegistry
from chiyu_kernel.tools.fs import PathEscapeError, SandboxedFs, register_fs_tools


def _fs():
    d = tempfile.mkdtemp()
    return SandboxedFs(d), d


def test_read_write_list_roundtrip():
    fs, d = _fs()
    n = fs.write("a/b.txt", "hello")
    assert n == 5
    assert fs.read("a/b.txt") == "hello"
    names = fs.list(".")
    assert "a" in names


def test_path_escape_rejected():
    fs, d = _fs()
    raised = False
    try:
        fs.write("../evil.txt", "x")
    except PathEscapeError:
        raised = True
    assert raised, "越界写未被拒绝"


def test_register_fs_tools_high_risk_and_scope():
    fs, d = _fs()
    reg = ToolRegistry()
    register_fs_tools(reg, d)
    # write 标记高危险
    assert reg.spec("fs_write").high_risk is True
    assert reg.spec("fs_read").high_risk is False
    assert reg.spec("fs_list").high_risk is False
    # 经 registry 调用（scope=fs）：先写后读
    reg.execute("fs_write", {"path": "a/b.txt", "content": "hello"}, scope="fs")
    assert reg.execute("fs_read", {"path": "a/b.txt"}, scope="fs") == "hello"
    # 越权：scope 不匹配被拒
    raised = False
    try:
        reg.execute("fs_read", {"path": "a/b.txt"}, scope="other")
    except ScopeDenied:
        raised = True
    assert raised, "fs 工具越权未拒绝"
