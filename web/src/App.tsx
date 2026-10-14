import { useEffect, useState } from 'react';
import Onboarding from './components/Onboarding';
import Workbench from './components/Workbench';
import type { ModeId, Direction, Workflow } from './types';
import { fetchBootstrap, type Bootstrap } from './data/api';

interface Selection {
  direction: Direction;
  workflow: Workflow;
  mode: ModeId;
}

export default function App() {
  const [view, setView] = useState<'onboarding' | 'workbench'>('onboarding');
  const [selection, setSelection] = useState<Selection | null>(null);
  const [theme, setTheme] = useState<string>('light');

  // 连接到内核后端：拉取真实能力；失败则回退演示模式
  const [bootstrap, setBootstrap] = useState<Bootstrap | null>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  useEffect(() => {
    let alive = true;
    fetchBootstrap().then((b) => {
      if (!alive) return;
      setBootstrap(b);
      setConnected(!!b);
    });
    return () => {
      alive = false;
    };
  }, []);

  if (view === 'onboarding' || !selection) {
    return (
      <div className="app-shell">
        <Onboarding
          modes={bootstrap?.modes}
          levels={bootstrap?.levels}
          workflows={bootstrap?.workflows}
          directions={bootstrap?.directions}
          onEnter={(sel) => {
            setSelection(sel);
            setView('workbench');
          }}
        />
      </div>
    );
  }

  return (
    <div className="app-shell">
      <Workbench
        selection={selection}
        connected={connected}
        onExit={() => setView('onboarding')}
        theme={theme}
        onToggleTheme={() => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))}
      />
    </div>
  );
}
