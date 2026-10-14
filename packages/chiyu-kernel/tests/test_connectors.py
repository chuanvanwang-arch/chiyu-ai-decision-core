"""GAP-8 connectors 传输层守卫（Batch-2b，2026-10-14）。

覆盖：文件传输三格式（csv 含 BOM / json 双形态 / xlsx 双后端）/ 非法配置
fail-closed / 外部字段名不做换算 / 注册表（登记即承诺 + 未注册抛错）/
默认注册表 / 门面与契约同一对象 / APS 锚点 parity 形态。

parity 锚点（APS 仓只读，file:line 可反证）：
    · ``platform/connectors/base.py:47``   fetch(cfg)->ConnectorResult 无状态工厂
    · ``platform/connectors/file.py:25``   csv/json/xlsx → list[dict]
    · ``platform/connectors/registry.py:30`` get_connector 未注册 KeyError
"""
from __future__ import annotations

import json

import pytest

from chiyu_kernel import api
from chiyu_kernel import connectors
from chiyu_kernel.contract import connector as contract_cn
from chiyu_kernel.contract.connector import ConnectorNotRegisteredError
from chiyu_kernel.connectors import (
    ConnectorRegistry,
    FileConnector,
    SourceConnector,
    default_registry,
)


@pytest.fixture()
def file_connector() -> FileConnector:
    return FileConnector()


# ── 文件传输 ─────────────────────────────────────────────────────────

def test_csv_read_with_bom(tmp_path, file_connector):
    p = tmp_path / "data.csv"
    p.write_text("外部名,数量\n甲,1\n乙,2\n", encoding="utf-8-sig")
    out = file_connector.fetch({"path": str(p)})
    # 外部字段名原样保留（no_conversion_in_connector：不进连接器换算）
    assert out.rows == [{"外部名": "甲", "数量": "1"}, {"外部名": "乙", "数量": "2"}]
    assert out.external_refs == [str(p)]
    assert out.meta == {"ext": "csv", "n_rows": 2}


def test_json_read_list_and_rows_envelope(tmp_path, file_connector):
    p1 = tmp_path / "a.json"
    p1.write_text(json.dumps([{"x": 1}, {"x": 2}], ensure_ascii=False), encoding="utf-8")
    assert file_connector.fetch({"path": str(p1)}).rows == [{"x": 1}, {"x": 2}]

    p2 = tmp_path / "b.json"
    p2.write_text(json.dumps({"rows": [{"y": 3}]}, ensure_ascii=False), encoding="utf-8")
    assert file_connector.fetch({"path": str(p2)}).rows == [{"y": 3}]


def test_json_invalid_shape_rejected(tmp_path, file_connector):
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"not_rows": 1}), encoding="utf-8")
    with pytest.raises(ValueError, match="rows"):
        file_connector.fetch({"path": str(p)})


def test_missing_path_and_nonexistent_file_rejected(tmp_path, file_connector):
    with pytest.raises(ValueError, match="path"):
        file_connector.fetch({})
    with pytest.raises(FileNotFoundError):
        file_connector.fetch({"path": str(tmp_path / "nope.csv")})


def test_unsupported_extension_rejected(tmp_path, file_connector):
    p = tmp_path / "d.txt"
    p.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="不支持的文件类型"):
        file_connector.fetch({"path": str(p)})


def test_xlsx_read_via_pandas(tmp_path, file_connector):
    pd = pytest.importorskip("pandas")
    p = tmp_path / "e.xlsx"
    pd.DataFrame([{"a": 1, "b": None}, {"a": 2, "b": "x"}]).to_excel(p, index=False)
    out = file_connector.fetch({"path": str(p)})
    assert out.meta["ext"] == "xlsx"
    assert out.rows[0]["a"] == 1
    assert out.rows[0]["b"] is None      # NaN → None（不污染外部字段）


def test_xlsx_openpyxl_fallback_reader(tmp_path, file_connector):
    openpyxl = pytest.importorskip("openpyxl")
    p = tmp_path / "f.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["h1", "h2"])
    ws.append([1, None])
    ws.append([None, None])               # 全空行跳过
    wb.save(p)
    rows = FileConnector._read_xlsx_openpyxl(str(p))
    assert rows == [{"h1": 1, "h2": None}]


