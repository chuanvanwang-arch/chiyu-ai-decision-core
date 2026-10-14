import type {
  ModePreset, PluginSpec, Direction, Workflow, Conversation, Level, LevelId, ModeId,
} from '../types';

/* ─────────────────────────────────────────────────────────────
   插件注册表（镜像 chiyu_kernel.plugins.BUILTIN_PLUGINS）
   ⛔ 仅声明能力槽位，零领域字面量
   ───────────────────────────────────────────────────────────── */
export const PLUGINS: PluginSpec[] = [
  { id: 'terminal', label: 'Terminal', description: '受限命令壳与对话环' },
  { id: 'loop', label: 'Loop', description: '循环 / 批量编排' },
  { id: 'subagent', label: 'SubAgent', description: '子智能体派发' },
  { id: 'web_search', label: 'Web Search', description: '联网检索' },
  { id: 'team', label: 'Team', description: '多智能体协作' },
  { id: 'voice', label: 'Voice', description: '语音输入输出' },
];

export const PLUGIN_MAP: Record<string, PluginSpec> = Object.fromEntries(
  PLUGINS.map((p) => [p.id, p]),
);

/* ─────────────────────────────────────────────────────────────
   四种工作模式（镜像 chiyu_kernel.plugins.MODE_PRESETS）
   ───────────────────────────────────────────────────────────── */
export const MODES: ModePreset[] = [
  {
    id: 'standard',
    label: '标准模式',
    description: '全能力默认编排：6 插件全开 + 确定性决策脊柱；Phase B 接 DeepSeek 走 auto 路径。',
    plugins: ['terminal', 'loop', 'subagent', 'web_search', 'team'],
    phaseBBackend: 'deepseek-ai/DeepSeek-V4-Flash',
    default: true,
    accent: 'green',
  },
  {
    id: 'ptc',
    label: 'PTC 模式',
    description: '先写「小程序 / 编排脚本」再批量调工具：开启脚本规划槽位，Agent 先生成幂等计划再批量 dispatch。',
    plugins: ['terminal', 'loop', 'web_search'],
    phaseBBackend: 'deepseek-ai/DeepSeek-V4-Flash',
    accent: 'amber',
  },
  {
    id: 'minimal',
    label: '极简模式',
    description: '仅终端：隐藏门户与导航，只剩 chiyu shell + 受限对话环；最快上手、最小心智负担。',
    plugins: ['terminal'],
    phaseBBackend: '无需 LLM（确定性）',
    accent: 'cyan',
  },
  {
    id: 'creative',
    label: '创造模式',
    description: 'Everything is a Plugin：全插件 + voice + 自定义 hook，开放插件注册与模式声明框架。',
    plugins: ['terminal', 'loop', 'subagent', 'web_search', 'team', 'voice'],
    phaseBBackend: 'deepseek-ai/DeepSeek-V4-Flash',
    accent: 'violet',
  },
];

export const MODE_MAP: Record<string, ModePreset> = Object.fromEntries(
  MODES.map((m) => [m.id, m]),
);

/* ─────────────────────────────────────────────────────────────
   场景三级分类（解法分层，中性通用；消费方可经 bootstrap 覆盖）
   边界判据：AI 替几个岗位、替几次 —— 而非系统数量/链路长短
   ───────────────────────────────────────────────────────────── */
export const LEVELS: Level[] = [
  {
    id: 'single',
    label: '单点提效',
    criteria: '单智能体取数算出完整结果，交回一个岗位一次确认；人只提供输入 + 一次审批',
    solution: '沉淀为可复用 SKILL / 单 Agent，低成本、快见效、易治理',
  },
  {
    id: 'flow',
    label: '流程提效',
    criteria: 'AI 输出必须喂送下一个岗位做不同的事，形成 A→B→C 接力；每环节有不同角色的独立动作/批准',
    solution: '智能体编排：角色智能体 + 状态机 + 事件总线 + 审批闸门（HITL）',
  },
  {
    id: 'end2end',
    label: '端到端增值',
    criteria: '从开始到结束改变经营结果：感知 → 认知 → 决策 → 执行闭环，AI 完成决策、人做审核',
    solution: '企业级 AI 决策平台：统一决策内核 + 记忆系统 + 治理（RBAC/审计）',
  },
];

export const LEVEL_MAP: Record<string, Level> = Object.fromEntries(
  LEVELS.map((l) => [l.id, l]),
);

/** 层级 → 工作模式联动推荐（第 2 步选中工作流后，第 3 步据此高亮） */
export const LEVEL_MODES: Record<LevelId, ModeId[]> = {
  single: ['ptc', 'minimal'],
  flow: ['standard'],
  end2end: ['standard', 'creative'],
};

/* ─────────────────────────────────────────────────────────────
   方向（行业 / 租户，经 TenantProfile 注入；此处仅作演示枚举）
   ───────────────────────────────────────────────────────────── */
