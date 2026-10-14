"""本地 LLM 基座「档位」策略的**单一事实源**（U1 决：维持 7B；故事线注入按档位开关）。

内核实测版：demo `src/chiyu_group/llm/tier.py` 逐字保留，仅改包路径
`chiyu_group.llm` → `chiyu_kernel.llm`，**不增不改**。

它修的是什么
------------
设计稿 §4 把本地基座写成"7B int4 CPU 单次 3~8s"，据此推出"LLM 可进主链路"。
2026-09-21 在本机（Core Ultra 7 155U / 12 线程 / 无 GPU）实测**推翻**该前提：

| 档位 | 体积 | prefill `pp512` | 生成 `tg32` | 第9尺 prompt 600 tok | 注入故事线后 1055 tok |
|---|---|---|---|---|---|
| `7b`   | 4.36 GiB | 15.52 tok/s | 3.77 tok/s | ≈47s | ≈76s（实测 108.9s，含冷读盘） |
| `3b`   | 1.95 GiB | 38.16 tok/s | 7.17 tok/s | ≈20s | ≈32s |
| `1.5b` | 1.04 GiB | 78.36 tok/s | 13.15 tok/s | ≈10s | ≈16s |

关键结构：**第 9 尺的单次耗时由 prefill 支配**（prompt 越长越致命），而生成侧
3.77 tok/s ≈ 16GB/s 有效带宽，**已触到该 U 系列芯片的内存带宽上限** ⇒ 生成侧无调参空间。

⇒ 「故事线注入」这项**能力**没错（它承载 S4「单源双视图」的顺序推理），但它把
   prompt 从 127 → 1055 token（×8.3）。在 7B CPU 档下，一次判读因此从 ≈10s 推到分钟级。
   ⇒ **按档位开关**：大档（7b）默认关闭、由调用方显式开；小档（3b/1.5b）默认开。

三条设计约束
------------
① **两侧共用一张表**：`tools/run_llama_server.py`（部署侧，按文件路径加载）与
   `llm/client.py`（应用侧，import）读同一份 `TIERS` ⇒ 不会出现"启动器实际跑 7B、
   应用以为在跑 3B"的口径分叉（本项目已撞多次的同族缺陷）。
② **本模块零项目内 import**（只用 `os` / `re`）：部署侧用
   `importlib.util.spec_from_file_location` 按路径直接加载，**不经** `chiyu_group/__init__`
   （那会连锁触发 dotenv 等副作用）——故本文件必须能独立执行。
③ **未知档位 ⇒ 保持既有行为（注入）**：云端 https 端点 + 大模型名（如
   `deepseek-ai/DeepSeek-V4-Flash`）不满足"CPU prefill 15 tok/s"这个前提，
   不该被本地档位策略误伤。缺省永远向后兼容。
"""
from __future__ import annotations

import os
import re

# ── 档位表（唯一事实源）───────────────────────────────────────────────────
#   `storyline`：该档位下**默认**是否注入故事线/图谱邻域（可被 CHIYU_LLM_STORYLINE 覆盖）。
#   `parallel` ：llama-server 槽位数。**决定性判据优先于并发** ⇒ 一律 1：
#                第 9 尺是"可复现锚点"，非确定性会让锚点失去意义（见 L2 记录）。
TIERS: dict[str, dict] = {
    "7b": {
        "model": "qwen2.5-7b-instruct",
        "gguf": "qwen2.5-7b-instruct-q4_k_m.gguf",
        "ctx": 8192,
        "parallel": 1,
        "storyline": False,
        "pp512": 15.52,
        "tg32": 3.77,
        "note": "质量优先档。故事线注入默认关闭：1055 token 的 prompt 在本机 prefill ≈68s。",
    },
    "3b": {
        "model": "qwen2.5-3b-instruct",
        "gguf": "qwen2.5-3b-instruct-q4_k_m.gguf",
        "ctx": 8192,
        "parallel": 1,
        "storyline": True,
        "pp512": 38.16,
        "tg32": 7.17,
        "note": "平衡档。prefill 快 2.5 倍，故事线注入的成本（≈28s）可被接受。",
    },
    "1.5b": {
        "model": "qwen2.5-1.5b-instruct",
        "gguf": "qwen2.5-1.5b-instruct-q4_k_m.gguf",
        "ctx": 8192,
        "parallel": 1,
        "storyline": True,
        "pp512": 78.36,
        "tg32": 13.15,
        "note": "速度优先档。接近交互级；但判读质量风险较高，不宜作为决定性判据的唯一依据。",
    },
}

DEFAULT_TIER = "7b"          # U1 决（2026-09-21）：维持 7B（质量优先）
DEFAULT_PARALLEL = 1         # 见 TIERS 注释：决定性判据优先

_TIER_RE = re.compile(r"(\d+(?:\.\d+)?)\s*b", re.I)


