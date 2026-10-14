# foundation R2–R14 落实 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **来源设计稿（已批准）**：`docs/plans/2026-10-09-foundation-R2-R14落实方案.md`
> **契约校验**：`valid=true`，11 契约块 / 3 agent 全覆盖，判别力自证通过（3 坏块各 `exit=1`）

**Goal:** 让foundation 对三个消费方形成「能力有出口、契约有守卫、违规不必靠自觉」的可依赖底座，落实 APS 回信 R2/R4/R5/R8–R14 共 11 项。

**Architecture:** 严格加法 + 弃用标注（零既存代码失效）。三批次编排，每批单一意图、可独立验收与二分归因：①门面纯新增（零行为变更）②store 加法（含唯一真实行为风险项 R9）③命名与披露。

**Tech Stack:** Python 3.11+、pytest、psycopg2（将被解耦）、Git（零 remote，分层提交）

---

## ⛔ 实施前必读（违反即返工）

### 1. 必须先取组合回归基线

**HEAD 停在 09-27，但 WS6/WS2 等 10-09 能力已落盘未提交。**
⇒ 不取基线就动手，回归一旦变红**无法判断是本次改造引入还是既有漂移**。

```bash
cd /d/system/chiyu-foundation && \
C:/Users/wangchuan08/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe -m pytest \
  packages/chiyu-kernel/tests tools/tests packages/chiyu-decision/src/chiyu_decision/tests -q 2>&1 | tail -15
```

**期望**：记录末尾 `N passed`（当前记忆基线 434 passed，以实跑为准）。
**若基线本身有红**：⛔ 停下报用户，**不得**在有未知红的情况下叠加改造。

### 2. 纪律红线

| 纪律 | 内容 |
|---|---|
| 验收集合 | **跑组合命令，不跑单包**（本项目多次踩过"单跑绿、组合塌"） |
| 假绿防范 | 每任务**必须变异自证**：故意删判据分支 ⇒ 必须转红 ⇒ 还原 |
| 退出码判据 | **禁止经管道**（`\| head` 会取到 `head` 的退出码）；须 `> /dev/null; echo $?` |
| 路径 | 契约校验器**必须用 `C:/` 绝对路径**（`/tmp`、`~` 会被解析成 `D:\...`） |
| manifest | ⛔ **不改 `contract/*.py`** ⇒ 不触发 `manifest.json` 重生成 |
| git | 显式路径 `git add`，⛔ 禁 `git add -A`；单行 `-m`，前缀 `T<n>:`，尾部附实测计数；零 remote |
| 本机| **无 `make`** ⇒ 验证 Makefile 目标须直接实跑其命令行 |
| 既有违规 | `check_cython_friendly` 长期报 1 条历史既有违规（`llm/client.py:60`）⇒ **非本次引入**，不计失败 |

### 3. 测试约定（照现有范式）

参照 `packages/chiyu-kernel/tests/test_pg_isolation_guard.py:1-11`：
**纯函数级、不连真 DB**。理由：真 DB 判据会因环境无 PG/pgvector 而假红，且污染进程级 `created_schemas()`。
⇒凡能用打桩/纯函数判据的，**不连真库**。

---

## File Structure

| 文件 | 动作 | 责任 |
|---|---|---|
| `chiyu_kernel/api.py` | 改 | 门面：R8 补 4 符号导出 · R10 增VTIER族 · R11 出口 |
| `chiyu_kernel/version.py` | **建** | R11：`API_VERSION` / `CONTRACT_VERSION` / `CAPABILITIES` |
| `chiyu_kernel/store/dsn.py` | 改 | R2 env 注入 · R13 双形态 |
| `chiyu_kernel/store/conn.py` | 改 | R9 驱动解耦 + 两条硬知识 |
| `chiyu_kernel/context/retrieval.py` | 改 | R10 `VTIER_*` 主名 + `TIER_*` 别名 |
| `chiyu_decision/api.py` | 改 | R5 docstring 中性化 |
| `tests/test_api_facade_covers_all_layers.py` | 改 | R12 机械推导 |
| `tests/test_store_facade_contract.py` | **建** | R8/R12/R13/R2 判据 |
| `tests/test_store_driver_decoupling.py` | **建** | R9 判据 |
| `tests/test_version_manifest.py` | **建** | R11/R4 判据 |
| `tests/test_tier_naming.py` | **建** | R10 判据 |

---

#批次一 · 门面纯新增（零行为变更）

## Task 1: R8 门面补齐 4 个已实现未导出符号

**Files:**
- Modify: `packages/chiyu-kernel/src/chiyu_kernel/api.py:27-38`（import 区）、`:332` 附近（`__all__` store 段）
- Modify: `packages/chiyu-kernel/tests/test_api_facade_covers_all_layers.py:31-35`（`STORE_REQUIRED`）
- Test: `packages/chiyu-kernel/tests/test_store_facade_contract.py`（新建）

**背景**：APS `foundation.py:67-70` 因门面缺口被迫 import 4 个**内部路径**，违反「消费方只许 import `api` 与 `contract`」纪律。**消费方的违规是被门面缺口逼出来的。**

已实测 4 符号均可导入 ⇒ 本任务**纯新增，零行为变更**：
- `assert_no_hard_delete`（`store/pg_store.py:26`）
- `validate_dsn`（`store/dsn.py:79`）
- `assert_safe_identifier`（`store/dsn.py:121`）
- `pg_to_vec`（`store/conn.py:124`）← **补齐向量往返的回程**

- [ ] **Step 1: 写失败测试**

Create `packages/chiyu-kernel/tests/test_store_facade_contract.py`：

