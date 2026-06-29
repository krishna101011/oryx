// ORYX root app

const { useState, useEffect, useMemo } = React;

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "accent": "indigo",
  "density": "compact",
  "showWatermark": true,
  "monoData": true
}/*EDITMODE-END*/;

const ACCENTS = {
  indigo:  { grad: 'linear-gradient(135deg, #5B5BF5 0%, #8B5CF6 100%)', solo: '#8B5CF6', soft: 'rgba(139,92,246,0.18)' },
  teal:    { grad: 'linear-gradient(135deg, #0EA5A0 0%, #14B8A6 100%)', solo: '#14B8A6', soft: 'rgba(20,184,166,0.18)' },
  violet:  { grad: 'linear-gradient(135deg, #7C3AED 0%, #C026D3 100%)', solo: '#A855F7', soft: 'rgba(168,85,247,0.18)' },
  azure:   { grad: 'linear-gradient(135deg, #2563EB 0%, #60A5FA 100%)', solo: '#3B82F6', soft: 'rgba(96,165,250,0.18)' },
};

function NavIcon({ name }) {
  const Comp = Icon[name] || Icon.Dot;
  return <span className="nav-icon"><Comp size={14} /></span>;
}

function Sidebar({ route, setRoute }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="mark"><HornMark size={22} /></div>
        <div className="word">ORYX</div>
        <div className="badge">v0.9</div>
      </div>
      <div className="workspace-pill">
        <div className="ws-icon" style={{ background: 'rgba(20,184,166,0.12)', border: '1px solid rgba(20,184,166,0.3)' }}>
          <HornMark size={12}/>
        </div>
        <div>
          <div className="ws-name">ORYX Editorial</div>
          <div className="ws-role">WORKSPACE · PRO</div>
        </div>
        <span className="ws-chev"><Icon.ChevDown size={12}/></span>
      </div>
      <nav className="nav">
        {NAV.map(g => (
          <div className="nav-group" key={g.group}>
            <div className="nav-label">{g.group}</div>
            {g.items.map(it => (
              <div key={it.id}
                   className={"nav-item" + (route === it.id ? " active" : "")}
                   onClick={() => setRoute(it.id)}>
                <NavIcon name={it.icon} />
                <span>{it.label}</span>
                {it.badge && <span className="nav-badge">{it.badge}</span>}
                {it.dot && !it.badge && <span className="nav-dot" />}
              </div>
            ))}
          </div>
        ))}
      </nav>
      <div className="sidebar-foot">
        <div className="avatar">JM</div>
        <div>
          <div className="name">Jordan Mehta</div>
          <div className="role">EDITOR-IN-CHIEF</div>
        </div>
        <div className="status-dot" title="online" />
      </div>
    </aside>
  );
}

function TopBar({ route }) {
  const meta = SCREEN_META[route] || {};
  return (
    <header className="topbar">
      <div className="crumbs">
        <span>{meta.breadcrumb?.[0]}</span>
        <span className="sep"><Icon.ChevRight size={10} /></span>
        <span className="here">{meta.breadcrumb?.[1]}</span>
      </div>
      <div className="cmd">
        <Icon.Search size={12} />
        <span>Search markets, claims, sources, drafts…</span>
        <span className="kbd">⌘K</span>
      </div>
      <div className="ticker-strip">
        {TICKERS.slice(0,6).map(t => (
          <div className="t" key={t.sym}>
            <span className="sym">{t.sym}</span>
            <span className="px">{t.px.toLocaleString(undefined,{minimumFractionDigits: t.px<100?2:0})}</span>
            <span className={t.chg >= 0 ? 'pos' : 'neg'}>{t.chg >= 0 ? '+' : ''}{t.chg.toFixed(2)}%</span>
          </div>
        ))}
      </div>
      <div className="top-icons">
        <div className="ai-btn">
          <span className="pulse" />
          AI Analyst
        </div>
        <div className="icon-btn"><Icon.Bell size={14} /><span className="bell-dot" /></div>
        <div className="icon-btn"><Icon.Cog size={14} /></div>
      </div>
    </header>
  );
}

function App() {
  const [route, setRoute] = useState(() => localStorage.getItem('oryx-route') || 'home');
  useEffect(() => { localStorage.setItem('oryx-route', route); }, [route]);

  const [tweaks, setTweak] = useTweaks(TWEAK_DEFAULTS);

  // Apply accent to CSS vars
  useEffect(() => {
    const a = ACCENTS[tweaks.accent] || ACCENTS.indigo;
    document.documentElement.style.setProperty('--accent-grad', a.grad);
    document.documentElement.style.setProperty('--accent-grad-soft', a.soft);
    document.documentElement.style.setProperty('--row-h', tweaks.density === 'cozy' ? '32px' : '24px');
  }, [tweaks.accent, tweaks.density]);

  const Screen = useMemo(() => ({
    home: window.CommandCenter,
    news: window.NewsScreen,
    verify: window.VerificationScreen,
    research: window.ResearchScreen,
    technical: window.TechnicalScreen,
    terminal: window.TerminalScreen,
    opps: window.OppsScreen,
    content: window.ContentScreen,
    publish: window.PublishScreen,
    automation: window.AutomationScreen,
    analytics: window.AnalyticsScreen,
    academy: window.AcademyScreen,
    ai: window.AIAnalystScreen,
    team: window.TeamScreen,
    settings: window.SettingsScreen,
    intake: window.IntakeScreen,
  }[route] || window.CommandCenter), [route]);

  return (
    <div className="app">
      <Sidebar route={route} setRoute={setRoute} />
      <TopBar route={route} />
      <main className="main" key={route}>
        {Screen ? <Screen tweaks={tweaks} setRoute={setRoute} /> : <div style={{ padding: 40 }}>Loading…</div>}
      </main>

      <TweaksPanel title="Tweaks">
        <TweakSection title="Accent">
          <TweakRadio label="Primary" value={tweaks.accent} onChange={v => setTweak('accent', v)}
                      options={[{ label: 'Indigo', value: 'indigo' }, { label: 'Teal', value: 'teal' }, { label: 'Violet', value: 'violet' }, { label: 'Azure', value: 'azure' }]} />
        </TweakSection>
        <TweakSection title="Layout">
          <TweakRadio label="Density" value={tweaks.density} onChange={v => setTweak('density', v)}
                      options={[{ label: 'Compact', value: 'compact' }, { label: 'Cozy', value: 'cozy' }]} />
          <TweakToggle label="Mono for data" value={tweaks.monoData} onChange={v => setTweak('monoData', v)} />
          <TweakToggle label="Brand watermark" value={tweaks.showWatermark} onChange={v => setTweak('showWatermark', v)} />
        </TweakSection>
        <TweakSuggestionBar suggestions={[
          'Open the Markets Terminal',
          'Show me the verification flow for a BTC ETF rumor',
          'Add a Substack channel to publishing',
          'Make the AI Analyst panel feel more agentic',
        ]} />
      </TweaksPanel>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
