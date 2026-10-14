"""chiyu portal render —— NL → 受控 Schema → HTML（零 Web 服务，落盘即可看）。

链路：guard_nl_input（注入护栏）→ parse_nl_to_schema（绝不直出 HTML）
     → render_page（唯一渲染出口，非法 Schema 字段级拒绝）。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List

from chiyu_kernel.contract.particle import CORE_ROLES, ParticleTypeSet
from chiyu_portal.api import guard_nl_input, parse_nl_to_schema, render_page, render_onboarding
from ._plugins import resolve


def _parse_entity_map(raw: str | None) -> Dict[str, str]:
    """解析 `--entity-map 客户=entity,订单=entity`（NL 实体词 → 粒子类型）。

    ⛔ 映射值由**调用方注入** —— 内核零领域字面量，CLI 不得内置任何业务实体词。
    """
    mapping: Dict[str, str] = {}
    if not raw:
        return mapping
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        if "=" not in item:
            raise ValueError(f"实体映射项须形如 实体词=粒子类型：{item!r}")
        token, _, ptype = item.partition("=")
        mapping[token.strip()] = ptype.strip()
    return mapping


def _particle_set(raw: str | None, entity_map: Dict[str, str]) -> ParticleTypeSet:
    """默认核心角色 + `--particle-types` + 实体映射值（后者否则 Schema 校验会拒）。"""
    extra: List[str] = []
    if raw:
        extra += [x.strip() for x in raw.split(",") if x.strip()]
    extra += [p for p in entity_map.values() if p]
    # ⚠ 必须对 CORE_ROLES + extra 整体去重：映射值可能与核心角色重名（如 entity）
    names: tuple = tuple(dict.fromkeys((*CORE_ROLES, *extra)))
    return ParticleTypeSet(names=names)


def handler(args: argparse.Namespace) -> int:
    guard = guard_nl_input(args.nl)
    if not guard.ok:
        print(f"[护栏拒绝] {guard.reason}", file=sys.stderr)   # ⚠ 字段名是 reason（单数）
        return 2

    mode, enabled, disabled, mwarn = resolve(args.mode)
    # 极简模式隐藏门户导航：强制 portal=False，仅产出裸页面
    portal_on = bool(mode.orchestration.get("portal", True))
    if mwarn:
        for w in mwarn:
            print(f"[模式警告] {w}", file=sys.stderr)

    try:
        entity_map = _parse_entity_map(args.entity_map)
        particle_types = _particle_set(args.particle_types, entity_map)
    except ValueError as exc:
        print(f"[参数非法] {exc}", file=sys.stderr)
        return 2

    parsed = parse_nl_to_schema(args.nl, entity_map=entity_map, title=args.title)
    print(f"schema_type   : {parsed.schema.get('type')}")
    print(f"confidence    : {parsed.confidence}")
    print(f"需澄清        : {parsed.needs_clarification}")
    if parsed.notes:
        print(f"notes         : {'; '.join(parsed.notes)}")
    print(f"工作模式      : {mode.id}（portal导航={'开' if portal_on else '关'}；"
          f"启用插件：{', '.join(enabled) or '无'}）")

    result = render_page(parsed.schema, particle_types=particle_types)
    if not result.ok:
        print("[渲染拒绝] 非法 Schema，字段级错误：", file=sys.stderr)
        for err in result.errors:
            print(f"  - {err}", file=sys.stderr)
        return 2

    if args.out:
        path = Path(args.out)
        if path.parent != Path(""):
            path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(result.html, encoding="utf-8")
        print(f"已写出        : {path.resolve()}  ({len(result.html)} 字节)")
    else:
        print(result.html)
    return 0


def _onboarding_handler(args: argparse.Namespace) -> int:
    """生成引导式导航页（选方向→选工作流→选工作模式→进入工作台）。"""
    result = render_onboarding()
    if not result.ok:
        print("[引导式导航生成失败]", file=sys.stderr)
        for err in result.errors:
            print(f"  - {err}", file=sys.stderr)
        return 2
    if args.out:
        path = Path(args.out)
        if path.parent != Path(""):
            path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(result.html, encoding="utf-8")
        print(f"已写出引导式导航：{path.resolve()}  ({len(result.html)} 字节)")
    else:
        print(result.html)
    return 0


def register(sub: Any) -> None:
    p = sub.add_parser("portal", help="免代码门户")
    sub2 = p.add_subparsers(dest="portal_cmd", required=True)
    r = sub2.add_parser("render", help="NL → HTML")
    r.add_argument("--nl", required=True, help="页面自然语言描述")
    r.add_argument("--out", default=None, help="输出 HTML 路径；缺省打印到 stdout")
    r.add_argument("--title", default=None, help="页面标题")
    r.add_argument("--particle-types", default=None,
                   help=f"追加粒子类型（逗号分隔）；默认仅核心角色 {','.join(CORE_ROLES)}")
    r.add_argument("--entity-map", default=None,
                   help="NL 实体词→粒子类型，如 客户=entity（消费方注入，内核不内置）")
    r.add_argument("--mode", default=None,
                   help="工作模式：standard/ptc/minimal/creative（minimal 关门户导航）")
    r.set_defaults(handler=handler)
    o = sub2.add_parser("onboarding", help="生成引导式导航页（选工作模式）")
    o.add_argument("--out", default=None, help="输出 HTML 路径；缺省打印到 stdout")
    o.set_defaults(handler=_onboarding_handler)
