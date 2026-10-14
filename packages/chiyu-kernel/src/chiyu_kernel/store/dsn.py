"""DSN 与 schema 名解析 —— 存储层**唯一入口**（内核通用版）。

⛔ 与 demo `db/dsn.py` 的差异（设计 §0.3 + 零领域字面量原则）
────────────────────────────────────────────────────────────
demo 把 `bj12345` / `bj12345_app` / `bj_t_*` / 端口 5433 焊成模块常量 —— 那是
**群诉域的部署名**。内核不得携带任意领域/部署字面量，故拆成两轨：

    · 通用约束（进内核，任意域都成立）：\n        禁连被禁主机 · 应用禁超级用户 · scheme 必须 postgresql ·\n        缺 DSN 不默认回退 · schema 名须白名单化\n    · 领域取值（外移调用方）：库名前缀、测试库名、默认 schema、端口\n        —— 由调用方从 env 读，内核只校验形态不写死取值。

⛔ DSN 只从 env 读，源码零硬编码口令。`mask_dsn()` 是唯一允许的日志形态。
⛔ 校验放在取 DSN 那一刻：误配打进生产是**运行期**事故，配置错就起不来。
"""
from __future__ import annotations

import os
import re
import urllib.parse as _up

# ── env 键名（消费方可覆盖；此处为默认名）──────────────────────────────
DSN_ENV = "CHIYU_DB_DSN"
DSN_TEST_ENV = "CHIYU_DB_DSN_TEST"
SCHEMA_ENV = "CHIYU_DB_SCHEMA"
DB_TESTING_ENV = "CHIYU_DB_TESTING"
TESTING_FLAG_ENV = "CHIYU_TEST"

# ⛔ 通用红线：任何环境都不得指向被禁主机 / 以超级用户连接
FORBIDDEN_HOSTS = ("81.70.184.198",)          # 生产机（CRM 侧），任何库都不得连
FORBIDDEN_ROLES = ("postgres", "supabase_admin", "rdsadmin", "admin")

# schema 名白名单长度上限（PG 标识符 63 字节）
IDENT_MAX = 63


class DBConfigError(RuntimeError):
    """DSN/schema 配置违规。**必须显式抛出**，不得静默回退到默认库。"""


def in_testing_context() -> bool:
    return (os.environ.get(TESTING_FLAG_ENV) == "1"
            or os.environ.get(DB_TESTING_ENV) == "1")


def _effective_testing(testing: bool | None) -> bool:
    return bool(testing) if testing is not None else in_testing_context()


def raw_dsn(*, testing: bool | None = None,
            dsn_env: str | None = None,
            dsn_test_env: str | None = None) -> str:
    """读原始 DSN（不校验）。testing 时优先取测试 DSN，缺则回退主 DSN。

    `dsn_env` / `dsn_test_env` 允许消费方注入自己的 env 键名（R2：第③坑收口）。
    ⛔ 不传即走模块默认键，**既有调用零影响**（严格加法）。
    """
    main_key = dsn_env or DSN_ENV
    test_key = dsn_test_env or DSN_TEST_ENV
    if _effective_testing(testing):
        return (os.environ.get(test_key) or "").strip() \
            or (os.environ.get(main_key) or "").strip()
    return (os.environ.get(main_key) or "").strip()


def mask_dsn(dsn: str | None) -> str:
    """日志安全形态：`postgresql://user@host:port/db`（口令段一律抹去）。"""
    if not dsn:
        return "<empty>"
    try:
        u = _up.urlparse(dsn)
        return (f"{u.scheme}://{u.username or '?'}@{u.hostname or '?'}:"
                f"{u.port or '?'}{u.path or ''}")
    except Exception:                                    # noqa: BLE001
        return "<unparsable>"


#: `parse_dsn` 允许的形态。
VALID_FORMS = ("auto", "uri", "kv")

#: keyword/value 形态的键名 → 归一化字段名（`port` 另需转 int，见 `_parse_kv`）。
_KV_FIELDS = {"dbname": "db", "host": "host", "user": "user", "password": "password"}


def _parse_uri(dsn: str) -> dict:
    u = _up.urlparse(dsn)
    return {
        "scheme": u.scheme,
        "user": u.username,
        "password": u.password,
        "host": u.hostname,
        "port": u.port,
        "db": (u.path or "").lstrip("/"),
    }


def _parse_kv(dsn: str) -> dict:
    """解析 keyword/value 形态（`host=… port=… dbname=… user=…`）。

    ⛔ `password` 可缺省：校验连接形态不需要口令，这正是免构造中间串的价值。
    ⛔ 未知键（sslmode / connect_timeout 等 libpq 参数）与红线判定无关，显式忽略；
       但**缺 `=` 的字段**必须报错，否则畸形串会静默解析成"无主机无库"而绕过红线。
    """
    info: dict = {"scheme": "postgresql", "user": None, "password": None,
                  "host": None, "port": None, "db": ""}
    for tok in dsn.split():
        if "=" not in tok:
            raise DBConfigError(
                f"DSN 的 keyword/value 形态字段缺 '='：{tok!r}（形如 host=127.0.0.1）")
        key, _, val = tok.partition("=")
        key = key.strip().lower()
        if key == "port":
            if not val.isdigit():
                raise DBConfigError(f"DSN 的 port 非数字：{val!r}")
            info["port"] = int(val)
        elif key in _KV_FIELDS:
            info[_KV_FIELDS[key]] = val
    return info


