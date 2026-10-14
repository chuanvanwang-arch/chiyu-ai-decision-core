"""session.prompt 接入 L1–L2 上下文装配（复用 AgentLoop 同步委派）测试。

判别项（防假绿）：
- session.prompt 返回 {accepted:true} 且该 session 会话真现 assistant/message（证明真调 LLM）；
- 会话日志须含 context/assemble 事件（装配元数据结构化落档，missing 暴露 L1/L2 缺口）；
- 变异自证：移除 pre_step 装配钩子后，context/assemble 判别项须转红（防假绿）。
"""
from __future__ import annotations

from chiyu_host.methods import session_create, session_prompt, session_history


def _kinds(sid: str):
    return [e["event"].get("type") for e in session_history({"sessionId": sid})["events"]]


def test_session_prompt_returns_accepted_and_runs_llm_turn():
    """session.prompt 须返回 accepted:true 且会话真现 assistant/message（真调 LLM 闭环）。"""
    sid = session_create({"sessionId": "sp-1"})["sessionId"]
    v = session_prompt({"sessionId": sid, "content": [{"type": "text", "text": "你好"}]})
    assert v == {"accepted": True}
    kinds = _kinds(sid)
    assert "user/message" in kinds
    assert "assistant/message" in kinds, "session.prompt 必须真调 LLM（否则假绿）"
    assert "turn/end" in kinds


def test_session_prompt_records_l1l2_assembly_metadata():
    """会话日志须含 context/assemble 事件：L1–L2 装配缺口结构化暴露（provided 为空 → missing 非空）。"""
    sid = session_create({"sessionId": "sp-2"})["sessionId"]
    session_prompt({"sessionId": sid, "content": [{"type": "text", "text": "装配"}]})
    events = [e["event"] for e in session_history({"sessionId": sid})["events"]]
    asm = [e for e in events if e.get("type") == "context/assemble"]
    assert asm, "会话缺 context/assemble 装配元数据（假绿）"
    missing = asm[0].get("data", {}).get("missing", [])
    # provided 为空 → L1/L2 均未供给 → missing 含两层（结构化，非吞）
    assert ("L1", "") in missing and ("L2", "") in missing, f"expected L1/L2 missing, got {missing}"


def test_session_prompt_assembly_metadata_requires_pre_step(monkeypatch):
    """变异自证：移除 pre_step 装配钩子 → 主判别项 context/assemble 须消失（证明判别项非真空绿）。"""
    from chiyu_host import methods
    def _no_ctx_inject(_sid):
        return lambda messages: messages  # 装配钩子被删：不写 context/assemble
    monkeypatch.setattr(methods, "_ctx_inject", _no_ctx_inject)
    sid = session_create({"sessionId": "sp-mut-1"})["sessionId"]
    session_prompt({"sessionId": sid, "content": [{"type": "text", "text": "x"}]})
    kinds = _kinds(sid)
    assert "context/assemble" not in kinds, "主判别项依赖装配钩子，移除后须转红（防假绿）"
