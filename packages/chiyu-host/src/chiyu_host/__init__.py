"""chiyu-host —— DSH 前端 + 本平台后端 桌面客户端的桥接层（M0）。

⚠️ **已弃用（DEPRECATED，2026-09-26）**：DSH 协议实现已迁入企业 host
`D:\\system\\chiyu-enterprise\\packages\\enterprise\\src\\enterprise\\host\\dsh_adapter\\`
（`bridge.py` + `methods.py` + `app.py` 的 `/api/<method>` 与 `WS /api/events.mux` 路由），
并复用企业 host 治理中间件（token 认租户、读类直连、写类两阶段 confirm + 写闸 G0–G3）。
本包保留为历史快照/参考实现，**不再维护、不再演进**；新集成一律走 chiyu-enterprise。

桥接形态（实测 DSH apiproxy 契约，非早期 SSE 假设）：
- 单一 RPC 路由器：POST /api/<method>，body=ClientRequest 全形，响应=ServerResponse 全形
- mux 事件流：WebSocket /api/events.mux（DSH 实测为 WebSocket，非 SSE），
  下行帧为 ServerRequest 全形 + MuxFrame payload
- boot manifest：供 T3 thin launcher 注入 window.__DSH_BOOT__

消费 chiyu_kernel 门面，逐字段对齐 DSH apiproxy/*.schema.ts（防假绿）。
"""
from __future__ import annotations

__version__ = "0.1.0"
DEPRECATED = True          # 2026-09-26：已并入 chiyu-enterprise 企业 host（见模块 doc）
SUPERSEDED_BY = "chiyu-enterprise enterprise.host.dsh_adapter"
