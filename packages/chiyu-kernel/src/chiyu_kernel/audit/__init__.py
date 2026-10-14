"""审计子系统 —— SHA-256 链式审计（SKILL #10 机制层；★ 内核新建，demo 无此目录）。

Batch-1b-2（2026-10-14）链加固：seal_chain / verify_sealed / verify_tail / find_forks
（对拍 CRM provenance.js seal + FORKED + 增量续链；词汇面见 contract.audit PROV_CHAIN_*）。
"""
from .chain import (
    EMPTY_PLACEHOLDER,
    VerifyResult,
    build_chain,
    canonical,
    chain_hash,
    find_forks,
    seal_chain,
    verify_chain,
    verify_sealed,
    verify_tail,
)

__all__ = ["EMPTY_PLACEHOLDER", "VerifyResult", "build_chain",
           "canonical", "chain_hash", "verify_chain",
           "seal_chain", "verify_sealed", "verify_tail", "find_forks"]
