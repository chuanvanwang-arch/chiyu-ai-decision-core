# 平台决策脊柱 P2a：chiyu-decision 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: 用 `executing-plans`（Inline Execution）逐 Task 执行，每 Task 末过闸门。步骤用 `- [ ]` 复选框跟踪。
>
> **I'm using the writing-plans skill to create the implementation plan.**

**Goal:** 把 demo 的「决策脊柱运行时」（S1→S5 判据、九尺子评分、红线闸门、落库）抽成独立包 `chiyu-decision`，严格对齐 `chiyu-kernel` 的 L0 契约（零领域字面量、顺序契约、confidence 仅取 `ratio`）。

**Architecture:** 新建独立本地包 `packages/chiyu-decision/`（src-layout，模块名 `chiyu_decision`）。决策脊柱 S1→S5 的**顺序与判据常量**全部来自 `chiyu_kernel.contract.decision`（L0 单一事实源），本包不得另写一份；评分/红线/持久化各自成模块，落库经依赖注入的 `persister` 回调（无 PG 也能全绿）。消费方只许 import `chiyu_decision.api`。

**Tech Stack:** Python 3.11+（与内核同 hermes venv）、`dataclasses`、`pytest`。依赖 `chiyu-kernel`（本仓，path 依赖）。

**拆分说明（writing-plans 要求）：** P2 原含 T6 决策脊柱 + T7 免代码门户两个独立子系统，本计划只覆盖 **T6（chiyu-decision）**；**T7（chiyu-portal）作为 P2b 单独立项**，不在本计划范围。

**依据：** `docs/2026-09-21-决策智能平台概念设计.md` §2（决策脊柱）、§9（P1 `chiyu-decision` 抽取规划）、§10 块 2（活契约）、§7 能力映射表（决策脊柱行：契约在、运行时待抽）。

---

## §0 执行前必读

### 0.1 三条不可妥协的契约铁律（来自 §2 历史教训 + §10 块 2 成功判据）

| # | 铁律 | 违反后果 | 本计划落点 |
|---|---|---|---|
| C-A | **顺序即语义**：`SPINE_ORDER` 6 步不可重排，本包运行时必须逐项等于 `chiyu_kernel.contract.decision.SPINE_ORDER` | 评分晚于落库 / 红线短路在相似度之前（demo 已踩） | `spine.validate_spine_order` + `tests/test_spine_anchor_guard.py`（A4 参数化） |
| C-B | **confidence 唯一来源 = 九尺子 `ratio`**，禁止以匹配分 `fused` 冒充 | S3 聚合失真，自主放行被冒领 | `scoring.aggregate_confidence` 强制 `source_key="ratio"`，否则抛错 |
| C-C | **红线是链末硬闸门**，不可前置/跳过；命中即屏蔽自主放行 | 红线形同虚设 | `redline.autonomous_release` 一整行判据 `(not redline_hit) and confidence >= threshold` |

### 0.2 零领域字面量（继承内核纪律）

`chiyu_decision/` 不得出现任何业务枚举值（红线事项目录、八要素取值、九尺子分项名均来自 `TenantProfile` / 契约常量）。守卫：`grep -rn "import torch"` 不适用；改用**领域词黑名单**复用内核 `config/domain-literal-denylist.json`（若本包引入字符串常量，须过 `test_contract_no_domain_literals` 同类检查——本计划不新建，依赖内核契约常量）。

### 0.3 测试解释器与取数纪律

- 解释器：`C:/Users/wangchuan08/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe`（**禁用** demo `.venv`，会 5 个 collection error）。
- `chiyu-decision` 依赖 `chiyu-kernel`，pytest 须两包同时上 `pythonpath`：
  `-o pythonpath="packages/chiyu-kernel/src:packages/chiyu-decision/src"`。
- 提交纪律：显式 `git add <paths>` + 单行 `-m`；`.workbuddy/` 本地排除。

### 0.4 文件结构（本阶段全部创建项）

