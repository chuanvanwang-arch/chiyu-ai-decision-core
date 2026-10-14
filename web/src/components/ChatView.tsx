import { useEffect, useRef, useState } from 'react';
import type { ChatMessage, ToolCallData, TraceStep, ModeId, Direction } from '../types';
import {
  PlusIcon, SendIcon, CopyIcon, ThumbUpIcon, ThumbDownIcon, RefreshIcon,
  BrainIcon, SearchIcon, ChevronDownIcon, FolderIcon, ShieldIcon,
} from './icons';
import type { ScenarioPackInfo } from '../data/api';

interface ChatViewProps {
  messages: ChatMessage[];
  thinking: boolean;
  online: boolean;
  onToggleThink: () => void;
  onToggleOnline: () => void;
  onSend: (text: string) => void;
  /** 空态顶部下拉：工作区（方向） */
  direction: Direction;
  directionItems: Direction[];
  onPickDirection: (id: string) => void;
  onReOnboard: () => void;
  /** 空态顶部下拉：工作模式（可实时切换） */
  mode: { id: ModeId; label: string };
  modeItems: { id: ModeId; label: string }[];
  onPickMode: (id: ModeId) => void;
  /** composer 右侧模型选择 */
  model: string;
  models: string[];
  onModelChange: (m: string) => void;
  /** 场景包（composer 左侧入口） */
  packLabel: string | null;
  packLocked: boolean;
  packs: ScenarioPackInfo[];
  packsOpen: boolean;
  packBusy: boolean;
  onTogglePacks: () => void;
  onPackSelect: (p: ScenarioPackInfo) => void;
  onPackRun: (p: ScenarioPackInfo) => void;
  onPackLock: (p: ScenarioPackInfo) => void;
  onPackGenerate: () => void;
}

function ToolCallCard({ tool }: { tool: ToolCallData }) {
  const cls = tool.status === 'ok' ? 'ok' : tool.status === 'skipped' ? 'skipped' : 'blocked';
  const statusText = tool.status === 'ok' ? '✓ 成功'
    : tool.status === 'skipped' ? '○ 未执行' : '⛔ 已拦截';
  return (
    <div className={'toolcard ' + cls}>
      <div className="tc-head">
        <span className="ico">⚙</span>
        <span>{tool.name}</span>
        <span className="tc-status">{statusText}</span>
      </div>
      <div className="tc-body">
        {Object.entries(tool.args).map(([k, v]) => (
          <div className="tc-row" key={k}>
            <span className="tc-k">{k}</span>
            <span className="tc-v">{JSON.stringify(v)}</span>
          </div>
        ))}
        {tool.result && (
          <div className="tc-row">
            <span className="tc-k">result</span>
            <span className="tc-v">{JSON.stringify(tool.result)}</span>
          </div>
        )}
        {tool.note && (
          <div className="tc-row">
            <span className="tc-k">note</span>
            <span className="tc-v">{tool.note}</span>
          </div>
        )}
      </div>
    </div>
  );
}

function ReasoningTrace({ steps }: { steps: TraceStep[] }) {
  return (
    <div className="trace">
      <h4>决策脊柱 · Decision Spine</h4>
      {steps.map((s, i) => (
        <div className={'trace-step ' + s.status} key={i}>
          <span className="mk">
            {s.status === 'pass' ? '✓' : s.status === 'warn' ? '!' : '✕'}
          </span>
          <span>
            <span className="label">{s.label}</span>
            {s.note && <div className="note">{s.note}</div>}
          </span>
        </div>
      ))}
    </div>
  );
}

function MessageRow({ msg }: { msg: ChatMessage }) {
  return (
    <div className={'msg ' + msg.role}>
      <span className="avatar">{msg.role === 'assistant' ? 'C' : '我'}</span>
      <div className="body">
        {msg.pending ? (
          <div className="bubble"><span className="muted">思考中…</span></div>
        ) : (
          <div className="bubble">
            {msg.content}
            {msg.role === 'assistant' && msg.llmModel && (
              <span className="llm-tag" title="Phase B：本回复由 LLM 基于内核产出生成">
                ◆ {msg.llmModel}
              </span>
            )}
          </div>
        )}
        {msg.toolCalls?.map((t, i) => <ToolCallCard key={i} tool={t} />)}
        {msg.trace && <ReasoningTrace steps={msg.trace} />}
        {!msg.pending && msg.role === 'assistant' && (
          <div className="msg-actions">
            <button className="icon-btn" title="复制"><CopyIcon /></button>
            <button className="icon-btn" title="赞"><ThumbUpIcon /></button>
            <button className="icon-btn" title="踩"><ThumbDownIcon /></button>
            <button className="icon-btn" title="重新生成"><RefreshIcon /></button>
          </div>
        )}
      </div>
    </div>
  );
}

