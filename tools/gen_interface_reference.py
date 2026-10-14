#!/usr/bin/env python3
"""生成版本联动的接口参考 manifest（JSON）。

把 `v0.1.0-接口参考.md`（人类可读层）的"版本联动"落到机器可校验层：
- 头带版本戳：PACKAGE_VERSION / API_VERSION / CONTRACT_VERSION / __version__ + 生成时间
- 逐门面符号清单 + 形态 + 签名（inspect.signature）+ 源模块
- 每次 wheel 重建后重跑本脚本，diff manifest 即可发现接口漂移

用法：
    python tools/gen_interface_reference.py            # 写 docs/release/interface_reference.manifest.json
    python tools/gen_interface_reference.py --check    # 仅校验，不写文件（CI 用）

注意：本脚本只产机器可读 manifest，不覆盖 `v0.1.0-接口参考.md` 的策展说明列；
      markdown 参考的"说明"列由人工维护，发布时以本 manifest 的计数为权威对账。
"""
import sys, os, json, inspect, argparse, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in [os.path.join(ROOT, 'packages/chiyu-kernel/src'),
          os.path.join(ROOT, 'packages/chiyu-decision/src'),
          os.path.join(ROOT, 'packages/chiyu-portal/src')]:
    sys.path.insert(0, p)

import chiyu_kernel.version as kver
import chiyu_kernel, chiyu_kernel.api as kapi
import chiyu_kernel.contract as kcontract
import chiyu_kernel.approval as kapproval
import chiyu_decision.api as dapi
import chiyu_portal.api as papi
for nm, mod in [('chiyu_kernel', chiyu_kernel), ('chiyu_decision', __import__('chiyu_decision')), ('chiyu_portal', __import__('chiyu_portal'))]:
    assert 'site-packages' not in mod.__file__, f'{nm} resolved to wheel: {mod.__file__}'

FACADES = [
    ('chiyu_kernel.api', kapi),
    ('chiyu_kernel.contract', kcontract),
    ('chiyu_kernel.approval', kapproval),
    ('chiyu_decision.api', dapi),
    ('chiyu_portal.api', papi),
]


def kind_of(o):
    if inspect.isclass(o):
        return 'class'
    if inspect.isfunction(o) or inspect.isbuiltin(o):
        return 'function'
    if callable(o):
        return 'callable'
    return 'value'


def sig_of(o):
    try:
        return str(inspect.signature(o))
    except (ValueError, TypeError):
        return 'n/a'


def build():
    facades = {}
    total = 0
    for fname, mod in FACADES:
        syms = []
        for s in getattr(mod, '__all__', []):
            o = getattr(mod, s, None)
            syms.append({
                'name': s,
                'kind': kind_of(o) if o is not None else 'unknown',
                'signature': sig_of(o) if o is not None else 'n/a',
                'module': getattr(o, '__module__', '?') if o is not None else '?',
            })
        facades[fname] = {'count': len(syms), 'symbols': syms}
        total += len(syms)
    return {
        'generated_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'package_version': kver.PACKAGE_VERSION,
        'api_version': kver.API_VERSION,
        'contract_version': kver.CONTRACT_VERSION,
        'version': kver.__version__,
        'source': 'packages/*/src (pinned, not wheel)',
        'total_listed': total,
        'facades': facades,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true', help='only validate, do not write file')
    args = ap.parse_args()
    data = build()
    out = os.path.join(ROOT, 'docs', 'release', 'interface_reference.manifest.json')
    if args.check:
        print(f'CHECK total_listed={data["total_listed"]} api_version={data["api_version"]}')
        for f, d in data['facades'].items():
            print(f'  {f}: {d["count"]}')
        return
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'WROTE {out} (total_listed={data["total_listed"]}, api_version={data["api_version"]})')


if __name__ == '__main__':
    main()