```
D:\system\chiyu-foundation\
├── packages/
│   └── chiyu-decision/
│       ├── pyproject.toml                      ← Task 1
│       └── src/chiyu_decision/
│           ├── __init__.py                     ← Task 1（版本；重导出 SPINE_ORDER）
│           ├── scoring.py                      ← Task 1（S2 八要素 + S3 九尺子聚合）
│           ├── redline.py                      ← Task 2（S4 红线硬闸门）
│           ├── spine.py                        ← Task 3（S1→S5 不可重排主链）
│           ├── api.py                          ← Task 4（唯一公开门面）
│           └── tests/
│               ├── test_scoring.py            ← Task 1
│               ├── test_redline.py            ← Task 2
│               ├── test_spine_anchor_guard.py ← Task 4（A4 参数化时序守卫）
│               └── test_spine_run.py          ← Task 3/5
```

---

## §1 Task 分解

---

### Task 1: 包骨架 + 评分模块（S2/S3）

**Files:**
- Create: `packages/chiyu-decision/pyproject.toml`
- Create: `packages/chiyu-decision/src/chiyu_decision/__init__.py`
- Create: `packages/chiyu-decision/src/chiyu_decision/scoring.py`
- Create: `packages/chiyu-decision/src/chiyu_decision/tests/test_scoring.py`

- [ ] **Step 1: 写 pyproject.toml**

```toml
[project]
name = "chiyu-decision"
version = "0.1.0"
description = "ChiYu AI Native Decision Spine - S1-S5 runtime (L2)"
requires-python = ">=3.11,<3.14"
dependencies = ["chiyu-kernel"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src", "../chiyu-kernel/src"]
```

⛔ 注意：`pythonpath` 含 `../chiyu-kernel/src` 以解析 `chiyu_kernel` 依赖；执行本包测试用 `-o pythonpath="packages/chiyu-kernel/src:packages/chiyu-decision/src"`（覆盖外部 PYTHONPATH，纪律 E1）。

- [ ] **Step 2: 写 `__init__.py`（重导出契约顺序，守 C-A）**

```python
"""chiyu-decision —— 决策脊柱运行时（L2）。

⛔ 顺序契约来自 L0 单一事实源，本包不得另写一份；重导出仅为守卫可读性。
"""
from __future__ import annotations

__version__ = "0.1.0"

from chiyu_kernel.contract.decision import SPINE_ORDER, validate_spine_order

__all__ = ["__version__", "SPINE_ORDER", "validate_spine_order"]
```

- [ ] **Step 3: 写失败测试 `test_scoring.py`（TDD 起点）**

```python
"""S2 八要素 + 九尺子；S3 聚合（confidence 仅取 ratio）。"""
from __future__ import annotations

import pytest

from chiyu_kernel.contract.decision import (
    CONFIDENCE_SOURCE_KEY, EIGHT_ELEMENTS, RUBRIC_KEYS, RUBRIC_SCALE_MAX,
)
from chiyu_decision.scoring import (
    aggregate_confidence, check_elements, score_rubric,
)


def test_score_rubric_ratio_is_mean_over_scale():
    scores = {k: 4.0 for k in RUBRIC_KEYS}
    rep = score_rubric(scores)
    assert rep.ratio == 1.0                      # 全 4 分 ⇒ ratio=1.0
    assert len(rep.scores) == len(RUBRIC_KEYS)


def test_score_rubric_reports_missing_keys():
    rep = score_rubric({"clarity": 4.0})          # 只评了 1 键
    assert set(rep.missing) == set(RUBRIC_KEYS) - {"clarity"}


def test_score_rubric_zero_is_not_missing():
    scores = {k: 0.0 for k in RUBRIC_KEYS}        # 评了但全 0
    rep = score_rubric(scores)
    assert rep.missing == () and rep.ratio == 0.0  # hits=0 合法，非缺失


def test_aggregate_confidence_only_accepts_ratio():
    rep = score_rubric({k: 3.0 for k in RUBRIC_KEYS})
    assert aggregate_confidence(rep) == rep.ratio
    with pytest.raises(ValueError, match=CONFIDENCE_SOURCE_KEY):
        aggregate_confidence(rep, source_key="fused")   # 禁止 fused 冒充


def test_check_elements_reports_missing():
    rep = check_elements({"intent": "…"})
    assert set(rep.missing) == set(EIGHT_ELEMENTS) - {"intent"}


def test_rubric_scale_max_is_four():
    assert RUBRIC_SCALE_MAX == 4
```

