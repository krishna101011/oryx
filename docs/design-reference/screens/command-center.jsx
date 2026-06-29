function CommandCenter({ tweaks }) {
  const briefBullets = [
    { tag: 'MACRO', text: 'US 10Y holds 4.32% into PCE print Friday; DXY consolidates at 104.6.' },
    { tag: 'CRYPTO', text: 'Spot BTC ETF inflows snap 3-day outflow streak: +$378M led by IBIT.' },
    { tag: 'EARNINGS', text: 'NVDA AH: data-center revenue $26.3B vs $24.8B est; guide light on China.' },
    { tag: 'POLICY', text: 'ECB minutes signal July hold; staff sees core CPI sticky through Q3.' },
  ];

  const pulse = [
    { sym: 'BTC',  px: '64,218.40', chg: '+1.84%', vol: '38.2B',  rng: '63,940 — 64,612', state: 'up' },
    { sym: 'ETH',  px: '3,142.20',  chg: '+0.42%', vol: '12.4B',  rng: '3,118 — 3,164', state: 'up' },
    { sym: 'SOL',  px: '142.18',    chg: '+3.21%', vol: '2.1B',   rng: '138 — 143',     state: 'up' },
    { sym: 'SPX',  px: '5,247.10',  chg: '-0.18%', vol: '—',      rng: '5,238 — 5,261', state: 'dn' },
    { sym: 'DXY',  px: '104.62',    chg: '+0.11%', vol: '—',      rng: '104.4 — 104.8', state: 'up' },
    { sym: 'GOLD', px: '2,342.10',  chg: '+0.58%', vol: '—',      rng: '2,330 — 2,348', state: 'up' },
  ];

  const alerts = [
    { sev: 'HIGH',   t: '07:42', msg: 'BTC funding turned positive across Binance + Bybit perps', src: 'On-chain' },
    { sev: 'MED',    t: '07:21', msg: 'Coinbase whale outflow: 4,800 BTC moved off-exchange', src: 'Whale Alert' },
    { sev: 'MED',    t: '06:55', msg: 'SEC delays decision on spot SOL ETF until July 17', src: 'EDGAR' },
    { sev: 'LOW',    t: '06:12', msg: 'Glassnode: LTH supply at ATH 14.91M BTC', src: 'Glassnode' },
  ];

  const opps = [
    { tk: 'BTC',  th: 'ETF flows reaccelerating · funding flip', score: 84, dir: 'long',  rr: '3.4R', tf: '1D' },
    { tk: 'SOL',  th: 'Token unlock priced in · DEX vol uptrend', score: 78, dir: 'long',  rr: '2.8R', tf: '4H' },
    { tk: 'ETH',  th: 'Beta lag vs BTC despite ETF approval',     score: 71, dir: 'long',  rr: '2.2R', tf: '1D' },
  ];

  return (
    <div className="section" style={{ padding: 0 }}>
      {/* Atmospheric hero */}
      <div style={{
        position: 'relative',
        padding: '32px 28px 28px',
        borderBottom: '1px solid var(--border)',
        background: 'radial-gradient(ellipse at 70% 30%, rgba(139,92,246,0.10), transparent 60%), radial-gradient(ellipse at 20% 80%, rgba(20,184,166,0.06), transparent 50%)',
        overflow: 'hidden',
      }}>
        {tweaks.showWatermark && (
          <div className="horn-watermark" style={{ opacity: 0.045 }}>
            <HornMark size={520} />
          </div>
        )}
        <div style={{ position: 'relative', display: 'flex', alignItems: 'flex-end', gap: 24 }}>
          <div style={{ flex: 1 }}>
            <div className="mono" style={{ color: 'var(--text-4)', fontSize: 10, letterSpacing: '0.2em' }}>FRIDAY · JUN 28 · 07:48 ET</div>
            <h1 style={{ fontSize: 30, fontWeight: 600, letterSpacing: '-0.02em', margin: '8px 0 6px', lineHeight: 1.1 }}>
              Good morning, Jordan.
            </h1>
            <div style={{ color: 'var(--text-2)', fontSize: 13, maxWidth: 640 }}>
              <span className="chip teal dot" style={{ marginRight: 8 }}>RISK-ON</span>
              Markets opening higher on softer PCE expectations. <span style={{ color: 'var(--text)' }}>3 catalysts</span> on your radar today, <span style={{ color: 'var(--text)' }}>7 unverified claims</span> queued, and <span style={{ color: 'var(--text)' }}>2 drafts</span> pending approval.
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn"><Icon.Calendar size={12}/> Today's brief</button>
            <button className="btn primary"><Icon.Sparkles size={12}/> Generate morning report</button>
          </div>
        </div>

        {/* Hero KPIs */}
        <div className="grid g-4" style={{ marginTop: 24, position: 'relative' }}>
          <Kpi label="Verified claims · 24h" val="142" delta="+18 vs avg" deltaPos sparkData={walk('k1', 24, 0.06, 0.005)} />
          <Kpi label="Avg confidence score"  val="0.847" delta="+0.04 wk" deltaPos sparkData={walk('k2', 24, 0.05, 0.003)} />
          <Kpi label="Active research packets" val="9" delta="3 in approval" deltaPos sparkData={walk('k3', 24, 0.08)} />
          <Kpi label="Newsletter MRR"        val="$48.2K" delta="+6.8% MoM" deltaPos sparkData={walk('k4', 24, 0.04, 0.006)} />
        </div>
      </div>

      <div className="section" style={{ padding: '14px 18px' }}>
        <div className="grid" style={{ gridTemplateColumns: '2fr 1.1fr', gap: 12 }}>
          {/* Morning Brief */}
          <Card title="Morning Brief" sub="AI-COMPOSED · 6 SOURCES" right={<span className="chip violet dot">DRAFT v3</span>}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {briefBullets.map((b, i) => (
                <div key={i} style={{ display: 'flex', gap: 10, paddingBottom: 10, borderBottom: i < briefBullets.length-1 ? '1px solid var(--hairline)' : 'none' }}>
                  <span className="chip indigo" style={{ minWidth: 64, justifyContent: 'center' }}>{b.tag}</span>
                  <div style={{ fontSize: 12.5, color: 'var(--text)', lineHeight: 1.5 }}>{b.text}</div>
                </div>
              ))}
            </div>
            <div style={{ marginTop: 12, display: 'flex', gap: 6 }}>
              <button className="btn"><Icon.Pen size={11}/> Edit in Studio</button>
              <button className="btn"><Icon.Send size={11}/> Publish to subs</button>
              <button className="btn ghost" style={{ marginLeft: 'auto' }}><Icon.Sparkles size={11}/> Regenerate</button>
            </div>
          </Card>

          {/* Urgent Alerts */}
          <Card title="Urgent Alerts" sub="LIVE" right={<><span className="chip teal dot">4 NEW</span></>}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {alerts.map((a, i) => (
                <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'flex-start', padding: '6px 0', borderBottom: i < alerts.length-1 ? '1px solid var(--hairline)' : 'none' }}>
                  <span className={"chip " + (a.sev === 'HIGH' ? 'neg' : a.sev === 'MED' ? 'warn' : '')} style={{ minWidth: 44, justifyContent: 'center' }}>{a.sev}</span>
                  <div style={{ flex: 1, fontSize: 11.5 }}>
                    <div style={{ color: 'var(--text)' }}>{a.msg}</div>
                    <div className="mono" style={{ fontSize: 10, color: 'var(--text-4)', marginTop: 2 }}>{a.t} · {a.src}</div>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>

        {/* Market Pulse */}
        <div style={{ marginTop: 12 }}>
          <Card title="Market Pulse" sub="LIVE · 8 ASSETS" right={<><span className="chip">1D</span><span className="chip">4H</span><span className="chip teal">1H</span></>} noPad>
            <table className="tbl">
              <thead>
                <tr>
                  <th>Asset</th><th className="num">Last</th><th className="num">24h</th>
                  <th className="num">Vol</th><th>Range</th><th>1H spark</th><th>Verified events</th>
                </tr>
              </thead>
              <tbody>
                {pulse.map(p => (
                  <tr key={p.sym}>
                    <td className="sym">{p.sym}</td>
                    <td className="num">{p.px}</td>
                    <td className={"num " + (p.state === 'up' ? 'pos' : 'neg')}>{p.chg}</td>
                    <td className="num muted">{p.vol}</td>
                    <td className="mono muted-2" style={{ fontSize: 11 }}>{p.rng}</td>
                    <td><Spark data={walk('pulse-'+p.sym, 24, 0.08, p.state === 'up' ? 0.005 : -0.005)} pos={p.state === 'up'} width={80}/></td>
                    <td className="muted-2">
                      {p.sym === 'BTC' && <><span className="chip teal" style={{ marginRight: 4 }}>ETF +</span><span className="chip">Funding flip</span></>}
                      {p.sym === 'ETH' && <span className="chip">Whale outflow</span>}
                      {p.sym === 'SOL' && <span className="chip warn">Unlock 2.4M</span>}
                      {p.sym === 'SPX' && <span className="chip">PCE Friday</span>}
                      {p.sym === 'DXY' && <span className="chip">FOMC speak</span>}
                      {p.sym === 'GOLD' && <span className="chip">CB demand</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </div>

        {/* Bottom row */}
        <div className="grid" style={{ gridTemplateColumns: '1.4fr 1fr', gap: 12, marginTop: 12 }}>
          <Card title="Top Opportunities" sub="RANKED BY ORYX SCORE" right={<button className="btn ghost" style={{ fontSize: 10.5 }}>Open radar →</button>}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {opps.map((o, i) => (
                <div key={i} style={{ display: 'grid', gridTemplateColumns: '54px 1fr 64px 60px 90px', gap: 10, alignItems: 'center', padding: '8px 0', borderBottom: i < opps.length-1 ? '1px solid var(--hairline)' : 'none' }}>
                  <span className="mono" style={{ fontSize: 14, fontWeight: 600 }}>{o.tk}</span>
                  <div>
                    <div style={{ fontSize: 12, color: 'var(--text)' }}>{o.th}</div>
                    <div className="mono" style={{ fontSize: 10, color: 'var(--text-4)', marginTop: 2 }}>{o.dir.toUpperCase()} · {o.tf} · {o.rr}</div>
                  </div>
                  <div>
                    <div className="meter"><div className="meter-fill" style={{ width: o.score + '%' }} /></div>
                    <div className="mono" style={{ fontSize: 10, color: 'var(--text-3)', marginTop: 3 }}>{o.score}/100</div>
                  </div>
                  <span className={"chip " + (o.dir === 'long' ? 'teal' : 'neg')}>{o.dir.toUpperCase()}</span>
                  <button className="btn ghost" style={{ fontSize: 10.5 }}>Open <Icon.ChevRight size={10}/></button>
                </div>
              ))}
            </div>
          </Card>

          <Card title="Workflow" sub="WHAT NEEDS YOU">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {[
                { ic: 'Shield',  t: '7 claims awaiting verification', sub: 'Avg age 38m · 3 high-priority', cta: 'Review' },
                { ic: 'Beaker',  t: '2 research packets in approval', sub: 'NVDA earnings · BTC ETF flows', cta: 'Approve' },
                { ic: 'Pen',     t: 'Newsletter draft v3 ready',      sub: 'Last edit 12m ago', cta: 'Open' },
                { ic: 'Send',    t: '3 posts queued for 09:30 ET',    sub: 'X · LinkedIn · Substack', cta: 'Schedule' },
                { ic: 'Zap',     t: 'Automation: "Funding flip" fired', sub: 'Created BTC opportunity card', cta: 'View' },
              ].map((w, i) => {
                const I = Icon[w.ic];
                return (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 0', borderBottom: i < 4 ? '1px solid var(--hairline)' : 'none' }}>
                    <div style={{ width: 26, height: 26, display: 'grid', placeItems: 'center', background: 'var(--elev)', border: '1px solid var(--border)', borderRadius: 5, color: 'var(--violet)' }}>
                      <I size={13}/>
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 11.5 }}>{w.t}</div>
                      <div className="mono" style={{ fontSize: 10, color: 'var(--text-4)' }}>{w.sub}</div>
                    </div>
                    <button className="btn ghost" style={{ fontSize: 10.5 }}>{w.cta}</button>
                  </div>
                );
              })}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

window.CommandCenter = CommandCenter;
