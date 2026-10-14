"""建表 DDL 生成器 —— **由 TenantProfile 驱动**（内核与 demo 的关键差异）。

⛔ 与 demo 的差异（设计 §0.3 的落地）
────────────────────────────────────
demo 的 `db/schema.py` 把 `PARTICLE_TYPES` / `K_PREDICATES` 写成模块常量，等于把
群诉域焊进存储层。本模块改为：粒子类型 CHECK、知识谓词 CHECK 全部由 profile 生成。

    ddl(profile)  →  CHECK (type IN ('...', ...))
                      ↑ 这些值来自 profile，源码里零字面量

⛔ 保留的两条硬约束（各有可执行判据）：
  ① **零建表铁则**：不为每类对象开表。粒子 1 张表、属性 1 张表、边 1 张表。
  ② **禁自由字段**：业务粒子表 / 边表**零 jsonb 列**。例外仅 `event.payload`、
     `event.context_facts`、`spec.definition`（三者语义上异构，理由见 `assert_no_free_jsonb`）。
     demo 已把该否决固化为可执行判据，本模块照搬。

⛔ 禁 DELETE：本包不在 DDL 层提供 `DROP`（那是运维/测试动作），删除一律走墓碑语义
   （`status='deleted'` + `updated_at`）。硬删除拦截见 `pg_store.assert_no_hard_delete`。
"""
from __future__ import annotations

from typing import List

from chiyu_kernel.contract import (
    ATTR_TYPES,
    EDGE_LAYERS,
    LAYERS,
    TenantProfile,
    VECTOR_DIM,
)
from chiyu_kernel.contract.memory import MEMORY_KINDS

from .dsn import assert_safe_identifier

_ALLOWED_JSONB_TABLES = ("event", "spec")


def _q(schema: str, table: str) -> str:
    return f"{schema}.{table}"


