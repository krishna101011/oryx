function PublishScreen() {
  const channels = [
    { name: 'Substack',  hand: 'anantcapital', sub: '12,840', state: 'connected', col: '#FF6719' },
    { name: 'X',         hand: '@anantcap',    sub: '38,210', state: 'connected', col: '#fff'    },
    { name: 'LinkedIn',  hand: 'ORYX Editorial',sub: '4,210',  state: 'connected', col: '#0a66c2' },
    { name: 'YouTube',   hand: '@anantcap',    sub: '11,800', state: 'connected', col: '#ff0000' },
    { name: 'Threads',   hand: '@anantcap',    sub: '2,140',  state: 'paused',    col: '#fff'    },
    { name: 'RSS feed',  hand: '/feed.xml',    sub: '—',      state: 'connected', col: '#F26522' },
  ];

  const history = [
    { t: 'Jun 27 09:30', title: 'Pre-market notes — Fed Williams speech',          ch: 'Substack', opens: '8.2K', ctr: '4.2%', conv: '12'  },
    { t: 'Jun 27 08:14', title: 'NVDA at $135 — is the run over?',                  ch: 'X',        opens: '142K (imp)', ctr: '2.8%', conv: '38' },
    { t: 'Jun 26 17:40', title: 'Weekly recap · Macro + crypto',                     ch: 'Substack', opens: '9.1K', ctr: '5.1%', conv: '21' },
    { t: 'Jun 26 12:00', title: 'Thread: 5 charts the FOMC won\'t show you',         ch: 'X',        opens: '210K (imp)', ctr: '3.4%', conv: '52' },
    { t: 'Jun 25 09:30', title: 'PCE preview · base case is +0.2% MoM',              ch: 'Substack', opens: '7.8K', ctr: '3.9%', conv: '8'  },
    { t: 'Jun 24 16:00', title: 'LinkedIn brief · institutional BTC adoption',       ch: 'LinkedIn', opens: '5.2K', ctr: '2.2%', conv: '4'  },
  ];

  const hours = ['06','07','08','09','10','11','12','13','14','15','16','17'];

  return (
    <div className="section">
      <div className="grid g-4" style={{ marginBottom: 12 }}>
        <Kpi label="Subscribers · Substack" val="12,840" delta="+128 wk" deltaPos sparkData={walk('sub', 24, 0.04, 0.005)} />
        <Kpi label="Avg open rate"          val="46.2%"  delta="+2.1% MoM" deltaPos />
        <Kpi label="Paid conversion"        val="3.4%"   delta="+0.4% MoM" deltaPos />
        <Kpi label="MRR"                    val="$48.2K" delta="+6.8% MoM" deltaPos />
      </div>

      <div className="grid" style={{ gridTemplateColumns: '1fr 320px', gap: 12 }}>
        <Card title="Schedule · Week of Jun 24" sub="6 PUBLISHED · 4 QUEUED" right={<button className="btn primary"><Icon.Plus size={11}/> Schedule</button>}>
          {/* Day strip */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 4, marginBottom: 10 }}>
            {['MON 24','TUE 25','WED 26','THU 27','FRI 28','SAT 29','SUN 30'].map((d, i) => (
              <div key={d} style={{ padding: '6px 8px', background: i === 4 ? 'rgba(139,92,246,0.1)' : 'var(--elev)', border: '1px solid var(--border)', borderRadius: 4 }}>
                <div className="mono" style={{ fontSize: 9.5, color: 'var(--text-4)', letterSpacing: '0.1em' }}>{d.split(' ')[0]}</div>
                <div style={{ fontSize: 14, fontWeight: 600, fontFamily: 'var(--font-mono)' }}>{d.split(' ')[1]}</div>
                <div style={{ fontSize: 10, color: i < 4 ? 'var(--teal)' : 'var(--violet)', marginTop: 3 }} className="mono">{i < 4 ? '2 SENT' : i === 4 ? '4 QUEUED' : i === 5 ? '1 QUEUED' : '—'}</div>
              </div>
            ))}
          </div>

          {/* Hour-grid for Friday */}
          <div className="mono" style={{ fontSize: 9.5, color: 'var(--text-4)', letterSpacing: '0.1em', marginBottom: 6 }}>FRI · JUN 28 · ET</div>
          <div style={{ position: 'relative', background: 'var(--elev)', border: '1px solid var(--border)', borderRadius: 4, padding: '6px 8px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(12, 1fr)', gap: 0 }}>
              {hours.map(h => <div key={h} className="mono" style={{ fontSize: 9, color: 'var(--text-4)', textAlign: 'center', padding: '2px 0', borderLeft: '1px solid var(--hairline)' }}>{h}</div>)}
            </div>
            <div style={{ position: 'relative', height: 80, marginTop: 4 }}>
              {[
                { l: 8, w: 12, ch: 'Substack', t: 'Daily Brief — BTC ETF flows', col: '#FF6719', row: 0, stat: 'queued' },
                { l: 8, w: 6,  ch: 'X',        t: 'Thread · ETF flows + funding flip', col: '#fff', row: 1, stat: 'queued' },
                { l: 18,w: 8,  ch: 'X',        t: 'Chart post · PCE preview', col: '#fff', row: 1, stat: 'queued' },
                { l: 36,w: 14, ch: 'LinkedIn', t: 'NVDA Q1 teardown · part 1', col: '#0a66c2', row: 2, stat: 'review' },
                { l: 36,w: 18, ch: 'Substack', t: 'NVDA Q1 teardown · part 1', col: '#FF6719', row: 0, stat: 'review' },
              ].map((b, i) => (
                <div key={i} style={{
                  position: 'absolute', left: b.l*8.33 + '%', width: b.w*8.33 + '%',
                  top: b.row * 26, height: 22,
                  background: `linear-gradient(90deg, ${b.col}22, ${b.col}10)`,
                  borderLeft: `3px solid ${b.col}`, borderRadius: 3, padding: '2px 6px',
                  fontSize: 10.5, color: 'var(--text)', overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis', display: 'flex', alignItems: 'center', gap: 6
                }}>
                  <span className="mono" style={{ fontSize: 9, opacity: 0.7 }}>{b.ch}</span>
                  <span>{b.t}</span>
                  <span style={{ marginLeft: 'auto' }} className={"chip " + (b.stat === 'queued' ? 'teal' : 'warn')}>{b.stat}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Post history */}
          <div className="mono" style={{ fontSize: 9.5, color: 'var(--text-4)', letterSpacing: '0.1em', marginTop: 20, marginBottom: 6 }}>POST HISTORY · LAST 7 DAYS</div>
          <table className="tbl">
            <thead><tr><th>Time</th><th>Title</th><th>Channel</th><th className="num">Opens</th><th className="num">CTR</th><th className="num">Conv.</th></tr></thead>
            <tbody>
              {history.map((h, i) => (
                <tr key={i}>
                  <td className="mono">{h.t}</td>
                  <td style={{ color: 'var(--text)' }}>{h.title}</td>
                  <td><span className="chip" style={{ fontSize: 9 }}>{h.ch}</span></td>
                  <td className="num">{h.opens}</td>
                  <td className="num">{h.ctr}</td>
                  <td className="num pos">+{h.conv}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <Card title="Channels" sub="6 CONNECTED">
            {channels.map((c, i) => (
              <div key={c.name} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 0', borderBottom: i < channels.length-1 ? '1px solid var(--hairline)' : 'none' }}>
                <div style={{ width: 22, height: 22, borderRadius: 4, background: c.col, display: 'grid', placeItems: 'center', fontSize: 11, fontWeight: 700, color: c.name === 'X' ? '#000' : '#000' }}>{c.name[0]}</div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 11.5 }}>{c.name}</div>
                  <div className="mono" style={{ fontSize: 9.5, color: 'var(--text-4)' }}>{c.hand} · {c.sub}</div>
                </div>
                <span className={"chip " + (c.state === 'connected' ? 'teal dot' : 'warn')} style={{ fontSize: 9 }}>{c.state}</span>
              </div>
            ))}
          </Card>

          <Card title="Top performing · 30d">
            {[
              { t: 'Why BTC bottomed in March',  o: '24.2K', conv: 102 },
              { t: 'NVDA was a market — now it\'s the market', o: '19.4K', conv: 81 },
              { t: 'A taxonomy of stablecoin risk',  o: '14.8K', conv: 54 },
            ].map((p, i) => (
              <div key={i} style={{ padding: '8px 0', borderBottom: i < 2 ? '1px solid var(--hairline)' : 'none' }}>
                <div style={{ fontSize: 11.5, color: 'var(--text)' }}>{p.t}</div>
                <div style={{ fontSize: 10, color: 'var(--text-3)', marginTop: 3 }} className="mono">{p.o} OPENS · +{p.conv} PAID</div>
              </div>
            ))}
          </Card>
        </div>
      </div>
    </div>
  );
}
window.PublishScreen = PublishScreen;
