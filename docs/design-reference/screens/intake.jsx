function IntakeScreen() {
  const channels = [
    { name: 'Gmail intake',        ic: 'Mail',    cnt: 184, last: '2s',  state: 'on',  rate: '~76/h', col: '#EA4335' },
    { name: 'RSS feeds (24)',      ic: 'Rss',     cnt: 412, last: '8s',  state: 'on',  rate: '~170/h', col: '#F26522' },
    { name: 'Webhook · /v1/intake',ic: 'Webhook', cnt: 96,  last: '14s', state: 'on',  rate: '~40/h',  col: '#8B5CF6' },
    { name: 'API pull · Farside',  ic: 'Download',cnt: 14,  last: '4m',  state: 'on',  rate: 'cron 5m',col: '#14B8A6' },
    { name: 'API pull · EDGAR',    ic: 'Download',cnt: 8,   last: '12m', state: 'on',  rate: 'cron 15m',col: '#60A5FA' },
    { name: 'Slack ingest',         ic: 'Inbox',  cnt: 22,  last: '40m', state: 'paused', rate: '—',   col: '#A8B0BF' },
  ];

  const stream = [
    ['07:48:14', 'rss',      'CoinDesk · "Vitalik on layer-2 fees"',       'OK',   'norm·dedupe·v2'],
    ['07:48:09', 'gmail',    'Bloomberg alert: NVDA after-hours +3.4%',    'OK',   'norm·v2'],
    ['07:48:02', 'webhook',  'POST /v1/intake from "tradingview-alerts"',  'OK',   'idempotent · 200'],
    ['07:47:58', 'apipull',  'Farside ETF flows batch (24h)',              'OK',   '14 rows · cdc'],
    ['07:47:42', 'rss',      'Reuters · "Eurozone CPI 2.5%"',              'OK',   'dedupe→hit'],
    ['07:47:31', 'gmail',    'WSJ alert: Micron beat',                      'OK',   'norm·v2'],
    ['07:47:14', 'webhook',  'POST /v1/intake from "glassnode-alerts"',     'RETRY','429 · backoff 2s'],
    ['07:47:02', 'gmail',    'Marketing newsletter (filtered)',             'SKIP', 'rule: low-trust sender'],
    ['07:46:54', 'rss',      'CoinDesk · "BTC ETF flow recap"',              'OK',   'dedupe→variant'],
    ['07:46:39', 'webhook',  'POST /v1/intake from "x-bot"',                 'DLQ',  'schema mismatch'],
    ['07:46:18', 'apipull',  'EDGAR amendment batch',                       'OK',   '3 rows'],
    ['07:46:01', 'gmail',    'Federal Reserve · Williams speech preview',   'OK',   'norm·v2 · primary'],
  ];

  return (
    <div className="section">
      <div className="grid g-4" style={{ marginBottom: 12 }}>
        <Kpi label="Items ingested · 24h" val="6,842" delta="+12% vs avg" deltaPos sparkData={walk('in',24,0.06,0.005)} />
        <Kpi label="Dedupe ratio"          val="38.4%" delta="healthy" />
        <Kpi label="Norm. throughput"      val="142/min" delta="p95 latency 280ms" />
        <Kpi label="Dead-letter queue"     val="3"  delta="+1 in 24h" />
      </div>

      <div className="grid" style={{ gridTemplateColumns: '320px 1fr', gap: 12 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <Card title="Channels" sub="6 CONFIGURED" noPad>
            {channels.map((c, i) => {
              const Ic = Icon[c.ic];
              return (
                <div key={c.name} style={{ padding: '10px 12px', borderBottom: i < channels.length-1 ? '1px solid var(--hairline)' : 'none' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <div style={{ width: 26, height: 26, borderRadius: 5, background: c.col + '15', border: '1px solid ' + c.col + '40', display: 'grid', placeItems: 'center', color: c.col }}><Ic size={13}/></div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 11.5, color: 'var(--text)' }}>{c.name}</div>
                      <div className="mono" style={{ fontSize: 9.5, color: 'var(--text-4)' }}>{c.rate} · LAST {c.last}</div>
                    </div>
                    <span className={"chip " + (c.state === 'on' ? 'teal dot' : 'warn')} style={{ fontSize: 9 }}>{c.state}</span>
                  </div>
                  <div style={{ marginTop: 8 }}>
                    <svg viewBox="0 0 200 24" height="24" width="100%">
                      <polyline points={walk('ch-'+c.name, 24, 0.1).map((v,i) => `${(i/23)*200},${24-v*22-1}`).join(' ')} fill="none" stroke={c.col} strokeWidth="1"/>
                    </svg>
                  </div>
                </div>
              );
            })}
          </Card>

          <Card title="Dead-letter queue" sub="3 ITEMS">
            {[
              { c: 'webhook', e: 'x-bot · schema mismatch', t: '07:46' },
              { c: 'gmail',   e: 'Attachment decode error',  t: '06:14' },
              { c: 'rss',     e: 'Fetch timeout · feed.x.com', t: '04:02' },
            ].map((d, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 0', borderBottom: i < 2 ? '1px solid var(--hairline)' : 'none' }}>
                <span className="chip neg" style={{ fontSize: 9 }}>{d.c}</span>
                <span style={{ flex: 1, fontSize: 11.5 }}>{d.e}</span>
                <span className="mono" style={{ fontSize: 10, color: 'var(--text-4)' }}>{d.t}</span>
                <button className="btn ghost" style={{ fontSize: 10.5 }}>Retry</button>
              </div>
            ))}
          </Card>
        </div>

        <Card title="Live intake stream" sub="WS · /v1/intake · LIVE" right={<><span className="chip teal dot">CONNECTED</span><span className="mono" style={{ fontSize: 10, color: 'var(--text-4)' }}>p95 280ms · p99 1.4s</span></>} noPad>
          <table className="tbl">
            <thead><tr><th style={{ width: 90 }}>Time</th><th>Channel</th><th>Payload</th><th>Result</th><th>Pipeline</th></tr></thead>
            <tbody>
              {stream.map((r, i) => (
                <tr key={i}>
                  <td className="mono">{r[0]}</td>
                  <td><span className="chip" style={{ fontSize: 9 }}>{r[1]}</span></td>
                  <td style={{ color: 'var(--text)' }}>{r[2]}</td>
                  <td><span className={"chip " + (r[3] === 'OK' ? 'teal dot' : r[3] === 'RETRY' ? 'warn' : r[3] === 'DLQ' ? 'neg' : '')} style={{ fontSize: 9 }}>{r[3]}</span></td>
                  <td className="mono muted">{r[4]}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div style={{ padding: '8px 12px', borderTop: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="mono" style={{ fontSize: 10, color: 'var(--text-4)' }}>SHOWING LAST 12 OF 142 IN BUFFER</span>
            <div style={{ display: 'flex', gap: 6 }}>
              <button className="btn ghost" style={{ fontSize: 10.5 }}>Pause stream</button>
              <button className="btn ghost" style={{ fontSize: 10.5 }}><Icon.Download size={11}/> Export</button>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
window.IntakeScreen = IntakeScreen;