export default function ChatView({
  messages, thinking, online, onToggleThink, onToggleOnline, onSend,
  direction, directionItems, onPickDirection, onReOnboard,
  mode, modeItems, onPickMode,
  model, models, onModelChange,
  packLabel, packLocked, packs, packsOpen, packBusy,
  onTogglePacks, onPackSelect, onPackRun, onPackLock, onPackGenerate,
}: ChatViewProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const taRef = useRef<HTMLTextAreaElement>(null);
  const [draft, setDraft] = useState('');
  const [ddOpen, setDdOpen] = useState<'ws' | 'mode' | 'model' | null>(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  function submit() {
    const t = draft.trim();
    if (!t) return;
    onSend(t);
    setDraft('');
    if (taRef.current) taRef.current.style.height = 'auto';
  }

  function onKey(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  function autoGrow(e: React.FormEvent<HTMLTextAreaElement>) {
    const el = e.currentTarget;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 200) + 'px';
  }

  function toggleDd(which: 'ws' | 'mode' | 'model') {
    setDdOpen((cur) => (cur === which ? null : which));
  }

  const empty = messages.length === 0;

  return (
    <>
      <div className="chat-scroll" ref={scrollRef}>
        <div className="chat-inner">
          {empty ? (
            <div className="greet harness">
              <div className="greet-mark">C</div>
              <h1>让决策有脊柱 <span className="ver">预览版</span></h1>
              <div className="greet-dds">
                <div className="dd-wrap">
                  <button className={'dd' + (ddOpen === 'ws' ? ' open' : '')}
                    onClick={() => toggleDd('ws')}>
                    <FolderIcon size={14} /> {direction.label}
                    <ChevronDownIcon size={13} />
                  </button>
                  {ddOpen === 'ws' && (
                    <div className="dd-menu">
                      {directionItems.map((d) => (
                        <div key={d.id} className={'dd-item' + (d.id === direction.id ? ' sel' : '')}
                          onClick={() => { onPickDirection(d.id); setDdOpen(null); }}>
                          {d.label}
                        </div>
                      ))}
                      <div className="dd-sep" />
                      <div className="dd-item muted" onClick={() => { onReOnboard(); setDdOpen(null); }}>
                        重新选择方向 / 工作流…
                      </div>
                    </div>
                  )}
                </div>
                <div className="dd-wrap">
                  <button className={'dd' + (ddOpen === 'mode' ? ' open' : '')}
                    onClick={() => toggleDd('mode')}>
                    <ShieldIcon size={14} /> {mode.label}
                    <ChevronDownIcon size={13} />
                  </button>
                  {ddOpen === 'mode' && (
                    <div className="dd-menu">
                      {modeItems.map((m) => (
                        <div key={m.id} className={'dd-item' + (m.id === mode.id ? ' sel' : '')}
                          onClick={() => { onPickMode(m.id); setDdOpen(null); }}>
                          {m.label}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ) : (
            messages.map((m) => <MessageRow key={m.id} msg={m} />)
          )}
        </div>
      </div>

      <div className="composer-zone">
        <div className="composer">
          <textarea
            ref={taRef}
            value={draft}
            placeholder="描述你的决策目标 / 调用指令，@ 文件或对话"
            onChange={(e) => { setDraft(e.target.value); autoGrow(e); }}
            onKeyDown={onKey}
            rows={1}
          />
          <div className="composer-row">
            <div className="left">
              <button className="tg" title="附件"><PlusIcon size={15} /></button>
              <button
                className={'tg' + (thinking ? ' on' : '')}
                onClick={onToggleThink}
              >
                <BrainIcon size={15} /> 深度思考
              </button>
              <button
                className={'tg' + (online ? ' on cyan' : '')}
                onClick={onToggleOnline}
              >
                <SearchIcon size={15} /> 联网搜索
              </button>
              <button
                className={'tg' + (packLabel ? ' on' : '')}
                onClick={onTogglePacks}
                title="场景包：选择 / 锁定 / 运行（ScenarioPack，WorkflowRunner 真执行）"
              >
                📦 {packLabel ? packLabel + (packLocked ? ' 🔒' : '') : '场景包'}
              </button>
            </div>
            <div className="right">
              <div className="dd-wrap">
                <button className={'dd slim' + (ddOpen === 'model' ? ' open' : '')}
                  onClick={() => toggleDd('model')} title="决策引擎档位">
                  {model} <ChevronDownIcon size={13} />
                </button>
                {ddOpen === 'model' && (
                  <div className="dd-menu up">
                    {models.map((m) => (
                      <div key={m} className={'dd-item' + (m === model ? ' sel' : '')}
                        onClick={() => { onModelChange(m); setDdOpen(null); }}>
                        {m}
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <button
                className={'send round' + (draft.trim() ? ' accent' : '')}
                onClick={submit}
                disabled={!draft.trim()}
                title="发送"
              >
                <SendIcon size={16} />
              </button>
            </div>
          </div>

          {packsOpen && (
            <div className="pack-menu">
              <div className="pack-hint">
                场景包 = 模式 + 插件 + 声明式工作流 DAG（MCP / 向导双入口生成）
              </div>
              {packs.length === 0 && (
                <div className="pack-hint">暂无包——可从当前向导四元组生成初稿。</div>
              )}
              {packs.map((p) => (
                <div key={p.id} className="dd-item pack-row">
                  <span className="plabel" onClick={() => onPackSelect(p)}>
                    {p.name}
                  </span>
                  <span className="spacer" />
                  <button className="btn ghost" disabled={packBusy}
                    onClick={() => onPackRun(p)}>运行</button>
                  <button className="btn ghost" disabled={packBusy || !!p.locked_by}
                    title={p.locked_by ? `已由 ${p.locked_by} 锁定` : '锁定为默认（写操作，需确认）'}
                    onClick={() => onPackLock(p)}>锁定</button>
                </div>
              ))}
              <button className="btn ghost pack-gen" disabled={packBusy}
                onClick={onPackGenerate}>
                从当前向导生成初稿包
              </button>
            </div>
          )}
        </div>
        <div className="composer-hint">
          内容由 AI 生成，请核对决策建议；红线命中将被硬闸门拦截。
        </div>
      </div>
    </>
  );
}
