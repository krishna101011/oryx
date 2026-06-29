function ContentScreen() {
  const templates = [
    { name: 'Daily Brief',     desc: '6 bullets · 320 words · 3 charts', use: 124 },
    { name: 'Earnings Recap',  desc: 'TL;DR · numbers · transcript snips', use: 38 },
    { name: 'Macro deep-dive', desc: 'Long-form · 1500w · charts', use: 22 },
    { name: 'Twitter thread',  desc: '6–10 tweets · hooks · CTA', use: 86 },
    { name: 'Substack issue',  desc: 'Subject · TOC · sections', use: 41 },
  ];

  const queue = [
    { t: '09:30 ET', title: 'BTC ETF flows snap back — what it means', ch: ['Substack','X','LinkedIn'], stat: 'approved' },
    { t: '12:00 ET', title: 'PCE preview — three scenarios',           ch: ['X','Substack'],           stat: 'draft' },
    { t: '16:30 ET', title: 'NVDA Q1 teardown · part 1',                ch: ['Substack','LinkedIn'],    stat: 'review' },
    { t: '07:30 ET (Sat)', title: 'Weekend macro recap',                ch: ['Substack'],                stat: 'scheduled' },
  ];

  return (
    <div className="section" style={{ height: 'calc(100vh - 44px - 32px)', display: 'flex', flexDirection: 'column' }}>
      <div className="grid" style={{ gridTemplateColumns: '220px 1fr 280px', gap: 12, flex: 1, minHeight: 0 }}>
        {/* Templates */}
        <Card title="Templates" sub="BRAND KIT" noPad>
          <div>
            {templates.map((t, i) => (
              <div key={t.name} style={{ padding: '10px 12px', borderBottom: i < templates.length-1 ? '1px solid var(--hairline)' : 'none', cursor: 'pointer', borderLeft: i === 0 ? '2px solid var(--violet)' : '2px solid transparent', background: i === 0 ? 'rgba(139,92,246,0.05)' : undefined }}>
                <div style={{ display: 'flex', alignItems: 'center' }}>
                  <span style={{ fontSize: 12, fontWeight: 500 }}>{t.name}</span>
                  <span style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--text-4)' }} className="mono">{t.use}×</span>
                </div>
                <div style={{ fontSize: 10.5, color: 'var(--text-3)', marginTop: 3 }}>{t.desc}</div>
              </div>
            ))}
            <div style={{ padding: 10 }}>
              <button className="btn ghost" style={{ width: '100%', fontSize: 11, justifyContent: 'center' }}><Icon.Plus size={11}/> New template</button>
            </div>
          </div>
        </Card>

        {/* Editor */}
        <Card title="Daily Brief · Jun 28" sub="DRAFT v3 · AUTOSAVED 12s ago" right={<>
          <span className="chip warn">REVIEW</span>
          <span className="mono" style={{ fontSize: 10, color: 'var(--text-4)' }}>312 / 320 words</span>
        </>}>
          <div style={{ display: 'flex', gap: 4, padding: '4px 0 10px', borderBottom: '1px solid var(--border)', marginBottom: 12 }}>
            {[{l:'H1',v:'B'},{l:'H2'},{l:'P'},{l:'B', v:'B'},{l:'I',v:'I'},{l:'• List'},{l:'❝ Quote'},{l:'< Code/>'},{l:'⚏ Chart'},{l:'🔗 Link'}].map(t => (
              <button key={t.l} className="btn ghost" style={{ fontSize: 10, padding: '3px 6px' }}>{t.l}</button>
            ))}
            <button className="btn ghost" style={{ marginLeft: 'auto', fontSize: 10, padding: '3px 6px' }}><Icon.Sparkles size={10}/> AI</button>
          </div>

          <h1 style={{ fontSize: 24, fontWeight: 700, letterSpacing: '-0.02em', margin: '0 0 6px' }}>BTC ETF flows snap back — what it means</h1>
          <div className="mono" style={{ fontSize: 11, color: 'var(--text-3)', marginBottom: 14 }}>Jun 28, 2026 · 4 min read · Daily Brief</div>

          <h2 style={{ fontSize: 14, fontWeight: 600, margin: '12px 0 6px', color: 'var(--text)' }}>TL;DR</h2>
          <p style={{ fontSize: 12.5, lineHeight: 1.65, color: 'var(--text-2)', margin: '0 0 10px' }}>
            Spot Bitcoin ETFs recorded their first positive net inflow in four sessions on Thursday — <span className="mono" style={{ color: 'var(--text)', background: 'rgba(20,184,166,0.1)', padding: '0 4px', borderRadius: 2 }}>+$378M</span>, led by BlackRock's IBIT. Combined with a funding-rate flip across major perps and a 4,800-BTC whale withdrawal from Coinbase, the on-chain setup is the cleanest it's been since March.
          </p>

          <h2 style={{ fontSize: 14, fontWeight: 600, margin: '14px 0 6px' }}>The flows</h2>
          <p style={{ fontSize: 12.5, lineHeight: 1.65, color: 'var(--text-2)', margin: '0 0 10px' }}>
            <span style={{ background: 'rgba(139,92,246,0.12)', padding: '0 3px', borderBottom: '1px dashed var(--violet)' }}>IBIT alone took $241M</span> — 64% of the day's net flow — while GBTC's bleed has slowed to a trickle. The four-day outflow streak that started after the Fed's June hold appears to be exhausted.
          </p>

          <div style={{ background: 'var(--elev)', border: '1px solid var(--border)', borderRadius: 5, padding: 12, margin: '10px 0' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
              <Icon.Chart size={12}/> <span className="mono" style={{ fontSize: 10, color: 'var(--text-3)', letterSpacing: '0.08em' }}>EMBEDDED CHART · Spot BTC ETF net flows</span>
            </div>
            <svg width="100%" height="80" viewBox="0 0 400 80">
              {[3,-1,4,5,-2,-3,-1,8,12].map((v, i) => {
                const x = 20 + i*40, w = 28;
                const h = Math.abs(v) * 4;
                return <rect key={i} x={x} y={v >= 0 ? 40 - h : 40} width={w} height={h} fill={v >= 0 ? '#14B8A6' : '#F87171'} opacity="0.8"/>;
              })}
              <line x1="0" x2="400" y1="40" y2="40" stroke="#1A2330"/>
            </svg>
          </div>

          <h2 style={{ fontSize: 14, fontWeight: 600, margin: '14px 0 6px' }}>What changes the call</h2>
          <p style={{ fontSize: 12.5, lineHeight: 1.65, color: 'var(--text-2)' }}>
            Watch PCE at 08:30 ET. A hot print (above 0.3% MoM core) would re-arm the duration-led risk-off trade and likely fade ETF demand. A soft print and the path of least resistance is back toward the 68,500 zone…
          </p>

          <div style={{ marginTop: 16, display: 'flex', gap: 6, paddingTop: 12, borderTop: '1px solid var(--border)' }}>
            <button className="btn"><Icon.Sparkles size={11}/> Tighten</button>
            <button className="btn"><Icon.Sparkles size={11}/> Brand voice check</button>
            <button className="btn primary" style={{ marginLeft: 'auto' }}><Icon.Send size={11}/> Send for approval</button>
          </div>
        </Card>

        {/* Right rail */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12, minHeight: 0 }}>
          <Card title="Linked sources" sub="3 PACKETS · 8 CLAIMS" noPad>
            {[
              { p: 'PKT-44', t: 'BTC ETF June flows', n: 5 },
              { p: 'PKT-42', t: 'PCE inflation watch', n: 2 },
              { p: 'PKT-40', t: 'SOL ETF probability', n: 1 },
            ].map((p, i) => (
              <div key={p.p} style={{ padding: '8px 10px', borderBottom: i < 2 ? '1px solid var(--hairline)' : 'none' }}>
                <div className="mono" style={{ fontSize: 10, color: 'var(--text-4)' }}>{p.p}</div>
                <div style={{ fontSize: 11.5 }}>{p.t}</div>
                <div style={{ fontSize: 10, color: 'var(--text-3)', marginTop: 2 }} className="mono">{p.n} CLAIMS LINKED</div>
              </div>
            ))}
          </Card>

          <Card title="Approval workflow">
            {[
              { who: 'Alex K.', state: 'approved', t: '5m' },
              { who: 'Compliance', state: 'pending', t: '—', active: true },
              { who: 'Auto-publish 09:30', state: 'queued', t: '—' },
            ].map((s, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '5px 0', borderBottom: i < 2 ? '1px solid var(--hairline)' : 'none' }}>
                <div style={{ width: 6, height: 6, borderRadius: 50, background: s.state === 'approved' ? 'var(--teal)' : s.state === 'pending' ? 'var(--violet)' : 'var(--text-4)' }}/>
                <span style={{ fontSize: 11.5, flex: 1, color: s.active ? 'var(--text)' : undefined }}>{s.who}</span>
                <span className="mono" style={{ fontSize: 9.5, color: 'var(--text-4)' }}>{s.state.toUpperCase()}</span>
              </div>
            ))}
          </Card>

          <Card title="Content queue" sub="NEXT 24H">
            {queue.map((q, i) => (
              <div key={i} style={{ padding: '7px 0', borderBottom: i < queue.length-1 ? '1px solid var(--hairline)' : 'none' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span className="mono" style={{ fontSize: 10, color: 'var(--text-3)', minWidth: 80 }}>{q.t}</span>
                  <span className={"chip " + (q.stat === 'approved' || q.stat === 'scheduled' ? 'teal' : q.stat === 'review' ? 'warn' : '')} style={{ fontSize: 9 }}>{q.stat.toUpperCase()}</span>
                </div>
                <div style={{ fontSize: 11, color: 'var(--text)', marginTop: 3 }}>{q.title}</div>
                <div style={{ fontSize: 10, color: 'var(--text-4)', marginTop: 2 }} className="mono">{q.ch.join(' · ')}</div>
              </div>
            ))}
          </Card>
        </div>
      </div>
    </div>
  );
}
window.ContentScreen = ContentScreen;
