function AnalyticsScreen() {
  const cohort = [
    ['W-12', 100, 78, 64, 56, 51, 49, 47, 45, 43, 42, 41, 40],
    ['W-11', 100, 81, 67, 58, 52, 50, 48, 46, 44, 43, 42, null],
    ['W-10', 100, 79, 65, 55, 52, 49, 47, 45, 43, 41, null, null],
    ['W-9',  100, 82, 69, 60, 54, 51, 48, 46, 44, null, null, null],
    ['W-8',  100, 80, 66, 57, 53, 50, 48, 46, null, null, null, null],
    ['W-7',  100, 83, 71, 62, 56, 53, 51, null, null, null, null, null],
    ['W-6',  100, 81, 68, 59, 55, 52, null, null, null, null, null, null],
    ['W-5',  100, 84, 72, 64, 58, null, null, null, null, null, null, null],
    ['W-4',  100, 85, 73, 66, null, null, null, null, null, null, null, null],
    ['W-3',  100, 86, 74, null, null, null, null, null, null, null, null, null],
    ['W-2',  100, 87, null, null, null, null, null, null, null, null, null, null],
    ['W-1',  100, null, null, null, null, null, null, null, null, null, null, null],
  ];
  const heat = (v) => v == null ? 'transparent' : `rgba(91,91,245,${0.05 + (v/100)*0.55})`;

  const funnel = [
    { l: 'Landing visit',     v: 48200 },
    { l: 'Email signup',      v: 12640 },
    { l: 'First read',        v: 9820 },
    { l: 'Engaged 3+ reads',  v: 5410 },
    { l: 'Paid conversion',   v: 1684 },
  ];
  const max = funnel[0].v;

  return (
    <div className="section">
      <div className="grid g-4" style={{ marginBottom: 12 }}>
        <Kpi label="MRR"                val="$48.2K" delta="+6.8% MoM" deltaPos sparkData={walk('mrr',24,0.04,0.006)} />
        <Kpi label="Paid subscribers"   val="1,684"  delta="+102 wk"    deltaPos sparkData={walk('sub',24,0.05,0.005)} />
        <Kpi label="Avg session · daily"val="6m 42s" delta="+18s WoW"  deltaPos />
        <Kpi label="Verified claims/day"val="142"    delta="+18 vs avg" deltaPos sparkData={walk('cl',24,0.08)} />
      </div>

      <div className="grid" style={{ gridTemplateColumns: '1.4fr 1fr', gap: 12 }}>
        <Card title="MRR & subscribers" sub="LAST 12 WEEKS">
          <svg width="100%" height="220" viewBox="0 0 600 220">
            {/* grid */}
            {[0,55,110,165].map((y,i) => <line key={i} x1="40" x2="580" y1={y+20} y2={y+20} stroke="#1A2330" strokeDasharray="2 4"/>)}
            {/* MRR area */}
            <defs><linearGradient id="mrrFill" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor="#8B5CF6" stopOpacity="0.3"/><stop offset="1" stopColor="#8B5CF6" stopOpacity="0"/></linearGradient></defs>
            <path d={`M 40 180 ${[28,40,50,46,62,70,78,88,98,112,128,144,162].map((v,i) => `L ${40 + i*45} ${200-v}`).join(' ')} L 580 180 Z`} fill="url(#mrrFill)"/>
            <polyline points={[28,40,50,46,62,70,78,88,98,112,128,144,162].map((v,i) => `${40 + i*45},${200-v}`).join(' ')} stroke="#8B5CF6" strokeWidth="1.5" fill="none"/>
            {/* Subscribers line */}
            <polyline points={[15,22,30,36,40,46,52,60,66,72,82,94,108].map((v,i) => `${40 + i*45},${200-v*0.9}`).join(' ')} stroke="#14B8A6" strokeWidth="1.5" fill="none" strokeDasharray="3 2"/>
            {/* x labels */}
            {Array.from({length: 13}).map((_, i) => <text key={i} x={40 + i*45} y={215} fill="#4A5263" fontSize="9" fontFamily="JetBrains Mono" textAnchor="middle">{`W-${12-i}`}</text>)}
            {/* y labels */}
            {[60,45,30,15,0].map((v,i) => <text key={v} x={32} y={i*40+24} fill="#4A5263" fontSize="9" fontFamily="JetBrains Mono" textAnchor="end">${v}K</text>)}
            {/* legend */}
            <g transform="translate(440, 16)">
              <rect x="0" y="0" width="10" height="2" fill="#8B5CF6"/>
              <text x="14" y="4" fontSize="9.5" fill="#A8B0BF" fontFamily="JetBrains Mono">MRR ($K)</text>
              <rect x="80" y="0" width="10" height="2" fill="#14B8A6"/>
              <text x="94" y="4" fontSize="9.5" fill="#A8B0BF" fontFamily="JetBrains Mono">Subscribers (K)</text>
            </g>
          </svg>
        </Card>

        <Card title="Conversion funnel" sub="LAST 30 DAYS">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, padding: '4px 0' }}>
            {funnel.map((f, i) => {
              const w = (f.v / max) * 100;
              const drop = i > 0 ? ((funnel[i-1].v - f.v)/funnel[i-1].v * 100).toFixed(1) : null;
              return (
                <div key={f.l}>
                  <div style={{ display: 'flex', alignItems: 'center', marginBottom: 3, fontSize: 11.5 }}>
                    <span style={{ color: 'var(--text)' }}>{f.l}</span>
                    <span className="mono" style={{ marginLeft: 'auto', color: 'var(--text)' }}>{f.v.toLocaleString()}</span>
                    {drop && <span className="mono neg" style={{ width: 56, textAlign: 'right', fontSize: 10 }}>-{drop}%</span>}
                  </div>
                  <div style={{ height: 18, background: 'var(--elev)', borderRadius: 2, position: 'relative' }}>
                    <div style={{ width: w + '%', height: '100%', background: 'var(--accent-grad)', borderRadius: 2 }}/>
                  </div>
                </div>
              );
            })}
            <div style={{ marginTop: 4, padding: '8px 0 0', borderTop: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between' }}>
              <span className="mono" style={{ fontSize: 10.5, color: 'var(--text-3)' }}>VISITOR → PAID</span>
              <span className="mono" style={{ fontSize: 12, color: 'var(--teal)' }}>3.49%</span>
            </div>
          </div>
        </Card>
      </div>

      <div className="grid" style={{ gridTemplateColumns: '1.4fr 1fr', gap: 12, marginTop: 12 }}>
        {/* Cohort retention */}
        <Card title="Retention cohort" sub="WEEKLY · % RETAINED">
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'separate', borderSpacing: 2, fontSize: 10 }} className="mono">
              <thead><tr><th style={{ textAlign: 'left', color: 'var(--text-4)', padding: 4 }}>Cohort</th>
                {Array.from({length: 12}).map((_, i) => <th key={i} style={{ color: 'var(--text-4)', padding: 4 }}>W{i}</th>)}
              </tr></thead>
              <tbody>
                {cohort.map(row => (
                  <tr key={row[0]}>
                    <td style={{ padding: 4, color: 'var(--text-3)' }}>{row[0]}</td>
                    {row.slice(1).map((v, i) => (
                      <td key={i} style={{ background: heat(v), padding: '6px 4px', textAlign: 'center', borderRadius: 2, color: v == null ? 'transparent' : v > 60 ? '#fff' : 'var(--text-2)' }}>
                        {v == null ? '·' : v}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        <Card title="Attribution · Paid conversions" sub="LAST 30 DAYS">
          {[
            { src: 'Substack referral',  conv: 612, pct: 36, col: '#FF6719' },
            { src: 'X (organic)',         conv: 384, pct: 23, col: '#A8B0BF' },
            { src: 'Direct',              conv: 268, pct: 16, col: '#8B5CF6' },
            { src: 'LinkedIn',            conv: 168, pct: 10, col: '#0a66c2' },
            { src: 'Search · SEO',        conv: 142, pct: 8,  col: '#14B8A6' },
            { src: 'Other partners',      conv: 110, pct: 7,  col: '#60A5FA' },
          ].map((a, i) => (
            <div key={i} style={{ padding: '6px 0' }}>
              <div style={{ display: 'flex', fontSize: 11.5, alignItems: 'center', gap: 8 }}>
                <span style={{ width: 8, height: 8, background: a.col, borderRadius: 2 }}/>
                <span>{a.src}</span>
                <span className="mono" style={{ marginLeft: 'auto', color: 'var(--text)' }}>{a.conv}</span>
                <span className="mono" style={{ color: 'var(--text-3)', width: 36, textAlign: 'right' }}>{a.pct}%</span>
              </div>
              <div style={{ height: 4, background: 'var(--elev)', borderRadius: 2, marginTop: 3 }}>
                <div style={{ width: a.pct * 2.7 + '%', height: '100%', background: a.col, borderRadius: 2 }}/>
              </div>
            </div>
          ))}
        </Card>
      </div>

      <div style={{ marginTop: 12 }}>
        <Card title="Content performance" sub="TOP 8 · LAST 30D" noPad>
          <table className="tbl">
            <thead><tr><th>Title</th><th>Channel</th><th>Published</th><th className="num">Opens</th><th className="num">CTR</th><th className="num">Paid conv.</th><th className="num">Revenue</th><th>Performance</th></tr></thead>
            <tbody>
              {[
                ['Why BTC bottomed in March',     'Substack', 'Jun 12', '24,210', '6.2%', '+102', '$4,080', 95],
                ['NVDA was a market — now it\'s the market', 'Substack', 'Jun 18', '19,420', '5.8%', '+81',  '$3,240', 88],
                ['Five charts the FOMC won\'t show you','X',  'Jun 26', '210K imp', '3.4%', '+52',  '$2,080', 76],
                ['Stablecoin risk taxonomy',         'Substack', 'Jun 04', '14,820', '5.1%', '+54',  '$2,160', 72],
                ['SOL ETF probability model',         'Substack', 'Jun 22', '12,140', '4.8%', '+38',  '$1,520', 64],
                ['JPY intervention thesis',           'LinkedIn', 'Jun 20',  '5,210', '2.4%', '+12',  '$480',   42],
                ['PCE preview',                       'Substack', 'Jun 25',  '7,840', '3.9%', '+8',   '$320',   28],
                ['Daily Brief · Jun 14',              'Substack', 'Jun 14',  '7,610', '4.1%', '+6',   '$240',   24],
              ].map((r, i) => (
                <tr key={i}>
                  <td style={{ color: 'var(--text)' }}>{r[0]}</td>
                  <td><span className="chip" style={{ fontSize: 9 }}>{r[1]}</span></td>
                  <td className="mono muted">{r[2]}</td>
                  <td className="num">{r[3]}</td>
                  <td className="num">{r[4]}</td>
                  <td className="num pos">{r[5]}</td>
                  <td className="num">{r[6]}</td>
                  <td><div className="meter" style={{ width: 70 }}><div className="meter-fill" style={{ width: r[7]+'%' }}/></div></td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>
    </div>
  );
}
window.AnalyticsScreen = AnalyticsScreen;
