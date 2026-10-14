"""仓库开发者入口（纯 stdlib，等价于 Makefile 的目标）。

⛔ 为什么需要它：本机（Windows）**未安装 make**（实测 `which make` → not found），
   而计划里的闸门命令写作 `make test` / `make check`。为确保闸门可执行、可复现，
   这里给出等价的跨平台入口；Makefile 保留，供具备 make 的环境使用。

用法：
    python tools/dev.py test             # 全部守卫测试
    python tools/dev.py check            # 可编译友好检查
    python tools/dev.py manifest         # 重生成契约 sha256 清单
    python tools/dev.py mutate-literals  # G1-3/α4：零领域字面量守卫的突变自证
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PKG = REPO / "packages" / "chiyu-kernel"
SRC = PKG / "src"
CONTRACT_PARTICLE = SRC / "chiyu_kernel" / "contract" / "particle.py"
GUARD_TEST = PKG / "tests" / "test_contract_no_domain_literals.py"

TEST_TARGETS = ["packages/chiyu-kernel/tests", "tools/tests"]


def _run(args: list[str], cwd: Path = REPO) -> int:
    print("$ " + " ".join(args))
    return subprocess.call(args, cwd=str(cwd))


def cmd_test(_args) -> int:
    return _run([sys.executable, "-m", "pytest", *TEST_TARGETS, "-q"])


def cmd_check(_args) -> int:
    return _run([sys.executable, "tools/check_cython_friendly.py",
                 "--root", ".", "packages/chiyu-kernel/src"])


def cmd_manifest(_args) -> int:
    return _run([sys.executable, "_gen_manifest.py"], cwd=CONTRACT_PARTICLE.parent)


def cmd_mutate_literals(_args) -> int:
    """G1-3 / α4：注入领域字面量 ⇒ 守卫必须转红；还原 ⇒ 必须转绿。

    判据是**退出码的翻转**（0 → 非 0），不是"看输出里有没有 failed 字样"。
    """
    backup = Path(tempfile.mkdtemp(prefix="chiyu_mut_")) / "particle.py.bak"
    shutil.copy2(CONTRACT_PARTICLE, backup)

    def run_guard() -> tuple[int, str]:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", str(GUARD_TEST), "-q"],
            cwd=str(REPO), capture_output=True, text=True, encoding="utf-8",
            errors="replace",
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")

    try:
        base_rc, base_out = run_guard()
        with CONTRACT_PARTICLE.open("a", encoding="utf-8") as fh:
            fh.write('\nBAD = ("cluster", "slab")\n')
        mut_rc, mut_out = run_guard()
    finally:
        shutil.copy2(backup, CONTRACT_PARTICLE)
        shutil.rmtree(backup.parent, ignore_errors=True)

    after_rc, _ = run_guard()

    print(f"基线（应绿）:   exit={base_rc}")
    print(f"注入后（应红）: exit={mut_rc}")
    print(f"还原后（应绿）: exit={after_rc}")
    tail = [ln for ln in mut_out.splitlines() if "命中领域词" in ln]
    for ln in tail[:4]:
        print("  " + ln.strip()[:160])
    if base_rc != 0:
        print("── 基线失败详情（应为空） ──────────────")
        for ln in (base_out.splitlines() or base_out.splitlines()):
            if "assert" in ln or "Error" in ln or "FAILED" in ln or "failed" in ln:
                print("  " + ln.strip()[:160])

    ok = (base_rc == 0) and (mut_rc != 0) and (after_rc == 0)
    print("突变自证：" + ("通过（守卫有判别力）" if ok else "⛔ 不通过"))
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="chiyu-foundation 开发入口")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn, help_text in (
        ("test", cmd_test, "全部守卫测试"),
        ("check", cmd_check, "可编译友好检查"),
        ("manifest", cmd_manifest, "重生成契约 sha256 清单"),
        ("mutate-literals", cmd_mutate_literals, "零领域字面量守卫的突变自证"),
    ):
        p = sub.add_parser(name, help=help_text)
        p.set_defaults(func=fn)
    args = ap.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
