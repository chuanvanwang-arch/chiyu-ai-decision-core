import { useEffect, useState } from 'react';
import type { ModePreset } from '../types';
import { PLUGINS } from '../data/chiyu';
import { fetchEnterpriseControl } from '../data/api';
import { ShieldIcon, SidebarIcon } from './icons';

interface CapabilityPanelProps {
  mode: ModePreset;
  onClose: () => void;
}

interface EntDashboard {
  kpis?: { tenants?: number; decisions24h?: number; redline24h?: number; pendingApprovals?: number };
}
interface EntProviders {
  items?: { id: string; name: string; role: string; status: string }[];
}

/** 企业控制面区块：经后端代理拉 chiyu-enterprise host(/control/*) 只读聚合。 */
function EnterpriseSection() {
  const [dash, setDash] = useState<EntDashboard | null>(null);
  const [providers, setProviders] = useState<EntProviders | null>(null);
  const [state, setState] = useState<'loading' | 'ok' | 'down'>('loading');
  const [err, setErr] = useState('');

  useEffect(() => {
    let alive = true;
    (async () => {
      const d = await fetchEnterpriseControl<EntDashboard>('dashboard');
      if (!alive) return;
      if (!d.reachable) {
        setState('down'); setErr(d.error ?? '不可达');
        return;
      }
      setDash(d.data ?? null);
      const p = await fetchEnterpriseControl<EntProviders>('providers');
      if (!alive) return;
      if (p.reachable) setProviders(p.data ?? null);
      setState('ok');
    })();
    return () => { alive = false; };
  }, []);

  const k = dash?.kpis;
  return (
    <div className="panel-card">
      <h4>企业控制面（chiyu-enterprise）</h4>
      {state === 'loading' && <div className="pdesc">连接中…</div>}
      {state === 'down' && (
        <div className="pdesc">
          ○ 企业 host 不可达（<code>/control/*</code> 代理失败）。启动 <code>enterprise.host.app</code>（:8000）后自动接通。{err && <div style={{ fontSize: 11, marginTop: 2 }}>错误：{err}</div>}
        </div>
      )}
      {state === 'ok' && (
        <>
          <div className="kv"><span>接入租户</span><b>{k?.tenants ?? '—'}</b></div>
          <div className="kv"><span>24h 决策数</span><b>{k?.decisions24h ?? '—'}</b></div>
          <div className="kv"><span>24h 红线拦截</span><b style={{ color: 'var(--red)' }}>{k?.redline24h ?? '—'}</b></div>
          <div className="kv"><span>待人工审批</span><b style={{ color: 'var(--amber)' }}>{k?.pendingApprovals ?? '—'}</b></div>
          {providers?.items?.length ? (
            <div className="pdesc" style={{ marginTop: 4 }}>
              LLM Provider 注册表：{providers.items.map((p) => `${p.name}（${p.role}·${p.status}）`).join('、')}
            </div>
          ) : null}
          <div className="pdesc" style={{ marginTop: 4 }}>
            数据来自企业 host <code>/control/dashboard·providers</code>（只读聚合，经本端 <code>/api/enterprise/control/*</code> 代理，避免跨域）。
          </div>
        </>
      )}
    </div>
  );
}

export default function CapabilityPanel({ mode, onClose }: CapabilityPanelProps) {
  const enabled = new Set(mode.plugins);
  return (
    <aside className="panel">
      <div className="panel-head">
        <span>能力面板</span>
        <span className="spacer" />
        <button className="icon-btn" onClick={onClose} title="关闭"><SidebarIcon /></button>
      </div>
      <div className="panel-body">
        <div className="panel-card">
          <h4><SidebarIcon size={15} /> 工作模式</h4>
          <div className="kv"><span>模式</span><b>{mode.label}</b></div>
          <div className="kv"><span>编排开关</span><b>{mode.id === 'ptc' ? '脚本规划槽位' : '默认'}</b></div>
          <div className="kv"><span>Phase B 后端</span><b style={{ fontSize: 11.5 }}>{mode.phaseBBackend}</b></div>
        </div>

        <div className="panel-card">
          <h4><ShieldIcon size={15} /> 插件注册表</h4>
          {PLUGINS.map((p) => {
            const on = enabled.has(p.id);
            return (
              <div className={'plug' + (on ? '' : ' off')} key={p.id}>
                <span className="pdot" />
                <span>
                  <span className="pname">{p.label}</span>
                  <div className="pdesc">{p.description}</div>
                </span>
              </div>
            );
          })}
        </div>

        <div className="panel-card">
          <h4><ShieldIcon size={15} /> 原生工具（无缝集成桥）</h4>
          <div className="plug"><span className="pdot" style={{ background: 'var(--green)' }} />
            <span><span className="pname">native-context-assemble</span>
              <div className="pdesc">装配 L1–L4 分层上下文</div></span></div>
          <div className="plug"><span className="pdot" style={{ background: 'var(--amber)' }} />
            <span><span className="pname">native-redline-check</span>
              <div className="pdesc">红线命中检查（high_risk）</div></span></div>
          <div className="pdesc" style={{ marginTop: 6, padding: 0 }}>
            high_risk 工具经 <code>redline_guard</code> 硬闸门复核；
            命中冻结红线集即抛 GuardDenied，对话闭环不放行。
          </div>
        </div>

        <div className="panel-card">
          <h4>决策脊柱 · 九尺子</h4>
          <div className="kv"><span>S1 目标锚定</span><b>—</b></div>
          <div className="kv"><span>S2 上下文装配</span><b>L1–L4</b></div>
          <div className="kv"><span>S3 红线校验</span><b style={{ color: 'var(--red)' }}>meta_redline</b></div>
          <div className="kv"><span>S4 九尺子评分</span><b>safe/risk</b></div>
          <div className="kv"><span>S5 决策产出</span><b>建议</b></div>
        </div>

        <EnterpriseSection />
      </div>
    </aside>
  );
}
