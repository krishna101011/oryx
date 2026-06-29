function AcademyScreen() {
  const courses = [
    { code: 'ORYX-101', title: 'Foundations of Financial Intelligence',  lvl: 'Beginner',   mins: 84, pct: 100, mod: 8,  cert: true,  col: '#8B5CF6' },
    { code: 'ORYX-201', title: 'Source Verification & Confidence Models', lvl: 'Intermediate', mins: 124, pct: 64,  mod: 10, cert: false, col: '#14B8A6', active: true },
    { code: 'ORYX-301', title: 'Building a Research Packet',              lvl: 'Intermediate', mins: 96,  pct: 22,  mod: 9,  cert: false, col: '#60A5FA' },
    { code: 'ORYX-302', title: 'On-chain Forensics for Editors',          lvl: 'Advanced',     mins: 142, pct: 0,   mod: 12, cert: false, col: '#A855F7' },
    { code: 'ORYX-401', title: 'Macro Frameworks for the Modern Cycle',   lvl: 'Advanced',     mins: 188, pct: 0,   mod: 14, cert: false, col: '#F59E0B' },
    { code: 'ORYX-501', title: 'AI Co-piloting Your Newsroom',            lvl: 'Pro',          mins: 76,  pct: 0,   mod: 6,  cert: false, col: '#5B5BF5' },
  ];
  const lessons = [
    { n: '04.1', t: 'Primary vs. secondary sources',          done: true,  d: '8 min' },
    { n: '04.2', t: 'Trust-score components',                  done: true,  d: '12 min' },
    { n: '04.3', t: 'Quote vs. paraphrase: epistemic typing',  done: true,  d: '14 min' },
    { n: '04.4', t: 'Building the confidence meter (math)',    done: true,  d: '22 min' },
    { n: '05.1', t: 'Conflict detection workflow',             done: false, active: true, d: '18 min' },
    { n: '05.2', t: 'Case study: rumor vs. report',            done: false, d: '12 min' },
    { n: '05.3', t: 'Practical exercise · Verify 5 claims',    done: false, d: '24 min' },
    { n: '06.1', t: 'Quiz · Sources & verification',           done: false, d: '15 min' },
  ];

  return (
    <div className="section">
      <div className="grid g-3" style={{ marginBottom: 12 }}>
        <Kpi label="Courses enrolled"    val="6"   delta="2 in progress" />
        <Kpi label="Lessons completed"   val="42 / 81" delta="52% · cohort avg 38%" deltaPos />
        <Kpi label="Certifications earned" val="1"  delta="ORYX Foundations · May 2024" />
      </div>

      <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
        {courses.map(c => (
          <div key={c.code} style={{ background: 'var(--panel)', border: '1px solid ' + (c.active ? c.col + '40' : 'var(--border)'), borderRadius: 6, padding: 14, cursor: 'pointer' }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
              <div style={{ width: 56, height: 56, borderRadius: 6, background: c.col + '15', border: '1px solid ' + c.col + '40', display: 'grid', placeItems: 'center', color: c.col, fontSize: 11, fontFamily: 'var(--font-mono)', fontWeight: 600, letterSpacing: '0.05em' }}>
                {c.code.split('-')[1]}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                  <span className="mono" style={{ fontSize: 10, color: 'var(--text-4)' }}>{c.code}</span>
                  <span className="chip" style={{ fontSize: 9 }}>{c.lvl}</span>
                  {c.cert && <span className="chip teal dot" style={{ fontSize: 9 }}>CERTIFIED</span>}
                </div>
                <div style={{ fontSize: 13.5, fontWeight: 500, color: 'var(--text)', marginBottom: 4 }}>{c.title}</div>
                <div style={{ fontSize: 10.5, color: 'var(--text-3)' }} className="mono">{c.mod} MODULES · {c.mins} MIN</div>
                <div style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div className="meter" style={{ flex: 1 }}><div className="meter-fill" style={{ width: c.pct + '%' }}/></div>
                  <span className="mono" style={{ fontSize: 10.5, color: 'var(--text)' }}>{c.pct}%</span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Lesson viewer */}
      <Card title="ORYX-201 · Module 5: Conflict Detection" sub="LESSON 5.1 · 18 MIN" right={<><span className="chip teal dot">IN PROGRESS</span></>}>
        <div className="grid" style={{ gridTemplateColumns: '260px 1fr', gap: 16 }}>
          <div style={{ borderRight: '1px solid var(--border)', paddingRight: 12 }}>
            {lessons.map((l, i) => (
              <div key={l.n} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 0', borderBottom: i < lessons.length-1 ? '1px solid var(--hairline)' : 'none', cursor: 'pointer', background: l.active ? 'rgba(20,184,166,0.06)' : undefined, marginLeft: l.active ? -8 : 0, marginRight: l.active ? -8 : 0, paddingLeft: l.active ? 8 : 0, paddingRight: l.active ? 8 : 0, borderRadius: 3 }}>
                <div style={{ width: 14, height: 14, borderRadius: 50, border: '1px solid ' + (l.done ? 'var(--teal)' : 'var(--border-strong)'), background: l.done ? 'var(--teal)' : 'transparent', display: 'grid', placeItems: 'center' }}>
                  {l.done && <Icon.Check size={9} stroke={3} />}
                </div>
                <span className="mono" style={{ fontSize: 10, color: 'var(--text-3)', width: 28 }}>{l.n}</span>
                <span style={{ fontSize: 11, flex: 1, color: l.active ? 'var(--text)' : 'var(--text-2)' }}>{l.t}</span>
                <span className="mono" style={{ fontSize: 9.5, color: 'var(--text-4)' }}>{l.d}</span>
              </div>
            ))}
          </div>
          <div>
            <div style={{ background: 'linear-gradient(135deg, #10151D, #0A0E14)', border: '1px solid var(--border)', borderRadius: 6, aspectRatio: '16/9', position: 'relative', display: 'grid', placeItems: 'center', overflow: 'hidden' }}>
              <div style={{ position: 'absolute', inset: 0, opacity: 0.4 }}><div className="horn-watermark" style={{ opacity: 0.1 }}><HornMark size={300}/></div></div>
              <div style={{ width: 60, height: 60, borderRadius: 50, background: 'var(--accent-grad)', display: 'grid', placeItems: 'center', boxShadow: '0 12px 40px rgba(139,92,246,0.4)', cursor: 'pointer' }}>
                <Icon.Play size={22}/>
              </div>
              <div style={{ position: 'absolute', bottom: 12, left: 12, right: 12, display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{ height: 3, flex: 1, background: 'rgba(255,255,255,0.1)', borderRadius: 2 }}>
                  <div style={{ width: '34%', height: '100%', background: 'var(--accent-grad)', borderRadius: 2 }}/>
                </div>
                <span className="mono" style={{ fontSize: 10, color: '#fff' }}>06:14 / 18:22</span>
              </div>
            </div>
            <h2 style={{ fontSize: 16, fontWeight: 600, marginTop: 14 }}>Conflict detection workflow</h2>
            <p style={{ fontSize: 12, color: 'var(--text-2)', lineHeight: 1.6 }}>
              When two trusted sources disagree on a quantitative claim, the verification engine flags a conflict. In this lesson we walk through the conflict-review surface, how to interpret the diff, and when to escalate vs. quietly absorb the discrepancy.
            </p>
            <div style={{ display: 'flex', gap: 6, marginTop: 12 }}>
              <button className="btn"><Icon.Download size={11}/> Transcript</button>
              <button className="btn"><Icon.Book size={11}/> Reading list (4)</button>
              <button className="btn primary" style={{ marginLeft: 'auto' }}>Next lesson →</button>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
window.AcademyScreen = AcademyScreen;
