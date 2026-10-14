import { useEffect, useRef, useState } from 'react';
import type { ChatMessage, Conversation, ModeId, Direction, Workflow, TraceStep } from '../types';
import { MODE_MAP, LEVEL_MAP, SAMPLE_CONVERSATION, MODES, DIRECTIONS } from '../data/chiyu';
import {
  sendChat, fetchLlmStatus, exportConversationHtml,
  fetchScenarioPacks, generateScenarioPack, selectScenarioPack, lockScenarioPack, runScenarioPack,
  type ScenarioPackInfo,
} from '../data/api';
import Sidebar from './Sidebar';
import CapabilityPanel from './CapabilityPanel';
import ChatView from './ChatView';
import SettingsModal from './SettingsModal';
import { SidebarIcon, DownloadIcon, PanelIcon } from './icons';

interface WorkbenchProps {
  selection: { direction: Direction; workflow: Workflow; mode: ModeId };
  connected: boolean;
  onExit: () => void;
  theme: string;
  onToggleTheme: () => void;
}

const MODELS = ['ChiYu-Decision (auto)', 'deepseek-ai/DeepSeek-V4-Flash', '本地确定性引擎'];

export default function Workbench({ selection, connected, onExit, theme, onToggleTheme }: WorkbenchProps) {
  // 空态下拉可实时切换方向 / 模式（工作流保持引导选择，完整路径走「重新引导」）
  const [dirId, setDirId] = useState(selection.direction.id);
  const [modeId, setModeId] = useState<ModeId>(selection.mode);
  const direction = DIRECTIONS.find((d) => d.id === dirId) ?? selection.direction;
  const mode = MODE_MAP[modeId] ?? MODE_MAP[selection.mode];

  const [conversations, setConversations] = useState<Conversation[]>([SAMPLE_CONVERSATION]);
  const [activeId, setActiveId] = useState(SAMPLE_CONVERSATION.id);
  const [thinking, setThinking] = useState(false);
  const [online, setOnline] = useState(false);
  const [panelOpen, setPanelOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [model, setModel] = useState(MODELS[0]);
  const [llmReady, setLlmReady] = useState<boolean | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [exporting, setExporting] = useState(false);
  const pendingRef = useRef<string | null>(null);

  // ── 场景包（ScenarioPack）状态 ──
  const [packs, setPacks] = useState<ScenarioPackInfo[]>([]);
  const [packsOpen, setPacksOpen] = useState(false);
  const [packId, setPackId] = useState<string | null>(null);
  const [packBusy, setPackBusy] = useState(false);

  const active = conversations.find((c) => c.id === activeId) ?? conversations[0];

  async function refreshPacks() {
    try {
      const list = await fetchScenarioPacks();
      setPacks(list);
      setPackId((cur) => (cur && list.some((p) => p.id === cur)
        ? cur
        : list.find((p) => p.selected)?.id ?? cur));
    } catch { /* 后端未连接：静默，保持演示模式 */ }
  }

  // 挂载即拉包列表（后端未连接时静默回退）
  useEffect(() => { void refreshPacks(); }, []);

  // Phase B LLM 可用性（如实展示：未配置 key 时显示确定性模式）
  useEffect(() => {
    let alive = true;
    fetchLlmStatus().then((s) => { if (alive) setLlmReady(!!s?.available); });
    return () => { alive = false; };
  }, []);

  function updateActive(updater: (msgs: ChatMessage[]) => ChatMessage[]) {
    setConversations((cs) =>
      cs.map((c) => (c.id === activeId ? { ...c, messages: updater(c.messages) } : c)),
    );
  }

  async function handleSend(text: string) {
    const uid = 'u' + Date.now();
    const aid = 'a' + Date.now();
    const userMsg: ChatMessage = { id: uid, role: 'user', content: text };
    const pendingMsg: ChatMessage = { id: aid, role: 'assistant', content: '', pending: true };
    updateActive((ms) => [...ms, userMsg, pendingMsg]);
    pendingRef.current = aid;

    if (!connected) {
      // 后端未连接：回退本地演示响应
      setTimeout(() => {
        if (pendingRef.current !== aid) return;
        pendingRef.current = null;
        updateActive((ms) =>
          ms.map((m) =>
            m.id === aid
              ? {
                  ...m,
                  pending: false,
                  content:
                    '（演示模式 · 后端未连接）已调用本仓原生工具完成上下文装配，并按当前工作模式装配编排。下面是一次 native-context-assemble 调用示例。',
                  toolCalls: [
                    {
                      name: 'native-context-assemble',
                      status: 'ok',
                      args: { needs: [{ layer: 'L1', dims: ['semantics'] }], provided: { L1: [] } },
                      result: { facts: { L1: [] }, missing: [] },
                    },
                  ],
                  trace: [
                    { label: 'S1 目标锚定', status: 'pass' },
                    { label: 'S2 上下文装配', status: 'pass' },
                    { label: 'S3 红线校验', status: 'pass' },
                    { label: 'S4 九尺子评分', status: 'pass' },
                    { label: 'S5 决策产出', status: 'pass' },
                  ],
                }
              : m,
          ),
        );
      }, 850);
      return;
    }

    // 真实内核：POST /api/chat，composer 调用 chiyu_kernel 原生工具
    try {
      const turn = await sendChat({
        text,
        mode: modeId,
        deep_think: thinking,
        web_search: online,
        direction: dirId,
        workflow: selection.workflow.id,
        level: selection.workflow.level,
      });
      if (pendingRef.current !== aid) return;
      pendingRef.current = null;
      updateActive((ms) =>
        ms.map((m) =>
          m.id === aid
            ? {
                ...m,
                pending: false,
                content: turn.content,
                toolCalls: turn.toolCalls,
                trace: turn.trace,
                llmModel: turn.llm?.used ? turn.llm.model : undefined,
              }
            : m,
        ),
      );
    } catch (e) {
      if (pendingRef.current !== aid) return;
      pendingRef.current = null;
      updateActive((ms) =>
        ms.map((m) =>
          m.id === aid
            ? {
                ...m,
                pending: false,
                content: '内核调用失败：' + (e instanceof Error ? e.message : String(e)),
                trace: [{ label: 'S0 出错', note: '后端不可达', status: 'fail' }],
              }
            : m,
        ),
      );
    }
  }

  function handleNewChat() {
    const id = 'c' + Date.now();
    const conv: Conversation = { id, title: '新会话', messages: [], ts: Date.now() };
    setConversations((cs) => [conv, ...cs]);
    setActiveId(id);
  }

  async function handlePackSelect(p: ScenarioPackInfo) {
    setPackBusy(true);
    try {
      await selectScenarioPack(p.id);
      setPackId(p.id);
      setPacksOpen(false);
      updateActive((ms) => [...ms, {
        id: 's' + Date.now(), role: 'assistant',
        content: `已装载场景包「${p.name}」（${LEVEL_MAP[p.level]?.label ?? p.level} · ${MODE_MAP[p.mode as ModeId]?.label ?? p.mode}），工作模式与插件组合将按包声明生效。`,
      }]);
    } catch (e) {
      alert(e instanceof Error ? e.message : String(e));
    } finally {
      setPackBusy(false);
    }
  }

  async function handlePackLock(p: ScenarioPackInfo) {
    // HITL：浏览器原生确认弹窗后方可调用锁定（confirm:true）
    if (!window.confirm(`锁定为写操作，确认把场景包「${p.name}」锁定为默认？锁定后其他人不得改锁。`)) return;
    setPackBusy(true);
    try {
      await lockScenarioPack(p.id, 'web', true);
      await refreshPacks();
      updateActive((ms) => [...ms, {
        id: 's' + Date.now(), role: 'assistant',
        content: `场景包「${p.name}」已锁定（holder=web，confirm=true 已通过 HITL 确认）。`,
      }]);
    } catch (e) {
      alert(e instanceof Error ? e.message : String(e));
    } finally {
      setPackBusy(false);
    }
  }

  async function handlePackRun(p: ScenarioPackInfo) {
    setPackBusy(true);
    try {
      const res = await runScenarioPack(p.id);
      setPacksOpen(false);
      const trace: TraceStep[] = res.steps.map((s) => ({
        label: `step ${s.name}`,
        note: s.output || s.status,
        status: s.status === 'done' ? 'pass' : 'fail',
      }));
      trace.unshift({
        label: '场景包运行',
        note: `${p.name} · ${res.agentsStarted} 个子智能体 · ${res.stopReason}`,
        status: res.ok ? 'pass' : 'fail',
      });
      updateActive((ms) => [...ms, {
        id: 's' + Date.now(), role: 'assistant',
        content: `场景包「${p.name}」运行完成：${res.steps.filter((s) => s.status === 'done').length}/${res.steps.length} 步 done（WorkflowRunner + SubagentPool 真执行，确定性引擎）。`,
        trace,
      }]);
    } catch (e) {
      alert(e instanceof Error ? e.message : String(e));
    } finally {
      setPackBusy(false);
    }
  }

  async function handlePackGenerate() {
    setPackBusy(true);
    try {
      await generateScenarioPack({
        direction: dirId,
        workflow: selection.workflow.id,
        level: selection.workflow.level,
        mode: modeId,
      });
      await refreshPacks();
    } catch (e) {
      alert(e instanceof Error ? e.message : String(e));
    } finally {
      setPackBusy(false);
    }
  }

  /** 导出当前对话：后端复用 chiyu_portal.render_conversation 生成真实 HTML 下载。 */
  async function handleExport() {
    if (!active.messages.length || exporting) return;
    setExporting(true);
    try {
      await exportConversationHtml(`${direction.label} · ${selection.workflow.label}`, active.messages);
    } catch (e) {
      alert(e instanceof Error ? e.message : String(e));
    } finally {
      setExporting(false);
    }
  }

  const curPack = packId ? packs.find((p) => p.id === packId) : undefined;

  return (
    <div className={'wb' + (mode.id === 'minimal' ? ' minimal' : '')}>
      {sidebarOpen && (
        <Sidebar
          conversations={conversations}
          activeId={activeId}
          onSelect={setActiveId}
          onNewChat={handleNewChat}
          mode={mode}
          direction={direction}
          theme={theme}
          onToggleTheme={onToggleTheme}
          onOpenPlugins={() => setPanelOpen(true)}
          onOpenSettings={() => setSettingsOpen(true)}
        />
      )}

      <div className="main">
        {/* 浮动操作（替代原顶栏）：仅保留必要的 icon，页面常空 */}
        <div className="float-actions">
          {!sidebarOpen && (
            <button className="icon-btn" onClick={() => setSidebarOpen(true)} title="侧边栏">
              <SidebarIcon />
            </button>
          )}
          {active.messages.length > 0 && (
            <button className="icon-btn" onClick={handleExport}
              disabled={exporting}
              title="导出当前对话为 HTML（chiyu_portal.render_conversation 真实渲染）">
              <DownloadIcon />
            </button>
          )}
          <button className="icon-btn" onClick={() => setPanelOpen((v) => !v)} title="插件 / 能力面板">
            <PanelIcon />
          </button>
        </div>

        <ChatView
          messages={active.messages}
          thinking={thinking}
          online={online}
          onToggleThink={() => setThinking((v) => !v)}
          onToggleOnline={() => setOnline((v) => !v)}
          onSend={handleSend}
          direction={direction}
          directionItems={DIRECTIONS}
          onPickDirection={setDirId}
          onReOnboard={onExit}
          mode={{ id: mode.id, label: mode.label }}
          modeItems={MODES.map((m) => ({ id: m.id, label: m.label }))}
          onPickMode={setModeId}
          model={model}
          models={MODELS}
          onModelChange={setModel}
          packLabel={curPack?.name ?? null}
          packLocked={!!curPack?.locked_by}
          packs={packs}
          packsOpen={packsOpen}
          packBusy={packBusy}
          onTogglePacks={() => setPacksOpen((v) => !v)}
          onPackSelect={handlePackSelect}
          onPackRun={handlePackRun}
          onPackLock={handlePackLock}
          onPackGenerate={handlePackGenerate}
        />
      </div>

      {panelOpen && <CapabilityPanel mode={mode} onClose={() => setPanelOpen(false)} />}

      {settingsOpen && (
        <SettingsModal
          onClose={() => setSettingsOpen(false)}
          onSaved={() => { fetchLlmStatus().then((s) => setLlmReady(!!s?.available)); }}
        />
      )}
    </div>
  );
}
