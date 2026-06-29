function TerminalScreen() {
  // Heatmap data
  const heatSectors = [
    { name: 'AI / Semis',   items: [['NVDA',+3.1,1900],['AMD',+2.4,290],['AVGO',+1.8,650],['ASML',+0.4,380],['TSM',+1.1,720],['MU',+4.2,140]] },
    { name: 'Mega tech',    items: [['AAPL',-0.4,3100],['MSFT',+0.6,3200],['GOOGL',+0.2,2100],['META',+1.4,1240],['AMZN',-0.3,1900]] },
    { name: 'Crypto',       items: [['BTC',+1.84,1270],['ETH',+0.42,378],['SOL',+3.21,64],['BNB',-0.14,86],['XRP',-0.22,28]] },
    { name: 'Energy',       items: [['XOM',-1.2,510],['CVX',-0.8,300],['COP',-1.6,150]] },
    { name: 'Financials',   items: [['JPM',+0.2,580],['BAC',-0.1,290],['WFC',+0.6,220]] },
    { name: 'Defensive',    items: [['JNJ',+0.4,380],['PG',+0.1,420],['KO',-0.2,270]] },
  ];

  const heatColor = (v) => {
    const a = Math.min(1, Math.abs(v) / 4);
    if (v >= 0) return `rgba(20,184,166,${0.15 + a*0.65})`;
    return `rgba(248,113,113,${0.15 + a*0.65})`;
  };

  // Stock screener results
  const screenerRows = [
    ['BTC',   'Bitcoin',          '64,218.40', +1.84, '38.2B', '1.27T',  72, 'BUY'],
    ['ETH',   'Ethereum',         '3,142.20',  +0.42, '12.4B', '378B',   58, 'HOLD'],
    ['SOL',   'Solana',           '142.18',    +3.21, '2.10B', '64B',    81, 'STRONG'],
    ['NVDA',  'NVIDIA',           '128.42',    +3.10, '52.8B', '3.15T',  79, 'STRONG'],
    ['AVGO',  'Broadcom',         '1,734.20',  +1.80, '4.20B', '650B',   71, 'BUY'],
    ['MU',    'Micron',           '128.40',    +4.20, '3.80B', '140B',   84, 'STRONG'],
    ['META',  'Meta Platforms',   '498.40',    +1.40, '8.40B', '1.24T',  74, 'BUY'],
    ['MSTR',  'MicroStrategy',    '1,468.20',  +5.20, '780M',  '25B',    88, 'STRONG'],
  ];

  const calEcon = [
    { t: '08:30', region: 'US', evt: 'Core PCE Price Index MoM', imp: 'HIGH', fc: '+0.2%', prv: '+0.3%' },
    { t: '08:30', region: 'US', evt: 'Personal Spending',         imp: 'MED',  fc: '+0.3%', prv: '+0.2%' },
    { t: '10:00', region: 'US', evt: 'UMich Consumer Sentiment Final', imp: 'MED', fc: '65.8', prv: '69.1' },
    { t: '13:00', region: 'US', evt: 'Fed Williams speaks',       imp: 'MED',  fc: '—',     prv: '—' },
    { t: '15:00', region: 'EU', evt: 'ECB de Guindos speaks',     imp: 'LOW',  fc: '—',     prv: '—' },
  ];

  const calEarn = [
    { sym: 'NKE',  name: 'Nike',         when: 'AMC', eps: '$0.83', rev: '$12.85B', sz: 'mega' },
    { sym: 'WBA',  name: 'Walgreens',    when: 'BMO', eps: '$0.64', rev: '$36.0B',  sz: 'large' },
    { sym: 'MKC',  name: 'McCormick',    when: 'BMO', eps: '$0.58', rev: '$1.61B',  sz: 'mid' },
    { sym: 'KMX',  name: 'CarMax',       when: 'BMO', eps: '$0.94', rev: '$7.10B',  sz: 'mid' },
    { sym: 'GIS',  name: 'General Mills',when: 'BMO', eps: '$1.00', rev: '$4.86B',  sz: 'large' },
  ];

  return (
    <div className="section">
      <div className="grid" style={{ gridTemplateColumns: '1.4fr 1fr', gap: 12 }}>
        {/* Heatmap */}
        <Card title="Market heatmap" sub="MARKET CAP WEIGHTED · 24H" right={<>
          <span className="chip">1H</span><span className="chip teal">24H</span><span className="chip">7D</span>
        </>}>
          <div style={{ display: 'grid', gridTemplateColumns: '1.6fr 1.3fr 1fr', gap: 4 }}>
            {heatSectors.slice(0,3).map(s => (
              <div key={s.name}>
                <div className="mono" style={{ fontSize: 9.5, color: 'var(--text-4)', letterSpacing: '0.1em', textTransform: 'uppercase', padding: '0 0 4px' }}>{s.name}</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  {s.items.map(it => (
                    <div key={it[0]} className="heat-cell" style={{ background: heatColor(it[1]), height: 40 + (it[2]/40) }}>
                      <div style={{ fontWeight: 700, fontSize: 11 }}>{it[0]}</div>
                      <div style={{ fontSize: 10 }}>{it[1] >= 0 ? '+' : ''}{it[1].toFixed(2)}%</div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 4, marginTop: 10 }}>
            {heatSectors.slice(3).map(s => (
              <div key={s.name}>
                <div className="mono" style={{ fontSize: 9.5, color: 'var(--text-4)', letterSpacing: '0.1em', textTransform: 'uppercase', padding: '0 0 4px' }}>{s.name}</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  {s.items.map(it => (
                    <div key={it[0]} className="heat-cell" style={{ background: heatColor(it[1]), height: 32 }}>
                      <div style={{ fontWeight: 700, fontSize: 10.5 }}>{it[0]}</div>
                      <div style={{ fontSize: 9.5 }}>{it[1] >= 0 ? '+' : ''}{it[1].toFixed(2)}%</div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Economic calendar */}
        <Card title="Economic calendar" sub="TODAY · JUN 28" right={<button className="btn ghost" style={{ fontSize: 10 }}>Week →</button>} noPad>
          <table className="tbl">
            <thead><tr><th style={{ width: 60 }}>Time</th><th>Region</th><th>Event</th><th>Imp.</th><th className="num">Forecast</th><th className="num">Prior</th></tr></thead>
            <tbody>
              {calEcon.map((e, i) => (
                <tr key={i}>
                  <td className="mono">{e.t}</td>
                  <td><span className="chip" style={{ fontSize: 9 }}>{e.region}</span></td>
                  <td>{e.evt}</td>
                  <td><span className={"chip " + (e.imp === 'HIGH' ? 'neg' : e.imp === 'MED' ? 'warn' : '')} style={{ fontSize: 9 }}>{e.imp}</span></td>
                  <td className="num">{e.fc}</td>
                  <td className="num muted">{e.prv}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>

      {/* Screener */}
      <div style={{ marginTop: 12 }}>
        <Card title="Screener · BTC ecosystem + AI Semis" sub="8 RESULTS · SAVED VIEW" right={<>
          <button className="btn ghost" style={{ fontSize: 10 }}><Icon.Filter size={10}/> 4 filters</button>
          <button className="btn ghost" style={{ fontSize: 10 }}>Export</button>
        </>} noPad>
          <table className="tbl">
            <thead><tr>
              <th>Symbol</th><th>Name</th><th className="num">Last</th><th className="num">Chg</th>
              <th className="num">Vol 24h</th><th className="num">Mcap</th>
              <th>ORYX score</th><th>Sig</th><th>1D</th>
            </tr></thead>
            <tbody>
              {screenerRows.map((r, i) => (
                <tr key={i}>
                  <td className="sym">{r[0]}</td>
                  <td className="muted-2">{r[1]}</td>
                  <td className="num">{r[2]}</td>
                  <td className={"num " + (r[3] >= 0 ? 'pos' : 'neg')}>{r[3] >= 0 ? '+' : ''}{r[3].toFixed(2)}%</td>
                  <td className="num muted">{r[4]}</td>
                  <td className="num muted">{r[5]}</td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <div className="meter" style={{ width: 70 }}><div className="meter-fill" style={{ width: r[6]+'%' }}/></div>
                      <span className="mono" style={{ fontSize: 10 }}>{r[6]}</span>
                    </div>
                  </td>
                  <td><span className={"chip " + (r[7] === 'STRONG' ? 'teal' : r[7] === 'BUY' ? 'indigo' : '')} style={{ fontSize: 9 }}>{r[7]}</span></td>
                  <td><Spark data={walk('scr-'+r[0], 24, 0.1, r[3] > 0 ? 0.006 : -0.005)} pos={r[3] > 0} width={70}/></td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>

      {/* Earnings calendar + global cal */}
      <div className="grid g-2" style={{ marginTop: 12 }}>
        <Card title="Earnings this week" sub="14 REPORTS · 5 TODAY" noPad>
          <table className="tbl">
            <thead><tr><th>Sym</th><th>Company</th><th>When</th><th className="num">EPS est.</th><th className="num">Rev est.</th></tr></thead>
            <tbody>
              {calEarn.map(e => (
                <tr key={e.sym}>
                  <td className="sym">{e.sym}</td>
                  <td className="muted-2">{e.name}</td>
                  <td><span className="chip" style={{ fontSize: 9 }}>{e.when}</span></td>
                  <td className="num">{e.eps}</td>
                  <td className="num">{e.rev}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>

        <Card title="Calendar · June 2026">
          <div className="cal">
            {['MON','TUE','WED','THU','FRI','SAT','SUN'].map(d => <div key={d} className="mono" style={{ fontSize: 9, color: 'var(--text-4)', padding: 4, letterSpacing: '0.1em' }}>{d}</div>)}
            {Array.from({length: 30}).map((_, i) => {
              const n = i + 1;
              const today = n === 28;
              const evt = [3,7,11,17,22,25,28].includes(n);
              return (
                <div key={i} className={"day" + (today ? ' today' : '')}>
                  <div className="n">{n.toString().padStart(2,'0')}</div>
                  {evt && <div className="event">{n===28 ? 'PCE' : n===17 ? 'CPI' : n===11 ? 'FOMC' : 'Econ'}</div>}
                </div>
              );
            })}
          </div>
        </Card>
      </div>
    </div>
  );
}
window.TerminalScreen = TerminalScreen;