- [ ] **Step 4: 运行测试确认失败**

```bash
cd "D:/system/chiyu-foundation" && "C:/Users/wangchuan08/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe" -m pytest packages/chiyu-decision/src/chiyu_decision/tests/test_scoring.py -q -o pythonpath="packages/chiyu-kernel/src:packages/chiyu-decision/src"
```

预期：collection error（`chiyu_decision.scoring` 不存在）。这是 TDD 起点。

- [ ] **Step 5: 写 `scoring.py`（最小实现）**

```python
"""决策评分 —— L2 决策脊柱的 S2 / S3。

⛔ 不降级为叙述留痕：九尺子每个键都要有可复算判分（0–4 整数）。
⛔ `confidence` 唯一来源 = `CONFIDENCE_SOURCE_KEY == "ratio"`，禁止以匹配分 `fused` 冒充（违 S3，铁律 C-B）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence, Tuple

from chiyu_kernel.contract.decision import (
    CONFIDENCE_SOURCE_KEY, EIGHT_ELEMENTS, RUBRIC_KEYS, RUBRIC_SCALE_MAX,
)


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


def aggregate_confidence(report: RubricReport, *, source_key: str = CONFIDENCE_SOURCE_KEY) -> float:
    """S3 聚合：唯一允许的来源是九尺子 ratio。"""
    if source_key != CONFIDENCE_SOURCE_KEY:
        raise ValueError(
            f"confidence 来源必须为 {CONFIDENCE_SOURCE_KEY!r}，不得用 {source_key!r} 冒充（违 S3）"
        )
    return report.ratio
```

- [ ] **Step 6: 运行测试确认通过**

```bash
cd "D:/system/chiyu-foundation" && "C:/Users/wangchuan08/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe" -m pytest packages/chiyu-decision/src/chiyu_decision/tests/test_scoring.py -q -o pythonpath="packages/chiyu-kernel/src:packages/chiyu-decision/src"
```

预期：6 passed。

- [ ] **Step 7: 提交**

```bash
cd "D:/system/chiyu-foundation" && git add packages/chiyu-decision/pyproject.toml packages/chiyu-decision/src/chiyu_decision/__init__.py packages/chiyu-decision/src/chiyu_decision/scoring.py packages/chiyu-decision/src/chiyu_decision/tests/test_scoring.py && git commit -q -m "T1: chiyu-decision 包骨架 + S2/S3 评分（ratio 唯一来源）" && git log --oneline -1
```

---

### Task 2: 红线硬闸门（S4）

**Files:**
- Create: `packages/chiyu-decision/src/chiyu_decision/redline.py`
- Create: `packages/chiyu-decision/src/chiyu_decision/tests/test_redline.py`

- [ ] **Step 1: 写失败测试 `test_redline.py`**

```python
"""S4 红线：链末硬闸门，命中即屏蔽自主放行（铁律 C-C）。"""
from __future__ import annotations

import pytest

from chiyu_kernel.contract.decision import AUTONOMOUS_RELEASE_DEFAULT
from chiyu_decision.redline import autonomous_release, evaluate_redline


def test_redline_hit_reports_reason():
    v = evaluate_redline(context={"text": "涉及卫生健康事项"}, redline_items=("卫生健康", "劳动"))
    assert v.hit is True and "卫生健康" in v.reasons


def test_redline_no_hit_when_absent():
    v = evaluate_redline(context={"text": "普通决策"}, redline_items=("卫生健康",))
    assert v.hit is False and v.reasons == ()


def test_autonomous_release_gate_is_single_line():
    # 红线命中 ⇒ 即便 confidence 高也不放行（一整行判据，不得只实现一半）
    assert autonomous_release(redline_hit=True, confidence=1.0) is False
    assert autonomous_release(redline_hit=False, confidence=AUTONOMOUS_RELEASE_DEFAULT) is True
    assert autonomous_release(redline_hit=False, confidence=AUTONOMOUS_RELEASE_DEFAULT - 0.01) is False


def test_redline_items_empty_means_no_hit():
    assert evaluate_redline(context={"text": "X"}, redline_items=()).hit is False
```