```python
"""store 层能力门面契约（R8/R12）—— **纯函数级，不连真 DB**。

⛔ 为什么是「消费方视角」：本组用例模拟**消费方只import `chiyu_kernel.api`**，
   断言其能拿到全部所需符号 —— 这是 R8 的**直接**判据（门面补齐前必红）。
"""
from chiyu_kernel import api


def test_consumer_can_get_all_four_via_facade_only() -> None:
    """消费方仅经门面即可拿到 R8 四符号（不必触碰内部路径）。"""
    for name in ("assert_no_hard_delete", "validate_dsn",
                 "assert_safe_identifier", "pg_to_vec"):
        assert hasattr(api, name), f"门面缺 {name} ⇒ 消费方被迫 import 内部路径"
        assert name in api.__all__, f"{name} 未进 __all__⇒ 不算门面出口"


def test_vector_round_trip_is_complete() -> None:
    """向量往返须有去程**与**回程（R8 的'只有去程'缺陷的守卫）。"""
    assert "vec_to_pg" in api.__all__
    assert "pg_to_vec" in api.__all__, "向量往返缺回程pg_to_vec"
```

- [ ] **Step 2: 运行确认失败**

```bash
cd /d/system/chiyu-foundation && C:/Users/wangchuan08/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe -m pytest packages/chiyu-kernel/tests/test_store_facade_contract.py -q
```
**期望**：FAIL —— `assert_no_hard_delete` 不在 `api.__all__`。

- [ ] **Step 3: 改 api.py 补 import**

`api.py:27-38` 现有块之后**追加**：

```python
# ── store 门面补齐（R8：已实现但未导出 ⇒ 消费方被迫 import 内部路径）────
from chiyu_kernel.store.conn import pg_to_vec          # noqa: F401（向量往返回程）
from chiyu_kernel.store.dsn import (                # noqa: F401
    assert_safe_identifier,
    validate_dsn,
)
from chiyu_kernel.store.pg_store import assert_no_hard_delete  # noqa: F401
```

- [ ] **Step 4: 改 api.py 补 `__all__`**

在 `api.py` `__all__` 的 store 段（`:332` 附近，紧邻 `"PgVectorStore"`）**追加 4 项**：

```python
    "assert_no_hard_delete", "validate_dsn", "assert_safe_identifier", "pg_to_vec",
```

- [ ] **Step 5: 改 STORE_REQUIRED 同步 4 项**

`tests/test_api_facade_covers_all_layers.py:31-35`：

```python
STORE_REQUIRED = (
    "PgVectorStore", "open_store", "ddl_statements", "vector_index_ddl",
    "assert_no_free_jsonb", "created_schemas", "close_schema", "pad_to_dim",
    "vec_to_pg",
    # R8 补齐：门面补 4 符号 ⇒ 白名单同步，否则机械推导守卫（Task 2）会红
    "assert_no_hard_delete", "validate_dsn", "assert_safe_identifier", "pg_to_vec",
)
```

- [ ] **Step 6: 运行确认通过**

```bash
cd /d/system/chiyu-foundation && C:/Users/wangchuan08/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe -m pytest packages/chiyu-kernel/tests/test_store_facade_contract.py packages/chiyu-kernel/tests/test_api_facade_covers_all_layers.py -q
```
**期望**：PASS。

- [ ] **Step 7: 变异自证（⛔ 不可跳过）**

临时从 `api.__all__` 删除 `"pg_to_vec"`：
```bash
# 变异
sed -i 's/"assert_no_hard_delete", "validate_dsn", "assert_safe_identifier", "pg_to_vec",/"assert_no_hard_delete", "validate_dsn", "assert_safe_identifier",/' packages/chiyu-kernel/src/chiyu_kernel/api.py
#跑测试 ⇒ 期望 RED
C:/Users/wangchuan08/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe -m pytest packages/chiyu-kernel/tests/test_store_facade_contract.py -q
# 还原
sed -i 's/"assert_no_hard_delete", "validate_dsn", "assert_safe_identifier",$/"assert_no_hard_delete", "validate_dsn", "assert_safe_identifier", "pg_to_vec",/' packages/chiyu-kernel/src/chiyu_kernel/api.py
```
**期望**：变异后 RED、还原后 GREEN。**未转红则探针无判别力，不得判验收。**

- [ ] **Step 8: 组合回归**

```bash
cd /d/system/chiyu-foundation && C:/Users/wangchuan08/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe -m pytest packages/chiyu-kernel/tests tools/tests packages/chiyu-decision/src/chiyu_decision/tests -q 2>&1 | tail -5
```
**期望**：不低于基线计数。

- [ ] **Step 9: 提交**

```bash
git add packages/chiyu-kernel/src/chiyu_kernel/api.py packages/chiyu-kernel/tests/test_api_facade_covers_all_layers.py packages/chiyu-kernel/tests/test_store_facade_contract.py
git commit -m "T5: R8 门面补齐 4 符号（消费方免 import 内部路径）+ 变异自证"
```

---

## Task 2: R12 `STORE_REQUIRED` 由人工枚举改为机械推导

**Files:**
- Modify: `packages/chiyu-kernel/tests/test_api_facade_covers_all_layers.py`
- Test: 同文件（新增用例）

**背景**：那 4 个符号长期漏出而无人发现的根因 —— `store` 层登记为 `EXEMPT_LAYERS["store"]`（理由：子模块直连、`__all__` 为空），靠**人工白名单** `STORE_REQUIRED` 核验，而白名单**不含**它们 ⇒ **既未进门面、又不在豁免白名单 = 三不管**。

已实测 `store/{dsn,conn,pg_store,ddl}.py` **均有 `__all__`** ⇒ 可真正改为机械推导。

**⚠️ 本任务是测试收紧，可能暴露既有漏项。** 若转红属"真实漏导出"⇒ **修门面，不改判据**；若属"确应豁免"⇒ 登记豁免**并写明理由**。⛔ 禁止为让测试变绿而放宽判据。

- [ ] **Step 1: 加机械推导用例**

在 `tests/test_api_facade_covers_all_layers.py` 追加：

