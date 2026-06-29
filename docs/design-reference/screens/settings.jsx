function SettingsScreen() {
  const [tab, setTab] = React.useState('Profile');
  const tabs = ['Profile', 'Security', 'Sources', 'Theme', 'Billing', 'API', 'Admin'];

  return (
    <div className="section">
      <div className="tab-row" style={{ marginBottom: 12, display: 'inline-flex' }}>
        {tabs.map(t => <div key={t} className={"tab" + (t === tab ? ' active' : '')} onClick={() => setTab(t)}>{t}</div>)}
      </div>

      <div className="grid" style={{ gridTemplateColumns: '1fr 320px', gap: 12 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {tab === 'Profile' && (
            <>
              <Card title="Profile">
                <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 16 }}>
                  <div style={{ width: 60, height: 60, borderRadius: 50, background: 'linear-gradient(135deg, #232F42, #10151D)', border: '1px solid var(--border-strong)', display: 'grid', placeItems: 'center', fontSize: 20, fontFamily: 'var(--font-mono)' }}>JM</div>
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 600 }}>Jordan Mehta</div>
                    <div className="mono" style={{ fontSize: 10.5, color: 'var(--text-3)' }}>jordan@oryx.app · EDITOR-IN-CHIEF · OWNER</div>
                    <button className="btn ghost" style={{ marginTop: 6, fontSize: 10.5 }}><Icon.Upload size={11}/> Replace avatar</button>
                  </div>
                </div>
                {[
                  ['Display name', 'Jordan Mehta'],
                  ['Public handle', '@jordanmehta'],
                  ['Time zone', 'America/New_York (ET)'],
                  ['Language', 'English (US)'],
                  ['Default workspace', 'ORYX Editorial'],
                ].map((f, i) => (
                  <div key={f[0]} style={{ display: 'grid', gridTemplateColumns: '160px 1fr', alignItems: 'center', padding: '8px 0', borderBottom: i < 4 ? '1px solid var(--hairline)' : 'none' }}>
                    <div style={{ fontSize: 11.5, color: 'var(--text-3)' }}>{f[0]}</div>
                    <div style={{ display: 'flex', gap: 8 }}>
                      <input defaultValue={f[1]} style={{ background: 'var(--elev)', border: '1px solid var(--border)', borderRadius: 4, padding: '5px 9px', color: 'var(--text)', fontSize: 12, fontFamily: 'var(--font-ui)', flex: 1 }}/>
                    </div>
                  </div>
                ))}
              </Card>

              <Card title="Notifications">
                {[
                  ['Morning brief digest', 'Daily, 06:00 ET', true],
                  ['Verified high-impact news', 'Real-time', true],
                  ['Conflict alerts', 'Real-time', true],
                  ['Approval requests', 'Real-time', true],
                  ['Weekly analytics summary', 'Mondays, 09:00 ET', false],
                  ['Academy nudges', 'Off', false],
                ].map((n, i) => (
                  <div key={n[0]} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '8px 0', borderBottom: i < 5 ? '1px solid var(--hairline)' : 'none' }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 12 }}>{n[0]}</div>
                      <div className="mono" style={{ fontSize: 10, color: 'var(--text-4)' }}>{n[1]}</div>
                    </div>
                    <div style={{ width: 28, height: 14, borderRadius: 8, background: n[2] ? 'var(--teal)' : 'var(--border-strong)', position: 'relative' }}>
                      <div style={{ position: 'absolute', top: 2, left: n[2] ? 16 : 2, width: 10, height: 10, borderRadius: 50, background: '#fff' }}/>
                    </div>
                  </div>
                ))}
              </Card>
            </>
          )}

          {tab === 'Security' && (
            <>
              <Card title="Authentication">
                <div style={{ padding: 6 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 0', borderBottom: '1px solid var(--hairline)' }}>
                    <Icon.Lock size={14} />
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 12 }}>Password</div>
                      <div className="mono" style={{ fontSize: 10, color: 'var(--text-4)' }}>ARGON2ID · LAST CHANGED 42 DAYS AGO</div>
                    </div>
                    <button className="btn ghost" style={{ fontSize: 10.5 }}>Update</button>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 0', borderBottom: '1px solid var(--hairline)' }}>
                    <Icon.Shield size={14} />
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 12 }}>Multi-factor authentication</div>
                      <div className="mono" style={{ fontSize: 10, color: 'var(--teal)' }}>HARDWARE KEY · WEBAUTHN</div>
                    </div>
                    <span className="chip teal dot" style={{ fontSize: 9 }}>ACTIVE</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 0' }}>
                    <Icon.Cpu size={14} />
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 12 }}>Trusted devices</div>
                      <div className="mono" style={{ fontSize: 10, color: 'var(--text-4)' }}>3 ACTIVE · 2 EXPIRE SOON</div>
                    </div>
                    <button className="btn ghost" style={{ fontSize: 10.5 }}>Manage</button>
                  </div>
                </div>
              </Card>

              <Card title="Active sessions" sub="3 DEVICES" noPad>
                <table className="tbl">
                  <thead><tr><th>Device</th><th>Location</th><th>Last active</th><th>IP</th><th></th></tr></thead>
                  <tbody>
                    {[
                      ['MacBook Pro · Chrome',  'Brooklyn, NY', 'Just now',     '74.91.…',  true],
                      ['iPhone 15 Pro · Safari','Brooklyn, NY', '34m ago',     '174.62.…', false],
                      ['iPad · ORYX Mobile',    'Brooklyn, NY', '2 days ago',  '174.62.…', false],
                    ].map((r, i) => (
                      <tr key={i}>
                        <td style={{ color: 'var(--text)' }}>{r[0]}</td>
                        <td className="muted-2">{r[1]}</td>
                        <td className="mono">{r[2]}</td>
                        <td className="mono muted">{r[3]}</td>
                        <td>{r[4] ? <span className="chip teal dot" style={{ fontSize: 9 }}>CURRENT</span> : <button className="btn ghost" style={{ fontSize: 10.5 }}>Revoke</button>}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>

              <Card title="Audit log · recent">
                {[
                  ['07:42','jordan.m logged in','MacBook Pro · 74.91.…','OK'],
                  ['07:43','jordan.m approved CL-1408','—','OK'],
                  ['06:18','alex.k merged PKT-43 section', '—','OK'],
                  ['00:14','API token rotated · oryx-prod-key','automation','OK'],
                  ['Jun 27 22:08','mira.s 2FA reset request','iPhone Safari','APPROVED'],
                ].map((r, i) => (
                  <div key={i} style={{ display: 'grid', gridTemplateColumns: '90px 1fr 1fr 80px', gap: 8, padding: '5px 0', borderBottom: i < 4 ? '1px solid var(--hairline)' : 'none', fontSize: 11 }}>
                    <span className="mono muted">{r[0]}</span>
                    <span>{r[1]}</span>
                    <span className="muted-2">{r[2]}</span>
                    <span className="chip teal" style={{ fontSize: 9 }}>{r[3]}</span>
                  </div>
                ))}
              </Card>
            </>
          )}

          {tab === 'Sources' && (
            <Card title="Source trust catalog" sub="142 SOURCES · 6 TIERS" noPad>
              <table className="tbl">
                <thead><tr><th>Source</th><th>Tier</th><th>Type</th><th className="num">Trust</th><th className="num">Verified</th><th className="num">Conflicts</th><th>State</th></tr></thead>
                <tbody>
                  {[
                    ['EDGAR / SEC',         'PRIMARY',  'Filing',    100, 412, 0,  'on'],
                    ['Eurostat',            'PRIMARY',  'Data',      100, 38,  0,  'on'],
                    ['Federal Reserve',     'PRIMARY',  'Statement', 100, 92,  0,  'on'],
                    ['Bloomberg Terminal',  'TIER-1',   'News',      96,  840, 4,  'on'],
                    ['Reuters',             'TIER-1',   'News',      94,  680, 6,  'on'],
                    ['Financial Times',     'TIER-1',   'News',      93,  410, 3,  'on'],
                    ['Wall Street Journal', 'TIER-1',   'News',      92,  388, 5,  'on'],
                    ['Farside Investors',   'TIER-1',   'Data',      96,  124, 0,  'on'],
                    ['Glassnode',           'TIER-2',   'On-chain',  88,  220, 4,  'on'],
                    ['CoinDesk',            'TIER-2',   'News',      78,  140, 12, 'on'],
                    ['The Block',           'TIER-2',   'News',      82,  98,  6,  'on'],
                    ['X (curated list)',    'TIER-3',   'Social',    52,  44,  18, 'on'],
                    ['Substack OSINT',      'TIER-3',   'Newsletter',58,  22,  8,  'review'],
                    ['Anonymous tip line',  'QUARANTINE','Social',   18,  2,   12, 'off'],
                  ].map((r, i) => (
                    <tr key={i}>
                      <td style={{ color: 'var(--text)' }}>{r[0]}</td>
                      <td><span className={"chip " + (r[1] === 'PRIMARY' ? 'teal' : r[1] === 'TIER-1' ? 'indigo' : r[1] === 'QUARANTINE' ? 'neg' : '')} style={{ fontSize: 9 }}>{r[1]}</span></td>
                      <td className="muted-2">{r[2]}</td>
                      <td className="num">
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6, justifyContent: 'flex-end' }}>
                          <div className="meter" style={{ width: 50 }}><div className={"meter-fill " + (r[3] < 50 ? 'neg' : r[3] > 85 ? 'teal' : '')} style={{ width: r[3]+'%' }}/></div>
                          <span style={{ width: 24 }}>{r[3]}</span>
                        </div>
                      </td>
                      <td className="num">{r[4]}</td>
                      <td className={"num " + (r[5] > 10 ? 'neg' : '')}>{r[5]}</td>
                      <td><span className={"chip " + (r[6] === 'on' ? 'teal dot' : r[6] === 'review' ? 'warn' : 'neg')} style={{ fontSize: 9 }}>{r[6]}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          )}

          {tab === 'Theme' && (
            <Card title="Appearance">
              <div style={{ padding: 4 }}>
                <div className="mono" style={{ fontSize: 9.5, color: 'var(--text-4)', letterSpacing: '0.12em', marginBottom: 8 }}>BASE</div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
                  {[
                    { n: 'Obsidian', a: '#05070A', b: '#0A0E14', c: '#10151D', active: true },
                    { n: 'Midnight Navy', a: '#06091A', b: '#0A1024', c: '#101830' },
                    { n: 'Ink',      a: '#0A0A0E', b: '#13131A', c: '#1A1A22' },
                  ].map(t => (
                    <div key={t.n} style={{ padding: 10, background: t.b, border: '1px solid ' + (t.active ? 'var(--violet)' : 'var(--border)'), borderRadius: 6, cursor: 'pointer' }}>
                      <div style={{ display: 'flex', gap: 4, marginBottom: 8 }}>
                        <div style={{ width: 24, height: 24, background: t.a, borderRadius: 3 }}/>
                        <div style={{ width: 24, height: 24, background: t.b, border: '1px solid var(--border)', borderRadius: 3 }}/>
                        <div style={{ width: 24, height: 24, background: t.c, borderRadius: 3 }}/>
                      </div>
                      <div style={{ fontSize: 11.5, color: 'var(--text)' }}>{t.n}</div>
                      <div className="mono" style={{ fontSize: 9.5, color: 'var(--text-4)' }}>{t.active ? 'ACTIVE' : 'PREVIEW'}</div>
                    </div>
                  ))}
                </div>

                <div className="mono" style={{ fontSize: 9.5, color: 'var(--text-4)', letterSpacing: '0.12em', marginTop: 18, marginBottom: 8 }}>ACCENT</div>
                <div style={{ display: 'flex', gap: 10 }}>
                  {[
                    { n: 'Indigo · Violet', g: 'linear-gradient(135deg, #5B5BF5, #8B5CF6)', active: true },
                    { n: 'Aurora Teal',     g: 'linear-gradient(135deg, #0EA5A0, #14B8A6)' },
                    { n: 'Violet',          g: 'linear-gradient(135deg, #7C3AED, #C026D3)' },
                    { n: 'Soft Blue',       g: 'linear-gradient(135deg, #2563EB, #60A5FA)' },
                  ].map(a => (
                    <div key={a.n} style={{ flex: 1, padding: 10, border: '1px solid ' + (a.active ? 'var(--violet)' : 'var(--border)'), borderRadius: 6, cursor: 'pointer' }}>
                      <div style={{ height: 24, background: a.g, borderRadius: 3, marginBottom: 8 }}/>
                      <div style={{ fontSize: 11, color: 'var(--text)' }}>{a.n}</div>
                    </div>
                  ))}
                </div>

                <div className="mono" style={{ fontSize: 9.5, color: 'var(--text-4)', letterSpacing: '0.12em', marginTop: 18, marginBottom: 8 }}>DENSITY · TYPOGRAPHY</div>
                <div style={{ display: 'flex', gap: 16, fontSize: 12 }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}><input type="radio" defaultChecked/> Compact</label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}><input type="radio"/> Cozy</label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 6, marginLeft: 'auto' }}><input type="checkbox" defaultChecked/> Mono numerals</label>
                </div>
              </div>
            </Card>
          )}

          {tab === 'Billing' && (
            <Card title="Plan">
              <div style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
                {[
                  { n: 'Starter', p: 'Free',     items: ['1 workspace','Read-only AI','Basic verification'] },
                  { n: 'Editorial', p: '$49/mo', items: ['5 members','Full AI Analyst','Automation Hub','Priority sources'], active: true },
                  { n: 'Pro newsroom', p: '$249/mo', items: ['25 members','SSO','Audit retention','Custom sources'] },
                ].map(p => (
                  <div key={p.n} style={{ flex: 1, padding: 14, background: 'var(--panel)', border: '1px solid ' + (p.active ? 'var(--violet)' : 'var(--border)'), borderRadius: 6 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span style={{ fontSize: 13, fontWeight: 600 }}>{p.n}</span>
                      {p.active && <span className="chip violet" style={{ fontSize: 9 }}>CURRENT</span>}
                    </div>
                    <div className="mono" style={{ fontSize: 18, marginTop: 6 }}>{p.p}</div>
                    {p.items.map(i => <div key={i} style={{ fontSize: 11, color: 'var(--text-2)', padding: '3px 0' }}><Icon.Check size={10}/> {i}</div>)}
                  </div>
                ))}
              </div>
              <table className="tbl">
                <thead><tr><th>Date</th><th>Description</th><th className="num">Amount</th><th>Status</th></tr></thead>
                <tbody>
                  {[
                    ['Jun 01', 'Editorial · monthly', '$245.00', 'PAID'],
                    ['May 01', 'Editorial · monthly', '$245.00', 'PAID'],
                    ['Apr 01', 'Editorial · monthly', '$196.00', 'PAID'],
                  ].map(r => (
                    <tr key={r[0]}><td className="mono">{r[0]}</td><td>{r[1]}</td><td className="num">{r[2]}</td><td><span className="chip teal" style={{ fontSize: 9 }}>{r[3]}</span></td></tr>
                  ))}
                </tbody>
              </table>
            </Card>
          )}

          {tab === 'API' && (
            <Card title="API tokens" sub="4 ACTIVE" right={<button className="btn primary" style={{ fontSize: 10.5 }}><Icon.Plus size={11}/> New token</button>} noPad>
              <table className="tbl">
                <thead><tr><th>Label</th><th>Token</th><th>Scope</th><th>Created</th><th>Expires</th><th>State</th></tr></thead>
                <tbody>
                  {[
                    ['oryx-prod-key',    'sk_live_••••••8a4f', 'rw:claims, ro:packets', 'Jun 12', 'Sep 12', 'on'],
                    ['intake-webhook',   'sk_live_••••••2c1b', 'rw:intake',              'May 04', 'Aug 04', 'on'],
                    ['readonly-analyst', 'sk_live_••••••91da', 'ro:all',                  'Apr 18', 'Jul 18', 'expiring'],
                    ['legacy-zapier',    'sk_live_••••••4d77', 'rw:publish',              'Jan 14', 'Jul 14', 'expiring'],
                  ].map(r => (
                    <tr key={r[0]}>
                      <td style={{ color: 'var(--text)' }}>{r[0]}</td>
                      <td className="mono muted">{r[1]}</td>
                      <td className="mono" style={{ fontSize: 10, color: 'var(--text-2)' }}>{r[2]}</td>
                      <td className="mono muted">{r[3]}</td>
                      <td className="mono muted">{r[4]}</td>
                      <td><span className={"chip " + (r[5] === 'on' ? 'teal dot' : 'warn')} style={{ fontSize: 9 }}>{r[5]}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          )}

          {tab === 'Admin' && (
            <Card title="Workspace administration">
              {[
                ['Workspace name', 'ORYX Editorial'],
                ['Workspace slug', 'anant-capital'],
                ['Default visibility', 'Private'],
                ['Feature flags', '12 enabled · 4 in preview'],
                ['Audit retention', '12 months'],
                ['Data export', 'Last export: Jun 24'],
                ['SSO · SAML', 'Not configured'],
                ['IP allowlist', '3 ranges'],
              ].map((r, i) => (
                <div key={r[0]} style={{ display: 'grid', gridTemplateColumns: '180px 1fr 100px', alignItems: 'center', padding: '8px 0', borderBottom: i < 7 ? '1px solid var(--hairline)' : 'none' }}>
                  <div style={{ fontSize: 11.5, color: 'var(--text-3)' }}>{r[0]}</div>
                  <div style={{ fontSize: 12, color: 'var(--text)' }}>{r[1]}</div>
                  <button className="btn ghost" style={{ fontSize: 10.5, justifySelf: 'flex-end' }}>Configure</button>
                </div>
              ))}
            </Card>
          )}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <Card title="Workspace at a glance">
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', fontSize: 11.5 }}><span className="muted">Plan</span><span className="chip violet">EDITORIAL</span></div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', fontSize: 11.5 }}><span className="muted">Seats</span><span className="mono">7 / 10</span></div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', fontSize: 11.5 }}><span className="muted">AI credits</span><span className="mono">42K / 80K</span></div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', fontSize: 11.5 }}><span className="muted">Data retention</span><span className="mono">12 months</span></div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', fontSize: 11.5 }}><span className="muted">Created</span><span className="mono">May 14, 2023</span></div>
          </Card>

          <Card title="Danger zone" sub="OWNER ONLY">
            {[
              ['Rotate all API tokens',     'Forces re-auth of integrations'],
              ['Export workspace · ZIP',    'Snapshot of all data'],
              ['Transfer ownership',        'Hand off to another admin'],
              ['Delete workspace',          'Permanent · irreversible'],
            ].map((a, i) => (
              <div key={a[0]} style={{ padding: '7px 0', borderBottom: i < 3 ? '1px solid var(--hairline)' : 'none' }}>
                <div style={{ display: 'flex', alignItems: 'center' }}>
                  <span style={{ fontSize: 12, color: i === 3 ? 'var(--neg)' : 'var(--text)' }}>{a[0]}</span>
                  <button className="btn ghost" style={{ marginLeft: 'auto', fontSize: 10.5, color: i === 3 ? 'var(--neg)' : undefined }}>{i === 3 ? 'Delete' : 'Run'}</button>
                </div>
                <div className="mono" style={{ fontSize: 9.5, color: 'var(--text-4)', marginTop: 2 }}>{a[1]}</div>
              </div>
            ))}
          </Card>
        </div>
      </div>
    </div>
  );
}
window.SettingsScreen = SettingsScreen;