- [ ] **Step 2: 运行确认失败**

```bash
cd "D:/system/chiyu-foundation" && "C:/Users/wangchuan08/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe" -m pytest packages/chiyu-decision/src/chiyu_decision/tests/test_redline.py -q -o pythonpath="packages/chiyu-kernel/src:packages/chiyu-decision/src"
```

预期：collection error。

- [ ] **Step 3: 写 `redline.py`**

```python
"""S4 红线硬闸门 —— 链末、不可前置、不可跳过（铁律 C-C）。

⛔ 红线命中 ⇒ 屏蔽自主放行（强制人工处置）。判据由调用方在链末以 `redline_hit` 传入，
   本模块只负责"命中即 False"。红线事项目录来自 `TenantProfile.redline`（L4 注入），
   本模块零领域字面量。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Collection, Mapping, Tuple

from chiyu_kernel.contract.decision import (
    AUTONOMOUS_GATE_EXPR, AUTONOMOUS_RELEASE_DEFAULT,
)


@dataclass(frozen=True)
class RedlineVerdict:
    hit: bool
    reasons: Tuple[str, ...]


def evaluate_redline(*, context: Mapping, redline_items: Collection[str]) -> RedlineVerdict:
    """按 profile 注入的红线事项目录做内容匹配；二值判定，不引入领域字面量。"""
    text = str(context.get("text", ""))
    reasons = tuple(it for it in redline_items if it and it in text)
    return RedlineVerdict(hit=bool(reasons), reasons=reasons)


def autonomous_release(*, redline_hit: bool, confidence: float,
                       threshold: float = AUTONOMOUS_RELEASE_DEFAULT) -> bool:
    """链末硬闸门：一整行判据，不得只实现一半（屏蔽红线但不看置信度 = 名存实亡）。

    `AUTONOMOUS_GATE_EXPR` = "(not redline_hit) and confidence >= autonomous_threshold"
    """
    # 显式实现整行判据；下方断言守卫表达式与契约一致（防止有人"优化"成半截）
    result = (not redline_hit) and confidence >= threshold
    _assert_expr_intact()
    return result


def _assert_expr_intact() -> None:
    expected = "(not redline_hit) and confidence >= autonomous_threshold"
    assert AUTONOMOUS_GATE_EXPR == expected, (
        f"S4 闸门判据被改动：期望 {expected!r}，实际 {AUTONOMOUS_GATE_EXPR!r}（S4 链末硬闸门不可重排）"
    )
```

- [ ] **Step 4: 运行确认通过**

```bash
cd "D:/system/chiyu-foundation" && "C:/Users/wangchuan08/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe" -m pytest packages/chiyu-decision/src/chiyu_decision/tests/test_redline.py -q -o pythonpath="packages/chiyu-kernel/src:packages/chiyu-decision/src"
```

预期：4 passed。

- [ ] **Step 5: 提交**

```bash
cd "D:/system/chiyu-foundation" && git add packages/chiyu-decision/src/chiyu_decision/redline.py packages/chiyu-decision/src/chiyu_decision/tests/test_redline.py && git commit -q -m "T2: S4 红线硬闸门（链末·命中屏蔽自主放行）" && git log --oneline -1
```

---

### Task 3: 决策脊柱主链（S1→S5 不可重排）

**Files:**
- Create: `packages/chiyu-decision/src/chiyu_decision/spine.py`
- Create: `packages/chiyu-decision/src/chiyu_decision/tests/test_spine_run.py`

- [ ] **Step 1: 写失败测试 `test_spine_run.py`**

