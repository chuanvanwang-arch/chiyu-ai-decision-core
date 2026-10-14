"""LLM 层 —— 档位策略（U1 决：本地基座按档位开关故事线注入）。

⛔ 本层**只有档位策略**，没有 HTTP 网关。这不是遗漏，是登记在案的待批项：
────────────────────────────────────────────────────────────────────────
计划 `docs/superpowers/plans/2026-09-21-底座内核抽取T1-T5实施计划.md` Task 5 Step 5
要求"搬迁 `llm/client.py`（包路径 + `CHIYU_LLM_API_KEY` 双重身份）"，但**逐字搬迁
与设计稿 §0.3 的内核铁律冲突**：demo 版 `llm/client.py` 内含领域内容 ——
`SYSTEM_CAUSE`（"政务诉求归并判定专家"）、`SYSTEM_NAME`（"政务诉求分析专家"）、
`score_cause_consistency`、`name_and_summarize`。把这些搬进内核即违反
"内核零领域字面量 / 方法论只承载跨域洞察"（用户 2026-08-24 立的去污染判据）。

因此本项的正确形态是**设计变更**，不是搬迁：
    机制（进内核）＝ OpenAI 兼容调用的传输层 + fail_reason 归一化 + 逐字留痕 sink
    领域（留 L4）＝ system prompt、领域业务方法、trace 落库的具体表
⛔ 该变更**未经批准**，故本轮不写实现代码（HARD-GATE：未批准不写实现）。
   需新增一个"网关接口"设计（prompt 由消费方注入、留痕 sink 由消费方注入），
   由用户批准后另开 Task。

消费者当前可用：`tier.py`（档位策略，零依赖、可被部署侧按文件路径加载）。
"""
from .tier import (
    DEFAULT_PARALLEL,
    DEFAULT_TIER,
    TIERS,
    is_cloud_endpoint,
    normalize_tier,
    resolve_storyline_policy,
    tier_spec,
)

__all__ = [
    "DEFAULT_PARALLEL", "DEFAULT_TIER", "TIERS", "is_cloud_endpoint",
    "normalize_tier", "resolve_storyline_policy", "tier_spec",
]
