import type { Conversation, ModePreset, Direction } from '../types';
import { NewChatIcon, MoonIcon, SunIcon, GearIcon, PlugIcon, FolderIcon } from './icons';

interface SidebarProps {
  conversations: Conversation[];
  activeId: string;
  onSelect: (id: string) => void;
  onNewChat: () => void;
  mode: ModePreset;
  direction: Direction;
  theme: string;
  onToggleTheme: () => void;
  onOpenPlugins: () => void;
  onOpenSettings: () => void;
}

function relTime(ts?: number): string {
  if (!ts) return '';
  const diff = Date.now() - ts;
  if (diff < 60_000) return '刚刚';
  if (diff < 3_600_000) return Math.floor(diff / 60_000) + ' 分钟';
  if (diff < 86_400_000) return Math.floor(diff / 3_600_000) + ' 小时';
  return Math.floor(diff / 86_400_000) + ' 天';
}

export default function Sidebar({
  conversations, activeId, onSelect, onNewChat, mode, direction,
  theme, onToggleTheme, onOpenPlugins, onOpenSettings,
}: SidebarProps) {
  return (
    <aside className="sb">
      <div className="sb-head">
        <span className="logo">C</span>
        <span className="name">chiyu</span>
        <span className="brand-badge">PORTAL</span>
      </div>

      <button className="sb-new" onClick={onNewChat}>
        <NewChatIcon /> 新会话
      </button>

      <button className="sb-nav" onClick={onOpenPlugins} title="插件注册表 / 原生工具 / 决策脊柱 / 企业控制面">
        <PlugIcon /> 插件
      </button>

      <div className="sb-section">
        工作区
        <span className="spacer" />
        <span className="ws-cur" title="当前方向（从引导进入可改）">
          <FolderIcon size={13} /> {direction.label}
        </span>
      </div>
      <div className="sb-list">
        <div className="sb-ws">
          <span className="ws-dot" />
          {direction.label} · {mode.label}
        </div>
        <div className="sb-group">会话</div>
        {conversations.map((c) => (
          <div
            key={c.id}
            className={'sb-item' + (c.id === activeId ? ' active' : '')}
            onClick={() => onSelect(c.id)}
          >
            <span className="label">{c.title}</span>
            {c.ts && <span className="time">{relTime(c.ts)}</span>}
          </div>
        ))}
      </div>

      <div className="sb-foot">
        <span className="avatar">王</span>
        <span>王川</span>
        <span className="spacer" />
        <button className="icon-btn" onClick={onOpenSettings} title="LLM 设置">
          <GearIcon />
        </button>
        <button className="icon-btn" onClick={onToggleTheme} title="切换主题">
          {theme === 'dark' ? <SunIcon /> : <MoonIcon />}
        </button>
      </div>
    </aside>
  );
}