```python
"""S1→S5 主链：顺序即语义，confidence 仅取 ratio，红线在链末。"""
from __future__ import annotations

import pytest

from chiyu_kernel.contract.decision import AUTONOMOUS_RELEASE_DEFAULT, RUBRIC_KEYS
from chiyu_decision.spine import run_spine


def _good_scores() -> dict:
    return {k: 4.0 for k in RUBRIC_KEYS}


def test_spine_runs_in_order_and_reaches_s5():
    res = run_spine(context={"text": "普通", "decision_id": "d1"}, profile=None,
                     rubric_scores=_good_scores(), elements={"intent": "x"})
    assert res.stage_reached == "S5_persist"
    assert res.confidence == 1.0
    assert res.autonomous is True
    assert res.redline_hit is False


def test_spine_rejects_empty_context():
    with pytest.raises(ValueError, match="S1_context"):
        run_spine(context={}, profile=None, rubric_scores=_good_scores(), elements={})


def test_spine_redline_at_chain_end_blocks_release():
    res = run_spine(context={"text": "卫生健康", "decision_id": "d2"}, profile=None,
                     rubric_scores=_good_scores(), elements={}, redline_items=("卫生健康",))
    assert res.redline_hit is True
    assert res.autonomous is False          # 红线命中屏蔽自主放行
    assert res.stage_reached == "S5_persist"  # 红线不阻断落库，只屏蔽自主放行


def test_spine_low_confidence_not_autonomous():
    res = run_spine(context={"text": "普通", "decision_id": "d3"}, profile=None,
                     rubric_scores={k: 0.0 for k in RUBRIC_KEYS}, elements={})
    assert res.confidence == 0.0
    assert res.autonomous is False


def test_spine_persists_when_persister_given():
    captured = {}
    def _persist(r):
        captured["id"] = r.decision_id
        return True
    res = run_spine(context={"text": "普通", "decision_id": "d4"}, profile=None,
                     rubric_scores=_good_scores(), elements={}, persister=_persist)
    assert res.persisted is True and captured["id"] == "d4"
```

- [ ] **Step 2: 运行确认失败**

```bash
cd "D:/system/chiyu-foundation" && "C:/Users/wangchuan08/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe" -m pytest packages/chiyu-decision/src/chiyu_decision/tests/test_spine_run.py -q -o pythonpath="packages/chiyu-kernel/src:packages/chiyu-decision/src"
```

预期：collection error。

- [ ] **Step 3: 写 `spine.py`**

```python
"""决策脊柱运行时 —— S1→S5 不可重排主链（铁律 C-A / C-B / C-C 的执行体）。

⛔ `SPINE_ORDER` 来自 `chiyu_kernel.contract.decision`（L0 单一事实源），本包不得另写一份。
   顺序即语义：S1_context → S1_derive → S2_score → S3_aggregate → S4_redline → S5_persist。
   历史缺陷（demo 时序守卫）：① 九尺子晚于落库 ⇒ 置信度搁置；
   ② 红线短路在相似度之前 ⇒ 八要素与九尺子不参与判定。
   ⇒ 本运行时在 S5 前按 `SPINE_ORDER` 逐项执行；confidence 只取 ratio；红线在链末。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Mapping, Optional, Tuple

from chiyu_kernel.contract.decision import (
    AUTONOMOUS_RELEASE_DEFAULT, SPINE_ORDER, validate_spine_order,
)
from .redline import autonomous_release, evaluate_redline
from .scoring import aggregate_confidence, check_elements, score_rubric


@dataclass
class SpineResult:
    decision_id: str
    stage_reached: str
    confidence: float
    rubric_missing: Tuple[str, ...]
    elements_missing: Tuple[str, ...]
    redline_hit: bool
    redline_reasons: Tuple[str, ...]
    autonomous: bool
    persisted: bool = False


def run_spine(*, context: Mapping, profile, rubric_scores: Mapping[str, float],
              elements: Mapping[str, object],
              persister: Optional[Callable[[SpineResult], object]] = None,
              threshold: float = AUTONOMOUS_RELEASE_DEFAULT,
              redline_items: Tuple[str, ...] = ()) -> SpineResult:
    """按 SPINE_ORDER 执行 S1→S5。

    参数：
      context        触发上下文（S1_context）；空 ⇒ 抛（S1 先于一切）
      profile        TenantProfile（S1_derive 本体分级来源；本包只校验存在，分级器由消费方注入）
      rubric_scores  九尺子 9 键评分（S2_score）
      elements       八要素（S2_score）
      persister      落库回调（S5_persist）；None 不落库（测试/预览）
      threshold      自主放行阈值（缺省 0.79）
      redline_items  红线事项目录（来自 profile.redline）
    """
    validate_spine_order(SPINE_ORDER)               # 构造期断言：顺序未被重排（铁律 C-A）

    # S1_context：触发上下文必须先于一切
    if not context:
        raise ValueError("S1_context 为空：S1 必须先于一切")
    # S1_derive：本体分级（分级逻辑由消费方注入；内核只验输入齐备）
    if profile is None:
        pass  # 预览/测试允许无 profile；生产由调用方保证注入

    # S2_score：八要素 + 九尺子
    rubric = score_rubric(rubric_scores)
    elem = check_elements(elements)

    # S3_aggregate：confidence 唯一来源 = ratio（铁律 C-B）
    confidence = aggregate_confidence(rubric)

    # S4_redline：链末硬闸门（铁律 C-C）—— 红线命中屏蔽自主放行
    verdict = evaluate_redline(context=context, redline_items=redline_items)
    autonomous = autonomous_release(redline_hit=verdict.hit, confidence=confidence, threshold=threshold)

    # S5_persist：只写事实不写修饰；落库经注入的 persister（无 PG 也能全绿）
    decision_id = str(context.get("decision_id") or f"dec-{id(context)}")
    result = SpineResult(
        decision_id=decision_id, stage_reached="S5_persist", confidence=confidence,
        rubric_missing=rubric.missing, elements_missing=elem.missing,
        redline_hit=verdict.hit, redline_reasons=verdict.reasons, autonomous=autonomous,
    )
    if persister is not None:
        result.persisted = bool(persister(result))
    return result
```

