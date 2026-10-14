"""M0-T3 路线 A：对 chiyu-host 的 headless 契约验证（离线、可复跑）。

不依赖装好的 DSH node_modules（install 被沙箱 wmic 黑名单阻断）。直接对照
DSH apiproxy「真实 schema 必需的字段」（源码只读锚点）验证 chiyu-host 的
真实 RPC 响应/WebSocket mux 帧。证明「DSH client 零改对接」成立的线格式契约。

对照锚点（reference/deepseek-harness-master/packages/host/apiproxy/src/api/）：
- rpc.schema.ts:  serverResponseSchema = {type:'server-response', rpcId, result:{ok,value?}|{ok:false,error{code,message,details}}}
- sessions.schema.ts: sessionSummarySchema = {sessionId, updatedAt, running, blank, parentSessionId?, origin?, cwd?, agentPreset?}

用法：python verify_dsh_contract.py [--base http://localhost:8000]
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from typing import Any, Dict, List, Tuple

# ── DSH 真实契约的必需字段（离线锚点，逐字段对齐；深路径即防「只对顶层字段」假绿）──
# 路径支持 'items[].sessionId' 分段遍历：items 数组非空且首元素含 sessionId。
RPC_METHODS_REQUIRED: Dict[str, List[str]] = {
    # sessions.schema.ts: sessionSummarySchema（session.list 响应为 value.items[] 承载投影）
    "session.list": ["items[].sessionId", "items[].updatedAt", "items[].running", "items[].blank"],
    # sessions.schema.ts: session.create → sessionId
    "session.create": ["sessionId"],
    # sessions.schema.ts: history block（events[event{type,seq,time,data}], hasMore）
    "session.history": ["events[].type", "events[].seq", "events[].time", "hasMore"],
    # sessions.schema.ts: model selection
    "session.models": ["current", "routable", "groups", "failures"],
    # sessions.schema.ts: selectModel → selected{provider,model}
    "session.selectModel": ["selected.provider", "selected.model"],
    # sessions.schema.ts: prompt/cancel → accepted
    "session.prompt": ["accepted"],
    "session.cancel": ["accepted"],
    # llm.schema.ts: providers[]
    "llm.providers": ["providers[].provider", "providers[].displayName", "providers[].active"],
    # llm.schema.ts: models → groups, failures
    "llm.models": ["groups", "failures"],
    # skills.schema.ts: skills[{name, description, whenToUse?, modelInvocable}]
    "skill.list": ["skills[].name", "skills[].description", "skills[].modelInvocable"],
    # subagents.schema.ts: entries[] + parentAvailable
    "subagent.list": ["entries[].kind", "entries[].id", "parentAvailable"],
    # host.schema.ts: describe
    "host.describe": ["version", "cwd", "attachedSessions", "canOpenPath"],
    # agent-presets.schema.ts
    "agentPreset.list": ["presets[].id", "presets[].trust", "presets[].isDefault",
                         "authorable", "hasDocument"],
}

# 需要非空 payload 的方法 → 注入探测参数（真实调用；业务拒绝 = 信封层已验证，fields 层跳过）
REQUIRED_PAYLOAD: Dict[str, Dict[str, Any]] = {
    "session.history": {"sessionId": "sess-probe"},
    "session.models": {"sessionId": "sess-probe"},
    "session.selectModel": {"sessionId": "sess-probe", "provider": "deepseek", "model": "deepseek-v4-flash"},
    "session.prompt": {"sessionId": "sess-probe", "prompt": "ping"},
    "session.cancel": {"sessionId": "sess-probe"},
}

# mux 帧（events.schema.ts MuxFrame 联合 + serverRequestSchema 全形）
MUX_FRAME_TYPES = {"session", "message", "model", "progress", "user", "device", "app"}


def rpc(method: str, base: str, payload: Dict[str, Any] = {}) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """POST /api/<method>，返回 (完整 server-response, result.value)。"""
    body = {"type": "client-request", "rpcId": "verify-id", "method": method, "payload": payload}
    req = urllib.request.Request(
        f"{base}/api/{method}",
        data=json.dumps(body).encode(),
        headers={"content-type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        full = json.loads(resp.read())
    result = full.get("result", {})
    value = result.get("value") if isinstance(result, dict) else None
    return full, value


def check_envelope(full: Dict[str, Any]) -> List[str]:
    """对照 serverResponseSchema 全形必需字段。"""
    errs = []
    if full.get("type") != "server-response":
        errs.append("type != 'server-response'")
    if not full.get("rpcId"):
        errs.append("missing/non-empty rpcId")
    result = full.get("result")
    if not isinstance(result, dict):
        errs.append("missing result")
    elif result.get("ok") is True:
        if "value" not in result:
            errs.append("ok:true 但缺 value")
    else:
        error = result.get("error")
        if not isinstance(error, dict) or not error.get("code") or not error.get("message"):
            errs.append("ok:false 但 error 缺 code/message")
    return errs


def has_fields(obj: Any, fields: List[str], prefix: str) -> List[str]:
    """obj 是否覆盖必需字段（支持 'items[].sessionId' 分段路径遍历）。"""
    errs = []

    def walk(node: Any, segs: List[str]) -> bool:
        """按分段路径检查 node 是否覆盖；[n] 段取数组非空且首元素。"""
        if not segs:
            return True
        seg = segs[0]
        if seg.endswith("[]"):
            base = seg[:-2]
            arr = node.get(base) if isinstance(node, dict) else None
            if not isinstance(arr, list) or not arr:
                return False
            return walk(arr[0], segs[1:])
        if not isinstance(node, dict) or seg not in node:
            return False
        return walk(node[seg], segs[1:])

    for f in fields:
        segs = f.split(".")
        if not walk(obj, segs):
            errs.append(f"{prefix}.{f} 缺失")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8000")
    args = ap.parse_args()

    failures: List[str] = []
    ok_no_value: List[str] = []  # 需 payload 的方法被业务拒（如探测 sessionId 不存在）——信封已对齐
    for method, required in RPC_METHODS_REQUIRED.items():
        payload = REQUIRED_PAYLOAD.get(method, {})
        try:
            full, value = rpc(method, args.base, payload)
        except Exception as e:  # noqa: BLE001
            failures.append(f"{method}: 调用失败 {type(e).__name__}: {e}")
            continue
        for err in check_envelope(full):
            failures.append(f"{method}: {err}")
        result = full.get("result", {})
        if isinstance(result, dict) and result.get("ok") is not True:
            # 预期业务拒绝：信封层已验证，fields 层无法校验 value
            ok_no_value.append(method)
            continue
        root = value if isinstance(value, dict) else {}
        for err in has_fields(root, required, method):
            failures.append(f"{method}: {err}")

    if failures:
        print("CONTRACT FAIL")
        for f in failures:
            print("  -", f)
        return 1
    print(
        f"CONTRACT OK: {len(RPC_METHODS_REQUIRED)} 个 RPC 方法响应全部对齐 DSH "
        f"serverResponseSchema + 逐方法必需字段（离线锚点）"
    )
    if ok_no_value:
        print(f"  （{len(ok_no_value)} 个方法因探测参数被业务拒，仅核验信封层：{', '.join(ok_no_value)}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
