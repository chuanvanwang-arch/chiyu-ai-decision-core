"""生成 contract/manifest.json（契约 sha256 清单）。

用途：
  ① T9 双轨同源校验：源码 wheel 与编译 wheel 的 contract/ 必须逐文件 sha256 一致；
  ② 消费方钉版本：新项目记录所依赖的契约指纹，底座升级时可比对。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def build() -> dict:
    files = {}
    for p in sorted(HERE.glob("*.py")):
        if p.name == "_gen_manifest.py":
            continue
        files[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
    return {"algo": "sha256", "count": len(files), "files": files}


if __name__ == "__main__":
    target = HERE / "manifest.json"
    target.write_text(json.dumps(build(), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"manifest written: {target}")
