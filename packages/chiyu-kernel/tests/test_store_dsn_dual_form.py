"""R13 —— `validate_dsn` 接受 URI 与 keyword/value 双形态。

⛔ 为什么要双形态：消费方的连接参数常以 keyword/value 形态持有
   （`host=… port=… dbname=… user=…`）。此前内核只认 URI，消费方为了过校验
   不得不**先拼出一个含口令的中间串**——那个中间串是新的泄密面（日志/异常/traceback
   都可能带上）。双形态让校验直接吃 kv，无需构造中间串。

判据是**对拍**：同一组连接参数写成两种形态，解析结果与红线判定必须一致。
只有"能解析"不够——若两形态判定口径不同，就成了新的假绿源。

⛔ 纯函数级，不连真 DB。
"""
import pytest

from chiyu_kernel.store.dsn import (
    DBConfigError,
    get_dsn,
    parse_dsn,
    validate_dsn,
)

URI = "postgresql://chiyu:s3cr3t@127.0.0.1:5432/chiyu_test"
KV = "host=127.0.0.1 port=5432 dbname=chiyu_test user=chiyu password=s3cr3t"
KV_NO_PW = "host=127.0.0.1 port=5432 dbname=chiyu_test user=chiyu"


# ── 判据一：KV 形态能被解析 ───────────────────────────────────────────
def test_kv_form_parses():
    info = parse_dsn(KV, form="kv")
    assert info["host"] == "127.0.0.1"
    assert info["port"] == 5432
    assert info["db"] == "chiyu_test"
    assert info["user"] == "chiyu"
    assert info["password"] == "s3cr3t"


def test_kv_form_without_password_parses():
    """校验形态不依赖口令 —— kv 允许不带 password（这正是免构造中间串的价值）。"""
    info = parse_dsn(KV_NO_PW, form="kv")
    assert info["user"] == "chiyu"
    assert info["password"] is None


# ── 判据二：两形态对拍一致 ────────────────────────────────────────────
def test_two_forms_agree_on_parsed_fields(monkeypatch):
    u = parse_dsn(URI, form="uri")
    k = parse_dsn(KV, form="kv")
    for field in ("host", "port", "db", "user", "password"):
        assert u[field] == k[field], f"字段 {field} 两形态不一致：{u[field]} vs {k[field]}"


def test_two_forms_agree_on_redline(monkeypatch):
    """红线判定必须两形态一致 —— 否则换形态即绕过护栏。"""
    forbidden_uri = "postgresql://postgres@81.70.184.198:5432/crm_native"
    forbidden_kv = "host=81.70.184.198 port=5432 dbname=crm_native user=postgres"
    with pytest.raises(DBConfigError):
        validate_dsn(forbidden_uri, form="uri")
    with pytest.raises(DBConfigError):
        validate_dsn(forbidden_kv, form="kv")


def test_two_forms_agree_on_db_prefix(monkeypatch):
    ok_uri = "postgresql://chiyu@127.0.0.1:5432/chiyu_test"
    ok_kv = "host=127.0.0.1 port=5432 dbname=chiyu_test user=chiyu"
    assert validate_dsn(ok_uri, form="uri", required_db_prefix="chiyu")["db"] == "chiyu_test"
    assert validate_dsn(ok_kv, form="kv", required_db_prefix="chiyu")["db"] == "chiyu_test"
    with pytest.raises(DBConfigError):
        validate_dsn(ok_uri, form="uri", required_db_prefix="aps")
    with pytest.raises(DBConfigError):
        validate_dsn(ok_kv, form="kv", required_db_prefix="aps")


# ── 判据三：auto 自动识别 ─────────────────────────────────────────────
def test_auto_detects_uri_by_scheme_marker():
    assert parse_dsn(URI)["db"] == "chiyu_test"


def test_auto_detects_kv_without_scheme_marker():
    assert parse_dsn(KV)["db"] == "chiyu_test"


def test_form_rejects_unknown_value():
    with pytest.raises(DBConfigError):
        parse_dsn(URI, form="yaml")


# ── 判据四：畸形 KV 有界报错，不静默通过 ───────────────────────────────
def test_malformed_kv_raises():
    with pytest.raises(DBConfigError):
        parse_dsn("host=127.0.0.1 port=notanumber dbname=x", form="kv")
    with pytest.raises(DBConfigError):
        parse_dsn("host 127.0.0.1", form="kv")      # 缺 '='


# ── 严格加法回归保护：不传 form ⇒ URI 行为逐字不变 ─────────────────────
def test_default_form_unchanged():
    info = parse_dsn(URI)
    assert info["scheme"] == "postgresql"
    assert info["host"] == "127.0.0.1"
    assert info["port"] == 5432
    assert info["db"] == "chiyu_test"
    assert info["user"] == "chiyu"
    assert info["password"] == "s3cr3t"


def test_default_form_still_rejects_kv_string():
    """旧行为：kv 串按 URI 解析 ⇒ 库名为空 ⇒ 判红。改造后 auto 才认 kv。"""
    with pytest.raises(DBConfigError):
        validate_dsn(KV, form="uri")