```python
def test_store_layer_public_symbols_are_mechanically_derived():
    """store 层公共符号须由 `__all__` **机械推导**核验，而非人工枚举。

    ⛔ 根因：store 登记为 EXEMPT_LAYERS（子模块直连），旧实现靠人工白名单
       `STORE_REQUIRED` ⇒ 符号可「既不在门面、也不在白名单」而长期漏出（R8 即此例）。
    """
    import importlib
    pkg = importlib.import_module("chiyu_kernel.store")
    facade = set(importlib.import_module("chiyu_kernel.api").__all__)
    exempt = set(STORE_REQUIRED)
    missing: dict[str, list[str]] = {}
    for sub in ("dsn", "conn", "pg_store", "ddl"):
        mod = importlib.import_module(f"chiyu_kernel.store.{sub}")
        for name in getattr(mod, "__all__", ()):
            if name.startswith("_"):
                continue
            if name not in facade and name not in exempt:
                missing.setdefault(sub, []).append(name)
    assert not missing, (
        f"store 层符号既未进 api.__all__、也不在 STORE_REQUIRED（⇒三不管）: {missing}"
    )
```

- [ ] **Step 2: 运行**

```bash
cd /d/system/chiyu-foundation && C:/Users/wangchuan08/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe -m pytest packages/chiyu-kernel/tests/test_api_facade_covers_all_layers.py -q
```
**期望**：若 PASS ⇒ 说明既有符号已覆盖；若 FAIL ⇒ **列出漏项，逐条判断"补门面 or 登记豁免+理由"，不得改判据**。

- [ ] **Step 3: 变异自证**

临时把`assert_no_hard_delete` 从 `STORE_REQUIRED` 与 `api.__all__` 同时移除：
**期望**：新用例 RED（证明它真能抓到三不管状态）。

- [ ] **Step 4: 组合回归 + 提交**

```bash
git add packages/chiyu-kernel/tests/test_api_facade_covers_all_layers.py
git commit -m "T6: R12 STORE_REQUIRED 改机械推导（store 层三不管状态提交即红）"
```

---

## Task 3: R11 门面暴露版本与能力出口

**Files:**
- Create: `packages/chiyu-kernel/src/chiyu_kernel/version.py`
- Modify: `packages/chiyu-kernel/src/chiyu_kernel/api.py`
- Test: `packages/chiyu-kernel/tests/test_version_manifest.py`（新建）

**背景**：`__version__` 恒为 `0.1.0`，门面无版本出口 ⇒ APS 只能用 `hasattr` 探针（`kmd.py:679`）。符号嗅探无法表达"最低要求版本"，也无法表达"某符号是刻意移除而非从未提供"。

- [ ] **Step 1: 写失败测试**

Create `packages/chiyu-kernel/tests/test_version_manifest.py`：

```python
"""版本与能力出口（R11/R4）—— 纯函数级，不连真 DB。"""
from chiyu_kernel import api


def test_version_exit_exists() -> None:
    """门面须暴露版本出口（消费方可用版本断言替代 hasattr 嗅探）。"""
    assert hasattr(api, "api_version")
    assert callable(api.api_version)
    v = api.api_version()
    assert isinstance(v, dict) and v.get("api")


def test_capabilities_listing() -> None:
    """能力清单须可枚举，且 memory 的 experimental 状态可机检（R4）。"""
    caps = api.capabilities()
    assert isinstance(caps, (list, tuple)) and caps
    mem = [c for c in caps if "memory" in str(c).lower()]
    assert mem, "能力清单缺 memory 条目 ⇒ experimental 边界不可机检"
```

- [ ] **Step 2: 运行确认失败**

```bash
cd /d/system/chiyu-foundation && C:/Users/wangchuan08/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe -m pytest packages/chiyu-kernel/tests/test_version_manifest.py -q
```
**期望**：FAIL —— `api` 无 `api_version`。

- [ ] **Step 3: 建 version.py**

Create `packages/chiyu-kernel/src/chiyu_kernel/version.py`：

```python
"""版本与能力清单（R11/R4）—— 让消费方用**版本断言**替代 `hasattr` 符号嗅探。

⛔ 为什么需要：`__version__` 恒为 "0.1.0"，且能力增删不体现在版本号上⇒
   消费方只能靠 `hasattr` 探针。而符号嗅探**无法表达**：
   ① "我需要至少 X 版本"；② "这个符号是刻意移除，而非从未提供"。
   本模块把能力显式化为清单，两者皆可断言。

⚠️ `CAPABILITIES` 是**契约面**：新增对外能力时应登记，否则守卫（Task 3Step 5）转红。
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

#: 门面 API 版本（与包 `__version__` 区分：后者随实现变，前者是契约面）
API_VERSION = "1.0"

#: L0 契约版本
CONTRACT_VERSION = "1.0"

#: 能力清单：`(name, status)`；status 取 `stable` / `experimental`
CAPABILITIES: Tuple[Tuple[str, str], ...] = (
    ("store", "stable"),
    ("vector", "stable"),
    ("ontology", "stable"),
    ("context", "stable"),
    ("domain", "stable"),
    ("persist", "stable"),
    ("decision_spine", "stable"),
    ("graph", "stable"),
    ("mcp", "experimental"),
    # ⛔ memory 仍 experimental（T5′ 未验收）：消费方**不得**把本包写进硬判据
    ("memory", "experimental"),
)


def api_version() -> Dict[str, Any]:
    """返回版本与能力摘要（消费方版本断言入口）。"""
    return {
        "api": API_VERSION,
        "contract": CONTRACT_VERSION,
        "capabilities": len(CAPABILITIES),
    }


def capabilities() -> Tuple[str, ...]:
    """返回能力清单；experimental 项前缀 ``~`` 以示不稳定。"""
    return tuple(f"~{n}" if s == "experimental" else n for n, s in CAPABILITIES)


__all__ = [
    "API_VERSION", "CONTRACT_VERSION", "CAPABILITIES",
    "api_version", "capabilities",
]
```

- [ ] **Step 4: 门面 re-export**

`api.py` 追加：
```python
# ── 版本与能力出口（R11/R4）：让消费方用版本断言替代 hasattr 嗅探 ──────
from chiyu_kernel.version import (  # noqa: F401
    API_VERSION, CONTRACT_VERSION, api_version, capabilities,
)
```
`api.__all__` 追加：`"API_VERSION", "CONTRACT_VERSION", "api_version", "capabilities",`

