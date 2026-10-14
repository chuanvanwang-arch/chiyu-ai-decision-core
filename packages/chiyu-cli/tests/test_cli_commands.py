"""CLI 子命令行为测试。

⛔ 反假齐备：`decide` 必须如实报出未提供的八要素，不得用空串占位蒙混。
"""
from __future__ import annotations

import argparse
import json

from chiyu_cli.commands import decide, evolution, portal

ALL_ELEMENTS = (
    "intent", "assumptions", "inference", "viewpoints",
    "impact", "risk_register", "stop_loss", "concept_refs",
)


def _ns(**kw):
    return argparse.Namespace(**kw)


def test_decide_reports_missing_elements_honestly(capsys):
    """只给了 topic ⇒ 其余 7 项要素必须报 missing（空占位会让此项恒绿 ⇒ 假绿）。"""
    rc = decide.handler(_ns(topic="是否投入售前资源", scores=None,
                            threshold=0.79, decision_id=None, json=False, mode=None))
    out = capsys.readouterr().out
    assert rc == 0
    assert "要素缺失" in out
    missing_line = [ln for ln in out.splitlines() if ln.startswith("要素缺失")][0]
    for key in ALL_ELEMENTS:
        if key != "intent":
            assert key in missing_line, f"{key} 应被报为缺失"


def test_decide_json_shape(capsys):
    rc = decide.handler(_ns(topic="x", scores=None, threshold=0.79,
                            decision_id=None, json=True, mode=None))
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    for key in ("decision_id", "confidence", "autonomous", "redline_hit"):
        assert key in payload


def test_decide_unknown_rubric_key_rejected(capsys):
    """未知尺子键必须报错（不得静默忽略）。"""
    try:
        decide.handler(_ns(topic="x", scores="nosuch=3", threshold=0.79,
                           decision_id=None, json=True, mode=None))
    except ValueError as exc:
        assert "nosuch" in str(exc)
    else:
        raise AssertionError("未知尺子键未被拒绝")


def test_readiness_prints_ten_checks(capsys):
    rc = evolution.handler(_ns(assert_=False, json=False))
    out = capsys.readouterr().out
    assert rc == 0
    assert "checks=10" in out
    assert "red=0" in out


def test_guard_rejects_injection(capsys, tmp_path):
    """NL 含 <script 必须被输入护栏挡下并退 2。"""
    rc = portal.handler(_ns(nl="<script>alert(1)</script>", out=str(tmp_path / "a.html"),
                            title=None, particle_types=None, entity_map=None, mode=None))
    err = capsys.readouterr().err
    assert rc == 2
    assert "护栏拒绝" in err


def test_render_writes_valid_html(tmp_path, capsys):
    """带 entity-map 渲染 ⇒ 产出含 <!DOCTYPE html> 的文件。"""
    out_file = tmp_path / "page.html"
    rc = portal.handler(_ns(nl="客户360看板，客户数低于 30% 告警",
                            out=str(out_file), title="客户360",
                            particle_types=None, entity_map="客户=entity", mode=None))
    assert rc == 0
    html = out_file.read_text(encoding="utf-8")
    assert html.startswith("<!DOCTYPE html>")
    assert "客户360" in html
