"""chiyu decide —— 跑决策脊柱（确定性分支，零 IO、不接 LLM）。

⛔ 诚实原则：八要素未提供的项一律留空，由脊柱如实报 missing；
   绝不伪造齐备以换取「看起来跑通」。
"""
from __future__ import annotations

import argparse
import json
from typing import Any, Dict

from chiyu_decision.api import run_spine
from chiyu_kernel.contract.decision import RUBRIC_KEYS
from ._plugins import resolve

DEFAULT_SCORE = 3          # RUBRIC_SCALE_MAX=4；全 3 ⇒ ratio=27/36=0.75 < 0.79 阈值
DEFAULT_THRESHOLD = 0.79


def _parse_scores(raw: str | None) -> Dict[str, float]:
    """解析 `--scores clarity=3,logic=4`；未提及的键取 DEFAULT_SCORE。"""
    scores: Dict[str, float] = {k: float(DEFAULT_SCORE) for k in RUBRIC_KEYS}
    if not raw:
        return scores
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        if "=" not in item:
            raise ValueError(f"评分项须形如 key=value：{item!r}")
        key, _, value = item.partition("=")
        key = key.strip()
        if key not in RUBRIC_KEYS:
            raise ValueError(f"未知尺子键 {key!r}；合法键：{', '.join(RUBRIC_KEYS)}")
        scores[key] = float(value.strip())
    return scores


def _build_elements(topic: str) -> Dict[str, object]:
    """八要素：只填真实提供的项（intent = topic）。

    ⛔ 不得用空串/占位补齐其余键 —— `check_elements` 只判**键是否存在**，
       补空键会让「要素缺失」恒为「无」，属典型假齐备。CLI 只拿到了议题，
       故如实只给 intent，其余由脊柱报 missing。
    """
    return {"intent": topic}


def handler(args: argparse.Namespace) -> int:
    scores = _parse_scores(args.scores)
    elements = _build_elements(args.topic)
    mode, enabled, disabled, mwarn = resolve(args.mode)
    result = run_spine(
        context={
            "decision_id": args.decision_id or f"cli-{args.topic[:24]}",
            "topic": args.topic,
            "work_mode": mode.id,        # 观测面：本次走的工作模式
        },
        profile=None,                  # ⛔ 无默认值，预览模式显式传 None
        rubric_scores=scores,
        elements=elements,
        persister=None,                # 不落库
        threshold=args.threshold,
    )
    payload: Dict[str, Any] = {
        "decision_id": result.decision_id,
        "stage_reached": result.stage_reached,
        "confidence": round(result.confidence, 4),
        "autonomous": result.autonomous,
        "redline_hit": result.redline_hit,
        "redline_reasons": list(result.redline_reasons),
        "rubric_missing": list(result.rubric_missing),
        "elements_missing": list(result.elements_missing),
        "persisted": result.persisted,
        "work_mode": mode.id,
        "work_mode_plugins": list(enabled),
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    print(f"decision_id   : {payload['decision_id']}")
    print(f"stage_reached : {payload['stage_reached']}")
    print(f"confidence    : {payload['confidence']}  (阈值 {args.threshold})")
    print(f"autonomous    : {payload['autonomous']}")
    print(f"redline_hit   : {payload['redline_hit']} {payload['redline_reasons'] or ''}")
    print(f"尺子缺失      : {', '.join(payload['rubric_missing']) or '无'}")
    print(f"要素缺失      : {', '.join(payload['elements_missing']) or '无'}")
    print(f"工作模式      : {payload['work_mode']}（启用插件：{', '.join(payload['work_mode_plugins']) or '无'}）")
    return 0


def register(sub: Any) -> None:
    p = sub.add_parser("decide", help="跑决策脊柱（确定性分支）")
    p.add_argument("--topic", required=True, help="决策议题描述")
    p.add_argument("--scores", default=None, help="九尺子评分，如 clarity=4,logic=3")
    p.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD, help="自主放行阈值")
    p.add_argument("--decision-id", default=None, help="指定决策 ID")
    p.add_argument("--mode", default=None,
                   help="工作模式：standard/ptc/minimal/creative（缺省=standard）")
    p.add_argument("--json", action="store_true", help="机器可读输出")
    p.set_defaults(handler=handler)