def test_stateless_factory_refetches_per_cfg(tmp_path, file_connector):
    # 同一连接器实例按不同 cfg 拉取（无状态工厂：不持长连接/不缓存）
    p1 = tmp_path / "g1.json"
    p1.write_text(json.dumps([{"k": 1}]), encoding="utf-8")
    p2 = tmp_path / "g2.json"
    p2.write_text(json.dumps([{"k": 2}]), encoding="utf-8")
    assert file_connector.fetch({"path": str(p1)}).rows == [{"k": 1}]
    assert file_connector.fetch({"path": str(p2)}).rows == [{"k": 2}]


# ── 注册表 ───────────────────────────────────────────────────────────

def test_registry_register_get_and_names():
    reg = ConnectorRegistry()
    reg.register(FileConnector)
    assert reg.names() == ["file"]
    assert "file" in reg
    assert "db" not in reg
    got = reg.get("file")
    assert isinstance(got, FileConnector)
    # 无状态工厂：每次新实例
    assert reg.get("file") is not got


def test_registry_unregistered_fails_closed():
    reg = ConnectorRegistry()
    with pytest.raises(ConnectorNotRegisteredError, match="无已注册连接器"):
        reg.get("db")
    with pytest.raises(KeyError):  # APS 既有 except KeyError 契约保持
        reg.get("db")


def test_registry_rejects_empty_name():
    class Nameless(SourceConnector):
        name = ""

        def fetch(self, cfg):  # pragma: no cover - 不应被调用
            raise AssertionError("不应拉取")

    with pytest.raises(ValueError, match="name"):
        ConnectorRegistry().register(Nameless)


def test_registry_registration_is_promise_consumer_domain():
    # 消费方域连接器自注册（机制不含域字面量）
    class LegacyApsLike(SourceConnector):
        name = "legacy_aps"

        def fetch(self, cfg):
            from chiyu_kernel.connectors import ConnectorResult
            return ConnectorResult(rows=[{"order": 1}], external_refs=["legacy"])

    reg = default_registry()
    reg.register(LegacyApsLike)
    assert sorted(reg.names()) == ["file", "legacy_aps"]
    assert reg.get("legacy_aps").fetch({}).rows == [{"order": 1}]


def test_default_registry_has_file_transport():
    reg = default_registry()
    assert reg.names() == ["file"]
    assert isinstance(reg.get("file"), FileConnector)


# ── 契约词汇 + 门面同一对象 ─────────────────────────────────────────

def test_invariants_vocabulary_complete():
    assert set(contract_cn.CONNECTOR_INVARIANTS) == {
        "stateless_factory", "rows_are_list_of_dicts",
        "no_conversion_in_connector", "registration_is_promise",
        "unregistered_fails_closed",
    }
    assert contract_cn.FILE_CONNECTOR_FORMATS == ("csv", "json", "xlsx")


def test_facade_exports_all_connector_symbols():
    names = [
        "CONNECTOR_RESULT_FIELDS", "CONNECTOR_NAME_FIELD",
        "FILE_CONNECTOR_FORMATS", "CONNECTOR_INVARIANTS",
        "ConnectorNotRegisteredError",
        "ConnectorResult", "SourceConnector", "FileConnector",
        "ConnectorRegistry", "default_registry",
    ]
    for n in names:
        assert hasattr(api, n), f"门面缺 {n}"
        assert n in api.__all__, f"__all__ 缺 {n}"


def test_facade_symbols_are_same_objects():
    for n in ("FILE_CONNECTOR_FORMATS", "ConnectorNotRegisteredError"):
        assert getattr(api, n) is getattr(contract_cn, n)
    for n in ("FileConnector", "ConnectorRegistry", "default_registry",
              "ConnectorResult", "SourceConnector"):
        assert getattr(api, n) is getattr(connectors, n)


def test_source_connector_is_abstract():
    with pytest.raises(TypeError):
        SourceConnector()  # type: ignore[abstract]
