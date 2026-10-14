"""平台只读控制面 + 场景包读写 + RBAC + 双模型映射 + 变异自证。"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from chiyu_host.app import app


def _write_pack(store_dir: Path, pkg: str, body: dict) -> None:
    (store_dir / f"{pkg}.json").write_text(json.dumps(body), encoding="utf-8")


def test_control_scenarios_read_only_lists_disk(monkeypatch, tmp_path: Path) -> None:
    d = tmp_path / "scenario_packs"
    d.mkdir()
    from chiyu_host import scenario_store
    monkeypatch.setattr(scenario_store, "packs_dir", lambda: d)
    _write_pack(d, "sales-north", {"pkg": "sales-north", "namespace": "sales",
        "tenant": "t-default", "actions": ["sales.native.action_propose"],
        "assets": [{"layer": "L1", "dims": ["semantics"]}], "integrations": [],
        "status": "draft"})
    client = TestClient(app)
    r = client.get("/control/scenarios")
    assert r.status_code == 200
    data = r.json()
    assert data["items"]
    pkgs = [i["pkg"] for i in data["items"]]
    assert "sales-north" in pkgs


def test_control_scenario_by_name(monkeypatch, tmp_path: Path) -> None:
    d = tmp_path / "scenario_packs"
    d.mkdir()
    from chiyu_host import scenario_store
    monkeypatch.setattr(scenario_store, "packs_dir", lambda: d)
    _write_pack(d, "sales-north", {"pkg": "sales-north", "namespace": "sales",
        "tenant": "t-default", "actions": [], "assets": [], "integrations": [],
        "status": "draft"})
    client = TestClient(app)
    r = client.get("/control/scenario/sales-north")
    assert r.status_code == 200
    assert r.json()["pkg"] == "sales-north"


def test_control_scenario_missing_404(monkeypatch, tmp_path: Path) -> None:
    d = tmp_path / "scenario_packs"
    d.mkdir()
    from chiyu_host import scenario_store
    monkeypatch.setattr(scenario_store, "packs_dir", lambda: d)
    client = TestClient(app)
    r = client.get("/control/scenario/does-not-exist")
    assert r.status_code == 404


def test_control_rbac_lists_roles() -> None:
    client = TestClient(app)
    r = client.get("/control/rbac")
    assert r.status_code == 200
    roles = {u["role"] for u in r.json()["users"]}
    assert {"admin", "finance", "sales_manager"}.issubset(roles)


def test_control_agents_by_role() -> None:
    client = TestClient(app)
    r = client.get("/control/agents/sales_manager")
    assert r.status_code == 200
    assert "sales_manager" == r.json()["role"]


def test_control_agents_unknown_role_404() -> None:
    client = TestClient(app)
    r = client.get("/control/agents/nobody")
    assert r.status_code == 404


# ── 写接口（T2）──

def _dev_headers(role: str = "dev.admin") -> dict:
    return {"Authorization": f"Bearer t-default-{role}"}


def test_post_control_scenarios_rejects_non_dev(monkeypatch, tmp_path: Path) -> None:
    """非 dev.*/admin 用户名写场景包 → 403（开发/运行权限隔离红线）。"""
    d = tmp_path / "scenario_packs"
    d.mkdir()
    from chiyu_host import scenario_store
    monkeypatch.setattr(scenario_store, "packs_dir", lambda: d)
    client = TestClient(app)
    r = client.post("/control/scenarios",
        headers=_dev_headers("finance"),
        json={"pkg": "sales-north", "namespace": "sales", "tenant": "t-default",
              "actions": [], "assets": [], "integrations": [], "status": "draft"})
    assert r.status_code == 403


def test_post_missing_token_401(monkeypatch, tmp_path: Path) -> None:
    d = tmp_path / "scenario_packs"
    d.mkdir()
    from chiyu_host import scenario_store
    monkeypatch.setattr(scenario_store, "packs_dir", lambda: d)
    client = TestClient(app)
    r = client.post("/control/scenarios",
        json={"pkg": "sales-north", "namespace": "sales", "tenant": "t-default",
              "actions": [], "assets": [], "integrations": [], "status": "draft"})
    assert r.status_code == 401


def test_post_control_scenarios_dev_writes(monkeypatch, tmp_path: Path) -> None:
    """dev.* 用户名写场景包 → 200 落盘；非法模型（assets.layer 越界）→ 422。"""
    d = tmp_path / "scenario_packs"
    d.mkdir()
    from chiyu_host import scenario_store
    monkeypatch.setattr(scenario_store, "packs_dir", lambda: d)
    client = TestClient(app)
    good = {"pkg": "sales-north", "namespace": "sales", "tenant": "t-default",
            "actions": ["sales.native.action_propose"],
            "assets": [{"layer": "L1", "dims": ["semantics"]}],
            "integrations": [], "status": "draft"}
    r = client.post("/control/scenarios", headers=_dev_headers(), json=good)
    assert r.status_code == 200
    assert r.json()["pkg"] == "sales-north"
    assert (d / "sales-north.json").exists()

    # 非法模型：assets.layer 越界 → 422（经 kernel scenario_from_dict 校验）
    bad = dict(good)
    bad["pkg"] = "bad-pack"
    bad["assets"] = [{"layer": "L9", "dims": ["x"]}]
    r2 = client.post("/control/scenarios", headers=_dev_headers(), json=bad)
    assert r2.status_code == 422


def test_lock_requires_confirm_and_role(monkeypatch, tmp_path: Path) -> None:
    """锁定写操作：无 confirm → 400；dev+confirm → 200 且 locked_by 落盘。"""
    d = tmp_path / "scenario_packs"
    d.mkdir()
    from chiyu_host import scenario_store
    monkeypatch.setattr(scenario_store, "packs_dir", lambda: d)
    client = TestClient(app)
    dev = _dev_headers()
    client.post("/control/scenarios", headers=dev,
                json={"pkg": "sales-north", "namespace": "sales", "tenant": "t-default",
                      "actions": [], "assets": [], "integrations": [], "status": "draft"})

    # 无 confirm → 400
    r = client.post("/control/scenario/sales-north/lock", headers=dev, json={"holder": "dev-x"})
    assert r.status_code == 400

    # 非 dev → 403
    r1 = client.post("/control/scenario/sales-north/lock", headers=_dev_headers("finance"),
                     json={"holder": "dev-x", "confirm": True})
    assert r1.status_code == 403

    # dev + confirm → 200，locked_by 落盘
    r2 = client.post("/control/scenario/sales-north/lock", headers=dev,
                     json={"holder": "dev-x", "confirm": True})
    assert r2.status_code == 200
    saved = json.loads((d / "sales-north.json").read_text(encoding="utf-8"))
    assert saved["locked_by"] == "dev-x"


# ── MCP server（T3）──

def _load_mcp_server():
    """从仓根 tools/mcp_scenario_server.py 加载（避免依赖 import tools 包路径）。"""
    import importlib.util
    root = Path(__file__).resolve().parents[3]
    path = root / "tools" / "mcp_scenario_server.py"
    spec = importlib.util.spec_from_file_location("mcp_scenario_server", path)
    assert spec and spec.loader, f"无法定位 mcp_scenario_server.py at {path}"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_mcp_server_three_tools() -> None:
    from chiyu_kernel.mcp import InMemoryMcpServer
    m = _load_mcp_server()
    srv = m.build_server()
    assert isinstance(srv, InMemoryMcpServer)
    names = {t.raw_name for t in srv.list_tools()}
    assert {"scenario-pack-write", "scenario-pack-list", "scenario-pack-lock"} <= names


def test_mcp_server_list_tool_calls_platform(monkeypatch) -> None:
    m = _load_mcp_server()
    captured = {}
    def fake_http(method, path, body=None):
        captured["method"] = method
        captured["path"] = path
        return {"items": [{"pkg": "flow-sales"}]}
    monkeypatch.setattr(m, "_http", fake_http)
    out = m._tool_list({})
    assert out["items"][0]["pkg"] == "flow-sales"
    assert captured["method"] == "GET"
    assert captured["path"] == "/control/scenarios"


def test_mcp_server_lock_requires_confirm() -> None:
    m = _load_mcp_server()
    import pytest as _pt
    # 无 confirm → 抛错
    with _pt.raises(ValueError):
        m._tool_lock({"id": "flow-sales"})
    # 有 confirm → 调平台
    captured = {}
    def fake_http(method, path, body=None):
        captured["confirm"] = body.get("confirm")
        return {"pkg": "flow-sales", "locked_by": "dev"}
    m._http = fake_http
    out = m._tool_lock({"id": "flow-sales", "confirm": True})
    assert out["locked_by"] == "dev"
    assert captured["confirm"] is True


def test_mapper_roundtrip() -> None:
    """kernel→platform→kernel 往返一致（platform_to_pack 后再 pack_to_platform 不丢 actions）。"""
    from chiyu_host.scenario_mapper import pack_to_platform, platform_to_pack
    kernel = {"id": "flow-sales", "name": "flow-sales", "level": "flow", "mode": "standard",
              "plugins": ["loop"], "direction": "sales",
              "workflow": {"steps": [{"name": "step-0", "prompt": "sales.native.action_propose",
                                      "depends_on": []}]},
              "knowledge_needs": [{"layer": "L1", "dims": ["semantics"]}]}
    platform = pack_to_platform(kernel, tenant="t-default")
    assert platform["pkg"] == "flow-sales"
    assert platform["actions"] == ["sales.native.action_propose"]
    # 转回 kernel 再校验
    back = platform_to_pack(platform)
    from chiyu_kernel.api import scenario_from_dict
    scenario_from_dict(back)  # 不应抛


def test_mapper_roundtrip_preserves_actions() -> None:
    """往返后 actions 不丢失且方向/层保持。"""
    from chiyu_host.scenario_mapper import pack_to_platform, platform_to_pack
    kernel = {"id": "end2end-sales", "name": "end2end-sales", "level": "end2end",
              "mode": "standard", "plugins": ["loop", "web_search"], "direction": "sales",
              "workflow": {"steps": [
                  {"name": "step-0", "prompt": "sales.native.action_propose", "depends_on": []},
                  {"name": "step-1", "prompt": "sales.native.action_close", "depends_on": ["step-0"]}]},
              "knowledge_needs": [{"layer": "L1", "dims": ["semantics"]},
                                  {"layer": "L2", "dims": ["decision"]}]}
    platform = pack_to_platform(kernel)
    back = platform_to_pack(platform)
    assert back["id"] == "end2end-sales"
    assert back["level"] == "end2end"
    # actions=steps 的 prompt 序列不可丢
    assert [s["prompt"] for s in back["workflow"]["steps"]] == [
        "sales.native.action_propose", "sales.native.action_close"]
    assert back["direction"] == "sales"


def test_perm_matrix() -> None:
    """权限矩阵：admin 可写；finance/sales_manager 不可写（403）。"""
    from chiyu_host.scenario_store import ROLL_ROLES
    assert "scenario.write" in ROLL_ROLES["admin"]
    assert "scenario.write" not in ROLL_ROLES["finance"]
    assert "scenario.write" not in ROLL_ROLES["sales_manager"]


def test_perm_matrix_dev_admin_writes() -> None:
    """dev.admin 有完整写权限（开发身份）。"""
    from chiyu_host.scenario_store import ROLL_ROLES
    assert "scenario.write" in ROLL_ROLES["dev.admin"]
    assert "scenario.write" in ROLL_ROLES["admin"]
