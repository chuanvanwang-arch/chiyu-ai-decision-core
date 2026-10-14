# MCP Transport 接口契约（CRM R5 · 2026-10-09）

> 状态：**正式交付**（CRM 回信 R5 "MCP transport 接口规范，使自实现可回捐为范式"）
> 日期：2026-10-09
> 致：CRM-ai-native（Node 侧 transport 自实现 + 回捐）
> 关联：`docs/2026-10-09-CRM-回信-对专项建议的答复.md` §R5 与 §F-03
> 取证基线：foundation 2026-10-09 工作树；契约真值来源 `chiyu_kernel/mcp/__init__.py`

---

## 0. 一句话

底座不落地网络 transport（`mcp/__init__.py:4` 明示 stdio / Streamable HTTP 不在本阶段），但把 `McpTransport` 定义成**协议**。本契约即该协议的**语言无关规格**：任何实现 `McpTransport` 四方法的 transport，都能被 `McpBridge` 接入并注册进 `ToolRegistry`，无需改底底座一行。CRM 自实现（Node）按本契约回捐即成为范式，无成本。

---

## 1. Transport 抽象接口（四方法，生命周期有序）

`McpTransport` 是契约的核心（`mcp/__init__.py:25`）。任意语言实现**必须且只实现**这四个方法：

| 方法 | 签名（语言无关语义） | 前置条件 | 行为契约 |
|---|---|---|---|
| `connect()` | `() -> void` | 未连接 | 建立到 MCP server 的连接。**幂等**：已连接再调不报错（可重入）。 |
| `list_tools()` | `() -> ToolDef[]` | 已 connect | 返回该 server 的工具枚举。`ToolDef = {raw_name: string, description: string}`。不得在连接前调用（应抛）。 |
| `call_tool(raw_name, args)` | `(string, map) -> any` | 已 connect | 调用 `raw_name` 对应工具。`args` 为扁平 map。工具不存在 ⇒ 抛（见 §4 错误语义）。返回值直通调用方。 |
| `disconnect()` | `() -> void` | 已 connect | 释放连接。**幂等**：重复调用不报错。 |

**生命周期状态机**：
```
[new] --connect()--> [connected] --list_tools()/call_tool()*--> [connected]
                      [connected] --disconnect()--> [closed]（终态，不得再 connect）
```
> 违反序（未 connect 即 list_tools / 已 closed 再 connect）应 fail-fast；实现侧可自行选择抛错或安全降级，但**不得静默返回伪造数据**。

---

## 2. `McpBridge` 编排契约（transport 如何被接入）

`McpBridge`（`mcp/__init__.py:77`）是 transport 的**唯一消费者**。CRM 回捐 transport 时，须保证被 `McpBridge` 按下列方式驱动：

1. **构造**：`McpBridge(transport, server_name)`。
   - `server_name` 须匹配 `^[A-Za-z0-9_-]{1,32}$`（`:79` 校验）；不匹配 ⇒ 构造期抛。
   - **命名空间唯一**：同进程内 `server_name` 不得复用（`:91-92` 预留集合判定，占用即抛 `ValueError`）。
2. **接入**：`bridge.connect(registry)` → 依次 `transport.connect()` → 对 `list_tools()` 每个工具 `registry.register(ToolSpec, impl)`，返回注册的 public 名列表。
3. **调用**：`bridge.call_tool(public_name, args)` → 内部按 public→raw 映射后 `transport.call_tool(raw, args)`。
4. **释放**：`bridge.disconnect(registry)` → 反注册全部工具 + `transport.disconnect()` + 释放命名空间预留。

> **回捐边界**：CRM 只需实现 transport（§1 四方法）；`McpBridge` 的编排逻辑属底座，CRM 回捐 Node 时**不应重造**，而应复用本契约语义（或直接对齐等价实现）。

---

## 3. 命名契约（public 名派生，防塌缩）

工具注册进 `ToolRegistry` 的 public 名由 `normalize_mcp_name`（`:66`）派生：

```
public = "mcp__" + server_name + "__" + raw_name
   ├─ 若长度 ≤ 64         → 直接作为 public 名
   └─ 若长度 > 64         → 非 [A-Za-z0-9_-] 字符替换为 '_'，截断到 (64-12-2)，
                            末尾追加 "__" + SHA-256(base)[:12]
```

- **目的**：避免不同 server/raw 组合塌缩为同一 public 名（与 dsh 同纪律，`:67-74`）。
- **回捐约束**：CRM 若自行实现命名派生，必须保证**与上表逐字节一致**，否则跨仓引用 public 名无法对齐。推荐直接移植本函数语义。

---

## 4. 错误语义（语言无关）

| 场景 | 抛出 | 类别 |
|---|---|---|
| server_name 不匹配 `^[A-Za-z0-9_-]{1,32}$` | `ValueError` | 配置错误（构造期 fail-fast） |
| server_name 已被占用 | `ValueError` | 命名空间冲突（连接期 fail-fast） |
| 调用未注册的 public 名 | `ToolNotFound(public_name)` | 调用错误（`bridge.call_tool` 时） |
| transport 内部工具不存在 | transport 实现自行抛（`InMemoryMcpServer` 用 `KeyError`） | 底层错误（直通调用方） |
| 生命周期序违规 | transport 实现自行决定（建议抛） | 违背契约（不得静默伪造） |

**铁律**：
- 连接失败 / 调用失败**不得静默吞掉返回 "成功"**（fail-closed，对齐 R6 失败语义）。
- 调用方按异常类型路由，**禁止按 message 文本字符串匹配**（对齐 R8 错误码纪律）。

---

## 5. 消费方（CRM / Node）回捐验收

CRM 自实现 transport 后，满足以下即确认"协议对齐、可无成本回捐"：

1. **四方法签名与生命周期序**符合 §1 状态机；
2. **命名派生**与 §3 `normalize_mcp_name` 逐字节一致；
3. **错误不静默**：按 §4 铁律抛错而非返回假成功；
4. 用 `@pytest.mark.pg` 无关的**替身 server**（如 `InMemoryMcpServer` 语义等价物）做 E2E：connect → list_tools → call_tool → disconnect 全通。

> 回捐形态：Node transport 实现 + 命名函数等价件 + E2E 测试记录。底座侧复核以本契约为准（§1 状态机 + §3 命名 + §4 铁律），不逐行对拍代码。

---

## 附：契约 ↔ 来源映射

| 元素 | 含义 | 真值来源 | 规格段 |
|---|---|---|---|
| `McpTransport` | transport 抽象协议（四方法） | `mcp/__init__.py:25` | §1 |
| `McpBridge` | transport 编排（接入/调用/释放） | `mcp/__init__.py:77` | §2 |
| `normalize_mcp_name` | public 名派生（截断+哈希） | `mcp/__init__.py:66` | §3 |
| `InMemoryMcpServer` | 测试替身（回捐参考范式） | `mcp/__init__.py:37` | §1/§5 |
| `ToolNotFound` | 未注册 public 名调用错误 | `tools` 层（bridge 引用） | §4 |
