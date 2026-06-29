// Shared demo data used across screens

const TICKERS = [
  { sym: 'BTC',    name: 'Bitcoin',         px: 64218.40, chg: +1.84, mc: '1.27T' },
  { sym: 'ETH',    name: 'Ethereum',        px: 3142.20,  chg: +0.42, mc: '378B' },
  { sym: 'SOL',    name: 'Solana',          px: 142.18,   chg: +3.21, mc: '64B' },
  { sym: 'SPX',    name: 'S&P 500',         px: 5247.10,  chg: -0.18, mc: '—' },
  { sym: 'NDX',    name: 'Nasdaq 100',      px: 18642.5,  chg: -0.32, mc: '—' },
  { sym: 'DXY',    name: 'US Dollar Index', px: 104.62,   chg: +0.11, mc: '—' },
  { sym: 'GOLD',   name: 'Gold spot',       px: 2342.10,  chg: +0.58, mc: '—' },
  { sym: 'OIL',    name: 'WTI Crude',       px: 81.42,    chg: -1.12, mc: '—' },
];

const NAV = [
  { group: 'INTELLIGENCE', items: [
    { id: 'home',    label: 'Command Center',  icon: 'Home', dot: true },
    { id: 'news',    label: 'News Intelligence', icon: 'News', badge: '42' },
    { id: 'verify',  label: 'Verification Center', icon: 'Shield', badge: '7' },
  ]},
  { group: 'RESEARCH', items: [
    { id: 'research', label: 'Research Workspace', icon: 'Beaker' },
    { id: 'ai',       label: 'AI Analyst', icon: 'Sparkles', badge: 'NEW' },
  ]},
  { group: 'MARKETS', items: [
    { id: 'technical',  label: 'Technical Analysis', icon: 'Chart' },
    { id: 'terminal',   label: 'Markets Terminal',   icon: 'Globe' },
    { id: 'opps',       label: 'Opportunities',      icon: 'Target', badge: '3' },
  ]},
  { group: 'PUBLISHING', items: [
    { id: 'content', label: 'Content Studio',  icon: 'Pen' },
    { id: 'publish', label: 'Publishing Center', icon: 'Send' },
  ]},
  { group: 'OPERATIONS', items: [
    { id: 'automation', label: 'Automation Hub', icon: 'Zap' },
    { id: 'analytics',  label: 'Analytics',      icon: 'Bar' },
    { id: 'intake',     label: 'Intake Engine',  icon: 'Inbox' },
  ]},
  { group: 'LEARN', items: [
    { id: 'academy', label: 'Academy', icon: 'Book' },
  ]},
  { group: 'SYSTEM', items: [
    { id: 'team',     label: 'Team',     icon: 'Users' },
    { id: 'settings', label: 'Settings', icon: 'Cog' },
  ]},
];

const SCREEN_META = {
  home:       { title: 'Command Center', sub: 'WORKSPACE / OVERVIEW', breadcrumb: ['Workspace', 'Command Center'] },
  news:       { title: 'News Intelligence', sub: 'INTAKE · VERIFIED FEED', breadcrumb: ['Intelligence', 'News'] },
  verify:     { title: 'Verification Center', sub: 'CLAIMS · EVIDENCE · CONFIDENCE', breadcrumb: ['Intelligence', 'Verification'] },
  research:   { title: 'Research Workspace', sub: 'PACKETS · NOTES · APPROVALS', breadcrumb: ['Research', 'Workspace'] },
  ai:         { title: 'AI Analyst', sub: 'MULTI-AGENT · SOURCE-BACKED', breadcrumb: ['Research', 'AI Analyst'] },
  technical:  { title: 'Technical Analysis', sub: 'CHART · INDICATORS · DRAWING', breadcrumb: ['Markets', 'Technical'] },
  terminal:   { title: 'Markets Terminal', sub: 'HEATMAP · SCREENER · CALENDARS', breadcrumb: ['Markets', 'Terminal'] },
  opps:       { title: 'Opportunities', sub: 'RADAR · CATALYSTS · RISK', breadcrumb: ['Markets', 'Opportunities'] },
  content:    { title: 'Content Studio', sub: 'DRAFT · TEMPLATES · APPROVALS', breadcrumb: ['Publishing', 'Studio'] },
  publish:    { title: 'Publishing Center', sub: 'SCHEDULE · CHANNELS · QUEUE', breadcrumb: ['Publishing', 'Center'] },
  automation: { title: 'Automation Hub', sub: 'RULES · TRIGGERS · LOGS', breadcrumb: ['Operations', 'Automation'] },
  analytics:  { title: 'Analytics', sub: 'KPIs · FUNNELS · ATTRIBUTION', breadcrumb: ['Operations', 'Analytics'] },
  intake:     { title: 'Intake Engine', sub: 'GMAIL · RSS · WEBHOOKS · API', breadcrumb: ['Operations', 'Intake'] },
  academy:    { title: 'Academy', sub: 'COURSES · LESSONS · CERTIFICATION', breadcrumb: ['Learn', 'Academy'] },
  team:       { title: 'Workspace & Team', sub: 'MEMBERS · ROLES · ASSETS', breadcrumb: ['System', 'Team'] },
  settings:   { title: 'Settings', sub: 'PROFILE · SECURITY · SOURCES', breadcrumb: ['System', 'Settings'] },
};

Object.assign(window, { TICKERS, NAV, SCREEN_META });
