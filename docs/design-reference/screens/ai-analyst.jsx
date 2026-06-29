function AIAnalystScreen() {
  const convo = [
    { role: 'user',  txt: 'Did BTC ETF flows actually turn positive yesterday, and what would invalidate the bullish read?' },
    { role: 'ai',    agent: 'MARKET COPILOT',
      txt: 'Yes — spot Bitcoin ETFs recorded **+$378M** in net inflow on Jun 27, 2024, ending a 3-day outflow streak. IBIT led with $241M (64% of net flow).',
      sources: [
        { n: '[1]', src: 'Farside Investors · primary data',  q: 96, claim: 'CL-1408' },
        { n: '[2]', src: 'Bloomberg Terminal',                  q: 94, claim: 'CL-1408' },
        { n: '[3]', src: 'Reuters',                              q: 94, claim: 'CL-1408' },
      ],
      followup: 'The bullish read would weaken if (a) PCE prints hot (>0.3% MoM core), (b) ETF flow fails to clear $200M in the next session, or (c) the funding-rate flip reverses on Binance perps within 24h.',
      conf: 0.92,
    },
    { role: 'user',  txt: 'Draft a paragraph I can use in today\'s brief.' },
    { role: 'ai',    agent: 'CONTENT COPILOT',
      txt: '"Spot Bitcoin ETFs broke a four-day cold streak yesterday with **+$378M** in net inflows, led by BlackRock\'s IBIT at $241M. Combined with funding rates flipping positive across the major perp venues and a 4,800-BTC whale withdrawal from Coinbase, the on-chain picture is the cleanest it\'s been since March. That said, the read invalidates quickly: any hot PCE print this morning, or a failure to clear $200M in flows tomorrow, would reset the call."',
      meta: { words: 78, voice: 'On-brand · 94%', readability: 'Grade 11' },
      sources: [],
      conf: 0.88,
    },
  ];

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '240px 1fr 280px', height: 'calc(100vh - 44px)' }}>
      {/* Agent / convo rail */}
      <div style={{ borderRight: '1px solid var(--border)', background: 'var(--panel)', overflow: 'auto' }}>
        <div style={{ padding: 12 }}>
          <button className="btn primary" style={{ width: '100%', justifyContent: 'center' }}><Icon.Plus size={11}/> New thread</button>
        </div>
        <div className="mono" style={{ fontSize: 9.5, color: 'var(--text-4)', letterSpacing: '0.12em', padding: '8px 12px 4px' }}>AGENTS</div>
        {[
          { n: 'Market Copilot',    s: 'Charts, prices, signals',     col: '#14B8A6', active: true },
          { n: 'Research Copilot',  s: 'Verify, cite, summarize',     col: '#8B5CF6', active: true },
          { n: 'Content Copilot',   s: 'Draft, tighten, brand-voice', col: '#5B5BF5', active: true },
          { n: 'Automation Copilot',s: 'Build rules from intent',     col: '#60A5FA' },
        ].map((a, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '7px 12px', cursor: 'pointer', borderLeft: a.active ? '2px solid ' + a.col : '2px solid transparent', background: a.active ? a.col + '08' : undefined }}>
            <div style={{ width: 6, height: 6, borderRadius: 50, background: a.col, boxShadow: a.active ? '0 0 6px ' + a.col : undefined }}/>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 11.5, color: 'var(--text)' }}>{a.n}</div>
              <div className="mono" style={{ fontSize: 9.5, color: 'var(--text-4)' }}>{a.s}</div>
            </div>
          </div>
        ))}

        <div className="mono" style={{ fontSize: 9.5, color: 'var(--text-4)', letterSpacing: '0.12em', padding: '14px 12px 4px' }}>RECENT THREADS</div>
        {[
          { t: 'BTC ETF flow analysis', d: '2m', active: true },
          { t: 'NVDA Q1 earnings teardown', d: '3h' },
          { t: 'PCE preview scenarios', d: '1d' },
          { t: 'SOL ETF probability model', d: '2d' },
          { t: 'Compare BTC cycles 2017/2021/2024', d: '4d' },
          { t: 'JPY intervention thesis', d: '6d' },
        ].map((t, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 12px', borderLeft: t.active ? '2px solid var(--violet)' : '2px solid transparent', background: t.active ? 'rgba(139,92,246,0.06)' : undefined, cursor: 'pointer' }}>
            <span style={{ fontSize: 11, flex: 1, color: t.active ? 'var(--text)' : 'var(--text-2)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{t.t}</span>
            <span className="mono" style={{ fontSize: 9.5, color: 'var(--text-4)' }}>{t.d}</span>
          </div>
        ))}
      </div>

      {/* Conversation */}
      <div style={{ display: 'flex', flexDirection: 'column', background: 'var(--bg)', overflow: 'hidden' }}>
        {/* Thread header */}
        <div style={{ padding: '12px 18px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 10 }}>
          <HornMark size={20}/>
          <div>
            <div style={{ fontSize: 13, fontWeight: 600 }}>BTC ETF flow analysis</div>
            <div className="mono" style={{ fontSize: 10, color: 'var(--text-4)' }}>3 AGENTS · 8 SOURCES · STARTED 07:44 ET</div>
          </div>
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
            <button className="btn ghost" style={{ fontSize: 10.5 }}><Icon.Download size={11}/> Export</button>
            <button className="btn ghost" style={{ fontSize: 10.5 }}><Icon.Send size={11}/> To Studio</button>
          </div>
        </div>

        <div style={{ flex: 1, overflow: 'auto', padding: '20px 24px' }}>
          {convo.map((m, i) => (
            <div key={i} style={{ marginBottom: 22, display: 'flex', gap: 12 }}>
              {m.role === 'user' ? (
                <div className="avatar" style={{ marginTop: 2 }}>JM</div>
              ) : (
                <div style={{ width: 26, height: 26, borderRadius: 4, background: 'var(--accent-grad)', display: 'grid', placeItems: 'center' }}>
                  <Icon.Sparkles size={13} />
                </div>
              )}
              <div style={{ flex: 1, maxWidth: 720 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                  <span style={{ fontSize: 11.5, fontWeight: 600, color: m.role === 'user' ? 'var(--text)' : 'var(--violet)' }}>{m.role === 'user' ? 'Jordan' : m.agent}</span>
                  {m.role === 'ai' && <span className="chip teal dot" style={{ fontSize: 9 }}>VERIFIED · {m.conf.toFixed(2)}</span>}
                </div>
                <div style={{ fontSize: 13, color: 'var(--text)', lineHeight: 1.65 }}
                     dangerouslySetInnerHTML={{ __html: m.txt.replace(/\*\*(.+?)\*\*/g, '<span style="font-family:var(--font-mono); background: rgba(139,92,246,0.15); padding:1px 4px; border-radius:2px;">$1</span>') }}/>
                {m.followup && <div style={{ marginTop: 10, paddingTop: 10, borderTop: '1px dashed var(--border)', fontSize: 12.5, color: 'var(--text-2)', lineHeight: 1.6 }}>{m.followup}</div>}
                {m.sources && m.sources.length > 0 && (
                  <div style={{ marginTop: 12, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    {m.sources.map((s, j) => (
                      <div key={j} style={{ display: 'flex', alignItems: 'center', gap: 6, background: 'var(--elev)', border: '1px solid var(--border)', borderRadius: 4, padding: '4px 8px', fontSize: 10.5 }}>
                        <span className="mono" style={{ color: 'var(--violet)' }}>{s.n}</span>
                        <span style={{ color: 'var(--text-2)' }}>{s.src}</span>
                        <span className="mono" style={{ color: 'var(--text-4)' }}>Q{s.q}</span>
                        <span className="chip teal" style={{ fontSize: 9 }}>{s.claim}</span>
                      </div>
                    ))}
                  </div>
                )}
                {m.meta && (
                  <div className="mono" style={{ marginTop: 8, fontSize: 10, color: 'var(--text-4)', letterSpacing: '0.06em' }}>
                    {m.meta.words} WORDS · VOICE {m.meta.voice} · {m.meta.readability}
                  </div>
                )}
                {m.role === 'ai' && (
                  <div style={{ marginTop: 10, display: 'flex', gap: 6 }}>
                    <button className="btn ghost" style={{ fontSize: 10.5 }}>Copy</button>
                    <button className="btn ghost" style={{ fontSize: 10.5 }}><Icon.Beaker size={10}/> Save to packet</button>
                    <button className="btn ghost" style={{ fontSize: 10.5 }}><Icon.Pen size={10}/> Open in Studio</button>
                    <button className="btn ghost" style={{ fontSize: 10.5 }}>Regenerate</button>
                  </div>
                )}
              </div>
            </div>
          ))}

          {/* Agent activity ribbon */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 12px', background: 'rgba(139,92,246,0.04)', border: '1px solid rgba(139,92,246,0.15)', borderRadius: 4 }}>
            <div style={{ width: 4, height: 4, borderRadius: 50, background: 'var(--violet)', boxShadow: '0 0 6px var(--violet)' }}/>
            <span className="mono" style={{ fontSize: 10.5, color: 'var(--violet)', letterSpacing: '0.1em' }}>RESEARCH COPILOT</span>
            <span style={{ fontSize: 11.5, color: 'var(--text-2)' }}>Cross-checking 6 sources for ETH lag thesis…</span>
            <span style={{ marginLeft: 'auto' }} className="mono" style={{ fontSize: 10, color: 'var(--text-4)' }}>3 / 6</span>
          </div>
        </div>

        {/* Composer */}
        <div style={{ padding: 14, borderTop: '1px solid var(--border)' }}>
          <div style={{ background: 'var(--elev)', border: '1px solid var(--border-strong)', borderRadius: 8, padding: 10 }}>
            <div style={{ display: 'flex', gap: 6, marginBottom: 8 }}>
              <span className="chip violet">@market</span>
              <span className="chip indigo">@research</span>
              <span className="chip" style={{ fontSize: 9 }}>Source: PKT-44</span>
              <span style={{ marginLeft: 'auto' }} className="mono" style={{ fontSize: 9.5, color: 'var(--text-4)' }}>SOURCE-BACKED MODE · ON</span>
            </div>
            <div style={{ fontSize: 12.5, color: 'var(--text-3)' }}>Ask anything · cite sources · build a thesis…</div>
            <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
              <button className="btn ghost" style={{ fontSize: 10.5 }}><Icon.Chart size={10}/> Chart</button>
              <button className="btn ghost" style={{ fontSize: 10.5 }}><Icon.Beaker size={10}/> Packet</button>
              <button className="btn ghost" style={{ fontSize: 10.5 }}><Icon.Code size={10}/> Code</button>
              <button className="btn primary" style={{ marginLeft: 'auto' }}><Icon.Send size={11}/> Run</button>
            </div>
          </div>
        </div>
      </div>

      {/* Right rail */}
      <div style={{ borderLeft: '1px solid var(--border)', overflow: 'auto', padding: 10 }}>
        <Card title="Sources used" sub="THIS THREAD" noPad>
          {[
            { n: 1, s: 'Farside Investors API',   q: 96 },
            { n: 2, s: 'Bloomberg Terminal',       q: 94 },
            { n: 3, s: 'Reuters',                   q: 94 },
            { n: 4, s: 'CoinDesk',                  q: 78 },
            { n: 5, s: 'Glassnode',                 q: 88 },
            { n: 6, s: 'Arkham Intelligence',       q: 82 },
            { n: 7, s: 'NVDA 8-K filing',           q: 100 },
            { n: 8, s: 'PKT-44 internal',           q: 90 },
          ].map(s => (
            <div key={s.n} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 10px', borderBottom: '1px solid var(--hairline)', fontSize: 11 }}>
              <span className="mono" style={{ color: 'var(--violet)', width: 18 }}>[{s.n}]</span>
              <span style={{ flex: 1 }}>{s.s}</span>
              <span className="mono" style={{ color: 'var(--text-4)', fontSize: 10 }}>Q{s.q}</span>
            </div>
          ))}
        </Card>
        <div style={{ marginTop: 10 }}>
          <Card title="Thread confidence" sub="AGGREGATE">
            <div style={{ textAlign: 'center', padding: '10px 0' }}>
              <div className="mono" style={{ fontSize: 28, fontWeight: 600 }}>0.89</div>
              <div className="mono" style={{ fontSize: 9.5, color: 'var(--text-4)', letterSpacing: '0.15em' }}>WEIGHTED AVG · 8 SOURCES</div>
              <div className="meter" style={{ marginTop: 10 }}><div className="meter-fill teal" style={{ width: '89%' }}/></div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
window.AIAnalystScreen = AIAnalystScreen;
