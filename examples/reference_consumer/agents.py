"""N6：AgentRegistry baseline 登记样例（enterprise 反馈 #6 的参考实现）。

⛔ 为什么需要本样例（enterprise blocking-feedback N6 原文）：
   foundation 把 `AgentRegistry`/`AgentSpec` 导进了门面（api.py:219-220），但
   没有任何"消费方怎么登记、在哪登记、登记什么"的样例 ⇒ 消费方各自发明
   （或干脆不登记）。本模块给出最小可用范式，消费方照抄改字段即可。

登记处（何时何地登记）：
   消费方 host **启动期装配**（build_app / control_plane 初始化）时一次性登记
   全部 agent —— 注册期拒绝保证"缺契约的 agent 停在写入之前"，若放运行期
   登记就等于回到了"事后审计才发现没契约"的老路。

三道注册期闸（见 chiyu_kernel/orchestration/agent_registry.py）：
   ① 契约完整性：key / contract_task_id / skills / memory / success 缺一即拒；
   ② 重复 key 拒绝；
   ③ 契约键唯一：一个 contract_task_id 只能被一个 agent 持有（应并入，不得另起）。

⚠️ 字段内容属消费方（key 名、skills、memory 命名空间、success 判定式都是
   领域事实），kernel 零领域字面量 —— 本样例的字段值只是**中性示例**，
   消费方必须替换为自己的领域内容。
"""
from __future__ import annotations

from typing import List, Tuple

from chiyu_kernel.api import AgentRegistry, AgentRegistryError, AgentSpec

__all__ = ["build_baseline_agents", "register_baseline_agents"]


def build_baseline_agents() -> List[AgentSpec]:
    """baseline agent 清单（中性示例字段，消费方替换为自己的领域内容）。

    每条 AgentSpec 的字段语义：
      key              —— agent 唯一名（消费方命名空间内唯一）；
      contract_task_id —— 该 agent 在契约注册表（contract-ids.json 同构物）
                          中持有的契约键，一个键只能一个 agent；
      skills           —— 该 agent 具备的技能清单（注册期强制非空）；
      memory           —— 允许读写的记忆命名空间（越界即违约）；
      knowledge_scope  —— 知识层与跳数边界（如 {"layers": ["L1"], "max_hops": 2}）；
      success          —— 成功判定式（≥8 字符且须是可判定的判据，形容词不算）。
    """
    return [
        AgentSpec(
            key="reference-consumer-agent",
            contract_task_id="ct-reference-consumer",
            skills=("scenario-decision", "outcome-recording"),
            memory=("consumer-demo",),
            knowledge_scope={"layers": ["L1"], "max_hops": 2},
            success="决策产出 SpineResult 且三条反假绿探针全绿",
        ),
    ]


def register_baseline_agents(registry: AgentRegistry) -> Tuple[str, ...]:
    """把 baseline agent 登记进 registry，返回登记后的 keys（tuple，同 registry.keys()）。

    注册期闸会**当场拒绝**不合规登记（而非事后审计）：
      - 缺 success / 空 skills ⇒ AgentRegistryError；
      - 重复 key ⇒ AgentRegistryError；
      - 契约键被他人持有 ⇒ AgentRegistryError（应并入既有 agent）。
    消费方若想验证自己的字段写对了，可直接 try/except 本函数：
    抛错即说明契约缺项，修字段再启动（fail-fast 于启动期，不进运行期）。
    """
    for spec in build_baseline_agents():
        try:
            registry.register(spec)
        except AgentRegistryError:
            # 重复启动（同进程二次 build_app）时幂等放行；其余注册期错误如实上抛
            if registry.get(spec.key) is None:
                raise
    return registry.keys()
