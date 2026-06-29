// Shared primitives: HornMark logo, PageHead, Card, KPI, Spark, Heat, Candles SVG, etc.

const HornMark = ({ size = 28, glow = false }) => (
  <svg width={size} height={size} viewBox="0 0 200 200" fill="none" style={glow ? { filter: 'drop-shadow(0 0 18px rgba(20,184,166,0.5))' } : null}>
    <defs>
      <linearGradient id="hornGrad" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stopColor="#14B8A6" />
        <stop offset="1" stopColor="#0E8C82" />
      </linearGradient>
    </defs>
    {/* Left horn */}
    <path d="M82 50 C 58 80, 56 130, 78 160 C 84 168, 90 168, 92 160 C 94 130, 96 100, 92 75 C 90 60, 86 52, 82 50 Z" fill="url(#hornGrad)"/>
    {/* Right horn */}
    <path d="M118 50 C 142 80, 144 130, 122 160 C 116 168, 110 168, 108 160 C 106 130, 104 100, 108 75 C 110 60, 114 52, 118 50 Z" fill="url(#hornGrad)"/>
    {/* Inner curl detail */}
    <path d="M88 60 C 78 88, 80 130, 90 152" stroke="#05070A" strokeWidth="3" fill="none" strokeLinecap="round"/>
    <path d="M112 60 C 122 88, 120 130, 110 152" stroke="#05070A" strokeWidth="3" fill="none" strokeLinecap="round"/>
  </svg>
);

const PageHead = ({ title, sub, right, tabs, tab, onTab }) => (
  <div className="page-head">
    <div>
      <div className="title">{title}</div>
      {sub && <div className="sub" style={{ marginTop: 2 }}>{sub}</div>}
    </div>
    <div className="spacer" />
    {tabs && (
      <div className="tab-row">
        {tabs.map(t => (
          <div key={t} className={"tab" + (t === tab ? " active" : "")} onClick={() => onTab && onTab(t)}>{t}</div>
        ))}
      </div>
    )}
    {right}
  </div>
);

const Card = ({ title, sub, right, children, style, bodyStyle, noPad }) => (
  <div className="card" style={style}>
    {(title || right) && (
      <div className="card-head">
        {title && <div className="title">{title}</div>}
        {sub && <div className="sub">{sub}</div>}
        {right && <div className="right">{right}</div>}
      </div>
    )}
    <div className={noPad ? "" : "card-body"} style={bodyStyle}>{children}</div>
  </div>
);

const Kpi = ({ label, val, delta, deltaPos, sparkData, sparkPos = true }) => (
  <div className="kpi">
    <div className="label">{label}</div>
    <div className="val">{val}</div>
    {delta && <div className={"delta " + (deltaPos ? "pos" : "neg")}>{delta}</div>}
    {sparkData && (
      <svg className="micro" viewBox={`0 0 100 28`} preserveAspectRatio="none" style={{ width: '100%' }}>
        <polyline className={"spark " + (sparkPos ? "" : "neg")} points={sparkData.map((v, i) => `${(i / (sparkData.length - 1)) * 100},${28 - v * 28}`).join(' ')} />
      </svg>
    )}
  </div>
);

const Spark = ({ data, width = 60, height = 18, pos = true }) => {
  const max = Math.max(...data), min = Math.min(...data);
  const range = max - min || 1;
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
      <polyline className={"spark " + (pos ? "" : "neg")} points={data.map((v, i) => `${(i / (data.length - 1)) * width},${height - ((v - min) / range) * (height - 2) - 1}`).join(' ')} />
    </svg>
  );
};

// Pseudo-random walk seeded by string (deterministic)
const seed = (s) => {
  let h = 0; for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
  return () => { h = (h * 9301 + 49297) % 233280; return h / 233280; };
};
const walk = (s, n, vol = 0.05, drift = 0) => {
  const r = seed(s);
  let v = 0.5;
  const out = [];
  for (let i = 0; i < n; i++) {
    v += (r() - 0.5) * vol + drift;
    v = Math.max(0.05, Math.min(0.95, v));
    out.push(v);
  }
  return out;
};

