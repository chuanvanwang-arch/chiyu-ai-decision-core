"""R2 —— env 键名可注入（PgVectorStore 第③坑收口）。

⛔ 为什么这条必须存在：env 键名此前是**模块级常量**，消费方若想用自己的键，
   只能改内核源码；更糟的是报错文案把键名**硬编码**成默认键
   （`dsn.py` 原 `:88`）——消费方传了自定义键却缺配置时，报错仍指向
   `CHIYU_DB_DSN`，诊断被误导。判据因此是**两条**：取值可注入 + 报错随之变。

⛔ 纯函数级，不连真 DB（同 `test_pg_isolation_guard.py` 约定）：真库判据会因
   环境无 PG 而假红。这里只测键值解析与报错文案。

严格加法判据：不传新参数时行为**与改造前逐字一致**（见 `test_default_*`），
这是"零既存代码失效"的回归保护，删掉它就无法区分加法与破坏性变更。
"""
import pytest

from chiyu_kernel.store.dsn import (
    DSN_ENV,
    DSN_TEST_ENV,
    SCHEMA_ENV,
    DBConfigError,
    get_dsn,
    get_schema,
    raw_dsn,
)

# 合规 DSN：scheme/user/host 均不撞通用红线（不连真库，仅作字符串解析）
GOOD = "postgresql://chiyu@127.0.0.1:5432/chiyu_test"
GOOD_T = "postgresql://chiyu@127.0.0.1:5432/chiyu_test_b"

# 自定义键名（模拟消费方自带命名）
C_DSN = "APS_DB_DSN"
C_DSN_T = "APS_DB_DSN_TEST"
C_SCHEMA = "APS_DB_SCHEMA"


def _clear(monkeypatch):
    """清空所有相关 env，杜绝用例间串味。"""
    for k in (DSN_ENV, DSN_TEST_ENV, SCHEMA_ENV,
              C_DSN, C_DSN_T, C_SCHEMA,
              "CHIYU_DB_TESTING", "CHIYU_TEST"):
        monkeypatch.delenv(k, raising=False)


# ── 判据一：取值可注入 ────────────────────────────────────────────────
def test_custom_dsn_env_is_read(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv(C_DSN, GOOD)
    assert raw_dsn(dsn_env=C_DSN) == GOOD
    assert get_dsn(dsn_env=C_DSN) == GOOD


def test_custom_test_dsn_env_is_read(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv(C_DSN_T, GOOD_T)
    assert raw_dsn(testing=True, dsn_test_env=C_DSN_T) == GOOD_T
    assert get_dsn(testing=True, dsn_test_env=C_DSN_T) == GOOD_T


def test_custom_schema_env_is_read(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv(C_SCHEMA, "aps_tenant")
    assert get_schema(schema_env=C_SCHEMA) == "aps_tenant"
    # 注入键有值时，default 不生效
    assert get_schema("fallback", schema_env=C_SCHEMA) == "aps_tenant"


# ── 判据二：报错文案随之变化（否则诊断误导）────────────────────────────
def test_error_message_names_injected_dsn_env(monkeypatch):
    _clear(monkeypatch)
    with pytest.raises(DBConfigError) as ei:
        get_dsn(dsn_env=C_DSN, dsn_test_env=C_DSN_T)
    msg = str(ei.value)
    assert C_DSN in msg, f"报错未提及注入键：{msg}"
    assert C_DSN_T in msg, f"报错未提及注入测试键：{msg}"
    assert DSN_ENV not in msg, f"报错仍硬编码默认键 {DSN_ENV}：{msg}"


# ── 严格加法回归保护：不传参 ⇒ 行为逐字不变 ────────────────────────────
def test_default_dsn_env_unchanged(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv(DSN_ENV, GOOD)
    assert get_dsn() == GOOD


def test_default_error_message_unchanged(monkeypatch):
    _clear(monkeypatch)
    with pytest.raises(DBConfigError) as ei:
        get_dsn()
    assert DSN_ENV in str(ei.value)


def test_default_schema_env_unchanged(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv(SCHEMA_ENV, "chiyu_default")
    assert get_schema() == "chiyu_default"
    assert get_schema("fb") == "chiyu_default"
    _clear(monkeypatch)
    assert get_schema("fb") == "fb"


def test_injected_env_missing_falls_back_to_empty_not_default_key(monkeypatch):
    """注入键不存在时取空串 ⇒ 触发"缺 DSN"报错，而不是静默回退默认键。"""
    _clear(monkeypatch)
    monkeypatch.setenv(DSN_ENV, GOOD)      # 默认键有值
    with pytest.raises(DBConfigError) as ei:
        get_dsn(dsn_env=C_DSN)             # 但注入键无值
    assert C_DSN in str(ei.value)
