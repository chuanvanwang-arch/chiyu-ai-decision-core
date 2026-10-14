"""TeamRegistry：建团（≤5）/成员权限天花板/任务认领乐观锁/状态机/消息 FIFO。"""
import pytest

from chiyu_kernel.api import (TeamRegistry, TeamSpec, TeamMember, SharedTask)


def _spec(tid="t1", n=2, lead_allowlist=("a.read", "a.op0", "a.op1")):
    members = {f"m{i}": TeamMember(key=f"m{i}", role=f"角色{i}",
                                   action_allowlist=("a.read", f"a.op{i}"))
               for i in range(n)}
    return TeamSpec(id=tid, name="团队", lead_key="lead", members=members,
                    lead_allowlist=lead_allowlist)


def test_create_team_member_cap():
    r = TeamRegistry()
    r.create_team(_spec())
    with pytest.raises(ValueError, match="成员数"):
        r.create_team(_spec(tid="t2", n=6))


def test_permission_ceiling_member_subset_of_lead():
    r = TeamRegistry()
    r.create_team(_spec())
    # 成员 allowlist 必须是 lead.allowlist 子集（lead 声明全集）；
    # lead 只声明 a.read → m0/m1 的 a.op0/a.op1 超出 → 拒绝
    with pytest.raises(ValueError, match="权限天花板"):
        r.create_team(_spec(tid="t3", n=2, lead_allowlist=("a.read",)))
    # lead 未声明 allowlist（None）→ 不设限（企业层由 RBAC 补判）
    r2 = TeamRegistry()
    r2.create_team(TeamSpec(id="t4", name="t", lead_key="lead",
                            members={"m0": TeamMember(key="m0", role="r",
                                                      action_allowlist=("x.any",))}))
    r2.add_member("t4", TeamMember(key="m1", role="r2", action_allowlist=("x.any", "y.any")))


def test_claim_optimistic_lock():
    r = TeamRegistry()
    r.create_team(_spec())
    r.create_task("t1", SharedTask(id="k1", title="任务",
                                   write_scope=("a.read",)))
    ref = r.claim_task("t1", "k1", member_key="m0", revision=1)
    assert ref["status"] == "claimed"
    with pytest.raises(RuntimeError, match="版本冲突"):
        r.claim_task("t1", "k1", member_key="m1", revision=1)
    with pytest.raises(RuntimeError, match="状态机"):
        r.claim_task("t1", "k1", member_key="m1", revision=2)


def test_task_state_machine_transitions():
    r = TeamRegistry()
    r.create_team(_spec())
    r.create_task("t1", SharedTask(id="k1", title="t"))
    r.claim_task("t1", "k1", member_key="m0", revision=1)
    ref = r.update_task("t1", "k1", revision=2, status="running")
    assert ref["status"] == "running"
    ref = r.update_task("t1", "k1", revision=3, status="done")
    assert ref["status"] == "done"
    with pytest.raises(RuntimeError):
        r.update_task("t1", "k1", revision=4, status="running")  # done 终态


def test_message_fifo_and_board():
    r = TeamRegistry()
    r.create_team(_spec())
    r.send_message("t1", from_key="lead", to_key="m0", text="开工")
    r.send_message("t1", from_key="m0", to_key="lead", text="收到")
    board = r.board("t1")
    assert len(board["messages"]) == 2
    assert board["messages"][0]["text"] == "开工"
    assert board["tasks"] == [] or isinstance(board["tasks"], list)
