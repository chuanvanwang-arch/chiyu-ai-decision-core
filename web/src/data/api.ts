// 后端 API 客户端：把前端 composer 接到 chiyu_kernel 真实内核。
// 后端未运行时（fetch 失败）调用方回退到本地演示数据，保证页面始终可用。

import type { ModePreset, ToolCallData, TraceStep, Level, Workflow, Direction } from '../types';

// ── 平台后端地址（设置向导可写，localStorage 持久化）────────────────────────
// 留空 = 同源默认（开发走 vite /api 代理；生产 dist 由后端同源托管）。
// 填写后所有 /api/* 请求直连该地址（跨源；后端 CORS 已放行）。
export function platformBase(): string {
  return (localStorage.getItem('chiyu_api_base') || '').trim().replace(/\/+$/, '');
}

/** 拼 API 绝对地址：设置向导填了平台地址则直连，否则同源相对路径。 */
export function apiUrl(path: string): string {
  return platformBase() + path;
}

export interface NativeToolInfo {
  name: string;
  description: string;
  high_risk: boolean;
}

export interface Bootstrap {
  modes: ModePreset[];
  nativeTools: NativeToolInfo[];
  /** 向导三卡：后台动态生成（portal 渲染层），缺省时前端回退本地演示枚举 */
  levels?: Level[];
  workflows?: Workflow[];
  directions?: Direction[];
}

export interface ChatTurnResult {
  content: string;
  blocked: boolean;
  toolCalls: ToolCallData[];
  trace: TraceStep[];
  echo?: string;
  /** Phase B：本轮是否由 LLM 生成正文（未配置 key 时 used=false，确定性内核产出） */
  llm?: { used: boolean; model: string; error?: string };
}

export interface LlmStatus {
  available: boolean;
  base: string;
  models: { chat: string; reasoner: string };
  web_search: boolean;
  key_hint: string;
}

export interface ChatPayload {
  text: string;
  mode: string;
  deep_think: boolean;
  web_search: boolean;
  /** 向导选择透传（后端 S1 锚定回显 + 工作流决定意图 + 层级影响建议措辞） */
  direction?: string;
  workflow?: string;
  level?: string;
}

/** 拉取内核真实能力（四种模式 / 原生工具）。失败返回 null ⇒ 演示模式。 */
export async function fetchBootstrap(): Promise<Bootstrap | null> {
  try {
    const r = await fetch(apiUrl('/api/bootstrap'));
    if (!r.ok) return null;
    return (await r.json()) as Bootstrap;
  } catch {
    return null;
  }
}

/** composer 发送：真实调用 chiyu_kernel 原生工具（经由后端 mini agent loop）。 */
export async function sendChat(payload: ChatPayload): Promise<ChatTurnResult> {
  const r = await fetch(apiUrl('/api/chat'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!r.ok) {
    throw new Error('chat 请求失败：HTTP ' + r.status);
  }
  return (await r.json()) as ChatTurnResult;
}

/** 复用 chiyu_portal 渲染层：把当前对话交给 render_conversation 生成真实 HTML。 */
export async function renderConversationInPortal(
  goal: string,
  messages: { role: string; content: string }[],
): Promise<string> {
  const r = await fetch(apiUrl('/api/portal/conversation'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ goal, messages }),
  });
  if (!r.ok) throw new Error('portal 渲染失败：HTTP ' + r.status);
  return await r.text();
}

/** Phase B LLM 可用性（如实展示：key 是否配置、联网搜索是否接通）。 */
export async function fetchLlmStatus(): Promise<LlmStatus | null> {
  try {
    const r = await fetch(apiUrl('/api/llm/status'));
    if (!r.ok) return null;
    return (await r.json()) as LlmStatus;
  } catch {
    return null;
  }
}

// ── LLM 设置（UI 可写，后端持久化到 llm_config.local.json）──────────────────

export interface LlmConfigInfo {
  provider: string;
  baseUrl: string;
  apiKeyMasked: string;
  modelChat: string;
  modelReasoner: string;
  keySource: 'file' | 'env' | 'none';
  available: boolean;
  configFile: string;
}