- [ ] **Step 5: 加能力清单守卫 + 变异自证**

在 `test_version_manifest.py` 追加：
```python
def test_capability_membership_has_no_undocumented_entry() -> None:
    """新增对外能力须登记进 CAPABILITIES（守护清单本身不漂移）。"""
    from chiyu_kernel.version import CAPABILITIES
    for name, status in CAPABILITIES:
        assert status in ("stable", "experimental"), f"{name} 状态非法: {status}"
```
**变异自证**：临时往`CAPABILITIES` 加 `("bogus", "unstable")` ⇒ 期望 RED。

- [ ] **Step 6: 组合回归 + 提交**

```bash
git add packages/chiyu-kernel/src/chiyu_kernel/version.py packages/chiyu-kernel/src/chiyu_kernel/api.py packages/chiyu-kernel/tests/test_version_manifest.py
git commit -m "T7: R11+R4 门面暴露 api_version/capabilities（memory experimental 可机检）"
```

---

# 批次二 · store 加法

## Task 4: R2 env 键名改为可注入

**Files:**
- Modify: `packages/chiyu-kernel/src/chiyu_kernel/store/dsn.py:46-52`（`raw_dsn`）、`:86-89`（报错）、`:116-118`（`get_schema`）
- Test: `packages/chiyu-kernel/tests/test_store_facade_contract.py`（追加）

**背景**：D1 三坑的第 ③ 条。实测真问题不只是"取不到值"，而是**报错文案硬编码 `DSN_ENV`**（`dsn.py:88`）⇒ 消费方传自定义键名后，报错仍提示 `CHIYU_DB_DSN`，**误导排障**。

- [ ] **Step 1: 写失败测试**（追加到 `test_store_facade_contract.py`）

```python
def test_env_key_name_is_injectable_and_reflected_in_error(monkeypatch) -> None:
    """R2：env 键名可注入，且**报错文案随之变化**（不再硬编码 CHIYU_DB_DSN）。"""
    from chiyu_kernel.store import dsn as dsn_mod
    from chiyu_kernel.store.dsn import DBConfigError, validate_dsn
    monkeypatch.delenv("APS_CUSTOM_DSN", raising=False)
    with pytest.raises(DBConfigError) as ei:
        validate_dsn("", env="APS_CUSTOM_DSN")
    assert "APS_CUSTOM_DSN" in str(ei.value), "报错文案未跟随注入的 env 键名"
    assert "CHIYU_DB_DSN" not in str(ei.value), "报错仍硬编码默认键名 ⇒ 误导排障"


def test_injected_env_key_actually_reads(monkeypatch) -> None:
    """注入的 env 键名须真的被读取（不只是文案变化）。"""
    from chiyu_kernel.store.dsn import raw_dsn
    monkeypatch.setenv("APS_CUSTOM_DSN", "host=h dbname=x")
    assert raw_dsn(env="APS_CUSTOM_DSN") == "host=h dbname=x"
```
在文件顶部补`import pytest`。

- [ ] **Step 2: 运行确认失败**

```bash
cd /d/system/chiyu-foundation && C:/Users/wangchuan08/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe -m pytest packages/chiyu-kernel/tests/test_store_facade_contract.py -q
```
**期望**：FAIL —— `raw_dsn()` 不接受 `env` 形参。

- [ ] **Step 3: 改 `raw_dsn` 加 env 形参**

`store/dsn.py:46-52` 替换为：

```python
def raw_dsn(*, testing: bool | None = None,
            env: str | None = None, env_test: str | None = None) -> str:
    """读原始 DSN（不校验）。testing 时优先取测试 DSN，缺则回退主 DSN。

    ⛔ R2：`env` / `env_test` 让**调用方注入 env 键名**（默认仍取模块常量）。
       动机不只是"取不到值"，更是**报错文案必须随之变化** —— 否则消费方传了
       自定义键，报错仍提示 `CHIYU_DB_DSN`，误导排障。
    """
    dsn_env = env or DSN_ENV
    test_env = env_test or DSN_TEST_ENV
    if _effective_testing(testing):
        return (os.environ.get(test_env) or "").strip() \
            or (os.environ.get(dsn_env) or "").strip()
    return (os.environ.get(dsn_env) or "").strip()
```

- [ ] **Step 4: 改报错文案引用传入值**

`store/dsn.py:86-89` 的 `validate_dsn` 空串分支替换为：

```python
    if not dsn:
        raise DBConfigError(
            f"未配置 {env or DSN_ENV}（测试环境可用 {env_test or DSN_TEST_ENV}）；"
            f"内核**无 SQLite 回退**，缺 DSN 即不可用。")
```
并在 `validate_dsn` 签名增 `env` / `env_test` 形参（默认 `None`）。

- [ ] **Step 5: 改 `get_schema`**

`store/dsn.py:116-118`：
```python
def get_schema(default: str = "", *, env: str | None = None) -> str:
    v = (os.environ.get(env or SCHEMA_ENV) or "").strip()
    return v or default
```

- [ ] **Step 6: 运行 + 变异自证 + 组合回归**

**变异自证**：把 Step 4 的报错文案改回硬编码 `DSN_ENV` ⇒ 期望 RED。
```bash
git add packages/chiyu-kernel/src/chiyu_kernel/store/dsn.py packages/chiyu-kernel/tests/test_store_facade_contract.py
git commit -m "T8: R2 env 键名可注入且报错文案跟随（R2 第③坑）"
```

---

## Task 5: R13 `validate_dsn` 接受 keyword/value 双形态

**Files:**
- Modify: `packages/chiyu-kernel/src/chiyu_kernel/store/dsn.py:66-76`（`parse_dsn`）、`:79+`（`validate_dsn`）
- Test: `packages/chiyu-kernel/tests/test_store_facade_contract.py`（追加）

**背景**：`parse_dsn`（`dsn.py:66`）只用 `urlparse` ⇒ **KV 形态今天必然失败**（已实测）。APS 因此自写 `dsn_to_uri()`（`foundation.py:256-293`），且该函数**返回串含口令**，docstring 须挂"不得回灌连接、不得写日志"——**一个为绕过形态限制而生的、带安全约束的中间态**。

