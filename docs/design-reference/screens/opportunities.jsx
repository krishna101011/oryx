function OppsScreen() {
  const opps = [
    { rank: 1, sym: 'BTC',  th: 'ETF inflows reaccelerating after 3-day pause; funding flipped positive across major perps. Whale outflow from Coinbase confirms accumulation thesis.',
      score: 84, conf: 0.91, tf: '1D', cats: ['ETF flows','Funding','On-chain'] },
    { rank: 2, sym: 'SOL',  th: 'Token unlock priced in over past 2 weeks. DEX volume uptrend, Solana mobile shipments signal real adoption. Risk: SEC ETF delay.',
      score: 78, conf: 0.84, tf: '4H', cats: ['Unlocks','Adoption','ETF'] },
    { rank: 3, sym: 'ETH',  th: 'Lagging BTC by ~12% YTD despite ETF approval. Rotation thesis intact; staking yield + ETH/BTC bottoming pattern.',
      score: 71, conf: 0.79, tf: '1D', cats: ['Rotation','ETF','Staking'] },
  ];

  return (
    <div className="section">
      <div className="grid g-4" style={{ marginBottom: 12 }}>
        <Kpi label="Open opportunities" val="3" delta="+1 this week" deltaPos />
        <Kpi label="Avg activity score" val="77.7"  delta="+4.2 vs last batch" deltaPos />
        <Kpi label="New signals · 7d"   val="12" delta="+3 vs prior week" deltaPos />
        <Kpi label="Sources per signal · avg" val="6.2" delta="+0.8 vs prior" deltaPos />
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {opps.map(o => (
          <Card key={o.sym} title={o.sym} sub={o.tf} right={<>
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

              {/* Signal strength — informational only: how much independent
                  activity was detected, and how confident the sourcing is.
                  No price levels — this is not a trade setup. */}
              <div style={{ borderLeft: '1px solid var(--border)', paddingLeft: 16 }}>
                <div className="mono" style={{ fontSize: 9.5, color: 'var(--text-4)', letterSpacing: '0.1em', marginBottom: 8 }}>SIGNAL STRENGTH</div>
                <div style={{ fontSize: 11 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-3)' }}>
                    <span>Notable-activity score</span><span className="mono">{o.score}/100</span>
                  </div>
                  <div className="meter" style={{ marginTop: 4 }}><div className="meter-fill" style={{ width: o.score+'%' }}/></div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-3)', marginTop: 8 }}>
                    <span>Confidence</span><span className="mono">{o.conf.toFixed(2)}</span>
                  </div>
                  <div className="meter" style={{ marginTop: 4 }}><div className="meter-fill teal" style={{ width: o.conf*100+'%' }}/></div>
                </div>
              </div>

              {/* Activity gauge + AI brief — informational framing only:
                  what's notable and what would change the read, never a
                  position size, stop level, or other trade instruction. */}
              <div style={{ borderLeft: '1px solid var(--border)', paddingLeft: 16 }}>
                <div className="mono" style={{ fontSize: 9.5, color: 'var(--text-4)', letterSpacing: '0.1em', marginBottom: 8 }}>ACTIVITY SIGNAL</div>
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
                  <text x="100" y="93" textAnchor="middle" fontSize="8" letterSpacing="2" fill="#6B7588" fontFamily="JetBrains Mono">ACTIVITY SCORE</text>
                </svg>
                <div style={{ background: 'rgba(139,92,246,0.06)', border: '1px solid rgba(139,92,246,0.2)', padding: '8px 10px', borderRadius: 4, marginTop: 8 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                    <Icon.Sparkles size={11} /> <span className="mono" style={{ fontSize: 9.5, letterSpacing: '0.1em', color: 'var(--violet)' }}>AI BRIEF</span>
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-2)', lineHeight: 1.5 }}>
                    {o.sym === 'BTC' && 'Multiple independent signals point the same way on BTC — ETF flows, funding rates, and on-chain activity all shifted together. The PCE print is the data point most likely to change this read.'}
                    {o.sym === 'SOL' && "Price tends to move more than BTC's, in both directions. The ETF decision on July 17 is the binary event to watch."}
                    {o.sym === 'ETH' && 'ETH has lagged BTC on a rolling basis despite similar catalysts, and price has stayed range-bound recently.'}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 6, marginTop: 10 }}>
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
