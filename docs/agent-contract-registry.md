# Agent 契约注册表登记处（N6）

> 状态：**已生效**（2026-10-09，N6 落地）
> 样例：`examples/reference_consumer/agents.py`（最小可运行范本 + 测试）
> 机制：`chiyu_kernel/orchestration/agent_registry.py`（注册期拒绝，非事后审计）

---

## 1. 消费方应在**何处**登记

**host 启动期装配**（build_app / control_plane 初始化）时一次性登记全部 agent。
注册期拒绝保证"缺契约的 agent 停在写入之前"；运行期动态登记 = 回到"事后审计才发现没契约"的老路，⛔ 禁止。

## 2. 登记什么（AgentSpec 六字段）

| 字段 | 必填 | 语义 |
|---|---|---|
| `key` | ✅ | agent 唯一名（消费方命名空间内唯一，重复即拒） |
| `contract_task_id` | ✅ | 该 agent 持有的契约键；**一个键只能一个 agent**（被他人持有即拒，应并入既有 agent 而非另起） |
| `skills` | ✅ | 该 agent 具备的技能清单（空即拒） |
| `memory` | ✅ | 允许读写的记忆命名空间（越界即违约） |
| `knowledge_scope` | 建议 | 知识层与跳数边界，行内写法 `{"layers": ["L1"], "max_hops": 2}` |
| `success` | ✅ | 成功判定式（≥8 字符且须可判定；形容词不算判据） |

## 3. 契约键的**唯一事实源**

- 本仓：`contract/contract-ids.json`（如 `ct-chiyu-foundation` → `foundation-builder`）。
- 消费方仓：各自维护同构注册表；跨仓闭合时 `contract_task_id` 的归属由
  workbench 校验（`registryChecked=true`）。
- ⛔ `contract_task_id` 不得凭空捏造：先在注册表登记键，再写 agent。

## 4. 注册期三道闸（违反即 `AgentRegistryError`，当场拒绝）

1. 契约完整性：key / contract_task_id / skills / memory / success 缺一即拒；
2. 重复 key 拒绝；
3. 契约键唯一性：一个 `contract_task_id` 只能被一个 agent 持有。

## 5. 最小可运行范本

见 `examples/reference_consumer/agents.py`：

```python
from chiyu_kernel.api import AgentRegistry, AgentRegistryError, AgentSpec
from reference_consumer.agents import register_baseline_agents

registry = AgentRegistry()
register_baseline_agents(registry)     # 抛 AgentRegistryError = 契约缺项，启动期即暴露
```

守卫测试：`examples/reference_consumer/tests/test_agents_registry.py`
（缺契约即拒、重复即拒、重复启动幂等放行）。