**目标**：在基座内部直接判 KV，**不构造含口令的 URI 串**（消除中间态外泄）。

- [ ] **Step 1: 写失败测试**

```python
def test_validate_dsn_accepts_both_forms_consistently() -> None:
    """R13：URI 与 keyword/value 两形态判定须一致（对拍）。"""
    from chiyu_kernel.store.dsn import validate_dsn
    uri = "postgresql://chiyu@127.0.0.1:5432/chiyu_test"
    kv = "host=127.0.0.1 port=5432 dbname=chiyu_test user=chiyu"
    assert validate_dsn(uri) == validate_dsn(kv)


def test_kv_form_still_enforces_redlines() -> None:
    """KV 形态同样受红线约束（禁被禁主机）——形态不同不得削弱判据。"""
    from chiyu_kernel.store.dsn import DBConfigError, validate_dsn
    with pytest.raises(DBConfigError):
        validate_dsn("host=81.70.184.198 port=5432 dbname=x user=chiyu")
```

- [ ] **Step 2: 运行确认失败**

**期望**：FAIL —— KV 形态抛`DBConfigError`（scheme 为空）。

- [ ] **Step 3: `parse_dsn` 支持双形态**

`store/dsn.py:66-76` 替换为：

```python
_KV_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\s*=")


def parse_dsn(dsn: str) -> dict:
    """解析 DSN → dict。**同时接受 URI 与 keyword/value 两种形态**（R13）。

    ⛔ 为什么要双形态：消费方（APS 裁决书 R1）用 psycopg3，其 DSN 契约为
       keyword/value（`host=... port=... dbname=...`）。此前本函数只走
       `urlparse` ⇒ KV 串被当成无 scheme 而误报"scheme 必须为 postgresql"，
       迫使消费方自写转换串 —— **该串含口令**，须挂"不得回灌/不得写日志"的
       安全约束。在基座内直接解析可消除该中间态。
    """
    s = (dsn or "").strip()
    if s and not _URI_SCHEME_RE.match(s) and _KV_RE.match(s):
        # keyword/value 形态：**不构造 URI 串**（避免口令出现在中间态）
        return _parse_kv_dsn(s)
    u = _up.urlparse(s)
    return {
        "scheme": u.scheme,
        "user": u.username,
        "password": u.password,
        "host": u.hostname,
        "port": u.port,
        "db": (u.path or "").lstrip("/"),
    }


def _parse_kv_dsn(s: str) -> dict:
    """keyword/value DSN 解析（驱动无关，不构造含口令的 URI）。

    ⚠️ 端口用 `int()` 归一为 int，与 URI 分支的 `urlparse().port` 类型一致
       ⇒ 消费方拿到同构 dict，可直接对拍。
    """
    kv: dict[str, str] = {}
    for m in re.finditer(r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*('[^']*'|\"[^\"]*\"|\S+)", s):
        kv[m.group(1).lower()] = m.group(2).strip("'\"")
    port = kv.get("port")
    db = kv.get("dbname") or kv.get("db") or ""
    return {
        "scheme": "postgresql",       # KV 形态无 scheme 前缀，按 psycopg 约定即 PG
        "user": kv.get("user"),
        "password": kv.get("password"),
        "host": kv.get("host"),
        "port": int(port) if port and port.isdigit() else None,
        "db": db,
    }
```
并补模块级 `_URI_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*://")`（若尚无）。

- [ ] **Step 4: 运行 + 变异自证**

**变异自证**：把 `_parse_kv_dsn` 的 `FORBIDDEN_HOSTS` 检查绕过（临时改host 为 `""`）⇒ `test_kv_form_still_enforces_redlines` 须 RED。
```bash
git add packages/chiyu-kernel/src/chiyu_kernel/store/dsn.py packages/chiyu-kernel/tests/test_store_facade_contract.py
git commit -m "T9: R13 validate_dsn 双形态（免消费方构造含口令中间串）+ 对拍判据"
```

---

## Task 6: R9 驱动解耦 + 两条硬知识

**Files:**
- Modify: `packages/chiyu-kernel/src/chiyu_kernel/store/conn.py:138-158`（`connect`）、`:286-307`（`drop_test_schema`）
- Test: `packages/chiyu-kernel/tests/test_store_driver_decoupling.py`（新建）

**背景**：基座 `conn.py` 在 `:24/:150/:162/:178` 硬绑 `psycopg2`；APS 用 psycopg3 ⇒ 只能自建约 200 行（`foundation.py:337-538`）。

**已知**：三条硬知识中 **`search_path` 保留 `public` 基座已实现**（`conn.py:155`）⇒ **不重复做**。真实缺口仅 2 条：
1. `DROP SCHEMA` 前须 `SET lock_timeout`（APS 实测曾卡死 >7 分钟）；
2. 摘连接须按 `application_name` + pid **精准命中本进程**（只按名字扫库会误伤并行会话）。

⚠️ **本批唯一有真实行为风险的任务** ⇒ 独立验证，不与其他任务混批。

- [ ] **Step 1: 写失败测试**

Create `packages/chiyu-kernel/tests/test_store_driver_decoupling.py`：