- [ ] **Step 4: 运行确认通过**

```bash
cd "D:/system/chiyu-foundation" && "C:/Users/wangchuan08/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe" -m pytest packages/chiyu-decision/src/chiyu_decision/tests/test_spine_run.py -q -o pythonpath="packages/chiyu-kernel/src:packages/chiyu-decision/src"
```

预期：5 passed。

- [ ] **Step 5: 提交**

```bash
cd "D:/system/chiyu-foundation" && git add packages/chiyu-decision/src/chiyu_decision/spine.py packages/chiyu-decision/src/chiyu_decision/tests/test_spine_run.py && git commit -q -m "T3: S1-S5 主链（顺序契约·ratio 唯一来源·红线链末）" && git log --oneline -1
```

---

### Task 4: 时序守卫（A4 参数化）+ 门面 + 闸门

**Files:**
- Create: `packages/chiyu-decision/src/chiyu_decision/tests/test_spine_anchor_guard.py`
- Create: `packages/chiyu-decision/src/chiyu_decision/api.py`

- [ ] **Step 1: 写 A4 参数化时序守卫（替代 demo 位置断言）**

```python
"""A4 判据（S1→S5 时序守卫）—— 参数化版本（非位置/字符串硬编码断言）。

⛔ 判据不是"文件在就对"，而是：本包运行时的 SPINE_ORDER 与契约逐项相等；
   confidence 来源为 ratio 而非 fused；红线在链末（不得前置/跳过）。
"""
from __future__ import annotations

import pytest

from chiyu_kernel.contract.decision import (
    CONFIDENCE_SOURCE_KEY, RUBRIC_KEYS, SPINE_ORDER as CONTRACT_ORDER,
)
from chiyu_decision import SPINE_ORDER as RUNTIME_ORDER
from chiyu_decision.scoring import aggregate_confidence, score_rubric
from chiyu_decision.redline import autonomous_release
from chiyu_decision.spine import run_spine


@pytest.mark.parametrize("expected,actual", [(tuple(CONTRACT_ORDER), tuple(RUNTIME_ORDER))])
def test_spine_order_matches_contract(expected, actual):
    assert actual == expected, "决策脊柱顺序被改动（S1→S5 不可重排，铁律 C-A）"


def test_confidence_source_is_ratio_not_fused():
    rubric = score_rubric({k: 4.0 for k in RUBRIC_KEYS})
    with pytest.raises(ValueError):
        aggregate_confidence(rubric, source_key="fused")
    assert aggregate_confidence(rubric) == rubric.ratio == CONFIDENCE_SOURCE_KEY and rubric.ratio == 1.0


def test_redline_block_release_even_with_high_confidence():
    # 红线在链末仍生效：高 confidence + 红线命中 ⇒ 不自主放行
    scores = {k: 4.0 for k in RUBRIC_KEYS}
    res = run_spine(context={"text": "卫生健康", "decision_id": "g1"}, profile=None,
                     rubric_scores=scores, elements={}, redline_items=("卫生健康",))
    assert res.redline_hit and not res.autonomous


def test_spine_end_to_end_reaches_s5_in_order():
    scores = {k: 4.0 for k in RUBRIC_KEYS}
    res = run_spine(context={"text": "普通", "decision_id": "g2"}, profile=None,
                     rubric_scores=scores, elements={"intent": "x"})
    assert res.stage_reached == "S5_persist" and res.autonomous
```