def normalize_tier(raw: object) -> str | None:
    """把任意写法收敛到 `TIERS` 的键：`7B` / `qwen2.5-7b-instruct` / `Qwen2.5-1.5B` → `7b` / `1.5b`。

    认不出返回 `None`（= 未知档位），**不猜**。
    """
    if raw is None:
        return None
    s = str(raw).strip().lower()
    if not s or s in ("auto", "none", "null"):
        return None
    if s in TIERS:
        return s
    m = _TIER_RE.search(s)
    if not m:
        return None
    cand = f"{m.group(1)}b"
    return cand if cand in TIERS else None


def is_cloud_endpoint(base_url: str | None) -> bool:
    """https 一律视为"非本机基座"。

    理由：本策略的全部数值前提（`pp512=15.52 tok/s`，无 GPU、CPU prefill 支配耗时）
    只在**本机 CPU 基座**上成立。云端 https 端点即使是同名 `qwen2.5-7b-instruct`，
    也跑在别人的 GPU 上，套用本地档位策略会**误伤**（白白关掉故事线注入）。
    """
    return str(base_url or "").strip().lower().startswith("https://")


_TRUTHY = ("1", "true", "on", "yes", "y")
_FALSY = ("0", "false", "off", "no", "n")


def resolve_storyline_policy(*, model: str = "", base_url: str = "",
                             tier: object = None, storyline: object = None) -> dict:
    """解出「本次是否注入故事线/图谱邻域」及其**判定出处**。

    优先级：显式开关 `CHIYU_LLM_STORYLINE` > 显式档位 `CHIYU_LLM_TIER` > 由模型名推断的档位
            > 未知档位（宽松：注入）。

    返回 `{tier, inject, source, reason, flag, warnings}`。
    ⚠ `source` / `warnings` 是**给人看的可核验字段**：不放进返回值，就成了"配了等于没配"
      的静默分叉（配置写错与配置没问题外观一致 —— 本项目反复记录的假绿家族）。
    """
    warnings: list[str] = []

    # ── ① 档位：显式 > 推断 ─────────────────────────────────────────────
    raw_tier = tier if tier is not None else os.environ.get("CHIYU_LLM_TIER")
    t = normalize_tier(raw_tier)
    source = "explicit-tier" if t else ""
    if raw_tier not in (None, "") and t is None:
        warnings.append(
            f"档位 {raw_tier!r} 不在已知档位 {sorted(TIERS)} 内 —— 已回落自动判定")

    bu = base_url or os.environ.get("CHIYU_LLM_BASE_URL") or ""
    if t is None and not is_cloud_endpoint(bu):
        t = normalize_tier(model or os.environ.get("CHIYU_LLM_MODEL") or "")
        if t:
            source = "inferred-tier"

    # ── ② 开关：显式 > 由档位派生 > 宽松 ────────────────────────────────
    raw_flag = storyline if storyline is not None else os.environ.get("CHIYU_LLM_STORYLINE")
    flag = str(raw_flag).strip().lower() if raw_flag not in (None, "") else "auto"
    if flag in _TRUTHY:
        return {"tier": t, "inject": True, "source": "explicit-flag", "flag": flag,
                "reason": "CHIYU_LLM_STORYLINE 显式开启（覆盖档位策略）",
                "warnings": warnings}
    if flag in _FALSY:
        return {"tier": t, "inject": False, "source": "explicit-flag", "flag": flag,
                "reason": "CHIYU_LLM_STORYLINE 显式关闭（覆盖档位策略）",
                "warnings": warnings}
    if flag != "auto":
        warnings.append(
            f"CHIYU_LLM_STORYLINE={raw_flag!r} 不是 auto/on/off 之一 —— 已按 auto 处理")
        flag = "auto"

    if t is not None:
        inj = bool(TIERS[t]["storyline"])
        return {"tier": t, "inject": inj, "source": source or "auto", "flag": flag,
                "reason": f"档位 {t}：{TIERS[t]['note']}",
                "warnings": warnings}

    return {"tier": None, "inject": True, "source": "permissive-unknown", "flag": flag,
            "reason": ("档位未知（云端 / 未声明，或端点为 https）⇒ 保持既有行为：注入"
                       "（本地 CPU 档位的 prefill 前提在此不成立，不套用本地策略）"),
            "warnings": warnings}


def tier_spec(tier: object = None) -> dict:
    """取档位的部署参数（含 `tier` 键与 `source`）。认不出则回落 `DEFAULT_TIER`。"""
    t = normalize_tier(tier if tier is not None else os.environ.get("CHIYU_LLM_TIER"))
    if t is None:
        t = DEFAULT_TIER
        source = "default"
    else:
        source = "explicit"
    d = dict(TIERS[t])
    d["tier"] = t
    d["source"] = source
    return d
