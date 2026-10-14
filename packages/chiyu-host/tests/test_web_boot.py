"""chiyu-host Web 表面单测：离线重建 boot 图 + 注入 + 静态路由（不依赖 DSH 真实构建）。

T3-2/T3-3 判别式：boot 图只收录 dsh.client.platform==='web' 的包；注入转义 '<'；
GET /plugins/<id>/client.js 寻址正确；未知包/非 client.js 后缀 → 404；dist 未构建 → 503。
"""
import json

import pytest
from fastapi.testclient import TestClient

from chiyu_host import web as web_surface
from chiyu_host.app import app


@pytest.fixture
def fake_dsh(tmp_path, monkeypatch):
    def pkg(scope_name, decl, client_body: bytes = b"// bundle"):
        d = tmp_path / "packages" / "client" / scope_name
        d.mkdir(parents=True)
        (d / "package.json").write_text(
            json.dumps(
                {
                    "name": f"@deepseek-ai/{scope_name}",
                    "exports": {"./client": {"default": "./lib/client.js"}},
                    "dsh": {"client": decl},
                }
            ),
            encoding="utf-8",
        )
        (d / "lib").mkdir()
        (d / "lib" / "client.js").write_bytes(client_body)

    pkg("dsh-client-ui-conversation",
        {"platform": "web", "inject": ["@deepseek-ai/dsh-client-connection"]})
    pkg("dsh-client-ui-model-selection", {"platform": "web"})
    # 非 web 平台包：不应进入 boot 图
    d = tmp_path / "packages" / "client" / "dsh-client-lib"
    d.mkdir(parents=True)
    (d / "package.json").write_text(
        json.dumps(
            {
                "name": "@deepseek-ai/dsh-client-lib",
                "exports": {"./client": "./lib/client.js"},
                "dsh": {"client": {"platform": "node"}},
            }
        ),
        encoding="utf-8",
    )
    (d / "lib").mkdir()
    (d / "lib" / "client.js").write_bytes(b"// node bundle")

    monkeypatch.setenv("DSH_CLIENT_DIR", str(tmp_path))
    web_surface._SURFACE_CACHE.clear()
    return tmp_path


def test_compose_boot_graph_scans_web_only(fake_dsh):
    graph = web_surface.compose_boot_graph(str(fake_dsh))
    ids = {e["id"] for e in graph["entries"]}
    assert ids == {
        "@deepseek-ai/dsh-client-ui-conversation",
        "@deepseek-ai/dsh-client-ui-model-selection",
    }
    conv = next(e for e in graph["entries"] if e["id"].endswith("ui-conversation"))
    assert conv["url"].startswith(
        "/plugins/@deepseek-ai/dsh-client-ui-conversation/client.js?rev="
    )
    assert conv["inject"] == ["@deepseek-ai/dsh-client-connection"]
    assert graph["rev"] == web_surface._short_hash(
        json.dumps(graph["entries"], sort_keys=True).encode()
    )


def test_inject_boot_manifest_escapes_lt(fake_dsh):
    html = "<!doctype html><html><head><title>x</title></head><body></body></html>"
    graph = web_surface.compose_boot_graph(str(fake_dsh))
    out = web_surface.inject_boot_manifest(html, graph)
    assert "window.__DSH_BOOT__" in out
    assert out.index("<script>window.__DSH_BOOT__") < out.index("</head>")
    # 插件受控字符串含 '<' 必须转义，防逃逸 script 元素
    evil = {"rev": "r", "entries": [{"id": "a", "url": "x", "rev": "r", "inject": ["<script>"]}]}
    out2 = web_surface.inject_boot_manifest(html, evil)
    injected = out2.split("window.__DSH_BOOT__ =", 1)[1].split("</script>", 1)[0]
    assert "\\u003c" in out2 and "<script>" not in injected


def test_routes_serve_bundle_and_404(fake_dsh):
    client = TestClient(app)
    graph = web_surface.compose_boot_graph(str(fake_dsh))
    conv = next(e for e in graph["entries"] if e["id"].endswith("ui-conversation"))
    resp = client.get(
        f"/plugins/@deepseek-ai/dsh-client-ui-conversation/client.js?rev={conv['rev']}"
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/javascript")
    assert resp.text == "// bundle"
    # 未知包 → 404
    assert client.get("/plugins/@deepseek-ai/nope/client.js").status_code == 404
    # 非 client.js 后缀 → 404
    assert client.get("/plugins/@deepseek-ai/dsh-client-ui-conversation/other.js").status_code == 404
    # dist 未构建 → 503
    assert client.get("/").status_code == 503
