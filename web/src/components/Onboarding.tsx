import { useState } from 'react';
import type { ModeId, Direction, Workflow, ModePreset, Level, LevelId } from '../types';
import {
  DIRECTIONS, WORKFLOWS, MODES, LEVELS, LEVEL_MODES,
} from '../data/chiyu';
import { CheckIcon } from './icons';

interface OnboardingProps {
  onEnter: (sel: { direction: Direction; workflow: Workflow; mode: ModeId }) => void;
  /** 来自内核后端（/api/bootstrap）的真实能力；缺省项回退本地演示数据。 */
  modes?: ModePreset[];
  levels?: Level[];
  workflows?: Workflow[];
  directions?: Direction[];
}

const STEPS = ['选方向', '选工作流', '选工作模式', '进入工作台'];

/** Phase B 后端展示文案（防御：内核可能返回 null/空，禁止对 null 调字符串方法） */
function phaseBText(m: ModePreset): string {
  const pb = m.phaseBBackend || '';
  return pb && !pb.startsWith('无需') ? 'Phase B → ' + pb : '无需 LLM（确定性）';
}
function phaseBGray(m: ModePreset): boolean {
  const pb = m.phaseBBackend || '';
  return !pb || pb.startsWith('无需');
}

export default function Onboarding({ onEnter, modes, levels, workflows, directions }: OnboardingProps) {
  // 后端数据优先；未连接内核时使用本地镜像数据
  const displayModes = modes && modes.length ? modes : MODES;
  const displayLevels = levels && levels.length ? levels : LEVELS;
  const displayWorkflows = workflows && workflows.length ? workflows : WORKFLOWS;
  const displayDirections = directions && directions.length ? directions : DIRECTIONS;
  const defaultMode =
    (modes && modes.find((m) => m.default)?.id) ||
    (MODES.find((m) => m.default)?.id as ModeId) ||
    'standard';

  // 层级 → 模式联动推荐：后台 recommended_modes 优先，本地 LEVEL_MODES 兜底
  const levelModes: Record<string, ModeId[]> = {};
  for (const l of displayLevels) {
    const rec = l.recommended_modes;
    levelModes[l.id] = rec && rec.length ? rec : (LEVEL_MODES[l.id as LevelId] ?? []);
  }
  const levelById: Record<string, Level> = Object.fromEntries(
    displayLevels.map((l) => [l.id, l]),
  );

  const [step, setStep] = useState(0);
  const [direction, setDirection] = useState<Direction | null>(null);
  const [workflow, setWorkflow] = useState<Workflow | null>(null);
  const [mode, setMode] = useState<ModeId>(defaultMode as ModeId);

  // 选中工作流 → 由其层级联动推荐工作模式；当前模式不在推荐集则自动切换
  const pickWorkflow = (w: Workflow) => {
    setWorkflow(w);
    const rec = levelModes[w.level] ?? [];
    if (rec.length && !rec.includes(mode)) setMode(rec[0]);
  };

  const nextDisabled =
    (step === 0 && !direction) || (step === 1 && !workflow);

  // 第 2 步：按三级分类分组渲染工作流
  const recModes = workflow ? (levelModes[workflow.level] ?? []) : [];

  return (
    <div className="ob">
      <div className="ob-top">
        <div className="ob-brand">
          <span className="logo">C</span>
          <span>ChiYu Portal</span>
        </div>
        <span className="spacer" />
        <span className="pill accent">参考 DeepSeek Harness 桌面版</span>
      </div>

      <div className="ob-body">
        <div className="ob-card-wrap">
          {/* 步骤指示 */}
          <div className="ob-steps">
            {STEPS.map((s, i) => (
              <span
                key={s}
                className={
                  'ob-step' +
                  (i === step ? ' active' : '') +
                  (i < step ? ' done' : '')
                }
              >
                <span className="num">{i < step ? <CheckIcon size={11} /> : i + 1}</span>
                {s}
              </span>
            ))}
          </div>

          <h1 className="ob-h1">{STEPS[step]}</h1>
          <p className="ob-sub">
            工作流按「单点提效 / 流程提效 / 端到端增值」三级分组，选中后联动推荐工作模式；
            菜单、层级与工作流均从插件注册表 / 工作模式预设动态生成，方向经 TenantProfile 注入，门户零领域字面量。
          </p>

          {/* 步骤内容 */}
          {step === 0 && (
            <div className="ob-grid">
              {displayDirections.map((d) => (
                <div
                  key={d.id}
                  className={'ob-choice' + (direction?.id === d.id ? ' selected' : '')}
                  onClick={() => setDirection(d)}
                >
                  <h3>{d.label}</h3>
                  <p>{d.hint}</p>
                </div>
              ))}
            </div>
          )}

          {step === 1 && (
            <div className="ob-groups">
              {displayLevels.map((lvl) => {
                const ws = displayWorkflows.filter((w) => w.level === lvl.id);
                if (!ws.length) return null;
                return (
                  <div key={lvl.id} className="ob-lvl-group">
                    <div className="ob-lvl-head">
                      <span className={'ob-lvl-tag lvl-' + lvl.id}>{lvl.label}</span>
                      <span className="ob-lvl-criteria">{lvl.criteria}</span>
                    </div>
                    <div className="ob-grid">
                      {ws.map((w) => (
                        <div
                          key={w.id}
                          className={'ob-choice' + (workflow?.id === w.id ? ' selected' : '')}
                          onClick={() => pickWorkflow(w)}
                        >
                          <h3>{w.label}</h3>
                          <p>{w.hint}</p>
                          <div className="ob-pb">解法：{lvl.solution}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {step === 2 && (
            <div className="ob-grid">
              {displayModes.map((m) => (
                <div
                  key={m.id}
                  className={
                    'ob-choice' +
                    (m.default ? ' default' : '') +
                    (mode === m.id ? ' selected' : '')
                  }
                  onClick={() => setMode(m.id)}
                >
                  <h3>
                    {m.label}
                    {m.default && <span className="pill" style={{ marginLeft: 4 }}>DEFAULT</span>}
                    {recModes.includes(m.id as ModeId) && (
                      <span className="ob-rec">推荐</span>
                    )}
                  </h3>
                  <p>{m.description}</p>
                  <div className="ob-plugins">
                    {m.plugins.map((p) => (
                      <span key={p} className={'ob-pill ' + m.accent}>{p}</span>
                    ))}
                  </div>
                  <div className={'ob-pb' + (phaseBGray(m) ? ' gray' : '')}>
                    {phaseBText(m)}
                  </div>
                </div>
              ))}
            </div>
          )}

          {step === 3 && (
            <div className="ob-grid">
              <div className="ob-choice selected">
                <h3>已选配置</h3>
                <p>
                  方向：<b>{direction?.label}</b> · 层级：<b>{levelById[workflow!.level]?.label}</b>
                </p>
                <p>
                  工作流：<b>{workflow?.label}</b> · 工作模式：
                  <b>{displayModes.find((m) => m.id === mode)?.label}</b>
                </p>
                <div className="ob-plugins">
                  {displayModes.find((m) => m.id === mode)?.plugins.map((p) => (
                    <span key={p} className="ob-pill">{p}</span>
                  ))}
                </div>
                <div className="ob-pb">
                  进入工作台后，对话页将按该模式装配插件与编排开关。
                </div>
              </div>
              <div className="ob-choice">
                <h3>下一步</h3>
                <p>
                  工作台 = 会话侧栏 + 对话主区 + 能力面板（插件 / 决策脊柱 / 红线）。
                  极简模式将仅保留终端对话环。
                </p>
              </div>
            </div>
          )}

          {/* 操作 */}
          <div className="ob-actions">
            <button className="btn ghost" onClick={() => setStep((s) => Math.max(0, s - 1))} disabled={step === 0}>
              上一步
            </button>
            {step < 3 ? (
              <button
                className="btn primary"
                disabled={nextDisabled}
                onClick={() => setStep((s) => s + 1)}
              >
                下一步
              </button>
            ) : (
              <button
                className="btn primary"
                onClick={() =>
                  onEnter({
                    direction: direction!,
                    workflow: workflow!,
                    mode,
                  })
                }
              >
                进入工作台 →
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
