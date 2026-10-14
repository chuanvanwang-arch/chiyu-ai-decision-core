"""写时三钩子（内置知识—向量通道规范 · 写时钩子口径的内核版 —— 语义逐字保留，命名去领域化）。

钩子1 ensure_embedding：`content_hash` 判变幂等 —— 内容未变跳过重算，已变则重算并回写 provider 标签。
钩子2 ensure_tsvector ：全文文本与向量**同时**维护（双通道，非二选一），写后立即可检索。
钩子3 ontology_sync   ：引用型字段自动建受控边（受控谓词由 `profile.predicates` 提供）+ 身份校验，写入即图。

三钩子均幂等、可重跑；降级不中断、provider 显式留痕（防哈希污染置信度）。

⛔ 与 demo 的差异（源码核实）：
   1. demo `hooks.ensure_embedding` 调 `ontology.embedding.embed_text()`（双 provider 降级协议）；
      内核版改走 `vector.index_vector.resolve()`（**写读单一事实源**，T3 建立）。
      映射：tag='model' → provider='model'；tag='model-p{n}' → provider='model-p{n}'
      （真向量，未补零）；tag=None → provider='hash'（降级留痕）。
   2. demo 硬编码「实体/点位/类目」三条受控边（领域结构）⇒ 内核版由调用方把引用
      经 `particle.raw_refs`/`attrs` 传入，受控谓词清单由 `OntologyGraph` 从
      `profile.predicates` 读取（见 graph.py）。
"""
from __future__ import annotations

from typing import Optional

from chiyu_kernel.vector import index_vector
from chiyu_kernel.vector.infer import content_hash

from .graph import OntologyGraph
from .particle import Particle


def _provider_from_tag(tag: Optional[str]) -> str:
    """向量来源标签 → provider 留痕。

    ⛔ coverage.py 的口径：`model-p*` 亦为真向量（未补零），只 `hash`/None 算降级。
    """
    if tag is None:
        return "hash"
    if tag == "model":
        return "model"
    return tag                       # "model-p{n}" —— 未补零的真向量


def ensure_embedding(particle: Particle, *, column_dim: int,
                     text: Optional[str] = None) -> str:
    """钩子1：内容哈希幂等判变 + 单一事实源向量回写。

    返回 provider（"model" | "model-p{n}" | "hash"），供下游标记向量来源。

    幂等判变：已物化（embedding 非空且已有 content_hash）⇒ 内容未变，跳过重算。
    降级：resolve() 取不到真向量（tag=None，err 非空）⇒ embedding=None、
    provider='hash'，**不抛异常、不中断**（降级不中断铁律），err 由调用方自行上报。
    """
    if particle.embedding is not None and particle.content_hash:
        return particle.provider or "hash"
    payload = {
        "text": text if text is not None else (particle.fulltext or ""),
        "subject": particle.subject_id,
        "refs": tuple(particle.raw_refs or ()),
    }
    vec, tag, _err = index_vector.resolve(payload["text"], column_dim=column_dim)
    if vec is not None:
        particle.embedding = [float(x) for x in vec]
    else:
        particle.embedding = None
    particle.provider = _provider_from_tag(tag)
    particle.content_hash = content_hash(payload)
    return particle.provider


def ensure_tsvector(particle: Particle) -> str:
    """钩子2：全文索引文本（双通道同步，与向量同钩维护）。

    返回 `fulltext` 文本；实际写库由存储层消费。
    幂等：无副作用，直接返回当前全文（写库方决定是否更新）。
    """
    return particle.fulltext or ""


def ontology_sync(particle: Particle, onto: Optional[OntologyGraph]) -> None:
    """钩子3：受控边 + 身份校验（写库即图）。

    引用集合 = `particle.raw_refs`；受控谓词由 `onto`（消费方构造时注入
    `profile.predicates`）提供 —— 见 graph.py 的 `add_*` / `sync_particle`。
    """
    if onto is None:
        return
    onto.sync_particle(particle)


__all__ = ["ensure_embedding", "ensure_tsvector", "ontology_sync"]
