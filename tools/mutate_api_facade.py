"""变异自证（临时工具，不属交付物）：证明门面接线守卫**有鉴别力**。

做法：把 `api.py` 里 orchestration 的 `fold_history` 同时从 import 与 `__all__` 移除，
      断言 `test_api_facade_covers_all_layers.py` 转红；随后原样还原。

⛔ 为什么必须做：`test_facade_covers_every_layer_export` 若因"比对逻辑空跑"而恒绿，
   就等于给一个假的接线保证。本项目已记录同族假绿多次。

用法：python tools/mutate_api_facade.py（在本仓根执行）
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PY = r"C:/Users/wangchuan08/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe"
ROOT = Path(r"D:/system/chiyu-foundation")
API = ROOT / "packages/chiyu-kernel/src/chiyu_kernel/api.py"
BAK = API.with_suffix(".py.facade-bak")

IMPORT_LINE = "    fold_history,\n"
ALL_LINE = '    "fold_history", "is_stuck", "summarize",\n'
ALL_LINE_MUT = '    "is_stuck", "summarize",\n'


def run_test() -> tuple[int, str]:
    p = subprocess.run(
        [PY, "-m", "pytest",
         "packages/chiyu-kernel/tests/test_api_facade_covers_all_layers.py",
         "-q", "-o", "pythonpath=packages/chiyu-kernel/src"],
        cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "").strip().splitlines()[-1]


def main() -> int:
    src = API.read_text(encoding="utf-8")
    assert IMPORT_LINE in src and ALL_LINE in src, "变异锚点未命中，判据失去意义"
    BAK.write_text(src, encoding="utf-8")
    try:
        mutated = (src.replace(IMPORT_LINE, "")
                      .replace(ALL_LINE, ALL_LINE_MUT))
        assert "fold_history" not in mutated, "变异未生效"
        API.write_text(mutated, encoding="utf-8")
        code, tail = run_test()
        print(f"[变异态] 退出码={code} :: {tail}")
        assert code != 0, "守卫对『符号未接线』无反应 ⇒ 鉴别力为零（假绿）"
    finally:
        API.write_text(src, encoding="utf-8")
        # ⛔ 本机 safe-delete shim 在把备份丢进回收站时会抛 OSError（网络路径）⇒ 不致命
        try:
            BAK.unlink(missing_ok=True)
        except OSError as e:                       # noqa: BLE001
            print(f"[提示] 备份文件未能删除（非致命）：{e}")
    code2, tail2 = run_test()
    print(f"[还原态] 退出码={code2} :: {tail2}")
    assert code2 == 0, f"还原后仍红 ⇒ 变异未清理干净：{tail2}"
    print("✅ 变异自证通过：注入未接线符号 ⇒ 红；还原 ⇒ 绿")
    return 0


if __name__ == "__main__":
    sys.exit(main())
