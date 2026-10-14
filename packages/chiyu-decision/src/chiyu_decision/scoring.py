"""决策评分 —— L2 决策脊柱的 S2 / S3。

⛔ 不降级为叙述留痕：九尺子每个键都要有可复算判分（0–4 整数）。
⛔ `confidence` 唯一来源 = `CONFIDENCE_SOURCE_KEY == "ratio"`，禁止以匹配分 `fused` 冒充（违 S3，铁律 C-B）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping, Sequence, Tuple

from chiyu_kernel.contract.decision import (
    CONFIDENCE_SOURCE_KEY, EIGHT_ELEMENTS, ELEMENT_MISSING_CAP,
    ELEMENT_RUBRIC_CAPS, RUBRIC_KEYS, RUBRIC_SCALE_MAX,
)

from .errors import DecisionError


@dataclass(frozen=True)
class RubricReport:
    scores: Mapping[str, float]
    ratio: float
    missing: Tuple[str, ...]


@dataclass(frozen=True)
class ElementReport:
    elements: Mapping[str, object]
    missing: Tuple[str, ...]


def score_rubric(scores: Mapping[str, float]) -> RubricReport:
    """九尺子评分 → ratio。ratio = Σscore / (键数 × SCALE_MAX)，等权。

    ⛔ 缺任一键 ⇒ missing 非空；调用方据此区分 hits=None（缺失）vs 0（评了但差）。
    """
    missing = tuple(k for k in RUBRIC_KEYS if k not in scores)
    present = [float(scores[k]) for k in RUBRIC_KEYS if k in scores]
    denom = len(RUBRIC_KEYS) * RUBRIC_SCALE_MAX
    ratio = sum(present) / denom if denom else 0.0
    padded = {k: float(scores.get(k, 0.0)) for k in RUBRIC_KEYS}
    return RubricReport(scores=padded, ratio=ratio, missing=missing)


def check_elements(elements: Mapping[str, object]) -> ElementReport:
    """八要素结构齐备校验；判分质量由上层 rubric 负责。"""
    missing = tuple(e for e in EIGHT_ELEMENTS if e not in elements)
    return ElementReport(elements=elements, missing=missing)


def cap_rubric_by_elements(
    scores: Mapping[str, float],
    elements_missing: Sequence[str],
    *,
    cap: int = ELEMENT_MISSING_CAP,
    mapping: Mapping[str, Sequence[str]] = ELEMENT_RUBRIC_CAPS,
) -> Dict[str, float]:
    """J9-C：八要素缺失 ⇒ 映射尺子封顶（`ELEMENT_RUBRIC_CAPS`），单向下调。

    ⛔ 语义边界：
      - **不改 confidence 来源**：封顶发生在 ratio 计算**之前**，约束的是九尺子
        输入；`CONFIDENCE_SOURCE_KEY == "ratio"`（铁律 C-B）不动；
      - **单向**：capped = min(原分, cap)；永不升分；要素齐备 ⇒ 逐键原样；
      - **不补键**：scores 里缺的尺子键保持缺失（score_rubric 的 missing 判定
        不受影响，"缺失"与"评了但差"的区分不被此函数抹掉）；
      - **纯函数零语义填充**：不猜 narrative，只对"证据缺失"降权（R41 防假绿）。
    调用时机：S2 之前 —— 消费方在 run_spine 前调用，或 run_spine(element_cap=True)。
    """
    capped = {k: float(v) for k, v in scores.items()}
    if not elements_missing:
        return capped
    for element in elements_missing:
        for ruler in mapping.get(element, ()):
            if ruler in capped and capped[ruler] > cap:
                capped[ruler] = float(cap)
    return capped


def aggregate_confidence(report: RubricReport, *, source_key: str = CONFIDENCE_SOURCE_KEY) -> float:
    """S3 聚合：唯一允许的来源是九尺子 ratio。"""
    if source_key != CONFIDENCE_SOURCE_KEY:
        raise DecisionError(
            "ENGINE_FAULT",
            f"confidence 来源必须为 {CONFIDENCE_SOURCE_KEY!r}，不得用 {source_key!r} 冒充（违 S3）",
        )
    return report.ratio
