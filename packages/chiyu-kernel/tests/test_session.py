from chiyu_kernel.session import SessionEvent, SessionLog, SessionManager


def test_append_orders_by_seq():
    log = SessionLog()
    a = log.append("user/message", {"content": "hi"})
    b = log.append("assistant/message", {"content": "hello"})
    assert a.seq == 1 and b.seq == 2
    assert [e.kind for e in log.events()] == ["user/message", "assistant/message"]


def test_derive_messages_projects_model_history():
    log = SessionLog()
    log.append("user/message", {"content": "q"})
    log.append("tool/call", {"name": "x", "args": {}})          # 非 model-visible，不进历史
    log.append("assistant/message", {"content": "a"})
    msgs = log.derive_messages()
    assert msgs == [
        {"role": "user", "content": "q"},
        {"role": "assistant", "content": "a"},
    ]


def test_session_manager_get_or_create():
    mgr = SessionManager()
    s1 = mgr.get_or_create("agent-a")
    s2 = mgr.get_or_create("agent-a")
    assert s1 is s2
