function ResearchScreen() {
  const packets = [
    { id: 'PKT-44', name: 'BTC ETF June flows',         status: 'In approval', claims: 14, owner: 'JM', tag: 'crypto' },
    { id: 'PKT-43', name: 'NVDA Q1 FY25 teardown',      status: 'Drafting',    claims: 22, owner: 'JM', tag: 'equity', active: true },
    { id: 'PKT-42', name: 'PCE inflation watch',         status: 'Live',        claims: 9,  owner: 'AK', tag: 'macro' },
    { id: 'PKT-41', name: 'JPY intervention thesis',    status: 'Live',        claims: 7,  owner: 'AK', tag: 'fx' },
    { id: 'PKT-40', name: 'SOL ETF probability model',  status: 'Drafting',    claims: 11, owner: 'JM', tag: 'crypto' },
    { id: 'PKT-39', name: 'AI capex cycle (5 vendors)',  status: 'Published',   claims: 31, owner: 'JM', tag: 'equity' },
  ];

  return (
    <div className="section">
      <div className="grid" style={{ gridTemplateColumns: '260px 1fr 280px', gap: 12 }}>
        <Card title="Packets" sub="6 ACTIVE" right={<button className="btn ghost" style={{ fontSize: 10 }}><Icon.Plus size={10}/></button>} noPad>
          {packets.map((p, i) => (
            <div key={p.id} style={{ padding: '10px 12px', borderBottom: i < packets.length-1 ? '1px solid var(--hairline)' : 'none', background: p.active ? 'rgba(139,92,246,0.06)' : undefined, cursor: 'pointer', borderLeft: p.active ? '2px solid var(--violet)' : '2px solid transparent' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span className="mono" style={{ fontSize: 10, color: 'var(--text-4)' }}>{p.id}</span>
                <span className="chip" style={{ marginLeft: 'auto', fontSize: 9 }}>{p.tag}</span>
              </div>
              <div style={{ fontSize: 12, color: 'var(--text)', margin: '4px 0' }}>{p.name}</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span className={"chip " + (p.status === 'Live' ? 'teal dot' : p.status === 'Published' ? 'indigo' : 'warn')} style={{ fontSize: 9 }}>{p.status.toUpperCase()}</span>
                <span className="mono" style={{ fontSize: 10, color: 'var(--text-3)', marginLeft: 'auto' }}>{p.claims} claims · {p.owner}</span>
              </div>
            </div>
          ))}
        </Card>

        {/* Packet builder */}
        <Card title="PKT-43 · NVDA Q1 FY25 teardown" sub="DRAFTING · 22 CLAIMS" right={<>
          <span className="chip">Outline</span><span className="chip teal">Canvas</span><span className="chip">Sources</span><span className="chip">Approvals</span>
        </>}>
          <div style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
            <span className="chip teal dot">VERIFIED 18</span>
            <span className="chip warn">REVIEW 3</span>
            <span className="chip neg">CONFLICT 1</span>
            <span style={{ marginLeft: 'auto' }} className="mono muted">Avg conf 0.86</span>
          </div>

          {/* Outline cards */}
          {[
            { h: 'TL;DR', body: 'NVDA beat top-line and beat data-center segment but guided softer on China H20 demand. Blackwell on track for Q3. Margin gross 78.4%, +90bps QoQ.', n: 4 },
            { h: 'Datacenter segment', body: 'Revenue $26.3B (+427% Y/Y). HBM3E ramp pulled forward. Hyperscaler concentration ~45%. CFO Kress: "capex visibility through CY26".', n: 7 },
            { h: 'China & H20', body: 'H20 SKU demand softening into 2H. Inventory adjustment of ~$1.2B taken in cost line. Geopolitical risk repricing.', n: 4, conflict: true },
            { h: 'Forward setup', body: 'Blackwell B100/B200 sampling complete. Pricing premium 30-40% over Hopper. CSP capex commitments imply 65% Y/Y growth in CY25 AI spend.', n: 5 },
            { h: 'Counter-thesis', body: 'ASIC threat from Trainium/TPU not modeled. Maxon revenue cyclicality. Multiple compression risk if Fed delays cuts.', n: 2 },
          ].map((c, i) => (
            <div key={i} style={{ background: 'var(--elev)', border: '1px solid var(--border)', borderRadius: 5, padding: '10px 12px', marginBottom: 8 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                <span className="mono" style={{ fontSize: 10, color: 'var(--text-4)', width: 16 }}>{(i+1).toString().padStart(2,'0')}</span>
                <span style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--text)' }}>{c.h}</span>
                {c.conflict && <span className="chip neg" style={{ fontSize: 9 }}>CONFLICT</span>}
                <span style={{ marginLeft: 'auto' }} className="chip">{c.n} CLAIMS</span>
              </div>
              <div style={{ fontSize: 11.5, color: 'var(--text-2)', lineHeight: 1.55, paddingLeft: 24 }}>{c.body}</div>
            </div>
          ))}

          <div style={{ display: 'flex', gap: 6, marginTop: 10 }}>
            <button className="btn"><Icon.Plus size={11}/> Add section</button>
            <button className="btn"><Icon.Sparkles size={11}/> Suggest counter-thesis</button>
            <button className="btn primary" style={{ marginLeft: 'auto' }}><Icon.Send size={11}/> Send for approval</button>
          </div>
        </Card>

        {/* Notes */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <Card title="Notes" sub="JORDAN" noPad>
            <div style={{ padding: 10, display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div style={{ background: 'rgba(245,158,11,0.06)', borderLeft: '2px solid var(--warn)', padding: '6px 9px', borderRadius: 3 }}>
                <div className="mono" style={{ fontSize: 9.5, color: 'var(--warn)', letterSpacing: '0.1em' }}>HYPOTHESIS</div>
                <div style={{ fontSize: 11.5, marginTop: 2 }}>If China H20 is fully written down in CY25, ex-China DC rev still implies 55% growth → multiple expansion warranted.</div>
              </div>
              <div style={{ background: 'rgba(20,184,166,0.06)', borderLeft: '2px solid var(--teal)', padding: '6px 9px', borderRadius: 3 }}>
                <div className="mono" style={{ fontSize: 9.5, color: 'var(--teal)', letterSpacing: '0.1em' }}>CITATION</div>
                <div style={{ fontSize: 11.5, marginTop: 2 }}>Kress earnings call transcript, 38:14 — "we have multi-year visibility into datacenter demand"</div>
              </div>
              <div style={{ background: 'rgba(139,92,246,0.06)', borderLeft: '2px solid var(--violet)', padding: '6px 9px', borderRadius: 3 }}>
                <div className="mono" style={{ fontSize: 9.5, color: 'var(--violet)', letterSpacing: '0.1em' }}>TO-DO</div>
                <div style={{ fontSize: 11.5, marginTop: 2 }}>Pull hyperscaler capex from MSFT/AMZN/GOOGL/META 10-Qs to triangulate guide.</div>
              </div>
            </div>
          </Card>

          <Card title="Approvals" sub="ROUTE">
            {[
              { who: 'Alex K. · Research lead', state: 'approved' },
              { who: 'Mira S. · Compliance',   state: 'approved' },
              { who: 'Jordan M. · EIC',         state: 'pending', active: true },
              { who: 'Auto-publish',            state: 'queued' },
            ].map((s, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '6px 0', borderBottom: i < 3 ? '1px solid var(--hairline)' : 'none' }}>
                <div style={{ width: 18, height: 18, borderRadius: 50, border: '1px solid ' + (s.state === 'approved' ? 'var(--teal)' : s.state === 'pending' ? 'var(--violet)' : 'var(--border-strong)'), display: 'grid', placeItems: 'center', color: s.state === 'approved' ? 'var(--teal)' : 'var(--text-3)' }}>
                  {s.state === 'approved' ? <Icon.Check size={10}/> : s.state === 'pending' ? <Icon.Dot size={6}/> : null}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 11.5, color: s.active ? 'var(--text)' : 'var(--text-2)' }}>{s.who}</div>
                  <div className="mono" style={{ fontSize: 9.5, color: 'var(--text-4)' }}>{s.state.toUpperCase()}</div>
                </div>
              </div>
            ))}
          </Card>
        </div>
      </div>
    </div>
  );
}
window.ResearchScreen = ResearchScreen;