def ddl_statements(profile: TenantProfile, schema: str) -> List[str]:
    """幂等 DDL（全部 IF NOT EXISTS）。schema 名经白名单校验，粒子/谓词由 profile 注入。"""
    s = assert_safe_identifier(schema, what="schema")
    ptype_chk = profile.particle_types.sql_check()
    attr_chk = ", ".join(f"'{t}'" for t in ATTR_TYPES)
    edge_layer_chk = ", ".join(f"'{t}'" for t in EDGE_LAYERS)
    layer_chk = ", ".join(f"'{t}'" for t in LAYERS)
    kind_chk = ", ".join(f"'{t}'" for t in MEMORY_KINDS)
    return [
        f"CREATE SCHEMA IF NOT EXISTS {s}",
        f"""
        CREATE TABLE IF NOT EXISTS {_q(s, 'particle')} (
          particle_id  text        NOT NULL,
          type         text        NOT NULL,
          layer        text        NOT NULL,
          label        text,
          status       text,
          ts           timestamptz,
          created_at   timestamptz NOT NULL DEFAULT now(),
          updated_at   timestamptz NOT NULL DEFAULT now(),
          vec          vector({VECTOR_DIM}),
          provider     text,
          ai_generated boolean     NOT NULL DEFAULT false,
          CONSTRAINT particle_pkey      PRIMARY KEY (particle_id),
          CONSTRAINT particle_type_chk  CHECK (type IN ({ptype_chk})),
          CONSTRAINT particle_layer_chk CHECK (layer IN ({layer_chk}))
        )""",
        f"""
        CREATE TABLE IF NOT EXISTS {_q(s, 'particle_attribute')} (
          particle_id text        NOT NULL REFERENCES {_q(s, 'particle')}(particle_id),
          attr        text        NOT NULL,
          attr_type   text        NOT NULL,
          value_text  text,
          value_num   double precision,
          value_bool  boolean,
          value_ts    timestamptz,
          value_set   text[],
          source      text        NOT NULL,
          confidence  real,
          model       text,
          observed_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT particle_attribute_pkey PRIMARY KEY (particle_id, attr, source),
          CONSTRAINT particle_attribute_type_chk   CHECK (attr_type IN ({attr_chk})),
          CONSTRAINT particle_attribute_source_chk CHECK (source IN ('human','rule','ai','llm','engine'))
        )""",
        f"""
        CREATE TABLE IF NOT EXISTS {_q(s, 'graph_edge')} (
          edge_id             bigserial PRIMARY KEY,
          from_id             text NOT NULL,
          to_id               text NOT NULL,
          predicate           text NOT NULL,
          layer               text NOT NULL,
          serves_dims         text[],
          relation_confidence real,
          edge_source         text NOT NULL,
          evidence_ref        text,
          valid_from          timestamptz,
          valid_until         timestamptz,
          weight              real,
          ai_reasoning_trace  text,
          ts                  timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT graph_edge_uniq      UNIQUE (from_id, to_id, predicate),
          CONSTRAINT graph_edge_layer_chk CHECK (layer IN ({edge_layer_chk})),
          CONSTRAINT graph_edge_source_chk CHECK (edge_source IN ('human','rule','ai','llm','engine','manual'))
        )""",
        f"""
        CREATE TABLE IF NOT EXISTS {_q(s, 'edge_attribute')} (
          edge_id    bigint NOT NULL REFERENCES {_q(s, 'graph_edge')}(edge_id),
          attr       text   NOT NULL,
          attr_type  text   NOT NULL,
          value_text text,
          value_num  double precision,
          value_bool boolean,
          value_ts   timestamptz,
          value_set  text[],
          CONSTRAINT edge_attribute_pkey     PRIMARY KEY (edge_id, attr),
          CONSTRAINT edge_attribute_type_chk CHECK (attr_type IN ({attr_chk}))
        )""",
        f"""
        CREATE TABLE IF NOT EXISTS {_q(s, 'event')} (
          seq           bigserial PRIMARY KEY,
          id            text        NOT NULL UNIQUE,
          ts            timestamptz NOT NULL,
          domain        text        NOT NULL,
          event_type    text        NOT NULL,
          stage         text,
          subject_id    text,
          decision_id   text,
          agent_id      text,
          parent_id     text,
          dims          text[],
          context_facts jsonb,
          payload       jsonb
        )""",
        f"""
        CREATE TABLE IF NOT EXISTS {_q(s, 'spec')} (
          spec_key   text PRIMARY KEY,
          spec_type  text NOT NULL,
          definition jsonb NOT NULL,
          version    text NOT NULL,
          updated_at timestamptz NOT NULL DEFAULT now()
        )""",
        f"CREATE INDEX IF NOT EXISTS particle_type_idx   ON {_q(s,'particle')} (type)",
        f"CREATE INDEX IF NOT EXISTS particle_layer_idx  ON {_q(s,'particle')} (layer)",
        f"CREATE INDEX IF NOT EXISTS particle_status_idx ON {_q(s,'particle')} (type, status)",
        f"CREATE INDEX IF NOT EXISTS pattr_attr_idx      ON {_q(s,'particle_attribute')} (attr)",
        f"CREATE INDEX IF NOT EXISTS edge_from_idx       ON {_q(s,'graph_edge')} (from_id)",
        f"CREATE INDEX IF NOT EXISTS edge_to_idx         ON {_q(s,'graph_edge')} (to_id)",
        f"CREATE INDEX IF NOT EXISTS edge_pred_idx       ON {_q(s,'graph_edge')} (predicate)",
        f"CREATE INDEX IF NOT EXISTS edge_layer_idx      ON {_q(s,'graph_edge')} (layer)",
        f"CREATE INDEX IF NOT EXISTS event_decision_idx  ON {_q(s,'event')} (decision_id)",
        f"CREATE INDEX IF NOT EXISTS event_subject_idx   ON {_q(s,'event')} (subject_id)",
        # memory_kind 由 kind 属性区分（不炸两表）——种子进 spec
        f"""
        INSERT INTO {_q(s,'spec')} (spec_key, spec_type, definition, version)
        VALUES ('memory_kinds', 'enum',
                '{{"values": [{", ".join(f'"{k}"' for k in MEMORY_KINDS)}]}}'::jsonb, '1')
        ON CONFLICT (spec_key) DO UPDATE SET definition = EXCLUDED.definition
        """,
    ]


def vector_index_ddl(schema: str) -> List[str]:
    """向量索引单列（HNSW 建索引受 maintenance_work_mem 影响，失败不应阻断建表）。"""
    s = assert_safe_identifier(schema, what="schema")
    return [
        f"CREATE INDEX IF NOT EXISTS particle_vec_hnsw ON {_q(s,'particle')} "
        f"USING hnsw (vec vector_cosine_ops)",
    ]


def assert_no_free_jsonb(schema_tables: dict) -> List[str]:
    """可执行判据：业务粒子表 / 边表不得有 jsonb 列。返回违规列表。

    demo 已把用户对「N 张宽表 + payload JSONB」的否决固化成这个函数。
    ⛔ 本判据必须**保持可执行**——写成文档条款就无人能拦住下一次加 jsonb。
    """
    violations: List[str] = []
    for table, cols in schema_tables.items():
        if table in _ALLOWED_JSONB_TABLES:
            continue
        for col in cols:
            name, _, typ = col.partition(":")
            if typ.strip().lower() in ("jsonb", "json"):
                violations.append(f"{table}.{name}:{typ}")
    return violations


__all__ = ["ddl_statements", "vector_index_ddl", "assert_no_free_jsonb"]
