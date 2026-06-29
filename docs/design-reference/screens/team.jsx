function TeamScreen() {
  const members = [
    { name: 'Jordan Mehta',  role: 'Editor-in-chief', email: 'jordan@oryx.app',  state: 'online',  acl: 'OWNER',  joined: 'May 2023', mfa: true,  init: 'JM' },
    { name: 'Alex Kazakov',  role: 'Research lead',   email: 'alex@oryx.app',     state: 'online',  acl: 'ADMIN',  joined: 'Jul 2023', mfa: true,  init: 'AK' },
    { name: 'Mira Sato',     role: 'Compliance',      email: 'mira@oryx.app',     state: 'idle',    acl: 'EDITOR', joined: 'Sep 2023', mfa: true,  init: 'MS' },
    { name: 'Dean Velasco',  role: 'Markets analyst', email: 'dean@oryx.app',     state: 'online',  acl: 'EDITOR', joined: 'Nov 2023', mfa: true,  init: 'DV' },
    { name: 'Priya Iyer',    role: 'On-chain analyst',email: 'priya@oryx.app',    state: 'offline', acl: 'EDITOR', joined: 'Jan 2024', mfa: true,  init: 'PI' },
    { name: 'Theo Brandt',   role: 'Distribution',    email: 'theo@oryx.app',     state: 'online',  acl: 'CONTRIB',joined: 'Mar 2024', mfa: false, init: 'TB' },
    { name: 'Yuki Tan',      role: 'Designer',        email: 'yuki@oryx.app',     state: 'offline', acl: 'CONTRIB',joined: 'Apr 2024', mfa: true,  init: 'YT' },
    { name: 'Pending invite', role: '—',              email: 'sara@example.com', state: 'pending', acl: 'EDITOR', joined: '—',         mfa: false, init: 'SA' },
  ];

  return (
    <div className="section">
      <div className="grid g-4" style={{ marginBottom: 12 }}>
        <Kpi label="Workspaces"    val="2" delta="ORYX Editorial · Personal" />
        <Kpi label="Active members" val="7"  delta="1 pending invite" />
        <Kpi label="Shared assets"  val="142" delta="Brand · Sources · Templates" />
        <Kpi label="API tokens"     val="4"  delta="2 expire <30d" />
      </div>

      <div className="grid" style={{ gridTemplateColumns: '1fr 320px', gap: 12 }}>
        <Card title="Members" sub="8 PEOPLE · ORYX EDITORIAL" right={<button className="btn primary"><Icon.Plus size={11}/> Invite</button>} noPad>
          <table className="tbl">
            <thead><tr><th>Member</th><th>Role</th><th>Email</th><th>Access</th><th>Joined</th><th>MFA</th><th>Status</th><th></th></tr></thead>
            <tbody>
              {members.map(m => (
                <tr key={m.email}>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <div className="avatar" style={{ width: 22, height: 22, fontSize: 9 }}>{m.init}</div>
                      <span style={{ color: 'var(--text)', fontWeight: 500 }}>{m.name}</span>
                    </div>
                  </td>
                  <td className="muted-2">{m.role}</td>
                  <td className="muted">{m.email}</td>
                  <td><span className={"chip " + (m.acl === 'OWNER' ? 'violet' : m.acl === 'ADMIN' ? 'indigo' : '')} style={{ fontSize: 9 }}>{m.acl}</span></td>
                  <td className="mono muted">{m.joined}</td>
                  <td>{m.mfa ? <span className="chip teal" style={{ fontSize: 9 }}>ON</span> : <span className="chip warn" style={{ fontSize: 9 }}>OFF</span>}</td>
                  <td>
                    <span className={"chip " + (m.state === 'online' ? 'teal dot' : m.state === 'pending' ? 'warn' : '')} style={{ fontSize: 9 }}>{m.state}</span>
                  </td>
                  <td><button className="btn ghost" style={{ fontSize: 10.5, padding: '2px 6px' }}>Manage</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <Card title="Roles · capability matrix">
            {[
              ['OWNER',  ['Full', 'Full', 'Full', 'Full']],
              ['ADMIN',  ['Full', 'Full', 'Full', '—']],
              ['EDITOR', ['Full', 'Full', 'Read', '—']],
              ['CONTRIB',['Read', 'Write', '—',   '—']],
            ].map(r => (
              <div key={r[0]} style={{ display: 'grid', gridTemplateColumns: '70px repeat(4, 1fr)', gap: 4, padding: '5px 0', borderBottom: '1px solid var(--hairline)', alignItems: 'center' }}>
                <span className="chip" style={{ fontSize: 9, justifyContent: 'center' }}>{r[0]}</span>
                {r[1].map((v, i) => (
                  <span key={i} className="mono" style={{ fontSize: 10, textAlign: 'center', color: v === 'Full' ? 'var(--teal)' : v === '—' ? 'var(--text-4)' : 'var(--text-2)' }}>{v}</span>
                ))}
              </div>
            ))}
            <div className="mono" style={{ fontSize: 9, color: 'var(--text-4)', display: 'grid', gridTemplateColumns: '70px repeat(4, 1fr)', gap: 4, padding: '4px 0 0', letterSpacing: '0.06em' }}>
              <span></span><span style={{ textAlign: 'center' }}>VIEW</span><span style={{ textAlign: 'center' }}>EDIT</span><span style={{ textAlign: 'center' }}>PUB</span><span style={{ textAlign: 'center' }}>BILL</span>
            </div>
          </Card>

          <Card title="Shared assets">
            {[
              { t: 'Brand kit',          n: '24 assets',    ic: 'Layers' },
              { t: 'Verified sources',   n: '142 sources',  ic: 'Shield' },
              { t: 'Templates',          n: '14 templates', ic: 'Pen' },
              { t: 'Saved screeners',    n: '7 views',      ic: 'Filter' },
              { t: 'Watchlists',         n: '6 lists',      ic: 'Eye' },
            ].map((a, i) => {
              const Ic = Icon[a.ic];
              return (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '7px 0', borderBottom: i < 4 ? '1px solid var(--hairline)' : 'none' }}>
                  <div style={{ width: 24, height: 24, borderRadius: 4, background: 'var(--elev)', border: '1px solid var(--border)', display: 'grid', placeItems: 'center', color: 'var(--violet)' }}><Ic size={12}/></div>
                  <span style={{ flex: 1, fontSize: 11.5 }}>{a.t}</span>
                  <span className="mono" style={{ fontSize: 10, color: 'var(--text-4)' }}>{a.n}</span>
                </div>
              );
            })}
          </Card>
        </div>
      </div>
    </div>
  );
}
window.TeamScreen = TeamScreen;
