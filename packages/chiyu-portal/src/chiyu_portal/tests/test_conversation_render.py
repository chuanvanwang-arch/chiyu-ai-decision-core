from chiyu_portal.renderer import RenderResult, render_conversation


def test_render_conversation_ok():
    r = render_conversation(
        events=[{"role": "user", "content": "你好"},
                {"role": "assistant", "content": "在的"}],
        composer_action="send_message", goal="解答客户问题",
    )
    assert isinstance(r, RenderResult) and r.ok
    assert "你好" in r.html and "在的" in r.html
    assert "goal-bar" in r.html and "composer" in r.html


def test_render_conversation_escapes_and_no_script():
    r = render_conversation(events=[{"role": "user", "content": "<script>alert(1)</script>"}])
    assert r.ok
    assert "<script" not in r.html       # 转义后只应是 &lt;script
    assert "&lt;script" in r.html