export interface LlmSaveResult {
  ok: boolean;
  apiKeyMasked: string;
  keySource: string;
  available: boolean;
  configFile: string;
}

export async function fetchLlmConfig(): Promise<LlmConfigInfo | null> {
  try {
    const r = await fetch(apiUrl('/api/llm/config'));
    if (!r.ok) return null;
    return (await r.json()) as LlmConfigInfo;
  } catch {
    return null;
  }
}

export async function saveLlmConfig(cfg: {
  provider: string; baseUrl: string; apiKey: string; modelChat: string; modelReasoner: string;
}): Promise<LlmSaveResult> {
  const r = await fetch(apiUrl('/api/llm/config'), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(cfg),
  });
  if (!r.ok) {
    let detail = 'HTTP ' + r.status;
    try { const j = await r.json(); if (j?.detail) detail = String(j.detail); } catch { /* ignore */ }
    throw new Error('保存 LLM 配置失败：' + detail);
  }
  return (await r.json()) as LlmSaveResult;
}

/** 连通性实测（真实最小请求），成败如实返回。 */
export async function testLlmConfig(): Promise<{ ok: boolean; model?: string; error?: string }> {
  const r = await fetch(apiUrl('/api/llm/test'), { method: 'POST' });
  if (!r.ok) {
    let detail = 'HTTP ' + r.status;
    try { const j = await r.json(); if (j?.detail) detail = String(j.detail); } catch { /* ignore */ }
    return { ok: false, error: detail };
  }
  return (await r.json()) as { ok: boolean; model?: string; error?: string };
}

// ── 平台账号（token 登录，后端真实探测企业 host 校验）────────────────────────

export interface AccountStatus {
  loggedIn: boolean;
  tenantId: string;
  role: string;
  tokenMasked: string;
  /** 平台探测是否通过（平台不可达时为 false 并如实标注，不代表 token 错误） */
  verified: boolean;
  verifiedDetail: string;
  enterpriseBase: string;
  configFile: string;
  probe?: { reachable: boolean; verified: boolean; http: number; detail: string };
}

export async function fetchAccountStatus(): Promise<AccountStatus | null> {
  try {
    const r = await fetch(apiUrl('/api/account/status'));
    if (!r.ok) return null;
    return (await r.json()) as AccountStatus;
  } catch {
    return null;
  }
}

export async function loginAccount(token: string): Promise<AccountStatus> {
  const r = await fetch(apiUrl('/api/account/login'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token }),
  });
  if (!r.ok) {
    let detail = 'HTTP ' + r.status;
    try { const j = await r.json(); if (j?.detail) detail = String(j.detail); } catch { /* ignore */ }
    throw new Error('登录失败：' + detail);
  }
  return (await r.json()) as AccountStatus;
}

export async function logoutAccount(): Promise<void> {
  const r = await fetch(apiUrl('/api/account/logout'), { method: 'POST' });
  if (!r.ok) throw new Error('退出失败：HTTP ' + r.status);
}

// ── 企业控制面桥（chiyu-enterprise host /control/* 只读聚合）────────────────

export interface EnterpriseResult<T = Record<string, unknown>> {
  reachable: boolean;
  data?: T;
  error?: string;
}

/** 经后端代理拉企业控制面只读视图（dashboard/tenants/providers/approvals/…）。 */
export async function fetchEnterpriseControl<T = Record<string, unknown>>(
  name: string,
): Promise<EnterpriseResult<T>> {
  try {
    const r = await fetch(apiUrl('/api/enterprise/control/') + encodeURIComponent(name));
    const j = (await r.json()) as Record<string, unknown>;
    if (r.ok) return { reachable: true, data: j as T };
    return { reachable: false, error: String(j?.error ?? 'HTTP ' + r.status) };
  } catch (e) {
    return { reachable: false, error: e instanceof Error ? e.message : String(e) };
  }
}