```python
"""store 驱动解耦与清理硬知识（R9）—— **打桩，不连真 DB**。

⛔ 为什么打桩：真库才能触发 DROP SCHEMA 等锁，而本机环境无 PG/pgvector；
   真库判据会假红。这里打桩驱动，验证**调用序列**（lock_timeout 被设置、
   application_name 精准命中），这是"内核自身承诺"的判据。
"""
from typing import Any, List, Tuple

import pytest

from chiyu_kernel.store import conn as conn_mod


class _FakeCursor:
    def __init__(self, sink: List[Tuple[str, Any]]) -> None:
        self._sink = sink

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, *exc: Any) -> None:
        return None

    def execute(self, sql: str, *args: Any) -> None:
        self._sink.append((sql, args))

    def fetchone(self) -> Any:
        return None


class _FakeConn:
    def __init__(self, sink: List[Tuple[str, Any]]) -> None:
        self._sink = sink
        self.autocommit = False

    def cursor(self, **kw: Any) -> _FakeCursor:
        return _FakeCursor(self._sink)

    def commit(self) -> None:
        return None


@pytest.fixture()
def fake_sink() -> List[Tuple[str, Any]]:
    return []


def test_drop_schema_sets_lock_timeout(fake_sink, monkeypatch) -> None:
    """DROP SCHEMA 前必须 SET lock_timeout（否则持锁时无限等锁）。"""
    monkeypatch.setattr(conn_mod, "shared", lambda **kw: _FakeConn(fake_sink))
    monkeypatch.setattr(conn_mod._dsn, "get_dsn", lambda **kw: "postgresql://u@h/db")
    with pytest.raises(Exception):
        #_rule_pid 等无关；仅验证 SET lock_timeout 在 DROP 之前发出
        conn_mod.drop_test_schema("t_x")
    sqls = [s.upper() for s, _ in fake_sink]
    joined = " | ".join(sqls)
    assert "LOCK_TIMEOUT" in joined, f"未设 lock_timeout ⇒ 持锁时无限等锁: {sqls}"


def test_connect_factory_is_injectable(monkeypatch) -> None:
    """connect_factory 注入后不碰 psycopg2（驱动解耦判据，纯打桩）。"""
    calls: List[dict] = []

    def _factory(dsn: str, **kw: Any) -> _FakeConn:
        calls.append({"dsn": dsn, **kw})
        return _FakeConn([])

    conn_mod.connect(dsn="postgresql://u@h/db", schema="t_s", connect_factory=_factory)
    assert calls, "connect_factory 未被调用 ⇒ 仍硬绑 psycopg2"
```

- [ ] **Step 2: 运行确认失败**

**期望**：FAIL —— `connect()` 不接受 `connect_factory`；且 `drop_test_schema` 未发 lock_timeout。

- [ ] **Step 3: `connect` 加 `connect_factory`**

`store/conn.py:138-158` 的 `connect` 改签名与驱动段：

```python
def connect(*, dsn: Optional[str] = None, schema: Optional[str] = None,
            timeout: int = 5, autocommit: bool = False,
            connect_factory: Optional[Callable[..., Any]] = None) -> Any:
    """新建一条连接（调用方负责关闭）。DSN/schema 走 env，红线校验在 dsn 模块完成。

    ⛔ 红线先于驱动校验：无论是否传入 dsn、驱动是否就绪，先过 `validate_dsn`
       （禁连生产机 FORBIDDEN_HOSTS、禁超级用户、scheme 必须为 postgresql）。
       否则 `connect(dsn="postgresql://...@81.70.184.198/...")` 会绕过红线直接试连。

    ⛔ R9 `connect_factory`：注入连接工厂 ⇒ **驱动解耦**。默认 `None` 时走既有
       psycopg2 路径（**既有调用零影响**）。存在的理由：消费方裁决书 R1 定psycopg3，
       而本模块硬绑 psycopg2（`:24/:150/:162/:178`）⇒ 消费方被迫自建整套隔离机制。
       注入的工厂须接受 `(dsn, **kw)` 并返回带 `cursor()` 的连接对象。
    """
    dsn = dsn or _dsn.get_dsn()
    _dsn.validate_dsn(dsn)               # 红线在前：不依赖驱动，该拦则拦
    schema = _dsn.assert_safe_identifier(schema or _dsn.get_schema(), what="schema")
    if connect_factory is not None:
        conn = connect_factory(dsn, connect_timeout=timeout)
    else:
        if _pg is None:
            raise RuntimeError(
                f"psycopg2 不可用（{_PG_ERR}）；本环境解释器可能不是 hermes venv"
                "（或改用 connect_factory 注入驱动）")
        conn = _pg.connect(dsn, connect_timeout=timeout)
    conn.autocommit = autocommit
    with conn.cursor() as cur:
        # search_path 逐连接显式设置（不依赖 ALTER ROLE 默认值）
        # ⛔ public 必须在尾部：vector 类型与 zhparser parser 建在 public（R9 硬知识）
        cur.execute(f"SET search_path TO {schema}, public")
    return conn
```
并在文件头补 `from typing import Callable`（若缺）。

- [ ] **Step 4: `drop_test_schema` 增 lock_timeout**

`store/conn.py:286-307` 内，`conn = shared()` 之后加：

```python
    conn = shared()
    # ⛔ R9 硬知识（APS 真库实测）：`DROP SCHEMA` 会等所有锁；无超时则整套用例
    #   **无限等锁**（实测卡死 >7 分钟）。必须设 lock_timeout ⇒ 最坏情况快速失败并上报。
    with conn.cursor() as cur:
        cur.execute("SET lock_timeout = '3s'")
```

- [ ] **Step 5: 新增精准摘连接函数**

在 `store/conn.py` 追加（**只摘本进程**，不误伤并行会话）：

```python
def terminate_own_backends(*, application_name: str,
                           terminate: Optional[Callable[..., Any]] = None) -> int:
    """按 `application_name`（含 pid 后缀）摘除**本进程**连接，返回被终止数。

    ⛔ R9 硬知识（APS 真库实测）：只按名字扫库会**误伤并行会话**（其他 pytest
       进程 / 其他 worktree 的连接）。清理必须精准到本进程标识。

    ⚠️ `application_name` 约定须带 pid，由调用方构造（基座不猜pid）。
    """
    factory = terminate or (lambda: connect(autocommit=True))
    conn = factory()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) AS n FROM ("
                "  SELECT pg_terminate_backend(pid) "
                "  FROM pg_stat_activity "
                "  WHERE application_name = %s"
                "    AND pid <> pg_backend_pid()) t", (application_name,))
            row = cur.fetchone()
        return int(row["n"] if isinstance(row, dict) else row[0])
    finally:
        conn.close()
```
并把该函数名加入 `store/conn.py:342` 的 `__all__`。