def parse_dsn(dsn: str, form: str = "auto") -> dict:
    """解析 DSN，`form` 取 `auto`（默认）/ `uri` / `kv`。

    ⛔ 严格加法：`form` 缺省为 `auto`，含 `://` 走 URI、否则走 kv —— 既有 URI
       调用行为**逐字不变**；显式 `uri` 时 kv 串仍按旧行为判红。
    """
    if form not in VALID_FORMS:
        raise DBConfigError(
            f"DSN form 必须为 {'/'.join(VALID_FORMS)}，实际 {form!r}")
    if form == "uri":
        return _parse_uri(dsn)
    if form == "kv":
        return _parse_kv(dsn)
    return _parse_kv(dsn) if "://" not in dsn else _parse_uri(dsn)


def validate_dsn(dsn: str, *, required_db_prefix: str = "",
                 testing_db_suffix: str = "",
                 dsn_env: str | None = None,
                 dsn_test_env: str | None = None,
                 form: str = "auto") -> dict:
    """校验并返回解析结果。任一通用红线命中 ⇒ 抛 `DBConfigError`。

    ⛔ 领域取值由调用方传入：`required_db_prefix`（库名须以此开头）与
       `testing_db_suffix`（测试库名须以此结尾，缺省"不强制"）。
       内核不写死 `bj`/`bj12345_test`，故这两项无默认领域值。

    ⛔ 报错文案必须引用**实际使用的键名**（`dsn_env` / `dsn_test_env` 注入值），
       不得硬编码默认键 —— 否则消费方传了自定义键却缺配置时，报错指向
       它从未用过的键名，诊断被误导（R2 判据二）。
    """
    if not dsn:
        main_key = dsn_env or DSN_ENV
        test_key = dsn_test_env or DSN_TEST_ENV
        raise DBConfigError(f"未配置 {main_key}（测试环境可用 {test_key}）；"
                            f"内核**无 SQLite 回退**，缺 DSN 即不可用。")
    info = parse_dsn(dsn, form=form)
    if info["scheme"] not in ("postgresql", "postgres"):
        raise DBConfigError(f"DSN scheme 必须为 postgresql，实际 {info['scheme']!r}")
    if not info["db"]:
        raise DBConfigError("DSN 缺库名（形如 postgresql://user:pwd@host:5433/db）")
    if info["host"] in FORBIDDEN_HOSTS:
        raise DBConfigError(f"DSN 指向被禁主机 {info['host']}（红线：禁连生产机）")
    if required_db_prefix and not info["db"].startswith(required_db_prefix):
        raise DBConfigError(
            f"DSN 库名 {info['db']!r} 不以 {required_db_prefix!r} 开头（禁跨库）")
    if testing_db_suffix and not info["db"].endswith(testing_db_suffix):
        raise DBConfigError(
            f"测试库名必须 {testing_db_suffix!r} 结尾，实际 {info['db']!r}")
    if info["user"] in FORBIDDEN_ROLES:
        raise DBConfigError(f"应用连接禁止使用超级用户 {info['user']!r}（红线）")
    return info


def get_dsn(*, testing: bool | None = None,
            required_db_prefix: str = "", testing_db_suffix: str = "",
            dsn_env: str | None = None,
            dsn_test_env: str | None = None,
            form: str = "auto") -> str:
    dsn = raw_dsn(testing=testing, dsn_env=dsn_env, dsn_test_env=dsn_test_env)
    validate_dsn(dsn, required_db_prefix=required_db_prefix,
                 testing_db_suffix=testing_db_suffix,
                 dsn_env=dsn_env, dsn_test_env=dsn_test_env, form=form)
    return dsn


def get_schema(default: str = "", *, schema_env: str | None = None) -> str:
    """读 schema 名。`schema_env` 可注入自定义 env 键名（R2）；不传走默认键。"""
    key = schema_env or SCHEMA_ENV
    v = (os.environ.get(key) or "").strip()
    return v or default


def assert_safe_identifier(name: str, *, what: str = "identifier",
                           max_len: int = IDENT_MAX) -> str:
    """schema/表名是拼进 SQL 的，必须白名单化（PG 不允许参数化标识符）。

    ⛔ 只放行 `[a-z0-9_]` 且以字母开头 —— 防注入口子；且长度 ≤ max_len（63），
       防超长 schema 名被 PG 静默截断后指向错误对象（实测类隐患）。
    """
    if not name:
        raise DBConfigError(f"{what} 不得为空")
    if len(name) > max_len:
        raise DBConfigError(f"{what} 过长（{len(name)} > {max_len}）：{name!r} 会被截断")
    if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
        raise DBConfigError(f"非法 {what}: {name!r}（仅允许 [a-z][a-z0-9_]*）")
    return name


__all__ = ["DSN_ENV", "DSN_TEST_ENV", "SCHEMA_ENV", "DB_TESTING_ENV",
           "TESTING_FLAG_ENV", "FORBIDDEN_HOSTS", "FORBIDDEN_ROLES",
           "IDENT_MAX", "VALID_FORMS", "DBConfigError", "in_testing_context",
           "raw_dsn", "mask_dsn", "parse_dsn", "validate_dsn", "get_dsn",
           "get_schema", "assert_safe_identifier"]