/** 导出当前对话：后端用 chiyu_portal.render_conversation 渲染真实 HTML 并下载。 */
export async function exportConversationHtml(
  goal: string,
  messages: { role: string; content: string }[],
): Promise<void> {
  const r = await fetch(apiUrl('/api/export/conversation'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ goal, messages }),
  });
  if (!r.ok) {
    let detail = 'HTTP ' + r.status;
    try {
      const j = await r.json();
      if (j?.detail) detail = String(j.detail);
    } catch { /* ignore */ }
    throw new Error('导出失败：' + detail);
  }
  const blob = await r.blob();
  const cd = r.headers.get('Content-Disposition') || '';
  const m = /filename="([^"]+)"/.exec(cd);
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = m ? m[1] : 'chiyu-conversation.html';
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(a.href);
}

// ── 场景包（ScenarioPack）───────────────────────────────────────────────────

export interface ScenarioPackInfo {
  id: string;
  name: string;
  level: string;
  direction: string;
  mode: string;
  plugins: string[];
  workflow: { steps: { name: string; prompt: string; depends_on: string[] }[] };
  knowledge_needs?: { layer: string; dims: string[] }[];
  locked_by?: string | null;
  selected?: boolean;
}

export interface ScenarioRunStep {
  name: string;
  status: 'done' | 'failed';
  output: string;
}

export interface ScenarioRunResult {
  ok: boolean;
  stopReason: string;
  agentsStarted: number;
  error?: string | null;
  steps: ScenarioRunStep[];
  pack: { id: string; level: string; mode: string };
}

async function postJson<T>(url: string, body: unknown, what: string): Promise<T> {
  const r = await fetch(apiUrl(url), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    let detail = 'HTTP ' + r.status;
    try {
      const j = await r.json();
      if (j?.detail) detail = String(j.detail);
    } catch { /* ignore */ }
    throw new Error(what + '失败：' + detail);
  }
  return (await r.json()) as T;
}

/** 列场景包（含 locked_by / selected 状态）。 */
export async function fetchScenarioPacks(): Promise<ScenarioPackInfo[]> {
  const r = await fetch(apiUrl('/api/scenario/list'));
  if (!r.ok) throw new Error('场景包列表获取失败：HTTP ' + r.status);
  const j = (await r.json()) as { packs: Record<string, unknown>[] };
  // 兼容两种形状：内核(id/name/level) 与平台(pkg/namespace/locked_by)
  return (j.packs ?? []).map((raw) => {
    const p = (raw ?? {}) as Record<string, unknown>;
    const id = String(p.id ?? p.pkg ?? '');
    return {
      ...(raw as unknown as ScenarioPackInfo),
      id,
      name: String(p.name ?? p.pkg ?? id),
      level: String(p.level ?? p.namespace ?? ''),
      mode: String(p.mode ?? ''),
    } as ScenarioPackInfo;
  });
}

/** 向导四元组生成初稿包（双入口之一）。 */
export function generateScenarioPack(payload: {
  direction: string; workflow: string; level: string; mode: string;
}): Promise<{ ok: boolean; id: string }> {
  return postJson('/api/scenario/generate', payload, '场景包生成');
}

/** 选择装载场景包（会话态）。 */
export function selectScenarioPack(id: string): Promise<{ ok: boolean; id: string }> {
  return postJson('/api/scenario/select', { id }, '场景包选择');
}

/** 锁定场景包（写操作，HITL：confirm 必须为 true）。 */
export function lockScenarioPack(id: string, holder: string, confirm: boolean): Promise<{ ok: boolean; id: string; locked_by?: string }> {
  return postJson('/api/scenario/lock', { id, holder, confirm }, '场景包锁定');
}

/** MCP 文件调用真桥路径（write/list/lock）。 */
export function scenarioMcpCall(tool: string, args: Record<string, unknown>): Promise<Record<string, unknown>> {
  return postJson('/api/scenario/mcp-call', { tool, args }, 'MCP 调用');
}

/** 运行场景包：pack → Workflow → WorkflowRunner 真执行，返回每步轨迹。 */
export function runScenarioPack(id: string): Promise<ScenarioRunResult> {
  return postJson('/api/scenario/run', { id }, '场景包运行');
}
