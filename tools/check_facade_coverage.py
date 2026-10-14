"""门面完整性守卫模板（WS4 · 复用范式）。

把 `test_api_facade_covers_all_layers` 的「写好但未暴露即判红」逻辑抽成可复用
CLI，供消费方自检「我的领域工具/场景是否都进了门面」。

用法（foundation 自检）：
  python tools/check_facade_coverage.py \
      --facade chiyu_kernel.api --package chiyu_kernel \
      --layers vector,ontology,context,actions,orchestration,evolution,events,audit,llm,plugins,session,tools,skills,plan,mcp,hooks,interaction,workflow,scenario \
      --renames-file tools/facade_renames.txt
  - 某层 `__all__` 中有符号未出现在门面 ⇒ 退出 1。
"""
from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path


def load_renames(path) -> dict:
    """每行 `layer.name=facade_name`；空行 / `#` 注释跳过。"""
    renames: dict = {}
    p = Path(path)
    if not p.exists():
        return renames
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        layer, name = k.strip().split(".", 1)
        renames[(layer.strip(), name.strip())] = v.strip()
    return renames


def facade_name(layer: str, name: str, renames: dict) -> str:
    return renames.get((layer, name), name)


def missing_names(layer: str, layer_all, facade, renames: dict) -> list:
    """返回该层 `__all__` 里未被门面暴露的符号（已按改名表映射）。"""
    out = []
    for name in layer_all:
        target = facade_name(layer, name, renames)
        if not hasattr(facade, target):
            out.append(f"{layer}.{name} → api.{target}")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="门面完整性守卫模板")
    ap.add_argument("--facade", required=True, help="门面模块，如 chiyu_kernel.api")
    ap.add_argument("--package", required=True, help="子包所在父包，如 chiyu_kernel")
    ap.add_argument("--layers", required=True, help="逗号分隔的子包名列表")
    ap.add_argument("--renames-file", default=None,
                    help="layer.name=facade_name 映射文件")
    args = ap.parse_args(argv)
    # 自包含：CLI 直接运行时把仓库根与 foundation 的 src 布局目录加入 sys.path，
    # 使 `chiyu_kernel` 可导入（消费方按需在自己的环境调整）。
    repo = Path(__file__).resolve().parents[1]
    for cand in (repo, repo / "packages" / "chiyu-kernel" / "src"):
        s = str(cand)
        if cand.is_dir() and s not in sys.path:
            sys.path.insert(0, s)
    try:
        facade = importlib.import_module(args.facade)
    except Exception as e:  # noqa: BLE001
        print(f"[error] 无法导入门面 {args.facade!r}：{e}", file=sys.stderr)
        return 2
    renames = load_renames(args.renames_file) if args.renames_file else {}
    problems = []
    for layer in [x.strip() for x in args.layers.split(",") if x.strip()]:
        try:
            mod = importlib.import_module(f"{args.package}.{layer}")
        except Exception as e:  # noqa: BLE001
            print(f"[warn] 无法导入子包 {args.package}.{layer}：{e}",
                  file=sys.stderr)
            continue
        layer_all = getattr(mod, "__all__", None) or []
        problems.extend(missing_names(layer, layer_all, facade, renames))
    if problems:
        print("门面未覆盖下列符号 ⇒ 消费方只能违约 import 内部路径：")
        for p in problems:
            print("  " + p)
        return 1
    print("门面完整性：通过（0 处未暴露）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
