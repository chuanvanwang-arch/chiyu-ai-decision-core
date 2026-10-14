"""SHA-256 链式审计（SKILL #10 的机制层）—— ★ 内核新建，demo 无此目录。

⛔ 为什么是链式而不是逐条哈希
────────────────────────────
逐条哈希只能证明"这条没被改"；链式还能证明"**没有中间记录被删掉**"——
后者才是审计被绕过的常见形式（删掉不利记录，其余保持自洽）。

    h_i = sha256( h_{i-1} + canonical(record_i) )，h_0 = "0"*64

canonical 规则：按 AUDIT_REQUIRED_FIELDS 顺序取字段，缺失即 "∅"（占位符而非跳过
—— 跳过会让"删字段"与"原值就是空"产生同一哈希，蓄意者可借此抹除字段）。
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Iterable, List, Mapping, Sequence

from chiyu_kernel.contract import (
    AUDIT_GENESIS_HASH,
    AUDIT_HASH_ALGO,
    AUDIT_REQUIRED_FIELDS,
)

EMPTY_PLACEHOLDER = "∅"


def canonical(record: Mapping, fields: Sequence[str] = AUDIT_REQUIRED_FIELDS) -> str:
    payload = {f: record.get(f, EMPTY_PLACEHOLDER) for f in fields}
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def chain_hash(prev_hash: str, record: Mapping) -> str:
    if AUDIT_HASH_ALGO != "sha256":
        raise ValueError(f"未支持的审计哈希算法：{AUDIT_HASH_ALGO}")
    h = hashlib.sha256()
    h.update(prev_hash.encode("utf-8"))
    h.update(canonical(record).encode("utf-8"))
    return h.hexdigest()


def build_chain(records: Iterable[Mapping]) -> List[str]:
    prev = AUDIT_GENESIS_HASH
    out: List[str] = []
    for r in records:
        prev = chain_hash(prev, r)
        out.append(prev)
    return out


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    checked: int
    first_bad_index: int = -1
    reason: str = ""


def verify_chain(records: Sequence[Mapping], expected: Sequence[str]) -> VerifyResult:
    """重算并比对。返回首个失配位置（-1 表示全链通过）。"""
    if len(records) != len(expected):
        return VerifyResult(False, min(len(records), len(expected)), -1,
                            f"长度不一致：records={len(records)} expected={len(expected)}")
    prev = AUDIT_GENESIS_HASH
    for i, r in enumerate(records):
        prev = chain_hash(prev, r)
        if prev != expected[i]:
            return VerifyResult(False, i + 1, i, f"第 {i} 条哈希失配")
    return VerifyResult(True, len(records))


# ══ 链加固（Batch-1b-2 prov_chain；对拍 CRM provenance.js seal/FORKED/tail）══
def seal_chain(records: Sequence[Mapping]) -> Mapping[str, object]:
    """对链钉桩：{'head_checksum': 末条哈希, 'entry_count': 条数}。

    ⛔ 两字段**成对**生效（PROV_CHAIN_INVARIANTS.seal_binds_head_and_count）：
    只钉头可被截尾重算绕过；只钉条数可被就地重算绕过。
    """
    hashes = build_chain(records)
    return {"head_checksum": hashes[-1] if hashes else AUDIT_GENESIS_HASH,
            "entry_count": len(hashes)}


def verify_sealed(records: Sequence[Mapping], seal: Mapping[str, object]) -> VerifyResult:
    """按封条整链校验（CRM verifySeal 的域无关化）。

    判序（先截尾/加尾，后就地篡改——CRM 同序）：
      ① 条数 != seal.entry_count ⇒ tampered（截尾/加尾，reason=seal_count_mismatch）；
      ② 重算链中途失配 ⇒ tampered（reason=chain_break_at_<i>）；
      ③ 条数同但头哈希 != seal.head_checksum ⇒ tampered
        （就地篡改后重算出自洽链也拦——PROV_CHAIN_INVARIANTS 同名判据）；
      ④ 全对 ⇒ ok。
    """
    count = seal.get("entry_count")
    if count is None or len(records) != count:
        return VerifyResult(False, min(len(records), int(count or 0)), -1,
                            "seal_count_mismatch")
    prev = AUDIT_GENESIS_HASH
    for i, r in enumerate(records):
        prev = chain_hash(prev, r)
    if prev != seal.get("head_checksum"):
        return VerifyResult(False, len(records), -1, "seal_head_mismatch")
    return VerifyResult(True, len(records))


def verify_tail(records: Sequence[Mapping], prev_anchor: str) -> VerifyResult:
    """增量校验：从已知锚续链（PROV_CHAIN_INVARIANTS.tail_verification_continues_from_anchor）。

    :param prev_anchor: 已验证前缀的末条哈希（或 GENESIS）。禁只验尾部自身——
        不接锚的尾部自洽校验挡不住「锚点前历史被换」。
    :returns: ok 恒成立（纯续链重算）；``reason`` 携带**续链后新头哈希**，
        供调用方与自有锚点比对（不匹配即 broken_head，映射 CHAIN_VERIFY_STATUSES）。
    """
    prev = prev_anchor
    for i, r in enumerate(records):
        prev = chain_hash(prev, r)
    return VerifyResult(True, len(records), -1, prev)


def find_forks(links: Iterable[Sequence[str]]) -> List[str]:
    """分叉检出：同一 prev 锚出现两条不同后继 ⇒ 该 prev 已分叉（CRM FORKED 判据）。

    :param links: (previous_checksum, checksum) 二元组序列（由调用方从任意
      存储形态提取——基座不绑行 schema）。
    :returns: 分叉的 prev 锚列表（去重、按首现序）。
    """
    seen: dict = {}
    for link in links:
        if not link or len(link) < 2:
            continue
        prev, cur = link[0], link[1]
        seen.setdefault(prev, set()).add(cur)
    return [prev for prev, children in seen.items() if len(children) > 1]


__all__ = ["canonical", "chain_hash", "build_chain", "verify_chain",
           "VerifyResult", "EMPTY_PLACEHOLDER",
           "seal_chain", "verify_sealed", "verify_tail", "find_forks"]
