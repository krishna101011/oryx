function NewsScreen() {
  const [topic, setTopic] = React.useState('All');
  const topics = ['All', 'Macro', 'Crypto', 'Equities', 'Earnings', 'Policy', 'On-chain', 'Energy'];
  const sources = [
    { name: 'Bloomberg Terminal', n: 38, trust: 96, ic: 'B' },
    { name: 'Reuters',            n: 22, trust: 94, ic: 'R' },
    { name: 'FT',                 n: 14, trust: 93, ic: 'F' },
    { name: 'WSJ',                n: 11, trust: 92, ic: 'W' },
    { name: 'Coindesk',           n: 18, trust: 78, ic: 'C' },
    { name: 'The Block',          n: 9,  trust: 82, ic: 'T' },
    { name: 'EDGAR (SEC)',        n: 6,  trust: 100,ic: 'S' },
    { name: 'Fed press',          n: 3,  trust: 100,ic: 'F' },
    { name: 'Glassnode',          n: 12, trust: 88, ic: 'G' },
    { name: 'CryptoQuant',        n: 7,  trust: 84, ic: 'Q' },
  ];

  const news = [
    { tag: 'CRYPTO', src: 'Bloomberg', t: '07:42', title: 'BlackRock IBIT records $378M inflow as BTC retakes $64K',
      summary: 'Spot Bitcoin ETF complex sees net positive flow for first time in four sessions; IBIT alone accounted for 64% of net inflow, while GBTC continued to bleed at slower pace.',
      claims: 4, verified: 3, conflicts: 0, trust: 'HIGH' },
    { tag: 'MACRO', src: 'Reuters', t: '07:31', title: 'Eurozone June flash CPI prints 2.5% vs 2.6% expected',
      summary: 'Core HICP at 2.9%, services at 4.1%. ECB chief economist Lane signals data-dependence; markets price 78% odds of July hold.',
      claims: 6, verified: 6, conflicts: 0, trust: 'HIGH' },
    { tag: 'EARNINGS', src: 'WSJ', t: '07:18', title: 'Nvidia data-center revenue tops $26B but China outlook softens',
      summary: 'CFO Kress flags H20 demand uncertainty into 2H; Hopper transition to Blackwell on track for Q3 ramp. Stock indicated +2% in pre-market.',
      claims: 8, verified: 5, conflicts: 1, trust: 'MED' },
    { tag: 'POLICY', src: 'EDGAR', t: '06:55', title: 'SEC delays decision on spot SOL ETF — 19b-4 amendment posted',
      summary: 'New decision deadline July 17. VanEck and 21Shares filings remain active. No formal staff comment on commodity classification.',
      claims: 3, verified: 3, conflicts: 0, trust: 'HIGH' },
    { tag: 'CRYPTO', src: 'The Block', t: '06:41', title: 'Coinbase whale withdraws 4,800 BTC to cold storage',
      summary: 'On-chain attribution links cluster to institutional desk. Withdrawal coincides with funding rate flip across major perps venues.',
      claims: 2, verified: 1, conflicts: 1, trust: 'MED' },
    { tag: 'ON-CHAIN', src: 'Glassnode', t: '06:30', title: 'LTH supply reaches all-time high of 14.91M BTC',
      summary: 'Long-term holder cohort accumulating despite cycle-high prices; signals conviction rather than distribution per Glassnode model.',
      claims: 3, verified: 3, conflicts: 0, trust: 'HIGH' },
    { tag: 'MACRO', src: 'FT', t: '06:12', title: 'Japan MoF intervenes in FX as USDJPY tests 162',
      summary: 'Treasury official confirms BoJ-coordinated dollar selling of $35B equivalent over 24h. USDJPY now trading 158.4.',
      claims: 5, verified: 4, conflicts: 0, trust: 'HIGH' },
    { tag: 'EARNINGS', src: 'Bloomberg', t: '05:58', title: 'Micron beats on revenue, guides ahead on AI memory mix',
      summary: 'HBM3E ramp pulled forward to Q4; data-center DRAM bit growth +30% q/q. Margin guide implies pricing power across DDR5.',
      claims: 4, verified: 4, conflicts: 0, trust: 'HIGH' },
  ];

  return (
    <div className="section">
      <div style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
        <div className="tab-row">
          {topics.map(t => <div key={t} className={"tab" + (t === topic ? " active" : "")} onClick={() => setTopic(t)}>{t}</div>)}
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
          <button className="btn"><Icon.Filter size={11}/> Filters · 3</button>
          <button className="btn"><Icon.Calendar size={11}/> Last 24h</button>
          <button className="btn primary"><Icon.Plus size={11}/> Save view</button>
        </div>
      </div>

      <div className="grid" style={{ gridTemplateColumns: '220px 1fr 280px', gap: 12 }}>
        {/* Source rail */}
        <Card title="Sources" sub="140 ITEMS" noPad>
          <div style={{ padding: '4px 0' }}>
            {sources.map(s => (
              <div key={s.name} style={{ display: 'flex', alignItems: 'center', gap: 9, padding: '7px 10px', borderBottom: '1px solid var(--hairline)', cursor: 'pointer' }}>
                <div style={{ width: 22, height: 22, borderRadius: 4, background: 'var(--elev-2)', border: '1px solid var(--border)', display: 'grid', placeItems: 'center', fontSize: 10, fontWeight: 600, fontFamily: 'var(--font-mono)' }}>{s.ic}</div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 11.5, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.name}</div>
                  <div className="mono" style={{ fontSize: 9.5, color: 'var(--text-4)' }}>{s.n} · trust {s.trust}</div>
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* News feed */}
        <Card title="Verified feed" sub="142 ITEMS · 96% AUTO-VERIFIED" right={<><span className="chip teal dot">LIVE</span></>} noPad>
          <div>
            {news.map((n, i) => (
              <div key={i} style={{ padding: '12px 14px', borderBottom: '1px solid var(--hairline)', cursor: 'pointer' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                  <span className="chip indigo">{n.tag}</span>
                  <span className="mono" style={{ fontSize: 10, color: 'var(--text-3)' }}>{n.src} · {n.t}</span>
                  <span style={{ marginLeft: 'auto', display: 'flex', gap: 4 }}>
                    <span className="chip teal dot">VERIFIED {n.verified}/{n.claims}</span>
                    {n.conflicts > 0 && <span className="chip warn">CONFLICT {n.conflicts}</span>}
                  </span>
                </div>
                <div style={{ fontSize: 13.5, fontWeight: 500, color: 'var(--text)', marginBottom: 4, letterSpacing: '-0.005em' }}>{n.title}</div>
                <div style={{ fontSize: 11.5, color: 'var(--text-2)', lineHeight: 1.5 }}>{n.summary}</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 8 }}>
                  <button className="btn ghost" style={{ fontSize: 10.5, padding: '3px 7px' }}><Icon.Shield size={10}/> Verify</button>
                  <button className="btn ghost" style={{ fontSize: 10.5, padding: '3px 7px' }}><Icon.Beaker size={10}/> Add to packet</button>
                  <button className="btn ghost" style={{ fontSize: 10.5, padding: '3px 7px' }}><Icon.Pen size={10}/> Draft</button>
                  <span style={{ marginLeft: 'auto' }} className="mono"><span className="muted" style={{ fontSize: 10 }}>Confidence</span> <span style={{ fontSize: 11 }}>{(0.7 + Math.random()*0.25).toFixed(2)}</span></span>
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Right rail */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <Card title="Trending topics" sub="LAST 24H">
            {[
              { name: 'BTC ETF flows',    n: 38, d: '+128%' },
              { name: 'PCE inflation',    n: 21, d: '+62%' },
              { name: 'NVDA earnings',    n: 19, d: '+44%' },
              { name: 'SOL ETF delay',    n: 12, d: '+220%' },
              { name: 'JPY intervention', n: 11, d: '+82%' },
              { name: 'AI capex',         n: 9,  d: '+30%' },
            ].map((t, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 0', borderBottom: i < 5 ? '1px solid var(--hairline)' : 'none' }}>
                <span style={{ width: 18, color: 'var(--text-4)', fontFamily: 'var(--font-mono)', fontSize: 10 }}>{(i+1).toString().padStart(2,'0')}</span>
                <span style={{ flex: 1, fontSize: 11.5 }}>{t.name}</span>
                <span className="mono" style={{ fontSize: 10, color: 'var(--text-3)' }}>{t.n}</span>
                <span className="mono pos" style={{ fontSize: 10, width: 50, textAlign: 'right' }}>{t.d}</span>
              </div>
            ))}
          </Card>

          <Card title="Conflict watch" sub="MULTI-SOURCE">
            <div style={{ padding: 2 }}>
              <div className="chip warn" style={{ marginBottom: 6 }}>1 ACTIVE CONFLICT</div>
              <div style={{ fontSize: 11.5, color: 'var(--text)' }}>
                Coinbase whale withdrawal: <span className="muted-2">attribution split between Cumberland (The Block) vs Galaxy (Arkham)</span>
              </div>
              <button className="btn" style={{ marginTop: 8, fontSize: 10.5 }}><Icon.Shield size={10}/> Open in Verification</button>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
window.NewsScreen = NewsScreen;