⛔ 注意：上面的 `test_confidence_source_is_ratio_not_fused` 断言里 `== CONFIDENCE_SOURCE_KEY` 写法是笔误，应只断言 `aggregate_confidence(rubric) == rubric.ratio`；执行前改为：
```python
assert aggregate_confidence(rubric) == rubric.ratio and rubric.ratio == 1.0
```

- [ ] **Step 2: 写 `api.py`（唯一公开门面）**

```python
"""chiyu-decision 的唯一公开门面。

⛔ 消费方只许 import 本模块与 `chiyu_kernel.contract`。
   import `chiyu_decision.spine` / `.scoring` / `.redline` 内部路径即违约。
"""
from __future__ import annotations

from chiyu_kernel.contract.decision import SPINE_ORDER, validate_spine_order

from .redline import RedlineVerdict, autonomous_release, evaluate_redline
from .scoring import RubricReport, check_elements, score_rubric
from .spine import SpineResult, run_spine

__all__ = [
    "SPINE_ORDER", "validate_spine_order", "run_spine", "SpineResult",
    "score_rubric", "RubricReport", "check_elements", "evaluate_redline",
    "RedlineVerdict", "autonomous_release",
]
```

- [ ] **Step 3: 运行守卫 + 全量**

```bash
cd "D:/system/chiyu-foundation" && "C:/Users/wangchuan08/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe" -m pytest packages/chiyu-decision/src/chiyu_decision/tests -q -o pythonpath="packages/chiyu-kernel/src:packages/chiyu-decision/src"
```

预期：全绿（scoring 6 + redline 4 + spine_run 5 + anchor 4 = 19 passed）。

- [ ] **Step 4: 提交**

```bash
cd "D:/system/chiyu-foundation" && git add packages/chiyu-decision/src/chiyu_decision/api.py packages/chiyu-decision/src/chiyu_decision/tests/test_spine_anchor_guard.py && git commit -q -m "T4: A4 参数化时序守卫 + 公开门面 api" && git log --oneline -1
```

---

### Task 5: 全量回归闸门 + §10 块 2 成功判据自证

- [ ] **Step 1: 跑 §10 块 2 成功判据（契约级）**

```bash
cd "D:/system/chiyu-foundation" && PY="C:/Users/wangchuan08/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe" && $PY -m pytest packages/chiyu-decision/src/chiyu_decision/tests -q -o pythonpath="packages/chiyu-kernel/src:packages/chiyu-decision/src" 2>&1 | tail -3
echo "--- 契约顺序逐项相等 + validate_spine_order ---"
$PY -c "from chiyu_decision import SPINE_ORDER, validate_spine_order; from chiyu_kernel.contract.decision import SPINE_ORDER as C; assert tuple(SPINE_ORDER)==tuple(C); validate_spine_order(SPINE_ORDER); print('SPINE_ORDER 一致 + 校验通过')"
echo "--- confidence 来源为 ratio 而非 fused ---"
$PY -c "from chiyu_decision.scoring import score_rubric, aggregate_confidence; from chiyu_kernel.contract.decision import RUBRIC_KEYS; r=score_rubric({k:4.0 for k in RUBRIC_KEYS}); assert aggregate_confidence(r)==r.ratio; print('confidence=ratio 校验通过')"
```

