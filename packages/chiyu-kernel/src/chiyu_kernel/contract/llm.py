"""LLM 契约 —— L0 词汇与不变式（GAP-4，Batch-2a，2026-10-14）。

定位：LLM 层（`chiyu_kernel/llm/`）的**词汇单一事实源**：本地基座档位闭集 /
provider 协议字段面 / 故事线注入策略口径。此前 llm 只有 impl 无 sanctioned
contract，消费方（APS `aps/llm.py`，enterprise `llm/openai_compat.py`）被迫
import 内部路径（APS 盘点 §四 GAP-4）。

⛔ 本层零第三方依赖、零 IO、零领域字面量。
⛔ 档位**数值表**（TIERS：model/gguf/ctx/pp512…）刻意留在 `llm/tier.py`：
   该文件被部署侧按文件路径加载（`importlib.util.spec_from_file_location`），
   **零项目内 import** 是有守卫测试的硬约束（test_llm_tier_gate.py）。
   故本契约只持档位闭集与字段面，与 tier.py 的漂移由 parity 守卫对拍
   （test_llm_contract.py：闭集相等 + 每档字段恰等于 LLM_TIER_FIELDS）。
"""
from __future__ import annotations

from typing import Tuple

# ── 本地基座档位闭集（与 llm/tier.py TIERS 键对拍，勿单方面增删）──────
LLM_TIERS: Tuple[str, ...] = ("7b", "3b", "1.5b")
#: 缺省档位（U1 决：质量优先；未知档位不猜，回落到此）。
LLM_DEFAULT_TIER = "7b"
#: llama-server 槽位默认（决定性判据优先于并发 ⇒ 一律 1）。
LLM_DEFAULT_PARALLEL = 1

# ── 档位参数字段面（TIERS 每档的键闭集；缺键即口径漂移）──────────────
LLM_TIER_FIELDS: Tuple[str, ...] = (
    "model", "gguf", "ctx", "parallel", "storyline", "pp512", "tg32", "note")

# ── provider 协议字段面（llm/client.py 数据形态；协议本身在 impl）─────
#: 工具调用字段（name + args）。
TOOL_CALL_FIELDS: Tuple[str, ...] = ("name", "args")
#: 模型响应字段（content + tool_calls；缺一即消费方解包错）。
LLM_RESPONSE_FIELDS: Tuple[str, ...] = ("content", "tool_calls")

# ── 故事线注入策略口径（resolve_storyline_policy 的 source 闭集）──────
#: 判定出处必须进返回值 —— 不放进就成了"配了等于没配"的静默分叉。
LLM_STORYLINE_POLICY_SOURCES: Tuple[str, ...] = (
    "explicit-flag", "explicit-tier", "inferred-tier", "auto", "permissive-unknown")

# ── 云端判定（本地档位策略的全部数值前提只在本机 CPU 成立）────────────
#: https 一律视为非本机基座；套用本地档位策略会误伤（白白关掉故事线注入）。
LLM_CLOUD_SCHEME = "https"

# ── 不变式（有守卫测试，不是注释）────────────────────────────────────
LLM_INVARIANTS: Tuple[str, ...] = (
    "tier_table_is_single_source",       # 部署侧与消费侧读同一份档位口径
    "unknown_tier_permissive",           # 未知档位保持既有行为（注入），不误伤
    "cloud_not_subject_to_local_policy",  # 云端端点不套本地 CPU 档位策略
    "policy_source_and_warnings_reported",  # source/warnings 必须进返回值
)

__all__ = [
    "LLM_TIERS", "LLM_DEFAULT_TIER", "LLM_DEFAULT_PARALLEL", "LLM_TIER_FIELDS",
    "TOOL_CALL_FIELDS", "LLM_RESPONSE_FIELDS", "LLM_STORYLINE_POLICY_SOURCES",
    "LLM_CLOUD_SCHEME", "LLM_INVARIANTS",
]
