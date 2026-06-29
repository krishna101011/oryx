function VerificationScreen() {
  const queue = [
    { id: 'CL-1408', claim: 'IBIT received $378M net inflow on Jun 27', src: 'Bloomberg + Farside', conf: 0.92, stat: 'verified',  age: '3m'  },
    { id: 'CL-1407', claim: 'NVDA data-center revenue $26.3B in Q1 FY25', src: 'NVDA 8-K + WSJ',    conf: 0.97, stat: 'verified',  age: '7m'  },
    { id: 'CL-1406', claim: '4,800 BTC moved from Coinbase to cold wallet', src: 'Arkham + The Block', conf: 0.74, stat: 'review',   age: '14m' },
    { id: 'CL-1405', claim: 'BlackRock plans Ethereum staking ETF amendment', src: 'CoinDesk single-src', conf: 0.41, stat: 'low-conf', age: '22m' },
    { id: 'CL-1404', claim: 'Eurozone June CPI 2.5% YoY',                   src: 'Eurostat primary', conf: 1.00, stat: 'verified',  age: '38m' },
    { id: 'CL-1403', claim: 'Fed Williams: rate path "well calibrated"',     src: 'Fed transcript',   conf: 0.99, stat: 'verified',  age: '52m' },
    { id: 'CL-1402', claim: 'Coinbase to delist 4 low-volume assets in July', src: 'Coinbase blog',   conf: 0.95, stat: 'verified',  age: '1h'  },
    { id: 'CL-1401', claim: 'Tether mints 2B USDT on Tron',                  src: 'On-chain + Whale Alert', conf: 0.96, stat: 'verified', age: '1h' },
    { id: 'CL-1400', claim: 'Saudi Arabia drops petrodollar agreement',       src: 'Twitter rumor',    conf: 0.18, stat: 'rejected',  age: '2h'  },
  ];

  const stat = (s) => {
    if (s === 'verified') return <span className="chip teal dot">VERIFIED</span>;
    if (s === 'review')   return <span className="chip warn">REVIEW</span>;
    if (s === 'low-conf') return <span className="chip warn">LOW CONF</span>;
    if (s === 'rejected') return <span className="chip neg">REJECTED</span>;
    return <span className="chip">{s}</span>;
  };

  // Active claim
  const evidence = [
    { src: 'Farside Investors API', type: 'PRIMARY DATA', q: 96, snip: 'Net flow data: IBIT +$378.2M (Jun 27 close)', match: 'EXACT' },
    { src: 'Bloomberg Terminal',    type: 'NEWS WIRE',    q: 94, snip: '"IBIT recorded its largest single-day inflow…"', match: 'CORROBORATES' },
    { src: 'BlackRock IR statement',type: 'PRIMARY',      q: 100,snip: 'No official statement issued yet (T+1 standard)', match: 'NEUTRAL' },
    { src: 'Reuters',               type: 'NEWS WIRE',    q: 94, snip: '"BlackRock spot Bitcoin fund led inflows…"',    match: 'CORROBORATES' },
    { src: 'CoinDesk',              type: 'NEWS',         q: 78, snip: '"IBIT inflows top $370M…"',                     match: 'CORROBORATES' },
    { src: 'X / @SoSoValueAlerts',  type: 'SOCIAL',       q: 52, snip: '"BTC ETF +$378M today"',                       match: 'CORROBORATES' },
  ];

  return (
    <div className="section">
      <div className="grid" style={{ gridTemplateColumns: '1fr 380px', gap: 12 }}>

        {/* Queue */}
        <Card title="Claim queue" sub="9 ACTIVE · 7 PENDING REVIEW" right={<>
          <span className="chip">All</span><span className="chip teal">Verified · 5</span><span className="chip warn">Review · 2</span><span className="chip neg">Rejected · 1</span>
        </>} noPad>
          <table className="tbl">
            <thead><tr>
              <th>ID</th><th>Claim</th><th>Sources</th><th>Status</th><th className="num">Conf.</th><th>Age</th><th></th>
            </tr></thead>
            <tbody>
              {queue.map((q, i) => (
                <tr key={q.id} style={{ background: i === 0 ? 'rgba(139,92,246,0.04)' : undefined }}>
                  <td className="mono" style={{ color: 'var(--text-3)', fontSize: 10.5 }}>{q.id}</td>
                  <td style={{ color: 'var(--text)', maxWidth: 420 }}>{q.claim}</td>
                  <td className="muted-2" style={{ fontSize: 11 }}>{q.src}</td>
                  <td>{stat(q.stat)}</td>
                  <td className="num">
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, justifyContent: 'flex-end' }}>
                      <div className="meter" style={{ width: 50 }}>
                        <div className={"meter-fill " + (q.conf < 0.5 ? 'neg' : q.conf < 0.75 ? '' : 'teal')} style={{ width: (q.conf*100)+'%' }} />
                      </div>
                      <span style={{ width: 36 }}>{q.conf.toFixed(2)}</span>
                    </div>
                  </td>
                  <td className="mono" style={{ color: 'var(--text-4)', fontSize: 10.5 }}>{q.age}</td>
                  <td><button className="btn ghost" style={{ fontSize: 10.5, padding: '2px 6px' }}>Open</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>

        {/* Active claim */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <Card title="Active claim" sub="CL-1408" right={<span className="chip teal dot">VERIFIED</span>}>
            <div style={{ fontSize: 13, color: 'var(--text)', lineHeight: 1.5, marginBottom: 10 }}>
              "IBIT received <span className="mono" style={{ color: 'var(--violet)' }}>$378M</span> in net inflows on <span className="mono">Jun 27, 2024</span>, snapping a 3-day outflow streak across the spot BTC ETF complex."
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 14, paddingBottom: 12, borderBottom: '1px solid var(--hairline)' }}>
              <div>
                <div className="mono" style={{ fontSize: 9.5, color: 'var(--text-4)', letterSpacing: '0.1em' }}>EPISTEMIC TYPE</div>
                <div style={{ fontSize: 12, marginTop: 3 }}>Quantitative · Time-bound</div>
              </div>
              <div>
                <div className="mono" style={{ fontSize: 9.5, color: 'var(--text-4)', letterSpacing: '0.1em' }}>FALSIFIABLE</div>
                <div style={{ fontSize: 12, marginTop: 3, color: 'var(--teal)' }}>YES · via primary API</div>
              </div>
            </div>

            {/* Confidence dial */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 18 }}>
              <svg width="100" height="100" viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="42" stroke="#1A2330" strokeWidth="6" fill="none" />
                <circle cx="50" cy="50" r="42" stroke="url(#cg)" strokeWidth="6" fill="none"
                        strokeDasharray={`${0.92 * 264} 264`} strokeDashoffset="0"
                        transform="rotate(-90 50 50)" strokeLinecap="round" />
                <defs>
                  <linearGradient id="cg" x1="0" x2="1" y1="0" y2="1">
                    <stop offset="0" stopColor="#14B8A6" />
                    <stop offset="1" stopColor="#8B5CF6" />
                  </linearGradient>
                </defs>
                <text x="50" y="48" textAnchor="middle" fontFamily="JetBrains Mono" fontSize="20" fontWeight="600" fill="#E6EAF2">0.92</text>
                <text x="50" y="62" textAnchor="middle" fontFamily="JetBrains Mono" fontSize="8" fill="#6B7588" letterSpacing="2">CONFIDENCE</text>
              </svg>
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 6 }}>
                {[
                  { l: 'Primary source agree', v: 1.00 },
                  { l: 'Secondary corroboration', v: 0.90 },
                  { l: 'Recency · freshness', v: 0.95 },
                  { l: 'Conflict-adjusted', v: 0.92 },
                ].map((m, i) => (
                  <div key={i}>
                    <div style={{ display: 'flex', fontSize: 10.5, color: 'var(--text-3)', marginBottom: 2 }}>
                      <span>{m.l}</span><span className="mono" style={{ marginLeft: 'auto', color: 'var(--text)' }}>{m.v.toFixed(2)}</span>
                    </div>
                    <div className="meter" style={{ height: 4 }}><div className="meter-fill teal" style={{ width: m.v*100 + '%' }}/></div>
                  </div>
                ))}
              </div>
            </div>
            <div style={{ display: 'flex', gap: 6, marginTop: 14 }}>
              <button className="btn primary"><Icon.Check size={11}/> Approve</button>
              <button className="btn"><Icon.Flag size={11}/> Flag</button>
              <button className="btn"><Icon.X size={11}/> Reject</button>
              <button className="btn ghost" style={{ marginLeft: 'auto' }}><Icon.Beaker size={11}/> To packet</button>
            </div>
          </Card>

          <Card title="Evidence ledger" sub="6 SOURCES" noPad>
            {evidence.map((e, i) => (
              <div key={i} style={{ padding: '8px 12px', borderBottom: i < evidence.length-1 ? '1px solid var(--hairline)' : 'none' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                  <span className="chip" style={{ fontSize: 9 }}>{e.type}</span>
                  <span style={{ fontSize: 11, color: 'var(--text)' }}>{e.src}</span>
                  <span className="mono" style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--text-3)' }}>Q {e.q}</span>
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-2)', fontStyle: 'italic', marginBottom: 4 }}>{e.snip}</div>
                <span className={"chip " + (e.match === 'EXACT' ? 'teal' : e.match === 'NEUTRAL' ? '' : 'indigo')} style={{ fontSize: 9 }}>{e.match}</span>
              </div>
            ))}
          </Card>
        </div>
      </div>

      {/* Audit trail */}
      <div style={{ marginTop: 12 }}>
        <Card title="Audit log" sub="CL-1408" noPad>
          <table className="tbl">
            <thead><tr><th style={{ width: 110 }}>Time</th><th>Actor</th><th>Event</th><th>From → To</th><th>Note</th></tr></thead>
            <tbody>
              <tr><td className="mono">07:42:18</td><td>system</td><td>Claim extracted from BBG-78421</td><td>—</td><td className="muted-2">Auto · NER + claim model</td></tr>
              <tr><td className="mono">07:42:19</td><td>system</td><td>Sources queried (6)</td><td>—</td><td className="muted-2">Farside, BBG, Reuters, BlackRock IR, CoinDesk, X</td></tr>
              <tr><td className="mono">07:42:22</td><td>system</td><td>Confidence scored</td><td>— → 0.92</td><td className="muted-2">Above auto-verify threshold (0.85)</td></tr>
              <tr><td className="mono">07:43:01</td><td>jordan.m</td><td>Reviewed</td><td>verified → verified</td><td className="muted-2">Approved as canonical</td></tr>
              <tr><td className="mono">07:43:04</td><td>jordan.m</td><td>Linked to packet</td><td>— → PKT-44</td><td className="muted-2">"BTC ETF June flows"</td></tr>
            </tbody>
          </table>
        </Card>
      </div>
    </div>
  );
}
window.VerificationScreen = VerificationScreen;
