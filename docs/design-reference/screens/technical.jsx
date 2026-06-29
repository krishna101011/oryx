function TechnicalScreen() {
  const [tf, setTf] = React.useState('1H');
  const [layout, setLayout] = React.useState('Single');
  const candles = window.btcCandles(72, 63800);
  const last = candles[candles.length-1];

  const indicators = [
    { name: 'EMA 9',  val: '64,142', col: '#60A5FA' },
    { name: 'EMA 21', val: '63,892', col: '#A855F7' },
    { name: 'EMA 50', val: '63,418', col: '#F59E0B' },
    { name: 'VWAP',   val: '64,041', col: '#14B8A6' },
    { name: 'BB(20,2)', val: '63,200 / 64,800', col: '#6B7588' },
  ];

  const tools = [
    { ic: 'Plus', label: 'Cursor' },
    { ic: 'Pen',  label: 'Trend' },
    { ic: 'Filter', label: 'Fib' },
    { ic: 'Target', label: 'Pos' },
    { ic: 'Flag', label: 'Note' },
    { ic: 'Code', label: 'Box' },
  ];

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '44px 1fr 280px', height: 'calc(100vh - 44px)' }}>
      {/* Drawing tool rail */}
      <div style={{ background: 'var(--panel)', borderRight: '1px solid var(--border)', display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '8px 0', gap: 4 }}>
        {tools.map((t, i) => {
          const I = Icon[t.ic];
          return <div key={i} className="icon-btn" title={t.label} style={{ width: 32, height: 32 }}><I size={14}/></div>;
        })}
        <div style={{ width: 24, height: 1, background: 'var(--border)', margin: '6px 0' }} />
        <div className="icon-btn" style={{ width: 32, height: 32 }} title="Layers"><Icon.Layers size={14}/></div>
        <div className="icon-btn" style={{ width: 32, height: 32 }} title="Settings"><Icon.Cog size={14}/></div>
      </div>

      {/* Chart area */}
      <div style={{ display: 'flex', flexDirection: 'column', background: 'var(--bg)' }}>
        {/* Chart header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '8px 12px', borderBottom: '1px solid var(--border)' }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
            <span style={{ fontSize: 16, fontWeight: 600 }} className="mono">BTC/USD</span>
            <span style={{ fontSize: 10, color: 'var(--text-3)' }}>· Coinbase · spot</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }} className="mono">
            <span style={{ fontSize: 18, color: last.c >= last.o ? 'var(--teal)' : 'var(--neg)' }}>{last.c.toFixed(2)}</span>
            <span style={{ fontSize: 11, color: last.c >= last.o ? 'var(--teal)' : 'var(--neg)' }}>+1,142.40 (+1.84%)</span>
          </div>
          <div className="tab-row" style={{ marginLeft: 'auto' }}>
            {['1m','5m','15m','1H','4H','1D','1W'].map(t => <div key={t} className={"tab" + (t === tf ? ' active' : '')} onClick={() => setTf(t)}>{t}</div>)}
          </div>
          <div className="tab-row">
            {['Single','Split','Quad','+ News'].map(l => <div key={l} className={"tab" + (l === layout ? ' active' : '')} onClick={() => setLayout(l)}>{l}</div>)}
          </div>
        </div>

        {/* Indicator bar */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, padding: '6px 12px', borderBottom: '1px solid var(--border)', background: 'var(--panel)' }}>
          {indicators.map(ind => (
            <div key={ind.name} style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 10.5 }} className="mono">
              <span style={{ width: 8, height: 2, background: ind.col }}/>
              <span style={{ color: 'var(--text-3)' }}>{ind.name}</span>
              <span style={{ color: 'var(--text)' }}>{ind.val}</span>
            </div>
          ))}
          <button className="btn ghost" style={{ marginLeft: 'auto', fontSize: 10 }}><Icon.Plus size={10}/> Indicator</button>
        </div>

        {/* Chart canvas */}
        <div style={{ flex: 1, overflow: 'auto', position: 'relative', background: 'radial-gradient(ellipse at center, rgba(139,92,246,0.03), transparent 70%)' }}>
          <Candles data={candles} width={1000} height={460} />
          {/* RSI subchart */}
          <div style={{ padding: '0 12px 4px', borderTop: '1px solid var(--border)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '6px 0' }}>
              <span className="mono" style={{ fontSize: 10.5, color: 'var(--text-3)' }}>RSI(14)</span>
              <span className="mono" style={{ fontSize: 11, color: 'var(--text)' }}>58.4</span>
              <span className="chip">Neutral</span>
            </div>
            <svg viewBox="0 0 1000 80" width="100%" height="80">
              <line x1="0" x2="1000" y1="20" y2="20" stroke="#1A2330" strokeDasharray="2 4"/>
              <line x1="0" x2="1000" y1="40" y2="40" stroke="#1A2330" strokeDasharray="2 4"/>
              <line x1="0" x2="1000" y1="60" y2="60" stroke="#1A2330" strokeDasharray="2 4"/>
              <text x="4" y="22" fontSize="9" fill="#4A5263" fontFamily="JetBrains Mono">70</text>
              <text x="4" y="42" fontSize="9" fill="#4A5263" fontFamily="JetBrains Mono">50</text>
              <text x="4" y="62" fontSize="9" fill="#4A5263" fontFamily="JetBrains Mono">30</text>
              <polyline points={walk('rsi', 72, 0.1).map((v,i) => `${(i/71)*990+5},${80 - v*60 - 10}`).join(' ')} fill="none" stroke="#A855F7" strokeWidth="1.2"/>
            </svg>
          </div>
        </div>

        {/* Bottom drawing meta */}
        <div style={{ borderTop: '1px solid var(--border)', padding: '4px 12px', display: 'flex', gap: 14, alignItems: 'center', fontSize: 10, color: 'var(--text-4)' }} className="mono">
          <span>5 OBJECTS</span><span>·</span><span>1 ALERT</span><span>·</span><span>SNAPSHOT 14m ago</span>
          <span style={{ marginLeft: 'auto' }}>POS · LONG 0.5 BTC · entry 63,418 · pnl +400 (+1.26%)</span>
        </div>
      </div>

      {/* Right rail */}
      <div style={{ borderLeft: '1px solid var(--border)', overflow: 'auto', background: 'var(--bg)' }}>
        <div style={{ padding: 10 }}>
          <Card title="Watchlist" sub="DEFAULT" noPad>
            <table className="tbl">
              <thead><tr><th>Sym</th><th className="num">Last</th><th className="num">Chg%</th></tr></thead>
              <tbody>
                {[
                  ['BTC', '64,218', '+1.84', true],
                  ['ETH', '3,142',  '+0.42', true],
                  ['SOL', '142.18', '+3.21', true],
                  ['BNB', '589.4',  '-0.14', false],
                  ['DOGE','0.1318', '+2.04', true],
                  ['XRP', '0.4912', '-0.22', false],
                  ['LINK','14.82',  '+1.11', true],
                  ['AVAX','27.91',  '+2.42', true],
                  ['MATIC','0.586', '-0.84', false],
                  ['ADA', '0.387',  '-0.41', false],
                ].map((r, i) => (
                  <tr key={i} style={r[0]==='BTC' ? { background: 'rgba(139,92,246,0.05)' } : null}>
                    <td className="sym">{r[0]}</td>
                    <td className="num">{r[1]}</td>
                    <td className={"num " + (r[3] ? 'pos' : 'neg')}>{r[2]}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </div>
        <div style={{ padding: '0 10px 10px' }}>
          <Card title="Order book" sub="L2 · LIVE" noPad>
            <div style={{ padding: '8px 10px' }}>
              {[...Array(7)].map((_, i) => {
                const px = (64218 + (7-i)*8).toLocaleString();
                const sz = (Math.random()*4+0.2).toFixed(3);
                return (
                  <div key={'a'+i} style={{ display: 'flex', fontFamily: 'var(--font-mono)', fontSize: 10.5, justifyContent: 'space-between', padding: '1px 0', position: 'relative' }}>
                    <div style={{ position: 'absolute', right: 0, top: 0, bottom: 0, background: 'rgba(248,113,113,0.08)', width: (Math.random()*60+10)+'%' }}/>
                    <span style={{ color: 'var(--neg)', zIndex: 1 }}>{px}</span>
                    <span style={{ zIndex: 1 }}>{sz}</span>
                  </div>
                );
              })}
              <div style={{ textAlign: 'center', padding: '4px 0', borderTop: '1px solid var(--border)', borderBottom: '1px solid var(--border)', margin: '4px 0' }} className="mono">
                <span style={{ color: 'var(--teal)' }}>64,218.40</span> <span style={{ color: 'var(--text-4)', fontSize: 9 }}>SPREAD 0.40 (0.0006%)</span>
              </div>
              {[...Array(7)].map((_, i) => {
                const px = (64210 - i*8).toLocaleString();
                const sz = (Math.random()*4+0.2).toFixed(3);
                return (
                  <div key={'b'+i} style={{ display: 'flex', fontFamily: 'var(--font-mono)', fontSize: 10.5, justifyContent: 'space-between', padding: '1px 0', position: 'relative' }}>
                    <div style={{ position: 'absolute', right: 0, top: 0, bottom: 0, background: 'rgba(20,184,166,0.08)', width: (Math.random()*60+10)+'%' }}/>
                    <span style={{ color: 'var(--teal)', zIndex: 1 }}>{px}</span>
                    <span style={{ zIndex: 1 }}>{sz}</span>
                  </div>
                );
              })}
            </div>
          </Card>
        </div>
        <div style={{ padding: '0 10px 10px' }}>
          <Card title="Linked claims" sub="VERIFIED" noPad>
            {[
              { t: 'ETF inflows +$378M',     c: 0.92 },
              { t: 'Funding flipped positive', c: 0.88 },
              { t: '4,800 BTC off Coinbase', c: 0.74 },
              { t: 'LTH supply ATH',          c: 0.91 },
            ].map((c, i) => (
              <div key={i} style={{ padding: '7px 10px', borderBottom: i < 3 ? '1px solid var(--hairline)' : 'none' }}>
                <div style={{ fontSize: 11.5 }}>{c.t}</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 4 }}>
                  <div className="meter" style={{ flex: 1, height: 3 }}><div className="meter-fill teal" style={{ width: c.c*100+'%' }}/></div>
                  <span className="mono" style={{ fontSize: 9.5, color: 'var(--text-3)' }}>{c.c.toFixed(2)}</span>
                </div>
              </div>
            ))}
          </Card>
        </div>
      </div>
    </div>
  );
}
window.TechnicalScreen = TechnicalScreen;