// Candlestick chart in pure SVG. data = [{o,h,l,c}]
const Candles = ({ data, width = 800, height = 320, showGrid = true, showVol = true, color }) => {
  const pad = { l: 44, r: 56, t: 8, b: showVol ? 60 : 18 };
  const w = width, h = height;
  const innerW = w - pad.l - pad.r, innerH = h - pad.t - pad.b;
  const max = Math.max(...data.map(d => d.h));
  const min = Math.min(...data.map(d => d.l));
  const range = max - min;
  const y = v => pad.t + (1 - (v - min) / range) * innerH;
  const cw = innerW / data.length;
  const barW = Math.max(2, cw * 0.62);
  const grid = [];
  if (showGrid) {
    for (let i = 0; i <= 5; i++) {
      const v = min + (range * i) / 5;
      grid.push(<g key={i}>
        <line x1={pad.l} x2={w - pad.r} y1={y(v)} y2={y(v)} stroke="#1A2330" strokeDasharray="2 4" />
        <text x={w - pad.r + 6} y={y(v) + 3} fontSize="9" fill="#6B7588" fontFamily="JetBrains Mono">{v.toFixed(0)}</text>
        <text x={pad.l - 6} y={y(v) + 3} fontSize="9" fill="#4A5263" fontFamily="JetBrains Mono" textAnchor="end">{v.toFixed(0)}</text>
      </g>);
    }
  }
  // volume scale
  const maxV = Math.max(...data.map(d => d.v || 1));
  const volBase = h - 10;
  const volH = 40;
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{ display: 'block' }}>
      {grid}
      {data.map((d, i) => {
        const cx = pad.l + cw * (i + 0.5);
        const up = d.c >= d.o;
        const fill = up ? '#14B8A6' : '#F87171';
        const yo = y(d.o), yc = y(d.c), yh = y(d.h), yl = y(d.l);
        const top = Math.min(yo, yc), bh = Math.max(1, Math.abs(yc - yo));
        return (
          <g key={i}>
            <line x1={cx} x2={cx} y1={yh} y2={yl} stroke={fill} strokeWidth="1" />
            <rect x={cx - barW/2} y={top} width={barW} height={bh} fill={fill} opacity={up ? 0.85 : 0.85} />
            {showVol && d.v != null && (
              <rect x={cx - barW/2} y={volBase - (d.v / maxV) * volH} width={barW} height={(d.v / maxV) * volH} fill={fill} opacity="0.35" />
            )}
          </g>
        );
      })}
      {/* current price line */}
      {(() => {
        const last = data[data.length - 1].c;
        const ly = y(last);
        return <g>
          <line x1={pad.l} x2={w - pad.r} y1={ly} y2={ly} stroke="#8B5CF6" strokeDasharray="3 3" />
          <rect x={w - pad.r + 2} y={ly - 9} width={50} height={18} fill="#8B5CF6" rx="2" />
          <text x={w - pad.r + 27} y={ly + 4} fontSize="10" fontFamily="JetBrains Mono" fontWeight="600" fill="#fff" textAnchor="middle">{last.toFixed(0)}</text>
        </g>;
      })()}
    </svg>
  );
};

// Build BTC candles
const btcCandles = (n = 80, base = 64200) => {
  const r = seed('btc' + n);
  const arr = [];
  let p = base;
  for (let i = 0; i < n; i++) {
    const drift = (r() - 0.48) * 600;
    const o = p;
    const c = Math.max(45000, p + drift);
    const hi = Math.max(o, c) + r() * 300;
    const lo = Math.min(o, c) - r() * 300;
    const v = 0.3 + r() * 0.7;
    arr.push({ o, h: hi, l: lo, c, v });
    p = c;
  }
  return arr;
};

Object.assign(window, { HornMark, PageHead, Card, Kpi, Spark, Candles, walk, seed, btcCandles });
