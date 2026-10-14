// 类型定义：对齐 chiyu_kernel.plugins / chiyu_portal 的领域概念（演示用，零领域字面量）。

export type ModeId = 'standard' | 'ptc' | 'minimal' | 'creative';

export interface ModePreset {
  id: ModeId;
  label: string;
  description: string;
  plugins: string[];      // 启用插件 id 列表
  phaseBBackend: string;  // Phase B 后端（LLM 引擎）
  default?: boolean;
  accent: 'green' | 'amber' | 'cyan' | 'violet';
}

export interface PluginSpec {
  id: string;
  label: string;
  description: string;
}

export interface Direction {
  id: string;
  label: string;
  hint: string;
}

/**
 * 场景三级分类（解法分层）：边界按「AI 替几个岗位、替了几次」划分，
 * 不按系统数量/链路长短划分。中性通用维度，零领域字面量；
 * 消费方可经 TenantProfile / bootstrap 注入自己的层级画像。
 */
export type LevelId = 'single' | 'flow' | 'end2end';

export interface Level {
  id: LevelId;
  label: string;
  /** 判断标准（一句话） */
  criteria: string;
  /** 匹配解法形态 */
  solution: string;
  /** 层级 → 工作模式联动推荐（后台下发优先，本地枚举兜底） */
  recommended_modes?: ModeId[];
}

export interface Workflow {
  id: string;
  label: string;
  hint: string;
  /** 归属层级：决定第 3 步的工作模式联动推荐 */
  level: LevelId;
}

export type ToolStatus = 'ok' | 'blocked' | 'skipped';

export interface ToolCallData {
  name: string;
  args: Record<string, unknown>;
  status: ToolStatus;
  result?: Record<string, unknown>;
  note?: string;
}

export type TraceStatus = 'pass' | 'warn' | 'fail';

export interface TraceStep {
  label: string;
  note?: string;
  status: TraceStatus;
}

export type Role = 'user' | 'assistant';

export interface ChatMessage {
  id: string;
  role: Role;
  content: string;
  toolCalls?: ToolCallData[];
  trace?: TraceStep[];
  pending?: boolean;
  /** Phase B：本条回复由该 LLM 模型生成（未启用时为空 → 确定性内核产出） */
  llmModel?: string;
}

export interface Conversation {
  id: string;
  title: string;
  messages: ChatMessage[];
  /** 创建时间戳（用于会话列表相对时间展示，Harness 风格） */
  ts?: number;
}
