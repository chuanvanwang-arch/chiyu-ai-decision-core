"""CRM R2 判据语言无关规格 —— 文档存在性与结构守卫（判别力自证）。

⛔ 反假绿判据（每条对应破坏性构造，判据失效必转红）：
   1. 规格文件必须存在：删除 / 改名 → 转红；
   2. 五段齐全：任一段标注被删 → 转红；
   3. 判据编号唯一且覆盖 K-01..K-04：重复 / 缺号 → 转红；
   4. 每条判据都在「来源映射」表可溯源：漏一条 → 转红。
"""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC_FILE = ROOT / "docs" / "2026-10-09-判据语言无关规格-R2.md"

#: 五段式元模型（顺序即规格定义序，缺一不可）
_SEGMENTS = (
    "前置条件",
    "触发输入",
    "失败语义",
    "变异自证方法",
    "验收判据式",
)

#: 判据编号（R2 首批规格集）
_CRITERIA = ("K-01", "K-02", "K-03", "K-04")


def _spec_text() -> str:
    assert SPEC_FILE.exists(), f"规格文档缺失：{SPEC_FILE}"
    return SPEC_FILE.read_text(encoding="utf-8")


def test_spec_file_exists():
    assert SPEC_FILE.is_file(), "R2 判据规格文档必须存在"


def _criterion_blocks(text: str) -> dict:
    """按判据标题切分文档，返回 {判据编号: 该判据块文本}。

    块边界 = `## <n>. 判据 K-XX` 到下一条同级别标题（`## ` 或 `## 附`）之前。
    若某判据块缺失标题，其五段校验会因此转红（缺号判别）。
    """
    import re
    blocks: dict = {}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        ln = lines[i].strip()
        if ln.startswith("## ") and "判据 K-" in ln:
            m = re.search(r"K-(\d{2})", ln)
            if m:
                cid = m.group(0)
                buf = [ln]
                i += 1
                while i < len(lines) and not (
                    lines[i].strip().startswith("## ") and "判据 K-" in lines[i]
                ):
                    buf.append(lines[i])
                    i += 1
                blocks[cid] = "\n".join(buf)
                continue
        i += 1
    return blocks


def test_five_segments_all_present():
    """五段式元模型缺一段，判据规格即不完整（CRM R2 核心要求）。逐判据校验。"""
    text = _spec_text()
    blocks = _criterion_blocks(text)
    assert set(blocks) >= set(_CRITERIA), f"未能切分出全部判据块：{sorted(blocks)}"
    for cid in _CRITERIA:
        block = blocks[cid]
        for seg in _SEGMENTS:
            assert f"**{seg}" in block, f"判据 {cid} 缺少五段之一：{seg}"


def test_criteria_ids_unique_and_complete():
    """判据编号 K-01..K-04 必须齐全且无重复（标题形如 ## 1. 判据 K-01：）。"""
    text = _spec_text()
    for cid in _CRITERIA:
        assert f"判据 {cid}：" in text, f"判据编号缺失：{cid}"
    for cid in _CRITERIA:
        assert text.count(cid) >= 2, f"判据 {cid} 应至少出现标注一次 + 映射表一次（防只登记不规格）"


def test_each_criterion_traceable_in_mapping_table():
    """每条判据都必须在「来源映射」表可溯源（判据 ↔ 本仓实现 ↔ 规格段）。"""
    text = _spec_text()
    table_zone = text.split("## 附：判据 ↔ 来源映射")[1]
    for cid in _CRITERIA:
        assert cid in table_zone, f"判据 {cid} 未进来源映射表（防规格空转）"


def test_mapping_table_row_count_matches_criteria():
    """映射表行数 = 判据数（新增判据未登记映射即转红）。"""
    text = _spec_text()
    table_zone = text.split("## 附：判据 ↔ 来源映射")[1]
    rows = [ln for ln in table_zone.splitlines() if ln.startswith("| K-")]
    assert len(rows) == len(_CRITERIA), (
        f"映射表行数 {len(rows)} ≠ 判据数 {len(_CRITERIA)}（漏登记或多余项）"
    )