- [ ] **Step 6: 运行 + 变异自证 + 组合回归 + 提交**

**变异自证**：删掉 Step 4 的 `SET lock_timeout` ⇒ `test_drop_schema_sets_lock_timeout` 须 RED。
```bash
git add packages/chiyu-kernel/src/chiyu_kernel/store/conn.py packages/chiyu-kernel/tests/test_store_driver_decoupling.py
git commit -m "T10: R9 connect_factory 驱动解耦 + lock_timeout 与精准摘连接两条硬知识"
```

---

# 批次三 · 命名与披露

## Task 7: R10 `TIER_` 两族加法分族

**Files:**
- Modify: `packages/chiyu-kernel/src/chiyu_kernel/context/retrieval.py:28-33`
- Test: `packages/chiyu-kernel/tests/test_tier_naming.py`（新建）

**背景**：两族共用 `TIER_` 前缀、同处 `api` 命名空间、语义无关：
- 向量降级族（`retrieval.py:28-33`）：`TIER_FTS_VECTOR`/`TIER_VECTOR`/`TIER_FTS`/`TIER_NONE`/`TIER_ORDER`
- 自进化风险族（`contract/evolution.py:34`）：`TIER_AUTO`/`TIER_GUARDED`/`TIER_FORBIDDEN`

⇒ APS 被迫写长注释警告"不得简写"（`foundation.py:184-187`）= **消费方替基座打补丁**。

**严格加法**：`VTIER_*` 为主名，`TIER_*` 保留别名（弃用标注）⇒ **零破坏**。

- [ ] **Step 1: 写失败测试**

Create `packages/chiyu-kernel/tests/test_tier_naming.py`：

```python
"""TIER_ 两族命名（R10）—— 纯函数级。"""
from chiyu_kernel import api


def test_vtier_is_primary_and_old_names_still_work() -> None:
    """向量降级族以 VTIER_* 为主名，且旧名 TIER_* 仍可用（严格加法，零破坏）。"""
    from chiyu_kernel.context import retrieval
    for old, new in (("TIER_FTS_VECTOR", "VTIER_FTS_VECTOR"),
                     ("TIER_VECTOR", "VTIER_VECTOR"),
                     ("TIER_FTS", "VTIER_FTS"),
                     ("TIER_NONE", "VTIER_NONE")):
        assert hasattr(retrieval, new), f"缺主名 {new}"
        assert hasattr(retrieval, old), f"旧名 {old} 被移除 ⇒ 破坏性变更"


def test_two_tier_families_do_not_collide_in_facade() -> None:
    """两族在门面命名空间内不得同名（同名歧义即缺陷）。"""
    names = [n for n in api.__all__ if n.startswith("TIER_") or n.startswith("VTIER_")]
    assert len(names) == len(set(names)), "门面存在同名 TIER_ 符号"
    assert "VTIER_VECTOR" in api.__all__
    assert "TIER_GUARDED" in api.__all__, "自进化风险族不应被本任务改动"
```

- [ ] **Step 2: 运行确认失败**

**期望**：FAIL —— 缺 `VTIER_VECTOR`。

- [ ] **Step 3: 加 VTIER 主名 +旧名别名**

`context/retrieval.py:28-33` 替换为：

```python
# ── 三级降级链的层级标识（顺序即决策优先级）────────────────────────────
# ⛔ R10 命名分族：向量降级族统一 `VTIER_` 前缀，与自进化风险族
#    （`contract/evolution.py` 的 `TIER_AUTO`/`TIER_GUARDED`/`TIER_FORBIDDEN`）
#    同处 `api` 命名空间却语义无关。旧 `TIER_*` 保留为**弃用别名**（严格加法，
#    零破坏）—— 消费方可用 `VTIER_*` 新名，旧名仍可用。
VTIER_FTS_VECTOR = "fts+vector"   # 一级：FTS 预过滤 + 池内向量排序（理想）
VTIER_VECTOR = "vector"           # 二级：纯向量排序（FTS 0 命中放宽）
VTIER_FTS = "fts"# 三级：纯 FTS 排序（无向量 / 向量 0 命中）
VTIER_NONE = "none"               # 无候选（池内无语料）

VTIER_ORDER: tuple[str, ...] = (VTIER_FTS_VECTOR, VTIER_VECTOR, VTIER_FTS, VTIER_NONE)

# ⛔ 弃用（保留兼容，消费方请改用 VTIER_*）：与自进化风险族同名异义。
TIER_FTS_VECTOR = VTIER_FTS_VECTOR
TIER_VECTOR = VTIER_VECTOR
TIER_FTS = VTIER_FTS
TIER_NONE = VTIER_NONE
TIER_ORDER = VTIER_ORDER
```

- [ ] **Step 4: 门面 `__all__` 同增两族**

`api.py` `__all__` 追加：`"VTIER_FTS_VECTOR", "VTIER_VECTOR", "VTIER_FTS", "VTIER_NONE", "VTIER_ORDER",`

- [ ] **Step 5: 运行 + 变异自证 + 提交**

**变异自证**：删 `VTIER_VECTOR = VTIER_VECTOR` ⇒ `test_vtier_is_primary_and_old_names_still_work` 须 RED。
```bash
git add packages/chiyu-kernel/src/chiyu_kernel/context/retrieval.py packages/chiyu-kernel/src/chiyu_kernel/api.py packages/chiyu-kernel/tests/test_tier_naming.py
git commit -m "T11: R10 TIER_ 两族加法分族（VTIER_ 为主名，旧名弃用别名保留）"
```

---

## Task 8: R5 门面 docstring 移除内部标记（守 §13）

**Files:**
- Modify: `packages/chiyu-decision/src/chiyu_decision/api.py:4`（及同类位置）

- [ ] **Step 1: 扫描违规字样**

```bash
cd /d/system/chiyu-foundation && grep -nE "违约|内部路径|未接线|api\.py:[0-9]" packages/chiyu-decision/src/chiyu_decision/api.py
```

- [ ] **Step 2: 中性化 docstring**

