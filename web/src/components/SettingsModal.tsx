import { useEffect, useState } from 'react';
import {
  fetchLlmConfig, saveLlmConfig, testLlmConfig,
  fetchAccountStatus, loginAccount, logoutAccount, platformBase,
  type LlmConfigInfo, type AccountStatus,
} from '../data/api';

type SettingsTab = 'account' | 'general' | 'models' | 'plugins' | 'agents';

interface SettingsModalProps {
  onClose: () => void;
  /** 保存成功后通知父组件刷新 LLM 状态 pill。 */
  onSaved: () => void;
  theme?: string;
  onToggleTheme?: () => void;
}

const TABS: { id: SettingsTab; label: string; icon: string; ready: boolean }[] = [
  { id: 'account', label: '账号', icon: '👤', ready: true },
  { id: 'general', label: '通用设置', icon: '⚙️', ready: true },
  { id: 'models', label: '模型', icon: '🧠', ready: true },
  { id: 'plugins', label: '内置插件', icon: '🧩', ready: false },
  { id: 'agents', label: 'Agent 预设', icon: '🤖', ready: false },
];

/** 设置弹窗：左侧导航（账号 / 通用设置 / 模型 …）+ 右侧面板。 */
export default function SettingsModal({ onClose, onSaved, theme, onToggleTheme }: SettingsModalProps) {
  const [tab, setTab] = useState<SettingsTab>('account');
  const [configPaths, setConfigPaths] = useState<string[]>([]);
  const [showPaths, setShowPaths] = useState(false);

  useEffect(() => {
    Promise.all([fetchAccountStatus(), fetchLlmConfig()]).then(([a, l]) => {
      const paths: string[] = [];
      if (a?.configFile) paths.push(`账号：${a.configFile}`);
      if (l?.configFile) paths.push(`LLM：${l.configFile}`);
      setConfigPaths(paths);
    });
  }, []);

  return (
    <div className="modal-mask" onClick={onClose}>
      <div className="modal settings-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3>设置</h3>
          <div className="settings-head-actions">
            {configPaths.length > 0 && (
              <button className="btn ghost sm" onClick={() => setShowPaths((v) => !v)}>
                打开配置文件
              </button>
            )}
            <button className="icon-btn" onClick={onClose} title="关闭">✕</button>
          </div>
        </div>
        {showPaths && (
          <div className="settings-paths">
            {configPaths.map((p) => <div key={p} className="settings-path">{p}</div>)}
          </div>
        )}

        <div className="settings-layout">
          <aside className="settings-nav">
            {TABS.map((t) => (
              <button
                key={t.id}
                className={'settings-nav-item' + (tab === t.id ? ' active' : '') + (t.ready ? '' : ' soon')}
                onClick={() => t.ready && setTab(t.id)}
                title={t.ready ? t.label : `${t.label}（即将接入）`}
              >
                <span className="settings-nav-icon">{t.icon}</span>
                <span>{t.label}</span>
              </button>
            ))}
          </aside>

          <section className="settings-panel">
            {tab === 'account' && <AccountPanel />}
            {tab === 'general' && <GeneralPanel theme={theme} onToggleTheme={onToggleTheme} />}
            {tab === 'models' && <ModelsPanel onSaved={onSaved} />}
            {(tab === 'plugins' || tab === 'agents') && (
              <div className="settings-placeholder">
                <div className="settings-placeholder-icon">{tab === 'plugins' ? '🧩' : '🤖'}</div>
                <b>{tab === 'plugins' ? '内置插件' : 'Agent 预设'}</b>
                <p className="muted">该分区即将接入，当前请使用内核自带的原生工具与四种工作模式。</p>
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}

// ── 账号面板：平台 token 登录（真实探测企业 host 校验）+ 用户名密码占位 ──────
function AccountPanel() {
  const [status, setStatus] = useState<AccountStatus | null>(null);
  const [token, setToken] = useState('');
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const refresh = () => fetchAccountStatus().then(setStatus);
  useEffect(() => { refresh(); }, []);

  async function handleLogin() {
    setBusy(true); setMsg(null);
    try {
      const st = await loginAccount(token);
      setStatus(st);
      setToken('');
      const p = st.probe;
      if (p?.verified) {
        setMsg({ ok: true, text: `已登录并经平台验证：租户 ${st.tenantId}${st.role ? ` · 角色 ${st.role}` : ''}` });
      } else if (p && !p.reachable) {
        setMsg({ ok: false, text: `已保存 token，但平台不可达（${st.enterpriseBase}），未能验证` });
      } else {
        setMsg({ ok: false, text: p?.detail || '平台未通过该 token' });
      }
    } catch (e) {
      setMsg({ ok: false, text: e instanceof Error ? e.message : String(e) });
    } finally { setBusy(false); }
  }

  async function handleLogout() {
    setBusy(true); setMsg(null);
    try {
      await logoutAccount();
      await refresh();
      setMsg({ ok: true, text: '已退出登录' });
    } catch (e) {
      setMsg({ ok: false, text: e instanceof Error ? e.message : String(e) });
    } finally { setBusy(false); }
  }

  return (
    <div className="settings-section">
      <h4 className="settings-title">平台账号</h4>
      <p className="muted settings-desc">
        登录后客户端与平台账号（租户 + 角色）绑定，后续平台请求自动携带该身份。
        token 形如 <code>t-&lt;租户&gt;-&lt;角色&gt;-&lt;id&gt;</code>，由平台侧签发。
      </p>

      {status?.loggedIn ? (
        <div className="account-card">
          <div className="account-card-head">
            <span className="account-avatar">{(status.tenantId || '?').slice(0, 1).toUpperCase()}</span>
            <div className="account-id">
              <b>{status.tenantId}</b>
              <span className="muted">{status.role ? `角色 ${status.role}` : '未含角色段'} · {status.tokenMasked}</span>
            </div>
            <span className={'pill ' + (status.verified ? '' : 'amber')}>
              {status.verified ? '已验证' : '未验证'}
            </span>
          </div>
          {!status.verified && status.verifiedDetail && (
            <div className="account-warn">{status.verifiedDetail}</div>
          )}
          <div className="account-card-foot">
            <span className="muted" style={{ fontSize: 11 }}>平台：{status.enterpriseBase}</span>
            <button className="btn ghost sm" disabled={busy} onClick={handleLogout}>退出登录</button>
          </div>
        </div>
      ) : (
        <div className="account-login">
          <label className="set-field">
            <span>平台 Token</span>
            <input
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="t-<租户>-<角色>-<id>"
              spellCheck={false}
              autoComplete="off"
              disabled={busy}
            />
          </label>
          <div className="account-login-actions">
            <span className={msg ? (msg.ok ? 'ok-text' : 'err-text') : ''}>{msg?.text}</span>
            <button className="btn primary sm" disabled={busy || !token.trim()} onClick={handleLogin}>
              {busy ? '验证中…' : '登录'}
            </button>
          </div>
        </div>
      )}

      <div className="account-divider" />
      <h4 className="settings-title">用户名 / 密码登录</h4>
      <div className="account-password-placeholder">
        <div className="set-row">
          <label className="set-field">
            <span>用户名</span>
            <input placeholder="即将开放" disabled />
          </label>
          <label className="set-field">
            <span>密码</span>
            <input type="password" placeholder="即将开放" disabled />
          </label>
        </div>
        <div className="muted" style={{ fontSize: 11, lineHeight: 1.6 }}>
          平台当前账号体系为 token 制；用户名/密码登录将在平台侧鉴权模块就绪后开放（界面已预留）。
        </div>
      </div>
    </div>
  );
}

// ── 通用设置：主题 + 平台后端地址（真实探测 /api/health，成败如实）───────────
function GeneralPanel({ theme, onToggleTheme }: { theme?: string; onToggleTheme?: () => void }) {
  const [apiBase, setApiBase] = useState(() => platformBase());
  const [apiBaseMsg, setApiBaseMsg] = useState('');

  /** 平台后端地址：写 localStorage 持久化；随后真实探测 /api/health，成败如实。 */
  async function handleApiBaseSave() {
    const v = apiBase.trim().replace(/\/+$/, '');
    if (v) localStorage.setItem('chiyu_api_base', v);
    else localStorage.removeItem('chiyu_api_base');
    setApiBase(v);
    try {
      const r = await fetch((v || '') + '/api/health');
      const j = await r.json().catch(() => null);
      setApiBaseMsg(r.ok && j?.status === 'ok'
        ? '已保存并接通 ✓'
        : `已保存，但探测失败：HTTP ${r.status}`);
    } catch (e) {
      setApiBaseMsg(`已保存，但当前不可达：${e instanceof Error ? e.message : String(e)}`);
    }
  }

  return (
    <div className="settings-section">
      <h4 className="settings-title">外观</h4>
      <div className="settings-general-row">
        <span>主题</span>
        {onToggleTheme ? (
          <button className="btn ghost sm" onClick={onToggleTheme}>
            {theme === 'dark' ? '🌙 深色（点击切换为浅色）' : '☀️ 浅色（点击切换为深色）'}
          </button>
        ) : (
          <span className="muted">{theme === 'dark' ? '深色' : '浅色'}</span>
        )}
      </div>

      <div className="account-divider" />
      <h4 className="settings-title">平台后端</h4>
      <label className="set-field">
        <span>API 地址（留空 = 同源 /api 代理；填写后所有 /api/* 直连该地址）</span>
        <input
          value={apiBase}
          onChange={(e) => { setApiBase(e.target.value); setApiBaseMsg(''); }}
          placeholder="http://127.0.0.1:8013"
          spellCheck={false}
        />
      </label>
      <div className="account-login-actions">
        {apiBaseMsg && (
          <span className={apiBaseMsg.includes('✓') ? 'ok-text' : 'err-text'} style={{ fontSize: 11.5 }}>
            {apiBaseMsg}
          </span>
        )}
        <button className="btn sm" onClick={handleApiBaseSave}>应用平台地址</button>
      </div>
      <div className="muted" style={{ fontSize: 11 }}>
        保存于本机（localStorage）并持久生效；应用后真实探测 /api/health，不假绿。
      </div>
    </div>
  );
}

// ── 模型面板：原 LLM 设置整体迁入 ───────────────────────────────────────────
function ModelsPanel({ onSaved }: { onSaved: () => void }) {
  const [info, setInfo] = useState<LlmConfigInfo | null>(null);
  const [baseUrl, setBaseUrl] = useState('https://api.deepseek.com');
  const [apiKey, setApiKey] = useState('');
  const [modelChat, setModelChat] = useState('deepseek-chat');
  const [modelReasoner, setModelReasoner] = useState('deepseek-reasoner');
  const [busy, setBusy] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; text: string } | null>(null);
  const [saveMsg, setSaveMsg] = useState('');

  useEffect(() => {
    fetchLlmConfig().then((c) => {
      if (!c) { setSaveMsg('后端不可达，无法读取当前配置'); return; }
      setInfo(c);
      setBaseUrl(c.baseUrl);
      setModelChat(c.modelChat);
      setModelReasoner(c.modelReasoner);
    });
  }, []);

  async function handleSave() {
    setBusy(true); setSaveMsg(''); setTestResult(null);
    try {
      const r = await saveLlmConfig({
        provider: 'deepseek', baseUrl, apiKey, modelChat, modelReasoner,
      });
      setSaveMsg(`已保存（key ${r.apiKeyMasked}，来源 ${r.keySource}）`);
      setApiKey('');
      onSaved();
      const c = await fetchLlmConfig();
      if (c) setInfo(c);
    } catch (e) {
      setSaveMsg(e instanceof Error ? e.message : String(e));
    } finally { setBusy(false); }
  }

  async function handleTest() {
    setBusy(true); setTestResult(null);
    try {
      const r = await testLlmConfig();
      setTestResult(r.ok
        ? { ok: true, text: `连通 ✓（${r.model}）` }
        : { ok: false, text: '失败：' + (r.error ?? '未知错误') });
    } finally { setBusy(false); }
  }

  return (
    <div className="settings-section">
      <h4 className="settings-title">模型</h4>
      <p className="muted settings-desc">填入各提供商的 API 密钥即可使用其模型。</p>

      <div className="model-provider-card">
        <div className="model-provider-head">
          <b>DeepSeek</b>
          <span className="muted" style={{ fontSize: 12 }}>deepseek-official</span>
          <span className={'pill ' + (info?.available ? '' : 'gray')}>
            {info?.available ? `已配置（${info.apiKeyMasked}）` : '未配置'}
          </span>
        </div>

        <label className="set-field">
          <span>API 密钥{info?.keySource === 'env' ? '（留空 = 继续用环境变量）' : '（留空 = 不改动已保存值）'}</span>
          <input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)}
            placeholder="sk-…" spellCheck={false} autoComplete="off" />
        </label>

        <label className="set-field">
          <span>Base URL（OpenAI 兼容端点）</span>
          <input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)}
            placeholder="https://api.deepseek.com" spellCheck={false} />
        </label>

        <div className="set-row">
          <label className="set-field">
            <span>普通档模型（composer 默认）</span>
            <input value={modelChat} onChange={(e) => setModelChat(e.target.value)} spellCheck={false} />
          </label>
          <label className="set-field">
            <span>深度思考档（R1 toggle）</span>
            <input value={modelReasoner} onChange={(e) => setModelReasoner(e.target.value)} spellCheck={false} />
          </label>
        </div>

        <div className="account-login-actions">
          {saveMsg && <span className={saveMsg.startsWith('已保存') ? 'ok-text' : 'err-text'}>{saveMsg}</span>}
          {testResult && <span className={testResult.ok ? 'ok-text' : 'err-text'}>{testResult.text}</span>}
          <button className="btn ghost sm" disabled={busy} onClick={handleTest}>测试连接</button>
          <button className="btn primary sm" disabled={busy} onClick={handleSave}>保存</button>
        </div>
      </div>

      <div className="muted" style={{ fontSize: 11, lineHeight: 1.6 }}>
        说明：key 只存本机配置文件，前端永不回显明文；保存后 composer 的「深度思考」即走该端点。
        联网搜索当前未接通（DeepSeek API 无检索参数），界面会如实标注。
      </div>
    </div>
  );
}