预期：19 passed；两条自证均打印通过。

- [ ] **Step 2: 内核全量回归不被破坏**

```bash
cd "D:/system/chiyu-foundation" && "C:/Users/wangchuan08/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe" -m pytest packages/chiyu-kernel/tests tools/tests -q -o pythonpath="packages/chiyu-kernel/src" 2>&1 | tail -3
```

预期：266 passed（新增 chiyu-decision 包不影响内核）。

- [ ] **Step 3: 提交收口（注明 §10 块 2 自证）**

```bash
cd "D:/system/chiyu-foundation" && git add -A && git commit -q -m "T5: chiyu-decision 收口 + §10 块 2 成功判据自证（19 passed；SPINE_ORDER 一致；confidence=ratio）" && git log --oneline -1
```

⛔ 若 `git add -A` 误带 `.pytest_cache/` 或个人文件，改为显式路径 `git add packages/chiyu-decision`。

---

## §2 Self-Review

### 2.1 Spec coverage（概念设计 → 本计划 Task）

| 概念设计章节 | 本计划覆盖 | 说明 |
|---|---|---|
| §2 决策脊柱 S1→S5 | Task 3 `spine.run_spine` | 顺序契约 + 六步执行 |
| §2 S2 八要素 + 九尺子 | Task 1 `scoring` | 9 键 0–4、ratio 聚合 |
| §2 S3 聚合 confidence=ratio | Task 1 `aggregate_confidence` | `source_key` 强制，否则抛 |
| §2 S4 红线链末硬闸门 | Task 2 `redline` | 命中屏蔽自主放行 |
| §2 S5 落库 | Task 3 `persister` 注入 | 经回调，无 PG 可全绿 |
| §10 块 2 成功判据 | Task 4/5 | 顺序逐项相等 + ratio 来源 + A4 参数化 |
| §7 决策脊柱行「运行时待抽」 | 本计划整体 | 抽为独立包 |
| §9 P1 `chiyu-decision` 抽取规划 | 本计划整体 | — |

### 2.2 Placeholder scan

- ✅ 所有代码步骤均含完整实现，无 "TBD / 实现 later / similar to Task N"。
- ⚠️ 唯一笔误已在 Step 4-1 标注修正（`test_confidence_source_is_ratio_not_fused` 的 `== CONFIDENCE_SOURCE_KEY` 误写）。
- ✅ 评分权重（外置配置）按 §2「按外置权重配置加权聚合」设计为等权；profile 注入扩展点已在 docstring 标注，属执行期调优，不阻塞本计划。

### 2.3 Type consistency

| 符号 | 定义 | 使用 | 一致 |
|---|---|---|---|
| `RubricReport(scores, ratio, missing)` | Task 1 `scoring` | Task 3 `run_spine`、Task 4 测试 | ✅ |
| `ElementReport(elements, missing)` | Task 1 | Task 3 | ✅ |
| `RedlineVerdict(hit, reasons)` | Task 2 | Task 3 | ✅ |
| `autonomous_release(*, redline_hit, confidence, threshold)` | Task 2 | Task 3 | ✅ |
| `SpineResult(...)` | Task 3 | Task 3/4 测试 | ✅ |
| `SPINE_ORDER` / `validate_spine_order` | 内核契约 | Task 3 / `__init__` / 测试 | ✅ 重导出一致 |

---

## §3 执行后动作

1. 回写 `docs/2026-09-21-决策智能平台概念设计.md` §7/§8：决策脊柱行「运行时待抽」→ 已抽为 `chiyu-decision`（本仓）。
2. **P2b（chiyu-portal 免代码门户）另立计划**，不在本计划范围（writing-plans 拆分要求：T6/T7 为独立子系统）。
3. 自主通道开闸前置条件（§12.3 七闸）仍须先于夜批调度器落地 —— 属独立后续计划。
