function OppsScreen() {
  const opps = [
    { rank: 1, sym: 'BTC',  th: 'ETF inflows reaccelerating after 3-day pause; funding flipped positive across major perps. Whale outflow from Coinbase confirms accumulation thesis.',
      score: 84, conf: 0.91, dir: 'LONG', tf: '1D', rr: '3.4R', entry: '64,200', target: '68,500', stop: '62,800', cats: ['ETF flows','Funding','On-chain'] },
    { rank: 2, sym: 'SOL',  th: 'Token unlock priced in over past 2 weeks. DEX volume uptrend, Solana mobile shipments signal real adoption. Risk: SEC ETF delay.',
      score: 78, conf: 0.84, dir: 'LONG', tf: '4H', rr: '2.8R', entry: '142.0', target: '162.5', stop: '136.4', cats: ['Unlocks','Adoption','ETF'] },
    { rank: 3, sym: 'ETH',  th: 'Lagging BTC by ~12% YTD despite ETF approval. Rotation thesis intact; staking yield + ETH/BTC bottoming pattern.',
      score: 71, conf: 0.79, dir: 'LONG', tf: '1D', rr: '2.2R', entry: '3,140', target: '3,580', stop: '3,012', cats: ['Rotation','ETF','Staking'] },
  ];

  return (
    <div className="section">
      <div className="grid g-4" style={{ marginBottom: 12 }}>
        <Kpi label="Open opportunities" val="3" delta="+1 this week" deltaPos />
        <Kpi label="Avg ORYX score"     val="77.7"  delta="+4.2 vs last batch" deltaPos />
        <Kpi label="Hit-rate · trailing 30d" val="68%" delta="+6% vs benchmark" deltaPos />
        <Kpi label="Realized R · 30d"   val="+11.4R" delta="+3.2R vs prior" deltaPos />
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {opps.map(o => (
          <Card key={o.sym} title={`${o.sym} · ${o.dir}`} sub={`${o.tf} · R/R ${o.rr}`} right={<>
            <span className="chip teal dot">ACTIVE</span>
            <span className="mono" style={{ color: 'var(--text-3)', fontSize: 10 }}>#{o.rank}</span>
          </>}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 240px 240px', gap: 16 }}>
              <div>
                <div style={{ fontSize: 13, color: 'var(--text)', lineHeight: 1.6, marginBottom: 10 }}>{o.th}</div>
                <div style={{ display: 'flex', gap: 6, marginBottom: 10 }}>
                  {o.cats.map(c => <span key={c} className="chip indigo">{c}</span>)}
                </div>
                <div style={{ fontSize: 10.5, color: 'var(--text-4)' }} className="mono">CATALYSTS · TRIGGERS</div>
                <div style={{ marginTop: 4, display: 'flex', flexDirection: 'column', gap: 4 }}>
                  {[
                    { t: '08:30 ET · Core PCE print → confirms or invalidates risk-on regime', when: 'today' },
                    { t: 'BTC > 65,000 sustained close → confirms breakout', when: 'level' },
                    { t: 'ETF aggregate flow > $500M / day for 2 consecutive days', when: 'condition' },
                  ].map((c, i) => (
                    <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11.5, color: 'var(--text-2)' }}>
                      <span className="chip warn" style={{ fontSize: 9 }}>{c.when.toUpperCase()}</span>
                      <span>{c.t}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Levels */}
              <div style={{ borderLeft: '1px solid var(--border)', paddingLeft: 16 }}>
                <div className="mono" style={{ fontSize: 9.5, color: 'var(--text-4)', letterSpacing: '0.1em', marginBottom: 8 }}>LEVELS</div>
                {[
                  { l: 'Entry',   v: o.entry,  c: '#8B5CF6' },
                  { l: 'Target',  v: o.target, c: 'var(--teal)' },
                  { l: 'Stop',    v: o.stop,   c: 'var(--neg)' },
                ].map(l => (
                  <div key={l.l} style={{ display: 'flex', alignItems: 'baseline', padding: '6px 0', borderBottom: '1px solid var(--hairline)' }}>
                    <span style={{ width: 8, height: 8, background: l.c, borderRadius: 2, marginRight: 8 }}/>
                    <span style={{ fontSize: 11, color: 'var(--text-3)' }}>{l.l}</span>
                    <span className="mono" style={{ marginLeft: 'auto', fontSize: 14, fontWeight: 600 }}>{l.v}</span>
                  </div>
                ))}
                <div style={{ marginTop: 10, fontSize: 11 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-3)' }}>
                    <span>ORYX score</span><span className="mono">{o.score}/100</span>
                  </div>
                  <div className="meter" style={{ marginTop: 4 }}><div className="meter-fill" style={{ width: o.score+'%' }}/></div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-3)', marginTop: 8 }}>
                    <span>Confidence</span><span className="mono">{o.conf.toFixed(2)}</span>
                  </div>
                  <div className="meter" style={{ marginTop: 4 }}><div className="meter-fill teal" style={{ width: o.conf*100+'%' }}/></div>
                </div>
              </div>

              {/* Risk gauge + AI brief */}
              <div style={{ borderLeft: '1px solid var(--border)', paddingLeft: 16 }}>
                <div className="mono" style={{ fontSize: 9.5, color: 'var(--text-4)', letterSpacing: '0.1em', marginBottom: 8 }}>RISK PROFILE</div>
                <svg width="200" height="100" viewBox="0 0 200 100">
                  <path d="M 20 90 A 80 80 0 0 1 180 90" stroke="#1A2330" strokeWidth="10" fill="none"/>
                  <path d="M 20 90 A 80 80 0 0 1 180 90" stroke="url(#riskGrad)" strokeWidth="10" fill="none" strokeDasharray={`${o.score/100 * 251} 251`}/>
                  <defs>
                    <linearGradient id="riskGrad">
                      <stop offset="0" stopColor="#14B8A6"/>
                      <stop offset="0.5" stopColor="#F59E0B"/>
                      <stop offset="1" stopColor="#F87171"/>
                    </linearGradient>
                  </defs>
                  <text x="100" y="78" textAnchor="middle" fontSize="22" fontFamily="JetBrains Mono" fontWeight="600" fill="#E6EAF2">{o.score}</text>
                  <text x="100" y="93" textAnchor="middle" fontSize="8" letterSpacing="2" fill="#6B7588" fontFamily="JetBrains Mono">RISK-ADJ SCORE</text>
                </svg>
                <div style={{ background: 'rgba(139,92,246,0.06)', border: '1px solid rgba(139,92,246,0.2)', padding: '8px 10px', borderRadius: 4, marginTop: 8 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                    <Icon.Sparkles size={11} /> <span className="mono" style={{ fontSize: 9.5, letterSpacing: '0.1em', color: 'var(--violet)' }}>AI BRIEF</span>
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-2)', lineHeight: 1.5 }}>
                    {o.sym === 'BTC' && 'Setup confluence is strong. Watch PCE for invalidation; soft print is the asymmetric catalyst.'}
                    {o.sym === 'SOL' && 'High beta to BTC; size accordingly. ETF delay is binary risk on July 17.'}
                    {o.sym === 'ETH' && 'Mean-reversion thesis. Tight stop required given range-bound action.'}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 6, marginTop: 10 }}>
                  <button className="btn primary"><Icon.Send size={11}/> Publish</button>
                  <button className="btn"><Icon.Pen size={11}/> Edit</button>
                </div>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
window.OppsScreen = OppsScreen;