export const DIRECTIONS: Direction[] = [
  { id: 'finance', label: '金融 / 风控', hint: '信贷、反欺诈、合规' },
  { id: 'retail', label: '零售 / 电商', hint: '选品、运营、客服' },
  { id: 'manufacturing', label: '制造 / 供应链', hint: '排程、质量、履约' },
  { id: 'generic', label: '通用助手', hint: '跨领域问答与任务' },
];

/* ─────────────────────────────────────────────────────────────
   工作流（从已注册能力动态生成；level = 归属三级分类）
   ───────────────────────────────────────────────────────────── */
export const WORKFLOWS: Workflow[] = [
  { id: 'decide', label: '决策辅助', hint: '决策脊柱 · 红线校验 · 闭环审核', level: 'end2end' },
  { id: 'research', label: '调研检索', hint: '联网 + 子智能体归纳，一次交回', level: 'single' },
  { id: 'automate', label: '任务编排', hint: '跨岗位接力 · 状态机 + 审批闸门', level: 'flow' },
  { id: 'build', label: '能力沉淀', hint: '封装为 SKILL / 插件，单点复用', level: 'single' },
];

/* ─────────────────────────────────────────────────────────────
   示例会话：演示「本仓原生能力 → agent 工具」无缝集成
   （native-context-assemble / native-redline-check + 决策脊柱）
   ───────────────────────────────────────────────────────────── */
export const SAMPLE_CONVERSATION: Conversation = {
  id: 'c1',
  title: '为信贷客户做决策辅助',
  messages: [
    {
      id: 'm1',
      role: 'user',
      content: '帮我给一位申请 50 万经营贷的客户做决策辅助，先装配 L1 语义与 L2 历史，再校验红线。',
    },
    {
      id: 'm2',
      role: 'assistant',
      content:
        '已为你装配分层上下文并跑通决策脊柱。下面先调用本仓原生工具「上下文装配」，再执行「红线命中检查」。',
      toolCalls: [
        {
          name: 'native-context-assemble',
          status: 'ok',
          args: {
            needs: [{ layer: 'L1', dims: ['semantics'] }, { layer: 'L2', dims: ['history'] }],
            provided: { L1: [{ dim: 'semantics', key: 'industry', value: '餐饮' }] },
          },
          result: { facts: { L1: ['餐饮'], L2: [] }, missing: ['L2.history'] },
        },
        {
          name: 'native-redline-check',
          status: 'ok',
          args: { actions: ['承诺保本收益', '隐瞒费率'] },
          result: { redline_hit: false, hits: [] },
          note: 'high_risk 工具经 redline_guard 硬闸门复核，未命中冻结红线集',
        },
      ],
      trace: [
        { label: 'S1 目标锚定', note: '经营贷 · 50万', status: 'pass' },
        { label: 'S2 上下文装配', note: 'L1 命中 · L2 缺失', status: 'warn' },
        { label: 'S3 红线校验', note: '0 命中', status: 'pass' },
        { label: 'S4 九尺子评分', note: 'safe 7.8 / risk 2.1', status: 'pass' },
        { label: 'S5 决策产出', note: '建议：补充 L2 后进入人工复核', status: 'pass' },
      ],
    },
    {
      id: 'm3',
      role: 'user',
      content: '如果销售承诺「保本保收益」会怎样？',
    },
    {
      id: 'm4',
      role: 'assistant',
      content:
        '该表述命中本仓冻结红线集（meta_redline），原生红线工具会经 redline_guard 直接拦截，对话闭环不会放行。下面是一次被拦截的调用演示。',
      toolCalls: [
        {
          name: 'native-redline-check',
          status: 'blocked',
          args: { actions: ['承诺保本保收益'] },
          result: { redline_hit: true, hits: ['meta: 承诺保本收益'] },
          note: 'GuardDenied：high_risk 工具被红线硬闸门拦截',
        },
      ],
      trace: [
        { label: 'S3 红线校验', note: '命中 meta:承诺保本收益', status: 'fail' },
        { label: '决策产出', note: '已拦截，建议合规话术替代', status: 'warn' },
      ],
    },
  ],
};

/* 问候屏的建议 chip */
export const GREET_CHIPS = [
  { title: '做决策辅助', desc: '用九尺子 + 红线为业务判断打分', prompt: '帮我给一位申请经营贷的客户做决策辅助' },
  { title: '装配上下文', desc: '按 L1–L4 分层装配知识', prompt: '先装配 L1 语义与 L2 历史，再校验红线' },
  { title: '任务编排', desc: '先规划脚本再批量 dispatch', prompt: '帮我把这批工单按优先级排成脚本再批量处理' },
  { title: '开发插件', desc: '把能力封装为新插件', prompt: '我想把合同审查封装成一个自定义插件' },
];