`chiyu_decision/api.py:4` 现为：
```
import chiyu_decision.spine / .scoring / .redline 内部路径即违约。
```
改为中性表述（保留约束语义，去掉内部实现指路与"违约"字样）：
```
本模块是决策能力的**唯一公开入口**；请勿绕过本模块访问下层实现路径。
```

- [ ] **Step 3: ⛔ 强制重编译（docstring 会编入 `.pyc`）**

```bash
cd /d/system/chiyu-foundation && C:/Users/wangchuan08/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe -m compileall -f packages/chiyu-decision/src/chiyu_decision/api.py
```

- [ ] **Step 4: 复核含`.pyc` 零残留**

```bash
cd /d/system/chiyu-foundation && grep -rn "违约" packages/chiyu-decision/src/chiyu_decision/ --include="*.py" --include="*.pyc"
```
**期望**：零命中。
⚠️ **禁以「`git status` 未列出该文件」为准**（大目录只显示 `?? dir/`，易误判已忽略）。

- [ ] **Step 5: 组合回归 + 提交**

```bash
git add packages/chiyu-decision/src/chiyu_decision/api.py
git commit -m "T12: R5 门面 docstring 中性化（守 §13 披露纪律，含 .pyc 零残留复核）"
```

---

## Task 9: 跨批次守卫 · 三消费方导入面回归

**Files:**
- Test: `packages/chiyu-kernel/tests/test_consumer_facade_stability.py`（新建）

**背景**：严格加法的**唯一验收口径** = 既有导入面零失效。

- [ ] **Step 1: 写用例**

```python
"""三消费方导入面稳定性（严格加法的验收口径）—— 纯门面级，不连真 DB。"""
import importlib


def test_aps_facade_import_surface_still_available() -> None:
    """APS 侧曾依赖的符号（模拟其 import 语句）仍可从门面拿到。"""
    api = importlib.import_module("chiyu_kernel.api")
    for n in ("score_rubric", "check_elements", "autonomous_release",
              "evaluate_redline", "MEMORY_PREDICATES", "EDGE_LAYERS",
              "assert_safe_identifier", "validate_dsn",
              "assert_no_hard_delete", "pg_to_vec", "vec_to_pg", "pad_to_dim"):
        assert hasattr(api, n), f"APS 依赖的 {n} 失效 ⇒ 严格加法被破坏"


def test_enterprise_facade_import_surface_still_available() -> None:
    """enterprise 侧曾依赖的符号仍可用。"""
    api = importlib.import_module("chiyu_kernel.api")
    for n in ("PgVectorStore", "open_store", "ddl_statements", "vector_index_ddl"):
        assert hasattr(api, n), f"enterprise 依赖的 {n} 失效"


def test_decision_package_surface_still_available() -> None:
    """决策包门面（R1已补 aggregate_confidence）仍完整。"""
    dec = importlib.import_module("chiyu_decision.api")
    for n in ("score_rubric", "check_elements", "autonomous_release",
              "evaluate_redline", "aggregate_confidence"):
        assert hasattr(dec, n), f"决策门面 {n} 失效"
```

- [ ] **Step 2: 运行 + 组合回归 + 提交**

```bash
cd /d/system/chiyu-foundation && C:/Users/wangchuan08/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe -m pytest packages/chiyu-kernel/tests/test_consumer_facade_stability.py -q
git add packages/chiyu-kernel/tests/test_consumer_facade_stability.py
git commit -m "T13: 跨消费方导入面回归守卫（严格加法零失效验收口径）"
```

---

# Self-Review

## 1. 规格覆盖自检

| 设计稿任务 | 本计划Task | 覆盖 |
|---|---|---|
| 1.1 R8 门面补 4 符号 | Task 1 | ✅ |
| 1.2 R12 机械推导 | Task 2 | ✅ |
| 1.3 R11 版本出口 | Task 3 | ✅ |
| 2.1 R9 驱动解耦 + 硬知识 | Task 6 | ✅ |
| 2.2 R13 双形态 DSN | Task 5 | ✅ |
| 2.3 R2 env 注入 | Task 4 | ✅ |
| 3.1 R10 TIER 分族 | Task 7 | ✅ |
| 3.2 R4 experimental 显式化 | Task 3（合流 CAPABILITIES） | ✅ |
| 3.3 R5 docstring 清理 | Task 8 | ✅ |
| 跨批次三消费方守卫 | Task 9 | ✅ |

**无遗漏**。R4 与 R11 合流（同一新建文件 `version.py`），符合 DRY。

## 2. 占位符扫描

无 "TBD" / "implement later" / "类似 Task N"。所有代码步骤均含实际代码与命令。
**已知需实施者判断的两处**（已在正文写明判断准则，非占位符）：
- Task 2 Step 2：机械推导若暴露既有漏项 ⇒ 补门面 or 登记豁免（准则已给）
- Task 6：`connect_factory` 须实跑 psycopg3 验证，不只加参数

## 3. 类型/命名一致性

- `connect_factory` 签名：`(dsn: str, **kw) -> conn`，Task 6 定义与测试一致 ✅
- `raw_dsn(env=..., env_test=...)` 与 `validate_dsn(env=..., env_test=...)` 签名一致 ✅
- `parse_dsn` 两形态返回**同构 dict**（`port` 均为 `int | None`）⇒ 对拍断言成立 ✅
- `VTIER_*` 主名 / `TIER_*` 别名，Task 7 定义与测试一致 ✅
- `api_version()` / `capabilities()` 命名在 Task 3 定义与测试一致 ✅

---

# Execution Handoff

**Plan complete and saved to `docs/plans/2026-10-09-foundation-R2-R14落实计划.md`.**

**Two execution options:**

1. **Inline Execution（本会话内执行）** — 用 `executing-plans` 按批次执行，每批完成后设检查点汇报。**推荐**：本仓有大量未提交改动，同会话能保持上下文连续，且每批的回归判据需现场判读。

2. **Subagent-Driven** — 每个 Task派新subagent，任务间双阶段评审。

**Which approach?**