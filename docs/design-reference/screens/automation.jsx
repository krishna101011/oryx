function AutomationScreen() {
  const rules = [
    { id: 'AUT-08', name: 'BTC funding flip → opportunity card', trig: 'On-chain', fires: 28, last: '14m', state: 'on', active: true },
    { id: 'AUT-07', name: 'Earnings beat ≥10% → draft recap',     trig: 'Earnings', fires: 12, last: '3h',  state: 'on' },
    { id: 'AUT-06', name: 'High-impact news + verified → push',  trig: 'News',     fires: 142,last: '8m',  state: 'on' },
    { id: 'AUT-05', name: 'Daily Brief at 09:00 ET',              trig: 'Schedule', fires: 184,last: '22h', state: 'on' },
    { id: 'AUT-04', name: 'Conflict detected → Slack #conflicts',  trig: 'Verify',   fires: 9,  last: '1d',  state: 'on' },
    { id: 'AUT-03', name: 'Whale outflow >2,500 BTC → alert',     trig: 'On-chain', fires: 6,  last: '14m', state: 'on' },
    { id: 'AUT-02', name: 'Weekly recap auto-publish (Sat 07:30)',trig: 'Schedule', fires: 12, last: '6d',  state: 'on' },
    { id: 'AUT-01', name: 'Source trust score < 0.5 → quarantine',trig: 'Intake',   fires: 4,  last: '2d',  state: 'off' },
  ];

  return (
    <div className="section">
      <div className="grid g-4" style={{ marginBottom: 12 }}>
        <Kpi label="Active rules"        val="7"  delta="of 8 total" />
        <Kpi label="Fires · last 24h"    val="42" delta="+18% vs wk avg" deltaPos sparkData={walk('aut',24,0.1,0.005)} />
        <Kpi label="Saved analyst hours" val="14.2" delta="estimated, this week" deltaPos />
        <Kpi label="Failure rate"        val="0.4%" delta="3 retries auto-resolved" deltaPos />
      </div>

      <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        <Card title="Rules" sub="8 TOTAL" right={<button className="btn primary"><Icon.Plus size={11}/> New rule</button>} noPad>
          <table className="tbl">
            <thead><tr><th>ID</th><th>Rule</th><th>Trigger</th><th className="num">Fires</th><th>Last</th><th>State</th></tr></thead>
            <tbody>
              {rules.map(r => (
                <tr key={r.id} style={r.active ? { background: 'rgba(139,92,246,0.05)' } : null}>
                  <td className="mono" style={{ color: 'var(--text-3)' }}>{r.id}</td>
                  <td style={{ color: 'var(--text)' }}>{r.name}</td>
                  <td><span className="chip" style={{ fontSize: 9 }}>{r.trig}</span></td>
                  <td className="num">{r.fires}</td>
                  <td className="mono muted">{r.last}</td>
                  <td>
                    <div style={{ width: 28, height: 14, borderRadius: 8, background: r.state === 'on' ? 'var(--teal)' : 'var(--border-strong)', position: 'relative', cursor: 'pointer' }}>
                      <div style={{ position: 'absolute', top: 2, left: r.state === 'on' ? 16 : 2, width: 10, height: 10, borderRadius: 50, background: '#fff' }}/>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>

        {/* Rule builder */}
        <Card title="AUT-08 · BTC funding flip → opportunity card" sub="EDIT" right={<><span className="chip teal dot">ENABLED</span></>}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14, padding: 4 }}>
            {[
              { num: '01', kind: 'TRIGGER', col: '#8B5CF6', t: 'When', body: 'BTC funding rate flips from negative to positive', meta: 'Source: Binance + Bybit (avg) · Confirmed across 2 venues' },
              { num: '02', kind: 'CONDITION', col: '#60A5FA', t: 'And',  body: 'BTC 24h volume > $30B AND ETF aggregate flow > $200M', meta: '2 conditions · all must match' },
              { num: '03', kind: 'CONDITION', col: '#60A5FA', t: 'And',  body: 'No active opportunity for BTC in last 12h',           meta: 'Cooldown · prevents duplicate cards' },
              { num: '04', kind: 'ACTION',    col: '#14B8A6', t: 'Then', body: 'Create opportunity card · LONG · auto-score · notify Slack #ops', meta: 'Template: BTC long radar · CC: editorial' },
              { num: '05', kind: 'ACTION',    col: '#14B8A6', t: 'Then', body: 'Generate draft post via "Catalyst alert" template',  meta: 'Routes to Content Studio · review required' },
            ].map(s => (
              <div key={s.num} style={{ display: 'flex', gap: 10, position: 'relative' }}>
                <div style={{ width: 28, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                  <div style={{ width: 24, height: 24, borderRadius: 4, background: s.col + '20', border: '1px solid ' + s.col + '60', display: 'grid', placeItems: 'center', color: s.col, fontSize: 9, fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{s.num}</div>
                  <div style={{ width: 1, flex: 1, background: 'var(--border)', marginTop: 4 }}/>
                </div>
                <div style={{ flex: 1, paddingBottom: 8 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                    <span className="chip" style={{ color: s.col, borderColor: s.col + '60', background: s.col + '12', fontSize: 9 }}>{s.kind}</span>
                    <span className="mono" style={{ fontSize: 10, color: 'var(--text-4)' }}>{s.t}</span>
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text)' }}>{s.body}</div>
                  <div style={{ fontSize: 10.5, color: 'var(--text-4)', marginTop: 3 }} className="mono">{s.meta}</div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Logs */}
      <div style={{ marginTop: 12 }}>
        <Card title="Action log" sub="LAST 24H · 42 EVENTS" right={<><span className="chip teal">Success 41</span><span className="chip warn">Retry 1</span></>} noPad>
          <table className="tbl">
            <thead><tr><th style={{ width: 130 }}>Timestamp</th><th>Rule</th><th>Trigger payload</th><th>Action</th><th>Duration</th><th>State</th></tr></thead>
            <tbody>
              {[
                ['07:42:14','AUT-08','BTC funding 0.0098% → 0.0142%','Created opp card OPP-217 + Slack ping','428ms','OK'],
                ['07:42:01','AUT-06','BBG-78421 high-impact verified','Push notif to 12,840 subs','1.21s','OK'],
                ['07:21:39','AUT-08','BTC volume 38B / threshold 30B','Cooldown — skipped','12ms','SKIP'],
                ['07:18:02','AUT-07','MU +4.2% AH','Drafted "Micron beats" recap to Studio','3.41s','OK'],
                ['06:55:00','AUT-06','SEC delay SOL ETF (HIGH)','Push notif · queued draft','892ms','OK'],
                ['06:41:08','AUT-03','4,800 BTC outflow Coinbase','Slack #ops + alert card','312ms','OK'],
                ['06:12:11','AUT-06','MoF intervention confirmed (HIGH)','Push notif','1.10s','OK'],
                ['05:58:30','AUT-07','MU after-hours print','Awaiting transcript — retry queued','—','RETRY'],
              ].map((row, i) => (
                <tr key={i}>
                  <td className="mono">{row[0]}</td>
                  <td className="mono" style={{ color: 'var(--text-3)' }}>{row[1]}</td>
                  <td className="muted-2">{row[2]}</td>
                  <td>{row[3]}</td>
                  <td className="num muted">{row[4]}</td>
                  <td><span className={"chip " + (row[5] === 'OK' ? 'teal dot' : row[5] === 'RETRY' ? 'warn' : '')}>{row[5]}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>
    </div>
  );
}
window.AutomationScreen = AutomationScreen;
